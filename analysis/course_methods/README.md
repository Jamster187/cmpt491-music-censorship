# CMPT 491: completed course-method campaign

This directory contains the executed frequent-pattern, association, classification
and clustering campaign authorized on 2026-10-25. It uses the existing public
song table and performs no acquisition, lyric inference or genre relabelling.
All findings are exploratory; the historical evaluation outcomes have been inspected
in earlier campaigns. This is not independent replication or evidence of COVID causality.

Start with the [eight measured findings](findings.md), [methodology](methodology.md),
the [locked protocol](protocol.json), and [population/split audit](preparation.json).
The analysis unit is one exact
original title/artist identity. There are 20,979 songs with all 42 scores; the primary
split contains 16,079 training, 1,907 validation and 2,382 test songs. Boundary-crossing
histories and 2026 evaluation songs are excluded, with all original data preserved.

## Frequent patterns and associations

| Output | Contents |
|---|---|
| [Algorithm comparison](frequent_patterns/algorithm_comparison.csv) | Apriori, FP-Growth and ECLAT, three identical support thresholds/populations |
| [Itemset summary](frequent_patterns/itemset_summary.csv) | Frequent, closed and maximal counts at each threshold |
| [5% itemsets](frequent_patterns/itemsets_support_0.05.csv.gz) | Every frequent itemset up to size four, with exact global closed/maximal flags |
| [8% primary itemsets](frequent_patterns/itemsets_support_0.08.csv.gz) | Primary rule-discovery collection |
| [12% itemsets](frequent_patterns/itemsets_support_0.12.csv.gz) | Higher-support sensitivity |
| [Transaction definitions](frequent_patterns/transaction_schema.json) | Actual training-derived cutoffs, sample counts and transaction hashes |
| [All association rules](association_rules/all_rules.csv.gz) | Complete primary, rare-pair and negative searches; validation/test effects and global BY |
| [Cross-domain leaderboard](association_rules/cross_domain_leaderboard.csv) | Strict outcome-versus-antecedent domain separation; up to 100 rows |
| [Presentation shortlist](association_rules/presentation_shortlist.csv) | Direction/domain quotas, simpler-rule comparisons, no novelty score |
| [Historical and genre stability](association_rules/historical_and_genre_stability.csv) | Shortlist diagnostics including pre-/post-2020 |
| [Conditional pair results](association_rules/conditional_pairs.csv.gz) | All bounded cross-domain pair/genre cells, including null and unsupported cells |
| [Artist-credit sensitivity](association_rules/artist_sensitivity.csv) | Fixed-rule cluster-bootstrap intervals; post-hoc and descriptive |

Closed/maximal flags inspect extensions beyond four items, so a size-four boundary
is never mistaken for proof of maximality. Larger patterns themselves are not
enumerated or published. The negative numerical search excludes missing values
from its denominator; “not high” includes observed middle and low values.

## Classification and clustering

| Output | Contents |
|---|---|
| [Classifier evaluation](classification/evaluation.csv) | All three targets, four chronological folds, tree/rules/Bayes and two baselines |
| [Validation grid](classification/validation_grid.csv) | Every depth/class-weight candidate, with training-only selection |
| [Confusion matrices](classification/confusion_matrices.json) / [per-class metrics](classification/per_class_metrics.csv) | All class counts, including unsuccessful classes |
| [Interpretable rules](classification/rules.csv) | Every tree leaf, precise conditions, training/test support and observed test correctness |
| [Uncertainty](classification/uncertainty.csv) / [subgroups](classification/subgroup_metrics.csv) | Block/artist-credit intervals, historical, genre and unseen-credit checks |
| [Classifier exports](classification/models.json.gz) / [predictions](classification/predictions.csv.gz) | Plain numeric model specifications and complete public-song predictions |
| [Clustering grid](clustering/grid.csv) / [stability](clustering/stability.csv) | All 99 configurations and 198 resample comparisons |
| [Selected/fallback configurations](clustering/selected_configurations.csv) | Nine independently selected method/representation results, unsupported results marked |
| [Cluster assignments](clustering/assignments.csv.gz) | One row per public song, split label, and nine configuration columns; no repeated identity copies |
| [Profiles](clustering/profiles.csv) / [genre composition](clustering/genre_composition.csv) | All 42 feature means and cluster/genre shares |
| [Historical prevalence](clustering/historical_prevalence.csv) / [chart distributions](clustering/chart_distributions.csv) | Descriptive full-population diagnostics |
| [Pre-/post-2020 contrasts](clustering/pre2020_post2020.csv) / [genre standardization](clustering/genre_standardized_prevalence.csv) | Fixed-cluster uncertainty and explicit support limitations; no causal claim |
| [Representation agreement](clustering/representation_agreement.csv) | Assignment ARI across selected configurations on each chronological split |
| [Clustering exports](clustering/models.json.gz) | Fitted training transforms, centroids/medoids and selection status |
| [Seven figures](figure_index.json) | Exportable SVGs; captions and links also appear in the findings report |

