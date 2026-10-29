"""Calendar-preserving influence, HAC and block-resampling diagnostics.

All fits are descriptive audits of a selected historical sample. The original
V5 correction is never replaced by the smaller diagnostic family.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import numpy as np
import pandas as pd
from scipy import linalg, stats
import pairwise_v5_common as v5
import pairwise_v5_stats as old
import robustness_v51_common as c


@dataclass
class Series:
    x: np.ndarray
    y: np.ndarray
    controls: np.ndarray
    weights: np.ndarray
    first_month: np.ndarray
    last_month: np.ndarray
    frequency: str
    lag: int
    label: str = ''

    def mask(self):
        return np.isfinite(self.x)&np.isfinite(self.y)&np.isfinite(self.controls).all(axis=1)&np.isfinite(self.weights)&(self.weights>0)&(self.first_month>=0)


def from_workspace(workspace, task, name):
    a=workspace.aligned(task); j=a.names.index(name)
    controls=a.controls_composition if a.profiles[j]=='composition' else a.controls_time
    return Series(a.x.astype(float),a.y[:,j],controls,a.weights.copy(),a.first_month,a.last_month,a.frequency,task['lag'],name)


def month_number(value): return (pd.Period(value,'M')-pd.Period(v5.CONFIG['months'][0],'M')).n


def month_labels(numbers):
    first=pd.Period(v5.CONFIG['months'][0],'M')
    return np.array([str(first+int(n)) if n>=0 else '' for n in numbers])


def calendar_years(data):
    return np.array([(pd.Period(v5.CONFIG['months'][0],'M')+int(n)).year if n>=0 else -1 for n in data.last_month])


def period_mask(data,start,end,include_exposure=False):
    """Any overlap with [start,end), including native support and lag if asked."""
    a,b=month_number(start),month_number(end)
    result=(data.first_month<b)&(data.last_month>=a)&(data.first_month>=0)
    if include_exposure:
        result|=(data.first_month-data.lag<b)&(data.last_month-data.lag>=a)&(data.first_month>=0)
    return result


def kish(energy):
    energy=np.asarray(energy,float)
    return float(energy.sum()**2/(energy@energy)) if np.any(energy) else 0.


def fit(data,bandwidth=None,subset=None,ranked=False,weighted=False,minimum=None):
    bandwidth=v5.CONFIG['hac_lags'][data.frequency] if bandwidth is None else int(bandwidth)
    mask=data.mask()
    if subset is not None: mask &= np.asarray(subset,bool)
    pos=np.flatnonzero(mask); n=len(pos)
    out=dict(status='insufficient_observations',n=n,bandwidth=bandwidth,method='rank' if ranked else 'pearson',
        weighted=bool(weighted),inferential_support=False,p_for_family=1.)
    floor=c.CONFIG['minimum_descriptive_n'][data.frequency] if minimum is None else minimum
    if n<floor:return out,None
    x,y,C=data.x[mask],data.y[mask],data.controls[mask]
    if ranked:x,y=stats.rankdata(x),stats.rankdata(y)
    weights=data.weights[mask] if weighted else np.ones(n)
    root=np.sqrt(weights); basis=old.control_basis(C,weights)
    xr=old.residualize(basis,x*root);yr=old.residualize(basis,y*root)
    sxx=float(xr@xr);syy=float(yr@yr)
    out.update(control_rank=basis.rank,residual_df=n-basis.rank-1)
    if n-basis.rank-1<12:out['status']='insufficient_residual_df';return out,None
    if sxx<=max(1e-20,float(np.sum((x*root)**2))*1e-22) or syy<=max(1e-20,float(np.sum((y*root)**2))*1e-22):
        out['status']='unidentified_effect';return out,None
    beta=float(xr@yr/sxx);error=yr-beta*xr
    score=xr*error/sxx
    variance=float(old.hac_variance(score,pos,len(mask),bandwidth)[0])*n/(n-basis.rank-1)
    se=np.sqrt(variance);df=min(n-basis.rank-1,max(1,n//(bandwidth+1)-1))
    probability=float(2*stats.t.sf(abs(beta)/se,df)) if se>1e-300 else 0. if abs(beta)>1e-14 else 1.
    scale=np.sqrt(sxx/syy);r=float(np.clip(beta*scale,-1,1));quantile=stats.t.ppf(.975,df)
    supported=n>=v5.CONFIG['minimum_native'][data.frequency] and n//(bandwidth+1)>=6
    blocks=pos//(v5.CONFIG['hac_lags'][data.frequency]+1)
    energy=np.bincount(blocks,weights=xr*xr);score_energy=np.bincount(blocks,weights=(xr*error)**2)
    hat=np.sum(basis.train**2,axis=1)+xr*xr/sxx
    delta=np.divide(xr*error,sxx*(1-hat),out=np.full(n,np.nan),where=1-hat>1e-10)
    # delta = full coefficient - coefficient after deleting the observation.
    mse=float(error@error/(n-basis.rank-1))
    cook=np.divide(error*error*hat,(basis.rank+1)*mse*(1-hat)**2,out=np.full(n,np.nan),where=(1-hat>1e-10)&(mse>0))
    consecutive=np.flatnonzero(np.diff(pos)==1)
    ax=float(np.corrcoef(xr[consecutive],xr[consecutive+1])[0,1]) if len(consecutive)>3 and np.std(xr[consecutive])>0 and np.std(xr[consecutive+1])>0 else np.nan
    ay=float(np.corrcoef(yr[consecutive],yr[consecutive+1])[0,1]) if len(consecutive)>3 and np.std(yr[consecutive])>0 and np.std(yr[consecutive+1])>0 else np.nan
    effective=float(np.clip(n*(1-ax*ay)/(1+ax*ay),1,n)) if np.isfinite(ax*ay) and 1+ax*ay>0 else np.nan
    out.update(status='ok',slope=beta,se=float(se),r=r,ci_low=float(beta-quantile*se),ci_high=float(beta+quantile*se),
        r_ci_low=max(-1.,float((beta-quantile*se)*scale)),r_ci_high=min(1.,float((beta+quantile*se)*scale)),
        nominal_p=probability,inferential_support=supported,p_for_family=probability if supported else 1.,df=df,
        first_month=month_labels([data.first_month[mask].min()])[0],last_month=month_labels([data.last_month[mask].max()])[0],
        effective_exposure_blocks=kish(energy),effective_score_blocks=kish(score_energy),
        largest_exposure_block_fraction=float(energy.max()/energy.sum()),largest_score_block_fraction=float(score_energy.max()/score_energy.sum()) if score_energy.sum()>0 else np.nan,
        acf_x=ax,acf_y=ay,ar1_effective_n_diagnostic=effective,calendar_hac_blocks=int(n//(bandwidth+1)),
        maximum_leverage=float(hat.max()),maximum_cooks_distance=float(np.nanmax(cook)))
    internal=dict(mask=mask,positions=pos,x=x,y=y,controls=C,weights=weights,basis=basis,xr=xr,yr=yr,sxx=sxx,syy=syy,
        error=error,score=score,hat=hat,deletion_delta=delta,cook=cook,blocks=blocks,energy=energy,score_energy=score_energy)
    return out,internal


def influence_rows(data,info):
    pos=info['positions']; x=info['xr'];y=info['yr']; error=info['error'];cov=x*y
    denominator=float(np.sum(abs(cov)))
    rows=[]
    for i,p in enumerate(pos):
        rows.append(dict(grid_position=int(p),first_month=month_labels([data.first_month[p]])[0],last_month=month_labels([data.last_month[p]])[0],
            exposure_energy_fraction=float(x[i]**2/info['sxx']),
            absolute_covariance_fraction=float(abs(cov[i])/denominator) if denominator else 0.,
            signed_covariance_fraction=float(cov[i]/denominator) if denominator else 0.,
            score_energy_fraction=float((x[i]*error[i])**2/np.sum((x*error)**2)),
            leverage=float(info['hat'][i]),cooks_distance=float(info['cook'][i]),
            slope_change_on_deletion=float(-info['deletion_delta'][i]),
            dfbeta=float(info['deletion_delta'][i]/np.sqrt(np.sum(error**2)/max(1,len(x)-info['basis'].rank-1)/info['sxx']))))
    return rows


def block_rows(data,info,width=None):
    width=v5.CONFIG['hac_lags'][data.frequency]+1 if width is None else width
    block=info['positions']//width; rows=[]
    for key in np.unique(block):
        mask=block==key; p=info['positions'][mask];energy=info['xr'][mask]**2
        score=(info['xr'][mask]*info['error'][mask])**2
        rows.append(dict(block=int(key),width_native_periods=int(width),first_month=month_labels([data.first_month[p].min()])[0],
            last_month=month_labels([data.last_month[p].max()])[0],observations=int(mask.sum()),
            exposure_fraction=float(energy.sum()/info['sxx']),
            score_fraction=float(score.sum()/np.sum((info['xr']*info['error'])**2))))
    return rows


def block_draws(size,length,rng):
    """Overlapping, noncircular moving blocks; draw grid slots before dropping NaN."""
    if length<1 or length>size:raise ValueError('Unsupported moving block length')
    starts=rng.integers(0,size-length+1,size=int(np.ceil(size/length)))
    return (starts[:,None]+np.arange(length)).ravel()[:size]


def bootstrap(data,method,repetitions,random_seed,check=lambda:None):
    original,info=fit(data)
    if info is None:return dict(method=method,status=original['status'],attempted=repetitions,successful=0),[]
    rng=np.random.default_rng(random_seed);n_grid=len(data.x);pos=info['positions'];rank=info['basis'].rank
    # An orthonormal basis keeps full regression resampling well conditioned.
    D=np.column_stack([info['basis'].train,info['xr']/np.sqrt(info['sxx'])]);y=info['y'];k=D.shape[1]
    moments=(D[:,:,None]*D[:,None,:]).reshape(len(D),-1)
    cross=D*y[:,None];yy=y*y
    years=calendar_years(data)
    if method=='calendar_year_pairs':
        # A one-year block is one row for annual data and cannot retain dependence.
        labels=years//5 if data.frequency in ['A','term','event'] else years
        groups=[np.flatnonzero(labels==key) for key in np.unique(labels[years>=0])]
    elif method!='moving_pairs':raise ValueError('Unknown resampling method')
    length=c.CONFIG['moving_block_periods'][data.frequency];slopes=[];correlations=[];n_samples=[]
    for start in range(0,repetitions,32):
        count=min(32,repetitions-start);weights=[]
        for _ in range(count):
            if method=='moving_pairs':indices=block_draws(n_grid,min(length,n_grid),rng)
            else:indices=np.concatenate([groups[i] for i in rng.integers(0,len(groups),size=len(groups))])
            weights.append(np.bincount(indices,minlength=n_grid)[pos])
        weights=np.asarray(weights,float); gram=(weights@moments).reshape(count,k,k);rhs=weights@cross;yty=weights@yy
        eigen,vectors=np.linalg.eigh(gram);valid=eigen[:,0]>np.maximum(eigen[:,-1],1)*1e-10
        for b in range(count):
            if not valid[b] or weights[b].sum()<rank+13:
                slopes.append(np.nan);correlations.append(np.nan);n_samples.append(int(weights[b].sum()));continue
            inverse=(vectors[b]/eigen[b])@vectors[b].T;coef=inverse@rhs[b]
            sxx=1/inverse[-1,-1];sse=float(yty[b]-rhs[b]@coef);syy=max(0,sse)+coef[-1]**2*sxx
            slopes.append(float(coef[-1]/np.sqrt(info['sxx'])))
            correlations.append(float(np.clip(coef[-1]*np.sqrt(sxx/syy),-1,1)) if syy>1e-20 else np.nan)
            n_samples.append(int(weights[b].sum()))
        check()
    slopes=np.asarray(slopes);correlations=np.asarray(correlations);valid=np.isfinite(slopes)&np.isfinite(correlations)
    summary=dict(method=method,status='ok' if valid.mean()>=.9 else 'insufficient_resampling_support',attempted=repetitions,successful=int(valid.sum()),
        block_definition=f'{length} consecutive native periods' if method=='moving_pairs' else 'five calendar years' if data.frequency in ['A','term','event'] else 'one calendar year',
        original_slope=original['slope'],original_r=original['r'],same_direction_fraction=float(np.mean(slopes[valid]*original['slope']>0)) if valid.any() else np.nan,
        interval_interpretation='Percentile paired-block diagnostic, full nuisance refit; conditional on selected variables, observed periods and model. Not selection-adjusted confirmation.')
    if valid.any():
        summary.update(ci_low=float(np.quantile(slopes[valid],.025)),ci_high=float(np.quantile(slopes[valid],.975)),
            r_ci_low=float(np.quantile(correlations[valid],.025)),r_ci_high=float(np.quantile(correlations[valid],.975)),
            median_slope=float(np.median(slopes[valid])),minimum_resampled_n=int(np.min(np.array(n_samples)[valid])))
    draws=[dict(replicate=i,slope=float(a),r=float(b),sample_n=int(n)) for i,(a,b,n) in enumerate(zip(slopes,correlations,n_samples))]
    return summary,draws


def shifted(array,steps):
    """Positive steps: earlier exposure; negative steps: FUTURE placebo. No wrap."""
    values=np.asarray(array);result=np.full(len(values),np.nan)
    if steps==0:return values.copy()
    if abs(steps)>=len(values):return result
    if steps>0:result[steps:]=values[:-steps]
    else:result[:steps]=values[-steps:]
    return result


def block_permutation(data,repetitions,random_seed,check=lambda:None):
    reference,info=fit(data)
    if info is None:return dict(status=reference['status'],attempted=repetitions,successful=0,p_for_family=1.),[]
    rng=np.random.default_rng(random_seed);x=np.full(len(data.x),np.nan);x[info['positions']]=info['xr']
    length={'M':12,'Q':4,'A':5,'term':3,'event':5}[data.frequency]
    groups=[np.arange(i,min(i+length,len(x))) for i in range(0,len(x),length)]
    values=[]
    for b in range(repetitions):
        permutation=np.concatenate([groups[i] for i in rng.permutation(len(groups))])
        value,_=fit(replace(data,x=x[permutation]))
        values.append(value.get('r',np.nan))
        if b%32==0:check()
    values=np.asarray(values);finite=np.isfinite(values)
    probability=float((1+np.sum(abs(values[finite])>=abs(reference['r'])))/(1+finite.sum()))
    summary=dict(status='ok' if finite.mean()>=.9 else 'insufficient_permutation_support',attempted=repetitions,successful=int(finite.sum()),
        method='residual_exposure_block_permutation',block_native_periods=length,observed_r=reference['r'],
        exceedance_probability=probability,p_for_family=probability if finite.mean()>=.9 else 1.,
        null_r_low=float(np.quantile(values[finite],.025)) if finite.any() else np.nan,
        null_r_high=float(np.quantile(values[finite],.975)) if finite.any() else np.nan,
        interpretation='Diagnostic only: block exchangeability/stationarity may fail; preserves local exposure ordering within blocks, not all long-range dependence. Same selected historical data.')
    return summary,[dict(replicate=i,r=float(r)) for i,r in enumerate(values)]


def time_controls(data,quadratic=False,composition=None):
    t=(data.first_month+data.last_month)/24
    month=(data.first_month+7)%12+1
    controls=[np.ones(len(t)),t,np.sin(2*np.pi*month/12),np.cos(2*np.pi*month/12)]
    if quadratic:controls.append((t-t.mean())**2)
    if composition is not None:controls.extend(np.asarray(composition).T)
    return np.column_stack(controls)


def rolling(data,periods=3):
    apply=lambda v:pd.Series(v).rolling(periods,min_periods=periods).mean().to_numpy()
    controls=pd.DataFrame(data.controls).rolling(periods,min_periods=periods).mean().to_numpy()
    first=np.r_[np.full(periods-1,-1),data.first_month[:len(data.x)-periods+1]]
    return replace(data,x=apply(data.x),y=apply(data.y),controls=controls,first_month=first)


def break_fit(data,year):
    post=(data.first_month>=month_number(f'{year}-01')).astype(float)
    valid=data.mask();before=int(np.sum(valid&(post==0)));after=int(np.sum(valid&(post==1)))
    minimum={'M':60,'Q':20,'A':12,'term':12,'event':12}[data.frequency]
    if min(before,after)<minimum:return dict(status='insufficient_periods_either_side',n=int(valid.sum()),p_for_family=1.)
    # The one prespecified interaction tests stability of this fixed pair only.
    controls=np.column_stack([data.controls,data.x,post])
    result,_=fit(replace(data,x=data.x*post,controls=controls))
    return dict(result,break_year=year,estimand='Post-minus-pre external slope; fixed diagnostic breakpoint, not a causal event estimate')
