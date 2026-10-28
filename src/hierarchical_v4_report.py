"""Publication and read-only integrity checks for the frozen hierarchical pilot."""
from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import pickle
import sqlite3
import zlib

import numpy as np
import pandas as pd

import hierarchical_v4_common as c


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Reader:
    """Never creates a table, repairs a record or changes a runtime segment."""
    def __init__(self, path):
        self.db = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)

    def get(self, kind, key):
        row = self.db.execute('SELECT payload,sha256 FROM records WHERE kind=? AND key=?', (kind, str(key))).fetchone()
        require(row is not None, 'Missing checkpoint '+kind+'/'+str(key))
        require(hashlib.sha256(row[0]).hexdigest() == row[1], 'Checkpoint checksum mismatch')
        return pickle.loads(zlib.decompress(row[0]))

    def keys(self, kind):
        return {int(row[0]) for row in self.db.execute('SELECT key FROM records WHERE kind=?', (kind,))}


def private_checks(mode='pilot', write=False):
    import hierarchical_v4_engine as engine
    import hierarchical_v4_run as runner
    import hierarchical_v4_screen as screen
    protocol = c.read_json(c.LOCAL/'frozen_protocol.json')
    for key in ['code', 'inputs']:
        for name, expected in protocol[key].items():
            require(c.sha(c.ROOT/name) == expected, 'Frozen '+key+' changed: '+name)
    tasks = c.tasks()
    cohorts = c.read_json(c.LOCAL/'cohorts.json')
    require(c.sha(c.LOCAL/'cohorts.json') == c.read_json(c.PUBLIC/'search_design.json')['cohort_catalog_sha256'], 'Cohorts changed')
    tasks = runner.pilot_tasks(tasks, cohorts) if mode == 'pilot' else tasks
    store = Reader(c.LOCAL/(mode+'.sqlite'))
    try:
        identity = c.digest([c.digest(protocol), mode, [t['task_id'] for t in tasks]])
        require(store.db.execute('SELECT value FROM identity').fetchone()[0] == identity, 'Run identity differs')
        ids = {t['task_id'] for t in tasks}
        require(store.keys('screen') == store.keys('stability') == ids, 'Incomplete task coverage')
        frozen = store.get('audit', 'frozen')
        require(frozen['scope_hash'] == c.digest([t['task_id'] for t in tasks]), 'Audit scope differs')
        require(frozen['independent_audit_hash'] == c.digest(frozen['draws']), 'Audit draw hash differs')
        selections, task_rows, coverage, signs, samples = {}, [], [], [], collections.defaultdict(list)
        for draw in frozen['draws']:
            samples[draw['task_id']].append(draw)
        seen = set()
        hits = collections.Counter()
        attempted = retained = selected_total = 0
        strata_sizes = collections.Counter()
        domains = sorted({r['domain'] for pop in ['song', 'monthly', 'genre_month'] for r in c.registry(pop).values()})
        patterns = list(itertools.combinations_with_replacement(domains, 3))
        for task in tasks:
            task_id = task['task_id']
            reg = c.registry(task['population'])
            first, last = store.get('screen', task_id), store.get('stability', task_id)
            lower, triples, values = first['lower'], first['triples'], last['results']
            require(lower['attempted_one'] == task['counts'][1] and lower['attempted_two'] == task['counts'][2], 'Lower-order count mismatch')
            total = task['counts'][1]+task['counts'][2]
            require(all(sum(s) == total for s in lower['status_counts']), 'Status ledger loses attempts')
            require(len(lower['attempt_digest']) == 64, 'Missing exhaustive score digest')
            rebuilt = screen.triples(task, lower, reg)
            require(rebuilt == triples, 'Triple screening replay differs')
            chosen = triples['candidates']
            selections[task_id] = chosen
            selected_total += len(chosen)
            names = last['variable_names']
            expected = chosen+[d['predictors'] for d in samples[task_id]]
            actual = [tuple(names[int(row[f])] for f in ['i', 'j', 'k']) for row in values]
            require(actual == expected, 'Stored candidate IDs differ from frozen selection/audit')
            require(values.dtype == runner.RESULT_DTYPE, 'Lossy or unsupported result schema')
            require(len(chosen) <= c.CONFIG['triple_cap_per_target'], 'Triple cap exceeded')
            require(last['selection_hash'] == triples['candidates_sha256'] == c.digest(chosen), 'Selection checksum differs')
            require(last['selected_count'] == len(chosen) and last['audit_count'] == len(samples[task_id]), 'Candidate count mismatch')
            require((values['audit'][:len(chosen)] == 0).all() and (values['audit'][len(chosen):] == 1).all(), 'Audit isolation flags differ')
            edges, forbidden = {frozenset(x) for x in task['edges']}, {frozenset(x) for x in task['triples']}
            counts = screen.domain_counts(task, reg, patterns)
            for pattern, count in zip(patterns, counts):
                strata_sizes[(task['population'], task['track'], pattern)] += int(count)
            for combo in chosen:
                strata_sizes[(task['population'], task['track'], tuple(sorted(reg[n]['domain'] for n in combo)))] -= 1
            for draw in samples[task_id]:
                combo = tuple(draw['predictors'])
                unit = task_id, combo
                require(unit not in seen and combo not in set(chosen), 'Audit is repeated or selected')
                seen.add(unit)
                require(len(set(combo)) == 3 and set(combo) <= set(task['predictors']), 'Invalid audit variable IDs')
                require(frozenset(combo) not in forbidden and not any(frozenset(p) in edges for p in itertools.combinations(combo, 2)), 'Ineligible audit model')
                stratum = frozen['strata'][draw['stratum']]
                require((stratum['population'], stratum['track'], tuple(stratum['domains'])) ==
                        (task['population'], task['track'], tuple(sorted(reg[n]['domain'] for n in combo))), 'Wrong audit stratum')
            skills = np.column_stack([values['skill_early'], values['skill_late']])
            increments = np.column_stack([values['increment_early'], values['increment_late']])
            statuses = np.column_stack([values['status_early'], values['status_late']])
            qualifies = runner.qualify(skills, increments, statuses, last['native_support'])
            require(np.array_equal(qualifies, values['qualifies'].astype(bool)), 'Stable qualification replay differs')
            selected_good = int(qualifies[:len(chosen)].sum())
            require(selected_good == last['selected_qualifying'], 'Selected qualifying count differs')
            task_hits = collections.Counter(d['stratum'] for i, d in enumerate(samples[task_id]) if qualifies[len(chosen)+i])
            require(dict(task_hits) == last['audit_hits'], 'Audit successes differ')
            hits.update(task_hits); retained += selected_good; attempted += total
            row = {key: task[key] for key in ['task_id', 'population', 'track', 'scope', 'target']}
            row.update(one=task['counts'][1], two=task['counts'][2], screen_estimable=lower['screen_eligible'],
                       retained_lower=len(lower['retained']), proposed_triples=triples['proposed'], selected_triples=len(chosen),
                       audit_triples=len(samples[task_id]), selected_qualifying=selected_good,
                       audit_qualifying=sum(task_hits.values()), screening_digest=lower['attempt_digest'],
                       candidates_sha256=triples['candidates_sha256'], bounds='|'.join(task['bounds']))
            for fold, support in zip([2, 3], last['native_support']):
                row.update({f'fold{fold}_{key}': value for key, value in support.items()})
            for fold in range(2):
                row.update({f'screen{fold}_{name}': int(count) for name, count in zip(engine.STATUS_NAMES, lower['status_counts'][fold])})
            task_rows.append(row)
            for item in lower['domain_coverage']:
                coverage.append(dict(task_id=task_id, population=task['population'], track=task['track'],
                                     **{**item, 'domains': '|'.join(item['domains'])}))
            coefficients = collections.defaultdict(dict)
            for item in last['coefficient_stability']:
                coefficients[tuple(item['predictors'])][item['fold']] = item['scalar_standardized_coefficients']
            comparable = agree = 0
            for folds in coefficients.values():
                a, b = folds.get(2), folds.get(3)
                if a is None or b is None:
                    continue
                for name in set(a) & set(b):
                    comparable += 1; agree += int(np.sign(a[name]) == np.sign(b[name]))
            signs.append(dict(task_id=task_id, population=task['population'], track=task['track'],
                              frozen_diagnostic_models=len(coefficients), scalar_comparisons=comparable,
                              same_sign=agree, same_sign_fraction=agree/comparable if comparable else None))
        require(c.digest(selections) == frozen['selection_hash'], 'Global selection hash differs')
        sample_counts = collections.Counter(d['stratum'] for d in frozen['draws'])
        published = c.read_json(c.PUBLIC/(mode+'_screening_audit.json'))
        stored = c.read_json(c.LOCAL/(mode+'_false_negative_estimate.json'))
        for i, item in enumerate(frozen['strata']):
            require(sample_counts[i] == item['sample_size'], 'Stratum sample count differs')
            require(strata_sizes[(item['population'], item['track'], tuple(item['domains']))] == item['population_size'], 'Omitted-universe count differs')
            require(stored['strata'][i]['qualifying_sample'] == hits[i], 'Published stratum successes differ')
        require(published['qualifying_sample_total'] == sum(hits.values()) and published['retained_qualifying'] == retained, 'Published screening audit differs')
        missed = sum(s['population_size']*hits[i]/s['sample_size'] for i, s in enumerate(frozen['strata']))
        require(np.isclose(missed, published['missed_qualifying_estimate'], rtol=1e-13), 'Miss estimator differs')
        execution = c.read_json(c.PUBLIC/(mode+'_execution.json'))
        require(execution['screening_models'] == attempted and execution['selected_triples'] == selected_total and execution['audit_triples'] == len(seen), 'Execution totals differ')
        checks = [check for row in store.db.execute('SELECT payload FROM timing') for check in json.loads(row[0]).get('reference_checks', [])]
        require(len(checks) == execution['reference_checks'] and all(r['scaled_mse_error'] <= 2e-7 for r in checks), 'Independent OLS checks differ')
        result = dict(status='PASS', scope=mode, tasks=len(tasks), lower_relationships=attempted,
                      lower_fold_attempts=2*attempted, selected_triples=selected_total,
                      audit_triples=len(seen), audit_strata=len(frozen['strata']),
                      selected_qualifying=retained, audit_qualifying=sum(hits.values()), reference_checks=len(checks),
                      frozen_code_files=len(protocol['code']), frozen_input_files=len(protocol['inputs']),
                      checkpoint_read_only=True)
        if write:
            c.write_csv(c.PUBLIC/(mode+'_target_ledger.csv'), task_rows)
            c.write_csv(c.PUBLIC/(mode+'_domain_coverage.csv'), coverage)
            c.write_csv(c.PUBLIC/(mode+'_coefficient_sign_stability.csv'), signs)
            c.write_json(c.PUBLIC/'validation.json', result)
        return result
    finally:
        store.db.close()


