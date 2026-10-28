"""Frozen inputs, scope, serialization and resource limits for hierarchical V4."""
from __future__ import annotations

import json
import pickle
import platform
import time
from importlib.metadata import version
from pathlib import Path

import cross_domain_v4_common as parent

ROOT = parent.ROOT
PUBLIC = ROOT / 'analysis/cross_domain_discovery_v4_hierarchical'
LOCAL = ROOT / 'data/experiments/cross_domain_discovery_v4_hierarchical'
SEED = 4914101
CONFIG = {
    'version': 'hierarchical-v4-1', 'parent_commit': 'b41e2c6', 'seed': SEED,
    'runtime_limit_seconds': 14400, 'temporary_disk_limit_bytes': 15_000_000_000,
    'disk_headroom_bytes': 2 * 1024**3, 'benchmark_limit_seconds': 1800,
    'screening_folds': [0, 1], 'independent_stability_folds': [2, 3],
    'one_and_two_predictor_scope': 'Every structurally eligible V4 target/model combination; no variable performance screen before this stage',
    'populations_tracks_genre_scopes_lags': 'Unchanged V4 task catalog; all 15 registered domains remain in scope',
    'single_global_quota': 16, 'single_per_domain_quota': 4,
    'pair_global_quota': 32, 'pair_per_domain_multiset_quota': 2,
    'triple_per_domain_multiset_quota': 2, 'triple_cap_per_target': 4096,
    'screen_rank': 'Descending mean screening skill, descending worst screening skill, ascending exact variable IDs; metrics rounded to 10 decimals for tie handling',
    'triple_proxy': 'Best retained pair mean skill plus 0.5 times added retained single mean skill; then minimum of their worst-fold skills; then exact IDs',
    'audit_samples_full': 131072, 'audit_minimum_per_stratum_full': 16,
    'audit_samples_pilot': 16384, 'audit_minimum_per_stratum_pilot': 4,
    'audit_strata': 'Population x track x unordered predictor-domain multiset; uniform without replacement within each stratum of rejected triples',
    'audit_seed_independent_of_screening': 4914199,
    'audit_feedback': 'Audit outcomes never change screening, candidates, thresholds, quotas or published selection',
    'qualifying_mean_stability_skill': 0.01, 'qualifying_min_stability_skill': 0.0,
    'qualifying_mean_increment_over_best_contained_pair': 0.005,
    'qualifying_min_increment_over_best_contained_pair': 0.0,
    'coefficient_stability_replays_per_target': 20,
    'minimum_residual_degrees_of_freedom': 8,
    'maximum_within_group_gram_condition': 1e8,
    'minimum_schur_eigenvalue': 1e-8,
    'native_training_period_minimum': 12,
    'native_stability_period_minimum': 3,
    'target_batch_size': 8, 'candidate_chunk_size': 1024, 'blas_threads': 1,
    'metrics': 'Exact float64 held-out MSE and baseline-relative skill for exhaustive screening; rowwise MAE and coefficient replay reserved for bounded retained results',
    'retention': 'Full attempted-count/status/digest audit and bounded seeds/candidates/results; unretained lower-order metrics reproducible from pinned inputs, not stored billions of times',
    'inference': 'Chronological predictive stability and design-based screening audit; no causal, IID-significance or FDR claims',
    'prior_holdout_status': 'Later years were inspected in earlier campaigns; these are forward-transfer tests, not newly untouched data',
}

sha = parent.sha
digest = parent.digest
clean = parent.clean
atomic = parent.atomic
write_json = parent.write_json
read_json = parent.read_json
write_csv = parent.write_csv


def tasks():
    return pickle.loads((parent.LOCAL / 'tasks.pkl').read_bytes())


def registry(population):
    return read_json(parent.LOCAL / (population + '_registry.json'))


def initialize():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    write_json(PUBLIC / 'protocol.json', CONFIG)


def protocol():
    files = list((ROOT / 'src').glob('hierarchical_v4_*.py'))
    files = [p for p in files if not p.name.endswith('_report.py')]
    files += [ROOT/'src'/name for name in ['cross_domain_v4_common.py', 'cross_domain_v4_audit.py',
                                         'cross_domain_v4_data.py', 'cross_domain_v4_pilot.py', 'regression_core.py']]
    inputs = [parent.LOCAL/name for name in ['tasks.pkl', 'song.pkl', 'monthly.pkl', 'genre_month.pkl',
              'external_raw.pkl', 'external_adjusted.pkl', 'external_period_end.pkl',
              'song_registry.json', 'monthly_registry.json', 'genre_month_registry.json']]
    return dict(config=CONFIG, code={str(p.relative_to(ROOT)): sha(p) for p in sorted(files)},
                inputs={str(p.relative_to(ROOT)): sha(p) for p in inputs},
                runtime=dict(python=platform.python_version(), machine=platform.machine(),
                             packages={name: version(name) for name in ['numpy', 'pandas', 'scipy', 'threadpoolctl']}),
                source_release_inputs=read_json(parent.PUBLIC/'input_manifest.json'))


def freeze():
    value = protocol()
    path = LOCAL / 'frozen_protocol.json'
    if path.exists() and read_json(path) != clean(value):
        raise ValueError('Hierarchical checkpoint differs: preserve and version the prior run')
    if not path.exists():
        write_json(path, value)
    return digest(value)


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, seconds, storage_limit=None):
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.storage_limit = storage_limit or CONFIG['temporary_disk_limit_bytes']

    def check(self, new_bytes=0):
        import shutil
        if time.monotonic() >= self.deadline - 30:
            raise BudgetExceeded('Runtime limit reached; incomplete work is not a completed campaign')
        used = sum(p.stat().st_size for p in LOCAL.rglob('*') if p.is_file())
        used += sum(p.stat().st_size for p in PUBLIC.rglob('*') if p.is_file())
        free = shutil.disk_usage(LOCAL).free
        if used + new_bytes > self.storage_limit or free - new_bytes < CONFIG['disk_headroom_bytes']:
            raise BudgetExceeded('Storage/headroom limit reached; no larger run is authorized')

    @property
    def elapsed(self):
        return time.monotonic() - self.started
