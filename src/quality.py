"""Source diagnostics, lossless-transform checks, and reproducible quality reports."""

import csv
import json
from collections import Counter, defaultdict
from datetime import date
from itertools import zip_longest

from billboard import (
    CHART_FIELDS, NUMERIC_FIELDS, OBSERVATION_COLUMNS, SONG_COLUMNS, SONG_FIELDS,
    DataError,
)


def _type_name(value):
    return {str: "string", int: "integer", list: "array", type(None): "null"}.get(type(value), type(value).__name__)


def _profile(records, fields):
    result = {field: {"missing": 0, "null": 0, "blank": 0, "types": Counter()} for field in fields}
    for row in records:
        for field, profile in result.items():
            if field not in row:
                profile["missing"] += 1
                continue
            value = row[field]
            profile["types"][_type_name(value)] += 1
            profile["null"] += value is None
            profile["blank"] += isinstance(value, str) and not value.strip()
    return result


def analyze_source(source):
    dates = Counter(chart["date"] for chart in source.charts)
    sizes = Counter(len(chart["data"]) for chart in source.charts)
    song_weeks = defaultdict(list)
    rank_weeks = defaultdict(list)
    exact_rows = defaultdict(list)
    ranges = {field: [] for field in NUMERIC_FIELDS}
    chart_exceptions, rank_exceptions, invalid_numeric, inconsistent_peaks = [], [], [], []
    for chart_index, chart in enumerate(source.charts):
        ranks = Counter(row.get("this_week") for row in chart["data"])
        chart_info = {
            "chart_date": chart["date"], "source_chart_index": chart_index,
            "entries": len(chart["data"]),
            "missing_ranks_1_to_100": sorted(set(range(1, 101)) - set(ranks)),
        }
        if len(chart["data"]) != 100:
            chart_exceptions.append(chart_info)
        if sorted(r for r in ranks.elements() if r is not None) != list(range(1, 101)) or None in ranks:
            rank_exceptions.append(chart_info)
        for row_index, row in enumerate(chart["data"]):
            ref = {"source_chart_index": chart_index, "source_row_index": row_index, "rank": row.get("this_week")}
            song_weeks[(chart["date"], row["song"], row["artist"])].append(ref)
            rank_weeks[(chart["date"], row.get("this_week"))].append(ref)
            exact_rows[(chart["date"], json.dumps(row, ensure_ascii=False, sort_keys=True))].append(ref)
            for field in NUMERIC_FIELDS:
                value = row.get(field)
                if value is not None:
                    ranges[field].append(value)
                    if value < 1 or (field != "weeks_on_chart" and value > 100):
                        invalid_numeric.append(dict(ref, chart_date=chart["date"], field=field, value=value))
            rank, peak = row.get("this_week"), row.get("peak_position")
            if rank is not None and peak is not None and peak > rank:
                inconsistent_peaks.append(dict(ref, chart_date=chart["date"], title=row["song"], artist=row["artist"], peak_position=peak))

    normalized = defaultdict(list)
    for identifier, title, artist, normalized_title, normalized_artist in source.songs:
        normalized[(normalized_title, normalized_artist)].append({"song_id": identifier, "title": title, "artist": artist})
    collisions = [
        {"normalized_title": title, "normalized_artist": artist, "identities": sorted(identities, key=lambda row: (row["title"], row["artist"]))}
        for (title, artist), identities in sorted(normalized.items()) if len(identities) > 1
    ]
    duplicate_song_weeks = [
        {"chart_date": chart_date, "title": title, "artist": artist,
         "song_id": source.identities[(title, artist)], "observations": refs}
        for (chart_date, title, artist), refs in sorted(song_weeks.items()) if len(refs) > 1
    ]
    duplicate_rank_weeks = [
        {"chart_date": key[0], "rank": key[1], "observations": refs}
        for key, refs in rank_weeks.items() if len(refs) > 1
    ]
    duplicate_exact_rows = [
        {"chart_date": key[0], "record": json.loads(key[1]), "observations": refs}
        for key, refs in sorted(exact_rows.items()) if len(refs) > 1
    ]
    distinct_dates = sorted(date.fromisoformat(value) for value in dates)
    intervals = [
        {"from": left.isoformat(), "to": right.isoformat(), "days": (right - left).days,
         "from_weekday": left.strftime("%A"), "to_weekday": right.strftime("%A")}
        for left, right in zip(distinct_dates, distinct_dates[1:]) if (right - left).days != 7
    ]
    return {
        "counts": {
            "weekly_charts": len(source.charts), "distinct_chart_dates": len(dates),
            "chart_observations": source.observation_count, "songs": len(source.songs),
            "artist_credits": len({row[2] for row in source.songs}),
        },
        "date_coverage": {"first": min(dates), "last": max(dates)},
        "chart_size_distribution": {str(size): count for size, count in sorted(sizes.items())},
        "numeric_ranges": {field: {"min": min(values) if values else None, "max": max(values) if values else None} for field, values in ranges.items()},
        "schema": {
            "top_level": "array",
            "chart_key_sets": sorted({tuple(sorted(chart)) for chart in source.charts}),
            "song_record_key_sets": sorted({tuple(sorted(row)) for chart in source.charts for row in chart["data"]}),
        },
        "missingness": {
            "charts": _profile(source.charts, CHART_FIELDS),
            "song_records": _profile((row for chart in source.charts for row in chart["data"]), SONG_FIELDS),
        },
        "anomalies": {
            "charts_with_non_100_entries": chart_exceptions,
            "charts_without_exact_1_to_100_ranks": rank_exceptions,
            "duplicate_chart_dates": [{"chart_date": value, "count": count} for value, count in sorted(dates.items()) if count > 1],
            "out_of_order_chart_indices": [i for i in range(1, len(source.charts)) if source.charts[i]["date"] < source.charts[i - 1]["date"]],
            "non_seven_day_intervals": intervals,
            "duplicate_song_week_groups": duplicate_song_weeks,
            "duplicate_song_week_extra_rows": sum(len(row["observations"]) - 1 for row in duplicate_song_weeks),
            "duplicate_rank_week_groups": duplicate_rank_weeks,
            "exact_duplicate_observation_groups": duplicate_exact_rows,
            "normalized_identity_collisions": collisions,
            "identities_in_normalized_collisions": sum(len(row["identities"]) for row in collisions),
            "invalid_numeric_values": invalid_numeric,
            "peak_worse_than_current_rank": inconsistent_peaks,
        },
    }


