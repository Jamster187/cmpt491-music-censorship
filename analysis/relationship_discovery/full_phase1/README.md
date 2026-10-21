# Complete relationship discovery, Phase 1

This publication covers the three explicitly approved exhaustive families:
**2,775 pairwise + 3,192 nonlinear + 3,192 genre interactions = 9,159 candidates**.
All findings are exploratory. No independent confirmation or causation is claimed.
The [pilot publication](../README.md) is preserved as a historical snapshot; its
statements about a future full search describe that earlier sprint.

Start with [the findings report](../full_phase1_findings.md),
[methodology and interpretation rules](methodology.md),
[execution accounting](execution.json), and [validation](validation.json).
No numeric-interaction, threshold, breakpoint or additional structure campaign
was launched. Prior datasets, classifiers, genre definitions and analyses retain
their original bytes.

## Complete and interpreted results

| File | Contents |
|---|---|
| [candidates.csv](candidates.csv) | All 9,159 deterministic candidate definitions, locked before execution |
| [protocol.json](protocol.json) | Frozen input, code, environment and candidate identity |
| [environment.json](environment.json) | Measured platform and native numerical libraries with one thread per candidate |
| [pairwise_results.csv.gz](pairwise_results.csv.gz) | Every pair, all applicable effect measures, raw p, global/family BY, uncertainty and warnings |
| [nonlinear_results.csv.gz](nonlinear_results.csv.gz) | Every directed relationship, selected model performance, OLS comparison and four periods |
| [genre_interaction_results.csv.gz](genre_interaction_results.csv.gz) | Every interaction, additive comparison, support and historical performance |
| [nonlinear_leaderboard.csv.gz](nonlinear_leaderboard.csv.gz) | All non-reconstruction nonlinear rows, with explicit performance/stability ordering |
| [genre_interaction_leaderboard.csv.gz](genre_interaction_leaderboard.csv.gz) | All non-reconstruction genre rows |
| [cross_numeric_leaderboard.csv.gz](cross_numeric_leaderboard.csv.gz) | Priority cross-domain numerical dependence, ordered within effect type |
| [cross_categorical_leaderboard.csv.gz](cross_categorical_leaderboard.csv.gz) | Priority cross-domain categorical associations |
| [cross_predictive_leaderboard.csv.gz](cross_predictive_leaderboard.csv.gz) | Priority cross-domain predictive comparisons |
| [cross_shortlist_leaderboard.csv.gz](cross_shortlist_leaderboard.csv.gz) | Ten presentation examples in three separately labelled effect blocks |
| [sign_reversals_and_attenuation.csv.gz](sign_reversals_and_attenuation.csv.gz) | All available genre-adjusted diagnostics, including unflagged rows |
| [period_sign_changes.csv.gz](period_sign_changes.csv.gz) | Sign-change diagnostics across the four already approved evaluation periods |
| [lyric_chart_null_summary.csv](lyric_chart_null_summary.csv) | Complete lyric-to-chart predictor summaries, including failures to generalize |
| [artist_sensitivity.csv](artist_sensitivity.csv) | Bounded post-hoc artist-credit uncertainty checks; no new significance claims |
| [family_summary.json](family_summary.json) | Complete-family counts, throughput and multiple-testing outcomes |
| [method_throughput.csv](method_throughput.csv) | Actual fit-call timing by method and inner/outer stage |
| [selected_method_counts.json](selected_method_counts.json) | Nonlinear method selections made by inner validation |
| [figure_index.json](figure_index.json) | Selected measured figures and their candidate provenance |
| [replay_validation.json](replay_validation.json) | Independent statistics, deterministic reruns and unchanged pilot overlap |
| [resume_validation.json](resume_validation.json) | All 9,159 checkpoints reused with a guard preventing new fits |
| [test_results.json](test_results.json) | Actual unit, UI, planning and preservation validation outcomes |
| [artifact_manifest.json](artifact_manifest.json) | Published file hashes and reporting/demo source hashes |

