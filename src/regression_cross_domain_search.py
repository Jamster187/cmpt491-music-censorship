"""Budgeted exhaustive V3 search with frozen validation selections before evaluation."""
import os
for _key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[_key]='1'
import argparse
import gc
import hashlib
import json
from pathlib import Path
import resource
import shutil
import tempfile
import time
import numpy as np
import pandas as pd
import regression_cross_domain_spec as spec
import regression_cross_domain_core as core
from regression_cross_domain_store import Store


def disk_guard():
    if shutil.disk_usage(spec.ROOT).free<spec.CONFIG['minimum_disk_headroom_bytes']:raise RuntimeError('Checkpoint preserved: disk headroom below 2 GiB')


def score_chunk(fold,ids):
    values=np.empty((len(ids),2),float);status=np.empty(len(ids),np.uint16);timing={}
    for start in range(0,len(ids),spec.CONFIG['batch_size']):
        batch=ids[start:start+spec.CONFIG['batch_size']];result,seconds=core.evaluate(fold,[spec.combo(int(i)) for i in batch])
        values[start:start+len(batch),0]=result['mse'];values[start:start+len(batch),1]=result['mae']
        status[start:start+len(batch)]=result['rank'].astype(np.uint16)|(result['fallback'].astype(np.uint16)<<15)
        for key,v in seconds.items():timing[key]=timing.get(key,0)+v
    return values,status,timing


def fit_fold(store,fold,number,deadline=None,stop_after_chunks=None):
    done=store.completed(number);chunks=0;started=time.perf_counter();last_notice=started
    for start in range(0,store.n,spec.CONFIG['checkpoint_rows']):
        if start in done:continue
        if deadline is not None and time.perf_counter()>deadline:raise RuntimeError('Four-hour runtime bound reached; committed chunks preserved for explicit approval')
        disk_guard();stop=min(start+spec.CONFIG['checkpoint_rows'],store.n);t=time.perf_counter()
        values,status,timing=score_chunk(fold,store.ids[start:stop]);store.save(number,start,values,status,fold.metadata,timing);chunks+=1
        if time.perf_counter()-last_notice>45:
            print(json.dumps(dict(stage='progress',target=store.target,fold=number,rows=stop,total=store.n)),flush=True);last_notice=time.perf_counter()
        if stop_after_chunks is not None and chunks>=stop_after_chunks:break
    return time.perf_counter()-started


