# Expanded dataset V2: exhaustive OLS findings

Generated from the frozen validation selections and complete evaluation catalog. This is exploratory; the 2018-onward period was previously inspected. **Complete 26-week windows are the primary forecast evidence.** Retrospective and observed-lifetime results carry the limits below.

All **1,311,090** task/candidate combinations were retained and evaluated: **5,244,360** fits across three validation periods and final evaluation. The numerical search took **225.4 seconds** with **684.2 MiB** peak resident memory. This excludes source preservation, benchmark, reporting and integrity validation. The search used 37 strict variables or 108 retrospective variables, with every eligible one-, two- and three-variable combination.

## Primary strict forecast results

The validation-selected best-rank model carries useful evaluation signal. The selected weeks and points models do not transfer reliably to recent debuts. Negative R² is preserved and is not described as randomness. The table reports the winner selected on validation, not the candidate with the highest evaluation score.

| target | predictors | n_evaluation | validation_skill | evaluation_r2 | evaluation_mae | evaluation_rmse | evaluation_skill |
| --- | --- | --- | --- | --- | --- | --- | --- |
| best_rank | credit_previous_entry_best_rank_so_far  +  debut_rank  +  debut_time_years | 5072 | 0.068 | 0.305 | 21.892 | 23.575 | 0.327 |
| chart_weeks | credit_prior_song_observed_longevity_median  +  prior_year_unique_chart_song_count  +  same_credit_debut_cluster_size | 5072 | 0.229 | -0.511 | 8.081 | 10.159 | -0.234 |
| chart_points | debut_rank  +  prior_year_unique_chart_song_count  +  same_credit_debut_cluster_size | 5072 | 0.147 | -0.621 | 553.773 | 695.886 | -0.399 |

The outcome includes the debut chart itself, and debut rank is already known. The results therefore concern total performance after first publication, including that known initial contribution. Strict chart history covers identities without content scores as well as the monthly study cohort.

## Observed-history sensitivity

These labels use chart history observed by each cutoff on a cohort at least five years old and inactive for at least two years. They are **not verified completed lifetime outcomes**. Future returns remain possible, and their older, selected populations differ from the complete 26-week population. See `lifetime_return_audit.csv` for later-return diagnostics; no future return was used to decide a historical cohort.

| target | predictors | n_evaluation | evaluation_r2 | evaluation_mae | evaluation_rmse | evaluation_skill |
| --- | --- | --- | --- | --- | --- | --- |
| best_rank | debut_reported_peak_position  +  debut_time_years  +  prior_year_unique_chart_song_count | 2224 | 0.446 | 17.306 | 21.372 | 0.468 |
| chart_weeks | credit_prior_chart_rank_volatility  +  debut_reported_peak_position  +  prior_year_unique_chart_song_count | 2224 | -0.062 | 9.811 | 11.808 | -0.011 |
| chart_points | debut_reported_peak_position  +  prior_year_unique_chart_song_count  +  same_credit_debut_cluster_size | 2224 | -0.282 | 686.737 | 955.026 | -0.253 |

## Retrospective measurement sensitivity

Modern lyric/classifier, genre and metadata information was explicitly allowed only in this separate sensitivity. Its smaller selected population differs from the strict track. Genre annotation confidence appears in the selected models; it is a measurement-process proxy and does not establish an intrinsic musical mechanism or historically available predictive signal.

| horizon | target | predictors | n_evaluation | evaluation_r2 | evaluation_mae | evaluation_rmse |
| --- | --- | --- | --- | --- | --- | --- |
| 26 | best_rank | debut_rank  +  debut_time_years  +  genre_confidence | 2573 | 0.422 | 17.442 | 20.597 |
| 26 | chart_weeks | genre_confidence  +  prior_year_unique_chart_song_count  +  secondary_genres | 2573 | 0.034 | 7.584 | 8.718 |
| 26 | chart_points | debut_reported_peak_position  +  genre_confidence  +  secondary_genres | 2573 | -0.280 | 629.209 | 723.738 |
| observed_lifetime | best_rank | debut_reported_peak_position  +  debut_time_years  +  genre_confidence | 1095 | 0.288 | 20.205 | 22.909 |
| observed_lifetime | chart_weeks | credit_prior_song_count  +  debut_time_years  +  genre_confidence | 1095 | -0.138 | 11.021 | 13.733 |
| observed_lifetime | chart_points | debut_reported_peak_position  +  genre_confidence  +  secondary_genres | 1095 | 0.031 | 767.611 | 1011.417 |

