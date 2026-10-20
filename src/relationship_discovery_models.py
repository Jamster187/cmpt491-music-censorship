"""Small real model families, nested time splits and fixed-model block evidence."""
from __future__ import annotations
import time
import numpy as np
import pandas as pd
from scipy import linalg,stats
from sklearn.preprocessing import SplineTransformer,StandardScaler
from sklearn.tree import DecisionTreeRegressor
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score,silhouette_score

import regression_core as core
import relationship_discovery_spec as spec
import relationship_discovery_stats as inference


def least_squares(x,y):
    return linalg.lstsq(x,y,cond=np.finfo(float).eps*max(x.shape),lapack_driver='gelsd')[0]


def make_splits(frame):
    raw=frame[['song_id','first_iso','last_iso']].rename(columns={'first_iso':'first_chart_date','last_iso':'last_chart_date'})
    ranges=set(spec.OUTER)
    for start,_ in spec.OUTER:ranges.update([(start-10,start-5),(start-5,start)])
    return {(a,b):tuple(v.to_numpy() for v in core.partition(raw,f'{a}-01-01',f'{b}-01-01')) for a,b in sorted(ranges)}


def partitions(frame,masks,period,target):
    tr,va=masks[period];observed=frame[target].notna().to_numpy()
    return frame.loc[tr & observed],frame.loc[va & observed]


class Univariate:
    def __init__(self,predictor,method):self.predictor=predictor;self.method=method
    def values(self,frame):
        x=frame[self.predictor].to_numpy(float);missing=~np.isfinite(x)
        return (np.where(missing,self.median,x)-self.mean)/self.scale,missing.astype(float)
    def design(self,frame):
        x,m=self.values(frame)
        if self.method=='linear':terms=x[:,None]
        elif self.method=='quadratic':terms=np.column_stack([x,x*x])
        elif self.method.startswith('hinge'):terms=np.column_stack([x,np.maximum(0,x-self.knot)])
        elif self.method.startswith('spline'):terms=self.spline.transform(x[:,None])
        else:return np.column_stack([x,m])
        return np.column_stack([np.ones(len(x)),terms,m])
    def fit(self,frame,target):
        x=frame[self.predictor].to_numpy(float);finite=x[np.isfinite(x)]
        self.median=float(np.median(finite)) if len(finite) else 0.
        fill=np.where(np.isfinite(x),x,self.median);self.mean=float(fill.mean());self.scale=float(fill.std()) or 1.
        z=(fill-self.mean)/self.scale
        if self.method.startswith('hinge'):
            self.knot=float(np.quantile((finite-self.mean)/self.scale,int(self.method[5:])/100)) if len(finite) else 0.
        if self.method.startswith('spline'):
            self.spline=SplineTransformer(n_knots=int(self.method[6:]),degree=3,knots='quantile',extrapolation='linear',include_bias=False)
            self.spline.fit(z[:,None])
        design=self.design(frame);y=frame[target].to_numpy(float)
        if self.method.startswith('tree'):
            self.tree=DecisionTreeRegressor(max_depth=int(self.method[4:]),min_samples_leaf=spec.MIN_GROUP_TRAIN,random_state=spec.SEED).fit(design,y)
        else:self.beta=least_squares(design,y)
        return self
    def predict(self,frame):
        design=self.design(frame)
        return self.tree.predict(design) if self.method.startswith('tree') else design@self.beta


