"""Validation-locked V3 summaries, portable models and full-hierarchy query."""
import os
for _key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[_key]='1'
import argparse
import csv
import gc
import json
import resource
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import regression_cross_domain_spec as spec
import regression_cross_domain_core as core
from regression_cross_domain_store import Store,save_array

PRIMARY='provenance_separated'
REQUIRED=['unrestricted_valid','cross_domain',PRIMARY]


def skill(error,baseline):return 1-error/baseline if baseline>0 else float('nan')


def describe(target,names,category):
    families=sorted({spec.REGISTRY[n]['family'] for n in names});tf=spec.REGISTRY[target]['family']
    allfamilies=set(families)|{tf}
    if category<=3:novelty='Expected related-measurement or conceptual-overlap association; not an independent discovery'
    elif tf in ['catalog_coverage','calendar','release_calendar'] or 'catalog_coverage' in families:novelty='Era/catalog-coverage association has limited intrinsic musical novelty'
    elif 'genre_annotation' in families and tf.startswith('lyri'):novelty='Genre/style association is plausible; novelty beyond prior musical knowledge is not established'
    else:novelty='Potentially useful cross-domain association; substantive novelty is unestablished'
    if {'debut_rank','debut_reported_peak_position'}<=set(names)|{target}:novelty='Near-duplicate source fields: reported peak on first observation almost copies observed debut rank; source disagreements prevent universal equality; substantively trivial'
    shared=sorted(set(spec.REGISTRY[target]['provenance'])&{p for n in names for p in spec.REGISTRY[n]['provenance']})
    confounding=['Selected enrichment coverage and shared asset linkage'];reverse=[]
    if allfamilies&{'catalog_coverage','release_calendar','recording_duration','collaboration_entities'}:
        confounding.append('Provider coverage/caps, recording-version mismatch, era and artist popularity');reverse.append('Popular artists/songs may receive more catalog documentation and linked manifestations')
    if allfamilies&{'calendar','release_calendar','chart_context'}:
        confounding.append('Era trends, chart rules and changing genre/language composition');reverse.append('Predicting calendar/context from song properties does not establish that a song caused its historical environment')
    if allfamilies&{'genre_annotation','genre_context','artist_genre_history'}:
        confounding.append('Genre/style composition and unknown learned annotation priors');reverse.append('Genre identity and lyrical choices can be jointly determined, with no causal direction identified')
    if allfamilies&{'lyrical_content','lyrical_affect','lyric_structure','content_reference'}:
        confounding.append('Language, lyrical style, transcriptions and classifier calibration across eras');reverse.append('Artistic choices, audience expectations and prior popularity may shape lyrics together')
    if allfamilies&{'artist_chart_history','entity_history','commercial_performance','debut_chart'}:
        confounding.append('Artist exposure, promotion, credit aliases and commercial selection');reverse.append('Commercial success can influence subsequent artistic choices and metadata coverage')
    if category<=3:confounding.append('Shared construct or measurement pipeline makes high fit unsurprising')
    timing='Retrospective enriched-cohort relationship; not a deployable historical forecast'
    if target in spec.COMMERCIAL and not target.startswith('observed_') and all(spec.REGISTRY[n]['availability']=='C' for n in names):timing='Predictor timing compatible with debut; retrospective enriched selection still prevents deployable-forecast claim'
    return dict(target_family=tf,predictor_families=' | '.join(families),target_provenance=' | '.join(spec.REGISTRY[target]['provenance']),
        predictor_provenance=' | '.join(sorted({p for n in names for p in spec.REGISTRY[n]['provenance']})),shared_recorded_sources=' | '.join(shared),
        measurement_independence='Disjoint recorded source sets; shared selection/identity and unknown learned priors remain' if category==5 else 'Not provenance-independent',
        potential_confounding='; '.join(confounding),reverse_causality='; '.join(reverse) or 'Direction is predictive only; shared underlying artistic and market choices remain possible',
        substantive_surprise=novelty,prediction_timing=timing)


def enrich(store,scores,selected,detail=False,metadata=None):
    if 'candidate_id' not in selected:return dict(selected)
    p=int(selected['row_index']);cid=int(selected['candidate_id']);names=spec.combo(cid)
    if int(store.ids[p])!=cid:raise ValueError('Selected candidate row mismatch')
    r={**selected,'predictors':' | '.join(names),'predictor_count':len(names),'status':'COMPLETE'}
    for key in ['validation_r2','validation_mae','validation_rmse','validation_skill','worst_period_r2','period_r2_range','worst_period_skill','evaluation_r2','evaluation_mae','evaluation_rmse','evaluation_skill']:r[key]=float(scores[key][p])
    meta=metadata if metadata is not None else [store.get('fold_'+str(i)) for i in range(4)]
    for i,m in enumerate(meta[:3]):
        r.update({f'period_{i}_r2':float(scores['period_r2'][i,p]),f'period_{i}_mae':float(store.metrics[i,p,1]),f'period_{i}_rmse':float(np.sqrt(store.metrics[i,p,0])),f'period_{i}_skill':float(scores['period_skill'][i,p])})
    r.update(n_train=meta[3]['n_train'],n_evaluation=meta[3]['n_validation'],n_validation=sum(m['n_validation'] for m in meta[:3]),
        evaluation_baseline_r2=meta[3]['baseline']['baseline_r2'],evaluation_baseline_mae=meta[3]['baseline']['baseline_mae'],evaluation_baseline_rmse=meta[3]['baseline']['baseline_rmse'],
        evaluation_mae_skill=skill(r['evaluation_mae'],meta[3]['baseline']['baseline_mae']),
        validation_mae_skill=float(np.mean([skill(store.metrics[i,p,1],m['baseline']['baseline_mae']) for i,m in enumerate(meta[:3])])),
        evaluation_minus_validation_r2=r['evaluation_r2']-r['validation_r2'],
        positive_every_period=r['worst_period_r2']>0 and r['evaluation_r2']>0,
        beats_mean_and_median_evaluation=r['evaluation_skill']>0 and r['evaluation_mae']<meta[3]['baseline']['baseline_mae'],
        evaluation_rank=int(store.status[3,p]&32767),evaluation_svd_fallback=bool(store.status[3,p]&32768),target_family=spec.REGISTRY[store.target]['family'],
        predictor_families=' | '.join(sorted({spec.REGISTRY[n]['family'] for n in names})),new_predictor_count=sum(spec.REGISTRY[n]['origin']=='new' for n in names))
    if detail:r.update(describe(store.target,names,int(store.categories[p])))
    return r


def artifact(path):return dict(path=str(path.relative_to(spec.ROOT)),bytes=path.stat().st_size,sha256=spec.sha(path))


def normalize_svg(path):
    """Remove renderer trailing whitespace without changing SVG coordinates."""
    spec.atomic_bytes(path,b'\n'.join(line.rstrip() for line in path.read_bytes().splitlines())+b'\n')


