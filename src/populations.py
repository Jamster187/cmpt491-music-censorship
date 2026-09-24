"""Build local weekly exports and monthly Top-100 baskets without changing Phase 1."""

import csv
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import statistics
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/music.db"
RAW = ROOT / "data/raw/billboard-hot-100.json"
OUTPUT = ROOT / "data/processed/populations"
REPORT = ROOT / "archive/intermediate_reports/analysis_populations.md"
MONTHLY_COLUMNS = ("month", "monthly_rank", "song_id", "monthly_points", "weeks_present",
                   "best_weekly_rank", "average_weekly_rank", "weekly_observations")
PERIODS = [(1958, 1969, "1958–1969"), (1970, 1979, "1970s"), (1980, 1989, "1980s"),
           (1990, 1999, "1990s"), (2000, 2009, "2000s"), (2010, 2019, "2010s"), (2020, 2026, "2020–2026")]
MONTHLY_SQL = """
WITH totals AS (
 SELECT substr(chart_date,1,7) AS month, song_id,
        SUM(101-rank) AS monthly_points, COUNT(DISTINCT chart_date) AS weeks_present,
        MIN(rank) AS best_weekly_rank, AVG(rank) AS average_weekly_rank,
        COUNT(*) AS weekly_observations
 FROM source.chart_observations GROUP BY month,song_id
), ranked AS (
 SELECT *, ROW_NUMBER() OVER (
   PARTITION BY month ORDER BY monthly_points DESC,best_weekly_rank,
   average_weekly_rank,song_id COLLATE BINARY) AS monthly_rank FROM totals
)
SELECT month,monthly_rank,song_id,monthly_points,weeks_present,best_weekly_rank,
       average_weekly_rank,weekly_observations
FROM ranked WHERE monthly_rank<=100 ORDER BY month,monthly_rank
"""


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def attach_weekly(conn, source=SOURCE):
    """Session view references the original read-only tables, never a weekly copy."""
    conn.execute("ATTACH DATABASE ? AS source", (Path(source).resolve().as_uri() + "?mode=ro",))
    conn.execute("CREATE TEMP VIEW weekly_top100 AS SELECT *,101-rank AS weekly_points FROM source.chart_observations")


def create_monthly(conn):
    invalid = conn.execute("SELECT COUNT(*) FROM source.chart_observations WHERE rank IS NULL OR typeof(rank)!='integer' OR rank NOT BETWEEN 1 AND 100").fetchone()[0]
    if invalid:
        raise ValueError("Invalid weekly ranks: {} (nothing may be silently discarded)".format(invalid))
    conn.execute("""CREATE TABLE monthly_top100 (
        month TEXT NOT NULL, monthly_rank INTEGER NOT NULL CHECK(monthly_rank BETWEEN 1 AND 100),
        song_id TEXT NOT NULL, monthly_points INTEGER NOT NULL CHECK(monthly_points>0),
        weeks_present INTEGER NOT NULL CHECK(weeks_present>0), best_weekly_rank INTEGER NOT NULL,
        average_weekly_rank REAL NOT NULL, weekly_observations INTEGER NOT NULL,
        PRIMARY KEY(month,monthly_rank), UNIQUE(month,song_id))""")
    conn.execute("INSERT INTO monthly_top100 " + MONTHLY_SQL)
    conn.execute("CREATE INDEX monthly_song ON monthly_top100(song_id,month)")


def validate(conn):
    """Independent Python aggregation with exact rational tie-breaking."""
    groups = defaultdict(list)
    for sid, date, rank in conn.execute("SELECT song_id,chart_date,rank FROM source.chart_observations"):
        groups[date[:7], sid].append((date, rank))
    months = defaultdict(list)
    for (month, sid), entries in groups.items():
        ranks = [r for _, r in entries]
        months[month].append((sid, sum(101-r for r in ranks), len({d for d, _ in entries}),
                              min(ranks), Fraction(sum(ranks), len(ranks)), len(ranks)))
    expected = []
    for month in sorted(months):
        ordered = sorted(months[month], key=lambda r: (-r[1], r[3], r[4], r[0]))[:100]
        expected.extend((month, i, r[0], r[1], r[2], r[3], float(r[4]), r[5]) for i, r in enumerate(ordered, 1))
    actual = conn.execute("SELECT * FROM monthly_top100 ORDER BY month,monthly_rank").fetchall()
    if actual != expected:
        raise ValueError("Independent monthly aggregation/rank reconciliation failed")
    orphans = conn.execute("SELECT count(*) FROM monthly_top100 m LEFT JOIN source.songs s USING(song_id) WHERE s.song_id IS NULL").fetchone()[0]
    if orphans:
        raise ValueError("Monthly song_id referential integrity failed")
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Derived database integrity check failed")
    return {"independent_points_statistics_and_selection_reconciliation": True,
            "unique_contiguous_monthly_ranks": True, "maximum_100_per_month": True,
            "referential_integrity": True, "eligible_song_months": len(groups)}


