"""Offline regressions for sampling, precision-first decisions, and HTTP caching."""

import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metadata_match import comparison_key, decide, query_literal
from musicbrainz import APIError, MusicBrainzClient
from phase2a import PERIODS, enrich_song, select_sample
from enrichment_report import coverage_flags, summarize


def song(**changes):
    return dict({"song_id": "billboard-song", "title": "Our Song", "artist": "One Artist", "first_chart_date": "1975-04-05"}, **changes)


def candidate(identifier="recording-1", **changes):
    return dict({"id": identifier, "title": "Our Song", "artist-credit": [{"artist": {"id": "artist-1", "name": "One Artist"}}],
                 "first-release-date": "1975-02", "score": 100, "length": 180000}, **changes)


class MatchingTests(unittest.TestCase):
    def test_accepts_single_exact_candidate_with_date_evidence(self):
        result = decide(song(), [candidate()])
        self.assertEqual(result["status"], "high_confidence")
        self.assertEqual(result["selected_recording_id"], "recording-1")

    def test_same_title_different_performer_is_not_accepted(self):
        other = candidate(**{"artist-credit": [{"artist": {"id": "other", "name": "Other Artist"}}]})
        self.assertEqual(decide(song(), [other])["status"], "ambiguous")

    def test_missing_featured_artist_is_not_accepted(self):
        self.assertEqual(decide(song(artist="One Artist Featuring Guest"), [candidate()])["status"], "ambiguous")
        self.assertEqual(comparison_key("One Artist Featuring Guest", True), comparison_key("One Artist feat. Guest", True))

    def test_recording_competitors_missing_dates_and_truncation_block_selection(self):
        alternatives = [candidate("recording-2"), candidate("recording-2", **{"first-release-date": None})]
        for rival in alternatives:
            self.assertEqual(decide(song(), [candidate(), rival])["status"], "ambiguous")
        self.assertEqual(decide(song(), [candidate()], truncated=True)["status"], "ambiguous")

    def test_release_dates_do_not_accept_late_reissues_or_missing_evidence(self):
        for value in ("2000", "", None):
            result = decide(song(), [candidate(**{"first-release-date": value})])
            self.assertEqual(result["status"], "ambiguous")

    def test_unexpected_versions_and_video_are_not_accepted(self):
        for extra in ({"disambiguation": "Live at a concert"}, {"video": True}, {"title": "Our Song (remix)"}, {"score": 80}):
            self.assertEqual(decide(song(), [candidate(**extra)])["status"], "ambiguous")

    def test_empty_results_are_not_found_and_query_is_escaped(self):
        self.assertEqual(decide(song(), [])["status"], "not_found")
        self.assertEqual(query_literal('A "Song" (Live)'), '"A \\"Song\\" \\(Live\\)"')
        self.assertNotEqual(comparison_key("Beyoncé"), comparison_key("Beyonce"))

    def test_api_failure_does_not_become_not_found(self):
        client = Mock()
        client.get.side_effect = APIError("Unavailable", "request-key")
        result = enrich_song(song(), client)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_cache_key"], "request-key")


class SamplingTests(unittest.TestCase):
    def test_deterministic_balanced_unique_sample_and_year_coverage(self):
        rows = []
        for _, start, end, _ in PERIODS:
            for year in range(start, end + 1):
                for index in range(10):
                    rows.append({"song_id": "{}-{}".format(year, index), "first_chart_date": "{}-01-01".format(year),
                                 "difficulty_flags": ["common_title", "unusual_credit", "punctuation_heavy", "featured_artists"]})
        actual = select_sample(rows)
        self.assertEqual(actual, select_sample(list(reversed(rows))))
        self.assertEqual(len(actual), 200)
        self.assertEqual(len({row["song_id"] for row in actual}), 200)
        self.assertEqual(len({row["first_chart_date"][:4] for row in actual}), 69)
        for label, _, _, count in PERIODS:
            self.assertEqual(sum(row["period"] == label for row in actual), count)