def documents():
    design = c.read_json(c.PUBLIC/'search_design.json')
    pilot = c.read_json(c.PUBLIC/'pilot_execution.json')
    gate = c.read_json(c.PUBLIC/'benchmark_gate.json')
    audit = c.read_json(c.PUBLIC/'pilot_screening_audit.json')
    signs = pd.read_csv(c.PUBLIC/'pilot_coefficient_sign_stability.csv')
    fraction = audit['false_negative_fraction_estimate']
    strata = pd.read_csv(c.PUBLIC/'pilot_audit_strata.csv')
    omitted = int(strata.population_size.sum())
    interval = audit['false_negative_fraction_simultaneous_interval']
    readme = f'''# Hierarchical cross-domain discovery V4

**Status: bounded pilot complete; full campaign {'eligible to launch' if gate['status'] == 'WITHIN_BUDGET' else 'not launched because the measured resource gate fails'}.** The revised design preserves the four-hour runtime and 15 GB temporary-storage limits. All original populations, raw/adjusted tracks, supported genre scopes, six calendar lags and 15 domains remain in scope. No economic or lyrical variable receives a subjective priority.

The complete design exhaustively attempts **{design['one_predictor_models']:,} one-predictor** and **{design['two_predictor_models']:,} two-predictor** relationships across **{design['target_tasks']:,} target tasks** in two screening periods. A fixed, domain-balanced rule retains at most **4,096 triples per target**, or **{design['selected_triple_cap']:,} selected triples**, with **131,072 independently sampled rejected triples** for the screening audit. This is a bounded additive three-predictor search, with no interaction terms or claim of exhaustive triple coverage.

| Resource | Revised plan / measured pilot | Limit |
| --- | ---: | ---: |
| Pilot wall time charged to campaign | {gate['benchmark_seconds']/60:.2f} minutes | 30-minute pilot cap |
| Pilot peak process memory | {pilot['peak_rss_bytes']/1024**3:.2f} GiB | Measured |
| Full computation projection before allowance | {gate['projected_seconds']/3600:.2f} hours | — |
| Conservative total including pilot | {gate['conservative_total_seconds']/3600:.2f} hours | 4 hours |
| Full temporary-storage projection | {gate['projected_temporary_storage_bytes']/1e9:.2f} GB | 15 GB |
| Pilot checkpoint | {pilot['local_checkpoint_bytes']/1e6:.1f} MB | Local only |

The gate uses actual measurements on this machine, shared-cohort preparation, measured target batches, maximum matching population/track rates, upward size scaling, a 1.5× compute allowance and 900 seconds for orchestration/reporting. It assumes no unmeasured parallel speedup. Resource projections are estimates for this implementation, not mathematical lower bounds for every possible implementation. The full command enforces the gate and pins its projection code. Restarted runs retain their cumulative runtime budget.

The pilot fully enumerated **{pilot['screening_models']:,} lower-order relationships** (**{pilot['exhaustive_screening_attempts']:,} screening-fold attempts**) for **{pilot['target_tasks']} deterministically selected target tasks**. It evaluated **{pilot['selected_triples']:,} selected triples** and **{pilot['audit_triples']:,} rejected audit triples** on two later periods. **{pilot['reference_checks']:,} independent full-row weighted SVD checks** agree with the fast engine; maximum baseline-scaled MSE discrepancy is {pilot['max_scaled_reference_mse_error']:.3g}. These pilot counts must not be represented as a completed all-target campaign.

The random audit found **{audit['qualifying_sample_total']:,} qualifying rejected triples**, sampled from **{omitted:,} omitted eligible triples** in the pilot's {len(strata):,} nonempty strata. The selected set contains **{audit['retained_qualifying']:,} qualifying triples**. Within this pilot task population, the estimated fraction of qualifying triples missed by screening is **{fraction:.3%}**, with a conservative simultaneous 95% interval of **{interval[0]:.3%}–{interval[1]:.3%}**. Many strata have only four draws, which limits precision. This is a design-based estimate conditional on a fixed predictive-stability criterion, not a causal false-negative rate. It does not estimate screening performance for the other target tasks. Audit outcomes never feed back into selection. The audit therefore does not support treating the screened triples as a near-exhaustive substitute. Many qualifying model combinations can describe the same underlying relationship, so this fraction is not a count of distinct missed scientific effects.

Read the [methodology](methodology.md), [benchmark gate](benchmark_gate.json), [execution ledger](pilot_execution.json), [target ledger](pilot_target_ledger.csv), [domain coverage](pilot_domain_coverage.csv), [random-audit estimates](pilot_screening_audit.json), [stratum estimates](pilot_audit_strata.csv), and [validation](validation.json), [engineering checks](engineering_validation.json), [audit replay](audit_replay_validation.json), and [launch-gate check](launch_gate_validation.json). The [parent V4 release](../cross_domain_discovery_v4/README.md) retains the complete input inventory, source reconciliation, exclusions and earlier exhaustive-search audit unchanged.

![Hierarchical search counts and resource gate](search_budget.svg)

## Reproduction

Public verification checks tracked artifacts and code only:

```bash
python3 src/hierarchical_v4_report.py verify
python3 -m unittest discover -s tests -p 'test_hierarchical_v4.py' -v
```

With the retained private parent views and dictionaries, reproduce/verify the bounded pilot:

```bash
python3 src/hierarchical_v4_run.py audit
python3 src/hierarchical_v4_run.py pilot
python3 src/hierarchical_v4_report.py build
python3 src/hierarchical_v4_report.py verify --private
```

Completed checkpoints are reused. A code, runtime or input mismatch fails explicitly; preserve and version the prior run before revising it. The `full` action is available only after a matching benchmark passes the unchanged runtime/storage gate. A failed gate does not authorize dropping domains, sampling one/two-predictor combinations, or raising either limit. Private predictors, embeddings, model metrics and checkpoints remain under ignored local storage. No acquisition or classification is performed.
'''
    methodology = f'''# Frozen hierarchical methodology

## Universe and preserved meanings

The [protocol](protocol.json) replaces exhaustive triple enumeration with deterministic screening. All {design['target_tasks']:,} parent target tasks remain: song, overall monthly and pooled/individual genre-month populations, raw/adjusted tracks, and calendar lags 0, 1, 3, 6, 12 and 24 months. The domains are {', '.join(design['domains'])}. Original exact Billboard title/artist identities, weighting, target support, algebraic exclusions, source aliases, native-frequency transformations and provenance remain defined by the [parent methodology](../cross_domain_discovery_v4/methodology.md). Chart dates remain distinct from release dates. Modern/revised information does not become historically available through calendar ordering.

All eligible original variables enter exhaustive one/two-predictor screening. Numeric variables retain training medians, scaling and missingness indicators; categorical vocabularies come from training data. The 384-dimensional semantic block remains one original predictor. Additive OLS retains the parent's training-only nuisance residualization in the adjusted track. This analysis cannot identify arbitrary nonlinear interactions or causal effects.

## Chronology and numerical eligibility

The four existing target-specific chronological folds and 84-month training embargo are preserved. Folds 0 and 1, covering approximately the 50–60% and 60–70% portions of each target's calendar span, determine all screening scores. The full candidate/audit catalog is frozen before folds 2 and 3 (approximately 70–80% and 80–100%) are accessed. Whole-song label availability restrictions remain in place. Prior campaigns inspected later historical years; these are forward-transfer checks, not newly untouched holdouts. Calendar gaps help separate periods but do not prove independent observations; see the [chronological split documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).

Every structurally eligible lower-order model is counted, including numerical failures. A variable block with fewer than eight residual degrees of freedom, an empty/constant representation, or within-block Gram condition exceeding 10^8 is explicitly flagged. Combined models require Schur minimum eigenvalue above 10^-8 and condition below 10^8. Numerical exceptions halt the run. These training-based eligibility rules can make wide blocks inestimable in short monthly samples; retaining a domain in the universe does not guarantee an estimable model in every task. Failure counts remain in the target ledger.

Training-centered, within-variable-whitened weighted Gram matrices and Schur complements evaluate exact float64 validation MSE. Cohorts share preparation only when population, track, genre scope, nuisance specification and all four train/validation row masks agree. Target batches contain at most eight columns. Independent full-row weighted SVD solves check the same losses. Lower-order arrays are streamed; each task retains exact attempt counts, status counts and a digest of all allowed IDs, losses and statuses. Unretained individual scores are reproducible from the pinned inputs, rather than saved billions of times.

## Objective screening and bounded triples

Skill is 1 minus held-out MSE divided by the training-mean baseline's held-out MSE. Rank eligible lower-order models by descending mean skill across the two screening folds, descending worst-fold skill, then exact predictor IDs. Ranking metrics are rounded to ten decimals for tie handling.

Retain the top 16 single-variable models globally plus four per represented domain. Retain the top 32 pairs globally plus two per unordered domain pair, including same-domain pairs. Quotas apply even to weak but estimable domains. Deduplicate the union; at most 348 lower-order seeds remain per task. No named economic or lyrical variable is privileged.

Propose each retained pair plus each retained single outside that pair; apply the original structural exclusions. Rank unique triples by the best generating pair's mean skill plus half the added single's mean skill, then the minimum of their worst-fold skills and exact IDs. Protect two triples per represented unordered domain multiset, then fill to 4,096 per target by the same global proxy. The maximum 680 multisets require at most 1,360 protected slots. A domain pattern with no estimable generating seeds cannot receive invented candidates. This proxy is reproducible, but suppressor effects can escape it; no sure-screening guarantee is asserted. The [original screening research](https://arxiv.org/abs/math/0612857) establishes guarantees under assumptions, not for every empirical screening rule.

## Independent historical stability

All frozen selected triples and all rejected audit triples are scored on folds 2 and 3. Each triple is compared with its best contained pair separately in each later fold; these pairs are fitted whether or not they survived screening. A triple qualifies only if both folds are estimable, both baseline-relative skills are positive, mean skill is at least 0.01, both incremental skills over the best pair are positive, and mean incremental skill is at least 0.005. The target needs at least 12 distinct native training reference periods and three validation reference periods in each later fold. Target native-period counts do not establish independence of repeated predictors, artists, songs or months.

Retained lower-order seeds also receive both later-fold scores. For 20 triples per target selected solely by the screening proxy, scalar coefficient signs are compared across later periods. Categorical and embedding coefficients are not assigned a single arbitrary sign. In the pilot, {int(signs.same_sign.sum()):,} of {int(signs.scalar_comparisons.sum()):,} comparable scalar signs agree. This descriptive stability diagnostic is not an inferential test and does not change selected candidates or the qualifying criterion. No causal, IID p-value or FDR claims are made.

## Independent random audit and false negatives

After freezing screening, enumerate the exact number of omitted eligible triples by population × track × unordered predictor-domain multiset. Inclusion-exclusion preserves the parent's forbidden edges/triples. All nonempty strata receive a minimum sample (16 full; four pilot), then allocate the remaining fixed total by proportional remaining capacity and deterministic largest remainders. Full/pilot totals are 131,072/16,384, bounded by the eligible omitted population. Seed 4914199 is separate from screening and task selection.

Within each stratum, choose target tasks proportional to their omitted eligible triple counts. Uniform domain-constrained draws are rejected within that chosen task until eligible and omitted; rejecting duplicates then gives simple random sampling without replacement. The audit uses the same fixed later-period qualifying rule as selected triples. Audit results are quarantined: no threshold, quota, variable, candidate or reported selection is retuned after seeing them.

For stratum s with omitted size M_s, sample n_s and qualifying count x_s, estimate missed qualifying triples by M_s × x_s/n_s and sum across strata. Divide the estimated missed count by itself plus the completely enumerated qualifying selected count to estimate the screening false-negative fraction. This ratio is a plug-in estimate, while the missed-total estimator is design-unbiased. Exact hypergeometric tail inversion supplies stratum intervals; Bonferroni-adjusted tails across all nonempty strata provide conservative simultaneous 95% bounds, summed and transformed to the fraction. This [hypergeometric model](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.hypergeom.html) describes sampling without replacement. Zero audit hits never imply zero possible misses. Intervals quantify audit sampling conditional on historical data and the operational criterion, not uncertainty in regression effects, causal truth or generalization to future periods.

The pilot audit covers only its 74 deterministic target tasks. It does not extrapolate to the other 10,023 tasks, and its many sparsely sampled strata can yield broad bounds. The random sample covers the entire omitted structural triple universe, including triples without any retained lower-order seed.

## Resource gate and reproducibility

The [benchmark](benchmark_gate.json) records measured rates for preparation, complete lower-order screening, candidate construction, later-period fits, pair comparisons, coefficient diagnostics and reference checks. The pilot selects tasks by support/feature/cohort size, without performance ranking, and uses complete rows and combinations within every selected task. Preparation is charged once per shared full-data cohort. Conservative projection uses the maximum observed two-fold preparation latency in each population/track, scales rows only beyond that stratum's maximum measured support, and adds conservative variable/target-width scaling. This avoids multiplying fixed setup latency by the ratio of a large cohort to a tiny cohort. Fitting is charged for the actual number of batches of at most eight targets, at the maximum measured batch rate per union candidate; screening/selection still scales per target/model relationship. Stability uses the maximum measured rate for each population/track. The estimate then adds 50% compute headroom, 900 seconds of overhead and pilot wall time. This projection-only refinement leaves the frozen screening rules, candidates, fits and audit outcomes unchanged. Storage includes a fixed 42-byte triple record, checkpoint/metadata allowance and extra overhead. It is an estimate, not a formal worst-case compressed-file bound; runtime storage checks enforce the hard 15 GB limit and 2 GiB free-space reserve.

Full execution requires the measured gate to pass and code/protocol hashes to match. SQLite records are immutable and checksummed; interrupted segments consume cumulative wall time through restart, so restarting cannot reset four hours. Chunk boundaries reserve 30 seconds for orderly stopping. An unfinished run never publishes itself as complete. CPU use is single-threaded; no speculative parallel speedup is credited. The earlier releases and immutable source/foundation remain unchanged.
'''
    c.atomic(c.PUBLIC/'README.md', readme.encode())
    c.atomic(c.PUBLIC/'methodology.md', methodology.encode())


