# Dataset columns and variable types

The names below match the final CSV headers. “Yes” means the column exists; cells can still be missing. Song-level fields repeat across observations.

| Group | Column(s) | Type | Weekly | Monthly | Description |
|---|---|---|---|---|---|
| Time | `chart_date` | Temporal | Yes | No | Weekly chart date |
| Time | `month`, `snapshot_chart_date` | Temporal | No | Yes | Calendar month and selected chart date |
| Billboard | `weekly_rank` | Discrete quantitative (ordinal) | Yes | No | Original Hot 100 position; 1 is highest |
| Billboard | `monthly_rank` | Discrete quantitative (ordinal) | No | Yes | Original rank on the month's selected chart |
| Billboard | `reported_last_week_rank`, `reported_peak_position` | Discrete quantitative (ordinal) | Yes | Yes | Source-reported previous rank and peak position |
| Billboard | `reported_weeks_on_chart` | Discrete quantitative | Yes | Yes | Source-reported cumulative weeks |
| Source | `source_chart_index`, `source_row_index` | Identifier | Yes | Yes | Zero-based source locations; together identify an observation |
| Song | `song_id` | Identifier | Yes | Yes | Stable exact-identity join key, not an analytical category |
| Song | `title`, `artist` | Categorical | Yes | Yes | Original Billboard title and full artist credit |
| Population | `in_final_study_population` | Binary | Yes | Yes | 1 = final study population; 0 = outside it |
| History | `first_chart_date`, `last_chart_date` | Temporal | Yes | Yes | First/last observed dates over the full weekly history |
| History | `best_chart_rank` | Discrete quantitative (ordinal) | Yes | Yes | Best rank over the full history |
| History | `weekly_observation_count`, `chart_weeks` | Discrete quantitative | Yes | Yes | Source-row count and distinct chart-date count, respectively |
| History | `total_chart_points` | Discrete quantitative | Yes | Yes | Whole-history sum of 101 − rank; not a content score |
| Membership | `first_snapshot_month`, `last_snapshot_month` | Temporal | Yes | Yes | First/last month-end membership |
| Membership | `snapshot_months_selected` | Discrete quantitative | Yes | Yes | Number of selected months containing the song |
| Metadata | `musicbrainz_match_status` | Categorical | Yes | Yes | Match disposition, including uncertain/unmatched cases |
| Metadata | `mb_earliest_release_date` | Temporal | Yes | Yes | Earliest reported date among matched releases; may be partial or a reissue |
| Metadata | `mb_release_date_precision` | Categorical | Yes | Yes | Year, month or day precision |
| Metadata | `mb_release_title` | Categorical | Yes | Yes | Selected MusicBrainz release title; not necessarily an original album |
| Metadata | `mb_duration_median_seconds`, `mb_duration_min_seconds`, `mb_duration_max_seconds` | Continuous quantitative | Yes | Yes | Median/minimum/maximum distinct matched recording lengths, in seconds |
| Metadata | `mb_recording_count`, `mb_release_count`, `mb_distinct_duration_count` | Discrete quantitative | Yes | Yes | Counts of matched recordings, releases and distinct durations |
| Genre | `primary_genre` | Categorical | Yes | Yes | One primary label from the 16-category taxonomy |
| Genre | `genre_confidence` | Categorical | Yes | Yes | High, medium or low model confidence |
| Genre | `secondary_genres` | Categorical | Yes | Yes | Provisional labels stored as a JSON array; `[]` means none |
| Lyrics | `lyrics_available` | Binary | Yes | Yes | 1 = usable lyrics; 0 = unsuccessful; blank outside the study population |
| Lyrics | `lyrics_status` | Categorical | Yes | Yes | Acquisition disposition, such as `success`, `quarantined` or `not_found` |
| LyricLens | `ll_sexual_content` | Continuous quantitative | Yes | Yes | Sexual-content score |
| LyricLens | `ll_violence` | Continuous quantitative | Yes | Yes | Violence score |
| LyricLens | `ll_explicit_language` | Continuous quantitative | Yes | Yes | Explicit-language score |
| LyricLens | `ll_substance_use` | Continuous quantitative | Yes | Yes | Substance-use score |
| Detoxify | `detox_toxicity`, `detox_severe_toxicity` | Continuous quantitative | Yes | Yes | Separate toxicity and severe-toxicity scores |
| Detoxify | `detox_obscene`, `detox_sexual_explicit` | Continuous quantitative | Yes | Yes | Separate obscene-language and sexual-explicitness scores |
| Detoxify | `detox_threat`, `detox_insult`, `detox_identity_attack` | Continuous quantitative | Yes | Yes | Separate threat, insult and identity-attack scores |
| GoEmotions | `emotion_*` | Continuous quantitative | Yes | Yes | 28 separate emotion scores, listed below |
| Sentiment | `sentiment_negative`, `sentiment_neutral`, `sentiment_positive` | Continuous quantitative | Yes | Yes | Separate negative, neutral and positive sentiment scores |

The 28 `emotion_*` suffixes are: admiration, amusement, anger, annoyance, approval, caring, confusion, curiosity, desire, disappointment, disapproval, disgust, embarrassment, excitement, fear, gratitude, grief, joy, love, nervousness, optimism, pride, realization, relief, remorse, sadness, surprise and neutral.

All 42 model scores are in [0,1]. Blank cells mean missing, not zero. Whole-history summaries describe the song, not the current week/month; do not sum their repeated values across observations.

See [complete schema, provenance and decompression documentation](../../data/public/README.md) for further details.
