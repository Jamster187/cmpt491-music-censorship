"""Post-hoc interpretation and artist-credit sensitivity; never adds search families."""
from __future__ import annotations
from collections import Counter
import numpy as np
import pandas as pd
from scipy import stats
from threadpoolctl import threadpool_limits
import relationship_discovery as engine
import relationship_discovery_spec as spec
import relationship_discovery_models as models
import relationship_discovery_stats as inference


def source_domain(name):
    value=spec.domain(name)
    return 'lyrics' if value.startswith('lyrical_') else value


def priority_cross(row):
    return row['category'].startswith('C') and source_domain(row['target'])!=source_domain(row['predictors'][0])


def utility_tier(row):
    return bool(row.get('evaluated_periods')==4 and (row.get('r2') or 0)>0 and
        (row.get('skill') or 0)>0 and row.get('stability_fraction')==1 and (row.get('ci_low') or 0)>0)


def predictive_key(row):
    return (not utility_tier(row),-(row.get('worst_period_relative_improvement') if row.get('worst_period_relative_improvement') is not None else -np.inf),
        -(row.get('ci_low') if row.get('ci_low') is not None else -np.inf),row['candidate_id'])


def pair_key(row):
    # Used only within a named effect-type stratum, never across scales.
    return (row.get('q_by_global',1)>.05,-(row.get('stability_fraction') or 0),-abs(row.get('effect') or 0),row['candidate_id'])


def rank_views(rows):
    eligible=[r for r in rows if not r['category'].startswith('A')]
    nonlinear=sorted([r for r in eligible if r['family']=='nonlinear'],key=predictive_key)
    genre=sorted([r for r in eligible if r['family']=='genre_interaction'],key=predictive_key)
    cross=[r for r in eligible if priority_cross(r)]
    categorical=lambda r:any(spec.kind(n)=='categorical' for n in [r['target'],*r['predictors']])
    num=sorted([r for r in cross if r['family']=='pairwise' and not categorical(r)],key=pair_key)
    cat=sorted([r for r in cross if r['family']=='pairwise' and categorical(r)],key=lambda r:(r.get('status')!='ok',r.get('effect_name',''),*pair_key(r)))
    pred=sorted([r for r in cross if r['family']!='pairwise'],key=predictive_key)
    # Fixed presentation coverage; the three blocks have no common effect-size scale.
    shortlist=num[:5]+cat[:2]+pred[:3]
    return dict(nonlinear=nonlinear,genre_interaction=genre,cross_numeric=num,cross_categorical=cat,cross_predictive=pred,cross_shortlist=shortlist)


def reversal_records(rows):
    records=[]
    for row in rows:
        if row['family']!='genre_interaction':continue
        for detail in row.get('diagnostics',[]):
            d=detail.get('conditional_correlations',{});pooled=d.get('marginal_spearman');partial=d.get('partial_spearman')
            if pooled is None or partial is None:continue
            adequate=[g for g in d.get('subgroups',[]) if g.get('adequate') and g.get('spearman') is not None]
            lo=min(adequate,key=lambda g:g['spearman']) if adequate else None
            hi=max(adequate,key=lambda g:g['spearman']) if adequate else None
            reversal=abs(pooled)>=.1 and abs(partial)>=.05 and pooled*partial<0
            attenuation=abs(pooled)>=.1 and abs(partial)<=.25*abs(pooled)
            opposed=bool(lo and lo['spearman']<=-.1 and hi['spearman']>=.1)
            records.append(dict(candidate_id=row['candidate_id'],target=row['target'],predictor=row['predictors'][0],category=row['category'],
                priority_cross_domain=priority_cross(row),period=detail['period'],n_complete=d.get('n_complete'),
                pooled_rho=pooled,genre_adjusted_rho=partial,sign_reversal=bool(reversal),attenuation=bool(attenuation),
                opposed_genre_signs=opposed,minimum_genre=lo['group'] if lo else None,minimum_genre_rho=lo['spearman'] if lo else None,
                minimum_genre_n=lo['n'] if lo else None,maximum_genre=hi['group'] if hi else None,
                maximum_genre_rho=hi['spearman'] if hi else None,maximum_genre_n=hi['n'] if hi else None,
                parent_model_q_by_global=row['q_by_global'],descriptive_only=True))
    return records


