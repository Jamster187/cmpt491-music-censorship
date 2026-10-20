"""Auditable bounded discovery pilot. Deliberately has no full-campaign runner."""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
import sklearn
import scipy

import regression_search as original
import regression_spec as old
from regression_store import clean
import relationship_discovery_spec as spec
import relationship_discovery_stats as stats
import relationship_discovery_models as models

_FRAME=None
_MASKS=None


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(clean(value),indent=2,sort_keys=True,allow_nan=False)+'\n')
    os.replace(temp,path)


def read_json(path):return json.loads(Path(path).read_text())


def write_csv(path,rows):
    rows=list(rows)
    if not rows:raise ValueError('Refusing to publish an empty placeholder table: '+str(path))
    fields=sorted(set().union(*(r.keys() for r in rows)))
    original.write_csv(path,({k:r.get(k) for k in fields} for r in rows))


def data():
    raw=original.read_table('songs')
    if raw.song_id.duplicated().any():raise ValueError('Repeated song identities in song table')
    f=old.original.convert(raw)
    f['first_iso']=raw.first_chart_date;f['last_iso']=raw.last_chart_date
    f['debut_year']=pd.to_datetime(raw.first_chart_date).dt.year.astype(int)
    parsed=raw.secondary_genres.map(lambda v:json.loads(v) if pd.notna(v) else None)
    for genre in spec.GENRES:
        f['secondary_genre::'+genre]=parsed.map(lambda v:float(genre in v) if v is not None else np.nan)
    f['_hash']=pd.util.hash_pandas_object(f.song_id,index=False).to_numpy()
    return f.sort_values('song_id',kind='stable').reset_index(drop=True)


def peak_rss_bytes():
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform=='darwin' else value*1024)


def preserve(initialize=False):
    snapshot=spec.LOCAL/'original_files.json'
    if not snapshot.exists():
        if not initialize:raise ValueError('Original preservation snapshot missing')
        names=subprocess.check_output(['git','ls-tree','-r','--name-only',spec.SOURCE_COMMIT,
            'data','analysis','src','tests','README.md','requirements.txt','requirements-demo.txt'],cwd=spec.ROOT,text=True).splitlines()
        files={n:old.original.sha(spec.ROOT/n) for n in names if (spec.ROOT/n).is_file()}
        for folder in [original.LOCAL/'campaign',original.LOCAL/'meaningful_v1']:
            files.update({str(p.relative_to(spec.ROOT)):old.original.sha(p) for p in folder.rglob('*') if p.is_file()})
        write_json(snapshot,dict(source_commit=spec.SOURCE_COMMIT,sha256=files))
    saved=read_json(snapshot)
    for name,h in saved['sha256'].items():
        if not (spec.ROOT/name).is_file() or old.original.sha(spec.ROOT/name)!=h:raise ValueError('Original artifact changed: '+name)
    return dict(status='PASS',protected_files=len(saved['sha256']),snapshot_sha256=old.original.sha(snapshot))


def identity():
    return dict(configuration=spec.configuration(),data_sha256=old.original.sha(spec.ROOT/old.FILES['songs']),
        code_sha256={p:old.original.sha(spec.ROOT/p) for p in [*spec.CODE,'src/regression_core.py','src/regression_relationships.py','src/regression_spec.py',
            'analysis/planning/regression_search/audit.py']},versions=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__),
        pilot_candidates=spec.pilot_candidates())


