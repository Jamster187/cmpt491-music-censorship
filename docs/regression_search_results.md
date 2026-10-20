# Full exhaustive numerical OLS results

Completed on 2026-10-20 with the exact search implementation from `426fdf199ea5bbc170f2b6089d4ba4d1b51b1245`.
All **59 targets**, **1,998,901 unique combinations**, and **5,996,703 historical
validation fits** completed. There were 3,466 one-variable, 100,118 two-variable
and 1,895,317 three-variable combinations. The final 2018-onward test was scored
only after every validation winner was selected and the full coverage audit passed.
No winner was revised using test performance. Categorical/ordinal tasks were not run.

## Results and interpretation

The following rankings compare held-out R², which adjusts squared error for each
target's test-population variance. MAE and RMSE remain in the named target's units;
they should not be compared across different units. Selection within each target
used equal-period mean MSE skill relative to the historical training-mean baseline,
with the approved fewer-predictors/lexicographic tie rule. Thus final target ranking
and validation candidate ranking have different purposes.
Each target uses its observed-outcome population, so sample sizes and missingness
patterns differ across targets. Rankings describe that population and need not
transfer to missing or unenriched songs. Small rank differences with overlapping
uncertainty intervals should not be treated as resolved performance differences.

### Ten most predictable targets

| Rank | Target | Selected predictors | Validation R² | Test R² | Test MAE | Test RMSE | Test songs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | weekly_observation_count | chart_weeks + first_snapshot_month + last_chart_date | 1.0000 | 1.0000 | 0.0039417 | 0.0074939 | 3,387 |
| 2 | chart_weeks | first_snapshot_month + last_snapshot_month + weekly_observation_count | 1.0000 | 1.0000 | 0.0050983 | 0.013093 | 3,387 |
| 3 | last_chart_date | last_snapshot_month + snapshot_months_selected + weekly_observation_count | 0.9997 | 0.9966 | 19.701 | 52.965 | 3,387 |
| 4 | last_snapshot_month | last_chart_date + snapshot_months_selected + weekly_observation_count | 0.9997 | 0.9963 | 0.91611 | 1.8058 | 3,387 |
| 5 | first_chart_date | chart_weeks + first_snapshot_month + snapshot_months_selected | 0.9993 | 0.9937 | 13.366 | 72.216 | 3,387 |
| 6 | first_snapshot_month | chart_weeks + first_chart_date + snapshot_months_selected | 0.9993 | 0.9937 | 0.43687 | 2.3734 | 3,387 |
| 7 | snapshot_months_selected | first_chart_date + first_snapshot_month + weekly_observation_count | 0.9563 | 0.9387 | 0.39498 | 0.66733 | 3,387 |
| 8 | mb_recording_count | mb_distinct_duration_count + mb_duration_max_seconds + mb_release_count | 0.9438 | 0.9243 | 0.67274 | 1.0356 | 2,973 |
| 9 | detox_toxicity | detox_insult + detox_obscene + detox_severe_toxicity | 0.8661 | 0.9094 | 0.078519 | 0.11708 | 2,729 |
| 10 | mb_distinct_duration_count | mb_duration_median_seconds + mb_duration_min_seconds + mb_recording_count | 0.9393 | 0.9029 | 0.54187 | 0.76559 | 2,973 |

### Ten least predictable targets

