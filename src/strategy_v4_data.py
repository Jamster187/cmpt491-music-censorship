"""Outcome-blind benchmark task allocation and isolated, hidden-truth worlds."""
from __future__ import annotations
import collections
import itertools
from functools import lru_cache
import numpy as np
import pandas as pd

import strategy_v4_common as c
from strategy_v4_engine import ObservedCase, real_case


def support_bins(task):
    first = int(task['bounds'][0][:4])
    n = min(f['n_train'] for f in task['folds'])
    return ('low' if n < 500 else ('medium' if n < 5000 else 'high'),
            'early' if first < 1990 else ('middle' if first < 2010 else 'recent'))


def references(tasks):
    # Mechanical reference inclusion from an existing validated publication.
    # These are observational reference mechanisms, not known causal truth.
    table = pd.read_csv(c.ROOT/'analysis/regression_cross_domain_v3/target_predictability.csv')
    table = table.loc[table.view.eq('provenance_separated') & table.positive_every_period.eq(True)]
    choices = []
    for _, row in table.iterrows():
        combo = tuple(sorted(row.predictors.split(' | ')))
        for task in tasks:
            if task['population'] == 'song' and task['track'] == 'raw' and task['target'] == row.target and c.eligible(task, combo):
                choices.append(dict(task_id=task['task_id'], target=row.target, predictors=combo,
                                    family=row.target_family, prior_candidate_id=int(row.candidate_id),
                                    prior_evaluation_r2=float(row.evaluation_r2),
                                    source='analysis/regression_cross_domain_v3/target_predictability.csv'))
    selected = {}
    for row in sorted(choices, key=lambda x: c.digest([4915307, x['prior_candidate_id']])):
        selected.setdefault(row['family'], row)
    return list(selected.values())


