# Meaningful regression findings

**POST-HOC EXPLORATORY — the original 2018-onward final test had already been inspected.**
This report filters the complete campaign from commit `6d8da5fab45b3fd3326355282e4b6f95175dd9fc`. No new
untouched holdout is claimed. The policy and all winners were frozen before these
new refits; no test result changed a rule or selected a replacement winner.
The original hierarchies, models, metrics and public datasets remain byte-identical.

## Scope and interpretation policy

All 1,998,901 original combinations were recovered locally and
verified against the completed campaign's exact candidate and score hashes. We
excluded **32,619 combinations**, leaving **1,966,282**;
**789,225** satisfy the strict cross-domain definition.
All 59 targets have filtered and cross-domain winners. The 20 directed pairwise
reconstruction relationships are supplemented by a two-endpoint exposure rule.
Rule counts overlap; exclusions count each combination only once.

The [frozen policy](meaningful/relationship_policy.json) and
[complete pair registry](meaningful/relationship_pairs.csv) record definitions,
domains, reasons and source references. Rules use the public schema and production
derivations, never a correlation threshold. See [the public definitions](../../data/public/README.md).

| Category | Operational meaning | Treatment |
|---|---|---|
| A: circular / reconstruction | Weekly rows versus distinct weekly dates; alternative calendar coordinates of the same chart career; min/median/max of the same recording-length set; both episode endpoints predicting its exposure count | Excluded |
| B: redundant / same-family | Shared information domain, including related classifier constructs, MusicBrainz counts, and chart-performance aggregates | Retained and labelled |
| C: cross-domain | Every predictor belongs to a different information domain from the target, with no A rule | Separate strict view |

There are six documented domains: lyrical content (LyricLens/Detoxify), lyrical
affect (GoEmotions/sentiment), genre, historical calendar, MusicBrainz metadata,
and chart performance. Mixed B/C combinations are B with cross-domain tags.
Domain boundaries are interpretive choices, not discovered natural categories.
C can share the same lyrics or chart source with its target; it does not establish
independent measurement. A also includes explicitly documented reconstruction
scope restrictions beyond exact algebraic identity: endpoints can differ because
of gaps, month sampling, and recording versions. These are not claims of equality.

Monthly versus weekly exposure counts, points versus count/best rank, and related
MusicBrainz counts remain B. They are not exactly interchangeable under the stated
definitions. Thus a filtered leaderboard can still be dominated by redundancy;
its label means eligible under this policy, not inherently novel science.

## Most predictable filtered targets

| Target | Predictors | Category | Validation R² | Exploratory test R² | 95% song-bootstrap R² interval |
| --- | --- | --- | --- | --- | --- |
| snapshot_months_selected | first_chart_date + first_snapshot_month + weekly_observation_count | B | 0.9563 | 0.9387 | [0.9097, 0.9602] |
| weekly_observation_count | first_chart_date + first_snapshot_month + snapshot_months_selected | B | 0.9551 | 0.9363 | [0.9098, 0.9561] |
| chart_weeks | first_chart_date + first_snapshot_month + snapshot_months_selected | B | 0.9550 | 0.9362 | [0.9098, 0.9561] |
| mb_recording_count | mb_distinct_duration_count + mb_duration_max_seconds + mb_release_count | B | 0.9438 | 0.9243 | [0.8238, 0.9533] |
| detox_toxicity | detox_insult + detox_obscene + detox_severe_toxicity | B | 0.8661 | 0.9094 | [0.9005, 0.9178] |
| mb_distinct_duration_count | mb_duration_median_seconds + mb_duration_min_seconds + mb_recording_count | B | 0.9393 | 0.9029 | [0.7750, 0.9444] |
| total_chart_points | best_chart_rank + chart_weeks + primary_genre | B | 0.8643 | 0.8679 | [0.8611, 0.8747] |
| detox_insult | detox_obscene + detox_severe_toxicity + detox_toxicity | B | 0.7661 | 0.8596 | [0.8482, 0.8699] |
| emotion_sadness | emotion_disappointment + emotion_grief + emotion_nervousness | B | 0.8779 | 0.8511 | [0.8295, 0.8673] |
| emotion_grief | emotion_nervousness + emotion_relief + emotion_sadness | B | 0.8636 | 0.8177 | [0.7824, 0.8447] |

