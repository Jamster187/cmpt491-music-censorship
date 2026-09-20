"""Explicit, offline transition from the audited LRCLIB wait-race implementation."""
import fcntl
import json
import sqlite3
from pathlib import Path

import lyrics_production as production
from lyrics_lrclib import ROOT, digest, stamp

OLD_PIPELINE = 'e82352325fa3efc854819458c10c79a14902175303d556656b2247cbfaeecb42'
UNCHANGED = {
    'lyrics_production_match.py': '811427ad1d03956c0fe4544e448638aa9fdb295837b46fd41e8d413dc0a08594',
    'lyrics_lrclib_r.py': 'fdb7089341561f61ecc9c3cb152819b89be0a540d085a8fc96a36c64529388ae',
}


def migrate(c, root=ROOT):
    """Keep original settings/results; bind their payload hashes to the old bundle."""
    settings = dict(c.execute('SELECT * FROM production_settings'))
    current = production.fingerprint()
    if settings.get('current_pipeline_sha256') == current:
        verify_preserved(c)
        return 0
    if settings.get('pipeline_sha256') != OLD_PIPELINE or 'current_pipeline_sha256' in settings:
        raise ValueError('Unsupported implementation transition')
    for name, checksum in UNCHANGED.items():
        if digest((root/'src'/name).read_bytes()) != checksum:
            raise ValueError('Matching/cleaning methodology changed')
    gate = json.loads((root/'data/processed/lyrics_production_gate.json').read_text())
    old_gate = json.loads(settings['gate'])
    if (not gate['passed'] or gate['pipeline_sha256'] != current or
        gate['review_ledger_sha256'] != digest((root/'reports/lyrics_lrclib_r_review.json').read_bytes()) or
        gate['cases'] != old_gate['cases']):
        raise ValueError('Current cached pilot replay differs from original decisions')
    production.validate(c,root)
    evidence = [(sid,OLD_PIPELINE,digest(payload.encode())) for sid,payload in
                c.execute('SELECT * FROM production_results ORDER BY song_id')]
    if c.execute("SELECT count(*) FROM production_runs WHERE state='running'").fetchone()[0]:
        raise ValueError('Unfinished worker run requires investigation')
    transition = dict(from_pipeline=OLD_PIPELINE,to_pipeline=current,at=stamp(),
                      reason='Single-clock-read wait fix; unchanged matching and cleaning; per-result implementation provenance',
                      preserved_results=len(evidence),gate=gate,
                      migration_sha256=digest(Path(__file__).read_bytes()),
                      bundle_files={name:digest((root/'src'/name).read_bytes()) for name in production.BUNDLE})
    # DDL participates in this explicit transaction; no partial migration on failure.
    try:
        c.execute('BEGIN IMMEDIATE')
        c.execute('CREATE TABLE production_result_implementations (song_id TEXT PRIMARY KEY REFERENCES production_results(song_id),pipeline_sha256 TEXT NOT NULL,payload_sha256 TEXT NOT NULL)')
        c.execute('CREATE TABLE production_version_transitions (pipeline_sha256 TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        c.executemany('INSERT INTO production_result_implementations VALUES (?,?,?)',evidence)
        c.execute('INSERT INTO production_version_transitions VALUES (?,?)',(current,json.dumps(transition,sort_keys=True)))
        c.execute("INSERT INTO production_settings VALUES ('current_pipeline_sha256',?)",(current,))
        c.commit()
    except BaseException:
        c.rollback()
        raise
    return len(evidence)


def verify_preserved(c):
    rows = c.execute('''SELECT i.song_id,i.payload_sha256,r.payload FROM production_result_implementations i
                        LEFT JOIN production_results r USING(song_id)''').fetchall()
    for sid, checksum, payload in rows:
        if payload is None or digest(payload.encode()) != checksum:
            raise ValueError('Pre-resume disposition changed: '+sid)
    return len(rows)


def main():
    production.guards()
    with (ROOT/'data/processed/lyrics.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        c=production.connect()
        backup=ROOT/'data/processed/backups/lyrics-before-wait-fix.db'
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():
            with sqlite3.connect(str(backup)) as target:c.backup(target)
        try:
            print('Preserved/versioned prior dispositions:',migrate(c))
            print('Verified unchanged:',verify_preserved(c))
            production.initialize(c)
        finally:c.close()


if __name__=='__main__':main()
