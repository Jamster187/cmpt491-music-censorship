# V5 exhaustive music × historical discovery

The authorized pairwise campaign is complete: **759,696 population-specific pairs**, six lags, two tracks and **18,046,656 method hypotheses**. It retains every planned comparison, including failures and null estimates. **712** pair/track rows meet at least one global BY threshold; this is exploratory association, not causal or untouched confirmatory evidence.

**No adjusted lyrical lead combined broad temporal variation with two positive chronological transfer folds.** The post-fit audit flags concentrated variation in 603 of the 712 corrected rows; the four broadly supported adjusted rows are calendar-timing patterns. See the [interpretation audit](interpretation_audit.json), [complete corrected table](corrected_relationships_complete.csv) and [source-informed measurement roles](corrected_by_measurement_role.csv) before treating a small q value as a substantive musical finding.

Start with [findings and all four requested top-20 tables](findings.md), the [methodology](methodology.md), [domain summary](domain_summary.csv), [coverage/status counts](coverage_and_status.csv) and [figure catalog](figure_catalog.csv).

| File | Purpose |
| --- | --- |
| [variable_inventory.csv](variable_inventory.csv), [exclusion_log.csv](exclusion_log.csv) | Complete variable accounting, definitions, source/frequency/availability and structural exclusions |
| [search_space.csv](search_space.csv), [search_counts.json](search_counts.json) | Complete work-unit enumeration and exact pair/method denominators |
| [raw_relationships.csv](raw_relationships.csv), [adjusted_relationships.csv](adjusted_relationships.csv) | First 200 rows from each complete ranking |
| [genre_relationships.csv](genre_relationships.csv), [between_genre_relationships.csv](between_genre_relationships.csv) | First 200 within-genre and composition rows |
| [historical_stability.csv](historical_stability.csv), [lagged_relationships.csv](lagged_relationships.csv) | First 200 stability and lagged rows |
| [financial_relationships.csv](financial_relationships.csv), [macroeconomic_relationships.csv](macroeconomic_relationships.csv), [political_social_relationships.csv](political_social_relationships.csv) | First 200 rows of each domain ranking |
| [multiple_testing.csv](multiple_testing.csv), [multiple_testing_summary.json](multiple_testing_summary.json) | Up to 200 corrected leaders and full global-family accounting |
| [leaderboard_catalog.csv](leaderboard_catalog.csv) | Complete local ranking sizes, definitions and hashes |
| [weighting_sensitivity.csv](weighting_sensitivity.csv), [composition_comparison_summary.json](composition_comparison_summary.json) | Saved-estimate weighting and fixed/matched-composition comparisons |
| [adjusted_monthly_fix.json](adjusted_monthly_fix.json), [synthetic_validation.json](synthetic_validation.json) | Reproduced V4 failure, span-preserving fix and independent null validation |
| [benchmark.json](benchmark.json), [resource_ledger.json](resource_ledger.json) | Required pre-execution resource gate and cumulative active computation |
| [validation.json](validation.json), [integrity_validation.json](integrity_validation.json) | Complete coverage, independent numerical checks, restart/replay and source preservation |

Public CSVs are explicitly **summaries**. The canonical complete local results are in the ignored `data/experiments/cross_domain_discovery_v5/`: `results.npy` (all 9,116,352 typed rows), `checkpoints.sqlite` (all atomic work units), `categorical_contrasts.csv` (descriptive category-effect intervals), and ten `rankings/*.npy` index arrays. Row offsets in the public search-space table and the local view metadata make every result reversible. No private lyrics or raw restricted economic observations are published.

## Verify or export

Run from the canonical repository root with the recorded Python/package environment in [frozen_protocol.json](frozen_protocol.json). Dependencies are the existing NumPy, pandas, SciPy, statsmodels, Matplotlib and threadpoolctl installation; no new service or acquisition is required.

```bash
# Public files only; available in a fresh clone.
python3 src/pairwise_v5_report.py verify

# Full local checkpoints/results, independent BY and deterministic sampled replay.
python3 src/pairwise_v5_report.py verify --private --replay

# Read any complete ranking. --limit is optional; omit to export every row.
python3 src/pairwise_v5_report.py export --ranking adjusted --limit 1000 --output /tmp/v5_adjusted.csv

python3 -m unittest discover -s tests -p test_pairwise_v5.py -v
```

Ranking names are `raw`, `adjusted`, `historically_stable`, `financial`, `macroeconomic`, `political_social`, `within_genre`, `between_genre`, `lagged`, and `multiple_testing`. Large full CSV exports are optional and can exceed the remaining disk allowance; the compact index arrays already provide complete rankings without duplicate data.

## Reproduce or resume offline

The full build requires the retained V4 monthly/genre views and historical/financial snapshots listed in the frozen input hashes. Some restricted inputs are intentionally absent from a fresh clone. Original source files and older analyses must remain unchanged. Exact hashes of the derived analysis inputs are in [derived_input_hashes.json](derived_input_hashes.json).

```bash
python3 src/pairwise_v5_data.py
python3 src/pairwise_v5_diagnostics.py fix
python3 src/pairwise_v5_runner.py benchmark
python3 src/pairwise_v5_diagnostics.py stationarity
python3 src/pairwise_v5_runner.py run
python3 src/pairwise_v5_runner.py finalize
python3 src/pairwise_v5_report.py build
python3 src/pairwise_v5_report.py verify --private --replay
```

The runner requires a passing synthetic validation and resource gate; it refuses changed compute code/protocols or corrupt checkpoints. Re-running `run` with the same frozen protocol verifies and reuses completed chunks. The published 100-chunk deliberate stop/resume is recorded in [restart_initial.json](restart_initial.json). A new scientific specification requires a new versioned campaign directory, preserving this completed attempt. The four-hour ledger is cumulative across commands/resumes; it does not reset with a new process. A crashed command is conservatively charged until resumed.

The seven SVG figures are deterministic, shareable statistical summaries. Their numerical content comes from completed estimates; no raw restricted historical-value traces are embedded. Temporary PNG previews are outside the repository so the frozen earlier figure catalog remains unchanged.

Any conditional, nonlinear, interaction or multivariate campaign, and any additional data acquisition, requires separate authorization.
