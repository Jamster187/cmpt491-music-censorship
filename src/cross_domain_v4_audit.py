"""Exact streaming V4 candidate universe and chronological support audit."""
from __future__ import annotations
from collections import Counter
from itertools import combinations
from functools import lru_cache
import argparse,json,math,pickle,time
import numpy as np
import pandas as pd
import cross_domain_v4_common as c
from cross_domain_v4_data import IDENTITIES

POPULATIONS=('song','monthly','genre_month')
def registry(pop):
 music=c.read_json(c.LOCAL/'music_registry.json');external=c.read_json(c.LOCAL/'external_registry.json');frame=c.load_frame(pop+'.pkl');r={}
 for name,d in music.items():
  if all(x in frame for x in d['source_columns']):r[name]=dict(d,lag=0,base=name,target_eligible=d['kind']=='numeric')
 if pop=='genre_month':
  r['primary_genre']=dict(name='primary_genre',source_columns=['primary_genre'],domain='genre',family='genre_annotation',source=['billboard','musicbrainz','wikidata','genre_model'],dependencies=[],frequency='M',units='category',definition='Frozen primary genre',availability='retrospective',public=True,origin='music',kind='categorical',transformation='genre_nuisance_in_adjusted_track',lag=0,base='primary_genre',target_eligible=False)
 for sid,d in external.items():
  for lag in c.LAGS:
   name='external__'+sid+(f'__lag{lag}' if lag else '')
   r[name]=dict(d,name=name,base=sid,lag=lag,source_columns=[sid],target_eligible=lag==0 and d['kind']=='numeric')
 return dict(sorted(r.items()))
def numeric_view(frame,reg,track):
 ext=c.load_frame('external_'+('adjusted' if track=='adjusted' else 'raw')+'.pkl');end=c.load_frame('external_period_end.pkl')
 months=pd.PeriodIndex(frame.month,freq='M');cols={}
 for name,d in reg.items():
  if d['origin']=='external':
   keys=months-d['lag'];series=ext[d['base']].reindex(keys)
   if d['kind']=='numeric':v=series.to_numpy(float)
   else:
    codes,_=pd.factorize(series.fillna(''));v=codes.astype(float);v[series.isna().to_numpy()]=np.nan
   if d['lag']:
    dates=pd.to_datetime(end[d['base']].reindex(keys).to_numpy(),errors='coerce')
    # A positive lag must actually precede target month. Annual and quarterly
    # context does not turn an unfinished reference period into a past value.
    v=np.where(dates<months.start_time,v,np.nan)
   cols[name]=v
  elif d['kind'] in ['numeric','block']:cols[name]=pd.to_numeric(frame[d['source_columns'][0]],errors='coerce').to_numpy(float)
  else:
   s=frame[d['source_columns'][0]];codes,_=pd.factorize(s.fillna(''));a=codes.astype(float);a[s.isna().to_numpy()|s.eq('').to_numpy()]=np.nan;cols[name]=a
 return pd.DataFrame(cols,index=frame.index)
def boundaries(months):
 lo=pd.Period(min(months),'M');hi=pd.Period(max(months),'M');n=hi.ordinal-lo.ordinal+1
 return [str(lo+int(n*f)) for f in c.CONFIG['validation_fraction_boundaries'][:-1]]+[str(hi+1)]
def masks(frame,target_values,bounds,fold):
 start,end=bounds[fold],bounds[fold+1];cutoff=str(pd.Period(start,'M')-c.CONFIG['embargo_months'])
 observed=np.isfinite(target_values);tr=frame.month.lt(cutoff).to_numpy()&observed;va=(frame.month.ge(start)&frame.month.lt(end)).to_numpy()&observed
 if 'last_chart_date' in frame:
  dates=frame['label_available_date'] if 'label_available_date' in frame else frame.last_chart_date
  tr &= dates.lt(cutoff+'-01').to_numpy();va &= dates.lt(end+'-01').to_numpy()
 return tr,va

def identity_sets(reg,track):
 result=set()
 for identity in IDENTITIES:
  external=all(x.startswith(('US_','FF_')) for x in identity)
  if external and track=='adjusted':
   definitions=[reg.get('external__'+x,{}) for x in identity];rules={d.get('transformation') for d in definitions}
   if not (len(rules)==1 and next(iter(rules)) in {'identity_rate_change_or_event','first_difference_native_period'}):continue
  for lag in (c.LAGS if external else [0]):
   values=[('external__'+x+(f'__lag{lag}' if lag else '')) if external else x for x in identity]
   if set(values)<=set(reg):result.add(tuple(sorted(values)))
 # Native percent growth from current and earlier levels is exactly invertible.
 for name,r in reg.items():
  if r['origin']!='external' or len(r['dependencies'])!=1:continue
  base=r['base'];look=12 if base.endswith(('YOY',)) else 1 if base.endswith(('MOM',)) else None
  if look is None:continue
  lag=r['lag'];parent=r['dependencies'][0]
  vars=[name,'external__'+parent+(f'__lag{lag}' if lag else ''),'external__'+parent+f'__lag{lag+look}']
  if set(vars)<=set(reg) and track=='raw':result.add(tuple(sorted(vars)))
 return sorted(result)
