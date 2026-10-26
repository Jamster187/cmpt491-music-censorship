# Local feature expansion v1 — measured findings

The tables report the final validation-selected models. Higher classification balanced accuracy and lower regression MAE indicate improvement. Positive values in the incremental-improvement table favor the combined model. Use the paired intervals and group ablations to assess how stable those improvements are.

## What improved, and what did not

New information improves **Top-10 discrimination and strict best-rank prediction**, but does not produce reliable forecasting of every chart outcome. The strict combined Top-10 model is regularized logistic regression (C=0.1, validation threshold 0.10): balanced accuracy rises from 0.549 to 0.666, ROC-AUC from 0.618 to 0.724. The paired artist-credit interval for the balanced-accuracy improvement is 7.1 to 16.7 percentage points.

This ranking improvement is **not reliable probability calibration**. Only 2.85% of eligible evaluation songs climb into the Top 10, versus 17.85% in training and 8.90% in validation. Combined precision is 4.81% at 79.3% recall. Its Brier score is 0.106, worse than the training-prevalence baseline's 0.050. The saved probabilities should be presented as raw model estimates, not dependable hit probabilities.

Strict combined HGB models reduce best-rank MAE from 26.44 to 20.94 (R² 0.203) and chart-week MAE from 10.33 to 7.30 (R² 0.022). Chart-point MAE improves versus the rank-only model, but the combined model's 474.35 is worse than the training-median baseline's 411.16. New-only HGB has lower point MAE (413.52) and essentially zero R²; even it does not beat that median baseline on MAE. These are limited improvements, not strong overall commercial-performance prediction.

For **26-week longevity**, adding features hurts the strict comparison: combined HGB balanced accuracy is 0.555 versus 0.588 for the rank-only logistic model. The new-only logistic model was strongest on validation among the three configurations, but falls to 0.506 in evaluation. That is substantial historical generalization failure, despite its evaluation ROC-AUC of 0.670; its saved validation threshold transfers poorly.

On the common retrospective cohort, combined logistic models improve Top-10 balanced accuracy from 0.626 to 0.674 and longevity from 0.502 to 0.587. The Top-10 improvement's artist-credit interval includes zero, and probability calibration worsens. Combined best-rank MAE is worse than baseline (20.79 versus 19.56). Retrospective combined chart-week and chart-point models have negative R² and do not beat the simple training-median MAE baseline. These F-track results cannot be described as historical forecasts.

## Where the information comes from

Chart competition is the strongest source group for the strict Top-10 gain: removing it costs 8.24 balanced-accuracy points, versus 1.59 points for removing artist history. It also accounts for much of the strict numerical error reduction. The highest-ranked new validation feature is the count of **other same-credit songs debuting together**. Its logistic coefficient is negative, as are the coefficients for the number of other new entrants and prior-chart incumbent age. These are conditional model associations; simultaneous debuts are not verified album membership.

Prior attained Top-10 count has a positive coefficient, while prior song count and accumulated weeks have negative conditional coefficients alongside other history measures. Thus, more observed output is not uniformly associated with higher success after controlling for prior hits and chart context. Collinearity makes individual coefficient interpretation fragile; the group ablation is more informative.

The 16 lyric-structure features add little consistent incremental value. Removing the whole group slightly improves retrospective Top-10 balanced accuracy, while its longevity contribution is only 0.74 percentage points. Removing existing 42 lyrical scores costs 1.09 Top-10 points and 0.12 longevity points on that retrospective cohort. Calendar/title features have little stable group benefit; chart weekday is nearly uninformative. Genre and entity-credit history help some retrospective comparisons, but retain modern-measurement and coverage limitations.

## Historical generalization

Strict combined Top-10 balanced accuracy is stable at 0.660, 0.669 and 0.665 across the three evaluation periods. Fixed-HGB earlier folds also improve on their own rank-only baselines (0.603 versus 0.526 in 2000–2009; 0.603 versus 0.576 in 2010–2017). This supports a recurring predictive signal, within the exploratory limitations. Longevity gains are inconsistent across eras. The 12-week strict combined classifier performs better (0.620 versus 0.497 baseline), showing that the chosen longevity window materially changes the task. No favorable horizon replaces the prespecified 26-week primary outcome.

## Strict comparison

