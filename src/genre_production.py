"""Frozen LLM genre production, independent of public/research databases."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time

from genre_evidence import DATABASE as EVIDENCE, ro, sha
from genre_pilot import collect
from genre_llm import ROOT, DOC, MODEL, CONFIG, BATCH, evidence_input, check_predictions, dump, digest, EXCLUDED_TAG
from genre_rules import TAXONOMY

LOCAL=ROOT/'data/experiments/genre_production'
DB=ROOT/'data/processed/genre_results.db'
PILOT_COMMIT='0514c2cdd1a3f52b9fe5cca704fe88a0d68c961e'
FROZEN=('docs/genre/llm/prompt.txt','docs/genre/llm/output.schema.json','src/genre_llm.py','docs/genre/taxonomy_mapping.json')


def now():return datetime.now(timezone.utc).isoformat()
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def connection(path=DB):
    c=sqlite3.connect(path,timeout=60);c.row_factory=sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA foreign_keys=ON')
    return c


def frozen():
    result={}
    for p in FROZEN:
        expected=subprocess.check_output(['git','show',PILOT_COMMIT+':'+p],cwd=ROOT)
        if (ROOT/p).read_bytes()!=expected:raise ValueError('Frozen implementation changed: '+p)
        result[p]=digest(expected)
    return result


def access():
    forbidden=('OPENAI_API_KEY','CODEX_API_KEY','OPENAI_BASE_URL','OPENAI_API_BASE')
    if any(os.environ.get(k) for k in forbidden):raise ValueError('API credential/endpoint environment detected; separate billing path prohibited')
    result=subprocess.run(['codex','login','status'],capture_output=True,text=True,check=True)
    if 'Logged in using ChatGPT' not in result.stdout+result.stderr:raise ValueError('ChatGPT-authenticated access required')
    version=subprocess.check_output(['codex','--version'],text=True).strip()
    if version!='codex-cli 0.155.1':raise ValueError('CLI changed; equivalence validation required')
    return {'path':'ChatGPT-authenticated Codex CLI','cli_version':version,'checked_at':now(),'api_fallback':False}


def request_text(rows):
    return (DOC/'prompt.txt').read_text()+json.dumps(rows,ensure_ascii=False,sort_keys=True)+'\n'


def prepare():
    hashes=frozen();billing=access();LOCAL.mkdir(parents=True,exist_ok=True)
    if DB.exists():
        with closing(connection()) as c:verify(c)
        print('Existing frozen production database validated; retained');return
    population=json.loads((ROOT/'data/processed/month_end_catchup/population.json').read_text())['new_population']
    if len(population)!=28041 or len(set(population))!=28041:raise ValueError('Population mismatch')
    temp=DB.with_suffix('.building.db')
    if temp.exists():raise ValueError('Interrupted input build exists; inspect before replacing it')
    c=connection(temp)
    c.executescript('''CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE songs(song_id TEXT PRIMARY KEY,title TEXT,artist TEXT,period TEXT,input_json TEXT NOT NULL,input_sha256 TEXT NOT NULL,batch_id INTEGER,
      status TEXT NOT NULL DEFAULT 'pending',primary_genre TEXT,secondary_genres TEXT,confidence TEXT,reason TEXT,
      model TEXT,prompt_version TEXT,source TEXT,error TEXT,completed_at TEXT);
    CREATE TABLE batches(batch_id INTEGER PRIMARY KEY,song_ids TEXT NOT NULL,request_sha256 TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending');
    CREATE TABLE attempts(attempt_id INTEGER PRIMARY KEY,batch_id INTEGER,started_at TEXT,finished_at TEXT,seconds REAL,
      status TEXT,error TEXT,folder TEXT,usage_json TEXT,response_sha256 TEXT);
    CREATE TABLE checkpoints(checkpoint_id INTEGER PRIMARY KEY,created_at TEXT,summary_json TEXT,stop_reason TEXT);
    ''')
    try:
        with closing(ro(EVIDENCE)) as e:
            e.row_factory=sqlite3.Row
            src={r['song_id']:dict(r) for r in e.execute('SELECT song_id,title,artist,first_chart_date,period FROM songs')}
            if set(src)!=set(population):raise ValueError('Evidence IDs do not match final population')
            pilot_inputs={r['song_id']:r for r in json.loads((ROOT/'reports/genre_llm/inputs.json').read_text())}
            for i,sid in enumerate(sorted(population)):
                inp=evidence_input(src[sid],collect(e,sid))
                if sid in pilot_inputs and inp!=pilot_inputs[sid]:raise ValueError('Pilot evidence changed: '+sid)
                payload=canonical(inp)
                c.execute('INSERT INTO songs(song_id,title,artist,period,input_json,input_sha256) VALUES (?,?,?,?,?,?)',
                          (sid,src[sid]['title'],src[sid]['artist'],src[sid]['period'],payload,digest(payload.encode())))
                if i%1000==0:c.commit();print('Frozen inputs',i,flush=True)
        pilot=json.loads((ROOT/'reports/genre_llm/metadata.json').read_text())
        check_predictions({'predictions':pilot},list(pilot_inputs))
        ordered=list(pilot_inputs)
        remaining=sorted(set(population)-set(ordered),key=lambda sid:digest(('genre-production-v1'+sid).encode()))
        groups=[ordered[i:i+BATCH] for i in range(0,len(ordered),BATCH)]+[remaining[i:i+BATCH] for i in range(0,len(remaining),BATCH)]
        for bi,ids in enumerate(groups):
            inputs=[json.loads(c.execute('SELECT input_json FROM songs WHERE song_id=?',(sid,)).fetchone()[0]) for sid in ids]
            c.execute('INSERT INTO batches(batch_id,song_ids,request_sha256) VALUES (?,?,?)',(bi,canonical(ids),digest(request_text(inputs).encode())))
            c.executemany('UPDATE songs SET batch_id=? WHERE song_id=?',[(bi,sid) for sid in ids])
        for r in pilot:persist(c,r,'approved_pilot',now())
        c.execute("UPDATE batches SET status='completed' WHERE batch_id<30")
        settings={'version':'genre-production-v1','frozen_commit':PILOT_COMMIT,'frozen_files':hashes,'model':MODEL,'config':CONFIG,
                  'taxonomy':list(TAXONOMY),'billing':billing,'created_at':now(),'population_sha256':digest(canonical(sorted(population)).encode()),
                  'evidence_db_sha256':sha(EVIDENCE),'pilot_predictions_sha256':sha(ROOT/'reports/genre_llm/metadata.json')}
        for k,v in settings.items():c.execute('INSERT INTO settings VALUES (?,?)',(k,canonical(v)))
        c.commit();c.execute('PRAGMA wal_checkpoint(TRUNCATE)');c.close();temp.replace(DB)
        dump(LOCAL/'manifest.json',settings)
        print('Prepared 28041 songs; reused 300 approved predictions; 27741 pending',flush=True)
    except BaseException:
        c.close();raise


def persist(c,r,source,when):
    # Successful results are immutable, including those recovered after interruption.
    c.execute("""UPDATE songs SET status='completed',primary_genre=?,secondary_genres=?,confidence=?,reason=?,model=?,
      prompt_version=?,source=?,error=NULL,completed_at=? WHERE song_id=? AND status!='completed'""",
      (r['primary_genre'],canonical(r['secondary_genres']),r['confidence'],r['reason'],MODEL,PILOT_COMMIT,source,when,r['song_id']))


def verify(c):
    settings={r['key']:json.loads(r['value']) for r in c.execute('SELECT * FROM settings')}
    if settings['frozen_files']!=frozen():raise ValueError('Frozen source mismatch')
    if settings['model']!=MODEL or settings['config']!=CONFIG or settings['taxonomy']!=list(TAXONOMY):raise ValueError('Frozen configuration mismatch')
    ids=[r[0] for r in c.execute('SELECT song_id FROM songs ORDER BY song_id')]
    expected=sorted(json.loads((ROOT/'data/processed/month_end_catchup/population.json').read_text())['new_population'])
    if ids!=expected or len(ids)!=28041:raise ValueError('Target population changed')
    for r in c.execute('SELECT * FROM songs'):
        if digest(r['input_json'].encode())!=r['input_sha256']:raise ValueError('Frozen input changed')
        inp=json.loads(r['input_json'])
        if set(inp)!={'song_id','title','artist','first_chart_date','genre_evidence'} or inp['song_id']!=r['song_id']:raise ValueError('Input whitelist/identity mismatch')
        if any(EXCLUDED_TAG.search(t['raw_tag']) for t in inp['genre_evidence']):raise ValueError('Excluded input tag')
        if r['status']=='completed':
            if r['model']!=MODEL or r['prompt_version']!=PILOT_COMMIT:raise ValueError('Prediction version mismatch')
            pred={k:r[k] for k in ('song_id','primary_genre','confidence','reason')};pred['secondary_genres']=json.loads(r['secondary_genres'])
            check_predictions({'predictions':[pred]},[r['song_id']])
    covered=[]
    for b in c.execute('SELECT * FROM batches'):
        batch_ids=json.loads(b['song_ids']);covered.extend(batch_ids)
        inputs=[]
        for sid in batch_ids:
            row=c.execute('SELECT input_json,batch_id,status FROM songs WHERE song_id=?',(sid,)).fetchone()
            if row is None or row['batch_id']!=b['batch_id']:raise ValueError('Batch identity mismatch')
            if b['status']=='completed' and row['status']!='completed':raise ValueError('Incomplete completed batch')
            inputs.append(json.loads(row['input_json']))
        if digest(request_text(inputs).encode())!=b['request_sha256']:raise ValueError('Batch request changed')
    if sorted(covered)!=ids:raise ValueError('Batch coverage mismatch')
    return settings


def drift(rows, previous=None):
    if len(rows)<200:return None
    genres=Counter(r['primary_genre'] for r in rows);conf=Counter(r['confidence'] for r in rows);n=len(rows)
    if max(genres.values())/n>=.80:return 'Single genre >=80% of recent 200+ predictions'
    if genres['Other']/n>=.50:return 'Other >=50% of recent predictions'
    if conf['low']/n>=.60:return 'Low confidence >=60% of recent predictions'
    if previous and len(previous)>=200:
        old=Counter(r['confidence'] for r in previous)
        if any(abs(conf[k]/n-old[k]/len(previous))>=.40 for k in ('high','medium','low')):return 'Confidence share changed by >=40 percentage points'
    return None


def stats(c):
    counts=dict(c.execute('SELECT status,count(*) FROM songs GROUP BY status').fetchall())
    genres={g:{'count':0,'percentage_population':0,'confidence':{}} for g in TAXONOMY}
    for g,n in c.execute("SELECT primary_genre,count(*) FROM songs WHERE status='completed' GROUP BY primary_genre"):
        genres[g]['count']=n;genres[g]['percentage_population']=round(n/28041*100,3)
        genres[g]['confidence']=dict(c.execute("SELECT confidence,count(*) FROM songs WHERE primary_genre=? AND status='completed' GROUP BY confidence",(g,)).fetchall())
    return {'target':28041,'status_counts':counts,'confidence':dict(c.execute("SELECT confidence,count(*) FROM songs WHERE status='completed' GROUP BY confidence").fetchall()),
            'genres':genres,'period_genres':[dict(r) for r in c.execute("SELECT period,primary_genre,count(*) n FROM songs WHERE status='completed' GROUP BY period,primary_genre ORDER BY period,primary_genre")],
            'new_requests':c.execute('SELECT count(*) FROM attempts').fetchone()[0],
            'request_seconds':c.execute('SELECT coalesce(sum(seconds),0) FROM attempts').fetchone()[0],
            'database_bytes':DB.stat().st_size if DB.exists() else 0,'as_of':now()}


def monitor(c):
    recent=[dict(r) for r in c.execute("SELECT primary_genre,confidence FROM songs WHERE source='production' AND status='completed' ORDER BY completed_at DESC,song_id LIMIT 400")]
    why=drift(recent[:200],recent[200:])
    s=stats(c)
    c.execute('INSERT INTO checkpoints(created_at,summary_json,stop_reason) VALUES (?,?,?)',(now(),canonical(s),why));c.commit()
    dump(LOCAL/'progress.json',s)
    if why:raise RuntimeError('QUALITY STOP: '+why)
    return s


def ingest_response(c, batch, folder):
    ids=json.loads(batch['song_ids']);obj=json.loads((folder/'response.json').read_text())
    events=[json.loads(x) for x in (folder/'events.jsonl').read_text().splitlines()]
    for e in events:
        if 'item' not in e:continue
        item=e['item']
        # CLI transport fallback is not a model tool call. Allow only this exact
        # observed notice; still require a completed turn and valid predictions.
        transport_notice=(item.get('type')=='error' and item.get('message')==
                          'Falling back from WebSockets to HTTPS transport. request timed out')
        if item['type'] not in ('agent_message','reasoning') and not transport_notice:raise ValueError('Unexpected tool use')
    if sum(e['type']=='turn.completed' for e in events)!=1:raise ValueError('No unique completed inference turn')
    # Preserve individually valid rows even if another row fails schema validation.
    rows=obj.get('predictions',[]) if isinstance(obj,dict) else []
    seen=Counter(r.get('song_id') for r in rows if isinstance(r,dict))
    for r in rows:
        if not isinstance(r,dict) or r.get('song_id') not in ids or seen[r.get('song_id')]!=1:continue
        try:check_predictions({'predictions':[r]},[r['song_id']])
        except (ValueError,TypeError,KeyError):continue
        persist(c,r,'production',now())
    c.commit()
    check_predictions(obj,ids)
    return next(e.get('usage',{}) for e in events if e['type']=='turn.completed')


def execute_batch(c,batch):
    bi=batch['batch_id'];ids=json.loads(batch['song_ids'])
    inputs=[json.loads(c.execute('SELECT input_json FROM songs WHERE song_id=?',(sid,)).fetchone()[0]) for sid in ids]
    prompt=request_text(inputs)
    if digest(prompt.encode())!=batch['request_sha256']:raise ValueError('Frozen request changed')
    # Recover a complete transport response without paying for another inference.
    previous=c.execute("SELECT * FROM attempts WHERE batch_id=? AND (status='running' OR (status='error' AND error='ValueError: Unexpected tool use')) ORDER BY attempt_id DESC LIMIT 1",(bi,)).fetchone()
    if previous:
        folder=LOCAL/previous['folder']
        if (folder/'response.json').exists():
            try:
                usage=ingest_response(c,batch,folder)
                c.execute("UPDATE attempts SET status='recovered',finished_at=?,usage_json=?,response_sha256=? WHERE attempt_id=?",(now(),canonical(usage),sha(folder/'response.json'),previous['attempt_id']))
                c.execute("UPDATE batches SET status='completed' WHERE batch_id=?",(bi,));c.commit();return
            except (ValueError,KeyError,TypeError,OSError) as exc:
                raise RuntimeError('Interrupted response failed validation; inspect before retrying') from exc
        c.execute("UPDATE attempts SET status='interrupted',finished_at=? WHERE attempt_id=?",(now(),previous['attempt_id']));c.commit()
    cur=c.execute("INSERT INTO attempts(batch_id,started_at,status) VALUES (?,?,'running')",(bi,now()));aid=cur.lastrowid
    rel=f'requests/{bi:05d}/{aid:06d}';folder=LOCAL/rel;folder.mkdir(parents=True,exist_ok=True)
    c.execute('UPDATE attempts SET folder=? WHERE attempt_id=?',(rel,aid))
    c.execute("UPDATE batches SET status='running' WHERE batch_id=?",(bi,))
    c.execute("UPDATE songs SET status='running' WHERE batch_id=? AND status!='completed'",(bi,));c.commit()
    (folder/'request.txt').write_text(prompt)
    start=time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix='genre-production-') as isolated:
            cmd=['codex','exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','-C',isolated,'-s','read-only','-m',MODEL,
                 '--output-schema',str(DOC/'output.schema.json'),'--json','-o',str(folder/'response.json')]
            for setting in CONFIG:cmd+=['-c',setting]
            cmd+=['-']
            with (folder/'events.jsonl').open('w') as out,(folder/'stderr.log').open('w') as err:
                result=subprocess.run(cmd,input=prompt,text=True,stdout=out,stderr=err,timeout=600)
        if result.returncode:raise RuntimeError('Transport/runtime failure; inspect private logs; no API fallback')
        usage=ingest_response(c,batch,folder)
        c.execute("UPDATE attempts SET status='completed',finished_at=?,seconds=?,usage_json=?,response_sha256=? WHERE attempt_id=?",(now(),time.monotonic()-start,canonical(usage),sha(folder/'response.json'),aid))
        c.execute("UPDATE batches SET status='completed' WHERE batch_id=?",(bi,));c.commit()
    except Exception as exc:
        message=type(exc).__name__+': '+str(exc)
        c.execute("UPDATE attempts SET status='error',finished_at=?,seconds=?,error=? WHERE attempt_id=?",(now(),time.monotonic()-start,message,aid))
        c.execute("UPDATE batches SET status='error' WHERE batch_id=?",(bi,))
        c.execute("UPDATE songs SET status='error',error=? WHERE batch_id=? AND status!='completed'",(message,bi));c.commit()
        monitor(c)
        raise RuntimeError('STOP: failed batch '+str(bi)+'; successful song rows preserved; inspect before retry') from exc


def run(retry_errors=False,limit=None):
    billing=access();LOCAL.mkdir(parents=True,exist_ok=True)
    with (LOCAL/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        dump(LOCAL/'worker.json',{'pid':os.getpid(),'started_at':now(),'billing':billing})
        with closing(connection()) as c:
            verify(c)
            last=c.execute('SELECT stop_reason FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 1').fetchone()
            if last and last[0]:raise ValueError('Quality stop remains unresolved: '+last[0])
            if not retry_errors and c.execute("SELECT 1 FROM batches WHERE status='error' LIMIT 1").fetchone():
                raise ValueError('Failed batches require inspection and explicit --retry-errors')
            if retry_errors:
                c.execute("UPDATE batches SET status='pending' WHERE status='error'")
                c.execute("UPDATE songs SET status='pending',error=NULL WHERE status='error'");c.commit()
            batches=c.execute("SELECT * FROM batches WHERE status IN ('pending','running') ORDER BY batch_id").fetchall()
            for i,b in enumerate(batches):
                if limit is not None and i>=limit:break
                execute_batch(c,b)
                s=monitor(c)
                print(now(),'batch',b['batch_id'],'completed',s['status_counts'].get('completed',0),flush=True)
            s=monitor(c)
            if not c.execute("SELECT 1 FROM songs WHERE status!='completed' LIMIT 1").fetchone():
                verify(c)
                # Automatic completion means inference finished, NOT qualitative audit approval.
                dump(LOCAL/'completion.json',{'inference_complete':True,'post_run_review_pending':True,'summary':s})
                export(c)


def export(c):
    path=LOCAL/'song_genres.jsonl';temp=path.with_suffix('.tmp')
    with temp.open('w') as f:
        for r in c.execute('SELECT song_id,primary_genre,secondary_genres,confidence,reason,model,prompt_version,status,source,error FROM songs ORDER BY song_id'):
            d=dict(r);d['secondary_genres']=json.loads(d['secondary_genres']) if d['secondary_genres'] else None
            f.write(canonical(d)+'\n')
    temp.replace(path)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run','status','validate'])
    p.add_argument('--retry-errors',action='store_true');p.add_argument('--limit-batches',type=int);a=p.parse_args()
    if a.command=='prepare':prepare()
    elif a.command=='run':run(a.retry_errors,a.limit_batches)
    else:
        with closing(connection()) as c:
            if a.command=='validate':verify(c)
            print(json.dumps(stats(c),ensure_ascii=False,indent=2))
