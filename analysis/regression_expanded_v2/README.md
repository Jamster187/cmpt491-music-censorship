# Exhaustive regression on expanded data, V2

**Executed exploratory campaign:** 1,311,090 task/candidate combinations, 5,244,360 validation/evaluation fits. All one-, two- and three-variable combinations were retained, including poor and rank-deficient models. Strict debut-time prediction is primary; a separately authorized retrospective sensitivity includes modern content and metadata measurements.

The clearest positive strict result is prediction of best rank within 26 weeks: evaluation **R² 0.305, MAE 21.892 ranks, RMSE 23.575 ranks**. The selected strict chart-weeks and chart-points models failed to generalize. The [findings](findings.md) include negative results, matched V1 comparisons and historical stability. The previously inspected 2018+ period is not fresh independent confirmation.

## Read the results

| Artifact | Purpose |
| --- | --- |
| [Methodology](methodology.md) | Prediction moment, availability, cohort selection, censoring, OLS, ranking and limitations |
| [Findings](findings.md) | Presentation-ready interpretation and numerical comparisons |
| [Target leaderboard](target_leaderboard.csv) | Validation-selected winners for all targets and original/new/combined universes |
| [Predictor hierarchy by count](predictor_hierarchy_top20_by_count.csv) | Top 20 at each of one, two and three variables in every universe; ranked only by validation |
| [Search space](search_space.csv) | Exact universe and candidate counts for every task/configuration |
| [Predictor inventory](predictor_inventory.csv) | Every variable's source, family, historical availability and encoding |
| [Source-column eligibility](source_column_eligibility.csv) | Inclusion, aliasing and exclusion decisions across source schemas |
| [Frozen protocol](protocol.json) | Pre-fit rules, source hashes and environment |
| [Frozen selections](selection_lock.json) | All overall and per-count winners locked before any evaluation |
| [Baselines](baselines.csv) | Training mean, training median and fitted debut-rank OLS |
| [Incremental information](incremental_information.csv) | New-only and combined differences from original-only on identical populations |
| [V1 comparison](v1_comparison.csv) | Identical evaluation outcomes/IDs; both primary and matched-training V2 refits |
| [Historical stability](historical_stability.csv) | Each selected model's performance and rank in all three periods |
| [Selected uncertainty](selected_uncertainty.csv) | Paired artist-credit and debut-year cluster intervals; excludes selection uncertainty |
| [Feature-family comparison](feature_family_comparison.csv) | Descriptive winner frequencies, not causal effects |
| [Focused feature comparisons](focused_predictor_comparison.csv) | Validation-selected best models including/excluding requested constructs |
| [Focused feature summary](focused_predictor_summary.csv) | Positive/negative ranges and winner counts for those constructs |
| [Cohorts](cohorts.csv) and [fold metadata](fold_metadata.json) | Fixed population sizes/hashes, period baselines and encoding support |
| [Coverage](coverage.json) | Complete candidate/fold counts and retained poor/singular results |
| [Local artifact manifest](local_artifacts.json) | Hashes, sizes and rows for all complete local hierarchies and predictions |
| [Figures](figures/manifest.json) | Five reproducible SVG figures, including matched V1 comparisons |

[Validation](validation.json) records completed integrity and direct-SVD checks: 530 tests ran successfully (514 passed, 16 skipped), 180 independent full-row SVD comparisons passed, all 32,723 fixed-window outcome rows were rebuilt, and all 246,564 protected files retained their hashes. [Deterministic replay](determinism.json) reproduced 96 numerical/model/hierarchy/figure artifacts byte for byte. `lifetime_return_audit.csv` quantifies the observed-history cohort's later-return limitation. These are produced by the validation commands below.

## Scope and interpretation

The strict inventory has **37 variables**: 5 original and 32 new. The retrospective inventory has **108**: 51 original and all 57 new constructs. A categorical block counts as one variable; season sine/cosine together also count as one. There are **8,473 strict** and **210,042 retrospective** candidates per outcome. Original/new rankings are subsets of this enumeration, not duplicate searches.

