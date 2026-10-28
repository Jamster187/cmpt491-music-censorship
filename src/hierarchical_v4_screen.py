"""Exhaustive lower-order accounting and fixed, domain-balanced triple screening."""
from __future__ import annotations

import hashlib
import itertools
import math

import numpy as np

import hierarchical_v4_common as c


def allowed_mask(task, names, ids):
    allowed = set(task['predictors'])
    flags = np.array([name in allowed for name in names], bool)
    single = ids[:, 1] < 0
    mask = flags[ids[:, 0]] & (single | flags[np.maximum(ids[:, 1], 0)])
    position = {name: i for i, name in enumerate(names)}
    p = len(names)
    for first, second in task['edges']:
        if first in position and second in position:
            i, j = sorted([position[first], position[second]])
            mask[p+i*(2*p-i-1)//2+j-i-1] = False
    if int(mask[single].sum()) != task['counts'][1] or int(mask[~single].sum()) != task['counts'][2]:
        raise ValueError('Lower-order enumeration changed the audited universe')
    return mask


def top_indices(indices, mean, worst, ids, count):
    """Bounded partial selection with deterministic treatment of boundary ties."""
    indices = np.asarray(indices, int)
    if len(indices) <= count:
        candidates = indices
    else:
        scores = mean[indices]
        threshold = np.partition(scores, len(scores)-count)[len(scores)-count]
        candidates = indices[scores >= threshold]
    candidates = sorted(candidates, key=lambda i: (-mean[i], -worst[i], tuple(ids[i])))
    return candidates[:count]


def lower_catalog(names, ids, registry):
    domains = sorted({registry[name]['domain'] for name in names})
    labels = {domain: i for i, domain in enumerate(domains)}
    d = np.array([labels[registry[name]['domain']] for name in names])
    first, second = d[ids[:, 0]], d[np.maximum(ids[:, 1], 0)]
    singles = ids[:, 1] < 0
    codes = np.where(singles, first, len(domains)+np.minimum(first, second)*len(domains)+np.maximum(first, second))
    order = np.argsort(codes, kind='stable')
    keys, starts = np.unique(codes[order], return_index=True)
    stops = np.r_[starts[1:], len(order)]
    strata = []
    for code, start, stop in zip(keys, starts, stops):
        if code < len(domains):
            pattern, size = (domains[code],), 1
        else:
            a, b = divmod(code-len(domains), len(domains))
            pattern, size = (domains[a], domains[b]), 2
        strata.append((size, pattern, order[start:stop]))
    return dict(strata=strata, singles=singles)


def screen_lower(task, names, ids, fold_scores, fold_statuses, baselines, registry, catalog=None):
    allowed = allowed_mask(task, names, ids)
    skills = 1-np.column_stack(fold_scores)/np.asarray(baselines)[None, :]
    eligible = allowed & np.all(np.column_stack(fold_statuses) == 0, axis=1) & np.isfinite(skills).all(axis=1)
    mean = np.round(np.mean(skills, axis=1), 10)
    worst = np.round(np.min(skills, axis=1), 10)
    catalog = catalog or lower_catalog(names, ids, registry)
    kept = set()
    coverage = []
    for size, global_quota, local_quota in [(1, c.CONFIG['single_global_quota'], c.CONFIG['single_per_domain_quota']),
                                           (2, c.CONFIG['pair_global_quota'], c.CONFIG['pair_per_domain_multiset_quota'])]:
        which = catalog['singles'] if size == 1 else ~catalog['singles']
        good = np.flatnonzero(eligible & which)
        kept.update(top_indices(good, mean, worst, ids, global_quota))
        for k, pattern, indexes in catalog['strata']:
            if k != size:
                continue
            valid = indexes[eligible[indexes]]
            selected = top_indices(valid, mean, worst, ids, local_quota)
            kept.update(selected)
            coverage.append(dict(domains=pattern, k=size, attempted=int(allowed[indexes].sum()), estimable=len(valid), quota_selected=len(selected)))
    retained = []
    for i in sorted(kept):
        combo = tuple(names[j] for j in ids[i] if j >= 0)
        retained.append(dict(predictors=combo, mean_skill=float(mean[i]), worst_skill=float(worst[i]),
                             fold_skill=skills[i].tolist()))
    digest = hashlib.sha256()
    digest.update(ids[allowed].astype('<i4').tobytes())
    # Digest finite values and diagnostic statuses for every allowed attempt.
    digest.update(np.asarray(np.column_stack(fold_scores)[allowed], dtype='<f8').tobytes())
    digest.update(np.asarray(np.column_stack(fold_statuses)[allowed], dtype='u1').tobytes())
    return dict(task_id=task['task_id'], retained=retained, domain_coverage=coverage,
                attempted_one=task['counts'][1], attempted_two=task['counts'][2],
                screen_eligible=int(eligible.sum()), attempt_digest=digest.hexdigest(),
                status_counts=[np.bincount(np.asarray(s)[allowed], minlength=5).tolist() for s in fold_statuses])


def triples(task, lower, registry):
    singles = [r for r in lower['retained'] if len(r['predictors']) == 1]
    pairs = [r for r in lower['retained'] if len(r['predictors']) == 2]
    edges = {frozenset(x) for x in task['edges']}
    forbidden = {frozenset(x) for x in task['triples']}
    candidates = {}
    for pair in pairs:
        for single in singles:
            if single['predictors'][0] in pair['predictors']:
                continue
            combo = tuple(sorted(pair['predictors']+single['predictors']))
            if frozenset(combo) in forbidden or (edges and any(frozenset(p) in edges for p in itertools.combinations(combo, 2))):
                continue
            score = round(pair['mean_skill']+.5*single['mean_skill'], 10)
            worst = min(pair['worst_skill'], single['worst_skill'])
            key = (score, worst)
            if combo not in candidates or key > candidates[combo]:
                candidates[combo] = key
    order = sorted(candidates, key=lambda combo: (-candidates[combo][0], -candidates[combo][1], combo))
    by_domain = {}
    for combo in order:
        pattern = tuple(sorted(registry[name]['domain'] for name in combo))
        by_domain.setdefault(pattern, []).append(combo)
    protected = {combo for values in by_domain.values() for combo in values[:c.CONFIG['triple_per_domain_multiset_quota']]}
    cap = c.CONFIG['triple_cap_per_target']
    if len(protected) > cap:
        raise ValueError('Domain quotas exceed the fixed triple budget; never silently truncate domains')
    selected = set(protected)
    for combo in order:
        if len(selected) >= cap:
            break
        selected.add(combo)
    result = sorted(selected)
    return dict(task_id=task['task_id'], candidates=result, proposed=len(order), domain_patterns=len(by_domain),
                domain_quota_candidates=len(protected), candidates_sha256=c.digest(result),
                diagnostic_candidates=[combo for combo in order if combo in selected][:c.CONFIG['coefficient_stability_replays_per_target']])


def domain_counts(task, registry, patterns):
    """Exact k=3 counts in domain multisets, including algebraic constraints."""
    names = task['predictors']
    name_set = set(names)
    domain = {name: registry[name]['domain'] for name in names}
    totals = {}
    for d in domain.values():
        totals[d] = totals.get(d, 0)+1
    index = {pattern: i for i, pattern in enumerate(patterns)}
    counts = np.zeros(len(patterns), dtype=np.int64)
    for pattern, i in index.items():
        multiplicity = {d: pattern.count(d) for d in set(pattern)}
        counts[i] = math.prod(math.comb(totals.get(d, 0), times) for d, times in multiplicity.items())
    edges = {tuple(sorted(pair)) for pair in task['edges'] if set(pair) <= name_set}
    adjacent = {name: set() for name in names}
    for a, b in edges:
        adjacent[a].add(b); adjacent[b].add(a)
        for d, n in totals.items():
            pattern = tuple(sorted([domain[a], domain[b], d]))
            counts[index[pattern]] -= n-int(domain[a] == d)-int(domain[b] == d)
    for center, neighbors in adjacent.items():
        for a, b in itertools.combinations(sorted(neighbors), 2):
            counts[index[tuple(sorted([domain[center], domain[a], domain[b]]))]] += 1
    triangles = set()
    for a, b in edges:
        for other in adjacent[a] & adjacent[b]:
            triangles.add(tuple(sorted([a, b, other])))
    for combo in triangles:
        counts[index[tuple(sorted(domain[n] for n in combo))]] -= 1
    for combo in {tuple(sorted(t)) for t in task['triples']}:
        if set(combo) <= name_set and not any(tuple(sorted(p)) in edges for p in itertools.combinations(combo, 2)):
            counts[index[tuple(sorted(domain[n] for n in combo))]] -= 1
    if np.any(counts < 0) or int(counts.sum()) != task['counts'][3]:
        raise ValueError('Domain-stratified triple counts disagree with exact V4 enumeration')
    return counts