class Interaction:
    def __init__(self,row,interact):self.row=row;self.interact=interact
    def fit(self,frame,target):
        self.x=self.row['predictors'][0];self.z=self.row['conditioner'];self.family=self.row['family']
        self.enc=core.Encoder().fit(frame,[self.x,self.z])
        xv=frame[self.x].to_numpy(float);self.xmedian=float(np.nanmedian(xv)) if np.isfinite(xv).any() else 0.
        fill=np.where(np.isfinite(xv),xv,self.xmedian);self.xmean=float(fill.mean());self.xscale=float(fill.std()) or 1.
        if self.family=='genre_interaction':
            self.supported=[g for g in spec.GENRES if len(frame.loc[frame.primary_genre.eq(g)])>=spec.MIN_GROUP_TRAIN
                and frame.loc[frame.primary_genre.eq(g),'debut_year'].nunique()>=5]
        else:
            zv=frame[self.z].to_numpy(float);self.zmedian=float(np.nanmedian(zv)) if np.isfinite(zv).any() else 0.
            filled=np.where(np.isfinite(zv),zv,self.zmedian);self.zmean=float(filled.mean());self.zscale=float(filled.std()) or 1.
            if self.family=='threshold_interaction':
                self.threshold=float(np.nanquantile(zv,self.row['quantile'])) if np.isfinite(zv).any() else 0.
                side=np.where(zv>self.threshold,'above','below')
                self.side_counts={s:int(np.sum((side==s)&np.isfinite(zv))) for s in ('above','below')}
                self.side_years={s:int(frame.loc[(side==s)&np.isfinite(zv),'debut_year'].nunique()) if 'debut_year' in frame else 5 for s in ('above','below')}
                if min(self.side_counts.values())<spec.MIN_GROUP_TRAIN or min(self.side_years.values())<5:raise ValueError('Insufficient training support on one side of threshold')
        self.beta=least_squares(self.design(frame),frame[target].to_numpy(float))
        return self
    def design(self,frame):
        base=self.enc.transform(frame)
        x=frame[self.x].to_numpy(float);valid=np.isfinite(x)
        x=(np.where(valid,x,self.xmedian)-self.xmean)/self.xscale
        if self.family=='genre_interaction':
            terms=np.column_stack([x*frame.primary_genre.eq(g).to_numpy()*valid for g in self.supported]) if self.supported else np.empty((len(frame),0))
        else:
            z=frame[self.z].to_numpy(float);valid=valid & np.isfinite(z)
            if self.family=='threshold_interaction':
                high=(z>self.threshold).astype(float)
                base=np.column_stack([base,high]) # A threshold main effect is part of the comparison baseline.
                terms=(x*high*valid)[:,None]
            else:
                z=(np.where(np.isfinite(z),z,self.zmedian)-self.zmean)/self.zscale
                terms=(x*z*valid)[:,None]
        return np.column_stack([base,terms]) if self.interact else base
    def predict(self,frame):return self.design(frame)@self.beta


def metric_bundle(y,p,baseline,median):
    y=np.asarray(y);p=np.asarray(p);baseline=np.asarray(baseline);median=np.asarray(median)
    mse=float(np.mean((y-p)**2));den=float(np.mean((y-y.mean())**2));bmse=float(np.mean((y-baseline)**2))
    return dict(r2=1-mse/den if den else None,mae=float(np.mean(abs(y-p))),rmse=float(np.sqrt(mse)),
                mse=mse,baseline_rmse=float(np.sqrt(bmse)),baseline_mae=float(np.mean(abs(y-median))),
                skill=1-mse/bmse if bmse else None)


def coverage(frame,row,pred,base,period):
    """Predeclared genre and period groups; small groups are retained as coverage failures."""
    yname=row['target'];xname=row['predictors'][0];records=[]
    for genre in spec.GENRES:
        mask=frame.primary_genre.eq(genre).to_numpy();g=frame.loc[mask]
        n=len(g);years=int(g.debut_year.nunique())
        ok=n>=spec.MIN_GROUP_EVALUATION and years>=5
        r=dict(genre=genre,period=list(period),n=n,years=years,adequate=ok)
        if ok:
            observed=g[[xname,yname]].dropna()
            r.update(spearman=inference.correlation(stats.rankdata(observed[xname]),stats.rankdata(observed[yname])) if len(observed)>=spec.MIN_GROUP_EVALUATION and observed[xname].nunique()>1 and observed[yname].nunique()>1 else None,
                mse_improvement=float(np.mean((g[yname].to_numpy()-base[mask])**2-(g[yname].to_numpy()-pred[mask])**2)))
        records.append(r)
    return records