| target | configuration | method | n | balanced_accuracy | roc_auc | pr_auc | brier | r2 | mae | rmse |
|---|---|---|---|---|---|---|---|---|---|---|
| Top 10 | baseline | regularized | 4733 | 0.5487 | 0.6184 | 0.0543 | 0.2022 | — | — | — |
| Top 10 | new_only | hist_gradient_boosting | 4733 | 0.5681 | 0.6001 | 0.0397 | 0.0444 | — | — | — |
| Top 10 | combined | regularized | 4733 | 0.6662 | 0.7242 | 0.0839 | 0.1058 | — | — | — |
| 13+ chart weeks | baseline | regularized | 5072 | 0.5884 | 0.5431 | 0.3878 | 0.3439 | — | — | — |
| 13+ chart weeks | new_only | regularized | 5072 | 0.5061 | 0.6700 | 0.3479 | 0.1926 | — | — | — |
| 13+ chart weeks | combined | hist_gradient_boosting | 5072 | 0.5548 | 0.6000 | 0.3144 | 0.1883 | — | — | — |
| Best rank | baseline | hist_gradient_boosting | 5072 | — | — | — | — | -0.1623 | 26.4366 | 30.4855 |
| Best rank | new_only | hist_gradient_boosting | 5072 | — | — | — | — | 0.0181 | 23.5446 | 28.0191 |
| Best rank | combined | hist_gradient_boosting | 5072 | — | — | — | — | 0.2029 | 20.9392 | 25.2449 |
| Chart weeks | baseline | regularized | 5072 | — | — | — | — | -0.8857 | 10.3267 | 11.3493 |
| Chart weeks | new_only | regularized | 5072 | — | — | — | — | -0.7998 | 8.7501 | 11.0878 |
| Chart weeks | combined | hist_gradient_boosting | 5072 | — | — | — | — | 0.0222 | 7.2951 | 8.1727 |
| Chart points | baseline | hist_gradient_boosting | 5072 | — | — | — | — | -1.0101 | 692.1558 | 774.8958 |
| Chart points | new_only | hist_gradient_boosting | 5072 | — | — | — | — | 0.0014 | 413.5216 | 546.1568 |
| Chart points | combined | hist_gradient_boosting | 5072 | — | — | — | — | -0.0583 | 474.3505 | 562.2552 |

## Retrospective comparison

| target | configuration | method | n | balanced_accuracy | roc_auc | pr_auc | brier | r2 | mae | rmse |
|---|---|---|---|---|---|---|---|---|---|---|
| Top 10 | baseline | hist_gradient_boosting | 2294 | 0.6256 | 0.7002 | 0.0964 | 0.1089 | — | — | — |
| Top 10 | new_only | regularized | 2294 | 0.6225 | 0.6394 | 0.0741 | 0.0816 | — | — | — |
| Top 10 | combined | regularized | 2294 | 0.6741 | 0.7305 | 0.1269 | 0.1435 | — | — | — |
| 13+ chart weeks | baseline | hist_gradient_boosting | 2573 | 0.5022 | 0.4841 | 0.4174 | 0.3327 | — | — | — |
| 13+ chart weeks | new_only | regularized | 2573 | 0.5237 | 0.6852 | 0.5471 | 0.2646 | — | — | — |
| 13+ chart weeks | combined | regularized | 2573 | 0.5869 | 0.6977 | 0.5904 | 0.2455 | — | — | — |
| Best rank | baseline | hist_gradient_boosting | 2573 | — | — | — | — | 0.2143 | 19.5618 | 24.0197 |
| Best rank | new_only | hist_gradient_boosting | 2573 | — | — | — | — | -0.0196 | 22.7662 | 27.3636 |
| Best rank | combined | hist_gradient_boosting | 2573 | — | — | — | — | 0.0973 | 20.7877 | 25.7467 |
| Chart weeks | baseline | hist_gradient_boosting | 2573 | — | — | — | — | -0.2819 | 8.9347 | 10.0414 |
| Chart weeks | new_only | regularized | 2573 | — | — | — | — | -0.0756 | 7.5599 | 9.1981 |
| Chart weeks | combined | regularized | 2573 | — | — | — | — | -0.2549 | 8.0436 | 9.9352 |
| Chart points | baseline | hist_gradient_boosting | 2573 | — | — | — | — | -0.3182 | 641.1741 | 734.5344 |
| Chart points | new_only | regularized | 2573 | — | — | — | — | -0.0739 | 499.4167 | 662.9953 |
| Chart points | combined | regularized | 2573 | — | — | — | — | -0.4448 | 607.9543 | 769.0089 |

