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

MusicBrainz metadata enrichment and the first lyrics acquisition pass are complete.
All 25,363 study assets have a lyrics disposition; 19,372 have usable local text.
Once the remaining data-quality decisions are settled,
we plan to run lyrics through a classifier to produce quantitative measurements
of song content for comparison across songs and years.

The final analysis will compare historical trends and rates of change with the
post-COVID period to see whether there is evidence of an unusual change. The
project is still in progress, and we do not have results yet.

Current status:

- Lyrics exclusion audit: [diagnostic findings and recovery scenarios](reports/lyrics_exclusion_audit.md), [scope and validation](docs/lyrics_exclusion_audit.md). Corpus unchanged; a separately validated second pass is recommended before freezing it.

- Lyrics completion: [final coverage and integrity](reports/lyrics_completion_audit.md), [fix, provenance and validation record](docs/lyrics_completion.md). The remaining 3,717 assets were dispositioned and the unified lyrics manifest synchronized. The [earlier post-run audit](reports/post_run_audit.md) remains a historical checkpoint.

- Billboard dataset processing: complete
- Weekly/monthly populations: [local build and report](docs/analysis_populations.md) complete
- Unified research database: [build and schema](docs/research_database.md)
- Metadata enrichment: first pass complete; [actual coverage](reports/post_run_audit.md). Raw provider tags remain separate from any future genre taxonomy; earlier pilots preserved.
- Lyrics: first acquisition pass complete, 19,372/25,363 usable (76.38%). Reviewed pilot retained (171/200 usable); [production matcher safety check](reports/lyrics_production_pilot.md), [full acquisition status](reports/lyrics_production_status.md), and [storage/resume instructions](docs/lyrics_production.md)
- Classification: not started
- Final analysis: not started

The Billboard data comes from
[mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100).
