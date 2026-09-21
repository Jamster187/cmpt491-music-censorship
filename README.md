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

**Population update under review:** the new definition uses the last available
weekly chart in each month. Its [candidate comparison](reports/month_end_population_comparison.md)
contains 28,041 songs and 81,797 observations (three source charts lack rank 100).
The downloads below still use the previous aggregated-month definition. No public
files have been replaced.

## Extra data

The original Billboard dataset did not have many columns, so we added more information using MusicBrainz. This includes things like:

- Release date
- Song duration
- Album/release information

We were able to confidently match 20,450 of our 25,363 songs.

We also collected usable lyrics for **19,372 songs**.

## Download

If you just want to use the dataset, download [master_dataset.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_dataset.csv). It contains one row per song per month, with the monthly Billboard data, available song metadata and 42 classifier features already joined together.

[songs.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/songs.csv) and [monthly_top100.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/monthly_top100.csv) are also available separately for anyone who prefers the normalized tables. The [dataset guide](data/public/README.md) explains the columns and rebuild commands. Lyrics text is not distributed.

## Content features

We ran four classifiers on the **19,372 songs with usable lyrics**:

- **LyricLens:** four lyrical-content dimensions—sexual content, violence, explicit language and substance use.
- **Detoxify:** seven toxicity/offensiveness-related features.
- **GoEmotions:** 28 emotion features.
- **Cardiff:** three sentiment features.

These are 42 **model-derived numerical features**, not ground-truth measurements. Each model processes the whole normalized song in chunks; we retain a token-weighted mean of its chunk scores. We have not combined the models into an overall hardness score.

Two songs lack the four LyricLens values because their text becomes empty under its preprocessing. Their other 38 features are retained. Songs without usable lyrics have blank classifier values. Blank means missing, not zero; no monthly observations were dropped.

## What's next?

The classifier dataset is complete with this documented model-specific missingness. Next, we can plan how to examine the historical trajectory and whether the post-COVID period departs unusually from it. That analysis has not started, and any eventual association would not establish that COVID caused a change.

## Status

- [x] Billboard data
- [x] Monthly Top 100
- [x] Extra song information
- [x] Lyrics
- [x] Classify song content (two documented LyricLens exceptions)
- [ ] Analyze changes over time
