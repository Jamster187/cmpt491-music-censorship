"""Deterministic representative OLS pilot, restart checks and mandatory budget gate."""
from __future__ import annotations
import os
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[key]='1'
import argparse,json,pickle,resource,shutil,sqlite3,sys,time
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd
from scipy import sparse
from threadpoolctl import threadpool_limits
import cross_domain_v4_common as c
import cross_domain_v4_audit as audit
from regression_core import Fold,metrics

class Encoder:
 def __init__(self,registry):self.registry=registry;self.state={};self.groups={}
 def raw(self,frame,name,state):
  d=self.registry[name];fields=d['source_columns'] if d['origin']=='music' and d['kind']=='block' else [name]
  if d['kind'] in ['numeric','block']:
   a=frame[fields].to_numpy(float);return np.column_stack([np.where(np.isfinite(a),a,state['median']),(~np.isfinite(a)).any(axis=1)]).astype(float)
  vals=frame[name].fillna('').astype(str)
  if d['kind']=='multilabel':
   vals=vals.map(lambda s:json.loads(s) if s else [])
   return np.asarray([[float(v in values) for v in state['levels']] for values in vals],float).reshape(len(frame),len(state['levels']))
  return np.asarray([[float(value==v) for v in state['levels'][1:]]+[float(value=='')] for value in vals],float)
 def fit(self,frame,names):
  for n in names:
   d=self.registry[n];fields=d['source_columns'] if d['kind']=='block' and d['origin']=='music' else [n];s={}
   if d['kind'] in ['numeric','block']:
    a=frame[fields].to_numpy(float);s['median']=[float(np.median(col[np.isfinite(col)])) if np.isfinite(col).any() else 0. for col in a.T]
   elif d['kind']=='multilabel':s['levels']=sorted({v for text in frame[n].fillna('') if text for v in json.loads(text)})
   else:s['levels']=sorted(set(frame[n].fillna('').astype(str))- {''})
   a=self.raw(frame,n,s);keep=np.flatnonzero(np.ptp(a,axis=0)>1e-12);s.update(keep=keep.tolist(),mean=a[:,keep].mean(axis=0),std=a[:,keep].std(axis=0));self.state[n]=s
  return self
 def transform(self,frame):
  out=[np.ones((len(frame),1))];position=1;self.groups={}
  for n,s in self.state.items():
   a=self.raw(frame,n,s)[:,s['keep']];a=(a-s['mean'])/s['std'];self.groups[n]=list(range(position,position+a.shape[1]));position+=a.shape[1];out.append(a)
  return np.ascontiguousarray(np.column_stack(out))
 def unsupported(self,frame):
  return {n:int((~frame[n].fillna('').astype(str).isin(s['levels'])).sum()) for n,s in self.state.items() if self.registry[n]['kind']=='categorical'}

@lru_cache(maxsize=3)
def population(name):return c.load_frame(name+'.pkl')
@lru_cache(maxsize=2)
def external(track):return c.load_frame('external_'+('adjusted' if track=='adjusted' else 'raw')+'.pkl')
@lru_cache(maxsize=1)
def period_end():return c.load_frame('external_period_end.pkl')
def materialize(frame,names,registry,track):
 result=frame.copy();months=pd.PeriodIndex(frame.month,freq='M')
 for n in names:
  d=registry[n]
  if d['origin']=='external':
   keys=months-d['lag'];values=external(track)[d['base']].reindex(keys).to_numpy()
   if d['lag']:
    dates=pd.to_datetime(period_end()[d['base']].reindex(keys).to_numpy(),errors='coerce');values=np.where(dates<months.start_time,values,np.nan)
   result[n]=values
  elif d['kind']!='block' and d['source_columns'][0]!=n:result[n]=result[d['source_columns'][0]]
 return result

