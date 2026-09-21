# CMPT 491 - Popular Music Content Analysis

We are studying how the content of popular music changed from 1958–2026, especially whether trends changed unusually around or after COVID.

## Dataset

We started with the weekly Billboard Hot 100, covering August 1958 through September 2026:

- 3,555 weekly charts
- 355,487 song-week observations
- 32,723 unique title + artist combinations

Source: [Billboard Hot 100 archive](https://github.com/mhollingshead/billboard-hot-100).

## Time periods

**Weekly:** each Billboard Hot 100 chart is one weekly snapshot.

**Monthly:** the final available Billboard Hot 100 chart in each calendar month becomes that month's snapshot. Its chart ranks become the monthly ranks.

This lets us switch between weekly and monthly resolution while keeping the same definition of the Top 100. The month-end dataset contains:

- 818 months
- 81,797 song-month observations
- 28,041 unique songs

Three historical monthly snapshots contain 99 songs because rank 100 is missing from the original source. We preserve those gaps rather than invent records. September 2026 uses the latest available chart, dated September 19.

## Extra data

**MusicBrainz** adds release dates, durations, album/release information and other metadata where we can confidently match a song.

**Lyrics** are collected locally for content analysis. Copyrighted lyrics themselves are not published on GitHub.

Songs with usable lyrics are processed by four models:

- **LyricLens:** sexual content, violence, explicit language and substance use.
- **Detoxify:** toxicity/offensiveness-related measurements.
- **GoEmotions:** emotion measurements.
- **Cardiff sentiment:** positive, neutral and negative sentiment.

Together they produce 42 numerical content features. These are model-derived scores, not ground truth. Metadata, lyrics and classifier catch-up for the 3,654 newly introduced songs is still running; final coverage is not yet available.

## Genre

Genre is the next core dataset addition. We plan to assign songs to a broad, fixed genre taxonomy so we can compare content trends between genres over time.

## Download

The current [master_dataset.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_dataset.csv) is a **previous, temporary release** using the old monthly aggregation definition. It has metadata and classifier features already joined.

[songs.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/songs.csv) and [monthly_top100.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/monthly_top100.csv) are also available separately from that release.

A new month-end version will replace it after acquisition/classifier catch-up and genre work are completed.

## Research direction

Once the dataset is finished, we want to track content scores over time, compare genres and create weekly/monthly moving averages. We will establish pre-COVID historical trends, then examine whether levels or slopes change unusually around or after COVID. This would not establish that COVID caused a change.

## Status

- [x] Billboard data foundation
- [x] Weekly/monthly end-of-period methodology
- [ ] Month-end population metadata/lyrics/classifier catch-up — running
- [ ] Genre classification — next
- [ ] Final master dataset
- [ ] Historical/post-COVID analysis
