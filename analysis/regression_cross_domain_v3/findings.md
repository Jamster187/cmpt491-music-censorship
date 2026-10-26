# Cross-domain discovery V3: completed exploratory findings

The complete campaign evaluated **40,884,781 valid target/combination pairs** across **123 supported numerical targets** and **129 predictor constructs**, including all 57 new constructs. Three historical validations plus final evaluation produced **163,539,124 OLS fits**. Two of 125 meaningful numerical target candidates lacked historical support.

Full search elapsed time was **40.91 minutes**, with peak process RSS **1.167 GiB**. This excludes the separately recorded audit, benchmark, reporting and independent validation. All combinations and all negative results remain in the local hierarchy.

## What the primary view says

Of 123 primary selected target models, **34** have positive R² in all three validation periods and in evaluation; **50** have positive evaluation R². These are descriptive stability counts, not multiplicity-adjusted discoveries. Winners were fixed using validation only, including winners that fail evaluation.

The primary view requires different substantive domains and disjoint recorded measurement-source sets. It does not establish statistical independence or causality. Models use a selected, retrospectively enriched population; target-specific sample sizes differ. The evaluation period was inspected in earlier campaigns.

## Top 15 unrestricted valid relationships

| Target | Predictors | Category¹ | Validation R² | Evaluation R² | Worst historical R² | Evaluation MAE | Evaluation RMSE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| debut_rank | debut_reported_peak_position + ll_explicit_language + mb_release_count | 2 | 1.000 | 0.996 | 1.000 | 0.138 | 1.892 | 2573 |
| debut_rank | debut_chart_same_genre_share + debut_reported_peak_position + ll_explicit_language | 2 | 1.000 | 0.996 | 1.000 | 0.139 | 1.892 | 2573 |
| debut_rank | debut_reported_peak_position + ll_explicit_language + song_title_token_count | 2 | 1.000 | 0.996 | 1.000 | 0.138 | 1.892 | 2573 |
| debut_rank | debut_reported_peak_position + ll_explicit_language + top10_26 | 2 | 1.000 | 0.996 | 1.000 | 0.138 | 1.892 | 2573 |
| debut_rank | debut_reported_peak_position + ll_explicit_language + top10_12 | 2 | 1.000 | 0.996 | 1.000 | 0.138 | 1.892 | 2573 |
| debut_rank | debut_reported_peak_position + ll_explicit_language + song_title_prior_usage_count | 2 | 1.000 | 0.996 | 1.000 | 0.139 | 1.892 | 2573 |
| debut_rank | credit_prior_best_rank + debut_reported_peak_position + ll_explicit_language | 2 | 1.000 | 0.996 | 1.000 | 0.139 | 1.892 | 2573 |
| debut_rank | credit_prior_genre_diversity + debut_reported_peak_position + ll_explicit_language | 2 | 1.000 | 0.996 | 1.000 | 0.138 | 1.892 | 2573 |
| debut_rank | credit_prior_top10_song_count + debut_reported_peak_position + ll_explicit_language | 2 | 1.000 | 0.996 | 1.000 | 0.139 | 1.892 | 2573 |
| debut_rank | debut_reported_peak_position + ll_explicit_language + sentiment_positive | 2 | 1.000 | 0.996 | 1.000 | 0.138 | 1.892 | 2573 |
| debut_rank | chart_weeks_12 + debut_reported_peak_position + ll_explicit_language | 2 | 1.000 | 0.996 | 1.000 | 0.139 | 1.892 | 2573 |
| debut_rank | credit_recent_chart_presence + debut_reported_peak_position + ll_explicit_language | 2 | 1.000 | 0.996 | 1.000 | 0.138 | 1.892 | 2573 |
| debut_rank | debut_reported_peak_position + ll_explicit_language + lyric_content_distance_recent_chart | 2 | 1.000 | 0.996 | 1.000 | 0.138 | 1.892 | 2573 |
| debut_rank | debut_reported_peak_position + ll_explicit_language + ll_violence | 2 | 1.000 | 0.996 | 1.000 | 0.139 | 1.892 | 2573 |
| debut_rank | debut_reported_peak_position + ll_explicit_language + lyric_first_person_singular_share | 2 | 1.000 | 0.996 | 1.000 | 0.138 | 1.892 | 2573 |