All of these leading combinations are B. Chart exposure summaries and metadata
counts retain substantial shared structure. The strongest lyric-score example is
toxicity from insult, obscenity and severe toxicity, R² 0.909.
It measures agreement among frozen model outputs rather than human-validated accuracy.

## Least predictable filtered targets

| Target | Predictors | Category | Validation R² | Exploratory test R² | 95% song-bootstrap R² interval |
| --- | --- | --- | --- | --- | --- |
| emotion_gratitude | emotion_joy + emotion_neutral + emotion_relief | B | 0.0109 | 0.0164 | [-0.0190, 0.0304] |
| weekly:reported_weeks_on_chart | mb_release_year + reported_peak_position + weekly_rank | B | 0.4685 | -0.1064 | [-0.1628, -0.0547] |
| mb_duration_min_seconds | mb_distinct_duration_count + snapshot_months_selected + total_chart_points | B | -0.0661 | -0.1276 | [-0.1544, -0.1041] |
| monthly:reported_weeks_on_chart | monthly_rank + reported_peak_position + snapshot_chart_date | B | 0.4288 | -0.1771 | [-0.2406, -0.1221] |
| mb_duration_median_seconds | ll_violence + mb_distinct_duration_count + mb_recording_count | B | -0.3481 | -0.3950 | [-0.4674, -0.3324] |
| mb_duration_max_seconds | mb_distinct_duration_count + mb_recording_count | B | 0.0136 | -0.5834 | [-0.7097, -0.4683] |
| first_snapshot_month | mb_release_year + primary_genre + snapshot_months_selected | B | -17.0199 | -49.7060 | [-53.8558, -46.0681] |
| last_chart_date | mb_release_year + primary_genre + snapshot_months_selected | B | -16.9951 | -50.1594 | [-54.3535, -46.3698] |
| last_snapshot_month | mb_release_year + primary_genre + snapshot_months_selected | B | -16.9975 | -50.2322 | [-54.4262, -46.4370] |
| first_chart_date | best_chart_rank + chart_weeks + detox_obscene | C | -79.6134 | -228.0318 | [-237.1844, -219.4581] |

Large negative calendar R² values are retained without clipping. The recent test
cohort has a much narrower date range than historical training, and these models
poorly extrapolate its calendar location after the same-career date predictors are
removed. The training-mean baseline is often worse still, so positive baseline
skill can coexist with very negative R². This does not make the model useful.
Date errors are in days, snapshot-month errors in months, and release-year errors
in years. Weak prediction in this setting is not evidence of objective randomness.

## Strongest cross-domain relationships

| Target | Predictors | Category | Validation R² | Exploratory test R² | 95% song-bootstrap R² interval |
| --- | --- | --- | --- | --- | --- |
| detox_insult | emotion_anger + emotion_annoyance + primary_genre | C | 0.3907 | 0.5713 | [0.5469, 0.5931] |
| detox_toxicity | emotion_anger + emotion_annoyance + primary_genre | C | 0.3816 | 0.5504 | [0.5203, 0.5769] |
| detox_obscene | emotion_anger + first_chart_date + primary_genre | C | 0.2970 | 0.5215 | [0.4951, 0.5465] |
| emotion_anger | detox_severe_toxicity + detox_sexual_explicit + detox_toxicity | C | 0.3101 | 0.4308 | [0.3866, 0.4744] |
| emotion_annoyance | detox_insult + detox_obscene + detox_sexual_explicit | C | 0.3030 | 0.4269 | [0.3974, 0.4594] |
| detox_severe_toxicity | emotion_anger + emotion_disapproval + primary_genre | C | 0.1541 | 0.3936 | [0.3595, 0.4253] |
| detox_identity_attack | emotion_anger + primary_genre + secondary_genres | C | 0.1851 | 0.3495 | [0.3274, 0.3694] |
| ll_explicit_language | emotion_annoyance + primary_genre + secondary_genres | C | 0.3663 | 0.2908 | [0.2432, 0.3394] |
| ll_violence | emotion_annoyance + primary_genre + sentiment_negative | C | 0.1600 | 0.2698 | [0.2400, 0.2972] |
| ll_sexual_content | emotion_grief + primary_genre + secondary_genres | C | 0.2103 | 0.2628 | [0.2281, 0.2968] |