## Professor demonstration

Reuse the existing Python 3.11 Streamlit environment:

```bash
.venv-regression-demo/bin/streamlit run src/course_demo.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8503`. The sidebar switches among classification, frequent
patterns, association rules and clustering. Choose a real public song, compare a
tree with Bayes, inspect the actual IF–THEN path, change one score, and compare the
saved metrics with their baselines. The other views expose itemsets, rule support/
confidence/lift and stability, cluster assignments/profiles, and unsupported results.
No selection launches fitting, acquisition or another search.

On another machine, create `.venv-regression-demo` with Python 3.11 and install
[requirements-demo.txt](../../requirements-demo.txt). No scikit-learn or private
cache is required for the demo: it independently evaluates the numeric exports
using NumPy. Manual inputs alter only the displayed example, not published metrics.
Exact artist-credit checks do not imply fully performer-disjoint validation.

## Reproduction

Run from the canonical repository root with the recorded Python 3.9.6 environment
and versions in [requirements-course-methods.txt](../../requirements-course-methods.txt).
The existing `python3` in the execution environment matched those versions.
For an isolated installation, use an ignored directory:

```bash
python3 -m venv data/experiments/course_methods_env
data/experiments/course_methods_env/bin/python -m pip install -r requirements-course-methods.txt
```

Use that interpreter in place of `python3` below if creating the separate environment.
The protocol also records the platform and refuses silently mixed environments;
another platform/version requires an explicitly versioned replication, not replacement
of this publication. The read-only classroom demonstration is portable and uses
the existing separate demo requirements.

```bash
python3 src/course_common.py
python3 src/course_patterns.py
python3 src/course_classification.py
python3 src/course_clustering.py
python3 src/course_report.py
```

Preparation hashes every pre-existing file under `data/` and `analysis/`, excluding
runtime bytecode and this campaign's own paths. On the execution host it verified
245,085 files / 33,460,842,025 bytes, including private databases and prior caches.
This can take several minutes and performs no network access. On another checkout
the snapshot includes the files present there; it does not require private data.

Atomic local checkpoints live under ignored `data/experiments/course_methods_v1/`.
They pin the input, configuration, environment, source hashes and logical result
hash. Completed algorithm/configuration fits are reused only after verification.
Reports and supporting tables are regenerated from deterministic results. Runtime
measurements can vary. The saved original timings remain attached to fit checkpoints.

## Validation

The [public replay audit](replay_validation.json) recounts all 28,152 support-level
itemset rows and 62,784 rule/split evaluations, checks 133,725 classifier prediction/
metric comparisons and 185,355 cluster assignments, and validates 120 checkpoints.
It also refits all 12 chronological classification tasks and 27 outcome-blind
clustering configurations (81 fits), reproducing their logical results exactly.
The [final audit](validation.json), [test results](test_results.json),
[execution summary](execution_summary.json), [stage resource accounting](report_execution.json)
and [artifact manifest](artifact_manifest.json)
record the completed checks and source/output hashes.

```bash
python3 -m unittest discover -s tests -v
.venv-regression-demo/bin/python -m unittest discover -s tests -p 'test_course_demo.py' -v
python3 src/course_verify.py
python3 src/course_verify.py --replay
python3 src/course_verify.py --preservation
python3 src/repository_layout.py
python3 src/figure_audit.py --validate
python3 src/phase1.py validate
```

Ordinary verification uses public files and checks any local checkpoints that are
present. `--replay` requires this campaign's completed local checkpoints for exact
refit comparisons. `--preservation` needs the local before-snapshot and reads all
pre-existing files. It does not change them. `--record` saves a measured validation
record and refreshes this campaign's manifest after successful checks. To reproduce
figures/reports, run the renderer before recording a new manifest; source changes
are never silently accepted by existing fit checkpoints. `--record` permits changed
timings and audit records from an explicit rerun, but still rejects changed scientific
tables, models, figures or source code. Ordinary read-only verification permits no
hash differences.

Earlier landing pages, figure catalogs and analysis code are hash-pinned by frozen
publications. They retain their bytes; this directory is the campaign's navigation
and reproduction entry point. All new scientific figures use SVG, preserving the
earlier frozen PNG catalog.