Each track has best rank, chart weeks and chart points for two windows. **Complete 26-week outcomes** are forward-looking primary targets and exactly match V1 definitions. **Observed-lifetime outcomes** use only history available at each cutoff, on a cohort at least five years old and inactive for two years. That rule does not prove a completed career or eliminate lifetime censoring. Source chart dates are not recording release dates. The latest source chart is 2026-09-19.

Three chronological validation periods select models before evaluation. Every candidate then receives evaluation metrics using pre-2018 training and eligible 2018+ debuts. Final target scores never choose predictor combinations. Retrospective results use modern labels and a selected content cohort; they are not historically deployable forecasts or directly comparable to strict results on a larger population.

## Reproduce

Work from the canonical repository root. Existing public exports and the feature-expansion V1 artifacts are required. No acquisition, classifier inference, private lyric access or prior-campaign rebuild is needed. The existing `requirements.txt` supplies the numerical dependencies; the frozen protocol records the exact runtime versions. A changed runtime or input hash intentionally fails checkpoint reuse.

```bash
python3 src/regression_expanded_spec.py preserve
python3 src/regression_expanded_spec.py audit
python3 src/regression_expanded_search.py benchmark
python3 src/regression_expanded_search.py run
python3 src/regression_expanded_report.py
python3 -m unittest discover -s tests -v > data/experiments/regression_expanded_v2/tests.log 2>&1
python3 src/regression_expanded_validate.py validate
python3 src/regression_expanded_validate.py snapshot
python3 src/regression_expanded_report.py
python3 src/regression_expanded_validate.py check-determinism
python3 src/repository_layout.py
python3 src/figure_audit.py --validate
python3 src/regression_expanded_validate.py publish-manifest
python3 src/regression_expanded_validate.py verify-publication
```

The first preservation command initializes a local snapshot if absent and verifies it otherwise. It never replaces an existing snapshot. On the original execution this covered 246,564 pre-existing files, including all source data and previous results. Fresh reproductions create their own prospective preservation baseline.

The measured benchmark took 13.1 seconds and projected a conservative 641.8-second campaign, below the frozen two-hour launch limit. The actual numerical search took **225.4 seconds** and peaked at **684.2 MiB** resident memory. Initial reporting took 161.7 seconds; the full deterministic replay took 162.5 seconds and peaked at 1.70 GiB. Preservation and validation are additional. Hardware, cache and filesystem conditions affect runtime. A local SQLite batch commits 256 models atomically; rerunning `run` resumes only missing batches. Exact code/data/protocol/candidate identity must match. Do not remove checkpoints to hide a mismatch.

Full hierarchies and SQLite stores remain under ignored `data/experiments/regression_expanded_v2/`; public summaries and selected model JSON files are under this directory. Large files are not committed. The public manifest records every complete hierarchy's row count and SHA-256. Each row includes overall and within-count validation ranks, original/new subset ranks, all three validation periods, final metrics, training R² and generalization gaps. A zero subset rank means the candidate is outside that subset. Equal-period validation aggregation is defined in the methodology; fold-level training/evaluation baseline details are in `fold_metadata.json`.

Query any task's complete local results without re-fitting:

```bash
python3 src/regression_expanded_report.py --query strict__26__best_rank --configuration combined --count 3 --limit 20
python3 src/regression_expanded_report.py --query retrospective__observed_lifetime__chart_points --configuration original --count 2 --limit 10
```

Use `--summary-only` to regenerate the findings and focused-feature summary from existing result CSVs. Selected model JSON exports contain their complete ordered encoder and coefficients. `regression_expanded_core.predict_model(model, frame)` replays them on matching feature rows. Overall winners have primary pre-2018 refits; the 26-week winners additionally have `__matched_v1.json` refits on the exact V1 pre-2010 training cohort.

## Preservation and navigation

The [campaign entry](../../docs/regression_expanded_v2.md) adds navigation without changing root documents that are hash-pinned dependencies of earlier publications. Source data, original regression campaigns and feature-expansion V1 retain their canonical paths and original hashes. `data/raw/` and the Phase 1 database remain read-only. Only this campaign's code, tests, documentation, summaries and selected SVG figures are published.