def constraints(target,names,reg,track):
 allowed=set(names);allowed.discard(target);t=reg[target]
 if track=='adjusted':
  allowed.discard('primary_genre')
  if not target.startswith('genre_share__'):allowed={n for n in allowed if not n.startswith('genre_share__')}
 if t['origin']=='external':
  width={'A':12,'Q':3,'M':1,'W':1,'D':1,'event':1}.get(t['frequency'],1)
  allowed={n for n in allowed if not (reg[n]['origin']=='external' and reg[n]['base']==t['base'] and reg[n]['lag']<width)}
 # A vector containing the outcome is an exact target-dependent predictor.
 for n in list(allowed):
  if target in reg[n]['source_columns'] or (reg[n]['kind']=='block' and target in reg[n]['source_columns']):allowed.discard(n)
 edges=set();triples=set()
 for identity in identity_sets(reg,track):
  vertices=set(identity)
  if target in vertices:
   pair=vertices-{target}
   if pair<=allowed and len(pair)==2:edges.add(tuple(sorted(pair)))
  elif vertices<=allowed and len(vertices)==3:triples.add(tuple(sorted(vertices)))
 return sorted(allowed),edges,triples

def count_combinations(names,edges=(),triples=()):
 """Exact independent sets of sizes <=3 by inclusion-exclusion; no screening."""
 nodes=set(names);edges={tuple(sorted(e)) for e in edges if set(e)<=nodes};adj={n:set() for n in nodes}
 for a,b in edges:adj[a].add(b);adj[b].add(a)
 triangles=sum(len(adj[a]&adj[b]) for a,b in edges)//3
 wedges=sum(math.comb(len(neighbors),2) for neighbors in adj.values())
 n=len(nodes);k1=n;k2=math.comb(n,2)-len(edges)
 k3=math.comb(n,3)-len(edges)*(n-2)+wedges-triangles if n>=3 else 0
 k3-=sum(set(t)<=nodes and not any(set(e)<=set(t) for e in edges) for t in set(tuple(sorted(t)) for t in triples))
 if min(k1,k2,k3)<0:raise ValueError('Negative combinatorial count')
 return {1:k1,2:k2,3:k3}
def enumerate_combinations(names,edges=(),triples=()):
 edge={frozenset(x) for x in edges};triple={frozenset(x) for x in triples}
 for k in [1,2,3]:
  for combo in combinations(sorted(names),k):
   s=frozenset(combo)
   if s in triple or any(frozenset(p) in edge for p in combinations(combo,2)):continue
   yield combo

def category_subsets(target,names,reg):
 t=reg[target];music={n for n in names if reg[n]['origin']=='music'};ext=set(names)-music
 cross={n for n in names if reg[n]['domain']!=t['domain']}
 strict={n for n in cross if not set(reg[n]['source'])&set(t['source'])}
 return dict(unrestricted=set(names),cross_domain=cross,provenance_separated=strict,within_music=music if t['origin']=='music' else set(),within_external=ext if t['origin']=='external' else set())

