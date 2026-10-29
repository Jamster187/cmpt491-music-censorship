# V5 findings: exhaustive music × historical conditions

The campaign completed **9,116,352 attempted pair/track analyses** and a global family of **18,046,656 method hypotheses**. **2,840,275** pair/track rows were estimable; **1,520,058** passed the inference screens. **712** pair/track rows had at least one global BY q≤0.05, representing **754** method rejections.

These are exploratory retrospective associations, conditional on the declared time-series assumptions. Statistical correction does not establish causality, point-in-time forecasting, or independence from changing coverage. Historical evaluation periods were already inspected in earlier campaigns.

**The corrected count is not a count of established musical discoveries.** A post-fit influence audit found **603 of 712** corrected rows with fewer than six effective exposure/score blocks. Among **178 adjusted lyrical rows**, **0** combined broad temporal variation with at least two positive same-direction transfer folds. The four adjusted rows without that concentration flag are all `christmas_proximity_days` versus `US_FEDERAL_ELECTION_MONTH`: calendar timing, not a discovered relationship between lyrical content and historical conditions. This sensitivity audit does not change any original estimate, q value or family denominator; it limits their substantive interpretation.

Among **133,839** raw numeric relationships with |r|≥0.5, **119,399** had an estimable adjusted counterpart; **107,882** fell below |r|=0.1 after adjustment. Unsupported adjusted fits are not counted as disappearing effects. The [complete status summary](coverage_and_status.csv) separates insufficient support, unidentified effects and other failures from valid nonsignificant estimates.

## Counts by domain and track

| External domain | Track | Attempted pair/track rows | Estimable | Passed inference screens | Any BY rejection |
| --- | --- | ---: | ---: | ---: | ---: |
| cultural | adjusted | 186,048 | 19,032 | 18,228 | 1 |
| cultural | raw | 186,048 | 22,624 | 0 | 0 |
| financial | adjusted | 1,534,896 | 575,683 | 513,591 | 0 |
| financial | raw | 1,534,896 | 669,012 | 196,809 | 5 |
| macroeconomic | adjusted | 1,860,480 | 605,953 | 531,669 | 564 |
| macroeconomic | raw | 1,860,480 | 696,660 | 157,728 | 63 |
| political | adjusted | 674,424 | 55,566 | 48,239 | 4 |
| political | raw | 674,424 | 62,054 | 9,919 | 41 |
| social | adjusted | 302,328 | 62,693 | 34,936 | 0 |
| social | raw | 302,328 | 70,998 | 8,939 | 34 |

## Reading the tables

Every table below follows a declared ranking rule; the leading rows can include repeated lags or related transformations of the same underlying construct. The top raw list is a diagnostic list and can be dominated by secular trends. Coverage/count variables are not lyrical-content discoveries. Adjusted and domain/genre/lag rankings prioritize stationarity-supported estimates; domain/genre/lag lists prefer adjusted fits before raw fits. Categorical effect is partial η²; numeric effect is Pearson r or its adjusted partial counterpart.

Intervals are **native-unit OLS slope intervals**, not correlation intervals. Best q is the smaller of the two separately corrected numeric method q values; both are retained in the CSVs. “Stable folds” means positive baseline-relative skill with the full-sample correlation direction, divided by completed folds; 1/1 does not mean success in all three periods. Categorical contrasts and their descriptive intervals remain in the complete local export.

Each linked CSV is a **top-200 summary**, not the entire campaign. The ten complete local rankings retain every row in their declared subset, including unsupported/null rows. [Reproduction and complete export instructions](README.md) explain how to retrieve them.

## Top 20 raw relationships

