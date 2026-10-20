"""Typed dependence, explicit nulls, block uncertainty and multiplicity control."""
from __future__ import annotations
import hashlib
import math
import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import pdist, squareform
from sklearn.feature_selection import mutual_info_regression
from sklearn.metrics import mutual_info_score

import relationship_discovery_spec as spec


def rng_for(key, purpose):
    seed=int(hashlib.sha256((str(spec.SEED)+str(key)+purpose).encode()).hexdigest()[:16],16)
    return np.random.default_rng(seed)


def correlation(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float)
    a=x-x.mean();b=y-y.mean();den=np.linalg.norm(a)*np.linalg.norm(b)
    return float(a@b/den) if den>0 else 0.


def eta_squared(groups,values):
    g=np.asarray(groups,int);v=np.asarray(values,float)
    counts=np.bincount(g);sums=np.bincount(g,weights=v)
    valid=counts>0
    total=float(np.sum((v-v.mean())**2))
    between=float(np.sum(counts[valid]*(sums[valid]/counts[valid]-v.mean())**2))
    return between/total if total>0 else 0.


def contingency(x,y):
    x=np.asarray(x,int);y=np.asarray(y,int)
    ny=int(y.max())+1
    return np.bincount(x*ny+y,minlength=(int(x.max())+1)*ny).reshape(-1,ny)


def cramers_v(x,y):
    table=contingency(x,y)
    table=table[table.sum(axis=1)>0][:,table.sum(axis=0)>0]
    n=table.sum();r,c=table.shape
    if min(r,c)<2:return 0.
    expected=np.outer(table.sum(axis=1),table.sum(axis=0))/n
    chi=float(np.sum((table-expected)**2/expected))
    # Bias-corrected V; nominal labels are used only as table coordinates.
    phi=max(0.,chi/n-(r-1)*(c-1)/(n-1))
    denom=min(r-1-(r-1)**2/(n-1),c-1-(c-1)**2/(n-1))
    return float(np.sqrt(phi/denom)) if denom>0 else 0.


def discretize(x,bins=10):
    x=np.asarray(x,float)
    edges=np.unique(np.quantile(x,np.linspace(0,1,bins+1)))
    return np.searchsorted(edges[1:-1],x,side='right')


def distance_correlation(x,y):
    a=squareform(pdist(np.asarray(x,float).reshape(-1,1)))
    b=squareform(pdist(np.asarray(y,float).reshape(-1,1)))
    for d in (a,b):d-=d.mean(axis=0)[None,:]+d.mean(axis=1)[:,None]-d.mean()
    denom=np.sqrt(np.mean(a*a)*np.mean(b*b))
    return float(np.sqrt(max(0.,np.mean(a*b)/denom))) if denom>0 else 0.


def typed_stat(x,y,xcat,ycat):
    if xcat and ycat:return cramers_v(x,y)
    if xcat:return eta_squared(x,y)
    if ycat:return eta_squared(y,x)
    return abs(correlation(x,y))


def permutation_p(x,y,years,xcat,ycat,key,repeats=spec.PERMUTATIONS):
    observed=typed_stat(x,y,xcat,ycat)
    groups=[np.flatnonzero(years==v) for v in np.unique(years)]
    rng=rng_for(key,'within-year-permutation');exceed=0
    for _ in range(repeats):
        yp=y.copy()
        for idx in groups:yp[idx]=y[rng.permutation(idx)]
        exceed+=typed_stat(x,yp,xcat,ycat)>=observed-1e-12
    return (1+exceed)/(repeats+1)