Content–affect links often share the same lyrics despite using different model
families. Genre adds population structure but is itself a frozen inferred label.
These results describe associations and cohort transfer, not causal effects or
independent validation of the classifier panel.

## Chart-success prediction

| Target | Predictors | Category | Validation R² | Exploratory test R² | 95% song-bootstrap R² interval |
| --- | --- | --- | --- | --- | --- |
| weekly:reported_weeks_on_chart | chart_date + first_chart_date + secondary_genres | C | 0.2066 | 0.1686 | [0.1481, 0.1915] |
| total_chart_points | first_chart_date + last_snapshot_month + mb_release_count | C | 0.1622 | 0.0077 | [-0.0313, 0.0340] |
| monthly:reported_weeks_on_chart | first_chart_date + mb_release_count + snapshot_chart_date | C | 0.1497 | 0.0026 | [-0.0342, 0.0305] |
| snapshot_months_selected | last_snapshot_month + mb_release_count + secondary_genres | C | 0.0603 | -0.1966 | [-0.2542, -0.1485] |
| chart_weeks | last_chart_date + mb_release_count + secondary_genres | C | 0.0576 | -0.2158 | [-0.2760, -0.1690] |
| weekly_observation_count | last_chart_date + mb_release_count + secondary_genres | C | 0.0576 | -0.2159 | [-0.2761, -0.1691] |

The cross-domain model for total chart points has R² 0.0077
and its fixed-model song-bootstrap interval includes zero. Monthly reported weeks
also has almost no explained variance. Whole-history exposure counts have negative
cross-domain test R². The weekly reported-weeks model uses current and first chart
dates plus genre; it is partly an elapsed-time proxy within chart history, not a
demonstration that lyrical characteristics forecast success. Gaps/re-entries and the
separately reported counter prevent an exact identity, but this shared provenance
limits its interpretation. No general lyric-to-chart-success claim is supported.

## Genre and historical period

Genre occurs in 31 cross-domain winners; calendar/date/year variables occur
in 16. Examples worth explaining are obscenity from anger, debut date and
genre (R² 0.521); explicit language from annoyance and the two
genre fields (R² 0.291); and substance-use score from
neutral affect, first snapshot month and primary genre (R² 0.176).
These combinations do not isolate a marginal genre or period effect. They cannot
support a COVID breakpoint claim, and no such analysis was performed.

## Biggest changes and historical transfer failures

Only 9 filtered winners differ from the original unrestricted winners.
The following comparison is descriptive; test changes did not select these models.

| Target | Original test R² | Filtered test R² | Change | Excluded original rule |
| --- | --- | --- | --- | --- |
| first_chart_date | 0.9937 | -228.0318 | -229.0255 | same_career_calendar |
| last_snapshot_month | 0.9963 | -50.2322 | -51.2285 | same_career_calendar |
| last_chart_date | 0.9966 | -50.1594 | -51.1560 | same_career_calendar |
| first_snapshot_month | 0.9937 | -49.7060 | -50.6997 | same_career_calendar |
| mb_duration_max_seconds | 0.8770 | -0.5834 | -1.4604 | same_recording_duration |
| mb_duration_median_seconds | 0.8245 | -0.3950 | -1.2195 | same_recording_duration |
| mb_duration_min_seconds | 0.8207 | -0.1276 | -0.9483 | same_recording_duration |
| chart_weeks | 1.0000 | 0.9362 | -0.0638 | row_date_count_alias, career_interval_exposure |
| weekly_observation_count | 1.0000 | 0.9363 | -0.0637 | row_date_count_alias, career_interval_exposure |

