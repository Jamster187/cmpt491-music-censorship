# Measured exploratory pilot findings

**No independent confirmation is claimed.** All 137 outcome-blind pilot
candidates were evaluated. There were 2,879 fits, including
inner selection and multivariate stability refits. The global BY family contains
110 attempted primary hypotheses; 35 have exploratory
q≤.05 (30 after omitting reconstruction controls).
This conditional-on-assumptions evidence is not a count of confirmed scientific
discoveries. Historical and latent-structure results are descriptive.

## Nonlinear improvements

Effects below are equal-calendar-block loss reductions divided by training target
variance. R² is pooled across held-out song rows. A positive improvement can
coexist with poor absolute prediction. The complete ranking retains those failures.

| Target | Predictor(s); condition | Category | Effect | 95% block interval | Outer R² | Global BY q | Positive periods |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mb_release_year | weekly_observation_count | C | 0.5242 | [0.3436, 0.7289] | -4.9451 | 0.0016 | 1.00 |
| first_snapshot_month | mb_duration_median_seconds | C | 0.5383 | [0.2906, 0.7443] | -6.4556 | 0.0140 | 0.75 |
| mb_release_year | ll_sexual_content | C | 0.1128 | [0.0952, 0.1293] | -5.9505 | 0.0016 | 1.00 |
| detox_identity_attack | emotion_amusement | C | 0.1345 | [0.0908, 0.1818] | -0.0530 | 0.0016 | 1.00 |
| ll_substance_use | detox_insult | B | 0.0943 | [0.0721, 0.1156] | -0.0303 | 0.0016 | 1.00 |

Examples with positive outer R², selected mechanically from that same ranking:

| Target | Predictor(s); condition | Category | Effect | 95% block interval | Outer R² | Global BY q | Positive periods |
| --- | --- | --- | --- | --- | --- | --- | --- |
| emotion_relief | emotion_optimism | B | 0.0266 | [0.0186, 0.0347] | 0.0305 | 0.0016 | 1.00 |
| mb_recording_count | mb_release_year | C | 0.0143 | [0.0042, 0.0277] | 0.1493 | 0.1787 | 0.50 |
| mb_release_year | first_chart_date | B | 0.0005 | [0.0003, 0.0007] | 0.9783 | 0.0033 | 1.00 |
| chart_weeks | total_chart_points | B | 0.0337 | [-0.0034, 0.0613] | 0.8368 | 0.4227 | 0.75 |

The first table is deliberately retained: a nonlinear fit can beat a badly
extrapolating linear calendar model while remaining unusable. This is why the
leaderboards expose absolute performance, baseline improvement, interval, q and
period stability separately. A curve alone does not establish a useful prediction.

## Conditional and genre interactions

| Target | Predictor(s); condition | Category | Effect | 95% block interval | Outer R² | Global BY q | Positive periods |
| --- | --- | --- | --- | --- | --- | --- | --- |
| detox_severe_toxicity | ll_sexual_content; primary_genre | B | 0.2324 | [0.1577, 0.3169] | 0.1903 | 0.0016 | 1.00 |
| mb_duration_min_seconds | first_chart_date; primary_genre | C | 0.1194 | [0.0832, 0.1570] | -0.5118 | 0.0016 | 1.00 |
| first_snapshot_month | mb_release_count; primary_genre | C | 0.0965 | [0.0781, 0.1140] | -4.1927 | 0.0016 | 1.00 |
| first_chart_date | chart_weeks; primary_genre | C | 0.1318 | [0.0777, 0.1884] | -3.9693 | 0.0073 | 0.75 |
| snapshot_months_selected | mb_duration_max_seconds; primary_genre | C | 0.0252 | [0.0070, 0.0436] | -0.1412 | 0.1246 | 0.50 |
| last_snapshot_month | detox_sexual_explicit; primary_genre | C | 0.0179 | [0.0028, 0.0328] | -4.4572 | 0.3116 | 0.75 |

Genre-specific slope examples:

| Target | Predictor(s); condition | Category | Effect | 95% block interval | Outer R² | Global BY q | Positive periods |
| --- | --- | --- | --- | --- | --- | --- | --- |
| detox_severe_toxicity | ll_sexual_content; primary_genre | B | 0.2324 | [0.1577, 0.3169] | 0.1903 | 0.0016 | 1.00 |
| mb_duration_min_seconds | first_chart_date; primary_genre | C | 0.1194 | [0.0832, 0.1570] | -0.5118 | 0.0016 | 1.00 |
| first_snapshot_month | mb_release_count; primary_genre | C | 0.0965 | [0.0781, 0.1140] | -4.1927 | 0.0016 | 1.00 |
| first_chart_date | chart_weeks; primary_genre | C | 0.1318 | [0.0777, 0.1884] | -3.9693 | 0.0073 | 0.75 |