These are the actual global top combinations by validation R². Repeated targets and closely related variants are retained; they are not 15 independent discoveries. The CSV includes measurement independence, likely confounding, possible reverse direction, substantive-surprise assessment, baseline improvements and period metrics.

The near-perfect debut-rank relationships are substantively trivial: source-reported peak on the first observation almost copies observed debut rank. These are distinct source fields with 106 disagreements among 20,508 enriched identities, so they are not a universal exact mathematical duplicate. They remain category B in the unrestricted audit and are excluded from both cross-domain views. The [near-duplicate audit](near_duplicate_audit.csv) records each historical population; no source values are repaired.

## Top 15 cross-domain relationships

| Target | Predictors | Category¹ | Validation R² | Evaluation R² | Worst historical R² | Evaluation MAE | Evaluation RMSE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lyric_vocabulary_size | primary_genre + prior_year_unique_chart_song_count + secondary_genres | 5 | 0.546 | 0.292 | 0.435 | 43.835 | 61.010 | 2573 |
| lyric_vocabulary_size | previous_chart_incumbent_age_median + primary_genre + secondary_genres | 5 | 0.537 | 0.364 | 0.405 | 39.694 | 57.831 | 2573 |
| lyric_vocabulary_size | debut_time_years + primary_genre + secondary_genres | 5 | 0.522 | 0.366 | 0.355 | 40.490 | 57.702 | 2573 |
| lyric_vocabulary_size | last_chart_date + primary_genre + secondary_genres | 5 | 0.520 | 0.337 | 0.407 | 41.670 | 59.044 | 2573 |
| lyric_vocabulary_size | artist_credit_feature_marker + primary_genre + prior_year_unique_chart_song_count | 5 | 0.519 | 0.234 | 0.406 | 45.301 | 63.437 | 2573 |
| lyric_vocabulary_size | mb_release_year + primary_genre + secondary_genres | 5 | 0.517 | 0.366 | 0.367 | 40.060 | 57.740 | 2573 |
| lyric_vocabulary_size | previous_chart_new_entry_count + primary_genre + secondary_genres | 5 | 0.516 | 0.318 | 0.409 | 42.249 | 59.867 | 2573 |
| lyric_vocabulary_size | previous_chart_turnover_share + primary_genre + secondary_genres | 5 | 0.515 | 0.290 | 0.405 | 43.534 | 61.094 | 2573 |
| lyric_vocabulary_size | mb_release_year + primary_genre + prior_year_unique_chart_song_count | 5 | 0.514 | 0.313 | 0.382 | 41.399 | 60.078 | 2573 |
| lyric_vocabulary_size | credited_artist_entity_count + primary_genre + prior_year_unique_chart_song_count | 5 | 0.513 | 0.257 | 0.392 | 44.810 | 62.484 | 2573 |
| lyric_vocabulary_size | previous_chart_incumbent_age_median + primary_genre + prior_year_unique_chart_song_count | 5 | 0.513 | 0.287 | 0.383 | 42.530 | 61.226 | 2573 |
| lyric_vocabulary_size | artist_credit_feature_marker + previous_chart_incumbent_age_median + primary_genre | 5 | 0.511 | 0.343 | 0.373 | 40.015 | 58.762 | 2573 |
| lyric_vocabulary_size | last_chart_date + primary_genre + prior_year_unique_chart_song_count | 5 | 0.511 | 0.293 | 0.388 | 42.951 | 60.966 | 2573 |
| lyric_vocabulary_size | debut_reported_peak_position + primary_genre + prior_year_unique_chart_song_count | 5 | 0.509 | 0.264 | 0.378 | 44.420 | 62.186 | 2573 |
| lyric_vocabulary_size | debut_rank + primary_genre + prior_year_unique_chart_song_count | 5 | 0.509 | 0.264 | 0.378 | 44.413 | 62.180 | 2573 |

These are the actual global top combinations by validation R². Repeated targets and closely related variants are retained; they are not 15 independent discoveries. The CSV includes measurement independence, likely confounding, possible reverse direction, substantive-surprise assessment, baseline improvements and period metrics.

## Top 15 strictly provenance-separated (primary) relationships

