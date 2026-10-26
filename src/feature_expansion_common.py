"""Shared protocol and atomic artifacts for the authorized local expansion v1."""
from __future__ import annotations
import csv
import gzip
import hashlib
import json
import lzma
import os
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import pandas as pd
import scipy
import sklearn

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'analysis/feature_expansion_v1'
DATA = ROOT / 'data/public/feature_expansion_v1'
LOCAL = ROOT / 'data/experiments/feature_expansion_v1'
SEED = 4911026
VERSION = 'feature-expansion-v1'
SCORES = list(pd.read_csv(ROOT/'data/public/songs.csv', nrows=0).filter(regex=r'^(ll_|detox_|emotion_|sentiment_)').columns)
TARGETS = ['top10', 'long_chart', 'best_rank', 'chart_weeks', 'chart_points']
CONFIG = dict(version=VERSION, seed=SEED, prediction_moment='Immediately after publication of first observed Billboard chart; all rows of that chart available',
    artist_history_cutoff='chart_date strictly less than focal debut; process entire date as one batch',
    unit='Exact original title + full artist credit; no automatic identity merge',
    primary_horizon_weeks=26, sensitivity_horizon_weeks=12, window='[debut, debut + 7*horizon days)',
    complete_followup='global last observed chart date >= exclusive horizon end',
    longevity='at least ceil(horizon/2) distinct chart dates within horizon',
    top10_eligibility='debut best observed rank > 10; songs already Top 10 are resolved and excluded',
    numerical_targets='best observed rank, distinct chart-date count, and source-row sum(101-rank) within fixed horizon; includes known debut contribution',
    duplicate_policy='Preserve every source row; points sum source rows; weeks count distinct dates; minimum rank resolves song/date only for rank changes',
    burn_in_end='1960-01-01', train_end='2010-01-01', validation_end='2018-01-01',
    partitions='Debut in assigned period AND entire target window ends by next boundary; horizon-crossing identities purged',
    strict_track='All weekly entrants with eligible complete follow-up; A=known debut rank; B=new A-C features only; C=union',
    retrospective_track='Final enriched identities with all 42 existing scores and usable structural text; same rows across A/B/C; modern content and credit proxies remain F',
    retrospective_baseline='42 frozen scores, primary genre, consistent single-valued matched duration and debut rank; no acquisition, final-success, release-date or catalog-count predictors',
    configurations=['baseline', 'new_only', 'combined'], methods=['regularized', 'tree', 'hist_gradient_boosting'],
    logistic_C=[0.1,1.0], ridge_alpha=[1.0,100.0], tree_depth=[3,6], tree_min_leaf=50,
    hgb_leaf_nodes=[15,31], hgb_max_iter=120, hgb_learning_rate=.06, hgb_min_leaf=30, hgb_l2=1.0,
    tuning='Train before 2010; validation 2010-2017 only. Select classification by balanced accuracy, then Brier; regression by MAE. Final selected estimator remains training-only, no validation refit.',
    thresholds=[round(v,2) for v in np.arange(.10,.901,.05)], probability_calibration='No fitted recalibration; report raw probabilities, Brier, log loss, ECE and reliability bins',
    hgb_early_stopping=False, preprocessing='Training-only median imputation without availability indicators, standardization, and observed-category one-hot encoding; unknown category all zero',
    bootstrap_repeats=199, bootstrap='Paired fixed-model resampling by exact full artist credit and by debut year; percentile 95% intervals; no model-selection uncertainty',
    permutation_repeats=3, permutation_sample_max=3000, permutation_population='Validation only; rankings not chosen from test',
    ablation='Validation-selected combined method/parameters held fixed; remove predefined source groups; same populations and preprocessing fit on train only',
    historical_backtests=[dict(test_start=2000,test_end=2010),dict(test_start=2010,test_end=2018)],
    historical_backtest_method='Prespecified HGB leaf_nodes=15,120 iterations; threshold selected in preceding five-year validation interval; no later model choice reused',
    prior_test_inspected=True, independent_confirmation=False, covid_analysis=False,
    external_acquisition=False, new_content_classifier_inference=False)


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [clean(x) for x in v]
    if isinstance(v,np.ndarray):return clean(v.tolist())
    if isinstance(v,np.generic):return clean(v.item())
    if isinstance(v,float) and not np.isfinite(v):return None
    if isinstance(v,(pd.Timestamp,)):return v.isoformat()
    return v


