# Exhaustive cross-domain regression discovery V3

The completed search covers **123 supported numerical targets**, **129 predictor constructs** (all **57 new constructs**) and **40,884,781 valid target/combination pairs**. Three historical validation periods and a final evaluation produce **163,539,124 additive OLS fits**. Two of the 125 meaningful numerical target candidates lack historical support. No additional data, features or classifier measurements were created.

Read [findings](findings.md) for the three requested top-15 tables and the substantive interpretation. The [methodology](methodology.md) and [protocol](protocol.json) define the frozen population, missingness, dependency policy and selection rule. Final evaluation was already inspected in earlier campaigns; these are exploratory retrospective relationships.

## Published results

| Artifact | Contents |
| --- | --- |
| [Target inventory](target_inventory.csv), [predictor inventory](predictor_inventory.csv) | Complete variable definitions, source sets, measurement families and target support |
| [Source-column inventory](source_column_inventory.csv), [relationship pairs](relationship_pairs.csv) | Every input column and every directed numerical-target/predictor relationship, including exclusions |
| [Measurement-source evidence](measurement_source_evidence.json) | Source-code/prompt hashes supporting the recorded provenance classification and its common-linkage limits |
| [Near-duplicate audit](near_duplicate_audit.csv) | Observed debut rank versus source-reported debut peak, including their preserved source disagreements |
| [Search space](search_space.csv), [cohorts](cohorts.csv) | Exact counts by target/view/configuration/variable count and frozen sample-identity hashes |
| [Unrestricted leaderboard](unrestricted_leaderboard.csv) | Global top 100 valid combinations by mean validation R²; related measurements remain |
| [Different-family audit](different_family_audit_leaderboard.csv) | Broader C/D/E view, retaining explicitly flagged conceptual overlaps |
| [Cross-domain leaderboard](cross_domain_leaderboard.csv) | D/E relationships, excluding same families and conceptual-overlap proxies |
| [Provenance-separated leaderboard](provenance_separated_leaderboard.csv) | Primary E view, requiring disjoint recorded measurement sources |
| [Target leaderboard](target_leaderboard.csv), [best by predictor count](best_by_predictor_count.csv) | Best overall and best one/two/three-variable models for every target, view and configuration |
| [Target predictability](target_predictability.csv) | One primary combined winner per target, ranked by validation |
| [Incremental information](incremental_information.csv) | New/combined versus original/classifier-only on identical target populations |
| [Feature-family comparison](feature_family_comparison.csv), [family winners](feature_family_winners.csv) | Descriptive family frequencies; correlated targets are not independent replications |
| [Baselines](baselines.csv), [uncertainty](selected_uncertainty.csv), [diagnostics](selected_diagnostics.csv) | Mean/median baselines, paired cluster intervals, within-year and exact-credit checks |
| [Selection lock](selection_lock.json), [coverage](coverage.json), [fold metadata](fold_metadata.json) | Frozen validation choices, complete fit accounting and exact metric denominators |
| [Benchmark](benchmark.json), [execution](execution.json), [report execution](report_execution.json) | Actual budget projection and separate search/report resource measurements |
| [Figures](figures/manifest.json), [portable models](models/) | Nine SVG figures and portable model exports for the three top-15 views |
| [Local artifact manifest](local_artifacts.json) | Names, sizes and hashes of all complete local hierarchy components and selected predictions |

`NO_ELIGIBLE_COMBINATIONS` is an explicit policy result, not a missing search. For example, a lyric-derived target has no provenance-separated classifier-only model because both use lyrics. Negative R² and singular models remain represented. Binary-target OLS is unclipped and is not calibrated classification.

`audit.json` preserves the prelaunch inventory stage. The completed search status and actual fit count are in `execution.json`; the earlier audit's stage flags are not a live execution tracker.

## Reproduction

Run from the canonical repository root with the existing Python numerical environment:

