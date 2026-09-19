# Research database construction status

Generated with `python3 src/research_report.py`. Counts describe persisted decisions at report generation; rerun after resuming acquisition. Historical periods use first Billboard appearance, not release year or first monthly entry.

Database: `data/processed/research.db`. **32,723 assets, 355,487 weekly observations, 81,800 monthly observations, 25,363 study members.**
The canonical Phase 1 database and raw JSON are unchanged. All weekly and monthly rows were reconciled field-for-field. Study membership does not depend on metadata/lyrics availability. See [schema and build instructions](../docs/research_database.md).

## Metadata

Attempted: **1,042**. High confidence: **859**; ambiguous: **117**; not found: **66**; errors: **0**; pending: **24,321**.
Accepted coverage is **3.39% of the study population**, or **82.44% of attempted assets**. These are different denominators; the partial run is not a full-population match-rate estimate.
The approved Phase 2A-R matcher is unchanged. The initial cache import reproduced all 160 pilot assets that belong to the study population: 137 accepted, 12 ambiguous, 11 not found, zero new requests. Other pilot songs were not imported. Live acquisition uses bounded original search queries; extra detailed lookups and difficult-tail rescue are deferred.

| First-chart period | Population | Attempted | Accepted | Ambiguous | Not found | Error | Accepted / population |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1958–1969 | 5,863 | 165 | 105 | 49 | 11 | 0 | 1.79% |
| 1970s | 4,364 | 143 | 114 | 16 | 13 | 0 | 2.61% |
| 1980s | 3,786 | 158 | 138 | 12 | 8 | 0 | 3.65% |
| 1990s | 3,053 | 159 | 129 | 16 | 14 | 0 | 4.23% |
| 2000s | 2,911 | 153 | 136 | 11 | 6 | 0 | 4.67% |
| 2010–2019 | 2,997 | 150 | 133 | 10 | 7 | 0 | 4.44% |
| 2020–2026 | 2,389 | 114 | 104 | 3 | 7 | 0 | 4.35% |

Reasons: `{"compatible_asset_with_release_anchor": 859, "compatible_identity_but_no_temporal_anchor": 70, "competing_artist_identities": 12, "no_cached_search_candidates": 66, "no_compatible_full_title_and_credit": 35}`.
Review flags: `{"anchor_only_in_following_year": 19, "bounded_search_truncated": 26, "content_version_requires_future_resolution": 88, "duration_outlier_review": 8, "formatting_normalization_used": 381, "later_or_undated_recordings_supported_by_asset_anchor": 533, "no_date_definitely_before_chart": 223, "version_descriptors_retained": 213}`.

Returned metadata among accepted assets (presence, not validation of one canonical value):

| Entity and field | Assets | Percent of accepted |
|---|---:|---:|
| artist.genres | 45 | 5.24% |
| artist.id | 859 | 100.00% |
| recording.genres | 15 | 1.75% |
| recording.id | 859 | 100.00% |
| recording.isrcs | 731 | 85.10% |
| recording.length | 857 | 99.77% |
| recording.tags | 732 | 85.22% |
| release-group.genres | 26 | 3.03% |
| release-group.id | 859 | 100.00% |
| release.date | 849 | 98.84% |
| release.title | 859 | 100.00% |

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

- 2015–2019: 1,553 study assets; metadata accepted 63/72 attempted; lyrics 0/1,553 (0.0%).
- 2020–2026: 2,389 study assets; metadata accepted 104/114 attempted; lyrics 0/2,389 (0.0%).

### Every first-chart year

