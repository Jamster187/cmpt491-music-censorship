"""Resource-gated exhaustive V5 execution; checksummed atomic checkpoints."""
from __future__ import annotations
import argparse
import collections
import hashlib
import io
import json
import resource
import sqlite3
import time
import numpy as np
import pairwise_v5_common as c
import pairwise_v5_diagnostics as diagnostics
import pairwise_v5_stats as engine


def encode(rows):
    stream=io.BytesIO(); np.save(stream,rows,allow_pickle=False); return stream.getvalue()


class Store:
    def __init__(self,path,fingerprint):
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT)')
        existing=self.db.execute("SELECT value FROM meta WHERE key='fingerprint'").fetchone()
        if existing and existing[0]!=fingerprint:
            self.db.close(); raise ValueError('Checkpoint protocol mismatch')
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('fingerprint',?)",(fingerprint,))
        self.db.execute('CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY,body BLOB NOT NULL,sha TEXT NOT NULL,contrasts TEXT NOT NULL,contrast_sha TEXT NOT NULL,seconds REAL NOT NULL)')
        self.db.commit()

    def get(self,number):
        row=self.db.execute('SELECT body,sha,contrasts,contrast_sha FROM chunks WHERE id=?',(number,)).fetchone()
        if row is None: return None
        body,expected,contrasts,contrast_sha=row
        if hashlib.sha256(body).hexdigest()!=expected or hashlib.sha256(contrasts.encode()).hexdigest()!=contrast_sha:
            raise ValueError('Checkpoint checksum mismatch: '+str(number))
        values=np.load(io.BytesIO(body),allow_pickle=False)
        if values.dtype!=engine.RESULT_DTYPE: raise ValueError('Checkpoint result schema mismatch')
        return values,json.loads(contrasts)

    def put(self,number,rows,contrasts,seconds):
        body=encode(rows); detail=json.dumps(c.clean(contrasts),sort_keys=True,separators=(',',':'))
        old=self.get(number)
        if old is not None:
            if encode(old[0])!=body or json.dumps(c.clean(old[1]),sort_keys=True,separators=(',',':'))!=detail:
                raise ValueError('Attempt to change completed checkpoint')
            return
        with self.db:
            self.db.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?)',
                (number,body,hashlib.sha256(body).hexdigest(),detail,hashlib.sha256(detail.encode()).hexdigest(),seconds))

    def close(self): self.db.close()


def measured_task(workspace,task,use_diagnostics=True):
    start=time.perf_counter(); aligned=workspace.aligned(task)
    sy,sx=diagnostics.lookup_diagnostics(workspace,task,aligned) if use_diagnostics else (None,np.nan)
    rows,contrasts=engine.evaluate(aligned,task,sy,sx)
    if len(rows)!=task['music_variables']: raise ValueError('Incomplete chunk')
    return rows,contrasts,time.perf_counter()-start


def peak_memory():
    # macOS reports bytes, Linux KiB.
    import sys
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform=='darwin' else value*1024)