def period_sign_records(rows):
    """Descriptive sign changes within the already approved outer evaluations."""
    records=[]
    for row in rows:
        if row['family']!='genre_interaction':continue
        values=[dict(period=d['period'],rho=d['conditional_correlations']['marginal_spearman'],
            n=d['conditional_correlations']['n_complete']) for d in row.get('diagnostics',[])
            if d.get('conditional_correlations',{}).get('marginal_spearman') is not None
            and d['conditional_correlations'].get('n_complete',0)>=200]
        low=min(values,key=lambda v:v['rho']) if values else None
        high=max(values,key=lambda v:v['rho']) if values else None
        records.append(dict(candidate_id=row['candidate_id'],target=row['target'],predictor=row['predictors'][0],
            category=row['category'],priority_cross_domain=priority_cross(row),periods=values,
            period_sign_reversal=bool(low and low['rho']<=-.1 and high['rho']>=.1),
            minimum_period=low['period'] if low else None,minimum_rho=low['rho'] if low else None,
            maximum_period=high['period'] if high else None,maximum_rho=high['rho'] if high else None,
            descriptive_only=True))
    return records


def replay_predictions(frame,masks,row):
    pieces=[];slopes=[];fit_calls=0
    for fold in row.get('folds',[]):
        if fold['status']!='ok':continue
        train,test=models.partitions(frame,masks,tuple(fold['period']),row['target'])
        x=row['predictors'][0];y=row['target']
        if row['family']=='nonlinear':
            base=models.Univariate(x,'linear').fit(train,y);fit_calls+=1
            model=base if fold['selected_method']=='linear' else models.Univariate(x,fold['selected_method']).fit(train,y)
            fit_calls+=int(fold['selected_method']!='linear')
        else:
            base=models.Interaction(row,False).fit(train,y);model=models.Interaction(row,True).fit(train,y);fit_calls+=2
        pred=model.predict(test);baseline=base.predict(test);actual=test[y].to_numpy(float)
        mean=float(train[y].mean());median=float(train[y].median())
        for got,expected in [(pred,fold['metrics']),(baseline,fold['comparison_metrics'])]:
            measured=models.metric_bundle(actual,got,np.full(len(test),mean),np.full(len(test),median))
            for metric in ('r2','mse','mae','rmse','skill'):
                np.testing.assert_allclose(measured[metric],expected[metric],atol=1e-9,rtol=2e-11)
        f=test[['song_id','artist','debut_year','primary_genre','_hash']].copy()
        f['actual']=actual;f['predicted']=pred;f['comparison']=baseline
        f['normalized_loss_gain']=((actual-baseline)**2-(actual-pred)**2)/train[y].var(ddof=0)
        f['period_start']=fold['period'][0];f['seen_artist_in_training']=test.artist.isin(set(train.artist))
        pieces.append(f)
        if row['family']=='genre_interaction':
            # Fitted raw-unit derivative: only x varies, at two finite observed values.
            low,high=train[x].dropna().quantile([.25,.75]).tolist()
            if high==low:low,high=train[x].dropna().min(),train[x].dropna().max()
            if high>low:
                for genre in spec.GENRES:
                    query=pd.DataFrame({x:[low,high],'primary_genre':[genre,genre]})
                    slope=float(np.diff(model.predict(query))[0]/(high-low))
                    additive=float(np.diff(base.predict(query))[0]/(high-low))
                    evaluation=test.loc[test.primary_genre.eq(genre)]
                    slopes.append(dict(period=fold['period'],genre=genre,slope=slope,additive_slope=additive,
                        train_supported=genre in model.supported,n_test=len(evaluation),years=int(evaluation.debut_year.nunique()),
                        evaluation_adequate=len(evaluation)>=100 and evaluation.debut_year.nunique()>=5))
    return pd.concat(pieces,ignore_index=True),slopes,fit_calls


