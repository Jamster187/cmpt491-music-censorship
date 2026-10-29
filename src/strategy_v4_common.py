"""Isolated strategy benchmark protocol, provenance, budgets and checkpoints."""
from __future__ import annotations
import os
for _key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[_key] = '1'
import hashlib
import json
import pickle
import platform
import shutil
import sqlite3
import threading
import sys
import time
import zlib
from importlib.metadata import version
from pathlib import Path

import cross_domain_v4_common as parent

ROOT = parent.ROOT
PUBLIC = ROOT/'analysis/cross_domain_discovery_v4_strategy_benchmark'
LOCAL = ROOT/'data/experiments/cross_domain_discovery_v4_strategy_benchmark'
CONFIG = dict(
    version='strategy-benchmark-v4-2', parent_commit='9cee34f2077da8e93a9c4f67c654ff5bf3809951',
    total_seconds=14400, strategy_seconds=3600, temporary_bytes=15_000_000_000,
    free_reserve_bytes=2*1024**3, search_seconds_per_cell=3., combinations_per_cell=4096,
    confirm_per_model_family=3, search_seeds=[4915101, 4915102, 4915103],
    model_families=['additive', 'polynomial'], polynomial_max_columns=64,
    polynomial_terms='Additive original-variable encodings plus numeric squares, all numeric pair products and the numeric triple product',
    search_folds=[0, 1], assessment_folds=[2, 3], embargo_months=84,
    minimum_residual_df=8, minimum_train_months=24, minimum_test_months=6,
    minimum_native_train_periods=12, minimum_native_test_periods=3,
    block_months=24, bootstrap_replicates=128, minimum_uncertainty_blocks=6,
    minimum_skill=.01, minimum_worst_skill=0., nominal_error=.05,
    production_minimum_family_recall=.5, production_maximum_null_world_acceptance=.1,
    a_random_fraction=.25, a_global_seeds=16, a_per_domain_seeds=2,
    c_initial_random=32, c_fixed_exploration_fraction=.5, c_elite=8,
    diversity_signature_cap=4, calibration_worlds_per_population_track=4,
    final_worlds_per_signal_population_track=2,
    signal_types=['linear', 'nonlinear', 'interaction', 'conditional', 'temporal', 'spurious_trend', 'null'],
    development_seed=4916000, calibration_seed=4917000, final_seed=4918000,
    synthetic_ar_levels=[.65, .85], synthetic_family_loading=.8, synthetic_noise_levels=[.65, 1.0],
    rank='Mean early validation skill plus 0.5 times worst early skill; exact IDs break ties',
    inference='Exploratory transfer and simulation recovery; no causal or post-selection p-value/FDR claims',
    multiplicity='Independent development-null calibration of the maximum reported score from the complete search-and-selection procedure; no selected-only adjusted p-values',
    full_campaign_authorized=False,
)
sha, digest, clean = parent.sha, parent.digest, parent.clean
read_json, write_json, write_csv, atomic = parent.read_json, parent.write_json, parent.write_csv, parent.atomic


def initialize():
    PUBLIC.mkdir(parents=True, exist_ok=True); LOCAL.mkdir(parents=True, exist_ok=True)
    write_json(PUBLIC/'protocol.json', CONFIG)


def tasks():
    return pickle.loads((parent.LOCAL/'tasks.pkl').read_bytes())


def registry(pop):
    return read_json(parent.LOCAL/(pop+'_registry.json'))


