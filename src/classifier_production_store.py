"""SQLite persistence for frozen, independent song/model jobs; no inference imports."""
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from classifier_panel_core import chunk_ranges, validate_ranges, aggregate, sigmoid, softmax

ROOT=Path(__file__).resolve().parents[1]
SCHEMA_PATH=ROOT/'docs/classifier_production_schema.json'
SPEC=json.loads(SCHEMA_PATH.read_text())
MODELS=tuple(SPEC['model_order'])
COLUMNS=tuple(c for m in MODELS for c in SPEC['models'][m]['columns'])


def now():return datetime.now(timezone.utc).isoformat()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def connect(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(path,timeout=30);c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL')
    return c


def initialize(c,targets,configuration):
    """Refuse reconfiguration; never replace an existing run or target set."""
    encoded=canonical(configuration)
    if c.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]:
        row=c.execute('SELECT configuration FROM run_config WHERE id=1').fetchone()
        actual=[dict(r) for r in c.execute('SELECT song_id,lyrics_sha256,source_words FROM targets ORDER BY song_id')]
        if not row or row[0]!=encoded or actual!=sorted(targets,key=lambda r:r['song_id']):raise ValueError('Existing run configuration/targets differ')
        return
    columns=',\n'.join(f'"{n}" REAL CHECK("{n}" IS NULL OR ("{n}" BETWEEN 0 AND 1))' for n in COLUMNS)
    metadata=',\n'.join(f'{m}_status TEXT NOT NULL DEFAULT \'pending\', {m}_token_count INTEGER, {m}_chunk_count INTEGER, {m}_normalized_sha256 TEXT, {m}_model_revision TEXT NOT NULL, {m}_checkpoint_sha256 TEXT NOT NULL' for m in MODELS)
    c.executescript(f'''
    BEGIN IMMEDIATE;
    CREATE TABLE run_config(id INTEGER PRIMARY KEY CHECK(id=1),configuration TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE targets(song_id TEXT PRIMARY KEY,lyrics_sha256 TEXT NOT NULL,source_words INTEGER NOT NULL);
    CREATE TABLE jobs(song_id TEXT NOT NULL REFERENCES targets(song_id),model TEXT NOT NULL CHECK(model IN {MODELS}),
      status TEXT NOT NULL CHECK(status IN ('pending','running','success','error')),attempts INTEGER NOT NULL DEFAULT 0,
      token_count INTEGER,chunk_count INTEGER,content_budget INTEGER,normalized_sha256 TEXT,
      inference_seconds REAL NOT NULL DEFAULT 0,error_type TEXT,updated_at TEXT NOT NULL,PRIMARY KEY(song_id,model));
    CREATE TABLE chunk_predictions(song_id TEXT NOT NULL,model TEXT NOT NULL,chunk_index INTEGER NOT NULL,
      content_start INTEGER NOT NULL,content_end INTEGER NOT NULL,input_tokens INTEGER NOT NULL,input_sha256 TEXT NOT NULL,
      logits TEXT NOT NULL,activated TEXT NOT NULL,scores TEXT NOT NULL,seconds REAL NOT NULL,
      PRIMARY KEY(song_id,model,chunk_index),FOREIGN KEY(song_id,model) REFERENCES jobs(song_id,model));
    CREATE TABLE executions(id INTEGER PRIMARY KEY,model TEXT NOT NULL,started_at TEXT NOT NULL,finished_at TEXT,
      status TEXT NOT NULL,new_successes INTEGER NOT NULL DEFAULT 0,failures INTEGER NOT NULL DEFAULT 0,
      load_seconds REAL NOT NULL DEFAULT 0,elapsed_seconds REAL NOT NULL DEFAULT 0,peak_rss_bytes INTEGER,error_type TEXT);
    CREATE TABLE song_results(song_id TEXT PRIMARY KEY REFERENCES targets(song_id),classifier_version TEXT NOT NULL,
      lyrics_sha256 TEXT NOT NULL,source_words INTEGER NOT NULL,processing_status TEXT NOT NULL DEFAULT 'pending',
      {metadata},{columns});
    ''')
    try:
        with c:
            c.execute('INSERT INTO run_config VALUES(1,?,?)',(encoded,now()))
            for t in targets:
                c.execute('INSERT INTO targets VALUES(?,?,?)',(t['song_id'],t['lyrics_sha256'],t['source_words']))
                row=dict(t,classifier_version=SPEC['version'])
                for m in MODELS:
                    a=SPEC['models'][m]['artifact'];row[m+'_model_revision']=a['revision'];row[m+'_checkpoint_sha256']=a['sha256'][a['weight_file']]
                    c.execute('INSERT INTO jobs(song_id,model,status,updated_at) VALUES(?,?,?,?)',(t['song_id'],m,'pending',now()))
                names=list(row);c.execute('INSERT INTO song_results('+','.join(names)+') VALUES('+','.join('?' for _ in names)+')',[row[k] for k in names])
    except BaseException:
        # An interrupted initialization is never mistaken for a usable partial target list.
        raise


def worklist(c,model,retry_errors=False):
    if model not in MODELS:raise ValueError('Unknown production model')
    states=('pending','running','error') if retry_errors else ('pending','running')
    return [dict(r) for r in c.execute('SELECT t.* FROM targets t JOIN jobs j USING(song_id) WHERE j.model=? AND j.status IN ('+','.join('?' for _ in states)+') ORDER BY t.song_id',(model,*states))]