def table_rows(connection, table):
    if table == "songs":
        columns, order = SONG_COLUMNS, "song_id"
    elif table == "chart_observations":
        columns, order = OBSERVATION_COLUMNS, "source_chart_index, source_row_index"
    else:
        raise ValueError("Unknown export table")
    return connection.execute("SELECT {} FROM {} ORDER BY {}".format(", ".join(columns), table, order))


def _require_equal_rows(actual, expected, label):
    missing = object()
    for index, (left, right) in enumerate(zip_longest(actual, expected, fillvalue=missing)):
        if left != right:
            raise DataError("{} differs from source at ordered row {} (including possible extra/missing rows)".format(label, index))


def validate_database(connection, source):
    integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    if integrity != ["ok"]:
        raise DataError("SQLite integrity_check failed: " + repr(integrity))
    fk_errors = list(connection.execute("PRAGMA foreign_key_check"))
    if fk_errors:
        raise DataError("Foreign-key violations: " + repr(fk_errors[:5]))
    foreign_keys = list(connection.execute("PRAGMA foreign_key_list(chart_observations)"))
    if not any(row[2:5] == ("songs", "song_id", "song_id") for row in foreign_keys):
        raise DataError("chart_observations must declare its song_id foreign key")
    orphans = connection.execute("SELECT count(*) FROM chart_observations c LEFT JOIN songs s USING (song_id) WHERE s.song_id IS NULL").fetchone()[0]
    if orphans:
        raise DataError("Orphan chart observations: {}".format(orphans))
    metadata = dict(connection.execute("SELECT key, value FROM build_metadata"))
    for key, expected in {
        "source_sha256": source.sha256, "source_bytes": str(source.byte_count),
        "source_weekly_charts": str(len(source.charts)),
        "source_observations": str(source.observation_count),
    }.items():
        if metadata.get(key) != expected:
            raise DataError("Database provenance mismatch: " + key)
    _require_equal_rows(table_rows(connection, "songs"), iter(source.songs), "songs")
    _require_equal_rows(table_rows(connection, "chart_observations"), source.observations(), "chart_observations")
    return {
        "sqlite_integrity_check": "ok", "foreign_key_violations": len(fk_errors),
        "orphan_observations": orphans, "song_id_hash_collisions": 0,
        "source_hash_matches": True, "all_song_rows_match_source": True,
        "all_observation_rows_match_source": True,
        "database_songs": connection.execute("SELECT count(*) FROM songs").fetchone()[0],
        "database_observations": connection.execute("SELECT count(*) FROM chart_observations").fetchone()[0],
        "database_artist_credits": connection.execute("SELECT count(DISTINCT artist) FROM songs").fetchone()[0],
        "database_distinct_chart_dates": connection.execute("SELECT count(DISTINCT chart_date) FROM chart_observations").fetchone()[0],
    }


