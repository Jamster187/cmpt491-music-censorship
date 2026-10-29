"""Budgeted experiments only. There is deliberately no full-campaign action."""
from __future__ import annotations
import strategy_v4_common as c
import argparse
import collections
import json
import resource
import sys
import time
import numpy as np
from threadpoolctl import threadpool_limits

import strategy_v4_data as data
import strategy_v4_engine as engine
import strategy_v4_search as search


def scalar_result(result):
    return {key: value for key, value in result.items() if key not in ['loss', 'prediction']}


def assess(case, folds, searched, store, budget):
    key = searched['key']; saved = store.get('assessment', key)
    if saved is not None:
        return saved
    start = time.perf_counter(); rows = []
    if c.digest(searched['selected']) != searched['selected_sha256']:
        raise ValueError('Post-selection candidate catalog changed')
    for number, candidate in enumerate(searched['selected']):
        budget.check()
        result = [engine.fit(fold, candidate['predictors'], candidate['family'], predictions=True) for fold in folds]
        uncertainty = engine.clustered_interval(folds, result, case.task['population'],
                                               int(c.digest([key, candidate, 'cluster'])[:15], 16))
        rows.append(dict(**candidate, periods=[scalar_result(r) for r in result],
                         min_skill=engine.assessment_stat(result), uncertainty=uncertainty,
                         classification=c.classification(case.task, candidate['predictors'], case.registry)))
    value = dict(key=key, case_key=case.key, strategy=searched['strategy'], seed=searched['seed'],
                 selected_sha256=searched['selected_sha256'], results=rows,
                 elapsed_seconds=time.perf_counter()-start, numerical_fit_attempts=2*len(rows))
    store.put('assessment', key, value)
    return value


def oracle(case, early, late, truth, store):
    saved = store.get('oracle', case.key)
    if saved is not None:
        return saved
    active = tuple(sorted(truth.get('active_predictors', [])))
    results = []
    if active and c.eligible(case.task, active):
        for family in c.CONFIG['model_families']:
            fitted = [engine.fit(fold, active, family, predictions=True) for fold in early+late]
            results.append(dict(family=family, predictors=active, periods=[scalar_result(r) for r in fitted],
                                min_skill=engine.assessment_stat(fitted[2:]),
                                uncertainty=engine.clustered_interval(late, fitted[2:], case.task['population'],
                                                                     int(c.digest([case.key, family, 'oracle'])[:15], 16))))
    value = dict(case_key=case.key, results=results, evaluated_only_after_all_searches_frozen=True)
    store.put('oracle', case.key, value)
    return value


def charge(budget_store, usage, key, strategy, seconds):
    if budget_store.get('charge', key) is None:
        budget_store.put('charge', key, dict(strategy=strategy, seconds=float(seconds)))
        usage[strategy] += seconds