def audit():
    before=preserve(True);started=time.perf_counter();configuration=identity()
    lock=spec.PUBLIC/'pilot_protocol.json'
    if lock.exists():
        saved=read_json(lock)
        if saved['identity']!=clean(configuration):raise ValueError('Pilot protocol/code/data changed; use an explicit new version, never silently revise after results')
    else:write_json(lock,dict(locked_utc=datetime.now(timezone.utc).isoformat(),identity=configuration,
        new_pilot_results_at_lock=0,full_campaign_approved=False))
    space=spec.search_space()
    space['planned_primary_pilot_tests']=sum(v for k,v in space['pilot_counts'].items() if k not in {'temporal','structure'})
    space['total_proposed_predictive_model_fits_upper_bound']=sum(space[k].get('fit_upper_bound',space[k].get('nested_fit_upper_bound',0)) for k in ['nonlinear','genre_interaction','numeric_interaction','threshold_interaction'])
    space['total_proposed_primary_inferential_hypotheses']=space['pairwise']['candidates']+sum(space[k]['candidates'] for k in ['nonlinear','genre_interaction','numeric_interaction','threshold_interaction'])
    space['preservation']=before;space['enumeration_seconds']=time.perf_counter()-started
    write_json(spec.PUBLIC/'search_space.json',space)
    write_csv(spec.PUBLIC/'variable_inventory.csv',[dict(variable=n,kind=spec.kind(n),domain=spec.domain(n),
        availability=old.original.availability(spec.canonical(n)),role='association and ordered dependence only' if n in spec.ORDERED else 'nominal labels or membership flags' if n in spec.CATEGORICAL else 'numerical target/predictor') for n in spec.VARIABLES])
    write_csv(spec.PUBLIC/'pilot_candidates.csv',spec.pilot_candidates())
    return space


def initializer():
    global _FRAME,_MASKS
    _FRAME=data();_MASKS=models.make_splits(_FRAME)


def execute(row):
    global _FRAME,_MASKS
    if _FRAME is None:initializer()
    started=time.perf_counter()
    with threadpool_limits(limits=1):
        closed=_FRAME.loc[_FRAME.last_iso.lt('2026-01-01')]
        if row['family']=='pairwise':result=stats.pair_analysis(closed,row)
        elif row['family']=='temporal':result=models.temporal_analysis(closed,row)
        elif row['family']=='structure':result=models.structure_analysis(_FRAME,_MASKS,row)
        else:result=models.predictive_analysis(_FRAME,_MASKS,row)
    result['wall_seconds']=time.perf_counter()-started;result['peak_rss_bytes']=peak_rss_bytes()
    result['evaluation_label']='EXPLORATORY PILOT; previously inspected population'
    return clean(result)


def cache_path(row):return spec.LOCAL/'checkpoints'/(row['candidate_id']+'.json')


def logical(result):
    if isinstance(result,dict):return {k:logical(v) for k,v in result.items() if k not in {'wall_seconds','peak_rss_bytes','timings'}}
    if isinstance(result,list):return [logical(v) for v in result]
    return result


def load_results():
    lock=read_json(spec.PUBLIC/'pilot_protocol.json');fingerprint=old.digest(lock['identity']);rows=[]
    for candidate in spec.pilot_candidates():
        saved=read_json(cache_path(candidate))
        if saved['protocol_sha256']!=fingerprint:raise ValueError('Checkpoint protocol mismatch')
        if saved['logical_sha256']!=old.digest(logical(saved['result'])):raise ValueError('Checkpoint result corrupted')
        rows.append(saved['result'])
    return stats.adjust_multiple_testing(rows)


def pilot(workers=1):
    audit();lock=read_json(spec.PUBLIC/'pilot_protocol.json');fingerprint=old.digest(lock['identity'])
    candidates=spec.pilot_candidates()
    if len(candidates)>200:raise ValueError('Hard pilot cap exceeded; full campaign is not authorized')
    pending=[]
    for row in candidates:
        if cache_path(row).exists():
            saved=read_json(cache_path(row))
            if saved['protocol_sha256']!=fingerprint or saved['logical_sha256']!=old.digest(logical(saved['result'])):
                raise ValueError('Checkpoint identity/integrity mismatch')
        else:pending.append(row)
    started=time.perf_counter();print(f'Bounded pilot: {len(candidates)} candidates, {len(pending)} pending; workers={workers}',flush=True)
    def save(result):
        write_json(cache_path(result),dict(protocol_sha256=fingerprint,result=result,logical_sha256=old.digest(logical(result))))
        print(result['family'],result['candidate_id'],result['status'],round(result['wall_seconds'],3),'s',flush=True)
    if workers==1:
        for row in pending:save(execute(row))
    else:
        with ProcessPoolExecutor(max_workers=workers,initializer=initializer) as pool:
            for result in pool.map(execute,pending):save(result)
    results=load_results()
    write_json(spec.PUBLIC/'pilot_results/results.json',results)
    write_json(spec.PUBLIC/'pilot_results/run_audit.json',dict(status='PASS',candidates=len(candidates),
        newly_computed=len(pending),resumed=len(candidates)-len(pending),wall_seconds=time.perf_counter()-started,
        total_candidate_seconds=sum(r['wall_seconds'] for r in results),workers=workers,
        maximum_process_rss_bytes=max(r['peak_rss_bytes'] for r in results),
        fit_count=sum(r.get('fit_count',0) for r in results),protocol_sha256=fingerprint,
        logical_results_sha256=old.digest(logical(results)),original_preservation=preserve(),full_campaign_launched=False))
    return results