def figure():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    design = c.read_json(c.PUBLIC/'search_design.json')
    gate = c.read_json(c.PUBLIC/'benchmark_gate.json')
    plt.rcParams.update({'svg.hashsalt': 'hierarchical-v4', 'font.size': 10})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), gridspec_kw={'width_ratios': [1.35, 1]})
    labels = ['Exhaustive singles', 'Exhaustive pairs', 'Selected triples (cap)', 'Random omitted-triple audit']
    counts = [design['one_predictor_models'], design['two_predictor_models'], design['selected_triple_cap'], design['independent_audit_triples']]
    axes[0].barh(labels, counts, color=['#286b8b', '#286b8b', '#d48a24', '#678c53'])
    axes[0].set_xscale('log'); axes[0].invert_yaxis()
    axes[0].set_xlabel('Target/model combinations (log scale)')
    axes[0].set_title('Frozen full design: all 15 domains', loc='left')
    for i, value in enumerate(counts):
        axes[0].text(value*1.12, i, f'{value:,}', va='center', fontsize=9)
    axes[0].set_xlim(1e4, 2e11)
    labels = ['Runtime', 'Temporary storage']
    ratios = [gate['conservative_total_seconds']/14400, gate['projected_temporary_storage_bytes']/15e9]
    axes[1].barh(labels, ratios, color=['#b45546' if v > 1 else '#678c53' for v in ratios])
    axes[1].axvline(1, color='black', linestyle='--', linewidth=1)
    axes[1].invert_yaxis(); axes[1].set_xlabel('Projected usage / user limit')
    axes[1].set_title('Measured implementation gate', loc='left')
    for i, value in enumerate(ratios):
        axes[1].text(value+.04, i, f'{value:.2f}×', va='center')
    axes[1].set_xlim(0, max(1.5, max(ratios)*1.3))
    for ax in axes:
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='x', alpha=.18); ax.set_axisbelow(True)
    fig.suptitle('Hierarchical V4 — benchmark precedes full launch', x=.02, ha='left', fontweight='bold')
    fig.tight_layout(rect=(0, .04, 1, .94))
    fig.text(.02, .015, 'Counts are planned structural coverage. Full campaign has not run. Storage uses decimal GB.', fontsize=9)
    fig.savefig(c.PUBLIC/'search_budget.svg', metadata={'Date': None})
    svg = c.PUBLIC/'search_budget.svg'
    c.atomic(svg, ('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n').encode())
    fig.savefig('/tmp/cmpt491_hierarchical_v4_budget.png', dpi=140)
    plt.close(fig)