def export_query(conn, path, sql):
    cursor = conn.execute(sql)
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([c[0] for c in cursor.description])
        writer.writerows(cursor)
    # Read the complete export back and reconcile against the ordered query.
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        count = 0
        for row in conn.execute(sql):
            if next(reader, None) != ["" if v is None else str(v) for v in row]:
                raise ValueError("CSV reconciliation failed: " + str(path))
            count += 1
        if next(reader, None) is not None:
            raise ValueError("CSV contains extra rows")
    return count


def summarize(conn):
    def scalar(sql):
        return conn.execute(sql).fetchone()[0]
    weekly = scalar("SELECT count(*) FROM source.chart_observations")
    total_songs = scalar("SELECT count(DISTINCT song_id) FROM source.chart_observations")
    month_rows = conn.execute("SELECT substr(chart_date,1,7), count(distinct chart_date), count(*), count(distinct song_id), min(chart_date), max(chart_date) FROM source.chart_observations GROUP BY 1 ORDER BY 1").fetchall()
    basket_counts = dict(conn.execute("SELECT month,count(*) FROM monthly_top100 GROUP BY month"))
    frequencies = dict(conn.execute("SELECT song_id,count(*) FROM monthly_top100 GROUP BY song_id"))
    first_months = dict(conn.execute("SELECT song_id,min(month) FROM monthly_top100 GROUP BY song_id"))
    new_year = Counter(m[:4] for m in first_months.values())
    represented = scalar("SELECT count(*) FROM source.chart_observations WHERE song_id IN (SELECT song_id FROM monthly_top100)")
    contemporaneous = scalar("SELECT count(*) FROM source.chart_observations w JOIN monthly_top100 m ON w.song_id=m.song_id AND substr(w.chart_date,1,7)=m.month")
    duplicates = conn.execute("SELECT song_id,chart_date,count(*) FROM source.chart_observations GROUP BY song_id,chart_date HAVING count(*)>1 ORDER BY chart_date,song_id").fetchall()
    periods = []
    for start, end, name in PERIODS:
        active = {sid for month, sid in conn.execute("SELECT month,song_id FROM monthly_top100 WHERE month BETWEEN ? AND ?", (str(start)+"-01",str(end)+"-12"))}
        entrants = sum(start <= int(m[:4]) <= end for m in first_months.values())
        periods.append({"period": name, "unique_songs_appearing": len(active), "first_monthly_entry_in_period": entrants})
    histogram = sorted(Counter(frequencies.values()).items())
    years = [{"year": y, "new_unique_songs": new_year[str(y)]} for y in range(int(month_rows[0][0][:4]),int(month_rows[-1][0][:4])+1)]
    if sum(r["new_unique_songs"] for r in years) != len(frequencies) or sum(n*k for n,k in histogram) != sum(basket_counts.values()):
        raise ValueError("Population totals do not reconcile")
    examples = {}
    for month in ["1958-08", "1977-06", "1995-07", "2019-06", "2020-04", "2026-08", "2026-09"]:
        examples[month] = [dict(zip(("monthly_rank","title","artist","monthly_points","weeks_present","best_weekly_rank","average_weekly_rank"), row)) for row in conn.execute("SELECT m.monthly_rank,s.title,s.artist,m.monthly_points,m.weeks_present,m.best_weekly_rank,m.average_weekly_rank FROM monthly_top100 m JOIN source.songs s USING(song_id) WHERE m.month=? ORDER BY monthly_rank LIMIT 5",(month,))]
    return {"weekly_charts": scalar("SELECT count(distinct chart_date) FROM source.chart_observations"),
            "weekly_observations": weekly, "weekly_unique_songs": total_songs,
            "first_chart_date": month_rows[0][4], "last_chart_date": month_rows[-1][5],
            "calendar_months": len(month_rows), "complete_100_song_baskets": sum(n==100 for n in basket_counts.values()),
            "months_below_100": [{"month": m, "songs": n} for m,n in basket_counts.items() if n<100],
            "monthly_observations": sum(basket_counts.values()), "monthly_unique_songs": len(frequencies),
            "unique_song_reduction": total_songs-len(frequencies), "unique_song_reduction_percent": round(100*(total_songs-len(frequencies))/total_songs,4),
            "weekly_observations_of_ever_selected_songs": represented,
            "weekly_observations_of_ever_selected_songs_percent": round(100*represented/weekly,4),
            "weekly_observations_in_selected_song_months": contemporaneous,
            "weekly_observations_in_selected_song_months_percent": round(100*contemporaneous/weekly,4),
            "by_period": periods, "new_songs_by_year": years,
            "months_per_song_histogram": [{"months": n, "songs": k} for n,k in histogram],
            "months_per_song_summary": {"min": min(frequencies.values()), "median": statistics.median(frequencies.values()),
                "mean": statistics.mean(frequencies.values()), "max": max(frequencies.values())},
            "month_inventory": [dict(zip(("month","chart_dates","weekly_observations","eligible_songs","first_chart_date","last_chart_date"),r)) for r in month_rows],
            "duplicate_song_week_groups": [{"song_id": s,"chart_date": d,"observations": n} for s,d,n in duplicates],
            "selected_months_with_duplicate_observations": scalar("SELECT count(*) FROM monthly_top100 WHERE weekly_observations>weeks_present"),
            "examples": examples}


