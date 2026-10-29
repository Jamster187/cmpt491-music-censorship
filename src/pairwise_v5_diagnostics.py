"""Prespecified stationarity diagnostics, control-rank repair and null validation."""
from __future__ import annotations
import argparse
import collections
import json
import time
import warnings
import numpy as np
import pandas as pd
from scipy import linalg,stats
from statsmodels.tsa.stattools import adfuller
import pairwise_v5_common as c
import pairwise_v5_stats as engine


def stationarity(values,frequency):
    values=np.asarray(values,float); observed=np.isfinite(values); indexes=np.flatnonzero(observed)
    result=dict(status='insufficient_contiguous_support',p_value=None,statistic=None,n_observed=len(indexes),longest_run=0,used_lags=0)
    if not len(indexes): return result
    runs=np.split(indexes,np.flatnonzero(np.diff(indexes)>1)+1); run=max(runs,key=len); result['longest_run']=len(run)
    lag={'M':12,'Q':4,'A':1,'term':1,'event':1}[frequency]
    if len(run)<max(24,3*lag+8): return result
    series=values[run]
    if np.ptp(series)<=1e-12: result['status']='constant'; return result
    with warnings.catch_warnings():
        warnings.simplefilter('error',RuntimeWarning)
        try: statistic,p,used,n,*_=adfuller(series,maxlag=lag,regression='c',autolag=None)
        except (ValueError,np.linalg.LinAlgError,RuntimeWarning): result['status']='unestimable_adf'; return result
    result.update(status='ok',p_value=float(p),statistic=float(statistic),used_lags=int(used),adf_rows=int(n))
    return result


def build_stationarity(budget):
    workspace=engine.Workspace(); plan=c.load(c.LOCAL/'plan.pkl'); rows=[]; lookup={}
    external=workspace.external
    for view in workspace.views:
        for frequency in ['M','Q','A','term']:
            matching=[t for t in plan if t['view_id']==view['id'] and t['frequency']==frequency and t['lag']==0]
            if not matching: continue
            for track in c.CONFIG['tracks']:
                task=next(t for t in matching if t['track']==track); a=workspace.aligned(task)
                groups=collections.defaultdict(list)
                for j,profile in enumerate(a.profiles):
                    controls=a.controls_composition if profile=='composition' else a.controls_time
                    mask=np.isfinite(a.y[:,j])&np.isfinite(controls).all(axis=1)
                    groups[(profile,np.packbits(mask).tobytes())].append(j)
                for (profile,_),columns in groups.items():
                    controls=a.controls_composition if profile=='composition' else a.controls_time
                    mask=np.isfinite(a.y[:,columns[0]])&np.isfinite(controls).all(axis=1)
                    residual=np.full((len(a.grid),len(columns)),np.nan)
                    if mask.sum()>controls.shape[1]+3:
                        basis=engine.control_basis(controls[mask]); residual[mask]=engine.residualize(basis,a.y[mask][:,columns])
                    for k,j in enumerate(columns):
                        value=stationarity(residual[:,k],frequency)
                        lookup[(view['id'],frequency,track,a.names[j])]=value['p_value']
                        rows.append(dict(origin='music',view=view['name'],variable=a.names[j],track=track,frequency=frequency,
                            diagnostic_cohort='Own available lag-zero native grid; no external outcome used',**value))
                budget.check()
        print(json.dumps(dict(stage='stationarity_music',view=view['name'],completed=len(rows))),flush=True)
    for name,d in sorted(external['metadata'].items()):
        frequency=d['analysis_frequency']
        for track in c.CONFIG['tracks']:
            if d['kind']=='categorical': value=dict(status='not_applicable_nominal_indicator',p_value=None)
            else:
                series=external[track][name].loc['1958-08':'2026-09']
                if frequency in ['Q','A']:
                    series=pd.Series(series.to_numpy(float),index=series.index.asfreq('Q-DEC' if frequency=='Q' else 'Y-DEC')).groupby(level=0).first()
                value=stationarity(series.to_numpy(float),frequency)
            lookup[('external',name,track)]=value.get('p_value')
            rows.append(dict(origin='external',view='native_source',variable=name,track=track,frequency=frequency,
                diagnostic_cohort='Original native source grid in the music study span',**value))
        budget.check()
    c.write_csv(c.PUBLIC/'stationarity_diagnostics.csv',rows); c.save(c.LOCAL/'stationarity.pkl',lookup)
    return dict(status='PASS',diagnostics=len(rows),interpretation='ADF is an assumption screen, not proof of stationarity; the full BY denominator includes failed/unsupported screens.')