def benchmark(budget):
    if c.read_json(c.PUBLIC/'synthetic_validation.json')['status']!='PASS':
        raise ValueError('Null-validation gate failed')
    plan=c.load(c.LOCAL/'plan.pkl'); workspace=engine.Workspace(); groups=collections.defaultdict(list)
    # Every view, native frequency, variable kind and track is represented.
    # The hash order is fixed independently of numerical outcomes.
    for task in plan:
        groups[(task['view_id'],task['frequency'],task['external_kind'],task['track'])].append(task)
    measurements=[]; strata=[]
    for key,tasks in sorted(groups.items()):
        chosen=sorted(tasks,key=lambda t:c.digest({'seed':c.CONFIG['seed'],'chunk':t['chunk_id']}))[:4]
        times=[]
        for task in chosen:
            workspace.cache.clear()  # Cold alignment is a conservative execution cost.
            rows,contrasts,seconds=measured_task(workspace,task,use_diagnostics=False)
            start=time.perf_counter(); encode(rows); json.dumps(c.clean(contrasts)); seconds+=time.perf_counter()-start
            times.append(seconds)
            measurements.append(dict(chunk_id=task['chunk_id'],view_id=key[0],frequency=key[1],kind=key[2],track=key[3],
                seconds=seconds,pair_track_rows=len(rows),estimable=int(np.sum(rows['status']==0))))
            budget.check()
        projected=len(tasks)*float(np.mean(times)); conservative=len(tasks)*float(np.max(times))*1.5
        strata.append(dict(view_id=key[0],frequency=key[1],kind=key[2],track=key[3],chunks=len(tasks),
            benchmark_chunks=len(times),mean_seconds=float(np.mean(times)),max_seconds=float(np.max(times)),
            projected_seconds=projected,conservative_seconds=conservative))
        if len(strata)%10==0: print(json.dumps(dict(stage='benchmark',strata=len(strata),total_strata=len(groups))),flush=True)
    counts=c.read_json(c.PUBLIC/'search_counts.json'); rows=counts['pair_track_rows']; hypotheses=counts['method_hypotheses']
    result_bytes=rows*engine.RESULT_DTYPE.itemsize
    # SQLite checkpoints + merged array + BY sorting/work arrays + ten index
    # rankings, plus 1 GB for preparation/reports and SQLite page overhead.
    projected_bytes=2*result_bytes+hypotheses*40+rows*8*10+1_000_000_000
    used=budget.prior+time.perf_counter()-budget.start
    estimate=sum(t['projected_seconds'] for t in strata)
    upper=sum(t['conservative_seconds'] for t in strata)
    reserve=1800  # checkpoint I/O, stationarity, BY, ranking, reports and audits
    remaining=c.CONFIG['maximum_seconds']-used
    fits=upper+reserve<=remaining and projected_bytes<=c.CONFIG['maximum_bytes'] and projected_bytes<=budget.shutil.disk_usage(c.LOCAL).free-c.CONFIG['free_reserve_bytes']
    result=dict(status='WITHIN_BUDGET' if fits else 'APPROVAL_REQUIRED',full_campaign_started=False,
        counts=counts,benchmark_chunks=len(measurements),benchmark_strata=len(strata),
        projected_fit_seconds=estimate,conservative_fit_seconds=upper,postprocessing_reserve_seconds=reserve,
        cumulative_seconds_at_gate=used,projected_total_seconds=used+upper+reserve,
        projected_storage_bytes=projected_bytes,result_array_bytes=result_bytes,
        measured_peak_process_bytes=peak_memory(),projected_peak_process_bytes=max(peak_memory()*2,1_500_000_000),
        runtime_estimator='Sum by stratum: 1.5 times maximum of four deterministic cold-cache chunks; add 1800 seconds for remaining work. No outcome-based subsampling.',
        storage_estimator='Two complete result copies, forty bytes per method for BY work arrays, ten full 8-byte index rankings, plus one GB reserve.',
        protocol_hash=c.digest(c.CONFIG),compute_code_hashes={p.name:c.sha(p) for p in sorted((c.ROOT/'src').glob('pairwise_v5_*.py')) if not p.name.endswith('_report.py')})
    c.write_csv(c.PUBLIC/'benchmark_measurements.csv',measurements); c.write_csv(c.PUBLIC/'benchmark_strata.csv',strata)
    c.write_json(c.PUBLIC/'benchmark.json',result)
    return result


def verify_gate():
    gate=c.read_json(c.PUBLIC/'benchmark.json')
    if gate['status']!='WITHIN_BUDGET': raise c.ResourceLimit('Full campaign requires approval: benchmark exceeds limits')
    if gate['protocol_hash']!=c.digest(c.CONFIG): raise ValueError('Benchmark protocol no longer matches')
    hashes={p.name:c.sha(p) for p in sorted((c.ROOT/'src').glob('pairwise_v5_*.py')) if not p.name.endswith('_report.py')}
    if hashes!=gate['compute_code_hashes']: raise ValueError('Compute code changed after benchmark')
    return gate


