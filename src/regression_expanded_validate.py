"""Independent data/OLS replay, exhaustive coverage, censoring and preservation audit."""
import os
for _key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[_key]='1'
import argparse
import json
import re
import time
from pathlib import Path
import numpy as np
import pandas as pd
import regression_expanded_spec as spec
import regression_expanded_core as core
from regression_expanded_search import open_store,lock_selections


def reproducible_files():
    excluded={'benchmark.json','execution.json','report_execution.json','validation.json','determinism_snapshot.json','determinism.json','publication_manifest.json'}
    files={str(p.relative_to(spec.ROOT)):spec.sha(p) for p in spec.PUBLIC.rglob('*') if p.is_file() and p.name not in excluded and p.suffix not in ['.md']}
    for r in spec.read_json(spec.PUBLIC/'local_artifacts.json'):
        p=spec.ROOT/r['path'];files[r['path']]=spec.sha(p)
    return files


def determinism(action):
    path=spec.LOCAL/'determinism_snapshot.json';actual=reproducible_files()
    if action=='snapshot':spec.write_json(path,actual);return
    expected=spec.read_json(path)
    if actual!=expected:raise ValueError('Deterministic regeneration differs: '+repr([n for n in set(actual)|set(expected) if actual.get(n)!=expected.get(n)]))
    result=dict(status='PASS',files=len(actual),snapshot_sha256=spec.sha(path),method='Full report regeneration: compressed complete hierarchies, model exports, numerical summaries, fixed-seed cluster intervals and SVG figures are byte-identical')
    spec.write_json(spec.PUBLIC/'determinism.json',result);print(json.dumps(result,indent=2),flush=True)