def freeze():
    sources = [p for p in (ROOT/'src').glob('strategy_v4_*.py') if not p.name.endswith('_report.py')]
    sources += [ROOT/'src'/name for name in ['cross_domain_v4_common.py', 'cross_domain_v4_data.py',
                'cross_domain_v4_audit.py', 'cross_domain_v4_pilot.py', 'hierarchical_v4_common.py',
                'hierarchical_v4_engine.py', 'hierarchical_v4_screen.py', 'regression_core.py']]
    inputs = [parent.LOCAL/name for name in ['tasks.pkl', 'song.pkl', 'monthly.pkl', 'genre_month.pkl',
              'external_raw.pkl', 'external_adjusted.pkl', 'external_period_end.pkl',
              'song_registry.json', 'monthly_registry.json', 'genre_month_registry.json']]
    inputs += [ROOT/'analysis/regression_cross_domain_v3/target_predictability.csv']
    value = dict(config=CONFIG, code={str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)},
                 inputs={str(p.relative_to(ROOT)): sha(p) for p in inputs},
                 runtime=dict(python=platform.python_version(), platform=platform.platform(),
                              packages={name: version(name) for name in ['numpy', 'pandas', 'scipy', 'threadpoolctl', 'matplotlib']}))
    path = LOCAL/'frozen_protocol.json'
    if path.exists() and read_json(path) != clean(value):
        raise ValueError('Benchmark protocol changed: preserve/version previous experiment before proceeding')
    if not path.exists():
        write_json(path, value); write_json(PUBLIC/'frozen_protocol.json', value)
    return digest(value)


class BudgetExceeded(RuntimeError):
    pass