## Incremental improvement

| track | target | metric | baseline | new_only | combined | improvement | relative_mae_reduction_percent |
|---|---|---|---|---|---|---|---|
| strict | top10 | balanced_accuracy | 0.5487 | 0.5681 | 0.6662 | 0.1175 | — |
| strict | long_chart | balanced_accuracy | 0.5884 | 0.5061 | 0.5548 | -0.0335 | — |
| strict | best_rank | mae | 26.4366 | 23.5446 | 20.9392 | 5.4974 | 20.7946 |
| strict | chart_weeks | mae | 10.3267 | 8.7501 | 7.2951 | 3.0316 | 29.3566 |
| strict | chart_points | mae | 692.1558 | 413.5216 | 474.3505 | 217.8053 | 31.4677 |
| retrospective | top10 | balanced_accuracy | 0.6256 | 0.6225 | 0.6741 | 0.0485 | — |
| retrospective | long_chart | balanced_accuracy | 0.5022 | 0.5237 | 0.5869 | 0.0847 | — |
| retrospective | best_rank | mae | 19.5618 | 22.7662 | 20.7877 | -1.2259 | -6.2668 |
| retrospective | chart_weeks | mae | 8.9347 | 7.5599 | 8.0436 | 0.8911 | 9.9736 |
| retrospective | chart_points | mae | 641.1741 | 499.4167 | 607.9543 | 33.2198 | 5.1811 |

## Paired uncertainty

| track | target | cluster | estimate | lower | upper |
|---|---|---|---|---|---|
| strict | top10 | artist_credit | 0.1175 | 0.0708 | 0.1665 |
| strict | top10 | debut_year | 0.1175 | 0.0840 | 0.1483 |
| strict | long_chart | artist_credit | -0.0335 | -0.0511 | -0.0126 |
| strict | long_chart | debut_year | -0.0335 | -0.0613 | -0.0127 |
| strict | best_rank | artist_credit | 5.4974 | 4.4355 | 6.4532 |
| strict | best_rank | debut_year | 5.4974 | 4.7783 | 6.2657 |
| strict | chart_weeks | artist_credit | 3.0316 | 2.5189 | 3.4923 |
| strict | chart_weeks | debut_year | 3.0316 | 2.6805 | 3.3677 |
| strict | chart_points | artist_credit | 217.8053 | 191.6018 | 242.7382 |
| strict | chart_points | debut_year | 217.8053 | 195.2775 | 237.0524 |
| retrospective | top10 | artist_credit | 0.0485 | -0.0077 | 0.1020 |
| retrospective | top10 | debut_year | 0.0485 | 0.0194 | 0.0776 |
| retrospective | long_chart | artist_credit | 0.0847 | 0.0596 | 0.1127 |
| retrospective | long_chart | debut_year | 0.0847 | 0.0537 | 0.1169 |
| retrospective | best_rank | artist_credit | -1.2259 | -1.5528 | -0.9414 |
| retrospective | best_rank | debut_year | -1.2259 | -1.6089 | -0.8878 |
| retrospective | chart_weeks | artist_credit | 0.8911 | 0.0164 | 1.6061 |
| retrospective | chart_weeks | debut_year | 0.8911 | 0.3966 | 1.5509 |
| retrospective | chart_points | artist_credit | 33.2198 | -25.1342 | 83.1583 |
| retrospective | chart_points | debut_year | 33.2198 | 4.0109 | 68.4583 |

## Ten highest-ranked new debut-time features for Top-10 classification

Ranked on validation data; a near-zero or negative value is weak evidence of usefulness. Values are balanced-accuracy loss after shuffling.

| feature | group | mean_drop | std_drop |
|---|---|---|---|
| same_credit_debut_cluster_size | chart_competition | 0.0344 | 0.0015 |
| credit_prior_top10_song_count | artist_history | 0.0164 | 0.0053 |
| credit_prior_song_count | artist_history | 0.0144 | 0.0038 |
| credit_prior_chart_points | artist_history | 0.0113 | 0.0075 |
| previous_chart_incumbent_age_median | chart_competition | 0.0108 | 0.0023 |
| credit_prior_chart_weeks | artist_history | 0.0105 | 0.0102 |
| artist_credit_feature_marker | calendar_title | 0.0097 | 0.0020 |
| debut_competing_new_entry_count | chart_competition | 0.0089 | 0.0030 |
| credit_prior_song_observed_longevity_median | artist_history | 0.0085 | 0.0022 |
| credit_prior_best_rank | artist_history | 0.0072 | 0.0009 |

