# CMPT 491: Popular Music Over Time

This is a CMPT 491 Data Mining project looking at how the content of popular music
has changed over time. We are particularly interested in whether the trajectory
changed significantly in the post-COVID period, compared with the changes seen
over previous decades.

We are using weekly Billboard Hot 100 charts from 1958–2026 to identify popular
songs and establish a long-term historical baseline. The processed dataset
currently contains **355,487 chart observations** representing **32,723 unique
song/artist pairs**. A chart observation is one song's appearance on a weekly
chart, so a song can appear many times in the data.

Next, we plan to add metadata such as genre and eventually collect lyrics for
the songs. We will run the lyrics through a classifier to produce quantitative
measurements of song content. These measurements will give us a way to compare
content across songs and years.

The final analysis will compare historical trends and rates of change with the
post-COVID period to see whether there is evidence of an unusual change. The
project is still in progress, and we do not have results yet.

Current status:

- Billboard dataset processing: complete
- Metadata/genre enrichment: next
- Lyrics/classification: not started
- Final analysis: not started

The Billboard data comes from
[mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100).
