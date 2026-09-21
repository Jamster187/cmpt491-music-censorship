# Public research dataset — classifier features v2.0

The acquisition phase is frozen. These UTF-8 CSVs describe the constructed study
population, including songs without usable lyrics. No lyric text, excerpts,
provider response caches or private paths are included. The master now includes
42 model-derived numerical features from the completed four-model classifier panel.

## Downloads and joins

**Start with [master_dataset.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_dataset.csv)**
if you want one analysis-ready file. Its 81,800 rows each represent one song in
one monthly Top-100 basket. Monthly data and available song metadata are already
joined using `song_id`, along with the classifier features; you do not need to
join the tables yourself.

| File | Data rows | Meaning |
|---|---:|---|
| [master_dataset.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_dataset.csv) | 81,800 | Recommended: monthly observations, song metadata and 42 classifier features |
| [songs.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/songs.csv) | 25,363 | One exact Billboard title + artist identity per study song |
| [monthly_top100.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/monthly_top100.csv) | 81,800 | One song in one monthly Top-100 basket |
| [manifest.json](manifest.json) | — | Version, byte sizes, SHA-256 checksums, source fingerprints, and column lists |

The separate normalized tables remain unchanged. The master is a LEFT JOIN of
`monthly_top100.csv` to `songs.csv` on `song_id`, with exactly one song match per
monthly row, followed by a left join to the separate classifier results on the
same key. It contains all eight monthly columns followed by the 23 song
columns other than the shared `song_id`, followed by 42 classifier columns:
**73 columns total**. The original 31 columns retain their values and order.
Missing metadata stays blank. A song's metadata repeats when it appears in
multiple months; those are distinct observations and should not be deduplicated.
Song-history totals describe the whole song, so summing those repeated totals
would count the same song more than once.

If using the separate tables, join them on `song_id` (one-to-many). The monthly key is
`(month, monthly_rank)`; `(month, song_id)` is also unique. There are 818 baskets
of 100 songs. Do not flatten monthly and weekly observations together: that
would multiply observations. CSV row counts exclude headers.

## Song columns

Billboard titles and artist credits retain their original spelling and punctuation.
A credit can name several performers; it is not a normalized artist identity.
All chart-history summaries cover the song's entire supplied weekly history,
including weeks outside its selected monthly baskets.

| Columns | Variable type | Origin and meaning |
|---|---|---|
| `song_id` | Identifier | Deterministic project ID from exact original title + artist; not an analytical category |
| `title`, `artist` | Descriptive text labels | Billboard title and full credited artist string |
| `first_chart_date`, `last_chart_date` | Temporal | Derived earliest/latest observed Billboard dates; not release dates |
| `best_chart_rank` | Discrete, ordinal | Lowest observed Billboard rank; 1 is highest |
| `weekly_observation_count` | Discrete quantitative | Number of original weekly rows, retaining source duplicates |
| `chart_weeks` | Discrete quantitative | Number of distinct chart dates |
| `total_chart_points` | Discrete quantitative | Sum of `101 - rank` over all original weekly rows |
| `first_selected_month`, `last_selected_month` | Temporal | Earliest/latest monthly basket membership, `YYYY-MM` |
| `months_selected` | Discrete quantitative | Number of monthly Top-100 baskets containing this song |
| `musicbrainz_match_status` | Categorical | Project matching decision: `high_confidence`, `ambiguous`, `not_found`, or `error` |
| `mb_recording_count`, `mb_release_count` | Discrete quantitative | Distinct linked MusicBrainz recording/release IDs among accepted matches |
| `mb_earliest_release_date` | Temporal, possibly partial | Earliest reported date among linked releases; `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` |
| `mb_release_date_precision` | Categorical | `year`, `month`, or `day`; blank if no date |
| `mb_release_title` | Descriptive text label | Title of the selected linked release, not necessarily an original album |
| `mb_duration_median_seconds`, `mb_duration_min_seconds`, `mb_duration_max_seconds` | Continuous quantitative | Summaries of distinct positive recording lengths reported by MusicBrainz, in seconds |
| `mb_distinct_duration_count` | Discrete quantitative | Number of distinct lengths contributing to those summaries |
| `lyrics_status` | Categorical | Project LRCLIB disposition, defined below |
| `lyrics_available` | Binary categorical | `1` for usable local lyrics, `0` otherwise; not a numerical content measurement |

