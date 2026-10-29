# V5.1 robustness and replication findings

The completed audit covers **30 frozen V5 candidates**. **0 meet every prespecified robustness requirement**; 30 do not. Outcome counts: Insufficient evidence: 4; Likely artifact: 7; Sensitive or unstable candidate: 19.

A failed robustness label is not proof that the population association is exactly zero. It means these selected historical results do not supply the required breadth, stability and uncertainty evidence. Small original q-values remain in the record; this audit does not rewrite V5.

All 30 primary estimates and original chronological transfer calculations reproduce. The audit adds 59,940 paired-block resamples and 14,970 block permutations. It records 9,482 diagnostic comparison slots, including unsupported specifications and comparisons without a valid new p-value. Their BY correction is **not selection-adjusted independent confirmation**.

## R&B / Soul caring and unemployment

The mandatory case is C29, chosen by the general corrected-lyrical rule as well as the explicit diagnostic requirement. The original six-month-lag association reproduces at r=-0.154303, slope=-0.00683531 caring-score change per percentage-point unemployment change, N=756 months, and original global BY q=0.0199118. Its original rank association is much smaller: rho=-0.041111, global rank q=1. The slope's 95% HAC interval is [-0.00817089, -0.00549973].

The **1.4690 effective exposure blocks** reproduce numerically. They are a Kish concentration statistic for squared residual exposure in 49-month blocks, not a count of independent months or a fitted degrees-of-freedom estimate. The largest single exposure is **2020-04**, matched to music in **2020-10**, contributing **78.49%** of the total residual exposure energy. The corresponding unemployment change is 10.4 percentage points. Moving the block origin through every offset yields effective exposure counts from 1.4669 to 1.6019. The concentration is therefore not created solely by the original arbitrary block boundary.

No calculation error was found in that concentration statistic. The AR(1) effective-N shortcut gives 756, illustrating why weak lag-one correlation alone does not establish widely distributed exposure information. The interpretation is concentrated unemployment variation and limited independent episode support, not a literal replacement of 756 months by 1.47 independent observations.

Deleting response-calendar 2020 changes the estimate to r=-0.05223, slope=-0.00500554 (0.732 times the original slope). Excluding the predefined 2020–2022 shock window from either exposure or response support changes it to r=-0.05161, slope=-0.0053488. These deletions diagnose concentration; they are not estimates of a causal pandemic effect.

| Resampling | Slope 95% low | Slope 95% high | Same-sign draws | Successful draws |
| --- | --- | --- | --- | --- |
| moving_pairs | -0.008598 | 0.0008809 | 0.965 | 999 |
| calendar_year_pairs | -0.01005 | -0.0009996 | 0.99 | 999 |

The moving-block procedure retains roughly four years of monthly ordering. The calendar-year resampling keeps within-year dependence and can miss longer persistence. Neither repairs the lack of independent historical episodes or uncertainty from the original selection. Both refit the full nuisance-control span in every resample.

| Deleted period | Removed N | Exposure share removed | Remaining r | Remaining slope / original |
| --- | --- | --- | --- | --- |
| leave_recession:recession_2020-03 | 1 | 0.7849 | -0.05159 | 0.7232 |
| leave_year:2020 | 2 | 0.785 | -0.05223 | 0.7323 |
| leave_five_year:2020-2024 | 31 | 0.8242 | -0.04966 | 0.7483 |
| leave_shock:pandemic | 22 | 0.8231 | -0.05161 | 0.7825 |
| leave_recession:recession_1980-02 | 12 | 0.006783 | -0.1499 | 0.961 |
| leave_year:1980 | 12 | 0.006465 | -0.1501 | 0.9622 |
| leave_year:1986 | 12 | 0.003151 | -0.1518 | 0.965 |
| leave_five_year:1965-1969 | 60 | 0.007262 | -0.1653 | 1.034 |
| leave_year:2021 | 8 | 0.03355 | -0.1568 | 1.033 |
| leave_five_year:1960-1964 | 60 | 0.02432 | -0.1629 | 1.027 |
| leave_recession:recession_1970-01 | 17 | 0.005748 | -0.1612 | 1.026 |
| leave_five_year:1970-1974 | 60 | 0.01166 | -0.1644 | 1.026 |