| Rank | Target | Selected predictors | Validation R² | Test R² | Test MAE | Test RMSE | Test songs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | emotion_desire | emotion_approval + emotion_neutral + emotion_optimism | 0.1177 | 0.0984 | 0.053542 | 0.095409 | 2,729 |
| 51 | emotion_caring | emotion_approval + emotion_optimism + ll_substance_use | 0.0883 | 0.0834 | 0.019448 | 0.041639 | 2,729 |
| 52 | emotion_embarrassment | emotion_disappointment + emotion_disgust + emotion_realization | 0.1513 | 0.0788 | 0.0035613 | 0.017729 | 2,729 |
| 53 | emotion_amusement | emotion_joy + emotion_love + emotion_relief | 0.0909 | 0.0702 | 0.028596 | 0.06881 | 2,729 |
| 54 | emotion_remorse | emotion_disappointment + emotion_embarrassment + emotion_sadness | 0.0807 | 0.0678 | 0.0098632 | 0.04235 | 2,729 |
| 55 | emotion_disapproval | detox_obscene + emotion_annoyance + sentiment_positive | 0.1446 | 0.0604 | 0.02621 | 0.048292 | 2,729 |
| 56 | emotion_realization | emotion_embarrassment + emotion_relief + emotion_surprise | 0.1312 | 0.0561 | 0.013927 | 0.032015 | 2,729 |
| 57 | emotion_gratitude | emotion_joy + emotion_neutral + emotion_relief | 0.0109 | 0.0164 | 0.0081267 | 0.042061 | 2,729 |
| 58 | weekly:reported_weeks_on_chart | mb_release_year + reported_peak_position + weekly_rank | 0.4685 | -0.1064 | 5.3945 | 7.3533 | 5,377 |
| 59 | monthly:reported_weeks_on_chart | monthly_rank + reported_peak_position + snapshot_chart_date | 0.4288 | -0.1771 | 6.9681 | 8.7762 | 3,387 |

### Strongest lyric-score relationships

| Rank | Target | Selected predictors | Validation R² | Test R² | Test MAE | Test RMSE | Test songs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 9 | detox_toxicity | detox_insult + detox_obscene + detox_severe_toxicity | 0.8661 | 0.9094 | 0.078519 | 0.11708 | 2,729 |
| 13 | detox_insult | detox_obscene + detox_severe_toxicity + detox_toxicity | 0.7661 | 0.8596 | 0.06162 | 0.093915 | 2,729 |
| 14 | emotion_sadness | emotion_disappointment + emotion_grief + emotion_nervousness | 0.8779 | 0.8511 | 0.024866 | 0.046206 | 2,729 |
| 17 | emotion_grief | emotion_nervousness + emotion_relief + emotion_sadness | 0.8636 | 0.8177 | 0.00061214 | 0.0012996 | 2,729 |
| 18 | detox_obscene | detox_insult + detox_severe_toxicity + detox_toxicity | 0.6729 | 0.7997 | 0.11598 | 0.16799 | 2,729 |

Low R² describes the limitations of these additive models, candidate variables and
historical transfer setting. It does not establish objective randomness. The many
classifier outputs are frozen model scores, so strong score-to-score relationships
measure model agreement and overlapping content, not independent ground-truth validity.
OLS predictions are unbounded and were not clipped to score or count ranges.

Duration summaries, near-identity chart counts and related chart-date coordinates
can reconstruct one another very accurately. These retained correlations are part
of the approved universe; their high R² is not evidence of causal discovery or a
useful advance forecast. In particular, chart weeks and weekly observation count
are almost identical in the source data. Chart-date coordinates use days since
1970-01-01; first/last snapshot-month coordinates use months since 1970-01.
Release year remains a calendar year. These are the unchanged frozen conversions.

Genre appears in 8 selected models:
total_chart_points, detox_identity_attack, ll_explicit_language, ll_sexual_content, ll_violence, mb_release_count, mb_release_year, ll_substance_use. Historical date/year predictors appear in
11 selected models: weekly_observation_count, chart_weeks, last_chart_date, last_snapshot_month, first_chart_date, first_snapshot_month, snapshot_months_selected, mb_release_year, ll_substance_use, weekly:reported_weeks_on_chart, monthly:reported_weeks_on_chart.
Genre and time may encode cohort composition, measurement practices and changing
music populations. None of these observational relationships identify causal effects.

### Generalization and baselines

Targets that did not beat the refit-training mean under test squared error:
**weekly:reported_weeks_on_chart, monthly:reported_weeks_on_chart**.

Targets that did not beat the refit-training median under test absolute error:
**emotion_love, emotion_excitement, emotion_curiosity, detox_threat, emotion_approval, emotion_admiration, emotion_surprise, emotion_optimism, emotion_desire, emotion_caring, emotion_amusement, emotion_remorse, emotion_disapproval, emotion_realization, emotion_gratitude, weekly:reported_weeks_on_chart, monthly:reported_weeks_on_chart**.