def artist_prediction_interval(frame,key,repeats=499):
    artists,codes=np.unique(frame.artist.astype(str),return_inverse=True)
    _,blocks=np.unique(frame.debut_year.to_numpy(int)//2,return_inverse=True)
    shape=(len(artists),int(blocks.max()+1));sums=np.zeros(shape);counts=np.zeros(shape)
    np.add.at(sums,(codes,blocks),frame.normalized_loss_gain.to_numpy(float));np.add.at(counts,(codes,blocks),1)
    rng=inference.rng_for(key,'artist-credit-sensitivity');values=[];missing_blocks=0
    for _ in range(repeats):
        w=np.bincount(rng.integers(len(artists),size=len(artists)),minlength=len(artists))
        numerator=w@sums;denominator=w@counts
        missing_blocks+=bool(np.any(denominator==0))
        values.append(float(np.mean(numerator[denominator>0]/denominator[denominator>0])))
    point=float(np.mean(sums.sum(axis=0)/counts.sum(axis=0)))
    return dict(effect=point,interval=np.quantile(values,[.025,.975]).tolist(),artist_credits=len(artists),
        largest_credit_song_share=float(np.bincount(codes).max()/len(codes)),
        evaluation_songs_seen_artist_fraction=float(frame.seen_artist_in_training.mean()),replicates=repeats,
        replicates_missing_calendar_blocks=missing_blocks)


def weighted_correlation(x,y,w):
    total=w.sum();mx=float(w@x/total);my=float(w@y/total)
    xx=float(w@((x-mx)**2));yy=float(w@((y-my)**2));xy=float(w@((x-mx)*(y-my)))
    return xy/np.sqrt(xx*yy) if xx>0 and yy>0 else 0.


def weighted_eta(groups,values,w):
    counts=np.bincount(groups,weights=w);sums=np.bincount(groups,weights=w*values)
    total=float(w.sum());mean=float(w@values/total);den=float(w@((values-mean)**2));keep=counts>0
    return float(np.sum(counts[keep]*(sums[keep]/counts[keep]-mean)**2)/den) if den else 0.


def weighted_v(x,y,w):
    ny=int(y.max())+1
    table=np.bincount(x*ny+y,weights=w,minlength=(int(x.max())+1)*ny).reshape(-1,ny)
    table=table[table.sum(axis=1)>0][:,table.sum(axis=0)>0]
    n=table.sum();r,c=table.shape
    if min(r,c)<2:return 0.
    expected=np.outer(table.sum(axis=1),table.sum(axis=0))/n
    phi=max(0.,float(np.sum((table-expected)**2/expected))/n-(r-1)*(c-1)/(n-1))
    denominator=min(r-1-(r-1)**2/(n-1),c-1-(c-1)**2/(n-1))
    return float(np.sqrt(phi/denominator)) if denominator>0 else 0.


def artist_pair_interval(frame,row,repeats=499):
    xname=row['predictors'][0];yname=row['target'];f=frame.loc[frame.last_iso.lt('2026-01-01')].dropna(subset=[xname,yname])
    xcat=spec.kind(xname)=='categorical';ycat=spec.kind(yname)=='categorical'
    x=pd.factorize(f[xname],sort=True)[0] if xcat else f[xname].to_numpy(float)
    y=pd.factorize(f[yname],sort=True)[0] if ycat else f[yname].to_numpy(float)
    if not xcat and not ycat:x=stats.rankdata(x);y=stats.rankdata(y)
    artists,codes=np.unique(f.artist.astype(str),return_inverse=True);rng=inference.rng_for(row['candidate_id'],'artist-credit-sensitivity');draws=[]
    def measure(w):
        if xcat and ycat:return weighted_v(x,y,w)
        if xcat:return weighted_eta(x,y,w)
        if ycat:return weighted_eta(y,x,w)
        return weighted_correlation(x,y,w)
    point=measure(np.ones(len(f)))
    np.testing.assert_allclose(point,row['effect'],rtol=1e-11,atol=1e-12)
    for _ in range(repeats):
        cluster_w=np.bincount(rng.integers(len(artists),size=len(artists)),minlength=len(artists))
        draws.append(measure(cluster_w[codes]))
    return dict(effect=point,interval=np.quantile(draws,[.025,.975]).tolist(),artist_credits=len(artists),
        largest_credit_song_share=float(np.bincount(codes).max()/len(codes)),replicates=repeats)


def artist_sensitivity(rows,frame,masks):
    output=[];plots={};fit_calls=0
    with threadpool_limits(limits=1):
        for row in rows:
            if row['status']!='ok':continue
            if row['family']=='pairwise':record=artist_pair_interval(frame,row)
            else:
                f,slopes,count=replay_predictions(frame,masks,row);fit_calls+=count
                record=artist_prediction_interval(f,row['candidate_id'])
                np.testing.assert_allclose(record['effect'],row['effect'],atol=1e-10,rtol=1e-10)
                take=f.sort_values('_hash',kind='stable').head(1200)
                plots[row['candidate_id']]=dict(artist_slopes=slopes,
                    actual_predicted=take[['actual','predicted','comparison','period_start']].to_dict('records'))
            output.append(dict(candidate_id=row['candidate_id'],family=row['family'],target=row['target'],predictor=row['predictors'][0],
                **record,descriptive_only=True,warning='Post-hoc exact artist-credit cluster sensitivity; fixed model/ranks; collaboration aliases unresolved; temporal and artist intervals are separate; no new significance claim'))
    return output,plots,fit_calls