def audit():
 started=time.time();inventories=[];spaces=[];tasks=[];coverage=[];summary={};task_id=0
 for pop in POPULATIONS:
  frame=c.load_frame(pop+'.pkl');reg=registry(pop);c.write_json(c.LOCAL/(pop+'_registry.json'),reg)
  scopes=['pooled']+(sorted(frame.primary_genre.unique()) if pop=='genre_month' else [])
  pop_summary={}
  for track in ['raw','adjusted']:
   values=numeric_view(frame,reg,track);names=list(reg);matrix=values.to_numpy(float);finite=np.isfinite(matrix)
   for name,d in reg.items():
    a=values[name];good=a.notna();inventories.append(dict(population=pop,track=track,variable=name,**{k:json.dumps(d[k]) if isinstance(d[k],(list,dict)) else d[k] for k in ['kind','domain','family','source','dependencies','frequency','units','availability','public','origin','definition','transformation','base','lag']},
     source_rows=len(frame),nonnull_rows=int(good.sum()),missing_fraction=float(1-good.mean()),first_month=frame.loc[good,'month'].min() if good.any() else '',last_month=frame.loc[good,'month'].max() if good.any() else '',target_candidate=bool(d['target_eligible']),predictor_candidate=bool(good.any()),
     leakage_risk='Retrospective source/target timing; lag alone does not establish availability' if d['origin']=='external' else 'Current measurement; label and historical metadata availability must not be treated as original release evidence'))
   for scope in scopes:
    ix=np.arange(len(frame)) if scope=='pooled' else np.flatnonzero(frame.primary_genre.eq(scope));f=frame.iloc[ix].reset_index(drop=True);x=matrix[ix];fin=finite[ix];support_cache={};valid_targets=0;predictor_union=set();total=0
    for col,target in enumerate(names):
     if not reg[target]['target_eligible']:continue
     y=x[:,col];obs=np.isfinite(y)
     if not obs.any():continue
     bounds=boundaries(f.loc[obs,'month']);folds=[];okay=True;reason='';predictors=set(names)
     for fold in range(4):
      tr,va=masks(f,y,bounds,fold)
      nt,nv=int(tr.sum()),int(va.sum());tm=f.loc[tr,'month'].nunique();vm=f.loc[va,'month'].nunique()
      valid=nt>=c.CONFIG['minimum_training_rows'] and nv>=c.CONFIG['minimum_validation_rows'] and tm>=c.CONFIG['minimum_training_months'] and vm>=c.CONFIG['minimum_validation_months']
      # Evaluation outcomes are never inspected for variation or model selection.
      if fold<3:valid=valid and (np.ptp(y[tr])>1e-12 if nt else False)
      if not valid:okay=False;reason='Insufficient chronological rows/months or constant training target';break
      folds.append(dict(fold=fold,start=bounds[fold],end=bounds[fold+1],n_train=nt,n_validation=nv,train_months=int(tm),validation_months=int(vm)))
      if fold<3:
       key=np.packbits(tr).tobytes()
       if key not in support_cache:
        a=x[tr];nonnull=fin[tr].sum(axis=0);minimum=np.where(np.isfinite(a),a,np.inf).min(axis=0);maximum=np.where(np.isfinite(a),a,-np.inf).max(axis=0)
        # At least six distinct observed training calendar months for each predictor.
        bymonth=pd.DataFrame(fin[tr],index=f.loc[tr,'month']).groupby(level=0).any().sum(axis=0).to_numpy()
        support_cache[key]=(nonnull>=c.CONFIG['minimum_predictor_observed_training_rows'])&(bymonth>=c.CONFIG['minimum_predictor_observed_training_months'])&(maximum>minimum+1e-12)
       predictors &= {n for n,yes in zip(names,support_cache[key]) if yes}
     coverage.append(dict(population=pop,track=track,scope=scope,target=target,target_supported=okay,reason=reason,boundaries=json.dumps(bounds),target_observed_rows=int(obs.sum())))
     if not okay:continue
     eligible,edges,triples=constraints(target,predictors,reg,track)
     if not eligible:continue
     counts=count_combinations(eligible,edges,triples);subsets=category_subsets(target,eligible,reg);allcounts={k:count_combinations(v,edges,triples) for k,v in subsets.items()}
     opposite='within_music' if reg[target]['origin']=='music' else 'within_external'
     allcounts['music_external']={k:counts[k]-allcounts[opposite][k] for k in [1,2,3]}
     valid_targets+=1;predictor_union.update(eligible);total+=sum(counts.values())
     tasks.append(dict(task_id=task_id,population=pop,track=track,scope=scope,target=target,predictors=eligible,edges=sorted(edges),triples=sorted(triples),bounds=bounds,folds=folds,counts=counts));task_id+=1
     for category,co in allcounts.items():
      for k,n in co.items():spaces.append(dict(task_id=task_id-1,population=pop,track=track,scope=scope,target=target,category=category,predictors=len(eligible),k=k,combinations=n,planned_fits=4*n))
    pop_summary[track+'::'+scope]=dict(targets=valid_targets,predictors=len(predictor_union),combinations=total,planned_fits=4*total)
    print(json.dumps(dict(stage='audit',population=pop,track=track,scope=scope,**pop_summary[track+'::'+scope])),flush=True)
   del values,matrix,finite
  summary[pop]=pop_summary
 c.atomic(c.LOCAL/'tasks.pkl',pickle.dumps(tasks,protocol=4));c.write_csv(c.PUBLIC/'variable_inventory.csv',inventories);c.write_csv(c.PUBLIC/'search_space.csv',spaces);c.write_csv(c.PUBLIC/'target_coverage.csv',coverage)
 n=sum(sum(t['counts'].values()) for t in tasks)
 out=dict(status='AUDITED',summary=summary,target_tasks=len(tasks),structurally_eligible_combinations=n,planned_fits=4*n,folds=4,core_metric_payload_bytes=n*4*18,
  storage_definition='Per model/fold float64 MSE + float64 MAE + uint16 rank/status = 18 bytes; other metrics losslessly derived from fixed fold constants. Catalog/rankings/checkpoints extra.',
  dependency_policy='Explicit algebraic identities only; conceptual overlap retained and labelled. Unsupported or rank-deficient numerical fits remain attempted statuses, never successful discoveries.',
  seconds=time.time()-started,task_catalog_sha256=c.sha(c.LOCAL/'tasks.pkl'))
 c.write_json(c.PUBLIC/'audit.json',out);print(json.dumps({k:v for k,v in out.items() if k!='summary'},indent=2),flush=True)
if __name__=='__main__':audit()