Numeric-product examples:

| Target | Predictor(s); condition | Category | Effect | 95% block interval | Outer R² | Global BY q | Positive periods |
| --- | --- | --- | --- | --- | --- | --- | --- |
| emotion_grief | detox_identity_attack; last_chart_date | C | 0.0032 | [0.0014, 0.0050] | -0.0011 | 0.0390 | 0.75 |
| emotion_embarrassment | emotion_approval; emotion_sadness | B | 0.0002 | [0.0000, 0.0004] | 0.0114 | 0.6299 | 0.50 |
| total_chart_points | detox_threat; emotion_realization | C | 0.0025 | [-0.0000, 0.0069] | -0.0408 | 0.8247 | 0.75 |

Threshold-conditioned examples (all three training quantiles retained):

| Target | Predictor(s); condition | Category | Effect | 95% block interval | Outer R² | Global BY q | Positive periods |
| --- | --- | --- | --- | --- | --- | --- | --- |
| emotion_realization | ll_explicit_language; emotion_surprise | B | 0.0022 | [0.0014, 0.0030] | 0.0956 | 0.0025 | 1.00 |
| emotion_realization | ll_explicit_language; emotion_surprise | B | 0.0013 | [0.0008, 0.0020] | 0.0782 | 0.0016 | 1.00 |
| emotion_realization | ll_explicit_language; emotion_surprise | B | 0.0015 | [0.0006, 0.0023] | 0.1152 | 0.0390 | 1.00 |

These gains compare against additive models with the same inputs. Same-family B
relationships can still be informative about classifier agreement but are not
independent content measurements. Numeric product and threshold effects are also
retained when weak or negative. All prespecified subgroup coverage, partial rank
correlations and sign reversals are in the compressed complete results; an
individual subgroup sign flag has no separate corrected significance claim.

## Cross-domain evidence

This is ordered by global BY q and stability, not by a weighted novelty score.
Effect scales differ between pairwise and predictive families.

| Target | Predictor(s); condition | Category | Effect | 95% block interval | Outer R² | Global BY q | Positive periods |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mb_release_year | weekly_observation_count | C | 0.5242 | [0.3436, 0.7289] | -4.9451 | 0.0016 | 1.00 |
| mb_release_year | ll_sexual_content | C | 0.1128 | [0.0952, 0.1293] | -5.9505 | 0.0016 | 1.00 |
| mb_duration_min_seconds | first_chart_date; primary_genre | C | 0.1194 | [0.0832, 0.1570] | -0.5118 | 0.0016 | 1.00 |
| first_snapshot_month | emotion_relief | C | 0.0729 | [0.0442, 0.1061] | -6.9501 | 0.0016 | 1.00 |
| first_snapshot_month | mb_release_count; primary_genre | C | 0.0965 | [0.0781, 0.1140] | -4.1927 | 0.0016 | 1.00 |
| detox_identity_attack | emotion_amusement | C | 0.1345 | [0.0908, 0.1818] | -0.0530 | 0.0016 | 1.00 |
| ll_violence | chart_weeks | C | 0.0337 | [0.0123, 0.0582] | -0.0803 | 0.0025 | 1.00 |
| snapshot_months_selected | mb_duration_median_seconds | C | 0.1002 | [0.0687, 0.1287] | -0.1039 | 0.0033 | 0.75 |

C means different documented information domains. It does not guarantee different
source material, historical availability, causal direction or usefulness. In
particular, tiny improvements and negative R² remain visible even when a
block-based test yields a small exploratory q-value.

## Pairwise agreement and disagreement

