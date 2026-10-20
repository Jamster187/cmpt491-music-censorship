# Statistical relationship discovery pilot

This is a bounded, real-data feasibility sprint. **The full discovery campaign
has not run. No independent confirmation is claimed.** Previous datasets,
classifiers, genre assignments, OLS models/results and historical analyses are
preserved. The original regression demo is unchanged.

Start with the [measured findings](pilot_results/findings.md),
[exact search spaces](search_space.md), [statistical protocol](methodology.md),
and [measured performance](benchmark_results/README.md).

## Classroom demonstration

From the repository root, using the already installed local demo environment:

```bash
.venv-regression-demo/bin/streamlit run src/relationship_demo.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8502`. The companion view preserves the original regression
application at port 8501 and links to it. Stop a foreground server with Ctrl-C.
On another machine, install the existing `requirements-demo.txt` in an isolated
Python 3.11 environment first; this read-only view does not require scikit-learn
or the large local regression databases.

Choose a relationship family, target/panel and candidate. Genre and year filters
change supporting observations and descriptive tables; the displayed published
metrics remain those of the saved complete evaluation cohort. Inspect linear
versus selected nonlinear curves, conditional improvements by period, subgroup
coverage, historical/placebo plots, PCA loadings and cluster profiles. All
predictions/curves and statistics come from measured fits; selecting a view does
not run or expand a search. The compressed publication contains every pilot
candidate, including poor results and reconstruction controls.

## Reproduce the bounded pilot

The measured numerical environment uses Python 3.9.6 with the versions recorded
in `pilot_protocol.json`. `requirements-discovery.txt` is a separate minimal set;
do not overwrite the original numerical environment or use the unrelated
notebook lockfile as proof of compatibility.

```bash
python3 -m venv .venv-relationship-discovery
.venv-relationship-discovery/bin/python -m pip install -r requirements-discovery.txt
.venv-relationship-discovery/bin/python src/relationship_discovery.py audit
.venv-relationship-discovery/bin/python src/relationship_discovery.py pilot --workers 1
.venv-relationship-discovery/bin/python src/relationship_discovery.py verify
.venv-relationship-discovery/bin/python src/relationship_discovery.py benchmark
.venv-relationship-discovery/bin/python analysis/relationship_discovery/render.py
```

Exact replay requires the recorded Python/numerical versions. Version differences
fail the protocol lock rather than silently replacing a published run. A planned
migration requires a new explicit protocol version. The source commit must exist
in Git history for the preservation audit; a normal full clone includes it.
Only public `songs.csv` is required for fitting. Existing large OLS artifacts,
when present, are included in preservation checks, never refitted or modified.

`pilot` repeats resume verified local checkpoints under
`data/experiments/relationship_discovery/pilot_v2/`. That directory is ignored.
The hard cap is 200 candidates; the frozen manifest has 137. There is no command
for launching the proposed full campaign. `benchmark` reruns four fixed nonlinear
candidates using one and two workers to measure scaling and equality; it is not
an additional discovery search. The CLI verifies code/data/configuration hashes
before reuse. Public JSON/CSV outputs are generated, not manually edited.

The first implementation run was retained locally. A constant-subgroup guard
and complete-predictor counts were added in v2, with the same candidate list and
selection rules. [The revision audit](pilot_results/revision_check.json) confirms
that all primary measured effects, metrics and p-values were unchanged. Both
runs were exploratory; no newly untouched data is implied.

## Published artifacts

| File | Contents |
|---|---|
| [pilot_protocol.json](pilot_protocol.json) | Frozen code/data identity, candidates, types, periods and inference rules |
| [variable_inventory.csv](variable_inventory.csv) | 75 typed variables with domain and availability provenance |
| [pilot_candidates.csv](pilot_candidates.csv) | Complete outcome-blind pilot selection |
| [search_space.json](search_space.json) | Exact proposed counts and pilot sizes |
| [relationship_inventory.csv](relationship_inventory.csv) | All measured pilot relationships, including reconstruction controls |
| [discovery_leaderboard.csv](discovery_leaderboard.csv) | Statistical evidence ordering with separate effect/utility/stability fields |
| [cross_domain_leaderboard.csv](cross_domain_leaderboard.csv) | Strict cross-domain subset |
| [nonlinear_leaderboard.csv](nonlinear_leaderboard.csv) | Nonlinear improvement ranking, including weak/negative results |
| [conditional_leaderboard.csv](conditional_leaderboard.csv) | Genre, product and threshold interactions |
| [temporal_leaderboard.csv](temporal_leaderboard.csv) | Adequately covered descriptive historical contrasts |
| [stable_leaderboard.csv](stable_leaderboard.csv) | Worst-period-first ranking across all four evaluation periods |
| [results.json.gz](pilot_results/results.json.gz) | Lossless complete aggregate results, curves, profiles and coverage diagnostics |
| [temporal_comparisons.csv](pilot_results/temporal_comparisons.csv) | All prespecified historical comparison cells, including inadequate cells |
| [validation.json](pilot_results/validation.json) | Song splits, correction, protocol and preservation audit |
| [initial_run_audit.json](pilot_results/initial_run_audit.json) | Measured first v2 execution, fit count and peak memory |
| [run_audit.json](pilot_results/run_audit.json) | Resume evidence and logical result identity |
| [ranking_policy.json](pilot_results/ranking_policy.json) | Explicit separate sort rules; no weighted novelty score |
| [benchmark_results/](benchmark_results/README.md) | Family/method throughput, scaling and extrapolation assumptions |

## Validation

```bash
python3 -m unittest discover -s tests -v
.venv-regression-demo/bin/python -m unittest discover -s tests -p test_relationship_demo.py -v
python3 src/relationship_discovery.py verify
python3 analysis/relationship_discovery/verify_replay.py
python3 src/relationship_discovery.py verify-originals
```

The interactive tests use actual published results and public dataset values.
They skip in environments without the optional Streamlit dependency. Statistical
unit tests cover typed effects, multiplicity, chronological purging, train-only
preprocessing, nonlinear recovery and interaction baselines. Replay checks compare
real outer-fold metrics and saved curves with reproducibly refitted models.

## Before a full campaign

Approve the family scope and runtime/storage budget; the complete threshold grid
is much larger than univariate and genre searches. Approve a calibrated null and
Monte Carlo precision plan for the much larger correction family. Historical
breakpoint inference, artist dependence and longitudinal weekly/monthly targets
need additional work. A production full runner should reuse designs, batch
statistics and extend checkpoints without heuristic screening.

The existing data can support a larger **exploratory** chronological study. An
independent confirmation claim requires genuinely new, non-overlapping evidence
collected after hypotheses and evaluation rules are frozen. This sprint acquires
no such data and does not launch a full campaign.
