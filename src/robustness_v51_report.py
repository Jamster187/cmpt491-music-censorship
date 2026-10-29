"""Publish complete fixed-candidate diagnostics and conservative audit outcomes."""
from __future__ import annotations
import argparse
import collections
import io
import json
import lzma
from pathlib import Path
import time
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
import pairwise_v5_common as v5
import pairwise_v5_stats as old
import pairwise_v5_report as previous
import robustness_v51_common as c
import robustness_v51_runner as runner
import robustness_v51_select as selection

TABLES=['primary','influence_diagnostics','observation_influence','block_influence','concentration_sensitivity',
    'temporal_sensitivity','weighting_sensitivity','negative_controls','bootstrap_intervals','replication_status','caring_exposure_audit']
TEST_TABLES=['primary','influence_diagnostics','temporal_sensitivity','weighting_sensitivity','negative_controls']
COLORS={'Robust exploratory candidate':'#168477','Sensitive or unstable candidate':'#cc802f',
    'Likely artifact':'#ac485d','Insufficient evidence':'#687b96'}


def load_payloads():
    fingerprint=c.execution_fingerprint();candidates=pd.read_csv(c.PUBLIC/'candidate_selection.csv')
    return [runner.read_checkpoint(c.LOCAL/'checkpoints'/f'{cid}.json',fingerprint) for cid in candidates.candidate_id]


def compare_numerical_payloads(expected,actual,rtol=1e-10,atol=1e-12):
    """Exact structure/statuses; tight documented tolerance for independent BLAS replay."""
    result=dict(float_values_compared=0,maximum_absolute_error=0.,maximum_scaled_error=0.,rtol=rtol,atol=atol)
    def compare(a,b,path='root'):
        if isinstance(a,dict):
            if not isinstance(b,dict) or a.keys()!=b.keys():raise ValueError('Replay keys changed: '+path)
            for key in a:compare(a[key],b[key],path+'/'+key)
        elif isinstance(a,list):
            if not isinstance(b,list) or len(a)!=len(b):raise ValueError('Replay array length changed: '+path)
            for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
        elif isinstance(a,float):
            if not isinstance(b,(int,float)) or isinstance(b,bool) or not np.isclose(a,b,rtol=rtol,atol=atol,equal_nan=True):raise ValueError('Replay numeric value changed: '+path)
            result['float_values_compared']+=1
            if np.isfinite(a) and np.isfinite(b):
                result['maximum_absolute_error']=max(result['maximum_absolute_error'],abs(a-b))
                result['maximum_scaled_error']=max(result['maximum_scaled_error'],abs(a-b)/max(1,abs(a)))
        elif a!=b:raise ValueError('Replay status/value changed: '+path)
    compare(v5.clean(expected),v5.clean(actual));result['canonical_bytes_equal']=c.digest(expected)==c.digest(actual)
    return result


def tables(payloads):
    frames={name:pd.DataFrame([row for value in payloads for row in value[name]]) for name in TABLES}
    family=[]
    for name in TEST_TABLES:
        frame=frames[name]
        if 'method' not in frame:frame['method']='diagnostic'
        frame['method']=frame.method.fillna('diagnostic')
        if name=='temporal_sensitivity':
            # Fixed slope-change contrasts retain their nominal diagnostics, but
            # did not run the ordinary pair's residual-stationarity screens.
            # They cannot inherit formal support merely from a large row count.
            breaks=frame.method.eq('slope_change')
            frame.loc[breaks,'inferential_support']=False
            frame.loc[breaks,'p_for_family']=1.
            frame.loc[breaks,'inference_note']='Nominal fixed-break contrast only; no comparable residual-stationarity gate, so formal diagnostic slot p=1'
        frame['test_id']=[c.digest([row['candidate_id'],name,row['specification'],row['method']])[:24] for row in frame.to_dict('records')]
        if frame.test_id.duplicated().any():raise ValueError('Repeated diagnostic test key in '+name)
        for row in frame.to_dict('records'):
            p=row.get('p_for_family',1.)
            family.append(dict(test_id=row['test_id'],candidate_id=row['candidate_id'],table=name,specification=row['specification'],method=row['method'],
                status=row['status'],p=1. if p is None or not np.isfinite(p) else float(p)))
    # Resampling intervals and transfer comparisons have no selection-valid p-value.
    # Retain explicit unit-p slots so they cannot disappear from comparison accounting.
    for name in ['bootstrap_intervals','replication_status']:
        for row in frames[name].to_dict('records'):
            key=c.digest([row['candidate_id'],name,row['specification']])[:24]
            family.append(dict(test_id=key,candidate_id=row['candidate_id'],table=name,specification=row['specification'],method='interval_or_replication_accounting',
                status=row['status'],p=1.))
    family=pd.DataFrame(family)
    if family.test_id.duplicated().any():raise ValueError('Duplicate hypothesis accounting ID')
    family['diagnostic_BY_q']=old.by_adjust(family.p.to_numpy(float))
    family['selection_adjusted_confirmation']=False
    lookup=family.set_index('test_id').diagnostic_BY_q
    for name in TEST_TABLES:frames[name]['diagnostic_BY_q']=frames[name].test_id.map(lookup)
    frames['multiple_testing']=family
    return frames


def successful(frame):return frame.loc[frame.status.eq('ok')]


