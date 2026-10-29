"""Isolated, bounded audit of frozen V5 candidates; never writes V5 inputs."""
from __future__ import annotations
import os
for _name in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[_name] = '1'
import contextlib
import json
import resource
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path
import numpy as np
import pandas as pd
import pairwise_v5_common as v5

ROOT = v5.ROOT
PUBLIC = ROOT/'analysis/cross_domain_discovery_v5_robustness'
LOCAL = ROOT/'data/experiments/cross_domain_discovery_v5_robustness'
sha, digest, atomic, write_json, read_json, write_csv = v5.sha, v5.digest, v5.atomic, v5.write_json, v5.read_json, v5.write_csv
CONFIG = dict(version='v5.1-robustness-1', parent_commit='5f6ab14739d63ad9d026c74a3827e587b2060a08', seed=4915101,
    maximum_seconds=14400, maximum_bytes=15_000_000_000, free_reserve_bytes=2*1024**3,
    selection=dict(corrected_adjusted_lyrical=16, corrected_adjusted_other=4, corrected_raw=4,
        failed_adjusted_per_domain=1, raw_trend_controls=2,
        failed_domains=['financial','macroeconomic','political_social','cultural'],
        mandatory=dict(music_variable='emotion_caring',view='R&B / Soul',external_variable='US_UNEMPLOYMENT',lag_months=6,track='adjusted'),
        rank_order=['broad_variation_desc','positive_same_direction_folds_desc','effect_magnitude_desc','global_q_asc','coverage_months_desc','native_n_desc','row_id_asc'],
        deduplication='One per (base music variable, view, external root, track); at most two per (base music variable, view, track) in each stratum. Raw strata take one per external superdomain before filling. Selection uses saved V5 estimates only.',
        eligibility='Estimable numeric V5 rows; original native sample floor; nonempty cross-domain source provenance. Substantive lyrical strata exclude source count, quality and provenance roles.'),
    bootstrap_repetitions=999, permutation_repetitions=499,
    moving_block_periods={'M':49,'Q':17,'A':7,'term':4,'event':7},
    hac_bandwidths={'M':[12,24,48,96],'Q':[4,8,16,32],'A':[2,3,6,12],'term':[1,2,3,6],'event':[2,3,6,12]},
    windows=[['1958-08','1990-01'],['1990-01','2010-01'],['2010-01','2026-10'],['1958-08','2020-01'],['2020-01','2026-10']],
    shock_windows=[['oil_and_recessions','1973-01','1976-01'],['double_dip','1980-01','1983-01'],
        ['1987_crash','1987-01','1989-01'],['dotcom_911','2000-01','2003-01'],['financial_crisis','2007-01','2010-01'],['pandemic','2020-01','2023-01']],
    fixed_break_years=[1985,2000,2010], future_placebo_months=[12,60], past_placebo_months=[60,120],
    genre_confidence_thresholds=['high','medium_or_high'], minimum_feature_songs=[5,10,20],
    minimum_descriptive_n={'M':24,'Q':12,'A':12,'term':12,'event':12},
    minimum_independent_blocks=6, minimum_same_sign_fraction=.9, minimum_deletion_magnitude_fraction=.5,
    independent_replication_policy='No acquisition. Shared provider observations, songs, classifiers, genre assignments and previously inspected years are not independent evidence.',
    outcome_rule='Robust exploratory requires original adjusted global correction and substantive role; >=6 effective exposure and score blocks; original HAC and both resampling intervals exclude zero in original direction; all year/five-year/recession deletions keep direction and >=50% slope magnitude; >=2 nonoverlapping periods same direction and >=2 positive V5 transfer folds; >=90% estimable weighting/adjacent-lag specifications keep direction; block-permutation diagnostic p<=.05. Missing required evidence fails the robust label. Known calendar/provenance measures or a raw trend losing >=75% correlation on adjustment are likely artifacts as musical discoveries; unstable corrected substantive effects are sensitive; remaining cases insufficient evidence.',
    multiplicity='Every attempted analytic sensitivity (including unsupported slots) and every negative-control test enters one diagnostic BY family. Original V5 q values are preserved. These selected-data diagnostics are not independent confirmation or a new selection-adjusted discovery family.',
    classifier_comparators={'detox_obscene':'ll_explicit_language','detox_sexual_explicit':'ll_sexual_content',
        'detox_threat':'ll_violence','ll_explicit_language':'detox_obscene','ll_sexual_content':'detox_sexual_explicit',
        'll_violence':'detox_threat','emotion_joy':'sentiment_positive','emotion_optimism':'sentiment_positive',
        'emotion_sadness':'sentiment_negative','emotion_disappointment':'sentiment_negative',
        'emotion_anger':'sentiment_negative','emotion_disgust':'sentiment_negative','emotion_nervousness':'sentiment_negative'},
    classifier_policy='Predeclared related constructs, not interchangeable scales; caring has no independent comparable classifier in the release. Same-song comparisons are measurement robustness only.',
    simulation_repetitions=200, simulation_ar=[0.,.6,.9],
    all_sensitivity_results_exploratory=True, acquisition_authorized=False, broad_search_authorized=False)


