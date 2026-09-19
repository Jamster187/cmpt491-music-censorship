"""Offline regressions for asset matching, provenance, and metadata semantics."""

import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from musicbrainz_asset_match import credit_compatible, date_bounds, decide, text_key
from phase2ar import ROOT, CACHE, OLD, read_cache, replay_song
from phase2ar_report import coverage, review_sample


def song(**kwargs):
    return dict({"title": "Our Song", "artist": "One Artist", "first_chart_date": "1975-04-05"}, **kwargs)


def candidate(rid="r1", **kwargs):
    return dict({"id": rid, "title": "Our Song", "artist-credit": [
        {"artist": {"id": "a1", "name": "One Artist"}}], "first-release-date": "1975-02", "score": 100}, **kwargs)


class AssetMatchingTests(unittest.TestCase):
    def test_multiple_recordings_support_one_asset(self):
        r = decide(song(), [candidate(), candidate("r2")])
        self.assertEqual(r["asset_match_status"], "high_confidence")
        self.assertEqual(r["supporting_recording_ids"], ["r1", "r2"])
        self.assertEqual(r["canonical_recording_status"], "unresolved_multiple")

    def test_late_and_undated_reissues_can_use_asset_anchor(self):
        r = decide(song(), [candidate(), candidate("r2", **{"first-release-date": "2010"}), candidate("r3", **{"first-release-date": ""})])
        self.assertEqual(len(r["supporting_recording_ids"]), 3)
        self.assertIn("later_or_undated_recordings_supported_by_asset_anchor", r["review_flags"])

    def test_late_only_not_impossible_but_still_unresolved(self):
        r = decide(song(), [candidate(**{"first-release-date": "2010"})])
        self.assertEqual(r["reason"], "compatible_identity_but_no_temporal_anchor")
        self.assertFalse(r["candidates"][0]["impossible_artist_chronology"])

    def test_explicit_artist_chronology_blocks_match(self):
        r = decide(song(), [candidate()], {"a1": {"type": "Person", "life-span": {"begin": "1980-01-01"}}})
        self.assertEqual(r["asset_match_status"], "ambiguous")
        self.assertTrue(r["candidates"][0]["impossible_artist_chronology"])

    def test_homonymous_artist_ids_not_merged(self):
        other = candidate("r2", **{"artist-credit": [{"artist": {"id": "different", "name": "One Artist"}}]})
        self.assertEqual(decide(song(), [candidate(), other])["reason"], "competing_artist_identities")

    def test_wrong_artist_cannot_supply_temporal_anchor(self):
        other = candidate("r2", **{"artist-credit": [{"artist": {"id": "other", "name": "Other Artist"}}]})
        r = decide(song(), [candidate(**{"first-release-date": "2010"}), other])
        self.assertEqual(r["reason"], "compatible_identity_but_no_temporal_anchor")

    def test_no_fuzzy_title_or_parenthetical_dropping(self):
        for title in ("Our Songs", "Our Song (Part Two)", "Song"):
            self.assertEqual(decide(song(), [candidate(title=title)])["asset_match_status"], "ambiguous")

    def test_punctuation_preserves_word_boundaries_and_symbols(self):
        self.assertEqual(text_key("Don't—Go"), text_key("Dont Go"))
        self.assertNotEqual(text_key("Re-sign"), text_key("Resign"))
        self.assertNotEqual(text_key("P!nk", True), text_key("Pink", True))
        self.assertNotEqual(text_key("A+B", True), text_key("AB", True))

    def test_accents_and_articles_are_artist_only(self):
        self.assertEqual(text_key("The Monáes", True), text_key("Monaes", True))
        self.assertNotEqual(text_key("The Song"), text_key("Song"))
        self.assertNotEqual(text_key("Á"), text_key("A"))

    def test_full_featured_credit_required(self):
        c = candidate(**{"artist-credit": [
            {"name": "One Artist", "artist": {"id": "a1", "name": "One Artist"}, "joinphrase": " feat. "},
            {"name": "Guest", "artist": {"id": "a2", "name": "Guest"}}]})
        for credit in ("One Artist Featuring Guest", "One Artist & Guest", "One Artist With Guest"):
            self.assertTrue(credit_compatible(credit, c))
        self.assertFalse(credit_compatible("One Artist", c))
        self.assertFalse(credit_compatible("One Artist Featuring Other", c))

    def test_with_inside_band_name_is_not_connector(self):
        c = candidate(**{"artist-credit": [{"artist": {"id": "a1", "name": "Man With A Mission"}}]})
        self.assertFalse(credit_compatible("Man And A Mission", c))

    def test_unrecognized_versions_do_not_supply_metadata(self):
        for descriptor in ("club mix", "Simplified version", "2 Meter Sessie", "DJ Blazita mix", "2019 version", "live", "re-recording"):
            r = decide(song(), [candidate(), candidate("bad", disambiguation=descriptor)])
            self.assertEqual(r["supporting_recording_ids"], ["r1"], descriptor)

    def test_benign_editions_do_not_force_unique_recording(self):
        for descriptor in ("remastered", "2011 remaster", "mono", "single version", "Dolby Atmos mix, explicit", "clean"):
            self.assertEqual(len(decide(song(), [candidate(), candidate("r2", disambiguation=descriptor)])["supporting_recording_ids"]), 2)

    def test_clean_explicit_content_stays_flagged(self):
        r = decide(song(), [candidate(disambiguation="clean"), candidate("r2", disambiguation="explicit")])
        self.assertIn("content_version_requires_future_resolution", r["review_flags"])

    def test_implausible_duration_retained_but_flagged_not_corrected(self):
        r = decide(song(), [candidate(length=3000)])
        self.assertIn("duration_outlier_review", r["review_flags"])
        self.assertEqual(r["candidates"][0]["duration_ms"], 3000)

    def test_release_date_can_anchor_missing_recording_date(self):
        c = candidate(**{"first-release-date": "", "releases": [{"id": "rel", "date": "1974"}]})
        self.assertEqual(decide(song(), [c])["asset_match_status"], "high_confidence")

    def test_partial_and_invalid_dates(self):
        self.assertEqual(date_bounds("1975"), (dt.date(1975, 1, 1), dt.date(1975, 12, 31)))
        self.assertEqual(date_bounds("1976-02")[1], dt.date(1976, 2, 29))
        for value in ("1975-02-30", "unknown", "1975-13", None):
            self.assertIsNone(date_bounds(value))

    def test_year_tolerance_flag_distinguishes_same_year(self):
        later = decide(song(), [candidate(**{"first-release-date": "1975-08"})])
        next_year = decide(song(), [candidate(**{"first-release-date": "1976"})])
        self.assertNotIn("anchor_only_in_following_year", later["review_flags"])
        self.assertIn("anchor_only_in_following_year", next_year["review_flags"])
        self.assertEqual(decide(song(), [candidate(**{"first-release-date": "1977"})])["asset_match_status"], "ambiguous")

    def test_search_relevance_is_not_identity_probability(self):
        self.assertEqual(decide(song(), [candidate(score=60)])["asset_match_status"], "high_confidence")
        self.assertEqual(decide(song(), [candidate(title="Wrong", score=100)])["asset_match_status"], "ambiguous")

    def test_truncation_visible_without_recording_uniqueness_requirement(self):
        r = decide(song(), [candidate()], truncated=True)
        self.assertEqual(r["asset_match_status"], "high_confidence")
        self.assertIn("bounded_search_truncated", r["review_flags"])

    def test_not_found_only_for_empty_candidates(self):
        self.assertEqual(decide(song(), [])["asset_match_status"], "not_found")
        self.assertEqual(decide(song(), [candidate(title="Wrong")])["asset_match_status"], "ambiguous")

    def test_decisions_are_order_invariant_and_do_not_mutate_input(self):
        inputs = [candidate("z"), candidate("a")]
        saved = copy.deepcopy(inputs)
        self.assertEqual(decide(song(), inputs), decide(song(), list(reversed(inputs))))
        self.assertEqual(inputs, saved)


