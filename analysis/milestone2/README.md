# Milestone 2 — descriptive statistics

Open [descriptive_findings.md](descriptive_findings.md) first: it is a factual cheat
sheet with results, limitations, question mapping and eight suggested figures.

| Folder/file | Use |
|---|---|
| [tables/summary_statistics.csv](tables/summary_statistics.csv) | Observation-weighted numerical summaries |
| [tables/song_level_summary_statistics.csv](tables/song_level_summary_statistics.csv) | One row per song before summarization |
| [tables/](tables/) | All 12 tables: categories, artists, genres, correlations, missingness and annual summaries |
| [figures/](figures/) | 27 default distribution, comparison, relationship and historical figures, plus distribution references |
| [manifest.json](manifest.json) | Input/code hashes, methods, versions and output hashes |

From the repository root:

```bash
python3 src/descriptive_analysis.py
```

Input: `data/public/master_monthly.csv`. Repeated song-month observations and unique
songs answer different descriptive questions; both weightings are identified.
Missing values are not zero, and outliers remain included. Detailed unchanged
methods are in [the methods guide](../../docs/methodology/descriptive_analysis.md).

Presentation-only rebuild: `python3 src/figure_audit.py`. This reads saved annual and
availability tables and the unchanged public population, without rewriting any table.
Skewed histograms retain their original bins and add log-density panels. Central
score-box views disclose out-of-view counts and link to full-scale references.
Near-zero genre boxes use a labeled symlog axis with a linear companion; all outliers
remain plotted. See the [figure audit](../figure_audit.md) for exact rules.
