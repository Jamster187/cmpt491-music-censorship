# Feature expansion v1 methodology

## Scope and prediction moment

This authorized campaign implements local features and evaluates chart performance among songs that have already entered the Billboard Hot 100. The prediction moment is immediately after publication of the first observed chart containing an exact original title/full artist-credit identity. The entire published debut chart is available then. Artist history, prior reference corpora and collaboration histories use dates strictly earlier than that date. All songs debuting on the same date are processed before any of their observations update history.

Source chart dates are chart labels; actual publication clock times and song release dates are not observed. Ordering and calendar calculations use those source date labels.

The supplied local chart snapshot is reported to come from [mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100); this is reported provenance rather than independent source verification. All 32,723 weekly identities and 355,487 source rows supply chart history, including identities outside the 28,041-song final monthly population. Original title/credit strings and song IDs are preserved. No entity merge, acquisition, new content-classifier inference, COVID analysis or original-dataset rewrite occurs.

## Outcomes and censoring

The primary window is **[first chart date, first chart date + 182 days)**. Follow-up is complete only if the global final source-chart date is at least the exclusive window end. The source ends on 2026-09-19; 305 identities lack complete 26-week follow-up. This conservative rule also excludes a window ending just after the final source chart. The 12-week sensitivity uses the same rule with 84 days; 111 identities lack that follow-up.

| Target | 26-week definition |
|---|---|
| Top 10 | At least one observed rank <=10; exclude identities already <=10 on debut |
| Long chart life | At least 13 distinct chart dates in the window |
| Best rank | Minimum source rank in the window |
| Chart weeks | Count of distinct chart dates in the window |
| Chart points | Sum of 101-rank over all source rows in the window |

The 12-week long-life threshold is six distinct chart dates. Numerical outcomes include the known debut contribution; this is disclosed partial target information, not an undisclosed future predictor. Top-10-at-debut cases are already resolved, so their classification would be trivial and they are excluded. Fixed windows do not estimate complete eventual careers. Full observed totals, the last observed chart date, near-endpoint presence (within 28 days), and appearances at least 26 weeks after debut are descriptive audit fields only. There are 1,910 identities with an observed appearance at least 26 weeks after debut; these include both sustained runs and later returns.

Every source observation is retained. Thirteen repeated song/date rows exist. Points sum these rows; weeks count distinct song/date pairs; rank calculations use minimum rank within a song/date. The source has 3,553 seven-day intervals and one twelve-day interval. Turnover and consecutive-rank-change calculations do not cross gaps longer than eight days. A reentry requires a known absent chart and no such source gap since the prior appearance.

## Point-in-time engineering

The [dictionary](feature_dictionary.csv) gives the exact definition, source fields, calculation, type, availability, leakage risk and matching limits of each new column. There are **57 new constructs across 58 columns**; the circular season construct needs sine and cosine. Of the 59 researched local candidates, 48 are implemented. The additional columns cover explicitly requested prior Top-40 attainment, prior chart weeks/best rank, contemporaneous competing entrants, mean lyric line length, current same-genre share, and prior consensus-entity/team success. The [59-candidate disposition table](candidate_dispositions.csv) records all decisions.

The dictionary's numeric dtype is the model-input representation (`float64`); count and binary-flag features are integer-valued within that representation. CSV itself has no native numeric types.

Artist history is indexed by the **exact complete original credit**, including collaborations. It includes prior song/attained Top-10/attained Top-40 counts; accumulated points and distinct song/date appearances; prior best rank; observed career age; time since prior entry; activity in the previous 365 days; and the slope of points across the previous 13 observed charts, counting absence as zero. Prior-song longevity is truncated at the focal debut. When previous entries share a date, the previous-entry rank feature takes the best attained rank across the tied entries. Zero history means none observed since 1958, not an actual new career.

Chart context uses earlier charts plus explicitly contemporaneous information available at publication: competing first entrants, same-credit debut clusters, and other established credits. Counts use actual source populations, not an assumed 100 rows. Exact title reuse is a count, never an identity merge. The title and credit marker rules are documented Unicode/English string rules; ampersands do not imply two people. Calendar weekday is an observed calendar field. **An official chart-methodology regime was deferred:** source weekday changes do not establish sales/radio/streaming methodology, and no independently validated historical regime crosswalk was supplied locally.

