"""Isolated V5 pairwise campaign: immutable inputs, protocol and resource ledger."""
from __future__ import annotations
import os
for _name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:
    os.environ[_name] = '1'
import hashlib
import json
import pickle
import platform
import sqlite3
import subprocess
import time
from importlib.metadata import version
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT/'analysis/cross_domain_discovery_v5'
LOCAL = ROOT/'data/experiments/cross_domain_discovery_v5'
PARENT = ROOT/'data/experiments/cross_domain_discovery_v4'
CONFIG = dict(version='pairwise-v5-1', parent_commit='bf1e299f9842ee9297082d020bb24041936af44b',
    months=['1958-08','2026-09'], lags=[0,1,3,6,12,24], tracks=['raw','adjusted'],
    maximum_seconds=14400,maximum_bytes=15_000_000_000,free_reserve_bytes=2*1024**3,
    minimum_feature_songs=5, minimum_residual_df=12, minimum_hac_blocks=6,
    minimum_native={'M':120,'Q':40,'A':30,'term':24,'event':30},
    hac_lags={'M':48,'Q':16,'A':6,'term':3,'event':6},
    uncertainty_revision='Before any discovery rankings: double the original monthly/quarterly/annual HAC horizon after its strong-AR null validation failed; retain the original failed simulation. Use block-count t degrees of freedom and six-block minimum. Independently seeded validation is required.',
    native_aggregation_minimum_fraction=.75, minimum_category_periods=5,minimum_binary_periods=10,
    confidence=.95, false_discovery_rate=.05, stationarity_threshold=.05,
    control_rank_tolerance=1e-10, temporal_embargo_months=84,
    validation_periods=[['1990-01','2002-01'],['2002-01','2014-01'],['2014-01','2026-10']],
    fixed_composition_training_end='1983-01',fixed_composition_minimum_months=60,
    minimum_validation_periods={'M':24,'Q':8,'A':8,'term':4,'event':8},
    minimum_training_periods={'M':120,'Q':40,'A':20,'term':20,'event':20},
    music_adjustment='First difference on the aligned native-period grid, with fixed time/season controls; overall lyrical means additionally use differenced genre shares. No differencing across missing periods.',
    external_adjustment='Source-type-specific native-period changes/log growth; existing returns, growth, event indicators and categorical labels retain their declared meaning.',
    family='One global BY family across all structurally eligible pairs, populations, tracks, lags and methods. Numerical/underpowered/nonstationary tests contribute p=1; raw nominal diagnostics are retained separately.',
    inference='Retrospective exploratory association and chronological transfer; no causality or untouched historical confirmation.',
    full_pairwise_execution_authorized=True, nonlinear_or_multivariate_search_authorized=False,
    seed=4919001)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def clean(value):
    if isinstance(value,dict): return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(tuple,list,set)): return [clean(v) for v in value]
    if isinstance(value,np.ndarray): return clean(value.tolist())
    if isinstance(value,np.generic): return clean(value.item())
    if isinstance(value,float) and not np.isfinite(value): return None
    if isinstance(value,Path): return str(value)
    return value