[Full summary CSV](raw_relationships.csv)

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 12m; raw | r=0.997 | 313 | [41.5, 44.1] | 1 | 2/2 |
| 2 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 24m; raw | r=0.997 | 313 | [41.1, 44.1] | 1 | 2/2 |
| 3 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 6m; raw | r=0.997 | 313 | [41.8, 44.4] | 1 | 2/2 |
| 4 | `fixed_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 24m; raw | r=0.997 | 313 | [40.9, 43.8] | 1 | 2/2 |
| 5 | `fixed_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 6m; raw | r=0.997 | 313 | [41.6, 44.1] | 1 | 2/2 |
| 6 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 3m; raw | r=0.997 | 313 | [41.8, 44.4] | 1 | 2/2 |
| 7 | `fixed_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 12m; raw | r=0.997 | 313 | [41.3, 43.9] | 1 | 2/2 |
| 8 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 1m; raw | r=0.997 | 313 | [41.8, 44.4] | 1 | 2/2 |
| 9 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 0m; raw | r=0.997 | 313 | [41.8, 44.4] | 1 | 2/2 |
| 10 | `fixed_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 3m; raw | r=0.997 | 313 | [41.6, 44.1] | 1 | 2/2 |
| 11 | `fixed_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 1m; raw | r=0.997 | 313 | [41.6, 44.1] | 1 | 2/2 |
| 12 | `fixed_composition__lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | overall; 0m; raw | r=0.996 | 313 | [41.5, 44.1] | 1 | 2/2 |
| 13 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | overall; 24m; raw | r=0.995 | 302 | [0.0352, 0.0406] | 1 | 2/2 |
| 14 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | overall; 12m; raw | r=0.995 | 309 | [0.0359, 0.0411] | 1 | 2/2 |
| 15 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | overall; 6m; raw | r=0.994 | 313 | [0.0361, 0.0415] | 1 | 2/2 |
| 16 | `fixed_composition__lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | overall; 24m; raw | r=0.994 | 302 | [0.0348, 0.0405] | 1 | 2/2 |
| 17 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | overall; 3m; raw | r=0.994 | 313 | [0.0361, 0.0417] | 1 | 2/2 |
| 18 | `fixed_composition__lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | overall; 12m; raw | r=0.994 | 309 | [0.0355, 0.041] | 1 | 2/2 |
| 19 | `matched_composition__lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | overall; 1m; raw | r=0.994 | 313 | [0.0361, 0.0418] | 1 | 2/2 |
| 20 | `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | R&B / Soul; 0m; raw | r=0.994 | 776 | [0.0381, 0.0417] | 1 | 3/3 |


## Top 20 adjusted relationships

[Full summary CSV](adjusted_relationships.csv)

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `genre_share__Afrobeats / African Pop` | `US_LIFE_EXPECTANCY` | overall; 12m; adjusted | r=-0.776 | 64 | [-0.00608, -0.00132] | 1 | 2/3 |
| 2 | `emotion_amusement` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 24m; adjusted | η²=0.474 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 3 | `lyric_parser_sentence_length_mean` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 24m; adjusted | η²=0.452 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 4 | `first_credited_entity_prior_song_count` | `US_PERSONAL_INCOME` | R&B / Soul; 6m; adjusted | r=0.669 | 757 | [1.21, 5.32] | 1 | 0/3 |
| 5 | `lyric_pos_num_share` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 0m; adjusted | η²=0.446 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 6 | `lyric_question_line_share` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 3m; adjusted | η²=0.432 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 7 | `lyric_pos_adj_share` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 12m; adjusted | η²=0.412 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 8 | `first_credited_entity_prior_song_count` | `US_DISPOSABLE_INCOME` | R&B / Soul; 6m; adjusted | r=0.635 | 757 | [0.619, 4.64] | 1 | 0/3 |
| 9 | `first_credited_entity_prior_song_count` | `US_REAL_DISPOSABLE_INCOME` | R&B / Soul; 6m; adjusted | r=0.632 | 757 | [0.553, 4.67] | 1 | 0/3 |
| 10 | `first_credited_entity_prior_song_count` | `US_REAL_DISPOSABLE_INCOME_PC` | R&B / Soul; 6m; adjusted | r=0.632 | 757 | [0.551, 4.67] | 1 | 0/3 |
| 11 | `first_credited_entity_prior_song_count` | `US_REAL_DISPOSABLE_INCOME_PC_MOM` | R&B / Soul; 6m; adjusted | r=0.63 | 757 | [0.629, 4.44] | 1 | 0/3 |
| 12 | `emotion_curiosity` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 3m; adjusted | η²=0.39 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 13 | `mb_v2_external_release_list_truncated__available_n` | `US_LIFE_EXPECTANCY` | Alternative / Indie; 1m; adjusted | r=-0.624 | 42 | [-0.946, -0.0304] | 1 | 0/1 |
| 14 | `lyric_cmu_endword_coverage` | `US_GINI` | overall; 0m; adjusted | r=-0.619 | 61 | [-0.00908, -0.00287] | 1 | 0/0 |
| 15 | `lyric_semantic_prior_hit_reference_n` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | R&B / Soul; 0m; adjusted | η²=0.372 | 28 | omnibus; contrasts local | 1 | 0/0 |
| 16 | `lyric_pos_adj_share` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 6m; adjusted | η²=0.368 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 17 | `lyric_semantic_prior_hit_reference_n` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 0m; adjusted | η²=0.367 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 18 | `emotion_confusion` | `US_GINI` | overall; 0m; adjusted | r=0.603 | 61 | [0.00299, 0.0086] | 1 | 0/0 |
| 19 | `credit_prior_song_observed_longevity_median` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | R&B / Soul; 24m; adjusted | η²=0.358 | 25 | omnibus; contrasts local | 1 | 0/0 |
| 20 | `lyric_modern_wordfreq_coverage` | `US_GINI` | overall; 0m; adjusted | r=-0.597 | 61 | [-0.00251, -0.000776] | 1 | 0/0 |


