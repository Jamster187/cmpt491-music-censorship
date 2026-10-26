"""Bounded benchmark, exhaustive rolling validation, selection lock, evaluation."""
import os
for _key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[_key]='1'
import argparse
import gc
import json
from pathlib import Path
import resource
import shutil
import tempfile
import time
import numpy as np
import regression_expanded_spec as spec
import regression_expanded_core as core
from regression_expanded_store import Store


def open_store(task,provenance=None):
    return Store(spec.LOCAL/(task['task_id']+'.sqlite'),dict(task=task,provenance=provenance or spec.provenance()),spec.candidates(task['track']),spec.predictors(task['track']))


def disk_guard():
    if shutil.disk_usage(spec.ROOT).free<spec.CONFIG['minimum_disk_headroom_bytes']:raise RuntimeError('Checkpoint retained: disk headroom below frozen 3 GiB bound')


def fit_remaining(store,fold,number,candidates,stop_after=None):
    done=store.completed(number);pending=[r for r in candidates if r[0] not in done];start=time.perf_counter()
    for offset in range(0,len(pending),spec.CONFIG['batch_size']):
        batch=pending[offset:offset+spec.CONFIG['batch_size']];combos=[c for _,c in batch]
        result,timing=fold.evaluate(combos)
        training=None
        if number==3:
            t=time.perf_counter();beta,_,_=fold.fit_batch(combos);training=core.training_r2(fold,beta);timing['training_metric_seconds']=time.perf_counter()-t
        store.save(number,batch,result,fold.metadata,timing,training)
        if offset%16384==0:disk_guard()
        if stop_after is not None and offset+len(batch)>=stop_after:break
    return time.perf_counter()-start