Negative final R²: **weekly:reported_weeks_on_chart, monthly:reported_weeks_on_chart**. A negative R² compares with the
test-set mean; baseline skill compares with the training mean. These comparisons
can disagree under historical shift. R² drops larger than 0.10 from aggregate
validation: **emotion_joy, emotion_love, mb_release_count, mb_release_year, emotion_disgust, weekly:reported_weeks_on_chart, monthly:reported_weeks_on_chart**. These are descriptive flags,
not significance tests or a revised selection criterion.

| Target | Validation R² | Test R² | Test − validation R² | Test MSE skill |
| --- | --- | --- | --- | --- |
| mb_release_year | 0.8329 | 0.1996 | -0.6333 | 0.9799 |
| monthly:reported_weeks_on_chart | 0.4288 | -0.1771 | -0.6059 | -0.1771 |
| weekly:reported_weeks_on_chart | 0.4685 | -0.1064 | -0.5749 | -0.0588 |
| emotion_disgust | 0.3393 | 0.1871 | -0.1521 | 0.2266 |
| mb_release_count | 0.3773 | 0.2581 | -0.1192 | 0.6976 |
| emotion_joy | 0.4843 | 0.3656 | -0.1188 | 0.4099 |
| emotion_love | 0.3721 | 0.2620 | -0.1101 | 0.4381 |

All 59 models fitted successfully; successful fitting
does not imply useful generalization. 2 models
failed the squared-error baseline and 17 failed
the median absolute-error baseline. OLS selection optimizes squared-error skill,
so absolute-error improvements are not guaranteed. All 59 overall winners use
three original predictors; the best smaller models remain available separately.

The [full leaderboard](../analysis/regression_search/campaign/target_leaderboard.csv)
includes validation/test R², MAE, RMSE, both baselines, sample sizes, R²/skill/error
gaps, worst-period skill and all uncertainty intervals. Validation R²/MAE are means
over the three periods; validation RMSE is the square root of their mean MSE.
The [historical stability table](../analysis/regression_search/campaign/historical_stability.csv)
retains the chosen model's rank and skill in 1990–1999, 2000–2009 and 2010–2017,
alongside each period's own winner. The [cohort table](../analysis/regression_search/campaign/test_cohorts.csv)
shows final performance in successive two-year debut cohorts.

Uncertainty uses the implemented 500 song-cluster resamples of fixed predictions,
plus exploratory two-year debut-block intervals when at least three blocks exist.
These intervals condition on the selected fitted model: they do not include search
selection or refit uncertainty, and the many targets are not independent tests.
Recent chart histories are censored at the frozen 2026-09-19 snapshot. Follow-up
length differs by cohort, so observed career counts are not lifetime outcomes.

## Full target leaderboard