## Top 20 within-genre relationships

[Full summary CSV](genre_relationships.csv)

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `first_credited_entity_prior_song_count` | `US_PERSONAL_INCOME` | R&B / Soul; 6m; adjusted | r=0.669 | 757 | [1.21, 5.32] | 1 | 0/3 |
| 2 | `first_credited_entity_prior_song_count` | `US_DISPOSABLE_INCOME` | R&B / Soul; 6m; adjusted | r=0.635 | 757 | [0.619, 4.64] | 1 | 0/3 |
| 3 | `first_credited_entity_prior_song_count` | `US_REAL_DISPOSABLE_INCOME` | R&B / Soul; 6m; adjusted | r=0.632 | 757 | [0.553, 4.67] | 1 | 0/3 |
| 4 | `first_credited_entity_prior_song_count` | `US_REAL_DISPOSABLE_INCOME_PC` | R&B / Soul; 6m; adjusted | r=0.632 | 757 | [0.551, 4.67] | 1 | 0/3 |
| 5 | `first_credited_entity_prior_song_count` | `US_REAL_DISPOSABLE_INCOME_PC_MOM` | R&B / Soul; 6m; adjusted | r=0.63 | 757 | [0.629, 4.44] | 1 | 0/3 |
| 6 | `mb_v2_external_release_list_truncated__available_n` | `US_LIFE_EXPECTANCY` | Alternative / Indie; 1m; adjusted | r=-0.624 | 42 | [-0.946, -0.0304] | 1 | 0/1 |
| 7 | `lyric_semantic_prior_hit_reference_n` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | R&B / Soul; 0m; adjusted | η²=0.372 | 28 | omnibus; contrasts local | 1 | 0/0 |
| 8 | `credit_prior_song_observed_longevity_median` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | R&B / Soul; 24m; adjusted | η²=0.358 | 25 | omnibus; contrasts local | 1 | 0/0 |
| 9 | `first_credited_entity_prior_song_count` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | Pop; 24m; adjusted | η²=0.354 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 10 | `lyric_semantic_prior_hit_reference_n` | `US_PCE_NOMINAL` | Hip-Hop / Rap; 12m; adjusted | r=0.595 | 432 | [5.33, 12.5] | 1 | 1/1 |
| 11 | `credit_prior_chart_points` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | Pop; 24m; adjusted | η²=0.35 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 12 | `credit_prior_chart_weeks` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | Pop; 24m; adjusted | η²=0.339 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 13 | `credit_prior_song_observed_longevity_median` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | R&B / Soul; 12m; adjusted | η²=0.329 | 25 | omnibus; contrasts local | 1 | 0/0 |
| 14 | `audio_submission_count__available_n` | `US_LIFE_EXPECTANCY` | Country; 24m; adjusted | r=0.573 | 55 | [0.966, 4.42] | 1 | 1/2 |
| 15 | `credit_prior_top10_song_count` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | Pop; 24m; adjusted | η²=0.326 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 16 | `credited_entities_prior_top10_mean` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | Pop; 24m; adjusted | η²=0.32 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 17 | `lyric_semantic_prior_credit_reference_n` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | Pop; 24m; adjusted | η²=0.314 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 18 | `artist_prior_collaborator_count` | `US_PERSONAL_INCOME` | R&B / Soul; 6m; adjusted | r=0.556 | 757 | [0.317, 1.48] | 1 | 0/3 |
| 19 | `first_credited_entity_prior_song_count` | `US_PERSONAL_SAVING_RATE` | R&B / Soul; 6m; adjusted | r=0.554 | 757 | [-0.372, 5.83] | 1 | 0/3 |
| 20 | `artist_prior_collaboration_degree_max` | `US_PERSONAL_INCOME` | R&B / Soul; 6m; adjusted | r=0.55 | 757 | [0.421, 1.85] | 1 | 1/3 |


