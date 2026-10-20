# Local meaningful-regression demonstration

This is a separate **post-hoc exploratory** analysis of the completed `6d8da5f`
campaign. The original 2018-onward test was already inspected. Original data,
hierarchies, selected models and results are preserved. No exhaustive search runs
when launching the demonstration or selecting a model.

Read [the findings](../meaningful_findings.md) and
[the frozen relationship policy](relationship_policy.json) first. Filtering excludes
category A only. Category B remains eligible and labelled; category C requires
every predictor to differ from the target's documented information domain.

## Launch

The environment is already installed locally. From the repository root:

```bash
.venv-regression-demo/bin/streamlit run src/regression_demo.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Open the local address printed by Streamlit, normally `http://127.0.0.1:8501`.
Stop the server with Ctrl-C. This is a local classroom tool, not a hosted service.

On another machine, use an isolated Python 3.11 environment:

```bash
python3.11 -m venv .venv-regression-demo
.venv-regression-demo/bin/python -m pip install -r requirements-demo.txt
```

The separate requirements pin the campaign's NumPy, pandas and SciPy versions.
The Streamlit dependency is isolated from the original Python 3.9 campaign
environment. PyArrow is pinned for NumPy 1.x compatibility. See the official
[installation guidance](https://docs.streamlit.io/get-started/installation/command-line)
and [AppTest documentation](https://docs.streamlit.io/develop/api-reference/app-testing).

## Three views and a real prediction

1. **Predictor hierarchy:** choose a target, unrestricted/filtered view, predictor
   count and relationship category. The table is paginated over the complete
   matching hierarchy; search predictor names and download all matching rows.
   Select a model on any page. Validation scores are the original saved values.
2. **Target predictability:** compare original and filtered winners, sorted by
   final R² in either direction. Baselines, N and generalization gaps accompany
   the model metrics. Original and exploratory evaluations are labelled separately.
3. **Cross-domain:** inspect the validation-selected pure-C winner for each target.
   Sorting this table by test performance does not revise predictor selections.

Below each view, choose a held-out row or enter predictor values. The demonstration
uses saved coefficients and preprocessing, with real public data and actual outcomes.
The held-out prediction is checked against its saved prediction. Arbitrary candidates
are refitted one at a time after clicking **Load/refit this model**; this takes seconds,
uses the frozen pre-2018 refit/2018-onward test protocol and saves a local cache.
It never updates the published leaderboards or starts a new model search.

The form distinguishes missing values from empty secondary-genre lists. A checked
missing box overrides the entered value and uses the fitted training median/missing
indicator or category encoding. Date fields accept ISO dates; snapshot months accept
`YYYY-MM`. The same conversion is used for dataset examples and manual values.
Manual entries have no claimed actual outcome. OLS predictions are not clipped.

The first-chart-appearance scenario is an **availability check**, not a new forecast
evaluation. Warnings identify later chart history and enrichment whose historical
availability is unverified. Manual prediction requires acknowledging these warnings.
The published accuracy remains retrospective. Plots use at most 2,000 deterministic
held-out rows; displayed metrics use all observed test outcomes with equal song weight.

## Local artifacts and complete hierarchy recovery

The local demonstration requires the complete original campaign under
`data/experiments/regression_search/campaign/`, plus the new filtered indices and
model caches under `data/experiments/regression_search/meaningful_v1/`.
These large artifacts are deliberately ignored by Git. A fresh clone contains
published summaries, specifications, code and tests; it does not contain the full
model databases. Copy the retained local campaign artifacts from the research
machine before requesting arbitrary hierarchy models. Do not substitute the
top-ten extract or the old bounded pilot for complete coverage.

If only a hierarchy CSV archive survives, investigate recovery of its complete
candidate catalog, per-fold scores and metadata before proceeding. If all full
artifacts are lost, the original exact campaign can be regenerated with its
documented commands in [the original experiment guide](../README.md), but that is
a separate explicit recovery operation. The demo and filtering tools fail clearly
when complete artifacts are missing; they do not automatically rerun the campaign.

To reproduce this filtering and selected evaluation with the original numerical
environment, after recovering the original campaign:

```bash
python3 src/regression_meaningful.py build
python3 src/regression_meaningful.py evaluate
python3 analysis/regression_search/meaningful/verify.py
python3 analysis/regression_search/meaningful/render.py
```

The policy and selection locks reject changed rules or winners. Complete per-target
indices contain every original candidate ID, category and unrestricted/filtered/
cross-domain rank; original metrics are joined read-only from the original databases.
The build verifies all 1,998,901 candidates against the saved campaign audits before
freezing all winners. Repeating evaluation reuses verified caches. It does not tune
on the already inspected test population.

Export a complete target hierarchy without fitting models:

```bash
python3 src/regression_meaningful.py export --task songs:ll_violence --view filtered --output /tmp/violence-filtered.csv.gz
python3 src/regression_meaningful.py export --task songs:ll_violence --view cross_domain --output /tmp/violence-cross-domain.csv.gz
```

## Published files

| File | Contents |
|---|---|
| [relationship_policy.json](relationship_policy.json) | Frozen definitions, provenance, scope choices and domain map |
| [relationship_pairs.csv](relationship_pairs.csv) | Every allowed directed target–predictor relationship |
| [filter_audit.json](filter_audit.json) | Complete counts, source hashes and local index hashes |
| [selected_candidates.json](selected_candidates.json) | All validation-only winners, frozen before the new evaluation |
| [best_by_predictor_count.csv](best_by_predictor_count.csv) | Best 1/2/3-predictor models in filtered and strict cross-domain views |
| [filtered_leaderboard.csv](filtered_leaderboard.csv) | Filtered winners with metrics, baselines, N, gaps, historical periods and uncertainty |
| [cross_domain_leaderboard.csv](cross_domain_leaderboard.csv) | Pure cross-domain winners with the same evaluation fields |
| [original_annotated_leaderboard.csv](original_annotated_leaderboard.csv) | A separately annotated copy; original results remain unchanged |
| [changes_from_unrestricted.csv](changes_from_unrestricted.csv) | Changed winners and descriptive test-score differences |
| [model_manifest.json](model_manifest.json) | Local selected-model paths, predictors and integrity hashes |
| [validation.json](validation.json) | Full ranking, split, preprocessing and prediction replay audit |
| [run_summary.json](run_summary.json) | Counts, measured runtime, storage and test status |

## Validation commands

```bash
python3 -m unittest discover -s tests -v
.venv-regression-demo/bin/python -m unittest discover -s tests -p test_regression_demo_app.py -v
python3 src/regression_meaningful.py verify-originals
```

The optional AppTest suite exercises real held-out examples, manual inputs,
availability warnings, all three views and an arbitrary one-predictor refit.
It needs the local artifacts and isolated demo environment; ordinary repository
tests skip those optional UI cases when these prerequisites are absent.
