"""Offline regressions for asset identity, entity scope and restartable access."""

import copy
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from musicbrainz import APIError
from phase2b import SAMPLE_SHA256, enrich, load_sample, metadata
from phase2b_report import coverage_flags, summarize
from wikidata import WikidataClient
from wikidata_match import MATCHER_VERSION, credit_evidence, decide


def statement(value, rank="normal", **extra):
    return dict({"rank": rank, "mainsnak": {"snaktype": "value", "datavalue": {"value": value}}}, **extra)


def item(qid, name, **props):
    return {"id": qid, "lastrevid": 123, "labels": {"en": {"language": "en", "value": name}},
            "claims": {p: [statement({"id": v}) for v in vals] for p, vals in props.items()}}


def song(**changes):
    return dict({"song_id": "song", "title": "Our Song", "artist": "One Artist", "first_chart_date": "1970-01-01"}, **changes)


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.artist = item("Q1", "One Artist")
        self.track = item("Q2", "Our Song", P31=["Q7366"], P175=["Q1"])
        self.context = {"Q1": self.artist}

    def test_exact_asset_does_not_require_one_recording_or_release_date(self):
        duplicate = dict(self.track, id="Q3")
        original = copy.deepcopy(self.track)
        result = decide(song(), {"Q2": self.track, "Q3": duplicate}, self.context)
        self.assertEqual(result["status"], "high_confidence")
        self.assertEqual(result["selected_entity_ids"], ["Q2", "Q3"])
        self.assertEqual(self.track, original)

    def test_same_title_different_artist_is_not_a_found_asset(self):
        self.context["Q1"] = item("Q1", "Someone Else")
        result = decide(song(), {"Q2": self.track}, self.context)
        self.assertEqual(result["status"], "not_found")
        self.assertFalse(result["found"])

    def test_featured_artist_must_be_present(self):
        result = decide(song(artist="One Artist Featuring Guest"), {"Q2": self.track}, self.context)
        self.assertEqual(result["status"], "ambiguous")
        self.context["Q3"] = item("Q3", "Guest")
        self.track["claims"]["P175"].append(statement({"id": "Q3"}))
        self.assertEqual(decide(song(artist="One Artist feat. Guest"), {"Q2": self.track}, self.context)["status"], "high_confidence")

    def test_ensemble_name_is_matched_whole_and_aliases_are_provider_evidence(self):
        band = item("Q1", "The Band, With A Name")
        band["aliases"] = {"en": [{"language": "en", "value": "Band, With A Name"}]}
        self.assertTrue(credit_evidence("Band, With A Name", {"Q1": band})["full_credit_exact"])
        self.assertFalse(credit_evidence("Band With A Name", {"Q1": band})["full_credit_exact"])

    def test_composition_with_multiple_cover_performers_is_ambiguous(self):
        self.context["Q3"] = item("Q3", "Cover Artist")
        self.track["claims"]["P175"].append(statement({"id": "Q3"}))
        result = decide(song(), {"Q2": self.track}, self.context)
        self.assertEqual(result["status"], "ambiguous")
        self.assertFalse(result["selected_entity_ids"])

    def test_unknown_performer_and_homonymous_artist_ids_block_acceptance(self):
        self.track["claims"]["P175"].append({"rank": "normal", "mainsnak": {"snaktype": "somevalue"}})
        self.assertEqual(decide(song(), {"Q2": self.track}, self.context)["status"], "ambiguous")
        self.track["claims"]["P175"].pop()
        other = item("Q4", "Our Song", P31=["Q7366"], P175=["Q3"])
        self.context["Q3"] = item("Q3", "One Artist")
        self.assertEqual(decide(song(), {"Q2": self.track, "Q4": other}, self.context)["reason"], "different_artist_entities_share_the_credit")

    def test_album_is_not_song_and_subclass_path_is_kept(self):
        self.track["claims"]["P31"] = [statement({"id": "Q482994"})]
        self.assertEqual(decide(song(), {"Q2": self.track}, self.context)["status"], "ambiguous")
        self.track["claims"]["P31"] = [statement({"id": "Q99"})]
        self.context["Q99"] = item("Q99", "vocal track", P279=["Q7302866"])
        result = decide(song(), {"Q2": self.track}, self.context)
        self.assertEqual(result["status"], "high_confidence")
        self.assertEqual(result["candidates"][0]["evidence"]["music_type_paths"], [["Q99", "Q7302866"]])

    def test_bounded_search_flags_and_late_dates_remain_visible(self):
        self.track["claims"]["P577"] = [statement({"time": "+2020-01-01T00:00:00Z", "precision": 11})]
        result = decide(song(), {"Q2": self.track}, self.context, truncated=True)
        self.assertEqual(result["status"], "high_confidence")
        self.assertTrue(result["search_truncated"])
        self.assertTrue(result["candidates"][0]["evidence"]["all_publication_years_after_chart"])
        self.assertEqual(decide(song(), {}, {}, truncated=True)["status"], "ambiguous")

    def test_unexpected_remix_description_blocks_selection(self):
        self.track["descriptions"] = {"en": {"value": "a 2001 remix"}}
        self.assertEqual(decide(song(), {"Q2": self.track}, self.context)["status"], "ambiguous")

    def test_errors_do_not_become_negative_search_results(self):
        client = Mock()
        client.get.side_effect = APIError("test transport failure", "cache-id")
        result = enrich(song(), client)
        self.assertEqual(result["status"], "error")
        self.assertIn("cache-id", result["cache_keys"])

    def test_sample_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            path.write_text('{"songs": []}')
            with self.assertRaisesRegex(ValueError, "differs"):
                load_sample(path)