## Incremental information on identical populations

The following differences compare the combined validation-selected winner with the original-only validation-selected winner, using identical targets, samples, splits and final training. Positive R² differences and positive error reductions favor the combined universe. A larger exhaustive universe can improve validation while making evaluation worse.

| track | horizon | target | validation_skill_difference | evaluation_r2_difference | evaluation_mae_reduction | evaluation_rmse_reduction |
| --- | --- | --- | --- | --- | --- | --- |
| strict | 26 | best_rank | 0.049 | 0.011 | 0.462 | 0.191 |
| strict | 26 | chart_weeks | 0.201 | 0.081 | 1.574 | 0.267 |
| strict | 26 | chart_points | 0.079 | 0.185 | 105.220 | 38.722 |
| strict | observed_lifetime | best_rank | 0.070 | 0.323 | 8.113 | 5.520 |
| strict | observed_lifetime | chart_weeks | 0.150 | 0.664 | 3.636 | 3.244 |
| strict | observed_lifetime | chart_points | 0.085 | 0.154 | 173.837 | 55.692 |
| retrospective | 26 | best_rank | 0.000 | 0.000 | 0.000 | 0.000 |
| retrospective | 26 | chart_weeks | 0.048 | 0.384 | 1.474 | 1.588 |
| retrospective | 26 | chart_points | 0.000 | 0.000 | 0.000 | 0.000 |
| retrospective | observed_lifetime | best_rank | 0.000 | 0.000 | 0.000 | 0.000 |
| retrospective | observed_lifetime | chart_weeks | 0.011 | -0.053 | -0.254 | -0.323 |
| retrospective | observed_lifetime | chart_points | 0.000 | 0.000 | 0.000 | 0.000 |

For strict 26-week best rank, the primary combined R² gain over original-only is only 0.011. Its paired exact-credit interval is −0.006 to 0.030; this does not establish a robust incremental gain. The debut-year interval is much narrower and uses only nine years. These are conditional exploratory intervals, not selection-adjusted confirmation.

New-only comparisons and all baseline metrics are retained in `incremental_information.csv`, `target_leaderboard.csv` and `baselines.csv`. `selected_uncertainty.csv` gives paired intervals for these improvements by artist credit and debut year. Fixed-prediction intervals do not correct the large model search or previous evaluation inspection.

## Comparison with the previously selected V1 models

This table uses identical pre-2010 training identities and identical complete 26-week evaluation identities/outcomes. V2 combinations were chosen using the frozen multi-period validation rule; V1 retains its existing selected model. Differences also reflect estimator and selection changes, so they cannot be attributed solely to newly engineered features. Primary V2 refits using more recent pre-2018 labels are shown separately in the full CSV.

| track | target | v1_method | v1_r2 | v2_r2 | delta_r2 | v1_rmse | v2_rmse |
| --- | --- | --- | --- | --- | --- | --- | --- |
| strict | best_rank | hist_gradient_boosting | 0.203 | -0.098 | -0.301 | 25.245 | 29.630 |
| strict | chart_weeks | hist_gradient_boosting | 0.022 | -0.719 | -0.741 | 8.173 | 10.836 |
| strict | chart_points | hist_gradient_boosting | -0.058 | -0.910 | -0.852 | 562.255 | 755.325 |
| retrospective | best_rank | hist_gradient_boosting | 0.097 | 0.295 | 0.198 | 25.747 | 22.746 |
| retrospective | chart_weeks | regularized | -0.255 | 0.027 | 0.282 | 9.935 | 8.748 |
| retrospective | chart_points | regularized | -0.445 | -0.462 | -0.017 | 769.009 | 773.576 |