Thirty-three new columns are category C (available at chart publication). Twenty-five are category F (modern retrospective measurement). F includes all lyric structure, modern genre/content references, and MusicBrainz entity-credit features. Strict chart-prefix joins remove reference lookahead but do not make modern labels or crosswalks historically available.

The retained approved recording variants agree on the ordered structured artist-credit list for all 22,290 high-confidence study matches. Duplicate MBIDs within a list count once. Multiple returned recordings remain evidence for one study identity. Bands are single entities. The first listed entity is called **first credited**, not presumed lead vocalist; join phrases do not reliably establish performer roles. Prior collaboration teams are identical unordered sets of at least two consensus MBIDs. Each identity is counted once per entity/team, and same-day teams never enter each other's prior history. Prior histories for these features only cover locally mapped study identities, so they are incomplete lower bounds on full entity careers.

Local approved lyrics are hash-checked at their canonical paths and never sent to an external service. Their existing provenance and acquisition records remain read-only. Tokenization uses NFC, casefolding, Unicode alphanumeric tokens with internal apostrophes, and straight/curly apostrophe equivalence. Digits remain lexical tokens. Only recognized standalone bracketed section labels are removed; other bracketed text and title-equal opening lines remain lyrics. Provider repeat instructions are not expanded. MATTR averages all 50-token sliding windows and is null for shorter texts. Compression uses zlib level 9 on normalized token lines (runtime version recorded). English pronoun/negation/time lists are literal lexical measures; they do not infer language, mental state or narrative meaning. No new sentiment model is run.

Content-profile distances are RMSE across the frozen 42 scores, each on its existing [0,1] scale. There is no estimated corpus-wide scaling. Prior-hit centroids include a song only after it has attained Top 10 before the focal date; previous-chart centroids weight each available complete-profile identity once. Both comparisons inherit modern-measurement and monthly-population selection limits. Genre references use labelled earlier entries and explicitly labelled current-chart denominators, not missing genre treated as a category.

## Fair comparison populations

Two complementary tracks prevent retrospective proxies from being mislabeled as genuine historical forecasts.

| Track | A: baseline | B: new only | C: combined |
|---|---|---|---|
| Strict | Known debut rank | 33 new category-C columns | Union of A and B |
| Retrospective | Debut rank, 42 existing scores, primary genre, consistent matched duration | All 58 new columns | Union of A and B |

The retrospective track uses final-study identities with all 42 scores and nonempty parsed local lyrics. Duration is retained only for high-confidence metadata with exactly one distinct retained duration; missing duration is allowed. Release dates, acquisition statuses, final chart summaries, matched recording/release counts, and release-country/status/type fields are not predictors. Existing scores, genre and duration remain F. The baseline includes debut rank to avoid crediting new features merely for comparison against an artificially weak lyrics-only model.

Within each track and target, A/B/C share the same exact identities, outcome window and split. There is no listwise deletion by a particular feature configuration. Missing predictors are imputed from training medians; an entirely missing training column gets zero. No explicit availability indicators are added. Categorical vocabulary and numeric standardization are fitted on training rows only; unknown future categories map to all zeroes.

## Chronological partitions and model selection

The frozen [protocol](protocol.json) predates fitting. The first eligible debut is 1960-01-01, allowing a short observed-history burn-in while retaining pre-1960 observations as history. This does not eliminate 1958 left-censoring.

- Training: eligible identities whose complete target window ends on or before 2010-01-01.
- Validation: debut on or after 2010-01-01 and target window ends on or before 2018-01-01.
- Evaluation: debut on or after 2018-01-01 with complete follow-up.

Identities whose windows cross a partition boundary are purged. Each song occurs once and never crosses partitions. Same artists can appear in different periods: this tests future entries, not unseen-artist generalization. Artist-credit cluster resampling acknowledges only part of that dependence.

Each of the two tracks, three feature configurations and five outcomes evaluates three families with two fixed candidate settings: logistic C={0.1,1} or ridge alpha={1,100}; decision-tree depth={3,6}, minimum leaf 50; and histogram gradient boosting with {15,31} leaves, 120 iterations, learning rate 0.06, minimum leaf 30, L2=1 and early stopping disabled. Seed is 4911026; thread pools are limited to two. This is 180 primary candidate fits, not a combinatorial feature search.

