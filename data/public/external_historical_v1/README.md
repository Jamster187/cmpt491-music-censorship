# Public external historical data v1

This release contains 56,469 source and derived observations cleared for redistribution in this campaign. Restricted source values are excluded; coverage and reproduction details remain documented. [Full report](../../../analysis/external_historical/README.md).

| File | Meaning |
|---|---|
| [observations.csv.xz](observations.csv.xz) | Long native-frequency observations, units, dates, source URLs, hashes, licenses, transformations |
| [month_overall.csv.xz](month_overall.csv.xz) | Monthly original music-score summaries and monthly external columns |
| [month_genre.csv.xz](month_genre.csv.xz) | Genre-specific monthly summaries |
| [quarter_overall.csv.xz](quarter_overall.csv.xz), [quarter_genre.csv.xz](quarter_genre.csv.xz) | Natural quarterly views; incomplete music periods flagged |
| [year_overall.csv.xz](year_overall.csv.xz), [year_genre.csv.xz](year_genre.csv.xz) | Natural annual views |
| [asof_monthly_releases.csv.xz](asof_monthly_releases.csv.xz) | Only documented historical-release values strictly before chart cutoffs |
| [release_context_keys.csv.xz](release_context_keys.csv.xz) | Uncertain release candidates and explicit month-join eligibility |
| [chart_context_keys.csv.xz](chart_context_keys.csv.xz) | All original weekly chart/source locations |
| [manifest.json](manifest.json) | Artifact/input/code hashes and license selection |

Use the documented query command for selected chart/release context; do not duplicate all external columns into the song master. Dates refer to chart observation or explicit external measurement periods, never automatically lyric-writing dates.