class MemoryMeter:
    """Sample live RSS while a policy runs; common prepared data is included."""
    def __enter__(self):
        if sys.platform == 'darwin':
            import ctypes
            # Native SDK mach/task_info.h: MACH_TASK_BASIC_INFO (20), 48 bytes.
            class Info(ctypes.Structure):
                _fields_ = [('virtual', ctypes.c_uint64), ('resident', ctypes.c_uint64), ('maximum', ctypes.c_uint64),
                            ('user_seconds', ctypes.c_int32), ('user_microseconds', ctypes.c_int32),
                            ('system_seconds', ctypes.c_int32), ('system_microseconds', ctypes.c_int32),
                            ('policy', ctypes.c_int32), ('suspended', ctypes.c_int32)]
            library = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
            library.mach_task_self.restype = ctypes.c_uint32
            library.task_info.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
            task = library.mach_task_self()
            def read():
                info = Info(); count = ctypes.c_uint32(ctypes.sizeof(info)//4)
                if library.task_info(task, 20, ctypes.byref(info), ctypes.byref(count)) != 0:
                    raise RuntimeError('Native RSS measurement failed')
                return info.resident
            self.read = read
        elif sys.platform.startswith('linux'):
            self.read = lambda: int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
        else:
            raise RuntimeError('Live RSS sampling requires the documented macOS/Linux environment')
        self.peak = self.read()
        self.samples = 1; self.done = threading.Event()
        def sample():
            while not self.done.wait(.01):
                self.peak = max(self.peak, self.read()); self.samples += 1
        self.thread = threading.Thread(target=sample, daemon=True); self.thread.start()
        return self

    def __exit__(self, *args):
        self.done.set(); self.thread.join()
        self.peak = max(self.peak, self.read())

    def result(self):
        return dict(sampled_peak_rss_bytes=int(self.peak), samples=self.samples, interval_seconds=.01,
                    scope='Policy operation plus common prepared data; sampled RSS, not an isolated-process high-water mark')


class Store:
    def __init__(self, path, identity):
        self.path = Path(path); self.identity = identity; self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS identity(value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT,key TEXT,payload BLOB,sha TEXT,PRIMARY KEY(kind,key))')
        self.db.execute('CREATE TABLE IF NOT EXISTS segments(id INTEGER PRIMARY KEY,start REAL,stop REAL,elapsed REAL)')
        row = self.db.execute('SELECT value FROM identity').fetchone()
        if row and row[0] != identity:
            raise ValueError('Checkpoint identity differs')
        if not row:
            with self.db:
                self.db.execute('INSERT INTO identity VALUES (?)', (identity,))
        self.verify()

    def verify(self):
        for kind, key, body, expected in self.db.execute('SELECT kind,key,payload,sha FROM records'):
            if hashlib.sha256(body).hexdigest() != expected:
                raise ValueError('Corrupt benchmark checkpoint '+kind+'/'+key)

    def get(self, kind, key):
        row = self.db.execute('SELECT payload,sha FROM records WHERE kind=? AND key=?', (kind, str(key))).fetchone()
        if row is None:
            return None
        if hashlib.sha256(row[0]).hexdigest() != row[1]:
            raise ValueError('Checkpoint checksum mismatch')
        return pickle.loads(zlib.decompress(row[0]))

    def put(self, kind, key, value):
        body = zlib.compress(pickle.dumps(value, protocol=4), level=3); checksum = hashlib.sha256(body).hexdigest()
        row = self.db.execute('SELECT sha FROM records WHERE kind=? AND key=?', (kind, str(key))).fetchone()
        if row:
            if row[0] != checksum:
                raise ValueError('Immutable checkpoint replay differs')
            return
        with self.db:
            self.db.execute('INSERT INTO records VALUES (?,?,?,?)', (kind, str(key), body, checksum))

    def items(self, kind):
        return [(row[0], self.get(kind, row[0])) for row in self.db.execute('SELECT key FROM records WHERE kind=? ORDER BY key', (kind,)).fetchall()]

    def start(self):
        now = time.time()
        with self.db:
            self.db.execute('UPDATE segments SET stop=?,elapsed=MAX(0,?-start) WHERE stop IS NULL', (now, now))
            spent = float(self.db.execute('SELECT COALESCE(SUM(elapsed),0) FROM segments').fetchone()[0])
            segment = self.db.execute('INSERT INTO segments(start) VALUES (?)', (now,)).lastrowid
        return segment, spent

    def finish(self, segment, elapsed):
        with self.db:
            self.db.execute('UPDATE segments SET stop=?,elapsed=? WHERE id=?', (time.time(), elapsed, segment))


class Budget:
    def __init__(self, previous=0.):
        self.started = time.monotonic(); self.previous = previous

    @property
    def elapsed(self):
        return self.previous+time.monotonic()-self.started

    def check(self):
        if self.elapsed >= CONFIG['total_seconds']-120:
            raise BudgetExceeded('Four-hour benchmark cap reached; preserve partial results')
        used = sum(p.stat().st_size for root in [LOCAL, PUBLIC] for p in root.rglob('*') if p.is_file())
        if used > CONFIG['temporary_bytes'] or shutil.disk_usage(LOCAL).free < CONFIG['free_reserve_bytes']:
            raise BudgetExceeded('Benchmark storage/headroom cap reached')


def eligible(task, combo):
    import itertools
    combo = tuple(combo)
    return (1 <= len(combo) <= 3 and len(set(combo)) == len(combo) and set(combo) <= set(task['predictors'])
            and frozenset(combo) not in {frozenset(t) for t in task['triples']}
            and not any(frozenset(p) in {frozenset(e) for e in task['edges']} for p in itertools.combinations(combo, 2)))


def classification(task, combo, reg):
    t = reg[task['target']]; ds = [reg[n] for n in combo]
    within = all(d['domain'] == t['domain'] for d in ds)
    shared = any(set(d['source']) & set(t['source']) for d in ds)
    strict = all(d['domain'] != t['domain'] and not set(d['source']) & set(t['source']) for d in ds)
    region = 'provenance_separated' if strict else ('within_domain' if within else ('cross_shared_source' if shared else 'other_cross_domain'))
    sources = [set(t['source'])]+[set(d['source']) for d in ds]
    import itertools
    return dict(region=region, cross_domain=not within, target_provenance_separated=strict,
                all_sources_disjoint=all(not a & b for a, b in itertools.combinations(sources, 2)),
                same_family=any(d['family'] == t['family'] for d in ds) or len({d['family'] for d in ds}) < len(ds),
                mathematical_reconstruction=False)


def signature(combo, reg):
    # Lag/transform variants of the same source base are near-duplicate regions.
    return tuple(sorted((reg[n]['domain'], reg[n]['family'], reg[n]['base']) for n in combo))


def family_signature(combo, reg):
    return tuple(sorted((reg[n]['domain'], reg[n]['family']) for n in combo))
