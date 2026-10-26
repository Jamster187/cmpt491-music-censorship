"""Deterministic reporting after the immutable validation-selection lock."""
import os
for _key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[_key]='1'
import gc
import gzip
import io
import json
import resource
from pathlib import Path
import time
import numpy as np
import pandas as pd
import regression_expanded_spec as spec
import regression_expanded_core as core
from regression_expanded_search import open_store


def save_large(path,frame):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=5) as zipped:
            with io.TextIOWrapper(zipped,encoding='utf-8',newline='') as text:frame.to_csv(text,index=False,lineterminator='\n',float_format='%.15g')
    temp.replace(path)
    return dict(path=str(path.relative_to(spec.ROOT)),rows=len(frame),bytes=path.stat().st_size,sha256=spec.sha(path))


def clustered_intervals(frame,y,pred,mean,reference,seed):
    """Paired cluster resampling of fixed predictions; no independence claim."""
    output=[];rng=np.random.default_rng(seed)
    for grouping,labels in [('exact_artist_credit',frame.artist),('debut_year',frame.first_chart_date.str[:4])]:
        a=pd.DataFrame(dict(group=labels.to_numpy(),n=1.,y=y,y2=y*y,se=(y-pred)**2,ae=abs(y-pred),base=(y-mean)**2,reference=(y-reference)**2))
        summed=a.groupby('group',sort=True).sum().to_numpy();groups=len(summed)
        counts=rng.multinomial(groups,np.full(groups,1/groups),size=spec.CONFIG['bootstrap_repeats']);totals=counts@summed
        n,sy,sy2,se,ae,base,ref=totals.T;variance=sy2/n-(sy/n)**2;mse=se/n
        values=dict(r2=1-mse/variance,mae=ae/n,rmse=np.sqrt(mse),skill=1-se/base,delta_r2_vs_original=(ref-se)/(n*variance),rmse_reduction_vs_original=np.sqrt(ref/n)-np.sqrt(mse))
        for metric,v in values.items():
            lo,hi=np.quantile(v,[.025,.975]);output.append(dict(grouping=grouping,groups=groups,repeats=spec.CONFIG['bootstrap_repeats'],metric=metric,lower=float(lo),upper=float(hi)))
    return output


def enrich(store,ranked,task):
    f=ranked.copy();names=store.get('predictors')
    combos=[store.combo(r) for r in f.to_dict('records')]
    f['predictors']=[' | '.join(c) for c in combos];f['families']=[' | '.join(sorted(set(spec.REGISTRY[n]['family'] for n in c))) for c in combos]
    f['validation_rmse']=np.sqrt(f.validation_mse);f['evaluation_rmse']=np.sqrt(f.evaluation_mse)
    f['evaluation_minus_validation_r2']=f.evaluation_r2-f.validation_r2;f['evaluation_minus_training_r2']=f.evaluation_r2-f.train_r2
    f['evaluation_minus_validation_skill']=f.evaluation_skill-f.validation_skill
    for number in range(3):
        scores=pd.read_sql_query('SELECT id,r2,mae,mse,skill,rank FROM scores WHERE fold=?',store.db,params=(number,)).set_index('id')
        for metric in ['r2','mae','skill','rank']:f[f'period_{number}_{metric}']=f.id.map(scores[metric])
        f[f'period_{number}_rmse']=np.sqrt(f.id.map(scores.mse))
    meta=[store.get('fold_'+str(i)) for i in range(4)]
    f['n_train']=meta[3]['n_train'];f['n_evaluation']=meta[3]['n_validation'];f['n_validation']=sum(m['n_validation'] for m in meta[:3])
    f['evaluation_baseline_r2']=meta[3]['baseline']['baseline_r2'];f['evaluation_baseline_mae']=meta[3]['baseline']['baseline_mae'];f['evaluation_baseline_rmse']=meta[3]['baseline']['baseline_rmse']
    for key,value in task.items():f[key]=value
    return f.drop(columns=['i1','i2','i3']),meta


