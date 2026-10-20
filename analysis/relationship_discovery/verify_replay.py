"""Replay all outer fitted metrics/curves; independently check published dependence."""
import gzip
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy import stats
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import relationship_discovery as engine
import relationship_discovery_models as models
import relationship_discovery_stats as inference
import relationship_discovery_spec as spec
import regression_core as original_metrics


def verify():
    started=time.perf_counter()
    path=spec.PUBLIC/'pilot_results/results.json.gz'
    rows=json.loads(gzip.decompress(path.read_bytes())) if path.exists() else engine.read_json(path.with_suffix(''))
    frame=engine.data();masks=models.make_splits(frame);closed=frame.loc[frame.last_iso.lt('2026-01-01')]
    fitted=0;pair_checks=0;annual_checks=0;curve_checks=0;references=0
    with threadpool_limits(limits=1):
        for row in rows:
            if row['family'] in {'nonlinear','genre_interaction','numeric_interaction','threshold_interaction'}:
                yname=row['target'];x=row['predictors'][0];all_d=[];all_year=[]
                for fold in row['folds']:
                    if fold['status']!='ok':continue
                    train,test=models.partitions(frame,masks,tuple(fold['period']),yname)
                    assert len(train)==fold['n_train'] and len(test)==fold['n_test']
                    if row['family']=='nonlinear':
                        chosen=min(fold['inner_models'],key=lambda m:(-m['mean_skill'],spec.METHODS.index(m['method'])))['method']
                        assert chosen==fold['selected_method']
                        base=models.Univariate(x,'linear').fit(train,yname)
                        model=base if chosen=='linear' else models.Univariate(x,chosen).fit(train,yname)
                        # Original-row raw-input least squares is an independent linear reference.
                        missing=train[x].isna().to_numpy();median=float(train[x].median())
                        tx=train[x].fillna(median).to_numpy();vx=test[x].fillna(median).to_numpy()
                        design=np.column_stack([np.ones(len(train)),tx,missing])
                        vdesign=np.column_stack([np.ones(len(test)),vx,test[x].isna()])
                        coef=np.linalg.lstsq(design,train[yname],rcond=None)[0]
                        np.testing.assert_allclose(vdesign@coef,base.predict(test),rtol=1e-8,atol=1e-7);references+=1
                        diag=next(d for d in row['diagnostics'] if d['period']==fold['period'])
                        import pandas as pd
                        grid=pd.DataFrame({x:diag['x']})
                        np.testing.assert_allclose(base.predict(grid),diag['linear'],rtol=1e-12,atol=1e-12)
                        np.testing.assert_allclose(model.predict(grid),diag['nonlinear'],rtol=1e-12,atol=1e-12);curve_checks+=1
                    else:
                        base=models.Interaction(row,False).fit(train,yname);model=models.Interaction(row,True).fit(train,yname)
                    y=test[yname].to_numpy(float);pred=model.predict(test);comparison=base.predict(test)
                    mean=float(train[yname].mean());median=float(train[yname].median());weights=np.ones(len(y))
                    for expected,actual in [(fold['metrics'],pred),(fold['comparison_metrics'],comparison)]:
                        measured=original_metrics.metrics(y,actual,weights,mean,median)
                        for key in ['r2','mae','rmse','mse','skill','baseline_rmse','baseline_mae']:
                            np.testing.assert_allclose(measured[key],expected[key],rtol=2e-12,atol=1e-9)
                    all_d.extend(((y-comparison)**2-(y-pred)**2)/train[yname].var(ddof=0));all_year.extend(test.debut_year)
                    fitted+=1
                evidence=inference.paired_evidence(all_d,np.array(all_year),row['candidate_id'])
                for key in ['effect','p_value','ci_low','ci_high']:
                    assert evidence.get(key)==row.get(key),(row['candidate_id'],key)
            elif row['family']=='pairwise' and row['status']=='ok':
                x=row['predictors'][0];y=row['target'];f=closed.dropna(subset=[x,y])
                if row.get('pearson') is not None:np.testing.assert_allclose(stats.pearsonr(f[x],f[y]).statistic,row['pearson'],rtol=1e-12,atol=1e-12)
                if row.get('spearman') is not None:np.testing.assert_allclose(stats.spearmanr(f[x],f[y]).statistic,row['spearman'],rtol=1e-12,atol=1e-12)
                pair_checks+=1
            elif row['family']=='temporal':
                x=row['predictors'][0];y=row['target']
                for annual in row['annual']:
                    if annual['genre']!='All genres':continue
                    f=closed.loc[closed.debut_year.eq(annual['year'])].dropna(subset=[x,y])
                    assert len(f)==annual['n']
                    np.testing.assert_allclose(stats.spearmanr(f[x],f[y]).statistic,annual['rho'],rtol=1e-12,atol=1e-12);annual_checks+=1
            elif row['family']=='structure' and row['method']=='pca':
                for fold in row['folds']:
                    loading=np.array(fold['loadings'])
                    np.testing.assert_allclose(loading@loading.T,np.eye(row['k']),atol=1e-12)
    result=dict(status='PASS',outer_model_folds_replayed=fitted,saved_curves_replayed=curve_checks,
        independent_raw_linear_reference_checks=references,pairwise_scipy_checks=pair_checks,annual_scipy_checks=annual_checks,
        predictive_p_values_and_intervals_replayed=True,original_metric_implementation_agreement=True,
        original_preservation=engine.preserve(),elapsed_seconds=time.perf_counter()-started)
    engine.write_json(spec.PUBLIC/'pilot_results/replay_validation.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':verify()
