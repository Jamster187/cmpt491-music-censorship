# CMPT 491: completed course-method campaign

This directory contains the executed frequent-pattern, association, classification
and clustering campaign authorized on 2026-10-25. It uses the existing public
song table and performs no acquisition, lyric inference or genre relabelling.
All findings are exploratory; the historical evaluation outcomes have been inspected
in earlier campaigns. This is not independent replication or evidence of COVID causality.

Start with [methodology](methodology.md), the [locked protocol](protocol.json),
and [population/split audit](preparation.json). The analysis unit is one exact
original title/artist identity. There are 20,979 songs with all 42 scores; the primary
split contains 16,079 training, 1,907 validation and 2,382 test songs. Boundary-crossing
histories and 2026 evaluation songs are excluded, with all original data preserved.

## Frequent patterns and associations

| Output | Contents |
|---|---|
| [Algorithm comparison](frequent_patterns/algorithm_comparison.csv) | Apriori, FP-Growth and ECLAT, three identical support thresholds/populations |
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

Earlier landing pages, figure catalogs and analysis code are hash-pinned by frozen
publications. They retain their bytes; this directory is the campaign's navigation
and reproduction entry point. All new scientific figures use SVG, preserving the
earlier frozen PNG catalog.