### Lag, weighting and composition

| Lag specification | N | r | Slope CI low | Slope CI high | Diagnostic q |
| --- | --- | --- | --- | --- | --- |
| lag_0 | 755 | 0.02633 | -0.007003 | 0.01245 | 1 |
| lag_5 | 755 | 0.09034 | -0.002741 | 0.02027 | 1 |
| lag_6 | 756 | -0.1543 | -0.008171 | -0.0055 | 1.166e-06 |
| lag_7 | 757 | 0.01934 | -0.004123 | 0.007759 | 1 |

| Weight/cohort specification | Status | Inference support | N | r | Slope CI low | Slope CI high |
| --- | --- | --- | --- | --- | --- | --- |
| population:overall | ok | True | 815 | -0.03027 | -0.0009683 | -2.151e-05 |
| fixed_composition_common_cohort | ok | False | 264 | -0.09111 | -0.008724 | 0.001358 |
| matched_composition_common_cohort | ok | False | 264 | -0.08917 | -0.008229 | 0.001317 |
| within_month_source_equal | ok | True | 756 | -0.1543 | -0.008171 | -0.0055 |
| within_month_rank | ok | True | 756 | -0.0734 | -0.004285 | -0.001981 |
| within_month_unique_song | ok | True | 756 | -0.1543 | -0.008171 | -0.0055 |
| genre_confidence_high | ok | True | 708 | -0.02114 | -0.007573 | 0.003608 |
| genre_confidence_medium_or_high | ok | True | 754 | -0.1537 | -0.008207 | -0.005504 |
| minimum_feature_songs_10 | ok | True | 587 | -0.04541 | -0.01256 | 0.003612 |
| minimum_feature_songs_20 | ok | False | 168 | 0.04751 | -0.03672 | 0.04665 |

Overall, within-genre and fixed-composition estimates have different target populations. Fixed and matched composition are compared on identical supported-genre months with identical time/season controls. Missing fixed-composition months are not filled. The source-row and distinct-song versions differ only where the original monthly release repeats a song/month; this is a small weighting sensitivity, not independent replication.

For caring, the fixed/matched composition comparison has only 264 months, below the original six 49-month-block support floor of 294. Its point estimates are descriptive, with formal diagnostic p=1. Rank weighting, high-confidence genre restriction and minimum available-song thresholds change the result materially; these also change the measured song cohort and do not diagnose a particular genre label as wrong.

The caring case's block-permutation exceedance probability is 0.002. This checks whether a shifted placement of locally ordered exposure blocks produces similarly large correlations; nonstationary shocks can violate exchangeability, so it is a diagnostic rather than an exact randomization test. Future-exposure comparisons are explicitly placebos and never forecasting predictors.

| Negative control | N | r | Nominal p | Diagnostic q |
| --- | --- | --- | --- | --- |
| future_external_at_least_12_months | 743 | 0.1187 | 3.597e-06 | 0.0001134 |
| future_external_at_least_60_months | 713 | 0.001732 | 0.9243 | 1 |
| extra_past_shift_60_months | 698 | -0.006845 | 0.589 | 1 |
| extra_past_shift_120_months | 638 | 0.01271 | 0.7962 | 1 |

**Outcome: Sensitive or unstable candidate.** Failed requirements: broad_effective_information, both_bootstrap_intervals_exclude_zero, weighting_stability, adjacent_lag_stability. There is no second retained classifier that independently measures caring on a new song sample. Alternate emotion or sentiment labels were not substituted after seeing these results.

## All candidates, including failures and controls

