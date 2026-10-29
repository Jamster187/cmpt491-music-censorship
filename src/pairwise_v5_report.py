"""Read-only result interpretation, complete local index rankings and public summaries.

Ranking rules are declared before inspecting the exhaustive campaign output.
Raw ranks by absolute Pearson r (categorical: sqrt(partial eta squared)).
Adjusted ranks supported stationary fits first, then effect magnitude.
Domain/genre/lag rankings include both tracks and prefer supported adjusted fits.
Stability ranks completed positive, same-direction transfer folds before strength.
All ineligible estimates remain at the end of their complete index ranking.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import resource
import subprocess
import time
import numpy as np
import pandas as pd
from scipy import stats
import pairwise_v5_common as c
import pairwise_v5_stats as engine
import pairwise_v5_runner as runner
import pairwise_v5_diagnostics as diagnostics

RANKINGS=['raw','adjusted','historically_stable','financial','macroeconomic','political_social',
          'within_genre','between_genre','lagged','multiple_testing']
SUMMARY_NAMES={'raw':'raw_relationships','adjusted':'adjusted_relationships','historically_stable':'historical_stability',
    'within_genre':'genre_relationships','between_genre':'between_genre_relationships','lagged':'lagged_relationships',
    'multiple_testing':'multiple_testing','financial':'financial_relationships','macroeconomic':'macroeconomic_relationships',
    'political_social':'political_social_relationships'}


def atomic_npy(path,value): c.atomic(path,runner.encode(value))


class Results:
    def __init__(self):
        self.rows=np.load(c.LOCAL/'results.npy',mmap_mode='r',allow_pickle=False)
        self.plan=c.load(c.LOCAL/'plan.pkl'); self.views=c.load(c.LOCAL/'views.pkl'); self.external=c.load(c.LOCAL/'external.pkl')['metadata']
        self.offsets=np.array([t['offset'] for t in self.plan],dtype=np.int64)
        self.names=[list(v['values']) for v in self.views]
        dictionary=pd.read_csv(c.ROOT/'analysis/music_enrichment_v2/feature_dictionary.csv').set_index('feature')
        self.source_roles=dictionary.column_role.to_dict()

    def role(self,name,metadata):
        base=name.removeprefix('fixed_composition__').removeprefix('matched_composition__')
        pipeline=metadata.get('role','measurement')
        return pipeline if pipeline in ['sample_size','genre_composition'] else self.source_roles.get(base,pipeline)

    def locate(self,index):
        chunk=int(np.searchsorted(self.offsets,index,side='right')-1)
        task=self.plan[chunk]; column=int(index-task['offset'])
        return task,self.names[task['view_id']][column]

    def record(self,index,rank=None):
        task,name=self.locate(index); row=self.rows[index]; music=self.views[task['view_id']]['metadata'][name]; external=self.external[task['external']]
        category=task['external_kind']=='categorical'; q=float(row['q']); q_rank=float(row['q_rank'])
        quantile=stats.t.ppf(.975,float(row['df'])) if np.isfinite(row['df']) and row['df']>0 else np.nan
        folds_ok=row['fold_status']==0; folds_good=folds_ok & (row['fold_skill']>0)
        if not category: folds_good &= row['fold_r']*row['r']>0
        flags=['exploratory; previously inspected historical periods','chart month is not lyric-writing or release date','latest/revised external snapshot; incomplete historical vintages']
        if task['track']=='raw': flags.append('raw association; secular trend may explain result')
        if row['inferential']!=1: flags.append('failed/unsupported stationarity or estimability screen; formal p=1')
        if row['status']!=0: flags.append(engine.STATUS[int(row['status'])])
        if max(abs(row['trend_x']),abs(row['trend_y']))>.7: flags.append('strong time correlation')
        if max(abs(row['acf_x']),abs(row['acf_y']))>.6: flags.append('strong lag-one autocorrelation')
        if folds_ok.sum()<3: flags.append('not all chronological folds estimable')
        role=self.role(name,music)
        if role in ['sample_size','provenance_or_quality','quality_diagnostic']: flags.append('source labels this as count/provenance/quality; inspect its definition before interpreting content')
        if name.startswith(('fixed_composition__','matched_composition__')): flags.append('fixed supported-genre subset; incomplete months excluded')
        if row['last_month']==817: flags.append('September 2026 chart snapshot ends September 19')
        first=str(pd.Period(c.CONFIG['months'][0],'M')+int(row['first_month'])) if row['first_month']>=0 else ''
        last=str(pd.Period(c.CONFIG['months'][0],'M')+int(row['last_month'])) if row['last_month']>=0 else ''
        result=dict(rank=rank,row_id=int(index),chunk_id=task['chunk_id'],music_variable=name,external_variable=task['external'],
            music_domain=music['domain'],external_domain=task['external_domain'],music_family=music['family'],music_role=role,
            pipeline_music_role=music.get('role','measurement'),
            population=task['population'],genre=task['genre'],view=self.views[task['view_id']]['name'],
            composition_relationship=bool(name.startswith('genre_share__')),track=task['track'],lag_months=task['lag'],
            timing='contemporaneous' if task['lag']==0 else 'external precedes music by declared reference-month lag',
            native_frequency=task['frequency'],music_units=music.get('units','source units'),external_units=external['units'],
            transformation='Raw observed values; intercept only' if task['track']=='raw' else c.CONFIG['music_adjustment']+' External: '+external['transformation'],
            method='categorical HAC omnibus' if category else 'Pearson/OLS and rank-regression Spearman',
            status=engine.STATUS[int(row['status'])],inferential_support=bool(row['inferential']),
            pearson_r=float(row['r']),spearman_rho=float(row['rho']),partial_eta_squared=float(row['eta_squared']),
            slope=float(row['slope']),intercept=float(row['intercept']),slope_se=float(row['se']),
            slope_ci_low=float(row['slope']-quantile*row['se']),slope_ci_high=float(row['slope']+quantile*row['se']),
            direction='categorical omnibus; see contrasts' if category else 'positive' if row['slope']>0 else 'negative' if row['slope']<0 else 'undefined',
            native_n=int(row['n']),contributing_music_months=int(row['n_months']),first_month=first,last_month=last,
            control_rank=int(row['control_rank']),inference_df=float(row['df']),hac_lags=int(row['hac_lags']),
            nominal_p=float(row['p']),nominal_rank_p=float(row['p_rank']),global_BY_q=q,global_rank_BY_q=q_rank,
            any_global_BY_rejection=bool(q<=.05 or q_rank<=.05),
            rejected_methods='; '.join((['categorical omnibus'] if category and q<=.05 else ['Pearson/OLS'] if q<=.05 else [])+(['rank association'] if q_rank<=.05 else [])),
            month_weighted_r=float(row['r']),chart_song_weighted_r=float(row['r_song_weighted']),
            chart_song_weighted_slope=float(row['slope_song_weighted']),
            acf_external=float(row['acf_x']),acf_music=float(row['acf_y']),
            time_correlation_external=float(row['trend_x']),time_correlation_music=float(row['trend_y']),
            adf_external_p=float(row['stationarity_x']),adf_music_p=float(row['stationarity_y']),
            effective_n_ar1_diagnostic=float(row['effective_n_ar1_diagnostic']),
            completed_transfer_folds=int(folds_ok.sum()),positive_same_direction_folds=int(folds_good.sum()),
            observed_music_months=int(self.views[task['view_id']]['values'][name].notna().sum()),
            nonzero_music_months=int((self.views[task['view_id']]['values'][name].fillna(0)!=0).sum()),
            external_source=json.dumps(external['source']),external_availability=external['availability'],
            methodological_breaks=external.get('methodological_breaks',''),limitations=' | '.join(flags))
        for i in range(3):
            result.update({f'fold_{i+1}_status':engine.PREDICT_STATUS[int(row['fold_status'][i])],
                f'fold_{i+1}_r':float(row['fold_r'][i]),f'fold_{i+1}_skill':float(row['fold_skill'][i]),f'fold_{i+1}_mae':float(row['fold_mae'][i])})
        return c.clean(result)


def classifications(results):
    n=len(results.rows); domain=np.empty(n,dtype='u1'); track=np.empty(n,dtype='u1'); scope=np.empty(n,dtype='u1'); lag=np.empty(n,dtype='u1'); category=np.empty(n,bool); view=np.empty(n,dtype='u1')
    domains=sorted({t['external_domain'] for t in results.plan}); domain_id={name:i for i,name in enumerate(domains)}
    for task in results.plan:
        a=task['offset']; b=a+task['music_variables']; names=results.names[task['view_id']]
        domain[a:b]=domain_id[task['external_domain']]; track[a:b]=int(task['track']=='adjusted'); lag[a:b]=task['lag']
        view[a:b]=task['view_id']
        scope[a:b]=1 if task['population']=='within_genre' else 0
        if task['population']=='overall': scope[a:b]=np.array([2 if name.startswith('genre_share__') else 0 for name in names],dtype='u1')
        category[a:b]=task['external_kind']=='categorical'
    return dict(domain=domain,track=track,scope=scope,lag=lag,category=category,view=view,domain_id=domain_id)


def ranking_mask(name,r,labels):
    if name=='raw': return labels['track']==0
    if name=='adjusted': return labels['track']==1
    if name=='within_genre': return labels['scope']==1
    if name=='between_genre': return labels['scope']==2
    if name=='lagged': return labels['lag']>0
    if name=='multiple_testing': return (r['q']<=.05)|(r['q_rank']<=.05)
    if name in ['financial','macroeconomic']: return labels['domain']==labels['domain_id'][name]
    if name=='political_social': return np.isin(labels['domain'],[labels['domain_id'][d] for d in ['political','social']])
    return np.ones(len(r),bool)


def rankings(results,budget):
    r=results.rows; labels=classifications(results); valid=r['status']==0
    effect=np.where(labels['category'],np.sqrt(r['eta_squared']),abs(r['r'])).astype(float)
    effect=np.nan_to_num(effect,nan=-1.)
    support=(valid & (r['inferential']==1)).astype('u1')
    ok=r['fold_status']==0
    stable=(ok & (r['fold_skill']>0) & (labels['category'][:,None] | (r['fold_r']*r['r'][:,None]>0))).sum(axis=1)
    completed=ok.sum(axis=1)
    summaries={}; catalog=[]
    for name in RANKINGS:
        mask=ranking_mask(name,r,labels); indexes=np.flatnonzero(mask); keys=[indexes,-r['n'][indexes].astype(int),-stable[indexes],-effect[indexes]]
        # np.lexsort's final key is the primary key. Invalid entries remain complete.
        if name=='historically_stable': keys=[indexes,-effect[indexes],-stable[indexes],-completed[indexes]]
        elif name not in ['raw','adjusted','multiple_testing']: keys.extend([-labels['track'][indexes].astype(int),-support[indexes].astype(int)])
        elif name in ['adjusted','multiple_testing']: keys.append(-support[indexes].astype(int))
        keys.append(-valid[indexes].astype(int)); order=indexes[np.lexsort(tuple(keys))]
        path=c.LOCAL/'rankings'/f'{name}.npy'; atomic_npy(path,order.astype('<u8'))
        selected=[results.record(int(index),rank=i+1) for i,index in enumerate(order[:200])]
        summaries[name]=selected; c.write_csv(c.PUBLIC/(SUMMARY_NAMES[name]+'.csv'),pd.DataFrame(selected,columns=list(results.record(0,rank=1))))
        catalog.append(dict(name=name,rows=len(order),summary_rows=len(selected),local_file=str(path.relative_to(c.ROOT)),sha256=c.sha(path),
            definition='Complete index ranking for declared subset; joins to results.npy and search_space.csv',
            order='Estimable first; '+('absolute effect, positive same-direction fold count, native N, deterministic row ID' if name=='raw' else
            'completed folds, positive same-direction folds, absolute effect, row ID' if name=='historically_stable' else
            'stationarity-supported first, adjusted before raw where both tracks apply, absolute effect, stability, native N, row ID')))
        budget.check(True)
    c.write_csv(c.PUBLIC/'leaderboard_catalog.csv',catalog)
    return summaries,labels


def summarize(results,labels):
    rows=[]; domains=[]; r=results.rows
    for task in results.plan:
        a=task['offset']; b=a+task['music_variables']; value=r[a:b]
        methods=1 if task['external_kind']=='categorical' else 2
        rows.append(dict(view=results.views[task['view_id']]['name'],population=task['population'],track=task['track'],frequency=task['frequency'],
            domain=task['external_domain'],lag=task['lag'],pair_track_rows=len(value),method_hypotheses=methods*len(value),
            estimable=int(np.sum(value['status']==0)),inferential=int(np.sum(value['inferential']==1)),
            global_BY_pair_rejections=int(np.sum((value['q']<=.05)|(value['q_rank']<=.05))),
            positive_all_three_folds=int(np.sum(np.all((value['fold_status']==0)&(value['fold_skill']>0),axis=1))),
            **{status:int(np.sum(value['status']==i)) for i,status in enumerate(engine.STATUS)}))
    frame=pd.DataFrame(rows); keys=['view','population','track','frequency','domain','lag']; number=[x for x in frame if x not in keys]
    c.write_csv(c.PUBLIC/'coverage_and_status.csv',frame.groupby(keys,sort=True,dropna=False)[number].sum().reset_index())
    domain=frame.groupby(['domain','track'],sort=True)[number].sum().reset_index()
    c.write_csv(c.PUBLIC/'domain_summary.csv',domain)
    # Raw and adjusted rows have identical per-chunk variable ordering. The
    # comparison includes every pair, even where the adjusted fit is unsupported.
    changes=[]; total_raw_strong=0; adjusted_estimable=0; decreased=0
    for raw,adjusted in zip(results.plan[::2],results.plan[1::2]):
        if raw['track']!='raw' or adjusted['track']!='adjusted' or raw['external']!=adjusted['external']: raise ValueError('Pair-track alignment changed')
        a=r[raw['offset']:raw['offset']+raw['music_variables']]; b=r[adjusted['offset']:adjusted['offset']+adjusted['music_variables']]
        strong=(a['status']==0)&(abs(a['r'])>=.5); comparable=strong&(b['status']==0); lost=comparable&(abs(b['r'])<.1)
        total_raw_strong+=int(strong.sum()); adjusted_estimable+=int(comparable.sum()); decreased+=int(lost.sum())
        for j in np.flatnonzero(lost):
            changes.append((float(abs(a['r'][j])-abs(b['r'][j])),raw['offset']+int(j),adjusted['offset']+int(j)))
    changes.sort(key=lambda v:(-v[0],v[1])); exported=[]
    for rank,(delta,a,b) in enumerate(changes[:200],1):
        original=results.record(a); changed=results.record(b)
        exported.append(dict(rank=rank,music_variable=original['music_variable'],external_variable=original['external_variable'],view=original['view'],lag_months=original['lag_months'],
            raw_r=original['pearson_r'],adjusted_r=changed['pearson_r'],raw_q=original['global_BY_q'],adjusted_q=changed['global_BY_q'],
            raw_n=original['native_n'],adjusted_n=changed['native_n'],raw_row_id=a,adjusted_row_id=b,absolute_correlation_drop=delta))
    c.write_csv(c.PUBLIC/'disappeared_after_adjustment.csv',exported)
    value=dict(pair_track_rows=len(r),estimable_pair_track_rows=int(np.sum(r['status']==0)),inferential_pair_track_rows=int(np.sum(r['inferential']==1)),
        BY_rejected_pair_track_rows=int(np.sum((r['q']<=.05)|(r['q_rank']<=.05))),
        raw_absolute_r_at_least_half=total_raw_strong,with_estimable_adjusted_match=adjusted_estimable,
        dropping_below_absolute_r_point_one=decreased,status_counts={name:int(np.sum(r['status']==i)) for i,name in enumerate(engine.STATUS)})
    c.write_json(c.PUBLIC/'result_summary.json',value)
    return value,domain,exported


def interpretation_audit(results,budget):
    """Post-fit diagnostics only: no changed estimates, p-values or BY family."""
    indexes=np.load(c.LOCAL/'rankings/multiple_testing.npy'); workspace=engine.Workspace(); records=[]; influence=[]
    for index in indexes:
        index=int(index); record=results.record(index); task,name=results.locate(index)
        if task['external_kind']=='categorical':
            record.update(exposure_effective_blocks=None,score_effective_blocks=None,concentration_screen='categorical; no numeric exposure audit')
        else:
            a=workspace.aligned(task); j=results.names[task['view_id']].index(name)
            controls=a.controls_composition if a.profiles[j]=='composition' else a.controls_time
            mask=np.isfinite(a.x.astype(float))&np.isfinite(a.y[:,j])&np.isfinite(controls).all(axis=1)&np.isfinite(a.weights)&(a.weights>0)
            positions=np.flatnonzero(mask); C=controls[mask]; basis=engine.control_basis(C)
            x=a.x[mask].astype(float); y=a.y[mask,j]; block=positions//(c.CONFIG['hac_lags'][a.frequency]+1)
            diagnostics_for_pair=[]
            methods=['Pearson/OLS'] if record['global_BY_q']<=.05 else []
            if record['global_rank_BY_q'] is not None and record['global_rank_BY_q']<=.05: methods.append('rank association')
            for method in methods:
                X=stats.rankdata(x) if method=='rank association' else x
                Y=stats.rankdata(y) if method=='rank association' else y
                xr=engine.residualize(basis,X); yr=engine.residualize(basis,Y); beta=float(xr@yr/(xr@xr)); error=yr-beta*xr
                energy=np.bincount(block,weights=xr*xr); score=np.bincount(block,weights=(xr*error)**2)
                effective=lambda a:float(a.sum()**2/(a@a)) if a@a>0 else 0.
                e=effective(energy); q=effective(score)
                diagnostics_for_pair.append((e,q))
                influence.append(dict(row_id=index,music_variable=name,external_variable=task['external'],view=record['view'],track=task['track'],lag_months=task['lag'],method=method,
                    observed_native_periods=len(x),calendar_blocks=len(energy),effective_exposure_blocks=e,effective_score_blocks=q,
                    largest_exposure_block_fraction=float(energy.max()/energy.sum()),largest_score_block_fraction=float(score.max()/score.sum()) if score.sum()>0 else None,
                    concentrated_variation=bool(min(e,q)<c.CONFIG['minimum_hac_blocks'])))
            e=min(v[0] for v in diagnostics_for_pair); q=min(v[1] for v in diagnostics_for_pair)
            record.update(exposure_effective_blocks=e,score_effective_blocks=q,
                concentration_screen='concentrated; fewer than six effective exposure/score blocks' if min(e,q)<6 else 'at least six effective exposure and score blocks')
        records.append(record)
        if len(records)%50==0: budget.check()
    frame=pd.DataFrame(records); c.write_csv(c.PUBLIC/'corrected_relationships_complete.csv',frame)
    c.write_csv(c.PUBLIC/'corrected_influence_diagnostics.csv',influence)
    if len(frame):
        frame['all_three_transfer_positive']=frame.positive_same_direction_folds.eq(3)
        frame['concentrated']=frame.concentration_screen.str.startswith('concentrated;')
        role=frame.groupby(['music_role','track'],sort=True).agg(corrected_pair_track_rows=('row_id','size'),
            positive_all_three_folds=('all_three_transfer_positive','sum'),concentrated_numeric_rows=('concentrated','sum')).reset_index()
        content=frame.loc[frame.track.eq('adjusted') & frame.music_domain.str.startswith('lyric') & ~frame.music_role.isin(['sample_size','provenance_or_quality','quality_diagnostic'])].copy()
        content=content.sort_values(['positive_same_direction_folds','completed_transfer_folds','rank'],ascending=[False,False,True],kind='stable')
    else: role=pd.DataFrame(); content=pd.DataFrame()
    c.write_csv(c.PUBLIC/'corrected_by_measurement_role.csv',role)
    c.write_csv(c.PUBLIC/'adjusted_lyrical_corrected_leads.csv',content)
    crosswalk=[]
    for view in results.views:
        for name,metadata in view['metadata'].items():
            crosswalk.append(dict(view=view['name'],music_variable=name,pipeline_music_role=metadata.get('role','measurement'),
                source_informed_role=results.role(name,metadata),role_source='Published enrichment feature dictionary where available; original V5 role otherwise'))
    c.write_csv(c.PUBLIC/'measurement_role_crosswalk.csv',crosswalk)
    qualifying=content.loc[content.positive_same_direction_folds.ge(2)&content.concentration_screen.eq('at least six effective exposure and score blocks')] if len(content) else content
    summary=dict(corrected_rows=len(records),numeric_corrected_rows=len({r['row_id'] for r in influence}),
        numeric_rows_with_concentrated_variation=int(frame.concentrated.sum()) if len(frame) else 0,
        corrected_adjusted_lyrical_rows=len(content),adjusted_lyrical_rows_with_two_positive_folds_and_broad_variation=len(qualifying),
        diagnostic_status='Post-fit sensitivity/interpretation audit; original estimates, global family and q values unchanged',
        concentration_rule='Kish effective block count (sum energy)^2/sum(energy^2), separately for residual exposure energy and OLS score energy; six-block flag matches the original count floor but is an additional post-fit diagnostic.',
        source_role_policy='Propagate the published feature dictionary role through fixed/matched composition; retain the original pipeline role and every tested row.')
    c.write_json(c.PUBLIC/'interpretation_audit.json',summary)
    return summary


def saved_estimate_sensitivities(results,labels):
    """Summarize already fitted weighting/composition comparators; no new fits."""
    r=results.rows; weighting=[]
    for track,label in [(0,'raw'),(1,'adjusted')]:
        for scope in ['overall','within_genre']:
            use=(labels['track']==track)&((labels['scope']==1) if scope=='within_genre' else (labels['scope']!=1))
            use &= (r['status']==0)&np.isfinite(r['r'])&np.isfinite(r['r_song_weighted'])
            a=r['r'][use].astype(float); b=r['r_song_weighted'][use].astype(float); difference=abs(a-b)
            weighting.append(dict(track=label,population=scope,comparable_pairs=len(a),
                median_absolute_correlation_change=float(np.median(difference)) if len(a) else None,
                p95_absolute_correlation_change=float(np.quantile(difference,.95)) if len(a) else None,
                maximum_absolute_correlation_change=float(np.max(difference)) if len(a) else None,
                sign_changes=int(np.sum(a*b<0)),sign_changes_with_both_absolute_r_above_point01=int(np.sum((a*b<0)&(abs(a)>.01)&(abs(b)>.01))),
                interpretation='Equal native-period weighting versus distinct chart-song population count weighting; descriptive only'))
    c.write_csv(c.PUBLIC/'weighting_sensitivity.csv',weighting)
    names=results.names[0]; indexes={n:i for i,n in enumerate(names)}
    bases=[n[len('fixed_composition__'):] for n in names if n.startswith('fixed_composition__')]
    planned=collections.Counter(); counts=collections.Counter(); three=collections.Counter(); comparisons=[]
    for task in results.plan:
        if task['view_id']!=0 or task['external_kind']=='categorical': continue
        rows=r[task['offset']:task['offset']+task['music_variables']]
        for base in bases:
            if base not in indexes or 'matched_composition__'+base not in indexes: continue
            original=rows[indexes[base]]; fixed=rows[indexes['fixed_composition__'+base]]; matched=rows[indexes['matched_composition__'+base]]; track=task['track']
            planned[track]+=1
            if fixed['status']!=0 or matched['status']!=0: continue
            if fixed['n']!=matched['n'] or fixed['first_month']!=matched['first_month'] or fixed['last_month']!=matched['last_month']:
                raise ValueError('Fixed/matched composition comparators have different support')
            counts[track]+=1; three[track]+=int(original['status']==0)
            comparisons.append(dict(base_music_variable=base,external_variable=task['external'],lag_months=task['lag'],track=track,
                original_overall_r=float(original['r']),fixed_composition_r=float(fixed['r']),matched_composition_r=float(matched['r']),
                absolute_fixed_vs_matched_r_difference=float(abs(fixed['r']-matched['r'])),
                original_native_n=int(original['n']),fixed_and_matched_native_n=int(fixed['n']),
                fixed_BY_q=float(fixed['q']),matched_BY_q=float(matched['q']),
                original_status=engine.STATUS[int(original['status'])],
                interpretation='Fixed and matched share the same supported-genre/month cohort; original overall can use a different cohort. Adjusted nuisance-control profiles also differ.'))
    comparisons.sort(key=lambda d:(-d['absolute_fixed_vs_matched_r_difference'],d['base_music_variable'],d['external_variable'],d['lag_months'],d['track']))
    c.write_csv(c.PUBLIC/'composition_comparison.csv',comparisons[:200])
    summary={track:dict(planned_numeric_comparators=planned[track],estimable_fixed_and_matched_pairs=counts[track],all_three_estimable_pairs=three[track]) for track in ['raw','adjusted']}
    c.write_json(c.PUBLIC/'composition_comparison_summary.json',summary)
    return dict(weighting=weighting,composition=summary)


def export(name,path,limit=None):
    results=Results(); indexes=np.load(c.LOCAL/'rankings'/f'{name}.npy',mmap_mode='r')
    if limit is not None: indexes=indexes[:limit]
    path=Path(path).resolve()
    if path==c.ROOT or c.ROOT/'data/raw' in path.parents: raise ValueError('Protected export path')
    if path.exists(): raise FileExistsError('Use a new export path; existing files are preserved: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True); temporary=path.with_name('.'+path.name+'.tmp')
    import shutil
    estimated=len(indexes)*(len(json.dumps(results.record(int(indexes[0])))) if len(indexes) else 0)
    if estimated>c.CONFIG['maximum_bytes'] or estimated>shutil.disk_usage(path.parent).free-c.CONFIG['free_reserve_bytes']:
        raise c.ResourceLimit('CSV export exceeds storage allowance; use --limit or read the complete index/result arrays')
    with temporary.open('w',newline='') as file:
        writer=None
        for rank,index in enumerate(indexes,1):
            value=results.record(int(index),rank)
            if writer is None: writer=csv.DictWriter(file,fieldnames=list(value)); writer.writeheader()
            writer.writerow(value)
    temporary.replace(path)
    return dict(rows=len(indexes),path=str(path))


def short_label(record,maximum=78):
    music=record['music_variable'].replace('fixed_composition__','fixed: ').replace('matched_composition__','matched: ').replace('lyric_','').replace('_',' ')
    external=record['external_variable'].replace('_',' ')
    if len(music)>49: music=music[:32]+'…'+music[-14:]
    return f"{record['view']} · {music}\n{external} · L{record['lag_months']}"


def figures(results,summaries,domain,labels):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    plt.rcParams.update({'font.size':10,'axes.titlesize':14,'axes.labelsize':10,'svg.hashsalt':'cmpt491-v5',
        'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.facecolor':'white'})
    destination=c.PUBLIC/'figures'; destination.mkdir(exist_ok=True); catalog=[]
    def save(fig,name,description):
        svg_path=destination/(name+'.svg')
        fig.savefig(svg_path,bbox_inches='tight',metadata={'Date':None,'Creator':'CMPT 491 V5'})
        c.atomic(svg_path,('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines())+'\n').encode())
        fig.savefig(Path('/tmp')/('cmpt491_v5_'+name+'.png'),dpi=140,bbox_inches='tight')
        plt.close(fig); catalog.append(dict(file='figures/'+name+'.svg',description=description,sha256=c.sha(destination/(name+'.svg'))))
    summary=c.read_json(c.PUBLIC/'result_summary.json')
    counts=c.read_json(c.PUBLIC/'search_counts.json')
    audit=c.read_json(c.PUBLIC/'interpretation_audit.json')
    fig,ax=plt.subplots(figsize=(9,4.8)); bar_labels=['Attempted pair/track rows','Estimable','Passed inference screens','At least one BY q ≤ 0.05','Adjusted lyrical + broad variation\n+ at least two positive transfer folds']
    values=[counts['pair_track_rows'],summary['estimable_pair_track_rows'],summary['inferential_pair_track_rows'],summary['BY_rejected_pair_track_rows'],audit['adjusted_lyrical_rows_with_two_positive_folds_and_broad_variation']]
    bars=ax.barh(bar_labels[::-1],values[::-1],color=['#286b55','#508b8b','#7899a9','#9eb6c3','#c9d1d9'])
    ax.set_xscale('symlog',linthresh=1); ax.set_xlabel('Relationships (log scale above 1); final row is a post-fit diagnostic'); ax.set_title('Coverage, correction and post-fit support')
    for bar,value in zip(bars,values[::-1]): ax.text(max(value,1)*1.08,bar.get_y()+bar.get_height()/2,f'{value:,}',va='center',fontsize=10)
    ax.set_xlim(0,max(values)*5); fig.tight_layout(); save(fig,'coverage_and_inference','Complete attempt denominator, valid support and global BY result counts; log scale.')
    numeric=[row for row in summaries['adjusted'] if row['status']=='ok' and row['pearson_r'] is not None][:12]
    if numeric:
        fig,ax=plt.subplots(figsize=(12,7.2)); positions=np.arange(len(numeric))[::-1]
        for position,row in zip(positions,numeric):
            scale=abs(row['pearson_r']/row['slope']) if row['slope'] else 0.
            effect=row['pearson_r']; lower=row['slope_ci_low']*scale; upper=row['slope_ci_high']*scale
            color='#236b50' if row['any_global_BY_rejection'] else '#62788d'
            ax.errorbar(effect,position,xerr=[[max(0,effect-lower)],[max(0,upper-effect)]],fmt='o',color=color,capsize=3)
        ax.set_yticks(positions,[short_label(row) for row in numeric]); ax.axvline(0,color='#888888',linewidth=.8)
        ax.set_xlabel('OLS slope in sample residual-SD units; conditional 95% HAC interval')
        ax.set_title('Leading time-series-adjusted associations')
        ax.text(0,-.16,'Green: at least one global BY q ≤ 0.05. Gray-blue: exploratory estimate. Selection follows the complete adjusted ranking.',transform=ax.transAxes,fontsize=9)
        fig.tight_layout(); save(fig,'strongest_adjusted','First twelve estimable numeric adjusted rows; sample-standardized OLS slopes and HAC intervals, not Fisher correlation intervals.')
    raw=[row for row in summaries['raw'] if row['pearson_r'] is not None and row['status']=='ok'][:20]
    if raw:
        fig,ax=plt.subplots(figsize=(12,8)); plot_rows=[]
        for original in raw:
            task,name=results.locate(original['row_id']); column=original['row_id']-task['offset']; other=results.plan[task['chunk_id']+1]
            changed=results.record(other['offset']+column)
            plot_rows.append((original,changed))
        for position,(original,changed) in zip(np.arange(len(plot_rows))[::-1],plot_rows):
            raw_r=abs(original['pearson_r']); adjusted_r=abs(changed['pearson_r']) if changed['status']=='ok' and changed['pearson_r'] is not None else np.nan
            ax.plot([raw_r,adjusted_r],[position,position],color='#b8c2ca',linewidth=2)
            ax.scatter(raw_r,position,color='#bb6b3e',s=30,zorder=3); ax.scatter(adjusted_r,position,color='#286b55',s=30,zorder=3)
            if not np.isfinite(adjusted_r): ax.text(.01,position,'adjusted unsupported',fontsize=8,va='center',color='#666666')
        ax.scatter([],[],label='Raw',color='#bb6b3e'); ax.scatter([],[],label='Adjusted',color='#286b55')
        ax.legend(loc='upper center'); ax.set_yticks(np.arange(len(plot_rows))[::-1],[short_label(a) for a,_ in plot_rows])
        ax.set_xlim(0,1.04); ax.set_xlabel('Absolute Pearson / partial correlation'); ax.set_title('The same leading raw pairs after adjustment')
        fig.tight_layout(); save(fig,'raw_vs_adjusted','Exact pair/population/lag matches for the first twenty numeric raw leaders; unsupported adjusted matches are labeled.')
    if numeric:
        fig,ax=plt.subplots(figsize=(10,6.5)); values=np.array([[r[f'fold_{i}_skill'] if r[f'fold_{i}_status']=='ok' else np.nan for i in [1,2,3]] for r in numeric])
        show=ax.imshow(np.ma.masked_invalid(values),cmap='RdYlGn',vmin=-1,vmax=1,aspect='auto')
        for i in range(len(numeric)):
            for j in range(3):
                value=values[i,j]; text='unsupported' if not np.isfinite(value) else f'{value:.2f}' if abs(value)<100 else f'{value:.0f}'
                ax.text(j,i,text,ha='center',va='center',fontsize=8)
        ax.set_yticks(np.arange(len(numeric)),[short_label(row,70) for row in numeric]); ax.set_xticks([0,1,2],['1990–2001','2002–2013','2014–2026 Sep'])
        ax.set_title('Chronological transfer of the leading adjusted estimates')
        colorbar=fig.colorbar(show,ax=ax,pad=.02); colorbar.set_label('MSE skill versus training-fitted baseline\nColor scale capped at −1 and +1; labels give actual values')
        fig.tight_layout(); save(fig,'historical_stability','Baseline-relative MSE skill in the three embargoed chronological transfer folds; unsupported folds are explicit.')
    if numeric:
        lead=numeric[0]; task,name=results.locate(lead['row_id']); column=lead['row_id']-task['offset']
        rows=[]
        for t in results.plan:
            if t['view_id']==task['view_id'] and t['external']==task['external']:
                rows.append(results.record(t['offset']+column))
        fig,ax=plt.subplots(figsize=(9,4.8))
        for track,color in [('raw','#bb6b3e'),('adjusted','#286b55')]:
            part=sorted([r for r in rows if r['track']==track],key=lambda r:r['lag_months'])
            ax.plot([r['lag_months'] for r in part],[r['pearson_r'] if r['status']=='ok' else np.nan for r in part],'-o',label=track.capitalize(),color=color)
            for row in part:
                if row['any_global_BY_rejection'] and row['pearson_r'] is not None:
                    ax.scatter(row['lag_months'],row['pearson_r'],s=100,facecolors='none',edgecolors=color,linewidths=2)
        ax.axhline(0,color='#888888',linewidth=.8); ax.set_xticks(c.CONFIG['lags']); ax.set_xlabel('External reference-month lead (months)')
        ax.set_ylabel('Pearson / partial correlation'); ax.set_title('All declared lags of the first adjusted numeric leader\n'+short_label(lead,95),fontsize=11)
        qualification='No lag passes global BY.' if not any(row['any_global_BY_rejection'] for row in rows) else 'Outlined points: at least one global BY q ≤ 0.05.'
        qualification+=f" Music series nonzero in {lead['nonzero_music_months']} of {lead['observed_music_months']} observed months."
        ax.legend(); ax.text(0,-.22,qualification+' Retrospective association.',transform=ax.transAxes,fontsize=8)
        fig.tight_layout(); save(fig,'lag_profile','All six predefined lags for the exact first adjusted numeric leader; no manual hypothesis selection.')
    fig,axes=plt.subplots(1,2,figsize=(11,5)); domains=sorted(domain.domain.unique())
    for track,color,offset in [('raw','#bb6b3e',-.18),('adjusted','#286b55',.18)]:
        part=domain.loc[domain.track.eq(track)].set_index('domain').reindex(domains)
        for ax,column,title in [(axes[0],'inferential','Passed inference screens'),(axes[1],'global_BY_pair_rejections','At least one global BY rejection')]:
            ax.barh(np.arange(len(domains))+offset,part[column],height=.35,color=color,label=track.capitalize()); ax.set_title(title)
            ax.set_yticks(np.arange(len(domains)),domains); ax.set_xscale('symlog',linthresh=1); ax.set_xlabel('Pair/track rows (log scale above 1)')
    axes[0].legend(); fig.suptitle('Results across every external domain',fontsize=15); fig.tight_layout()
    save(fig,'domain_results','Domain support and global BY rejection counts for both tracks; no raw restricted source values plotted.')
    ordering=np.load(c.LOCAL/'rankings/within_genre.npy',mmap_mode='r'); selected=[]
    eligible=(labels['track'][ordering]==1)&(results.rows['status'][ordering]==0)&np.isfinite(results.rows['r'][ordering])
    for view in results.views[1:]:
        found=np.flatnonzero(eligible&(labels['view'][ordering]==view['id']))
        selected.append(results.record(int(ordering[found[0]])) if len(found) else dict(view=view['name'],status='No estimable adjusted numeric pair'))
    c.write_csv(c.PUBLIC/'genre_best_adjusted.csv',selected)
    fig,ax=plt.subplots(figsize=(10,7)); positions=np.arange(len(selected))[::-1]
    for position,row in zip(positions,selected):
        if row['status']=='ok':
            color='#236b50' if row['any_global_BY_rejection'] else '#62788d'; ax.scatter(row['pearson_r'],position,color=color,s=45)
            unit={'M':'months','Q':'quarters','A':'years','term':'terms','event':'event periods'}[row['native_frequency']]
            ax.text(1.02,position,f"{row['native_n']} {unit}; q={min(row['global_BY_q'],row['global_rank_BY_q']):.3g}",va='center',fontsize=8,transform=ax.get_yaxis_transform())
        else: ax.text(.01,position,'insufficient supported history',va='center',fontsize=9,color='#777777')
    ax.axvline(0,color='#888888',linewidth=.8); ax.set_xlim(-1,1); ax.set_yticks(positions,[r['view'] for r in selected]); ax.set_ylim(-.7,len(selected)-.3); ax.set_xlabel('Partial correlation of each genre’s leading adjusted numeric pair')
    ax.set_title('Within-genre coverage and strongest adjusted estimates')
    fig.tight_layout(); save(fig,'genre_adjusted','First estimable adjusted numeric pair per genre in the complete within-genre ranking; omitted estimates are explicitly unsupported. Variable names are in genre_best_adjusted.csv.')
    c.write_csv(c.PUBLIC/'figure_catalog.csv',catalog)
    return catalog


def markdown_table(records,limit=20):
    text=['| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |',
          '| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |']
    def fmt(value,places=3): return '—' if value is None else f'{value:.{places}g}'
    for i,row in enumerate(records[:limit],1):
        effect='r='+fmt(row['pearson_r']) if row['pearson_r'] is not None else 'η²='+fmt(row['partial_eta_squared'])
        ci='['+fmt(row['slope_ci_low'])+', '+fmt(row['slope_ci_high'])+']' if row['slope_ci_low'] is not None else 'omnibus; contrasts local'
        q=min(v for v in [row['global_BY_q'],row['global_rank_BY_q']] if v is not None)
        text.append(f"| {i} | `{row['music_variable']}` | `{row['external_variable']}` | {row['view']}; {row['lag_months']}m; {row['track']} | {effect} | {row['native_n']} | {ci} | {q:.3g} | {row['positive_same_direction_folds']}/{row['completed_transfer_folds']} |")
    if not records: return 'No relationship meets this ranking’s criteria.\n'
    return '\n'.join(text)+'\n'


def findings(results,summaries,value,domain,changes):
    counts=c.read_json(c.PUBLIC/'search_counts.json'); correction=c.read_json(c.PUBLIC/'multiple_testing_summary.json')
    audit=c.read_json(c.PUBLIC/'interpretation_audit.json')
    lines=['# V5 findings: exhaustive music × historical conditions','',
        f"The campaign completed **{counts['pair_track_rows']:,} attempted pair/track analyses** and a global family of **{counts['method_hypotheses']:,} method hypotheses**. "
        f"**{value['estimable_pair_track_rows']:,}** pair/track rows were estimable; **{value['inferential_pair_track_rows']:,}** passed the inference screens. "
        f"**{value['BY_rejected_pair_track_rows']:,}** pair/track rows had at least one global BY q≤0.05, representing **{correction['method_rejections']:,}** method rejections.",'',
        'These are exploratory retrospective associations, conditional on the declared time-series assumptions. Statistical correction does not establish causality, point-in-time forecasting, or independence from changing coverage. Historical evaluation periods were already inspected in earlier campaigns.','',
        f"**The corrected count is not a count of established musical discoveries.** A post-fit influence audit found **{audit['numeric_rows_with_concentrated_variation']:,} of {audit['corrected_rows']:,}** corrected rows with fewer than six effective exposure/score blocks. "
        f"Among **{audit['corrected_adjusted_lyrical_rows']:,} adjusted lyrical rows**, **{audit['adjusted_lyrical_rows_with_two_positive_folds_and_broad_variation']}** combined broad temporal variation with at least two positive same-direction transfer folds. "
        'The four adjusted rows without that concentration flag are all `christmas_proximity_days` versus `US_FEDERAL_ELECTION_MONTH`: calendar timing, not a discovered relationship between lyrical content and historical conditions. '
        'This sensitivity audit does not change any original estimate, q value or family denominator; it limits their substantive interpretation.','',
        f"Among **{value['raw_absolute_r_at_least_half']:,}** raw numeric relationships with |r|≥0.5, **{value['with_estimable_adjusted_match']:,}** had an estimable adjusted counterpart; "
        f"**{value['dropping_below_absolute_r_point_one']:,}** fell below |r|=0.1 after adjustment. Unsupported adjusted fits are not counted as disappearing effects. "
        'The [complete status summary](coverage_and_status.csv) separates insufficient support, unidentified effects and other failures from valid nonsignificant estimates.','',
        '## Counts by domain and track','',
        '| External domain | Track | Attempted pair/track rows | Estimable | Passed inference screens | Any BY rejection |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for row in domain.to_dict('records'):
        lines.append(f"| {row['domain']} | {row['track']} | {row['pair_track_rows']:,} | {row['estimable']:,} | {row['inferential']:,} | {row['global_BY_pair_rejections']:,} |")
    lines+=['','## Reading the tables','',
        'Every table below follows a declared ranking rule; the leading rows can include repeated lags or related transformations of the same underlying construct. The top raw list is a diagnostic list and can be dominated by secular trends. Coverage/count variables are not lyrical-content discoveries. Adjusted and domain/genre/lag rankings prioritize stationarity-supported estimates; domain/genre/lag lists prefer adjusted fits before raw fits. Categorical effect is partial η²; numeric effect is Pearson r or its adjusted partial counterpart.','',
        'Intervals are **native-unit OLS slope intervals**, not correlation intervals. Best q is the smaller of the two separately corrected numeric method q values; both are retained in the CSVs. “Stable folds” means positive baseline-relative skill with the full-sample correlation direction, divided by completed folds; 1/1 does not mean success in all three periods. Categorical contrasts and their descriptive intervals remain in the complete local export.','',
        'Each linked CSV is a **top-200 summary**, not the entire campaign. The ten complete local rankings retain every row in their declared subset, including unsupported/null rows. [Reproduction and complete export instructions](README.md) explain how to retrieve them.','']
    for name,title in [('raw','Top 20 raw relationships'),('adjusted','Top 20 adjusted relationships'),
                       ('within_genre','Top 20 within-genre relationships'),('between_genre','Top 20 between-genre composition relationships')]:
        lines+=['## '+title,'',f"[Full summary CSV]({SUMMARY_NAMES[name]}.csv)",'',markdown_table(summaries[name]),'']
    for name,title in [('financial','Strongest financial associations'),('macroeconomic','Strongest macroeconomic associations'),
                       ('political_social','Strongest political/social associations'),('lagged','Leading lagged relationships'),
                       ('historically_stable','Historical transfer stability'),('multiple_testing','Global BY survivors')]:
        lines+=['## '+title,'',f"[Full summary CSV]({SUMMARY_NAMES[name]}.csv)",'',markdown_table(summaries[name],5),'']
    leads=pd.read_csv(c.PUBLIC/'adjusted_lyrical_corrected_leads.csv').replace({np.nan:None}).to_dict('records')
    lines+=['## Corrected lyrical leads and the influence caveat','',
        'The [complete 178-row adjusted lyrical table](adjusted_lyrical_corrected_leads.csv) separates content/structure constructs from the published source’s provenance/quality fields. '
        'The following rows are ordered by successful chronological transfer, then the existing corrected ranking. They are candidates for **robustness checks and independent replication**, not presently defensible substantive discoveries. '
        'Even the rows with three positive transfer folds rely on highly concentrated exposure variation; for example, some claims-series relationships have only about one effective exposure block despite hundreds of observed months.','',
        markdown_table(leads,8),'',
        'The [influence diagnostics](corrected_influence_diagnostics.csv) cover every corrected numeric method. '
        'The [complete corrected table](corrected_relationships_complete.csv) includes all 712 rows, source-informed measurement roles, effective-block diagnostics and the actual rejecting method. '
        'The original pipeline role is retained beside the source-informed role in the [measurement-role crosswalk](measurement_role_crosswalk.csv). '
        '`lyric_semantic_prior_hit_reference_n`, which dominates the strongest raw list, is explicitly defined by the source dictionary as the number of earlier Top-10 identities in a reference centroid; it is not a semantic-content score.','']
    lines+=['## Associations attenuated by adjustment','',
        '[Top 200 matched attenuations](disappeared_after_adjustment.csv) give the exact raw and adjusted rows, lags, sample sizes and q values. These compare the same declared pair while the estimand changes from levels to adjusted native-period changes. They do not identify the cause of attenuation.','',
        '| Music measure | External series | Population; lag | Raw r | Adjusted r |',
        '| --- | --- | --- | ---: | ---: |']
    for row in changes[:10]:
        lines.append(f"| `{row['music_variable']}` | `{row['external_variable']}` | {row['view']}; {row['lag_months']}m | {row['raw_r']:.3f} | {row['adjusted_r']:.3f} |")
    lines+=['','## Weighting and fixed-composition comparisons','',
        'The [weighting sensitivity](weighting_sensitivity.csv) summarizes the already fitted equal-period and distinct chart-song-count weighted estimates. These are descriptive comparisons; no extra weighting p-values enter the global family. The weighting uses chart population counts, not the feature-specific count of observed lyrics.','',
        '| Population | Track | Comparable numeric rows | Median absolute change in r | 95th percentile absolute change | Sign changes with both absolute r > 0.01 |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for row in pd.read_csv(c.PUBLIC/'weighting_sensitivity.csv').to_dict('records'):
        lines.append(f"| {row['population']} | {row['track']} | {row['comparable_pairs']:,} | {row['median_absolute_correlation_change']:.4f} | {row['p95_absolute_correlation_change']:.4f} | {row['sign_changes_with_both_absolute_r_above_point01']:,} |")
    lines+=['','The [fixed/matched composition comparison](composition_comparison.csv) lists the 200 largest saved correlation differences on the identical supported-genre/month cohort. The original overall estimate is shown separately because it may use more months or genres. Adjusted fixed and matched fits also differ in nuisance-control profiles, so their difference is not a pure weighting effect.','',
        '| Track | Planned numeric feature/external/lag comparisons | Both fixed/matched estimable | Original + fixed + matched estimable |',
        '| --- | ---: | ---: | ---: |']
    for track,row in c.read_json(c.PUBLIC/'composition_comparison_summary.json').items():
        lines.append(f"| {track} | {row['planned_numeric_comparators']:,} | {row['estimable_fixed_and_matched_pairs']:,} | {row['all_three_estimable_pairs']:,} |")
    lines+=['','Strict complete-genre coverage and the six-block support rule limit these comparisons. Missing supported genres are not reweighted away to create a longer series. The within-genre rankings and original overall fits remain available when a fixed-composition counterpart is unsupported.']
    lines+=['','## Null findings and coverage limits','',
        f"**{value['inferential_pair_track_rows']-value['BY_rejected_pair_track_rows']:,}** inference-supported pair/track rows did not meet either global BY threshold. "
        'This is a lack of corrected evidence for these specific tests, not proof that their effects are zero. The much larger set of unsupported rows is a coverage/assumption limitation and must not be described as a scientific null. The domain table above states which populations supplied actual inferential support.','',
        'The 16-genre [coverage figure](figures/genre_adjusted.svg) and [best-estimate table](genre_best_adjusted.csv) retain genres with insufficient supported history explicitly. Audio and metadata measures have uneven coverage; missing lyrics and classifier scores are not random across history. Five observed songs in a feature-month is a measurement support floor, not proof of population representativeness. Counts, coverage and release/edition metadata can track source collection practices.','',
        'The leading between-genre adjusted coefficient concerns Afrobeats share and life expectancy (12-month reference lag), with r≈−0.776 across 64 annual units and q=1. The underlying genre share is nonzero in only 38 of 818 months. Known zero shares are not missing observations, but 64 annual rows do not establish 64 years of active Afrobeats coverage. This is an explicitly unsupported substantive lead, not evidence that life expectancy caused genre change.','',
        'Raw trend correlations can be striking even when adjusted estimates are small. ADF screening uses each series’ broader available history, not a guarantee for each pair’s overlap. HAC and BY depend on valid individual-model assumptions; the strong-AR null simulation still had 7.35% nominal rejection at a 5% threshold, despite passing the declared development tolerance and having 1.875% corrected all-null world rejection. Confidence intervals are marginal, not simultaneous across the full campaign.','',
        'Annual/quarterly context uses its native sample size; categories use term/event support. Positive lags refer to source reference periods and cannot recover unavailable original publication vintages. September 2026 is incomplete. Genre and content classifiers are uncertain modern measurements of historical music. None of these tables estimates a causal effect of economic conditions, politics or COVID.','',
        '## Validation and resources','',
        'The [validation record](validation.json) checks complete work-unit coverage, unchanged restart chunks, numerically deterministic replays with recorded floating-point tolerances, complete ranking membership and independent global BY calculation. '
        'The [integrity record](integrity_validation.json) records unchanged original data/previous analyses and the repository test suite. '
        'Actual cumulative active computation is in [resource_ledger.json](resource_ledger.json); measured process memory and output sizes are in [execution_resources.json](execution_resources.json). '
        'The [benchmark](benchmark.json) authorized execution within the four-hour/15 GB limits.','',
        '## Next steps; no further campaign executed','',
        'No adjusted lyrical relationship in this run clears both the broad-variation diagnostic and two positive chronological folds. A nonlinear campaign is therefore not justified by these results alone. The caring/unemployment or claims, insult/continued-claims, and linguistic-structure/claims rows above are concrete candidates for a **separately approved robustness/replication protocol**: examine leverage, independent episodes, stronger finite-sample uncertainty and measurement coverage before conditional or nonlinear modelling. Treat related lags/transforms as the same substantive lead, not independent replications. Strong raw-only effects and sparse genres do not justify a nonlinear search.','',
        'Every substantive lead requires independent replication: genuinely future observations under a locked protocol, a separately sampled chart population, or independently measured lyrical constructs. Reusing the repeatedly inspected 2018-onward data does not provide untouched confirmation. Additional as-of publication vintages would improve forecasting claims; broader historical audio, missing-lyric coverage and independently validated classifier measurements would address different measurement limits. More data should be chosen to address a documented limitation, not simply to manufacture a significant result.','',
        'No nonlinear, interaction, clustering, multivariate search or additional acquisition was launched.']
    c.atomic(c.PUBLIC/'findings.md',('\n'.join(lines)+'\n').encode())


def readme():
    counts=c.read_json(c.PUBLIC/'search_counts.json'); result=c.read_json(c.PUBLIC/'result_summary.json')
    text=f'''# V5 exhaustive music × historical discovery

The authorized pairwise campaign is complete: **{counts['eligible_view_pairs']:,} population-specific pairs**, six lags, two tracks and **{counts['method_hypotheses']:,} method hypotheses**. It retains every planned comparison, including failures and null estimates. **{result['BY_rejected_pair_track_rows']:,}** pair/track rows meet at least one global BY threshold; this is exploratory association, not causal or untouched confirmatory evidence.

**No adjusted lyrical lead combined broad temporal variation with two positive chronological transfer folds.** The post-fit audit flags concentrated variation in 603 of the 712 corrected rows; the four broadly supported adjusted rows are calendar-timing patterns. See the [interpretation audit](interpretation_audit.json), [complete corrected table](corrected_relationships_complete.csv) and [source-informed measurement roles](corrected_by_measurement_role.csv) before treating a small q value as a substantive musical finding.

Start with [findings and all four requested top-20 tables](findings.md), the [methodology](methodology.md), [domain summary](domain_summary.csv), [coverage/status counts](coverage_and_status.csv) and [figure catalog](figure_catalog.csv).

| File | Purpose |
| --- | --- |
| [variable_inventory.csv](variable_inventory.csv), [exclusion_log.csv](exclusion_log.csv) | Complete variable accounting, definitions, source/frequency/availability and structural exclusions |
| [search_space.csv](search_space.csv), [search_counts.json](search_counts.json) | Complete work-unit enumeration and exact pair/method denominators |
| [raw_relationships.csv](raw_relationships.csv), [adjusted_relationships.csv](adjusted_relationships.csv) | First 200 rows from each complete ranking |
| [genre_relationships.csv](genre_relationships.csv), [between_genre_relationships.csv](between_genre_relationships.csv) | First 200 within-genre and composition rows |
| [historical_stability.csv](historical_stability.csv), [lagged_relationships.csv](lagged_relationships.csv) | First 200 stability and lagged rows |
| [financial_relationships.csv](financial_relationships.csv), [macroeconomic_relationships.csv](macroeconomic_relationships.csv), [political_social_relationships.csv](political_social_relationships.csv) | First 200 rows of each domain ranking |
| [multiple_testing.csv](multiple_testing.csv), [multiple_testing_summary.json](multiple_testing_summary.json) | Up to 200 corrected leaders and full global-family accounting |
| [leaderboard_catalog.csv](leaderboard_catalog.csv) | Complete local ranking sizes, definitions and hashes |
| [weighting_sensitivity.csv](weighting_sensitivity.csv), [composition_comparison_summary.json](composition_comparison_summary.json) | Saved-estimate weighting and fixed/matched-composition comparisons |
| [adjusted_monthly_fix.json](adjusted_monthly_fix.json), [synthetic_validation.json](synthetic_validation.json) | Reproduced V4 failure, span-preserving fix and independent null validation |
| [benchmark.json](benchmark.json), [resource_ledger.json](resource_ledger.json) | Required pre-execution resource gate and cumulative active computation |
| [validation.json](validation.json), [integrity_validation.json](integrity_validation.json) | Complete coverage, independent numerical checks, restart/replay and source preservation |

Public CSVs are explicitly **summaries**. The canonical complete local results are in the ignored `data/experiments/cross_domain_discovery_v5/`: `results.npy` (all {counts['pair_track_rows']:,} typed rows), `checkpoints.sqlite` (all atomic work units), `categorical_contrasts.csv` (descriptive category-effect intervals), and ten `rankings/*.npy` index arrays. Row offsets in the public search-space table and the local view metadata make every result reversible. No private lyrics or raw restricted economic observations are published.

## Verify or export

Run from the canonical repository root with the recorded Python/package environment in [frozen_protocol.json](frozen_protocol.json). Dependencies are the existing NumPy, pandas, SciPy, statsmodels, Matplotlib and threadpoolctl installation; no new service or acquisition is required.

```bash
# Public files only; available in a fresh clone.
python3 src/pairwise_v5_report.py verify

# Full local checkpoints/results, independent BY and deterministic sampled replay.
python3 src/pairwise_v5_report.py verify --private --replay

# Read any complete ranking. --limit is optional; omit to export every row.
python3 src/pairwise_v5_report.py export --ranking adjusted --limit 1000 --output /tmp/v5_adjusted.csv

python3 -m unittest discover -s tests -p test_pairwise_v5.py -v
```

Ranking names are `raw`, `adjusted`, `historically_stable`, `financial`, `macroeconomic`, `political_social`, `within_genre`, `between_genre`, `lagged`, and `multiple_testing`. Large full CSV exports are optional and can exceed the remaining disk allowance; the compact index arrays already provide complete rankings without duplicate data.

## Reproduce or resume offline

The full build requires the retained V4 monthly/genre views and historical/financial snapshots listed in the frozen input hashes. Some restricted inputs are intentionally absent from a fresh clone. Original source files and older analyses must remain unchanged. Exact hashes of the derived analysis inputs are in [derived_input_hashes.json](derived_input_hashes.json).

```bash
python3 src/pairwise_v5_data.py
python3 src/pairwise_v5_diagnostics.py fix
python3 src/pairwise_v5_runner.py benchmark
python3 src/pairwise_v5_diagnostics.py stationarity
python3 src/pairwise_v5_runner.py run
python3 src/pairwise_v5_runner.py finalize
python3 src/pairwise_v5_report.py build
python3 src/pairwise_v5_report.py verify --private --replay
```

The runner requires a passing synthetic validation and resource gate; it refuses changed compute code/protocols or corrupt checkpoints. Re-running `run` with the same frozen protocol verifies and reuses completed chunks. The published 100-chunk deliberate stop/resume is recorded in [restart_initial.json](restart_initial.json). A new scientific specification requires a new versioned campaign directory, preserving this completed attempt. The four-hour ledger is cumulative across commands/resumes; it does not reset with a new process. A crashed command is conservatively charged until resumed.

The seven SVG figures are deterministic, shareable statistical summaries. Their numerical content comes from completed estimates; no raw restricted historical-value traces are embedded. Temporary PNG previews are outside the repository so the frozen earlier figure catalog remains unchanged.

Any conditional, nonlinear, interaction or multivariate campaign, and any additional data acquisition, requires separate authorization.
'''
    c.atomic(c.PUBLIC/'README.md',text.encode())


def verify(private=False,replay=False):
    if not private:
        manifest=c.read_json(c.PUBLIC/'publication_manifest.json')
        for name,expected in manifest['files'].items():
            if c.sha(c.ROOT/name)!=expected: raise ValueError('Publication hash mismatch: '+name)
        counts=c.read_json(c.PUBLIC/'search_counts.json'); plan=pd.read_csv(c.PUBLIC/'search_space.csv')
        if int(plan.music_variables.sum())!=counts['pair_track_rows'] or int(plan.method_hypotheses.sum())!=counts['method_hypotheses']:
            raise ValueError('Public search-space denominator mismatch')
        return dict(status='PASS',publication_files=len(manifest['files']),pair_track_rows=counts['pair_track_rows'],method_hypotheses=counts['method_hypotheses'])
    results=Results(); fingerprint=c.freeze(); store=runner.Store(c.LOCAL/'checkpoints.sqlite',fingerprint)
    if {r[0] for r in store.db.execute('SELECT id FROM chunks')}!={t['chunk_id'] for t in results.plan}: raise ValueError('Incomplete checkpoint coverage')
    actual_rows=0; hypotheses=0; checks=0; q_parts=[]; p_parts=[]
    for task in results.plan:
        rows,contrasts=store.get(task['chunk_id']); a=task['offset']; b=a+len(rows); final=results.rows[a:b]
        compared=final.copy(); compared['q']=rows['q']; compared['q_rank']=rows['q_rank']
        if runner.encode(compared)!=runner.encode(rows): raise ValueError('Final array differs from original checkpoint')
        eligible=(rows['status']==0)&(rows['inferential']==1)&np.isfinite(rows['p'])
        p_parts.append(np.where(eligible,rows['p'],1.)); q_parts.append(final['q'].copy()); hypotheses+=len(rows)
        if task['external_kind']!='categorical':
            p_parts.append(np.where(eligible&np.isfinite(rows['p_rank']),rows['p_rank'],1.)); q_parts.append(final['q_rank'].copy()); hypotheses+=len(rows)
        actual_rows+=len(rows); checks+=1
    initial=c.read_json(c.PUBLIC/'restart_initial.json')
    for row in initial['chunks']:
        if store.db.execute('SELECT sha FROM chunks WHERE id=?',(row['chunk_id'],)).fetchone()[0]!=row['sha256']: raise ValueError('Resumed checkpoint changed')
    store.close()
    from statsmodels.stats.multitest import multipletests
    p=np.concatenate(p_parts); q=np.concatenate(q_parts); del p_parts,q_parts
    reference=multipletests(p,method='fdr_by')[1]
    np.testing.assert_allclose(q,reference,rtol=1e-12,atol=1e-14)
    for name,record in c.read_json(c.PUBLIC/'derived_input_hashes.json').items():
        if c.sha(c.LOCAL/name)!=record['sha256']: raise ValueError('Derived analysis input changed: '+name)
    labels=classifications(results); ranking_rows={}
    for name in RANKINGS:
        indexes=np.load(c.LOCAL/'rankings'/f'{name}.npy'); expected=np.flatnonzero(ranking_mask(name,results.rows,labels))
        np.testing.assert_array_equal(np.sort(indexes),expected); ranking_rows[name]=len(indexes)
        records=[results.record(int(index),rank=i+1) for i,index in enumerate(indexes[:200])]
        frame=pd.DataFrame(records,columns=list(results.record(0,rank=1)))
        reproduced=frame.to_csv(index=False,float_format='%.17g').encode()
        if hashlib.sha256(reproduced).hexdigest()!=c.sha(c.PUBLIC/(SUMMARY_NAMES[name]+'.csv')):
            raise ValueError('Public numerical summary does not reproduce: '+name)
    replayed=0; maximum_scaled_error=0.
    if replay:
        workspace=engine.Workspace(); groups=collections.defaultdict(list)
        for task in results.plan: groups[(task['view_id'],task['frequency'],task['track'])].append(task)
        for tasks in groups.values():
            task=min(tasks,key=lambda t:c.digest({'replay':t['chunk_id']})); new,_,_=runner.measured_task(workspace,task)
            old=results.rows[task['offset']:task['offset']+len(new)]
            for field in old.dtype.names:
                if field in ['q','q_rank']: continue
                if old.dtype[field].base.kind=='f':
                    np.testing.assert_allclose(new[field],old[field],rtol=1e-9,atol=1e-12,equal_nan=True)
                    finite=np.isfinite(old[field])&np.isfinite(new[field])
                    if finite.any(): maximum_scaled_error=max(maximum_scaled_error,float(np.max(abs(new[field][finite]-old[field][finite])/np.maximum(1,abs(old[field][finite])))))
                else: np.testing.assert_array_equal(new[field],old[field])
            replayed+=1
    value=dict(status='PASS',complete_chunks=checks,pair_track_rows=actual_rows,method_hypotheses=hypotheses,
        independent_global_BY_max_error=float(np.max(abs(q-reference))),replayed_chunks=replayed,
        replay_maximum_scaled_error=maximum_scaled_error,replay_float_rtol=1e-9,replay_float_atol=1e-12,
        resumed_initial_chunks_unchanged=len(initial['chunks']),complete_ranking_rows=ranking_rows,peak_process_bytes=runner.peak_memory())
    return value


def publication_manifest():
    paths=[p for p in c.PUBLIC.rglob('*') if p.is_file() and p.name!='publication_manifest.json']
    paths+=list((c.ROOT/'src').glob('pairwise_v5_*.py'))+[c.ROOT/'tests/test_pairwise_v5.py']
    c.write_json(c.PUBLIC/'publication_manifest.json',dict(files={str(p.relative_to(c.ROOT)):c.sha(p) for p in sorted(paths)},
        parent_commit=c.CONFIG['parent_commit'],full_results='Local complete results.npy and ten complete index rankings; public CSVs are top-200 summaries.'))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['build','verify','export','manifest'])
    parser.add_argument('--private',action='store_true'); parser.add_argument('--replay',action='store_true'); parser.add_argument('--record',action='store_true')
    parser.add_argument('--ranking',choices=RANKINGS); parser.add_argument('--output'); parser.add_argument('--limit',type=int); args=parser.parse_args()
    if args.action=='verify':
        value=verify(args.private,args.replay)
        if args.record: c.write_json(c.PUBLIC/'validation.json',value)
        print(json.dumps(value,indent=2)); return
    if args.action=='export': print(json.dumps(export(args.ranking,args.output,args.limit),indent=2)); return
    if args.action=='manifest': publication_manifest(); return
    budget=c.Budget('rankings_and_report')
    try:
        results=Results(); summaries,labels=rankings(results,budget); value,domain,changes=summarize(results,labels)
        interpretation_audit(results,budget); saved_estimate_sensitivities(results,labels)
        figures(results,summaries,domain,labels); findings(results,summaries,value,domain,changes); readme()
        print(json.dumps(value,indent=2),flush=True)
    finally:
        total=budget.close()
        c.write_json(c.PUBLIC/'report_execution.json',dict(cumulative_seconds=total,peak_process_bytes=runner.peak_memory()))


if __name__=='__main__': main()
