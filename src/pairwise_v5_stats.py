"""Native-period alignment and vectorized, dependence-aware pairwise estimators."""
from __future__ import annotations
import collections
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy import linalg,stats
import pairwise_v5_common as c

STATUS=['ok','insufficient_native_periods','insufficient_residual_df','insufficient_time_blocks',
        'constant_or_control_collinear','sparse_category','singular_covariance','numerical_failure']
PREDICT_STATUS=['ok','insufficient_training','insufficient_validation','unidentified_external_effect','unsupported_future_control_space','unsupported_category']
FIELDS=[('status','u1'),('inferential','u1'),('n','u2'),('n_months','u2'),('first_month','i2'),('last_month','i2'),
        ('control_rank','u1'),('hac_lags','u1'),('df','f4'),('r','f4'),('rho','f4'),
        ('slope','f8'),('intercept','f8'),('se','f8'),('rho_se','f4'),('p','f8'),('p_rank','f8'),('q','f8'),('q_rank','f8'),
        ('r_song_weighted','f4'),('slope_song_weighted','f8'),('acf_x','f4'),('acf_y','f4'),
        ('trend_x','f4'),('trend_y','f4'),('stationarity_x','f4'),('stationarity_y','f4'),
        ('effective_n_ar1_diagnostic','f4'),('eta_squared','f4'),('category_df','u1'),
        ('fold_status','u1',(3,)),('fold_r','f4',(3,)),('fold_skill','f4',(3,)),('fold_mae','f4',(3,))]
RESULT_DTYPE=np.dtype(FIELDS)


def blank(n):
    rows=np.zeros(n,dtype=RESULT_DTYPE)
    for name in rows.dtype.names:
        if rows.dtype[name].base.kind=='f': rows[name]=np.nan
    rows['status']=1; rows['fold_status']=1; rows['first_month']=-1; rows['last_month']=-1
    return rows


@dataclass
class Basis:
    train: np.ndarray
    transform: np.ndarray
    scale: np.ndarray
    row_projector: np.ndarray
    rank: int

    def apply(self,controls):
        scaled=controls/self.scale
        outside=scaled-scaled@self.row_projector
        supported=np.linalg.norm(outside,axis=1)<=1e-8*(1+np.linalg.norm(scaled,axis=1))
        return controls@self.transform,supported


def control_basis(controls,weights=None):
    """Keep the complete declared control span; remove no substantive direction."""
    a=np.asarray(controls,float); w=np.ones(len(a)) if weights is None else np.asarray(weights,float)
    if not np.isfinite(a).all() or not np.isfinite(w).all() or np.any(w<=0): raise ValueError('Invalid control/weight data')
    scale=np.sqrt(np.average(a*a,axis=0,weights=w)); scale=np.where(scale>1e-12,scale,1.)
    u,s,vt=linalg.svd((a/scale)*np.sqrt(w)[:,None],full_matrices=False,lapack_driver='gesdd')
    rank=int(np.sum(s>s[0]*c.CONFIG['control_rank_tolerance'])) if len(s) and s[0]>0 else 0
    if not rank: raise ValueError('Nuisance basis has no intercept')
    transform=(vt[:rank].T/s[:rank])/scale[:,None]
    return Basis(u[:,:rank],transform,scale,vt[:rank].T@vt[:rank],rank)


def residualize(basis,values): return values-basis.train@(basis.train.T@values)


def correlation(x,y):
    if y.ndim==1: y=y[:,None]
    a=x-x.mean(); b=y-y.mean(axis=0)
    denominator=np.sqrt(np.sum(a*a)*np.sum(b*b,axis=0))
    return np.divide(a@b,denominator,out=np.full(y.shape[1],np.nan),where=denominator>1e-20)