Classification thresholds are chosen on validation from 0.10 to 0.90 in 0.05 steps, maximizing balanced accuracy, with ties favoring proximity to 0.5 and then the lower threshold. Model choice maximizes validation balanced accuracy, then minimizes Brier score. Regression selects validation MAE. No test score selects features, thresholds, hyperparameters or model families. The selected estimator remains fitted only to the training partition; there is no training-plus-validation refit. This makes all reported generalization gaps directly comparable.

## Metrics, uncertainty and interpretation

Classification reports balanced accuracy, precision, recall, F1, ROC-AUC, average precision (the reported PR-AUC convention), confusion counts, prevalence, Brier score, log loss and ten equal-width-bin expected calibration error. Undefined ROC-AUC is missing. Probabilities are raw fitted outputs with no recalibration. Regression reports R², MAE, RMSE, signed-error quantiles, median and 90th/95th-percentile absolute errors. Predictions are not clipped to physical bounds.

Simple baselines use training majority/prevalence and mean/median. Top-10 additionally uses `(prior attained Top10 count + 5 × training target prevalence) / (prior song count + 5)` and a validation-chosen threshold. The strong rank-only model is the strict A comparator.

For selected combined-versus-baseline comparisons, 199 paired resamples use identical evaluation identities in each resample, grouped separately by exact artist credit and by debut year. Percentile 95% intervals cover improvement and the combined model's primary metric. These are fixed-model intervals, not full pipeline/model-selection uncertainty. There are only nine evaluation-year clusters; different exact credits may refer to the same person. A/B/C remain the same population in every paired comparison.

Permutation importance uses at most 3,000 validation rows, three repeats and a seeded sample. It reports loss of balanced accuracy at the saved threshold or increase in MAE. It never ranks features on test results. Linear coefficients and tree impurity importances are saved for each validation-tuned family. Numeric coefficients use training-standard-deviation units; genre coefficients use unscaled 0/1 indicators, despite the shared `standardized_coefficient` table label. Group ablations remove artist history, chart competition, calendar/title, lyric structure, relative content, entity credit, existing scores, genre, duration or debut rank when present. The selected combined family and structural hyperparameters stay fixed; each reduced model fits preprocessing on training rows and reselects its threshold on validation. Negative test degradation is reported without deleting the group or retuning the final model.

Earlier historical evaluations are fixed HGB(15-leaf) models for 2000–2009 and 2010–2017, with the preceding five-year interval reserved for validation and the same window purge. The primary evaluation is further described in fixed three-year groups 2018–2020, 2021–2023 and 2024–partial 2026. These are predictive-stability summaries, not crisis-effect or causal comparisons. The 12-week sensitivity uses the prespecified HGB configuration on all three feature sets.

## Audits, preservation and reproduction

The feature builder validates exact identities and source coordinates, checks approved private-text hashes, writes temporary files and atomically replaces only the new versioned outputs. Its manifest records source, pipeline and private-provenance hashes. Existing raw inputs, Phase 1 database, public datasets and experiment outputs are protected by a local pre-campaign snapshot. No original raw anomaly is repaired.

Focused tests cover future suffixes, current-song and same-day history exclusion, distinct credits, duplicated collaborators, ambiguous entity consensus, source-row/unique-date distinctions, source gaps, release-date exclusion, right-censoring, partition purge, training-only preprocessing, short texts, conservative title handling and all supported model exports. An independent pandas calculation checks 256 identities × six historical values. Rebuilding a chart prefix through 1990 checks all 33 strict columns for 17,186 identities. A second feature build with a different Python hash seed checks byte identity. Selected model exports are replayed on every training/validation/test row; one strict combined Top-10 model in each family is refitted for bitwise prediction checks.

Public output includes the versioned features/outcomes, model specifications, validation/test predictions, diagnostics, figures and reports. Private lyrics, databases, fitted sklearn objects and intermediate checkpoints remain local. The [README](README.md) gives bounded commands and the professor demonstration. The campaign stops after publication; it does not authorize follow-on acquisition or inference.
