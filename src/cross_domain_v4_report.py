"""Publish the bounded V4 audit without exposing private measurements or models."""
from __future__ import annotations

import argparse
import io
import json
import lzma
import pickle
import platform
import sys
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

import cross_domain_v4_common as c
import cross_domain_v4_audit as audit
import cross_domain_v4_pilot as pilot


def compact_search_space():
    detailed = c.PUBLIC / 'search_space_by_target.csv.xz'
    current = pd.read_csv(c.PUBLIC / 'search_space.csv')
    if 'task_id' in current:
        c.atomic(detailed, lzma.compress((c.PUBLIC / 'search_space.csv').read_bytes()))
    else:
        current = pd.read_csv(detailed)
    keys = ['population', 'track', 'scope', 'category', 'k']
    grouped = current.groupby(keys, sort=True).agg(
        target_tasks=('task_id', 'nunique'), combinations=('combinations', 'sum'),
        planned_fits=('planned_fits', 'sum')).reset_index()
    c.write_csv(c.PUBLIC / 'search_space.csv', grouped)
    counts = current.loc[current.category.eq('unrestricted')].groupby('k').combinations.sum()
    expected = c.read_json(c.PUBLIC / 'audit.json')['structurally_eligible_combinations']
    if int(counts.sum()) != expected:
        raise ValueError('Detailed and aggregate search spaces disagree')
    return counts


def runtime_environment():
    from threadpoolctl import threadpool_info, threadpool_limits
    with threadpool_limits(limits=1):
        libraries = [{key: value for key, value in row.items() if key != 'filepath'}
                     for row in threadpool_info()]
    c.write_json(c.PUBLIC/'runtime_environment.json', dict(
        python=sys.version, system=platform.system(), os_release=platform.release(),
        machine=platform.machine(), pilot_blas_threads=1,
        packages={name: version(name) for name in ['numpy', 'scipy', 'pandas', 'matplotlib', 'threadpoolctl']},
        numerical_libraries=libraries))


def native_support(tasks):
    """Count source reference periods, never infer effective independent sample size."""
    rows = []
    for pop in audit.POPULATIONS:
        registry = c.read_json(c.LOCAL / (pop + '_registry.json'))
        frame = c.load_frame(pop + '.pkl')
        for track in ['raw', 'adjusted']:
            values = audit.numeric_view(frame, registry, track)
            for task in (t for t in tasks if t['population'] == pop and t['track'] == track):
                ix = np.arange(len(frame)) if task['scope'] == 'pooled' else np.flatnonzero(frame.primary_genre.eq(task['scope']))
                subset = frame.iloc[ix].reset_index(drop=True)
                target = task['target']
                definition = registry[target]
                y = values[target].to_numpy()[ix]
                if definition['origin'] == 'external':
                    periods = pilot.period_end()[definition['base']].reindex(pd.PeriodIndex(subset.month, freq='M')).to_numpy()
                else:
                    periods = subset.month.to_numpy()
                for number in range(4):
                    train, valid = audit.masks(subset, y, task['bounds'], number)
                    rows.append(dict(task_id=task['task_id'], population=pop, track=track,
                                     scope=task['scope'], target=target, target_origin=definition['origin'],
                                     native_frequency=definition['frequency'], fold=number,
                                     training_rows=int(train.sum()), validation_rows=int(valid.sum()),
                                     training_months=int(subset.loc[train, 'month'].nunique()),
                                     validation_months=int(subset.loc[valid, 'month'].nunique()),
                                     training_target_reference_periods=int(pd.Series(periods[train]).nunique()),
                                     validation_target_reference_periods=int(pd.Series(periods[valid]).nunique())))
    body = pd.DataFrame(rows).to_csv(index=False, lineterminator='\n').encode()
    c.atomic(c.PUBLIC / 'native_frequency_support.csv.xz', lzma.compress(body))
    return len(rows)


