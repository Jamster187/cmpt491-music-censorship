# Exhaustive three-predictor OLS experiment

Implementation and a bounded actual-data pilot are complete. **The exhaustive
campaign has not been launched.** Read the [current report](../../docs/regression_search_plan.md)
for measured runtime, findings, exact counts and the launch decision.

| Location | Contents |
|---|---|
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

After explicit approval, the commands are:

```bash
python3 src/regression_search.py campaign --execute-full --workers 1
# Re-run the identical command to resume committed batches.
python3 src/regression_search.py hierarchy --task songs:detox_toxicity --output /tmp/toxicity.csv.gz
python3 src/regression_search.py hierarchy --task songs:detox_toxicity --k 2 --limit 20 --output /tmp/toxicity-two.csv
# Only after every target's validation search has finished:
python3 src/regression_search.py finalize --evaluate-final-test
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
