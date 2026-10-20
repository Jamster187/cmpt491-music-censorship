"""Independent complete-index and saved-model replay validation; read-only."""
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
import regression_meaningful as m
import regression_demo_model as models
import regression_core as core
import regression_relationships as rel


def verify():
    started=time.perf_counter()
    m.lock_policy()
    preservation=m.preserve_originals()
    audit=m.read_json(m.PUBLIC/"filter_audit.json")
    selection=m.read_json(m.PUBLIC/"selected_candidates.json")
    if m.spec.original.sha(m.PUBLIC/"selected_candidates.json")!=audit["selection_sha256"]:
        raise ValueError("Selections changed after they were frozen")
    targets={t["task_id"]:t for t in selection["targets"]}
    proofs={t["task_id"]:t for t in audit["targets"]}
    checked=[];seen=set();model_checks=[]
    with threadpool_limits(limits=1):
        for task in m.tasks():
            proof=proofs[task["task_id"]]
            if m.spec.original.sha(m.index_path(task))!=proof["index_sha256"]:raise ValueError("Filtered index hash changed")
            with m.readonly(m.original_path(task)/"results.sqlite") as source,m.readonly(m.index_path(task)) as index:
                if index.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("Filtered index integrity")
                original=[dict(r) for r in source.execute("SELECT * FROM hierarchy ORDER BY validation_rank")]
                actual=[dict(r) for r in index.execute("SELECT * FROM ranking ORDER BY original_rank")]
                if [r['id'] for r in original]!=[r['id'] for r in actual]:raise ValueError("Missing or duplicate original candidates")
                predictors={r['id']:[task['predictors'][r[k]] for k in ('i1','i2','i3') if r[k] is not None] for r in original}
                retained=[r for r in original if not rel.circular_reasons(task['target'],predictors[r['id']])]
                cross=[r for r in retained if all(rel.domain(p)!=rel.domain(task['target']) for p in predictors[r['id']])]
                for mode,expected,column in [('filtered',retained,'filtered_rank'),('cross_domain',cross,'cross_rank')]:
                    ordered=[dict(r) for r in index.execute('SELECT * FROM ranking WHERE '+column+' IS NOT NULL ORDER BY '+column)]
                    if [r['id'] for r in ordered]!=[r['id'] for r in expected]:raise ValueError("Incorrect filtered order")
                    if [r[column] for r in ordered]!=list(range(1,len(expected)+1)):raise ValueError("Nonconsecutive filtered ranks")
                    saved=targets[task['task_id']]
                    if saved['winners'][mode]['id']!=expected[0]['id']:raise ValueError("Winner differs from validation rank")
                    for k in (1,2,3):
                        best=next(r for r in saved['best_by_k'][mode] if r['k']==k)
                        reference=next(r for r in expected if r['k']==k)
                        if best['id']!=reference['id']:raise ValueError("Best-by-size winner mismatch")
                        for key in ('validation_r2','validation_mae','validation_mse','validation_skill'):
                            if best[key]!=reference[key]:raise ValueError("Saved original validation metric changed")
                    repeated=[r[0] for r in index.execute('SELECT id FROM ranking WHERE '+column+' IS NOT NULL ORDER BY '+column)]
                    if repeated!=[r['id'] for r in expected]:raise ValueError("Ranking is not deterministic")
            raw=m.original.read_table(task['table'])
            converted=m.spec.original.convert(raw)
            tr,te=core.partition(raw,'2018-01-01',None)
            observed=converted[task['target']].notna()
            train,test=converted.loc[tr & observed],converted.loc[te & observed]
            for chosen in targets[task['task_id']]['winners'].values():
                key=(task['task_id'],chosen['id'])
                if key in seen:continue
                seen.add(key);dest=models.model_directory(*key)
                for name,h in m.read_json(dest/'artifacts.json').items():
                    if m.spec.original.sha(dest/name)!=h:raise ValueError("Saved model artifact changed")
                model=m.read_json(dest/'model.json');result=m.read_json(dest/'metrics.json')
                if model['predictors']!=chosen['predictors'] or not model['test_previously_inspected']:raise ValueError("Model selection or exploratory label mismatch")
                enc=core.Encoder().fit(train,model['predictors'])
                if enc.state!=model['encoder']:raise ValueError("Preprocessing was not fitted on refit rows alone")
                pred=pd.read_csv(dest/'predictions.csv.gz',float_precision='round_trip',dtype={'song_id':str})
                if pred.source_row.tolist()!=test.index.tolist() or pred.song_id.tolist()!=test.song_id.tolist():raise ValueError("Test membership mismatch")
                if set(train.song_id)&set(test.song_id):raise ValueError("Train/test song overlap")
                y=train[task['target']].to_numpy(float);z=test[task['target']].to_numpy(float)
                w,u=core.weights(train),core.weights(test)
                mean=float(np.average(y,weights=w));median=core.weighted_median(y,w)
                if model['target_center']!=mean or model['training_median_baseline']!=median:raise ValueError("Wrong training baseline")
                replay=models.predict_frame(model,models.input_rows(raw.loc[test.index],model['predictors']))
                np.testing.assert_allclose(replay,pred.predicted,atol=1e-10,rtol=1e-10)
                np.testing.assert_array_equal(z,pred.actual)
                np.testing.assert_allclose(u,pred.weight,atol=1e-12,rtol=1e-12)
                for name,value in core.metrics(z,replay,u,mean,median).items():
                    np.testing.assert_allclose(value,result[name],atol=1e-10,rtol=1e-10)
                if result['direct_prediction_max_scaled_error']>2e-7:raise ValueError("Independent SVD check failed")
                model_checks.append(dict(task_id=task['task_id'],candidate_id=chosen['id'],test_rows=len(test),test_songs=int(test.song_id.nunique()),
                    replay_max_absolute_error=float(np.max(abs(replay-pred.predicted))),preprocessing_train_only=True,metrics_recomputed=True))
            checked.append(dict(task_id=task['task_id'],original=len(original),eligible=len(retained),cross_domain=len(cross)))
            print('Verified',task['task_id'],flush=True)
    out=dict(status='PASS',elapsed_seconds=time.perf_counter()-started,original_preservation=preservation,
        source_combinations=sum(r['original'] for r in checked),eligible_combinations=sum(r['eligible'] for r in checked),
        cross_domain_combinations=sum(r['cross_domain'] for r in checked),targets=checked,model_checks=model_checks,
        unique_models_verified=len(model_checks),policy_sha256=selection['policy_sha256'],selection_sha256=audit['selection_sha256'],
        deterministic_rankings=True,test_based_reselection=False,prediction_interface_replayed=True)
    m.write_json(m.PUBLIC/'validation.json',out)


if __name__=='__main__':verify()
