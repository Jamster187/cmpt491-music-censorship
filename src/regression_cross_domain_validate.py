"""Independent V3 coverage, chronology, prediction, preservation and replay audits."""
import os
for _key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[_key]='1'
import argparse
import gc
import json
import re
import resource
import time
import numpy as np
import pandas as pd
import regression_cross_domain_spec as spec
import regression_cross_domain_core as core
from regression_cross_domain_store import Store
from regression_cross_domain_search import lock_selections


def reproducible_files():
    excluded={'benchmark.json','execution.json','report_execution.json','validation.json','determinism.json','publication_manifest.json'}
    files={str(p.relative_to(spec.ROOT)):spec.sha(p) for p in spec.PUBLIC.rglob('*') if p.is_file() and p.name not in excluded}
    files['docs/regression_cross_domain_v3.md']=spec.sha(spec.ROOT/'docs/regression_cross_domain_v3.md')
    for r in spec.read_json(spec.PUBLIC/'local_artifacts.json'):files[r['path']]=spec.sha(spec.ROOT/r['path'])
    return files


def determinism(action):
    path=spec.LOCAL/'determinism_snapshot.json';actual=reproducible_files()
    if action=='snapshot':spec.write_json(path,actual);return
    expected=spec.read_json(path)
    if actual!=expected:raise ValueError('Regeneration differs: '+repr([n for n in set(actual)|set(expected) if actual.get(n)!=expected.get(n)]))
    result=dict(status='PASS',files=len(actual),snapshot_sha256=spec.sha(path),method='Full report regeneration: all selected numerical summaries, models, predictions, seeded cluster intervals, findings and SVG figures are byte-identical; all complete numerical arrays remain identical')
    spec.write_json(spec.PUBLIC/'determinism.json',result);print(json.dumps(result,indent=2),flush=True)