## Top 20 between-genre composition relationships

[Full summary CSV](between_genre_relationships.csv)

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `genre_share__Afrobeats / African Pop` | `US_LIFE_EXPECTANCY` | overall; 12m; adjusted | r=-0.776 | 64 | [-0.00608, -0.00132] | 1 | 2/3 |
| 2 | `genre_share__Latin` | `US_LIFE_EXPECTANCY` | overall; 24m; adjusted | r=-0.57 | 64 | [-0.0459, -0.00319] | 1 | 0/2 |
| 3 | `genre_share__Latin` | `US_GINI` | overall; 24m; adjusted | r=-0.452 | 61 | [-0.0333, 0.00915] | 1 | 0/1 |
| 4 | `genre_share__Afrobeats / African Pop` | `US_REAL_GDP` | overall; 24m; adjusted | r=0.441 | 271 | [-0.000184, 0.00186] | 1 | 2/3 |
| 5 | `genre_share__Afrobeats / African Pop` | `US_REAL_GDP_GROWTH` | overall; 24m; adjusted | r=0.418 | 271 | [-4.78e-05, 0.000439] | 1 | 2/3 |
| 6 | `genre_share__Alternative / Indie` | `GLOBAL_STATE_CONFLICTS` | overall; 6m; adjusted | r=-0.407 | 67 | [-0.00506, -0.000153] | 1 | 1/3 |
| 7 | `genre_share__Afrobeats / African Pop` | `US_LIFE_EXPECTANCY` | overall; 3m; adjusted | r=-0.407 | 64 | [-0.00771, 0.000183] | 1 | 0/3 |
| 8 | `genre_share__Electronic / Dance` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 24m; adjusted | η²=0.165 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 9 | `genre_share__Afrobeats / African Pop` | `US_NOMINAL_GDP` | overall; 24m; adjusted | r=0.404 | 271 | [-0.000171, 0.00156] | 1 | 1/3 |
| 10 | `genre_share__Afrobeats / African Pop` | `US_LIFE_EXPECTANCY` | overall; 24m; adjusted | r=-0.401 | 64 | [-0.00383, -4.42e-05] | 1 | 1/2 |
| 11 | `genre_share__Afrobeats / African Pop` | `US_LIFE_EXPECTANCY` | overall; 1m; adjusted | r=-0.399 | 64 | [-0.00661, 7.26e-05] | 1 | 0/3 |
| 12 | `genre_share__Alternative / Indie` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 24m; adjusted | η²=0.159 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 13 | `genre_share__Afrobeats / African Pop` | `US_GINI` | overall; 24m; adjusted | r=-0.394 | 61 | [-0.00288, 0.000524] | 1 | 0/1 |
| 14 | `genre_share__Afrobeats / African Pop` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 0m; adjusted | η²=0.151 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 15 | `genre_share__Afrobeats / African Pop` | `US_LIFE_EXPECTANCY` | overall; 6m; adjusted | r=-0.379 | 64 | [-0.00406, 2.84e-05] | 1 | 2/3 |
| 16 | `genre_share__Afrobeats / African Pop` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 3m; adjusted | η²=0.133 | 33 | omnibus; contrasts local | 1 | 0/1 |
| 17 | `genre_share__Afrobeats / African Pop` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 12m; adjusted | η²=0.107 | 33 | omnibus; contrasts local | 1 | 0/1 |
| 18 | `genre_share__Afrobeats / African Pop` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 6m; adjusted | η²=0.106 | 33 | omnibus; contrasts local | 1 | 0/1 |
| 19 | `genre_share__K-Pop` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 24m; adjusted | η²=0.106 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 20 | `genre_share__Metal` | `GLOBAL_HIGH_INTENSITY_CONFLICTS` | overall; 24m; adjusted | r=0.324 | 67 | [-9.06e-05, 0.00159] | 1 | 1/2 |