def run(budget,stop_after=None):
    verify_gate(); fingerprint=c.freeze()
    if not (c.LOCAL/'stationarity.pkl').exists(): raise ValueError('Build stationarity diagnostics before full execution')
    workspace=engine.Workspace(); plan=c.load(c.LOCAL/'plan.pkl'); store=Store(c.LOCAL/'checkpoints.sqlite',fingerprint)
    completed=0; new=0; started=time.perf_counter()
    try:
        valid_ids={t['chunk_id'] for t in plan}
        if not {r[0] for r in store.db.execute('SELECT id FROM chunks')}<=valid_ids: raise ValueError('Unknown checkpoint IDs')
        for task in plan:
            existing=store.get(task['chunk_id'])
            if existing is None:
                rows,contrasts,seconds=measured_task(workspace,task)
                store.put(task['chunk_id'],rows,contrasts,seconds); new+=1
            elif len(existing[0])!=task['music_variables']: raise ValueError('Wrong checkpoint row count')
            completed+=1
            if completed%100==0:
                print(json.dumps(dict(stage='run',completed_chunks=completed,total_chunks=len(plan),new_chunks=new,
                    elapsed_seconds=time.perf_counter()-started,peak_process_bytes=peak_memory())),flush=True)
            budget.check()
            if stop_after is not None and new>=stop_after: break
    finally: store.close()
    state=dict(status='COMPLETE' if completed==len(plan) else 'CHECKPOINTED',completed_chunks=completed,total_chunks=len(plan),
        new_chunks=new,seconds=time.perf_counter()-started,peak_process_bytes=peak_memory(),fingerprint=fingerprint)
    c.write_json(c.PUBLIC/'execution.json',state); return state


def finalize(budget):
    fingerprint=c.freeze(); plan=c.load(c.LOCAL/'plan.pkl'); counts=c.read_json(c.PUBLIC/'search_counts.json')
    store=Store(c.LOCAL/'checkpoints.sqlite',fingerprint)
    expected={t['chunk_id'] for t in plan}; actual={r[0] for r in store.db.execute('SELECT id FROM chunks')}
    if actual!=expected: store.close(); raise ValueError('Full candidate coverage is required before global BY')
    temporary=c.LOCAL/'results.tmp.npy'; final=c.LOCAL/'results.npy'
    result=np.lib.format.open_memmap(temporary,mode='w+',dtype=engine.RESULT_DTYPE,shape=(counts['pair_track_rows'],))
    p=np.ones(counts['method_hypotheses'],dtype=float); cursor=0; cat=[]
    for task in plan:
        rows,contrasts=store.get(task['chunk_id']); a=task['offset']; b=a+len(rows); result[a:b]=rows
        permitted=(rows['status']==0)&(rows['inferential']==1)&np.isfinite(rows['p'])
        primary=np.where(permitted,rows['p'],1.); p[cursor:cursor+len(rows)]=primary; cursor+=len(rows)
        if task['external_kind']!='categorical':
            p[cursor:cursor+len(rows)]=np.where(permitted & np.isfinite(rows['p_rank']),rows['p_rank'],1.); cursor+=len(rows)
        if contrasts: cat.extend(dict(chunk_id=task['chunk_id'],**row) for row in contrasts)
        if task['chunk_id']%100==0: budget.check()
    store.close()
    if cursor!=len(p): raise ValueError('Global hypothesis denominator mismatch')
    print(json.dumps(dict(stage='global_BY',hypotheses=len(p))),flush=True)
    q=engine.by_adjust(p); cursor=0
    for task in plan:
        a=task['offset']; b=a+task['music_variables']; n=b-a
        result['q'][a:b]=q[cursor:cursor+n]; cursor+=n
        if task['external_kind']!='categorical': result['q_rank'][a:b]=q[cursor:cursor+n]; cursor+=n
    result.flush(); del result; temporary.replace(final)
    c.write_csv(c.LOCAL/'categorical_contrasts.csv',cat)
    value=dict(status='COMPLETE',global_hypotheses=len(p),method_rejections=int(np.sum(q<=.05)),
        inferential_p_below_05=int(np.sum(p<=.05)),invalid_slots_set_to_one=int(np.sum(p==1)),
        result_rows=counts['pair_track_rows'],result_sha256=c.sha(final),peak_process_bytes=peak_memory())
    c.write_json(c.PUBLIC/'multiple_testing_summary.json',value); budget.check(True); return value


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['benchmark','run','finalize']); parser.add_argument('--stop-after',type=int)
    args=parser.parse_args(); budget=c.Budget(args.action)
    try:
        value=benchmark(budget) if args.action=='benchmark' else run(budget,args.stop_after) if args.action=='run' else finalize(budget)
        print(json.dumps(c.clean(value),indent=2),flush=True)
    finally: budget.close()


if __name__=='__main__': main()