def benchmark():
    start=time.perf_counter();provenance=spec.provenance();rng=np.random.default_rng(spec.SEED);rows=[];checks=[]
    # Outcome-blind uniform samples within original-variable count and categorical presence.
    # Every validation period is measured; no evaluation target is touched.
    for track in spec.CONFIG['tracks']:
        catalog=spec.candidates(track);strata={}
        for row in catalog:
            combo=row[1];key=(len(combo),any(spec.REGISTRY[n]['kind'] in ['categorical','multilabel','numeric_block'] for n in combo))
            strata.setdefault(key,[]).append(row)
        sample=[]
        for key,items in sorted(strata.items()):
            selected=sorted(rng.choice(len(items),size=min(96,len(items)),replace=False));sample.extend(items[i] for i in selected)
        sample.sort()
        for horizon in ['26','observed_lifetime']:
            task=dict(task_id=f'benchmark__{track}__{horizon}',track=track,horizon=horizon,target='chart_points')
            for number,(a,b) in enumerate(spec.FOLDS):
                prepare_start=time.perf_counter();fold=core.prepare(task,a,b);prepare_seconds=time.perf_counter()-prepare_start
                with tempfile.TemporaryDirectory(dir=spec.LOCAL) as directory:
                    store=Store(Path(directory)/'sample.sqlite',dict(provenance=provenance,task=task,fold=number),sample,spec.predictors(track))
                    seconds=fit_remaining(store,fold,number,sample)
                    rows.append(dict(track=track,horizon=horizon,fold=number,sampled=len(sample),catalog=len(catalog),seconds=seconds,prepare_seconds=prepare_seconds,n_train=len(fold.y),n_validation=len(fold.z),encoded_width=fold.X.shape[1],projected_validation_seconds=seconds*len(catalog)/len(sample)))
                    store.close()
                for combo in [sample[0][1],sample[-1][1],tuple(n for n in ['debut_rank','debut_reported_peak_position','primary_genre'] if n in spec.predictors(track))]:
                    checks.append(dict(track=track,horizon=horizon,fold=number,**core.independent_reference(fold,combo)))
                print(json.dumps(rows[-1]),flush=True);del fold;gc.collect()
    # Evaluation on at most ~1.65x validation rows; extra training-R2 solve/metric and storage overhead.
    projected=sum(r['projected_validation_seconds'] for r in rows)*3
    estimate=projected*(1+2/3)*2+sum(r['prepare_seconds'] for r in rows)*4+180
    report=dict(status='WITHIN_BUDGET' if estimate<=spec.CONFIG['full_launch_budget_seconds'] else 'CHECKPOINT_BUDGET_EXCEEDED',rows=rows,independent_svd_checks=checks,
        projected_validation_seconds=projected,conservative_total_seconds=estimate,budget_seconds=spec.CONFIG['full_launch_budget_seconds'],
        projection='3 targets per measured track/horizon; evaluation allowance 2/3 validation runtime; 2x compute contingency plus loading/cache and 180s reporting allowance',
        elapsed_seconds=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,free_disk_bytes=shutil.disk_usage(spec.ROOT).free,provenance=provenance)
    spec.write_json(spec.PUBLIC/'benchmark.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['rows','independent_svd_checks','provenance']},indent=2),flush=True)


def lock_selections(provenance):
    selections=[]
    for task in spec.tasks():
        store=open_store(task,provenance)
        if not store.complete():raise ValueError('All validation tasks must finish before selection lock')
        ranked=store.rankings()
        for config,mask in [('original',1),('new',2),('combined',None)]:
            subset=ranked if mask is None else ranked[ranked['mask'].eq(mask)]
            for k in [0,1,2,3]:
                r=(subset if k==0 else subset[subset.k.eq(k)]).iloc[0]
                selections.append(dict(**task,configuration=config,selection_count='best_any_k' if k==0 else k,candidate_id=int(r.id),predictors=store.combo(r),validation_skill=float(r.validation_skill),validation_r2=float(r.validation_r2),validation_mae=float(r.validation_mae),validation_rmse=float(r.validation_mse)**.5))
        store.close()
    lock=dict(provenance=provenance,rule=spec.CONFIG['selection'],selections=selections)
    path=spec.PUBLIC/'selection_lock.json'
    if path.exists() and spec.read_json(path)!=spec.clean(lock):raise ValueError('Selection lock changed')
    if not path.exists():spec.write_json(path,lock)
    return spec.sha(path)


def run():
    started=time.perf_counter();provenance=spec.provenance();report=spec.read_json(spec.PUBLIC/'benchmark.json')
    if report['provenance']!=spec.clean(provenance):raise ValueError('Benchmark provenance changed')
    if report['status']!='WITHIN_BUDGET':raise RuntimeError('Full run exceeds frozen bounded runtime; checkpoint/report before launch')
    disk_guard()
    for task in spec.tasks():
        store=open_store(task,provenance);catalog=spec.candidates(task['track'])
        for number,(start,end) in enumerate(spec.FOLDS):
            if len(store.completed(number))==len(catalog):continue
            fold=core.prepare(task,start,end);seconds=fit_remaining(store,fold,number,catalog)
            print(json.dumps(dict(stage='validation',task=task['task_id'],fold=number,candidates=len(catalog),seconds=seconds)),flush=True);del fold;gc.collect()
        store.close()
    selection_hash=lock_selections(provenance);print('ALL VALIDATION SELECTIONS LOCKED '+selection_hash,flush=True)
    for task in spec.tasks():
        store=open_store(task,provenance);catalog=spec.candidates(task['track'])
        if len(store.completed(3))<len(catalog):
            fold=core.prepare(task,'2018-01-01',None);seconds=fit_remaining(store,fold,3,catalog)
            print(json.dumps(dict(stage='evaluation',task=task['task_id'],candidates=len(catalog),seconds=seconds)),flush=True);del fold;gc.collect()
        with store.db:store.put('selection_sha256',selection_hash)
        store.close()
    if selection_hash!=spec.sha(spec.PUBLIC/'selection_lock.json'):raise ValueError('Evaluation changed selection lock')
    record=dict(status='COMPLETE',elapsed_seconds_this_invocation=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        free_disk_bytes=shutil.disk_usage(spec.ROOT).free,selection_sha256=selection_hash,provenance=provenance)
    spec.write_json(spec.PUBLIC/'execution.json',record);print(json.dumps({k:v for k,v in record.items() if k!='provenance'},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['benchmark','run']);a=p.parse_args()
    spec.LOCAL.mkdir(parents=True,exist_ok=True)
    benchmark() if a.action=='benchmark' else run()
