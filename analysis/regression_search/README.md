# Exhaustive three-predictor OLS experiment

**The authorized full numerical campaign is complete:** 59 targets, 1,998,901
eligible combinations and 5,996,703 validation fits, followed by final evaluation
of the 59 validation winners. Read the [full results](../../docs/regression_search_results.md)
for measured resources, all target rankings, interpretation and validation.
The [prelaunch pilot report](../../docs/regression_search_plan.md) remains historical evidence.

| Location | Contents |
|---|---|
| [campaign/target_leaderboard.csv](campaign/target_leaderboard.csv) | All 59 validation-selected models: validation/test metrics, baselines, N, gaps, stability and intervals |
| [campaign/best_by_predictor_count.csv](campaign/best_by_predictor_count.csv) | All 177 best one-, two- and three-variable models by validation |
| [campaign/historical_stability.csv](campaign/historical_stability.csv) | Chosen model's rank in each historical period and each period's winner |
| [campaign/hierarchy_manifest.json](campaign/hierarchy_manifest.json) | Local paths, sizes, row counts and hashes for all 1,998,901 exported hierarchy rows |
| [campaign/hierarchy_top10_per_target.csv](campaign/hierarchy_top10_per_target.csv) | Small top-ten extract per target; complete hierarchy stays local |
| [campaign/selected_models.json](campaign/selected_models.json) | Exact selected variables, common model specification and local fitted-artifact hashes |
| [campaign/run_summary.json](campaign/run_summary.json) | Actual measured runtime, RAM/disk, checks and generalization flags |
| [campaign/coverage_before_test.json](campaign/coverage_before_test.json), [coverage_after_test.json](campaign/coverage_after_test.json) | Exhaustive coverage, deterministic rankings, split checks and unchanged selection hashes |
| [specification/](specification/) | Current data hashes/schema, all 73 targets, allowed predictors, exact counts, splits and censoring audit |
| [pilot/predictor_hierarchy.csv](pilot/predictor_hierarchy.csv) | View A: every sampled combination, including poor models, ranked within target |
| [pilot/best_by_predictor_count.csv](pilot/best_by_predictor_count.csv) | Best sampled one-, two- and three-variable models |
| [pilot/target_leaderboard.csv](pilot/target_leaderboard.csv) | View B rehearsal: validation-selected models evaluated on held-out 2014–2017 songs |
| [pilot/historical_stability.csv](pilot/historical_stability.csv) | Selected model's rank and skill in each earlier period |
| [pilot/professor_demo.txt](pilot/professor_demo.txt) | Working trained-model demonstration and interpretation |
| [pilot/professor_model.json](pilot/professor_model.json) | Small reproducible public-data demo model; no lyrics |
| [pilot/professor_actual_vs_predicted.csv](pilot/professor_actual_vs_predicted.csv) | Deterministic 40-song display sample; reported metrics use the whole rehearsal test |
| [pilot/runtime_estimate.json](pilot/runtime_estimate.json) | Measured throughput, runtime extrapolation, memory and disk |
| [specification/categorical_ordinal_tasks.csv](specification/categorical_ordinal_tasks.csv) | Separate native-family task registry and appropriate metrics; no invented OLS results |

The pilot's 2014–2017 rehearsal holdout is distinct from the campaign's 2018-onward
test. The timing pilot uses the full campaign training/validation populations,
without scoring the final test. Neither pilot establishes the exhaustive winners.

From the repository root, using the existing scientific Python environment:

```bash
python3 src/regression_search.py audit
python3 -m unittest discover -s tests -p 'test_regression_search.py' -v
python3 src/regression_search.py pilot
python3 src/regression_search.py demo
python3 analysis/regression_search/render_report.py
```

The pilot is hard bounded to 1,179 unique combinations across nine targets. It
also checks an interrupted search against an uninterrupted replay and runs a
second bounded pass for full-population timing. All fits use at most three
original predictors. The historical four-predictor feasibility benchmark in
`analysis/planning/regression_search` is superseded and must not be used as the
current run command.

Full results/checkpoints live under ignored `data/experiments/regression_search/`.
SQLite stores one candidate catalog plus three metric rows per combination;
the `hierarchy` SQL view ranks the complete results. There are no millions of
fitted objects. One final model JSON per target is saved only after selection.

The completed run used the exact implementation from commit `426fdf1`. These
commands reproduce it or resume existing results with matching code/data/library
versions. The supplied execution wrapper additionally checks frozen code/data and
measures resources; it does not change search methodology:

```bash
python3 analysis/regression_search/measure_campaign.py search
# Re-run the identical command to resume committed batches.
# Only after every target's validation search has finished:
python3 analysis/regression_search/campaign_report.py before-test
python3 analysis/regression_search/measure_campaign.py resume_probe
python3 analysis/regression_search/measure_campaign.py finalize
python3 analysis/regression_search/campaign_report.py after-test
python3 analysis/regression_search/campaign_report.py export
python3 analysis/regression_search/publish_campaign.py
```

`before-test` intentionally refuses to run after final evaluation; use `after-test`
to recheck an already completed campaign. The underlying engine commands remain
`python3 src/regression_search.py campaign --execute-full --workers 1` and
`python3 src/regression_search.py finalize --evaluate-final-test`.

Complete rankings already exist locally as 59 compressed CSVs under
`data/experiments/regression_search/campaign/hierarchies/`. Each target directory
also has a `results.sqlite` database with a complete `hierarchy` SQL view,
`selection.json`, `selected_model.json` (encoder, coefficients and baselines),
split membership and final prediction files. These large artifacts are ignored.
To regenerate or filter an individual hierarchy without fitting models:

```bash
python3 src/regression_search.py hierarchy --task songs:detox_toxicity --output /tmp/toxicity.csv.gz
python3 src/regression_search.py hierarchy --task songs:detox_toxicity --k 2 --limit 20 --output /tmp/toxicity-two.csv
```

The full command refuses to run without its launch flag. Final evaluation first
checks all 59 completed searches and freezes every winner, then refits/evaluates.
Changed code, inputs, candidate lists, numerical-library versions or model
specifications invalidate resume. Use a new output directory for a deliberate
new specification; never recycle final test results to tune it.

Two or three target workers are supported, each with one BLAS thread. The
reported estimate assumes the measured single worker; parallel speedup is not
promised. Keep enough disk for SQLite journals and exported rankings.

View A ranks by equal-period mean baseline-relative MSE skill. It also includes
mean period R²/MAE, square root of mean period MSE, sample sizes, baselines and
per-period results. View B sorts final targets by test R², with baseline skill,
coverage and uncertainty alongside it. Raw MAE is never compared across target
units. Unsupported constant/category columns are recorded and receive no fitted
coefficient; the conceptual combination is still evaluated.

The professor demo replays the saved coefficients and verifies every saved
prediction. Its plot is in [the documentation assets](../../docs/assets/regression_search_professor_demo.png).
Large splits, predictions, checkpoints and other models stay local; the small
demo is the explicit public-data exception.
