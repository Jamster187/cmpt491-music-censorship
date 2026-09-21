# CMPT 491 - Popular Music Content Analysis

We are investigating how the content of mainstream popular music has changed over time, particularly whether the post-COVID period represents an unusual change relative to the historical trajectory.

## Data

We started with a complete weekly Billboard Hot 100 archive covering 1958–2026: **3,555 weekly charts, 355,487 song-week observations, and 32,723 unique Billboard title + artist identities**. Our supplied snapshot runs from August 4, 1958 to September 19, 2026.

The source is [mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100).

## Study population

We constructed monthly Top-100 baskets from the weekly charts, giving us **818 monthly periods, 81,800 song-month observations, and 25,363 unique songs**. Here, a song means an exact Billboard title and artist credit.

These songs account for approximately **95.3%** of the original weekly observations. The original weekly data remains preserved, so eventual analysis can use either weekly or monthly resolution.

## Enrichment and lyrics

MusicBrainz enrichment attempted all 25,363 study songs, producing **20,450 high-confidence matches (80.63%)**, with approximately 90% matching coverage in modern periods. Available information includes release dates, durations, album/release information, and external identifiers. Metadata is supplementary; it is not a requirement for content classification.

Lyrics acquisition is complete for this phase: all **25,363** songs were attempted, and **19,372** have confidently matched, usable lyrics. Coverage is **76.38% overall**, **82.81% for 2015–2019**, and **79.99% for 2020–2026**, grouping songs by their first Billboard appearance. Acquisition is now frozen, including unresolved cases.

Lyrics are copyrighted research inputs and are **not distributed in this repository**. They remain local, linked through `song_id`.

## Download the dataset

Download [songs.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/songs.csv) and [monthly_top100.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/monthly_top100.csv). The [dataset guide](data/public/README.md) explains their columns, joins, provenance, and rebuild commands. These tables contain no lyric text or classifier scores.

## Next step and research idea

We are investigating existing classifiers before deciding whether to build our own. The next phase is evaluating a classifier that converts lyrical content into continuous numerical measurements, such as explicitness or content severity.

We intend to establish the historical trajectory and rate of change from 1958 through the pre-COVID period, then test whether the post-COVID period shows an unusual change in level and/or trajectory. The classifier and longitudinal analysis have not started.

## Current status

- [x] Billboard data foundation — complete
- [x] Monthly study population — complete
- [x] Metadata enrichment — complete
- [x] Lyrics corpus — complete
- [ ] Content classifier — next
- [ ] Longitudinal/post-COVID analysis — not started