| ID | Music measure | External | Population | Lag | r | Min effective blocks | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01 | christmas_proximity_days | US_FEDERAL_ELECTION_MONTH | overall | 6 | -0.311 | 12.73 | Likely artifact |
| C02 | christmas_proximity_days | US_FEDERAL_ELECTION_MONTH | overall | 24 | -0.1135 | 10.01 | Likely artifact |
| C03 | emotion_confusion | US_GINI | overall | 0 | 0.603 | 5.244 | Insufficient evidence |
| C04 | title_version_marker | US_INITIAL_CLAIMS | overall | 12 | 0.2109 | 1.001 | Sensitive or unstable candidate |
| C05 | matched_composition__lyric_semantic_prior_hit_reference_n | US_IP_UTILITIES | overall | 12 | 0.9974 | 5.286 | Likely artifact |
| C06 | matched_composition__lyric_semantic_prior_hit_reference_n | US_NONFARM_EMPLOYMENT | overall | 24 | 0.9954 | 2.829 | Likely artifact |
| C07 | artist_credit_feature_marker | US_UNEMPLOYMENT | overall | 1 | 0.1472 | 1.437 | Sensitive or unstable candidate |
| C08 | christmas_proximity_days | US_EQUITY_DAILY_OBSERVED_TRADING_DAYS | Country | 3 | 0.2394 | 9.332 | Likely artifact |
| C09 | lyric_pos_other_share | US_REAL_GDP | Country | 24 | -0.4749 | 1.089 | Insufficient evidence |
| C10 | lyric_pos_other_share | US_RECREATION_SERVICES_NOMINAL | Country | 24 | -0.305 | 1.014 | Insufficient evidence |
| C11 | lyric_verb_present_share | US_TREASURY_3M | Country | 0 | 0.2902 | 2.353 | Insufficient evidence |
| C12 | detox_sexual_explicit | US_CONTINUED_CLAIMS | Pop | 3 | 0.1392 | 1.068 | Sensitive or unstable candidate |
| C13 | lyric_pos_other_share | US_CONTINUED_CLAIMS | Pop | 24 | 0.2429 | 1.015 | Sensitive or unstable candidate |
| C14 | christmas_proximity_days | US_FEDERAL_ELECTION_MONTH | Pop | 6 | -0.2923 | 11.78 | Likely artifact |
| C15 | emotion_nervousness | US_NONFARM_EMPLOYMENT | Pop | 0 | -0.1353 | 1.31 | Sensitive or unstable candidate |
| C16 | emotion_anger | US_NONFARM_EMPLOYMENT | Pop | 3 | -0.08538 | 1.311 | Sensitive or unstable candidate |
| C17 | emotion_amusement | US_NONFARM_EMPLOYMENT | Pop | 12 | -0.1395 | 1.338 | Sensitive or unstable candidate |
| C18 | detox_sexual_explicit | US_UNEMPLOYMENT_BENEFITS | Pop | 0 | 0.2427 | 1.04 | Likely artifact |
| C19 | artist_credit_feature_marker | US_CONTINUED_CLAIMS | R&B / Soul | 6 | 0.1373 | 1.072 | Sensitive or unstable candidate |
| C20 | detox_insult | US_CONTINUED_CLAIMS | R&B / Soul | 6 | 0.13 | 1.072 | Sensitive or unstable candidate |
| C21 | detox_obscene | US_CONTINUED_CLAIMS | R&B / Soul | 6 | 0.1602 | 1.048 | Sensitive or unstable candidate |
| C22 | lyric_mtld | US_CONTINUED_CLAIMS | R&B / Soul | 6 | 0.09498 | 1.072 | Sensitive or unstable candidate |
| C23 | emotion_amusement | US_CONTINUED_CLAIMS | R&B / Soul | 24 | 0.2301 | 1.075 | Sensitive or unstable candidate |
| C24 | lyric_word_count | US_CONTINUED_CLAIMS | R&B / Soul | 24 | 0.1329 | 1.075 | Sensitive or unstable candidate |
| C25 | detox_obscene | US_INITIAL_CLAIMS | R&B / Soul | 6 | 0.1416 | 1.086 | Sensitive or unstable candidate |
| C26 | emotion_caring | US_INITIAL_CLAIMS | R&B / Soul | 6 | -0.1673 | 1.086 | Sensitive or unstable candidate |
| C27 | lyric_pos_adp_share | US_INITIAL_CLAIMS | R&B / Soul | 6 | 0.1405 | 1.086 | Sensitive or unstable candidate |
| C28 | detox_toxicity | US_UNEMPLOYMENT | R&B / Soul | 6 | 0.1339 | 1.469 | Sensitive or unstable candidate |
| C29 | emotion_caring | US_UNEMPLOYMENT | R&B / Soul | 6 | -0.1543 | 1.469 | Sensitive or unstable candidate |
| C30 | lyric_pos_adj_share | US_UNEMPLOYMENT_BENEFITS | R&B / Soul | 6 | 0.1453 | 1.04 | Sensitive or unstable candidate |