def lookup_diagnostics(workspace,task,aligned):
    if not workspace.stationarity: workspace.stationarity=c.load(c.LOCAL/'stationarity.pkl')
    frequency=aligned.frequency if aligned.frequency in ['M','Q','A','term'] else 'M'
    music=[workspace.stationarity.get((task['view_id'],frequency,task['track'],name)) for name in aligned.names]
    external=workspace.stationarity.get(('external',task['external'],task['track']))
    return np.array([np.nan if p is None else p for p in music]),np.nan if external is None else external


def reproduce_control_fix():
    frame=c.load(c.PARENT/'monthly.pkl'); months=pd.PeriodIndex(frame.month,freq='M')
    target='lyric_pos_aux_share'; names=sorted(n for n in frame if n.startswith('genre_share__'))
    time_index=(months.asi8-pd.Period('1958-01','M').ordinal)/12
    C=np.column_stack([np.ones(len(frame)),time_index,np.sin(2*np.pi*months.month/12),np.cos(2*np.pi*months.month/12),frame[names[1:]].to_numpy(float)])
    labels=['intercept','time','season_sine','season_cosine']+names[1:]
    mask=np.isfinite(frame[target]) & (months<pd.Period('1983-01','M'))
    y=frame[target].to_numpy(float)[mask]; controls=C[mask]
    u,s,vt=linalg.svd(controls,full_matrices=False); old_rank=int(np.sum(s>s[0]*1e-8))
    basis=engine.control_basis(controls)
    null=vt[-1]; null/=max(abs(null))
    null_relation={name:float(v) for name,v in zip(labels,null) if abs(v)>1e-5}
    rng=np.random.default_rng(c.CONFIG['seed']); x=rng.normal(size=len(y))
    design=np.column_stack([controls,x]); ref=linalg.lstsq(design,y,cond=1e-10,lapack_driver='gelsd')[0]
    xr=engine.residualize(basis,x); yr=engine.residualize(basis,y)
    slope=float(xr@yr/(xr@xr)); nuisance=basis.train.T@(y-x*slope); prediction=basis.train@nuisance+x*slope
    np.testing.assert_allclose(prediction,design@ref,rtol=1e-8,atol=1e-10)
    assert old_rank<controls.shape[1] and len(y)-basis.rank-1>=c.CONFIG['minimum_residual_df']
    result=dict(status='PASS',original_columns=controls.shape[1],original_rank=old_rank,retained_span_rank=basis.rank,
        training_rows=len(y),correct_residual_df=len(y)-basis.rank-1,nominal_residual_df=len(y)-controls.shape[1]-1,
        null_space_relation=null_relation,null_relation_max_abs_residual=float(np.max(abs(controls@null))),
        reference_prediction_max_abs_error=float(np.max(abs(prediction-design@ref))),
        original_failure='V4 rejected every rank-deficient full design, including harmless linear dependencies among nuisance controls.',
        correction='Weighted, column-scaled SVD retains the entire nuisance column space. Inference uses its numerical rank. No outcome-based control removal; external effects still require identifiable residual variation.',
        future_control_policy='A validation row outside the training control row space is marked unsupported, not assigned an invented coefficient.',
        original_v4_code_and_results_changed=False)
    c.write_json(c.PUBLIC/'adjusted_monthly_fix.json',result)
    return result