def hac_variance(scores,positions,grid_size,bandwidth):
    """Bartlett HAC on the original period grid, including calendar gaps."""
    if scores.ndim==1: scores=scores[:,None]
    grid=np.zeros((grid_size,scores.shape[1])); grid[positions]=scores
    variance=np.sum(grid*grid,axis=0)
    for lag in range(1,min(bandwidth,grid_size-1)+1):
        variance+=2*(1-lag/(bandwidth+1))*np.sum(grid[lag:]*grid[:-lag],axis=0)
    if np.any(variance < -1e-10*np.maximum(1,np.sum(grid*grid,axis=0))): raise ValueError('Non-positive HAC kernel covariance')
    return np.maximum(0,variance)


def numeric_fit(x,y,controls,positions,grid_size,bandwidth):
    basis=control_basis(controls); xr=residualize(basis,x); yr=residualize(basis,y)
    sxx=float(xr@xr); syy=np.sum(yr*yr,axis=0)
    if sxx <= 1e-20: return None
    beta=xr@yr/sxx; error=yr-xr[:,None]*beta
    score=xr[:,None]*error/sxx
    variance=hac_variance(score,positions,grid_size,bandwidth)*len(x)/(len(x)-basis.rank-1)
    se=np.sqrt(variance); scale=np.sqrt(np.divide(sxx,syy,out=np.full_like(syy,np.nan),where=syy>1e-20))
    r=np.clip(beta*scale,-1,1); valid=syy>1e-20
    degrees=min(len(x)-basis.rank-1,max(1,len(x)//(bandwidth+1)-1))
    t=np.divide(abs(beta),se,out=np.where(abs(beta)>1e-14,np.inf,0.),where=se>1e-300)
    p=2*stats.t.sf(t,degrees)
    return dict(beta=beta,se=se,r=r,p=p,df=degrees,rank=basis.rank,xr=xr,yr=yr,valid=valid,r_se=se*scale)


def weighted_point(x,y,controls,weights):
    weights=np.asarray(weights,float); basis=control_basis(controls,weights); root=np.sqrt(weights)
    xr=residualize(basis,x*root); yr=residualize(basis,y*root[:,None])
    sxx=xr@xr; syy=np.sum(yr*yr,axis=0)
    if sxx<=1e-20: return np.full(y.shape[1],np.nan),np.full(y.shape[1],np.nan)
    beta=xr@yr/sxx
    scale=np.sqrt(np.divide(sxx,syy,out=np.full_like(syy,np.nan),where=syy>1e-20))
    return beta,np.clip(beta*scale,-1,1)


def lag_one(x,y,positions):
    consecutive=np.flatnonzero(np.diff(positions)==1)
    if len(consecutive)<4: return np.nan,np.full(y.shape[1],np.nan)
    ax=correlation(x[consecutive],x[consecutive+1])[0]
    a=y[consecutive]; b=y[consecutive+1]; a=a-a.mean(axis=0); b=b-b.mean(axis=0)
    denominator=np.sqrt(np.sum(a*a,axis=0)*np.sum(b*b,axis=0))
    ay=np.divide(np.sum(a*b,axis=0),denominator,out=np.full(y.shape[1],np.nan),where=denominator>1e-20)
    return ax,ay


def categorical_fit(x,y,controls,positions,grid_size,bandwidth):
    levels=np.unique(x); counts=np.array([np.sum(x==level) for level in levels])
    if len(levels)<2 or np.any(counts<c.CONFIG['minimum_category_periods']): return None,'sparse_category'
    design=np.column_stack([x==level for level in levels[1:]]).astype(float)
    basis=control_basis(controls); z=residualize(basis,design); yr=residualize(basis,y)
    gram=z.T@z
    if np.linalg.matrix_rank(gram,tol=1e-10)<len(levels)-1: return None,'constant_or_control_collinear'
    inverse=np.linalg.inv(gram); beta=inverse@z.T@yr; error=yr-z@beta; influence=z@inverse
    p=len(levels)-1; k=y.shape[1]; covariance=np.zeros((k,p,p))
    scores=influence[:,:,None]*error[:,None,:]
    grid=np.zeros((grid_size,p,k)); grid[positions]=scores
    covariance+=np.einsum('npk,nqk->kpq',grid,grid)
    for lag in range(1,min(bandwidth,grid_size-1)+1):
        cross=np.einsum('npk,nqk->kpq',grid[lag:],grid[:-lag])
        covariance+=(1-lag/(bandwidth+1))*(cross+cross.transpose(0,2,1))
    covariance*=len(x)/(len(x)-basis.rank-p)
    degrees=min(len(x)-basis.rank-p,max(1,len(x)//(bandwidth+1)-1))
    probabilities=np.full(k,np.nan)
    for j in range(k):
        if np.linalg.matrix_rank(covariance[j],tol=np.max(np.abs(covariance[j]))*1e-10)==p:
            wald=float(beta[:,j]@np.linalg.solve(covariance[j],beta[:,j])); probabilities[j]=stats.f.sf(max(0,wald)/p,p,degrees)
    eta=np.clip(1-np.sum(error*error,axis=0)/np.maximum(np.sum(yr*yr,axis=0),1e-300),0,1)
    return dict(p=probabilities,eta=eta,df=degrees,rank=basis.rank,category_df=p,beta=beta,
                se=np.sqrt(np.maximum(0,np.diagonal(covariance,axis1=1,axis2=2))).T,levels=levels),'ok'


def forecast(x,y,controls,train,valid,frequency,categorical=False):
    k=y.shape[1]; result=dict(status=0,r=np.full(k,np.nan),skill=np.full(k,np.nan),mae=np.full(k,np.nan))
    if train.sum()<c.CONFIG['minimum_training_periods'][frequency]: result['status']=1; return result
    if valid.sum()<c.CONFIG['minimum_validation_periods'][frequency]: result['status']=2; return result
    basis=control_basis(controls[train]); future,supported=basis.apply(controls[valid])
    if not supported.all(): result['status']=4; return result
    yt,yv=y[train],y[valid]; cy=basis.train.T@yt; baseline=future@cy; yr=yt-basis.train@cy
    if categorical:
        levels=np.unique(x[train])
        if len(levels)<2 or not set(x[valid])<=set(levels): result['status']=5; return result
        xt=np.column_stack([x[train]==v for v in levels[1:]]).astype(float)
        xv=np.column_stack([x[valid]==v for v in levels[1:]]).astype(float)
    else: xt=x[train,None]; xv=x[valid,None]
    cx=basis.train.T@xt; xr=xt-basis.train@cx; vr=xv-future@cx
    if np.linalg.matrix_rank(xr,tol=1e-10)<xr.shape[1]: result['status']=3; return result
    coefficient=linalg.lstsq(xr,yr,cond=1e-10,lapack_driver='gelsy')[0]
    prediction=baseline+vr@coefficient; base_loss=np.mean((yv-baseline)**2,axis=0)
    result['skill']=np.divide(base_loss-np.mean((yv-prediction)**2,axis=0),base_loss,out=np.full(k,np.nan),where=base_loss>1e-20)
    result['mae']=np.mean(abs(yv-prediction),axis=0)
    if not categorical: result['r']=correlation(vr[:,0],yv-baseline)
    return result


@dataclass
class Aligned:
    y: np.ndarray
    x: np.ndarray
    controls_time: np.ndarray
    controls_composition: np.ndarray
    weights: np.ndarray
    months_count: np.ndarray
    first_month: np.ndarray
    last_month: np.ndarray
    grid: np.ndarray
    names: list
    profiles: list
    frequency: str


class Workspace:
    def __init__(self):
        self.views=c.load(c.LOCAL/'views.pkl'); self.shares=c.load(c.LOCAL/'shares.pkl').to_numpy(float)
        self.external=c.load(c.LOCAL/'external.pkl'); self.months=pd.period_range(*c.CONFIG['months'],freq='M')
        self.cache=collections.OrderedDict(); self.stationarity={}

    def aligned(self,task):
        view=self.views[task['view_id']]; name=task['external']; definition=self.external['metadata'][name]
        frequency=definition['analysis_frequency']; lag=task['lag']; track=task['track']; keys=self.months-lag
        source=self.external[track][name].reindex(keys)
        ends=pd.to_datetime(self.external['ends'][name].reindex(keys),errors='coerce')
        x=source.to_numpy(); eligible=np.ones(len(keys),bool)
        if lag: eligible=np.asarray(ends<self.months.start_time)
        cache_key=(view['id'],frequency,lag,track,name if frequency in ['event','term'] else '')
        if cache_key in self.cache:
            saved=self.cache.pop(cache_key); self.cache[cache_key]=saved
            values,codes,allowed=saved
        else:
            if frequency in ['Q','A']:
                periods=keys.asfreq('Q-DEC' if frequency=='Q' else 'Y-DEC'); labels=periods.asi8
                actual_end=periods.end_time
                allowed=np.asarray(actual_end<self.months.start_time) if lag else np.ones(len(keys),bool)
                expected=3 if frequency=='Q' else 12
                if lag: expected=min(expected,lag)
            elif frequency=='term':
                labels=np.where(ends.notna(),np.asarray(ends.dt.year.fillna(0),int)//2,-9999)
                allowed=eligible & ends.notna().to_numpy(); expected=24 if not lag else max(1,min(24,lag-1))
            elif frequency=='event' and name=='US_NBER_LAST_ANNOUNCED_TURNING_POINT':
                labels=np.where(ends.notna(),pd.PeriodIndex(ends,freq='M').asi8,-9999)
                allowed=eligible & ends.notna().to_numpy(); expected=1
            else:
                labels=self.months.asi8; allowed=np.ones(len(keys),bool); expected=1
            meaningful=labels>-9999
            grid=np.arange(labels[meaningful].min(),labels[meaningful].max()+1) if meaningful.any() else np.array([0])
            codes=labels-grid[0]; codes=np.where(meaningful,codes,-1)
            y0=view['values'].to_numpy(float); n=len(grid); m=y0.shape[1]
            y=np.full((n,m),np.nan); counts=np.zeros((n,m),dtype=np.uint16); weights=np.full(n,np.nan)
            first=np.full(n,-1,dtype=int); last=np.full(n,-1,dtype=int)
            time=np.full((n,4),np.nan); composition=np.full((n,self.shares.shape[1]),np.nan)
            clock=np.column_stack([np.ones(len(keys)),np.arange(len(keys))/12,
                np.sin(2*np.pi*self.months.month/12),np.cos(2*np.pi*self.months.month/12)])
            for i in range(n):
                rows=(codes==i)&allowed
                if not rows.any(): continue
                count=np.isfinite(y0[rows]).sum(axis=0); total=np.nansum(y0[rows],axis=0)
                good=count>=max(1,int(np.ceil(expected*c.CONFIG['native_aggregation_minimum_fraction'])))
                y[i,good]=total[good]/count[good]; counts[i]=count
                weights[i]=np.nansum(view['counts'][rows]); first[i]=np.flatnonzero(rows)[0]; last[i]=np.flatnonzero(rows)[-1]
                time[i]=clock[rows].mean(axis=0); composition[i]=self.shares[rows].mean(axis=0)
            if track=='adjusted':
                y=np.vstack([np.full((1,m),np.nan),np.diff(y,axis=0)])
                composition=np.vstack([np.full((1,composition.shape[1]),np.nan),np.diff(composition,axis=0)])
                weights=np.r_[np.nan,np.minimum(weights[1:],weights[:-1])]
            # Raw estimates have an intercept only; adjusted controls retain time,
            # season and every declared composition direction via the SVD basis.
            if track=='raw': time=np.ones((n,1)); composition=np.empty((n,0))
            all_controls=np.column_stack([time,composition])
            profiles=[view['metadata'][n]['profile'] if view['scope']=='overall' else 'time' for n in view['values']]
            values=dict(y=y,controls_time=time,controls_composition=all_controls,weights=weights,months_count=counts,
                        first_month=first,last_month=last,grid=grid,names=list(view['values']),profiles=profiles,frequency=frequency)
            self.cache[cache_key]=(values,codes,allowed)
            while len(self.cache)>32: self.cache.popitem(last=False)
        aggregated=np.full(len(values['grid']),'',dtype=object) if definition['kind']=='categorical' else np.full(len(values['grid']),np.nan)
        for i in range(len(aggregated)):
            rows=(codes==i)&allowed&eligible
            observed=x[rows]
            if definition['kind']=='categorical': observed=np.array([v for v in observed if isinstance(v,str) and v],dtype=object)
            else: observed=np.asarray(observed,float); observed=observed[np.isfinite(observed)]
            if len(observed):
                if len(np.unique(observed))!=1: raise ValueError('External native-period values disagree within an analytical unit: '+name)
                aggregated[i]=observed[0]
        return Aligned(x=aggregated,**values)


def evaluate(aligned,task,stationarity_y=None,stationarity_x=np.nan):
    a=aligned; output=blank(len(a.names)); category=task.get('external_kind')=='categorical'
    x_ok=np.array([isinstance(v,str) and bool(v) for v in a.x]) if category else np.isfinite(a.x.astype(float))
    groups=collections.defaultdict(list)
    for j,profile in enumerate(a.profiles):
        controls=a.controls_composition if profile=='composition' else a.controls_time
        mask=x_ok & np.isfinite(a.y[:,j]) & np.isfinite(controls).all(axis=1) & np.isfinite(a.weights) & (a.weights>0)
        groups[(profile,np.packbits(mask).tobytes())].append(j)
    contrasts=[]; bandwidth=c.CONFIG['hac_lags'][a.frequency]
    for (profile,_),columns in groups.items():
        controls=a.controls_composition if profile=='composition' else a.controls_time
        mask=x_ok & np.isfinite(a.y[:,columns[0]]) & np.isfinite(controls).all(axis=1) & np.isfinite(a.weights) & (a.weights>0)
        positions=np.flatnonzero(mask); n=len(positions); output['n'][columns]=n; output['hac_lags'][columns]=bandwidth
        output['stationarity_x'][columns]=stationarity_x
        if stationarity_y is not None: output['stationarity_y'][columns]=np.asarray(stationarity_y)[columns]
        if n:
            output['n_months'][columns]=a.months_count[mask][:,columns].sum(axis=0)
            output['first_month'][columns]=a.first_month[mask].min(); output['last_month'][columns]=a.last_month[mask].max()
        if n<c.CONFIG['minimum_native'][a.frequency]: continue
        C=controls[mask]; Y=a.y[mask][:,columns]; X=a.x[mask]; basis=control_basis(C)
        output['control_rank'][columns]=basis.rank
        dimension=len(np.unique(X))-1 if category else 1
        if n-basis.rank-dimension<c.CONFIG['minimum_residual_df']: output['status'][columns]=2; continue
        if n//(bandwidth+1)<c.CONFIG['minimum_hac_blocks']: output['status'][columns]=3; continue
        if category:
            fitted,status=categorical_fit(X,Y,C,positions,len(a.grid),bandwidth)
            if fitted is None: output['status'][columns]=STATUS.index(status); continue
            output['status'][columns]=np.where(np.isfinite(fitted['p']),0,6); output['p'][columns]=fitted['p']
            output['eta_squared'][columns]=fitted['eta']; output['category_df'][columns]=fitted['category_df']; output['df'][columns]=fitted['df']
            quantile=stats.t.ppf(.975,fitted['df'])
            for k,j in enumerate(columns):
                for level,beta,se in zip(fitted['levels'][1:],fitted['beta'][:,k],fitted['se'][:,k]):
                    contrasts.append(dict(music_index=j,level=str(level),reference=str(fitted['levels'][0]),effect=float(beta),
                        ci_low=float(beta-quantile*se),ci_high=float(beta+quantile*se),interpretation='Descriptive contrast interval; only the omnibus test enters the hypothesis family'))
        else:
            X=X.astype(float)
            if len(np.unique(X))==2 and min(np.unique(X,return_counts=True)[1])<c.CONFIG['minimum_binary_periods']:
                output['status'][columns]=5; continue
            fitted=numeric_fit(X,Y,C,positions,len(a.grid),bandwidth)
            ranked=numeric_fit(stats.rankdata(X),stats.rankdata(Y,axis=0),C,positions,len(a.grid),bandwidth)
            if fitted is None or ranked is None: output['status'][columns]=4; continue
            output['status'][columns]=np.where(fitted['valid'] & ranked['valid'],0,4)
            for field,key in [('slope','beta'),('se','se'),('r','r'),('p','p'),('df','df')]: output[field][columns]=fitted[key]
            output['rho'][columns]=ranked['r']; output['p_rank'][columns]=ranked['p']; output['rho_se'][columns]=ranked['r_se']
            if task['track']=='raw': output['intercept'][columns]=Y.mean(axis=0)-fitted['beta']*X.mean()
            slope,r=weighted_point(X,Y,C,a.weights[mask]); output['slope_song_weighted'][columns]=slope; output['r_song_weighted'][columns]=r
            ax,ay=lag_one(fitted['xr'],fitted['yr'],positions); output['acf_x'][columns]=ax; output['acf_y'][columns]=ay
            output['trend_x'][columns]=correlation(positions.astype(float),X)[0]; output['trend_y'][columns]=correlation(positions.astype(float),Y)
            product=ax*ay; output['effective_n_ar1_diagnostic'][columns]=np.clip(n*(1-product)/np.maximum(1+product,1e-8),1,n)
        # A missing/failed stationarity diagnostic is an explicit inference gate,
        # not an exclusion from the candidate catalog or descriptive estimates.
        sy=output['stationarity_y'][columns]
        stationary=(sy<=c.CONFIG['stationarity_threshold']) & (category or stationarity_x<=c.CONFIG['stationarity_threshold'])
        output['inferential'][columns]=(stationary & (output['status'][columns]==0)).astype('u1')
        for fold,(start,end) in enumerate(c.CONFIG['validation_periods']):
            start_idx=(pd.Period(start,'M')-pd.Period(c.CONFIG['months'][0],'M')).n
            end_idx=(pd.Period(end,'M')-pd.Period(c.CONFIG['months'][0],'M')).n
            train=a.last_month[mask]<start_idx-c.CONFIG['temporal_embargo_months']
            valid=(a.first_month[mask]>=start_idx)&(a.last_month[mask]<end_idx)
            prediction=forecast(X,Y,C,train,valid,a.frequency,category)
            output['fold_status'][columns,fold]=prediction['status']
            for field,key in [('fold_r','r'),('fold_skill','skill'),('fold_mae','mae')]: output[field][columns,fold]=prediction[key]
    return output,contrasts


def by_adjust(pvalues):
    p=np.asarray(pvalues,float)
    if np.any(~np.isfinite(p)) or np.any((p<0)|(p>1)): raise ValueError('BY requires every attempted slot, with invalid slots set to one')
    n=len(p)
    if not n: return p.copy()
    harmonic=float(np.sum(1/np.arange(1,n+1,dtype=float)))
    order=np.argsort(p,kind='stable'); scaled=p[order]*n*harmonic/np.arange(1,n+1)
    ranked=np.minimum.accumulate(scaled[::-1])[::-1]; result=np.empty(n); result[order]=np.minimum(1,ranked)
    return result