| Target | Predictors | Category¹ | Validation R² | Evaluation R² | Worst historical R² | Evaluation MAE | Evaluation RMSE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lyric_vocabulary_size | primary_genre + prior_year_unique_chart_song_count + secondary_genres | 5 | 0.546 | 0.292 | 0.435 | 43.835 | 61.010 | 2573 |
| lyric_vocabulary_size | previous_chart_incumbent_age_median + primary_genre + secondary_genres | 5 | 0.537 | 0.364 | 0.405 | 39.694 | 57.831 | 2573 |
| lyric_vocabulary_size | debut_time_years + primary_genre + secondary_genres | 5 | 0.522 | 0.366 | 0.355 | 40.490 | 57.702 | 2573 |
| lyric_vocabulary_size | last_chart_date + primary_genre + secondary_genres | 5 | 0.520 | 0.337 | 0.407 | 41.670 | 59.044 | 2573 |
| lyric_vocabulary_size | artist_credit_feature_marker + primary_genre + prior_year_unique_chart_song_count | 5 | 0.519 | 0.234 | 0.406 | 45.301 | 63.437 | 2573 |
| lyric_vocabulary_size | mb_release_year + primary_genre + secondary_genres | 5 | 0.517 | 0.366 | 0.367 | 40.060 | 57.740 | 2573 |
| lyric_vocabulary_size | previous_chart_new_entry_count + primary_genre + secondary_genres | 5 | 0.516 | 0.318 | 0.409 | 42.249 | 59.867 | 2573 |
| lyric_vocabulary_size | previous_chart_turnover_share + primary_genre + secondary_genres | 5 | 0.515 | 0.290 | 0.405 | 43.534 | 61.094 | 2573 |
| lyric_vocabulary_size | mb_release_year + primary_genre + prior_year_unique_chart_song_count | 5 | 0.514 | 0.313 | 0.382 | 41.399 | 60.078 | 2573 |
| lyric_vocabulary_size | credited_artist_entity_count + primary_genre + prior_year_unique_chart_song_count | 5 | 0.513 | 0.257 | 0.392 | 44.810 | 62.484 | 2573 |
| lyric_vocabulary_size | previous_chart_incumbent_age_median + primary_genre + prior_year_unique_chart_song_count | 5 | 0.513 | 0.287 | 0.383 | 42.530 | 61.226 | 2573 |
| lyric_vocabulary_size | artist_credit_feature_marker + previous_chart_incumbent_age_median + primary_genre | 5 | 0.511 | 0.343 | 0.373 | 40.015 | 58.762 | 2573 |
| lyric_vocabulary_size | last_chart_date + primary_genre + prior_year_unique_chart_song_count | 5 | 0.511 | 0.293 | 0.388 | 42.951 | 60.966 | 2573 |
| lyric_vocabulary_size | debut_reported_peak_position + primary_genre + prior_year_unique_chart_song_count | 5 | 0.509 | 0.264 | 0.378 | 44.420 | 62.186 | 2573 |
| lyric_vocabulary_size | debut_rank + primary_genre + prior_year_unique_chart_song_count | 5 | 0.509 | 0.264 | 0.378 | 44.413 | 62.180 | 2573 |

These are the actual global top combinations by validation R². Repeated targets and closely related variants are retained; they are not 15 independent discoveries. The CSV includes measurement independence, likely confounding, possible reverse direction, substantive-surprise assessment, baseline improvements and period metrics.

¹ Category codes: 2 = same family (B), 3 = conceptual overlap (C), 4 = distinct domains with shared recorded sources (D), 5 = distinct domains and disjoint recorded sources (E). A dependencies are excluded from all valid selections.

## Target predictability hierarchy

Most predictable primary targets, ranked by validation:

| Target | Best predictors | Validation R² | Evaluation R² | Positive every period |
| --- | --- | --- | --- | --- |
| lyric_vocabulary_size | primary_genre + prior_year_unique_chart_song_count + secondary_genres | 0.546 | 0.292 | True |
| lyric_word_count | previous_chart_incumbent_age_median + primary_genre + secondary_genres | 0.459 | 0.249 | True |
| ll_explicit_language | debut_time_years + primary_genre + secondary_genres | 0.362 | 0.340 | True |
| detox_toxicity | debut_time_years + primary_genre + secondary_genres | 0.232 | 0.424 | True |
| detox_obscene | debut_time_years + primary_genre + secondary_genres | 0.231 | 0.408 | True |
| lyric_repeated_bigram_share | debut_time_years + primary_genre + secondary_genres | 0.191 | 0.024 | True |
| ll_sexual_content | debut_time_years + primary_genre + secondary_genres | 0.189 | 0.267 | True |
| detox_insult | debut_chart_same_genre_share + primary_genre + secondary_genres | 0.184 | 0.332 | True |
| lyric_mattr | mb_duration_min_seconds + primary_genre + secondary_genres | 0.183 | 0.022 | True |
| ll_substance_use | debut_time_years + primary_genre + secondary_genres | 0.167 | 0.178 | True |

