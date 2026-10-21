# Historical change and genre decomposition

Completed exploratory analysis of the existing Billboard monthly dataset,
1960–2025. Start with [findings](findings.md) and [methodology](methodology.md).
The Milestone 2 Question 4 percentages supplied by the user remain unverified:
their original calculation code, six-genre set and weighting were unavailable.
The new symmetric accounting was independently checked without tuning to them.

All 42 scores and all 16 original genres are retained. Seven fixed comparisons
under three weightings produce 882 complete decompositions. Formal uncertainty
covers eleven named scores; a single BY correction covers 715 planned terms.
There are 23 corrected long-run decomposition terms and no corrected breakpoint
terms. This is exploratory evidence from an already inspected population.

## Published evidence

| File | Contents |
|---|---|
| [historical_comparisons.csv](historical_comparisons.csv) | 882 totals, within/composition shares, coverage, intervals and global q where planned |
| [decomposition_results.csv](decomposition_results.csv) | 14,112 original-genre contributions, cell means/shares and sparse/entry flags |
| [genre_period_statistics.csv](genre_period_statistics.csv) | Eight periods, three weightings, all score-specific populations and missingness |
| [sensitivity_results.csv](sensitivity_results.csv) | Genre restrictions, missing-score scenarios/bounds, dependence and 2020 specification sensitivity |
| [breakpoint_results.csv](breakpoint_results.csv) | 242 score/model/date rows; level and slope effects, intervals, q and historical ranks |
| [breakpoint_coefficients.csv](breakpoint_coefficients.csv) | All fitted coefficients, including seasonal and genre terms |
| [primary_tests.csv](primary_tests.csv) | All 715 raw p-values and global BY q-values |
| [annual_trajectories.csv.gz](annual_trajectories.csv.gz) | All-score annual overall/genre means and coverage under all three weightings |
| [annual_genre_shares.csv](annual_genre_shares.csv) | Genre shares of the full population, including unavailable scores |
| [preliminary_claims_audit.csv](preliminary_claims_audit.csv) | Supplied Milestone 2 claims versus the new results; provenance limitations |
| [reference_path_audit.csv](reference_path_audit.csv) | Both sequential reference paths whose average gives the symmetric within component |
| [duplicate_song_month_audit.csv](duplicate_song_month_audit.csv) | Existing three duplicate source identities, collapsed by the validated preparation |
| [figures/](figures/) and [figure index](figure_index.json) | Eight standalone SVG figures, with source-table references |
| [test results](test_results.json) | Full repository suite, historical tests, preserved figure catalog and repository integrity |
| [validation.json](validation.json) | Direct weighted-mean, reference-path, reconciliation and preservation checks |
| [replay validation](replay_validation.json), [resume validation](resume_validation.json) | Fresh resamples and complete cached reproduction of the scientific tables |
| [resume-fix audit](resume_fix_audit.json) | JSON fingerprint comparison repair; original fingerprint and unchanged resample-array hashes |
| [protocol.json](protocol.json), [execution.json](execution.json) | Frozen design/software/input fingerprints and initial execution accounting |
| [precision audit](precision_audit.json) | Disclosed uniform 999 → 9,999 resampling refinement; all coarse tests retained |
| [preservation manifest](preservation_manifest.json) | 1,692 unchanged original files plus the documented historical/current hashes for one updated verification test |
| [artifact manifest](artifact_manifest.json) | Current public artifacts and implementation hashes |

Blank uncertainty columns mean the row is descriptive, outside the planned
inference family. Missing means remain blank. Entry/exit allocations, sparse cells,
unstable percentage ratios and scenario assumptions are explicit in the tables.
Effects use the original classifier scales; they are not calibrated prevalence.
Breakpoint R² is in-sample descriptive fit, not held-out forecast performance.

## Verification and reproduction

No private lyrics, database or cached bootstrap arrays are needed to inspect or
verify the publication. From the repository root:

```bash
python3 analysis/historical_decomposition/verify.py
python3 -m unittest discover -s tests -p 'test_historical_decomposition*.py' -v
python3 analysis/historical_decomposition/verify.py --replay
```

The optional replay recomputes 9,999 resamples for the legacy decomposition and
the earliest/latest genre-adjusted breakpoint windows. It verifies point effects,
intervals, p-values and standard errors against the published results and leaves
the publication unchanged. The lightweight check also compares 33,264 monthly
score cells against the previous moving-average series, including equal and rank
weights and exact counts.

The frozen execution used Python 3.9.6, NumPy 1.26.4, pandas 2.2.2, SciPy 1.13.1
and one numerical thread on macOS arm64. Matplotlib 3.9.4 renders figures.
These are the recorded analysis versions; the repository-wide requirements file
serves other workflows and is not this exact frozen environment. Full replay
refuses a changed runtime/source fingerprint rather than silently mixing caches.

For a full reproduction in that environment:

```bash
python3 analysis/historical_decomposition/prepare.py
python3 src/historical_decomposition.py run
python3 analysis/historical_decomposition/render.py
python3 analysis/historical_decomposition/verify.py --replay
```

Preparation verifies original files and initializes an ignored local preservation
guard. The analysis uses atomic, identity-checked local bootstrap caches under
`data/experiments/historical_decomposition_v2/`. A cold full run took 311.7 seconds
and 988.0 MiB peak RSS; the initial coarse pass took another 61.6 seconds. Rendering
and validation time are separate. Rendering also creates PNG previews in the system
temporary directory; the SVGs are the canonical publication artifacts. This keeps
the separately validated catalog of 951 previous PNGs unchanged.
A resumed run reuses cached draws and records
that invocation's runtime; retain the original execution record when comparing
performance. Only completed public tables and figures belong in Git.

This workflow neither acquires data nor changes existing scores, genres or prior
results. It launches no additional discovery families.

The four navigation documents now link this completed work. One existing
publication test was extended to check the previous root README and its own prior
version against commit `d5a062c`, while this publication pins their current bytes.
All original manifests and numerical artifacts are unchanged. The preservation
manifest records both hashes and the reason for this narrow test revision.
