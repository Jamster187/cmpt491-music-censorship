"""Restartable hierarchical pilot/campaign with an enforced pre-launch budget gate."""
from __future__ import annotations

import os
for variable in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[variable] = '1'

import argparse
import collections
import hashlib
import itertools
import json
import pickle
import resource
import shutil
import sqlite3
import sys
import time
import zlib

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

import cross_domain_v4_common as parent
import cross_domain_v4_pilot as old_pilot
import hierarchical_v4_common as c
import hierarchical_v4_engine as engine
import hierarchical_v4_sampling as sampling
import hierarchical_v4_screen as screening

RESULT_DTYPE = np.dtype([('i', '<u2'), ('j', '<u2'), ('k', '<u2'),
                         ('skill_early', '<f8'), ('skill_late', '<f8'),
                         ('increment_early', '<f8'), ('increment_late', '<f8'),
                         ('status_early', 'u1'), ('status_late', 'u1'),
                         ('audit', 'u1'), ('qualifies', 'u1')])


class Store:
    def __init__(self, path, identity):
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.execute('CREATE TABLE IF NOT EXISTS identity (value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT, key TEXT, payload BLOB, sha256 TEXT, PRIMARY KEY(kind,key))')
        self.db.execute('CREATE TABLE IF NOT EXISTS timing (sequence INTEGER PRIMARY KEY, payload TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS runtime_segments (sequence INTEGER PRIMARY KEY, start REAL NOT NULL, stop REAL, elapsed REAL)')
        row = self.db.execute('SELECT value FROM identity').fetchone()
        if row and row[0] != identity:
            raise ValueError('Hierarchical run identity changed')
        if row is None:
            with self.db:
                self.db.execute('INSERT INTO identity VALUES (?)', (identity,))
        self.verify()

    def verify(self):
        for kind, key, payload, expected in self.db.execute('SELECT kind,key,payload,sha256 FROM records'):
            if hashlib.sha256(payload).hexdigest() != expected:
                raise ValueError('Corrupt checkpoint: '+kind+'/'+key)

    def get(self, kind, key):
        row = self.db.execute('SELECT payload,sha256 FROM records WHERE kind=? AND key=?', (kind, str(key))).fetchone()
        if row is None:
            return None
        if hashlib.sha256(row[0]).hexdigest() != row[1]:
            raise ValueError('Checkpoint checksum mismatch')
        return pickle.loads(zlib.decompress(row[0]))

    def put(self, kind, key, value):
        payload = zlib.compress(pickle.dumps(value, protocol=4), level=3)
        digest = hashlib.sha256(payload).hexdigest()
        old = self.db.execute('SELECT sha256 FROM records WHERE kind=? AND key=?', (kind, str(key))).fetchone()
        if old:
            if old[0] != digest:
                raise ValueError('Deterministic checkpoint replay differs')
            return
        with self.db:
            self.db.execute('INSERT INTO records VALUES (?,?,?,?)', (kind, str(key), payload, digest))

    def timing(self, value):
        with self.db:
            self.db.execute('INSERT INTO timing(payload) VALUES (?)', (json.dumps(c.clean(value), sort_keys=True),))

    def timings(self):
        return [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM timing ORDER BY sequence')]

    def keys(self, kind):
        return {int(row[0]) for row in self.db.execute('SELECT key FROM records WHERE kind=?', (kind,))}

    def close(self):
        self.db.close()

    def previous_runtime(self):
        now = time.time()
        # An interrupted segment consumes elapsed wall time through restart.
        # This conservative rule cannot grant a fresh four-hour budget.
        with self.db:
            self.db.execute('UPDATE runtime_segments SET stop=?,elapsed=MAX(0,?-start) WHERE stop IS NULL', (now, now))
        return float(self.db.execute('SELECT COALESCE(SUM(elapsed),0) FROM runtime_segments').fetchone()[0])

    def start_segment(self, start):
        with self.db:
            cursor = self.db.execute('INSERT INTO runtime_segments(start) VALUES (?)', (start,))
        return cursor.lastrowid

    def finish_segment(self, sequence, elapsed):
        with self.db:
            self.db.execute('UPDATE runtime_segments SET stop=?,elapsed=? WHERE sequence=?', (time.time(), elapsed, sequence))


def cohort_catalog(tasks):
    path = c.LOCAL/'cohorts.json'
    if path.exists():
        rows = c.read_json(path)
    else:
        rows = engine.catalog(tasks)
        c.write_json(path, rows)
    if sorted(row['task_id'] for row in rows) != sorted(task['task_id'] for task in tasks):
        raise ValueError('Cohort catalog lacks exact target coverage')
    return rows


def grouped(tasks, rows):
    mapping = {row['task_id']: row['cohort'] for row in rows}
    groups = {}
    for task in sorted(tasks, key=lambda t: (t['population'], t['track'], t['scope'], t['task_id'])):
        groups.setdefault(mapping[task['task_id']], []).append(task)
    return list(groups.items())


def pilot_tasks(tasks, rows):
    # Selection depends on sample size, feature count and cohort size, never scores.
    ids = {task['task_id'] for task in old_pilot.representatives(tasks)}
    groups = grouped(tasks, rows)
    for pop in ['song', 'monthly', 'genre_month']:
        for track in ['raw', 'adjusted']:
            candidates = [task for task in tasks if task['population'] == pop and task['track'] == track]
            ids.add(max(candidates, key=lambda t: (len(t['predictors']), -t['task_id']))['task_id'])
            biggest = max((group for _, group in groups if group[0]['population'] == pop and group[0]['track'] == track),
                          key=lambda group: (len(group), -group[0]['task_id']))
            ids.update(task['task_id'] for task in biggest[:c.CONFIG['target_batch_size']])
    return [task for task in tasks if task['task_id'] in ids]


def audit_plan(tasks, rows):
    summaries = []
    for (pop, track), part in itertools.groupby(sorted(tasks, key=lambda t: (t['population'], t['track'])), key=lambda t: (t['population'], t['track'])):
        part = list(part)
        summaries.append(dict(population=pop, track=track, target_tasks=len(part),
                              one_predictor=sum(t['counts'][1] for t in part),
                              two_predictor=sum(t['counts'][2] for t in part),
                              full_three_predictor=sum(t['counts'][3] for t in part)))
    singles = sum(t['counts'][1] for t in tasks)
    pairs = sum(t['counts'][2] for t in tasks)
    cap = len(tasks)*c.CONFIG['triple_cap_per_target']
    max_triples = cap+c.CONFIG['audit_samples_full']
    domains = sorted({r['domain'] for pop in ['song', 'monthly', 'genre_month'] for r in c.registry(pop).values()})
    lower_retention = c.CONFIG['single_global_quota']+len(domains)*c.CONFIG['single_per_domain_quota']+c.CONFIG['pair_global_quota']+len(domains)*(len(domains)+1)//2*c.CONFIG['pair_per_domain_multiset_quota']
    result = dict(status='DESIGN_AUDITED', target_tasks=len(tasks), shared_cohorts=len({row['cohort'] for row in rows}),
                  domains=domains, one_predictor_models=singles, two_predictor_models=pairs,
                  exhaustive_screening_attempts=2*(singles+pairs), selected_triple_cap=cap,
                  independent_audit_triples=c.CONFIG['audit_samples_full'],
                  selected_plus_audit_triple_cap=max_triples,
                  conservative_stability_attempt_cap=2*(4*max_triples+len(tasks)*lower_retention),
                  result_record_bytes=RESULT_DTYPE.itemsize,
                  triple_payload_byte_cap=max_triples*RESULT_DTYPE.itemsize,
                  lower_retained_per_target_cap=lower_retention, cohort_catalog_sha256=c.sha(c.LOCAL/'cohorts.json'),
                  summary=summaries, full_campaign_started=False)
    c.write_json(c.PUBLIC/'search_design.json', result)
    c.write_csv(c.PUBLIC/'cohort_catalog.csv', [{k: v for k, v in row.items() if k != 'fold_keys'} for row in rows])
    return result


def stage_screen(tasks, rows, store, budget):
    groups = grouped(tasks, rows)
    for number, (cohort, group) in enumerate(groups, 1):
        pending = [task for task in group if store.get('screen', task['task_id']) is None]
        if not pending:
            continue
        budget.check()
        # Keep the full cohort's feature union even when resuming a partial batch.
        started = time.perf_counter()
        first, second = engine.prepare(group, 0), engine.prepare(group, 1)
        if first.names != second.names:
            raise ValueError('Screening fold feature IDs differ')
        if len(first.names) >= 65536:
            raise ValueError('Variable IDs exceed the lossless uint16 result schema')
        store.timing(dict(stage='prepare_screen', cohort=cohort, seconds=time.perf_counter()-started,
                          population=group[0]['population'], track=group[0]['track'], scope=group[0]['scope'],
                          tasks=len(group), variables=len(first.names), n_train_max=max(len(first.X), len(second.X)),
                          encoded_columns_max=max(first.X.shape[1], second.X.shape[1])))
        positions = {task['task_id']: i for i, task in enumerate(group)}
        reg = c.registry(group[0]['population'])
        catalog = screening.lower_catalog(first.names, engine.lower_order_ids(first.names), reg)
        for offset in range(0, len(pending), c.CONFIG['target_batch_size']):
            batch = pending[offset:offset+c.CONFIG['target_batch_size']]
            columns = [positions[t['task_id']] for t in batch]
            started = time.perf_counter()
            ids, loss0, status0 = engine.score_lower(first, columns, budget)
            other_ids, loss1, status1 = engine.score_lower(second, columns, budget)
            if not np.array_equal(ids, other_ids):
                raise ValueError('Screening enumeration changed between folds')
            fit_seconds = time.perf_counter()-started
            started = time.perf_counter()
            for j, (task, column) in enumerate(zip(batch, columns)):
                lower = screening.screen_lower(task, first.names, ids, [loss0[:, j], loss1[:, j]],
                                                [status0, status1], [first.baseline[column], second.baseline[column]], reg, catalog)
                triples = screening.triples(task, lower, reg)
                store.put('screen', task['task_id'], dict(lower=lower, triples=triples))
            seconds = time.perf_counter()-started
            # Reference checks are independent full-row solves, selected by IDs.
            checks = []
            for design, status in [(first, status0), (second, status1)]:
                safe = np.flatnonzero(status == engine.OK)
                for index in safe[::max(1, len(safe)//8)][:8]:
                    combo = tuple(i for i in ids[index] if i >= 0)
                    checks.append(design.reference(combo, columns[0]))
            store.timing(dict(stage='screen', cohort=cohort, population=group[0]['population'], track=group[0]['track'],
                              scope=group[0]['scope'], tasks=len(batch), task_ids=[t['task_id'] for t in batch],
                              attempted_models=sum(t['counts'][1]+t['counts'][2] for t in batch),
                              fit_seconds=fit_seconds, screen_seconds=seconds, reference_checks=checks))
            del loss0, loss1
        del first, second
        print(json.dumps(dict(stage='screen', completed_cohorts=number, cohorts=len(groups), completed_targets=len(store.keys('screen')))), flush=True)
    if store.keys('screen') != {t['task_id'] for t in tasks}:
        raise ValueError('Incomplete exhaustive screening coverage')


def freeze_candidates(tasks, store, mode, budget):
    cached = store.get('audit', 'frozen')
    if cached is not None:
        return cached
    if store.keys('screen') != {task['task_id'] for task in tasks}:
        raise ValueError('Cannot access stability periods before all screens are frozen')
    selected = {task['task_id']: store.get('screen', task['task_id'])['triples']['candidates'] for task in tasks}
    regs = {pop: c.registry(pop) for pop in ['song', 'monthly', 'genre_month']}
    budget.check()
    started = time.perf_counter()
    suffix = 'pilot' if mode == 'pilot' else 'full'
    strata, draws = sampling.sample(tasks, selected, regs, c.CONFIG['audit_samples_'+suffix], c.CONFIG['audit_minimum_per_stratum_'+suffix], budget)
    result = dict(selection_hash=c.digest(selected), scope_hash=c.digest([t['task_id'] for t in tasks]),
                  strata=strata, draws=draws, independent_audit_hash=c.digest(draws))
    store.put('audit', 'frozen', result)
    store.timing(dict(stage='audit_sampling', seconds=time.perf_counter()-started, strata=len(strata), draws=len(draws)))
    return result


def native_support(task, design):
    definition = c.registry(task['population'])[task['target']]
    if definition['origin'] == 'external':
        ends = old_pilot.period_end()[definition['base']]
        train = ends.reindex(pd.PeriodIndex(design.train_months, freq='M')).nunique()
        valid = ends.reindex(pd.PeriodIndex(design.validation_months, freq='M')).nunique()
    else:
        train, valid = len(set(design.train_months)), len(set(design.validation_months))
    return dict(training_reference_periods=int(train), validation_reference_periods=int(valid),
                support_sufficient=bool(train >= c.CONFIG['native_training_period_minimum'] and valid >= c.CONFIG['native_stability_period_minimum']))


def qualify(skills, increments, statuses, support):
    return (np.isfinite(skills).all(axis=1) & np.isfinite(increments).all(axis=1) & (statuses == engine.OK).all(axis=1)
            & (skills.mean(axis=1) >= c.CONFIG['qualifying_mean_stability_skill'])
            & (skills.min(axis=1) > c.CONFIG['qualifying_min_stability_skill'])
            & (increments.mean(axis=1) >= c.CONFIG['qualifying_mean_increment_over_best_contained_pair'])
            & (increments.min(axis=1) > c.CONFIG['qualifying_min_increment_over_best_contained_pair'])
            & bool(all(row['support_sufficient'] for row in support)))


def stage_stability(tasks, rows, store, frozen, budget):
    audits = collections.defaultdict(list)
    for draw in frozen['draws']:
        audits[draw['task_id']].append(draw)
    groups = grouped(tasks, rows)
    for number, (cohort, group) in enumerate(groups, 1):
        pending = [task for task in group if store.get('stability', task['task_id']) is None]
        if not pending:
            continue
        budget.check()
        started = time.perf_counter()
        first, second = engine.prepare(group, 2), engine.prepare(group, 3)
        store.timing(dict(stage='prepare_stability', cohort=cohort, seconds=time.perf_counter()-started,
                          population=group[0]['population'], track=group[0]['track'], scope=group[0]['scope'],
                          tasks=len(group), variables=len(first.names), n_train_max=max(len(first.X), len(second.X)),
                          encoded_columns_max=max(first.X.shape[1], second.X.shape[1])))
        locations = {name: i for i, name in enumerate(first.names)}
        columns = {task['task_id']: i for i, task in enumerate(group)}
        reg = c.registry(group[0]['population'])
        for task in pending:
            started = time.perf_counter()
            budget.check()
            record = store.get('screen', task['task_id'])
            chosen = record['triples']['candidates']
            random = audits[task['task_id']]
            candidate_names = chosen+[draw['predictors'] for draw in random]
            candidates = [tuple(locations[name] for name in combo) for combo in candidate_names]
            pairs = sorted({tuple(pair) for combo in candidates for pair in itertools.combinations(combo, 2)})
            pair_lookup = {combo: i for i, combo in enumerate(pairs)}
            lower_names = [row['predictors'] for row in record['lower']['retained']]
            lower_ids = [tuple(locations[name] for name in combo) for combo in lower_names]
            target = columns[task['task_id']]
            skill, delta, status, support, coefficient_rows, lower_rows, checks = [], [], [], [], [], [], []
            numerical_attempts = 0
            for fold_number, design in [(2, first), (3, second)]:
                losses, diagnostic = design.score(candidates, [target])
                pair_loss, _ = design.score(pairs, [target])
                best_pair = np.array([min(pair_loss[pair_lookup[pair], 0] for pair in itertools.combinations(combo, 2)) for combo in candidates])
                sk = 1-losses[:, 0]/design.baseline[target]
                with np.errstate(invalid='ignore'):
                    improvement = (best_pair-losses[:, 0])/design.baseline[target]
                improvement[~np.isfinite(best_pair)] = -np.inf
                skill.append(sk); delta.append(improvement); status.append(diagnostic)
                support.append(native_support(task, design))
                lows = []
                for k in [1, 2]:
                    positions = [i for i, combo in enumerate(lower_ids) if len(combo) == k]
                    values, why = design.score([lower_ids[i] for i in positions], [target])
                    lows.extend((i, float(1-values[j, 0]/design.baseline[target]), int(why[j])) for j, i in enumerate(positions))
                lower_rows.append(sorted(lows))
                for combo in record['triples']['diagnostic_candidates']:
                    ids = tuple(locations[name] for name in combo)
                    coefficients = design.coefficients(ids, target)
                    coefficients = None if coefficients is None else {name: float(value[0]) for name, value in coefficients.items() if reg[name]['kind'] == 'numeric'}
                    coefficient_rows.append(dict(fold=fold_number, predictors=combo, scalar_standardized_coefficients=coefficients))
                safe = np.flatnonzero(diagnostic == engine.OK)
                for index in safe[::max(1, len(safe)//4)][:4]:
                    checks.append(design.reference(candidates[index], target))
                numerical_attempts += len(candidates)+len(pairs)+len(lower_ids)
            skills, increments, statuses = np.column_stack(skill), np.column_stack(delta), np.column_stack(status)
            qualifying = qualify(skills, increments, statuses, support)
            results = np.zeros(len(candidates), dtype=RESULT_DTYPE)
            for j, field in enumerate(['i', 'j', 'k']):
                results[field] = [combo[j] for combo in candidates]
            for j, suffix in enumerate(['early', 'late']):
                results['skill_'+suffix] = skills[:, j]
                results['increment_'+suffix] = increments[:, j]
                results['status_'+suffix] = statuses[:, j]
            results['audit'][len(chosen):] = 1
            results['qualifies'] = qualifying
            hits = collections.Counter(draw['stratum'] for i, draw in enumerate(random) if qualifying[len(chosen)+i])
            output = dict(task_id=task['task_id'], variable_names=first.names, results=results,
                          selected_count=len(chosen), audit_count=len(random), audit_hits=dict(hits),
                          selected_qualifying=int(qualifying[:len(chosen)].sum()), native_support=support,
                          lower_retained_names=lower_names, lower_stability=lower_rows,
                          coefficient_stability=coefficient_rows, selection_hash=record['triples']['candidates_sha256'])
            store.put('stability', task['task_id'], output)
            store.timing(dict(stage='stability', task_id=task['task_id'], cohort=cohort,
                              population=task['population'], track=task['track'], scope=task['scope'],
                              seconds=time.perf_counter()-started, selected_triples=len(chosen), audit_triples=len(random),
                              attempted_models=numerical_attempts, reference_checks=checks))
        del first, second
        print(json.dumps(dict(stage='stability', completed_cohorts=number, cohorts=len(groups), completed_targets=len(store.keys('stability')))), flush=True)
    if store.keys('stability') != {task['task_id'] for task in tasks}:
        raise ValueError('Incomplete stability coverage')


def summarize(tasks, store, frozen, mode, elapsed, budget):
    hits, retained = collections.Counter(), 0
    support_ok = 0
    for task in tasks:
        result = store.get('stability', task['task_id'])
        hits.update(result['audit_hits']); retained += result['selected_qualifying']
        support_ok += int(all(row['support_sufficient'] for row in result['native_support']))
    audit = sampling.estimate(frozen['strata'], hits, retained, budget=budget)
    c.write_json(c.LOCAL/(mode+'_false_negative_estimate.json'), audit)
    public_audit = {key: value for key, value in audit.items() if key != 'strata'}
    public_audit.update(scope=mode, target_tasks=len(tasks), population_scope='Pilot target tasks only' if mode == 'pilot' else 'Full frozen hierarchical task population')
    c.write_json(c.PUBLIC/(mode+'_screening_audit.json'), public_audit)
    c.write_csv(c.PUBLIC/(mode+'_audit_strata.csv'), audit['strata'])
    timings = store.timings()
    references = [check for row in timings for check in row.get('reference_checks', [])]
    output = dict(status='COMPLETE', scope=mode, target_tasks=len(tasks),
                  screening_models=sum(t['counts'][1]+t['counts'][2] for t in tasks),
                  exhaustive_screening_attempts=2*sum(t['counts'][1]+t['counts'][2] for t in tasks),
                  selected_triples=sum(store.get('screen', t['task_id'])['triples']['candidates'].__len__() for t in tasks),
                  audit_triples=len(frozen['draws']), native_support_complete_tasks=support_ok,
                  reference_checks=len(references), max_scaled_reference_mse_error=max((r['scaled_mse_error'] for r in references), default=0.),
                  elapsed_seconds=elapsed, local_checkpoint_bytes=store.path.stat().st_size,
                  peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform == 'darwin' else 1024),
                  selection_hash=frozen['selection_hash'], independent_audit_hash=frozen['independent_audit_hash'],
                  full_campaign_started=mode == 'full')
    c.write_json(c.PUBLIC/(mode+'_execution.json'), output)
    c.write_json(c.PUBLIC/(mode+'_timings.json'), [{key: value for key, value in row.items() if key != 'reference_checks'} for row in timings])
    return output


from hierarchical_v4_benchmark_report import projection


def run(mode):
    wall_start, monotonic_start = time.time(), time.monotonic()
    c.initialize()
    all_tasks = c.tasks()
    rows = cohort_catalog(all_tasks)
    audit_plan(all_tasks, rows)
    identity = c.freeze()
    if mode == 'full':
        gate = c.read_json(c.PUBLIC/'benchmark_gate.json')
        if gate['status'] != 'WITHIN_BUDGET' or gate['protocol_sha256'] != identity or gate['projection_code_sha256'] != c.sha(c.ROOT/'src/hierarchical_v4_benchmark_report.py'):
            raise c.BudgetExceeded('Full launch denied by the measured four-hour/15 GB gate')
        tasks = all_tasks
        seconds = c.CONFIG['runtime_limit_seconds']-gate['benchmark_seconds']
    else:
        tasks = pilot_tasks(all_tasks, rows)
        seconds = c.CONFIG['benchmark_limit_seconds']
    store = Store(c.LOCAL/(mode+'.sqlite'), c.digest([identity, mode, [t['task_id'] for t in tasks]]))
    previous = store.previous_runtime()
    initialization = time.monotonic()-monotonic_start
    budget = c.Budget(seconds-previous-initialization)
    budget.check()
    segment = store.start_segment(wall_start)
    try:
        stage_screen(tasks, rows, store, budget)
        frozen = freeze_candidates(tasks, store, mode, budget)
        stage_stability(tasks, rows, store, frozen, budget)
        output = summarize(tasks, store, frozen, mode, previous+initialization+budget.elapsed, budget)
        if mode == 'pilot':
            output['gate'] = projection(all_tasks, rows, output, store.timings(), previous+initialization+budget.elapsed)
        store.verify()
        print(json.dumps(output, indent=2), flush=True)
    finally:
        store.finish_segment(segment, time.monotonic()-monotonic_start)
        store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['audit', 'pilot', 'full'])
    args = parser.parse_args()
    with threadpool_limits(limits=c.CONFIG['blas_threads']):
        if args.action == 'audit':
            c.initialize(); all_tasks = c.tasks(); rows = cohort_catalog(all_tasks)
            print(json.dumps(audit_plan(all_tasks, rows), indent=2), flush=True)
        else:
            run(args.action)