Least predictable primary targets, also ranked by validation:

| Target | Best predictors | Validation R² | Evaluation R² |
| --- | --- | --- | --- |
| last_chart_date | detox_obscene + lyric_word_count + mb_duration_min_seconds | -377.974 | -629.694 |
| debut_time_years | detox_obscene + lyric_word_count + mb_duration_min_seconds | -77.263 | -165.704 |
| prior_year_unique_chart_song_count | credited_artist_entity_count + mb_duration_median_seconds + mb_release_year | -11.523 | -23.301 |
| mb_release_year | artist_credit_feature_marker + lyric_word_count + previous_chart_incumbent_age_median | -10.246 | -15.977 |
| credit_team_prior_song_count | emotion_caring + ll_explicit_language + lyric_vocabulary_size | -4.130 | -0.057 |
| previous_chart_incumbent_age_median | credited_artist_entity_count + lyric_word_count + mb_release_year | -0.944 | -1.563 |
| previous_chart_new_entry_count | lyric_compression_ratio + lyric_vocabulary_size + mb_duration_min_seconds | -0.777 | -0.423 |
| previous_chart_turnover_share | lyric_compression_ratio + lyric_vocabulary_size + mb_duration_median_seconds | -0.729 | -0.845 |
| prior_year_primary_genre_share | ll_sexual_content + lyric_repeated_line_share + lyric_vocabulary_size | -0.503 | -0.099 |
| debut_chart_same_genre_share | ll_sexual_content + lyric_repeated_line_share + lyric_vocabulary_size | -0.495 | -0.174 |

Every one-, two-, three-predictor and overall winner is in [best-by-count](best_by_predictor_count.csv) and [target leaderboard](target_leaderboard.csv), with all views/configurations. The complete locally stored candidate hierarchies are documented in the README.

## New information and the classifier baseline

The strongest primary lyrical-target winners by validation are shown below, including evaluation failures. This focuses attention on musical measurements while retaining the global catalog/calendar results above.

| Lyrical target | Separate-domain predictors | Validation R² | Evaluation R² | Positive every period |
| --- | --- | --- | --- | --- |
| lyric_vocabulary_size | primary_genre + prior_year_unique_chart_song_count + secondary_genres | 0.546 | 0.292 | True |
| lyric_word_count | previous_chart_incumbent_age_median + primary_genre + secondary_genres | 0.459 | 0.249 | True |
| ll_explicit_language | debut_time_years + primary_genre + secondary_genres | 0.362 | 0.340 | True |
| detox_toxicity | debut_time_years + primary_genre + secondary_genres | 0.232 | 0.424 | True |
| detox_obscene | debut_time_years + primary_genre + secondary_genres | 0.231 | 0.408 | True |
| lyric_repeated_bigram_share | debut_time_years + primary_genre + secondary_genres | 0.191 | 0.024 | True |
| ll_sexual_content | debut_time_years + primary_genre + secondary_genres | 0.189 | 0.267 | True |
| detox_insult | debut_chart_same_genre_share + primary_genre + secondary_genres | 0.184 | 0.332 | True |
| lyric_mattr | mb_duration_min_seconds + primary_genre + secondary_genres | 0.183 | 0.022 | True |
| ll_substance_use | debut_time_years + primary_genre + secondary_genres | 0.167 | 0.178 | True |
| lyric_compression_ratio | debut_time_years + primary_genre + secondary_genres | 0.167 | -0.158 | False |
| detox_identity_attack | artist_credit_feature_marker + primary_genre + secondary_genres | 0.150 | 0.260 | False |

Across all 58 lyrical targets, 30 fixed primary winners have positive R² in every historical validation period and evaluation. This is exploratory stability, not confirmation of novelty.

- New versus original: 123 comparable primary targets; 29 validation improvements, 41 evaluation improvements, and 19 improvements in both. Median evaluation ΔR² = -0.0269.
- Combined versus original: 123 comparable primary targets; 87 validation improvements, 48 evaluation improvements, and 48 improvements in both. Median evaluation ΔR² = 0.0000.
- New versus classifier only: 59 comparable primary targets; 51 validation improvements, 31 evaluation improvements, and 28 improvements in both. Median evaluation ΔR² = 0.0005.
- Combined versus classifier only: 59 comparable primary targets; 59 validation improvements, 39 evaluation improvements, and 39 improvements in both. Median evaluation ΔR² = 0.0185.

