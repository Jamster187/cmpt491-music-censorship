# Local feature expansion v1

Completed local engineering and exploratory prediction campaign for songs already on the Billboard Hot 100. Read [findings](findings.md) with the [methodology](methodology.md). The prior 2018-onward test population was already inspected. No external acquisition, new content-classifier inference, or COVID analysis was performed.

The [navigation and command note](../../docs/feature_expansion_v1.md) explains why the hash-pinned original root navigation files remain unchanged. All new reproduction instructions live with this campaign and its separate dataset.

The separate [versioned dataset](../../data/public/feature_expansion_v1/README.md) contains 32,723 exact weekly identities, 58 new columns representing 57 constructs, and separate outcomes. It preserves the existing 28,041-song release. Of 59 researched local candidates, 48 are implemented; [dispositions](candidate_dispositions.csv) explain the rest.

| Artifact | Purpose |
|---|---|
| [Frozen protocol](protocol.json) | Prediction moment, windows, cohorts, tuning and seeds |
| [Feature dictionary](feature_dictionary.csv) | Definitions, sources, availability, missingness and risks |
| [Coverage](coverage_report.csv) | All-weekly and final-study denominators |
| [Model comparison](model_comparison.csv) | All three methods, A/B/C, five outcomes, train/validation/test |
| [Selected models](selected_models.csv) | Choices made on validation only |
| [Incremental improvements](incremental_improvements.csv) | Matched-cohort baseline/new/combined effects |
| [Simple baselines](simple_baselines.csv) | Majority, prevalence, historical credit, mean and median |
| [Predictions](selected_predictions.csv.gz) | Selected models, validation and test; no raw lyrics |
| [Permutation importance](permutation_importance.csv) | Validation-only ranking, three repeats |
| [Coefficients/tree importance](coefficient_tree_importance.csv) | All validation-tuned linear/tree configurations |
| [Ablations](feature_ablation.csv) | Remove each predefined feature group |
| [Uncertainty](uncertainty.csv) | 199 paired artist-credit/year cluster resamples |
| [Historical and horizon checks](historical_sensitivity.csv) | Earlier folds and 12-week sensitivity |
| [Generalization gaps](generalization_gaps.csv) | Every model's training/validation/test gap |
| [Calibration](calibration.csv) | Reliability bins; full metrics include Brier/log loss/ECE |
| [Validation audit](validation_audit.json) | Independent as-of checks, splits and preservation |
| [Replay audit](model_replay_audit.csv) | Every selected model on all three partitions |
| [Repeat-fit audit](determinism_audit.csv) | Bitwise repeats of the three strict Top-10 model families |

Standalone figures: [classification](figures/classification_comparison.svg), [regression](figures/regression_comparison.svg), [new-feature importance](figures/top10_new_feature_importance.svg), [period stability](figures/evaluation_period_stability.svg), [calibration](figures/calibration.svg), [regression diagnostics](figures/regression_diagnostics.svg). SVG files have their own [manifest](figures/manifest.json); previous PNG catalogs are unchanged.

## Reproduction

Run from the canonical repository root with the versions recorded in [protocol.json](protocol.json) and the campaign-specific [requirements](requirements.txt). These differ from the repository's historical requirements; do not replace the original file. Model fitting uses NumPy, pandas, SciPy, scikit-learn, joblib and threadpoolctl. The existing local environment has these packages; no new installation is needed here. The protocol guard includes the recorded platform/environment; portable saved-model replay does not require that fitting environment.

```bash
python3 src/feature_expansion_common.py prepare
python3 src/feature_expansion_features.py
python3 src/feature_expansion_models.py all
python3 src/feature_expansion_validate.py --prefix --preservation
python3 src/feature_expansion_report.py
python3 -m unittest discover -s tests -v
```

Feature rebuilding requires the retained private lyric/metadata stores and approved lyric text. These are read-only and never distributed. The published feature/outcome tables are sufficient for model fitting in the frozen environment. Models are checkpointed by data/protocol/code hashes under ignored `data/experiments/feature_expansion_v1/`; changed code requires a new matching checkpoint. The environment/protocol guard fails rather than silently accepting a changed experiment. A preservation baseline is local; fresh clones can use the public dataset and replay the portable models without private inputs.

Individual bounded stages are `train`, `baselines`, `interpret`, `backtests`, and `determinism` on `feature_expansion_models.py`. `all` runs them sequentially. No exhaustive combination search is invoked. Publication includes compact NumPy-replay model specifications; fitted sklearn objects and intermediate checkpoints remain private/local.

## Professor demonstration

```bash
.venv-regression-demo/bin/streamlit run src/feature_expansion_demo.py --server.address 127.0.0.1 --server.port 8503 --browser.gatherUsageStats false
.venv-regression-demo/bin/python -m unittest discover -s tests -p test_feature_expansion_demo.py -v
```

The existing Streamlit environment is reused. The page shows the known debut information, strict earlier credit history, real saved Top-10/long-chart/numerical predictions, actual 26-week outcomes, observed full-history context, baseline comparisons, confusion matrices, calibration and validation importance. Every displayed prediction is checked against its saved value. It performs no model fitting or network acquisition. The earlier demos remain at their existing entry points.
