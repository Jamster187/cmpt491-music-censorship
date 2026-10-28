"""Isolated V4 artifacts, immutable provenance and deterministic serialization."""
from pathlib import Path
import hashlib,json,os,subprocess,time
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'analysis/cross_domain_discovery_v4'
LOCAL=ROOT/'data/experiments/cross_domain_discovery_v4'
VERSION='cross-domain-discovery-v4-pilot-1'
SEED=4914004
LAGS=(0,1,3,6,12,24)
CONFIG=dict(version=VERSION,parent_commit='51eb89878f072bc713cb43b7d1a5b69be4a4d95c',seed=SEED,lags=LAGS,
 tracks=['raw','adjusted'],populations=['song','monthly','genre_month'],predictor_counts=[1,2,3],
 validation_fraction_boundaries=[.5,.6,.7,.8,1.],validation_folds=3,evaluation_folds=1,
 minimum_training_rows=30,minimum_validation_rows=12,minimum_training_months=24,minimum_validation_months=6,
 minimum_predictor_observed_training_rows=20,minimum_predictor_observed_training_months=6,
 embargo_months=84,runtime_limit_seconds=14400,temporary_disk_limit_bytes=15_000_000_000,disk_headroom_bytes=2*1024**3,
 estimator='Additive OLS; intercept; numeric training median plus missing indicator; categorical training vocabulary; no interaction or screening',
 analysis_mode='Retrospective association and chronological transfer; no deployable historical forecast claims from revised/current measurements',
 target_missingness='Never imputed; fixed target-specific cohort for all candidates; row eligibility never uses correlation or evaluation performance',
 adjusted='Native-frequency change/growth of external levels; unchanged rates-of-change/events; training-only time/season residualization; genre fixed effects for pooled genre-month; composition controls for monthly music',
 lag_direction='X at t-L predicts Y at t; lagged reference periods do not establish publication-time availability',
 weights='One vote per song; one per monthly row; pooled genre-month one total vote per calendar month',
 selection='Mean validation baseline-relative MSE skill, then worst-period skill, then fewer original variables, then lexicographic IDs; evaluation never used for selection',
 inference='Predictive rankings are not formal discoveries. No IID p-values. No significance/CI claims from pilot. Exhaustive inferential family must include every attempted model if later executed.',
 release_sensitivity='No verified original-edition release dates in source release; do not substitute unverified candidates',
 previous_evaluation_inspected=True,new_acquisition=False)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple,set)):return [clean(x) for x in v]
 if isinstance(v,np.ndarray):return clean(v.tolist())
 if isinstance(v,np.generic):return clean(v.item())
 if isinstance(v,float) and not np.isfinite(v):return None
 if isinstance(v,Path):return str(v)
 return v
def digest(obj):return hashlib.sha256(json.dumps(clean(obj),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def atomic(path,body):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name('.'+path.name+'.tmp')
 with tmp.open('wb') as f:f.write(body);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def write_json(path,obj):atomic(path,(json.dumps(clean(obj),sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
def read_json(path):return json.loads(Path(path).read_text())
def write_csv(path,data):
 frame=data if isinstance(data,pd.DataFrame) else pd.DataFrame(data)
 atomic(path,frame.to_csv(index=False,float_format='%.17g',lineterminator='\n').encode())
def save_frame(path,frame):
 import pickle
 atomic(path,pickle.dumps(frame,protocol=4))
def load_frame(name):return pd.read_pickle(LOCAL/name)
def freeze():
 protocol=dict(config=CONFIG,code={p.name:sha(p) for p in sorted((ROOT/'src').glob('cross_domain_v4_*.py')) if not p.name.endswith('_report.py')},inputs=read_json(PUBLIC/'input_manifest.json'))
 p=LOCAL/'protocol.json'
 if p.exists() and read_json(p)!=clean(protocol):raise ValueError('V4 checkpoint protocol differs; preserve existing run and version changes explicitly')
 if not p.exists():write_json(p,protocol)
 return digest(protocol)
def preservation(initialize=False):
 path=LOCAL/'preservation.json'
 if initialize:
  if path.exists():return preservation(False)
  records={}
  for base in [ROOT/'data',ROOT/'analysis']:
   for p in sorted(base.rglob('*')):
    if not p.is_file() or '__pycache__' in p.parts or LOCAL in p.parents or PUBLIC in p.parents:continue
    records[str(p.relative_to(ROOT))]={'bytes':p.stat().st_size,'sha256':sha(p)}
  write_json(path,dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files=records))
 d=read_json(path)
 for name,r in d['files'].items():
  p=ROOT/name
  if not p.is_file() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise ValueError('Protected original changed: '+name)
 return dict(status='PASS',files=len(d['files']),bytes=sum(x['bytes'] for x in d['files'].values()),baseline_commit=d['commit'])
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('action',choices=['preserve','verify']);a=p.parse_args();print(json.dumps(preservation(a.action=='preserve'),indent=2),flush=True)
