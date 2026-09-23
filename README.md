# CMPT 491 - Popular Music Content Analysis

This CMPT 491 Data Mining project studies changes in mainstream popular music from 1958–2026: lyrical characteristics, genre differences, historical rates of change, and unusual changes in levels or slopes around/post COVID. Differences would not establish that COVID caused them.

**Dataset construction is complete. Our next phase is exploratory data analysis; historical/COVID analysis has not started.**

## Billboard foundation

We started with the [weekly Billboard Hot 100 archive](https://github.com/mhollingshead/billboard-hot-100), covering August 1958 through September 2026:

- **3,555** weekly charts
- **355,487** song-week observations
- **32,723** unique title + artist combinations

Each exact Billboard title + artist combination defines a `song_id`.

## Weekly and monthly snapshots

**Weekly:** each Billboard Hot 100 chart is one snapshot.

**Monthly:** the final available Billboard chart in each calendar month is the monthly snapshot.

Both use the same definition of popularity. Monthly samples the weekly series less frequently and keeps the selected chart’s ranks.

The final monthly study population contains **818 snapshots, 81,797 song-month observations and 28,041 unique songs**. Three historical snapshots contain 99 rather than 100 songs because rank 100 is absent from the source. We preserve those gaps rather than invent records. Chart dates are not release dates.

## Metadata and lyrics

Billboard had relatively few variables, so we enriched the 28,041 study songs.

### MusicBrainz

MusicBrainz adds release dates, durations and album/release information: **22,290 / 28,041 high-confidence matches**.

### Lyrics

We collected usable lyrics locally for **20,981 / 28,041 songs**:

- **74.82%** overall coverage
- **81.33%** for 2015–2019
- **80.59%** for 2020–2026

These period groups use first Billboard appearance, not release dates. Lyrics are copyrighted research inputs and are **not distributed through GitHub**.

## Four content classifiers

Songs with usable lyrics were processed through four pretrained models, producing **42 numerical content features**. Long lyrics are processed in chunks so the complete lyric is represented.

### LyricLens

Designed specifically for song lyrics, with four measurements covering sexual content, violence, explicit language and substance use.

### Detoxify Unbiased

Provides seven toxicity/offensiveness measurements. It was trained on online comments rather than lyrics, so its scores are model-derived features, not objective ground truth.

### GoEmotions

Provides 28 emotion measurements; the full list appears below.

### Cardiff multilingual sentiment

Provides negative, neutral and positive sentiment. Its multilingual design is useful because Billboard songs are not exclusively English.

We preserve all 42 features without an arbitrary “hardness” score, so analysis can examine which characteristics change and move together.

**20,979 songs have all 42 features.** Two songs lack only the four LyricLens outputs; their other 38 features remain populated. Songs without usable lyrics have missing classifier values, not zeros.

## Genre

Genre assignment is complete: **28,041 / 28,041 study songs** have a model-derived primary genre.

GPT-5.5 with medium reasoning uses a frozen structured prompt containing title, artist, first-chart-date context and available genre/tag evidence.

The fixed taxonomy is:

Pop; Rock; Hip-Hop / Rap; R&B / Soul; Country; Latin; Electronic / Dance; Alternative / Indie; Metal; Folk / Singer-Songwriter; Jazz / Blues; Reggae / Dancehall; Gospel / Christian; K-Pop; Afrobeats / African Pop; Other.

Confidence: **18,621 high, 7,538 medium and 1,882 low**. These model-derived classifications are not objective ground truth.

## Download the data

**Start with `master_monthly.csv`.** Use the weekly file for higher-frequency analysis.

| Direct download | Rows | Columns | Contents |
|---|---:|---:|---|
| [master_monthly.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_monthly.csv) | 81,797 | 78 | One row per song in each month-end snapshot; recommended starting point |
| [songs.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/songs.csv) | 28,041 | 70 | One row per study song, with metadata, genre and classifier features |
| [master_weekly.csv.xz](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_weekly.csv.xz) | 355,487 | 77 | One row per weekly chart observation |

The weekly download is losslessly compressed: about **15 MB**, expanding to a roughly **350 MB CSV**. Both master tables use the same song-level columns. Weekly includes identities outside the enriched study population; `in_final_study_population` identifies which rows belong to it. Outside-population enrichment is blank.

## Dataset columns

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

See [complete schema, provenance and decompression documentation](data/public/README.md) for further details.

## Final dataset SITREP

**Dataset construction is complete.** “Complete” means the planned work finished, not that every song has available metadata or lyrics.

| Component | Status |
|---|---|
| Billboard weekly data | Complete |
| Weekly/monthly snapshot methodology | Complete |
| MusicBrainz enrichment | Complete |
| Lyrics acquisition | Complete |
| 42 lyrical-content features | Complete |
| Genre classification | Complete |
| Weekly master dataset | Complete |
| Monthly master dataset | Complete |
| Historical / genre analysis | Next |
| COVID slope/level analysis | Not started |

## Roadmap — where we are now

```text
Billboard → Weekly/monthly snapshots → Metadata + lyrics
    → 42 classifier features → Genre → Final master datasets
    ↓
WE ARE HERE: ready for exploratory data analysis
    ↓
Moving averages / genre comparisons
    ↓
Historical trend modelling
    ↓
Pre-COVID vs post-COVID level/slope comparison
```

Next we will visualize the 42 features through time, create weekly/monthly moving averages, compare genre-specific trajectories, and examine relationships and correlations between classifier outputs. We will establish historical baselines before testing whether post-COVID levels or slopes differ unusually from earlier trends. There are no analysis results yet.

## Methodological caution

Content measurements and genres are model-derived, not ground truth. Lyrics coverage is incomplete, and missing lyrics are not perfectly random. Analysis must account for these limitations when comparing periods, genres and rates of change.