def report():
    begun=time.perf_counter();lock=spec.read_json(spec.PUBLIC/'selection_lock.json');selection_hash=spec.sha(spec.PUBLIC/'selection_lock.json')
    if spec.read_json(spec.PUBLIC/'execution.json')['status']!='COMPLETE':raise ValueError('Evaluation incomplete')
    provenance=spec.provenance()
    if lock['provenance']!=spec.clean(provenance):raise ValueError('Frozen numerical provenance changed')
    v1=pd.read_csv(spec.V1/'selected_predictions.csv.gz');v1=v1[v1.partition.eq('test') & v1.target.isin(spec.TARGETS)]
    v1metrics=pd.read_csv(spec.V1/'model_comparison.csv');v1selected=pd.read_csv(spec.V1/'selected_models.csv')
    leaderboard=[];top=[];baselines=[];intervals=[];comparison=[];family=[];focused=[];manifest=[];coverage=[];metadata={};predictions=[];stability=[]
    focus=['credit_prior_top10_song_count','credit_prior_song_count','credit_recent_chart_presence','credit_recent_points_slope','same_credit_debut_cluster_size','previous_chart_new_entry_count','debut_competing_new_entry_count','lyric_word_count','lyric_repeated_line_share','lyric_compression_ratio','primary_genre','secondary_genres','debut_time_years','chart_weekday']
    for task in spec.tasks():
        store=open_store(task,provenance);ranked,meta=enrich(store,store.rankings(True),task);metadata[task['task_id']]=meta
        manifest.append(save_large(spec.LOCAL/'hierarchies'/(task['task_id']+'.csv.gz'),ranked))
        coverage.append(dict(**task,candidates=len(ranked),score_rows=store.db.execute('SELECT COUNT(*) FROM scores').fetchone()[0],negative_evaluation_r2=int(ranked.evaluation_r2.lt(0).sum()),negative_validation_skill=int(ranked.validation_skill.lt(0).sum()),negative_evaluation_skill=int(ranked.evaluation_skill.lt(0).sum()),svd_fallback_candidates=int(ranked.evaluation_svd.sum()),overlap_flagged=int(ranked.overlap.ne('').sum()),minimum_evaluation_r2=float(ranked.evaluation_r2.min()),maximum_evaluation_r2=float(ranked.evaluation_r2.max()),timing=store.get('timing')))
        for config,mask in [('original',1),('new',2),('combined',None)]:
            subset=ranked if mask is None else ranked[ranked['mask'].eq(mask)]
            for k in [1,2,3]:
                f=subset[subset.k.eq(k)].head(20).copy();f.insert(0,'configuration',config);f.insert(1,'configuration_rank_within_k',np.arange(1,len(f)+1));top.extend(f.to_dict('records'))
        names=spec.predictors(task['track']);id_to_combo=dict(spec.candidates(task['track']))
        for name in focus:
            if name not in names:continue
            contains=ranked.predictors.str.split(' | ',regex=False).map(lambda c:name in c)
            for mode,subset in [('best_including',ranked[contains]),('best_excluding',ranked[~contains])]:
                r=subset.iloc[0];focused.append(dict(**task,focus_predictor=name,comparison=mode,candidate_id=int(r.id),predictors=r.predictors,validation_skill=r.validation_skill,evaluation_skill=r.evaluation_skill,evaluation_r2=r.evaluation_r2,evaluation_rmse=r.evaluation_rmse))
        fold=core.prepare(task,'2018-01-01',None);matched=core.prepare(task,'2010-01-01',None) if task['horizon']=='26' else None
        chosen=[r for r in lock['selections'] if r['task_id']==task['task_id'] and r['selection_count']=='best_any_k']
        forecasts={};models={}
        for r in chosen:
            model=core.export_model(fold,r['predictors'],task,selection_hash);models[r['configuration']]=model
            spec.write_json(spec.PUBLIC/'models'/(task['task_id']+'__'+r['configuration']+'.json'),model)
            forecasts[r['configuration']]=core.predict_model(model,fold.validation)
        debut=core.predict_model(core.export_model(fold,['debut_rank'],task,selection_hash),fold.validation)
        for name,pred in [('training_mean',np.full(len(fold.z),fold.mean)),('training_median',np.full(len(fold.z),fold.median)),('debut_rank_ols',debut)]:
            baselines.append(dict(**task,baseline=name,n_train=len(fold.y),n_evaluation=len(fold.z),**core.metrics(fold.z,pred,fold.u,fold.mean,fold.median)))
        for i,r in enumerate(chosen):
            config=r['configuration'];row=ranked[ranked.id.eq(r['candidate_id'])].iloc[0].to_dict();pred=forecasts[config]
            actual_metrics=core.metrics(fold.z,pred,fold.u,fold.mean,fold.median)
            for metric in ['r2','mae','rmse','skill']:
                if not np.isclose(row['evaluation_'+metric],actual_metrics[metric],rtol=2e-9,atol=1e-7):raise ValueError('Exported prediction mismatch')
            leaderboard.append(dict(configuration=config,**row,debut_rank_baseline_r2=core.metrics(fold.z,debut,fold.u,fold.mean,fold.median)['r2']))
            for item in clustered_intervals(fold.validation,fold.z,pred,fold.mean,forecasts['original'],spec.SEED+i):intervals.append(dict(**task,configuration=config,**item))
            for number,m in enumerate(meta[:3]):
                score=dict(store.db.execute('SELECT * FROM scores WHERE id=? AND fold=?',(r['candidate_id'],number)).fetchone())
                period_rank=store.db.execute('SELECT COUNT(*) FROM scores s JOIN candidates c ON s.id=c.id WHERE fold=? AND (s.skill>? OR (s.skill=? AND (c.k<? OR (c.k=? AND c.id<?))))',(number,score['skill'],score['skill'],len(r['predictors']),len(r['predictors']),r['candidate_id'])).fetchone()[0]+1
                stability.append(dict(**task,configuration=config,fold=number,start=m['start'],end=m['end'],n_train=m['n_train'],n_validation=m['n_validation'],rank_among_all_candidates=period_rank,**{k:score[k] for k in ['r2','mae','mse','skill']}))
            for domain in sorted(set(spec.REGISTRY[n]['family'] for n in r['predictors'])):family.append(dict(**task,configuration=config,family=domain,selected_predictors=' | '.join(n for n in r['predictors'] if spec.REGISTRY[n]['family']==domain),predictor_count=sum(spec.REGISTRY[n]['family']==domain for n in r['predictors'])))
            prediction=pd.DataFrame(dict(task_id=task['task_id'],configuration=config,song_id=fold.validation.song_id,actual=fold.z,prediction=pred));predictions.append(prediction)
            if matched is not None:
                oldconfig={'original':'baseline','new':'new_only','combined':'combined'}[config]
                old=v1[v1.track.eq(task['track'])&v1.target.eq(task['target'])&v1.configuration.eq(oldconfig)].sort_values('song_id')
                if old.song_id.tolist()!=fold.validation.song_id.tolist() or not np.array_equal(old.actual.to_numpy(float),fold.z):raise ValueError('V1 population/outcome mismatch')
                old_selection=v1selected[v1selected.track.eq(task['track'])&v1selected.target.eq(task['target'])&v1selected.configuration.eq(oldconfig)].iloc[0]
                oldtrain=v1metrics[v1metrics.track.eq(task['track'])&v1metrics.target.eq(task['target'])&v1metrics.configuration.eq(oldconfig)&v1metrics.method.eq(old_selection.method)&v1metrics.partition.eq('train')].iloc[0]
                if oldtrain.song_ids_sha256!=spec.digest(matched.train.song_id.tolist()):raise ValueError('V1 training population differs')
                oldpred=old.prediction.to_numpy(float)
                matched_model=core.export_model(matched,r['predictors'],task,selection_hash);matched_pred=core.predict_model(matched_model,fold.validation)
                spec.write_json(spec.PUBLIC/'models'/(task['task_id']+'__'+config+'__matched_v1.json'),matched_model)
                for refit,pred2,mean,median,n in [('primary_pre2018',pred,fold.mean,fold.median,len(fold.y)),('matched_v1_pre2010',matched_pred,matched.mean,matched.median,len(matched.y))]:
                    a=core.metrics(fold.z,pred2,fold.u,mean,median);b=core.metrics(fold.z,oldpred,fold.u,mean,median)
                    comparison.append(dict(**task,configuration=config,refit=refit,n_train_v2=n,n_train_v1=len(matched.y),n_evaluation=len(fold.z),v1_method=old_selection.method,v2_predictors=' | '.join(r['predictors']),v1_r2=b['r2'],v2_r2=a['r2'],delta_r2=a['r2']-b['r2'],v1_mae=b['mae'],v2_mae=a['mae'],v1_rmse=b['rmse'],v2_rmse=a['rmse'],rmse_reduction=b['rmse']-a['rmse'],identical_training=refit=='matched_v1_pre2010',identical_evaluation=True))
        store.close();del fold,matched,ranked;gc.collect();print('Reported '+task['task_id'],flush=True)
    board=pd.DataFrame(leaderboard);board['target_skill_rank_within_track_horizon_configuration']=board.groupby(['track','horizon','configuration']).evaluation_skill.rank(ascending=False,method='min').astype(int)
    spec.write_csv(spec.PUBLIC/'target_leaderboard.csv',board);spec.write_csv(spec.PUBLIC/'predictor_hierarchy_top20_by_count.csv',top)
    spec.write_csv(spec.PUBLIC/'baselines.csv',baselines);spec.write_csv(spec.PUBLIC/'selected_uncertainty.csv',intervals);spec.write_csv(spec.PUBLIC/'v1_comparison.csv',comparison)
    spec.write_csv(spec.PUBLIC/'feature_family_winners.csv',family);spec.write_csv(spec.PUBLIC/'focused_predictor_comparison.csv',focused);spec.write_csv(spec.PUBLIC/'historical_stability.csv',stability)
    families=pd.DataFrame(family).groupby(['track','horizon','configuration','family'],as_index=False).agg(winning_targets=('target','nunique'),selected_variable_occurrences=('predictor_count','sum'))
    families['targets_in_each_configuration']=3;spec.write_csv(spec.PUBLIC/'feature_family_comparison.csv',families)
    increments=[]
    for task in spec.tasks():
        selected=board[board.task_id.eq(task['task_id'])].set_index('configuration')
        for config in ['new','combined']:
            r=selected.loc[config];b=selected.loc['original'];increments.append(dict(**task,configuration=config,original_predictors=b.predictors,expanded_predictors=r.predictors,validation_skill_difference=r.validation_skill-b.validation_skill,evaluation_r2_difference=r.evaluation_r2-b.evaluation_r2,evaluation_rmse_reduction=b.evaluation_rmse-r.evaluation_rmse,evaluation_mae_reduction=b.evaluation_mae-r.evaluation_mae))
    spec.write_csv(spec.PUBLIC/'incremental_information.csv',increments)
    manifest.append(save_large(spec.LOCAL/'selected_predictions.csv.gz',pd.concat(predictions,ignore_index=True)))
    spec.write_json(spec.PUBLIC/'local_artifacts.json',manifest);spec.write_json(spec.PUBLIC/'fold_metadata.json',metadata);spec.write_json(spec.PUBLIC/'coverage.json',coverage)
    figures(board,pd.DataFrame(stability),pd.DataFrame(comparison),pd.DataFrame(increments),families)
    findings()
    if spec.sha(spec.PUBLIC/'selection_lock.json')!=selection_hash:raise ValueError('Reporting modified frozen selections')
    spec.write_json(spec.PUBLIC/'report_execution.json',dict(seconds=time.perf_counter()-begun,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,selection_sha256=selection_hash))