def classify(row,frames):
    cid=row['candidate_id'];get=lambda name:frames[name].loc[frames[name].candidate_id.eq(cid)]
    primary=get('primary').query("method == 'pearson'").iloc[0]
    influence=get('influence_diagnostics').query("method == 'pearson'")
    deletions=influence.loc[influence.deletion_type.isin(['leave_year','leave_five_year','leave_recession'])&influence.removed_observations.gt(0)]
    usable=successful(deletions)
    temporal=get('temporal_sensitivity').query("method == 'pearson'")
    weight=get('weighting_sensitivity').query("method == 'pearson'")
    negative=get('negative_controls');boot=get('bootstrap_intervals')
    primary_sign=np.sign(primary.slope);r=float(primary.r)
    broad=min(primary.effective_exposure_blocks,primary.effective_score_blocks)>=6
    boot_ok=len(boot)==2 and boot.status.eq('ok').all() and ((boot.ci_low*primary_sign>0)&(boot.ci_high*primary_sign>0)).all()
    hac_ok=primary.ci_low*primary.ci_high>0
    deletion_ok=len(usable)>0 and len(usable)==len(deletions) and usable.same_direction.all() and usable.slope_ratio.abs().min()>=.5
    windows=temporal.loc[temporal.specification.isin([f'window_{a}_{b}' for a,b in c.CONFIG['windows'][:3]])]
    stable_windows=successful(windows);window_same=int((stable_windows.slope*primary_sign>0).sum())
    window_ok=window_same>=2 and row['positive_same_direction_folds']>=2
    required_weight=weight.loc[weight.specification.isin(['within_month_rank','within_month_unique_song'])]
    weighting=weight.loc[weight.specification.str.startswith(('within_month_','minimum_feature_songs_','genre_confidence_'))]
    weighting=successful(weighting);weight_same=float((weighting.slope*primary_sign>0).mean()) if len(weighting) else np.nan
    weight_ok=len(required_weight)==2 and required_weight.status.eq('ok').all() and len(weighting)>0 and weight_same>=.9
    lag_values={max(0,int(row['lag_months'])-1),int(row['lag_months']),int(row['lag_months'])+1}
    lags=temporal.loc[temporal.specification.isin([f'lag_{x}' for x in lag_values])]
    valid_lags=successful(lags);lag_same=float((valid_lags.slope*primary_sign>0).mean()) if len(valid_lags) else np.nan
    lag_ok=len(valid_lags)==len(lags) and len(lags)>0 and lag_same>=.9
    permutation=negative.loc[negative.specification.eq('block_permutation')].iloc[0]
    negative_ok=permutation.status=='ok' and permutation.exceedance_probability<=.05
    role=row['music_role'];base=row['base_music_variable']
    artifact_role=role in selection.EXCLUDED_ROLES or base in ['christmas_proximity_days','chart_day_of_month','chart_month_days','snapshot_day_of_month']
    supported=bool(primary.inferential_support)
    gates=dict(original_adjusted_global_correction=row['track']=='adjusted' and row['original_q_min']<=.05,
        substantive_measure=not artifact_role,primary_inference_support=supported,broad_effective_information=broad,
        hac_interval_excludes_zero=hac_ok,both_bootstrap_intervals_exclude_zero=bool(boot_ok),
        year_fiveyear_recession_deletions_stable=bool(deletion_ok),internal_temporal_stability=bool(window_ok),
        weighting_stability=bool(weight_ok),adjacent_lag_stability=bool(lag_ok),negative_control_screen=bool(negative_ok))
    opposite=temporal.loc[temporal.specification.eq('opposite_track')]
    opposite_r=float(opposite.iloc[0].r) if len(opposite) and opposite.iloc[0].status=='ok' else np.nan
    trend_lost=row['track']=='raw' and np.isfinite(opposite_r) and abs(opposite_r)<.25*abs(r)
    if all(gates.values()):outcome='Robust exploratory candidate'
    elif artifact_role or trend_lost:outcome='Likely artifact'
    elif row['original_q_min']<=.05:outcome='Sensitive or unstable candidate'
    else:outcome='Insufficient evidence'
    worst=usable.loc[(usable.slope_ratio-1).abs().idxmax()] if len(usable) else None
    future=successful(negative.loc[negative.specification.str.startswith('future_external')&negative.method.eq('pearson')])
    fixed=successful(weight.loc[weight.specification.eq('fixed_composition_common_cohort')])
    matched=successful(weight.loc[weight.specification.eq('matched_composition_common_cohort')])
    overall=successful(weight.loc[weight.specification.eq('population:overall')])
    result=dict(candidate_id=cid,row_id=row['row_id'],music_variable=row['music_variable'],external_variable=row['external_variable'],view=row['view'],
        track=row['track'],lag_months=row['lag_months'],selection_strata=row['selection_strata'],outcome=outcome,robust_gates_passed=sum(bool(v) for v in gates.values()),
        robust_gates_total=len(gates),failed_gates=';'.join(k for k,v in gates.items() if not v),
        original_r=row['pearson_r'],original_rho=row['spearman_rho'],original_global_q=row['global_BY_q'],original_global_rank_q=row['global_rank_BY_q'],
        updated_r=r,updated_slope=float(primary.slope),ci_low=float(primary.ci_low),ci_high=float(primary.ci_high),native_n=int(primary.n),
        effective_exposure_blocks=float(primary.effective_exposure_blocks),effective_score_blocks=float(primary.effective_score_blocks),
        ar1_effective_n_diagnostic=float(primary.ar1_effective_n_diagnostic),
        both_bootstrap_intervals_exclude_zero=bool(boot_ok),
        deletion_same_direction_fraction=float(usable.same_direction.mean()) if len(usable) else None,
        minimum_deletion_slope_ratio=float(usable.slope_ratio.min()) if len(usable) else None,
        most_influential_deletion=worst.specification if worst is not None else '',
        most_influential_deletion_r=float(worst.r) if worst is not None else None,
        most_influential_deletion_slope_ratio=float(worst.slope_ratio) if worst is not None else None,
        nonoverlapping_windows_estimable=len(stable_windows),nonoverlapping_windows_same_direction=window_same,
        original_positive_transfer_folds=row['positive_same_direction_folds'],weighting_same_direction_fraction=weight_same,
        adjacent_lag_same_direction_fraction=lag_same,block_permutation_p=float(permutation.exceedance_probability),
        future_placebo_max_abs_r=float(future.r.abs().max()) if len(future) else None,
        opposite_track_r=opposite_r,overall_r=float(overall.iloc[0].r) if len(overall) else None,
        fixed_composition_r=float(fixed.iloc[0].r) if len(fixed) else None,matched_composition_r=float(matched.iloc[0].r) if len(matched) else None,
        independent_replication='Unavailable; same retained songs/providers and previously inspected historical periods',
        main_confounders='Time, calendar season, genre/chart composition, feature coverage, repeated songs/artists, economic shocks, classifier and provider measurement changes; retrospective values and unknown writing/release dates')
    for _,b in boot.iterrows():
        for key in ['ci_low','ci_high','r_ci_low','r_ci_high','same_direction_fraction']:result[b.method+'_'+key]=b[key]
    return result


def summarize(frames,payloads):
    outcomes=pd.DataFrame([classify(p['candidate'],frames) for p in payloads])
    order={'Robust exploratory candidate':0,'Sensitive or unstable candidate':1,'Insufficient evidence':2,'Likely artifact':3}
    outcomes['sort_outcome']=outcomes.outcome.map(order);outcomes['min_effective_blocks']=outcomes[['effective_exposure_blocks','effective_score_blocks']].min(axis=1)
    outcomes['absolute_r']=outcomes.updated_r.abs()
    outcomes=outcomes.sort_values(['sort_outcome','robust_gates_passed','min_effective_blocks','absolute_r','candidate_id'],ascending=[True,False,False,False,True]).drop(columns=['sort_outcome','absolute_r'])
    outcomes.insert(0,'audit_rank',np.arange(1,len(outcomes)+1))
    c.write_csv(c.PUBLIC/'candidate_outcomes.csv',outcomes)
    primary=frames['primary'].query("method == 'pearson'")
    family=frames['multiple_testing']
    summary=dict(candidates=len(outcomes),outcomes=outcomes.outcome.value_counts().to_dict(),robust_candidates=int(outcomes.outcome.eq('Robust exploratory candidate').sum()),
        candidates_not_meeting_robust_rule=int(outcomes.outcome.ne('Robust exploratory candidate').sum()),
        primary_reproductions=len(primary),diagnostic_family_slots=len(family),diagnostic_BY_below_point05=int(family.diagnostic_BY_q.le(.05).sum()),
        broadly_supported_exposure_and_score=int((outcomes.min_effective_blocks>=6).sum()),
        both_bootstrap_intervals_exclude_zero=int(outcomes.both_bootstrap_intervals_exclude_zero.sum()),
        independent_replications=0,total_candidate_seconds=sum(p['runtime_seconds'] for p in payloads),
        bootstrap_repetitions_per_method=c.CONFIG['bootstrap_repetitions'],bootstrap_fits=sum(len(p['bootstrap_draws']) for p in payloads),
        block_permutation_repetitions=c.CONFIG['permutation_repetitions'],block_permutation_fits=sum(len(p['permutation_draws']) for p in payloads),
        new_discovery_search=False,original_global_correction_preserved=True,selected_sensitivity_q_values_are_not_confirmatory=True)
    c.write_json(c.PUBLIC/'result_summary.json',summary)
    deletions=frames['influence_diagnostics'].query("method == 'pearson' and status == 'ok'").copy()
    deletions=deletions.loc[deletions.removed_observations.gt(0)]
    deletions['absolute_relative_coefficient_change']=(deletions.slope_ratio-1).abs()
    worst=deletions.loc[deletions.groupby(['candidate_id','deletion_type']).absolute_relative_coefficient_change.idxmax()]
    worst=worst.merge(outcomes[['candidate_id','outcome']],on='candidate_id',validate='many_to_one')
    c.write_csv(c.PUBLIC/'most_influential_periods.csv',worst)
    period_summary=worst.groupby(['outcome','deletion_type','period'],sort=True).size().rename('candidates').reset_index()
    c.write_csv(c.PUBLIC/'influential_period_summary.csv',period_summary)
    views=v5.load(v5.LOCAL/'views.pkl');external=v5.load(v5.LOCAL/'external.pkl')['metadata'];measurements=[]
    for p in payloads:
        row=p['candidate'];view=next(v for v in views if v['name']==row['view']);m=view['metadata'][row['music_variable']];e=external[row['external_variable']]
        measurements.append(dict(candidate_id=row['candidate_id'],music_variable=row['music_variable'],music_definition=m.get('definition',''),
            music_source=';'.join(m.get('source',[])),source_informed_role=row['music_role'],observed_music_months=row['observed_music_months'],
            nonzero_music_months=row['nonzero_music_months'],external_variable=row['external_variable'],external_definition=e.get('definition',''),
            external_source=';'.join(e.get('source',[])),external_units=e['units'],native_frequency=row['native_frequency'],
            independent_replication=False))
    c.write_csv(c.PUBLIC/'candidate_measurement_audit.csv',measurements)
    return outcomes,summary