def nuisance(train,valid,pop,target):
 def clock(frame):
  m=pd.PeriodIndex(frame.month,freq='M');t=(m.asi8-pd.Period('1958-01','M').ordinal)/12
  return np.column_stack([np.ones(len(frame)),t,np.sin(2*np.pi*m.month/12),np.cos(2*np.pi*m.month/12)])
 a,b=clock(train),clock(valid)
 if pop in ['song','genre_month'] and 'primary_genre' in train:
  levels=sorted(train.primary_genre.dropna().unique())[1:]
  a=np.column_stack([a,*[train.primary_genre.eq(v).to_numpy(float) for v in levels]])
  b=np.column_stack([b,*[valid.primary_genre.eq(v).to_numpy(float) for v in levels]])
 elif pop=='monthly' and not target.startswith('genre_share__'):
  names=sorted(n for n in train if n.startswith('genre_share__'))[1:]
  if names:a=np.column_stack([a,train[names].to_numpy(float)]);b=np.column_stack([b,valid[names].to_numpy(float)])
 return a,b

def prepare(task,names,foldnumber):
 reg=c.read_json(c.LOCAL/(task['population']+'_registry.json'));source=population(task['population'])
 if task['scope']!='pooled':source=source.loc[source.primary_genre.eq(task['scope'])].reset_index(drop=True)
 frame=materialize(source,sorted(set(names)|{task['target']}),reg,task['track']);y=pd.to_numeric(frame[task['target']],errors='raise').to_numpy(float)
 tr,va=audit.masks(frame,y,task['bounds'],foldnumber);train=frame.loc[tr].copy();valid=frame.loc[va].copy()
 train['song_id']=train.row_id;valid['song_id']=valid.row_id
 encoder=Encoder(reg).fit(train,names);x=encoder.transform(train);v=encoder.transform(valid)
 yy=y[tr];zz=y[va]
 w=np.ones(len(train));u=np.ones(len(valid))
 if task['population']=='genre_month':
  w=1/train.month.map(train.month.value_counts()).to_numpy(float);u=1/valid.month.map(valid.month.value_counts()).to_numpy(float)
 if task['track']=='adjusted':
  a,b=nuisance(train,valid,task['population'],task['target']);root=np.sqrt(w)
  # FWL residualization: every nuisance coefficient is estimated on training only.
  cy=np.linalg.lstsq(a*root[:,None],yy*root,rcond=None)[0];cx=np.linalg.lstsq(a*root[:,None],x[:,1:]*root[:,None],rcond=None)[0]
  yy=yy-a@cy;zz=zz-b@cy;x[:,1:]-=a@cx;v[:,1:]-=b@cx
 # Remove numerical zero columns created by exact nuisance projection.
 keep=[0]+[j for j in range(1,x.shape[1]) if np.max(np.abs(x[:,j]))>1e-10]
 remap={old:new for new,old in enumerate(keep)};encoder.groups={n:[remap[j] for j in ix if j in remap] for n,ix in encoder.groups.items()}
 x=x[:,keep];v=v[:,keep]
 metadata=dict(task_id=task['task_id'],population=task['population'],track=task['track'],target=task['target'],scope=task['scope'],fold=foldnumber,train_months=train.month.nunique(),validation_months=valid.month.nunique(),train_ids_sha256=c.digest(train.row_id.tolist()),validation_ids_sha256=c.digest(valid.row_id.tolist()))
 return Fold(x,v,yy,zz,w,u,encoder.groups,encoder,train,valid,metadata)

def evaluate(fold,combos):
 start=time.perf_counter();beta,ranks,fallback=fold.fit_batch(combos);fit=time.perf_counter()-start;start=time.perf_counter()
 residual=fold.centered_z[None,:]-(sparse.csr_matrix(beta.T)@np.ascontiguousarray(fold.V.T))
 mse=(residual*residual)@fold.u/fold.u.sum();mae=abs(residual)@fold.u/fold.u.sum();variance=np.average((fold.z-np.average(fold.z,weights=fold.u))**2,weights=fold.u)
 result=dict(mse=mse,mae=mae,r2=1-mse/variance if variance>0 else np.full(len(combos),np.nan),skill=1-mse/fold.baseline['mse'] if fold.baseline['mse']>0 else np.full(len(combos),np.nan),rank=ranks,fallback=fallback)
 return result,dict(fit_seconds=fit,metric_seconds=time.perf_counter()-start)