## Strongest financial associations

[Full summary CSV](financial_relationships.csv)

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `prior_year_unique_chart_song_count` | `US_NFCI` | Rock; 12m; adjusted | r=0.291 | 441 | [0.161, 1.91] | 1 | 2/2 |
| 2 | `lyric_verb_present_share` | `US_TREASURY_3M` | Country; 0m; adjusted | r=0.29 | 358 | [0.00247, 0.0534] | 1 | 0/1 |
| 3 | `mb_v2_external_cover_evidence__available_n` | `US_TREASURY_3M` | R&B / Soul; 6m; adjusted | r=0.283 | 534 | [-0.0237, 0.249] | 1 | 2/2 |
| 4 | `mb_v2_external_cover_evidence__available_n` | `US_TREASURY_2Y` | R&B / Soul; 24m; adjusted | r=0.277 | 579 | [-0.0068, 0.194] | 1 | 0/2 |
| 5 | `prior_year_unique_chart_song_count` | `US_ANFCI` | Rock; 12m; adjusted | r=0.268 | 441 | [0.178, 1.63] | 1 | 2/2 |


## Strongest macroeconomic associations

[Full summary CSV](macroeconomic_relationships.csv)

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `first_credited_entity_prior_song_count` | `US_PERSONAL_INCOME` | R&B / Soul; 6m; adjusted | r=0.669 | 757 | [1.21, 5.32] | 1 | 0/3 |
| 2 | `first_credited_entity_prior_song_count` | `US_DISPOSABLE_INCOME` | R&B / Soul; 6m; adjusted | r=0.635 | 757 | [0.619, 4.64] | 1 | 0/3 |
| 3 | `first_credited_entity_prior_song_count` | `US_REAL_DISPOSABLE_INCOME` | R&B / Soul; 6m; adjusted | r=0.632 | 757 | [0.553, 4.67] | 1 | 0/3 |
| 4 | `first_credited_entity_prior_song_count` | `US_REAL_DISPOSABLE_INCOME_PC` | R&B / Soul; 6m; adjusted | r=0.632 | 757 | [0.551, 4.67] | 1 | 0/3 |
| 5 | `first_credited_entity_prior_song_count` | `US_REAL_DISPOSABLE_INCOME_PC_MOM` | R&B / Soul; 6m; adjusted | r=0.63 | 757 | [0.629, 4.44] | 1 | 0/3 |


## Strongest political/social associations

[Full summary CSV](political_social_relationships.csv)

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `genre_share__Afrobeats / African Pop` | `US_LIFE_EXPECTANCY` | overall; 12m; adjusted | r=-0.776 | 64 | [-0.00608, -0.00132] | 1 | 2/3 |
| 2 | `emotion_amusement` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 24m; adjusted | η²=0.474 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 3 | `lyric_parser_sentence_length_mean` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 24m; adjusted | η²=0.452 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 4 | `lyric_pos_num_share` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 0m; adjusted | η²=0.446 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 5 | `lyric_question_line_share` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 3m; adjusted | η²=0.432 | 33 | omnibus; contrasts local | 1 | 0/0 |


## Leading lagged relationships