def simulation_summary():
    rows=runner.read_checkpoint(c.LOCAL/'null_simulations.json',c.execution_fingerprint());frame=pd.DataFrame(rows);summaries=[]
    for (ar,scenario),d in frame.groupby(['ar','scenario'],sort=True):
        n=len(d)
        for mode,probability in [('nominal_HAC',d.nominal_p),('sample_and_stationarity_screen',d.screened_p),
            ('also_six_effective_blocks',d.screened_p.where((d.effective_exposure_blocks>=6)&(d.effective_score_blocks>=6),1.))]:
            k=int((probability<=.05).sum());center=(k/n+1.96**2/(2*n))/(1+1.96**2/n)
            radius=1.96*np.sqrt(k/n*(1-k/n)/n+1.96**2/(4*n*n))/(1+1.96**2/n)
            summaries.append(dict(ar=ar,scenario=scenario,mode=mode,repetitions=n,rejections=k,rate=k/n,
                monte_carlo_wilson_low=max(0,center-radius),monte_carlo_wilson_high=min(1,center+radius)))
    c.write_csv(c.PUBLIC/'null_simulations.csv',frame);result=pd.DataFrame(summaries);c.write_csv(c.PUBLIC/'null_simulation_summary.csv',result)
    return result


def source_reproduction_report():
    """A numeric source replay must have observations; empty equality is no replay."""
    from robustness_v51_data import overlap_reproduction
    values=overlap_reproduction(old.Workspace(),pd.read_csv(c.PUBLIC/'candidate_selection.csv'))
    for row in values:
        if row.get('common_native_observations')==0:
            row.update(status='no_common_native_observations',
                interpretation='The aliases describe a derived measure absent from one native table. Empty overlap is not numerical reproduction; no independent source evidence.')
    c.write_csv(c.PUBLIC/'external_source_reproduction.csv',values)
    return values


def short_label(row):
    label=str(row['music_variable']).replace('matched_composition__','matched: ').replace('fixed_composition__','fixed: ').replace('lyric_','').replace('_',' ')
    if len(label)>39:label=label[:36]+'…'
    return f"{row['candidate_id']} · {row['view']} · {label}"


def figures(frames,outcomes,payloads):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm
    plt.rcParams.update({'font.size':9,'axes.titlesize':13,'svg.hashsalt':'cmpt491-v51','axes.spines.top':False,'axes.spines.right':False})
    destination=c.PUBLIC/'figures';destination.mkdir(exist_ok=True);catalog=[]
    order=outcomes.sort_values('candidate_id');ids=order.candidate_id.tolist();labels=[short_label(r) for r in order.to_dict('records')]
    def save(fig,name,description):
        path=destination/(name+'.svg');fig.savefig(path,bbox_inches='tight',metadata={'Date':None,'Creator':'CMPT 491 V5.1'})
        c.atomic(path,('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n').encode())
        fig.savefig(Path('/tmp')/('cmpt491_v51_'+name+'.png'),dpi=130,bbox_inches='tight');plt.close(fig)
        catalog.append(dict(file='figures/'+name+'.svg',description=description,sha256=c.sha(path)))
    primary=frames['primary'].query("method == 'pearson'").set_index('candidate_id').loc[ids]
    boot=frames['bootstrap_intervals'].query("method == 'moving_pairs'").set_index('candidate_id').loc[ids]
    fig,ax=plt.subplots(figsize=(11,12));positions=np.arange(len(ids))
    for i,cid in enumerate(ids):
        color=COLORS[order.iloc[i].outcome];r=primary.loc[cid,'r']
        ax.plot([primary.loc[cid,'r_ci_low'],primary.loc[cid,'r_ci_high']],[i-.13]*2,color='#9aa1aa',lw=2)
        ax.plot([boot.loc[cid,'r_ci_low'],boot.loc[cid,'r_ci_high']],[i+.13]*2,color=color,lw=2)
        ax.scatter([r],[i],color=color,s=20,zorder=3)
    ax.axvline(0,color='black',lw=.7);ax.set(yticks=positions,yticklabels=labels,xlim=(-1,1),xlabel='Partial correlation: original fit and 95% diagnostic intervals',title='Original V5 effects under block-resampling scrutiny\nGrey: linearized HAC interval · colored: moving-block interval · dot: original effect')
    ax.invert_yaxis();ax.grid(axis='x',alpha=.2);save(fig,'original_and_resampling','All 30 original effects with HAC and moving-block intervals; selection uncertainty is not removed')
    opposite=frames['temporal_sensitivity'].query("method == 'pearson' and specification == 'opposite_track'").set_index('candidate_id')
    fig,ax=plt.subplots(figsize=(11,11))
    for i,(_,row) in enumerate(order.iterrows()):
        other=opposite.loc[row.candidate_id]
        if other.status!='ok':continue
        raw,adjusted=(row.updated_r,other.r) if row.track=='raw' else (other.r,row.updated_r)
        ax.plot([raw,adjusted],[i,i],color='#a4a4a4',lw=1)
        ax.scatter(raw,i,color='#b56b29',s=25,label='Raw values' if i==0 else None)
        ax.scatter(adjusted,i,color='#267c8e',s=25,label='Time-series adjusted' if i==0 else None)
    ax.axvline(0,color='black',lw=.7);ax.set(yticks=positions,yticklabels=labels,xlim=(-1,1),xlabel='Pearson / partial Pearson correlation',
        title='Raw versus time-series-adjusted estimates for every frozen pair\nSame music variable, external series, population and lag; eligible samples may differ')
    ax.invert_yaxis();ax.legend(loc='lower right');save(fig,'raw_vs_adjusted','Raw versus adjusted counterpart effects; no new pair or best-specification selection')
    deletion=frames['influence_diagnostics'].query("method == 'pearson' and deletion_type == 'leave_year'").copy()
    deletion['year']=deletion.period.astype(int);matrix=deletion.pivot(index='candidate_id',columns='year',values='slope_ratio').reindex(ids)
    fig,ax=plt.subplots(figsize=(12,11));values=matrix.to_numpy(float);im=ax.imshow(np.clip(values,-1,3),aspect='auto',cmap='RdBu',norm=TwoSlopeNorm(1,-1,3))
    ax.set(yticks=positions,yticklabels=labels,title='Leave-one-year-out coefficient stability\n1 = unchanged coefficient; negative values = sign reversal; colors clipped to [−1, 3]',xlabel='Deleted response-calendar year (native periods touching that year)')
    tick=np.arange(0,len(matrix.columns),5);ax.set_xticks(tick,matrix.columns[tick],rotation=45);fig.colorbar(im,ax=ax,label='Deleted-year slope / original slope',shrink=.65)
    save(fig,'leave_year_out','Every response-year deletion; full unclipped estimates are in influence_diagnostics.csv')
    lag=frames['temporal_sensitivity'].query("method == 'pearson'");lag=lag.loc[lag.specification.str.startswith('lag_')].copy();lag['lag']=lag.specification.str[4:].astype(int)
    matrix=lag.pivot(index='candidate_id',columns='lag',values='r').reindex(ids)
    fig,ax=plt.subplots(figsize=(11,11));im=ax.imshow(matrix.to_numpy(float),aspect='auto',vmin=-1,vmax=1,cmap='RdBu_r')
    ax.set(yticks=positions,yticklabels=labels,xticks=np.arange(len(matrix.columns)),xticklabels=matrix.columns,
        title='Frozen lag sensitivity: original, adjacent and contemporaneous\nBlank cells were not tested; no best-lag reselection',xlabel='External reference-month lag before music')
    fig.colorbar(im,ax=ax,label='Partial Pearson r',shrink=.6);save(fig,'lag_sensitivity','All prespecified lag comparisons without selecting an improved lag')
    fig,axes=plt.subplots(1,2,figsize=(12,10),sharey=True)
    for i,(_,row) in enumerate(order.iterrows()):
        axes[0].scatter(row.effective_exposure_blocks,i,color=COLORS[row.outcome],s=24)
        axes[1].scatter(row.effective_score_blocks,i,color=COLORS[row.outcome],s=24)
    for ax,label in zip(axes,['Exposure-energy effective blocks','OLS-score-energy effective blocks']):
        ax.axvline(6,color='#888888',ls='--');ax.set_xscale('log');ax.set_xlabel(label);ax.grid(axis='x',alpha=.2)
    axes[0].set_yticks(positions,labels);axes[0].invert_yaxis();fig.suptitle('Nominal sample size does not equal independent information\nKish concentration diagnostics at the original HAC block width; dashed line = six-block screen')
    save(fig,'influence_concentration','Effective exposure and score block counts for every candidate, not inferred independent sample sizes')
    neg=frames['negative_controls'].loc[frames['negative_controls'].specification.eq('block_permutation')].set_index('candidate_id').loc[ids]
    fig,ax=plt.subplots(figsize=(11,11))
    for i,cid in enumerate(ids):
        ax.plot([neg.loc[cid,'null_r_low'],neg.loc[cid,'null_r_high']],[i,i],color='#9aa1aa',lw=3)
        ax.scatter(primary.loc[cid,'r'],i,color=COLORS[order.iloc[i].outcome],s=24,zorder=3)
    ax.axvline(0,color='black',lw=.7);ax.set(yticks=positions,yticklabels=labels,xlim=(-1,1),xlabel='Partial correlation',
        title='Negative controls retain local temporal ordering\nGrey: middle 95% of block-permuted correlations · dot: observed correlation')
    ax.invert_yaxis();save(fig,'negative_controls','Observed effects against diagnostic block-permutation distributions; exchangeability is not guaranteed')
    caring=frames['caring_exposure_audit'];cid=caring.candidate_id.iloc[0]
    fig,axes=plt.subplots(2,1,figsize=(11,7),gridspec_kw={'height_ratios':[2,1]})
    dates=pd.to_datetime(caring.external_reference_month);axes[0].plot(dates,caring.exposure_energy_fraction*100,color='#385c91',lw=1)
    axes[0].set(ylabel='Share of total exposure energy (%)',title=f'{cid}: caring–unemployment information is concentrated in specific months\nExternal unemployment-change month; the music observation follows six months later')
    largest=caring.nlargest(8,'exposure_energy_fraction').sort_values('exposure_energy_fraction');axes[1].barh(largest.external_reference_month,largest.exposure_energy_fraction*100,color='#385c91')
    axes[1].set_xlabel('Residual unemployment-change energy (%)');fig.tight_layout()
    save(fig,'caring_exposure','Full and leading-month exposure shares for the mandatory diagnostic, using the public BLS unemployment series')
    c.write_csv(c.PUBLIC/'figure_catalog.csv',catalog)


