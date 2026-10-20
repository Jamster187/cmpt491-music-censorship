"""Finite, outcome-blind discovery universes. No function launches a full campaign."""
from __future__ import annotations
import itertools
from functools import lru_cache
import json
from pathlib import Path

import regression_spec as old
import regression_relationships as relationships

ROOT = old.ROOT
PUBLIC = ROOT / 'analysis/relationship_discovery'
LOCAL = ROOT / 'data/experiments/relationship_discovery/pilot_v2'
SOURCE_COMMIT = '35c6782edc73dfce0991d52afd0a0c015cfbe7a6'
SEED = 4912026
VERSION = 'relationship-pilot-v2'
NUMERIC = sorted(set(old.original.NUMERIC) - {'best_chart_rank'})
ORDERED = ['best_chart_rank']
GENRES = list(old.original.GENRE_TAXONOMY)
CATEGORICAL = ['primary_genre'] + ['secondary_genre::' + g for g in GENRES]
VARIABLES = sorted(NUMERIC + ORDERED + CATEGORICAL)
OUTER = [(1990, 2000), (2000, 2010), (2010, 2018), (2018, 2026)]
METHODS = ['linear', 'quadratic', 'hinge25', 'hinge50', 'hinge75', 'spline4', 'spline6', 'tree2', 'tree3']
BREAKPOINTS = [1980, 1990, 2000, 2010, 2020]
ROLLING_STARTS = list(range(1960, 2016, 5))
PERIODS = [(1958, 1970)] + [(y, y+10) for y in range(1970, 2020, 10)] + [(2020, 2026)]
PANELS = {'content': [n for n in old.original.SCORES if n.startswith(('ll_', 'detox_'))],
          'affect': [n for n in old.original.SCORES if n.startswith(('emotion_', 'sentiment_'))],
          'all_lyrics': list(old.original.SCORES)}
MIN_TRAIN = 500
MIN_EVALUATION = 200
MIN_GROUP_TRAIN = 100
MIN_GROUP_EVALUATION = 100
MIN_YEAR = 30
BOOTSTRAPS = 499
PERMUTATIONS = 999
SIGN_FLIPS = 32767
CODE = ['src/relationship_discovery_spec.py', 'src/relationship_discovery_stats.py',
        'src/relationship_discovery_models.py', 'src/relationship_discovery.py']


def canonical(name):
    return 'secondary_genres' if name.startswith('secondary_genre::') else name


def domain(name):
    return relationships.domain(canonical(name))


def kind(name):
    if name in CATEGORICAL: return 'categorical'
    if name in ORDERED: return 'ordinal'
    if name in old.original.MB_COUNTS + old.original.HISTORY_COUNTS: return 'count'
    if name in old.original.DATES + ['mb_release_year']: return 'calendar'
    return 'continuous'


def classify(target, predictors):
    target = canonical(target)
    ps = [canonical(n) for n in predictors]
    result = relationships.classify(target, ps)
    # A secondary-genre membership flag is a component of the secondary genre set.
    # Two different flags share a family but do not determine each other.
    return result


def candidate(family, target, predictors=(), conditioner=None, **extras):
    row = dict(family=family, target=target, predictors=list(predictors), conditioner=conditioner, **extras)
    row['candidate_id'] = old.digest(row)[:20]
    row.update(classify(target, [*predictors] + ([conditioner] if conditioner in VARIABLES else [])))
    return row


def pair_candidates():
    for a,b in itertools.combinations(VARIABLES, 2):
        yield candidate('pairwise', b, [a])


def nonlinear_candidates():
    for y in NUMERIC:
        for x in NUMERIC:
            if x != y: yield candidate('nonlinear', y, [x])


def genre_candidates():
    for y in NUMERIC:
        for x in NUMERIC:
            if x != y: yield candidate('genre_interaction', y, [x], 'primary_genre')


def product_candidates():
    for y in NUMERIC:
        for x,z in itertools.combinations([n for n in NUMERIC if n != y], 2):
            yield candidate('numeric_interaction', y, [x], z)


def threshold_candidates(quantiles=(.25,.5,.75)):
    for y in NUMERIC:
        for x in NUMERIC:
            if x == y: continue
            for z in NUMERIC:
                if z in (x,y): continue
                for q in quantiles:
                    yield candidate('threshold_interaction', y, [x], z, quantile=q)


def hash_sample(rows, per_stratum, stratum):
    buckets = {}
    for row in rows:
        key = stratum(row)
        # Only the smallest hashes need to be retained; enumeration remains exhaustive.
        bucket = buckets.setdefault(key, [])
        bucket.append((old.digest([SEED, row['candidate_id']]), row))
        bucket.sort(key=lambda item:item[0])
        del bucket[per_stratum:]
    return sorted([r for b in buckets.values() for _,r in b], key=lambda r:r['candidate_id'])