## Group ablations

Positive degradation means removing the group hurt the test result. Classification units are balanced accuracy; regression units are target MAE. Method and structural hyperparameters stay fixed.

| track | target | removed_group | degradation |
|---|---|---|---|
| strict | top10 | debut_rank | 0.1090 |
| strict | top10 | artist_history | 0.0159 |
| strict | top10 | chart_competition | 0.0824 |
| strict | top10 | calendar_title | -0.0020 |
| strict | long_chart | debut_rank | 0.0377 |
| strict | long_chart | artist_history | -0.0050 |
| strict | long_chart | chart_competition | -0.0062 |
| strict | long_chart | calendar_title | -0.0106 |
| strict | best_rank | debut_rank | 2.6054 |
| strict | best_rank | artist_history | -0.1902 |
| strict | best_rank | chart_competition | 3.3176 |
| strict | best_rank | calendar_title | -0.0412 |
| strict | chart_weeks | debut_rank | -0.1714 |
| strict | chart_weeks | artist_history | -0.0356 |
| strict | chart_weeks | chart_competition | 1.8227 |
| strict | chart_weeks | calendar_title | -0.0695 |
| strict | chart_points | debut_rank | -60.8290 |
| strict | chart_points | artist_history | 3.6594 |
| strict | chart_points | chart_competition | 161.9857 |
| strict | chart_points | calendar_title | 2.2493 |
| retrospective | top10 | debut_rank | 0.0827 |
| retrospective | top10 | primary_genre | 0.0286 |
| retrospective | top10 | duration_seconds | -0.0021 |
| retrospective | top10 | existing_scores | 0.0109 |
| retrospective | top10 | artist_history | 0.0317 |
| retrospective | top10 | chart_competition | 0.0470 |
| retrospective | top10 | calendar_title | 0.0135 |
| retrospective | top10 | lyric_structure | -0.0023 |
| retrospective | top10 | relative_content | 0.0015 |
| retrospective | top10 | entity_credit | 0.0160 |
| retrospective | long_chart | debut_rank | 0.0550 |
| retrospective | long_chart | primary_genre | -0.0035 |
| retrospective | long_chart | duration_seconds | 0.0006 |
| retrospective | long_chart | existing_scores | 0.0012 |
| retrospective | long_chart | artist_history | -0.0023 |
| retrospective | long_chart | chart_competition | 0.0147 |
| retrospective | long_chart | calendar_title | -0.0056 |
| retrospective | long_chart | lyric_structure | 0.0074 |
| retrospective | long_chart | relative_content | -0.0176 |
| retrospective | long_chart | entity_credit | -0.0125 |
| retrospective | best_rank | debut_rank | 1.1839 |
| retrospective | best_rank | primary_genre | 0.0815 |
| retrospective | best_rank | duration_seconds | 0.8514 |
| retrospective | best_rank | existing_scores | -0.0624 |
| retrospective | best_rank | artist_history | -0.1753 |
| retrospective | best_rank | chart_competition | -0.8712 |
| retrospective | best_rank | calendar_title | 0.1768 |
| retrospective | best_rank | lyric_structure | -0.0427 |
| retrospective | best_rank | relative_content | 0.2264 |
| retrospective | best_rank | entity_credit | 0.1477 |
| retrospective | chart_weeks | debut_rank | -0.4997 |
| retrospective | chart_weeks | primary_genre | 0.0229 |
| retrospective | chart_weeks | duration_seconds | 0.0049 |
| retrospective | chart_weeks | existing_scores | -0.0104 |
| retrospective | chart_weeks | artist_history | 0.1909 |
| retrospective | chart_weeks | chart_competition | 0.2748 |
| retrospective | chart_weeks | calendar_title | -0.0670 |
| retrospective | chart_weeks | lyric_structure | 0.0475 |
| retrospective | chart_weeks | relative_content | -0.0255 |
| retrospective | chart_weeks | entity_credit | -0.0604 |
| retrospective | chart_points | debut_rank | -118.7882 |
| retrospective | chart_points | primary_genre | 10.9012 |
| retrospective | chart_points | duration_seconds | -0.9046 |
| retrospective | chart_points | existing_scores | 3.7643 |
| retrospective | chart_points | artist_history | -18.6136 |
| retrospective | chart_points | chart_competition | 56.6749 |
| retrospective | chart_points | calendar_title | -3.5620 |
| retrospective | chart_points | lyric_structure | -0.4137 |
| retrospective | chart_points | relative_content | -0.2349 |
| retrospective | chart_points | entity_credit | -2.0680 |