| Target | Predictor | Pearson | Spearman | Binned MI (nats) | Distance correlation (≤512 songs) | Year-conditioned BY q |
| --- | --- | --- | --- | --- | --- | --- |
| total_chart_points | mb_release_count | 0.3269 | 0.4517 | 0.1180 | 0.4257 | 0.0182 |
| weekly_observation_count | last_snapshot_month | 0.2866 | 0.2501 | 0.1950 | 0.3204 | 0.0182 |
| emotion_approval | detox_toxicity | -0.1340 | -0.1797 | 0.0225 | 0.1671 | 0.0182 |
| detox_toxicity | detox_obscene | 0.8782 | 0.9465 | 1.0560 | 0.8400 | 0.0182 |
| weekly_observation_count | best_chart_rank | — | -0.7202 | 0.4002 | 0.6618 | 0.0182 |
| mb_recording_count | mb_duration_max_seconds | 0.1870 | 0.2732 | 0.0803 | 0.3162 | 0.0182 |
| sentiment_neutral | emotion_disgust | -0.0981 | -0.0555 | 0.0058 | 0.0881 | 0.0182 |
| total_chart_points | emotion_desire | 0.0235 | 0.0522 | 0.0039 | 0.1300 | 0.0182 |

Metrics have different scales and different sensitivity to shape, ties and sample
size. A large pooled date association can disappear under the within-year
permutation null: it mostly encodes historical placement. Binned MI and capped
distance correlation are descriptive diagnostics, not extra uncorrected tests.

## Historical relationships and 2020 placebos

| Target | Predictor | 2020 contrast | 95% descriptive interval | Genre-adjusted contrast | Magnitude rank among placebos |
| --- | --- | --- | --- | --- | --- |
| snapshot_months_selected | mb_release_year | -0.1081 | [-0.2159, -0.0182] | -0.0770 | 1/5 |
| mb_duration_min_seconds | detox_threat | -0.1078 | [-0.2222, 0.0017] | -0.0375 | 1/5 |
| snapshot_months_selected | mb_duration_min_seconds | 0.0781 | [0.0261, 0.1056] | 0.0373 | 1/5 |
| ll_violence | last_snapshot_month | -0.0604 | [-0.1282, 0.0350] | -0.0191 | 2/5 |
| mb_recording_count | last_chart_date | -0.0582 | [-0.1035, 0.0266] | -0.0462 | 1/5 |

Each row compares exactly five annual correlations on each side. Rank 1 means
largest magnitude among available prespecified breakpoints; it is **not a
p-value**. The other breakpoints are 1980, 1990, 2000 and 2010. All
1,275 planned pair/genre/breakpoint cells remain recorded;
252 meet the sample/year requirements.
There are only five annual observations per side, so intervals are descriptive
and no breakpoint is called significant or causal. Genre adjustment removes
within-year group intercepts only; it does not remove every compositional change.

## Multivariate structure

| Panel | Method | k | Mean held-out reconstruction/distortion fraction | Mean minimum block-refit stability | Stability metric |
| --- | --- | --- | --- | --- | --- |
| content | kmeans | 2 | 0.3365 | 0.9250 | adjusted Rand index |
| content | pca | 2 | 0.6090 | 0.9639 | minimum principal-angle cosine |
| all_lyrics | kmeans | 3 | 0.2472 | 0.7579 | adjusted Rand index |
| affect | kmeans | 3 | 0.1281 | 0.8719 | adjusted Rand index |
| affect | pca | 2 | 0.2331 | 0.9977 | minimum principal-angle cosine |
| all_lyrics | pca | 5 | 0.4846 | 0.9773 | minimum principal-angle cosine |
| affect | kmeans | 2 | 0.0846 | 0.9578 | adjusted Rand index |
| all_lyrics | kmeans | 2 | 0.1237 | 0.9463 | adjusted Rand index |
| all_lyrics | pca | 2 | 0.3696 | 0.9984 | minimum principal-angle cosine |
| content | kmeans | 3 | 0.4664 | 0.8831 | adjusted Rand index |
| affect | pca | 5 | 0.4295 | 0.9913 | minimum principal-angle cosine |
| content | pca | 5 | 0.7945 | 0.7958 | minimum principal-angle cosine |

PCA loadings and clustering profiles are fitted from real scores. Different k
values use different complexity and are not selected using these outer results.
The fixed panels include related outputs and sentiment closure; latent dimensions
are not new ground-truth musical qualities. Three stability resamples per fold
are useful diagnostics, not precise uncertainty estimates.

## Classroom figures

- [Linear versus nonlinear curves](figures/nonlinear.svg)
- [Conditional improvement by evaluation period](figures/conditional.svg)
- [Annual historical association and placebo dates](figures/historical.svg)
- [Actual PCA loadings](figures/pca_loadings.svg)

All figures are generated from saved measured results. The interactive demo adds
target/family selection, genre and period views, sample sizes and warnings. It
never launches a search when a plot is selected.
