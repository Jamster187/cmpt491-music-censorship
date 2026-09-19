"""Unified research database construction and integrity checks (no API requests)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from populations import ROOT, SOURCE, RAW, OUTPUT as POPULATIONS

DATABASE = ROOT / "data/processed/research.db"
INPUTS = [SOURCE, RAW, POPULATIONS / "populations.db"]
SCHEMA = """
CREATE TABLE songs (
 song_id TEXT PRIMARY KEY, title TEXT NOT NULL, artist TEXT NOT NULL,
 normalized_title TEXT NOT NULL, normalized_artist TEXT NOT NULL,
 first_chart_date TEXT NOT NULL, last_chart_date TEXT NOT NULL,
 best_chart_rank INTEGER NOT NULL, chart_observation_count INTEGER NOT NULL,
 distinct_chart_dates INTEGER NOT NULL, total_chart_points INTEGER NOT NULL,
 UNIQUE(title,artist));
CREATE TABLE chart_observations (
 song_id TEXT NOT NULL REFERENCES songs(song_id), chart_date TEXT NOT NULL,
 rank INTEGER, last_week INTEGER, peak_position INTEGER, weeks_on_chart INTEGER,
 source_chart_index INTEGER NOT NULL, source_row_index INTEGER NOT NULL,
 PRIMARY KEY(source_chart_index,source_row_index));
CREATE INDEX research_weekly_song ON chart_observations(song_id,chart_date);
CREATE INDEX research_weekly_date ON chart_observations(chart_date,rank);
CREATE TABLE monthly_top100 (
 month TEXT NOT NULL, monthly_rank INTEGER NOT NULL CHECK(monthly_rank BETWEEN 1 AND 100),
 song_id TEXT NOT NULL REFERENCES songs(song_id), monthly_points INTEGER NOT NULL,
 weeks_present INTEGER NOT NULL, best_weekly_rank INTEGER NOT NULL,
 average_weekly_rank REAL NOT NULL, weekly_observations INTEGER NOT NULL,
 PRIMARY KEY(month,monthly_rank), UNIQUE(month,song_id));
CREATE INDEX research_monthly_song ON monthly_top100(song_id,month);
CREATE TABLE study_population (
 song_id TEXT PRIMARY KEY REFERENCES songs(song_id), first_selected_month TEXT NOT NULL,
 last_selected_month TEXT NOT NULL, months_selected INTEGER NOT NULL);
CREATE VIEW weekly_top100 AS SELECT *,101-rank AS weekly_points FROM chart_observations;
CREATE TABLE build_metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE metadata_matches (
 song_id TEXT PRIMARY KEY REFERENCES study_population(song_id), provider TEXT NOT NULL,
 match_status TEXT NOT NULL CHECK(match_status IN ('high_confidence','ambiguous','not_found','error')),
 reason TEXT NOT NULL, matcher_version TEXT NOT NULL, result_path TEXT NOT NULL,
 result_sha256 TEXT NOT NULL, processed_at TEXT NOT NULL, evidence_json TEXT NOT NULL);
CREATE TABLE external_entities (
 provider TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
 metadata_json TEXT NOT NULL, provenance_json TEXT NOT NULL,
 PRIMARY KEY(provider,entity_type,entity_id));
CREATE TABLE song_external_links (
 song_id TEXT NOT NULL REFERENCES study_population(song_id), provider TEXT NOT NULL,
 entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, role TEXT NOT NULL,
 PRIMARY KEY(song_id,provider,entity_type,entity_id),
 FOREIGN KEY(provider,entity_type,entity_id) REFERENCES external_entities(provider,entity_type,entity_id));
CREATE TABLE lyrics_manifest (
 song_id TEXT PRIMARY KEY REFERENCES study_population(song_id),
 lyrics_status TEXT NOT NULL DEFAULT 'not_attempted' CHECK(lyrics_status IN
 ('not_attempted','blocked_source_access','success','ambiguous','not_found','error','instrumental')),
 lyrics_source TEXT, source_identifier TEXT, match_status TEXT NOT NULL DEFAULT 'not_attempted',
 matched_title TEXT, matched_artist TEXT, lyrics_path TEXT UNIQUE, lyrics_sha256 TEXT,
 retrieved_at TEXT, failure_reason TEXT, provenance_json TEXT NOT NULL DEFAULT '{}',
 CHECK(lyrics_status!='success' OR (lyrics_path IS NOT NULL AND lyrics_sha256 IS NOT NULL
 AND lyrics_source IS NOT NULL AND retrieved_at IS NOT NULL AND match_status='high_confidence')));