def manifest():
    files = [p for p in c.PUBLIC.rglob('*') if p.is_file() and p.name != 'publication_manifest.json']
    files += list((c.ROOT/'src').glob('hierarchical_v4_*.py'))+[c.ROOT/'tests/test_hierarchical_v4.py']
    protocol = c.read_json(c.LOCAL/'frozen_protocol.json')
    files += [c.ROOT/name for name in protocol['code']]
    c.write_json(c.PUBLIC/'publication_manifest.json', dict(version=c.CONFIG['version'],
                 files={str(p.relative_to(c.ROOT)): {'bytes': p.stat().st_size, 'sha256': c.sha(p)} for p in sorted(set(files))}))


def verify(private=False):
    record = c.read_json(c.PUBLIC/'publication_manifest.json')
    for name, expected in record['files'].items():
        path = c.ROOT/name
        require(path.is_file() and path.stat().st_size == expected['bytes'] and c.sha(path) == expected['sha256'], 'Publication changed: '+name)
    gate = c.read_json(c.PUBLIC/'benchmark_gate.json')
    require(gate['projection_code_sha256'] == c.sha(c.ROOT/'src/hierarchical_v4_benchmark_report.py'), 'Projection code changed')
    output = dict(status='PASS', publication_files=len(record['files']), gate=gate['status'], full_campaign_started=False)
    if private:
        output['private'] = private_checks()
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['build', 'verify'])
    parser.add_argument('--private', action='store_true')
    args = parser.parse_args()
    if args.action == 'build':
        private_checks(write=True)
        c.write_json(c.PUBLIC/'frozen_protocol.json', c.read_json(c.LOCAL/'frozen_protocol.json'))
        documents(); figure(); manifest()
    print(json.dumps(verify(args.private), indent=2), flush=True)