[Full summary CSV](lagged_relationships.csv)

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `genre_share__Afrobeats / African Pop` | `US_LIFE_EXPECTANCY` | overall; 12m; adjusted | r=-0.776 | 64 | [-0.00608, -0.00132] | 1 | 2/3 |
| 2 | `emotion_amusement` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 24m; adjusted | η²=0.474 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 3 | `lyric_parser_sentence_length_mean` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 24m; adjusted | η²=0.452 | 33 | omnibus; contrasts local | 1 | 0/0 |
| 4 | `first_credited_entity_prior_song_count` | `US_PERSONAL_INCOME` | R&B / Soul; 6m; adjusted | r=0.669 | 757 | [1.21, 5.32] | 1 | 0/3 |
| 5 | `lyric_question_line_share` | `US_CONGRESS_HOUSE_MAJORITY_SOURCE` | overall; 3m; adjusted | η²=0.432 | 33 | omnibus; contrasts local | 1 | 0/0 |


## Historical transfer stability

[Full summary CSV](historical_stability.csv)

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | R&B / Soul; 0m; raw | r=0.994 | 776 | [0.0381, 0.0417] | 1 | 3/3 |
| 2 | `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | R&B / Soul; 1m; raw | r=0.994 | 776 | [0.0381, 0.0417] | 1 | 3/3 |
| 3 | `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | R&B / Soul; 3m; raw | r=0.993 | 776 | [0.0381, 0.0417] | 1 | 3/3 |
| 4 | `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | Country; 6m; raw | r=0.993 | 521 | [0.0382, 0.0419] | 1 | 3/3 |
| 5 | `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | R&B / Soul; 6m; raw | r=0.993 | 776 | [0.038, 0.0418] | 1 | 3/3 |


## Global BY survivors

[Full summary CSV](multiple_testing.csv)

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `lyric_semantic_prior_hit_reference_n` | `US_CHILD_POPULATION_SHARE` | Pop; 12m; raw | r=-0.951 | 66 | [-332, -240] | 2.51e-05 | 3/3 |
| 2 | `lyric_semantic_prior_hit_reference_n` | `US_CHILD_POPULATION_SHARE` | Pop; 24m; raw | r=-0.951 | 65 | [-328, -235] | 2.91e-05 | 3/3 |
| 3 | `lyric_semantic_prior_hit_reference_n` | `US_CHILD_POPULATION_SHARE` | overall; 12m; raw | r=-0.951 | 66 | [-333, -240] | 2.51e-05 | 3/3 |
| 4 | `lyric_semantic_prior_hit_reference_n` | `US_CHILD_POPULATION_SHARE` | overall; 24m; raw | r=-0.951 | 65 | [-329, -235] | 2.91e-05 | 3/3 |
| 5 | `lyric_semantic_prior_hit_reference_n` | `US_CHILD_POPULATION_SHARE` | overall; 6m; raw | r=-0.95 | 66 | [-336, -241] | 2.51e-05 | 3/3 |


## Corrected lyrical leads and the influence caveat

The [complete 178-row adjusted lyrical table](adjusted_lyrical_corrected_leads.csv) separates content/structure constructs from the published source’s provenance/quality fields. The following rows are ordered by successful chronological transfer, then the existing corrected ranking. They are candidates for **robustness checks and independent replication**, not presently defensible substantive discoveries. Even the rows with three positive transfer folds rely on highly concentrated exposure variation; for example, some claims-series relationships have only about one effective exposure block despite hundreds of observed months.

