#!/usr/bin/env python3
"""Build or validate Phase 1 locally, using only the Python standard library."""

import argparse
import csv
import hashlib
import json
import os
import platform
import sqlite3
import sys
import tempfile
import unicodedata
from contextlib import ExitStack, closing
from pathlib import Path

from billboard import (
    IDENTITY_VERSION, NORMALIZATION_VERSION, OBSERVATION_COLUMNS, ROOT, SONG_COLUMNS,
    SOURCE_URL, DataError, pipeline_sha256, read_source, source_label,
)
from quality import analyze_source, markdown_report, table_rows, validate_csvs, validate_database


SCHEMA_VERSION = "1"
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE songs (
    song_id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    normalized_artist TEXT NOT NULL,
    UNIQUE (title, artist)
);
CREATE TABLE chart_observations (
    song_id TEXT NOT NULL REFERENCES songs(song_id),
    chart_date TEXT NOT NULL,
    rank INTEGER,
    last_week INTEGER,
    peak_position INTEGER,
    weeks_on_chart INTEGER,
    source_chart_index INTEGER NOT NULL CHECK (source_chart_index >= 0),
    source_row_index INTEGER NOT NULL CHECK (source_row_index >= 0),
    PRIMARY KEY (source_chart_index, source_row_index)
);
CREATE INDEX observations_song_date ON chart_observations(song_id, chart_date);
CREATE INDEX observations_date_rank ON chart_observations(chart_date, rank);
CREATE INDEX songs_normalized_identity ON songs(normalized_title, normalized_artist);
CREATE TABLE build_metadata (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
);
PRAGMA user_version = 1;
"""


def build_metadata(source):
    return {
        "schema_version": SCHEMA_VERSION,
        "source_repository": SOURCE_URL,
        "source_path": source_label(source.path),
        "source_sha256": source.sha256,
        "source_bytes": str(source.byte_count),
        "source_weekly_charts": str(len(source.charts)),
        "source_observations": str(source.observation_count),
        "source_chart_inventory": json.dumps(
            [[chart["date"], len(chart["data"])] for chart in source.charts], separators=(",", ":")
        ),
        "upstream_commit": "unknown; not supplied",
        "source_acquired_at": "unknown; not supplied",
        "identity_version": IDENTITY_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "pipeline_sha256": pipeline_sha256(),
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
        "unicode_version": unicodedata.unidata_version,
    }


def _inside(path, directory):
    return path == directory or directory in path.parents


def output_paths(source_path, output_dir, report_path):
    source_path, output_dir, report_path = (Path(p).resolve() for p in (source_path, output_dir, report_path))
    if report_path.suffix != ".md":
        raise DataError("Report path must end in .md (the full audit uses the same stem with .json)")
    paths = {
        "music.db": output_dir / "music.db",
        "songs.csv": output_dir / "songs.csv",
        "chart_observations.csv": output_dir / "chart_observations.csv",
        "report.md": report_path,
        "report.json": report_path.with_suffix(".json"),
    }
    resolved = [path.resolve() for path in paths.values()]
    immutable_dir = (ROOT / "data" / "raw").resolve()
    if len(set(resolved)) != len(resolved):
        raise DataError("Output paths overlap")
    for path in resolved:
        if path == source_path or _inside(path, immutable_dir):
            raise DataError("Refusing to write to the source file or immutable data/raw/: " + str(path))
        if path.exists() and not path.is_file():
            raise DataError("Output target is not a regular file: " + str(path))
    return paths


def populate_database(connection, source, metadata):
    connection.executescript(SCHEMA)
    with connection:
        connection.executemany("INSERT INTO songs VALUES (?, ?, ?, ?, ?)", source.songs)
        connection.executemany("INSERT INTO chart_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", source.observations())
        connection.executemany("INSERT INTO build_metadata VALUES (?, ?)", sorted(metadata.items()))


def export_csvs(connection, directory):
    for table, columns in (("songs", SONG_COLUMNS), ("chart_observations", OBSERVATION_COLUMNS)):
        with (directory / (table + ".csv")).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\r\n")
            writer.writerow(columns)
            writer.writerows(table_rows(connection, table))


def _unchanged_source(source):
    if hashlib.sha256(source.path.read_bytes()).hexdigest() != source.sha256:
        raise DataError("Source changed during the operation; no build will be published")


def build(source_path, output_dir, report_path):
    paths = output_paths(source_path, output_dir, report_path)
    source = read_source(source_path)
    quality = analyze_source(source)
    metadata = build_metadata(source)
    paths["music.db"].parent.mkdir(parents=True, exist_ok=True)
    paths["report.md"].parent.mkdir(parents=True, exist_ok=True)
    # Stage in each destination filesystem. Validation failures leave prior outputs intact.
    with ExitStack() as stack:
        data_stage = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=".phase1-", dir=paths["music.db"].parent)))
        report_stage = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=".phase1-", dir=paths["report.md"].parent)))
        with closing(sqlite3.connect(str(data_stage / "music.db"))) as connection:
            populate_database(connection, source, metadata)
            validation = validate_database(connection, source)
            export_csvs(connection, data_stage)
            validate_csvs(connection, data_stage)
        validation["csv_exports_match_database"] = True
        report = {"provenance": metadata, "quality": quality, "validation": validation}
        (report_stage / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (report_stage / "report.md").write_text(markdown_report(report, paths["report.json"].name), encoding="utf-8")
        _unchanged_source(source)
        # Individual replacements are atomic; a process/OS failure between them can
        # leave mixed exports. The read-only validate command detects that; rebuild repairs it.
        for name in ("music.db", "songs.csv", "chart_observations.csv"):
            os.replace(data_stage / name, paths[name])
        for name in ("report.json", "report.md"):
            os.replace(report_stage / name, paths[name])
    return report


def validate(source_path, output_dir, report_path):
    paths = output_paths(source_path, output_dir, report_path)
    source = read_source(source_path)
    with closing(sqlite3.connect(paths["music.db"].as_uri() + "?mode=ro", uri=True)) as connection:
        validation = validate_database(connection, source)
        metadata = dict(connection.execute("SELECT key, value FROM build_metadata"))
        expected_metadata = build_metadata(source)
        # Recorded acquisition path and original runtime may differ on another machine.
        for key in ("schema_version", "identity_version", "normalization_version", "pipeline_sha256", "source_chart_inventory", "source_repository"):
            if metadata.get(key) != expected_metadata[key]:
                raise DataError("Build metadata/code mismatch for {}; rebuild with this pipeline".format(key))
        validate_csvs(connection, paths["music.db"].parent)
    validation["csv_exports_match_database"] = True
    report = {"provenance": metadata, "quality": analyze_source(source), "validation": validation}
    expected_json = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if paths["report.json"].read_text(encoding="utf-8") != expected_json:
        raise DataError("Full audit report differs from source/database validation; rebuild")
    if paths["report.md"].read_text(encoding="utf-8") != markdown_report(report, paths["report.json"].name):
        raise DataError("Markdown quality report differs from source/database validation; rebuild")
    _unchanged_source(source)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate"))
    parser.add_argument("--source", type=Path, default=ROOT / "data/raw/billboard-hot-100.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/phase1_data_quality.md")
    args = parser.parse_args(argv)
    try:
        report = {"build": build, "validate": validate}[args.command](args.source, args.output_dir, args.report)
    except (DataError, OSError, sqlite3.Error) as exc:
        print("Phase 1 failed: {}".format(exc), file=sys.stderr)
        return 1
    counts, anomalies = report["quality"]["counts"], report["quality"]["anomalies"]
    print("Phase 1 {} passed: {:,} charts; {:,} observations; {:,} exact songs; {:,} artist credits.".format(args.command, counts["weekly_charts"], counts["chart_observations"], counts["songs"], counts["artist_credits"]))
    print("Retained source anomalies: {} non-100-entry charts; {} duplicate song/week groups; {} normalized collision groups; {} inconsistent peaks.".format(len(anomalies["charts_with_non_100_entries"]), len(anomalies["duplicate_song_week_groups"]), len(anomalies["normalized_identity_collisions"]), len(anomalies["peak_worse_than_current_rank"])))
    print("Source SHA-256: " + report["provenance"]["source_sha256"])
    print("Quality report: " + str(args.report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