The calendar rows are real timing associations, but they do not establish musical-content responses to economic conditions. Semantic reference-corpus counts measure construction/provenance; strong raw associations with expanding economic aggregates are not changes in lyrical meaning. The corrected substantive rows retain concentration and stability warnings. The four strongest failed domain comparisons remain failed candidates, not discoveries rescued by specification changes.

**Most influential years:** among the 19 sensitive/unstable candidates, the largest one-year coefficient change occurs in 2020 for 12 candidates, 2021 for four, and 2022 for three. These counts describe correlated selected comparisons, not 19 independent confirmations of one historical mechanism. Complete period attribution is in `most_influential_periods.csv` and `influential_period_summary.csv`.

**Strongest remaining numerical leads:** R&B/Soul featured-artist credit-marker share versus continued claims at six months (C19), and Pop OTHER-POS-token share versus continued claims at 24 months (C13), pass ten of eleven operational gates but fail the breadth-of-information gate. Their minimum exposure/score effective counts are about 1.07 and 1.02. A featured-credit marker is literal credit syntax, and OTHER-POS share is a rare parser category (nonzero in only 46 Pop months), not a broad emotional theme. Their measurement definitions are explicit in `candidate_measurement_audit.csv`. Neither qualifies as a robust musical-content discovery.

Every candidate has complete year, five-year, recession, shock, lag, trend, native-frequency, genre, coverage and weighting results in the CSV tables. `candidate_outcomes.csv` gives the most influential deletion, bootstrap intervals, lag/weight sign agreement, fixed-composition estimates and all failed classification gates. `observation_influence.csv.xz` contains all observation-level leverage, Cook distance and coefficient-deletion diagnostics, without restricted raw economic values.

## Null simulations and negative controls

