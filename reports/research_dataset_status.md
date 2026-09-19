# Research database construction status

Generated with `python3 src/research_report.py`. Counts describe persisted decisions at report generation; rerun after resuming acquisition. Historical periods use first Billboard appearance, not release year or first monthly entry.

Database: `data/processed/research.db`. **32,723 assets, 355,487 weekly observations, 81,800 monthly observations, 25,363 study members.**
The canonical Phase 1 database and raw JSON are unchanged. All weekly and monthly rows were reconciled field-for-field. Study membership does not depend on metadata/lyrics availability. See [schema and build instructions](../docs/research_database.md).

## Metadata

Attempted: **927**. High confidence: **768**; ambiguous: **109**; not found: **50**; errors: **0**; pending: **24,436**.
Accepted coverage is **3.03% of the study population**, or **82.85% of attempted assets**. These are different denominators; the partial run is not a full-population match-rate estimate.
The approved Phase 2A-R matcher is unchanged. The initial cache import reproduced all 160 pilot assets that belong to the study population: 137 accepted, 12 ambiguous, 11 not found, zero new requests. Other pilot songs were not imported. Live acquisition uses bounded original search queries; extra detailed lookups and difficult-tail rescue are deferred.

| First-chart period | Population | Attempted | Accepted | Ambiguous | Not found | Error | Accepted / population |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1958–1969 | 5,863 | 153 | 95 | 48 | 10 | 0 | 1.62% |
| 1970s | 4,364 | 133 | 108 | 15 | 10 | 0 | 2.47% |
| 1980s | 3,786 | 139 | 121 | 11 | 7 | 0 | 3.2% |
| 1990s | 3,053 | 139 | 116 | 13 | 10 | 0 | 3.8% |
| 2000s | 2,911 | 133 | 120 | 9 | 4 | 0 | 4.12% |
| 2010–2019 | 2,997 | 130 | 115 | 10 | 5 | 0 | 3.84% |
| 2020–2026 | 2,389 | 100 | 93 | 3 | 4 | 0 | 3.89% |

Reasons: `{"compatible_asset_with_release_anchor": 768, "compatible_identity_but_no_temporal_anchor": 65, "competing_artist_identities": 11, "no_cached_search_candidates": 50, "no_compatible_full_title_and_credit": 33}`.
Review flags: `{"anchor_only_in_following_year": 15, "bounded_search_truncated": 23, "content_version_requires_future_resolution": 79, "duration_outlier_review": 7, "formatting_normalization_used": 340, "later_or_undated_recordings_supported_by_asset_anchor": 479, "no_date_definitely_before_chart": 201, "version_descriptors_retained": 190}`.

Returned metadata among accepted assets (presence, not validation of one canonical value):

| Entity and field | Assets | Percent of accepted |
|---|---:|---:|
| artist.genres | 43 | 5.60% |
| artist.id | 768 | 100.00% |
| recording.genres | 15 | 1.95% |
| recording.id | 768 | 100.00% |
| recording.isrcs | 654 | 85.16% |
| recording.length | 767 | 99.87% |
| recording.tags | 655 | 85.29% |
| release-group.genres | 26 | 3.39% |
| release-group.id | 768 | 100.00% |
| release.date | 760 | 98.96% |
| release.title | 768 | 100.00% |

All returned raw tag/genre values remain scoped to recordings, release groups, or artists. Missing new detailed genre lookups are unmeasured. Multiple recordings and conflicting dates/durations are retained; the database does not select a canonical recording or assign artist genres to songs. No final genre taxonomy is constructed.

Matching limitations remain visible in the decision files: missing candidates, incompatible full artist credits, conflicting artist identities, unsupported versions, and inadequate temporal anchors can leave an asset unresolved. Accepted later/undated manifestations inherit asset support from a compatible dated candidate; their own dates and durations should not be treated as the original release. Raw tags can include non-genre labels, and their presence is not a validated genre assignment. Production decisions have not received exhaustive manual review.

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

- 2015–2019: 1,553 study assets; metadata accepted 55/62 attempted; lyrics 0/1,553 (0.0%).
- 2020–2026: 2,389 study assets; metadata accepted 93/100 attempted; lyrics 0/2,389 (0.0%).

### Every first-chart year