def figures(board,stability,comparison,increments,families):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'svg.hashsalt':'regression-expanded-v2','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    directory=spec.PUBLIC/'figures';directory.mkdir(exist_ok=True);manifest=[]
    def save(fig,name,title):
        fig.text(.01,.01,'Exploratory; evaluation previously inspected. Retrospective measurements were obtained later.'+(' Observed history uses a mature/inactive cohort.' if name=='target_predictability' else ''),fontsize=7);fig.tight_layout(rect=(0,.05,1,1));p=directory/(name+'.svg');fig.savefig(p,metadata={'Date':None,'Title':title});preview=spec.LOCAL/'previews';preview.mkdir(exist_ok=True);fig.savefig(preview/(name+'.png'),dpi=130);plt.close(fig)
        p.write_text('\n'.join(s.rstrip() for s in p.read_text().splitlines())+'\n');manifest.append(dict(file=p.name,sha256=spec.sha(p),title=title))
    fig,axes=plt.subplots(1,2,figsize=(12,4),sharey=True,sharex=True)
    for ax,track in zip(axes,spec.CONFIG['tracks']):
        d=board[board.track.eq(track)&board.configuration.eq('combined')];ax.barh(d.horizon.map({'26':'26 weeks','observed_lifetime':'Observed history'})+' / '+d.target.map({'best_rank':'Best rank','chart_weeks':'Weeks','chart_points':'Points'}),d.evaluation_skill,color='#326c98');ax.axvline(0,color='black',lw=.7);ax.set_title(track+' — validation-selected winners');ax.set_xlabel('Evaluation MSE skill vs training mean')
    axes[0].invert_yaxis()
    save(fig,'target_predictability','Exploratory target predictability; observed lifetime is a selected cohort')
    fig,axes=plt.subplots(1,2,figsize=(12,4),sharey=True,sharex=True)
    for ax,track in zip(axes,spec.CONFIG['tracks']):
        d=board[board.track.eq(track)&board.horizon.eq('26')]
        for offset,config in enumerate(['original','new','combined']):
            a=d[d.configuration.eq(config)].set_index('target').loc[spec.TARGETS];ax.bar(np.arange(3)+(offset-1)*.25,a.evaluation_r2,width=.25,label=config)
        ax.set_xticks(range(3),['Best rank','Chart weeks','Chart points']);ax.axhline(0,color='black',lw=.7);ax.set_ylabel('Evaluation R²');ax.set_title(track+' / complete 26-week windows');ax.legend()
    save(fig,'incremental_26_week','Original, new and combined predictors on identical populations')
    fig,axes=plt.subplots(1,2,figsize=(12,4),sharey=True,sharex=True)
    for ax,track in zip(axes,spec.CONFIG['tracks']):
        d=stability[stability.track.eq(track)&stability.horizon.eq('26')&stability.configuration.eq('combined')]
        for target in spec.TARGETS:
            a=d[d.target.eq(target)];ax.plot(a.fold,a.skill,marker='o',label=target)
        ax.set_xticks([0,1,2],['1990–99','2000–09','2010–17']);ax.set_title(track);ax.set_ylabel('Validation MSE skill');ax.legend()
    save(fig,'historical_stability','Historical stability of selected combined 26-week models')
    fig,axes=plt.subplots(1,2,figsize=(12,4),sharey=True,sharex=True)
    for ax,track in zip(axes,spec.CONFIG['tracks']):
        d=comparison[comparison.track.eq(track)&comparison.configuration.eq('combined')&comparison.refit.eq('matched_v1_pre2010')].set_index('target').loc[spec.TARGETS]
        ax.bar(np.arange(3)-.18,d.v1_r2,.36,label='V1 selected model');ax.bar(np.arange(3)+.18,d.v2_r2,.36,label='V2 exhaustive OLS');ax.set_xticks(range(3),['Best rank','Chart weeks','Chart points']);ax.axhline(0,color='black',lw=.7);ax.set_title(track+' / same pre-2010 training');ax.set_ylabel('Evaluation R²');ax.legend()
    save(fig,'v1_matched_comparison','Identical 26-week outcomes, training identities and evaluation identities; selection methods differ')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,track in zip(axes,spec.CONFIG['tracks']):
        d=families[families.track.eq(track)&families.configuration.eq('combined')].groupby('family').winning_targets.sum().sort_values();ax.barh(d.index.str.replace('_',' ').str.title(),d.values);ax.set_title(track);ax.set_xlabel('Winning tasks containing family (of six)')
    save(fig,'family_frequency','Selection frequencies across correlated outcomes are descriptive, not causal')
    spec.write_json(directory/'manifest.json',manifest)



