"""Independent statistics, deterministic replay and public/full checkpoint agreement."""
from collections import Counter
import gzip
import json
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd
from scipy import stats
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
import relationship_phase1 as phase
import relationship_phase1_analysis as interpret
import relationship_discovery as engine
import relationship_discovery_spec as spec
import relationship_discovery_stats as inference
import relationship_discovery_models as models


def comparable(row):
    ignored={'evaluation_label','q_by_global','q_by_family','multiple_testing_status','independent_confirmation'}
    return engine.logical({k:v for k,v in row.items() if k not in ignored})


def verify():
    started=time.perf_counter();rows=phase.complete_results();lookup={r['candidate_id']:r for r in rows}
    frame=engine.data();closed=frame.loc[frame.last_iso.lt('2026-01-01')];masks=models.make_splits(frame)
    reference_checks=Counter();replays=[];outer_folds=0;fit_calls=0
    pilot=json.loads(gzip.decompress((spec.PUBLIC/'pilot_results/results.json.gz').read_bytes()))
    overlap=[r for r in pilot if r['family'] in phase.FAMILIES]
    for old in overlap:
        current=lookup[old['candidate_id']]
        if comparable(old)!=comparable(current):raise ValueError('Frozen pilot calculation changed: '+old['candidate_id'])
    selected=[]
    for family in phase.FAMILIES:
        group=sorted([r for r in rows if r['family']==family],key=lambda r:engine.old.digest(['phase1-replay',r['candidate_id']]))
        selected.extend(group[:12])
    with threadpool_limits(limits=1):
        for row in rows:
            if row['family']!='pairwise' or row['status']!='ok':continue
            x=row['predictors'][0];y=row['target'];f=closed.dropna(subset=[x,y])
            assert len(f)==row['n']
            if row.get('spearman') is not None:
                np.testing.assert_allclose(stats.spearmanr(f[x],f[y]).statistic,row['spearman'],atol=1e-12,rtol=1e-12)
                reference_checks['spearman']+=1
            if row.get('pearson') is not None:
                np.testing.assert_allclose(stats.pearsonr(f[x],f[y]).statistic,row['pearson'],atol=1e-12,rtol=1e-12)
                reference_checks['pearson']+=1
            xc=spec.kind(x)=='categorical';yc=spec.kind(y)=='categorical'
            if xc and yc:
                table=pd.crosstab(f[x],f[y]).to_numpy();n=table.sum();r,c=table.shape
                chi=stats.chi2_contingency(table,correction=False).statistic
                expected=np.sqrt(max(0.,chi/n-(r-1)*(c-1)/(n-1))/min(r-1-(r-1)**2/(n-1),c-1-(c-1)**2/(n-1)))
                np.testing.assert_allclose(expected,row['effect'],atol=1e-12,rtol=1e-12);reference_checks['cramers_v']+=1
            elif xc or yc:
                group=x if xc else y;value=y if xc else x;v=f[value];mean=v.mean()
                between=sum(len(g)*(g[value].mean()-mean)**2 for _,g in f.groupby(group))
                expected=between/float(np.sum((v-mean)**2))
                np.testing.assert_allclose(expected,row['effect'],atol=1e-12,rtol=1e-12);reference_checks['eta_squared']+=1
            # Independently calculate empirical MI from observed contingency probabilities.
            a=pd.factorize(f[x],sort=True)[0] if xc else inference.discretize(f[x])
            b=pd.factorize(f[y],sort=True)[0] if yc else inference.discretize(f[y])
            table=pd.crosstab(a,b).to_numpy(float);prob=table/table.sum();expected=np.outer(prob.sum(axis=1),prob.sum(axis=0));keep=prob>0
            mi=float(np.sum(prob[keep]*np.log(prob[keep]/expected[keep])))
            np.testing.assert_allclose(mi,row['mutual_information_nats'],atol=2e-12,rtol=1e-12);reference_checks['mutual_information']+=1
        # Outcome-blind hash sample reruns full inner selection, inference and diagnostics.
        for row in selected:
            candidate=next(c for c in phase.candidates() if c['candidate_id']==row['candidate_id'])
            replay=phase.execute(candidate)
            if comparable(replay)!=comparable(row):raise ValueError('Non-deterministic result: '+row['candidate_id'])
            replays.append(row['candidate_id']);fit_calls+=replay.get('fit_count',0)
            if row['family']!='pairwise':
                predictions,slopes,count=interpret.replay_predictions(frame,masks,row);fit_calls+=count
                evidence=inference.paired_evidence(predictions.normalized_loss_gain.to_numpy(),predictions.debut_year.to_numpy(),row['candidate_id'])
                for key in ('effect','ci_low','ci_high','p_value'):assert evidence[key]==row[key]
                outer_folds+=sum(f['status']=='ok' for f in row['folds'])
                if row['family']=='nonlinear':
                    x=row['predictors'][0];y=row['target']
                    for fold in row['folds']:
                        if fold['status']!='ok':continue
                        train,test=models.partitions(frame,masks,tuple(fold['period']),y)
                        median=float(train[x].median());design=np.column_stack([np.ones(len(train)),train[x].fillna(median),train[x].isna()])
                        validation=np.column_stack([np.ones(len(test)),test[x].fillna(median),test[x].isna()])
                        coef=np.linalg.lstsq(design,train[y],rcond=None)[0]
                        linear=models.Univariate(x,'linear').fit(train,y)
                        np.testing.assert_allclose(validation@coef,linear.predict(test),rtol=1e-8,atol=1e-6)
                        reference_checks['raw_input_linear_baseline']+=1;fit_calls+=2
    public=json.loads(gzip.decompress((phase.PUBLIC/'demo_results.json.gz').read_bytes()))
    assert len(public)==9159 and {r['candidate_id'] for r in public}==set(lookup)
    for row in public:
        raw=lookup[row['candidate_id']]
        for key in ('p_value','q_by_global','q_by_family','effect','r2','n','relative_mse_improvement','stability_fraction'):
            assert row.get(key)==raw.get(key),(row['candidate_id'],key)
    detail_files=engine.read_json(phase.PUBLIC/'demo_detail_files.json');detail_ids=[]
    for family,mapping in detail_files.items():
        for target,filename in mapping.items():
            details=json.loads(gzip.decompress((phase.PUBLIC/filename).read_bytes()))
            for row in details:
                detail_ids.append(row['candidate_id']);raw=lookup[row['candidate_id']]
                assert row['family']==family and row['target']==target
                for key in ('p_value','q_by_global','effect','r2','n','relative_mse_improvement'):
                    assert row.get(key)==raw.get(key),(row['candidate_id'],key)
                if 'folds' in raw:
                    expected_folds=[{k:v for k,v in f.items() if k!='inner_models'} for f in raw['folds']]
                    assert row['folds']==expected_folds
                if row['family']=='nonlinear':
                    assert len(row['diagnostics'])==len(raw['diagnostics'])
                    for detail,source in zip(row['diagnostics'],raw['diagnostics']):
                        indices=np.unique(np.round(np.linspace(0,len(source['x'])-1,25)).astype(int))
                        for key in ('x','linear','nonlinear'):assert detail[key]==[source[key][i] for i in indices]
                else:
                    for key in ('diagnostics','annual_effects','subgroup_results'):assert row.get(key)==raw.get(key)
    assert len(detail_ids)==9159 and len(set(detail_ids))==9159 and set(detail_ids)==set(lookup)
    # Every raw p is included, irrespective of status or the presentation shortlist.
    expected=stats.false_discovery_control([r.get('p_value') if r.get('p_value') is not None else 1 for r in public],method='by')
    np.testing.assert_array_equal(expected,[r['q_by_global'] for r in public])
    result=dict(status='PASS',full_candidates=len(rows),independent_reference_checks=dict(reference_checks),
        unchanged_pilot_overlap=len(overlap),exact_candidate_replays=replays,replayed_outer_folds=outer_folds,
        additional_fit_calls=fit_calls,public_values_match_all_checkpoints=True,all_global_by_values_recomputed=True,
        elapsed_seconds=time.perf_counter()-started,peak_rss_bytes=engine.peak_rss_bytes(),preservation=phase.preservation())
    engine.write_json(phase.PUBLIC/'replay_validation.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':verify()
