# Research database construction status

Generated with `python3 src/research_report.py`. Counts describe persisted decisions at report generation; rerun after resuming acquisition. Historical periods use first Billboard appearance, not release year or first monthly entry.

Database: `data/processed/research.db`. **32,723 assets, 355,487 weekly observations, 81,800 monthly observations, 25,363 study members.**
The canonical Phase 1 database and raw JSON are unchanged. All weekly and monthly rows were reconciled field-for-field. Study membership does not depend on metadata/lyrics availability. See [schema and build instructions](../docs/research_database.md).

## Metadata

Attempted: **367**. High confidence: **309**; ambiguous: **37**; not found: **21**; errors: **0**; pending: **24,996**.
Accepted coverage is **1.22% of the study population**, or **84.2% of attempted assets**. These are different denominators; the partial run is not a full-population match-rate estimate.
The approved Phase 2A-R matcher is unchanged. The initial cache import reproduced all 160 pilot assets that belong to the study population: 137 accepted, 12 ambiguous, 11 not found, zero new requests. Other pilot songs were not imported. Live acquisition uses bounded original search queries; extra detailed lookups and difficult-tail rescue are deferred.

| First-chart period | Population | Attempted | Accepted | Ambiguous | Not found | Error | Accepted / population |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1958–1969 | 5,863 | 57 | 30 | 19 | 8 | 0 | 0.51% |
| 1970s | 4,364 | 53 | 41 | 7 | 5 | 0 | 0.94% |
| 1980s | 3,786 | 59 | 53 | 4 | 2 | 0 | 1.4% |
| 1990s | 3,053 | 59 | 53 | 2 | 4 | 0 | 1.74% |
| 2000s | 2,911 | 53 | 50 | 2 | 1 | 0 | 1.72% |
| 2010–2019 | 2,997 | 49 | 46 | 2 | 1 | 0 | 1.53% |
| 2020–2026 | 2,389 | 37 | 36 | 1 | 0 | 0 | 1.51% |

Reasons: `{"compatible_asset_with_release_anchor": 309, "compatible_identity_but_no_temporal_anchor": 26, "competing_artist_identities": 4, "no_cached_search_candidates": 21, "no_compatible_full_title_and_credit": 7}`.
Review flags: `{"anchor_only_in_following_year": 9, "bounded_search_truncated": 9, "content_version_requires_future_resolution": 34, "duration_outlier_review": 3, "formatting_normalization_used": 132, "later_or_undated_recordings_supported_by_asset_anchor": 189, "no_date_definitely_before_chart": 86, "version_descriptors_retained": 74}`.

All returned raw tag/genre values remain scoped to recordings, release groups, or artists. Missing new detailed genre lookups are unmeasured. Multiple recordings and conflicting dates/durations are retained; the database does not select a canonical recording or assign artist genres to songs. No final genre taxonomy is constructed.

## Lyrics

**Source: none selected; acquisition blocked on verified source access/reuse permission.** See the [source assessment](lyrics_source_assessment.md) for evidence and provider limitations.
Pilot: **200 study-member identities prepared, 0 attempted**. Full acquisition did not proceed. Total attempted: **0**; successful: **0**; ambiguous: **0**; not found: **0**; errors: **0**. Overall acquired coverage: **0.0%**.
All 25,363 blocked manifest rows represent unattempted access, not provider misses or API errors. No lyrics text or lyrics-containing API response was downloaded into the project.

| First-chart period | Population | Lyrics attempted | Retrieved | Acquired coverage |
|---|---:|---:|---:|---:|
| 1958–1969 | 5,863 | 0 | 0 | 0.0% |
| 1970s | 4,364 | 0 | 0 | 0.0% |
| 1980s | 3,786 | 0 | 0 | 0.0% |
| 1990s | 3,053 | 0 | 0 | 0.0% |
| 2000s | 2,911 | 0 | 0 | 0.0% |
| 2010–2019 | 2,997 | 0 | 0 | 0.0% |
| 2020–2026 | 2,389 | 0 | 0 | 0.0% |

### Important recent periods

- 2015–2019: 1,553 study assets; metadata accepted 21/21 attempted; lyrics 0/1,553 (0.0%).
- 2020–2026: 2,389 study assets; metadata accepted 36/37 attempted; lyrics 0/2,389 (0.0%).

### Every first-chart year