CREATE TABLE acquisition_runs (
 run_id TEXT PRIMARY KEY, provider TEXT NOT NULL, started_at TEXT NOT NULL,
 finished_at TEXT, status TEXT NOT NULL, parameters_json TEXT NOT NULL, summary_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE lyrics_pilot (
 song_id TEXT PRIMARY KEY REFERENCES study_population(song_id), period TEXT NOT NULL,
 selection_order INTEGER NOT NULL UNIQUE, selection_version TEXT NOT NULL);
"""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def connect(path=DATABASE, readonly=False):
    conn = sqlite3.connect(Path(path).resolve().as_uri() + ("?mode=ro" if readonly else "?mode=rw"),uri=True,timeout=30)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def attach_sources(conn):
    conn.execute("ATTACH DATABASE ? AS phase1", (SOURCE.resolve().as_uri()+"?mode=ro",))
    conn.execute("ATTACH DATABASE ? AS populations", ((POPULATIONS / "populations.db").resolve().as_uri()+"?mode=ro",))


def input_hashes():
    return {str(p.relative_to(ROOT)):sha(p) for p in INPUTS}


def validate(conn, check_files=True):
    attach_sources(conn)
    try:
        expected = json.loads(conn.execute("SELECT value FROM build_metadata WHERE key='input_sha256'").fetchone()[0])
        if expected != input_hashes():
            raise ValueError("Immutable input hashes differ from research build")
        pairs = [
            ("SELECT song_id,title,artist,normalized_title,normalized_artist FROM songs", "SELECT * FROM phase1.songs"),
            ("SELECT * FROM chart_observations", "SELECT * FROM phase1.chart_observations"),
            ("SELECT * FROM monthly_top100", "SELECT * FROM populations.monthly_top100"),
            ("SELECT song_id,first_chart_date,last_chart_date,best_chart_rank,chart_observation_count,distinct_chart_dates,total_chart_points FROM songs",
             "SELECT song_id,min(chart_date),max(chart_date),min(rank),count(*),count(distinct chart_date),sum(101-rank) FROM phase1.chart_observations GROUP BY song_id"),
            ("SELECT * FROM study_population", "SELECT song_id,min(month),max(month),count(*) FROM monthly_top100 GROUP BY song_id")]
        for a,b in pairs:
            for left,right in ((a,b),(b,a)):
                if conn.execute("SELECT count(*) FROM ("+left+" EXCEPT "+right+")").fetchone()[0]:
                    raise ValueError("Research/source row reconciliation failed")
        counts = {table:conn.execute("SELECT count(*) FROM "+table).fetchone()[0] for table in
                  ("songs","chart_observations","monthly_top100","study_population","lyrics_manifest","lyrics_pilot","metadata_matches")}
        required = {"songs":32723,"chart_observations":355487,"monthly_top100":81800,"study_population":25363,"lyrics_manifest":25363}
        if any(counts[k]!=v for k,v in required.items()):
            raise ValueError("Unexpected study counts: "+str(counts))
        if conn.execute("PRAGMA foreign_key_check").fetchall() or conn.execute("PRAGMA integrity_check").fetchone()[0]!='ok':
            raise ValueError("Research database integrity failed")
        if conn.execute("SELECT count(*) FROM (SELECT month FROM monthly_top100 GROUP BY month HAVING count(*)!=100 OR min(monthly_rank)!=1 OR max(monthly_rank)!=100)").fetchone()[0]:
            raise ValueError("Monthly basket integrity failed")
        if check_files:
            for sid,status,path,checksum in conn.execute("SELECT song_id,lyrics_status,lyrics_path,lyrics_sha256 FROM lyrics_manifest WHERE lyrics_status='success'"):
                expected_path = ROOT / "data/lyrics" / (sid+".txt")
                if path != str(expected_path.relative_to(ROOT)) or not expected_path.is_file() or sha(expected_path)!=checksum:
                    raise ValueError("Lyrics manifest/file integrity failed: "+sid)
            for path,checksum in conn.execute("SELECT result_path,result_sha256 FROM metadata_matches"):
                target = (ROOT / path).resolve()
                if ROOT / "data/processed" not in target.parents or not target.is_file() or sha(target)!=checksum:
                    raise ValueError("Metadata evidence file integrity failed")
        return counts
    finally:
        conn.execute("DETACH DATABASE phase1")
        conn.execute("DETACH DATABASE populations")


def build(path=DATABASE):
    path = Path(path)
    if path.exists():
        with connect(path,readonly=True) as conn:
            result = validate(conn)
        print("Existing research database validated; enrichment preserved:",result)
        return
    before = input_hashes()
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".research-",dir=path.parent) as tmp:
        staged = Path(tmp) / "research.db"
        conn = sqlite3.connect(str(staged),uri=True)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(SCHEMA)
            attach_sources(conn)
            conn.execute("""INSERT INTO songs SELECT s.*,h.first_date,h.last_date,h.best,h.n,h.weeks,h.points
              FROM phase1.songs s JOIN (SELECT song_id,min(chart_date) first_date,max(chart_date) last_date,
              min(rank) best,count(*) n,count(distinct chart_date) weeks,sum(101-rank) points
              FROM phase1.chart_observations GROUP BY song_id) h USING(song_id)""")
            conn.execute("INSERT INTO chart_observations SELECT * FROM phase1.chart_observations")
            conn.execute("INSERT INTO monthly_top100 SELECT * FROM populations.monthly_top100")
            conn.execute("INSERT INTO study_population SELECT song_id,min(month),max(month),count(*) FROM monthly_top100 GROUP BY song_id")
            conn.execute("INSERT INTO lyrics_manifest(song_id) SELECT song_id FROM study_population")
            conn.executemany("INSERT INTO build_metadata VALUES (?,?)",[("schema_version","1"),("input_sha256",json.dumps(before,sort_keys=True)),("code_sha256",sha(__file__))])
            conn.commit()
            conn.execute("DETACH DATABASE phase1")
            conn.execute("DETACH DATABASE populations")
            result = validate(conn)
        finally:
            conn.close()
        if before!=input_hashes():
            raise ValueError("Source changed during research build")
        os.replace(str(staged),str(path))
    print("Research database built:",result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["build","validate"])
    args=parser.parse_args()
    if args.command=='build':
        build()
    else:
        with connect(readonly=True) as conn:
            print(validate(conn))