def conditional_description(train,test,row,model):
    x=row['predictors'][0];y=row['target'];z=row['conditioner']
    f=test.dropna(subset=[x,y,z]);result={'n_complete':len(f),'subgroups':[],
        'warning':'Descriptive conditional correlations and sign flags; no separate subgroup significance claim or post-hoc subgroup selection'}
    if len(f)<spec.MIN_GROUP_EVALUATION:return result
    if f[x].nunique()<2 or f[y].nunique()<2:return dict(result,status='insufficient_variation')
    a=stats.rankdata(f[x]);b=stats.rankdata(f[y]);result['marginal_spearman']=inference.correlation(a,b)
    if row['family']=='genre_interaction':
        labels=f[z].to_numpy()
        design=np.column_stack([np.ones(len(f))]+[f[z].eq(g).to_numpy(float) for g in spec.GENRES[1:]])
        groups=[(g,labels==g) for g in spec.GENRES]
    else:
        control=stats.rankdata(f[z]);design=np.column_stack([np.ones(len(f)),control])
        if row['family']=='threshold_interaction':
            groups=[('at_or_below_training_threshold',f[z].to_numpy()<=model.threshold),('above_training_threshold',f[z].to_numpy()>model.threshold)]
            result['training_threshold']=model.threshold
        else:
            edges=np.unique(np.nanquantile(train[z],[.25,.5,.75]));code=np.searchsorted(edges,f[z],side='right')
            groups=[('training_quantile_bin_'+str(i+1),code==i) for i in range(len(edges)+1)]
            result['training_quantile_edges']=edges.tolist()
    pa=a-design@least_squares(design,a);pb=b-design@least_squares(design,b)
    result['partial_spearman']=inference.correlation(pa,pb) if np.ptp(pa)>1e-12 and np.ptp(pb)>1e-12 else None
    result['aggregation_sign_reversal']=result['partial_spearman'] is not None and result['marginal_spearman']*result['partial_spearman']<0
    for label,take in groups:
        g=f.loc[take];ok=len(g)>=spec.MIN_GROUP_EVALUATION and g.debut_year.nunique()>=5 and g[x].nunique()>1 and g[y].nunique()>1
        item=dict(group=label,n=len(g),years=int(g.debut_year.nunique()),adequate=bool(ok))
        if ok:
            item['spearman']=inference.correlation(stats.rankdata(g[x]),stats.rankdata(g[y]))
            item['opposes_pooled_sign']=item['spearman']*result['marginal_spearman']<0
        result['subgroups'].append(item)
    return result