Classifier-only comparisons are unavailable for lyric-derived targets in the primary view because the classifiers share lyric provenance. An unavailable comparator is not a failed model. Original-only also contains pre-existing nonclassifier metadata and commercial measurements, so the two baselines answer different questions.

Largest primary combined-versus-original validation gains (evaluation retained regardless of outcome):

| Target | Combined predictors | Validation ΔR² | Evaluation ΔR² | RMSE reduction |
| --- | --- | --- | --- | --- |
| last_chart_date | detox_obscene + lyric_word_count + mb_duration_min_seconds | 50.656 | 4.366 | 35.735 |
| mb_release_year | artist_credit_feature_marker + lyric_word_count + previous_chart_incumbent_age_median | 23.553 | 1.005 | 0.748 |
| debut_time_years | detox_obscene + lyric_word_count + mb_duration_min_seconds | 9.720 | -10.769 | -0.997 |
| credit_team_prior_song_count | emotion_caring + ll_explicit_language + lyric_vocabulary_size | 0.344 | 0.003 | 0.002 |
| previous_chart_incumbent_age_median | credited_artist_entity_count + lyric_word_count + mb_release_year | 0.106 | -0.027 | -0.016 |
| previous_chart_turnover_share | lyric_compression_ratio + lyric_vocabulary_size + mb_duration_median_seconds | 0.103 | -0.074 | -0.002 |
| mb_distinct_duration_count | debut_time_years + lyric_mattr + prior_year_unique_chart_song_count | 0.081 | -1.169 | -1.267 |
| prior_year_unique_chart_song_count | credited_artist_entity_count + mb_duration_median_seconds + mb_release_year | 0.078 | 0.050 | 0.334 |
| mb_duration_median_seconds | chart_weekday + lyric_compression_ratio + lyric_repeated_bigram_share | 0.066 | 0.083 | 1.465 |
| duration_seconds | credit_prior_reentry_song_share + lyric_compression_ratio + lyric_repeated_bigram_share | 0.066 | 0.069 | 1.185 |
| credit_recent_chart_presence | credited_artist_entity_count + lyric_mattr + lyric_vocabulary_size | 0.060 | 0.138 | 1.074 |
| prior_year_primary_genre_share | ll_sexual_content + lyric_repeated_line_share + lyric_vocabulary_size | 0.057 | 0.024 | 0.002 |
| debut_chart_same_genre_share | ll_sexual_content + lyric_repeated_line_share + lyric_vocabulary_size | 0.049 | 0.018 | 0.001 |
| lyric_content_distance_prior_hits | credited_artist_entity_count + mb_duration_min_seconds + mb_release_year | 0.048 | 0.030 | 0.001 |
| credit_chart_career_days | credited_artist_entity_count + mb_distinct_duration_count + mb_duration_median_seconds | 0.042 | 0.077 | 98.273 |

Family occurrences are in [feature-family comparison](feature_family_comparison.csv). They describe the frozen winners across correlated targets; they are not causal importance estimates. Lyric structure cannot count as provenance-separated prediction of a classifier score because both use lyrics.

Combined versus original: 28/123 comparable targets have a positive lower bound for evaluation ΔR² under both clustering schemes. These fixed-prediction intervals exclude search uncertainty.
Combined versus classifier only: 31/59 comparable targets have a positive lower bound for evaluation ΔR² under both clustering schemes. These fixed-prediction intervals exclude search uncertainty.

Largest validation gains over the classifier-only baseline, with absolute performance:

