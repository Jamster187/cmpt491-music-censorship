# Downloadable music enrichment v2

New additive version; original datasets remain unchanged. Files are compressed CSVs readable with `pandas.read_csv(path)`.

| File | Purpose |
|---|---|
| [songs.csv.xz](songs.csv.xz) | 28,041 song identities, exact original fields, frozen V1 features and new numeric/categorical metadata |
| [song_missingness.csv.xz](song_missingness.csv.xz) | Explicit missing indicator for every added field |
| [monthly_overall.csv.xz](monthly_overall.csv.xz) | 818 month-level means/counts; equal available source rows |
| [monthly_by_genre.csv.xz](monthly_by_genre.csv.xz) | 7,173 observed genre-month units; same weighting |
| [chart_period_features.csv.xz](chart_period_features.csv.xz) | 355,487 exact original chart/source locations plus three availability-gated chart measures |
| [manifest.json](manifest.json) | Input, code and artifact SHA-256 fingerprints |

Definitions, licenses, model limitations, grouping rules and reproduction are in the [report](../../../analysis/music_enrichment_v2/README.md). Missing is not zero. Do not treat retrospective metadata as predebut information. No lyrics, audio, embeddings, credentials or private caches are distributed.