def predictive_analysis(frame,masks,row):
    target=row['target'];x=row['predictors'][0];family=row['family'];key=row['candidate_id']
    folds=[];all_y=[];all_p=[];all_base=[];all_mean=[];all_median=[];all_years=[];all_diff=[]
    diagnostics=[];groups=[];timings=[];total_fits=0
    for outer in spec.OUTER:
        train,test=partitions(frame,masks,outer,target)
        inputs=[*row['predictors']]+([row['conditioner']] if row['conditioner'] in spec.VARIABLES else [])
        info=dict(period=list(outer),n_train=len(train),n_test=len(test),test_years=int(test.debut_year.nunique()),
            n_train_predictor_complete=int(train[inputs].notna().all(axis=1).sum()),n_test_predictor_complete=int(test[inputs].notna().all(axis=1).sum()))
        if len(train)<spec.MIN_TRAIN or len(test)<spec.MIN_EVALUATION or train[target].var()==0:
            folds.append(dict(info,status='insufficient_coverage'));continue
        selected='interaction';inner_records=[]
        if family=='nonlinear':
            scores={m:[] for m in spec.METHODS}
            for inner in [(outer[0]-10,outer[0]-5),(outer[0]-5,outer[0])]:
                tr,va=partitions(frame,masks,inner,target)
                if len(tr)<spec.MIN_TRAIN or len(va)<spec.MIN_EVALUATION:continue
                mean=float(tr[target].mean());den=float(np.mean((va[target]-mean)**2))
                for method in spec.METHODS:
                    started=time.perf_counter()
                    try:
                        model=Univariate(x,method).fit(tr,target);prediction=model.predict(va)
                        score=1-float(np.mean((va[target]-prediction)**2))/den if den else -np.inf
                    except (ValueError,np.linalg.LinAlgError):score=-np.inf
                    elapsed=time.perf_counter()-started;total_fits+=1
                    timings.append(dict(method=method,n_train=len(tr),seconds=elapsed,phase='inner'))
                    scores[method].append(score)
            valid={m:float(np.mean(v)) for m,v in scores.items() if len(v)==2 and np.isfinite(v).all()}
            if not valid:folds.append(dict(info,status='insufficient_inner_coverage'));continue
            selected=min(valid,key=lambda m:(-valid[m],spec.METHODS.index(m)))
            inner_records=[dict(method=m,mean_skill=v) for m,v in valid.items()]
            started=time.perf_counter();baseline_model=Univariate(x,'linear').fit(train,target)
            baseline=baseline_model.predict(test);total_fits+=1
            timings.append(dict(method='linear',n_train=len(train),seconds=time.perf_counter()-started,phase='outer'))
            if selected=='linear':model=baseline_model;pred=baseline
            else:
                started=time.perf_counter();model=Univariate(x,selected).fit(train,target);pred=model.predict(test);total_fits+=1
                timings.append(dict(method=selected,n_train=len(train),seconds=time.perf_counter()-started,phase='outer'))
            observed=train[x].dropna()
            grid=np.linspace(float(observed.quantile(.01)),float(observed.quantile(.99)),100) if len(observed) else np.zeros(100)
            inputs=pd.DataFrame({x:grid})
            diagnostics.append(dict(period=list(outer),selected_method=selected,x=grid.tolist(),linear=baseline_model.predict(inputs).tolist(),nonlinear=model.predict(inputs).tolist(),
                training_min=float(observed.min()) if len(observed) else None,training_max=float(observed.max()) if len(observed) else None,
                extrapolation_rows=int(((test[x]<observed.min())|(test[x]>observed.max())).sum()) if len(observed) else len(test)))
        else:
            try:
                started=time.perf_counter();baseline_model=Interaction(row,False).fit(train,target);baseline=baseline_model.predict(test);total_fits+=1
                timings.append(dict(method=family+'_additive',n_train=len(train),seconds=time.perf_counter()-started,phase='outer'))
                started=time.perf_counter();model=Interaction(row,True).fit(train,target);pred=model.predict(test);total_fits+=1
                timings.append(dict(method=family,n_train=len(train),seconds=time.perf_counter()-started,phase='outer'))
            except ValueError as error:
                folds.append(dict(info,status='insufficient_subgroup_coverage',reason=str(error)));continue
            detail=dict(period=list(outer))
            if family=='genre_interaction':detail['training_supported_genres']=model.supported
            if family=='threshold_interaction':detail.update(threshold=model.threshold,training_side_counts=model.side_counts)
            detail['conditional_correlations']=conditional_description(train,test,row,model)
            diagnostics.append(detail)
        y=test[target].to_numpy(float);mean=float(train[target].mean());median=float(train[target].median());variance=float(train[target].var(ddof=0))
        metrics=metric_bundle(y,pred,np.full(len(y),mean),np.full(len(y),median))
        base_metrics=metric_bundle(y,baseline,np.full(len(y),mean),np.full(len(y),median))
        delta=(y-baseline)**2-(y-pred)**2
        folds.append(dict(info,status='ok',selected_method=selected,inner_models=inner_records,metrics=metrics,
            comparison_metrics=base_metrics,mse_improvement=float(delta.mean()),relative_mse_improvement=float(delta.mean()/np.mean((y-baseline)**2)) if np.mean((y-baseline)**2)>0 else 0.))
        groups.extend(coverage(test,row,pred,baseline,outer))
        all_y.extend(y);all_p.extend(pred);all_base.extend(baseline);all_mean.extend([mean]*len(y));all_median.extend([median]*len(y))
        all_years.extend(test.debut_year.to_numpy(int));all_diff.extend(delta/variance)
    result=dict(row,status='ok' if all_y else 'insufficient_coverage',n=len(all_y),folds=folds,diagnostics=diagnostics,
        subgroup_results=groups,fit_count=total_fits,timings=timings,p_value=None,
        comparison='linear x-only' if family=='nonlinear' else 'additive same-input model (threshold includes threshold main effect)',
        family_tags=['D: nonlinear' if family=='nonlinear' else 'D: conditional','E: chronological evaluation'],
        leakage_warning='Retrospective frozen enrichment; whole chart windows purged. Not an as-of forecast or independent confirmation.')
    if all_y:
        y=np.array(all_y);pred=np.array(all_p);base=np.array(all_base)
        result.update(metric_bundle(y,pred,all_mean,all_median))
        result['comparison_metrics']=metric_bundle(y,base,all_mean,all_median)
        result['relative_mse_improvement']=float(1-np.mean((y-pred)**2)/np.mean((y-base)**2)) if np.mean((y-base)**2)>0 else 0.
        result.update(inference.paired_evidence(all_diff,np.array(all_years),key))
        valid=[f for f in folds if f['status']=='ok']
        result['evaluated_periods']=len(valid);result['stability_fraction']=float(np.mean([f['mse_improvement']>0 for f in valid]))
        result['worst_period_relative_improvement']=float(min(f['relative_mse_improvement'] for f in valid))
        result['mean_period_relative_improvement']=float(np.mean([f['relative_mse_improvement'] for f in valid]))
        result['unstable']=result['stability_fraction']<.75 or result.get('ci_low') is None or result.get('ci_low',0)<=0
    return result