def catalog():
    tasks = c.tasks(); groups = collections.defaultdict(list)
    registries = {p: c.registry(p) for p in ['song', 'monthly', 'genre_month']}
    for task in tasks:
        groups[(task['population'], task['track'], registries[task['population']][task['target']]['domain'])].append(task)
    chosen = []; counts = collections.Counter()
    for group, candidates in sorted(groups.items(), key=lambda pair: c.digest([4915311, pair[0]])):
        # Rebalance available support/date/scope cells without inspecting outcomes.
        def key(task):
            coverage, period = support_bins(task)
            return (counts[(group[:2], 'scope', task['scope'])], counts[(group[:2], 'coverage', coverage)],
                    counts[(group[:2], 'period', period)], c.digest([4915311, task['task_id']]))
        task = min(candidates, key=key); chosen.append(task)
        coverage, period = support_bins(task)
        for dimension, value in [('scope', task['scope']), ('coverage', coverage), ('period', period)]:
            counts[(group[:2], dimension, value)] += 1
    known = references(tasks)
    chosen_ids = {t['task_id'] for t in chosen} | {r['task_id'] for r in known}
    selected = [t for t in tasks if t['task_id'] in chosen_ids]
    templates = {}
    for pop in ['song', 'monthly', 'genre_month']:
        candidates = [t for t in tasks if t['population'] == pop and t['track'] == 'raw' and t['scope'] == 'pooled'
                      and any(a['target'] == t['target'] and a['population'] == pop and a['scope'] == 'pooled' and a['track'] == 'adjusted' for a in tasks)]
        candidates.sort(key=lambda t: (t['folds'][0]['n_train'], t['task_id']))
        raw = candidates[len(candidates)//2]
        adjusted = next(t for t in tasks if t['population'] == pop and t['track'] == 'adjusted' and t['scope'] == 'pooled' and t['target'] == raw['target'])
        templates[(pop, 'raw')], templates[(pop, 'adjusted')] = raw, adjusted
    ledger = []
    for task in tasks:
        coverage, period = support_bins(task)
        ledger.append(dict(task_id=task['task_id'], population=task['population'], track=task['track'], scope=task['scope'],
                           target=task['target'], target_domain=registries[task['population']][task['target']]['domain'],
                           coverage_stratum=coverage, historical_stratum=period, benchmark_selected=task['task_id'] in chosen_ids,
                           eligible_predictors=len(task['predictors']), eligible_one=task['counts'][1], eligible_two=task['counts'][2], eligible_three=task['counts'][3],
                           eligibility_sha256=c.digest([task['predictors'], task['edges'], task['triples']]),
                           status='scheduled_benchmark' if task['task_id'] in chosen_ids else 'eligible_not_visited_by_bounded_benchmark'))
    c.write_csv(c.PUBLIC/'task_universe.csv', ledger)
    c.write_csv(c.PUBLIC/'known_reference_models.csv', known)
    plan = dict(all_tasks=len(tasks), benchmark_real_tasks=len(selected), domains=sorted({d['domain'] for reg in registries.values() for d in reg.values()}),
                structural_models=sum(sum(t['counts'].values()) for t in tasks),
                benchmark_task_ids=sorted(chosen_ids), templates={'|'.join(key): t['task_id'] for key, t in templates.items()},
                task_input_sha256=c.sha(c.parent.LOCAL/'tasks.pkl'), full_campaign_started=False)
    c.write_json(c.PUBLIC/'search_space_accounting.json', plan)
    return selected, templates, known


def ar(rng, length, rho):
    values = rng.normal(size=length)
    for i in range(1, length):
        values[i] = rho*values[i-1]+np.sqrt(1-rho*rho)*values[i]
    return values


def world(task, family, replicate, phase, template_pair):
    """Return observations and truth separately; strategies receive only the former."""
    original = real_case(task); reg = original.registry; frame = original.frame
    seed_base = c.CONFIG[phase+'_seed']
    seed = int(c.digest([seed_base, task['population'], family, replicate])[:15], 16)
    rng = np.random.default_rng(seed)
    rho = c.CONFIG['synthetic_ar_levels'][replicate % 2]
    noise_scale = c.CONFIG['synthetic_noise_levels'][replicate % 2]
    month = pd.PeriodIndex(frame.month, freq='M').asi8
    index = month-month.min()+24; length = int(index.max()+1)
    n = len(frame); genre = pd.factorize(frame.primary_genre.astype(str))[0] if 'primary_genre' in frame else np.zeros(n, int)
    genre_scale = .75+.5*((genre % 5)/4)
    common = set(template_pair[0]['predictors']) & set(template_pair[1]['predictors'])
    numeric = sorted(name for name in common if reg[name]['kind'] == 'numeric' and not name.startswith('genre_share__'))
    # Signal sites are selected before generating their outcomes, uniformly among
    # sufficiently observed numeric variables with distinct domains and families.
    train = month < pd.Period(task['bounds'][0], 'M').ordinal-84
    pool = [name for name in numeric if np.isfinite(frame[name].to_numpy(float))[train].mean() >= .7]
    if len(pool) < 3:
        raise ValueError('Synthetic template lacks supported hidden signal sites')
    rng.shuffle(pool); sites = []
    for name in pool:
        if (all(reg[name]['domain'] != reg[other]['domain'] and reg[name]['family'] != reg[other]['family'] for other in sites)
                and all(c.eligible(t, sites+[name]) for t in template_pair)):
            sites.append(name)
            if len(sites) == 3:
                break
    if len(sites) != 3:
        raise ValueError('Hidden sites lack distinct domains/families')
    # A temporal mechanism uses a genuinely lagged eligible source, chosen without
    # assigning scientific priority to any economic or lyrical variable.
    if family == 'temporal' and replicate % 2 == 0:
        lagged = [name for name in pool if reg[name]['origin'] == 'external' and reg[name]['lag'] > 0]
        if lagged:
            sites[0] = lagged[0]
    family_month, family_row, bases, columns, latent = {}, {}, {}, {}, {}
    for name in task['predictors']:
        definition = reg[name]
        if definition['kind'] != 'numeric' or name.startswith('genre_share__'):
            continue
        key = definition['origin'], definition['domain'], definition['family']
        if key not in family_month:
            local = np.random.default_rng(int(c.digest([seed, 'family', key])[:15], 16))
            family_month[key] = ar(local, length, rho)
            family_row[key] = local.normal(size=n)
        local = np.random.default_rng(int(c.digest([seed, 'variable', definition['base']])[:15], 16))
        loading = c.CONFIG['synthetic_family_loading']
        if definition['origin'] == 'external':
            base = definition['base']
            if base not in bases:
                bases[base] = loading*family_month[key]+np.sqrt(1-loading**2)*ar(local, length, rho)
            at = index-definition['lag']
            period = 12 if definition['frequency'] == 'A' else (3 if definition['frequency'] == 'Q' else 1)
            at = ((month-definition['lag'])//period)*period-month.min()+24
            z = bases[base][at]
        else:
            z = loading*(.6*family_month[key][index]+.8*family_row[key]) + np.sqrt(1-loading**2)*local.normal(size=n)
            z *= genre_scale
        if name in sites:
            latent[name] = z.copy()
        observed = np.isfinite(frame[name].to_numpy(float))
        columns[name] = np.where(observed, z, np.nan)
    if not all(name in latent for name in sites):
        raise ValueError('Hidden signal absent from template encoding')
    x1, x2, x3 = (latent[name] for name in sites)
    subtype, active, stable = family, sites[:1], True
    if family == 'linear':
        active = sites[:1] if replicate % 2 == 0 else sites
        signal = x1 if len(active) == 1 else x1+.7*x2-.5*x3
        subtype = 'linear_one' if len(active) == 1 else 'linear_three'
    elif family == 'nonlinear':
        signal = x1*x1 if replicate % 2 == 0 else np.sin(2.5*x1)
        subtype = 'quadratic' if replicate % 2 == 0 else 'oscillatory_outside_polynomial_family'
    elif family == 'interaction':
        active = sites[:2] if replicate % 2 == 0 else sites
        signal = x1*x2 if len(active) == 2 else x1*x2*x3
        subtype = 'pure_pair_product' if len(active) == 2 else 'pure_triple_product'
    elif family == 'conditional':
        active = sites[:2]
        if replicate % 2 == 0:
            x2 = .95*x1+np.sqrt(1-.95**2)*x2
            signal = x1-x2; subtype = 'suppressor'
            columns[sites[1]] = np.where(np.isfinite(columns[sites[1]]), x2, np.nan)
        else:
            x1 = .9*x2+np.sqrt(1-.9**2)*x1
            signal = 2*x1-4*x2; subtype = 'conditional_sign_reversal'
            columns[sites[0]] = np.where(np.isfinite(columns[sites[0]]), x1, np.nan)
    elif family == 'temporal':
        if replicate % 2 == 0:
            signal = x1; subtype = 'stable_lagged'
        else:
            signal = np.where(month < pd.Period(task['bounds'][3], 'M').ordinal, x1, -x1)
            subtype = 'regime_sign_flip'; stable = False
    elif family == 'spurious_trend':
        t = (month-month.min())/max(1, month.max()-month.min())*6
        for name in pool[:min(24, len(pool))]:
            columns[name] = columns[name]+t
        signal = t; active = []; stable = False
    elif family == 'null':
        signal = np.zeros(n); active = []; stable = False
    else:
        raise ValueError('Unknown synthetic mechanism')
    # Independent noise has month autocorrelation and (for songs) repeated-credit
    # components. No predictor is used to form a null outcome.
    noise_rng = np.random.default_rng(seed+99317)
    noise = .6*ar(noise_rng, length, rho)[index]+.8*noise_rng.normal(size=n)*genre_scale
    if task['population'] == 'song':
        artist, names = pd.factorize(frame.artist.astype(str))
        noise += .3*noise_rng.normal(size=len(names))[artist]
    training_signal = signal[train]
    if active or family == 'spurious_trend':
        # Signal scale uses development-era rows, never assessment outcomes.
        signal = (signal-np.mean(training_signal))/max(np.std(training_signal), 1e-8)
    y = signal+noise_scale*noise
    y[~np.isfinite(original.y)] = np.nan
    replaced = pd.DataFrame(columns, index=frame.index)
    copy = pd.concat([frame.drop(columns=list(columns)), replaced], axis=1)
    key = c.digest([phase, seed, task['track'], task['task_id']])[:20]
    observed = ObservedCase(key, task, copy, y, reg)
    truth = dict(case_key=key, phase=phase, population=task['population'], track=task['track'], family=family,
                 subtype=subtype, replicate=replicate, generator_seed=seed, active_predictors=active,
                 ar_coefficient=rho, noise_scale=noise_scale,
                 active_families=sorted({(reg[name]['domain'], reg[name]['family']) for name in active}),
                 expected_historically_stable=stable, null_or_spurious=not bool(active),
                 native_rows=n, observed_target_rows=int(np.isfinite(y).sum()),
                 missingness_preserved=all(np.array_equal(np.isfinite(copy[name]), np.isfinite(frame[name])) for name in columns),
                 sites_sha256=c.digest(sites), observations_sha256=c.digest([np.nan_to_num(y).tolist(), sites]),
                 injected_marginal_correlations={name: float(np.corrcoef(columns[name][train & np.isfinite(y) & np.isfinite(columns[name])],
                                                                                  y[train & np.isfinite(y) & np.isfinite(columns[name])])[0, 1]) for name in active})
    if not truth['missingness_preserved']:
        raise ValueError('Synthetic copy changed the template missingness mask')
    return observed, truth


def signal_hit(combo, truth, reg, tolerant=False):
    active = truth['active_predictors']
    if not active:
        return False
    if tolerant:
        return set(map(tuple, truth['active_families'])) <= {(reg[n]['domain'], reg[n]['family']) for n in combo}
    return set(active) <= set(combo)