| Year | Study assets | Metadata attempted | Metadata accepted | Lyrics attempted | Lyrics retrieved | Lyrics coverage |
|---|---:|---:|---:|---:|---:|---:|
| 1958 | 263 | 12 | 5 | 0 | 0 | 0.0% |
| 1959 | 448 | 11 | 7 | 0 | 0 | 0.0% |
| 1960 | 456 | 13 | 5 | 0 | 0 | 0.0% |
| 1961 | 513 | 13 | 7 | 0 | 0 | 0.0% |
| 1962 | 480 | 13 | 9 | 0 | 0 | 0.0% |
| 1963 | 502 | 13 | 9 | 0 | 0 | 0.0% |
| 1964 | 534 | 13 | 6 | 0 | 0 | 0.0% |
| 1965 | 543 | 13 | 7 | 0 | 0 | 0.0% |
| 1966 | 560 | 13 | 12 | 0 | 0 | 0.0% |
| 1967 | 544 | 14 | 11 | 0 | 0 | 0.0% |
| 1968 | 519 | 12 | 9 | 0 | 0 | 0.0% |
| 1969 | 501 | 13 | 8 | 0 | 0 | 0.0% |
| 1970 | 476 | 11 | 8 | 0 | 0 | 0.0% |
| 1971 | 477 | 13 | 12 | 0 | 0 | 0.0% |
| 1972 | 465 | 14 | 12 | 0 | 0 | 0.0% |
| 1973 | 422 | 16 | 11 | 0 | 0 | 0.0% |
| 1974 | 418 | 13 | 10 | 0 | 0 | 0.0% |
| 1975 | 443 | 15 | 9 | 0 | 0 | 0.0% |
| 1976 | 425 | 12 | 11 | 0 | 0 | 0.0% |
| 1977 | 397 | 12 | 10 | 0 | 0 | 0.0% |
| 1978 | 401 | 13 | 12 | 0 | 0 | 0.0% |
| 1979 | 440 | 14 | 13 | 0 | 0 | 0.0% |
| 1980 | 408 | 14 | 13 | 0 | 0 | 0.0% |
| 1981 | 379 | 14 | 10 | 0 | 0 | 0.0% |
| 1982 | 408 | 14 | 12 | 0 | 0 | 0.0% |
| 1983 | 404 | 14 | 12 | 0 | 0 | 0.0% |
| 1984 | 399 | 12 | 11 | 0 | 0 | 0.0% |
| 1985 | 371 | 14 | 10 | 0 | 0 | 0.0% |
| 1986 | 364 | 15 | 14 | 0 | 0 | 0.0% |
| 1987 | 357 | 15 | 14 | 0 | 0 | 0.0% |
| 1988 | 343 | 13 | 12 | 0 | 0 | 0.0% |
| 1989 | 353 | 14 | 13 | 0 | 0 | 0.0% |
| 1990 | 349 | 16 | 15 | 0 | 0 | 0.0% |
| 1991 | 348 | 15 | 12 | 0 | 0 | 0.0% |
| 1992 | 311 | 13 | 11 | 0 | 0 | 0.0% |
| 1993 | 292 | 14 | 10 | 0 | 0 | 0.0% |
| 1994 | 296 | 14 | 12 | 0 | 0 | 0.0% |
| 1995 | 290 | 12 | 11 | 0 | 0 | 0.0% |
| 1996 | 273 | 13 | 11 | 0 | 0 | 0.0% |
| 1997 | 286 | 14 | 8 | 0 | 0 | 0.0% |
| 1998 | 322 | 13 | 12 | 0 | 0 | 0.0% |
| 1999 | 286 | 15 | 14 | 0 | 0 | 0.0% |
| 2000 | 287 | 13 | 10 | 0 | 0 | 0.0% |
| 2001 | 267 | 12 | 12 | 0 | 0 | 0.0% |
| 2002 | 280 | 13 | 11 | 0 | 0 | 0.0% |
| 2003 | 279 | 13 | 12 | 0 | 0 | 0.0% |
| 2004 | 281 | 13 | 11 | 0 | 0 | 0.0% |
| 2005 | 295 | 13 | 13 | 0 | 0 | 0.0% |
| 2006 | 292 | 16 | 14 | 0 | 0 | 0.0% |
| 2007 | 288 | 12 | 11 | 0 | 0 | 0.0% |
| 2008 | 319 | 14 | 12 | 0 | 0 | 0.0% |
| 2009 | 323 | 14 | 14 | 0 | 0 | 0.0% |
| 2010 | 321 | 13 | 11 | 0 | 0 | 0.0% |
| 2011 | 319 | 14 | 12 | 0 | 0 | 0.0% |
| 2012 | 255 | 16 | 14 | 0 | 0 | 0.0% |
| 2013 | 270 | 11 | 9 | 0 | 0 | 0.0% |
| 2014 | 279 | 14 | 14 | 0 | 0 | 0.0% |
| 2015 | 272 | 12 | 11 | 0 | 0 | 0.0% |
| 2016 | 298 | 11 | 9 | 0 | 0 | 0.0% |
| 2017 | 295 | 12 | 12 | 0 | 0 | 0.0% |
| 2018 | 371 | 14 | 12 | 0 | 0 | 0.0% |
| 2019 | 317 | 13 | 11 | 0 | 0 | 0.0% |
| 2020 | 360 | 12 | 11 | 0 | 0 | 0.0% |
| 2021 | 348 | 14 | 13 | 0 | 0 | 0.0% |
| 2022 | 367 | 16 | 15 | 0 | 0 | 0.0% |
| 2023 | 362 | 17 | 16 | 0 | 0 | 0.0% |
| 2024 | 378 | 17 | 16 | 0 | 0 | 0.0% |
| 2025 | 317 | 12 | 11 | 0 | 0 | 0.0% |
| 2026 | 257 | 12 | 11 | 0 | 0 | 0.0% |

## Resume and remaining work

Metadata still pending: **24,436 assets**; errors eligible for explicit retry: **0**. At 1.1 seconds per uncached request, the pending set has a lower bound of 7.47 hours for one search each. Actual runtime is longer because of latency, fallbacks, and retries. The bounded run avoids blocking the source-access decision on a potentially multi-day metadata pass.
```bash
python3 src/production_metadata.py --max-seconds 28800
python3 src/production_metadata.py --retry-errors --max-seconds 3600
python3 src/research.py validate
python3 src/research_report.py
python3 -m unittest discover -s tests -v
```

Lyrics remaining: all 25,363 study identities. First obtain documented source access/storage/reuse terms, then implement and validate that provider client. `python3 src/lyrics_plan.py` only reproduces the frozen pilot; it does not retrieve lyrics or bypass this gate. No acquisition command is presented as working without a selected authorized provider.

The lyrics directory and all caches are Git-ignored; no lyrics are tracked. Code and non-lyrical reports are checkpointed. No classifier, rawness scores, genre collapse, or COVID analysis was started. See the [session validation record](research_validation.md) for restart checks and measured runtime.