def validate_simulations(budget):
    """Known mechanisms and independent null replications, before real-data fits."""
    validation_seed=c.CONFIG['seed']+1000
    rng=np.random.default_rng(validation_seed); results=[]
    n=600; position=np.arange(n); clock=np.column_stack([np.ones(n),np.arange(n)/n,np.sin(2*np.pi*position/12),np.cos(2*np.pi*position/12)])
    shares=rng.dirichlet(np.ones(5),n); controls=np.column_stack([clock,shares,shares[:,0]+shares[:,1],np.zeros(n)])
    x=rng.normal(size=n); errors=rng.normal(size=n)*.7
    y=1.5*x+controls@rng.normal(size=controls.shape[1])+errors
    bandwidth=c.CONFIG['hac_lags']['M']
    fitted=engine.numeric_fit(x,y[:,None],controls,position,n,bandwidth)
    assert fitted is not None and abs(fitted['beta'][0]-1.5)<.15 and fitted['p'][0]<.001
    changed=controls.copy(); changed[400:]*=17
    b1=engine.control_basis(controls[:400]); b2=engine.control_basis(changed[:400])
    np.testing.assert_array_equal(b1.transform,b2.transform)
    for ar in [0.,.5,.85]:
        raw_rejections=0; by_worlds=0; trials=160; hypotheses=40
        for replicate in range(trials):
            x=rng.normal(size=n); y=rng.normal(size=(n,hypotheses))
            for i in range(1,n): x[i]+=ar*x[i-1]; y[i]+=ar*y[i-1]
            fit=engine.numeric_fit(x,y,controls,position,n,bandwidth)
            rank=engine.numeric_fit(stats.rankdata(x),stats.rankdata(y,axis=0),controls,position,n,bandwidth)
            p=np.r_[fit['p'],rank['p']]; raw_rejections+=int(np.sum(p<.05)); by_worlds+=int(np.any(engine.by_adjust(p)<.05))
            if replicate%20==0: budget.check()
        total=trials*hypotheses*2; rate=raw_rejections/total; family_rate=by_worlds/trials
        # A fixed tolerance allows finite Monte Carlo error; all estimates remain
        # published even if a gate fails. These simulations cannot prove validity.
        results.append(dict(ar=ar,worlds=trials,hypotheses_per_world=hypotheses*2,
            unadjusted_rejection_rate=rate,worlds_with_any_BY_rejection=by_worlds,BY_world_rejection_rate=family_rate,
            passes=rate<=.08 and family_rate<=.08))
    random_walk=np.cumsum(rng.normal(size=n)); walk_diagnostic=stationarity(random_walk,'M')
    difference_diagnostic=stationarity(np.r_[np.nan,np.diff(random_walk)],'M')
    value=dict(status='PASS' if all(row['passes'] for row in results) else 'FAIL',null_settings=results,
        validation_seed=validation_seed,hac_lags=bandwidth,original_failed_simulation='synthetic_validation_initial.json',
        signal_slope=float(fitted['beta'][0]),signal_truth=1.5,signal_p=float(fitted['p'][0]),
        redundant_controls_preserve_signal=True,training_only_basis_unchanged=True,
        unit_root_example=walk_diagnostic,differenced_example=difference_diagnostic,
        interpretation='Finite AR simulations validate this implementation and error behavior in these scenarios; not a proof of universal FDR control.')
    c.write_json(c.PUBLIC/'synthetic_validation.json',value)
    if value['status']!='PASS': raise ValueError('Prespecified null validation failed; full execution is blocked')
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['fix','stationarity']); args=parser.parse_args()
    budget=c.Budget(args.action)
    try:
        result=dict(fix=reproduce_control_fix(),simulations=validate_simulations(budget)) if args.action=='fix' else build_stationarity(budget)
        print(json.dumps(result,indent=2),flush=True)
    finally: budget.close()