| # | Music measure | External series | Population; lag | Effect | Native N | Slope 95% HAC interval | Best global BY q | Stable folds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| 1 | `lyric_pos_other_share` | `US_CONTINUED_CLAIMS` | Pop; 24m; adjusted | r=0.243 | 692 | [2.32e-11, 2.89e-11] | 0.000179 | 3/3 |
| 2 | `emotion_caring` | `US_INITIAL_CLAIMS` | R&B / Soul; 6m; adjusted | r=-0.167 | 650 | [-3.63e-08, -2.9e-08] | 0.000601 | 3/3 |
| 3 | `emotion_caring` | `US_UNEMPLOYMENT` | R&B / Soul; 6m; adjusted | r=-0.154 | 756 | [-0.00817, -0.0055] | 0.0199 | 3/3 |
| 4 | `emotion_nervousness` | `US_NONFARM_EMPLOYMENT` | Pop; 0m; adjusted | r=-0.135 | 817 | [-0.00143, -0.000902] | 0.0446 | 3/3 |
| 5 | `detox_insult` | `US_CONTINUED_CLAIMS` | R&B / Soul; 6m; adjusted | r=0.13 | 650 | [5.56e-09, 7.65e-09] | 0.01 | 3/3 |
| 6 | `lyric_mtld` | `US_CONTINUED_CLAIMS` | R&B / Soul; 6m; adjusted | r=0.095 | 650 | [4.83e-07, 6.28e-07] | 0.0021 | 3/3 |
| 7 | `emotion_anger` | `US_NONFARM_EMPLOYMENT` | Pop; 3m; adjusted | r=-0.0854 | 817 | [-0.00135, -0.000909] | 0.0129 | 3/3 |
| 8 | `emotion_anger` | `US_NONFARM_EMPLOYMENT_MOM` | Pop; 3m; adjusted | r=-0.0843 | 817 | [-0.00143, -0.000928] | 0.0286 | 3/3 |


The [influence diagnostics](corrected_influence_diagnostics.csv) cover every corrected numeric method. The [complete corrected table](corrected_relationships_complete.csv) includes all 712 rows, source-informed measurement roles, effective-block diagnostics and the actual rejecting method. The original pipeline role is retained beside the source-informed role in the [measurement-role crosswalk](measurement_role_crosswalk.csv). `lyric_semantic_prior_hit_reference_n`, which dominates the strongest raw list, is explicitly defined by the source dictionary as the number of earlier Top-10 identities in a reference centroid; it is not a semantic-content score.

## Associations attenuated by adjustment

[Top 200 matched attenuations](disappeared_after_adjustment.csv) give the exact raw and adjusted rows, lags, sample sizes and q values. These compare the same declared pair while the estimand changes from levels to adjusted native-period changes. They do not identify the cause of attenuation.