def markdown(s):
    lines = ["# Billboard analysis populations", "", "Generated locally with `python3 src/populations.py`. No external metadata, lyrics, or content analysis.", "",
        f"The weekly view remains **{s['weekly_charts']:,} charts, {s['weekly_observations']:,} observations, and {s['weekly_unique_songs']:,} exact title/artist identities**, from {s['first_chart_date']} through {s['last_chart_date']}.",
        f"There are **{s['calendar_months']} months**, **{s['complete_100_song_baskets']} complete 100-song baskets**, **{s['monthly_observations']:,} song-month rows**, and **{s['monthly_unique_songs']:,} unique monthly-basket songs**.",
        f"Months with fewer than 100 eligible songs: {json.dumps(s['months_below_100'])}. The reduction is **{s['unique_song_reduction']:,} assets ({s['unique_song_reduction_percent']:.2f}%)**. No weekly rows or identities are removed.", "",
        "## Definition and interpretation", "", "Each source row contributes `101 - rank` points to its chart date's calendar month. Sum by month/song_id; order by points descending, best weekly rank ascending, average weekly rank ascending, then stable song_id in binary ascending order. Select exactly the first 100 eligible identities, or all if fewer. No prorating or week-spanning allocation is used.",
        "`weeks_present` counts distinct chart dates. `average_weekly_rank` is the arithmetic mean over source observations; `weekly_observations` separately records the number of contributing rows. Source duplicate song-week rows each contribute points, as requested for every observation. They are not silently deduplicated or interpreted as distinct weeks.",
        f"There are {len(s['duplicate_song_week_groups'])} duplicate source song-week groups; {s['selected_months_with_duplicate_observations']} selected song-month rows contain duplicates. These source anomalies can affect points and selection; they remain visible in the inventory and extra observation-count field.",
        "A complete 100-song basket does not mean complete calendar-month coverage. The snapshot ends on 2026-09-19: September 2026 contains only three chart dates and is provisional. August 1958 is the beginning of the supplied history, so first-entry counts are left-censored. Months are not normalized for having four versus five chart dates. Chart points are a rank-derived popularity proxy, not measured consumption.", "",
        "## Weekly representation", "",
        f"Songs selected in at least one month account for **{s['weekly_observations_of_ever_selected_songs']:,}/{s['weekly_observations']:,} weekly rows ({s['weekly_observations_of_ever_selected_songs_percent']:.2f}%)**, including their weekly appearances outside selected months.",
        f"For a different denominator interpretation, weekly rows whose song is selected in that same month total {s['weekly_observations_in_selected_song_months']:,} ({s['weekly_observations_in_selected_song_months_percent']:.2f}%).", "",
        "## Historical periods", "", "Appearing counts use any selected month in the period; a song can appear in multiple periods. First-entry counts are disjoint and sum to the overall unique population.", "",
        "| Period | Unique songs appearing | First monthly entry in period |", "|---|---:|---:|"]
    lines += [f"| {p['period']} | {p['unique_songs_appearing']:,} | {p['first_monthly_entry_in_period']:,} |" for p in s["by_period"]]
    lines += ["", "## New unique monthly-basket songs each year", "", "Year of first selected monthly basket, not release year or first weekly Billboard appearance. 1958 and 2026 are partial years.", "", "| Year | New songs |", "|---|---:|"]
    lines += [f"| {p['year']} | {p['new_unique_songs']} |" for p in s["new_songs_by_year"]]
    d = s["months_per_song_summary"]
    lines += ["", "## Months per selected song", "", f"Minimum {d['min']}; median {d['median']:g}; mean {d['mean']:.4f}; maximum {d['max']}. Excludes the {s['unique_song_reduction']:,} original identities selected in zero months.", "", "| Months selected | Songs |", "|---:|---:|"]
    lines += [f"| {p['months']} | {p['songs']:,} |" for p in s["months_per_song_histogram"]]
    lines += ["", "## Example baskets (first five rows)", ""]
    inventory = {r["month"]:r for r in s["month_inventory"]}
    for month, rows in s["examples"].items():
        lines += [f"### {month} — {inventory[month]['chart_dates']} chart dates", "", "| Rank | Title | Artist | Points | Weeks | Best rank | Mean rank |", "|---:|---|---|---:|---:|---:|---:|"]
        for r in rows:
            values = [r[k] for k in ("monthly_rank","title","artist","monthly_points","weeks_present","best_weekly_rank")]+[f"{r['average_weekly_rank']:.2f}"]
            lines.append("| " + " | ".join(str(v).replace('|','\\|') for v in values) + " |")
        lines.append("")
    lines += ["## Validation and reproduction", "", "All monthly rows, statistics, and top-100 selection reconcile to an independent Python aggregation using exact rational average-rank comparisons. Monthly ranks are unique and contiguous, basket sizes never exceed 100, and every song_id resolves to the canonical songs table. Both CSV exports were read back and reconciled row-for-row. Source JSON and canonical database hashes were unchanged across the build.",
        "The derived SQLite database, weekly/monthly CSVs, complete month inventory, yearly entrant counts, frequency distribution, and JSON report are under `data/processed/populations/` (ignored and rebuildable). See [population instructions](../old_methodology/analysis_populations.md) for joins and commands. Song metadata is not duplicated in the derived database or weekly/monthly exports. No classifier or COVID breakpoint is implemented.", ""]
    return "\n".join(lines)