| Target | Combined predictors | Combined validation R² | Combined evaluation R² | Classifier validation R² | Classifier evaluation R² |
| --- | --- | --- | --- | --- | --- |
| last_chart_date | detox_obscene + lyric_word_count + mb_duration_min_seconds | -377.974 | -629.694 | -477.025 | -583.614 |
| mb_release_year | artist_credit_feature_marker + lyric_word_count + previous_chart_incumbent_age_median | -10.246 | -15.977 | -54.259 | -18.277 |
| debut_time_years | detox_obscene + lyric_word_count + mb_duration_min_seconds | -77.263 | -165.704 | -95.251 | -143.738 |
| prior_year_unique_chart_song_count | credited_artist_entity_count + mb_duration_median_seconds + mb_release_year | -11.523 | -23.301 | -29.349 | -10.927 |
| previous_chart_incumbent_age_median | credited_artist_entity_count + lyric_word_count + mb_release_year | -0.944 | -1.563 | -6.937 | -0.587 |
| mb_recording_count | credit_days_since_last_entry + debut_time_years + lyric_mattr | 0.004 | -0.282 | -2.636 | -3.213 |
| mb_distinct_duration_count | debut_time_years + lyric_mattr + prior_year_unique_chart_song_count | -0.017 | -1.213 | -2.425 | -4.719 |
| credit_prior_song_observed_longevity_median | detox_obscene + lyric_word_count + mb_release_year | -0.127 | -1.166 | -0.793 | -0.370 |
| observed_lifetime_chart_weeks | lyric_word_count + mb_release_count + mb_release_year | 0.012 | -0.167 | -0.392 | -0.060 |
| previous_chart_new_entry_count | lyric_compression_ratio + lyric_vocabulary_size + mb_duration_min_seconds | -0.777 | -0.423 | -1.135 | -0.372 |

In the broader D/E cross-domain view, combined models improve validation for 81/123 targets and evaluation for 44/123. This view permits different substantive measurements from the same recorded source; chart-history/context associations can enter here but are not provenance-separated.

Largest D/E combined-versus-original validation gains:

| Target | Combined predictors | Validation ΔR² | Evaluation ΔR² |
| --- | --- | --- | --- |
| last_chart_date | artist_credit_feature_marker + lyric_content_distance_recent_chart + previous_chart_incumbent_age_median | 254.094 | 109.927 |
| debut_time_years | artist_credit_feature_marker + detox_obscene + previous_chart_incumbent_age_median | 44.655 | 23.078 |
| mb_release_year | lyric_word_count + mb_distinct_duration_count + previous_chart_incumbent_age_median | 23.741 | 2.036 |
| credit_team_prior_song_count | debut_time_years + prior_year_unique_chart_song_count + top10_26 | 1.124 | -0.011 |
| chart_weeks_12 | mb_distinct_duration_count + prior_year_unique_chart_song_count + same_credit_debut_cluster_size | 0.123 | 0.081 |
| duration_seconds | credit_prior_chart_weeks + primary_genre + prior_year_unique_chart_song_count | 0.096 | 0.232 |
| long_chart_26 | debut_time_years + mb_release_count + prior_year_unique_chart_song_count | 0.071 | 0.756 |
| mb_duration_median_seconds | chart_weekday + lyric_compression_ratio + lyric_repeated_bigram_share | 0.063 | -0.152 |
| credit_recent_chart_presence | artist_credit_feature_marker + primary_genre + prior_year_primary_genre_share | 0.054 | 0.055 |
| credited_artist_entity_count | credit_prior_chart_weeks + debut_time_years + first_credited_entity_prior_song_count | 0.053 | -0.335 |

New-feature families occurring in selected combined models (counts do not isolate a causal contribution):

| View | New family | Selected targets | Stable selected targets | New variable occurrences |
| --- | --- | --- | --- | --- |
| cross_domain | chart_context | 38 | 9 | 44 |
| cross_domain | artist_chart_history | 14 | 4 | 16 |
| cross_domain | credit_syntax | 13 | 5 | 13 |
| cross_domain | lyric_structure | 9 | 0 | 11 |
| cross_domain | calendar | 7 | 0 | 7 |
| cross_domain | genre_context | 6 | 3 | 6 |
| cross_domain | entity_history | 4 | 2 | 4 |
| cross_domain | collaboration_entities | 3 | 2 | 3 |
| cross_domain | content_reference | 3 | 0 | 3 |
| cross_domain | title_history | 3 | 1 | 3 |
| cross_domain | artist_genre_history | 1 | 0 | 1 |
| cross_domain | title_form | 1 | 1 | 1 |
| provenance_separated | lyric_structure | 43 | 3 | 55 |
| provenance_separated | chart_context | 22 | 8 | 24 |
| provenance_separated | collaboration_entities | 16 | 3 | 16 |
| provenance_separated | artist_chart_history | 13 | 2 | 15 |
| provenance_separated | credit_syntax | 6 | 1 | 6 |
| provenance_separated | genre_context | 4 | 2 | 4 |
| provenance_separated | calendar | 1 | 0 | 1 |

