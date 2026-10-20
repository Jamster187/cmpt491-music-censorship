# Regression-search planning artifacts

Read the [planning report](../../../docs/regression_search_plan.md) first.
This is an unapproved search specification and a bounded feasibility audit,
not a trained exhaustive campaign.

| Artifact | Purpose |
|---|---|
| `audit_manifest.json` | Audited Git revision, recent commits, provenance, input hashes |
| `dataset_inventory.json` | Eight current public/preprocessing files, dimensions and hashes |
| `schema_inventory.csv` | All 511 table/field entries: types, missingness, cardinality, timing, provenance |
| `category_counts.csv` | Full categorical distributions |
| `variable_catalog.json` | Conceptual variables, encodings and non-target/excluded fields |
| `target_inventory.csv` | All 73 target tasks, model families, support and transformations |
| `predictor_sets.json` | Explicit allowed predictors and exclusions per target; forbidden subsets |
| `search_counts.csv`, `search_totals.json` | Exact counts for k=1,2,3,4; matrix dimensions |
| `split_summary.csv` | Per-target/block observed rows, song counts, complete cases and cluster ESS diagnostic |
| `target_category_split_counts.csv` | Class/label support, including absent levels |
| `data_findings.json` | Verified schema, preprocessing, redundancy and coverage findings |
| `forecast_constraints.json` | Why retrospective counts are not an as-of forecasting specification |
| `benchmark_samples.csv` | Exactly 192 sampled predictor sets and actual matrix dimensions |
| `benchmark_timings.csv`, `benchmark_results.json` | OLS/Ridge timings, numerical checks, RSS, hardware and versions |
| `runtime_estimates.csv`, `feasibility_estimates.json` | Exact-stratum runtime extrapolation, fit multiplicity and storage |
| `validation_results.json` | Planning checks and existing-suite limitations |
| `artifact_manifest.json` | Hashes of deliverables, excluding this manifest itself |

Reproduction, from the repository root:

```bash
python3 analysis/planning/regression_search/audit.py
python3 analysis/planning/regression_search/benchmark.py
python3 analysis/planning/regression_search/estimate.py
python3 analysis/planning/regression_search/render_report.py
python3 -m unittest discover -s analysis/planning/regression_search -p 'test_*.py' -v
```

Use the existing scientific Python environment; recorded benchmark versions
differ from some repository pins. Nothing installs or modifies dependencies.
Run timing alone, not concurrently with the full test suite. The audit can take
longer than the timing sample because it scans all columns of all eight files.

The full candidate family is the sorted 1–4-variable subsets of each target's
`predictors`, excluding supersets of its `forbidden_subsets`. `audit.py` counts
these analytically. `benchmark.py` fits only 64 deterministic sets per resolution
and excludes test rows. The scripts have no exhaustive-fit command. Re-running
records the then-current HEAD and refreshed timings, so output hashes may change.

All original data and analyses remain read-only. Generated planning inventories
live only here, except the requested report under `docs/`.