| Rank | Target | Selected predictors | Validation R² | Test R² | Test MAE | Test RMSE | Test songs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | weekly_observation_count | chart_weeks + first_snapshot_month + last_chart_date | 1.0000 | 1.0000 | 0.0039417 | 0.0074939 | 3,387 |
| 2 | chart_weeks | first_snapshot_month + last_snapshot_month + weekly_observation_count | 1.0000 | 1.0000 | 0.0050983 | 0.013093 | 3,387 |
| 3 | last_chart_date | last_snapshot_month + snapshot_months_selected + weekly_observation_count | 0.9997 | 0.9966 | 19.701 | 52.965 | 3,387 |
| 4 | last_snapshot_month | last_chart_date + snapshot_months_selected + weekly_observation_count | 0.9997 | 0.9963 | 0.91611 | 1.8058 | 3,387 |
| 5 | first_chart_date | chart_weeks + first_snapshot_month + snapshot_months_selected | 0.9993 | 0.9937 | 13.366 | 72.216 | 3,387 |
| 6 | first_snapshot_month | chart_weeks + first_chart_date + snapshot_months_selected | 0.9993 | 0.9937 | 0.43687 | 2.3734 | 3,387 |
| 7 | snapshot_months_selected | first_chart_date + first_snapshot_month + weekly_observation_count | 0.9563 | 0.9387 | 0.39498 | 0.66733 | 3,387 |
| 8 | mb_recording_count | mb_distinct_duration_count + mb_duration_max_seconds + mb_release_count | 0.9438 | 0.9243 | 0.67274 | 1.0356 | 2,973 |
| 9 | detox_toxicity | detox_insult + detox_obscene + detox_severe_toxicity | 0.8661 | 0.9094 | 0.078519 | 0.11708 | 2,729 |
| 10 | mb_distinct_duration_count | mb_duration_median_seconds + mb_duration_min_seconds + mb_recording_count | 0.9393 | 0.9029 | 0.54187 | 0.76559 | 2,973 |
| 11 | mb_duration_max_seconds | mb_distinct_duration_count + mb_duration_median_seconds + mb_duration_min_seconds | 0.4943 | 0.8770 | 9.4186 | 16.82 | 2,956 |
| 12 | total_chart_points | best_chart_rank + chart_weeks + primary_genre | 0.8643 | 0.8679 | 243.89 | 344.51 | 3,387 |
| 13 | detox_insult | detox_obscene + detox_severe_toxicity + detox_toxicity | 0.7661 | 0.8596 | 0.06162 | 0.093915 | 2,729 |
| 14 | emotion_sadness | emotion_disappointment + emotion_grief + emotion_nervousness | 0.8779 | 0.8511 | 0.024866 | 0.046206 | 2,729 |
| 15 | mb_duration_median_seconds | mb_distinct_duration_count + mb_duration_max_seconds + mb_duration_min_seconds | 0.3561 | 0.8245 | 16.551 | 18.904 | 2,956 |
| 16 | mb_duration_min_seconds | mb_distinct_duration_count + mb_duration_median_seconds + mb_recording_count | 0.4591 | 0.8207 | 13.317 | 19.171 | 2,956 |
| 17 | emotion_grief | emotion_nervousness + emotion_relief + emotion_sadness | 0.8636 | 0.8177 | 0.00061214 | 0.0012996 | 2,729 |
| 18 | detox_obscene | detox_insult + detox_severe_toxicity + detox_toxicity | 0.6729 | 0.7997 | 0.11598 | 0.16799 | 2,729 |
| 19 | sentiment_positive | emotion_joy + emotion_love + sentiment_negative | 0.7626 | 0.7259 | 0.021308 | 0.02754 | 2,729 |
| 20 | sentiment_negative | emotion_neutral + ll_violence + sentiment_positive | 0.7590 | 0.7188 | 0.024921 | 0.032622 | 2,729 |
| 21 | emotion_anger | detox_severe_toxicity + emotion_annoyance + emotion_neutral | 0.5627 | 0.6381 | 0.028608 | 0.058702 | 2,729 |
| 22 | emotion_annoyance | detox_toxicity + emotion_anger + emotion_disapproval | 0.5819 | 0.6282 | 0.043761 | 0.069716 | 2,729 |
| 23 | detox_severe_toxicity | detox_identity_attack + detox_obscene + detox_sexual_explicit | 0.4392 | 0.6155 | 0.016012 | 0.036519 | 2,729 |
| 24 | detox_identity_attack | detox_obscene + detox_severe_toxicity + primary_genre | 0.5065 | 0.5874 | 0.04879 | 0.090321 | 2,729 |
| 25 | emotion_nervousness | emotion_confusion + emotion_fear + emotion_grief | 0.6149 | 0.5220 | 0.0050994 | 0.020654 | 2,729 |
| 26 | emotion_fear | emotion_disappointment + emotion_disgust + emotion_nervousness | 0.5444 | 0.4671 | 0.01501 | 0.054823 | 2,729 |
| 27 | emotion_disappointment | emotion_disapproval + emotion_grief + emotion_sadness | 0.4655 | 0.4562 | 0.036834 | 0.063409 | 2,729 |
| 28 | ll_explicit_language | detox_toxicity + primary_genre + secondary_genres | 0.4465 | 0.4379 | 0.24542 | 0.34103 | 2,729 |
| 29 | emotion_neutral | emotion_admiration + emotion_disappointment + emotion_love | 0.4747 | 0.4330 | 0.17696 | 0.2139 | 2,729 |
| 30 | detox_sexual_explicit | detox_insult + detox_severe_toxicity + detox_toxicity | 0.4041 | 0.4274 | 0.053547 | 0.089453 | 2,729 |
| 31 | emotion_relief | emotion_joy + emotion_pride + emotion_realization | 0.4716 | 0.4007 | 0.001251 | 0.0031456 | 2,729 |
| 32 | emotion_joy | emotion_amusement + emotion_excitement + emotion_relief | 0.4843 | 0.3656 | 0.018479 | 0.051073 | 2,729 |
| 33 | ll_sexual_content | detox_obscene + emotion_sadness + primary_genre | 0.2414 | 0.3279 | 0.27962 | 0.34593 | 2,729 |
| 34 | emotion_pride | emotion_admiration + emotion_excitement + emotion_relief | 0.1821 | 0.3237 | 0.00071557 | 0.0019079 | 2,729 |
| 35 | sentiment_neutral | emotion_joy + emotion_love + sentiment_negative | 0.2364 | 0.3060 | 0.021308 | 0.02754 | 2,729 |
| 36 | ll_violence | detox_toxicity + primary_genre + sentiment_negative | 0.1864 | 0.2911 | 0.31499 | 0.37978 | 2,729 |
| 37 | emotion_love | emotion_annoyance + emotion_disappointment + emotion_neutral | 0.3721 | 0.2620 | 0.13545 | 0.17558 | 2,729 |
| 38 | mb_release_count | best_chart_rank + mb_recording_count + primary_genre | 0.3773 | 0.2581 | 15.058 | 21.116 | 2,973 |
| 39 | emotion_excitement | emotion_joy + emotion_surprise + sentiment_positive | 0.2088 | 0.2260 | 0.01245 | 0.033502 | 2,729 |
| 40 | emotion_curiosity | emotion_confusion + emotion_neutral + emotion_realization | 0.1752 | 0.2028 | 0.03464 | 0.068913 | 2,729 |
| 41 | mb_release_year | first_snapshot_month + mb_release_count + secondary_genres | 0.8329 | 0.1996 | 1.1463 | 5.1805 | 2,838 |
| 42 | emotion_confusion | emotion_curiosity + emotion_nervousness + emotion_realization | 0.2151 | 0.1981 | 0.018801 | 0.053068 | 2,729 |
| 43 | detox_threat | detox_obscene + detox_toxicity + ll_violence | 0.1632 | 0.1973 | 0.010284 | 0.031101 | 2,729 |
| 44 | emotion_disgust | emotion_anger + emotion_annoyance + emotion_embarrassment | 0.3393 | 0.1871 | 0.0039061 | 0.015259 | 2,729 |
| 45 | emotion_approval | emotion_annoyance + emotion_grief + emotion_relief | 0.1573 | 0.1722 | 0.032309 | 0.053892 | 2,729 |
| 46 | ll_substance_use | detox_obscene + last_snapshot_month + primary_genre | 0.1972 | 0.1640 | 0.34861 | 0.41895 | 2,729 |
| 47 | emotion_admiration | emotion_approval + emotion_neutral + sentiment_positive | 0.1242 | 0.1603 | 0.025162 | 0.059414 | 2,729 |
| 48 | emotion_surprise | emotion_curiosity + emotion_excitement + emotion_realization | 0.1058 | 0.1273 | 0.0064446 | 0.018657 | 2,729 |
| 49 | emotion_optimism | emotion_caring + emotion_desire + ll_sexual_content | 0.1138 | 0.1151 | 0.016556 | 0.054664 | 2,729 |
| 50 | emotion_desire | emotion_approval + emotion_neutral + emotion_optimism | 0.1177 | 0.0984 | 0.053542 | 0.095409 | 2,729 |
| 51 | emotion_caring | emotion_approval + emotion_optimism + ll_substance_use | 0.0883 | 0.0834 | 0.019448 | 0.041639 | 2,729 |
| 52 | emotion_embarrassment | emotion_disappointment + emotion_disgust + emotion_realization | 0.1513 | 0.0788 | 0.0035613 | 0.017729 | 2,729 |
| 53 | emotion_amusement | emotion_joy + emotion_love + emotion_relief | 0.0909 | 0.0702 | 0.028596 | 0.06881 | 2,729 |
| 54 | emotion_remorse | emotion_disappointment + emotion_embarrassment + emotion_sadness | 0.0807 | 0.0678 | 0.0098632 | 0.04235 | 2,729 |
| 55 | emotion_disapproval | detox_obscene + emotion_annoyance + sentiment_positive | 0.1446 | 0.0604 | 0.02621 | 0.048292 | 2,729 |
| 56 | emotion_realization | emotion_embarrassment + emotion_relief + emotion_surprise | 0.1312 | 0.0561 | 0.013927 | 0.032015 | 2,729 |
| 57 | emotion_gratitude | emotion_joy + emotion_neutral + emotion_relief | 0.0109 | 0.0164 | 0.0081267 | 0.042061 | 2,729 |
| 58 | weekly:reported_weeks_on_chart | mb_release_year + reported_peak_position + weekly_rank | 0.4685 | -0.1064 | 5.3945 | 7.3533 | 5,377 |
| 59 | monthly:reported_weeks_on_chart | monthly_rank + reported_peak_position + snapshot_chart_date | 0.4288 | -0.1771 | 6.9681 | 8.7762 | 3,387 |