class Store:
 def __init__(self,path,protocol):
  self.db=sqlite3.connect(path);self.db.execute('CREATE TABLE IF NOT EXISTS identity(protocol TEXT NOT NULL)');self.db.execute('CREATE TABLE IF NOT EXISTS results(key TEXT PRIMARY KEY,body TEXT NOT NULL,sha TEXT NOT NULL)')
  row=self.db.execute('SELECT protocol FROM identity').fetchone()
  if row and row[0]!=protocol:raise ValueError('Checkpoint protocol mismatch')
  if not row:
   with self.db:self.db.execute('INSERT INTO identity VALUES (?)',(protocol,))
  self.verify()
 def verify(self):
  for key,body,expected in self.db.execute('SELECT key,body,sha FROM results'):
   if c.digest(json.loads(body))!=expected:raise ValueError('Checkpoint checksum mismatch: '+key)
 def get(self,key):
  row=self.db.execute('SELECT body,sha FROM results WHERE key=?',(key,)).fetchone()
  if not row:return None
  if c.digest(json.loads(row[0]))!=row[1]:raise ValueError('Checkpoint checksum mismatch')
  return json.loads(row[0])
 def put(self,key,value):
  value=c.clean(value);old=self.get(key)
  if old is not None and old!=value:raise ValueError('Deterministic replay differs')
  if old is None:
   with self.db:self.db.execute('INSERT INTO results VALUES (?,?,?)',(key,json.dumps(value,sort_keys=True),c.digest(value)))
 def close(self):self.db.close()

def kind(combo,reg):
 if 'lyric_semantic_embedding_private' in combo:return 'embedding_block'
 if any(reg[n]['kind']!='numeric' for n in combo):return 'categorical_or_small_block'
 return 'numeric'
def stratum_counts(task,reg):
 alln=task['counts'];names=task['predictors'];edges=task['edges'];triples=task['triples']
 scalar=audit.count_combinations([n for n in names if reg[n]['kind']=='numeric'],edges,triples)
 without=audit.count_combinations([n for n in names if n!='lyric_semantic_embedding_private'],edges,triples)
 return {(k,'numeric'):scalar[k] for k in [1,2,3]}|{(k,'embedding_block'):alln[k]-without[k] for k in [1,2,3]}|{(k,'categorical_or_small_block'):without[k]-scalar[k] for k in [1,2,3]}

def sample_combos(task,reg,k,group,n=16):
 rng=np.random.default_rng(c.SEED+task['task_id']*61+k*7+['numeric','categorical_or_small_block','embedding_block'].index(group));pool=task['predictors'];special=[x for x in pool if reg[x]['kind']!='numeric' and x!='lyric_semantic_embedding_private'];scalar=[x for x in pool if reg[x]['kind']=='numeric']
 edges={frozenset(x) for x in task['edges']};triples={frozenset(x) for x in task['triples']};found=set();limit=min(n,stratum_counts(task,reg)[(k,group)])
 from itertools import combinations
 for attempt in range(50000):
  if len(found)>=limit:break
  if group=='numeric':combo=tuple(sorted(rng.choice(scalar,size=k,replace=False)))
  else:
   first='lyric_semantic_embedding_private' if group=='embedding_block' else str(rng.choice(special));others=[x for x in pool if x!=first and (group=='embedding_block' or x!='lyric_semantic_embedding_private')]
   combo=tuple(sorted([first]+list(rng.choice(others,size=k-1,replace=False))))
  if frozenset(combo) in triples or any(frozenset(x) in edges for x in combinations(combo,2)):continue
  found.add(combo)
 if len(found)!=limit:raise ValueError('Pilot stratum sampling failed')
 return sorted(found)

