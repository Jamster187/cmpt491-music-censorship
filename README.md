# CMPT 491 — Popular Music Content Analysis

We study lyrical characteristics and genre differences in mainstream Billboard music
from 1958–2026. The final datasets and exploratory descriptive analyses are complete.
Formal COVID breakpoint/significance analysis has **not** been performed; descriptive
changes do not establish causation.

## Repository guide

| Start here | Location |
|---|---|
| Final downloadable datasets | [data/public/](data/public/README.md) |
| Milestone 2 statistics and figures | [analysis/milestone2/](analysis/milestone2/README.md) |
| Moving averages and preferred all-genres charts | [analysis/moving_averages/](analysis/moving_averages/README.md) |
| Methodology and technical documentation | [docs/](docs/README.md) |
| Reproducible code and commands | [src/](src/README.md) |
| Final audits and production evidence | [reports/](reports/README.md) |
| Superseded experiments and historical reports | [archive/](archive/README.md) |
| Regression tests | [tests/](tests/) |

For a quick tour, see [repository structure](docs/repository_structure.md).

## Download the data

**Start with the monthly dataset.** Each row is an observation in the final available
Billboard chart of a calendar month. Chart dates are not release dates.

| Download | Rows | Columns | Unit |
|---|---:|---:|---|
| [master_monthly.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_monthly.csv) | 81,797 | 78 | Song-month observation; 818 snapshots, 28,041 identities |
| [songs.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/songs.csv) | 28,041 | 70 | Exact title + artist identity |
| [master_weekly.csv.xz](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_weekly.csv.xz) | 355,487 | 77 | Song-week observation; lossless XZ |

See the [data guide](data/public/README.md), [column/type reference](docs/dataset/columns.md)
and [release manifest](data/public/manifest.json) for schemas, missingness, provenance
and decompression. Legacy v2 exports remain clearly labelled historical inputs in
`data/public/`; they are retained because the frozen release validator checks them.

## What is measured?

The supplied chart snapshot comes from the reported upstream
[Billboard archive](https://github.com/mhollingshead/billboard-hot-100).
MusicBrainz metadata and a primary genre are linked to the 28,041 study identities.
Usable lyrics exist privately for 20,981 songs; 20,979 have all 42 model scores.
The scores are four LyricLens, seven Detoxify, 28 GoEmotions and three sentiment
measurements. They remain separate dimensions, with no composite hardness score.

Missing scores are blank, not zero. Genres and scores are model-derived, not ground
truth. Songs recur across chart months; the analysis guides explain weighting and
coverage rules. Lyrics, databases, model environments, checkpoints and credentials
are not distributed. Source anomalies and unsuccessful matches remain documented.

## Reproduce the existing analyses

Install the existing dependencies from `requirements.txt`, then run from the root:

```bash
python3 src/descriptive_analysis.py
python3 src/moving_average_analysis.py
python3 src/moving_average_all_genres.py
python3 -m unittest discover -s tests -v
```

These commands use public data/saved time series and perform no acquisition or model
inference. For the offline dataset builder/validator and retained private prerequisites,
see the [command guide](docs/commands.md). Do not run historical acquisition or model
commands just to view or rebuild the analyses.
