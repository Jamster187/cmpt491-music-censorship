"""Three search policies. This module has no access to benchmark truth."""
from __future__ import annotations
import collections
import itertools
import math
import time
import numpy as np

import strategy_v4_common as c
import strategy_v4_engine as engine
import cross_domain_v4_audit as audit
import hierarchical_v4_screen as old_screen


def pattern_counts(task, reg, names, k, domains):
    names = sorted(names); patterns = list(itertools.combinations_with_replacement(domains, k))
    if k == 3:
        temp = dict(task, predictors=names, counts=audit.count_combinations(names, task['edges'], task['triples']))
        return patterns, old_screen.domain_counts(temp, reg, patterns)
    counts = collections.Counter(reg[name]['domain'] for name in names)
    result = []
    for pattern in patterns:
        multiplicity = collections.Counter(pattern)
        result.append(math.prod(math.comb(counts[d], n) for d, n in multiplicity.items()))
    if k == 2:
        indexes = {p: i for i, p in enumerate(patterns)}; allowed = set(names)
        for edge in {tuple(sorted(e)) for e in task['edges']}:
            if set(edge) <= allowed:
                result[indexes[tuple(sorted(reg[n]['domain'] for n in edge))]] -= 1
    return patterns, np.asarray(result, dtype=np.int64)


class StratifiedPool:
    """Exact eligible counts and conditional probabilities for random exploration."""
    def __init__(self, task, reg):
        self.task, self.reg = task, reg
        self.groups = collections.defaultdict(list)
        for name in sorted(task['predictors']):
            self.groups[reg[name]['domain']].append(name)
        self.domains = sorted(self.groups)
        t = reg[task['target']]; all_names = set(task['predictors'])
        within = {n for n in all_names if reg[n]['domain'] == t['domain']}
        disjoint = {n for n in all_names if not set(reg[n]['source']) & set(t['source'])}
        strict = disjoint-within
        self.sizes, self.available = {}, collections.defaultdict(list)
        self.region_pools = dict(provenance_separated=strict, within_domain=within,
                                 cross_shared_source=all_names, other_cross_domain=all_names)
        for k in [1, 2, 3]:
            matrices = []
            for pool in [all_names, within, disjoint, within & disjoint, strict]:
                patterns, values = pattern_counts(task, reg, pool, k, self.domains); matrices.append(values)
            total, inside, no_shared, inside_no_shared, separated = matrices
            cross_shared = total-inside-no_shared+inside_no_shared
            other = total-inside-separated-cross_shared
            sums = np.zeros(len(patterns), dtype=np.int64)
            for region, values in [('within_domain', inside), ('provenance_separated', separated),
                                   ('cross_shared_source', cross_shared), ('other_cross_domain', other)]:
                if np.any(values < 0):
                    raise ValueError('Invalid stratified search-space accounting')
                sums += values
                for pattern, size in zip(patterns, values):
                    if size:
                        key = k, pattern, region
                        self.sizes[key] = int(size); self.available[k].append(key)
            if not np.array_equal(sums, total) or int(total.sum()) != task['counts'][k]:
                raise ValueError('Strata do not partition the unchanged eligible universe')

    def stratum(self, combo):
        return len(combo), tuple(sorted(self.reg[n]['domain'] for n in combo)), c.classification(self.task, combo, self.reg)['region']

    def draw(self, rng, k, seen, used=None):
        used = collections.Counter(self.stratum(combo) for combo in seen if len(combo) == k) if used is None else used
        choices = [key for key in self.available[k] if used[key] < self.sizes[key]]
        if not choices:
            return None, None
        key = choices[int(rng.integers(len(choices)))]; _, pattern, region = key
        allowed = self.region_pools[region]
        for attempt in range(100000):
            combo = []
            for domain, count in sorted(collections.Counter(pattern).items()):
                pool = [name for name in self.groups[domain] if name in allowed]
                combo.extend(rng.choice(pool, count, replace=False).tolist())
            combo = tuple(sorted(combo))
            if combo in seen or not c.eligible(self.task, combo) or c.classification(self.task, combo, self.reg)['region'] != region:
                continue
            return combo, dict(stratum=key, population_size=self.sizes[key],
                               stratum_probability=1/len(choices), conditional_candidate_probability=1/(self.sizes[key]-used[key]),
                               proposal_probability=1/len(choices)/(self.sizes[key]-used[key]),
                               probability_kind='exact conditional draw probability; predictor count follows a fixed balanced schedule')
        raise RuntimeError('Stratified rejection sampler did not reach an eligible candidate')