## Historical stability and 12-week sensitivity

| experiment | track | target | configuration | n | balanced_accuracy | r2 | mae |
|---|---|---|---|---|---|---|---|
| horizon_12 | strict | top10 | baseline | 4909 | 0.5738 | — | — |
| historical_2000_2010 | strict | top10 | baseline | 3148 | 0.5261 | — | — |
| historical_2010_2018 | strict | top10 | baseline | 3021 | 0.5759 | — | — |
| horizon_12 | strict | top10 | new_only | 4909 | 0.5838 | — | — |
| historical_2000_2010 | strict | top10 | new_only | 3148 | 0.5718 | — | — |
| historical_2010_2018 | strict | top10 | new_only | 3021 | 0.5834 | — | — |
| horizon_12 | strict | top10 | combined | 4909 | 0.6206 | — | — |
| historical_2000_2010 | strict | top10 | combined | 3148 | 0.6034 | — | — |
| historical_2010_2018 | strict | top10 | combined | 3021 | 0.6028 | — | — |
| horizon_12 | strict | long_chart | baseline | 5266 | 0.4969 | — | — |
| historical_2000_2010 | strict | long_chart | baseline | 3185 | 0.5668 | — | — |
| historical_2010_2018 | strict | long_chart | baseline | 3111 | 0.5221 | — | — |
| horizon_12 | strict | long_chart | new_only | 5266 | 0.5301 | — | — |
| historical_2000_2010 | strict | long_chart | new_only | 3185 | 0.5257 | — | — |
| historical_2010_2018 | strict | long_chart | new_only | 3111 | 0.5299 | — | — |
| horizon_12 | strict | long_chart | combined | 5266 | 0.6198 | — | — |
| historical_2000_2010 | strict | long_chart | combined | 3185 | 0.5652 | — | — |
| historical_2010_2018 | strict | long_chart | combined | 3111 | 0.4811 | — | — |
| horizon_12 | strict | best_rank | baseline | 5266 | — | -0.1487 | 25.9478 |
| historical_2000_2010 | strict | best_rank | baseline | 3185 | — | 0.0441 | 24.1474 |
| historical_2010_2018 | strict | best_rank | baseline | 3111 | — | -0.0376 | 25.9728 |
| horizon_12 | strict | best_rank | new_only | 5266 | — | 0.0253 | 23.0866 |
| historical_2000_2010 | strict | best_rank | new_only | 3185 | — | -0.0108 | 25.5791 |
| historical_2010_2018 | strict | best_rank | new_only | 3111 | — | -0.0991 | 26.4599 |
| horizon_12 | strict | best_rank | combined | 5266 | — | 0.2378 | 20.1420 |
| historical_2000_2010 | strict | best_rank | combined | 3185 | — | 0.0847 | 23.6475 |
| historical_2010_2018 | strict | best_rank | combined | 3111 | — | -0.0939 | 26.6463 |
| horizon_12 | strict | chart_weeks | baseline | 5266 | — | -1.3446 | 6.0116 |
| historical_2000_2010 | strict | chart_weeks | baseline | 3185 | — | -0.2914 | 7.8338 |
| historical_2010_2018 | strict | chart_weeks | baseline | 3111 | — | -0.1797 | 8.8680 |
| horizon_12 | strict | chart_weeks | new_only | 5266 | — | -0.2160 | 4.5682 |
| historical_2000_2010 | strict | chart_weeks | new_only | 3185 | — | -0.0088 | 6.8816 |
| historical_2010_2018 | strict | chart_weeks | new_only | 3111 | — | -0.0395 | 8.5639 |
| horizon_12 | strict | chart_weeks | combined | 5266 | — | -0.3264 | 4.6103 |
| historical_2000_2010 | strict | chart_weeks | combined | 3185 | — | -0.0310 | 6.5897 |
| historical_2010_2018 | strict | chart_weeks | combined | 3111 | — | -0.1472 | 8.8279 |
| horizon_12 | strict | chart_points | baseline | 5266 | — | -2.4029 | 449.6517 |
| historical_2000_2010 | strict | chart_points | baseline | 3185 | — | -0.0230 | 516.8868 |
| historical_2010_2018 | strict | chart_points | baseline | 3111 | — | -0.1661 | 578.4872 |
| horizon_12 | strict | chart_points | new_only | 5266 | — | -0.2672 | 270.8720 |
| historical_2000_2010 | strict | chart_points | new_only | 3185 | — | 0.0025 | 547.6103 |
| historical_2010_2018 | strict | chart_points | new_only | 3111 | — | -0.0547 | 565.8999 |
| horizon_12 | strict | chart_points | combined | 5266 | — | -0.7987 | 314.2993 |
| historical_2000_2010 | strict | chart_points | combined | 3185 | — | -0.0553 | 556.3607 |
| historical_2010_2018 | strict | chart_points | combined | 3111 | — | -0.1998 | 597.3887 |
| horizon_12 | retrospective | top10 | baseline | 2385 | 0.6484 | — | — |
| historical_2000_2010 | retrospective | top10 | baseline | 2244 | 0.5785 | — | — |
| historical_2010_2018 | retrospective | top10 | baseline | 1806 | 0.6700 | — | — |
| horizon_12 | retrospective | top10 | new_only | 2385 | 0.5597 | — | — |
| historical_2000_2010 | retrospective | top10 | new_only | 2244 | 0.6084 | — | — |
| historical_2010_2018 | retrospective | top10 | new_only | 1806 | 0.6213 | — | — |
| horizon_12 | retrospective | top10 | combined | 2385 | 0.6670 | — | — |
| historical_2000_2010 | retrospective | top10 | combined | 2244 | 0.6500 | — | — |
| historical_2010_2018 | retrospective | top10 | combined | 1806 | 0.6732 | — | — |
| horizon_12 | retrospective | long_chart | baseline | 2676 | 0.5002 | — | — |
| historical_2000_2010 | retrospective | long_chart | baseline | 2273 | 0.5333 | — | — |
| historical_2010_2018 | retrospective | long_chart | baseline | 1888 | 0.5074 | — | — |
| horizon_12 | retrospective | long_chart | new_only | 2676 | 0.5829 | — | — |
| historical_2000_2010 | retrospective | long_chart | new_only | 2273 | 0.5535 | — | — |
| historical_2010_2018 | retrospective | long_chart | new_only | 1888 | 0.5114 | — | — |
| horizon_12 | retrospective | long_chart | combined | 2676 | 0.5480 | — | — |
| historical_2000_2010 | retrospective | long_chart | combined | 2273 | 0.5760 | — | — |
| historical_2010_2018 | retrospective | long_chart | combined | 1888 | 0.5098 | — | — |
| horizon_12 | retrospective | best_rank | baseline | 2676 | — | 0.2620 | 19.0568 |
| historical_2000_2010 | retrospective | best_rank | baseline | 2273 | — | 0.0723 | 22.1356 |
| historical_2010_2018 | retrospective | best_rank | baseline | 1888 | — | 0.1553 | 21.6028 |
| horizon_12 | retrospective | best_rank | new_only | 2676 | — | -0.0204 | 22.8439 |
| historical_2000_2010 | retrospective | best_rank | new_only | 2273 | — | 0.0530 | 23.0645 |
| historical_2010_2018 | retrospective | best_rank | new_only | 1888 | — | -0.0172 | 23.5785 |
| horizon_12 | retrospective | best_rank | combined | 2676 | — | 0.1158 | 20.8209 |
| historical_2000_2010 | retrospective | best_rank | combined | 2273 | — | 0.1249 | 21.4566 |
| historical_2010_2018 | retrospective | best_rank | combined | 1888 | — | 0.0968 | 22.0803 |
| horizon_12 | retrospective | chart_weeks | baseline | 2676 | — | -0.5525 | 4.5420 |
| historical_2000_2010 | retrospective | chart_weeks | baseline | 2273 | — | -0.3702 | 7.1057 |
| historical_2010_2018 | retrospective | chart_weeks | baseline | 1888 | — | -0.1115 | 7.6611 |
| horizon_12 | retrospective | chart_weeks | new_only | 2676 | — | -0.0479 | 3.9771 |
| historical_2000_2010 | retrospective | chart_weeks | new_only | 2273 | — | 0.0013 | 5.9107 |
| historical_2010_2018 | retrospective | chart_weeks | new_only | 1888 | — | -0.0013 | 7.4012 |
| horizon_12 | retrospective | chart_weeks | combined | 2676 | — | -0.1456 | 4.1079 |
| historical_2000_2010 | retrospective | chart_weeks | combined | 2273 | — | -0.0228 | 5.7642 |
| historical_2010_2018 | retrospective | chart_weeks | combined | 1888 | — | -0.0791 | 7.6343 |
| horizon_12 | retrospective | chart_points | baseline | 2676 | — | -0.8297 | 360.7701 |
| historical_2000_2010 | retrospective | chart_points | baseline | 2273 | — | 0.0278 | 513.1181 |
| historical_2010_2018 | retrospective | chart_points | baseline | 1888 | — | 0.0284 | 556.3673 |
| horizon_12 | retrospective | chart_points | new_only | 2676 | — | -0.3234 | 320.1501 |
| historical_2000_2010 | retrospective | chart_points | new_only | 2273 | — | 0.0598 | 532.6940 |
| historical_2010_2018 | retrospective | chart_points | new_only | 1888 | — | 0.0486 | 561.0059 |
| horizon_12 | retrospective | chart_points | combined | 2676 | — | -0.7002 | 350.8168 |
| historical_2000_2010 | retrospective | chart_points | combined | 2273 | — | 0.0574 | 524.8473 |
| historical_2010_2018 | retrospective | chart_points | combined | 1888 | — | 0.0581 | 554.7891 |