def seed(label):
    return int(digest([CONFIG['seed'],str(label)])[:16],16) % (2**32)


def peak_bytes():
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if __import__('sys').platform=='darwin' else value*1024)


class Budget:
    """Cumulative active commands, with a conservative crashed-command charge."""
    def __init__(self, action):
        LOCAL.mkdir(parents=True,exist_ok=True); PUBLIC.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(LOCAL/'resources.sqlite')
        self.db.execute('CREATE TABLE IF NOT EXISTS segments(id INTEGER PRIMARY KEY,action TEXT,start REAL,stop REAL,seconds REAL)')
        now=time.time(); self.db.execute('UPDATE segments SET stop=?,seconds=?-start WHERE stop IS NULL',(now,now))
        self.prior=self.db.execute('SELECT COALESCE(SUM(seconds),0) FROM segments').fetchone()[0]
        self.id=self.db.execute('INSERT INTO segments(action,start) VALUES(?,?)',(action,now)).lastrowid
        self.db.commit(); self.start=time.perf_counter(); self.last=0
    def check(self, force=False):
        elapsed=time.perf_counter()-self.start
        if self.prior+elapsed>CONFIG['maximum_seconds']-120: raise RuntimeError('V5.1 cumulative computation budget reached')
        if force or elapsed-self.last>10:
            self.last=elapsed
            size=sum(p.stat().st_size for p in LOCAL.rglob('*') if p.is_file())
            if size>CONFIG['maximum_bytes']: raise RuntimeError('V5.1 storage budget reached')
            if shutil.disk_usage(LOCAL).free<CONFIG['free_reserve_bytes']: raise RuntimeError('Filesystem reserve reached')
    def close(self):
        self.db.execute('UPDATE segments SET stop=?,seconds=? WHERE id=?',(time.time(),time.perf_counter()-self.start,self.id));self.db.commit()
        rows=[dict(zip(['id','action','start','stop','seconds'],r)) for r in self.db.execute('SELECT * FROM segments')]
        self.db.close()
        write_json(PUBLIC/'resource_ledger.json',dict(total_seconds=sum(r['seconds'] for r in rows),segments=rows,
            peak_process_bytes=peak_bytes(),local_bytes=sum(p.stat().st_size for p in LOCAL.rglob('*') if p.is_file())))
    def __enter__(self): self.check(True); return self
    def __exit__(self,*args): self.close()


def snapshot():
    path=LOCAL/'preservation.json'
    if path.exists(): return
    paths={ROOT/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT,text=True).split('\0') if p}
    paths.update(p for p in v5.LOCAL.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.update(v5.inputs())
    records={}
    for p in sorted(paths):
        if p.is_symlink(): records[str(p.relative_to(ROOT))]={'symlink':os.readlink(p)}
        elif p.is_file(): records[str(p.relative_to(ROOT))]={'sha256':sha(p),'bytes':p.stat().st_size}
    write_json(path,dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files=records))


def verify_preservation(deep=False):
    value=read_json(LOCAL/'preservation.json')
    for name,expected in value['files'].items():
        p=ROOT/name
        if 'symlink' in expected:
            if not p.is_symlink() or os.readlink(p)!=expected['symlink']: raise ValueError('Changed original symlink: '+name)
        elif not p.is_file() or p.stat().st_size!=expected['bytes'] or sha(p)!=expected['sha256']:
            raise ValueError('Changed original input/output: '+name)
    result=dict(status='PASS',files=len(value['files']),bytes=sum(r.get('bytes',0) for r in value['files'].values()),baseline_commit=value['commit'])
    if deep:
        import cross_domain_v4_common
        result['all_original_data_and_analyses']=cross_domain_v4_common.preservation()
        result['pre_v5_files']=v5.verify_previous()
    return result


def execution_fingerprint():
    selection=read_json(PUBLIC/'selection_freeze.json')
    if sha(PUBLIC/'candidate_selection.csv')!=selection['candidate_sha256']: raise ValueError('Frozen candidate list changed')
    if selection['config']!=v5.clean(CONFIG): raise ValueError('Frozen scientific specification changed')
    value=dict(selection_sha256=sha(PUBLIC/'selection_freeze.json'),
        code={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src').glob('robustness_v51_*.py')) if not p.name.endswith('_report.py')})
    path=LOCAL/'execution_freeze.json'
    if path.exists() and read_json(path)!=value: raise ValueError('Compute code changed after execution freeze; audit before resuming')
    if not path.exists(): write_json(path,value);write_json(PUBLIC/'execution_freeze.json',value)
    return digest(value)
