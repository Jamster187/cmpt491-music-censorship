"""Regression tests for identity, lossless ingestion, provenance, and safe rebuilds."""

import copy
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from billboard import ROOT, DataError, normalize_text, read_source, song_id
from phase1 import build, output_paths, validate
from quality import analyze_source


def record(title="A Song", artist="An Artist", rank=1, **changes):
    row = {"song": title, "artist": artist, "this_week": rank, "last_week": None,
           "peak_position": 1, "weeks_on_chart": 1}
    row.update(changes)
    return row


class Phase1Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source_path = self.root / "source.json"
        self.output_dir = self.root / "processed"
        self.report_path = self.root / "reports" / "quality.md"

    def write_source(self, charts):
        self.source_path.write_text(json.dumps(charts, ensure_ascii=False), encoding="utf-8")
        return read_source(self.source_path)

    def run_build(self):
        return build(self.source_path, self.output_dir, self.report_path)

    def run_validate(self):
        return validate(self.source_path, self.output_dir, self.report_path)

    def artifact_hashes(self):
        paths = list(self.output_dir.iterdir()) + list(self.report_path.parent.iterdir())
        return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.is_file()}

    def test_ids_survive_reordering_and_appended_charts(self):
        first = {"date": "2020-01-04", "data": [record(), record("Other", rank=2)]}
        second = {"date": "2020-01-11", "data": [record()]}
        before = self.write_source([first, second]).identities
        after = self.write_source([second, first, {"date": "2020-01-18", "data": [record("New")]}]).identities
        self.assertTrue(all(after[key] == value for key, value in before.items()))
        self.assertNotEqual(song_id("a|b", "c"), song_id("a", "b|c"))
        self.assertNotEqual(song_id("Song", "Artist"), song_id("song", "Artist"))

    def test_conservative_normalization_and_original_strings(self):
        title = '  Cafe\u0301\t"Live"\r\n'
        rows = [record(title, "Straße"), record('Café "Live"', "STRASSE", rank=2)]
        source = self.write_source([{"date": "2020-01-04", "data": rows}])
        self.assertEqual(normalize_text(title), 'café "live"')
        self.assertEqual(normalize_text(" AC/DC feat. Beyoncé (Live) "), "ac/dc feat. beyoncé (live)")
        self.assertEqual(len(source.songs), 2)
        report = self.run_build()
        self.assertEqual(len(report["quality"]["anomalies"]["normalized_identity_collisions"]), 1)
        with sqlite3.connect(str(self.output_dir / "music.db")) as connection:
            self.assertEqual(connection.execute("SELECT title FROM songs WHERE artist = 'Straße'").fetchone()[0], title)
        self.run_validate()  # Also proves CSVs preserve quotes, CR/LF, tabs and Unicode.

    def test_repeated_observations_and_source_anomalies_are_preserved(self):
        row = record(peak_position=5)
        rows = [row, copy.deepcopy(row), record(rank=2, weeks_on_chart=0), record("Third", rank=101)]
        self.write_source([{"date": "2020-01-04", "data": rows}, {"date": "2020-01-16", "data": []}])
        report = self.run_build()
        anomalies = report["quality"]["anomalies"]
        self.assertEqual(report["quality"]["counts"]["chart_observations"], 4)
        self.assertEqual(report["validation"]["database_observations"], 4)
        self.assertEqual(anomalies["duplicate_song_week_extra_rows"], 2)
        self.assertEqual(len(anomalies["duplicate_rank_week_groups"]), 1)
        self.assertEqual(len(anomalies["exact_duplicate_observation_groups"]), 1)
        self.assertEqual(len(anomalies["peak_worse_than_current_rank"]), 2)
        self.assertEqual(len(anomalies["invalid_numeric_values"]), 2)
        self.assertEqual(anomalies["non_seven_day_intervals"][0]["days"], 12)
        self.assertEqual(json.loads(report["provenance"]["source_chart_inventory"]), [["2020-01-04", 4], ["2020-01-16", 0]])
        self.run_validate()

    def test_missing_keys_and_nulls_remain_distinguishable_in_audit(self):
        missing = record("Missing")
        del missing["last_week"]
        self.write_source([{"date": "2020-01-04", "data": [record(), missing]}])
        report = self.run_build()
        profile = report["quality"]["missingness"]["song_records"]["last_week"]
        self.assertEqual(profile["missing"], 1)
        self.assertEqual(profile["null"], 1)
        self.run_validate()

    def test_duplicate_dates_and_out_of_order_charts_are_reported(self):
        source = self.write_source([
            {"date": "2020-01-11", "data": [record()]},
            {"date": "2020-01-04", "data": [record()]},
            {"date": "2020-01-04", "data": [record()]},
        ])
        anomalies = analyze_source(source)["anomalies"]
        self.assertEqual(anomalies["out_of_order_chart_indices"], [1])
        self.assertEqual(anomalies["duplicate_chart_dates"], [{"chart_date": "2020-01-04", "count": 2}])
        self.run_build()
        self.run_validate()

    def test_rebuild_is_byte_reproducible_and_source_unchanged(self):
        self.write_source([{"date": "2020-01-04", "data": [record(), record("Other", rank=2)]}])
        original = self.source_path.read_bytes()
        self.run_build()
        before = self.artifact_hashes()
        self.run_build()
        self.assertEqual(before, self.artifact_hashes())
        self.assertEqual(self.source_path.read_bytes(), original)
        self.run_validate()

    def test_schema_errors_fail_without_replacing_existing_outputs(self):
        self.write_source([{"date": "2020-01-04", "data": [record()]}])
        self.run_build()
        before = self.artifact_hashes()
        bad_rows = [record(genre="invented"), record(this_week=True), record(last_week="NEW"),
                    record(artist=None), record(weeks_on_chart=1.5), record(weeks_on_chart=2**63)]
        for row in bad_rows:
            with self.subTest(row=row):
                self.source_path.write_text(json.dumps([{"date": "2020-01-04", "data": [row]}]), encoding="utf-8")
                with self.assertRaises(DataError):
                    self.run_build()
                self.assertEqual(before, self.artifact_hashes())

    def test_rejects_duplicate_json_keys_and_nonstandard_constants(self):
        for content in ('[{"date":"2020-01-04","date":"2020-01-11","data":[]}]', '[NaN]'):
            with self.subTest(content=content):
                self.source_path.write_text(content, encoding="utf-8")
                with self.assertRaises(DataError):
                    read_source(self.source_path)

    def test_rejects_invalid_chart_shape_and_dates(self):
        for value in ({}, [], [{"date": "2020-02-30", "data": []}], [{"date": "2020-01-04", "data": None}], [{"date": "2020-01-04", "data": [], "extra": 1}]):
            with self.subTest(value=value):
                self.source_path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(DataError):
                    read_source(self.source_path)

    def test_hash_collision_fails_instead_of_merging(self):
        self.write_source([{"date": "2020-01-04", "data": [record(), record("Other")]}])
        with patch("billboard.song_id", return_value="forced-collision"):
            with self.assertRaisesRegex(DataError, "collision"):
                read_source(self.source_path)

    def test_output_guards_protect_raw_source_and_symlinks(self):
        self.write_source([{"date": "2020-01-04", "data": [record()]}])
        with self.assertRaisesRegex(DataError, "immutable"):
            output_paths(self.source_path, ROOT / "data/raw", self.report_path)
        with self.assertRaisesRegex(DataError, "immutable"):
            output_paths(self.source_path, self.output_dir, ROOT / "data/raw/report.md")
        self.output_dir.mkdir()
        (self.output_dir / "songs.csv").symlink_to(self.source_path)
        original = self.source_path.read_bytes()
        with self.assertRaisesRegex(DataError, "immutable"):
            self.run_build()
        self.assertEqual(original, self.source_path.read_bytes())

    def test_report_failure_leaves_previous_artifacts_intact(self):
        self.write_source([{"date": "2020-01-04", "data": [record()]}])
        self.run_build()
        before = self.artifact_hashes()
        with patch("phase1.markdown_report", side_effect=RuntimeError("simulated report failure")):
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                self.run_build()
        self.assertEqual(before, self.artifact_hashes())

    def test_validation_detects_changed_values_and_foreign_keys(self):
        self.write_source([{"date": "2020-01-04", "data": [record()]}])
        for statement, expected in [
            ("UPDATE chart_observations SET rank = 2", "differs from source"),
            ("UPDATE songs SET title = 'Silently edited'", "differs from source"),
            ("UPDATE chart_observations SET song_id = 'nonexistent'", "Foreign-key"),
            ("UPDATE build_metadata SET value = 'wrong' WHERE key = 'source_sha256'", "provenance mismatch"),
            ("DELETE FROM chart_observations", "differs from source"),
        ]:
            with self.subTest(statement=statement):
                self.run_build()
                with sqlite3.connect(str(self.output_dir / "music.db")) as connection:
                    connection.execute(statement)
                with self.assertRaisesRegex(DataError, expected):
                    self.run_validate()

    def test_validation_detects_stale_exports_and_reports(self):
        self.write_source([{"date": "2020-01-04", "data": [record()]}])
        for path, expected in [(self.output_dir / "songs.csv", "CSV header"), (self.report_path, "Markdown quality"), (self.report_path.with_suffix(".json"), "Full audit")]:
            with self.subTest(path=path):
                self.run_build()
                path.write_text("changed", encoding="utf-8")
                with self.assertRaisesRegex(DataError, expected):
                    self.run_validate()

    def test_validation_does_not_create_a_missing_database(self):
        self.write_source([{"date": "2020-01-04", "data": [record()]}])
        with self.assertRaises(sqlite3.OperationalError):
            self.run_validate()
        self.assertFalse((self.output_dir / "music.db").exists())


if __name__ == "__main__":
    unittest.main()