def annual_correlations(frame,x,y,adjust_genre=False):
    rows=[]
    for year,g in frame.dropna(subset=[x,y]).groupby('debut_year'):
        if len(g)<spec.MIN_YEAR or g[x].nunique()<2 or g[y].nunique()<2:continue
        a=stats.rankdata(g[x]);b=stats.rankdata(g[y])
        if adjust_genre:
            # Within-year partial rank association; controls group intercepts, not all confounding.
            groups=g.primary_genre.fillna('__missing__').to_numpy()
            for group in np.unique(groups):
                take=groups==group;a[take]-=a[take].mean();b[take]-=b[take].mean()
        if np.ptp(a)==0 or np.ptp(b)==0:continue
        rows.append(dict(year=int(year),rho=inference.correlation(a,b),n=len(g)))
    return rows


def temporal_analysis(frame,row):
    x=row['predictors'][0];y=row['target'];records=[];annual=[];rolling=[];conditional=[]
    for genre in [None]+spec.GENRES:
        f=frame if genre is None else frame.loc[frame.primary_genre.eq(genre)]
        f=f.dropna(subset=[x,y]);label='All genres' if genre is None else genre
        ann=annual_correlations(f,x,y);annual.extend([dict(r,genre=label) for r in ann])
        adjusted=annual_correlations(f,x,y,True) if genre is None else []
        for a,b in spec.PERIODS:
            g=f.loc[f.debut_year.ge(a)&f.debut_year.lt(b)]
            ok=len(g)>=spec.MIN_GROUP_EVALUATION and g.debut_year.nunique()>=5 and g[x].nunique()>1 and g[y].nunique()>1
            conditional.append(dict(genre=label,period=[a,b],n=len(g),years=int(g.debut_year.nunique()),adequate=bool(ok),
                rho=inference.correlation(stats.rankdata(g[x]),stats.rankdata(g[y])) if ok else None))
        for start in spec.ROLLING_STARTS:
            g=f.loc[f.debut_year.ge(start)&f.debut_year.lt(start+10)]
            ok=len(g)>=spec.MIN_GROUP_EVALUATION and g.debut_year.nunique()>=5 and g[x].nunique()>1 and g[y].nunique()>1
            rolling.append(dict(genre=label,start=start,end=start+10,n=len(g),adequate=bool(ok),
                rho=inference.correlation(stats.rankdata(g[x]),stats.rankdata(g[y])) if ok else None))
        for cutoff in spec.BREAKPOINTS:
            before=[r for r in ann if cutoff-5<=r['year']<cutoff];after=[r for r in ann if cutoff<=r['year']<cutoff+5]
            adequate=len(before)==len(after)==5 and sum(r['n'] for r in before)>=200 and sum(r['n'] for r in after)>=200
            result=dict(genre=label,breakpoint=cutoff,n_before=sum(r['n'] for r in before),n_after=sum(r['n'] for r in after),
                annual_points_before=len(before),annual_points_after=len(after),adequate=adequate,p_value=None,
                reliability_warning='Five annual points per side: descriptive block interval only; insufficient independent blocks for confirmation. All five breakpoints tested descriptively.')
            if adequate:
                z0=np.arctanh(np.clip([r['rho'] for r in before],-.999999,.999999));z1=np.arctanh(np.clip([r['rho'] for r in after],-.999999,.999999))
                rng=inference.rng_for(row['candidate_id'],label+str(cutoff));draws=[]
                # Moving length-two blocks within each five-year side, including endpoint block.
                blocks0=[z0[i:i+2] for i in range(4)];blocks1=[z1[i:i+2] for i in range(4)]
                for _ in range(spec.BOOTSTRAPS):
                    a=np.concatenate([blocks0[i] for i in rng.integers(4,size=3)])[:5]
                    b=np.concatenate([blocks1[i] for i in rng.integers(4,size=3)])[:5]
                    draws.append(float(b.mean()-a.mean()))
                result.update(effect=float(z1.mean()-z0.mean()),effect_name='change in mean annual Fisher-z Spearman association',
                    rho_before=float(np.mean([r['rho'] for r in before])),rho_after=float(np.mean([r['rho'] for r in after])),
                    ci_low=float(np.quantile(draws,.025)),ci_high=float(np.quantile(draws,.975)))
                if genre is None:
                    a0=[r for r in adjusted if cutoff-5<=r['year']<cutoff];a1=[r for r in adjusted if cutoff<=r['year']<cutoff+5]
                    if len(a0)==len(a1)==5:
                        result['genre_adjusted_change']=float(np.mean(np.arctanh(np.clip([r['rho'] for r in a1],-.999999,.999999)))-np.mean(np.arctanh(np.clip([r['rho'] for r in a0],-.999999,.999999))))
            records.append(result)
    eligible=[r for r in records if r['adequate']]
    return dict(row,status='ok',n=len(frame.dropna(subset=[x,y])),annual=annual,rolling=rolling,breakpoints=records,
        conditional_correlations=conditional,p_value=None,effect=max([abs(r['effect']) for r in eligible],default=0.),
        effect_name='maximum absolute prespecified breakpoint contrast; descriptive selection among all logged comparisons',
        family_tags=['E: historical/genre-specific'],adequate_breakpoint_comparisons=len(eligible),
        missingness_by_period=[dict(period=[a,b],total=int(((frame.debut_year>=a)&(frame.debut_year<b)).sum()),
            observed=int(((frame.debut_year>=a)&(frame.debut_year<b)&frame[x].notna()&frame[y].notna()).sum())) for a,b in spec.PERIODS])