With the exact V1 pre-2010 training population, all three strict combined OLS winners perform worse than V1. The primary pre-2018 best-rank result benefits from a different training window; it must not be presented as an unqualified improvement over V1. Retrospective matched best-rank and weeks comparisons improve, while points remains weak.

## Requested predictor checks and family contributions

All prior Top-10 count, prior chart-song count, recent presence/momentum, simultaneous-debut, competition, lyric-length/repetition, genre and calendar variables were searched whenever eligible. `focused_predictor_comparison.csv` preserves the best validation-selected combination including and excluding each requested feature. These are comparisons between selected models, not controlled ablations. The table below counts overall combined winners and shows the range of validation advantage across the six outcomes; inclusion can be harmful and a zero count does not prove absence of signal.

| track | predictor | winning_tasks | maximum_validation_skill_advantage | minimum_evaluation_r2_difference | maximum_evaluation_r2_difference |
| --- | --- | --- | --- | --- | --- |
| retrospective | chart_weekday | 0 | -0.015 | -0.121 | -0.019 |
| retrospective | credit_prior_song_count | 1 | 0.007 | -0.102 | 0.030 |
| retrospective | credit_prior_top10_song_count | 0 | -0.014 | -0.132 | -0.012 |
| retrospective | credit_recent_chart_presence | 0 | -0.015 | -0.124 | -0.015 |
| retrospective | credit_recent_points_slope | 0 | -0.016 | -0.138 | -0.022 |
| retrospective | debut_competing_new_entry_count | 0 | -0.014 | -0.036 | 0.082 |
| retrospective | debut_time_years | 3 | 0.027 | -0.236 | 0.256 |
| retrospective | lyric_compression_ratio | 0 | -0.006 | -0.053 | 0.011 |
| retrospective | lyric_repeated_line_share | 0 | -0.014 | -0.069 | -0.002 |
| retrospective | lyric_word_count | 0 | -0.006 | -0.214 | -0.029 |
| retrospective | previous_chart_new_entry_count | 0 | -0.015 | -0.097 | 0.021 |
| retrospective | primary_genre | 0 | -0.018 | -0.370 | 0.006 |
| retrospective | same_credit_debut_cluster_size | 0 | -0.004 | -0.280 | 0.093 |
| retrospective | secondary_genres | 3 | 0.019 | -0.034 | 0.053 |
| strict | chart_weekday | 0 | -0.018 | -0.320 | 0.165 |
| strict | credit_prior_song_count | 0 | -0.002 | -0.550 | 0.179 |
| strict | credit_prior_top10_song_count | 0 | -0.016 | -0.550 | 0.166 |
| strict | credit_recent_chart_presence | 0 | -0.013 | -0.400 | 0.164 |
| strict | credit_recent_points_slope | 0 | -0.021 | -0.328 | 0.159 |
| strict | debut_competing_new_entry_count | 0 | -0.016 | -0.113 | 0.202 |
| strict | debut_time_years | 2 | 0.051 | -0.125 | 0.572 |
| strict | previous_chart_new_entry_count | 0 | -0.013 | -0.323 | 0.087 |
| strict | same_credit_debut_cluster_size | 3 | 0.030 | -0.495 | -0.179 |

No lyrical classifier score or lyric-structure construct occurs in the overall combined winners in this campaign. This is a finding within these additive models, selected cohorts and one-to-three-variable limit, not evidence that lyrical content never matters. Prior Top-10 count and recent momentum are also not universal winning predictors. Exact-credit history cannot be interpreted as resolved individual-artist history.

| track | horizon | family | winning_targets | selected_variable_occurrences |
| --- | --- | --- | --- | --- |
| retrospective | 26 | chart_competition | 1 | 1 |
| retrospective | 26 | debut_chart | 2 | 2 |
| retrospective | 26 | genre_information | 3 | 5 |
| retrospective | 26 | historical_time | 1 | 1 |
| retrospective | observed_lifetime | artist_history | 1 | 1 |
| retrospective | observed_lifetime | debut_chart | 2 | 2 |
| retrospective | observed_lifetime | genre_information | 3 | 4 |
| retrospective | observed_lifetime | historical_time | 2 | 2 |
| strict | 26 | artist_history | 2 | 2 |
| strict | 26 | chart_competition | 2 | 4 |
| strict | 26 | debut_chart | 2 | 2 |
| strict | 26 | historical_time | 1 | 1 |
| strict | observed_lifetime | artist_history | 1 | 1 |
| strict | observed_lifetime | chart_competition | 3 | 4 |
| strict | observed_lifetime | debut_chart | 3 | 3 |
| strict | observed_lifetime | historical_time | 1 | 1 |