## Integrity and measured resources

Independent enumeration verified every candidate identity and all three scores,
without missing or duplicate combinations. SQLite integrity checks passed for all
59 stores; repeated ranking queries and independent metric averaging agreed.
An actual no-op resume reused every completed target; validation score/ranking and
selection hashes were unchanged at the post-test audit. All 59 final encoders were
reconstructed from training rows only, predictions replayed, metrics recomputed,
and predictions checked against direct original-row LAPACK SVD. The maximum scaled
prediction discrepancy was 6.19e-11.

Whole-song temporal membership and source-row membership were checked for every
validation and final split. All six frozen implementation files and eight approved
input hashes match the launch specification. Every tracked public/preprocessing data
file and protected existing analytical output remains byte-identical. These checks
establish the approved leakage boundaries; the metadata's enrichment times are not
historically certified, so results describe retrospective cohort transfer.

| Measurement | Actual |
|---|---:|
| Full search including checkpoint/ranking work | 6.96 min |
| Final refits, test scoring and intervals | 0.84 min |
| Search + final evaluation | 7.80 min |
| No-op resume verification | 33.02 s |
| Independent pre-/post-test audits | 3.14 min |
| Complete hierarchy export and verification | 5.29 min |
| Peak child-process RAM during search/finalization | 2.42 GiB |
| Peak hierarchy export RAM | 0.32 GiB |
| SQLite result stores | 0.39 GiB |
| Complete compressed hierarchy exports | 0.36 GiB |
| Total retained campaign files, logical bytes | 0.93 GiB |