def representatives(tasks):
 selected=[]
 for pop in audit.POPULATIONS:
  for track in ['raw','adjusted']:
   group=[t for t in tasks if t['population']==pop and t['track']==track and t['scope']=='pooled'];group.sort(key=lambda t:(t['folds'][0]['n_train'],t['target']))
   if group:selected.extend(group[i] for i in sorted(set([0,len(group)//2,len(group)-1])))
 # A sparse genre-specific workload, selected by sample size rather than effects.
 for track in ['raw','adjusted']:
  group=[t for t in tasks if t['population']=='genre_month' and t['track']==track and t['scope']!='pooled']
  if group:selected.append(min(group,key=lambda t:(t['folds'][0]['n_train'],t['scope'],t['target'])))
 return selected

def pilot():
 started=time.perf_counter();tasks=pickle.loads((c.LOCAL/'tasks.pkl').read_bytes());protocol=c.freeze();selected=representatives(tasks);records=[];checks=[];unique_fits=0;numerical_calls=0;resumed=0
 store=Store(c.LOCAL/'pilot.sqlite',protocol)
 for index,task in enumerate(selected):
  reg=c.read_json(c.LOCAL/(task['population']+'_registry.json'));counts=stratum_counts(task,reg);strata={k:sample_combos(task,reg,*k) for k,n in counts.items() if n}
  names=sorted({n for combos in strata.values() for combo in combos for n in combo})
  for number in range(3):
   t=time.perf_counter();fold=prepare(task,names,number);setup=time.perf_counter()-t
   for (k,group),combos in strata.items():
    before=time.perf_counter();result,timing=evaluate(fold,combos);elapsed=time.perf_counter()-before;numerical_calls+=len(combos)
    for i,combo in enumerate(combos):
     key=c.digest([task['task_id'],number,combo]);value=dict(task_id=task['task_id'],fold=number,predictors=combo,metrics={name:values[i] for name,values in result.items()},n_train=len(fold.y),n_validation=len(fold.z),train_months=fold.train.month.nunique(),validation_months=fold.validation.month.nunique(),rank_deficient=int(result['rank'][i])<len(fold.indices(combo)))
     if store.get(key) is not None:resumed+=1
     store.put(key,value);unique_fits+=1
    records.append(dict(task_id=task['task_id'],population=task['population'],track=task['track'],scope=task['scope'],target=task['target'],fold=number,k=k,encoding=group,eligible_combinations=counts[(k,group)],sampled=len(combos),seconds=elapsed,setup_seconds=setup,n_train=len(fold.y),n_validation=len(fold.z),encoded_columns=fold.X.shape[1],rank_deficient=sum(int(result['rank'][i])<len(fold.indices(combo)) for i,combo in enumerate(combos)),**timing))
    # Independently solve one full-row model from each timing stratum.
    check=fold.reference_check(combos[0]);numerical_calls+=2;checks.append(dict(task_id=task['task_id'],fold=number,k=k,encoding=group,**check))
   del fold
  store.close();store=Store(c.LOCAL/'pilot.sqlite',protocol)
  print(json.dumps(dict(stage='pilot',completed=index+1,tasks=len(selected),unique_validation_fits=unique_fits)),flush=True)
 store.verify();stored=store.db.execute('SELECT COUNT(*) FROM results').fetchone()[0];store.close()
 if stored!=unique_fits:raise ValueError('Unexpected pilot checkpoint coverage')
 # Reopen and reuse results without fitting. This is the same path used on restart.
 resumed_store=Store(c.LOCAL/'pilot.sqlite',protocol);replayed=0
 for key, in resumed_store.db.execute('SELECT key FROM results'):
  assert resumed_store.get(key) is not None;replayed+=1
 resumed_store.close()
 c.write_csv(c.PUBLIC/'benchmark_strata.csv',records);c.write_csv(c.PUBLIC/'ols_reference_checks.csv',[{k:v for k,v in r.items() if k not in ['predictors','max_metric_abs_error','max_prediction_abs_error']} for r in checks])
 grouped={}
 for r in records:
  key=(r['population'],r['track'],r['k'],r['encoding']);grouped.setdefault(key,[]).append(r)
 projected=0.;optimistic=0.;stratum_projection=[]
 for task in tasks:
  reg=c.read_json(c.LOCAL/(task['population']+'_registry.json'))
  for (k,group),n in stratum_counts(task,reg).items():
   if not n:continue
   candidates=grouped.get((task['population'],task['track'],k,group),[])
   if not candidates:raise ValueError('Unbenchmarked eligible encoding stratum')
   for fold in task['folds']:
    rates=[(r['fit_seconds']+r['metric_seconds']*max(1.,fold['n_validation']/r['n_validation']))/r['sampled'] for r in candidates]
    estimate=max(rates)*n;projected+=estimate;optimistic+=min(rates)*n
  # Setup cache cost is added per task/fold; the gate is already conservative in
  # residual work, but no claim is made that the sampled feature union equals the full matrix.
  candidates=[r for r in records if r['population']==task['population'] and r['track']==task['track']]
  projected+=4*max(r['setup_seconds'] for r in candidates)
 audit_result=c.read_json(c.PUBLIC/'audit.json');core=audit_result['core_metric_payload_bytes'];storage=int(core*1.15+1_000_000_000)
 seconds=projected*2+1800;free=shutil.disk_usage(c.ROOT).free;allowed=seconds<=c.CONFIG['runtime_limit_seconds'] and storage<=c.CONFIG['temporary_disk_limit_bytes'] and storage+c.CONFIG['disk_headroom_bytes']<=free
 rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
 out=dict(status='WITHIN_BUDGET' if allowed else 'APPROVAL_REQUIRED',full_campaign_started=False,protocol=protocol,representative_target_tasks=len(selected),unique_validation_fits=unique_fits,numerical_fit_calls_including_reference_checks=numerical_calls,
 unique_pilot_relationships=unique_fits//3,checkpoint_rows=stored,restart_rows_verified=replayed,resumed_rows=resumed,evaluation_models_fitted=0,independent_svd_checks=len(checks),
 elapsed_seconds=time.perf_counter()-started,peak_rss_bytes=rss,actual_local_bytes=sum(p.stat().st_size for p in c.LOCAL.rglob('*') if p.is_file()),
 projected_compute_seconds=projected,conservative_total_seconds=seconds,optimistic_measured_rate_seconds=optimistic,
 projection_rule='For every task/encoding/k/fold, maximum measured matching-stratum fit time plus residual time scaled upward for row count; 2x contingency plus 1800 seconds. Sampled-union cache estimates are approximate. Storage alone independently exceeds gate when blocked.',
 designed_core_storage_bytes=core,projected_temporary_storage_bytes=storage,free_disk_bytes=free,limits=dict(runtime_seconds=c.CONFIG['runtime_limit_seconds'],temporary_storage_bytes=c.CONFIG['temporary_disk_limit_bytes'],headroom_bytes=c.CONFIG['disk_headroom_bytes']),
 uncertainty='No formal p-values or confidence intervals; computational pilot only, no discoveries or evaluation-based selection')
 c.write_json(c.PUBLIC/'benchmark.json',out);print(json.dumps(out,indent=2),flush=True)
 if not allowed:print('FULL EXECUTION STOPPED AT USER RUNTIME/STORAGE GATE. Explicit scope/budget approval required.',flush=True)
 return out
if __name__=='__main__':
 with threadpool_limits(limits=1):pilot()
