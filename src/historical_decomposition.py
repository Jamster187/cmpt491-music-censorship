"""Bounded, reproducible historical accounting of the existing monthly population."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import platform
import resource
import subprocess
import time

import numpy as np
import pandas as pd
import scipy
from scipy import sparse, stats
from threadpoolctl import threadpool_limits

import moving_average_analysis as moving
import descriptive_analysis as descriptive

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'analysis/historical_decomposition'
LOCAL=ROOT/'data/experiments/historical_decomposition_v2'
FEATURES=list(moving.FEATURES)
PRIMARY=['ll_explicit_language','ll_violence','ll_sexual_content','ll_substance_use',
         'detox_toxicity','sentiment_positive','sentiment_negative','emotion_joy',
         'emotion_love','emotion_sadness','emotion_anger']
PERIODS={str(y)+'s':(y,y+9) for y in range(1960,2020,10)}
PERIODS.update({'2020–2025':(2020,2025),'2015–2024':(2015,2024)})
COMPARISONS=[(str(y)+'s',str(y+10)+'s') for y in range(1960,2010,10)]+[
    ('2010s','2020–2025'),('1990s','2015–2024')]
BREAKS=list(range(1970,2021,5))
WEIGHTINGS=['song_month','rank_weighted','unique_song']
BOOTSTRAPS=9999
SENSITIVITY_BOOTSTRAPS=499
BLOCK=24
HYPOTHESES=7*11*3+11*11*2*2
CLAIMS={'detox_toxicity':74.,'ll_sexual_content':69.,'ll_explicit_language':65.,
        'll_substance_use':61.,'ll_violence':46.}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


def rng_for(key):
    return np.random.default_rng(int(digest(['historical-v1',key])[:16],16))


def write_json(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    def clean(v):
        if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
        if isinstance(v,(list,tuple)):return [clean(x) for x in v]
        if isinstance(v,np.ndarray):return clean(v.tolist())
        if isinstance(v,np.generic):return clean(v.item())
        if isinstance(v,float) and not np.isfinite(v):return None
        return v
    temp=Path(str(path)+'.tmp');temp.write_text(json.dumps(clean(value),indent=2,sort_keys=True,allow_nan=False)+'\n');temp.replace(path)


def write_csv(name,records):
    frame=records if isinstance(records,pd.DataFrame) else pd.DataFrame(records)
    path=PUBLIC/name;temp=Path(str(path)+'.tmp')
    compression=dict(method='gzip',mtime=0) if name.endswith('.gz') else None
    frame.to_csv(temp,index=False,lineterminator='\n',float_format='%.17g',compression=compression);temp.replace(path)


def preserve():
    record=json.loads((LOCAL/'preservation.json').read_text())
    for name,expected in record['sha256'].items():
        if descriptive.sha(ROOT/name)!=expected:raise ValueError('Protected input/prior artifact changed: '+name)
    return dict(status='PASS',files=len(record['sha256']),baseline_commit=record['baseline_commit'])


def load_data():
    raw=pd.read_csv(moving.INPUT,dtype={'song_id':str},keep_default_na=False,na_values=[''])
    data,calendar,duplicates=moving.prepare(raw)
    metadata=raw[['song_id','artist','genre_confidence','lyrics_available']].drop_duplicates('song_id')
    data=data.merge(metadata,on='song_id',validate='many_to_one')
    data['year']=data.month.str[:4].astype(int)
    data['month_index']=data.year*12+data.month.str[5:7].astype(int)-1
    data=data[data.year.between(1960,2025)].sort_values(['month','song_id']).reset_index(drop=True)
    if data.duplicated(['month','song_id']).any():raise ValueError('Duplicate analysis song-month')
    if data.month.nunique()!=66*12:raise ValueError('Incomplete fixed analysis calendar')
    genres=sorted(raw.primary_genre.unique())
    if len(genres)!=16:raise ValueError('Original genre taxonomy changed')
    return data,genres,duplicates


def period_frame(data,period,weighting='song_month'):
    a,b=PERIODS[period];f=data[data.year.between(a,b)].copy()
    if weighting=='unique_song':f=f.drop_duplicates('song_id')
    f['weight']=f.rank_weight if weighting=='rank_weighted' else 1.
    return f


def cell_summary(frame,features,genres):
    """Score-specific available populations; keep every original genre."""
    y=frame[features].to_numpy(float);valid=np.isfinite(y);w=frame.weight.to_numpy(float)
    gc=pd.Categorical(frame.primary_genre,categories=genres).codes
    count=np.zeros((len(genres),len(features)));numerator=np.zeros_like(count)
    total=np.bincount(gc,weights=w,minlength=len(genres))
    unique=np.zeros_like(count,dtype=int)
    total_unique=np.zeros(len(genres),dtype=int)
    for g in range(len(genres)):
        mask=gc==g
        count[g]=(valid[mask]*w[mask,None]).sum(axis=0)
        numerator[g]=(np.where(valid[mask],y[mask],0)*w[mask,None]).sum(axis=0)
        total_unique[g]=frame.loc[mask,'song_id'].nunique()
        songs=frame.loc[mask].drop_duplicates('song_id')
        unique[g]=songs[features].notna().sum().to_numpy()
    mean=np.divide(numerator,count,out=np.full_like(count,np.nan),where=count>0)
    shares=count/count.sum(axis=0)
    return dict(mean=mean,share=shares,scored_weight=count,total_weight=total,
                unique_scored=unique,unique_total=total_unique,
                observed_mean=numerator.sum(axis=0)/count.sum(axis=0),
                coverage=count.sum(axis=0)/total.sum(),n_songs=frame.song_id.nunique(),
                n_rows=len(frame),n_months=frame.month.nunique(),
                n_artists=frame.artist.nunique())


def kitagawa(p0,mu0,p1,mu1):
    """Arrays end in (genre, score); zero-share undefined means use entry/exit rule."""
    p0,mu0,p1,mu1=[np.asarray(x,dtype=float) for x in (p0,mu0,p1,mu1)]
    if np.any((p0>0)&~np.isfinite(mu0)) or np.any((p1>0)&~np.isfinite(mu1)):
        raise ValueError('A positive-share observed cell cannot have an unavailable mean')
    a=mu0.copy();b=mu1.copy()
    a=np.where((p0==0)&(p1>0),b,a);b=np.where((p1==0)&(p0>0),a,b)
    a=np.where((p0==0)&(p1==0),0,a);b=np.where((p0==0)&(p1==0),0,b)
    within=(p0+p1)/2*(b-a);composition=(a+b)/2*(p1-p0)
    m0=np.sum(p0*a,axis=-2);m1=np.sum(p1*b,axis=-2);delta=m1-m0
    np.testing.assert_allclose(within.sum(axis=-2)+composition.sum(axis=-2),delta,atol=2e-12,rtol=2e-12)
    # Bound the allocation caused only by unobserved counterperiod means.
    lo=within.copy();hi=within.copy()
    entry=(p0==0)&(p1>0);exit_=(p1==0)&(p0>0)
    lo=np.where(entry,p1/2*(b-1),lo);hi=np.where(entry,p1/2*b,hi)
    lo=np.where(exit_,-p0/2*a,lo);hi=np.where(exit_,p0/2*(1-a),hi)
    return dict(mean0=m0,mean1=m1,delta=delta,within=within,composition=composition,
                entry_exit=entry|exit_,within_allocation_low=lo.sum(axis=-2),
                within_allocation_high=hi.sum(axis=-2))


def comparison_id(a,b):return a+'_vs_'+b


def multiplier_batches(artists,months,repeats,key,block=BLOCK,mode='crossed',batch=32):
    """Positive crossed artist / random-origin contiguous-calendar multipliers."""
    _,ac=np.unique(np.asarray(artists,str),return_inverse=True)
    t=np.asarray(months,int);t=t-t.min();rng=rng_for([key,block,mode,repeats])
    done=0
    while done<repeats:
        size=min(batch,repeats-done)
        aw=rng.exponential(size=(size,int(ac.max())+1))[:,ac] if mode!='calendar_only' else np.ones((size,len(t)))
        if mode!='artist_only':
            offset=rng.integers(block,size=size)
            codes=(t[None,:]+offset[:,None])//block
            tw=rng.exponential(size=(size,int(codes.max())+1))
            aw*=np.take_along_axis(tw,codes,axis=1)
        yield aw
        done+=size


def uncertainty(point,draws):
    values=np.asarray(draws,float);point=np.asarray(point,float)
    if not np.isfinite(values).all():raise ValueError('Non-finite bootstrap result')
    errors=values-point
    return dict(low=np.quantile(values,.025,axis=0),high=np.quantile(values,.975,axis=0),
                p=(1+(np.abs(errors)>=np.abs(point)).sum(axis=0))/(len(values)+1),
                se=values.std(axis=0,ddof=1))


def decomposition_bootstrap(data,genres,a,b,features=PRIMARY,repeats=BOOTSTRAPS,block=BLOCK,mode='crossed'):
    left=period_frame(data,a);right=period_frame(data,b)
    f=pd.concat([left.assign(_period=0),right.assign(_period=1)],ignore_index=True)
    p=f._period.to_numpy();gc=pd.Categorical(f.primary_genre,categories=genres).codes
    y=f[features].to_numpy(float);valid=np.isfinite(y);n,F=y.shape;G=len(genres)
    # Sparse sufficient statistics retain separate score-specific denominators.
    columns=(p[:,None]*G+gc[:,None])*F+np.arange(F)[None,:]
    ix=np.repeat(np.arange(n),F)
    matrix=sparse.csr_matrix((np.r_[np.where(valid,y,0).ravel(),valid.astype(float).ravel()],
        (np.r_[ix,ix],np.r_[columns.ravel(),columns.ravel()+2*G*F])),shape=(n,4*G*F))
    matrix.eliminate_zeros();out=[]
    for weights in multiplier_batches(f.artist,f.month_index,repeats,comparison_id(a,b),block,mode):
        values=np.asarray(weights@matrix)
        sums=values[:,:2*G*F].reshape(-1,2,G,F);counts=values[:,2*G*F:].reshape(-1,2,G,F)
        means=np.divide(sums,counts,out=np.full_like(sums,np.nan),where=counts>0)
        shares=counts/counts.sum(axis=2,keepdims=True)
        d=kitagawa(shares[:,0],means[:,0],shares[:,1],means[:,1])
        out.append(np.stack([d['delta'],d['within'].sum(axis=1),d['composition'].sum(axis=1)],axis=-1))
    return np.concatenate(out)


def cached_bootstrap(name,identity,calculate):
    path=LOCAL/(name+'.npz');key=digest(identity)
    if path.exists():
        with np.load(path,allow_pickle=False) as saved:
            if str(saved['identity'])!=key:raise ValueError('Refuse stale diagnostic cache: '+name)
            return saved['draws'].copy(),True
    draws=calculate();temp=LOCAL/(name+'.tmp.npz')
    np.savez_compressed(temp,identity=key,draws=draws);temp.replace(path)
    return draws,False


def design(frame,break_month,adjusted=False,quadratic=False):
    t=(frame.month_index.to_numpy()-break_month)/12
    post=(t>=0).astype(float)
    columns=[np.ones(len(t)),t,post,t*post]
    names=['intercept','time_years','level','slope']
    if quadratic:columns.append(t*t);names.append('quadratic_time')
    months=frame.month_index.to_numpy()%12
    for k in range(1,12):columns.append((months==k).astype(float));names.append('month_'+str(k+1))
    if adjusted:
        for g in sorted(frame.primary_genre.unique())[1:]:
            columns.append(frame.primary_genre.eq(g).to_numpy(float));names.append('genre::'+g)
    x=np.column_stack(columns)
    if np.linalg.matrix_rank(x)!=x.shape[1]:raise ValueError('Rank-deficient breakpoint design')
    return x,names


def weighted_fit(x,y,w):
    a=x.T@(w[:,None]*x);b=x.T@(w[:,None]*y)
    return np.linalg.solve(a,b)


def hac_intervals(x,y,w,beta,months,lags=24):
    """Bartlett HAC of monthly sums of coefficient influence contributions."""
    bread=np.linalg.inv(x.T@(w[:,None]*x))
    influence=(w[:,None]*(x@bread[:,[2,3]]))[:,:,None]*(y-x@beta)[:,None,:]
    month=np.asarray(months,int)-min(months);T=int(month.max()+1)
    grouped=np.zeros((T,2,y.shape[1]));np.add.at(grouped,month,influence)
    variance=np.sum(grouped**2,axis=0)
    for lag in range(1,min(lags,T-1)+1):
        variance+=2*(1-lag/(lags+1))*np.sum(grouped[lag:]*grouped[:-lag],axis=0)
    variance*=T/(T-x.shape[1]);se=np.sqrt(np.maximum(variance,0))
    values=beta[[2,3]];critical=stats.norm.ppf(.975)
    return dict(low=values-critical*se,high=values+critical*se,se=se,
                residual_lag1=[np.corrcoef(grouped[1:,0,j],grouped[:-1,0,j])[0,1] for j in range(y.shape[1])])


def breakpoint_group(frame,features,year,adjusted=False,weighting='song_month',break_offset=0,
                     quadratic=False,repeats=BOOTSTRAPS,block=BLOCK,mode='crossed',do_bootstrap=True):
    if frame[features].isna().any().any():raise ValueError('Pass a common, score-specific complete mask')
    x,names=design(frame,year*12+break_offset,adjusted,quadratic)
    y=frame[features].to_numpy(float)
    base=frame.rank_weight.to_numpy(float) if weighting=='rank_weighted' else np.ones(len(frame))
    month=frame.month_index.to_numpy();totals=pd.Series(base).groupby(month).transform('sum').to_numpy()
    w=base/totals;beta=weighted_fit(x,y,w)
    reference=np.linalg.lstsq(x*np.sqrt(w[:,None]),y*np.sqrt(w[:,None]),rcond=None)[0]
    np.testing.assert_allclose(beta,reference,atol=2e-10,rtol=1e-8)
    fitted=x@beta;residual=y-fitted
    result=dict(beta=beta[[2,3]].T,hac=hac_intervals(x,y,w,beta,month),
        r2=1-np.sum(w[:,None]*residual**2,axis=0)/np.sum(w[:,None]*(y-np.average(y,weights=w,axis=0))**2,axis=0),
        n_rows=len(frame),n_songs=frame.song_id.nunique(),n_artists=frame.artist.nunique(),
        n_months=frame.month.nunique(),parameters=x.shape[1],condition=float(np.linalg.cond(x.T@(w[:,None]*x))),
        all_beta=beta,names=names)
    if do_bootstrap:
        draws=[];key=['breakpoint',year,adjusted,features,weighting,break_offset,quadratic]
        for weights in multiplier_batches(frame.artist,month,repeats,key,block,mode):
            draws.extend(weighted_fit(x,y,w*row)[[2,3]].T for row in weights)
        result['draws']=np.asarray(draws)
    return result


def score_groups(frame,features=PRIMARY):
    masks=defaultdict(list)
    for feature in features:masks[frame[feature].notna().to_numpy().tobytes()].append(feature)
    for mask,group in masks.items():yield frame.loc[np.frombuffer(mask,dtype=bool)].copy(),group


def source_identity():
    identity=dict(version='historical-decomposition-v2-precision',input_sha256=descriptive.sha(moving.INPUT),
        source_sha256=descriptive.sha(Path(__file__)),preparation_sha256=descriptive.sha(Path(moving.__file__)),
        descriptive_source_sha256=descriptive.sha(Path(descriptive.__file__)),
        periods=PERIODS,comparisons=COMPARISONS,features=FEATURES,primary=PRIMARY,breaks=BREAKS,
        bootstraps=BOOTSTRAPS,block_months=BLOCK,primary_hypotheses=HYPOTHESES,
        source_commit='d5a062c27ac88c15a02615e6f284cd801c19ee38',
        python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,
        preliminary_claims_provenance='User: group Milestone 2 report, Question 4; original source code unavailable; unverified')
    # JSON stores period/comparison tuples as lists. Canonicalize before comparing
    # a saved protocol so an unchanged analysis can actually resume.
    return json.loads(json.dumps(identity))


def benchmark(data,genres):
    started=time.perf_counter()
    decomposition_bootstrap(data,genres,'1990s','2015–2024',repeats=30)
    decomp=time.perf_counter()-started
    f=data[data.year.between(2014,2025)].dropna(subset=PRIMARY)
    started=time.perf_counter();breakpoint_group(f,PRIMARY,2020,True,repeats=30)
    regression=time.perf_counter()-started
    result=dict(decomposition_30_replicates_seconds=decomp,regression_30_replicates_seconds=regression,
        conservative_primary_seconds=decomp/30*BOOTSTRAPS*7+regression/30*BOOTSTRAPS*44,
        estimate_note='44 regression mask/model groups is conservative; 11 outcomes share matrix solves; sensitivities add bounded work')
    write_json(LOCAL/'benchmark.json',result);return result


def period_statistics(data,genres):
    cells={};records=[]
    for weighting in WEIGHTINGS:
        for period in PERIODS:
            f=period_frame(data,period,weighting);s=cell_summary(f,FEATURES,genres);cells[weighting,period]=s
            for gi,g in enumerate(genres):
                for j,c in enumerate(FEATURES):
                    records.append(dict(period=period,weighting=weighting,classifier=c,genre=g,
                        mean=s['mean'][gi,j],scored_share=s['share'][gi,j],
                        full_population_share=s['total_weight'][gi]/s['total_weight'].sum(),
                        scored_weight=s['scored_weight'][gi,j],total_weight=s['total_weight'][gi],
                        score_coverage=s['scored_weight'][gi,j]/s['total_weight'][gi] if s['total_weight'][gi]>0 else np.nan,
                        unique_scored_songs=s['unique_scored'][gi,j],unique_total_songs=s['unique_total'][gi],
                        sparse=s['unique_scored'][gi,j]<30))
    return cells,records


def descriptive_comparisons(cells,genres):
    totals=[];details=[]
    for a,b in COMPARISONS:
        for weighting in WEIGHTINGS:
            left=cells[weighting,a];right=cells[weighting,b]
            d=kitagawa(left['share'],left['mean'],right['share'],right['mean'])
            for j,c in enumerate(FEATURES):
                delta=d['delta'][j];within=d['within'][:,j].sum();composition=d['composition'][:,j].sum()
                base=dict(comparison=comparison_id(a,b),period0=a,period1=b,weighting=weighting,classifier=c)
                totals.append(dict(**base,mean0=d['mean0'][j],mean1=d['mean1'][j],delta=delta,
                    within=within,composition=composition,
                    within_percent=100*within/delta if abs(delta)>1e-12 else np.nan,
                    composition_percent=100*composition/delta if abs(delta)>1e-12 else np.nan,
                    coverage0=left['coverage'][j],coverage1=right['coverage'][j],
                    song_months0=left['n_rows'],song_months1=right['n_rows'],
                    unique_scored0=left['unique_scored'][:,j].sum(),unique_scored1=right['unique_scored'][:,j].sum(),
                    months0=left['n_months'],months1=right['n_months'],
                    entry_exit_genres=int(d['entry_exit'][:,j].sum()),
                    within_allocation_low=d['within_allocation_low'][j],within_allocation_high=d['within_allocation_high'][j],
                    reconciliation_error=within+composition-delta,status='ok',exploratory=True))
                for gi,g in enumerate(genres):
                    details.append(dict(**base,genre=g,mean0=left['mean'][gi,j],mean1=right['mean'][gi,j],
                        share0=left['share'][gi,j],share1=right['share'][gi,j],
                        unique_scored0=left['unique_scored'][gi,j],unique_scored1=right['unique_scored'][gi,j],
                        within=d['within'][gi,j],composition=d['composition'][gi,j],
                        total_contribution=d['within'][gi,j]+d['composition'][gi,j],
                        entry_exit_convention=bool(d['entry_exit'][gi,j]),
                        sparse=bool(min(left['unique_scored'][gi,j],right['unique_scored'][gi,j])<30)))
    return totals,details


def add_decomposition_uncertainty(data,genres,totals,identity):
    lookup={(r['comparison'],r['classifier']):r for r in totals if r['weighting']=='song_month'}
    tests=[];sensitivity=[]
    for a,b in COMPARISONS:
        key=comparison_id(a,b);start=time.perf_counter()
        draws,reused=cached_bootstrap('decomposition_'+key,[identity,a,b],
            lambda:decomposition_bootstrap(data,genres,a,b))
        points=np.array([[lookup[key,c][term] for term in ['delta','within','composition']] for c in PRIMARY])
        u=uncertainty(points,draws)
        for j,c in enumerate(PRIMARY):
            row=lookup[key,c]
            for k,term in enumerate(['delta','within','composition']):
                for name in ['low','high','p','se']:row[term+'_'+name]=float(u[name][j,k])
                tests.append(dict(test_id='decomposition:'+key+':'+c+':'+term,
                    family='decomposition',comparison=key,classifier=c,term=term,p_value=float(u['p'][j,k])))
            row['percentage_unstable']=bool(row['delta_low']<=0<=row['delta_high'])
            ratio=100*draws[:,j,1]/draws[:,j,0]
            row['within_percent_low'],row['within_percent_high']=np.quantile(ratio,[.025,.975])
        print(json.dumps(dict(stage='decomposition_uncertainty',comparison=key,reused=reused,seconds=time.perf_counter()-start)),flush=True)
        if (a,b) in [COMPARISONS[-1],COMPARISONS[-2]]:
            for block,mode in [(12,'crossed'),(36,'crossed'),(24,'artist_only'),(24,'calendar_only')]:
                name=key+'_'+str(block)+'_'+mode
                extra,_=cached_bootstrap('sensitivity_'+name,[identity,name,SENSITIVITY_BOOTSTRAPS],
                    lambda:decomposition_bootstrap(data,genres,a,b,repeats=SENSITIVITY_BOOTSTRAPS,block=block,mode=mode))
                eu=uncertainty(points,extra)
                for j,c in enumerate(PRIMARY):
                    for k,term in enumerate(['delta','within','composition']):
                        sensitivity.append(dict(analysis='decomposition_uncertainty',comparison=key,classifier=c,
                            scenario=mode+'_'+str(block)+'months',term=term,estimate=points[j,k],
                            low=eu['low'][j,k],high=eu['high'][j,k],descriptive_only=True))
    return tests,sensitivity


def missing_scenario(summary,shift):
    """Expected missing-score scenario; never alters a stored song score."""
    mu=summary['mean'].copy();den=summary['scored_weight'];total=summary['total_weight'][:,None]
    unknown=(den==0)&(total>0)
    expected=np.where(np.isfinite(mu),mu,summary['observed_mean'][None,:])
    expected=np.clip(expected+shift,0,1)
    numerator=np.where(np.isfinite(mu),mu,0)*den+expected*(total-den)
    full_mean=np.divide(numerator,total,out=np.full_like(numerator,np.nan),where=total>0)
    shares=np.broadcast_to(total/total.sum(),mu.shape)
    fallback=((total-den)*unknown).sum(axis=0)/total.sum()
    return shares,full_mean,fallback


def sensitivities(data,genres,cells):
    records=[]
    six=data.primary_genre.value_counts().head(6).index.tolist()
    for a,b in COMPARISONS:
        key=comparison_id(a,b);left=cells['song_month',a];right=cells['song_month',b]
        for scenario,delta0,delta1 in [('mar_genre_period',0,0),('missing_minus_0.10',-.1,-.1),
            ('missing_plus_0.10',.1,.1),('missing_older_high_recent_low',.1,-.1),('missing_older_low_recent_high',-.1,.1)]:
            p0,m0,f0=missing_scenario(left,delta0);p1,m1,f1=missing_scenario(right,delta1)
            d=kitagawa(p0,m0,p1,m1)
            for j,c in enumerate(FEATURES):
                w=d['within'][:,j].sum();change=d['delta'][j]
                records.append(dict(analysis='missingness',comparison=key,classifier=c,scenario=scenario,
                    mean0=d['mean0'][j],mean1=d['mean1'][j],delta=change,within=w,
                    composition=d['composition'][:,j].sum(),within_percent=100*w/change if abs(change)>1e-12 else np.nan,
                    fallback_weight0=f0[j],fallback_weight1=f1[j],assumption='Expected missing scores only; observed scores unchanged',descriptive_only=True))
        for j,c in enumerate(FEATURES):
            lo0=left['coverage'][j]*left['observed_mean'][j];hi0=lo0+1-left['coverage'][j]
            lo1=right['coverage'][j]*right['observed_mean'][j];hi1=lo1+1-right['coverage'][j]
            records.append(dict(analysis='missingness',comparison=key,classifier=c,scenario='unrestricted_0_1_bounds',
                mean0_low=lo0,mean0_high=hi0,mean1_low=lo1,mean1_high=hi1,delta_low=lo1-hi0,delta_high=hi1-lo0,
                assumption='Bounds only; no zero imputation',descriptive_only=True))
        for scenario,filter_ in [('genre_high',data.genre_confidence.eq('high')),
                                ('genre_not_low',data.genre_confidence.ne('low')),
                                ('six_largest_genres',data.primary_genre.isin(six))]:
            subset=data.loc[filter_]
            l=cell_summary(period_frame(subset,a),FEATURES,genres);r=cell_summary(period_frame(subset,b),FEATURES,genres)
            d=kitagawa(l['share'],l['mean'],r['share'],r['mean'])
            for j,c in enumerate(FEATURES):
                w=d['within'][:,j].sum();change=d['delta'][j]
                records.append(dict(analysis='genre_restriction',comparison=key,classifier=c,scenario=scenario,
                    mean0=d['mean0'][j],mean1=d['mean1'][j],delta=change,within=w,composition=d['composition'][:,j].sum(),
                    within_percent=100*w/change if abs(change)>1e-12 else np.nan,
                    retained_full_weight0=l['total_weight'].sum()/left['total_weight'].sum(),
                    retained_full_weight1=r['total_weight'].sum()/right['total_weight'].sum(),descriptive_only=True))
        for j,c in enumerate(FEATURES):
            common=(left['unique_scored'][:,j]>=30)&(right['unique_scored'][:,j]>=30)
            selected=[g for g,ok in zip(genres,common) if ok]
            subset=data[data.primary_genre.isin(selected)]
            l=cell_summary(period_frame(subset,a),[c],genres);r=cell_summary(period_frame(subset,b),[c],genres)
            d=kitagawa(l['share'],l['mean'],r['share'],r['mean']);w=d['within'].sum();change=d['delta'][0]
            records.append(dict(analysis='genre_restriction',comparison=key,classifier=c,scenario='common_support_30_songs',
                retained_genres=' | '.join(selected),mean0=d['mean0'][0],mean1=d['mean1'][0],delta=change,within=w,
                composition=d['composition'].sum(),within_percent=100*w/change if abs(change)>1e-12 else np.nan,
                retained_full_weight0=l['total_weight'].sum()/left['total_weight'].sum(),
                retained_full_weight1=r['total_weight'].sum()/right['total_weight'].sum(),descriptive_only=True))
    return records,six


def breakpoint_analysis(data,identity):
    records=[];tests=[];coefficients=[];sens=[];accounting=[]
    for year in BREAKS:
        start=time.perf_counter();window=data[data.year.between(year-6,year+5)]
        if window.month.nunique()!=144:raise ValueError('Incomplete breakpoint observation window')
        for adjusted in [False,True]:
            model='genre_adjusted' if adjusted else 'unadjusted'
            for frame,features in score_groups(window):
                base=breakpoint_group(frame,features,year,adjusted,do_bootstrap=False)
                cache_name='break_'+str(year)+'_'+model+'_'+digest(features)[:8]
                draws,reused=cached_bootstrap(cache_name,[identity,year,model,features],
                    lambda:breakpoint_group(frame,features,year,adjusted)['draws'])
                u=uncertainty(base['beta'],draws)
                accounting.append(dict(year=year,model=model,scores=len(features),replicate_fits=0 if reused else BOOTSTRAPS,
                    reused=reused,parameters=base['parameters'],matrix_condition=base['condition']))
                for j,c in enumerate(features):
                    row=dict(break_year=year,break_month=str(year)+'-01',model=model,classifier=c,
                        window_start=str(year-6)+'-01',window_end=str(year+5)+'-12',
                        n_song_months=base['n_rows'],n_songs=base['n_songs'],n_artists=base['n_artists'],n_months=base['n_months'],
                        r2=base['r2'][j],status='ok',exploratory=True)
                    for k,term in enumerate(['level','slope']):
                        row[term]=base['beta'][j,k]
                        for name in ['low','high','p','se']:row[term+'_'+name]=u[name][j,k]
                        for name in ['low','high','se']:row[term+'_hac24_'+name]=base['hac'][name][k,j]
                        tests.append(dict(test_id='breakpoint:'+str(year)+':'+model+':'+c+':'+term,
                            family='breakpoint',comparison=str(year),model=model,classifier=c,term=term,p_value=u['p'][j,k]))
                    records.append(row)
                    coefficients.extend(dict(break_year=year,model=model,classifier=c,term=name,coefficient=base['all_beta'][k,j])
                        for k,name in enumerate(base['names']))
                if year==2020:
                    for block,mode in [(12,'crossed'),(36,'crossed'),(24,'artist_only'),(24,'calendar_only')]:
                        name=cache_name+'_'+str(block)+'_'+mode
                        extra,_=cached_bootstrap(name,[identity,name,SENSITIVITY_BOOTSTRAPS],
                            lambda:breakpoint_group(frame,features,year,adjusted,repeats=SENSITIVITY_BOOTSTRAPS,block=block,mode=mode)['draws'])
                        uextra=uncertainty(base['beta'],extra)
                        for j,c in enumerate(features):
                            for k,term in enumerate(['level','slope']):
                                sens.append(dict(analysis='breakpoint_uncertainty',comparison='2020',model=model,classifier=c,
                                    scenario=mode+'_'+str(block)+'months',term=term,estimate=base['beta'][j,k],
                                    low=uextra['low'][j,k],high=uextra['high'][j,k],descriptive_only=True))
        print(json.dumps(dict(stage='breakpoints',year=year,seconds=time.perf_counter()-start)),flush=True)
    # These predefined alternatives change specification, not the selected breakpoint.
    window=data[data.year.between(2014,2025)]
    for scenario,weighting,offset,quadratic,notlow in [
        ('rank_weighted','rank_weighted',0,False,False),('march_2020','song_month',2,False,False),
        ('quadratic_background','song_month',0,True,False),('genre_not_low','song_month',0,False,True)]:
        subset=window[window.genre_confidence.ne('low')] if notlow else window
        for adjusted in [False,True]:
            model='genre_adjusted' if adjusted else 'unadjusted'
            for frame,features in score_groups(subset):
                base=breakpoint_group(frame,features,2020,adjusted,weighting,offset,quadratic,do_bootstrap=False)
                for j,c in enumerate(features):
                    for k,term in enumerate(['level','slope']):
                        sens.append(dict(analysis='breakpoint_specification',comparison='2020',model=model,classifier=c,
                            scenario=scenario,term=term,estimate=base['beta'][j,k],low=base['hac']['low'][k,j],
                            high=base['hac']['high'][k,j],interval_method='HAC24 diagnostic',descriptive_only=True))
    for row in records:
        if row['break_year']!=2020:continue
        earlier=[r for r in records if r['break_year']!=2020 and r['model']==row['model'] and r['classifier']==row['classifier']]
        for term in ['level','slope']:
            row[term+'_absolute_rank_of_11']=1+sum(abs(r[term])>abs(row[term]) for r in earlier)
            row[term+'_historical_max_abs']=max(abs(r[term]) for r in earlier)
        row['placebo_comparison_warning']='Ten fixed historical windows overlap; ranks are descriptive, not randomization p-values'
    return records,tests,coefficients,sens,accounting


def annual_tables(data,genres):
    """All-score annual descriptive coverage; no annual hypothesis search."""
    rows=[];shares=[]
    for year,frame in data.groupby('year',sort=True):
        for weighting in WEIGHTINGS:
            f=frame.drop_duplicates('song_id').copy() if weighting=='unique_song' else frame.copy()
            f['weight']=f.rank_weight if weighting=='rank_weighted' else 1.
            s=cell_summary(f,FEATURES,genres)
            for j,c in enumerate(FEATURES):
                rows.append(dict(year=year,weighting=weighting,genre='All genres',classifier=c,mean=s['observed_mean'][j],
                    score_coverage=s['coverage'][j],n_songs=int(s['unique_scored'][:,j].sum()),n_total_songs=s['n_songs'],
                    scored_weight=s['scored_weight'][:,j].sum(),total_weight=s['total_weight'].sum()))
                for gi,g in enumerate(genres):
                    rows.append(dict(year=year,weighting=weighting,genre=g,classifier=c,mean=s['mean'][gi,j],
                        score_coverage=s['scored_weight'][gi,j]/s['total_weight'][gi] if s['total_weight'][gi]>0 else np.nan,
                        n_songs=s['unique_scored'][gi,j],n_total_songs=s['unique_total'][gi],
                        scored_weight=s['scored_weight'][gi,j],total_weight=s['total_weight'][gi]))
            for gi,g in enumerate(genres):
                shares.append(dict(year=year,weighting=weighting,genre=g,full_share=s['total_weight'][gi]/s['total_weight'].sum(),
                    total_weight=s['total_weight'][gi],unique_songs=s['unique_total'][gi],
                    lyrics_available_weight=float(f.loc[f.primary_genre.eq(g)&f.lyrics_available.eq(1),'weight'].sum())))
    return rows,shares


def independent_validate(data,genres,totals,details,tests):
    """Different calculation paths: direct weighted means and two reference paths."""
    maximum=0.;checks=0
    for row in totals:
        a=period_frame(data,row['period0'],row['weighting']);b=period_frame(data,row['period1'],row['weighting']);c=row['classifier']
        means=[]
        for f in [a,b]:
            valid=f[c].notna();means.append(np.average(f.loc[valid,c],weights=f.loc[valid,'weight']))
        np.testing.assert_allclose([row['mean0'],row['mean1'],row['delta']],[*means,means[1]-means[0]],atol=2e-12,rtol=2e-12)
        maximum=max(maximum,abs(row['within']+row['composition']-row['delta']));checks+=1
    df=pd.DataFrame(details)
    for _,g in df.groupby(['comparison','weighting','classifier'],sort=False):
        mu0=g.mean0.fillna(g.mean1).fillna(0).to_numpy();mu1=g.mean1.fillna(g.mean0).fillna(0).to_numpy()
        p0=g.share0.to_numpy();p1=g.share1.to_numpy()
        # Average the two sequential standardization paths independently.
        within=((p0@mu1-p0@mu0)+(p1@mu1-p1@mu0))/2
        composition=((p1@mu0-p0@mu0)+(p1@mu1-p0@mu1))/2
        np.testing.assert_allclose([g.within.sum(),g.composition.sum()],[within,composition],atol=2e-12)
        np.testing.assert_allclose([p0.sum(),p1.sum()],[1,1],atol=2e-12)
    if len(tests)!=HYPOTHESES or len({r['test_id'] for r in tests})!=HYPOTHESES:raise ValueError('Primary testing denominator changed')
    q=stats.false_discovery_control([r['p_value'] for r in tests],method='by')
    np.testing.assert_array_equal(q,[r['q_by_global'] for r in tests])
    return dict(status='PASS',independent_direct_comparisons=checks,independent_two_path_decompositions=checks,
        max_reconciliation_error=maximum,primary_tests=len(tests),all_original_genres=len(genres),
        duplicate_song_months=int(data.duplicated(['month','song_id']).sum()),preservation=preserve())


def audit_claims(totals,sensitivity):
    selected={r['classifier']:r for r in totals if r['comparison']==comparison_id('1990s','2015–2024') and r['weighting']=='song_month'}
    six={r['classifier']:r for r in sensitivity if r.get('comparison')==comparison_id('1990s','2015–2024') and r.get('scenario')=='six_largest_genres'}
    return [dict(classifier=c,claimed_within_percent=claim,provenance='Group Milestone 2 report, Question 4, supplied by user',
        original_code_available=False,original_six_genres_known=False,original_weighting_verified=False,
        independent_all16_within_percent=selected[c]['within_percent'],six_largest_sensitivity_percent=six[c]['within_percent'],
        difference_percentage_points=selected[c]['within_percent']-claim,
        verdict='Original claim unverified; new symmetric result independently reconciled; no tuning to match claim') for c,claim in CLAIMS.items()]


def run():
    started=time.perf_counter();before=preserve();data,genres,duplicates=load_data();identity=source_identity()
    protocol_path=PUBLIC/'protocol.json'
    if protocol_path.exists() and json.loads(protocol_path.read_text())['identity']!=identity:
        raise ValueError('Analysis identity changed; do not silently reuse earlier output/cache')
    write_json(protocol_path,dict(identity=identity,exploratory=True,original_claims_unverified=True))
    print(json.dumps(dict(stage='start',rows=len(data),songs=data.song_id.nunique(),primary_hypotheses=HYPOTHESES)),flush=True)
    cells,cell_rows=period_statistics(data,genres);totals,details=descriptive_comparisons(cells,genres)
    tests,uncertainty_sens=add_decomposition_uncertainty(data,genres,totals,identity)
    sensitivity,six=sensitivities(data,genres,cells)
    breaks,break_tests,coefficients,break_sens,accounting=breakpoint_analysis(data,identity);tests.extend(break_tests)
    if len(tests)!=HYPOTHESES:raise ValueError('Incomplete fixed primary test family')
    q=stats.false_discovery_control([r['p_value'] for r in tests],method='by')
    for row,value in zip(tests,q):row['q_by_global']=float(value)
    lookup={r['test_id']:r['q_by_global'] for r in tests}
    for row in totals:
        if row['weighting']=='song_month' and row['classifier'] in PRIMARY:
            for term in ['delta','within','composition']:row[term+'_q']=lookup['decomposition:'+row['comparison']+':'+row['classifier']+':'+term]
    for row in breaks:
        for term in ['level','slope']:row[term+'_q']=lookup['breakpoint:'+str(row['break_year'])+':'+row['model']+':'+row['classifier']+':'+term]
    annual,shares=annual_tables(data,genres)
    validation=independent_validate(data,genres,totals,details,tests)
    all_sens=sensitivity+uncertainty_sens+break_sens
    write_csv('decomposition_results.csv',details);write_csv('historical_comparisons.csv',totals)
    write_csv('genre_period_statistics.csv',cell_rows);write_csv('sensitivity_results.csv',all_sens)
    write_csv('breakpoint_results.csv',breaks);write_csv('breakpoint_coefficients.csv',coefficients)
    write_csv('primary_tests.csv',tests);write_csv('preliminary_claims_audit.csv',audit_claims(totals,sensitivity))
    write_csv('annual_trajectories.csv.gz',annual);write_csv('annual_genre_shares.csv',shares)
    write_csv('duplicate_song_month_audit.csv',duplicates)
    write_json(PUBLIC/'validation.json',validation)
    execution=dict(status='PASS',seconds=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        rows=len(data),songs=int(data.song_id.nunique()),artists=int(data.artist.nunique()),classifiers=len(FEATURES),
        comparisons=len(totals),genre_contribution_rows=len(details),primary_hypotheses=HYPOTHESES,
        primary_by_pass=sum(r['q_by_global']<=.05 for r in tests),breakpoint_groups=accounting,
        six_largest_genres=six,initial_preservation=before,input_sha256=descriptive.sha(moving.INPUT))
    write_json(PUBLIC/'execution.json',execution);print(json.dumps(execution,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['benchmark','run','verify-originals'])
    args=parser.parse_args();PUBLIC.mkdir(exist_ok=True);LOCAL.mkdir(parents=True,exist_ok=True)
    with threadpool_limits(limits=1):
        if args.command=='benchmark':
            data,genres,duplicates=load_data();print(json.dumps(benchmark(data,genres),indent=2))
        elif args.command=='run':run()
        else:print(json.dumps(preserve(),indent=2))