class Intervals:
    """Shared seeded cluster draws preserve pairing across selected models."""
    def __init__(self,fold,seed):
        self.fold=fold;self.groups=[];rng=np.random.default_rng(seed)
        for name,labels in [('exact_artist_credit',fold.validation.artist),('debut_year',fold.validation.first_chart_date.str[:4])]:
            codes,levels=pd.factorize(labels,sort=True);n=len(levels)
            counts=rng.multinomial(n,np.full(n,1/n),size=spec.CONFIG['bootstrap_repeats'])
            self.groups.append((name,codes,n,counts))
    def calculate(self,pred,reference):
        f=self.fold;y=f.z;rows=np.column_stack([np.ones(len(y)),y,y*y,(y-pred)**2,abs(y-pred),(y-f.mean)**2,(y-reference)**2]);out=[]
        for name,codes,ngroups,counts in self.groups:
            sums=np.column_stack([np.bincount(codes,weights=rows[:,i],minlength=ngroups) for i in range(rows.shape[1])]);n,sy,sy2,se,ae,base,ref=(counts@sums).T
            var=sy2/n-(sy/n)**2
            with np.errstate(divide='ignore',invalid='ignore'):
                metrics=dict(r2=1-se/(n*var),mae=ae/n,rmse=np.sqrt(se/n),skill=1-se/base,delta_r2_vs_reference=(ref-se)/(n*var),rmse_reduction_vs_reference=np.sqrt(ref/n)-np.sqrt(se/n))
            for metric,values in metrics.items():
                values=values[np.isfinite(values)];lo,hi=np.quantile(values,[.025,.975]) if len(values) else (np.nan,np.nan)
                out.append(dict(grouping=name,groups=ngroups,repeats=spec.CONFIG['bootstrap_repeats'],finite_repeats=len(values),metric=metric,lower=float(lo),upper=float(hi)))
        return out


def diagnostics(fold,pred):
    y=fold.z;years=fold.validation.first_chart_date.str[:4].to_numpy()
    yc=y-pd.Series(y).groupby(years).transform('mean').to_numpy();pc=pred-pd.Series(pred).groupby(years).transform('mean').to_numpy()
    result=dict(within_debut_year_r2=1-float(np.mean((yc-pc)**2))/float(np.mean(yc**2)) if np.mean(yc**2)>0 else None,
        within_year_interpretation='Descriptive evaluation-year centering uses actual labels; not a deployable prediction metric')
    seen=fold.validation.artist.isin(set(fold.train.artist)).to_numpy()
    for name,mask in [('seen_exact_credit',seen),('unseen_exact_credit',~seen)]:
        result[name+'_n']=int(mask.sum())
        result[name+'_r2']=core.metrics(y[mask],pred[mask],np.ones(mask.sum()),fold.mean,fold.median)['r2'] if mask.any() else None
    return result