```bash
python3 src/regression_cross_domain_spec.py preserve
python3 src/regression_cross_domain_spec.py audit
python3 src/regression_cross_domain_search.py benchmark
python3 src/regression_cross_domain_search.py run
python3 src/regression_cross_domain_report.py report
python3 -m unittest discover -s tests -v > data/experiments/regression_cross_domain_v3/tests.log 2>&1
python3 src/regression_cross_domain_validate.py validate
python3 src/regression_cross_domain_validate.py snapshot
python3 src/regression_cross_domain_report.py report
python3 src/regression_cross_domain_validate.py check-determinism
python3 src/regression_cross_domain_validate.py publish-manifest
python3 src/regression_cross_domain_validate.py verify-publication
```

The search refuses a changed numerical protocol, code, source or environment. The measured launch projection must remain within four hours and 15 GB, with disk headroom. It resumes verified committed chunks; there is no silent candidate reduction. Existing prior work is protected by the preservation snapshot. Regeneration of completed summaries does not require rerunning the exhaustive fits. Private source inputs are not acquired or reconstructed by these commands.

The independent validator records `validation.json`; complete report regeneration records `determinism.json`. The publication manifest is created only after both pass, including protected-source preservation. Existing project navigation and frozen release dependencies remain unchanged; the campaign has its own documentation entry at `docs/regression_cross_domain_v3.md`.

## Complete local hierarchy

Large results remain under ignored `data/experiments/regression_cross_domain_v3/`. They contain all valid combinations, including negative results, rather than only the published top rows. Query them without refitting:

```bash
python3 src/regression_cross_domain_report.py query --target ll_violence --view provenance_separated --configuration combined --limit 20
python3 src/regression_cross_domain_report.py query --target lyric_word_count --view cross_domain --count 2 --limit 20
python3 src/regression_cross_domain_report.py query --target ll_violence --view unrestricted_valid --limit 0 --output data/experiments/regression_cross_domain_v3/ll_violence_all.csv
```

`--limit 0` streams the complete requested target/view/configuration as CSV. The canonical compact arrays preserve float64 values; text exports may be much larger. Required local files are listed and hashed in the public manifest:

- `candidate_catalog.npy`: all 357,889 global unordered one/two/three-variable combinations; uint8 indices into the sorted predictor inventory, with 255 padding.
- `targets/<target>/categories.npy` and `exclusion_rules.npy`: all global combinations, including A exclusions. Categories are 1=A through 5=E; rule bits are defined in the protocol.
- `valid_ids.npy`: uint32 global candidate IDs for valid rows. `metrics.npy` is float64 with shape `(4, valid_candidates, 2)`; axes are period, candidate row, and `(MSE, MAE)`. Periods 0–2 are historical validation; 3 is 2018+ evaluation.
- `status.npy`: uint16 fit rank in the low 15 bits and QR/SVD fallback in the high bit. Constant encoded blocks are removed without deleting conceptual candidates.
- `validation_order.npy`: candidate-row positions ordered by mean historical R², then fewer variables and lexicographic tuple. Evaluation never changes this ordering.
- `checkpoint.sqlite`: checksummed committed chunks and exact period metadata. Together with the arrays it supports recovery and exact R²/RMSE/baseline-skill reconstruction.
- `selected_models.json.gz`, `selected_candidate_ids.npy`, `selected_predictions.npy`, `evaluation_actual.npy` and `evaluation_song_ids.npy`: portable models and replayable predictions for every published selection plus global top-100 combinations.

R² uses the held-out target variance. MSE skill uses the held-out error of the training mean; MAE skill uses the training median. Mean validation R² and MAE weight the three periods equally; validation RMSE is the square root of the equal-period mean MSE. The three period metrics remain separately available. A predictor with several encoded categories still counts as one original construct.

## Interpretation

Category E describes disjoint **recorded measurement pipelines**, not statistical independence, unknown pretrained knowledge, independent sampling or causality. Lyrics-based classifiers and lyrical structure share a source. Genre annotation uses chart identity/date and linked metadata, so it is not independent of Billboard or MusicBrainz. Common identity joins and retrospective enriched selection remain across every model.

Paired exact-credit and debut-year intervals hold the selected predictions fixed. They omit exhaustive-search and refitting uncertainty. Every figure uses validation-selected models and retains their evaluation failures. The within-year diagnostic centers actual evaluation outcomes and is not a deployable metric. Observed-history outcomes remain censored despite cutoff-specific maturity/inactivity rules. No COVID breakpoint or new statistical campaign is introduced.