def update_overall(c,sid):
    statuses=[r[0] for r in c.execute('SELECT status FROM jobs WHERE song_id=?',(sid,))]
    status='complete' if all(s=='success' for s in statuses) else 'partial' if 'success' in statuses else 'error' if 'error' in statuses else 'pending'
    c.execute('UPDATE song_results SET processing_status=? WHERE song_id=?',(status,sid))


def claim(c,sid,model):
    with c:
        row=c.execute('SELECT status FROM jobs WHERE song_id=? AND model=?',(sid,model)).fetchone()
        if not row:raise ValueError('Asset/model outside frozen targets')
        if row[0]=='success':return False
        c.execute("UPDATE jobs SET status='running',attempts=attempts+1,error_type=NULL,updated_at=? WHERE song_id=? AND model=?",(now(),sid,model))
        c.execute(f"UPDATE song_results SET {model}_status='running' WHERE song_id=?",(sid,))
    return True


def prepare(c,sid,model,token_count,chunk_count,budget,normalized_sha):
    old=c.execute('SELECT token_count,chunk_count,content_budget,normalized_sha256 FROM jobs WHERE song_id=? AND model=?',(sid,model)).fetchone()
    values=(token_count,chunk_count,budget,normalized_sha)
    if old['token_count'] is not None and tuple(old)!=values:raise ValueError('Resume tokenization changed')
    with c:
        c.execute('UPDATE jobs SET token_count=?,chunk_count=?,content_budget=?,normalized_sha256=? WHERE song_id=? AND model=?',(*values,sid,model))


def validate_chunk(model,row):
    spec=SPEC['models'][model];logits=row['logits'];activated=row['activated']
    if len(logits)!=spec['raw_dimension'] or len(activated)!=len(logits):raise ValueError('Wrong output dimensions')
    if any(not math.isfinite(v) for v in logits+activated):raise ValueError('Nonfinite output')
    expected=softmax(logits) if spec['activation']=='softmax' else [sigmoid(x) for x in logits]
    if any(not 0<=v<=1 or abs(v-e)>1e-7 for v,e in zip(activated,expected)):raise ValueError('Activation mismatch')
    if set(row['scores'])!=set(spec['columns']):raise ValueError('Undocumented/missing output')
    for name,index in zip(spec['columns'],spec['raw_indices']):
        if row['scores'][name]!=activated[index]:raise ValueError('Output mapping mismatch')
    if not 0<=row['content_start']<row['content_end'] or not 2<=row['input_tokens']<=spec['window']:raise ValueError('Invalid chunk bounds')
    if not math.isfinite(row['seconds']) or row['seconds']<0:raise ValueError('Invalid duration')


def save_chunk(c,sid,model,row):
    validate_chunk(model,row)
    with c:
        c.execute('INSERT INTO chunk_predictions VALUES(?,?,?,?,?,?,?,?,?,?,?)',(sid,model,row['chunk_index'],row['content_start'],row['content_end'],row['input_tokens'],row['input_sha256'],canonical(row['logits']),canonical(row['activated']),canonical(row['scores']),row['seconds']))


def chunks(c,sid,model):
    out=[]
    for r in c.execute('SELECT * FROM chunk_predictions WHERE song_id=? AND model=? ORDER BY chunk_index',(sid,model)):
        row=dict(r)
        for k in ('logits','activated','scores'):row[k]=json.loads(row[k])
        out.append(row)
    return out


def finish(c,sid,model):
    j=c.execute('SELECT * FROM jobs WHERE song_id=? AND model=?',(sid,model)).fetchone();rows=chunks(c,sid,model)
    if len(rows)!=j['chunk_count'] or [r['chunk_index'] for r in rows]!=list(range(j['chunk_count'])):raise ValueError('Incomplete chunks')
    validate_ranges([(r['content_start'],r['content_end']) for r in rows],j['token_count'],j['content_budget'])
    for r in rows:validate_chunk(model,r)
    values={col:aggregate([r['scores'][col] for r in rows],[r['content_end']-r['content_start'] for r in rows])['token_weighted_mean'] for col in SPEC['models'][model]['columns']}
    with c:
        c.execute("UPDATE jobs SET status='success',inference_seconds=?,error_type=NULL,updated_at=? WHERE song_id=? AND model=?",(sum(r['seconds'] for r in rows),now(),sid,model))
        values.update({model+'_status':'success',model+'_token_count':j['token_count'],model+'_chunk_count':j['chunk_count'],model+'_normalized_sha256':j['normalized_sha256']})
        c.execute('UPDATE song_results SET '+','.join(k+'=?' for k in values)+' WHERE song_id=?',(*values.values(),sid));update_overall(c,sid)


def fail(c,sid,model,error):
    with c:
        # Exception text may contain input snippets. Persist only the exception type.
        c.execute("UPDATE jobs SET status='error',error_type=?,updated_at=? WHERE song_id=? AND model=?",(type(error).__name__,now(),sid,model))
        c.execute(f"UPDATE song_results SET {model}_status='error' WHERE song_id=?",(sid,));update_overall(c,sid)
