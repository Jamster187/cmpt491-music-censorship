"""Independent rejected-triple sampling and finite-population miss estimates."""
from __future__ import annotations

import bisect
import itertools

import numpy as np
from scipy.stats import hypergeom

import hierarchical_v4_common as c
from hierarchical_v4_screen import domain_counts


def allocation(sizes, total, minimum):
    sizes = np.asarray(sizes, dtype=np.int64)
    result = np.minimum(sizes, minimum)
    total = min(int(sizes.sum()), int(total))
    if result.sum() > total:
        raise ValueError('Audit budget cannot honor every nonempty stratum quota')
    remaining = total-int(result.sum())
    while remaining:
        capacity = sizes-result
        weights = capacity/capacity.sum()
        ideal = remaining*weights
        addition = np.minimum(capacity, np.floor(ideal).astype(np.int64))
        result += addition; remaining -= int(addition.sum())
        if remaining:
            order = sorted(np.flatnonzero(result < sizes), key=lambda i: (-(ideal[i]-addition[i]), int(i)))
            for i in order[:remaining]:
                result[i] += 1
            remaining = total-int(result.sum())
    return result


def sample(tasks, selected, registries, total, minimum, budget=None):
    tasks = sorted(tasks, key=lambda task: task['task_id'])
    if len({task['task_id'] for task in tasks}) != len(tasks):
        raise ValueError('Repeated target task in audit population')
    domains = sorted({r['domain'] for reg in registries.values() for r in reg.values()})
    patterns = list(itertools.combinations_with_replacement(domains, 3))
    pattern_index = {key: i for i, key in enumerate(patterns)}
    matrix = []
    for number, task in enumerate(tasks):
        if budget is not None and number % 50 == 0:
            budget.check()
        reg = registries[task['population']]
        counts = domain_counts(task, reg, patterns)
        for combo in selected[task['task_id']]:
            counts[pattern_index[tuple(sorted(reg[n]['domain'] for n in combo))]] -= 1
        if np.any(counts < 0):
            raise ValueError('Selected triples not contained in structural universe')
        matrix.append(counts)
    matrix = np.asarray(matrix, dtype=np.int64)
    strata = []
    for pop, track in sorted({(task['population'], task['track']) for task in tasks}):
        task_rows = np.array([i for i, task in enumerate(tasks) if (task['population'], task['track']) == (pop, track)])
        size = matrix[task_rows].sum(axis=0)
        for p in np.flatnonzero(size):
            rows = task_rows[matrix[task_rows, p] > 0]
            strata.append(dict(population=pop, track=track, domains=patterns[p], pattern_index=int(p),
                               population_size=int(size[p]), task_rows=rows.tolist()))
    sizes = [s['population_size'] for s in strata]
    allocated = allocation(sizes, total, minimum)
    samples = []
    cache = {}
    selected_sets = {key: set(map(tuple, value)) for key, value in selected.items()}
    for index, (stratum, n) in enumerate(zip(strata, allocated)):
        if budget is not None and index % 20 == 0:
            budget.check()
        seed = int(c.digest([c.CONFIG['audit_seed_independent_of_screening'], stratum['population'], stratum['track'], stratum['domains']])[:16], 16)
        rng = np.random.default_rng(seed)
        rows = stratum['task_rows']
        weights = matrix[rows, stratum['pattern_index']]
        cumulative = np.cumsum(weights)
        seen = set()
        while len(seen) < n:
            row = rows[bisect.bisect_right(cumulative, int(rng.integers(int(cumulative[-1]))))]
            task = tasks[row]
            key = task['task_id']
            if key not in cache:
                reg = registries[task['population']]
                groups = {}
                for name in sorted(task['predictors']):
                    groups.setdefault(reg[name]['domain'], []).append(name)
                cache[key] = groups, {frozenset(e) for e in task['edges']}, {frozenset(t) for t in task['triples']}
            groups, edges, forbidden = cache[key]
            # Rejection within a selected task is essential: task probabilities
            # are proportional to OMITTED eligible counts, not unfiltered counts.
            while True:
                combo = []
                for domain in sorted(set(stratum['domains'])):
                    times = stratum['domains'].count(domain)
                    chosen = rng.choice(len(groups[domain]), size=times, replace=False)
                    combo.extend(groups[domain][j] for j in chosen)
                combo = tuple(sorted(combo))
                if combo in selected_sets[key] or frozenset(combo) in forbidden or any(frozenset(pair) in edges for pair in itertools.combinations(combo, 2)):
                    continue
                break
            unit = (key, combo)
            if unit not in seen:
                seen.add(unit)
        for key, combo in sorted(seen):
            samples.append(dict(stratum=index, task_id=key, predictors=combo))
        stratum.update(sample_size=int(n), seed=seed,
                       inclusion_probability=float(n/stratum['population_size']))
        del stratum['task_rows']
    return strata, samples


def hypergeom_interval(population, draws, successes, alpha=.05):
    """Invert exact hypergeometric tails for the number of good omitted triples."""
    M, n, x = int(population), int(draws), int(successes)
    if not (0 <= x <= n <= M) or n == 0:
        raise ValueError('Invalid finite-population sample')
    if n == M:
        return x, x
    if x == 0:
        lower = 0
    else:
        lo, hi = x, M-n+x
        while lo < hi:
            mid = (lo+hi)//2
            if hypergeom.sf(x-1, M, mid, n) >= alpha/2:
                hi = mid
            else:
                lo = mid+1
        lower = lo
    if x == n:
        upper = M
    else:
        lo, hi = x, M-n+x
        while lo < hi:
            mid = (lo+hi+1)//2
            if hypergeom.cdf(x, M, mid, n) >= alpha/2:
                lo = mid
            else:
                hi = mid-1
        upper = lo
    return lower, upper


def estimate(strata, hits, retained_qualifying, alpha=.05, budget=None):
    results = []
    point, lower, upper = 0., 0, 0
    for i, row in enumerate(strata):
        if budget is not None and i % 20 == 0:
            budget.check()
        M, n, x = row['population_size'], row['sample_size'], int(hits.get(i, 0))
        local_lo, local_hi = hypergeom_interval(M, n, x, alpha)
        simultaneous_lo, simultaneous_hi = hypergeom_interval(M, n, x, alpha/len(strata))
        value = M*x/n
        point += value; lower += simultaneous_lo; upper += simultaneous_hi
        results.append(dict(**row, qualifying_sample=x, missed_total_estimate=value,
                            missed_total_interval_95=[local_lo, local_hi],
                            simultaneous_total_bounds=[simultaneous_lo, simultaneous_hi]))
    def ratio(misses):
        return misses/(misses+retained_qualifying) if misses+retained_qualifying else None
    return dict(retained_qualifying=int(retained_qualifying), missed_qualifying_estimate=point,
                missed_qualifying_simultaneous_interval=[lower, upper],
                false_negative_fraction_estimate=ratio(point),
                false_negative_fraction_simultaneous_interval=[ratio(lower), ratio(upper)],
                confidence=1-alpha, sampled_triples=sum(s['sample_size'] for s in strata),
                qualifying_sample_total=sum(hits.values()), strata=results,
                interpretation='Sampling uncertainty conditional on fixed historical data and the prespecified qualifying rule; not uncertainty about causality or an IID regression test. Zero sampled misses do not imply perfect recall.')