def main():
    before = {str(p.relative_to(ROOT)): file_hash(p) for p in (SOURCE, RAW)}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".populations-", dir=OUTPUT) as tmp:
        stage = Path(tmp)
        conn = sqlite3.connect(str(stage / "populations.db"), uri=True)
        try:
            attach_weekly(conn)
            create_monthly(conn)
            checks = validate(conn)
            summary = summarize(conn)
            weekly_csv = export_query(conn, stage / "weekly_top100.csv", "SELECT * FROM weekly_top100 ORDER BY chart_date,rank,source_chart_index,source_row_index")
            monthly_csv = export_query(conn, stage / "monthly_top100.csv", "SELECT * FROM monthly_top100 ORDER BY month,monthly_rank")
            if weekly_csv != summary["weekly_observations"] or monthly_csv != summary["monthly_observations"]:
                raise ValueError("Export row counts do not reconcile")
            provenance = {"method_version": "monthly-rank-points-v1", "input_sha256": before,
                          "code_sha256": file_hash(__file__), "sqlite_version": sqlite3.sqlite_version}
            conn.execute("CREATE TABLE build_metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            conn.executemany("INSERT INTO build_metadata VALUES (?,?)", [(k,json.dumps(v,sort_keys=True)) for k,v in provenance.items()])
            conn.commit()
            summary.update(validation=checks, provenance=provenance)
        finally:
            conn.close()
        after = {str(p.relative_to(ROOT)): file_hash(p) for p in (SOURCE, RAW)}
        if before != after:
            raise ValueError("Phase 1 source changed during build; outputs not published")
        summary["validation"]["phase1_source_hashes_unchanged"] = True
        (stage / "population_summary.json").write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        for name, records in [("new_monthly_songs_by_year",summary["new_songs_by_year"]), ("months_per_song",summary["months_per_song_histogram"]), ("month_inventory",summary["month_inventory"])]:
            with (stage / (name+".csv")).open("w",newline="",encoding="utf-8") as f:
                writer = csv.DictWriter(f,fieldnames=list(records[0]))
                writer.writeheader(); writer.writerows(records)
        report = markdown(summary)
        for path in sorted(stage.iterdir()):
            os.replace(str(path),str(OUTPUT / path.name))
        report_tmp = REPORT.with_suffix(".md.tmp")
        report_tmp.write_text(report,encoding="utf-8")
        os.replace(str(report_tmp),str(REPORT))
    print(json.dumps({k:v for k,v in summary.items() if k not in ("month_inventory","examples","duplicate_song_week_groups","provenance")},indent=2))


if __name__ == "__main__":
    main()