def validate(preserve=True):
    started=time.perf_counter();logpath=spec.LOCAL/'tests.log';log=logpath.read_text();match=re.search(r'Ran (\d+) tests',log);skip=re.search(r'OK \(skipped=(\d+)\)',log)
    if match is None or not re.search(r'^OK(?: \(skipped=\d+\))?$',log,re.M):raise ValueError('Successful full test log required')
    totaltests=int(match.group(1));skipped=int(skip.group(1)) if skip else 0
    provenance=spec.provenance();lock=spec.read_json(spec.PUBLIC/'selection_lock.json');lockhash=spec.sha(spec.PUBLIC/'selection_lock.json');audit=spec.read_json(spec.PUBLIC/'audit.json')
    if lock_selections(provenance)!=lockhash:raise ValueError('Re-selection using validation alone changed lock')
    catalog=spec.catalog();np.testing.assert_array_equal(np.load(spec.LOCAL/'candidate_catalog.npy'),catalog)
    if len(np.unique(catalog,axis=0))!=len(catalog):raise ValueError('Duplicate combinations')
    cohorts=pd.read_csv(spec.PUBLIC/'cohorts.csv');spaces=pd.read_csv(spec.PUBLIC/'search_space.csv');checks=[];coverage=[];modelcount=0;rng=np.random.default_rng(spec.SEED)
    for ti,target in enumerate(spec.targets()):
        store=Store(target,provenance);categories,reasons=spec.relations(target)
        np.testing.assert_array_equal(store.ids,np.flatnonzero(categories>1));np.testing.assert_array_equal(np.load(store.path/'categories.npy'),categories);np.testing.assert_array_equal(np.load(store.path/'exclusion_rules.npy'),reasons)
        if not store.complete(range(4)) or store.get('selection_sha256')!=lockhash:raise ValueError('Incomplete or improperly selected evaluation')
        if not np.isfinite(store.metrics).all() or (store.metrics<0).any():raise ValueError('Nonfinite/negative error metrics')
        for view in spec.VIEWS:
            for config in spec.CONFIG['configurations']:
                r=spaces[spaces.target.eq(target)&spaces.view.eq(view)&spaces.configuration.eq(config)].iloc[0]
                for k in [1,2,3]:
                    if int(store.subset(view,config,k).sum())!=int(r[f'k{k}']):raise ValueError('Search-space count mismatch')
        for number,(start,end) in enumerate(spec.FOLDS+[('2018-01-01',None)]):
            tr,va=spec.partition(target,start,end);r=cohorts[cohorts.target.eq(target)&cohorts.fold.eq(number)].iloc[0];m=store.get('fold_'+str(number))
            for frame,key,hashkey in [(tr,'n_train','train_ids_sha256'),(va,'n_validation','validation_ids_sha256')]:
                digest=spec.digest(frame.song_id.tolist())
                if digest!=r[hashkey] or digest!=m[hashkey] or len(frame)!=m[key]:raise ValueError('Frozen cohort changed')
                if frame.song_id.duplicated().any() or not np.isfinite(frame.outcome).all():raise ValueError('Bad exact identity/target')
            if set(tr.song_id)&set(va.song_id) or not tr.first_chart_date.lt(start).all() or not va.first_chart_date.ge(start).all():raise ValueError('Chronological identity leakage')
            if not tr.window_end_26.le(start).all() or not va.window_end_26.le(end or spec.v2.end_date()).all():raise ValueError('Window exceeds cutoff')
            if target in spec.LIFETIME:
                for frame,cutoff in [(tr,start),(va,end or spec.v2.end_date())]:
                    labels=spec.v2.labels_at(cutoff).set_index('song_id').loc[frame.song_id]
                    if not (labels.mature&labels.inactive).all() or not labels.last_observed.lt(cutoff).all():raise ValueError('Historical target cutoff/maturity failure')
        fold=core.prepare(target,'2018-01-01',None)
        if target in fold.groups or any(spec.pair(target,n)[0]==1 for n in fold.groups):raise ValueError('Target-dependent column in design')
        chosen=[r for r in lock['selections'] if r['target']==target and 'candidate_id' in r]
        checkids={int(i) for i in rng.choice(store.ids,size=3,replace=False)}
        checkids|={r['candidate_id'] for r in chosen if r['configuration']=='combined' and r['selection_count']=='best_any_k'}
        for cid in sorted(checkids):
            combo=spec.combo(cid);checks.append(dict(target=target,candidate_id=cid,**fold.reference_check(combo)))
            dense,_=fold.evaluate([combo]);sparse,_=core.evaluate(fold,[combo]);pos=np.searchsorted(store.ids,cid)
            for name in ['mse','mae','r2','skill']:np.testing.assert_allclose(dense[name],sparse[name],rtol=2e-9,atol=2e-7)
            np.testing.assert_allclose([sparse['mse'][0],sparse['mae'][0]],store.metrics[3,pos],rtol=2e-9,atol=2e-7)
        models=spec.read_json(store.path/'selected_models.json.gz');ids=np.load(store.path/'selected_candidate_ids.npy');predictions=np.load(store.path/'selected_predictions.npy')
        np.testing.assert_array_equal(np.load(store.path/'evaluation_song_ids.npy'),fold.validation.song_id.to_numpy(dtype=str));np.testing.assert_array_equal(np.load(store.path/'evaluation_actual.npy'),fold.z)
        if predictions.shape!=(len(fold.z),len(ids)) or set(map(str,ids))!=set(models):raise ValueError('Model prediction coverage mismatch')
        for col,cid in enumerate(ids):
            model=models[str(cid)];pred=core.predict_model(model,fold.validation)
            np.testing.assert_allclose(pred,predictions[:,col],rtol=2e-12,atol=2e-9)
            if model['training_ids_sha256']!=spec.digest(fold.train.song_id.tolist()) or model['selection_sha256']!=lockhash:raise ValueError('Model provenance mismatch')
            if tuple(model['predictors'])!=spec.combo(int(cid)) or categories[cid]==1:raise ValueError('Model predictor dependency')
            actual=core.metrics(fold.z,pred,fold.u,fold.mean,fold.median);pos=np.searchsorted(store.ids,cid)
            np.testing.assert_allclose([actual['mse'],actual['mae']],store.metrics[3,pos],rtol=2e-9,atol=2e-7);modelcount+=1
        coverage.append(dict(target=target,candidates=store.n,fits=store.n*4,checkpoint_chunks=store.db.execute('SELECT COUNT(*) FROM chunks').fetchone()[0],status='PASS'))
        store.close();del store,fold,models,predictions;gc.collect();print(f'Validated {ti+1}/{len(spec.targets())}: {target}',flush=True)
    if sum(r['candidates'] for r in coverage)!=audit['valid_task_candidate_pairs']:raise ValueError('Overall coverage mismatch')
    # Reconstruct fixed windows from immutable chart rows, independently of exports.
    weekly=spec.v2.weekly();f=spec.v2.source_frame();joined=weekly[['song_id','chart_date','weekly_rank']].merge(f[['song_id','first_chart_date','window_end_12','window_end_26']],on='song_id',validate='many_to_one');rebuilt_counts={}
    actual=f.set_index('song_id')
    for horizon in [12,26]:
        win=joined[joined.chart_date.ge(joined.first_chart_date)&joined.chart_date.lt(joined[f'window_end_{horizon}'])].copy();win['points']=101-win.weekly_rank
        rebuilt=win.groupby('song_id').agg(best_rank=('weekly_rank','min'),chart_weeks=('chart_date','nunique'),chart_points=('points','sum'));rebuilt['top10']=(rebuilt.best_rank<=10).astype(int);rebuilt['long_chart']=(rebuilt.chart_weeks>=int(np.ceil(horizon/2))).astype(int)
        for name in rebuilt:np.testing.assert_array_equal(rebuilt[name],actual.loc[rebuilt.index,f'{name}_{horizon}'])
        rebuilt_counts[str(horizon)]=len(rebuilt)
    for row in spec.read_json(spec.PUBLIC/'local_artifacts.json'):
        p=spec.ROOT/row['path']
        if p.stat().st_size!=row['bytes'] or spec.sha(p)!=row['sha256']:raise ValueError('Complete local artifact changed: '+row['path'])
    for row in spec.read_json(spec.PUBLIC/'figures/manifest.json'):
        if spec.sha(spec.PUBLIC/'figures'/row['file'])!=row['sha256']:raise ValueError('Figure changed')
    preservation=spec.preservation() if preserve else {'status':'NOT_RUN'}
    if spec.sha(spec.PUBLIC/'selection_lock.json')!=lockhash:raise ValueError('Validation modified selection')
    result=dict(status='PASS',coverage=coverage,total_candidates=sum(r['candidates'] for r in coverage),total_fits=sum(r['fits'] for r in coverage),independent_full_row_svd_checks=checks,
        max_scaled_prediction_error=max(r['max_prediction_scaled_error'] for r in checks),selected_models_replayed=modelcount,fixed_window_identities_rebuilt=rebuilt_counts,preservation=preservation,selection_sha256=lockhash,
        full_test_suite=dict(tests=totaltests,passed=totaltests-skipped,skipped=skipped,command='python3 -m unittest discover -s tests -v',log_sha256=spec.sha(logpath)),elapsed_seconds=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    spec.write_json(spec.PUBLIC/'validation.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['coverage','independent_full_row_svd_checks']},indent=2),flush=True)


def publication(verify=False):
    path=spec.PUBLIC/'publication_manifest.json'
    if verify:
        manifest=spec.read_json(path)
        for name,r in manifest['files'].items():
            p=spec.ROOT/name
            if not p.is_file() or p.stat().st_size!=r['bytes'] or spec.sha(p)!=r['sha256']:raise ValueError('Publication artifact changed: '+name)
        result=dict(status='PASS',files=len(manifest['files']),manifest_sha256=spec.sha(path));print(json.dumps(result,indent=2),flush=True);return result
    validation=spec.read_json(spec.PUBLIC/'validation.json');determinism=spec.read_json(spec.PUBLIC/'determinism.json')
    if validation['status']!='PASS' or validation['preservation']['status']!='PASS' or determinism['status']!='PASS':raise ValueError('Integrity, preservation and deterministic replay must pass')
    paths=[p for p in spec.PUBLIC.rglob('*') if p.is_file() and p!=path]+list((spec.ROOT/'src').glob('regression_cross_domain*.py'))+[spec.ROOT/'tests/test_regression_cross_domain_v3.py',spec.ROOT/'docs/regression_cross_domain_v3.md']
    files={str(p.relative_to(spec.ROOT)):dict(bytes=p.stat().st_size,sha256=spec.sha(p)) for p in sorted(paths)}
    spec.write_json(path,dict(status='VALIDATED',version=spec.CONFIG['version'],parent_commit=validation['preservation']['baseline_commit'],selection_sha256=spec.sha(spec.PUBLIC/'selection_lock.json'),files=files));return publication(True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['validate','snapshot','check-determinism','publish-manifest','verify-publication'],nargs='?',default='validate');p.add_argument('--skip-preservation',action='store_true');args=p.parse_args()
    if args.action=='validate':validate(not args.skip_preservation)
    elif args.action in ['publish-manifest','verify-publication']:publication(args.action=='verify-publication')
    else:determinism('snapshot' if args.action=='snapshot' else 'check')
