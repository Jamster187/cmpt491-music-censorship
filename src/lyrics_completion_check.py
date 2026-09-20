"""Verify full dispositions and preservation against the ignored pre-resume ledger."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3

import lyrics_production as production
import lyrics_resume as resume
import research
from lyrics_lrclib import ROOT, digest


def check(synchronized=False):
    c=production.connect(readonly=True)
    try:
        if c.execute('SELECT count(*) FROM production_assets').fetchone()[0]!=production.POPULATION:
            raise ValueError('Unexpected frozen population')
        assets={row[0] for row in c.execute('SELECT song_id FROM production_assets')}
        rows={sid:json.loads(payload) for sid,payload in c.execute('SELECT * FROM production_results')}
        if set(rows)!=assets:raise ValueError('Unprocessed or out-of-population assets remain')
        counts=Counter(r['status'] for r in rows.values())
        if set(counts)-set(production.STATUSES):raise ValueError('Unknown dispositions')
        if c.execute("SELECT count(*) FROM production_runs WHERE state='running'").fetchone()[0]:
            raise ValueError('A production run is still active')
        files=production.validate(c)
        old=resume.verify_preserved(c)
        if old!=21646:raise ValueError('Audited pre-resume disposition set differs')
        old_ids={sid for sid, in c.execute('SELECT song_id FROM production_result_implementations')}
        current=dict(c.execute('SELECT * FROM production_settings'))['current_pipeline_sha256']
        runs={row[0]:row[1] for row in c.execute('SELECT run_id,state FROM production_runs')}
        for sid in assets-old_ids:
            r=rows[sid]
            if r.get('pipeline_sha256')!=current or r.get('run_id') not in runs:
                raise ValueError('New result lacks implementation/run provenance')
        if len(assets-old_ids)!=3717:raise ValueError('Unexpected resumed result count')
    finally:c.close()
    baseline=json.loads((ROOT/'data/processed/lyrics_resume_baseline.json').read_text())
    for name,checksum in baseline.items():
        path=ROOT/name
        if synchronized and name=='data/processed/research.db':
            path=ROOT/'data/processed/backups'/('research-before-lyrics-'+checksum+'.db')
        if not path.is_file() or research.sha(path)!=checksum:
            raise ValueError('Pre-resume file changed: '+name)
    if sum(name.startswith('data/lyrics/') for name in baseline)!=16572:
        raise ValueError('Original lyrics baseline differs')
    if synchronized:
        archive=ROOT/'data/processed/backups'/('research-before-lyrics-'+baseline['data/processed/research.db']+'.db')
        c=research.connect(readonly=True)
        try:
            c.execute('ATTACH DATABASE ? AS prior',(archive.as_uri()+'?mode=ro',))
            protected=[name for name, in c.execute("SELECT name FROM main.sqlite_master WHERE type='table'") if name not in ('lyrics_manifest','build_metadata')]
            for name in protected:
                # Table names originate only in the controlled project schema.
                for left,right in [('main','prior'),('prior','main')]:
                    if c.execute(f'SELECT count(*) FROM (SELECT * FROM {left}."{name}" EXCEPT SELECT * FROM {right}."{name}")').fetchone()[0]:
                        raise ValueError('Non-lyrics research table changed: '+name)
            if c.execute("SELECT count(*) FROM lyrics_manifest WHERE lyrics_status IN ('not_attempted','blocked_source_access')").fetchone()[0]:
                raise ValueError('Unified manifest remains stale')
        finally:c.close()
    result=dict(population=len(assets),dispositioned=len(rows),counts=dict(counts),files=files,
                preserved_dispositions=old,new_dispositions=3717,protected_files=len(baseline),
                original_lyrics_preserved=16572,manifest_synchronized=synchronized)
    print(json.dumps(result,sort_keys=True))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-synchronized',action='store_true')
    args=parser.parse_args()
    check(args.manifest_synchronized)