There are 9 negative-R² filtered targets and
18 negative-R² cross-domain targets. Against the
training-mean squared-error baseline, 4
filtered models and 6 cross-domain
models fail. The full files also report training-median MAE baselines, validation
MAE/RMSE, all gaps, sample sizes and each historical validation period.

## Eight presentation findings

1. **High accuracy can be reconstruction.** Removing 32,619 definition-based
   candidates changes nine winners and sharply reduces calendar/duration performance.
2. **Redundancy remains informative but must be named.** Toxicity R² is
   0.909 within related content outputs versus
   0.550 for the selected cross-domain model.
3. **The strongest cross-domain result is moderate, not near-perfect.** Insult
   from anger, annoyance and genre reaches R² 0.571.
4. **Genre and affect jointly relate to explicitness.** The strict cross-domain
   explicit-language model reaches R² 0.291; do not
   interpret this as a causal genre effect.
5. **Moderation scores have different predictability.** Violence reaches
   cross-domain R² 0.270, sexual content
   0.263, and substance use
   0.176. These are limited explanatory fractions.
6. **Chart success does not transfer well from the other domains.** Total points
   has cross-domain R² 0.0077, with uncertainty spanning
   zero; longevity counts perform below the test-mean reference.
7. **Historical transfer matters.** Show the extreme calendar failures and the
   validation-to-test gaps instead of presenting only attractive fitted examples.
8. **A real interactive prediction can be wrong.** Use the local demo to compare
   actual values, predictions and residuals, then change inputs and discuss
   availability, missingness and extrapolation. Never replace a poor held-out row
   with a fabricated example or claim that a single good prediction proves accuracy.

## Limitations and reproducibility

All new results are post-hoc exploratory. The policy was informed by known variable
definitions and the already inspected unrestricted study. The same final population
cannot provide fresh confirmatory evidence. A new future cohort would be needed for
confirmation; none was acquired. The exhaustive original search creates selection
optimism; fixed-model bootstrap intervals do not include selection/refit uncertainty
or multiple-comparison adjustment. Two-year debut-block intervals are exploratory.

OLS is additive with at most three original predictors; genre variables expand to
multiple columns. Predictions are not clipped. Outcomes are frozen classifier scores
or retrospective metadata, with enrichment timing not certified at historical dates.
Missing-target populations differ. Chart histories are censored at 2026-09-19,
and whole-song temporal purging changes cohort composition. These limitations matter
especially for calendar extrapolation and apparent chart-success prediction.

Complete original hierarchies are accessed read-only. Complete filtered SQLite
indices retain every original candidate ID and its filtered/category rank; no sampled
candidate set was substituted. Validation ranks retain the original mean-period
baseline-relative MSE skill and tie rules. All 59 filtered winners and 59 strict
cross-domain winners were frozen together; 117
distinct refits sufficed. Filtering/integrity checks took 87.3s;
selected-model refits and uncertainty took 103.8s.
The original two-million-combination campaign was not rerun.

See the [launch and reproduction guide](meaningful/README.md),
[filtered leaderboard](meaningful/filtered_leaderboard.csv),
[cross-domain leaderboard](meaningful/cross_domain_leaderboard.csv),
[all best-by-size models](meaningful/best_by_predictor_count.csv),
[verification evidence](meaningful/validation.json), and
[selected-model manifest](meaningful/model_manifest.json).
Large indices, fitted models, predictions and splits remain local and ignored.
Current test status: PASS.