| AR(1) | Simulation | Screen | Rejections / 200 | Rate | MC 95% low | MC 95% high |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | independent_rare_shocks | nominal_HAC | 12 | 0.06 | 0.03465 | 0.1019 |
| 0 | independent_rare_shocks | also_six_effective_blocks | 0 | 0 | 0 | 0.01885 |
| 0 | shared_trend_differenced | nominal_HAC | 8 | 0.04 | 0.02041 | 0.07693 |
| 0 | shared_trend_differenced | also_six_effective_blocks | 8 | 0.04 | 0.02041 | 0.07693 |
| 0 | shared_trend_raw_control | nominal_HAC | 200 | 1 | 0.9812 | 1 |
| 0 | shared_trend_raw_control | also_six_effective_blocks | 0 | 0 | 0 | 0.01885 |
| 0 | stationary_independent | nominal_HAC | 8 | 0.04 | 0.02041 | 0.07693 |
| 0 | stationary_independent | also_six_effective_blocks | 8 | 0.04 | 0.02041 | 0.07693 |
| 0.6 | independent_rare_shocks | nominal_HAC | 12 | 0.06 | 0.03465 | 0.1019 |
| 0.6 | independent_rare_shocks | also_six_effective_blocks | 0 | 0 | 0 | 0.01885 |
| 0.6 | shared_trend_differenced | nominal_HAC | 15 | 0.075 | 0.04597 | 0.12 |
| 0.6 | shared_trend_differenced | also_six_effective_blocks | 15 | 0.075 | 0.04597 | 0.12 |
| 0.6 | shared_trend_raw_control | nominal_HAC | 200 | 1 | 0.9812 | 1 |
| 0.6 | shared_trend_raw_control | also_six_effective_blocks | 0 | 0 | 0 | 0.01885 |
| 0.6 | stationary_independent | nominal_HAC | 8 | 0.04 | 0.02041 | 0.07693 |
| 0.6 | stationary_independent | also_six_effective_blocks | 8 | 0.04 | 0.02041 | 0.07693 |
| 0.9 | independent_rare_shocks | nominal_HAC | 16 | 0.08 | 0.04984 | 0.126 |
| 0.9 | independent_rare_shocks | also_six_effective_blocks | 0 | 0 | 0 | 0.01885 |
| 0.9 | shared_trend_differenced | nominal_HAC | 7 | 0.035 | 0.01706 | 0.07047 |
| 0.9 | shared_trend_differenced | also_six_effective_blocks | 7 | 0.035 | 0.01706 | 0.07047 |
| 0.9 | shared_trend_raw_control | nominal_HAC | 200 | 1 | 0.9812 | 1 |
| 0.9 | shared_trend_raw_control | also_six_effective_blocks | 0 | 0 | 0 | 0.01885 |
| 0.9 | stationary_independent | nominal_HAC | 21 | 0.105 | 0.06971 | 0.1552 |
| 0.9 | stationary_independent | also_six_effective_blocks | 21 | 0.105 | 0.06971 | 0.1552 |

The deliberately shared-trend raw scenario is a spurious-association control, not a stationary zero-slope null. Stationary simulations use independent innovations; the rare-shock scenario has independent shock locations. These finite simulations assess this implementation under declared generating processes and do not validate every assumption in the historical data. Full results, including stationarity-only screens, are preserved.

**Inferential calibration limitation:** at AR(1)=0.9, the stationary independent null rejects in 21/200 cases (10.5%, Monte Carlo 95% interval approximately 7.0%–15.5%) at nominal 5%. The six-effective-block screen does not fix this persistence case. Thus the original HAC approximation and the new diagnostic q-values must not be presented as validated false-discovery control for all these historical series. The audit retains this failure; it does not tune bandwidths until the simulation looks favorable. Block intervals offer another sensitivity view, not a demonstrated universal repair.

Twenty-six of 28 candidates with adequate permutation support have nominal block-permutation exceedance probabilities at or below 0.05; two additional candidates have insufficient permutation support. Passing that diagnostic is plainly not sufficient for the full robustness label. Future exposures, original rank associations, influential-period removal and coverage/weighting checks remain visible even when less favorable.

## Replication and next research decision

**Independent replications: zero.** Reproduction (A) succeeded for the V5 calculations; specification and measurement robustness (B) was tested; nonoverlapping historical windows and original chronological transfers (C) provide internal stability evidence. They reuse the same inspected history. Same-provider values in the historical and financial releases are checked in `external_source_reproduction.csv`, but their agreement is not new evidence (D). Related classifier-family comparisons reuse the songs and usually measure neighboring constructs.

No candidate presently justifies a nonlinear or conditional discovery campaign on the strength of this audit alone. The next defensible research step would be genuinely independent measurements or prospectively held-out observations under a locked protocol, with enough separate economic episodes and validated lyrical measurement. More flexibility cannot create information absent from the exposure history. No new source acquisition, broad search, or nonlinear campaign was launched.

Read [methodology](methodology.md), [validation](validation.json), [resource ledger](resource_ledger.json), [all candidate outcomes](candidate_outcomes.csv) and the [figure catalog](figure_catalog.csv).