def markdown_table(frame,columns):
    labels=[label for _,label in columns];rows=['| '+' | '.join(labels)+' |','| '+' | '.join(['---']*len(labels))+' |']
    for row in frame.to_dict('records'):
        values=[]
        for key,_ in columns:
            value=row.get(key,'')
            if isinstance(value,(float,np.floating)):value='—' if not np.isfinite(value) else f'{value:.4g}'
            values.append(str(value).replace('|','/'))
        rows.append('| '+' | '.join(values)+' |')
    return '\n'.join(rows)


def documentation(frames,outcomes,summary,simulations):
    candidates=pd.read_csv(c.PUBLIC/'candidate_selection.csv');mandatory=candidates.loc[candidates.selection_strata.str.contains('mandatory_diagnostic')].iloc[0];cid=mandatory.candidate_id
    result=outcomes.set_index('candidate_id').loc[cid];primary=frames['primary'].query("candidate_id == @cid and method == 'pearson'").iloc[0]
    influence=frames['influence_diagnostics'].query("candidate_id == @cid and method == 'pearson'")
    caring=frames['caring_exposure_audit'];top=caring.nlargest(1,'exposure_energy_fraction').iloc[0]
    origin=frames['concentration_sensitivity'].query("candidate_id == @cid and method == 'pearson' and width_native_periods == 49")
    year2020=influence.loc[influence.specification.eq('leave_year:2020')].iloc[0]
    pandemic=influence.loc[influence.specification.eq('leave_shock:pandemic')].iloc[0]
    largest_deletions=influence.loc[influence.deletion_type.isin(['leave_year','leave_five_year','leave_recession','leave_shock'])&influence.removed_observations.gt(0)].copy()
    largest_deletions['change']=(largest_deletions.slope_ratio-1).abs();largest_deletions=largest_deletions.sort_values('change',ascending=False).head(12)
    boot=frames['bootstrap_intervals'].query('candidate_id == @cid')
    temporal=frames['temporal_sensitivity'].query("candidate_id == @cid and method == 'pearson'");lag=temporal.loc[temporal.specification.str.startswith('lag_')]
    weight=frames['weighting_sensitivity'].query("candidate_id == @cid and method == 'pearson'");weight=weight.loc[weight.specification.isin(['population:overall','within_month_source_equal','within_month_rank','within_month_unique_song',
        'genre_confidence_high','genre_confidence_medium_or_high','minimum_feature_songs_10','minimum_feature_songs_20','fixed_composition_common_cohort','matched_composition_common_cohort'])]
    neg=frames['negative_controls'].query('candidate_id == @cid');perm=neg.loc[neg.specification.eq('block_permutation')].iloc[0]
    outcomes_table=outcomes[['candidate_id','music_variable','external_variable','view','lag_months','updated_r','min_effective_blocks','outcome']]
    outcomes_table=outcomes_table.sort_values('candidate_id')
    lines=['# V5.1 robustness and replication findings','',
        f"The completed audit covers **{summary['candidates']} frozen V5 candidates**. **{summary['robust_candidates']} meet every prespecified robustness requirement**; {summary['candidates_not_meeting_robust_rule']} do not. Outcome counts: "+'; '.join(f'{k}: {v}' for k,v in sorted(summary['outcomes'].items()))+'.','',
        'A failed robustness label is not proof that the population association is exactly zero. It means these selected historical results do not supply the required breadth, stability and uncertainty evidence. Small original q-values remain in the record; this audit does not rewrite V5.','',
        f"All {summary['primary_reproductions']} primary estimates and original chronological transfer calculations reproduce. The audit adds {summary['bootstrap_fits']:,} paired-block resamples and {summary['block_permutation_fits']:,} block permutations. It records {summary['diagnostic_family_slots']:,} diagnostic comparison slots, including unsupported specifications and comparisons without a valid new p-value. Their BY correction is **not selection-adjusted independent confirmation**.",'',
        '## R&B / Soul caring and unemployment','',
        f"The mandatory case is {cid}, chosen by the general corrected-lyrical rule as well as the explicit diagnostic requirement. The original six-month-lag association reproduces at r={primary.r:.6f}, slope={primary.slope:.6g} caring-score change per percentage-point unemployment change, N={int(primary.n)} months, and original global BY q={mandatory.global_BY_q:.6g}. Its original rank association is much smaller: rho={mandatory.spearman_rho:.6f}, global rank q={mandatory.global_rank_BY_q:.4g}. The slope's 95% HAC interval is [{primary.ci_low:.6g}, {primary.ci_high:.6g}].",'',
        f"The **{primary.effective_exposure_blocks:.4f} effective exposure blocks** reproduce numerically. They are a Kish concentration statistic for squared residual exposure in 49-month blocks, not a count of independent months or a fitted degrees-of-freedom estimate. The largest single exposure is **{top.external_reference_month}**, matched to music in **{top.music_month}**, contributing **{100*top.exposure_energy_fraction:.2f}%** of the total residual exposure energy. The corresponding unemployment change is {top.change_unemployment_percentage_points:.4g} percentage points. Moving the block origin through every offset yields effective exposure counts from {origin.effective_exposure_blocks.min():.4f} to {origin.effective_exposure_blocks.max():.4f}. The concentration is therefore not created solely by the original arbitrary block boundary.",'',
        f"No calculation error was found in that concentration statistic. The AR(1) effective-N shortcut gives {primary.ar1_effective_n_diagnostic:.0f}, illustrating why weak lag-one correlation alone does not establish widely distributed exposure information. The interpretation is concentrated unemployment variation and limited independent episode support, not a literal replacement of {int(primary.n)} months by 1.47 independent observations.",'',
        f"Deleting response-calendar 2020 changes the estimate to r={year2020.r:.5f}, slope={year2020.slope:.6g} ({year2020.slope_ratio:.3f} times the original slope). Excluding the predefined 2020–2022 shock window from either exposure or response support changes it to r={pandemic.r:.5f}, slope={pandemic.slope:.6g}. These deletions diagnose concentration; they are not estimates of a causal pandemic effect.",'',
        markdown_table(boot,[('method','Resampling'),('ci_low','Slope 95% low'),('ci_high','Slope 95% high'),('same_direction_fraction','Same-sign draws'),('successful','Successful draws')]),'',
        'The moving-block procedure retains roughly four years of monthly ordering. The calendar-year resampling keeps within-year dependence and can miss longer persistence. Neither repairs the lack of independent historical episodes or uncertainty from the original selection. Both refit the full nuisance-control span in every resample.','',
        markdown_table(largest_deletions,[('specification','Deleted period'),('removed_observations','Removed N'),('exposure_energy_fraction_removed','Exposure share removed'),('r','Remaining r'),('slope_ratio','Remaining slope / original')]),'',
        '### Lag, weighting and composition','',
        markdown_table(lag,[('specification','Lag specification'),('n','N'),('r','r'),('ci_low','Slope CI low'),('ci_high','Slope CI high'),('diagnostic_BY_q','Diagnostic q')]),'',
        markdown_table(weight,[('specification','Weight/cohort specification'),('status','Status'),('inferential_support','Inference support'),('n','N'),('r','r'),('ci_low','Slope CI low'),('ci_high','Slope CI high')]),'',
        'Overall, within-genre and fixed-composition estimates have different target populations. Fixed and matched composition are compared on identical supported-genre months with identical time/season controls. Missing fixed-composition months are not filled. The source-row and distinct-song versions differ only where the original monthly release repeats a song/month; this is a small weighting sensitivity, not independent replication.','',
        'For caring, the fixed/matched composition comparison has only 264 months, below the original six 49-month-block support floor of 294. Its point estimates are descriptive, with formal diagnostic p=1. Rank weighting, high-confidence genre restriction and minimum available-song thresholds change the result materially; these also change the measured song cohort and do not diagnose a particular genre label as wrong.','',
        f"The caring case's block-permutation exceedance probability is {perm.exceedance_probability:.4g}. This checks whether a shifted placement of locally ordered exposure blocks produces similarly large correlations; nonstationary shocks can violate exchangeability, so it is a diagnostic rather than an exact randomization test. Future-exposure comparisons are explicitly placebos and never forecasting predictors.",'',
        markdown_table(neg.loc[neg.method.eq('pearson')],[('specification','Negative control'),('n','N'),('r','r'),('nominal_p','Nominal p'),('diagnostic_BY_q','Diagnostic q')]),'',
        f"**Outcome: {result.outcome}.** Failed requirements: {result.failed_gates.replace(';',', ')}. There is no second retained classifier that independently measures caring on a new song sample. Alternate emotion or sentiment labels were not substituted after seeing these results.",'',
        '## All candidates, including failures and controls','',
        markdown_table(outcomes_table,[('candidate_id','ID'),('music_variable','Music measure'),('external_variable','External'),('view','Population'),('lag_months','Lag'),('updated_r','r'),('min_effective_blocks','Min effective blocks'),('outcome','Outcome')]),'',
        'The calendar rows are real timing associations, but they do not establish musical-content responses to economic conditions. Semantic reference-corpus counts measure construction/provenance; strong raw associations with expanding economic aggregates are not changes in lyrical meaning. The corrected substantive rows retain concentration and stability warnings. The four strongest failed domain comparisons remain failed candidates, not discoveries rescued by specification changes.','',
        '**Most influential years:** among the 19 sensitive/unstable candidates, the largest one-year coefficient change occurs in 2020 for 12 candidates, 2021 for four, and 2022 for three. These counts describe correlated selected comparisons, not 19 independent confirmations of one historical mechanism. Complete period attribution is in `most_influential_periods.csv` and `influential_period_summary.csv`.','',
        '**Strongest remaining numerical leads:** R&B/Soul featured-artist credit-marker share versus continued claims at six months (C19), and Pop OTHER-POS-token share versus continued claims at 24 months (C13), pass ten of eleven operational gates but fail the breadth-of-information gate. Their minimum exposure/score effective counts are about 1.07 and 1.02. A featured-credit marker is literal credit syntax, and OTHER-POS share is a rare parser category (nonzero in only 46 Pop months), not a broad emotional theme. Their measurement definitions are explicit in `candidate_measurement_audit.csv`. Neither qualifies as a robust musical-content discovery.','',
        'Every candidate has complete year, five-year, recession, shock, lag, trend, native-frequency, genre, coverage and weighting results in the CSV tables. `candidate_outcomes.csv` gives the most influential deletion, bootstrap intervals, lag/weight sign agreement, fixed-composition estimates and all failed classification gates. `observation_influence.csv.xz` contains all observation-level leverage, Cook distance and coefficient-deletion diagnostics, without restricted raw economic values.','',
        '## Null simulations and negative controls','',
        markdown_table(simulations.loc[simulations['mode'].isin(['nominal_HAC','also_six_effective_blocks'])],[('ar','AR(1)'),('scenario','Simulation'),('mode','Screen'),('rejections','Rejections / 200'),('rate','Rate'),('monte_carlo_wilson_low','MC 95% low'),('monte_carlo_wilson_high','MC 95% high')]),'',
        'The deliberately shared-trend raw scenario is a spurious-association control, not a stationary zero-slope null. Stationary simulations use independent innovations; the rare-shock scenario has independent shock locations. These finite simulations assess this implementation under declared generating processes and do not validate every assumption in the historical data. Full results, including stationarity-only screens, are preserved.','',
        '**Inferential calibration limitation:** at AR(1)=0.9, the stationary independent null rejects in 21/200 cases (10.5%, Monte Carlo 95% interval approximately 7.0%–15.5%) at nominal 5%. The six-effective-block screen does not fix this persistence case. Thus the original HAC approximation and the new diagnostic q-values must not be presented as validated false-discovery control for all these historical series. The audit retains this failure; it does not tune bandwidths until the simulation looks favorable. Block intervals offer another sensitivity view, not a demonstrated universal repair.','',
        'Twenty-six of 28 candidates with adequate permutation support have nominal block-permutation exceedance probabilities at or below 0.05; two additional candidates have insufficient permutation support. Passing that diagnostic is plainly not sufficient for the full robustness label. Future exposures, original rank associations, influential-period removal and coverage/weighting checks remain visible even when less favorable.','',
        '## Replication and next research decision','',
        '**Independent replications: zero.** Reproduction (A) succeeded for the V5 calculations; specification and measurement robustness (B) was tested; nonoverlapping historical windows and original chronological transfers (C) provide internal stability evidence. They reuse the same inspected history. Same-provider values in the historical and financial releases are checked in `external_source_reproduction.csv`, but their agreement is not new evidence (D). Related classifier-family comparisons reuse the songs and usually measure neighboring constructs.','',
        'No candidate presently justifies a nonlinear or conditional discovery campaign on the strength of this audit alone. The next defensible research step would be genuinely independent measurements or prospectively held-out observations under a locked protocol, with enough separate economic episodes and validated lyrical measurement. More flexibility cannot create information absent from the exposure history. No new source acquisition, broad search, or nonlinear campaign was launched.','',
        'Read [methodology](methodology.md), [validation](validation.json), [resource ledger](resource_ledger.json), [all candidate outcomes](candidate_outcomes.csv) and the [figure catalog](figure_catalog.csv).']
    c.atomic(c.PUBLIC/'findings.md',('\n'.join(lines)+'\n').encode())
    method='''# V5.1 frozen robustness protocol

This is a bounded audit of previously selected historical associations, authorized separately from V5. The parent is `5f6ab14`. Original data, model outputs, q-values and private source snapshots are read-only. The exact scientific settings and input hashes are in `selection_freeze.json`; code hashes are in `execution_freeze.json`. An initial cultural-index routing error was corrected before any robustness fits, with the draft retained locally and the correction recorded in `preexecution_selection_audit.json`.

Before publication, boundary validation identified an omitted January–April 1958 recession fragment in the available lag-support data. The first complete attempt was preserved locally; the same frozen candidates, estimators, lags and seeds were rerun with that fragment included. An empty provider overlap is also explicitly unsupported, and one BLAS thread is enforced for execution. `prepublication_corrections.json` records these engineering corrections. Candidate selection was not changed. Independent numerical replay requires identical structure/statuses and float agreement at rtol=1e-10, atol=1e-12; saved checkpoint and published-file hashes are checked exactly.

## Candidate selection

Selection uses the complete V5 corrected results and complete local ranking indexes, not the first 200 public rows. Sixteen corrected adjusted lyrical candidates, four corrected adjusted nonlyrical candidates, four corrected raw candidates, one strongest failed adjusted lyrical comparison in each of four external superdomains, and two raw secular-trend controls are selected. The mandatory caring/unemployment row is unioned without preference in the outcome ranking; it was already selected. The list contains 30 distinct result rows. Cross-domain provenance and V5 native-sample eligibility are required. Source quality/count/provenance roles are excluded from the lyrical stratum.

Within corrected strata, sorting uses broad effective variation, then positive same-direction chronological folds, effect magnitude, original global q, coverage span, sample size and row ID. Repeated lags/transforms of a base music/view/external-root/track are collapsed and no more than two external roots per music/view/track are retained within a stratum. Raw corrected selection covers the available superdomains first. Failed comparisons use the existing full V5 domain order and never new audit outcomes. The final outcome ranking applies identical gates to every candidate, including caring.

## Alignment and estimation

The exact V5 aligned native-period arrays are reused. Monthly, quarterly and annual observations stay at their natural frequency. Positive lag means external reference period before the music response. Adjacent lags use the same explicit V5 availability/end-period rule. Calendar gaps remain gaps in HAC calculations, resampling and rolling means. September 2026 is the retained partial month-end chart snapshot; chart month is not the writing or release date.

The primary specification reproduces the original Pearson/OLS and rank-regression effects. Adjusted tracks retain original native changes/growth and differenced music, time/season and declared genre-share controls. SVD preserves the complete nuisance span. Every point fit requires at least 12 residual degrees of freedom. Short samples can produce descriptive estimates, but their formal diagnostic p-value is one unless the original native-count floor, at least six HAC-length blocks, and both residual ADF screens pass. ADF uses the longest contiguous observed run and the frozen V5 lag rule; failure or absence is not silently converted to success. Passing ADF is not proof of stationarity.

Bartlett HAC is computed on the original period grid. The baseline bandwidth is 48 months, 16 quarters or six years, with the V5 conservative block-count t degrees of freedom. Shorter/longer bandwidths are sensitivity checks, not selected substitutes. WLS uses the correctly weighted estimating scores and independent reference tests. The implementation is checked against [statsmodels HAC](https://www.statsmodels.org/dev/generated/statsmodels.stats.sandwich_covariance.cov_hac.html); the library's regular-spacing assumption is handled by retaining the complete calendar grid.

## Influence and temporal comparisons

All observed native periods receive full-model leverage, Cook distance and exact analytic coefficient-deletion diagnostics. Each response year and calendar-aligned five-year block is deleted and the full model refitted. Recession deletions use all available frozen NBER dated membership runs, including the left-censored January–April 1958 fragment before the first chart month and a separate 12-month buffer sensitivity; only observed historical recession membership is used. The fragment's earlier start is not invented. Shock windows are fixed at 1973–1975, 1980–1982, 1987–1988, 2000–2002, 2007–2009 and 2020–2022. Recession/shock removal deletes any row whose response or lagged exposure support intersects the window. These comparisons diagnose influence, not event causality.

The observation table's `dfbeta` field divides the coefficient-deletion change by the full-fit ordinary-OLS standard error. It is a descriptive standardized deletion measure, not an externally studentized DFBETAS statistic or an additional independent-observation test.

Squared residual exposure and squared OLS estimating-score energy are grouped into the original HAC-length blocks. Kish effective counts, maximum shares, and every possible origin offset for four predetermined block widths are retained. These are concentration diagnostics, not calibrated independent sample sizes. AR(1) effective-N values are also diagnostics only; they do not override a dominant historical shock.

Temporal specifications are the original lag, both adjacent nonnegative lags, contemporaneous alignment, the opposite raw/adjusted track, intercept-only controls, linear or quadratic time/season controls, original genre controls, additional genre-share changes for adjusted rows, and a strictly trailing three-native-period mean. Windows are 1958–1989, 1990–2009, 2010–September 2026, pre-2020, and 2020–September 2026. Fully contained native response periods are required. Fixed 1985/2000/2010 slope-change checks include the original exposure and a post-period intercept as nuisance terms; they are stability diagnostics for the fixed pair, not a conditional model search or chosen pandemic breakpoint.

The fixed-break contrasts retain nominal HAC uncertainty, but have no comparable residual-stationarity screen for the interaction design. Publication marks their formal inference unsupported and contributes p=1 to the diagnostic family. Their coefficients and nominal uncertainty remain available; a large row count alone does not confer formal support.

The original three chronological transfers are independently replayed with training-only nuisance fitting, explicit baselines and the 84-month embargo. Later years have been inspected repeatedly. A positive internal transfer is not untouched or independent confirmation.

Effects concern frozen model scores and textual proxies, not calibrated human-annotated lyrical prevalence. Missing lyrics, modern-classifier time-domain drift, uncertain genre assignments, changing chart rules, retrospective provider revisions and unknown lyric-writing dates remain potential confounders. Time blocks preserve local shared-month dependence but do not exhaustively model artist dependence across distant decades.

## Weighting, genre and measurement

Every fixed pair is compared across the available frozen genre views and overall view without pooling genres as independent economic observations. Month/native-period OLS is contrasted with regression weighted by distinct chart-song counts. Song-level source means must first reproduce V5 exactly before rank weighting (101 minus monthly rank), distinct-song-per-month weighting or genre-confidence filtering is allowed. Repeated song/months are deduplicated deterministically only in the named sensitivity; the source is preserved. Feature-specific minimum available-song counts are 5, 10 and 20. Dynamic/derived aggregates without a reproducible source mean remain explicit unavailable cases.

Fixed and contemporaneously weighted composition summaries use V5's frozen pre-1983 supported-genre weights. Their intersection cohort and time/season controls are identical; missing genres/months are never renormalized or imputed. Overall estimates and within-genre estimates target different populations. Related classifier substitutions follow the mapping frozen before new fits. Caring has no independently comparable retained classifier. Reusing songs or a different genre-confidence threshold is measurement sensitivity, not independent replication.

## Resampling and negative controls

Each candidate gets 999 overlapping noncircular moving-block paired resamples, with block lengths 49 months, 17 quarters or seven years, and 999 paired calendar-year resamples. Annual/event/term series use five-year groups for the second method because a one-year resample would retain no annual serial dependence. X, Y and every nuisance-control row are sampled together; the full nuisance design is refitted through an orthonormal representation. Sampling occurs on the complete native grid before missing rows are dropped. Rank-deficient resamples are retained as failures; at least 90% must be valid. Percentile intervals are conditional stability diagnostics, do not cover variable-selection uncertainty, and can be unreliable under changing distributions or too few independent episodes. Year blocks may miss dependence spanning years. The rationale follows the stationary dependent-data framework of [Künsch (1989)](https://doi.org/10.1214/aos/1176347265); it is not a guarantee for these nonstationary historical measurements.

Each candidate also gets 499 permutations of residual exposure blocks (12 months, four quarters or five years), keeping local ordering and its missingness pattern within blocks. The exceedance proportion uses the plus-one convention. Its validity as an exact test would require exchangeability that economic shocks may violate; it is labeled diagnostic. Future external values at least 12 and 60 months after the response, and additional past shifts of 60/120 months, are fixed placebos. They use no circular wrap or interpolation; future comparisons are never forecasting features. Quarterly/annual shifts round upward in native periods to ensure the indicated minimum future separation.

Null calibration uses independent AR(1) innovations at 0, 0.6 and 0.9, with 200 repetitions for each stationary, independent-rare-shock, deliberately shared-trend raw, and shared-trend-differenced scenario. All simulation outcomes and Monte Carlo Wilson intervals are saved. These simulations expose specific weaknesses rather than certifying universal null calibration.

## Multiplicity and outcomes

Original global V5 q-values, covering all 18,046,656 method hypotheses, remain prerequisites for a robust discovery candidate. Every attempted analytic audit comparison enters a single diagnostic BY family; unsupported fits use p=1. Bootstrap intervals and replication-status comparisons get explicit p=1 accounting slots because no new valid hypothesis p-value is supplied. Resampling repetitions, concentration summaries and analytic influence coefficients are not separate searched hypotheses. The resulting diagnostic q-values describe these selected comparisons; they do not repair data-dependent candidate selection. [Benjamini and Yekutieli's dependency correction](https://www.math.tau.ac.il/~ybenja/depApr27.pdf) addresses multiplicity under valid p-values, not invalid effective-information assumptions or selective reporting.

A robust exploratory label requires a substantive adjusted globally corrected original, primary support, six effective exposure and score blocks, sign-consistent original HAC and both block intervals, all applicable year/five-year/recession deletions retaining direction and at least half the slope, at least two same-direction nonoverlapping windows and two positive original transfer folds, at least 90% same-direction weighting and adjacent-lag fits, and block-permutation diagnostic p<=0.05. Required missing evidence fails the gate. Known calendar/provenance measures, or raw trends losing at least 75% of their correlation after adjustment, are classified as likely artifacts **as musical-content discoveries**. Remaining corrected failures are sensitive/unstable; uncorrected cases are insufficient evidence. No positive outcome is required.

## Reproducibility and resources

Deterministic candidate-specific seeds, atomic checksummed JSON checkpoints and a cumulative ledger enforce the four-hour/15-GB limits. One candidate was deliberately completed and stopped before resumption. Corrupt or mismatched checkpoints fail clearly. The publication excludes resampling draws and restricted raw series; it includes complete statistical summaries and a public-BLS-only caring diagnostic. Original assets and every V5 input/output are hashed before and after the audit. No acquisition, broad relationship search, conditional discovery or nonlinear campaign is authorized here.
'''
    c.atomic(c.PUBLIC/'methodology.md',method.encode())
    readme=f'''# V5.1 cross-domain robustness and replication

The fixed-candidate audit is complete: **{summary['candidates']} candidates; {summary['robust_candidates']} pass the full robustness rule; no independent replications**. Start with [findings](findings.md), [all outcomes](candidate_outcomes.csv) and [methodology](methodology.md). The original V5 results remain unchanged.

| File | Contents |
| --- | --- |
| [candidate_selection.csv](candidate_selection.csv), [selection_freeze.json](selection_freeze.json) | Frozen selection, original estimates, source roles, complete-ranking hashes and rules |
| [candidate_measurement_audit.csv](candidate_measurement_audit.csv) | Actual measurement definitions, source roles and nonzero-month support |
| [primary.csv](primary.csv) | Reproduced Pearson and rank estimates, uncertainty and support |
| [influence_diagnostics.csv](influence_diagnostics.csv) | Every year, five-year, recession and shock deletion |
| [observation_influence.csv.xz](observation_influence.csv.xz) | Complete leverage, Cook distance and exact native-period coefficient deletion |
| [block_influence.csv](block_influence.csv), [concentration_sensitivity.csv](concentration_sensitivity.csv) | Exposure/score concentration and block-origin sensitivity |
| [most_influential_periods.csv](most_influential_periods.csv) | Largest coefficient changes per candidate and deletion type |
| [temporal_sensitivity.csv](temporal_sensitivity.csv) | All fixed lag, window, trend, smoothing, HAC and breakpoint comparisons |
| [weighting_sensitivity.csv](weighting_sensitivity.csv) | All genre, rank, unique-song, coverage, confidence and composition comparisons |
| [bootstrap_intervals.csv](bootstrap_intervals.csv) | Both block-resampling intervals, failures and direction frequencies |
| [negative_controls.csv](negative_controls.csv), [null_simulation_summary.csv](null_simulation_summary.csv) | Block permutation, future/past placebos and dependent-data null calibration |
| [replication_status.csv](replication_status.csv), [external_source_reproduction.csv](external_source_reproduction.csv) | Reproduction vs robustness vs internal transfer vs genuinely independent evidence |
| [multiple_testing.csv](multiple_testing.csv) | Complete diagnostic comparison accounting; not selection-adjusted confirmation |
| [caring_exposure_audit.csv](caring_exposure_audit.csv) | Trace of the required caring–unemployment case using public BLS values |
| [figure_catalog.csv](figure_catalog.csv) | Seven deterministic shareable SVG figures |
| [validation.json](validation.json), [resource_ledger.json](resource_ledger.json) | Tests, preservation, replay, restart and cumulative resources |

Run from the canonical repository with the existing V5 Python environment (NumPy, pandas, SciPy, statsmodels, Matplotlib; versions recorded in the parent frozen protocol). No network acquisition or new dependencies are needed.

```bash
# Public-only integrity and numerical classification/accounting checks.
python3 src/robustness_v51_report.py verify

# Full retained-local audit; includes original data/V5 preservation.
python3 src/robustness_v51_report.py verify --private

# Deterministic numerical replay of one complete candidate, without replacing it.
python3 src/robustness_v51_report.py verify --private --replay C29

# Resume/reconstruct; existing frozen candidates and code must match.
python3 src/robustness_v51_select.py
python3 src/robustness_v51_runner.py run
python3 src/robustness_v51_report.py build
python3 -m unittest discover -s tests -v
```

Complete candidate checkpoints, bootstrap/permutation draws, preserved selection draft and source hashes remain ignored under `data/experiments/cross_domain_discovery_v5_robustness/`. These require retained V5 inputs, including restricted source snapshots absent from a fresh clone. Checkpoint recovery validates hashes and reuses completed work. A changed scientific protocol requires a separate version rather than overwriting this audit.

The result does not establish that all population associations are zero. It establishes that these selected candidates lack the complete robustness and independent-evidence requirements. No follow-on nonlinear or conditional campaign was started.
'''
    c.atomic(c.PUBLIC/'README.md',readme.encode())


