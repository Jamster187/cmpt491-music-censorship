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

- [songs.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/songs.csv)
- [monthly_top100.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/monthly_top100.csv)
- [Dataset guide](data/public/README.md)

`songs.csv` contains our song information and `monthly_top100.csv` contains the monthly Top 100 rankings. They can be joined using `song_id`.

## What's next?

Our next step is to run the lyrics through a classifier that gives each song numerical scores for its content.

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