def markdown_table(frame,columns):
    def cell(value):
        if isinstance(value,(float,np.floating)):return f'{value:.3f}'
        return str(value).replace('|',' + ').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']+['| '+' | '.join(cell(r[c]) for c in columns)+' |' for r in frame.to_dict('records')])


def findings():
    board=pd.read_csv(spec.PUBLIC/'target_leaderboard.csv');increments=pd.read_csv(spec.PUBLIC/'incremental_information.csv');v1=pd.read_csv(spec.PUBLIC/'v1_comparison.csv')
    stability=pd.read_csv(spec.PUBLIC/'historical_stability.csv');focus=pd.read_csv(spec.PUBLIC/'focused_predictor_comparison.csv');family=pd.read_csv(spec.PUBLIC/'feature_family_comparison.csv')
    execution=spec.read_json(spec.PUBLIC/'execution.json');coverage=spec.read_json(spec.PUBLIC/'coverage.json')
    combined=board[board.configuration.eq('combined')];strict=combined[combined.track.eq('strict')];retro=combined[combined.track.eq('retrospective')]
    summary=[]
    for (track,name),group in focus.groupby(['track','focus_predictor'],sort=True):
        include=group[group.comparison.eq('best_including')].set_index('task_id');exclude=group[group.comparison.eq('best_excluding')].set_index('task_id')
        winners=combined[combined.track.eq(track)].predictors.str.split(' | ',regex=False).map(lambda c:name in c).sum()
        summary.append(dict(track=track,predictor=name,winning_tasks=int(winners),tasks=6,minimum_validation_skill_advantage=float((include.validation_skill-exclude.validation_skill).min()),maximum_validation_skill_advantage=float((include.validation_skill-exclude.validation_skill).max()),minimum_evaluation_r2_difference=float((include.evaluation_r2-exclude.evaluation_r2).min()),maximum_evaluation_r2_difference=float((include.evaluation_r2-exclude.evaluation_r2).max())))
    spec.write_csv(spec.PUBLIC/'focused_predictor_summary.csv',summary)
    sections=['# Expanded dataset V2: exhaustive OLS findings','Generated from the frozen validation selections and complete evaluation catalog. This is exploratory; the 2018-onward period was previously inspected. **Complete 26-week windows are the primary forecast evidence.** Retrospective and observed-lifetime results carry the limits below.',
        f'All **1,311,090** task/candidate combinations were retained and evaluated: **5,244,360** fits across three validation periods and final evaluation. The numerical search took **{execution["elapsed_seconds_this_invocation"]:.1f} seconds** with **{execution["peak_rss_bytes"]/1024**2:.1f} MiB** peak resident memory. This excludes source preservation, benchmark, reporting and integrity validation. The search used 37 strict variables or 108 retrospective variables, with every eligible one-, two- and three-variable combination.',
        '## Primary strict forecast results',
        'The validation-selected best-rank model carries useful evaluation signal. The selected weeks and points models do not transfer reliably to recent debuts. Negative R² is preserved and is not described as randomness. The table reports the winner selected on validation, not the candidate with the highest evaluation score.',
        markdown_table(strict[strict.horizon.eq('26')],["target","predictors","n_evaluation","validation_skill","evaluation_r2","evaluation_mae","evaluation_rmse","evaluation_skill"]),
        'The outcome includes the debut chart itself, and debut rank is already known. The results therefore concern total performance after first publication, including that known initial contribution. Strict chart history covers identities without content scores as well as the monthly study cohort.',
        '## Observed-history sensitivity',
        'These labels use chart history observed by each cutoff on a cohort at least five years old and inactive for at least two years. They are **not verified completed lifetime outcomes**. Future returns remain possible, and their older, selected populations differ from the complete 26-week population. See `lifetime_return_audit.csv` for later-return diagnostics; no future return was used to decide a historical cohort.',
        markdown_table(strict[strict.horizon.eq('observed_lifetime')],["target","predictors","n_evaluation","evaluation_r2","evaluation_mae","evaluation_rmse","evaluation_skill"]),
        '## Retrospective measurement sensitivity',
        'Modern lyric/classifier, genre and metadata information was explicitly allowed only in this separate sensitivity. Its smaller selected population differs from the strict track. Genre annotation confidence appears in the selected models; it is a measurement-process proxy and does not establish an intrinsic musical mechanism or historically available predictive signal.',
        markdown_table(retro,["horizon","target","predictors","n_evaluation","evaluation_r2","evaluation_mae","evaluation_rmse"]),
        '## Incremental information on identical populations',
        'The following differences compare the combined validation-selected winner with the original-only validation-selected winner, using identical targets, samples, splits and final training. Positive R² differences and positive error reductions favor the combined universe. A larger exhaustive universe can improve validation while making evaluation worse.',
        markdown_table(increments[increments.configuration.eq('combined')],["track","horizon","target","validation_skill_difference","evaluation_r2_difference","evaluation_mae_reduction","evaluation_rmse_reduction"]),
        'For strict 26-week best rank, the primary combined R² gain over original-only is only 0.011. Its paired exact-credit interval is −0.006 to 0.030; this does not establish a robust incremental gain. The debut-year interval is much narrower and uses only nine years. These are conditional exploratory intervals, not selection-adjusted confirmation.',
        'New-only comparisons and all baseline metrics are retained in `incremental_information.csv`, `target_leaderboard.csv` and `baselines.csv`. `selected_uncertainty.csv` gives paired intervals for these improvements by artist credit and debut year. Fixed-prediction intervals do not correct the large model search or previous evaluation inspection.',
        '## Comparison with the previously selected V1 models',
        'This table uses identical pre-2010 training identities and identical complete 26-week evaluation identities/outcomes. V2 combinations were chosen using the frozen multi-period validation rule; V1 retains its existing selected model. Differences also reflect estimator and selection changes, so they cannot be attributed solely to newly engineered features. Primary V2 refits using more recent pre-2018 labels are shown separately in the full CSV.',
        markdown_table(v1[v1.configuration.eq('combined')&v1.refit.eq('matched_v1_pre2010')],["track","target","v1_method","v1_r2","v2_r2","delta_r2","v1_rmse","v2_rmse"]),
        'With the exact V1 pre-2010 training population, all three strict combined OLS winners perform worse than V1. The primary pre-2018 best-rank result benefits from a different training window; it must not be presented as an unqualified improvement over V1. Retrospective matched best-rank and weeks comparisons improve, while points remains weak.',
        '## Requested predictor checks and family contributions',
        'All prior Top-10 count, prior chart-song count, recent presence/momentum, simultaneous-debut, competition, lyric-length/repetition, genre and calendar variables were searched whenever eligible. `focused_predictor_comparison.csv` preserves the best validation-selected combination including and excluding each requested feature. These are comparisons between selected models, not controlled ablations. The table below counts overall combined winners and shows the range of validation advantage across the six outcomes; inclusion can be harmful and a zero count does not prove absence of signal.',
        markdown_table(pd.DataFrame(summary),["track","predictor","winning_tasks","maximum_validation_skill_advantage","minimum_evaluation_r2_difference","maximum_evaluation_r2_difference"]),
        'No lyrical classifier score or lyric-structure construct occurs in the overall combined winners in this campaign. This is a finding within these additive models, selected cohorts and one-to-three-variable limit, not evidence that lyrical content never matters. Prior Top-10 count and recent momentum are also not universal winning predictors. Exact-credit history cannot be interpreted as resolved individual-artist history.',
        markdown_table(family[family.configuration.eq('combined')],["track","horizon","family","winning_targets","selected_variable_occurrences"]),
        'Family frequency is descriptive across correlated outcomes. Annotation confidence can be more prominent than lyric attributes without being a causal or deployable feature.',
        '## Stability and failures to generalize',
        markdown_table(stability[stability.configuration.eq('combined')&stability.horizon.eq('26')],["track","target","start","end","skill","r2","rank_among_all_candidates"]),
        f'Across the full catalog, **{sum(r["negative_evaluation_r2"] for r in coverage):,}** candidates have negative evaluation R², and **{sum(r["negative_evaluation_skill"] for r in coverage):,}** have negative training-mean-relative evaluation skill. All are preserved. Every hierarchy row includes period metrics and evaluation-minus-validation/training gaps. See `coverage.json` for task-specific counts and singular-fit fallbacks.',
        'OLS predictions are unbounded; the search does not clip ranks or counts or silently switch estimators when extrapolation fails. Continuous time, changing entry patterns, outcome distribution shifts and rare measurement categories can make historically useful linear associations unstable. These are plausible limitations, not established causal explanations.',
        '## Presentation-ready takeaways',
        '1. Exhaustive search is computationally feasible; exhaustive enumeration alone does not ensure generalization.\n2. Strict best-rank forecasting is the clearest positive result. Strict chart-weeks and chart-points winners failed on recent debuts.\n3. New-feature gains are target-specific and sometimes negative. Matched V1 comparisons prevent gains from being credited to different evaluation populations or extra training years.\n4. Retrospective genre-confidence associations and selected observed-history outcomes require separate interpretation. They are not equivalent evidence for debut-time lifetime forecasting.\n5. Further work would require new authorization; no acquisition, classification, clustering or COVID analysis was launched.'
    ]
    spec.atomic_bytes(spec.PUBLIC/'findings.md',('\n\n'.join(sections)+'\n').encode())

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--summary-only',action='store_true');parser.add_argument('--query',choices=[t['task_id'] for t in spec.tasks()]);parser.add_argument('--configuration',choices=['original','new','combined'],default='combined');parser.add_argument('--count',type=int,choices=[1,2,3]);parser.add_argument('--limit',type=int,default=20);args=parser.parse_args()
    if args.summary_only:findings()
    elif args.query:
        task=next(t for t in spec.tasks() if t['task_id']==args.query);store=open_store(task);frame,_=enrich(store,store.rankings(True),task)
        if args.configuration!='combined':frame=frame[frame['mask'].eq(1 if args.configuration=='original' else 2)]
        if args.count:frame=frame[frame.k.eq(args.count)]
        print(frame.head(args.limit)[['validation_rank','rank_within_k','predictors','validation_r2','validation_mae','validation_rmse','evaluation_r2','evaluation_mae','evaluation_rmse']].to_csv(index=False),end='');store.close()
    else:report()