def experiment(case, truth, seeds, store, budget_store, usage, budget):
    done = store.get('case', case.key)
    if done is not None:
        return done
    budget.check(); started = time.perf_counter(); namespace = store.identity[:12]+'/'
    store.put('case_metadata', case.key, dict(task_id=case.task['task_id'], population=case.task['population'],
              track=case.task['track'], target=case.task['target'], phase=truth['phase'], family=truth['family'],
              scope=case.task['scope'], eligibility_hash=c.digest([case.task['predictors'], case.task['edges'], case.task['triples']])))
    available = [name for name in ['A', 'B', 'C'] if usage[name] < c.CONFIG['strategy_seconds']-60]
    if not available:
        raise c.BudgetExceeded('All strategy allocations are exhausted')
    early = [engine.prepare(case, i) for i in c.CONFIG['search_folds']]
    pool = search.StratifiedPool(case.task, case.registry)
    preparation = time.perf_counter()-started
    for strategy in available:
        charge(budget_store, usage, namespace+f'{case.key}/prepare_early/{strategy}', strategy, preparation/len(available))
    # Rotation balances hardware warming and contention without using outcomes.
    rotation = int(c.digest(case.key)[:8], 16) % 3
    ordering = (['A', 'B', 'C']*2)[rotation:rotation+3]
    searches = []
    for seed in seeds:
        for strategy in ordering:
            if usage[strategy] >= c.CONFIG['strategy_seconds']-60:
                store.put('stopped', f'{case.key}/{strategy}/{seed}', dict(reason='strategy_budget', used_seconds=usage[strategy]))
                continue
            context = engine.SearchContext(case.key, case.task, case.registry)
            memory_key = f'{case.key}/{strategy}/{seed}/search'
            with c.MemoryMeter() as meter:
                found = search.run(context, early, strategy, seed, pool, store, budget)
            if store.get('memory', memory_key) is None:
                store.put('memory', memory_key, meter.result())
            charge(budget_store, usage, namespace+found['key']+'/search', strategy, found['charged_seconds'])
            searches.append(found)
    if not searches:
        raise c.BudgetExceeded('No strategy remains within its allocation')
    # No later labels are prepared until every search/seed for this case is frozen.
    start = time.perf_counter(); late = [engine.prepare(case, i) for i in c.CONFIG['assessment_folds']]
    later_preparation = time.perf_counter()-start
    for strategy in available:
        charge(budget_store, usage, namespace+f'{case.key}/prepare_late/{strategy}', strategy, later_preparation/len(available))
    for found in searches:
        with c.MemoryMeter() as meter:
            result = assess(case, late, found, store, budget)
        if store.get('memory', found['key']+'/assessment') is None:
            store.put('memory', found['key']+'/assessment', meter.result())
        charge(budget_store, usage, namespace+found['key']+'/assessment', found['strategy'], result['elapsed_seconds'])
    # Hidden labels are persisted/evaluated only after all policies have returned.
    store.put('truth', case.key, truth)
    oracle(case, early, late, truth, store)
    result = dict(case_key=case.key, task_id=case.task['task_id'], population=case.task['population'], track=case.task['track'],
                  scope=case.task['scope'], target=case.task['target'], eligible_predictors=len(case.task['predictors']),
                  phase=truth['phase'], benchmark_family=truth['family'], subtype=truth.get('subtype', truth['family']),
                  preparation_seconds=preparation+later_preparation, elapsed_seconds=time.perf_counter()-started,
                  completed_searches=len(searches), early_support=[f.support for f in early], late_support=[f.support for f in late],
                  predictor_domains=sorted(pool.domains), target_domain=case.registry[case.task['target']]['domain'],
                  coverage_and_history=data.support_bins(case.task),
                  eligibility_hash=c.digest([case.task['predictors'], case.task['edges'], case.task['triples']]),
                  peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform == 'darwin' else 1024))
    store.put('case', case.key, result)
    print(json.dumps(dict(case=case.key, phase=truth['phase'], population=result['population'], track=result['track'],
                          family=truth['family'], seconds=round(result['elapsed_seconds'], 2), searches=len(searches),
                          charged_strategy_seconds={k: round(v, 2) for k, v in usage.items()})), flush=True)
    return result


def specs(mode, selected, templates, refs):
    tasks = {t['task_id']: t for t in c.tasks()}
    if mode == 'development':
        for pop in ['monthly', 'song', 'genre_month']:
            for family in ['linear', 'interaction']:
                task = templates[(pop, 'raw')]
                yield dict(kind='synthetic', task=task, family=family, replicate=0, phase='development')
        return
    # Calibration outcomes cannot change search hyperparameters or candidate rules.
    for pop in ['song', 'monthly', 'genre_month']:
        for track in ['raw', 'adjusted']:
            for replicate in range(c.CONFIG['calibration_worlds_per_population_track']):
                yield dict(kind='synthetic', task=templates[(pop, track)], family='null', replicate=replicate, phase='calibration')
    # Real task order is balanced by metadata, not previous model performance.
    reference = {row['task_id']: row for row in refs}
    for task in sorted(selected, key=lambda t: (t['population'], t['track'], c.digest([4915323, t['task_id']]))):
        yield dict(kind='real', task=task, reference=reference.get(task['task_id']))
    for pop in ['song', 'monthly', 'genre_month']:
        for track in ['raw', 'adjusted']:
            for family in c.CONFIG['signal_types']:
                for replicate in range(c.CONFIG['final_worlds_per_signal_population_track']):
                    yield dict(kind='synthetic', task=templates[(pop, track)], family=family, replicate=replicate, phase='final')