@lru_cache(maxsize=1)
def pilot_candidates():
    pair_stratum = lambda r:(tuple(sorted([domain(r['target']),domain(r['predictors'][0])])),
        tuple(sorted([kind(r['target']) == 'categorical',kind(r['predictors'][0]) == 'categorical'])),r['category'][0])
    direct = lambda r:(domain(r['target']),domain(r['predictors'][0]),r['category'][0])
    rows = hash_sample(pair_candidates(), 1, pair_stratum)
    rows += hash_sample(nonlinear_candidates(), 1, direct)
    rows += hash_sample(genre_candidates(), 1, direct)
    # Fixed compact samples of the much larger triple universes. No outcome screening.
    rows += hash_sample(product_candidates(), 4, lambda r:r['category'][0])
    # Select triples first, then evaluate all three prespecified thresholds.
    triples = hash_sample(threshold_candidates((.5,)), 2, lambda r:r['category'][0])
    for r in triples:
        for q in (.25,.5,.75): rows.append(candidate('threshold_interaction',r['target'],r['predictors'],r['conditioner'],quantile=q))
    temporal = hash_sample((candidate('temporal',b,[a]) for a,b in itertools.combinations(NUMERIC+ORDERED,2)),
                          1, lambda r:tuple(sorted([domain(r['target']),domain(r['predictors'][0])])))
    rows += temporal
    for panel in PANELS:
        for method in ['pca','kmeans']:
            for k in ([2,5] if method=='pca' else [2,3]):
                rows.append(dict(candidate_id=old.digest(['structure',panel,method,k])[:20],family='structure',
                    target=panel,predictors=PANELS[panel],conditioner=None,method=method,k=k,
                    category='B: redundant/same-family',circular_rules=[],pure_cross_domain=False))
    return sorted(rows,key=lambda r:(r['family'],r['candidate_id']))


def configuration():
    return dict(version=VERSION,prior_pilot_results_seen=True,revision_reason='Constant-subgroup guard and explicit predictor-complete counts; candidate universe and selection rules unchanged from v1',seed=SEED,source_commit=SOURCE_COMMIT,unit='one exact title/artist song identity',
        population='songs.csv; observed history completed before 2026-01-01 for association/temporal analyses',
        outer_periods=OUTER,inner_rule='two consecutive five-year validation blocks ending at each outer start; expanding history; whole chart windows purged',
        methods=METHODS,minimum_train=MIN_TRAIN,minimum_evaluation=MIN_EVALUATION,
        minimum_group_train=MIN_GROUP_TRAIN,minimum_group_evaluation=MIN_GROUP_EVALUATION,
        minimum_year=MIN_YEAR,minimum_group_years=5,minimum_inference_blocks=8,
        bootstrap_repeats=BOOTSTRAPS,pairwise_within_year_permutations=PERMUTATIONS,
        paired_loss_block_sign_flips=SIGN_FLIPS,block_years=2,
        temporal_breakpoints=BREAKPOINTS,temporal_matched_years_each_side=5,rolling_width=10,
        rolling_starts=ROLLING_STARTS,periods=PERIODS,pilot_sampling='smallest seeded candidate hashes within predefined domain/type/category strata',
        pairwise_primary_test='permute the response within debut year; pooled statistic; conditional year-exchangeability null',
        inference='exploratory; block resampling assumes short-range dependence; no independent confirmation',
        multiple_testing='Benjamini-Yekutieli across all attempted pilot primary hypotheses; invalid/unavailable p values contribute p=1; also report family BY',
        preserve_categories='A retained in inventory; B retained and labelled; C strict; D/E are additional family tags, not replacements',
        ordinal='best_chart_rank: Spearman, dependence and temporal descriptions only; no cardinal-response regression',
        nominal='fixed genre labels/one-hot membership; never arbitrary numeric distances',
        status='PILOT ONLY; no full campaign command',test_previously_inspected=True)


def search_space():
    import math
    from collections import Counter
    p=len(NUMERIC);o=len(ORDERED);c=len(CATEGORICAL);n=p+o
    directed=p*(p-1);triples=p*math.comb(p-1,2);threshold=p*(p-1)*(p-2)*3
    pairs=math.comb(len(VARIABLES),2)
    temporal_pairs=math.comb(n,2);strata=1+len(GENRES)
    return dict(variables=dict(cardinal_numeric=p,ordinal=o,categorical=c,total=len(VARIABLES),numerical_targets=p,
                categorical_detail='one primary genre plus 16 secondary membership flags; no new genre classification'),
        pairwise=dict(candidates=pairs,numeric_or_ordinal_pairs=math.comb(n,2),numeric_categorical_pairs=n*c,
            categorical_pairs=math.comb(c,2),pearson=math.comb(p,2),spearman=math.comb(n,2),mutual_information=pairs,
            distance_correlation=math.comb(n,2),eta_squared=n*c,cramers_v=math.comb(c,2),primary_tests=pairs),
        nonlinear=dict(candidates=directed,method_variants=len(METHODS),nested_fit_upper_bound=directed*len(OUTER)*(2*len(METHODS)+2)),
        genre_interaction=dict(candidates=directed,fit_upper_bound=directed*len(OUTER)*2),
        numeric_interaction=dict(candidates=triples,fit_upper_bound=triples*len(OUTER)*2),
        threshold_interaction=dict(candidates=threshold,fit_upper_bound=threshold*len(OUTER)*2),
        conditional_correlations=dict(pair_group_cells=temporal_pairs*(len(GENRES)+len(PERIODS)),
            optional_numeric_threshold_cells=p*(p-1)*(p-2)*3*2),
        temporal=dict(pairs=temporal_pairs,strata=strata,annual_estimates=temporal_pairs*strata*68,
            rolling_estimates=temporal_pairs*strata*len(ROLLING_STARTS),breakpoint_comparisons=temporal_pairs*strata*len(BREAKPOINTS),
            formal_p_values='not certified; pilot reports block intervals and inadequate-block flags'),
        structure=dict(panels=3,pca_ranks=[2,5,10],cluster_counts=[2,3,4,5],
            pca_decompositions_with_five_stability_refits=3*4*6,clustering_fits_with_five_stability_refits=3*4*4*6),
        pilot_counts=dict(Counter(r['family'] for r in pilot_candidates())),full_campaign_launched=False)