Family frequency is descriptive across correlated outcomes. Annotation confidence can be more prominent than lyric attributes without being a causal or deployable feature.

## Stability and failures to generalize

| track | target | start | end | skill | r2 | rank_among_all_candidates |
| --- | --- | --- | --- | --- | --- | --- |
| strict | best_rank | 1990-01-01 | 2000-01-01 | 0.006 | 0.002 | 2737 |
| strict | best_rank | 2000-01-01 | 2010-01-01 | 0.094 | 0.093 | 2 |
| strict | best_rank | 2010-01-01 | 2018-01-01 | 0.104 | 0.061 | 13 |
| strict | chart_weeks | 1990-01-01 | 2000-01-01 | 0.339 | -0.015 | 972 |
| strict | chart_weeks | 2000-01-01 | 2010-01-01 | 0.259 | 0.042 | 7 |
| strict | chart_weeks | 2010-01-01 | 2018-01-01 | 0.090 | 0.090 | 30 |
| strict | chart_points | 1990-01-01 | 2000-01-01 | 0.338 | 0.237 | 40 |
| strict | chart_points | 2000-01-01 | 2010-01-01 | 0.092 | 0.009 | 481 |
| strict | chart_points | 2010-01-01 | 2018-01-01 | 0.010 | 0.008 | 1469 |
| retrospective | best_rank | 1990-01-01 | 2000-01-01 | 0.206 | 0.199 | 1 |
| retrospective | best_rank | 2000-01-01 | 2010-01-01 | 0.108 | 0.106 | 17 |
| retrospective | best_rank | 2010-01-01 | 2018-01-01 | 0.196 | 0.184 | 1 |
| retrospective | chart_weeks | 1990-01-01 | 2000-01-01 | 0.351 | 0.061 | 709 |
| retrospective | chart_weeks | 2000-01-01 | 2010-01-01 | 0.368 | 0.058 | 1 |
| retrospective | chart_weeks | 2010-01-01 | 2018-01-01 | 0.131 | 0.050 | 207 |
| retrospective | chart_points | 1990-01-01 | 2000-01-01 | 0.360 | 0.292 | 1 |
| retrospective | chart_points | 2000-01-01 | 2010-01-01 | 0.195 | 0.105 | 4 |
| retrospective | chart_points | 2010-01-01 | 2018-01-01 | 0.102 | 0.083 | 110 |

Across the full catalog, **1,047,685** candidates have negative evaluation R², and **799,863** have negative training-mean-relative evaluation skill. All are preserved. Every hierarchy row includes period metrics and evaluation-minus-validation/training gaps. See `coverage.json` for task-specific counts and singular-fit fallbacks.

OLS predictions are unbounded; the search does not clip ranks or counts or silently switch estimators when extrapolation fails. Continuous time, changing entry patterns, outcome distribution shifts and rare measurement categories can make historically useful linear associations unstable. These are plausible limitations, not established causal explanations.

## Presentation-ready takeaways

1. Exhaustive search is computationally feasible; exhaustive enumeration alone does not ensure generalization.
2. Strict best-rank forecasting is the clearest positive result. Strict chart-weeks and chart-points winners failed on recent debuts.
3. New-feature gains are target-specific and sometimes negative. Matched V1 comparisons prevent gains from being credited to different evaluation populations or extra training years.
4. Retrospective genre-confidence associations and selected observed-history outcomes require separate interpretation. They are not equivalent evidence for debut-time lifetime forecasting.
5. Further work would require new authorization; no acquisition, classification, clustering or COVID analysis was launched.