## Interpretation and limits

This is an exploratory evaluation on a previously inspected test population. No model or feature was selected by its final-test result; nevertheless, the campaign is not fresh independent confirmation. Confidence intervals condition on fitted models and omit selection and refit uncertainty. Artist-credit clusters are exact strings, so the same person may occur in several clusters; the year-cluster interval has only nine clusters.

Only the strict track uses historically available predictors. Retrospective comparisons use modern lyric/genre/metadata measurements, and membership in the enriched monthly population is itself determined using later history. Strict and retrospective tracks have different populations and must not be compared as a causal estimate of the value of lyrics. Within each track, A/B/C share exactly the same songs.

Debut rank is already known at the prediction moment. Numerical outcomes include that first chart contribution, which makes part of the target predictable by construction. Top-10 debut songs are excluded from Top-10 classification. Chart points are 101 minus rank summed over source rows, not sales, streams, revenue, or market share. No inference applies to uncharted releases.

The 26-week target handles endpoint censoring but is not complete eventual career success. Long returns and seasonal reentries can occur later. Observed careers before 1958 are unavailable; the 1960 burn-in does not reconstruct them. The final 2026 period is partial. Exact-credit history intentionally splits collaborations and spelling differences. Entity-credit features use unanimous modern recording credits but are still retrospective; first-listed does not prove lead/featured performance roles.

Lyrics retain provider/version/format and language effects. MATTR is missing below 50 tokens. English lexical lists are literal counts, not language detection or psychological labels. A title-equal opening line remains a lyric; only recognized standalone section markers are omitted. Symbolic repeat instructions are not expanded. Missing values are median-imputed from training data; this can still reveal missingness patterns even without explicit indicators. Genre and 42 existing scores are model measurements, not ground truth.

Permutation importance is marginal and can understate correlated predictors. Coefficients, impurity importance and fixed-hyperparameter ablations provide complementary checks; none establish causation. Ablations reselect only the decision threshold on validation data. Raw probabilities are not recalibrated and may be poorly calibrated after historical drift. Negative ablation degradation means removing a group improved that evaluation metric; it is not a new feature-selection instruction.

The historical folds use a prespecified HGB model with its own earlier validation interval. The primary comparison selects among three model families, so historical-fold and primary scores also differ in model-selection procedure. The 12-week sensitivity changes the target (including longevity to at least six weeks), not merely sample size. No COVID breakpoint or causal analysis was performed.
