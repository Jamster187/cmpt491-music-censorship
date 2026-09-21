# CMPT 491 - Popular Music Content Analysis

For our CMPT 491 project, we want to see how the content of popular music has changed over time. We are especially interested in whether music changed unusually after COVID compared to the trends that already existed before it.

## Dataset

We started with the weekly Billboard Hot 100 from 1958–2026:

- 3,555 weekly charts
- 355,487 chart entries
- 32,723 unique song + artist combinations

Source: https://github.com/mhollingshead/billboard-hot-100

We used the weekly charts to create a list of the **100 most popular songs for each month**. This gives us:

- 818 months
- 81,800 song/month observations
- 25,363 unique songs

We kept the weekly data too, so we can eventually look at changes either week-by-week or month-by-month.

## Extra data

The original Billboard dataset did not have many columns, so we added more information using MusicBrainz. This includes things like:

- Release date
- Song duration
- Album/release information

We were able to confidently match 20,450 of our 25,363 songs.

We also collected usable lyrics for **19,372 songs**.

## Download

If you just want to use the dataset, download [master_dataset.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_dataset.csv). It contains one row per song per month, with the monthly Billboard data and available song metadata already joined together.

[songs.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/songs.csv) and [monthly_top100.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/monthly_top100.csv) are also available separately for anyone who prefers the normalized tables. The [dataset guide](data/public/README.md) explains the columns and rebuild commands. No lyric text or classifier scores are included.

## What's next?

We have prepared a [four-model classifier panel](reports/classifier_production_readiness.md): LyricLens, Detoxify, GoEmotions and Cardiff sentiment. It preserves separate content, emotion and sentiment scores, without combining them into one hardness score. The production runner is tested on the same 200-song sample; the full corpus has not been classified. [Run and resume instructions](docs/classifier_production.md) are available for the next step.

We can then track these scores from 1958–2026 and ask:

- Has popular music been getting harder or softer over time?
- How quickly does music normally change?
- Did something unusual happen to that trend around or after COVID?

## Status

- [x] Billboard data
- [x] Monthly Top 100
- [x] Extra song information
- [x] Lyrics
- [ ] Classify song content
- [ ] Analyze changes over time
