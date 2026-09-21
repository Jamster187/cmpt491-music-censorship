"""Frozen four-model production runner. Full-corpus inference requires --scope full."""
import argparse
import csv
import fcntl
import importlib.metadata
import json
import platform
import resource
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
import classifier_production_store as store
from classifier_production_store import ROOT, SPEC, MODELS, COLUMNS, sha, digest, canonical, now

PILOT_SHA='47103f916c19dbe89e9d8541ee56c101158a1a24ec120c2123b529087e962f03'
DEFAULT_PILOT=ROOT/'data/experiments/classifier_production/pilot.db'
DEFAULT_FULL=ROOT/'data/processed/classifier_results.db'


def targets(scope):
    """Read only the approved research manifest; verify every approved source hash."""
    db=sqlite3.connect('file:'+str(ROOT/'data/processed/research.db')+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    if db.execute('SELECT count(*) FROM study_population').fetchone()[0]!=25363:raise ValueError('Study population changed')
    rows=db.execute("SELECT l.song_id,l.lyrics_sha256,l.lyrics_path FROM lyrics_manifest l JOIN study_population p USING(song_id) WHERE l.lyrics_status='success' AND l.match_status='high_confidence' ORDER BY l.song_id").fetchall();db.close()
    if len(rows)!=19372 or len({r['song_id'] for r in rows})!=19372:raise ValueError('Approved corpus changed')
    selected=None
    if scope=='pilot':
        path=ROOT/'reports/lyriclens_sample.csv'
        if sha(path)!=PILOT_SHA:raise ValueError('Pilot sample changed')
        with path.open() as f:selected={r['song_id']:r['lyrics_sha256'] for r in csv.DictReader(f)}
        if len(selected)!=200:raise ValueError('Wrong pilot population')
    elif scope!='full':raise ValueError('Unknown scope')
    result=[]
    for r in rows:
        path=ROOT/'data/lyrics'/(r['song_id']+'.txt')
        supplied=Path(r['lyrics_path']);supplied=supplied if supplied.is_absolute() else ROOT/supplied
        if supplied.resolve()!=path.resolve() or path.is_symlink():raise ValueError('Unexpected lyric path')
        if sha(path)!=r['lyrics_sha256']:raise ValueError('Source lyric hash mismatch')
        if selected is None or r['song_id'] in selected:
            if selected is not None and selected[r['song_id']]!=r['lyrics_sha256']:raise ValueError('Pilot lyric changed')
            result.append(dict(song_id=r['song_id'],lyrics_sha256=r['lyrics_sha256'],source_words=len(path.read_text().split())))
    if len(result)!=(200 if scope=='pilot' else 19372):raise ValueError('Targets missing from approved corpus')
    return result


def configuration(scope):
    files=['src/classifier_production.py','src/classifier_production_store.py','src/classifier_production_engine.py','src/classifier_panel_core.py','src/lyriclens_evaluation.py','src/lyriclens_diagnostics.py','docs/classifier_production_schema.json','data/experiments/lyriclens/source/app.py']
    nltk_pins=json.loads((ROOT/'reports/lyriclens_artifacts.json').read_text())['nltk']
    for name,h in nltk_pins.items():
        if sha(ROOT/'data/experiments/lyriclens/nltk_data'/name)!=h:raise ValueError('NLTK artifact changed')
    return dict(nltk=nltk_pins,version=SPEC['version'],scope=scope,python=platform.python_version(),machine=platform.machine(),
                files={p:sha(ROOT/p) for p in files},
                dependencies={p:importlib.metadata.version(p) for p in ['torch','transformers','safetensors','numpy','nltk','pandas','sentencepiece']},
                sample_sha256=PILOT_SHA if scope=='pilot' else None)


@contextmanager
def lock(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another classifier worker holds this run lock') from None
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)


def process(c,target,model,engine):
    sid=target['song_id']
    if not store.claim(c,sid,model):return False
    try:
        path=ROOT/'data/lyrics'/(sid+'.txt')
        before=sha(path)
        if before!=target['lyrics_sha256']:raise ValueError('Source lyric changed')
        ids,spans,normalized=engine.tokenize(path.read_text())
        store.prepare(c,sid,model,len(ids),len(spans),engine.budget,normalized)
        saved={r['chunk_index']:r for r in store.chunks(c,sid,model)}
        for index,(start,end) in enumerate(spans):
            if index in saved:
                r=saved[index];built,h=engine.input(ids,start,end)
                if (r['content_start'],r['content_end'],r['input_tokens'],r['input_sha256'])!=(start,end,len(built),h):raise ValueError('Resume chunk input changed')
                store.validate_chunk(model,r)
            else:store.save_chunk(c,sid,model,engine.predict(ids,start,end,index))
        if sha(path)!=before:raise ValueError('Source lyric changed during inference')
        store.finish(c,sid,model);return True
    except Exception as error:
        store.fail(c,sid,model,error);return False


def worker(db,model,retry_errors,scope):
    from classifier_production_engine import Engine
    with lock(Path(str(db)+'.'+model+'.lock')):
        c=store.connect(db)
        if c.execute('SELECT configuration FROM run_config WHERE id=1').fetchone()[0]!=canonical(configuration(scope)):raise ValueError('Worker configuration mismatch')
        pending=store.worklist(c,model,retry_errors)
        if not pending:return
        started=time.perf_counter()
        with c:
            execution=c.execute('INSERT INTO executions(model,started_at,status) VALUES(?,?,?)',(model,now(),'running')).lastrowid
        successes=failures=0;load=0;error_type=None;status='complete'
        try:
            engine=Engine(model);load=time.perf_counter()-started
            for i,target in enumerate(pending):
                if process(c,target,model,engine):successes+=1
                else:failures+=1
                if (i+1)%10==0:print(model,i+1,'/',len(pending),flush=True)
            if failures:status='errors'
        except BaseException as error:
            status='interrupted' if isinstance(error,(KeyboardInterrupt,SystemExit)) else 'error';error_type=type(error).__name__
            raise
        finally:
            rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
            with c:c.execute('UPDATE executions SET finished_at=?,status=?,new_successes=?,failures=?,load_seconds=?,elapsed_seconds=?,peak_rss_bytes=?,error_type=? WHERE id=?',(now(),status,successes,failures,load,time.perf_counter()-started,rss,error_type,execution))
            c.close()


def status(c):
    return [dict(r) for r in c.execute('SELECT model,status,count(*) AS songs FROM jobs GROUP BY model,status ORDER BY model,status')]


def validate(c,scope,require_complete=True):
    expected=targets(scope)
    actual=[dict(r) for r in c.execute('SELECT * FROM targets ORDER BY song_id')]
    if actual!=expected:raise ValueError('Target manifest mismatch')
    if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Database integrity failure')
    if c.execute('SELECT count(*) FROM jobs').fetchone()[0]!=len(expected)*4:raise ValueError('Wrong job population')
    for j in c.execute('SELECT * FROM jobs').fetchall():
        if j['model'] not in MODELS:raise ValueError('Unexpected model')
        if j['status']!='success':
            if require_complete:raise ValueError('Incomplete model jobs')
            continue
        rows=store.chunks(c,j['song_id'],j['model'])
        store.validate_ranges([(r['content_start'],r['content_end']) for r in rows],j['token_count'],j['content_budget'])
        if len(rows)!=j['chunk_count'] or [r['chunk_index'] for r in rows]!=list(range(len(rows))):raise ValueError('Invalid chunk sequence')
        for r in rows:store.validate_chunk(j['model'],r)
        song=c.execute('SELECT * FROM song_results WHERE song_id=?',(j['song_id'],)).fetchone()
        for col in SPEC['models'][j['model']]['columns']:
            value=store.aggregate([r['scores'][col] for r in rows],[r['content_end']-r['content_start'] for r in rows])['token_weighted_mean']
            if song[col]!=value:raise ValueError('Aggregate mismatch')
        if j['model']=='cardiff' and abs(sum(song[col] for col in SPEC['models']['cardiff']['columns'])-1)>3e-7:raise ValueError('Sentiment sum mismatch')
    return dict(targets=len(expected),score_columns=len(COLUMNS),jobs=status(c))


def result_path(path):
    path=Path(path).resolve()
    if path!=DEFAULT_FULL and not path.is_relative_to(ROOT/'data/experiments/classifier_production'):
        raise ValueError('Results must use classifier_results.db or the dedicated classifier experiment directory')
    return path


def main():
    def interrupted(signum,frame):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupted)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['run','worker','validate','status']);p.add_argument('--scope',choices=['pilot','full'],required=True)
    p.add_argument('--db',type=Path);p.add_argument('--model',choices=MODELS);p.add_argument('--retry-errors',action='store_true');p.add_argument('--allow-incomplete',action='store_true');a=p.parse_args()
    db=result_path(a.db or (DEFAULT_PILOT if a.scope=='pilot' else DEFAULT_FULL))
    if a.scope=='pilot' and db==DEFAULT_FULL:raise ValueError('Pilot cannot populate the full-corpus result destination')
    if a.command=='worker':
        if not a.model or not db.exists():raise ValueError('Worker requires initialized database/model')
        worker(db,a.model,a.retry_errors,a.scope);return
    if a.command in ('status','validate'):
        c=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
        print(json.dumps(status(c) if a.command=='status' else validate(c,a.scope,not a.allow_incomplete),indent=2));c.close();return
    with lock(Path(str(db)+'.run.lock')):
        c=store.connect(db);store.initialize(c,targets(a.scope),configuration(a.scope))
        for model in MODELS:
            if not store.worklist(c,model,a.retry_errors):continue
            command=[sys.executable,str(Path(__file__)), 'worker','--scope',a.scope,'--db',str(db),'--model',model]+(['--retry-errors'] if a.retry_errors else [])
            child=subprocess.Popen(command)
            try:child.wait()
            except BaseException:
                child.terminate();child.wait();raise
            if child.returncode:print(model,'worker exited',child.returncode,flush=True)
        result=validate(c,a.scope,False);print(json.dumps(result,indent=2))
        if any(r['status']!='success' for r in result['jobs']):raise SystemExit(1)

if __name__=='__main__':main()