def benchmark():
    started=time.perf_counter();provenance=spec.provenance();rng=np.random.default_rng(spec.SEED);records=[];checks=[]
    catalog=spec.catalog();k=(catalog!=255).sum(axis=1);special=np.zeros(256,bool)
    for i,n in enumerate(spec.NAMES):special[i]=spec.REGISTRY[n]['kind']!='numeric'
    categorical=special[catalog].any(axis=1);cohorts=pd.read_csv(spec.PUBLIC/'cohorts.csv');total_validation=0.;total_evaluation=0.;setup_total=0.;write_overhead=0.
    targets=spec.targets()
    for index,target in enumerate(targets):
        cats,_=spec.relations(target);strata=[];sample=[]
        for count in [1,2,3]:
            for block in [False,True]:
                pool=np.flatnonzero((cats>1)&(k==count)&(categorical==block))
                if not len(pool):continue
                chosen=np.sort(rng.choice(pool,size=min(256,len(pool)),replace=False)).astype(np.uint32);strata.append((count,block,pool,chosen));sample.extend(chosen.tolist())
        sample=sorted(sample);position={c:i for i,c in enumerate(sample)}
        with tempfile.TemporaryDirectory(dir=spec.LOCAL) as directory:
            store=Store(target,provenance,base=directory,sample_ids=sample)
            for number,(a,b) in enumerate(spec.FOLDS):
                t=time.perf_counter();fold=core.prepare(target,a,b);setup=time.perf_counter()-t;setup_total+=setup
                values=np.empty((len(sample),2));status=np.empty(len(sample),np.uint16);timing_total={};projected=0.;eval_projection=0.
                neval=int(cohorts[cohorts.target.eq(target)&cohorts.fold.eq(3)].n_validation.iloc[0])
                for count,block,pool,chosen in strata:
                    t=time.perf_counter();val,stat,timing=score_chunk(fold,chosen);elapsed=time.perf_counter()-t;indices=[position[int(i)] for i in chosen];values[indices]=val;status[indices]=stat
                    ratio=len(pool)/len(chosen);estimate=elapsed*ratio;projected+=estimate
                    # Benchmark only validation outcomes; evaluation population size is known from audit.
                    estimate_eval=(timing['fit_seconds']+timing['metrics_seconds']*neval/len(fold.z)+max(0.,elapsed-timing['fit_seconds']-timing['metrics_seconds']))*ratio
                    eval_projection+=estimate_eval
                    for key,v in timing.items():timing_total[key]=timing_total.get(key,0)+v
                    records.append(dict(target=target,fold=number,k=count,categorical_block=block,candidates=len(pool),sampled=len(chosen),seconds=elapsed,projected_seconds=estimate,n_train=len(fold.y),n_validation=len(fold.z),encoded_columns=fold.X.shape[1]))
                t=time.perf_counter();store.save(number,0,values,status,fold.metadata,timing_total);write_overhead+=(time.perf_counter()-t)*max(1,math_ceil_valid(cats)/spec.CONFIG['checkpoint_rows'])
                total_validation+=projected;total_evaluation+=eval_projection/3
                # Full-row independent SVD and dense-versus-sparse metric verification.
                for candidate in [sample[0],sample[-1]]:
                    combo=spec.combo(candidate);check=fold.reference_check(combo);checks.append(dict(target=target,fold=number,**check))
                    dense,_=fold.evaluate([combo]);sparse,_=core.evaluate(fold,[combo])
                    for key in ['mae','mse','r2','skill']:np.testing.assert_allclose(dense[key],sparse[key],rtol=2e-9,atol=2e-9)
                del fold;gc.collect()
            store.order();store.close()
        print(json.dumps(dict(stage='benchmark',target=target,index=index+1,total=len(targets),projected_validation_seconds_so_far=total_validation)),flush=True)
    audit=spec.read_json(spec.PUBLIC/'audit.json');n=audit['valid_task_candidate_pairs'];nt=len(targets);nc=len(catalog)
    # Exact dense-array payload plus complete categorical audits, sorted order and IDs;
    # generous fixed allowance for manifests, selected predictions, models and plots.
    storage_exact=n*(72+4+4)+nt*nc*3+nc*3
    projected_storage=int(storage_exact*1.15+500_000_000)
    projected_seconds=1.5*(total_validation+total_evaluation+setup_total*4/3+write_overhead*4/3)+900
    free=shutil.disk_usage(spec.ROOT).free
    allowed=projected_seconds<=spec.CONFIG['runtime_limit_seconds'] and projected_storage<=spec.CONFIG['temporary_storage_limit_bytes'] and projected_storage+spec.CONFIG['minimum_disk_headroom_bytes']<=free
    report=dict(status='WITHIN_BUDGET' if allowed else 'APPROVAL_REQUIRED',targets=len(targets),benchmark_candidate_fits=sum(r['sampled'] for r in records),validation_outcomes_only=True,
        projected_validation_seconds=total_validation,projected_evaluation_seconds=total_evaluation,projected_checkpoint_write_seconds=write_overhead*4/3,
        conservative_total_seconds=projected_seconds,runtime_limit_seconds=spec.CONFIG['runtime_limit_seconds'],projection_rule='Stratum-weighted measured fit/metric costs for every target and validation period; evaluation cost scaled by audited row counts; 1.5x compute/I-O contingency plus 900s reporting/validation allowance',
        exact_core_storage_bytes=storage_exact,projected_temporary_storage_bytes=projected_storage,storage_limit_bytes=spec.CONFIG['temporary_storage_limit_bytes'],free_disk_bytes=free,
        elapsed_seconds=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,independent_svd_checks=checks,provenance=provenance)
    spec.write_csv(spec.PUBLIC/'benchmark_strata.csv',records);spec.write_json(spec.PUBLIC/'benchmark.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['independent_svd_checks','provenance']},indent=2),flush=True)


def math_ceil_valid(categories):return int((categories>1).sum())


def row_summary(store,scores,pos,view,configuration,k):
    cid=int(store.ids[pos]);combo=spec.combo(cid)
    return dict(target=store.target,view=view,configuration=configuration,selection_count='best_any_k' if k==0 else k,candidate_id=cid,row_index=int(pos),predictors=list(combo),category_code=int(store.categories[pos]),category=spec.CATEGORIES[int(store.categories[pos])],
        validation_r2=float(scores['validation_r2'][pos]),validation_mae=float(scores['validation_mae'][pos]),validation_rmse=float(scores['validation_rmse'][pos]),validation_skill=float(scores['validation_skill'][pos]),worst_period_r2=float(scores['worst_period_r2'][pos]))


def lock_selections(provenance):
    selected=[];global_rows={v:[] for v in spec.VIEWS};coverage=[]
    for target in spec.targets():
        store=Store(target,provenance)
        if not store.complete():raise ValueError('All validation must complete before selection lock')
        scores=store.scores();order=store.order()
        for view in spec.VIEWS:
            for config in spec.CONFIG['configurations']:
                for k in [0,1,2,3]:
                    chosen=order[store.subset(view,config,k if k else None)[order]]
                    if len(chosen):selected.append(row_summary(store,scores,int(chosen[0]),view,config,k))
                    else:selected.append(dict(target=target,view=view,configuration=config,selection_count='best_any_k' if k==0 else k,status='NO_ELIGIBLE_COMBINATIONS'))
                if config=='combined':
                    chosen=order[store.subset(view,config)[order]][:100]
                    global_rows[view].extend(row_summary(store,scores,int(pos),view,config,0) for pos in chosen)
        coverage.append(dict(target=target,candidates=store.n,validation_fits=3*store.n,validation_order_sha256=spec.sha(store.path/'validation_order.npy')));store.close()
    top={view:sorted(rows,key=lambda r:(-r['validation_r2'],len(r['predictors']),r['target'],r['predictors']))[:100] for view,rows in global_rows.items()}
    lock=dict(provenance=provenance,rule=spec.CONFIG['selection'],selections=selected,global_top100_by_validation=top,coverage=coverage)
    path=spec.PUBLIC/'selection_lock.json'
    if path.exists() and spec.read_json(path)!=spec.clean(lock):raise ValueError('Validation selection lock changed')
    if not path.exists():spec.write_json(path,lock)
    return spec.sha(path)


def run():
    started=time.perf_counter();provenance=spec.provenance();benchmark=spec.read_json(spec.PUBLIC/'benchmark.json')
    if benchmark['provenance']!=spec.clean(provenance):raise ValueError('Benchmark no longer matches numerical code/protocol')
    if benchmark['status']!='WITHIN_BUDGET':raise RuntimeError('User budget exceeded: checkpoint and seek approval before full launch')
    if shutil.disk_usage(spec.ROOT).free<benchmark['projected_temporary_storage_bytes']+spec.CONFIG['minimum_disk_headroom_bytes']:raise RuntimeError('Insufficient free disk for projected search plus headroom')
    deadline=started+spec.CONFIG['runtime_limit_seconds'];targets=spec.targets()
    for index,target in enumerate(targets):
        store=Store(target,provenance)
        for fold,(a,b) in enumerate(spec.FOLDS):
            if store.complete([fold]):continue
            data=core.prepare(target,a,b);seconds=fit_fold(store,data,fold,deadline);del data;gc.collect()
            print(json.dumps(dict(stage='validation',target=target,index=index+1,total=len(targets),fold=fold,candidates=store.n,seconds=seconds)),flush=True)
        store.close()
    selection_hash=lock_selections(provenance);print('ALL VALIDATION SELECTIONS LOCKED '+selection_hash,flush=True)
    for index,target in enumerate(targets):
        store=Store(target,provenance)
        if not store.complete([3]):
            data=core.prepare(target,'2018-01-01',None);seconds=fit_fold(store,data,3,deadline);del data;gc.collect()
            print(json.dumps(dict(stage='evaluation',target=target,index=index+1,total=len(targets),candidates=store.n,seconds=seconds)),flush=True)
        with store.db:store.put('selection_sha256',selection_hash)
        store.close()
    if spec.sha(spec.PUBLIC/'selection_lock.json')!=selection_hash:raise ValueError('Evaluation changed frozen selections')
    summary=dict(status='COMPLETE',elapsed_seconds_this_invocation=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        targets=len(targets),candidates=spec.read_json(spec.PUBLIC/'audit.json')['valid_task_candidate_pairs'],candidate_fits=spec.read_json(spec.PUBLIC/'audit.json')['total_fits'],selection_sha256=selection_hash,provenance=provenance)
    spec.write_json(spec.PUBLIC/'execution.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='provenance'},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['benchmark','run']);args=p.parse_args();spec.LOCAL.mkdir(parents=True,exist_ok=True)
    benchmark() if args.action=='benchmark' else run()