| Music measure | External series | Population; lag | Raw r | Adjusted r |
| --- | --- | --- | ---: | ---: |
| `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | Country; 1m | 0.993 | 0.001 |
| `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | Country; 12m | 0.993 | 0.001 |
| `lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | R&B / Soul; 6m | 0.992 | -0.000 |
| `lyric_semantic_prior_hit_reference_n` | `US_REAL_GDP` | Hip-Hop / Rap; 1m | 0.992 | -0.001 |
| `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | Pop; 0m | 0.993 | 0.002 |
| `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | overall; 1m | 0.993 | 0.002 |
| `lyric_semantic_prior_hit_reference_n` | `US_IP_UTILITIES` | Country; 6m | 0.991 | 0.001 |
| `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | Country; 0m | 0.993 | 0.003 |
| `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | overall; 0m | 0.993 | -0.004 |
| `lyric_semantic_prior_hit_reference_n` | `US_NONFARM_EMPLOYMENT` | Pop; 3m | 0.993 | 0.004 |

## Weighting and fixed-composition comparisons

The [weighting sensitivity](weighting_sensitivity.csv) summarizes the already fitted equal-period and distinct chart-song-count weighted estimates. These are descriptive comparisons; no extra weighting p-values enter the global family. The weighting uses chart population counts, not the feature-specific count of observed lyrics.

| Population | Track | Comparable numeric rows | Median absolute change in r | 95th percentile absolute change | Sign changes with both absolute r > 0.01 |
| --- | --- | ---: | ---: | ---: | ---: |
| overall | raw | 375,756 | 0.0000 | 0.0001 | 0 |
| within_genre | raw | 1,140,941 | 0.0294 | 0.1392 | 55,661 |
| overall | adjusted | 217,009 | 0.0000 | 0.0001 | 0 |
| within_genre | adjusted | 1,097,911 | 0.0097 | 0.0427 | 22,157 |

The [fixed/matched composition comparison](composition_comparison.csv) lists the 200 largest saved correlation differences on the identical supported-genre/month cohort. The original overall estimate is shown separately because it may use more months or genres. Adjusted fixed and matched fits also differ in nuisance-control profiles, so their difference is not a pure weighting effect.

| Track | Planned numeric feature/external/lag comparisons | Both fixed/matched estimable | Original + fixed + matched estimable |
| --- | ---: | ---: | ---: |
| adjusted | 129,024 | 0 | 0 |
| raw | 129,024 | 57,310 | 57,310 |

Strict complete-genre coverage and the six-block support rule limit these comparisons. Missing supported genres are not reweighted away to create a longer series. The within-genre rankings and original overall fits remain available when a fixed-composition counterpart is unsupported.

## Null findings and coverage limits

**1,519,346** inference-supported pair/track rows did not meet either global BY threshold. This is a lack of corrected evidence for these specific tests, not proof that their effects are zero. The much larger set of unsupported rows is a coverage/assumption limitation and must not be described as a scientific null. The domain table above states which populations supplied actual inferential support.

The 16-genre [coverage figure](figures/genre_adjusted.svg) and [best-estimate table](genre_best_adjusted.csv) retain genres with insufficient supported history explicitly. Audio and metadata measures have uneven coverage; missing lyrics and classifier scores are not random across history. Five observed songs in a feature-month is a measurement support floor, not proof of population representativeness. Counts, coverage and release/edition metadata can track source collection practices.

The leading between-genre adjusted coefficient concerns Afrobeats share and life expectancy (12-month reference lag), with r≈−0.776 across 64 annual units and q=1. The underlying genre share is nonzero in only 38 of 818 months. Known zero shares are not missing observations, but 64 annual rows do not establish 64 years of active Afrobeats coverage. This is an explicitly unsupported substantive lead, not evidence that life expectancy caused genre change.

Raw trend correlations can be striking even when adjusted estimates are small. ADF screening uses each series’ broader available history, not a guarantee for each pair’s overlap. HAC and BY depend on valid individual-model assumptions; the strong-AR null simulation still had 7.35% nominal rejection at a 5% threshold, despite passing the declared development tolerance and having 1.875% corrected all-null world rejection. Confidence intervals are marginal, not simultaneous across the full campaign.

Annual/quarterly context uses its native sample size; categories use term/event support. Positive lags refer to source reference periods and cannot recover unavailable original publication vintages. September 2026 is incomplete. Genre and content classifiers are uncertain modern measurements of historical music. None of these tables estimates a causal effect of economic conditions, politics or COVID.

## Validation and resources

The [validation record](validation.json) checks complete work-unit coverage, unchanged restart chunks, numerically deterministic replays with recorded floating-point tolerances, complete ranking membership and independent global BY calculation. The [integrity record](integrity_validation.json) records unchanged original data/previous analyses and the repository test suite. Actual cumulative active computation is in [resource_ledger.json](resource_ledger.json); measured process memory and output sizes are in [execution_resources.json](execution_resources.json). The [benchmark](benchmark.json) authorized execution within the four-hour/15 GB limits.

## Next steps; no further campaign executed

No adjusted lyrical relationship in this run clears both the broad-variation diagnostic and two positive chronological folds. A nonlinear campaign is therefore not justified by these results alone. The caring/unemployment or claims, insult/continued-claims, and linguistic-structure/claims rows above are concrete candidates for a **separately approved robustness/replication protocol**: examine leverage, independent episodes, stronger finite-sample uncertainty and measurement coverage before conditional or nonlinear modelling. Treat related lags/transforms as the same substantive lead, not independent replications. Strong raw-only effects and sparse genres do not justify a nonlinear search.

Every substantive lead requires independent replication: genuinely future observations under a locked protocol, a separately sampled chart population, or independently measured lyrical constructs. Reusing the repeatedly inspected 2018-onward data does not provide untouched confirmation. Additional as-of publication vintages would improve forecasting claims; broader historical audio, missing-lyric coverage and independently validated classifier measurements would address different measurement limits. More data should be chosen to address a documented limitation, not simply to manufacture a significant result.

No nonlinear, interaction, clustering, multivariate search or additional acquisition was launched.