def manifest():
    paths=list(c.PUBLIC.rglob('*'))+list((c.ROOT/'src').glob('robustness_v51_*.py'))+[c.ROOT/'tests/test_robustness_v51.py']
    excluded={'publication_manifest.json','resource_ledger.json'}
    c.write_json(c.PUBLIC/'publication_manifest.json',dict(files={str(p.relative_to(c.ROOT)):c.sha(p) for p in sorted(paths) if p.is_file() and p.name not in excluded},
        original_v5_commit=c.CONFIG['parent_commit'],mutable_resource_ledger_separate=True))


def build():
    with c.Budget('publication') as budget:
        payloads=load_payloads();frames=tables(payloads)
        for name,frame in frames.items():
            if name=='observation_influence':c.atomic(c.PUBLIC/(name+'.csv.xz'),lzma.compress(frame.to_csv(index=False,float_format='%.17g').encode()))
            else:c.write_csv(c.PUBLIC/(name+'.csv'),frame)
        validations=[]
        for path in sorted(c.LOCAL.glob('song_view_validation_*.csv')):
            if path.stat().st_size>2:validations.append(pd.read_csv(path))
        if validations:c.write_csv(c.PUBLIC/'song_view_reconstruction.csv',pd.concat(validations,ignore_index=True).drop_duplicates())
        outcomes,summary=summarize(frames,payloads);sim=simulation_summary();source_reproduction_report();figures(frames,outcomes,payloads)
        documentation(frames,outcomes,summary,sim);budget.check();manifest()
        print(json.dumps(summary,indent=2),flush=True)