def structure_analysis(frame,masks,row):
    columns=row['predictors'];folds=[];timings=[];key=row['candidate_id'];fit_count=0
    for period in spec.OUTER:
        trmask,vamask=masks[period]
        # Complete panel rows: avoids interpreting imputation as a new lyrical profile.
        observed=frame[columns].notna().all(axis=1).to_numpy()
        train=frame.loc[trmask & observed];test=frame.loc[vamask & observed]
        if len(train)<spec.MIN_TRAIN or len(test)<spec.MIN_EVALUATION:continue
        started=time.perf_counter();scaler=StandardScaler().fit(train[columns]);x=scaler.transform(train[columns]);v=scaler.transform(test[columns])
        if row['method']=='pca':
            model=PCA(n_components=row['k'],svd_solver='full').fit(x)
            scores=model.transform(v);reconstructed=model.inverse_transform(scores)
            effect=float(1-np.sum((v-reconstructed)**2)/np.sum(v*v))
            details=dict(explained_training_variance=float(model.explained_variance_ratio_.sum()),
                heldout_reconstruction_fraction=effect,loadings=model.components_.tolist(),
                genre_profiles=[dict(genre=g,n=int(test.primary_genre.eq(g).sum()),
                    pc_means=scores[test.primary_genre.eq(g)].mean(axis=0).tolist()) for g in spec.GENRES if test.primary_genre.eq(g).sum()>=spec.MIN_GROUP_EVALUATION])
        else:
            model=KMeans(n_clusters=row['k'],n_init=10,random_state=spec.SEED,algorithm='lloyd').fit(x)
            labels=model.predict(v);dist=model.transform(v).min(axis=1)**2
            effect=float(1-dist.mean()/np.mean(np.sum(v*v,axis=1)))
            picked=np.argsort(test._hash.to_numpy(),kind='stable')[:1500]
            silhouette=float(silhouette_score(v[picked],labels[picked])) if len(np.unique(labels[picked]))>1 else None
            details=dict(heldout_distortion_reduction=effect,silhouette=silhouette,silhouette_n=len(picked),centers_standardized=model.cluster_centers_.tolist(),
                cluster_profiles=[dict(cluster=int(c),n=int(np.sum(labels==c)),
                    genre_counts=test.loc[labels==c,'primary_genre'].value_counts().to_dict(),
                    median_debut_year=float(test.loc[labels==c,'debut_year'].median())) for c in np.unique(labels)])
        fit_count+=1;timings.append(dict(method=row['method'],n_train=len(train),seconds=time.perf_counter()-started))
        blocks=[np.flatnonzero(train.debut_year.to_numpy()//2==b) for b in sorted(set(train.debut_year.to_numpy()//2))]
        rng=inference.rng_for(key,str(period));stability=[]
        for _ in range(3):
            picked=np.concatenate([blocks[i] for i in rng.integers(len(blocks),size=len(blocks))]);sample=train.iloc[picked]
            sc=StandardScaler().fit(sample[columns]);sx=sc.transform(sample[columns]);sv=sc.transform(test[columns]);started=time.perf_counter()
            if row['method']=='pca':
                other=PCA(n_components=row['k'],svd_solver='full').fit(sx)
                stability.append(float(np.cos(linalg.subspace_angles(model.components_.T,other.components_.T)).min()))
            else:
                other=KMeans(n_clusters=row['k'],n_init=10,random_state=spec.SEED,algorithm='lloyd').fit(sx)
                stability.append(float(adjusted_rand_score(labels,other.predict(sv))))
            fit_count+=1;timings.append(dict(method=row['method']+'_stability',n_train=len(sample),seconds=time.perf_counter()-started))
        folds.append(dict(period=list(period),n_train=len(train),n_test=len(test),effect=effect,
            stability_values=stability,minimum_stability=min(stability),**details))
    return dict(row,status='ok' if folds else 'insufficient_coverage',n=sum(f['n_test'] for f in folds),folds=folds,
        effect=float(np.mean([f['effect'] for f in folds])) if folds else None,
        effect_name='heldout standardized reconstruction fraction' if row['method']=='pca' else 'heldout standardized distortion reduction',
        stability_fraction=float(np.mean([f['minimum_stability'] for f in folds])) if folds else None,
        stability_metric='minimum principal-angle cosine' if row['method']=='pca' else 'adjusted Rand index',
        fit_count=fit_count,timings=timings,p_value=None,family_tags=['E: multivariate structure'],
        uncertainty_warning='Three two-year-block stability refits per fold are diagnostic, not a confidence interval. Latent components are data-fitted; no hand-weighted composite score. Standardization and genre composition can change over time.')