def figure(counts, benchmark):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'svg.hashsalt': 'cmpt491-v4-audit'})
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.7), constrained_layout=True)
    bars = axes[0].bar(['One', 'Two', 'Three'], [counts[k] for k in [1, 2, 3]], color=['#477998', '#31688e', '#153e5c'])
    axes[0].set_yscale('log')
    axes[0].set_ylabel('Structurally eligible models (log scale)')
    axes[0].set_xlabel('Original predictor variables per model')
    axes[0].set_title('Complete audited search universe')
    for bar, value in zip(bars, counts):
        axes[0].annotate(f'{value:,.0f}', (bar.get_x()+bar.get_width()/2, bar.get_height()),
                         ha='center', va='bottom', xytext=(0, 4), textcoords='offset points', fontsize=9)
    axes[0].set_ylim(1, max(counts)*20)
    storage = benchmark['projected_temporary_storage_bytes']/1e9
    axes[1].bar(['User limit', 'Designed full run'], [15, storage], color=['#477998', '#b94b45'])
    axes[1].set_yscale('log')
    axes[1].set_ylabel('Temporary storage, decimal GB (log scale)')
    axes[1].set_title('Full execution exceeds the approval gate')
    for x, value in enumerate([15, storage]):
        axes[1].annotate(f'{value:,.0f} GB', (x, value), ha='center', va='bottom', xytext=(0, 4), textcoords='offset points')
    axes[1].set_ylim(1, storage*10)
    for ax in axes:
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', alpha=.15)
        ax.set_axisbelow(True)
    fig.suptitle('V4 audit and computational pilot — no full-search discoveries', fontsize=13)
    buffer = io.StringIO()
    fig.savefig(buffer, format='svg', metadata={'Date': None})
    c.atomic(c.PUBLIC/'search_budget.svg', ('\n'.join(line.rstrip() for line in buffer.getvalue().splitlines())+'\n').encode())
    plt.close(fig)