Two leading lexical targets show why additional features need separate evaluation: the word-count winner adds preceding-chart incumbent age to primary/secondary genre and reaches evaluation R² 0.249, an improvement of 0.087 over original-only. The vocabulary winner adds prior-year unique chart-song count to genre and reaches 0.292, a change of -0.075. The former gain and latter deterioration have the same direction under both paired clustering schemes. These associations may reflect chart-era and genre composition; they do not identify a causal effect of chart context.

The vocabulary association remains positive within debut years (diagnostic R² 0.390) and for unseen exact artist credits (0.252); explicit-language and toxicity predictions also remain positive in those diagnostics. This rules out neither genre composition nor learned annotation priors. Repeated-bigram and MATTR winners have only about 0.02 evaluation R² and become negative for unseen credits; their positive average stability should not be overstated.

The very large negative R² values for calendar targets reflect failed extrapolation into disjoint later date ranges with much smaller within-period variance. Large gains over another very poor model do not make these targets reliably predictable. Ordinary calendar-source proxies were intentionally removed from the strict view.

New-only winners with positive R² in every period where classifier-only evaluation R² is nonpositive are listed below. This is a post-evaluation annotation of already locked winners, not a model-selection rule. The improvements are modest; these cases do not establish independent, multiplicity-adjusted discoveries.

| View | Target | New-only predictors | Validation R² | Evaluation R² | Classifier evaluation R² |
| --- | --- | --- | --- | --- | --- |
| cross_domain | credit_chart_career_days | artist_credit_feature_marker + chart_weekday + previous_chart_credit_concentration | 0.070 | 0.013 | -0.022 |
| cross_domain | observed_lifetime_best_rank | credit_previous_entry_best_rank_so_far + credited_entities_prior_top10_mean + debut_chart_same_genre_share | 0.051 | 0.046 | -0.002 |
| cross_domain | best_rank_26 | credit_previous_entry_best_rank_so_far + credited_entities_prior_top10_mean + debut_chart_same_genre_share | 0.048 | 0.002 | -0.006 |
| cross_domain | best_rank_12 | credit_previous_entry_best_rank_so_far + credited_entities_prior_top10_mean + debut_chart_same_genre_share | 0.042 | 0.008 | -0.008 |
| cross_domain | chart_points_26 | lyric_vocabulary_size + lyric_word_count + prior_year_unique_chart_song_count | 0.039 | 0.010 | -0.108 |
| provenance_separated | credit_chart_career_days | credited_artist_entity_count + lyric_compression_ratio + lyric_mattr | 0.051 | 0.038 | -0.022 |

## Reliability, negative results and limitations

The full valid hierarchy retains **32,088,617** negative mean-validation-R² combinations and **32,708,210** negative evaluation-R² combinations. Negative values are never truncated or removed. **73** primary winners have nonpositive evaluation R².

Paired artist-credit and debut-year intervals use 499 fixed-prediction cluster resamples. They omit refitting and exhaustive-search uncertainty and do not correct for multiple comparisons. Exact credits leave unresolved aliases and collaboration overlap. Year resampling has few clusters. [Selected diagnostics](selected_diagnostics.csv) also report seen/unseen exact-credit performance and within-debut-year R²; the latter centers using actual evaluation outcomes and is not a deployable metric.

High unrestricted R² can reflect expected relationships among measurement families or retrospective commercial quantities. Calendar and linked-catalog relationships have limited intrinsic musical novelty. A genre-to-lyric association is plausible stylistically; disjoint recorded pipelines do not rule out learned genre-model knowledge. No leading relationship is labeled a novel causal discovery.

Other limitations include language/style and era confounding, selected enrichment coverage, target-specific missingness, imputation without availability indicators, imperfect linked recordings, provider catalog caps, unclipped OLS for binary targets, and uncertainty about original release dates. Observed-history labels use cutoff-specific maturity/inactivity rules but are not verified completed careers. All comparisons are exploratory.

## Reproduction and validation

See the [README](README.md), [methodology](methodology.md), [coverage](coverage.json), [runtime](execution.json), [benchmark](benchmark.json), and [figure manifest](figures/manifest.json). Complete coverage, independent full-row SVD replay, deterministic regeneration, checkpoint recovery and protected-source preservation are checked by `src/regression_cross_domain_validate.py`. Validation results are published only after those checks complete.