| Year | Study assets | Metadata attempted | Metadata accepted | Lyrics attempted | Lyrics retrieved | Lyrics coverage |
|---|---:|---:|---:|---:|---:|---:|
| 1958 | 263 | 4 | 2 | 0 | 0 | 0.0% |
| 1959 | 448 | 3 | 2 | 0 | 0 | 0.0% |
| 1960 | 456 | 5 | 0 | 0 | 0 | 0.0% |
| 1961 | 513 | 5 | 1 | 0 | 0 | 0.0% |
| 1962 | 480 | 5 | 3 | 0 | 0 | 0.0% |
| 1963 | 502 | 5 | 5 | 0 | 0 | 0.0% |
| 1964 | 534 | 5 | 2 | 0 | 0 | 0.0% |
| 1965 | 543 | 5 | 2 | 0 | 0 | 0.0% |
| 1966 | 560 | 5 | 5 | 0 | 0 | 0.0% |
| 1967 | 544 | 6 | 4 | 0 | 0 | 0.0% |
| 1968 | 519 | 4 | 3 | 0 | 0 | 0.0% |
| 1969 | 501 | 5 | 1 | 0 | 0 | 0.0% |
| 1970 | 476 | 3 | 2 | 0 | 0 | 0.0% |
| 1971 | 477 | 5 | 5 | 0 | 0 | 0.0% |
| 1972 | 465 | 6 | 4 | 0 | 0 | 0.0% |
| 1973 | 422 | 8 | 5 | 0 | 0 | 0.0% |
| 1974 | 418 | 5 | 4 | 0 | 0 | 0.0% |
| 1975 | 443 | 7 | 4 | 0 | 0 | 0.0% |
| 1976 | 425 | 4 | 4 | 0 | 0 | 0.0% |
| 1977 | 397 | 4 | 4 | 0 | 0 | 0.0% |
| 1978 | 401 | 5 | 4 | 0 | 0 | 0.0% |
| 1979 | 440 | 6 | 5 | 0 | 0 | 0.0% |
| 1980 | 408 | 6 | 5 | 0 | 0 | 0.0% |
| 1981 | 379 | 6 | 3 | 0 | 0 | 0.0% |
| 1982 | 408 | 6 | 6 | 0 | 0 | 0.0% |
| 1983 | 404 | 6 | 6 | 0 | 0 | 0.0% |
| 1984 | 399 | 4 | 4 | 0 | 0 | 0.0% |
| 1985 | 371 | 6 | 5 | 0 | 0 | 0.0% |
| 1986 | 364 | 7 | 7 | 0 | 0 | 0.0% |
| 1987 | 357 | 7 | 6 | 0 | 0 | 0.0% |
| 1988 | 343 | 5 | 5 | 0 | 0 | 0.0% |
| 1989 | 353 | 6 | 6 | 0 | 0 | 0.0% |
| 1990 | 349 | 8 | 8 | 0 | 0 | 0.0% |
| 1991 | 348 | 7 | 5 | 0 | 0 | 0.0% |
| 1992 | 311 | 5 | 5 | 0 | 0 | 0.0% |
| 1993 | 292 | 6 | 4 | 0 | 0 | 0.0% |
| 1994 | 296 | 6 | 6 | 0 | 0 | 0.0% |
| 1995 | 290 | 4 | 4 | 0 | 0 | 0.0% |
| 1996 | 273 | 5 | 5 | 0 | 0 | 0.0% |
| 1997 | 286 | 6 | 5 | 0 | 0 | 0.0% |
| 1998 | 322 | 5 | 4 | 0 | 0 | 0.0% |
| 1999 | 286 | 7 | 7 | 0 | 0 | 0.0% |
| 2000 | 287 | 5 | 5 | 0 | 0 | 0.0% |
| 2001 | 267 | 4 | 4 | 0 | 0 | 0.0% |
| 2002 | 280 | 5 | 4 | 0 | 0 | 0.0% |
| 2003 | 279 | 5 | 5 | 0 | 0 | 0.0% |
| 2004 | 281 | 5 | 5 | 0 | 0 | 0.0% |
| 2005 | 295 | 5 | 5 | 0 | 0 | 0.0% |
| 2006 | 292 | 8 | 7 | 0 | 0 | 0.0% |
| 2007 | 288 | 4 | 3 | 0 | 0 | 0.0% |
| 2008 | 319 | 6 | 6 | 0 | 0 | 0.0% |
| 2009 | 323 | 6 | 6 | 0 | 0 | 0.0% |
| 2010 | 321 | 5 | 4 | 0 | 0 | 0.0% |
| 2011 | 319 | 6 | 6 | 0 | 0 | 0.0% |
| 2012 | 255 | 8 | 7 | 0 | 0 | 0.0% |
| 2013 | 270 | 3 | 2 | 0 | 0 | 0.0% |
| 2014 | 279 | 6 | 6 | 0 | 0 | 0.0% |
| 2015 | 272 | 4 | 4 | 0 | 0 | 0.0% |
| 2016 | 298 | 3 | 3 | 0 | 0 | 0.0% |
| 2017 | 295 | 4 | 4 | 0 | 0 | 0.0% |
| 2018 | 371 | 6 | 6 | 0 | 0 | 0.0% |
| 2019 | 317 | 4 | 4 | 0 | 0 | 0.0% |
| 2020 | 360 | 3 | 2 | 0 | 0 | 0.0% |
| 2021 | 348 | 5 | 5 | 0 | 0 | 0.0% |
| 2022 | 367 | 7 | 7 | 0 | 0 | 0.0% |
| 2023 | 362 | 8 | 8 | 0 | 0 | 0.0% |
| 2024 | 378 | 8 | 8 | 0 | 0 | 0.0% |
| 2025 | 317 | 3 | 3 | 0 | 0 | 0.0% |
| 2026 | 257 | 3 | 3 | 0 | 0 | 0.0% |

## Resume and remaining work

Metadata still pending: **24,996 assets**; errors eligible for explicit retry: **0**. At 1.1 seconds per uncached request, the pending set has a lower bound of 7.64 hours for one search each. Actual runtime is longer because of latency, fallbacks, and retries. The bounded run avoids blocking the source-access decision on a potentially multi-day metadata pass.
```bash
python3 src/production_metadata.py --max-seconds 28800
python3 src/production_metadata.py --retry-errors --max-seconds 3600
python3 src/research.py validate
python3 src/research_report.py
python3 -m unittest discover -s tests -v
```

Lyrics remaining: all 25,363 study identities. First obtain documented source access/storage/reuse terms, then implement and validate that provider client. `python3 src/lyrics_plan.py` only reproduces the frozen pilot; it does not retrieve lyrics or bypass this gate. No acquisition command is presented as working without a selected authorized provider.

The lyrics directory and all caches are Git-ignored; no lyrics are tracked. Code and non-lyrical reports are checkpointed. No classifier, rawness scores, genre collapse, or COVID analysis was started.