def run(mode):
    c.initialize(); process_start = time.monotonic()
    budget_store = c.Store(c.LOCAL/'resource_ledger.sqlite', c.digest(['resource-v1', c.CONFIG['total_seconds'], c.CONFIG['temporary_bytes']]))
    segment, previous = budget_store.start(); budget = c.Budget(previous)
    usage = collections.Counter()
    for _, record in budget_store.items('charge'):
        usage[record['strategy']] += record['seconds']
    if mode == 'benchmark':
        identity = c.freeze(); path = c.LOCAL/'benchmark.sqlite'
    else:
        # Development runs are isolated by source hash; old attempts are preserved.
        identity = c.digest([c.CONFIG, {p.name: c.sha(p) for p in (c.ROOT/'src').glob('strategy_v4_*.py') if not p.name.endswith('_report.py')}])
        path = c.LOCAL/('development_'+identity[:12]+'.sqlite')
        c.write_json(c.LOCAL/'development_latest.json', dict(path=str(path.relative_to(c.ROOT)), identity=identity))
    store = c.Store(path, identity); status, error = 'COMPLETE', None
    try:
        selected, templates, refs = data.catalog(); schedule = list(specs(mode, selected, templates, refs))
        store.put('schedule', mode, [dict(kind=s['kind'], task_id=s['task']['task_id'], phase=s.get('phase', 'real'),
                                        family=s.get('family', 'real'), replicate=s.get('replicate')) for s in schedule])
        for spec in schedule:
            budget.check(); task = spec['task']
            if spec['kind'] == 'synthetic':
                case, truth = data.world(task, spec['family'], spec['replicate'], spec['phase'],
                                         [templates[(task['population'], 'raw')], templates[(task['population'], 'adjusted')]])
            else:
                case = engine.real_case(task); reference = spec['reference']
                active = list(reference['predictors']) if reference else []
                truth = dict(case_key=case.key, phase='real', family='known_reference' if reference else 'real_unlabelled',
                             active_predictors=active, active_families=sorted({(case.registry[n]['domain'], case.registry[n]['family']) for n in active}),
                             expected_historically_stable=None, null_or_spurious=None, reference=reference)
            seeds = c.CONFIG['search_seeds'] if mode == 'benchmark' else c.CONFIG['search_seeds'][:1]
            experiment(case, truth, seeds, store, budget_store, usage, budget)
            del case, truth
        store.verify()
    except c.BudgetExceeded as exception:
        status, error = 'BUDGET_STOP_PARTIAL', str(exception)
    except KeyboardInterrupt:
        status, error = 'INTERRUPTED_PARTIAL', 'User/process interruption; completed checkpoints retained'
        raise
    except Exception as exception:
        status, error = 'FAILED', repr(exception)
        raise
    finally:
        seconds = time.monotonic()-process_start
        budget_store.finish(segment, seconds)
        output = dict(status=status, mode=mode, reason=error, this_run_seconds=seconds,
                      total_charged_benchmark_seconds=previous+seconds,
                      strategy_charged_seconds=dict(usage), completed_cases=len(store.items('case')),
                      completed_searches=len(store.items('search')), completed_assessments=len(store.items('assessment')),
                      local_bytes=sum(p.stat().st_size for p in c.LOCAL.rglob('*') if p.is_file()),
                      peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform == 'darwin' else 1024),
                      full_campaign_started=False, checkpoint=str(path.relative_to(c.ROOT)))
        c.write_json(c.PUBLIC/(mode+'_execution.json'), output)
        store.db.close(); budget_store.db.close()
        print(json.dumps(output, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['audit', 'development', 'benchmark'])
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        if args.action == 'audit':
            c.initialize(); data.catalog()
        else:
            run(args.action)