def documents(counts, benchmark):
    a = c.read_json(c.PUBLIC/'audit.json')
    v = c.read_json(c.PUBLIC/'view_validation.json')
    b = benchmark
    timing = pd.read_csv(c.PUBLIC/'benchmark_strata.csv')
    rank_deficient = int(timing.rank_deficient.sum())
    summary = []
    for pop in audit.POPULATIONS:
        for track in ['raw', 'adjusted']:
            d = a['summary'][pop][track+'::pooled']
            summary.append(f"| {pop} | {track} | {d['targets']:,} | {d['predictors']:,} | {d['combinations']:,} |")
    readme = f'''# Cross-domain discovery V4: audit and gated pilot

**Status: full execution stopped at the user's four-hour / 15 GB resource gate.** The complete structural audit and representative computational pilot are finished. No exhaustive result ranking, top-20 scientific findings, final evaluation fits, confidence intervals or multiple-testing discoveries have been produced. No scope reduction has been substituted for the requested exhaustive search.

The audit contains **{a['target_tasks']:,} target tasks**, **{a['structurally_eligible_combinations']:,} target/model combinations** and **{a['planned_fits']:,} planned fold fits**. A target task is a population × track × genre scope × target. Targets recur across tasks; this is not a count of distinct scientific constructs. Candidate counts are structural, before numerical estimability checks.

The pilot fitted **{b['unique_validation_fits']:,} unique validation models** ({b['unique_pilot_relationships']:,} sampled relationships across three folds), plus reference-check computation, for **{b['representative_target_tasks']} representative tasks**. It made **{b['numerical_fit_calls_including_reference_checks']:,} numerical fit calls** and **zero final-evaluation fits**. All {b['checkpoint_rows']:,} checkpoint rows were reopened and verified. The {b['independent_svd_checks']:,} independent full-row SVD checks passed.

Of those validation fits, {rank_deficient:,} were rank-deficient and remain diagnostics, not candidate scientific discoveries. The [bounded-pilot findings](findings.md) summarize the gate and the limitations revealed by the audit.

| Resource | Measurement or projection | User limit |
| --- | ---: | ---: |
| Pilot wall time, including audit projection | {b['elapsed_seconds']/60:,.2f} minutes | Bounded pilot |
| Pilot process peak resident memory | {b['peak_rss_bytes']/1024**3:,.2f} GiB | Measured, not extrapolated |
| V4 local artifacts at pilot completion | {b['actual_local_bytes']/1e9:,.3f} GB | Local only |
| Full run, optimistic sampled-rate projection | {b['optimistic_measured_rate_seconds']/86400:,.1f} days | 4 hours |
| Full run, conservative projection | {b['conservative_total_seconds']/86400:,.1f} days | 4 hours |
| Core full-result metric payload | {b['designed_core_storage_bytes']/1e12:,.3f} TB | 15 GB temporary storage |
| Designed full temporary storage | {b['projected_temporary_storage_bytes']/1e12:,.3f} TB | 15 GB |

These time figures extrapolate the existing single-thread OLS engine, not a measured full run or a guaranteed lower bound for other algorithms/hardware. The core storage design uses two float64 losses and one uint16 rank/status per candidate per fold; other metrics derive from fixed fold constants. Compression or a different storage design would require a revised, validated plan. Storage independently fails the gate even if compute is made much faster. The script cannot launch a full campaign.

| Pooled population | Track | Eligible target variables | Union of eligible predictors | Model combinations |
| --- | --- | ---: | ---: | ---: |
{chr(10).join(summary)}

The genre-month search additionally audits all 16 observed primary-genre scopes. Some scopes have no chronologically supported tasks; they remain visible in [audit.json](audit.json). Counts above do not include those additional genre-specific tasks. All scopes and the six overlapping category views appear in [search_space.csv](search_space.csv); do not sum overlapping category views. Exact per-target metadata are compressed in [search_space_by_target.csv.xz](search_space_by_target.csv.xz).

## Evidence and interpretation

- [Methodology](methodology.md) defines identity, weighting, chronology, adjusted tracks, aliases, eligibility, and the inferential limitations.
- [Variable inventory](variable_inventory.csv) lists domains, sources, dependencies, availability, lag, transformation and support for every candidate; [target coverage](target_coverage.csv) records exclusion reasons.
- [External crosswalk](series_crosswalk.csv), [source exclusions](source_exclusions.csv), and [music exclusions](music_source_exclusions.csv) document exact aliases and unsupported fields. The external view has {v['canonical_external_series']} canonical series after {v['verified_aliases']} verified financial/platform alias decisions; these are not {v['canonical_external_series']} independent constructs.
- [Native-frequency support](native_frequency_support.csv.xz) reports row, month and target reference-period counts per fold. Reference periods are not effective independent sample sizes.
- [Benchmark](benchmark.json), [timing strata](benchmark_strata.csv), [direct OLS checks](ols_reference_checks.csv), [runtime versions](runtime_environment.json), and [protocol](analysis_protocol.json) are machine-readable evidence.
- [Validation](validation.json), [engineering checks](engineering_validation.json), and [publication manifest](publication_manifest.json) support read-only verification. Restricted measurements, model metrics, embeddings and checkpoints remain in ignored local storage.

![Search size and storage gate](search_budget.svg)

## Reproduction

Run from the repository root using the existing project Python dependencies. Source acquisition and classification are unnecessary. Public verification needs only tracked files:

```bash
python3 src/cross_domain_v4_report.py verify
python3 -m unittest discover -s tests -p 'test_cross_domain_v4.py' -v
```

Rebuilding the bounded pilot requires the retained local source releases and private embedding evidence listed in [input_manifest.json](input_manifest.json). No lyrics are emitted. Preserve the existing protocol and checkpoints before changing analysis code or inputs; mismatches fail rather than silently reusing old results.

```bash
python3 src/cross_domain_v4_common.py preserve
python3 src/cross_domain_v4_data.py
python3 src/cross_domain_v4_audit.py
python3 src/cross_domain_v4_pilot.py
python3 src/cross_domain_v4_report.py build
python3 src/cross_domain_v4_report.py verify --private
python3 src/cross_domain_v4_common.py verify
```

The pilot command is bounded and rechecks previously saved model records on rerun. It does not execute the exhaustive campaign. The report command compacts the full audit CSV while preserving its per-target contents in XZ. Existing [project handoff](../../docs/PROJECT_STATE_HANDOFF.md), data releases and prior analysis artifacts retain their canonical paths and bytes.

The next decision is an explicit revision of scope or compute/storage budget, as required by the user's V4 resource gate. A larger budget alone does not establish that this machine can run the search. Any reduced campaign must be separately labelled and must not be represented as the original exhaustive V4 request.
'''
    methodology = '''# V4 bounded-pilot methodology

This document describes the frozen computational pilot and complete structural audit. It does not claim that a full inferential study has been implemented or run. All reported search sizes refer to this explicit protocol, not every conceivable analysis of these data.

## Population, identities and source reconciliation

The song view has one row for each of the 28,041 exact original Billboard title/artist identities, anchored to first chart month. All 70 original song fields are checked for exact string equality before enrichment is used. Eleven existing finite-window chart outcomes are included, with the original right-censoring masks; three lifetime-outcome aliases are checked equal to the existing chart measures and represented once. A title by another credited artist remains a different asset. The snapshot's reported upstream is mhollingshead/billboard-hot-100; this is attribution, not independent verification.

The 818 monthly and 7,173 genre-month rows aggregate the original 81,797 monthly source observations. All three repeated song/month source observations are retained, matching the enrichment release's denominator. Each field has its own nonmissing denominator; neither unavailable lyrics nor unavailable audio is encoded as zero. Song analysis weights each song once; monthly analysis weights each month once; pooled genre-month analysis gives each month total weight one across its available genres. This differs from the historical distinct-song-month moving-average pipeline and does not rewrite it.

Original scores, existing engineered numeric features, qualified audio/metadata, eligible chart outcomes and current chart-period metrics are inventoried. Categorical variables count as one original variable even when training-vocabulary encoding produces several columns. The existing 384-dimensional semantic representation counts as one predictor block, never 384 scalar discoveries; it remains private. A block containing a scalar outcome cannot predict that outcome. Audio/lyric coverage, modern models and retrospective metadata restrict interpretation to measured subsets and retrospective associations.

The two external releases are reconciled through declared source/formula equivalence and every overlapping nonmissing value is checked. The platform value is preferred; an explicit verified financial extension may fill missing earlier/warmup periods. Close names alone do not merge series. Different volatility definitions, log/simple returns and CPI-SA/NSA real-wage definitions remain separate. Provider provenance propagates through derived series. Dictionaries and inputs are hash-pinned.

Monthly reference keys preserve quarterly and annual native periods as repeated context, with the original period end retained. Change/growth is computed on the native grid before repetition; missing periods are not skipped. Repetition does not increase independent economic observations. Daily series use existing documented monthly aggregates; the last actually observed market date and observation count are recorded without inventing a closing price or a trading calendar. Congressional labels remain retrospective term summaries, not daily control. Electoral-vote results appear only in election months, without carry-forward or zero-filling. NBER announcement events remain distinct from retrospectively dated recessions.

## Chronology and eligibility

External predictors are evaluated at calendar lags 0, 1, 3, 6, 12 and 24 months: X at t−L predicts Y at t. For positive lags, the source period must end before the target month starts. Thus an unfinished quarter/year is not a past observation merely because its repeated monthly key was shifted. Same-series target/predictor lags shorter than the target's native period are excluded. Same-month reference context remains retrospective association. Current/revised economic observations and whole-month returns do not become historically available forecasts. Original-edition release dates are unverified, so release-aligned sensitivity is unavailable; chart dates are not release dates.

Each target's observed calendar span defines boundaries at 50%, 60%, 70%, 80% and 100%. Three chronological validation intervals follow the initial training segment; the last 20% is reserved for later evaluation. Training expands with an 84-month embargo: the maximum 24-month lag plus the longest finite 60-month rolling window. Whole-song chart labels must be available before the training cutoff or validation end, using the later of the last observed chart date and 26-week outcome endpoint. No song is split across rows within the song population. Cumulative/lifetime constructs can retain dependence beyond a finite embargo, so the embargo is not proof of independent folds.

Target cohorts are fixed across competing models and never imputed. Every fold needs at least 30 training rows, 12 validation rows, 24 training months and six validation months. Training targets must vary. Predictors need at least 20 observed training rows, six observed training months and variation in every validation-fold training set. Final-evaluation support is audited through availability counts; its outcome variation and performance are not used for predictor selection. Chronology is based on calendar months, not row positions. Sparse native-period support is separately reported and must be addressed before inferential use.

Numeric predictors use training medians plus a missingness indicator. Categorical levels and centering/scaling are learned from training rows only. Unknown future categories use the baseline encoding and should be interpreted as unsupported category transfer. No correlation, effect size, final-evaluation score or subjective importance screen removes a supported variable. The candidate audit removes explicit target containment and declared algebraic identities in every direction; broader conceptual overlap stays labelled. These rules do not prove every candidate is identifiable. Rank-deficient/overparameterized attempts must remain recorded statuses and cannot become scientific discoveries.

## Raw, adjusted and category views

The raw track uses retained levels and original music measurements. The adjusted track transforms positive economic level endpoints to 100×log(current/prior), signed/general levels to native first differences, and retains rates, returns, growth, events and other explicitly registered change/stress measures. These rules are visible per variable. They are transformations, not an assertion of stationarity. Pooled song and genre-month adjustment includes genre indicators; monthly non-genre-share targets include composition shares. Time trend and annual sine/cosine controls are fitted on training data. Weighted training-only Frisch–Waugh–Lovell projection residualizes both outcomes and candidate columns; validation uses those same fitted nuisance coefficients. Nuisance variables are not counted among the one, two or three original candidate predictors.

Every supported target is counted with all structurally allowed one-, two- and three-variable combinations. The enumeration uses exact graph/hypergraph inclusion-exclusion, tested against full brute-force enumeration on small randomized fixtures. Six category views are retained: unrestricted, cross-domain, provenance-separated, within-music, within-external and music/external crossing. They overlap and are not additive. Cross-domain means a different registered domain; provenance-separated additionally requires no shared recorded provider roots. These labels are operational metadata categories, not guarantees of statistical or conceptual independence.

## Pilot, ranking design and inference boundary

The pilot deterministically chooses the minimum, median and maximum training-row target task in each pooled population/track and one sparse genre task per track. A fixed seed samples up to 16 combinations in each predictor-count × numeric/categorical-or-small-block/embedding stratum. It uses all actual training/validation rows and all three validation folds. Cached OLS and sparse metric evaluation are compared with independent full-row weighted SVD solves. Numerical fallback and rank deficiency are retained. The checkpoint pins V4 analysis modules and inputs; publication verification additionally pins the shared OLS engine. Result checksums detect corrupted records. Reopening every record verifies restart access; regression fixtures verify idempotent reuse and deliberate corruption rejection.

The prospective predictive ranking uses mean validation skill relative to the training-mean baseline, then worst-period skill, fewer original variables and deterministic IDs. MSE, MAE and R² are computational diagnostics. The final evaluation is never used for selection and has zero fits in this pilot. Earlier studies have already inspected later years; future evaluation of this campaign is chronological transfer evidence, not a pristine untouched historical test.

No IID p-values, confidence intervals, significant discoveries or selected-model-only FDR adjustment are reported. Monthly shared exposures, repeated artists/songs, autocorrelation, native-frequency repetition and revised measurements preclude treating source rows as independent replicates. A later inferential campaign must freeze its estimands, native-period support thresholds, dependence treatment and full attempted-testing family before execution. A dependence-robust multiplicity method cannot rescue invalid component p-values. The [Benjamini–Yekutieli paper](https://projecteuclid.org/journals/annals-of-statistics/volume-29/issue-4/The-control-of-the-false-discovery-rate-in-multiple-testing/10.1214/aos/1013699998.full) provides a possible arbitrary-dependence FDR reference; this is not a claim that it was applied. Standard [HAC implementation assumptions](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html) do not justify applying rowwise HAC to repeated genre/song rows. Calendar-block or native-period-aware inference and training-only robustness checks remain unimplemented pending the resource decision.

Full-search top-20 lists, corrected significance tables, stability findings, counterfactuals, causal explanations and relationship plots are deliberately absent because the full search has not run. The only figure describes search counts and the resource gate. Preservation, fit correctness and a successful pilot establish engineering readiness for a revised plan, not scientific discoveries.
'''
    c.atomic(c.PUBLIC/'README.md', readme.encode())
    c.atomic(c.PUBLIC/'methodology.md', methodology.encode())
    support = pd.read_csv(c.PUBLIC/'native_frequency_support.csv.xz')
    annual = support.loc[support.native_frequency.eq('A')]
    event = support.loc[support.native_frequency.eq('event')]
    findings = f'''# V4 bounded-pilot findings

The requested exhaustive scientific search has **not run**. The engineering audit and computational pilot reached the user's mandatory runtime/storage gate. No top-20 relationships, corrected significance findings or final-evaluation results are available.

| Original predictors | Structurally eligible target/model combinations |
| --- | ---: |
| One | {counts[1]:,} |
| Two | {counts[2]:,} |
| Three | {counts[3]:,} |
| Total | {a['structurally_eligible_combinations']:,} |

The full design would attempt {a['planned_fits']:,} fold fits. Its current storage design needs {b['projected_temporary_storage_bytes']/1e12:,.3f} TB, compared with the 15 GB limit. Sampled-rate compute projections range from {b['optimistic_measured_rate_seconds']/(86400*365.25):,.1f} to {b['conservative_total_seconds']/(86400*365.25):,.1f} years on the existing single-thread implementation. Those projections are not lower bounds for every possible engine, compression scheme or machine. They are sufficient to reject executing this design within the existing four-hour budget.

The pilot contains {b['unique_validation_fits']:,} validation fits, {b['independent_svd_checks']:,} independent full-row OLS checks and {b['restart_rows_verified']:,} reopened checkpoint records. Final-evaluation models fitted: **zero**. Pilot metrics remain local and were not used to choose a new scope or publish relationship rankings.

Two audit findings require attention in any revised scientific plan:

- {rank_deficient:,} pilot fits were rank-deficient, including {int(timing.loc[timing.encoding.eq('embedding_block'), 'rank_deficient'].sum()):,} with the embedding block. Numerical predictions from an overparameterized model do not establish an estimable scientific relationship.
- Some annual-target tasks have only {int(annual.training_target_reference_periods.min())} distinct training reference years and {int(annual.validation_target_reference_periods.min())} validation years despite many repeated rows. Event targets can have only {int(event.validation_target_reference_periods.min())} validation reference event. Structural row/month eligibility is not sufficient inferential eligibility. Native-period support and dependence handling must be frozen before a later inferential campaign.

The complete audited catalog remains preserved. Reducing variables, lags, genre scopes, predictor counts, or retained output detail would change the requested design and needs an explicit decision. Increasing the budget would also require a feasible implementation and storage plan. No unapproved reduction or new statistical campaign was substituted after the gate failed.

See the [run summary](README.md), [methodology](methodology.md), [benchmark](benchmark.json), [native-period support](native_frequency_support.csv.xz) and [engineering checks](engineering_validation.json). All prior source datasets and analysis outputs retain their original bytes.
'''
    c.atomic(c.PUBLIC/'findings.md', findings.encode())