def validate_csvs(connection, output_dir):
    for table, columns in (("songs", SONG_COLUMNS), ("chart_observations", OBSERVATION_COLUMNS)):
        with (output_dir / (table + ".csv")).open(encoding="utf-8", newline="") as stream:
            rows = csv.reader(stream)
            if next(rows, None) != list(columns):
                raise DataError("CSV header mismatch: " + table)
            expected = (["" if value is None else str(value) for value in row] for row in table_rows(connection, table))
            _require_equal_rows(rows, expected, table + ".csv")


def _cell(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\n", " ").replace("\r", " ").replace("`", "&#96;")


def markdown_report(report, detail_name):
    metadata, quality, validation = report["provenance"], report["quality"], report["validation"]
    counts, anomalies = quality["counts"], quality["anomalies"]
    lines = [
        "# Phase 1 data quality", "",
        "Generated by `python3 src/phase1.py build`; do not edit manually. "
        "Source anomalies are retained; transformation and integrity checks pass.", "",
        "## Source and provenance", "",
        "- Reported upstream: [{}]({}). No remote verification or enrichment was performed.".format(metadata["source_repository"], metadata["source_repository"]),
        "- Snapshot: `{}` ({} bytes).".format(metadata["source_path"], metadata["source_bytes"]),
        "- SHA-256: `{}`.".format(metadata["source_sha256"]),
        "- Pipeline SHA-256: `{}`.".format(metadata["pipeline_sha256"]),
        "- Python {}; SQLite {}; Unicode database {}.".format(metadata["python_version"], metadata["sqlite_version"], metadata["unicode_version"]),
        "- Upstream commit, download time, and source licensing/redistribution terms were not supplied with the local file.", "",
        "## Source schema", "",
        "Top-level JSON array. Each chart has `date` (ISO date string) and `data` "
        "(array of song records). Observed chart key sets: `{}`.".format(json.dumps(quality["schema"]["chart_key_sets"])), "",
        "Observed song-record key sets: `{}`.".format(json.dumps(quality["schema"]["song_record_key_sets"])), "",
        "`song` and `artist` are original strings. `this_week`, `last_week`, "
        "`peak_position`, and `weeks_on_chart` are integers when present; `last_week` "
        "also contains JSON null. `this_week` maps directly to database `rank`.", "",
        "## Coverage and counts", "",
        "| Metric | Value |", "| --- | ---: |",
        "| Weekly chart objects | {:,} |".format(counts["weekly_charts"]),
        "| Distinct chart dates | {:,} |".format(counts["distinct_chart_dates"]),
        "| Chart observations | {:,} |".format(counts["chart_observations"]),
        "| Exact title/artist identities | {:,} |".format(counts["songs"]),
        "| Distinct artist-credit strings | {:,} |".format(counts["artist_credits"]),
        "| First chart date | {} |".format(quality["date_coverage"]["first"]),
        "| Last chart date | {} |".format(quality["date_coverage"]["last"]),
    ]
    for field, values in quality["numeric_ranges"].items():
        lines.append("| {} range (non-null) | {}–{} |".format(field, values["min"], values["max"]))
    lines += ["", "Chart sizes (entries: chart count): `{}`. Counts include every source row.".format(json.dumps(quality["chart_size_distribution"], sort_keys=True)),
              "", "## Missingness", "", "Missing keys, explicit nulls, and blank strings are counted separately. No imputation is applied.", "",
              "| Scope / field | Missing key | Null | Blank | Observed types/counts |", "| --- | ---: | ---: | ---: | --- |"]
    for scope, fields in quality["missingness"].items():
        for field, profile in fields.items():
            lines.append("| {} / {} | {:,} | {:,} | {:,} | {} |".format(scope, field, profile["missing"], profile["null"], profile["blank"], _cell(json.dumps(profile["types"], sort_keys=True))))
    lines += ["", "Null `last_week` is retained as unknown/not reported; Phase 1 does not infer a debut or re-entry from it.",
              "", "## Validation and anomalies", "",
              "- SQLite integrity: **{}**; foreign-key violations: {}; orphan observations: {}; ID hash collisions: {}.".format(validation["sqlite_integrity_check"], validation["foreign_key_violations"], validation["orphan_observations"], validation["song_id_hash_collisions"]),
              "- Every song and observation was compared field-by-field with the source-derived expectation, including source row coordinates. Both CSV exports were checked against SQLite. Counts reconcile exactly.",
              "- Duplicate chart dates: {}; out-of-order charts: {}; duplicate date/rank groups: {}; identical source-record duplicate groups: {}.".format(len(anomalies["duplicate_chart_dates"]), len(anomalies["out_of_order_chart_indices"]), len(anomalies["duplicate_rank_week_groups"]), len(anomalies["exact_duplicate_observation_groups"])),
              "- Numeric range violations (rank/last_week/peak outside 1–100 or weeks_on_chart below 1): {}.".format(len(anomalies["invalid_numeric_values"])),
              "- Non-100-entry charts: {}; charts without exactly one of every rank 1–100: {}.".format(len(anomalies["charts_with_non_100_entries"]), len(anomalies["charts_without_exact_1_to_100_ranks"])),
              "- Duplicate exact song/date groups: {} ({} extra rows; all retained).".format(len(anomalies["duplicate_song_week_groups"]), anomalies["duplicate_song_week_extra_rows"]),
              "- Normalized identity collision groups: {} across {} exact identities; no merges.".format(len(anomalies["normalized_identity_collisions"]), anomalies["identities_in_normalized_collisions"]),
              "- Reported peak numerically worse than current rank: {:,} observations; preserved, not corrected.".format(len(anomalies["peak_worse_than_current_rank"])),
              "", "Full diagnostics, including all anomaly rows and source locations, are generated in [{}]({}).".format(detail_name, detail_name),
              "", "### Charts with entry-count exceptions", "", "| Chart date | Entries | Missing ranks within 1–100 |", "| --- | ---: | --- |"]
    for row in anomalies["charts_with_non_100_entries"]:
        lines.append("| {} | {} | {} |".format(row["chart_date"], row["entries"], ", ".join(map(str, row["missing_ranks_1_to_100"])) or "None"))
    lines += ["", "### Date intervals other than seven days", ""]
    for interval in anomalies["non_seven_day_intervals"]:
        lines.append("- {from} ({from_weekday}) → {to} ({to_weekday}): {days} days.".format(**interval))
    if not anomalies["non_seven_day_intervals"]:
        lines.append("None.")
    lines += ["", "An unusual interval does not by itself establish that a weekly chart is missing; date-label conventions have not been independently verified.",
              "", "### Repeated exact song/date pairs", "", "| Chart date | Title | Artist | Ranks |", "| --- | --- | --- | --- |"]
    for row in anomalies["duplicate_song_week_groups"]:
        lines.append("| {} | {} | {} | {} |".format(row["chart_date"], _cell(row["title"]), _cell(row["artist"]), ", ".join(str(ref["rank"]) for ref in row["observations"])))
    lines += ["", "The same source credit may cover multiple recordings or releases. Phase 1 cannot resolve this: repeated pairs share a song ID but retain distinct observation rows.",
              "", "### Normalized identity collisions", "", "| Normalized title | Original title / artist variants (kept separate) |", "| --- | --- |"]
    for row in anomalies["normalized_identity_collisions"]:
        lines.append("| {} | {} |".format(_cell(row["normalized_title"]), "; ".join(_cell(v["title"] + " / " + v["artist"]) for v in row["identities"])))
    lines += ["", "### Examples of inconsistent reported peaks", "", "| Date | Title | Artist | Rank | Reported peak |", "| --- | --- | --- | ---: | ---: |"]
    for row in anomalies["peak_worse_than_current_rank"][:5]:
        lines.append("| {} | {} | {} | {} | {} |".format(row["chart_date"], _cell(row["title"]), _cell(row["artist"]), row["rank"], row["peak_position"]))
    lines += ["", "## Identity and normalization methodology", "",
              "- Identity is the exact, case-sensitive original `(song, artist)` pair. Original strings are stored unchanged as `title` and `artist`.",
              "- ID: `song_` plus the full SHA-256 hex digest of UTF-8 bytes for `billboard-song-v1`, a NUL separator, and a compact JSON array `[title,artist]` (`ensure_ascii=False`). IDs do not depend on order, chart dates, or normalized strings.",
              "- Normalization version: `{}`. Apply Unicode NFC, Unicode casefold, strip/collapse Unicode whitespace to a single ASCII space, then NFC again. Preserve punctuation, diacritics, feature credits, and version descriptors. Do not transliterate or fuzzy-match.".format(metadata["normalization_version"]),
              "- Normalized collisions are review candidates only; they remain distinct IDs. The runtime Unicode version is recorded because normalization tables can vary.",
              "- Observation primary key: zero-based `(source_chart_index, source_row_index)`. Together with the source hash, these locate the exact raw record. `(song_id, chart_date)` is intentionally not unique.",
              "- Missing numeric keys and explicit numeric nulls both export as SQL NULL / empty CSV cells; the report distinguishes their counts, and raw JSON plus coordinates preserves their origin.",
              "", "## Limitations and Phase 2 decisions", "",
              "- Counts measure source credits, not resolved recordings, compositions, or individual artists. Exact matching can split spelling variants and combine different recordings with identical credits.",
              "- Coverage reflects the local snapshot through its final chart date, not necessarily a complete calendar year or an independently certified complete history. The upstream commit, acquisition date, source authenticity, and redistribution terms have not been verified.",
              "- Chart inclusion represents charted mainstream music; population definition, exposure weighting, historical chart-rule changes, and missing-chart treatment are unresolved research decisions.",
              "- Source anomalies and chart-date conventions need investigation before longitudinal inference. No source values were fixed or observations dropped.",
              "- Before enrichment: define the target entity (recording/composition/chart credit), review identity candidates, agree on provenance and uncertain-match review, and check provider access/licensing constraints.",
              "- Lyrics, metadata/genre, content variables, COVID breakpoints, classifiers, and statistical tests are deferred.", ""]
    return "\n".join(lines)