Measurements use one target worker and one BLAS thread on the same Apple M2 Pro
machine as the pilot. Search/evaluation times exclude independent audits, hierarchy
export and documentation. Detailed phase timestamps, CPU/RAM, hashes and validation
evidence are in [run_summary.json](../analysis/regression_search/campaign/run_summary.json).
Test status: PASS.

## Access and reproduction

The [experiment README](../analysis/regression_search/README.md) gives the exact
commands. The complete local hierarchy consists of 59 compressed CSVs under
`data/experiments/regression_search/campaign/hierarchies/`, containing all 1,998,901
rows, not only winners. The [hierarchy manifest](../analysis/regression_search/campaign/hierarchy_manifest.json)
records every path, row count and SHA-256. SQLite `hierarchy` views provide the same
complete rankings. The [top-ten-per-target extract](../analysis/regression_search/campaign/hierarchy_top10_per_target.csv)
is a small convenience extract, not the complete hierarchy.

The [best-by-count file](../analysis/regression_search/campaign/best_by_predictor_count.csv)
retains all 177 best one-, two- and three-variable models and their validation metrics.
Only the overall validation winner per target was evaluated on the final test.
The [selected-model manifest](../analysis/regression_search/campaign/selected_models.json)
records final specifications and hashes. Each local target directory contains its
exact encoder, coefficients, training baselines, splits, predictions and integrity
hashes. Large databases, row-level predictions and exports remain ignored by Git.
Small summaries, model specifications and audit evidence are versioned.