def publish_manifest():
    files = [p for p in c.PUBLIC.iterdir() if p.is_file() and p.name != 'publication_manifest.json']
    files += list((c.ROOT/'src').glob('cross_domain_v4_*.py'))
    files += [c.ROOT/'src/regression_core.py', c.ROOT/'tests/test_cross_domain_v4.py']
    c.write_json(c.PUBLIC/'publication_manifest.json', dict(
        version=c.VERSION, files={str(p.relative_to(c.ROOT)): dict(bytes=p.stat().st_size, sha256=c.sha(p))
                                 for p in sorted(files)}))


def verify(private=False):
    manifest = c.read_json(c.PUBLIC/'publication_manifest.json')
    for name, expected in manifest['files'].items():
        path = c.ROOT/name
        if not path.is_file() or c.sha(path) != expected['sha256'] or path.stat().st_size != expected['bytes']:
            raise ValueError('Publication mismatch: '+name)
    a = c.read_json(c.PUBLIC/'audit.json')
    b = c.read_json(c.PUBLIC/'benchmark.json')
    detailed = pd.read_csv(c.PUBLIC/'search_space_by_target.csv.xz')
    full = detailed.loc[detailed.category.eq('unrestricted')]
    if int(full.combinations.sum()) != a['structurally_eligible_combinations'] or int(full.planned_fits.sum()) != a['planned_fits']:
        raise ValueError('Catalog count mismatch')
    if b['full_campaign_started'] or b['evaluation_models_fitted'] != 0:
        raise ValueError('Unexpected full/evaluation execution')
    expected_gate = (b['conservative_total_seconds'] <= b['limits']['runtime_seconds'] and
                     b['projected_temporary_storage_bytes'] <= b['limits']['temporary_storage_bytes'] and
                     b['projected_temporary_storage_bytes']+b['limits']['headroom_bytes'] <= b['free_disk_bytes'])
    if expected_gate != (b['status'] == 'WITHIN_BUDGET'):
        raise ValueError('Incorrect resource gate')
    if private:
        for name, sha in c.read_json(c.PUBLIC/'input_manifest.json').items():
            if c.sha(c.ROOT/name) != sha:
                raise ValueError('Source input changed: '+name)
        protocol = c.freeze()
        tasks = pickle.loads((c.LOCAL/'tasks.pkl').read_bytes())
        if c.sha(c.LOCAL/'tasks.pkl') != a['task_catalog_sha256']:
            raise ValueError('Local task catalog mismatch')
        counted = sum(sum(audit.count_combinations(t['predictors'], t['edges'], t['triples']).values()) for t in tasks)
        if counted != a['structurally_eligible_combinations']:
            raise ValueError('Private task enumeration mismatch')
        store = pilot.Store(c.LOCAL/'pilot.sqlite', protocol)
        count = store.db.execute('SELECT COUNT(*) FROM results').fetchone()[0]
        store.close()
        if count != b['checkpoint_rows']:
            raise ValueError('Pilot checkpoint coverage mismatch')
    return dict(status='PASS', publication_files=len(manifest['files']), private=private,
                target_tasks=a['target_tasks'], structurally_eligible_models=a['structurally_eligible_combinations'],
                full_campaign_started=False, evaluation_models_fitted=0)


def build():
    b = c.read_json(c.PUBLIC/'benchmark.json')
    runtime_environment()
    tasks = pickle.loads((c.LOCAL/'tasks.pkl').read_bytes())
    counts = compact_search_space()
    rows = native_support(tasks)
    figure(counts, b)
    documents(counts, b)
    checks = pd.read_csv(c.PUBLIC/'ols_reference_checks.csv')
    c.write_json(c.PUBLIC/'validation.json', dict(
        status='PASS', phase='bounded_audit_and_pilot', native_support_rows=rows,
        reference_checks=len(checks), max_prediction_scaled_error=float(checks.max_prediction_scaled_error.max()),
        original_release_preservation=c.preservation(), full_campaign_started=False,
        evaluation_models_fitted=0, discoveries_reported=0))
    publish_manifest()
    print(json.dumps(verify(True), indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['build', 'verify'])
    parser.add_argument('--private', action='store_true')
    args = parser.parse_args()
    if args.action == 'build':
        build()
    else:
        print(json.dumps(verify(args.private), indent=2), flush=True)
