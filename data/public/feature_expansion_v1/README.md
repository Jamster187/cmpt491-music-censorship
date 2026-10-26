# Billboard debut features — version 1

This separate derived release contains 32,723 exact weekly song identities. It does not overwrite or redefine the existing final monthly study population of 28,041 identities. Join by `song_id`; title and full artist credit are unchanged.

| File | Unit and contents |
|---|---|
| [song_features.csv.xz](song_features.csv.xz) | One row per exact weekly identity; ID/title/artist/debut date/rank, 58 new columns, existing primary genre/42 scores/consistent duration |
| [song_outcomes.csv.xz](song_outcomes.csv.xz) | Separate 12/26-week targets, window ends, eligibility and descriptive observed lifetime fields; never predictors |
| [manifest.json](manifest.json) | File, source and pipeline hashes, coverage and input provenance references |

Use the [feature dictionary](../../../analysis/feature_expansion_v1/feature_dictionary.csv), [coverage](../../../analysis/feature_expansion_v1/coverage_report.csv), [protocol](../../../analysis/feature_expansion_v1/protocol.json), and [methodology](../../../analysis/feature_expansion_v1/methodology.md). CSV blanks are missing, not zero. Numeric engineered columns are stored as numbers; categorical `primary_genre` is the existing model label. `first_chart_date` and window ends are ISO dates. `eligible_12`/`eligible_26` are booleans. Identity is never inferred from normalized strings.

33 new columns are available at chart publication (category C). The other 25 are retrospective measurements (F), even where their intrinsic content existed earlier. Baseline `debut_rank` is known at publication; existing lyrics, genre and matched duration are retrospective. The strict forecast uses only debut rank and the 33 C columns. The retrospective track requires complete existing scores and usable lyrics, and includes modern metadata proxies. It is not a verified historical forecast.

`top10_H` means minimum rank <=10 within H weeks, `long_chart_H` means at least ceil(H/2) distinct chart dates, `best_rank_H` is the minimum rank, `chart_weeks_H` counts distinct dates, and `chart_points_H` sums 101-rank over every source row. Windows are [debut, debut + 7H days). `eligible_H` requires the source endpoint to reach that exclusive end. Top-10 classification further excludes debut ranks <=10. Descriptive observed lifetime totals may include later returns and remain right-censored.

Source: the project's supplied Billboard snapshot, reported upstream as [mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100). This records reported provenance, not independent verification. Private lyrics and acquisition databases are excluded. Original source observations, including 13 repeated song/date rows, remain unchanged; points preserve source rows while weeks count distinct dates.

Rebuilding requires the already-retained private inputs; viewing this release and replaying models do not. See the [campaign reproduction guide](../../../analysis/feature_expansion_v1/README.md).