class Response(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/json"}


class ReportingTests(unittest.TestCase):
    def result(self, identifier="song", status="high_confidence", **extra):
        return dict({"song": song(song_id=identifier, period="1958–1969"), "status": status,
                     "matcher_version": MATCHER_VERSION, "sample_sha256": SAMPLE_SHA256,
                     "found": status == "high_confidence", "reason": "test", "metadata": {}}, **extra)

    def test_artist_and_album_genres_never_count_as_song_genres(self):
        artist = item("Q1", "Artist", P136=["Q10"])
        album = item("Q3", "Album", P136=["Q11"])
        result = self.result(metadata={"entities": [item("Q2", "Song")], "artists": [artist], "parents": [album], "album_ids": ["Q3"]})
        fields = coverage_flags(result)
        self.assertTrue(fields["artist_context_genres"])
        self.assertTrue(fields["album_context_genres"])
        self.assertFalse(fields["song_item_genres"])
        result["status"] = "ambiguous"
        self.assertFalse(any(coverage_flags(result).values()))

    def test_raw_qualified_and_deprecated_genres_survive_but_counts_are_separate(self):
        track = item("Q2", "Song", P136=["Q10"])
        track["claims"]["P136"][0]["qualifiers"] = {"P580": [{"raw": "untouched"}]}
        track["claims"]["P136"].append(statement({"id": "Q11"}, rank="deprecated"))
        expected = copy.deepcopy(track["claims"]["P136"])
        client = Mock()
        client.entities.side_effect = lambda ids: ({qid: item(qid, "Raw Genre Label") for qid in ids}, [])
        output, _ = metadata({"Q2": track}, {}, client)
        self.assertEqual([row["raw_statement"] for row in output["raw_genres"]], expected)
        self.assertEqual(output["raw_genres"][0]["genre_label"], "Raw Genre Label")
        fields = coverage_flags(self.result(metadata=output))
        self.assertTrue(fields["song_item_genres"])
        self.assertFalse(fields["song_item_genres_unqualified"])
        track["claims"]["P136"][0]["rank"] = "deprecated"
        self.assertFalse(coverage_flags(self.result(metadata=output))["song_item_genres"])

    def test_pending_and_coverage_denominators_remain_explicit(self):
        high = self.result(metadata={"entities": [item("Q2", "Song", P136=["Q10"])]})
        other = self.result("other", "not_found")
        sample = {"songs": [high["song"], other["song"]]}
        a_results = [dict(high, metadata={}), other]
        result = summarize(sample, [high], a_results)
        self.assertEqual(result["pending"], 1)
        self.assertEqual(result["high_confidence_percent"], 50)
        self.assertEqual(result["coverage"]["song_item_genres"]["percent_of_high_confidence"], 100)
        self.assertEqual(result["coverage"]["song_item_genres"]["percent_of_sample"], 50)
        with self.assertRaises(ValueError):
            summarize(sample, [high, high], a_results)
        bad = copy.deepcopy(other)
        bad["song"]["artist"] = "changed identity"
        with self.assertRaises(ValueError):
            summarize(sample, [bad], a_results)

    def test_single_genres_are_reported_separately_from_track_genres(self):
        entity = item("Q2", "Song", P136=["Q10"], P31=["Q134556"])
        candidate = {"entity_id": "Q2", "evidence": {"music_type_paths": [["Q134556"]]}}
        result = self.result(metadata={"entities": [entity]}, candidates=[candidate])
        fields = coverage_flags(result)
        self.assertTrue(fields["single_release_item_genres"])
        self.assertFalse(fields["recording_or_track_item_genres"])
        self.assertTrue(fields["song_item_genres"])

    def test_missing_genre_label_is_not_replaced_with_an_invented_label(self):
        entity = item("Q2", "Song", P136=["Q10"])
        client = Mock()
        client.entities.side_effect = lambda ids: ({qid: {"id": qid, "labels": {}} for qid in ids}, [])
        output, _ = metadata({"Q2": entity}, {}, client)
        self.assertEqual(output["raw_genres"][0]["genre_id"], "Q10")
        self.assertIsNone(output["raw_genres"][0]["genre_label"])


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        self.now = 1000.0

    def sleep(self, seconds):
        self.now += seconds

    def client(self, opener, **kwargs):
        return WikidataClient(self.path, opener=opener, clock=lambda: self.now, sleep=self.sleep, **kwargs)

    def test_entity_batches_reuse_cache_after_restart_and_offline(self):
        payload = {"entities": {"Q1": item("Q1", "Artist"), "Q2": item("Q2", "Song")}}
        opener = Mock(side_effect=lambda *a, **kw: Response(json.dumps(payload).encode()))
        with self.client(opener) as client:
            entities, keys = client.entities(["Q2", "Q1"])
            self.assertEqual(client.entities(["Q1"])[0]["Q1"], payload["entities"]["Q1"])
            self.assertEqual(client.network_requests, 1)
        blocked = Mock(side_effect=AssertionError("Network forbidden"))
        with self.client(blocked, offline=True) as client:
            self.assertEqual(client.entities(["Q1", "Q2"]), (entities, keys))
            with self.assertRaises(APIError):
                client.entities(["Q3"])
        self.assertEqual(blocked.call_count, 0)

    def test_maxlag_is_retried_and_all_attempts_survive(self):
        lag = Response(b'{"error": {"code": "maxlag", "info": "lagged"}}')
        lag.headers = {"Retry-After": "7"}
        opener = Mock(side_effect=[lag, Response(b'{"search": []}')])
        with self.client(opener) as client:
            payload, key = client.get(action="wbsearchentities", search="Test")
        self.assertEqual(payload["search"], [])
        self.assertGreaterEqual(self.now, 1007)
        saved = json.loads((self.path / "requests" / (key + ".json")).read_text())
        self.assertEqual(len(saved["attempts"]), 2)
        self.assertIn("maxlag", saved["attempts"][0]["error"])

    def test_throttle_persists_and_failed_requests_require_explicit_retry(self):
        opener = Mock(side_effect=lambda *a, **kw: Response(b'{}'))
        with self.client(opener) as client:
            client.get(action="one")
        with self.client(opener) as client:
            client.get(action="two")
        self.assertGreaterEqual(self.now, 1001.09)
        error = urllib.error.HTTPError("url", 400, "bad", {}, io.BytesIO(b"bad"))
        failed = Mock(side_effect=error)
        with self.client(failed) as client:
            with self.assertRaises(APIError):
                client.get(action="bad")
            with self.assertRaises(APIError):
                client.get(action="bad")
        self.assertEqual(failed.call_count, 1)
        with self.client(opener, retry_errors=True) as client:
            client.get(action="bad")

    def test_cache_tampering_is_detected_before_use(self):
        with self.client(Mock(return_value=Response(b'{"search": []}'))) as client:
            _, key = client.get(action="search")
        path = self.path / "requests" / (key + ".json")
        saved = json.loads(path.read_text())
        saved["attempts"][0]["body"] = '{}'
        path.write_text(json.dumps(saved))
        with self.assertRaisesRegex(APIError, "checksum"):
            with self.client(Mock(), offline=True):
                pass


if __name__ == "__main__":
    unittest.main()