| Year | Study assets | Metadata attempted | Metadata accepted | Lyrics attempted | Lyrics retrieved | Lyrics coverage |
|---|---:|---:|---:|---:|---:|---:|
| 1958 | 263 | 13 | 6 | 0 | 0 | 0.0% |
| 1959 | 448 | 12 | 8 | 0 | 0 | 0.0% |
| 1960 | 456 | 14 | 6 | 0 | 0 | 0.0% |
| 1961 | 513 | 14 | 8 | 0 | 0 | 0.0% |
| 1962 | 480 | 14 | 10 | 0 | 0 | 0.0% |
| 1963 | 502 | 14 | 10 | 0 | 0 | 0.0% |
| 1964 | 534 | 14 | 6 | 0 | 0 | 0.0% |
| 1965 | 543 | 14 | 8 | 0 | 0 | 0.0% |
| 1966 | 560 | 14 | 13 | 0 | 0 | 0.0% |
| 1967 | 544 | 15 | 11 | 0 | 0 | 0.0% |
| 1968 | 519 | 13 | 10 | 0 | 0 | 0.0% |
| 1969 | 501 | 14 | 9 | 0 | 0 | 0.0% |
| 1970 | 476 | 12 | 8 | 0 | 0 | 0.0% |
| 1971 | 477 | 14 | 12 | 0 | 0 | 0.0% |
| 1972 | 465 | 15 | 13 | 0 | 0 | 0.0% |
| 1973 | 422 | 17 | 11 | 0 | 0 | 0.0% |
| 1974 | 418 | 14 | 11 | 0 | 0 | 0.0% |
| 1975 | 443 | 16 | 10 | 0 | 0 | 0.0% |
| 1976 | 425 | 13 | 12 | 0 | 0 | 0.0% |
| 1977 | 397 | 13 | 11 | 0 | 0 | 0.0% |
| 1978 | 401 | 14 | 13 | 0 | 0 | 0.0% |
| 1979 | 440 | 15 | 13 | 0 | 0 | 0.0% |
| 1980 | 408 | 15 | 14 | 0 | 0 | 0.0% |
| 1981 | 379 | 16 | 12 | 0 | 0 | 0.0% |
| 1982 | 408 | 16 | 14 | 0 | 0 | 0.0% |
| 1983 | 404 | 16 | 14 | 0 | 0 | 0.0% |
| 1984 | 399 | 14 | 13 | 0 | 0 | 0.0% |
| 1985 | 371 | 16 | 11 | 0 | 0 | 0.0% |
| 1986 | 364 | 17 | 16 | 0 | 0 | 0.0% |
| 1987 | 357 | 17 | 16 | 0 | 0 | 0.0% |
| 1988 | 343 | 15 | 14 | 0 | 0 | 0.0% |
| 1989 | 353 | 16 | 14 | 0 | 0 | 0.0% |
| 1990 | 349 | 18 | 17 | 0 | 0 | 0.0% |
| 1991 | 348 | 17 | 14 | 0 | 0 | 0.0% |
| 1992 | 311 | 15 | 11 | 0 | 0 | 0.0% |
| 1993 | 292 | 16 | 11 | 0 | 0 | 0.0% |
| 1994 | 296 | 16 | 12 | 0 | 0 | 0.0% |
| 1995 | 290 | 14 | 13 | 0 | 0 | 0.0% |
| 1996 | 273 | 15 | 13 | 0 | 0 | 0.0% |
| 1997 | 286 | 16 | 9 | 0 | 0 | 0.0% |
| 1998 | 322 | 15 | 14 | 0 | 0 | 0.0% |
| 1999 | 286 | 17 | 15 | 0 | 0 | 0.0% |
| 2000 | 287 | 15 | 11 | 0 | 0 | 0.0% |
| 2001 | 267 | 14 | 13 | 0 | 0 | 0.0% |
| 2002 | 280 | 15 | 13 | 0 | 0 | 0.0% |
| 2003 | 279 | 15 | 14 | 0 | 0 | 0.0% |
| 2004 | 281 | 15 | 12 | 0 | 0 | 0.0% |
| 2005 | 295 | 15 | 15 | 0 | 0 | 0.0% |
| 2006 | 292 | 18 | 16 | 0 | 0 | 0.0% |
| 2007 | 288 | 14 | 13 | 0 | 0 | 0.0% |
| 2008 | 319 | 16 | 13 | 0 | 0 | 0.0% |
| 2009 | 323 | 16 | 16 | 0 | 0 | 0.0% |
| 2010 | 321 | 15 | 13 | 0 | 0 | 0.0% |
| 2011 | 319 | 16 | 14 | 0 | 0 | 0.0% |
| 2012 | 255 | 18 | 16 | 0 | 0 | 0.0% |
| 2013 | 270 | 13 | 11 | 0 | 0 | 0.0% |
| 2014 | 279 | 16 | 16 | 0 | 0 | 0.0% |
| 2015 | 272 | 14 | 12 | 0 | 0 | 0.0% |
| 2016 | 298 | 13 | 10 | 0 | 0 | 0.0% |
| 2017 | 295 | 14 | 14 | 0 | 0 | 0.0% |
| 2018 | 371 | 16 | 14 | 0 | 0 | 0.0% |
| 2019 | 317 | 15 | 13 | 0 | 0 | 0.0% |
| 2020 | 360 | 14 | 11 | 0 | 0 | 0.0% |
| 2021 | 348 | 16 | 14 | 0 | 0 | 0.0% |
| 2022 | 367 | 18 | 17 | 0 | 0 | 0.0% |
| 2023 | 362 | 19 | 18 | 0 | 0 | 0.0% |
| 2024 | 378 | 19 | 18 | 0 | 0 | 0.0% |
| 2025 | 317 | 14 | 13 | 0 | 0 | 0.0% |
| 2026 | 257 | 14 | 13 | 0 | 0 | 0.0% |

## Resume and remaining work

Metadata still pending: **24,321 assets**; errors eligible for explicit retry: **0**. At 1.1 seconds per uncached request, the pending set has a lower bound of 7.43 hours for one search each. Actual runtime is longer because of latency, fallbacks, and retries. The bounded run avoids blocking the source-access decision on a potentially multi-day metadata pass.
```bash
python3 src/production_metadata.py --max-seconds 28800
python3 src/production_metadata.py --retry-errors --max-seconds 3600
python3 src/research.py validate
python3 src/research_report.py
python3 -m unittest discover -s tests -v
```

Lyrics remaining: all 25,363 study identities. First obtain documented source access/storage/reuse terms, then implement and validate that provider client. `python3 src/lyrics_plan.py` only reproduces the frozen pilot; it does not retrieve lyrics or bypass this gate. No acquisition command is presented as working without a selected authorized provider.

The lyrics directory and all caches are Git-ignored; no lyrics are tracked. Code and non-lyrical reports are checkpointed. No classifier, rawness scores, genre collapse, or COVID analysis was started. See the [session validation record](research_validation.md) for restart checks and measured runtime.
