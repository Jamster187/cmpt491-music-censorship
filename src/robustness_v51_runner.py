"""Execute the frozen V5.1 audit with checksummed per-candidate checkpoints."""
from __future__ import annotations
import argparse
import copy
from dataclasses import replace
import json
import platform
import time
import robustness_v51_common as c
import numpy as np
import pandas as pd
from scipy import stats
import pairwise_v5_common as v5
import pairwise_v5_stats as old
import pairwise_v5_report as previous
import pairwise_v5_diagnostics as vd
import robustness_v51_stats as s
import robustness_v51_data as data
import robustness_v51_select as selection


def audited_fit(series,**kwargs):
    result,info=s.fit(series,**kwargs)
    if info is not None:
        screens=[]
        for label in ['xr','yr']:
            values=np.full(len(series.x),np.nan);values[info['positions']]=info[label]
            screen=vd.stationarity(values,series.frequency);screens.append(screen)
        result.update(adf_x_p=screens[0]['p_value'],adf_y_p=screens[1]['p_value'],
            adf_x_status=screens[0]['status'],adf_y_status=screens[1]['status'],
            adf_x_longest_run=screens[0]['longest_run'],adf_y_longest_run=screens[1]['longest_run'])
        stationary=all(d['p_value'] is not None and d['p_value']<=.05 for d in screens)
        result['stationarity_screen']=stationary
        result['inferential_support'] &= stationary
        if not result['inferential_support']:result['p_for_family']=1.
    return result,info


def fixed_concentration(series,info):
    rows=[];pos=info['positions']
    widths={'M':[12,24,49,60],'Q':[4,8,17,20],'A':[2,3,7,10],'term':[2,4,6],'event':[2,4,7]}[series.frequency]
    for width in widths:
        for origin in range(width):
            blocks=(pos+origin)//width
            energy=np.bincount(blocks,weights=info['xr']**2)
            scores=np.bincount(blocks,weights=(info['xr']*info['error'])**2)
            rows.append(dict(width_native_periods=width,origin_offset=origin,effective_exposure_blocks=s.kish(energy),effective_score_blocks=s.kish(scores),
                maximum_exposure_fraction=float(energy.max()/energy.sum()),maximum_score_fraction=float(scores.max()/scores.sum()) if scores.sum() else None))
    return rows