def verify(private=False,replay=None):
    publication=c.read_json(c.PUBLIC/'publication_manifest.json')
    for name,expected in publication['files'].items():
        if c.sha(c.ROOT/name)!=expected:raise ValueError('Publication changed: '+name)
    freeze=c.read_json(c.PUBLIC/'selection_freeze.json')
    if c.sha(c.PUBLIC/'candidate_selection.csv')!=freeze['candidate_sha256']:raise ValueError('Candidate selection changed')
    candidates=pd.read_csv(c.PUBLIC/'candidate_selection.csv');outcomes=pd.read_csv(c.PUBLIC/'candidate_outcomes.csv')
    if set(candidates.candidate_id)!=set(outcomes.candidate_id) or len(outcomes)!=len(candidates):raise ValueError('Candidate outcome coverage mismatch')
    family=pd.read_csv(c.PUBLIC/'multiple_testing.csv')
    reference=multipletests(family.p.to_numpy(float),method='fdr_by')[1]
    np.testing.assert_allclose(reference,family.diagnostic_BY_q,rtol=1e-10,atol=1e-14)
    result=dict(status='PASS',publication_files=len(publication['files']),candidates=len(candidates),diagnostic_family_slots=len(family),
        independent_BY_maximum_error=float(np.max(abs(reference-family.diagnostic_BY_q))))
    public_frames={name:pd.read_csv(c.PUBLIC/(name+'.csv')) for name in ['primary','influence_diagnostics','temporal_sensitivity','weighting_sensitivity','negative_controls','bootstrap_intervals']}
    calculated=pd.DataFrame([classify(row,public_frames) for row in candidates.to_dict('records')]).set_index('candidate_id')
    saved=outcomes.set_index('candidate_id').loc[calculated.index]
    for field in ['outcome','failed_gates','most_influential_deletion']:
        if not calculated[field].fillna('').equals(saved[field].fillna('')):raise ValueError('Outcome classification does not reproduce: '+field)
    for field in ['updated_r','updated_slope','effective_exposure_blocks','effective_score_blocks','robust_gates_passed']:
        np.testing.assert_allclose(calculated[field],saved[field],rtol=1e-10,atol=1e-12,equal_nan=True)
    source=pd.read_csv(c.PUBLIC/'external_source_reproduction.csv')
    if ((source.status=='same_provider_overlap_reproduced')&source.common_native_observations.fillna(0).le(0)).any():raise ValueError('Empty source overlap falsely labelled reproduced')
    result['all_outcome_rules_reproduced_from_public_tables']=True
    if private:
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=1):
            regenerated=selection.select()
            # Compare exact original records through the same serialization path.
            body=pd.DataFrame(regenerated).to_csv(index=False,float_format='%.17g').encode()
            if __import__('hashlib').sha256(body).hexdigest()!=freeze['candidate_sha256']:raise ValueError('Candidate rules do not reproduce frozen selection')
            payloads=load_payloads();frames=tables(payloads)
            for name in TABLES:
                body=frames[name].to_csv(index=False,float_format='%.17g').encode()
                path=c.PUBLIC/(name+'.csv.xz' if name=='observation_influence' else name+'.csv')
                actual=lzma.decompress(path.read_bytes()) if name=='observation_influence' else path.read_bytes()
                if body!=actual:raise ValueError('Public table failed saved-checkpoint replay: '+name)
            restart=c.read_json(c.PUBLIC/'restart_initial.json')
            if c.sha(c.LOCAL/'checkpoints/C01.json')!=restart['checkpoint_sha256']:raise ValueError('Restarted candidate was modified')
            result.update(selection_reproduced=True,complete_checkpoint_tables_reproduced=len(TABLES),deliberately_resumed_candidate_unchanged=True,
                original_assets=c.verify_preservation(True),v5_publication=previous.verify())
            if replay:
                selected=next(p for p in payloads if p['candidate']['candidate_id']==replay)
                results=previous.Results();workspace=old.Workspace()
                from robustness_v51_data import SongViews,recession_episodes
                songs=SongViews(workspace,candidates)
                class Check:
                    def check(self):pass
                replayed=runner.run_candidate(selected['candidate'],results,workspace,songs,recession_episodes(workspace),Check())
                original=dict(selected);replayed.pop('runtime_seconds');original.pop('runtime_seconds')
                result['deterministic_candidate_replay']=replay
                result['candidate_replay_numerics']=compare_numerical_payloads(original,replayed)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','verify','manifest']);p.add_argument('--private',action='store_true');p.add_argument('--replay');args=p.parse_args()
    if args.action=='build':build()
    elif args.action=='manifest':manifest()
    else:
        with c.Budget('verification') as budget:
            value=verify(args.private,args.replay);print(json.dumps(v5.clean(value),indent=2),flush=True)


if __name__=='__main__':main()