The compressed CSVs are ordinary CSV files inside gzip and preserve exact saved
numerical values. Read directly with `pandas.read_csv(path)`, or decompress with a
gzip-capable tool. Local full checkpoints retain every inner fit, complete curve,
subgroup and timing record. Public `demo_results.json.gz` indexes every candidate's
measured aggregates. [demo_detail_files.json](demo_detail_files.json) maps targets
to compact supporting-detail files; the app loads only the selected target's
details, with a bounded cache. Nonlinear display curves retain 25 of the 100 fitted
points. The display approximation never changes model metrics.
Selected plot data contain only numerical predictions/measurements, with no song
identifiers or lyrics. Large checkpoints remain ignored and local.

## Classroom demonstration

From the repository root:

```bash
.venv-regression-demo/bin/streamlit run src/relationship_demo.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8502`. The default collection is **Full Phase 1**; the
**Preserved pilot** remains selectable. Choose family, target and ranked
relationship. Filter by the frozen cross-domain category or the additional
broader-domain distinction. Inspect effects, p/q values, uncertainty, absolute
R², comparison performance, actual curves and genre/period summaries.
Pairwise browsing accepts either side as the variable of interest, including
ordinal chart rank; this does not turn the symmetric association into regression.

Genre/year supporting-data filters do not change published cohort metrics or
select/refit models. The display retains negative R² and explicit reconstruction
controls. Artist-credit intervals and selected prediction/slopes displays are
labelled post-hoc diagnostics. Selecting a candidate does not launch a search.
The original OLS application remains separate at port 8501.

On another machine, create an isolated Python 3.11 environment and install
`requirements-demo.txt`. The read-only app needs public files and no private
regression databases or scikit-learn fitting dependency.

## Reproduce or resume the approved scope

Use the exact Python 3.9.6/numerical versions recorded in `protocol.json` and the
separate `requirements-discovery.txt`. Other versions fail the lock deliberately;
a version migration needs an explicitly versioned replication. Do not replace
the original environment with the demo environment.
Bitwise results can also depend on native BLAS/platform libraries; their measured
versions are recorded. A different host must pass numerical replay checks before
being treated as an exact reproduction.

```bash
python3 -m venv .venv-relationship-discovery
.venv-relationship-discovery/bin/python -m pip install -r requirements-discovery.txt
.venv-relationship-discovery/bin/python src/relationship_phase1_prepare.py
.venv-relationship-discovery/bin/python src/relationship_phase1.py run
.venv-relationship-discovery/bin/python src/relationship_phase1.py verify
.venv-relationship-discovery/bin/python analysis/relationship_discovery/full_phase1/render.py
.venv-relationship-discovery/bin/python analysis/relationship_discovery/full_phase1/verify_replay.py
```

Preparation initializes only missing local preservation snapshots and verifies
protocol identity. It never runs the old pilot audit or rewrites its publication.
Verified CPython bytecode caches are excluded from preservation; the associated
source and every scientific artifact must retain their original hashes. The
[cache-only audit](preservation_runtime_cache_audit.json) records the correction
to the initial operational snapshot, with unchanged campaign identity and data.
A normal full Git clone includes the baseline commits used by preservation.
The campaign's only fitted data input is public `songs.csv`.

The runner verifies then resumes atomic checkpoints under ignored
`data/experiments/relationship_discovery/full_phase1_v1/`. `run --max-new 50`
checkpoints after at most 50 new candidates without changing the locked universe.
`progress.json` records completion, fit calls, errors, RSS and ETA. Resource guards
pause safely and return exit code 75; investigate and report before resuming.
No command in this runner can add an unapproved family.

The renderer refuses incomplete candidate coverage. It recomputes campaign-wide
BY adjustment, generates complete tables, bounded artist diagnostics, figures and
findings. Re-running with complete local checkpoints does not repeat the search.
Reports are generated from measured results; do not edit derived numbers by hand.

```bash
python3 -m unittest discover -s tests -v
.venv-regression-demo/bin/python -m unittest discover -s tests -p 'test_relationship*demo.py' -v
python3 src/repository_layout.py
python3 src/figure_audit.py --validate
python3 src/relationship_phase1.py verify-originals
```

The full-search replay audit needs local checkpoints and checks all pairwise
statistics against independent calculations, all 80 approved-family pilot
candidates against their preserved results, and 36 outcome-blind candidates by
exact rerun. It also replays outer predictions for the predictive sample and checks
all published values/correction against the complete checkpoint set. The ordinary
unit suite checks public artifacts without private local checkpoints.
