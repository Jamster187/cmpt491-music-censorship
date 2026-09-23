# Final weekly and month-end research datasets — v3.0

These analysis-ready tables preserve Billboard observations and attach the same
song-level metadata, genre labels and 42 content features at either resolution.
They include songs without usable lyrics. No lyric text, excerpts, model reasoning,
private file locations, credentials, caches or model checkpoints are distributed.
No historical/COVID analysis, moving averages or combined content score is included.

## Downloads

| File | Rows | Columns | Unit |
|---|---:|---:|---|
| [songs.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/songs.csv) | 28,041 | 70 | One exact title + artist identity in the final study population |
| [master_weekly.csv.xz](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_weekly.csv.xz) | 355,487 | 77 | One original observation on one weekly chart; decompress to `master_weekly.csv` |
| [master_monthly.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_monthly.csv) | 81,797 | 78 | One original observation on the final available chart in a month |
| [manifest.json](manifest.json) | — | — | Exact schemas, coverage, source/pipeline hashes, byte sizes and SHA-256 checksums |

The weekly CSV exceeds ordinary GitHub file limits. Its XZ download decompresses
byte-for-byte to the complete, full-precision `master_weekly.csv`. It is stored
in ordinary Git, without Git LFS. Monthly and song CSVs are published directly.
The [build report](../../reports/final_dataset_build.md) gives measured sizes and
coverage for each table. [GitHub documents its 100 MiB per-file limit](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

Python's standard library can decompress the weekly file without any packages:

```python
import lzma
import shutil

with lzma.open("master_weekly.csv.xz", "rb") as source:
    with open("master_weekly.csv", "wb") as output:
        shutil.copyfileobj(source, output)
```

Many analysis tools can read XZ directly; for example, pandas accepts
`pd.read_csv("master_weekly.csv.xz")` using extension-based compression detection.
Use the manifest's `csv_sha256` to verify decompressed bytes, and
`published_sha256` to verify the download. CSVs use UTF-8, comma delimiters, quoted
text where needed and LF line endings. Blank cells mean NULL/missing, never zero.

## Time and observation definitions

Weekly and monthly share an end-of-period snapshot concept: each actual Billboard
Hot 100 chart is a weekly snapshot, and monthly selects the latest available chart
in each calendar month. Monthly is lower-frequency sampling of the same charts;
there is no within-month averaging, points ranking or monthly reranking.

- Weekly: 3,555 charts, 355,487 source rows, 32,723 exact song identities.
- Monthly: 818 snapshots, 81,797 source rows, 28,041 exact song identities.
- The snapshots dated **1976-12-25, 1977-01-29 and 1977-02-26** have ranks 1–99:
  rank 100 is absent upstream. All other monthly snapshots contain ranks 1–100.
  No row is padded or replaced with an earlier chart.
- Coverage runs from 1958-08-04 through 2026-09-19. Boundary months and 2026 are
  incomplete; September's snapshot is the final *available* chart, September 19.
  Chart dates are not song release dates.

Original source anomalies are preserved. In particular, a repeated song/date pair
is not automatically an error to deduplicate. The stable row key for both tables
is `(source_chart_index, source_row_index)`, using zero-based locations in the
immutable supplied JSON. Weekly sorting is chart date, rank, then source location;
monthly sorting is month and rank. `songs.csv` sorts by exact `song_id`.

## Common song-level columns

All **70 columns of `songs.csv`** appear unchanged, with identical names and values,
in both master tables. Enrichment repeats for every observation of the same song;
this does not represent repeated independent model judgments. Song-history totals
must not be summed across repeated observations as if they were weekly measures.

| Fields | Meaning |
|---|---|
| `song_id` | Deterministic ID of the exact original Billboard title + full artist credit |
| `title`, `artist` | Exact original strings, including accents, punctuation, collaborations and versions |
| `first_chart_date`, `last_chart_date` | First/last observed Billboard dates over the complete weekly history |
| `best_chart_rank` | Minimum observed weekly rank over the complete history |
| `weekly_observation_count`, `chart_weeks` | Original row count (including duplicates) and distinct chart-date count |
| `total_chart_points` | Whole-history sum of `101 - rank`; an auxiliary Billboard history summary, never a content score or monthly selection rule |
| `first_snapshot_month`, `last_snapshot_month`, `snapshot_months_selected` | First/last month-end membership and distinct number of selected months; recomputed from the final snapshot definition |
| `in_final_study_population` | `1` for the final 28,041-song enriched universe, `0` otherwise |
| `musicbrainz_match_status` | `high_confidence`, `ambiguous`, `not_found`, `error`, or `outside_final_study_population` |
| `mb_recording_count`, `mb_release_count` | Distinct recording/release IDs among accepted links |
| `mb_earliest_release_date`, `mb_release_date_precision`, `mb_release_title` | Deterministically selected linked release manifestation and its date/precision |
| `mb_duration_median_seconds`, `mb_duration_min_seconds`, `mb_duration_max_seconds`, `mb_distinct_duration_count` | Summaries of distinct positive recording lengths |
| `lyrics_status`, `lyrics_available` | Acquisition disposition and usable-local-lyrics indicator; no lyric text |
| `primary_genre`, `genre_confidence`, `secondary_genres` | Frozen model assignment, qualitative confidence and JSON array of provisional secondary genres |
| 42 numerical features | The unchanged four-model panel, detailed below |

MusicBrainz factual fields are populated only for high-confidence matches:
**22,290 / 28,041** final-population songs. Uncertain matches retain their status
but have blank metadata. A missing date is not zero, and a partial date (`YYYY` or
`YYYY-MM`) is not expanded to an invented day. Date/title come from the same linked
release: date-bearing releases sort first, then date text, title and ID. The
selected release can be a reissue or compilation, not an original album or the
true earliest release. Distinct durations each receive one vote and may represent
multiple versions. Counts are not proof of definitive recording identity.

### Weekly population and enrichment coverage

The weekly table preserves **all 32,723 identities**. Filter
`in_final_study_population == 1` to restrict it to the same enriched universe as
`songs.csv` and the monthly table. The 4,682 other weekly identities are retained
with their Billboard identity and whole-history summaries. Their MusicBrainz and
lyrics statuses are `outside_final_study_population`; lyrics availability,
metadata, genre, snapshot membership summaries and all classifier values are blank.
This means outside the release's enrichment scope, not confirmed unavailable lyrics.
Some have older retained enrichment in the legacy release; this release does not
silently mix those assets into the approved final population.

The manifest and build report give exact observation-level coverage for metadata,
genre, any classifier features and all 42 features. Coverage denominators differ:
weekly uses all 355,487 source rows; monthly uses all 81,797 snapshot rows; songs
uses the 28,041 final identities. No row is removed to increase apparent coverage.

| Observation coverage | Weekly (355,487 rows) | Monthly (81,797 rows) |
|---|---:|---:|
| In final population / has primary genre | 347,995 | 81,797 |
| High-confidence MusicBrainz match | 287,951 | 67,510 |
| Has classifier data | 275,134 | 64,426 |
| Has all 42 features | 275,120 | 64,422 |
| Outside final population | 7,492 | 0 |

### Genre

All 28,041 final-population songs have one primary genre: **18,621 high**, **7,538
medium** and **1,882 low** confidence. Taxonomy:

Pop; Rock; Hip-Hop / Rap; R&B / Soul; Country; Latin; Electronic / Dance;
Alternative / Indie; Metal; Folk / Singer-Songwriter; Jazz / Blues;
Reggae / Dancehall; Gospel / Christian; K-Pop; Afrobeats / African Pop; Other.

Labels come from the frozen GPT-5.5 medium method, not the content classifiers.
Confidence is qualitative, not a calibrated probability. Secondary genres are
provisional suggestions; `[]` means the model supplied none. A blank secondary
cell occurs outside the final population. Parse nonblank values as JSON arrays,
not by splitting commas. Reasons and raw responses are excluded. The
[final genre audit](../../reports/genre_final_audit.md) documents the bounded review
and known limitations; its two clearly wrong sampled labels remain unchanged.

## Chart columns

| Weekly | Monthly | Meaning |
|---|---|---|
| `chart_date` | `snapshot_chart_date` | Actual date of the observed Billboard chart |
| — | `month` | Calendar month, `YYYY-MM` |
| `weekly_rank` | `monthly_rank` | Original Billboard `this_week` rank on that chart |
| `reported_last_week_rank` | Same | Original `last_week` value, including missing values |
| `reported_peak_position` | Same | Original reported peak; source inconsistencies are preserved |
| `reported_weeks_on_chart` | Same | Original reported cumulative weeks; not recomputed |
| `source_chart_index`, `source_row_index` | Same | Exact source row coordinates |

The legacy `monthly_points`, `weeks_present`, `average_weekly_rank` and other
within-month aggregation fields do not appear in these tables.

## Lyrics and classifier missingness

**20,981 / 28,041** final-population songs have usable lyrics and classifier data;
**20,979** have all 42 features. The remaining **7,060** have all features blank.
`lyrics_status=success` means usable confidently matched local text;
`quarantined`, `wrong_identity`, `bad_missing_text`, `not_found` and `error` retain
the distinct unsuccessful dispositions. `lyrics_available` is 1 for success, 0
for other final-population dispositions, and blank outside the final population.
Failures do not establish that lyrics cannot be obtained elsewhere.

Two songs retain only the four missing LyricLens values, with their other **38**
features populated:

- “Chinese Checkers” — Booker T. & The MG's
- “Snap Shot” — Slave

Their text becomes empty under frozen LyricLens normalization. This is documented
[accepted model-specific missingness](../../docs/classifier_accepted_missingness.json),
not pending inference. Lyrics and scores have not been modified, imputed or rerun.

| Model | Columns | Interpretation |
|---|---:|---|
| LyricLens | 4 (`ll_`) | Sexual content, violence, explicit language, substance use |
| Detoxify Unbiased | 7 (`detox_`) | Toxicity/offensiveness signals |
| GoEmotions | 28 (`emotion_`) | Emotion signals, including neutral |
| Cardiff multilingual sentiment | 3 (`sentiment_`) | Negative, neutral and positive sentiment |

All are separate model-derived continuous features in [0,1]. They are not
calibrated severity measures or interchangeable measures of the same construct.
Full lyrics were chunked under the frozen model-specific preprocessing and
summarized by content-token-weighted means. Scores retain full stored precision.
Models trained on comments/tweets have domain limitations when applied to lyrics.
There is no BART, hardness, consensus, CSI/MCR or cross-model combination.
The manifest lists all 42 exact column names in export order; the
[frozen schema](../../docs/classifier_production_schema.json) supplies model versions
and output mappings.

## Provenance and earlier releases

Billboard is the canonical chart-history authority. The supplied snapshot is
reported as originating from [mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100);
this is attribution, not independent archive verification. The upstream commit
for our snapshot is unknown. The manifest records its SHA-256. We do not claim a
blanket license over third-party Billboard material. MusicBrainz factual
release/recording fields are core metadata; supplementary tags, ratings,
annotations and raw evidence are not distributed. Lyrics remain private.

`master_dataset.csv` and `monthly_top100.csv` in this directory are preserved
**legacy aggregate-month v2 files**, not the current methodology. The matching
old `songs.csv`, manifest and documentation are archived under
[legacy_classifier_v2/](legacy_classifier_v2/). Historical documentation there
records old URLs and counts; do not join the old monthly files to current
`songs.csv`. The current entry points are the three downloads at the top.

## Rebuilding and validating

```bash
python3 src/final_dataset.py build
python3 src/final_dataset.py validate
python3 -m unittest discover -s tests -v
```

Both commands work offline. They require the retained immutable chart foundation,
research/acquisition stores, catch-up sidecars, genre results and audit manifests;
those private stores are not distributed. Exact reconstruction of enrichment is
not possible from a fresh chart-only database. Using the downloaded tables does
not require any private files or API access.

The builder stages outputs, checks exact source coordinates and song identities,
reconciles each CSV value to explicit public fields, validates classifier scores
against their saved chunks, compares independent serializations, and round-trips
compression before publishing. All frozen source databases and canonical lyric
files retain their hashes. The release manifest is replaced last. Validation
regenerates and compares every output, including the local uncompressed weekly
CSV. The legacy exporter refuses to overwrite the final release.

Earlier audit commands freeze the *previous* public-file hashes and remain
historical checks. Their public-file mismatch after this authorized release is
expected; use the final exporter validator for current outputs. The new validator
continues to enforce the private/source hashes from those frozen audits.