def run_candidate(row,results,workspace,songviews,episodes,budget):
    started=time.perf_counter();cid=row['candidate_id'];task,name=results.locate(int(row['row_id']))
    series=s.from_workspace(workspace,task,name);output={key:[] for key in ['primary','influence_diagnostics','observation_influence','block_influence',
        'concentration_sensitivity','temporal_sensitivity','weighting_sensitivity','negative_controls','bootstrap_intervals','bootstrap_draws','permutation_draws',
        'replication_status','caring_exposure_audit']}
    def stamp(record,group,specification):
        return dict(candidate_id=cid,row_id=int(row['row_id']),group=group,specification=specification,**record)
    def record_fit(group,specification,alternative,**kwargs):
        for rank in [False,True]:
            r,_=audited_fit(alternative,ranked=rank,**kwargs)
            output[group].append(stamp(r,group,specification))
        budget.check()
    primary,info=audited_fit(series)
    if info is None:raise ValueError('Frozen estimable candidate failed reconstruction '+cid)
    for key,oldkey in [('slope','slope'),('se','slope_se'),('r','pearson_r')]:
        np.testing.assert_allclose(primary[key],row[oldkey],rtol=2e-7 if key=='r' else 1e-9,atol=1e-12)
    if primary['n']!=int(row['native_n']):raise ValueError('V5 sample did not reproduce '+cid)
    primary.update(original_r=row['pearson_r'],original_rho=row['spearman_rho'],original_slope=row['slope'],
        original_global_q=row['global_BY_q'],original_global_rank_q=row['global_rank_BY_q'],original_inferential_support=bool(row['inferential_support']))
    output['primary'].append(stamp(primary,'primary','original'))
    rankfit,rankinfo=audited_fit(series,ranked=True)
    np.testing.assert_allclose(rankfit['r'],row['spearman_rho'],rtol=2e-7,atol=1e-12)
    output['primary'].append(stamp(rankfit,'primary','original_rank'))
    for method,inner in [('pearson',info),('rank',rankinfo)]:
        output['observation_influence'] += [stamp(dict(r,method=method),'observation_influence','delete_one_native_period') for r in s.influence_rows(series,inner)]
        output['block_influence'] += [stamp(dict(r,method=method),'block_influence','original_HAC_width') for r in s.block_rows(series,inner)]
        output['concentration_sensitivity'] += [stamp(dict(r,method=method),'concentration_sensitivity','block_width_and_origin') for r in fixed_concentration(series,inner)]
    years=s.calendar_years(series);available=series.mask();positions=info['positions']
    deletion=[]
    for year in np.unique(years[available]):deletion.append(('leave_year',str(year),s.period_mask(series,f'{year}-01',f'{year+1}-01')))
    for block in np.unique(years[available]//5):deletion.append(('leave_five_year',f'{block*5}-{block*5+4}',s.period_mask(series,f'{block*5}-01',f'{block*5+5}-01')))
    for episode in episodes:
        removed=s.period_mask(series,episode['start'],episode['end'],True)
        deletion.append(('leave_recession',episode['name'],removed))
        start=str(pd.Period(episode['start'],'M')-12);end=str(pd.Period(episode['end'],'M')+12)
        deletion.append(('leave_recession_buffer12',episode['name'],s.period_mask(series,start,end,True)))
    for label,start,end in c.CONFIG['shock_windows']:
        deletion.append(('leave_shock',label,s.period_mask(series,start,end,True)))
    for kind,label,removed in deletion:
        affected=removed[positions]
        for rank in [False,True]:
            result,_=audited_fit(series,subset=~removed,ranked=rank)
            reference=rankfit if rank else primary;inner=rankinfo if rank else info
            result.update(deletion_type=kind,period=label,removed_observations=int((removed&available).sum()),
                exposure_energy_fraction_removed=float(np.sum(inner['xr'][affected]**2)/inner['sxx']),
                score_energy_fraction_removed=float(np.sum((inner['xr'][affected]*inner['error'][affected])**2)/np.sum((inner['xr']*inner['error'])**2)),
                original_slope=reference['slope'],original_r=reference['r'])
            if result['status']=='ok':
                result.update(slope_ratio=result['slope']/reference['slope'],r_change=result['r']-reference['r'],
                    same_direction=bool(result['slope']*reference['slope']>0))
            output['influence_diagnostics'].append(stamp(result,'influence_diagnostics',kind+':'+label))
        budget.check()
    # Exactly the original, adjacent and contemporaneous lags; no lag optimization.
    for lag in sorted({0,task['lag'],max(0,task['lag']-1),task['lag']+1}):
        alternative=s.from_workspace(workspace,dict(task,lag=lag),name)
        record_fit('temporal_sensitivity',f'lag_{lag}',alternative)
    for bandwidth in c.CONFIG['hac_bandwidths'][series.frequency]:record_fit('temporal_sensitivity',f'HAC_{bandwidth}',series,bandwidth=bandwidth)
    counterpart=s.from_workspace(workspace,dict(task,track='raw' if task['track']=='adjusted' else 'adjusted'),name)
    record_fit('temporal_sensitivity','opposite_track',counterpart)
    record_fit('temporal_sensitivity','intercept_only',replace(series,controls=np.ones((len(series.x),1))))
    record_fit('temporal_sensitivity','linear_time_season',replace(series,controls=s.time_controls(series)))
    composition=series.controls[:,4:] if series.controls.shape[1]>4 else None
    record_fit('temporal_sensitivity','quadratic_time_season_original_composition',replace(series,controls=s.time_controls(series,True,composition)))
    aligned=workspace.aligned(task)
    if task['track']=='adjusted':record_fit('temporal_sensitivity','add_all_genre_share_changes',replace(series,controls=aligned.controls_composition))
    else:
        for method in ['pearson','rank']:output['temporal_sensitivity'].append(stamp(dict(status='not_applicable_raw_track',method=method,p_for_family=1.),'temporal_sensitivity','add_all_genre_share_changes'))
    record_fit('temporal_sensitivity','trailing_three_native_periods',s.rolling(series))
    for start,end in c.CONFIG['windows']:
        # Fully contained native response periods only.
        subset=(series.first_month>=s.month_number(start))&(series.last_month<s.month_number(end))
        record_fit('temporal_sensitivity',f'window_{start}_{end}',series,subset=subset)
    for year in c.CONFIG['fixed_break_years']:
        result=s.break_fit(series,year)
        output['temporal_sensitivity'].append(stamp(dict(result,method='slope_change'),'temporal_sensitivity',f'fixed_break_{year}'))
    # Reproduce training-only chronological transfer instead of claiming a new holdout.
    X=series.x[available];Y=series.y[available,None];C=series.controls[available]
    for i,(start,end) in enumerate(v5.CONFIG['validation_periods'],1):
        train=series.last_month[available]<s.month_number(start)-v5.CONFIG['temporal_embargo_months']
        valid=(series.first_month[available]>=s.month_number(start))&(series.last_month[available]<s.month_number(end))
        transfer=old.forecast(X,Y,C,train,valid,series.frequency)
        old_status=row[f'fold_{i}_status'];status=old.PREDICT_STATUS[transfer['status']]
        if old_status!=status:raise ValueError('Transfer status replay differs '+cid)
        if status=='ok':np.testing.assert_allclose(transfer['skill'][0],row[f'fold_{i}_skill'],rtol=2e-6,atol=2e-7)
        output['replication_status'].append(stamp(dict(kind='C_internal_temporal_transfer',period=f'{start}/{end}',status=status,
            train_n=int(train.sum()),validation_n=int(valid.sum()),skill=float(transfer['skill'][0]),r=float(transfer['r'][0]),
            independent=False,interpretation='Exact V5 training-only control/baseline replay with 84-month embargo; these periods were already inspected'),
            'replication_status',f'original_transfer_{i}'))
    # Weight month/native-periods equally, then weight their regression by chart-song counts.
    record_fit('weighting_sensitivity','original_equal_native_period',series)
    record_fit('weighting_sensitivity','chart_song_count_weighted_regression',series,weighted=True)
    base=selection.base_name(name)
    for view in workspace.views:
        spec='population:'+view['name']
        if base not in view['values']:
            for method in ['pearson','rank']:output['weighting_sensitivity'].append(stamp(dict(status='base_measure_unavailable_or_constant',method=method,p_for_family=1.),'weighting_sensitivity',spec))
            continue
        alternative=s.from_workspace(workspace,dict(task,view_id=view['id']),base)
        record_fit('weighting_sensitivity',spec,alternative)
    # Fixed versus contemporary composition on exactly the same supported genre/month cohort.
    fixed_name='fixed_composition__'+base;matched_name='matched_composition__'+base
    if fixed_name in workspace.views[0]['values'] and matched_name in workspace.views[0]['values']:
        t=dict(task,view_id=0);a=workspace.aligned(t)
        fixed=s.from_workspace(workspace,t,fixed_name);matched=s.from_workspace(workspace,t,matched_name)
        common=fixed.mask()&matched.mask()
        for label,alternative in [('fixed_composition_common_cohort',fixed),('matched_composition_common_cohort',matched)]:
            # Use identical time/season controls for an interpretable composition contrast.
            record_fit('weighting_sensitivity',label,replace(alternative,controls=a.controls_time),subset=common)
    else:
        for label in ['fixed_composition_common_cohort','matched_composition_common_cohort']:
            for method in ['pearson','rank']:output['weighting_sensitivity'].append(stamp(dict(status='no_frozen_supported_genre_composition_view',method=method,p_for_family=1.),'weighting_sensitivity',label))
    # Changing within-month weights requires independently reconstructing that exact source aggregate.
    base_valid,reason=songviews.verify_base(base,task['view_id'])
    for weighting in ['source_equal','rank','unique_song']:
        spec='within_month_'+weighting
        if base_valid and name==base:
            values,_=songviews.aggregate(base,row['view'],weighting)
            record_fit('weighting_sensitivity',spec,data.replace_music(workspace,task,name,values))
        else:
            why=reason if name==base else 'Derived fixed/matched composition requires its original genre construction; not a direct song mean'
            for method in ['pearson','rank']:output['weighting_sensitivity'].append(stamp(dict(status='unavailable',reason=why,method=method,p_for_family=1.),'weighting_sensitivity',spec))
    for confidence in c.CONFIG['genre_confidence_thresholds']:
        spec='genre_confidence_'+confidence
        if base_valid and name==base:
            values,_=songviews.aggregate(base,row['view'],confidence=confidence)
            record_fit('weighting_sensitivity',spec,data.replace_music(workspace,task,name,values))
        else:
            for method in ['pearson','rank']:output['weighting_sensitivity'].append(stamp(dict(status='unavailable',reason=reason,method=method,p_for_family=1.),'weighting_sensitivity',spec))
    for minimum in c.CONFIG['minimum_feature_songs']:
        values,status=songviews.threshold(name,task['view_id'],minimum)
        if values is not None:record_fit('weighting_sensitivity',f'minimum_feature_songs_{minimum}',data.replace_music(workspace,task,name,values))
        else:
            for method in ['pearson','rank']:output['weighting_sensitivity'].append(stamp(dict(status='not_applicable',reason=status,method=method,p_for_family=1.),'weighting_sensitivity',f'minimum_feature_songs_{minimum}'))
    # Prespecified related classifier; the same songs do not create independent evidence.
    comparator=c.CONFIG['classifier_comparators'].get(base)
    if comparator and comparator in workspace.views[task['view_id']]['values']:
        alternative=s.from_workspace(workspace,task,comparator);common=available&alternative.mask()
        record_fit('weighting_sensitivity','related_classifier:'+comparator,alternative,subset=common)
        record_fit('weighting_sensitivity','original_classifier_common_cohort',series,subset=common)
        replication=dict(kind='B_related_classifier_robustness',status='related_construct_available',comparator=comparator,
            independent=False,interpretation='Different classifier family on the same songs; related construct, not interchangeable or independently replicated')
    else:replication=dict(kind='B_related_classifier_robustness',status='no_predeclared_comparable_classifier',comparator='',independent=False,
        interpretation='No new semantic proxy was chosen after seeing robustness results')
    output['replication_status'].append(stamp(replication,'replication_status','alternate_classifier'))
    output['replication_status'].append(stamp(dict(kind='D_independent_replication',status='not_available',independent=False,
        interpretation='No new source observations, independently sampled songs or untouched historical/future period in this retained release; no acquisition authorized'),
        'replication_status','genuinely_new_evidence'))
    for method in ['moving_pairs','calendar_year_pairs']:
        summary,draws=s.bootstrap(series,method,c.CONFIG['bootstrap_repetitions'],c.seed(cid+method),budget.check)
        output['bootstrap_intervals'].append(stamp(summary,'bootstrap_intervals',method))
        output['bootstrap_draws'] += [dict(candidate_id=cid,method=method,**r) for r in draws]
    perm,draws=s.block_permutation(series,c.CONFIG['permutation_repetitions'],c.seed(cid+'permutation'),budget.check)
    output['negative_controls'].append(stamp(perm,'negative_controls','block_permutation'))
    output['permutation_draws'] += [dict(candidate_id=cid,**r) for r in draws]
    periods_per_year={'M':12,'Q':4,'A':1,'term':.5,'event':1}[series.frequency]
    for months in c.CONFIG['future_placebo_months']:
        steps=-int(np.ceil((task['lag']+months)*periods_per_year/12))
        alternative=replace(series,x=s.shifted(series.x,steps))
        record_fit('negative_controls',f'future_external_at_least_{months}_months',alternative)
    for months in c.CONFIG['past_placebo_months']:
        steps=int(np.ceil(months*periods_per_year/12));alternative=replace(series,x=s.shifted(series.x,steps))
        record_fit('negative_controls',f'extra_past_shift_{months}_months',alternative)
    if 'mandatory_diagnostic' in row['selection_strata']:
        if series.frequency!='M':raise ValueError('Mandatory diagnostic expected monthly')
        full_months=workspace.months
        values=workspace.external['raw'][task['external']].reindex(full_months-task['lag']).to_numpy(float)
        original_y=workspace.views[task['view_id']]['values'][name].to_numpy(float)
        for i,p in enumerate(info['positions']):
            output['caring_exposure_audit'].append(dict(candidate_id=cid,music_month=str(full_months[p]),external_reference_month=str(full_months[p]-task['lag']),
                unemployment_percent=float(values[p]),change_unemployment_percentage_points=float(series.x[p]),
                residualized_change=float(info['xr'][i]),caring_month_mean=float(original_y[p]),change_caring_mean=float(series.y[p]),
                exposure_energy_fraction=float(info['xr'][i]**2/info['sxx']),
                slope_after_deleting_month=float(primary['slope']-info['deletion_delta'][i])))
    output['candidate']=row;output['runtime_seconds']=time.perf_counter()-started
    return output


def simulate(budget):
    rows=[];n=818;rng=np.random.default_rng(c.seed('null_calibration'))
    time_controls=np.column_stack([np.ones(n),np.arange(n)/12,np.sin(2*np.pi*np.arange(n)/12),np.cos(2*np.pi*np.arange(n)/12)])
    for ar in c.CONFIG['simulation_ar']:
        for scenario in ['stationary_independent','independent_rare_shocks','shared_trend_raw_control','shared_trend_differenced']:
            for rep in range(c.CONFIG['simulation_repetitions']):
                e=rng.normal(size=(n+300,2));values=np.zeros_like(e)
                for i in range(1,len(values)):values[i]=ar*values[i-1]+e[i]
                x,y=values[300:].T
                if scenario=='independent_rare_shocks':
                    x=x.copy();y=y.copy();x[rng.integers(0,n)]+=30;y[rng.integers(0,n)]+=30
                if scenario.startswith('shared_trend'):
                    trend=np.linspace(0,20,n);x=x+trend;y=y+trend
                controls=time_controls
                if scenario=='shared_trend_raw_control':controls=np.ones((n,1))
                if scenario=='shared_trend_differenced':x=np.r_[np.nan,np.diff(x)];y=np.r_[np.nan,np.diff(y)]
                series=s.Series(x,y,controls,np.ones(n),np.arange(n),np.arange(n),'M',0)
                result,_=audited_fit(series)
                rows.append(dict(ar=ar,scenario=scenario,replicate=rep,r=result.get('r'),nominal_p=result.get('nominal_p'),
                    screened_p=result.get('p_for_family'),effective_exposure_blocks=result.get('effective_exposure_blocks'),effective_score_blocks=result.get('effective_score_blocks'),
                    support=result.get('inferential_support'),
                    interpretation='No substantive music/economic variables; diagnostic null with stationary innovations or deliberately spurious deterministic common trend'))
                if rep%25==0:budget.check()
    return rows


def write_checkpoint(path,payload,fingerprint):
    c.write_json(path,dict(fingerprint=fingerprint,payload_sha256=c.digest(payload),payload=payload))


def read_checkpoint(path,fingerprint):
    value=c.read_json(path)
    if value['fingerprint']!=fingerprint or value['payload_sha256']!=c.digest(value['payload']):raise ValueError('Corrupt or incompatible checkpoint: '+str(path))
    return value['payload']


def run(limit=None):
    from threadpoolctl import threadpool_limits
    with c.Budget('candidate_execution') as budget, threadpool_limits(limits=1):
        fingerprint=c.execution_fingerprint();candidates=pd.read_csv(c.PUBLIC/'candidate_selection.csv').to_dict('records')
        results=previous.Results();workspace=old.Workspace();songs=data.SongViews(workspace,pd.DataFrame(candidates));episodes=data.recession_episodes(workspace)
        c.write_json(c.PUBLIC/'recession_episodes.json',episodes)
        completed=0;reused=0;computed=0;checkpoints=c.LOCAL/'checkpoints';checkpoints.mkdir(exist_ok=True)
        for row in candidates:
            path=checkpoints/(row['candidate_id']+'.json')
            if path.exists():read_checkpoint(path,fingerprint);reused+=1
            else:
                result=run_candidate(row,results,workspace,songs,episodes,budget)
                write_checkpoint(path,result,fingerprint);computed+=1
                print(json.dumps(dict(candidate=row['candidate_id'],seconds=round(result['runtime_seconds'],3),status='checkpointed',peak_bytes=c.peak_bytes())),flush=True)
            completed+=1;budget.check()
            if limit is not None and computed>=limit:break
        c.write_csv(c.LOCAL/f'song_view_validation_{reused:02d}_{computed:02d}.csv',songs.validation)
        c.write_json(c.PUBLIC/'execution.json',dict(status='complete' if completed==len(candidates) else 'partial_checkpoint',completed=completed,
            total=len(candidates),reused=reused,computed=computed,fingerprint=fingerprint,peak_process_bytes=c.peak_bytes()))
        if completed==len(candidates):
            target=c.LOCAL/'null_simulations.json'
            if not target.exists():write_checkpoint(target,simulate(budget),fingerprint)
            else:read_checkpoint(target,fingerprint)
            c.write_csv(c.PUBLIC/'external_source_reproduction.csv',data.overlap_reproduction(workspace,pd.DataFrame(candidates)))


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','simulate']);p.add_argument('--limit',type=int);args=p.parse_args()
    if args.action=='run':run(args.limit)
    else:
        from threadpoolctl import threadpool_limits
        with c.Budget('null_simulations') as budget, threadpool_limits(limits=1):
            fingerprint=c.execution_fingerprint();path=c.LOCAL/'null_simulations.json'
            if path.exists():read_checkpoint(path,fingerprint)
            else:write_checkpoint(path,simulate(budget),fingerprint)


if __name__=='__main__':main()