def report():
    begun=time.perf_counter();execution=spec.read_json(spec.PUBLIC/'execution.json')
    if execution['status']!='COMPLETE':raise ValueError('Full search must complete before reporting')
    lock=spec.read_json(spec.PUBLIC/'selection_lock.json');lockhash=spec.sha(spec.PUBLIC/'selection_lock.json');provenance=spec.provenance()
    if lock['provenance']!=spec.clean(provenance) or execution['selection_sha256']!=lockhash:raise ValueError('Numerical provenance or selection mismatch')
    selected=[];globals_={v:[] for v in spec.VIEWS};baselines=[];uncertainty=[];diagnostic=[];coverage=[];manifest=[];metadata={};families=[]
    for ti,target in enumerate(spec.targets()):
        store=Store(target,provenance);scores=store.scores(True);order=store.order();metadata[target]=[store.get('fold_'+str(i)) for i in range(4)]
        rows=[r for r in lock['selections'] if r['target']==target];chosen=[r for r in rows if 'candidate_id' in r]
        globalrows=[r for values in lock['global_top100_by_validation'].values() for r in values if r['target']==target]
        ids=sorted({r['candidate_id'] for r in chosen+globalrows});fold=core.prepare(target,'2018-01-01',None);models={};predictions={}
        for cid in ids:
            model=core.export_model(fold,spec.combo(cid),lockhash);pred=core.predict_model(model,fold.validation);pos=int(np.searchsorted(store.ids,cid))
            actual=core.metrics(fold.z,pred,fold.u,fold.mean,fold.median)
            np.testing.assert_allclose([actual['mse'],actual['mae']],store.metrics[3,pos],rtol=2e-9,atol=2e-7)
            models[str(cid)]=model;predictions[cid]=pred
        path=store.path/'selected_models.json.gz';spec.write_json(path,models)
        for name,a in [('selected_candidate_ids.npy',np.asarray(ids,np.uint32)),('selected_predictions.npy',np.column_stack([predictions[cid] for cid in ids])),('evaluation_actual.npy',fold.z),('evaluation_song_ids.npy',fold.validation.song_id.to_numpy(dtype=str))]:save_array(store.path/name,a)
        for r in rows:selected.append(enrich(store,scores,r))
        for view,values in lock['global_top100_by_validation'].items():
            for rank,r in enumerate(values,1):
                if r['target']!=target:continue
                row=enrich(store,scores,r,True);row['validation_relationship_rank']=rank;globals_[view].append(row)
                if view in REQUIRED and rank<=15:spec.write_json(spec.PUBLIC/'models'/f'{target}__{r["candidate_id"]}.json',models[str(r['candidate_id'])])
        best={(r['view'],r['configuration']):r for r in chosen if r['selection_count']=='best_any_k'}
        requests=set()
        for (view,config),r in best.items():
            if view==PRIMARY:
                requests.add((r['candidate_id'],r['candidate_id'],'self'))
                if config in ['new','combined']:
                    for reference in ['original','classifier_only']:
                        if (view,reference) in best:requests.add((r['candidate_id'],best[(view,reference)]['candidate_id'],reference))
        for view in REQUIRED:
            for r in lock['global_top100_by_validation'][view][:15]:
                if r['target']==target:requests.add((r['candidate_id'],r['candidate_id'],'self'))
        intervals=Intervals(fold,spec.SEED+ti)
        for cid,refid,reference in sorted(requests):
            for result in intervals.calculate(predictions[cid],predictions[refid]):uncertainty.append(dict(target=target,candidate_id=cid,reference_candidate_id=refid,reference_configuration=reference,**result))
        diagids={cid for cid,_,_ in requests}
        for cid in sorted(diagids):diagnostic.append(dict(target=target,candidate_id=cid,**diagnostics(fold,predictions[cid])))
        for (view,config),r in best.items():
            for family in sorted({spec.REGISTRY[n]['family'] for n in r['predictors']}):
                names=[n for n in r['predictors'] if spec.REGISTRY[n]['family']==family]
                pos=int(r['row_index']);stable=bool(scores['worst_period_r2'][pos]>0 and scores['evaluation_r2'][pos]>0)
                families.append(dict(target=target,target_family=spec.REGISTRY[target]['family'],view=view,configuration=config,predictor_family=family,predictor_count=len(names),new_predictor_count=sum(spec.REGISTRY[n]['origin']=='new' for n in names),predictors=' | '.join(names),positive_every_period=stable))
        baselines.append(dict(target=target,n_train=len(fold.y),n_evaluation=len(fold.z),training_mean=fold.mean,training_median=fold.median,**fold.baseline))
        coverage.append(dict(target=target,candidates=store.n,fits=4*store.n,negative_validation_r2=int((scores['validation_r2']<0).sum()),negative_evaluation_r2=int((scores['evaluation_r2']<0).sum()),negative_evaluation_skill=int((scores['evaluation_skill']<0).sum()),minimum_evaluation_r2=float(np.min(scores['evaluation_r2'])),maximum_evaluation_r2=float(np.max(scores['evaluation_r2'])),fallback_fits=int(((store.status&32768)>0).sum()),timing=store.get('timing')))
        store.close()
        # Every local hierarchy component is independently named and hashed.
        for path in sorted((spec.LOCAL/'targets'/target).iterdir()):
            if path.is_file() and path.suffix in ['.npy','.json','.gz','.sqlite']:manifest.append(artifact(path))
        del fold,store,scores,intervals,models,predictions;gc.collect();print(f'Reported {ti+1}/{len(spec.targets())}: {target}',flush=True)
    board=pd.DataFrame(selected);overall=board[board.selection_count.eq('best_any_k')].copy();bycount=board[~board.selection_count.eq('best_any_k')].copy()
    spec.write_csv(spec.PUBLIC/'target_leaderboard.csv',overall);spec.write_csv(spec.PUBLIC/'best_by_predictor_count.csv',bycount)
    for view,rows in globals_.items():spec.write_csv(spec.PUBLIC/(view.replace('unrestricted_valid','unrestricted')+'_leaderboard.csv'),pd.DataFrame(rows).sort_values('validation_relationship_rank'))
    primary=overall[overall.view.eq(PRIMARY)&overall.configuration.eq('combined')].sort_values(['validation_r2','target'],ascending=[False,True]).copy();primary.insert(0,'validation_target_rank',np.arange(1,len(primary)+1))
    spec.write_csv(spec.PUBLIC/'target_predictability.csv',primary);spec.write_csv(spec.PUBLIC/'baselines.csv',baselines);spec.write_csv(spec.PUBLIC/'selected_uncertainty.csv',uncertainty);spec.write_csv(spec.PUBLIC/'selected_diagnostics.csv',diagnostic)
    increments=[]
    for (target,view),g in overall.groupby(['target','view'],sort=True):
        indexed=g.set_index('configuration')
        for config in ['new','combined']:
            for reference in ['original','classifier_only']:
                a,b=indexed.loc[config],indexed.loc[reference]
                row=dict(target=target,target_family=spec.REGISTRY[target]['family'],view=view,configuration=config,reference_configuration=reference,status='COMPLETE' if a.status==b.status=='COMPLETE' else 'NO_ELIGIBLE_REFERENCE_OR_MODEL')
                if row['status']=='COMPLETE':row.update(candidate_id=int(a.candidate_id),reference_candidate_id=int(b.candidate_id),predictors=a.predictors,reference_predictors=b.predictors,validation_r2_difference=a.validation_r2-b.validation_r2,evaluation_r2_difference=a.evaluation_r2-b.evaluation_r2,evaluation_rmse_reduction=b.evaluation_rmse-a.evaluation_rmse,evaluation_mae_reduction=b.evaluation_mae-a.evaluation_mae,model_positive_every_period=a.positive_every_period,n_train=int(a.n_train),n_evaluation=int(a.n_evaluation))
                increments.append(row)
    spec.write_csv(spec.PUBLIC/'incremental_information.csv',increments)
    family=pd.DataFrame(families);spec.write_csv(spec.PUBLIC/'feature_family_winners.csv',family)
    totals=family.groupby(['view','configuration','target_family','predictor_family'],as_index=False).agg(winning_targets=('target','nunique'),stable_winning_targets=('positive_every_period','sum'),selected_variables=('predictor_count','sum'),new_selected_variables=('new_predictor_count','sum'))
    denominators=overall[overall.status.eq('COMPLETE')].groupby(['view','configuration','target_family'],as_index=False).agg(eligible_targets_in_target_family=('target','nunique'))
    totals=totals.merge(denominators,on=['view','configuration','target_family'],validate='many_to_one');totals['fraction_of_target_family_winners']=totals.winning_targets/totals.eligible_targets_in_target_family
    spec.write_csv(spec.PUBLIC/'feature_family_comparison.csv',totals);spec.write_json(spec.PUBLIC/'coverage.json',coverage);spec.write_json(spec.PUBLIC/'fold_metadata.json',metadata)
    manifest.append(artifact(spec.LOCAL/'candidate_catalog.npy'));spec.write_json(spec.PUBLIC/'local_artifacts.json',manifest)
    evidence={
        'src/classifier_production.py':'Production process reads approved stored lyric text and passes it alone to model tokenization; identity is used to locate/check the asset',
        'src/classifier_production_engine.py':'Four classifier adapters tokenize lyric text only; no chart dates, ranks, artist histories or genre annotations enter model inference',
        'src/lyrics_lrclib_r.py':'Acquisition matching and conservative explicit title/artist/writer-header cleanup use asset identity; this shared linkage/formatting is not independent acquisition',
        'src/feature_expansion_features.py':'Existing scalar definitions and strict-prefix history/context calculations; content distances reuse the focal score vector',
        'src/genre_llm.py':'Existing genre payload construction',
        'docs/genre/llm/prompt.txt':'Existing genre prompt consumes identity/date and linked tags; forbids lyrics, classifier outputs and chart performance'}
    spec.write_json(spec.PUBLIC/'measurement_source_evidence.json',dict(scope='Recorded numerical measurement inputs; common asset matching, approved-text cleanup and enrichment selection remain shared and are not claimed independent',files={name:dict(sha256=spec.sha(spec.ROOT/name),evidence=description) for name,description in evidence.items()}))
    duplicates=[]
    populations=[('all_expanded_source',spec.v2.source_frame()),('enriched_post_burnin_base',spec.source_frame())]
    for number,(start,end) in enumerate(spec.FOLDS+[('2018-01-01',None)]):
        train,valid=spec.partition('debut_rank',start,end);populations.extend([(f'fold_{number}_training',train),(f'fold_{number}_heldout',valid)])
    for label,frame in populations:
        f=frame[['debut_rank','debut_reported_peak_position']].dropna();different=f.debut_rank.ne(f.debut_reported_peak_position)
        duplicates.append(dict(population=label,complete_pairs=len(f),exactly_equal=int((~different).sum()),unequal=int(different.sum()),equal_fraction=float((~different).mean()),maximum_absolute_difference=float(abs(f.debut_rank-f.debut_reported_peak_position).max()),interpretation='Distinct source fields with observed disagreements; near-duplicate B relationship, not an independent or interesting discovery'))
    spec.write_csv(spec.PUBLIC/'near_duplicate_audit.csv',duplicates)
    figures(overall,primary,pd.DataFrame(increments),pd.DataFrame(uncertainty),pd.DataFrame(diagnostic),totals)
    findings()
    readme()
    if spec.sha(spec.PUBLIC/'selection_lock.json')!=lockhash:raise ValueError('Reporting changed selections')
    spec.write_json(spec.PUBLIC/'report_execution.json',dict(seconds=time.perf_counter()-begun,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,selection_sha256=lockhash))


def query(target,view,configuration,count,limit,output):
    store=Store(target);scores=store.scores(True);order=store.order();positions=order[store.subset(view,configuration,count)[order]]
    if limit:positions=positions[:limit]
    metadata=[store.get('fold_'+str(i)) for i in range(4)];path=Path(output) if output else None
    if path:path.parent.mkdir(parents=True,exist_ok=True)
    destination=path.with_name(path.name+'.tmp') if path else None;stream=destination.open('w',newline='',encoding='utf-8') if path else sys.stdout;writer=None
    if not len(positions):
        row=dict(target=target,view=view,configuration=configuration,selection_count=count or 'best_any_k',status='NO_ELIGIBLE_COMBINATIONS');writer=csv.DictWriter(stream,fieldnames=list(row),lineterminator='\n');writer.writeheader();writer.writerow(row)
    for rank,p in enumerate(positions,1):
        selected=dict(target=target,view=view,configuration=configuration,selection_count=count or 'best_any_k',row_index=int(p),candidate_id=int(store.ids[p]),category_code=int(store.categories[p]),category=spec.CATEGORIES[int(store.categories[p])])
        row=dict(validation_rank=rank,**enrich(store,scores,selected,metadata=metadata))
        if writer is None:writer=csv.DictWriter(stream,fieldnames=list(row),lineterminator='\n');writer.writeheader()
        writer.writerow(row)
    store.close()
    if path:stream.close();destination.replace(path)