def benchmark():
    """Repeated fixed tiny workload, including startup; never a candidate screen."""
    audit();candidates=[r for r in spec.pilot_candidates() if r['family']=='nonlinear'][:4]
    runs=[]
    for workers in (1,2):
        started=time.perf_counter()
        if workers==1:results=[execute(r) for r in candidates]
        else:
            with ProcessPoolExecutor(max_workers=workers,initializer=initializer) as pool:results=list(pool.map(execute,candidates))
        runs.append(dict(workers=workers,wall_seconds=time.perf_counter()-started,candidates=len(candidates),
            fits=sum(r['fit_count'] for r in results),max_worker_rss_bytes=max(r['peak_rss_bytes'] for r in results),
            logical_sha256=old.digest(logical(results))))
    if runs[0]['logical_sha256']!=runs[1]['logical_sha256']:raise ValueError('Parallel benchmark changed measured results')
    write_json(spec.PUBLIC/'benchmark_results/parallel.json',dict(runs=runs,speedup=runs[0]['wall_seconds']/runs[1]['wall_seconds'],
        warning='Four candidate microbenchmark; process startup included; no extrapolated speedup guarantee',logical_equality=True))
    return runs


def verify():
    started=time.perf_counter();rows=load_results();frame=data();splits=models.make_splits(frame)
    protocol=read_json(spec.PUBLIC/'pilot_protocol.json')
    if protocol['identity']!=clean(identity()):raise ValueError('Published protocol no longer matches code/data')
    ids=[r['candidate_id'] for r in rows]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate candidates')
    split_proofs=[]
    for (a,b),(tr,va) in sorted(splits.items()):
        if set(frame.loc[tr,'song_id'])&set(frame.loc[va,'song_id']):raise ValueError('Repeated-song leakage')
        if not frame.loc[tr,'last_iso'].lt(f'{a}-01-01').all():raise ValueError('Training label window reaches evaluation')
        if not frame.loc[va,'last_iso'].lt(f'{b}-01-01').all():raise ValueError('Evaluation label window extends beyond evaluation')
        split_proofs.append(dict(period=[a,b],train=int(tr.sum()),evaluation=int(va.sum()),disjoint=True))
    primary=[r for r in rows if 'q_by_global' in r]
    p=[r.get('p_value') if r.get('p_value') is not None else 1. for r in primary]
    expected=scipy.stats.false_discovery_control(p,method='by')
    np.testing.assert_allclose(expected,[r['q_by_global'] for r in primary],rtol=0,atol=0)
    for r in rows:
        if r['evaluation_label']!='EXPLORATORY PILOT; previously inspected population':raise ValueError('Exploratory label missing')
        for group in r.get('subgroup_results',[]):
            if group['adequate'] and (group['n']<100 or group['years']<5):raise ValueError('Insufficient subgroup published')
    result=dict(status='PASS',candidates=len(rows),primary_hypotheses=len(primary),split_checks=split_proofs,
        deterministic_candidate_ids=True,multiple_testing_recomputed=True,original_preservation=preserve(),
        data_sha256=protocol['identity']['data_sha256'],logical_results_sha256=old.digest(logical(rows)),elapsed_seconds=time.perf_counter()-started)
    write_json(spec.PUBLIC/'pilot_results/validation.json',result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['audit','pilot','benchmark','verify','verify-originals'])
    p.add_argument('--workers',type=int,choices=[1,2],default=1)
    args=p.parse_args()
    if args.command=='audit':result=audit()
    elif args.command=='pilot':result=pilot(args.workers);result={'completed':len(result)}
    elif args.command=='benchmark':result=benchmark()
    elif args.command=='verify':result=verify()
    else:result=preserve()
    print(json.dumps(clean(result),indent=2),flush=True)


if __name__=='__main__':main()