def digest(value):
    return hashlib.sha256(json.dumps(clean(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def atomic(path,body):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name('.'+path.name+'.tmp')
    with temporary.open('wb') as f: f.write(body); f.flush(); os.fsync(f.fileno())
    os.replace(temporary,path)


def write_json(path,value): atomic(path,(json.dumps(clean(value),sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
def read_json(path): return json.loads(Path(path).read_text())
def write_csv(path,value): atomic(path,(value if isinstance(value,pd.DataFrame) else pd.DataFrame(value)).to_csv(index=False,float_format='%.17g').encode())
def save(path,value): atomic(path,pickle.dumps(value,protocol=4))
def load(path): return pickle.loads(Path(path).read_bytes())


class ResourceLimit(RuntimeError): pass


class Budget:
    """Cumulative active command time; closed idle periods are not charged."""
    def __init__(self,action):
        import shutil
        PUBLIC.mkdir(parents=True,exist_ok=True); LOCAL.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(LOCAL/'resources.sqlite')
        self.db.execute('CREATE TABLE IF NOT EXISTS segments(id INTEGER PRIMARY KEY,action TEXT,start REAL,stop REAL,seconds REAL)')
        now=time.time()
        # A crashed segment is conservatively charged until its next resume.
        self.db.execute('UPDATE segments SET stop=?,seconds=?-start WHERE stop IS NULL',(now,now))
        self.prior=self.db.execute('SELECT COALESCE(SUM(seconds),0) FROM segments').fetchone()[0]
        self.id=self.db.execute('INSERT INTO segments(action,start) VALUES(?,?)',(action,now)).lastrowid
        self.db.commit(); self.start=time.perf_counter(); self.last_check=0.; self.shutil=shutil

    def check(self,force=False):
        elapsed=time.perf_counter()-self.start
        if self.prior+elapsed >= CONFIG['maximum_seconds']-120: raise ResourceLimit('Cumulative four-hour runtime reserve reached')
        if force or elapsed-self.last_check >= 5:
            self.last_check=elapsed
            size=sum(p.stat().st_size for p in LOCAL.rglob('*') if p.is_file())
            if size > CONFIG['maximum_bytes']: raise ResourceLimit('15 GB temporary storage limit exceeded')
            if self.shutil.disk_usage(LOCAL).free < CONFIG['free_reserve_bytes']: raise ResourceLimit('Filesystem free-space reserve reached')

    def close(self):
        elapsed=time.perf_counter()-self.start
        self.db.execute('UPDATE segments SET stop=?,seconds=? WHERE id=?',(time.time(),elapsed,self.id)); self.db.commit()
        total=self.db.execute('SELECT SUM(seconds) FROM segments').fetchone()[0]
        records=[dict(zip(['id','action','start_epoch','stop_epoch','seconds'],r)) for r in self.db.execute('SELECT * FROM segments ORDER BY id')]
        self.db.close(); write_json(PUBLIC/'resource_ledger.json',dict(total_seconds=total,segments=records))
        return total


def inputs():
    paths=[PARENT/(name+suffix) for name,suffix in [('monthly','.pkl'),('genre_month','.pkl'),('music_registry','.json'),
           ('external_raw','.pkl'),('external_period_end','.pkl'),('external_registry','.json')]]
    paths += [ROOT/name for name in [
        'data/public/music_enrichment_v2/monthly_overall.csv.xz','data/public/music_enrichment_v2/monthly_by_genre.csv.xz',
        'data/public/master_monthly.csv','data/external_historical/derived/all_observations.csv.xz',
        'data/external_historical/financial/processed/acquisition_v1/native_local.csv.xz',
        'data/external_historical/financial/processed/acquisition_v1/aggregation_metadata_local.csv.xz',
        'analysis/external_historical/series_dictionary.csv','analysis/external_historical/derived_series_dictionary.csv',
        'analysis/external_historical/financial_acquisition/series_dictionary.csv',
        'analysis/external_historical/financial_acquisition/derived_feature_dictionary.csv',
        'analysis/music_enrichment_v2/feature_dictionary.csv','analysis/cross_domain_discovery_v4/series_crosswalk.csv',
        'analysis/cross_domain_discovery_v4_strategy_benchmark/publication_manifest.json']]
    return paths


def freeze():
    files=[p for p in sorted((ROOT/'src').glob('pairwise_v5_*.py')) if not p.name.endswith('_report.py')]
    value=dict(config=CONFIG,code={str(p.relative_to(ROOT)):sha(p) for p in files},
        inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs()},
        runtime=dict(python=platform.python_version(),platform=platform.platform(),
            packages={name:version(name) for name in ['numpy','pandas','scipy','statsmodels','matplotlib','threadpoolctl']}))
    path=LOCAL/'frozen_protocol.json'
    if path.exists() and read_json(path)!=clean(value): raise ValueError('Frozen V5 protocol changed; preserve/version the existing attempt')
    if not path.exists(): write_json(path,value); write_json(PUBLIC/'frozen_protocol.json',value)
    return digest(value)


def snapshot_previous():
    path=LOCAL/'previous_files.json'
    if path.exists(): return
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    paths={ROOT/name for name in tracked if name}
    for directory in (ROOT/'data/experiments').glob('cross_domain_discovery_v4*'):
        paths.update(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    records={}
    for p in sorted(paths):
        if p.is_symlink(): records[str(p.relative_to(ROOT))]=dict(symlink=os.readlink(p))
        elif p.is_file(): records[str(p.relative_to(ROOT))]=dict(bytes=p.stat().st_size,sha256=sha(p))
    write_json(path,dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files=records))


def verify_previous():
    baseline=read_json(LOCAL/'previous_files.json')
    for name,record in baseline['files'].items():
        path=ROOT/name
        if 'symlink' in record:
            if not path.is_symlink() or os.readlink(path)!=record['symlink']: raise ValueError('Previous symlink changed: '+name)
        elif not path.is_file() or path.stat().st_size!=record['bytes'] or sha(path)!=record['sha256']:
            raise ValueError('Previous file changed: '+name)
    return dict(status='PASS',files=len(baseline['files']),baseline_commit=baseline['commit'])