def digest(v):return hashlib.sha256(json.dumps(clean(v),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def atomic_bytes(path,raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(raw);os.replace(tmp,path)


def write_json(path,v):
    raw=(json.dumps(clean(v),sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    if str(path).endswith('.gz'):raw=gzip.compress(raw,mtime=0)
    atomic_bytes(path,raw)


def read_json(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def write_csv(path,rows):
    f=rows.copy() if isinstance(rows,pd.DataFrame) else pd.DataFrame(clean(rows))
    for col in f.select_dtypes('object'):
        if f[col].map(lambda x:isinstance(x,(dict,list,tuple))).any():
            f[col]=f[col].map(lambda x:json.dumps(clean(x),sort_keys=True) if isinstance(x,(dict,list,tuple)) else x)
    raw=f.to_csv(index=False,lineterminator='\n',float_format='%.15g').encode()
    if str(path).endswith('.xz'):raw=lzma.compress(raw,preset=6)
    elif str(path).endswith('.gz'):raw=gzip.compress(raw,mtime=0)
    atomic_bytes(path,raw)


def environment():
    return dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__,scipy=scipy.__version__,platform=platform.platform())


def freeze():
    record=dict(configuration=CONFIG,environment=environment(),input_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'data/public/songs.csv',ROOT/'data/public/master_weekly.csv.xz']})
    path=PUBLIC/'protocol.json'
    if path.exists() and read_json(path)!=clean(record):raise ValueError('Frozen protocol differs; use a new campaign version')
    if not path.exists():write_json(path,record)
    return digest(record)


def preservation(initialize=False):
    path=LOCAL/'preservation.json';LOCAL.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        if not initialize:raise ValueError('Missing preservation baseline')
        files={}
        for base in [ROOT/'data',ROOT/'analysis']:
            for p in sorted(base.rglob('*')):
                if not p.is_file() or '__pycache__' in p.parts or any(x==p or x in p.parents for x in [LOCAL,PUBLIC,DATA]):continue
                files[str(p.relative_to(ROOT))]=dict(size=p.stat().st_size,sha256=sha(p))
        write_json(path,dict(baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files=files))
        return dict(status='SNAPSHOT_CREATED',files=len(files),bytes=sum(x['size'] for x in files.values()))
    data=read_json(path)
    for name,expected in data['files'].items():
        p=ROOT/name
        if not p.is_file() or p.stat().st_size!=expected['size'] or sha(p)!=expected['sha256']:raise ValueError('Protected artifact changed: '+name)
    return dict(status='PASS',files=len(data['files']),bytes=sum(x['size'] for x in data['files'].values()),baseline_commit=data['baseline_commit'])


def split_frame(frame,horizon=26,train_end='2010-01-01',validation_end='2018-01-01',test_end=None):
    f=frame.copy();d=pd.to_datetime(f.first_chart_date);end=pd.to_datetime(f[f'window_end_{horizon}']);eligible=f[f'eligible_{horizon}'].astype(bool)&d.ge(CONFIG['burn_in_end'])
    tr=eligible&end.le(train_end)
    va=eligible&d.ge(train_end)&end.le(validation_end)
    te=eligible&d.ge(validation_end)
    if test_end is not None:te &=end.le(test_end)
    result={k:f.loc[m].copy() for k,m in [('train',tr),('validation',va),('test',te)]}
    sets=[set(x.song_id) for x in result.values()]
    if any(sets[i]&sets[j] for i in range(3) for j in range(i+1,3)):raise ValueError('Song crosses partitions')
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','preservation']);args=parser.parse_args()
    if args.action=='prepare':freeze();print(json.dumps(preservation(True),indent=2),flush=True)
    else:print(json.dumps(preservation(),indent=2),flush=True)