def figures(overall,primary,increments,uncertainty,diagnostic,families):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm
    from matplotlib.ticker import FixedLocator,FuncFormatter
    matplotlib.rcParams.update({'svg.hashsalt':'cross-domain-v3','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    directory=spec.PUBLIC/'figures';directory.mkdir(exist_ok=True);preview=spec.LOCAL/'figure_previews';preview.mkdir(exist_ok=True);manifest=[]
    def label(s):return s.replace('observed_lifetime_','history_').replace('credited_entities_','entities_').replace('previous_chart_','prev_chart_').replace('_',' ')
    def save(fig,name,title):
        fig.suptitle(title,fontsize=14,fontweight='bold',x=.02,ha='left');fig.text(.02,.015,'V3 exploratory retrospective analysis • examples fixed by validation • evaluation previously inspected',fontsize=8,color='#555555')
        fig.tight_layout(rect=(0,.04,1,.95));path=directory/(name+'.svg');fig.savefig(path,metadata={'Date':None},bbox_inches='tight');normalize_svg(path);fig.savefig(preview/(name+'.png'),dpi=130,bbox_inches='tight');plt.close(fig)
        manifest.append(dict(file=path.name,title=title,sha256=spec.sha(path),selection='Fixed validation winners; never selected by evaluation score'))
    lead=primary.head(15).iloc[::-1];y=np.arange(len(lead));fig,ax=plt.subplots(figsize=(12,8))
    ax.barh(y+.18,lead.validation_r2,.34,label='Mean historical validation',color='#245b80');ax.barh(y-.18,lead.evaluation_r2,.34,label='2018+ evaluation',color='#e89737');ax.set_yticks(y,[label(t) for t in lead.target]);ax.axvline(0,color='gray',lw=.8);ax.set_xlabel('R²');ax.legend(loc='lower right');save(fig,'01_primary_target_hierarchy','Most predictable targets with separate recorded measurement sources')
    pivot=overall[overall.configuration.eq('combined')&overall.view.isin(REQUIRED)].pivot(index='target',columns='view',values='validation_r2').reindex(primary.target)
    fig,ax=plt.subplots(figsize=(11,5))
    for view,color in zip(REQUIRED,['#9b526b','#3c927d','#245b80']):ax.plot(np.arange(len(pivot)),pivot[view],'.',ms=4,label=view.replace('_',' '),color=color)
    ax.axhline(0,color='gray',lw=.8);ax.set_xlabel('Target order fixed by primary validation R²');ax.set_ylabel('Mean validation R² (symmetric log)');ax.set_yscale('symlog',linthresh=.05);ax.margins(y=.07);ax.yaxis.set_major_locator(FixedLocator([-100,-10,-1,-.1,0,.1,1]));ax.yaxis.set_major_formatter(FuncFormatter(lambda value,pos:f'{value:g}'));ax.legend();save(fig,'02_separation_cost','Predictability changes as measurement separation becomes stricter')
    compare=increments[increments.view.eq(PRIMARY)&increments.reference_configuration.eq('original')&increments.status.eq('COMPLETE')]
    fig,axes=plt.subplots(1,2,figsize=(12,5),sharex=True,sharey=True)
    for ax,config in zip(axes,['new','combined']):
        g=compare[compare.configuration.eq(config)];ax.scatter(g.validation_r2_difference,g.evaluation_r2_difference,s=17,alpha=.65,color='#245b80');ax.axhline(0,color='gray',lw=.8);ax.axvline(0,color='gray',lw=.8);ax.set_xscale('symlog',linthresh=.05);ax.set_yscale('symlog',linthresh=.05);ax.set_title(config.title()+' versus original');ax.set_xlabel('Validation R² difference (symmetric log)')
        for axis in [ax.xaxis,ax.yaxis]:axis.set_major_locator(FixedLocator([-100,-10,-1,-.1,0,.1,1,10,100]));axis.set_major_formatter(FuncFormatter(lambda value,pos:f'{value:g}'))
    axes[0].set_ylabel('Evaluation R² difference (symmetric log)');save(fig,'03_new_information','Do new constructs improve provenance-separated prediction?')
    fm=families[families.view.eq(PRIMARY)&families.configuration.eq('combined')].pivot_table(index='target_family',columns='predictor_family',values='winning_targets',fill_value=0)
    fig,ax=plt.subplots(figsize=(13,8));im=ax.imshow(fm.to_numpy(),cmap='Blues',aspect='auto');ax.set_xticks(np.arange(len(fm.columns)),[label(x) for x in fm.columns],rotation=50,ha='right');ax.set_yticks(np.arange(len(fm)),[label(x) for x in fm.index]);fig.colorbar(im,ax=ax,label='Targets whose selected model includes family')
    for i in range(len(fm)):
        for j in range(len(fm.columns)):
            value=int(fm.iloc[i,j])
            if value:ax.text(j,i,str(value),ha='center',va='center',fontsize=8,color='white' if value>fm.to_numpy().max()*.6 else 'black')
    save(fig,'04_family_contributions','Predictor families in the primary winners (correlated targets, descriptive counts)')
    lead=primary.head(15);values=lead[[f'period_{i}_r2' for i in range(3)]+['evaluation_r2']].to_numpy();fig,ax=plt.subplots(figsize=(10,8));im=ax.imshow(values,cmap='RdBu',norm=TwoSlopeNorm(vcenter=0,vmin=min(-.01,values.min()),vmax=max(.01,values.max())),aspect='auto')
    ax.set_yticks(np.arange(len(lead)),[label(t) for t in lead.target]);ax.set_xticks(np.arange(4),['1990–1999','2000–2009','2010–2017','2018+ evaluation'])
    for i in range(len(lead)):
        for j in range(4):ax.text(j,i,f'{values[i,j]:.2f}',ha='center',va='center',fontsize=9,color='white' if im.norm(values[i,j])<.18 or im.norm(values[i,j])>.82 else 'black')
    fig.colorbar(im,ax=ax,label='R²; full observed range');save(fig,'05_historical_stability','Primary leading targets across all historical periods')
    fig,axes=plt.subplots(2,2,figsize=(12,10))
    for ax,r in zip(axes.flat,primary.head(4).itertuples()):
        base=spec.LOCAL/'targets'/r.target;ids=np.load(base/'selected_candidate_ids.npy');p=np.load(base/'selected_predictions.npy')[:,int(np.flatnonzero(ids==r.candidate_id)[0])];a=np.load(base/'evaluation_actual.npy')
        ax.hexbin(a,p,gridsize=38,mincnt=1,cmap='Blues',bins='log');lo=min(a.min(),p.min());hi=max(a.max(),p.max());ax.plot([lo,hi],[lo,hi],color='#d07e2b',lw=1);ax.set_xlabel('Observed');ax.set_ylabel('OLS prediction');ax.set_title(label(r.target)+f'\nEvaluation R² {r.evaluation_r2:.3f}; n={int(r.n_evaluation):,}',fontsize=10)
    fig.text(.02,.045,'Darker hexagons mean more songs within each panel (log scale); orange line marks prediction = observed.',fontsize=8,color='#555555')
    save(fig,'06_observed_predictions','Evaluation predictions for the first four primary validation targets')
    fig,axes=plt.subplots(1,2,figsize=(13,8),sharey=True);lead=primary.head(15).iloc[::-1]
    for ax,group in zip(axes,['exact_artist_credit','debut_year']):
        for i,r in enumerate(lead.itertuples()):
            point=increments[increments.target.eq(r.target)&increments.view.eq(PRIMARY)&increments.configuration.eq('combined')&increments.reference_configuration.eq('original')]
            ci=uncertainty[uncertainty.target.eq(r.target)&uncertainty.candidate_id.eq(r.candidate_id)&uncertainty.reference_configuration.eq('original')&uncertainty.grouping.eq(group)&uncertainty.metric.eq('delta_r2_vs_reference')]
            if len(point) and len(ci) and pd.notna(point.iloc[0].evaluation_r2_difference):
                d=float(point.iloc[0].evaluation_r2_difference);lo,hi=ci.iloc[0][['lower','upper']];ax.plot([lo,hi],[i,i],color='#245b80');ax.plot(d,i,'o',color='#245b80',ms=4)
        ax.axvline(0,color='gray',lw=.8);ax.set_yticks(np.arange(len(lead)),[label(t) for t in lead.target]);ax.set_xlabel('Evaluation ΔR² versus original-only');ax.set_title('Resample '+group.replace('_',' '))
    save(fig,'07_incremental_uncertainty','Combined versus original: paired fixed-prediction 95% intervals')
    dg=primary.merge(diagnostic,on=['target','candidate_id'],validate='one_to_one').head(15).iloc[::-1];fig,ax=plt.subplots(figsize=(12,8));y=np.arange(len(dg));ax.barh(y+.18,dg.evaluation_r2,.34,label='Ordinary evaluation R²',color='#245b80');ax.barh(y-.18,dg.within_debut_year_r2,.34,label='Within debut year diagnostic',color='#e89737');ax.axvline(0,color='gray',lw=.8);ax.set_yticks(y,[label(t) for t in dg.target]);ax.set_xlabel('R² (year centering is diagnostic, uses evaluation labels)');ax.legend();save(fig,'08_era_diagnostic','How much leading prediction persists within the same debut year?')
    lead=primary[primary.target_family.isin(['lyrical_content','lyrical_affect','lyric_structure'])].head(15).iloc[::-1];fig,ax=plt.subplots(figsize=(12,8));y=np.arange(len(lead));ax.barh(y+.18,lead.validation_r2,.34,label='Mean historical validation',color='#245b80');ax.barh(y-.18,lead.evaluation_r2,.34,label='2018+ evaluation',color='#e89737');ax.axvline(0,color='gray',lw=.8);ax.set_yticks(y,[label(t) for t in lead.target]);ax.set_xlabel('R²');ax.legend();save(fig,'09_lyrical_targets','Lyrical measurements predicted from separate recorded domains')
    spec.write_json(directory/'manifest.json',manifest)


def markdown_table(frame,columns):
    rows=['| '+' | '.join(columns.values())+' |','| '+' | '.join(['---']*len(columns))+' |']
    for _,r in frame.iterrows():
        values=[]
        for key in columns:
            v=r[key]
            if isinstance(v,(float,np.floating)):v=f'{v:.3f}'
            values.append(str(v).replace(' | ',' + ').replace('|','/'))
        rows.append('| '+' | '.join(values)+' |')
    return '\n'.join(rows)


def findings():
    primary=pd.read_csv(spec.PUBLIC/'target_predictability.csv');board=pd.read_csv(spec.PUBLIC/'target_leaderboard.csv');increments=pd.read_csv(spec.PUBLIC/'incremental_information.csv');coverage=spec.read_json(spec.PUBLIC/'coverage.json');execution=spec.read_json(spec.PUBLIC/'execution.json');audit=spec.read_json(spec.PUBLIC/'audit.json');uncertainty=pd.read_csv(spec.PUBLIC/'selected_uncertainty.csv');diagnostic=pd.read_csv(spec.PUBLIC/'selected_diagnostics.csv')
    lines=['# Cross-domain discovery V3: completed exploratory findings','',f"The complete campaign evaluated **{audit['valid_task_candidate_pairs']:,} valid target/combination pairs** across **{audit['eligible_targets']} supported numerical targets** and **{audit['predictors']} predictor constructs**, including all 57 new constructs. Three historical validations plus final evaluation produced **{audit['total_fits']:,} OLS fits**. Two of 125 meaningful numerical target candidates lacked historical support.",'',f"Full search elapsed time was **{execution['elapsed_seconds_this_invocation']/60:.2f} minutes**, with peak process RSS **{execution['peak_rss_bytes']/1024**3:.3f} GiB**. This excludes the separately recorded audit, benchmark, reporting and independent validation. All combinations and all negative results remain in the local hierarchy.",'','## What the primary view says','',f"Of {len(primary)} primary selected target models, **{int(primary.positive_every_period.sum())}** have positive R² in all three validation periods and in evaluation; **{int(primary.evaluation_r2.gt(0).sum())}** have positive evaluation R². These are descriptive stability counts, not multiplicity-adjusted discoveries. Winners were fixed using validation only, including winners that fail evaluation.",'','The primary view requires different substantive domains and disjoint recorded measurement-source sets. It does not establish statistical independence or causality. Models use a selected, retrospectively enriched population; target-specific sample sizes differ. The evaluation period was inspected in earlier campaigns.','']
    columns={'target':'Target','predictors':'Predictors','category_code':'Category¹','validation_r2':'Validation R²','evaluation_r2':'Evaluation R²','worst_period_r2':'Worst historical R²','evaluation_mae':'Evaluation MAE','evaluation_rmse':'Evaluation RMSE','n_evaluation':'n'}
    for view,title in [('unrestricted','Unrestricted valid'),('cross_domain','Cross-domain'),(PRIMARY,'Strictly provenance-separated (primary)')]:
        f=pd.read_csv(spec.PUBLIC/(view+'_leaderboard.csv')).head(15)
        lines+=['## Top 15 '+title.lower()+' relationships','',markdown_table(f,columns),'','These are the actual global top combinations by validation R². Repeated targets and closely related variants are retained; they are not 15 independent discoveries. The CSV includes measurement independence, likely confounding, possible reverse direction, substantive-surprise assessment, baseline improvements and period metrics.','']
        if view=='unrestricted':
            a=pd.read_csv(spec.PUBLIC/'near_duplicate_audit.csv');r=a[a.population.eq('enriched_post_burnin_base')].iloc[0]
            lines += [f"The near-perfect debut-rank relationships are substantively trivial: source-reported peak on the first observation almost copies observed debut rank. These are distinct source fields with {int(r.unequal):,} disagreements among {int(r.complete_pairs):,} enriched identities, so they are not a universal exact mathematical duplicate. They remain category B in the unrestricted audit and are excluded from both cross-domain views. The [near-duplicate audit](near_duplicate_audit.csv) records each historical population; no source values are repaired.",'']
    lines+=['¹ Category codes: 2 = same family (B), 3 = conceptual overlap (C), 4 = distinct domains with shared recorded sources (D), 5 = distinct domains and disjoint recorded sources (E). A dependencies are excluded from all valid selections.','','## Target predictability hierarchy','', 'Most predictable primary targets, ranked by validation:', '',markdown_table(primary.head(10),{'target':'Target','predictors':'Best predictors','validation_r2':'Validation R²','evaluation_r2':'Evaluation R²','positive_every_period':'Positive every period'}),'','Least predictable primary targets, also ranked by validation:', '',markdown_table(primary.tail(10).iloc[::-1],{'target':'Target','predictors':'Best predictors','validation_r2':'Validation R²','evaluation_r2':'Evaluation R²'}),'','Every one-, two-, three-predictor and overall winner is in [best-by-count](best_by_predictor_count.csv) and [target leaderboard](target_leaderboard.csv), with all views/configurations. The complete locally stored candidate hierarchies are documented in the README.','','## New information and the classifier baseline','']
    musical=primary[primary.target_family.isin(['lyrical_content','lyrical_affect','lyric_structure'])]
    lines+=['The strongest primary lyrical-target winners by validation are shown below, including evaluation failures. This focuses attention on musical measurements while retaining the global catalog/calendar results above.','',markdown_table(musical.head(12),{'target':'Lyrical target','predictors':'Separate-domain predictors','validation_r2':'Validation R²','evaluation_r2':'Evaluation R²','positive_every_period':'Positive every period'}),'',f"Across all {len(musical)} lyrical targets, {int(musical.positive_every_period.sum())} fixed primary winners have positive R² in every historical validation period and evaluation. This is exploratory stability, not confirmation of novelty.",'']
    for reference in ['original','classifier_only']:
        for config in ['new','combined']:
            f=increments[increments.view.eq(PRIMARY)&increments.reference_configuration.eq(reference)&increments.configuration.eq(config)&increments.status.eq('COMPLETE')]
            lines.append(f"- {config.title()} versus {reference.replace('_',' ')}: {len(f)} comparable primary targets; {int(f.validation_r2_difference.gt(1e-10).sum())} validation improvements, {int(f.evaluation_r2_difference.gt(1e-10).sum())} evaluation improvements, and {int((f.validation_r2_difference.gt(1e-10)&f.evaluation_r2_difference.gt(1e-10)).sum())} improvements in both. Median evaluation ΔR² = {f.evaluation_r2_difference.median():.4f}.")
    lines+=['','Classifier-only comparisons are unavailable for lyric-derived targets in the primary view because the classifiers share lyric provenance. An unavailable comparator is not a failed model. Original-only also contains pre-existing nonclassifier metadata and commercial measurements, so the two baselines answer different questions.','','Largest primary combined-versus-original validation gains (evaluation retained regardless of outcome):','']
    f=increments[increments.view.eq(PRIMARY)&increments.configuration.eq('combined')&increments.reference_configuration.eq('original')&increments.status.eq('COMPLETE')].sort_values(['validation_r2_difference','target'],ascending=[False,True])
    lines+=[markdown_table(f.head(15),{'target':'Target','predictors':'Combined predictors','validation_r2_difference':'Validation ΔR²','evaluation_r2_difference':'Evaluation ΔR²','evaluation_rmse_reduction':'RMSE reduction'}),'','Family occurrences are in [feature-family comparison](feature_family_comparison.csv). They describe the frozen winners across correlated targets; they are not causal importance estimates. Lyric structure cannot count as provenance-separated prediction of a classifier score because both use lyrics.','','## Reliability, negative results and limitations','',f"The full valid hierarchy retains **{sum(r['negative_validation_r2'] for r in coverage):,}** negative mean-validation-R² combinations and **{sum(r['negative_evaluation_r2'] for r in coverage):,}** negative evaluation-R² combinations. Negative values are never truncated or removed. **{int(primary.evaluation_r2.le(0).sum())}** primary winners have nonpositive evaluation R².",'','Paired artist-credit and debut-year intervals use 499 fixed-prediction cluster resamples. They omit refitting and exhaustive-search uncertainty and do not correct for multiple comparisons. Exact credits leave unresolved aliases and collaboration overlap. Year resampling has few clusters. [Selected diagnostics](selected_diagnostics.csv) also report seen/unseen exact-credit performance and within-debut-year R²; the latter centers using actual evaluation outcomes and is not a deployable metric.','','High unrestricted R² can reflect expected relationships among measurement families or retrospective commercial quantities. Calendar and linked-catalog relationships have limited intrinsic musical novelty. A genre-to-lyric association is plausible stylistically; disjoint recorded pipelines do not rule out learned genre-model knowledge. No leading relationship is labeled a novel causal discovery.','','Other limitations include language/style and era confounding, selected enrichment coverage, target-specific missingness, imputation without availability indicators, imperfect linked recordings, provider catalog caps, unclipped OLS for binary targets, and uncertainty about original release dates. Observed-history labels use cutoff-specific maturity/inactivity rules but are not verified completed careers. All comparisons are exploratory.','','## Reproduction and validation','', 'See the [README](README.md), [methodology](methodology.md), [coverage](coverage.json), [runtime](execution.json), [benchmark](benchmark.json), and [figure manifest](figures/manifest.json). Complete coverage, independent full-row SVD replay, deterministic regeneration, checkpoint recovery and protected-source preservation are checked by `src/regression_cross_domain_validate.py`. Validation results are published only after those checks complete.','']
    # Insert actual paired evidence before the limitations, without reselecting models.
    extra=[]
    for reference in ['original','classifier_only']:
        inc=increments[increments.view.eq(PRIMARY)&increments.configuration.eq('combined')&increments.reference_configuration.eq(reference)&increments.status.eq('COMPLETE')]
        paired=uncertainty[uncertainty.reference_configuration.eq(reference)&uncertainty.metric.eq('delta_r2_vs_reference')].pivot_table(index=['target','candidate_id'],columns='grouping',values='lower').reset_index()
        merged=inc.merge(paired,on=['target','candidate_id'],how='left',validate='one_to_one');robust=(merged.exact_artist_credit.gt(0)&merged.debut_year.gt(0))
        extra.append(f"Combined versus {reference.replace('_',' ')}: {int(robust.sum())}/{len(merged)} comparable targets have a positive lower bound for evaluation ΔR² under both clustering schemes. These fixed-prediction intervals exclude search uncertainty.")
    baseline=board[board.view.eq(PRIMARY)&board.configuration.eq('classifier_only')&board.status.eq('COMPLETE')][['target','validation_r2','evaluation_r2']].rename(columns={'validation_r2':'classifier_validation_r2','evaluation_r2':'classifier_evaluation_r2'})
    cmp=primary.merge(baseline,on='target',validate='one_to_one');cmp['validation_gain']=cmp.validation_r2-cmp.classifier_validation_r2
    extra+=['','Largest validation gains over the classifier-only baseline, with absolute performance:', '',markdown_table(cmp.sort_values(['validation_gain','target'],ascending=[False,True]).head(10),{'target':'Target','predictors':'Combined predictors','validation_r2':'Combined validation R²','evaluation_r2':'Combined evaluation R²','classifier_validation_r2':'Classifier validation R²','classifier_evaluation_r2':'Classifier evaluation R²'}),'']
    cross=increments[increments.view.eq('cross_domain')&increments.configuration.eq('combined')&increments.reference_configuration.eq('original')&increments.status.eq('COMPLETE')]
    extra += [f"In the broader D/E cross-domain view, combined models improve validation for {int(cross.validation_r2_difference.gt(1e-10).sum())}/{len(cross)} targets and evaluation for {int(cross.evaluation_r2_difference.gt(1e-10).sum())}/{len(cross)}. This view permits different substantive measurements from the same recorded source; chart-history/context associations can enter here but are not provenance-separated.",'','Largest D/E combined-versus-original validation gains:', '',markdown_table(cross.sort_values(['validation_r2_difference','target'],ascending=[False,True]).head(10),{'target':'Target','predictors':'Combined predictors','validation_r2_difference':'Validation ΔR²','evaluation_r2_difference':'Evaluation ΔR²'}),'']
    fam=pd.read_csv(spec.PUBLIC/'feature_family_winners.csv');fam=fam[fam.view.isin(['cross_domain',PRIMARY])&fam.configuration.eq('combined')&fam.new_predictor_count.gt(0)]
    fam=fam.groupby(['view','predictor_family'],as_index=False).agg(target_winners=('target','nunique'),stable_target_winners=('positive_every_period','sum'),new_variable_occurrences=('new_predictor_count','sum')).sort_values(['view','target_winners','predictor_family'],ascending=[True,False,True])
    extra += ['New-feature families occurring in selected combined models (counts do not isolate a causal contribution):','',markdown_table(fam,{'view':'View','predictor_family':'New family','target_winners':'Selected targets','stable_target_winners':'Stable selected targets','new_variable_occurrences':'New variable occurrences'}),'']
    word=primary[primary.target.eq('lyric_word_count')].iloc[0];vocab=primary[primary.target.eq('lyric_vocabulary_size')].iloc[0]
    gains=increments[increments.view.eq(PRIMARY)&increments.configuration.eq('combined')&increments.reference_configuration.eq('original')].set_index('target')
    extra += ['Two leading lexical targets show why additional features need separate evaluation: the word-count winner adds preceding-chart incumbent age to primary/secondary genre and reaches evaluation R² '+f'{word.evaluation_r2:.3f}, an improvement of {gains.loc["lyric_word_count","evaluation_r2_difference"]:.3f} over original-only. The vocabulary winner adds prior-year unique chart-song count to genre and reaches {vocab.evaluation_r2:.3f}, a change of {gains.loc["lyric_vocabulary_size","evaluation_r2_difference"]:.3f}. The former gain and latter deterioration have the same direction under both paired clustering schemes. These associations may reflect chart-era and genre composition; they do not identify a causal effect of chart context.','']
    dg=primary.merge(diagnostic,on=['target','candidate_id'],validate='one_to_one').set_index('target')
    extra += [f"The vocabulary association remains positive within debut years (diagnostic R² {dg.loc['lyric_vocabulary_size','within_debut_year_r2']:.3f}) and for unseen exact artist credits ({dg.loc['lyric_vocabulary_size','unseen_exact_credit_r2']:.3f}); explicit-language and toxicity predictions also remain positive in those diagnostics. This rules out neither genre composition nor learned annotation priors. Repeated-bigram and MATTR winners have only about 0.02 evaluation R² and become negative for unseen credits; their positive average stability should not be overstated.",'','The very large negative R² values for calendar targets reflect failed extrapolation into disjoint later date ranges with much smaller within-period variance. Large gains over another very poor model do not make these targets reliably predictable. Ordinary calendar-source proxies were intentionally removed from the strict view.','']
    crossings=[]
    for view in ['cross_domain',PRIMARY]:
        eligible=board[board.view.eq(view)&board.status.eq('COMPLETE')]
        pair=eligible[eligible.configuration.eq('new')].merge(eligible[eligible.configuration.eq('classifier_only')],on='target',suffixes=('_new','_classifier'),validate='one_to_one')
        for r in pair[pair.positive_every_period_new.eq(True)&pair.evaluation_r2_classifier.le(0)].sort_values(['validation_r2_new','target'],ascending=[False,True]).to_dict('records'):
            crossings.append(dict(view=view,target=r['target'],predictors=r['predictors_new'],validation_r2=r['validation_r2_new'],evaluation_r2=r['evaluation_r2_new'],classifier_evaluation_r2=r['evaluation_r2_classifier']))
    extra += ['New-only winners with positive R² in every period where classifier-only evaluation R² is nonpositive are listed below. This is a post-evaluation annotation of already locked winners, not a model-selection rule. The improvements are modest; these cases do not establish independent, multiplicity-adjusted discoveries.','',markdown_table(pd.DataFrame(crossings),{'view':'View','target':'Target','predictors':'New-only predictors','validation_r2':'Validation R²','evaluation_r2':'Evaluation R²','classifier_evaluation_r2':'Classifier evaluation R²'}),'']
    at=lines.index('## Reliability, negative results and limitations');lines[at:at]=extra
    spec.atomic_bytes(spec.PUBLIC/'findings.md','\n'.join(lines).encode())


def readme():
    text='''# Exhaustive cross-domain regression discovery V3

The completed search covers **123 supported numerical targets**, **129 predictor constructs** (all **57 new constructs**) and **40,884,781 valid target/combination pairs**. Three historical validation periods and a final evaluation produce **163,539,124 additive OLS fits**. Two of the 125 meaningful numerical target candidates lack historical support. No additional data, features or classifier measurements were created.

Read [findings](findings.md) for the three requested top-15 tables and the substantive interpretation. The [methodology](methodology.md) and [protocol](protocol.json) define the frozen population, missingness, dependency policy and selection rule. Final evaluation was already inspected in earlier campaigns; these are exploratory retrospective relationships.

## Published results

| Artifact | Contents |
| --- | --- |
| [Target inventory](target_inventory.csv), [predictor inventory](predictor_inventory.csv) | Complete variable definitions, source sets, measurement families and target support |
| [Source-column inventory](source_column_inventory.csv), [relationship pairs](relationship_pairs.csv) | Every input column and every directed numerical-target/predictor relationship, including exclusions |
| [Measurement-source evidence](measurement_source_evidence.json) | Source-code/prompt hashes supporting the recorded provenance classification and its common-linkage limits |
| [Near-duplicate audit](near_duplicate_audit.csv) | Observed debut rank versus source-reported debut peak, including their preserved source disagreements |
| [Search space](search_space.csv), [cohorts](cohorts.csv) | Exact counts by target/view/configuration/variable count and frozen sample-identity hashes |
| [Unrestricted leaderboard](unrestricted_leaderboard.csv) | Global top 100 valid combinations by mean validation R²; related measurements remain |
| [Different-family audit](different_family_audit_leaderboard.csv) | Broader C/D/E view, retaining explicitly flagged conceptual overlaps |
| [Cross-domain leaderboard](cross_domain_leaderboard.csv) | D/E relationships, excluding same families and conceptual-overlap proxies |
| [Provenance-separated leaderboard](provenance_separated_leaderboard.csv) | Primary E view, requiring disjoint recorded measurement sources |
| [Target leaderboard](target_leaderboard.csv), [best by predictor count](best_by_predictor_count.csv) | Best overall and best one/two/three-variable models for every target, view and configuration |
| [Target predictability](target_predictability.csv) | One primary combined winner per target, ranked by validation |
| [Incremental information](incremental_information.csv) | New/combined versus original/classifier-only on identical target populations |
| [Feature-family comparison](feature_family_comparison.csv), [family winners](feature_family_winners.csv) | Descriptive family frequencies; correlated targets are not independent replications |
| [Baselines](baselines.csv), [uncertainty](selected_uncertainty.csv), [diagnostics](selected_diagnostics.csv) | Mean/median baselines, paired cluster intervals, within-year and exact-credit checks |
| [Selection lock](selection_lock.json), [coverage](coverage.json), [fold metadata](fold_metadata.json) | Frozen validation choices, complete fit accounting and exact metric denominators |
| [Benchmark](benchmark.json), [execution](execution.json), [report execution](report_execution.json) | Actual budget projection and separate search/report resource measurements |
| [Figures](figures/manifest.json), [portable models](models/) | Nine SVG figures and portable model exports for the three top-15 views |
| [Local artifact manifest](local_artifacts.json) | Names, sizes and hashes of all complete local hierarchy components and selected predictions |

`NO_ELIGIBLE_COMBINATIONS` is an explicit policy result, not a missing search. For example, a lyric-derived target has no provenance-separated classifier-only model because both use lyrics. Negative R² and singular models remain represented. Binary-target OLS is unclipped and is not calibrated classification.

`audit.json` preserves the prelaunch inventory stage. The completed search status and actual fit count are in `execution.json`; the earlier audit's stage flags are not a live execution tracker.

## Reproduction

Run from the canonical repository root with the existing Python numerical environment:

```bash
python3 src/regression_cross_domain_spec.py preserve
python3 src/regression_cross_domain_spec.py audit
python3 src/regression_cross_domain_search.py benchmark
python3 src/regression_cross_domain_search.py run
python3 src/regression_cross_domain_report.py report
python3 -m unittest discover -s tests -v > data/experiments/regression_cross_domain_v3/tests.log 2>&1
python3 src/regression_cross_domain_validate.py validate
python3 src/regression_cross_domain_validate.py snapshot
python3 src/regression_cross_domain_report.py report
python3 src/regression_cross_domain_validate.py check-determinism
python3 src/regression_cross_domain_validate.py publish-manifest
python3 src/regression_cross_domain_validate.py verify-publication
```

The search refuses a changed numerical protocol, code, source or environment. The measured launch projection must remain within four hours and 15 GB, with disk headroom. It resumes verified committed chunks; there is no silent candidate reduction. Existing prior work is protected by the preservation snapshot. Regeneration of completed summaries does not require rerunning the exhaustive fits. Private source inputs are not acquired or reconstructed by these commands.

The independent validator records `validation.json`; complete report regeneration records `determinism.json`. The publication manifest is created only after both pass, including protected-source preservation. Existing project navigation and frozen release dependencies remain unchanged; the campaign has its own documentation entry at `docs/regression_cross_domain_v3.md`.

## Complete local hierarchy

Large results remain under ignored `data/experiments/regression_cross_domain_v3/`. They contain all valid combinations, including negative results, rather than only the published top rows. Query them without refitting:

```bash
python3 src/regression_cross_domain_report.py query --target ll_violence --view provenance_separated --configuration combined --limit 20
python3 src/regression_cross_domain_report.py query --target lyric_word_count --view cross_domain --count 2 --limit 20
python3 src/regression_cross_domain_report.py query --target ll_violence --view unrestricted_valid --limit 0 --output data/experiments/regression_cross_domain_v3/ll_violence_all.csv
```

`--limit 0` streams the complete requested target/view/configuration as CSV. The canonical compact arrays preserve float64 values; text exports may be much larger. Required local files are listed and hashed in the public manifest:

- `candidate_catalog.npy`: all 357,889 global unordered one/two/three-variable combinations; uint8 indices into the sorted predictor inventory, with 255 padding.
- `targets/<target>/categories.npy` and `exclusion_rules.npy`: all global combinations, including A exclusions. Categories are 1=A through 5=E; rule bits are defined in the protocol.
- `valid_ids.npy`: uint32 global candidate IDs for valid rows. `metrics.npy` is float64 with shape `(4, valid_candidates, 2)`; axes are period, candidate row, and `(MSE, MAE)`. Periods 0–2 are historical validation; 3 is 2018+ evaluation.
- `status.npy`: uint16 fit rank in the low 15 bits and QR/SVD fallback in the high bit. Constant encoded blocks are removed without deleting conceptual candidates.
- `validation_order.npy`: candidate-row positions ordered by mean historical R², then fewer variables and lexicographic tuple. Evaluation never changes this ordering.
- `checkpoint.sqlite`: checksummed committed chunks and exact period metadata. Together with the arrays it supports recovery and exact R²/RMSE/baseline-skill reconstruction.
- `selected_models.json.gz`, `selected_candidate_ids.npy`, `selected_predictions.npy`, `evaluation_actual.npy` and `evaluation_song_ids.npy`: portable models and replayable predictions for every published selection plus global top-100 combinations.

R² uses the held-out target variance. MSE skill uses the held-out error of the training mean; MAE skill uses the training median. Mean validation R² and MAE weight the three periods equally; validation RMSE is the square root of the equal-period mean MSE. The three period metrics remain separately available. A predictor with several encoded categories still counts as one original construct.

## Interpretation

Category E describes disjoint **recorded measurement pipelines**, not statistical independence, unknown pretrained knowledge, independent sampling or causality. Lyrics-based classifiers and lyrical structure share a source. Genre annotation uses chart identity/date and linked metadata, so it is not independent of Billboard or MusicBrainz. Common identity joins and retrospective enriched selection remain across every model.

Paired exact-credit and debut-year intervals hold the selected predictions fixed. They omit exhaustive-search and refitting uncertainty. Every figure uses validation-selected models and retains their evaluation failures. The within-year diagnostic centers actual evaluation outcomes and is not a deployable metric. Observed-history outcomes remain censored despite cutoff-specific maturity/inactivity rules. No COVID breakpoint or new statistical campaign is introduced.
'''
    spec.atomic_bytes(spec.PUBLIC/'README.md',text.encode())
    spec.atomic_bytes(spec.ROOT/'docs/regression_cross_domain_v3.md',b'''# Cross-domain regression V3

The completed exhaustive campaign asks which existing numerical variables predict measurements from different information domains. It covers all 123 supported targets and all eligible one-, two- and three-predictor additive OLS combinations. All 57 new constructs are included.

Use the [campaign README](../analysis/regression_cross_domain_v3/README.md) for results, commands and the complete local hierarchy format, the [methodology](../analysis/regression_cross_domain_v3/methodology.md) for frozen definitions, and the [findings](../analysis/regression_cross_domain_v3/findings.md) for all three top-15 tables and limitations.

The primary leaderboard requires disjoint recorded measurement provenance. Every conclusion remains exploratory and retrospective. Prior datasets, code and analyses are preserved; large numerical stores stay under ignored `data/experiments/regression_cross_domain_v3/`. Existing root navigation files retain their frozen paths and hashes.
''')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['report','query'],nargs='?',default='report');p.add_argument('--target');p.add_argument('--view',choices=list(spec.VIEWS),default=PRIMARY);p.add_argument('--configuration',choices=spec.CONFIG['configurations'],default='combined');p.add_argument('--count',type=int,choices=[1,2,3]);p.add_argument('--limit',type=int,default=20,help='0 exports every eligible row');p.add_argument('--output');args=p.parse_args()
    if args.action=='report':report()
    else:
        if args.target not in spec.targets():p.error('--target must be an eligible inventory name')
        if args.limit<0:p.error('--limit must be nonnegative')
        query(args.target,args.view,args.configuration,args.count,args.limit,args.output)
