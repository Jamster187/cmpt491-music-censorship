"""Prove a completed 200-song production pilot resumes without changing any table."""
import json
import sqlite3
import subprocess
import sys
import time
from classifier_production import DEFAULT_PILOT
from classifier_production_store import ROOT,canonical,digest


def snapshot():
    c=sqlite3.connect('file:'+str(DEFAULT_PILOT)+'?mode=ro',uri=True)
    if c.execute("SELECT count(*) FROM jobs WHERE status='success'").fetchone()[0]!=800 or c.execute('SELECT count(*) FROM jobs').fetchone()[0]!=800:
        raise ValueError('No-op check requires an already complete 200-song pilot')
    tables=('targets','jobs','chunk_predictions','song_results','executions','run_config')
    result={t:digest(canonical(c.execute('SELECT * FROM '+t+' ORDER BY 1,2').fetchall())) for t in tables}
    c.close();return result


def main():
    before=snapshot();started=time.perf_counter()
    subprocess.run([sys.executable,str(ROOT/'src/classifier_production.py'),'run','--scope','pilot'],check=True)
    if before!=snapshot():raise ValueError('Completed-run resume changed persisted tables')
    proof=dict(status='passed',new_jobs=0,new_executions=0,all_persisted_tables_unchanged=True,elapsed_seconds=time.perf_counter()-started,table_digests=before)
    path=DEFAULT_PILOT.parent/'noop_validation.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(proof,indent=2)+'\n');temp.replace(path)
    print('No-op resume: every table unchanged; zero model loads or new jobs.')

if __name__=='__main__':main()