def screened_universe(task, reg, scores):
    order = sorted(task['predictors'], key=lambda n: (-round(scores[n], 12), n))
    keep = set(order[:c.CONFIG['a_global_seeds']])
    for domain in sorted({reg[n]['domain'] for n in order}):
        chosen, families = [], collections.Counter()
        for name in order:
            if reg[name]['domain'] == domain and families[reg[name]['family']] < 1:
                chosen.append(name); families[reg[name]['family']] += 1
            if len(chosen) == c.CONFIG['a_per_domain_seeds']:
                break
        keep.update(chosen)
    result = {}
    for k in [1, 2, 3]:
        choices = [combo for combo in itertools.combinations(sorted(keep), k) if c.eligible(task, combo)]
        choices.sort(key=lambda combo: (-round(sum(scores[n] for n in combo)/np.sqrt(k), 12), combo))
        selected, counts = [], collections.Counter()
        for combo in choices:
            signature = c.family_signature(combo, reg)
            if counts[signature] < c.CONFIG['diversity_signature_cap']:
                selected.append(combo); counts[signature] += 1
        result[k] = selected
    return result


def run(case, folds, strategy, seed, pool, store, budget):
    if strategy not in ['A', 'B', 'C']:
        raise ValueError('Unknown strategy')
    key = f'{case.key}/{strategy}/{seed}'
    saved = store.get('search', key)
    if saved is not None:
        return saved
    start = time.perf_counter(); task, reg = case.task, case.registry
    rng = np.random.default_rng(seed+int(c.digest(case.key)[:8], 16))
    domain_order = list(pool.domains); rng.shuffle(domain_order)
    marginal, pair_record, proposals = {}, None, None
    if strategy == 'A':
        pair_record = store.get('pairwise', key)
        if pair_record is None:
            marginal, diagnostics = engine.pairwise(folds, task['predictors'])
            pair_record = dict(scores=marginal, diagnostics=diagnostics)
            store.put('pairwise', key, pair_record)
        marginal = pair_record['scores']
        proposals = screened_universe(task, reg, marginal)
    events, seen, signature_counts, cursor = [], set(), collections.Counter(), collections.Counter()
    family_counts = collections.Counter()
    used_strata = collections.Counter()
    charged_pairwise = pair_record['diagnostics']['seconds'] if pair_record else 0.
    # Replayed events consume their original time; unfinished prefixes are kept.
    numerical_seconds = 0.; reconstruction_start = time.perf_counter()
    for step in range(c.CONFIG['combinations_per_cell']):
        cached = store.get('event', key+'/'+str(step))
        spent = charged_pairwise+numerical_seconds+max(0., time.perf_counter()-reconstruction_start)
        if cached is None and step >= len(domain_order) and spent >= c.CONFIG['search_seconds_per_cell']:
            break
        if step % 8 == 0:
            budget.check()
        path, probability = 'exploration', None
        if step < len(domain_order):
            domain = domain_order[step]; names = pool.groups[domain]
            name = min(names, key=lambda n: (-marginal[n], n)) if strategy == 'A' else str(rng.choice(names))
            combo = (name,); path = 'domain_floor'
            probability = dict(stratum=('domain_floor', domain), population_size=len(names),
                               proposal_probability=None if strategy == 'A' else 1/len(names),
                               probability_kind='deterministic pairwise winner' if strategy == 'A' else 'uniform within mandated domain floor')
        else:
            k = 1+(step-len(domain_order)) % 3
            explore = (strategy == 'B' or (strategy == 'A' and (step-len(domain_order)) % 4 == 0)
                       or (strategy == 'C' and (step < c.CONFIG['c_initial_random'] or step % 2 == 0)))
            combo = None
            if not explore and strategy == 'A':
                path = 'pairwise_exploitation'
                while cursor[k] < len(proposals[k]):
                    candidate = proposals[k][cursor[k]]; cursor[k] += 1
                    if candidate not in seen:
                        combo = candidate; break
            elif not explore and strategy == 'C':
                path = 'adaptive_exploitation'
                elite = sorted(events, key=lambda event: (-event['reward'], tuple(event['predictors'])))[:c.CONFIG['c_elite']]
                for _ in range(200):
                    if not elite:
                        break
                    parent = elite[int(rng.integers(len(elite)))]['predictors']
                    domain = domain_order[int(rng.integers(len(domain_order)))]
                    candidate = list(parent)
                    if len(candidate) >= k:
                        candidate = rng.choice(candidate, max(0, k-1), replace=False).tolist()
                    while len(candidate) < k:
                        add = str(rng.choice(pool.groups[domain])); domain = domain_order[int(rng.integers(len(domain_order)))]
                        if add not in candidate:
                            candidate.append(add)
                    candidate = tuple(sorted(candidate))
                    if (candidate not in seen and c.eligible(task, candidate)
                            and signature_counts[c.signature(candidate, reg)] < c.CONFIG['diversity_signature_cap']
                            and family_counts[c.family_signature(candidate, reg)] < c.CONFIG['diversity_signature_cap']):
                        combo = candidate; break
            if combo is None:
                combo, probability = pool.draw(rng, k, seen, used_strata); path = 'exploration'
            if combo is None:
                continue
            if probability is None:
                probability = dict(stratum=pool.stratum(combo), population_size=pool.sizes[pool.stratum(combo)],
                                   proposal_probability=None, probability_kind='adaptive/deterministic selection; no known inclusion probability')
        if combo in seen or not c.eligible(task, combo):
            raise ValueError('Search emitted a duplicate or ineligible candidate')
        event_start = time.perf_counter()
        if cached is not None:
            if tuple(cached['predictors']) != combo or cached['path'] != path:
                raise ValueError('Checkpoint recovery changed deterministic candidate order')
            event = cached; numerical_seconds += event['fit_seconds']
        else:
            models = {family: [engine.fit(fold, combo, family) for fold in folds] for family in c.CONFIG['model_families']}
            reward = max(engine.rank(results) for results in models.values())
            event = dict(step=step, predictors=combo, path=path, probability=probability,
                         models=models, reward=reward, classification=c.classification(task, combo, reg),
                         fit_seconds=time.perf_counter()-event_start,
                         signature=c.signature(combo, reg))
            store.put('event', key+'/'+str(step), event)
        events.append(event); seen.add(combo); signature_counts[c.signature(combo, reg)] += 1
        family_counts[c.family_signature(combo, reg)] += 1
        used_strata[pool.stratum(combo)] += 1
    selected = []
    for family in c.CONFIG['model_families']:
        order = sorted(events, key=lambda e: (-engine.rank(e['models'][family]), e['predictors']))
        diverse = collections.Counter()
        for event in order:
            signature = c.family_signature(event['predictors'], reg)
            if not np.isfinite(engine.rank(event['models'][family])) or diverse[signature]:
                continue
            selected.append(dict(predictors=event['predictors'], family=family, search_score=engine.rank(event['models'][family])))
            diverse[signature] += 1
            if sum(row['family'] == family for row in selected) >= c.CONFIG['confirm_per_model_family']:
                break
    elapsed = time.perf_counter()-start
    result = dict(key=key, strategy=strategy, seed=seed, case_key=case.key, status='COMPLETE' if len(events) == c.CONFIG['combinations_per_cell'] else 'CELL_BUDGET_STOP',
                  candidates=events, selected=selected, selected_sha256=c.digest(selected),
                  numerical_fit_attempts=4*len(events), unique_combinations=len(events),
                  pairwise_relationships=len(task['predictors']) if strategy == 'A' else 0,
                  elapsed_seconds=elapsed, charged_seconds=max(elapsed, charged_pairwise+sum(e['fit_seconds'] for e in events)),
                  enumeration_frozen_before_assessment=True)
    store.put('search', key, result)
    return result