def validate(preserve=True):
    logpath=spec.LOCAL/'tests.log';log=logpath.read_text()
    match=re.search(r'Ran (\d+) tests',log);skipped=re.search(r'OK \(skipped=(\d+)\)',log)
    if match is None or not re.search(r'^OK(?: \(skipped=\d+\))?$',log,re.M):raise ValueError('Successful full unittest log required at '+str(logpath))
    testcount=int(match.group(1));skipcount=int(skipped.group(1)) if skipped else 0
    started=time.perf_counter();provenance=spec.provenance();lockhash=spec.sha(spec.PUBLIC/'selection_lock.json');checks=[];counts=[]
    if lock_selections(provenance)!=lockhash:raise ValueError('Validation-only re-selection changed lock')
    predictions=pd.read_csv(spec.LOCAL/'selected_predictions.csv.gz');board=pd.read_csv(spec.PUBLIC/'target_leaderboard.csv');cohorts=pd.read_csv(spec.PUBLIC/'cohorts.csv')
    rng=np.random.default_rng(spec.SEED)
    for task in spec.tasks():
        store=open_store(task,provenance);catalog=spec.candidates(task['track'])
        if not store.complete(range(4)):raise ValueError('Missing candidate/fold')
        if store.db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Orphan scores')
        if store.db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity failure')
        if store.db.execute('SELECT COUNT(*) FROM scores').fetchone()[0]!=4*len(catalog):raise ValueError('Unexpected scores')
        if store.get('selection_sha256')!=lockhash:raise ValueError('Evaluation selection mismatch')
        for number,(start,end) in enumerate(spec.FOLDS+[('2018-01-01',None)]):
            tr,va=spec.partition(task['track'],task['horizon'],task['target'],start,end)
            r=cohorts[cohorts.task_id.eq(task['task_id'])&cohorts.fold.eq(number)].iloc[0];m=store.get('fold_'+str(number))
            if spec.digest(tr.song_id.tolist())!=r.train_ids_sha256 or spec.digest(va.song_id.tolist())!=r.validation_ids_sha256:raise ValueError('Frozen population changed')
            if len(tr)!=m['n_train'] or len(va)!=m['n_validation']:raise ValueError('Sample size changed')
            if set(tr.song_id)&set(va.song_id):raise ValueError('Identity crosses partitions')
            if task['horizon']=='26':
                if not tr.window_end_26.le(start).all() or not va.window_end_26.le(end or spec.end_date()).all():raise ValueError('Window crosses cutoff')
            else:
                for frame,cutoff in [(tr,start),(va,end or spec.end_date())]:
                    labels=spec.labels_at(cutoff).set_index('song_id').loc[frame.song_id]
                    if not (labels.mature&labels.inactive).all():raise ValueError('Censoring mask mismatch')
            if not va.first_chart_date.ge(start).all():raise ValueError('Validation debut precedes cutoff')
        fold=core.prepare(task,'2018-01-01',None)
        selected=board[board.task_id.eq(task['task_id'])]
        combos=[catalog[i][1] for i in sorted(rng.choice(len(catalog),size=12,replace=False))]+[tuple(r.predictors.split(' | ')) for r in selected.itertuples()]
        for combo in combos:checks.append(dict(task=task['task_id'],**core.independent_reference(fold,combo)))
        for r in selected.itertuples():
            path=spec.PUBLIC/'models'/(task['task_id']+'__'+r.configuration+'.json');model=spec.read_json(path);pred=core.predict_model(model,fold.validation)
            saved=predictions[predictions.task_id.eq(task['task_id'])&predictions.configuration.eq(r.configuration)].sort_values('song_id')
            if saved.song_id.tolist()!=fold.validation.song_id.tolist():raise ValueError('Prediction population mismatch')
            np.testing.assert_allclose(pred,saved.prediction.to_numpy(),rtol=2e-12,atol=2e-9)
            if model['training_ids_sha256']!=spec.digest(fold.train.song_id.tolist()):raise ValueError('Model training hash mismatch')
            if model['selection_sha256']!=lockhash:raise ValueError('Model selection hash mismatch')
            if task['track']=='strict' and any(spec.REGISTRY[n]['availability']!='C' for n in model['predictors']):raise ValueError('Strict availability violation')
        counts.append(dict(task=task['task_id'],candidates=len(catalog),fits=4*len(catalog),sqlite_integrity='ok'))
        store.close();print('Validated '+task['task_id'],flush=True)
    # Independently rebuild all fixed-horizon outcomes directly from source rows.
    weekly=spec.weekly();f=spec.source_frame();joined=weekly[['song_id','chart_date','weekly_rank']].merge(f[['song_id','first_chart_date','window_end_26']],on='song_id',validate='many_to_one')
    window=joined[joined.chart_date.ge(joined.first_chart_date)&joined.chart_date.lt(joined.window_end_26)].copy();window['points']=101-window.weekly_rank
    rebuilt=window.groupby('song_id').agg(best_rank_26=('weekly_rank','min'),chart_weeks_26=('chart_date','nunique'),chart_points_26=('points','sum'))
    actual=f.set_index('song_id')
    for target in spec.TARGETS:np.testing.assert_array_equal(rebuilt[target+'_26'].to_numpy(),actual.loc[rebuilt.index,target+'_26'].to_numpy())
    # Later returns are an audit of historical censoring proxy failure, never inputs to eligibility.
    returns=[]
    for cutoff in sorted(set(x for pair in spec.FOLDS for x in pair)|{'2018-01-01'}):
        labels=spec.labels_at(cutoff);eligible=labels[labels.mature&labels.inactive&labels.first_observed.ge(spec.CONFIG['burn_in_end'])]
        future_ids=set(weekly.loc[weekly.chart_date.ge(cutoff),'song_id']);returned=int(eligible.song_id.isin(future_ids).sum())
        returns.append(dict(cutoff=cutoff,eligible_mature_inactive=len(eligible),later_returned_by_source_endpoint=returned,return_fraction=returned/len(eligible),note='Future returns are used ONLY in this retrospective limitation audit, not historical cohort eligibility'))
    spec.write_csv(spec.PUBLIC/'lifetime_return_audit.csv',returns)
    for r in spec.read_json(spec.PUBLIC/'local_artifacts.json'):
        path=spec.ROOT/r['path']
        if path.stat().st_size!=r['bytes'] or spec.sha(path)!=r['sha256']:raise ValueError('Local complete-result artifact changed')
        count=sum(len(chunk) for chunk in pd.read_csv(path,chunksize=50000,usecols=[0]))
        if count!=r['rows']:raise ValueError('Hierarchy row-count mismatch')
    for r in spec.read_json(spec.PUBLIC/'figures/manifest.json'):
        if spec.sha(spec.PUBLIC/'figures'/r['file'])!=r['sha256']:raise ValueError('Figure hash mismatch')
    integrity=spec.preservation() if preserve else {'status':'NOT_RUN'}
    if spec.sha(spec.PUBLIC/'selection_lock.json')!=lockhash:raise ValueError('Validation modified selection')
    report=dict(status='PASS',coverage=counts,total_candidates=sum(r['candidates'] for r in counts),total_fits=sum(r['fits'] for r in counts),
        independent_full_row_svd_checks=checks,max_scaled_prediction_error=max(r['max_prediction_scaled_error'] for r in checks),
        fixed_horizon_rows_rebuilt=len(rebuilt),selected_prediction_rows_replayed=len(predictions),selection_sha256=lockhash,preservation=integrity,
        full_test_suite=dict(tests=testcount,passed=testcount-skipcount,skipped=skipcount,log_sha256=spec.sha(logpath),command='python3 -m unittest discover -s tests -v'),
        limitations=['Observed lifetime remains right-censored despite maturity/inactivity proxy','Retrospective measurements are not historically available forecasts','Previously inspected evaluation is exploratory'],elapsed_seconds=time.perf_counter()-started)
    spec.write_json(spec.PUBLIC/'validation.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['coverage','independent_full_row_svd_checks']},indent=2),flush=True)


def publication(verify=False):
    path=spec.PUBLIC/'publication_manifest.json'
    if verify:
        manifest=spec.read_json(path)
        for name,expected in manifest['files'].items():
            p=spec.ROOT/name
            if not p.is_file() or p.stat().st_size!=expected['bytes'] or spec.sha(p)!=expected['sha256']:raise ValueError('Publication artifact changed: '+name)
        result=dict(status='PASS',files=len(manifest['files']),manifest_sha256=spec.sha(path))
        print(json.dumps(result,indent=2),flush=True);return result
    validation=spec.read_json(spec.PUBLIC/'validation.json');deterministic=spec.read_json(spec.PUBLIC/'determinism.json')
    if validation['status']!='PASS' or validation['preservation']['status']!='PASS' or deterministic['status']!='PASS':raise ValueError('Publication requires successful integrity and deterministic replay')
    paths=[p for p in spec.PUBLIC.rglob('*') if p.is_file() and p!=path]
    paths+=list((spec.ROOT/'src').glob('regression_expanded*.py'))+[spec.ROOT/'tests/test_regression_expanded_v2.py',spec.ROOT/'docs/regression_expanded_v2.md']
    files={str(p.relative_to(spec.ROOT)):dict(bytes=p.stat().st_size,sha256=spec.sha(p)) for p in sorted(paths)}
    spec.write_json(path,dict(version=spec.CONFIG['version'],status='VALIDATED',files=files,selection_sha256=spec.sha(spec.PUBLIC/'selection_lock.json'),parent_commit=validation['preservation']['baseline_commit']))
    return publication(True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['validate','snapshot','check-determinism','publish-manifest','verify-publication'],nargs='?',default='validate');p.add_argument('--skip-preservation',action='store_true');args=p.parse_args()
    if args.action=='validate':validate(not args.skip_preservation)
    elif args.action in ['publish-manifest','verify-publication']:publication(args.action=='verify-publication')
    else:determinism('snapshot' if args.action=='snapshot' else 'check')