class ReportingTests(unittest.TestCase):
    def test_artist_tags_are_not_counted_as_recording_genres(self):
        result = {"status": "high_confidence", "metadata": {"recording": {"id": "recording-1"},
                  "artists": [{"id": "artist-1", "genres": [{"name": "rock", "count": 3}]}]}}
        flags = coverage_flags(result)
        self.assertTrue(flags["artist_genres"])
        self.assertFalse(flags["recording_genres"])
        self.assertFalse(flags["recording_tags"])
        result["status"] = "ambiguous"
        self.assertEqual(coverage_flags(result), {})

    def test_coverage_denominators_and_pending_are_explicit(self):
        sample = {"songs": [song(song_id=str(index), period="1970s", difficulty_flags=[], selection_reason="hash_fill") for index in range(4)]}
        base = {"matcher_version": "phase2a-strict-v1", "reason": "test", "metadata": {"recording": {"genres": [{"name": "rock", "count": 1}]}}}
        results = [dict(base, song=sample["songs"][i], status=status) for i, status in enumerate(("high_confidence", "high_confidence", "ambiguous"))]
        results[1]["metadata"] = {"recording": {}}
        summary = summarize(sample, results)
        self.assertEqual(summary["pending"], 1)
        self.assertEqual(summary["high_confidence_percent"], 50)
        self.assertEqual(summary["coverage"]["recording_genres"], {"count": 1, "percent_of_high_confidence": 50.0, "percent_of_sample": 25.0})

    def test_nonpositive_votes_remain_raw_but_are_separate_in_coverage(self):
        result = {"status": "high_confidence", "metadata": {"recording": {"genres": [{"name": "pop", "count": 0}]}}}
        flags = coverage_flags(result)
        self.assertTrue(flags["recording_genres"])
        self.assertFalse(flags["recording_positive_vote_genres"])


class Response(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/json"}


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        self.now = 1000.0
        self.sleeps = []

    def sleep(self, amount):
        self.sleeps.append(amount)
        self.now += amount

    def client(self, opener, **options):
        return MusicBrainzClient(self.path, opener=opener, clock=lambda: self.now, sleep=self.sleep, **options)

    def test_cached_results_and_offline_replay_never_request_network(self):
        opener = Mock(side_effect=lambda *a, **kw: Response(b'{"recordings": [], "count": 0}'))
        with self.client(opener) as client:
            first, key = client.get("recording", query='recording:"Test"')
            second, _ = client.get("recording", query='recording:"Test"')
            self.assertEqual(first, second)
            self.assertEqual(opener.call_count, 1)
        blocked = Mock(side_effect=AssertionError("Network forbidden"))
        with self.client(blocked, offline=True) as client:
            self.assertEqual(client.get("recording", query='recording:"Test"')[0], first)
            with self.assertRaisesRegex(APIError, "Offline cache miss"):
                client.get("artist/unknown")
        self.assertEqual(blocked.call_count, 0)
        saved = json.loads((self.path / "requests" / (key + ".json")).read_text())
        self.assertIn("requested_at", saved["attempts"][0])
        self.assertIn("CMPT491", saved["request_headers"]["User-Agent"])

    def test_rate_limit_is_shared_across_restarts(self):
        opener = Mock(side_effect=lambda *a, **kw: Response(b'{}'))
        with self.client(opener) as client:
            client.get("artist/one")
            client.get("artist/two")
        with self.client(opener) as client:
            client.get("artist/three")
        self.assertEqual(len(self.sleeps), 2)
        self.assertTrue(all(delay >= 1.09 for delay in self.sleeps))

    def test_retry_after_and_all_attempts_are_cached(self):
        error = urllib.error.HTTPError("url", 503, "Unavailable", {"Retry-After": "7"}, io.BytesIO(b"busy"))
        opener = Mock(side_effect=[error, Response(b'{"ok": true}')])
        with self.client(opener) as client:
            payload, key = client.get("recording/id")
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(sum(self.sleeps), 7)
        attempts = json.loads((self.path / "requests" / (key + ".json")).read_text())["attempts"]
        self.assertEqual([row["status"] for row in attempts], [503, 200])
        self.assertEqual(attempts[0]["body"], "busy")

    def test_failed_response_is_cached_until_explicit_retry(self):
        def fail(*args, **kwargs):
            raise urllib.error.HTTPError("url", 400, "Bad request", {}, io.BytesIO(b"error"))
        opener = Mock(side_effect=fail)
        with self.client(opener) as client:
            with self.assertRaises(APIError):
                client.get("recording/id")
            with self.assertRaisesRegex(APIError, "Cached request failed"):
                client.get("recording/id")
        self.assertEqual(opener.call_count, 1)


if __name__ == "__main__":
    unittest.main()