MusicBrainz summaries are populated only for high-confidence matches. Blanks mean
unavailable, not zero. Durations give each distinct observed length one vote;
they do not select a definitive recording. Multiple lengths can indicate versions
of different duration. Release dates can describe reissues or compilations.
Date/title come from the same selected release manifestation. Date-bearing
releases sort before undated releases; ties use date text, title, then ID.
Partial dates retain their precision (no imputed January 1). If all dates are
missing, the title is selected deterministically from undated releases.

`lyrics_status` counts: `success` 19,372; `quarantined` 3,519;
`wrong_identity` 1,365; `bad_missing_text` 184; `not_found` 872; `error` 51.
Every song was attempted. `success` means confidently matched, usable local text;
other statuses do not prove that lyrics cannot be obtained elsewhere. Neither
text nor local file locations are distributed. Overall usable coverage is 76.38%.

## Monthly columns

All columns below are derived by this project from Billboard observations,
except `song_id`, which is the shared identifier.

| Column | Variable type | Meaning |
|---|---|---|
| `month` | Temporal | Calendar month of chart dates, `YYYY-MM` |
| `monthly_rank` | Discrete, ordinal | Position 1–100 within the monthly basket |
| `song_id` | Identifier | Foreign key to `songs.csv` |
| `monthly_points` | Discrete quantitative | Sum of `101 - weekly rank` in the month |
| `weeks_present` | Discrete quantitative | Distinct chart dates in the month |
| `best_weekly_rank` | Discrete, ordinal | Lowest observed weekly rank that month |
| `average_weekly_rank` | Continuous quantitative | Arithmetic mean rank over contributing weekly rows |
| `weekly_observations` | Discrete quantitative | Contributing row count, including source duplicates |

Songs are ordered by points descending, best weekly rank ascending, average
weekly rank ascending, then `song_id`. The first 100 form each basket. See
[population construction](../../docs/analysis_populations.md) for details.
Coverage runs August 1958–September 2026; boundary months and 2026 are incomplete.
Availability favors higher-charting, longer-lasting songs and simpler artist
credits; inclusion in the study population does not depend on lyrics success.

## Classifier features and missing values

The panel was run on **19,372 songs with usable lyrics**. These are continuous,
model-derived numerical features in [0,1], not ground truth or calibrated severity
measurements. Each song is divided into complete, non-overlapping chunks using
each model's tokenizer, then summarized with a content-token-weighted mean.
LyricLens retains its original lossy English preprocessing. All three other
models retain their frozen preprocessing too. No overall hardness, CSI, MCR or
consensus score is included.

| Model | Features | What they describe |
|---|---:|---|
| LyricLens | 4 (`ll_`) | Sexual content, violence, explicit language and substance use |
| Detoxify Unbiased | 7 (`detox_`) | Toxicity/offensiveness-related signals learned from online comments |
| GoEmotions | 28 (`emotion_`) | Emotion signals, including neutral, learned from Reddit comments |
| Cardiff multilingual sentiment | 3 (`sentiment_`) | Negative, neutral and positive sentiment learned from tweets |

Models trained on comments/tweets may interpret lyrics differently from a human
reader. Similarly named outputs from different models should not be treated as
interchangeable. Their numerical values are preserved separately, without
rounding or cross-model combination. Song-level scores repeat across monthly
observations; repeated rows are not independent new model judgments.

**Blank CSV cells represent missing/NULL, never zero.** All 42 features are blank
for the 5,991 songs without usable lyrics (16,625 monthly observations). Classifier
data is available for 19,372 songs (65,175 observations). Of these, 19,370 songs
(65,173 observations) have all 42 features. Two songs have the other 38 features
but four missing LyricLens values:

- “Chinese Checkers” — Booker T. & The MG's
- “Snap Shot” — Slave

Their accepted reason is `unsupported/empty-after-LyricLens-normalization`.
Their text becomes empty under LyricLens preprocessing; it was not modified,
transliterated or replaced, and the unchanged inputs were not retried. This is
accepted model-specific missingness, not an unfinished acquisition/classification
phase. Their original database failure evidence is preserved. Stable IDs and
reasons are in the [accepted-missingness policy](../../docs/classifier_accepted_missingness.json)
and the manifest. No observations are dropped for missing features.

Exact feature columns, in export order:

- lyriclens: `ll_sexual_content`, `ll_violence`, `ll_explicit_language`, `ll_substance_use`
- detoxify: `detox_toxicity`, `detox_severe_toxicity`, `detox_obscene`, `detox_threat`, `detox_insult`, `detox_identity_attack`, `detox_sexual_explicit`
- goemotions: `emotion_admiration`, `emotion_amusement`, `emotion_anger`, `emotion_annoyance`, `emotion_approval`, `emotion_caring`, `emotion_confusion`, `emotion_curiosity`, `emotion_desire`, `emotion_disappointment`, `emotion_disapproval`, `emotion_disgust`, `emotion_embarrassment`, `emotion_excitement`, `emotion_fear`, `emotion_gratitude`, `emotion_grief`, `emotion_joy`, `emotion_love`, `emotion_nervousness`, `emotion_optimism`, `emotion_pride`, `emotion_realization`, `emotion_relief`, `emotion_remorse`, `emotion_sadness`, `emotion_surprise`, `emotion_neutral`
- cardiff: `sentiment_negative`, `sentiment_neutral`, `sentiment_positive`

The [frozen schema](../../docs/classifier_production_schema.json) records model/checkpoint
versions and label mapping. The manifest records classifier/configuration hashes
and the accepted exceptions.

## Provenance and weekly data

The supplied Billboard snapshot is attributed to
[mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100).
It contains 3,555 charts and 355,487 observations, spanning 1958-08-04 through
2026-09-19. This attribution is not independent verification of the archive.
Its original upstream commit is unknown; the local source hash is in the manifest.

On September 20, 2026, the upstream repository had no license file or explicit
reuse grant (reviewed HEAD `add8fea6d16f9024bb5c3f664245beb0e9263fce`, not the
proven commit of our supplied snapshot). We therefore do **not** publish a new
`weekly_hot100.csv` mirror. The existing supplied raw snapshot remains unchanged
in the repository. The public tables are constructed song/monthly summaries;
we do not claim a blanket license for third-party Billboard material.

MusicBrainz factual release/recording fields are
[core data under CC0](https://musicbrainz.org/doc/About/Data_License).
Supplementary tags, ratings, annotations, and raw evidence are not exported.
Matching decisions, monthly baskets, and availability indicators are project
outputs. Lyrics remain copyrighted local research inputs.

To regenerate the full weekly table locally from the supplied source:

```bash
python3 src/phase1.py build
python3 src/populations.py
```

This produces ignored `data/processed/weekly_top100.csv` with all 355,487 weekly
observations, retaining source-row coordinates and stable `song_id` joins.
An inner join to public `songs.csv` selects 338,706 observations (95.28%);
the other 16,781 observations concern 7,360 identities outside this study.
The local Phase 1 `songs.csv` supplies the full 32,723-identity lookup.
Keep the supplied raw source read-only; replacing it with a newer upstream
snapshot would produce a different dataset.

## Rebuild and validation

Public downloads work without private databases. Rebuilding this exact enriched
release requires both retained local databases: `data/processed/research.db` and
`data/processed/classifier_results.db`. These databases and acquisition evidence
are not distributed. Rebuilding exports does not rerun inference. A fresh chart-only database
cannot reproduce the frozen enrichment by itself. No acquisition is restarted.

```bash
python3 src/public_dataset.py build
python3 src/public_dataset.py validate
python3 src/research.py validate
python3 -m unittest discover -s tests -v
```

The exporter opens the database read-only, uses explicit column allowlists,
checks the frozen counts/dispositions and relational integrity, reconciles CSV
values to source projections, and compares two independently generated outputs
before publication. The original 31 master columns are built from those public CSVs; the final 42
are left-joined from validated classifier results by `song_id`. Every value is
reconciled against its source; duplicate song keys and missing joins fail validation.
It rejects private path/credential patterns and checks that
both source database hashes are unchanged. The accepted-missingness policy
allows only the two named LyricLens exceptions; additional failures stop publication. The manifest has no runtime timestamp,
so unchanged inputs and code produce identical bytes. The full-precision master is larger than the earlier acquisition-only file. Its
exact size is recorded in the manifest. It is distributed directly through Git
and the raw download link, below GitHub's 100 MiB per-file limit; GitHub warns
above 50 MiB. We retain full numerical precision rather than rounding scores to
reduce size. The exporter caps this reviewed master at 95 MiB and other CSVs at
25 MiB. No Git LFS or private model/database files are needed for downloads.
See [GitHub's file-size documentation](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

Future features require an explicit reviewed schema/version change. The exporter
never copies arbitrary classifier or acquisition fields.