def block_interval(values,years,key,repeats=spec.BOOTSTRAPS,width=2):
    """Resample non-overlapping calendar blocks; equal weight per observed year."""
    frame=pd.DataFrame({'value':values,'year':years}).groupby('year',sort=True).value.mean()
    blocks=[g.to_numpy() for _,g in frame.groupby(frame.index//width)]
    if len(blocks)<3:return dict(interval=None,blocks=len(blocks),warning='Fewer than three calendar blocks')
    rng=rng_for(key,'blocks'+str(width));draws=[]
    for _ in range(repeats):
        picked=rng.integers(len(blocks),size=len(blocks))
        draws.append(float(np.concatenate([blocks[i] for i in picked]).mean()))
    return dict(interval=np.quantile(draws,[.025,.975]).tolist(),blocks=len(blocks),
                warning='Fixed-analysis interval; excludes model selection and refitting uncertainty')


def paired_evidence(difference,years,key):
    frame=pd.DataFrame({'d':difference,'year':years})
    block=frame.groupby(frame.year//2).d.mean().to_numpy()
    result=dict(effect=float(block.mean()),effect_name='equal-two-year-block mean loss reduction / training target variance',
        blocks=len(block),ci_low=None,ci_high=None,p_value=None)
    if len(block)<8:
        result['inference_warning']='Fewer than eight two-year blocks; no primary p value'
        return result
    rng=rng_for(key,'paired-loss');draw=rng.integers(len(block),size=(spec.BOOTSTRAPS,len(block)))
    result['ci_low'],result['ci_high']=np.quantile(block[draw].mean(axis=1),[.025,.975]).tolist()
    if np.allclose(block,0,atol=1e-15):p=1.
    else:
        # Symmetric block-level paired-loss null; one-sided improvement, fixed a priori.
        signs=rng.choice([-1.,1.],size=(spec.SIGN_FLIPS,len(block)))
        null=signs@block/len(block)
        p=(1+int(np.sum(null>=block.mean()-1e-12)))/(spec.SIGN_FLIPS+1)
    result['p_value']=p
    result['four_year_sensitivity']=block_interval(difference,years,key,width=4)
    result['inference_warning']='Exploratory symmetric paired-loss block null; short-range dependence assumed; overlapping training histories and prior data inspection prevent independent confirmation'
    return result


def dependence_interval(x,y,years,xcat,ycat,key):
    blocks=[np.flatnonzero(years//2==b) for b in np.unique(years//2)]
    if len(blocks)<3:return dict(interval=None,blocks=len(blocks))
    rng=rng_for(key,'dependence-interval');values=[]
    for _ in range(spec.BOOTSTRAPS):
        idx=np.concatenate([blocks[i] for i in rng.integers(len(blocks),size=len(blocks))])
        value=typed_stat(x[idx],y[idx],xcat,ycat) if xcat or ycat else correlation(x[idx],y[idx])
        values.append(value)
    return dict(interval=np.quantile(values,[.025,.975]).tolist(),blocks=len(blocks),
        warning='Two-year block interval; numerical ranks fixed before resampling; fixed-analysis uncertainty only')


def pair_analysis(frame,row):
    xname=row['predictors'][0];yname=row['target'];xcat=spec.kind(xname)=='categorical';ycat=spec.kind(yname)=='categorical'
    f=frame.dropna(subset=[xname,yname]);n=len(f)
    result=dict(row,n=n,n_missing=len(frame)-n,status='ok',family_tags=['Stage A: pairwise dependence'],
        primary_test='within-debut-year response permutation; conditional exchangeability, not unconditional independence',
        p_value=None,p_resolution=1/(spec.PERMUTATIONS+1))
    if n<spec.MIN_EVALUATION:
        return dict(result,status='insufficient_coverage')
    if f[xname].nunique()<2 or f[yname].nunique()<2:
        return dict(result,status='insufficient_variation',effect=None)
    x=pd.factorize(f[xname],sort=True)[0] if xcat else f[xname].to_numpy(float)
    y=pd.factorize(f[yname],sort=True)[0] if ycat else f[yname].to_numpy(float)
    xr=x if xcat else stats.rankdata(x);yr=y if ycat else stats.rankdata(y)
    years=f.debut_year.to_numpy(int)
    dx=x if xcat else discretize(x);dy=y if ycat else discretize(y)
    result['mutual_information_nats']=float(mutual_info_score(dx,dy))
    result['mi_estimator']='empirical ten-quantile-bin contingency MI; tied bins collapse; upward finite-sample bias; not comparable across cardinalities'
    if not xcat and not ycat:
        result['spearman']=correlation(xr,yr);result['effect']=result['spearman'];result['effect_name']='pooled Spearman rho'
        if spec.kind(xname)!='ordinal' and spec.kind(yname)!='ordinal':result['pearson']=correlation(x,y)
        take=np.argsort(f._hash.to_numpy(),kind='stable')[:512]
        result['distance_correlation']=distance_correlation(x[take],y[take]);result['distance_correlation_n']=len(take)
        if spec.kind(xname)==spec.kind(yname)=='continuous':
            take=np.argsort(f._hash.to_numpy(),kind='stable')[:5000]
            result['knn_mutual_information_nats']=float(mutual_info_regression(x[take,None],y[take],random_state=spec.SEED,n_neighbors=5)[0])
            result['knn_mutual_information_n']=len(take)
        annual=[]
        for year,g in f.groupby('debut_year'):
            if len(g)>=spec.MIN_YEAR and g[xname].nunique()>1 and g[yname].nunique()>1:
                annual.append((int(year),correlation(stats.rankdata(g[xname]),stats.rankdata(g[yname])),len(g)))
        result['annual_effects']=annual
        if annual:
            a=np.array(annual);ci=block_interval(a[:,1],a[:,0].astype(int),row['candidate_id'])
            result['annual_mean_rho']=float(a[:,1].mean());result['annual_mean_ci']=ci
            result['stability_fraction']=float(np.mean(np.sign(a[:,1])==np.sign(result['effect'])))
    elif xcat and ycat:
        result['effect']=cramers_v(x,y);result['effect_name']='bias-corrected Cramers V'
        tab=contingency(x,y);expected=np.outer(tab.sum(axis=1),tab.sum(axis=0))/n
        result['fraction_expected_cells_below_five']=float(np.mean(expected<5))
    else:
        result['effect']=eta_squared(x,y) if xcat else eta_squared(y,x);result['effect_name']='eta squared, categorical groups versus numerical values'
        group=x if xcat else y
        result['minimum_group_n']=int(np.bincount(group).min())
        result['group_coverage_warning']=result['minimum_group_n']<spec.MIN_GROUP_EVALUATION
    result['effect_interval']=dependence_interval(x if xcat or ycat else xr,y if xcat or ycat else yr,years,xcat,ycat,row['candidate_id'])
    result['p_value']=permutation_p(xr,yr,years,xcat,ycat,row['candidate_id'])
    result['primary_statistic']=typed_stat(xr,yr,xcat,ycat)
    result['primary_statistic_name']='absolute Spearman rho' if not xcat and not ycat else 'Cramers V' if xcat and ycat else 'rank eta squared'
    result['uncertainty_warning']='Permutation validity requires song exchangeability within year; shared artists/model errors are not independent evidence. The displayed pooled effect and year-adjusted null answer different questions.'
    return result


def adjust_multiple_testing(rows):
    inferential={'pairwise','nonlinear','genre_interaction','numeric_interaction','threshold_interaction'}
    tested=[r for r in rows if r['family'] in inferential]
    def assign(group,key):
        p=np.array([r.get('p_value') if r.get('p_value') is not None else 1. for r in group],float)
        if len(p):
            q=stats.false_discovery_control(p,method='by')
            for r,value in zip(group,q):r[key]=float(value)
    assign(tested,'q_by_global')
    for family in sorted(inferential):assign([r for r in tested if r['family']==family],'q_by_family')
    for row in rows:
        row['multiple_testing_status']=('exploratory BY q <= 0.05; not independently confirmed' if row.get('q_by_global',1)<=.05
            else 'no global BY evidence' if row['family'] in inferential else 'descriptive only; no certified inferential test')
        row['independent_confirmation']=False
    return rows
