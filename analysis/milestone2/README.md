# Milestone 2 — descriptive statistics

Open [descriptive_findings.md](descriptive_findings.md) first: it is a factual cheat
sheet with results, limitations, question mapping and eight suggested figures.

| Folder/file | Use |
|---|---|
| [tables/summary_statistics.csv](tables/summary_statistics.csv) | Observation-weighted numerical summaries |
| [tables/song_level_summary_statistics.csv](tables/song_level_summary_statistics.csv) | One row per song before summarization |
| [tables/](tables/) | All 12 tables: categories, artists, genres, correlations, missingness and annual summaries |
| [figures/](figures/) | 27 distribution, comparison, relationship and historical figures |
| [manifest.json](manifest.json) | Input/code hashes, methods, versions and output hashes |

From the repository root:

```bash
python3 src/descriptive_analysis.py
```

Input: `data/public/master_monthly.csv`. Repeated song-month observations and unique
songs answer different descriptive questions; both weightings are identified.
Missing values are not zero, and outliers remain included. Detailed unchanged
methods are in [the methods guide](../../docs/methodology/descriptive_analysis.md).