class OfflineIntegrityTests(unittest.TestCase):
    def test_missing_cache_fails_instead_of_negative_result(self):
        with self.assertRaises(KeyError):
            replay_song(song(), {"searches": [{"cache_key": "missing"}]}, {}, {})

    def test_corrupt_body_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            url = "https://musicbrainz.org/ws/2/recording?query=test"
            key = hashlib.sha256(url.encode()).hexdigest()
            envelope = {"url": url, "cache_key": key, "attempts": [{"status": 200, "body": "{}", "body_sha256": "wrong"}]}
            (base / (key + ".json")).write_text(json.dumps(envelope))
            with patch("phase2ar.ROOT", base), self.assertRaisesRegex(ValueError, "checksum"):
                read_cache(base)

    def test_artist_genres_do_not_become_recording_genres(self):
        r = {"metadata_evidence": [{"level": "artist", "response_kind": "lookup", "raw": {"genres": [{"name": "rock"}]}}],
             "candidates": [], "supporting_recording_ids": [], "supporting_artist_ids": ["a"], "linked_release_group_ids": []}
        flags = coverage(r)
        self.assertTrue(flags["artist_genres"])
        self.assertFalse(flags["recording_genres"])
        self.assertFalse(flags["recording_lookup_available"])

    @unittest.skipUnless((OLD / "sample.json").exists() and CACHE.exists(), "local frozen cache required")
    def test_full_sample_offline_replay(self):
        with patch("socket.create_connection", side_effect=AssertionError("Network prohibited")), patch("urllib.request.urlopen", side_effect=AssertionError("HTTP prohibited")):
            responses, entities, _ = read_cache(CACHE)
            songs = json.loads((OLD / "sample.json").read_text())["songs"]
            rows = []
            for s in songs:
                old = json.loads((OLD / "results" / (s["song_id"] + ".json")).read_text())
                row = replay_song(s, old, responses, entities)
                rows.append(row)
                supported = [c for c in row["candidates"] if c["recording_id"] in row["supporting_recording_ids"]]
                self.assertTrue(all(c["compatible"] for c in supported))
                if supported:
                    self.assertEqual(len({tuple(c["artist_ids"]) for c in supported}), 1)
                    self.assertTrue(any(c["temporal_anchor"] for c in supported))
                self.assertTrue(all(m["entity_id"] in row["supporting_recording_ids"] for m in row["metadata_evidence"] if m["level"] == "recording"))
            self.assertEqual(len(rows), 200)
            self.assertEqual(review_sample(rows), review_sample(list(reversed(rows))))
            self.assertGreaterEqual(len(review_sample(rows)), min(40, sum(r["newly_accepted"] for r in rows)))


if __name__ == "__main__":
    unittest.main()
