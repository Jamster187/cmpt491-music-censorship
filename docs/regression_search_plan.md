# Exhaustive regression search: feasibility audit and approval draft

**Status: planning only; search space NOT approved; exhaustive campaign NOT run.**
Audit date: 2026-10-20. Source repository: [cmpt491-music-censorship](https://github.com/Jamster187/cmpt491-music-censorship).
Audited source HEAD and fetched `origin/main`: **`1211545e6087112e6e9e189799d2061ef302d470`**.
The later planning-only commit is separate from this source-data revision.

The proposed frozen-release universe has **33,131,785
target/predictor specifications across 73 target tasks**. Of these,
**28,442,928 across 59 targets** are suitable for
numerical OLS/Ridge prediction as a first model family. Seven chart-rank tasks,
one ordinal confidence task, and six other categorical/binary/multilabel tasks need
separate model families. These counts are combinations, not fitted estimator instances.
Every eligible combination of **1–4 original variables** is included; encoded dummy
columns and missing indicators do not consume additional conceptual-variable slots.

The bounded benchmark covered 192 distinct predictor sets,
384 OLS/Ridge configurations, three timing repetitions,
and both direct and cached implementations. No test predictions, feature-set ranking,
classifier inference, acquisition, COVID testing, or full search took place.
The retained run completed in 26.2 seconds, including input preparation.

## 1. Synchronization, current work and evidence

The supplied workspace had no Git repository. A fresh clone was created in its
`cmpt491-music-censorship/` subdirectory. Branch, status and remote inspection found
clean `main`, tracking the requested GitHub `origin`. After `git fetch origin`,
`HEAD...origin/main` was **0 ahead / 0 behind**; `git merge --ff-only origin/main`
reported already up to date. No reset, forced pull, checkout over changes, or
teammate-file edits were used.

Recent changes inspected:

- `1211545`: merge PR #2, 2026-10-19.
- `1fa2eb7`: alesa30garcia merged Afrobeats into Other in preprocessing outputs.
- `5b1a59e`: merge PR #1, 2026-10-18.
- `c8fb5a1`: alesa30garcia introduced monthly/weekly preprocessing and an R project.
- `a933fe8`, `4fc34ba`, `d4497c8`: preceding figure presentation and repository organization work.

Read [AGENTS.md](../AGENTS.md), [README](../README.md), [command guide](commands.md),
[repository structure](repository_structure.md), [public data guide](../data/public/README.md),
[column documentation](dataset/columns.md), the public manifest, frozen classifier
schema, current `final_dataset.py`, `public_classifier_features.py`, descriptive and
moving-average code, relevant tests, and both recent preprocessing diffs.
The only current R analysis source found is
[`preprocessing.Rmd`](../data/preprocessing/preprocessing.Rmd); no additional fitted
regression/model table or notebook was found in tracked current code. Archived pilot
tables and v2 aggregate-month exports are historical outputs, not interchangeable
observations for the current search.

### Actual files, not filename assumptions

| File | Rows | Fields | Exact song identities | song_id retained |
| --- | --- | --- | --- | --- |
| `data/public/songs.csv` | 28,041 | 70 | 28,041 | True |
| `data/public/master_monthly.csv` | 81,797 | 78 | 28,041 | True |
| `data/public/master_weekly.csv.xz` | 355,487 | 77 | 32,723 | True |
| `data/preprocessing/monthly.csv` | 78,587 | 58 | 26,159 | False |
| `data/preprocessing/monthly_no_duplicates.csv` | 78,587 | 58 | 26,159 | False |
| `data/preprocessing/monthly_lyrics_available.csv` | 78,587 | 58 | 26,159 | False |
| `data/preprocessing/weekly.csv.xz` | 355,487 | 56 | 32,723 | False |
| `data/preprocessing/weekly_no_duplicates.csv` | 32,723 | 56 | 32,723 | False |

All **511 table/field entries** are inventoried in
[`schema_inventory.csv`](../analysis/planning/regression_search/schema_inventory.csv):
exact field name, parsed storage type, semantic class, missing count/percentage,
nonmissing distinct count, range, numeric variance, provenance and availability timing.
The same field is inventoried independently at each resolution; repeated-row
missingness is not substituted for song-level missingness.
[`category_counts.csv`](../analysis/planning/regression_search/category_counts.csv)
retains full categorical value distributions, including JSON secondary-genre sets.
Hashes, byte sizes and in-memory table sizes are in
[`dataset_inventory.json`](../analysis/planning/regression_search/dataset_inventory.json).
Blank public cells mean missing; literal identity text such as `NA` is preserved.
Preprocessing `NA` tokens are treated as missing in non-identity fields.

The public release still has **16 genres**. The preprocessing outputs have **15**
after Afrobeats → Other. These are different representations; neither was changed.
All shared public song attributes were checked for exact invariance against
`songs.csv` in every monthly/weekly occurrence, including missingness.

### Findings that affect any regression

1. The three monthly preprocessing files are byte-identical, each with 78,587 rows
   and 26,159 identities. Both “no_duplicates” and “lyrics_available” filenames
   overstate their contents. There are **15,685 rows without lyrics** in all three.
   The R code computes intermediate filtered objects but writes `m` three times.
   Its intended first-occurrence tables would have 26,159 songs, or **20,184**
   with lyrics after the same low-confidence exclusion. This is reported, not repaired.
2. Preprocessing removes `song_id`, duration/count metadata and some chart fields;
   thresholds all four `ll_*` scores at `>0.5`; converts linked-release dates to years;
   removes low-confidence monthly rows but masks low-confidence weekly genre labels.
   `weekly_no_duplicates.csv` actually has one exact title/artist pair per row,
   but its first-observation chart values are not career averages. None is the
   authoritative model source for this proposal.
3. Public songs have 20,981 scored identities; 20,979 have all 42 scores.
   The two accepted LyricLens-specific missing cases remain missing. Metadata
   durations exist for 22,194 songs; linked release year for 22,058.
   No eligible target has >50% missingness, but approximately 25.18% of lyrical
   targets are missing and this missingness is selective.
4. Weekly includes 4,682 identities outside the 28,041-song enrichment population
   (7,492 rows). Their blank enrichment is structural “outside scope,” not zero
   content or evidence that lyrics do not exist. Monthly and weekly are two
   resolutions of the same chart history, not independent replications.
5. There are **13 extra weekly song/date rows** and **3 extra monthly song/date rows**.
   Preserve source rows and cluster them by `song_id`; do not silently deduplicate.
   `weekly_observation_count` and `chart_weeks` differ for only **one** study song.
   They are retained because they are not exact duplicates, but this is near-identity
   reconstruction, not evidence of a substantive predictive discovery.
6. Sentiment sums to one within **1.34e-07** floating-point error.
   This is a softmax composition. GoEmotions uses independent sigmoid outputs;
   observed sums range 0.579–2.738,
   so no artificial sum-to-one exclusion applies to its 28 outputs.
7. Duration min/median/max coincide for 4,686 songs but differ elsewhere; retain
   all three as measurements. Four maximum durations exceed one hour, with a
   maximum of 15,303 seconds. These may represent versions or linked-recording
   anomalies; do not silently trim them. **998** linked release years are later
   than first chart year, consistent with reissues/matching limitations. This is
   not a verified original-release-date variable.

## 2. Target definitions and modelling scope

The primary numerical list consists of the **42 continuous classifier scores**,
**3 durations**, **3 MusicBrainz link/duration counts**, **4 chart-history counts/points**,
**4 chart-history dates/months**, **linked release year**, and the monthly and weekly
`reported_weeks_on_chart` outcomes: **59 tasks**.

The counted OLS/Ridge specification is an intercept plus additive main effects,
using the encodings below. Interactions, polynomial bases, target transforms and
post-fit clipping are not implicitly included. In particular, retain unbounded
OLS/Ridge predictions when scoring bounded 0–1 targets; clipped or beta-regression
alternatives are different, separately approvable model specifications.

Counts are quantitative outcomes, not arbitrary category codes. OLS/Ridge estimate
their conditional means; count GLMs, log transforms or nonnegative constraints are
separately approvable sensitivity models. The three MusicBrainz counts describe
the accepted-link process, so their results belong with acquisition diagnostics.
Date responses are interpretable cohort/timing reconstruction tasks; encode day
offsets from 1970-01-01 or month offsets from 1970-01, not lexicographic strings.
Only the year component of `mb_earliest_release_date` is comparable across its
partial-date precision, so the derived target is named **`mb_release_year`**.
First/last chart dates do not become release dates.

The **7 rank tasks** are `best_chart_rank`, monthly/weekly current rank, and
monthly/weekly `reported_last_week_rank` and `reported_peak_position`.
Use cumulative-link/ordinal regression or an explicitly approved rank-loss model.
OLS/Ridge rank fits in the benchmark are computational proxies and an optional
numeric-rank sensitivity; they do not silently promote ranks to interval measurements.

Categorical targets are `primary_genre` (16-class multinomial), `secondary_genres`
(16-label multi-label output, not 446 arbitrary integer categories),
`musicbrainz_match_status`, `mb_release_date_precision`, `lyrics_status`,
`lyrics_available` (binary), and `genre_confidence` (ordered low/medium/high).
The last five are explicitly **annotation/acquisition diagnostics**, not musical traits.
No nominal class, identifier, album title or artist-credit string is encoded as a
numerical regression response. `in_final_study_population` is a sampling flag,
constant in songs/monthly, rather than an eligible musical target.
Observation dates/month and source coordinates define the sampling process and
are not response variables; meaningful song-level debut/end dates remain eligible.

The binary preprocessing `ll_*` flags are deterministic threshold versions of
the same four public continuous measurements, not four additional independent
outcomes. A binary-classification sensitivity can replace those four targets
under approval; the original continuous target score must then be excluded as a
predictor because it defines the label. Holding the proposed predictor universe
fixed, that alternative has 489,348 sets per flag (1,957,392 in total), replacing
the corresponding four score tasks rather than silently enlarging this campaign.
Neither the thresholds nor public score values have been changed.

### Variation and support

All 73 targets have at least two observed values. The full target registry reports
distinct counts, modal shares, standard deviation where meaningful, observed song
counts and missingness. High uniqueness alone is not evidence of useful signal.
Near-zero or skewed emotion/toxicity scores remain eligible.

Some categorical levels cannot support useful individual evaluation: MusicBrainz
`error` has **one song total**, in training; primary Afrobeats has **3 training,
0 validation, 10 test songs**, and K-Pop has **1 training, 3 validation** songs.
Do not silently remove, merge, or numerically regress these labels. Retain the
target and flag per-class inference as unsupported; smoothing/regularization and
metrics for supported classes must be declared. Full split/class counts, including
zero-count levels, are in
[`target_category_split_counts.csv`](../analysis/planning/regression_search/target_category_split_counts.csv).

## 3. Complete predictor universe and justified restrictions

The **60-variable song universe** is:

- The 42 exact scores listed individually in the target/count table below.
- `mb_duration_median_seconds`, `mb_duration_min_seconds`, `mb_duration_max_seconds`.
- `mb_recording_count`, `mb_release_count`, `mb_distinct_duration_count`.
- `weekly_observation_count`, `chart_weeks`, `total_chart_points`, `snapshot_months_selected`.
- `first_chart_date`, `last_chart_date`, `first_snapshot_month`, `last_snapshot_month`,
  `mb_release_year`, `best_chart_rank`.
- `primary_genre`, `secondary_genres`.

Each song measurement target removes itself. Diagnostic targets start from this
same base and apply their explicit leakage exclusions. Every per-target allowed
list and excluded-field reason is expanded in
[`predictor_sets.json`](../analysis/planning/regression_search/predictor_sets.json).
The exhaustive candidate family is precisely:

```python
for k in (1, 2, 3, 4):
    for subset in itertools.combinations(sorted(spec["predictors"]), k):
        if not any(set(bad) <= set(subset) for bad in spec["forbidden_subsets"]):
            yield subset
```

This is a complete machine-readable definition of the set, not a sample or
shortlist; writing 33 million nearly repetitive combination rows is unnecessary.
It contains no correlation, significance, subjective-interest or univariate screen.
For example, toxicity–insult, all nonredundant same-model emotion combinations,
duration summaries, and the almost-identical chart-count variables remain included.
Flag same-model agreement, annotation dependence and unstable coefficients in
interpretation; do not call those relationships causal validation.

Global exclusions: `song_id`, source coordinates, exact title/artist/release-title
identity strings, population flag, and acquisition/confidence/precision bookkeeping
as substantive predictors. Those diagnostic variables remain targets. Raw
`mb_earliest_release_date` is replaced once by year; monthly `month` is an alias
of the represented chart date, not another variable. Counts of accepted metadata
links remain available for retrospective coverage diagnostics, with their limited
interpretation stated.

Target-specific restrictions:

- For a sentiment target, **each** of the other two sentiment variables is allowed
  alone, but **any set containing both is excluded**: it reconstructs the target.
  For any other target, a set containing all three sentiment probabilities is
  excluded as an affine duplicate with the intercept. Floating-point residue is
  not an independent measurement.
- Primary and secondary genre are both conceptual predictors for other targets.
  When either genre output is the target, exclude the other: secondary labels
  are explicitly constructed to omit the primary label, which reveals target
  membership by construction. This is narrower than a same-model ban.
- Lyrics-status/availability targets exclude all 42 score variables, including
  their missing indicators: production requires successful acquisition.
- MusicBrainz match-status/precision targets exclude the seven linked metadata
  predictors (three durations, three counts, year), whose values/missingness are
  generated by the process being predicted.
- `first_chart_date` excludes both genre outputs because frozen genre inference
  explicitly receives that date, and excludes all seven linked MusicBrainz
  metadata predictors because acceptance uses the date as a temporal anchor.
  This follows `src/genre_production.py` and
  `src/musicbrainz_asset_match.py: evaluate/decide`; it is target-conditioned
  annotation/selection, not an arbitrary correlation cutoff. Other chart-history
  dates remain valid retrospective reconstruction variables, with near-alias
  interpretation cautions.
- Chart-observation universes append current rank, actual chart date,
  `reported_last_week_rank`, `reported_peak_position`, `reported_weeks_on_chart`,
  then exclude `best_chart_rank`, all four final history counts/points,
  `last_chart_date`, `first_snapshot_month`, `last_snapshot_month` for **every**
  chart target. These expose later chart history.
- Current rank additionally excludes reported peak because the current target
  can enter that peak. Previous-week rank additionally excludes current rank,
  current reported peak/weeks and `first_chart_date`, which can be later than
  the previous-week outcome. Current rank remains an allowed explanatory
  covariate for current peak/weeks; that is concurrent chart-state explanation,
  not prediction before the chart is published.

### Retrospective explanation versus forecasting

**All reported counts describe retrospective prediction on the frozen release.**
Career summaries can explain another completed song-level measurement at this
retrospective origin. They cannot predict lyrical content or success at release.
Chronological evaluation measures transfer to later song cohorts; it does not
make historical enrichment into information that was available then.
Model scores, GPT genre judgments and accepted MusicBrainz manifestations were
obtained retrospectively. Their historical availability and model-training
knowledge are not established by these public CSVs.

A genuine forecast needs a declared origin (before debut, at debut, or prior
weekly chart) and horizon, archived as-of metadata/lyrics/genre availability,
lagged chart features constructed strictly before that origin, and fixed-horizon
labels or censoring treatment. It must also avoid selecting a weekly population
using future month-end membership. **No executable forecasting universe or
forecast model count is claimed here**: these missing origin/provenance choices
are approval gates, not an excuse to drop valid retrospective combinations.
[`forecast_constraints.json`](../analysis/planning/regression_search/forecast_constraints.json)
records this status for every task.

## 4. Exact search counts and feature dimensions

With `p` allowed original variables, unrestricted size-k counts are `C(p,k)`.
If a forbidden subset has size `b`, subtract `C(p-b,k-b)` when `k >= b`.
The audit uses general inclusion-exclusion for overlapping forbidden subsets and
has a separate brute-force known-answer test. No fit is needed to count the search.

For example, an ordinary score target has `p=59`, with the three-sentiment
redundancy removed: **59, 1,711, 32,508, 455,070** sets for k=1–4.
A sentiment target has `p=59` but forbids the other sentiment pair:
**59, 1,710, 32,452, 453,530**.

| Family | Targets | k=1 | k=2 | k=3 | k=4 | Total |
| --- | --- | --- | --- | --- | --- | --- |
| binary | 1 | 18 | 153 | 816 | 3,060 | 4,047 |
| multiclass | 4 | 182 | 4,562 | 78,521 | 1,012,825 | 1,096,090 |
| multilabel | 1 | 58 | 1,653 | 30,855 | 424,215 | 456,781 |
| ordinal_diagnostic | 1 | 60 | 1,770 | 34,219 | 487,578 | 523,627 |
| ordinal_rank | 7 | 385 | 10,413 | 184,612 | 2,412,902 | 2,608,312 |
| regression | 59 | 3,466 | 100,118 | 1,895,317 | 26,444,027 | 28,442,928 |
| ALL | 73 | 4,169 | 118,669 | 2,224,340 | 30,784,607 | 33,131,785 |

### Every target, with its complete combination counts

`p` counts conceptual predictors. `N` counts observed target rows before split
purging; song tasks have one row per identity. See the adjacent registry for
distinct-song denominators, transformations, diagnostics and missingness.

| Task (table:target) | Family | N | p | k=1 | k=2 | k=3 | k=4 | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `songs:ll_sexual_content` | regression | 20,979 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:ll_violence` | regression | 20,979 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:ll_explicit_language` | regression | 20,979 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:ll_substance_use` | regression | 20,979 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:detox_toxicity` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:detox_severe_toxicity` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:detox_obscene` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:detox_threat` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:detox_insult` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:detox_identity_attack` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:detox_sexual_explicit` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_admiration` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_amusement` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_anger` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_annoyance` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_approval` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_caring` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_confusion` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_curiosity` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_desire` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_disappointment` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_disapproval` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_disgust` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_embarrassment` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_excitement` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_fear` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_gratitude` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_grief` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_joy` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_love` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_nervousness` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_optimism` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_pride` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_realization` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_relief` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_remorse` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_sadness` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_surprise` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:emotion_neutral` | regression | 20,981 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:sentiment_negative` | regression | 20,981 | 59 | 59 | 1,710 | 32,452 | 453,530 | 487,751 |
| `songs:sentiment_neutral` | regression | 20,981 | 59 | 59 | 1,710 | 32,452 | 453,530 | 487,751 |
| `songs:sentiment_positive` | regression | 20,981 | 59 | 59 | 1,710 | 32,452 | 453,530 | 487,751 |
| `songs:mb_duration_median_seconds` | regression | 22,194 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:mb_duration_min_seconds` | regression | 22,194 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:mb_duration_max_seconds` | regression | 22,194 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:mb_recording_count` | regression | 22,290 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:mb_release_count` | regression | 22,290 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:mb_distinct_duration_count` | regression | 22,290 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:weekly_observation_count` | regression | 28,041 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:chart_weeks` | regression | 28,041 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:total_chart_points` | regression | 28,041 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:snapshot_months_selected` | regression | 28,041 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:first_chart_date` | regression | 28,041 | 50 | 50 | 1,225 | 19,599 | 230,253 | 251,127 |
| `songs:last_chart_date` | regression | 28,041 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:first_snapshot_month` | regression | 28,041 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:last_snapshot_month` | regression | 28,041 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:mb_release_year` | regression | 22,058 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:best_chart_rank` | ordinal_rank | 28,041 | 59 | 59 | 1,711 | 32,508 | 455,070 | 489,348 |
| `songs:primary_genre` | multiclass | 28,041 | 58 | 58 | 1,653 | 30,855 | 424,215 | 456,781 |
| `songs:secondary_genres` | multilabel | 28,041 | 58 | 58 | 1,653 | 30,855 | 424,215 | 456,781 |
| `songs:musicbrainz_match_status` | multiclass | 28,041 | 53 | 53 | 1,378 | 23,425 | 292,775 | 317,631 |
| `songs:mb_release_date_precision` | multiclass | 22,058 | 53 | 53 | 1,378 | 23,425 | 292,775 | 317,631 |
| `songs:lyrics_status` | multiclass | 28,041 | 18 | 18 | 153 | 816 | 3,060 | 4,047 |
| `songs:lyrics_available` | binary | 28,041 | 18 | 18 | 153 | 816 | 3,060 | 4,047 |
| `songs:genre_confidence` | ordinal_diagnostic | 28,041 | 60 | 60 | 1,770 | 34,219 | 487,578 | 523,627 |
| `monthly:monthly_rank` | ordinal_rank | 81,797 | 55 | 55 | 1,485 | 26,234 | 341,003 | 368,777 |
| `monthly:reported_last_week_rank` | ordinal_rank | 73,424 | 52 | 52 | 1,326 | 22,099 | 270,676 | 294,153 |
| `monthly:reported_peak_position` | ordinal_rank | 81,797 | 56 | 56 | 1,540 | 27,719 | 367,237 | 396,552 |
| `monthly:reported_weeks_on_chart` | regression | 81,797 | 56 | 56 | 1,540 | 27,719 | 367,237 | 396,552 |
| `weekly:weekly_rank` | ordinal_rank | 355,487 | 55 | 55 | 1,485 | 26,234 | 341,003 | 368,777 |
| `weekly:reported_last_week_rank` | ordinal_rank | 319,130 | 52 | 52 | 1,326 | 22,099 | 270,676 | 294,153 |
| `weekly:reported_peak_position` | ordinal_rank | 355,487 | 56 | 56 | 1,540 | 27,719 | 367,237 | 396,552 |
| `weekly:reported_weeks_on_chart` | regression | 355,487 | 56 | 56 | 1,540 | 27,719 | 367,237 | 396,552 |

These counts do **not** multiply by duplicate song rows, coefficient count or
number of genre dummies. Multi-label modelling has 16 output heads per conceptual
target/set. OLS plus four Ridge penalties across three folds means **15 numerical
fits per set**, or **426,643,920**
fits across the 59 regression tasks, before the small final selected-model refits.
Ordinal likelihoods and classification need their own estimator/grid accounting;
they are not included in that OLS/Ridge total.

### Encodings and missingness

Use one target-specific observation mask: **never impute the outcome**. Keep that
mask identical across all candidate sets for the target. For every numerical
predictor, learn a median on the training fold, impute predictors only, and append
a fixed missing indicator. Fit scaling on training data only. A fold with an
entirely absent predictor uses a deterministic zero placeholder plus its indicator;
constant encoded columns are removed, while the conceptual set remains logged as
an evaluated degenerate/intercept-equivalent specification.

Primary genre is **one variable**: 15 fixed-taxonomy contrasts (Pop reference) plus
one missing indicator, maximum 16 columns. Secondary genre is **one variable**:
16 multi-hot columns plus one missing indicator, maximum 17 columns; `[]` is an
observed empty set. Keep the public 16-label taxonomy, with no post hoc merge.
Train-absent levels have no estimable coefficient; fixed zero coefficients and
the unsupported-level flag are preferable to learning levels from held-out data.
The benchmark uses unweighted train-only column standardization and then
song-balanced fit/metric weights. The final implementation must freeze this
order explicitly, including how binary indicators are scaled for Ridge.

Thus a four-number set has at most **9 coefficients including intercept**;
two genre variables plus two numerical variables have at most **38**.
The full cached target-specific matrix is at most **150 columns including
intercept** in this proposal (148 for a typical song measurement target).
Constant-column removal reduces actual size: the benchmark used 99 song,
134 monthly and 136 weekly full-matrix columns. Each target's upper-bound
dimensions and float64 byte size are in `search_counts.csv`.

Imputation keeps all target-observed rows available to every set, so different
complete-case sample sizes cannot masquerade as feature improvements. Missingness
is plausibly nonrandom: success/metadata coverage and enrichment scope carry era
and genre signals. Keep missingness indicators tied to their original predictor;
never introduce them as extra independently selectable variables. For lyric
diagnostic targets the score/indicator leakage ban applies before encoding.

Complete-case sensitivities must use a **predeclared common cohort** within each
comparison, never set-dependent row dropping. The all-predictor complete cohort
for many song targets has 13,469 training and 1,749 validation songs, much smaller
than target-observed cohorts. These sensitivities alter the estimand and are
additional approved runs, not silently substituted counts.

## 5. Validation, sample size and baselines

Proposed outer calendar blocks: training debut before **2010-01-01**, validation
debut in **2010–2017**, final test debut from **2018-01-01** onward. These dates are
operational split proposals, not COVID breakpoints or tested structural changes.
For the audited conservative split, retain training songs only if their last
observed chart is also before 2010; retain validation songs only if their last
observed chart is before 2018. Purge entire boundary-crossing songs. This prevents
repeated identities or completed-career label windows from spanning blocks.
Use `song_id` for every identity assertion, bootstrap and split; title/artist
reconstruction is unnecessary with the public sources.

The snapshot is through 2026-09-19. Final-history targets are **observed-through-
snapshot totals**, not uncensored lifetime success. Recent songs have shorter
follow-up; re-entries and the 1958 boundary further complicate lifetime claims.
Purging by last observed date also selects against long-lived/recurrent songs.
For real historical forecasting, rebuild label windows as-of each origin and
approve a fixed horizon or survival/censoring method; do not treat this
retrospective purge as a solution to forecasting selection bias.

Song universe: **22,032 train / 2,326 validation / 3,387 test / 296 purged**.
Observed-target examples:

| Target | Train rows / songs | Validation rows / songs | Test rows / songs | Purged rows |
| --- | --- | --- | --- | --- |
| songs:ll_sexual_content | 16,079 / 16,079 | 1,907 / 1,907 | 2,729 / 2,729 | 264 |
| songs:detox_toxicity | 16,081 / 16,081 | 1,907 / 1,907 | 2,729 / 2,729 | 264 |
| songs:mb_duration_median_seconds | 16,888 / 16,888 | 2,093 / 2,093 | 2,956 / 2,956 | 257 |
| songs:mb_release_year | 16,873 / 16,873 | 2,089 / 2,089 | 2,838 / 2,838 | 258 |
| songs:chart_weeks | 22,032 / 22,032 | 2,326 / 2,326 | 3,387 / 3,387 | 296 |
| monthly:monthly_rank | 61,121 / 22,032 | 8,875 / 2,326 | 10,110 / 3,387 | 1,691 |
| weekly:weekly_rank | 265,873 / 23,845 | 38,580 / 3,198 | 43,696 / 5,377 | 7,338 |

Every target/block's row count, unique songs, observed variation and common-complete
count is in [`split_summary.csv`](../analysis/planning/regression_search/split_summary.csv).
The file also gives `(sum n_song)^2 / sum(n_song^2)`, the cluster effective sample
size for an unweighted row mean under perfect within-song dependence. It is a
diagnostic, not an estimated regression-residual ESS. For example, monthly
validation's 8,875 rows correspond to 2,326 songs and a full-dependence row-weight
ESS of about 1,641; weekly validation's 38,580 rows to 3,198 songs and about 1,666.
Residual dependence and serial correlation can lower information further.

Fit and evaluate observation-level tasks with inverse occurrence counts within
each song/block, normalized to mean weight 1, so each song contributes equal
total weight. A chart-exposure-weighted alternative is a different estimand and
requires approval. Song-level outcomes are fit once per `songs.csv` identity,
never once per repeated chart row. Preserve duplicate source observations in the
chart tasks and their within-song weights. Remaining artist overlap is not
song-ID leakage; an artist-held-out sensitivity would answer a different
generalization question and needs a careful credit/entity rule.

Within pre-test data, recommended selection uses three expanding, song-disjoint
validation blocks: **1990–1999, 2000–2009, 2010–2017**, each trained only on earlier
songs, with the same whole-song/label-window boundary rule. Fit all transforms
inside each training fold. Select a single predictor set/estimator/penalty per
target from aggregate validation skill; freeze it before final-test use.
Final refit uses all eligible pre-2018 songs, with group overlap and label-window
checks rerun. The final test is evaluated once per frozen target model.
The source data have already supported public EDA: “untouched test” here means
untouched by this **search/selection**, not never previously described by anyone.

The audit examined test schema, counts and category support only. The benchmark
excluded test rows before feature fitting and scoring; it did not rank candidates.
Time ordering alone and generic GroupKFold alone each miss part of this requirement:
use custom splits satisfying **both** chronology and disjoint song identities.
See the [scikit-learn cross-validation guide](https://scikit-learn.org/stable/modules/cross_validation.html).
All imputation, scaling and model selection must be trained without test data;
see [preprocessing leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html).

### Baselines and fair comparison

For **each numerical target/fold**, fit an intercept-only **training weighted mean**
baseline for squared error and a **training weighted median** baseline for MAE.
Report weighted R², MAE, RMSE, target support and uncertainty on exactly the same
rows/weights for every candidate. R² uses the held-out weighted mean only in the
scoring denominator, not as a prediction. Zero held-out variance makes R²
undefined; do not coerce it into an apparently successful score.

For each target also report baseline-relative MSE skill
`1 - MSE_model/MSE_training_mean_baseline`, relative MAE versus the training-median
baseline, and optional RMSE divided by **training** target SD/IQR with a zero-scale
guard. Negative skill is allowed. Never rank targets by raw MAE across seconds,
years, points and 0–1 scores. Even unitless R² comparisons need matching time
blocks, target populations and coverage: provide a common-song-cohort comparison
where possible and a separate coverage table. Near-identity chart-count tasks and
compositional/model-agreement tasks must be labelled as such in predictability
comparisons, without removing their valid combinations.

For ranks, use a training empirical rank-distribution / median-rank baseline and
ordinal log loss, ranked probability score and rank MAE; numeric-rank R² is only
an approved sensitivity. For nominal targets use training class frequencies,
smoothed with a predeclared rule, and a majority-class baseline; report log loss,
macro-F1, balanced accuracy and class counts. Binary tasks additionally use Brier
score, PR-AUC and ROC-AUC when both classes exist. Multi-label targets use
per-label prevalences, binary log loss, macro/micro PR/F1 and label support; an
empty secondary-genre list is a valid all-zero response. No raw-error cross-family
ranking is meaningful. Rare/absent classes have undefined metrics where appropriate.

### Millions of comparisons

Selecting the best of millions of noisy validation scores overfits validation
even when each individual fit has only four original predictors. Three time
folds reduce dependence on one period but do not eliminate selection bias.
Keep the final test isolated; lock metrics, tie breaking (prefer fewer original
variables, then a deterministic order), Ridge grid and candidate universe before
training. Report fold stability, uncertainty clustered by song and calendar
blocks, and all attempted-model counts. Avoid naïve selected-model p-values.
If estimating the performance of the **selection procedure** with nested outer
time folds, rerun the complete selection inside each outer training block and
budget that extra multiplicative cost. Choosing the “most predictable target”
from test results itself incurs another selection effect; report the full
prespecified target panel with uncertainty rather than a test-selected winner.
See [Cawley & Talbot (2010)](https://www.jmlr.org/papers/v11/cawley10a.html).

## 6. Bounded computational feasibility

Hardware: Apple M2 Pro, **12 logical CPUs / 16 GiB RAM**. Benchmark used **one BLAS
thread**, Python 3.9.6, NumPy 1.26.4,
pandas 2.2.2, SciPy 1.13.1, scikit-learn
1.5.2. These installed versions differ from some repository
pins; no dependency files or environments were changed. Rebenchmark the selected
production environment before a long run.

The seed is 491, with exactly 16 sets per k per resolution (64 each). Sampling
includes numeric-only, primary-genre, secondary-genre and both-genre sets so wide
matrices are exercised. It uses full proposed training/validation rows, not tiny
row subsamples. The exact sets and widths are in `benchmark_samples.csv`;
all timings are in `benchmark_timings.csv`. Three repeats are summarized by their
median; estimates include feature gathering and small cross-product slicing.
No fitted model or candidate score ranking is retained.

| Case | Train / validation rows | Cached matrix columns | SVD fallback OLS sets / 64 | Read + prep (s) | Cross-products (s) |
| --- | --- | --- | --- | --- | --- |
| songs:detox_toxicity | 16,081 / 1,907 | 99 | 2 / 64 | 0.369 | 0.012 |
| monthly:monthly_rank | 61,121 / 8,875 | 134 | 35 / 64 | 1.381 | 0.075 |
| weekly:weekly_rank | 265,873 / 38,580 | 136 | 37 / 64 | 9.358 | 0.309 |

Direct rank-aware NumPy OLS and cached OLS/Ridge predictions agreed to at most
1.22e-10
absolute prediction difference; maximum relative SSE discrepancy was
1.56e-12.
The default scikit-learn 1.5.2 OLS path was rejected during the pilot because
duplicated metadata missing indicators could yield very large cancelling
coefficients and a roughly 0.002 prediction discrepancy. The retained benchmark
uses explicit rank-aware SVD (`numpy.linalg.lstsq`, `rcond=None`) for the direct
OLS reference. This is a numerical implementation finding, not a dataset edit.

### Wall-time extrapolation

The following serial estimates cover **all 59 numerical targets**, weighting
each k/genre-encoding stratum by its exact combination count and adjusting for
target-specific sample size. They include observed fallback costs. They are
projections from a small benchmark, **not measured full-campaign durations**.

| Implementation | One OLS / one fold (h) | One Ridge alpha / one fold (h) | OLS + 4 Ridge alphas × 3 folds (h) |
| --- | --- | --- | --- |
| Direct fits + exact MAE | 16.63 | 13.65 | 213.74 |
| Cached squared-error metrics only | 6.23 | 0.46 | 24.25 |
| Cached fits + exact per-set MAE | 7.03 | 1.26 | 36.20 |
| Cached fits + batched exact MAE | 6.39 | 0.62 | 26.62 |

Budget **0.5×–5×** these central estimates for sample/fallback variability,
Python scheduling, checkpoint writing, cache layout, temperature and production
environment differences; this is a planning range, not a statistical confidence
interval. The three-fold estimate uses the largest fold timing for all folds.
Per-target estimates are in `runtime_estimates.csv`. For example, the cached
all-metrics central total is **36.2 h**,
with an approximate **18.1–181.0 h**
serial planning range. Input preparation and cross-products add small per-target
costs; result serialization and recovery overhead still need a production pilot.

OLS/Ridge numeric-rank sensitivity costs are provided separately in
`feasibility_estimates.json`; **native ordinal, multinomial and multilabel runtimes
are unmeasured**. Their iterative fits, convergence failures, 99 rank thresholds
or 16 output heads cannot honestly inherit the small-matrix OLS estimate.
Do a bounded timing pilot for those families after their loss/link specifications
are approved. No heuristic substitution has been proposed.

### RAM and storage

Measured peak process RSS was **1.81 GiB**,
including sequential CSV parsing, temporary DataFrames and matrix copies. The
weekly train+validation encoded matrix occupied
**315.9 MiB**; its cached
train/validation cross-products plus cross-vectors occupied
**291.1 KiB**.
All 355,487 weekly rows at the conservative 150-column bound would be about
**407 MiB** as one float64 matrix, before source frames or worker copies.
Process one resolution/target mask at a time, release source frames, and share
read-only encoded arrays or use memory maps. Start with **2–4 workers and one BLAS
thread each**, budgeting roughly **4–10 GiB** total on this 16-GiB machine.
That parallel RAM/speedup range is unmeasured; do not assume 12× speedup or copy
every full DataFrame into every worker.

At a proposed compact **128-byte aggregate record** (target ID, four predictor
IDs, k, estimator/penalty ID, counts, metric accumulators, numerical flags), one
record for every task/set is about **4.24 GB**.
Five estimator aggregates for every numerical set are about
**18.20 GB**.
Keeping every one of 15 fold/estimator records instead costs about
**54.61 GB**;
all maximum-width coefficient vectors would add up to
**129.70 GB**.
These are uncompressed payload estimates, excluding format metadata and duplicate
checkpoints; text CSV can be larger. Compression gains are not assumed.
Stream typed partitioned results, retain candidate hashes and sufficient fold
summaries, and serialize coefficients only for selected/finalist diagnostics.
Do not save millions of model objects or per-row predictions. Reserve roughly
25–40 GB for the aggregate-result numerical protocol, or 70+ GB if every fit
record is retained; choose retention before execution.

### Recommended exhaustive implementation

1. Freeze this approved schema/input-hash manifest, target masks, splits,
   conceptual encodings, weighting, metric rules and estimator grids. Use raw
   public tables; retain identities and verify source coordinates.
2. Prepare each training fold once. Cache `X'WX`, `X'Wy`, `y'Wy`, weight sums,
   validation cross-products and weighted target moments. Reuse across targets
   only when masks, encodings, weights and scalers are identical. Never construct
   each matrix with a fresh pandas formula fit.
3. Enumerate all allowed subsets deterministically, keyed by table/target and
   sorted original-variable IDs. Extract the corresponding encoded blocks,
   including intercept. Solve OLS/Ridge small systems, penalizing no intercept.
   A proposed Ridge grid is normalized lambda in
   `{0.0001, 0.001, 0.01, 0.1}`, with `alpha = n_train * lambda` for mean-one
   sample weights; it is not selected from the benchmark.
4. Check constant columns, rank and conditioning. Normal equations square the
   design condition number. At Gram-system condition >1e10, the benchmark uses
   direct weighted SVD for OLS. Do not label a singular candidate “untried” or
   silently drop correlated variables. Log its rank and minimum-norm convention.
   Exact duplicate encoded columns can potentially be coalesced, but preserving
   Ridge penalties and out-of-sample predictions requires explicit equivalence
   tests; the timing estimate does not assume that unimplemented speedup.
5. Compute validation SSE as `y'Wy - 2 beta'X'Wy + beta'X'WX beta`, with a
   scale-aware cancellation check and direct recomputation when unstable. Derive
   R² and RMSE from it. **MAE cannot be recovered from cross-products**: calculate
   every candidate's exact absolute residuals in bounded row/model batches if
   all-model MAE is required. Batched projection was measured and was not
   automatically faster in this pilot. A “MAE only for finalists” alternative
   saves work but changes reporting and requires explicit approval.
6. Parallelize deterministic batches by target/k/subset index with stable seeds,
   bounded queues and one BLAS thread per worker. Checkpoint input/spec hashes,
   completed index ranges and error states. Streaming ranking/aggregation must
   still evaluate every valid candidate; heuristic feature screening, beam
   search, stepwise selection, correlation cutoffs and early stopping by score
   are not substitutes for this exhaustive specification.
7. Validate optimized versus direct fits on deterministic random sets and
   adversarial rank-deficient/missingness cases. Only then run the approved
   campaign, freeze winners and perform the final held-out evaluation.

## 7. Validation of these planning artifacts

Twelve focused planning tests passed: complete target coverage, exclusion rules,
retained correlations, inclusion-exclusion versus brute force, whole-song temporal
purging, bounded deterministic benchmark sampling, training-only encoding,
weighted OLS/Ridge equivalence including exact duplicates, and saved count/hash
consistency, complete raw-field dispositions, benchmark guards and exact runtime
stratum partitions. Subsequent estimate/renderer validation is recorded in
`validation_results.json`.

The existing repository suite ran **364 tests in 60.156 seconds: 360 passed,
1 skipped, 3 errored**. All three errors are fresh-clone artifact availability:
`analysis/moving_averages/data/monthly_classifier_by_genre.csv` is absent while
its `.csv.xz` is tracked. Affected tests are:

- `test_figure_presentation.PresentationTests.test_published_audit_covers_catalog_and_no_unresolved_default_flags`
- `test_repository_layout.RepositoryLayoutTests.test_artifacts_links_frozen_implementation_and_ignore_rules`
- `test_repository_layout.RepositoryLayoutTests.test_overlay_corruption_is_not_exempt_from_integrity_checks`

The tests fail opening that file before their assertions, independently of the
planning modules. No existing analysis was regenerated or decompressed in place.
The private-store final-dataset rebuild validator was not run: the fresh clone
lacks its private prerequisites. Public file hashes and unchanged Git-tracked
source/analysis bytes were checked instead. This is a precise validation limit,
not a claim that the entire repository test suite is green.

Reproduce planning only, from the repository root:

```bash
python3 analysis/planning/regression_search/audit.py
python3 -m unittest discover -s analysis/planning/regression_search -p 'test_*.py' -v
python3 analysis/planning/regression_search/benchmark.py
python3 analysis/planning/regression_search/estimate.py
python3 analysis/planning/regression_search/render_report.py
```

`audit.py` inventories/counts only; `benchmark.py` has a hard 192-set limit;
`estimate.py` and `render_report.py` perform arithmetic/rendering only.
There is no full-campaign fit entry point in these artifacts. Inputs are hashed
before/after read-only work. All new files are under `analysis/planning/regression_search/`
except this requested report; existing datasets, scores, labels and analyses remain intact.

## 8. Decisions requiring approval before training

1. **Exact universe:** accept the 73-task retrospective proposal, including timing
   reconstruction and acquisition diagnostics, or explicitly amend it. Scientific
   claims and diagnostic results remain separate. Any amendment regenerates counts.
2. **Population and encoding:** use public song/monthly/weekly tables, preserve
   `song_id`, continuous LyricLens scores and 16 genres; approve the two genre
   conceptual groups and structural exclusions. The teammate preprocessing
   outputs remain unchanged; repairing their exports is a separate task.
3. **Origin:** confirm retrospective later-cohort generalization. Genuine forecasting
   requires another specification and as-of availability audit; no forecast
   training is authorized by this plan.
4. **Validation:** approve calendar boundaries, inner expanding blocks,
   whole-song purging, right-censoring interpretation, song-balanced weighting
   and the test-isolation rule. Decide whether fixed-horizon success targets are
   required instead of the frozen observed-history outcomes.
5. **Models:** approve OLS plus the four normalized Ridge penalties, and separately
   choose ordinal/multinomial/multilabel links, regularization and treatment of
   unsupported rare classes. Do not force those categories into OLS.
6. **Missingness and metrics:** approve train-only imputation, fixed indicators,
   common per-target masks, baseline-relative selection metric, tie rule and
   exact MAE for every candidate versus an explicitly scoped finalist-only option.
7. **Compute and retention:** approve wall-time/RAM budget, initial worker count,
   checkpoint/result format, storage retention and a bounded native-categorical
   timing pilot. No full-campaign execution follows automatically.

**Stop point reached: feasibility audit and planning artifacts only.**
