# V5.1 cross-domain robustness and replication

The fixed-candidate audit is complete: **30 candidates; 0 pass the full robustness rule; no independent replications**. Start with [findings](findings.md), [all outcomes](candidate_outcomes.csv) and [methodology](methodology.md). The original V5 results remain unchanged.

| File | Contents |
| --- | --- |
| [candidate_selection.csv](candidate_selection.csv), [selection_freeze.json](selection_freeze.json) | Frozen selection, original estimates, source roles, complete-ranking hashes and rules |
| [candidate_measurement_audit.csv](candidate_measurement_audit.csv) | Actual measurement definitions, source roles and nonzero-month support |
| [primary.csv](primary.csv) | Reproduced Pearson and rank estimates, uncertainty and support |
| [influence_diagnostics.csv](influence_diagnostics.csv) | Every year, five-year, recession and shock deletion |
| [observation_influence.csv.xz](observation_influence.csv.xz) | Complete leverage, Cook distance and exact native-period coefficient deletion |
| [block_influence.csv](block_influence.csv), [concentration_sensitivity.csv](concentration_sensitivity.csv) | Exposure/score concentration and block-origin sensitivity |
| [most_influential_periods.csv](most_influential_periods.csv) | Largest coefficient changes per candidate and deletion type |
| [temporal_sensitivity.csv](temporal_sensitivity.csv) | All fixed lag, window, trend, smoothing, HAC and breakpoint comparisons |
| [weighting_sensitivity.csv](weighting_sensitivity.csv) | All genre, rank, unique-song, coverage, confidence and composition comparisons |
| [bootstrap_intervals.csv](bootstrap_intervals.csv) | Both block-resampling intervals, failures and direction frequencies |
| [negative_controls.csv](negative_controls.csv), [null_simulation_summary.csv](null_simulation_summary.csv) | Block permutation, future/past placebos and dependent-data null calibration |
| [replication_status.csv](replication_status.csv), [external_source_reproduction.csv](external_source_reproduction.csv) | Reproduction vs robustness vs internal transfer vs genuinely independent evidence |
| [multiple_testing.csv](multiple_testing.csv) | Complete diagnostic comparison accounting; not selection-adjusted confirmation |
| [caring_exposure_audit.csv](caring_exposure_audit.csv) | Trace of the required caring–unemployment case using public BLS values |
| [figure_catalog.csv](figure_catalog.csv) | Seven deterministic shareable SVG figures |
| [validation.json](validation.json), [resource_ledger.json](resource_ledger.json) | Tests, preservation, replay, restart and cumulative resources |

Run from the canonical repository with the existing V5 Python environment (NumPy, pandas, SciPy, statsmodels, Matplotlib; versions recorded in the parent frozen protocol). No network acquisition or new dependencies are needed.

```bash
# Public-only integrity and numerical classification/accounting checks.
python3 src/robustness_v51_report.py verify

# Full retained-local audit; includes original data/V5 preservation.
python3 src/robustness_v51_report.py verify --private

# Deterministic numerical replay of one complete candidate, without replacing it.
python3 src/robustness_v51_report.py verify --private --replay C29

# Resume/reconstruct; existing frozen candidates and code must match.
python3 src/robustness_v51_select.py
python3 src/robustness_v51_runner.py run
python3 src/robustness_v51_report.py build
python3 -m unittest discover -s tests -v
```

Complete candidate checkpoints, bootstrap/permutation draws, preserved selection draft and source hashes remain ignored under `data/experiments/cross_domain_discovery_v5_robustness/`. These require retained V5 inputs, including restricted source snapshots absent from a fresh clone. Checkpoint recovery validates hashes and reuses completed work. A changed scientific protocol requires a separate version rather than overwriting this audit.

The result does not establish that all population associations are zero. It establishes that these selected candidates lack the complete robustness and independent-evidence requirements. No follow-on nonlinear or conditional campaign was started.
