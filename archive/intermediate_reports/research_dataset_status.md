# Research database construction status

Generated with `python3 src/research_report.py`. Counts describe persisted decisions at report generation; rerun after resuming acquisition. Historical periods use first Billboard appearance, not release year or first monthly entry.

Database: `data/processed/research.db`. **32,723 assets, 355,487 weekly observations, 81,800 monthly observations, 25,363 study members.**
The canonical Phase 1 database and raw JSON are unchanged. All weekly and monthly rows were reconciled field-for-field. Study membership does not depend on metadata/lyrics availability. See [schema and build instructions](../../docs/research_database.md).

## Metadata

Attempted: **25,363**. High confidence: **20,450**; ambiguous: **3,410**; not found: **1,502**; errors: **1**; pending: **0**.
Accepted coverage is **80.63% of the study population**, or **80.63% of attempted assets**. Attempted and population denominators coincide only when every study asset has a disposition.
The approved Phase 2A-R matcher is unchanged. The initial cache import reproduced all 160 pilot assets that belong to the study population: 137 accepted, 12 ambiguous, 11 not found, zero new requests. Other pilot songs were not imported. Live acquisition uses bounded original search queries; extra detailed lookups and difficult-tail rescue are deferred.

| First-chart period | Population | Attempted | Accepted | Ambiguous | Not found | Error | Accepted / population |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1958–1969 | 5,863 | 5863 | 3883 | 1624 | 356 | 0 | 66.23% |
| 1970s | 4,364 | 4364 | 3448 | 568 | 348 | 0 | 79.01% |
| 1980s | 3,786 | 3786 | 3250 | 352 | 183 | 1 | 85.84% |
| 1990s | 3,053 | 3053 | 2479 | 305 | 269 | 0 | 81.2% |
| 2000s | 2,911 | 2911 | 2569 | 251 | 91 | 0 | 88.25% |
| 2010–2019 | 2,997 | 2997 | 2700 | 179 | 118 | 0 | 90.09% |
| 2020–2026 | 2,389 | 2389 | 2121 | 131 | 137 | 0 | 88.78% |

Reasons: `{"api_or_cache_error": 1, "compatible_asset_with_release_anchor": 20450, "compatible_identity_but_no_temporal_anchor": 2049, "competing_artist_identities": 423, "no_cached_search_candidates": 1502, "no_compatible_full_title_and_credit": 938}`.
Review flags: `{"anchor_only_in_following_year": 663, "bounded_search_truncated": 870, "content_version_requires_future_resolution": 1873, "duration_outlier_review": 178, "formatting_normalization_used": 9110, "later_or_undated_recordings_supported_by_asset_anchor": 14004, "no_date_definitely_before_chart": 6586, "version_descriptors_retained": 4699}`.

Returned metadata among accepted assets (presence, not validation of one canonical value):

| Entity and field | Assets | Percent of accepted |
|---|---:|---:|
| artist.genres | 555 | 2.71% |
| artist.id | 20,450 | 100.00% |
| recording.genres | 15 | 0.07% |
| recording.id | 20,450 | 100.00% |
| recording.isrcs | 16,560 | 80.98% |
| recording.length | 20,380 | 99.66% |
| recording.tags | 17,514 | 85.64% |
| release-group.genres | 62 | 0.30% |
| release-group.id | 20,450 | 100.00% |
| release.date | 20,296 | 99.25% |
| release.title | 20,450 | 100.00% |

All returned raw tag/genre values remain scoped to recordings, release groups, or artists. Missing new detailed genre lookups are unmeasured. Multiple recordings and conflicting dates/durations are retained; the database does not select a canonical recording or assign artist genres to songs. No final genre taxonomy is constructed.

Matching limitations remain visible in the decision files: missing candidates, incompatible full artist credits, conflicting artist identities, unsupported versions, and inadequate temporal anchors can leave an asset unresolved. Accepted later/undated manifestations inherit asset support from a compatible dated candidate; their own dates and durations should not be treated as the original release. Raw tags can include non-genre labels, and their presence is not a validated genre assignment. Production decisions have not received exhaustive manual review.

## Lyrics

Manifest sources: **LRCLIB**. Status: **dispositioned**. Production details and local storage are described in [lyrics instructions](../../docs/lyrics_production.md).
Pilot: **200 study-member identities, 200 attempted**. Total attempted: **25363**; successful: **19372**. Overall acquired coverage: **76.38%**.
Manifest dispositions: `{"bad_missing_text": 184, "error": 51, "not_found": 872, "quarantined": 3519, "success": 19372, "wrong_identity": 1365}`. Unattempted/blocked rows are not provider misses; wrong identity, bad/missing text, quarantine and API errors remain distinct. Only successful paths supply the corpus. No lyric text is copied into this report.

| First-chart period | Population | Lyrics attempted | Retrieved | Acquired coverage |
|---|---:|---:|---:|---:|
| 1958–1969 | 5,863 | 5863 | 4175 | 71.21% |
| 1970s | 4,364 | 4364 | 3250 | 74.47% |
| 1980s | 3,786 | 3786 | 3028 | 79.98% |
| 1990s | 3,053 | 3053 | 2219 | 72.68% |
| 2000s | 2,911 | 2911 | 2306 | 79.22% |
| 2010–2019 | 2,997 | 2997 | 2483 | 82.85% |
| 2020–2026 | 2,389 | 2389 | 1911 | 79.99% |

### Important recent periods

- 2015–2019: 1,553 study assets; metadata accepted 1403/1553 attempted; lyrics 1286/1,553 (82.81%).
- 2020–2026: 2,389 study assets; metadata accepted 2121/2389 attempted; lyrics 1911/2,389 (79.99%).

### Every first-chart year

| Year | Study assets | Metadata attempted | Metadata accepted | Lyrics attempted | Lyrics retrieved | Lyrics coverage |
|---|---:|---:|---:|---:|---:|---:|
| 1958 | 263 | 263 | 153 | 263 | 172 | 65.4% |
| 1959 | 448 | 448 | 238 | 448 | 285 | 63.62% |
| 1960 | 456 | 456 | 270 | 456 | 303 | 66.45% |
| 1961 | 513 | 513 | 309 | 513 | 341 | 66.47% |
| 1962 | 480 | 480 | 297 | 480 | 325 | 67.71% |
| 1963 | 502 | 502 | 327 | 502 | 356 | 70.92% |
| 1964 | 534 | 534 | 349 | 534 | 415 | 77.72% |
| 1965 | 543 | 543 | 376 | 543 | 391 | 72.01% |
| 1966 | 560 | 560 | 410 | 560 | 421 | 75.18% |
| 1967 | 544 | 544 | 405 | 544 | 414 | 76.1% |
| 1968 | 519 | 519 | 397 | 519 | 396 | 76.3% |
| 1969 | 501 | 501 | 352 | 501 | 356 | 71.06% |
| 1970 | 476 | 476 | 326 | 476 | 349 | 73.32% |
| 1971 | 477 | 477 | 349 | 477 | 334 | 70.02% |
| 1972 | 465 | 465 | 358 | 465 | 340 | 73.12% |
| 1973 | 422 | 422 | 325 | 422 | 319 | 75.59% |
| 1974 | 418 | 418 | 351 | 418 | 326 | 77.99% |
| 1975 | 443 | 443 | 340 | 443 | 298 | 67.27% |
| 1976 | 425 | 425 | 343 | 425 | 315 | 74.12% |
| 1977 | 397 | 397 | 329 | 397 | 295 | 74.31% |
| 1978 | 401 | 401 | 340 | 401 | 319 | 79.55% |
| 1979 | 440 | 440 | 387 | 440 | 355 | 80.68% |
| 1980 | 408 | 408 | 338 | 408 | 317 | 77.7% |
| 1981 | 379 | 379 | 326 | 379 | 299 | 78.89% |
| 1982 | 408 | 408 | 355 | 408 | 321 | 78.68% |
| 1983 | 404 | 404 | 353 | 404 | 331 | 81.93% |
| 1984 | 399 | 399 | 338 | 399 | 315 | 78.95% |
| 1985 | 371 | 371 | 313 | 371 | 306 | 82.48% |
| 1986 | 364 | 364 | 313 | 364 | 298 | 81.87% |
| 1987 | 357 | 357 | 300 | 357 | 282 | 78.99% |
| 1988 | 343 | 343 | 296 | 343 | 275 | 80.17% |
| 1989 | 353 | 353 | 318 | 353 | 284 | 80.45% |
| 1990 | 349 | 349 | 305 | 349 | 268 | 76.79% |
| 1991 | 348 | 348 | 283 | 348 | 266 | 76.44% |
| 1992 | 311 | 311 | 266 | 311 | 222 | 71.38% |
| 1993 | 292 | 292 | 235 | 292 | 215 | 73.63% |
| 1994 | 296 | 296 | 232 | 296 | 224 | 75.68% |
| 1995 | 290 | 290 | 232 | 290 | 188 | 64.83% |
| 1996 | 273 | 273 | 204 | 273 | 175 | 64.1% |
| 1997 | 286 | 286 | 214 | 286 | 208 | 72.73% |
| 1998 | 322 | 322 | 251 | 322 | 228 | 70.81% |
| 1999 | 286 | 286 | 257 | 286 | 225 | 78.67% |
| 2000 | 287 | 287 | 249 | 287 | 230 | 80.14% |
| 2001 | 267 | 267 | 231 | 267 | 210 | 78.65% |
| 2002 | 280 | 280 | 253 | 280 | 219 | 78.21% |
| 2003 | 279 | 279 | 245 | 279 | 223 | 79.93% |
| 2004 | 281 | 281 | 240 | 281 | 216 | 76.87% |
| 2005 | 295 | 295 | 267 | 295 | 231 | 78.31% |
| 2006 | 292 | 292 | 262 | 292 | 236 | 80.82% |
| 2007 | 288 | 288 | 255 | 288 | 225 | 78.12% |
| 2008 | 319 | 319 | 270 | 319 | 256 | 80.25% |
| 2009 | 323 | 323 | 297 | 323 | 260 | 80.5% |
| 2010 | 321 | 321 | 278 | 321 | 246 | 76.64% |
| 2011 | 319 | 319 | 293 | 319 | 271 | 84.95% |
| 2012 | 255 | 255 | 231 | 255 | 218 | 85.49% |
| 2013 | 270 | 270 | 240 | 270 | 229 | 84.81% |
| 2014 | 279 | 279 | 255 | 279 | 233 | 83.51% |
| 2015 | 272 | 272 | 248 | 272 | 227 | 83.46% |
| 2016 | 298 | 298 | 274 | 298 | 246 | 82.55% |
| 2017 | 295 | 295 | 266 | 295 | 244 | 82.71% |
| 2018 | 371 | 371 | 337 | 371 | 299 | 80.59% |
| 2019 | 317 | 317 | 278 | 317 | 270 | 85.17% |
| 2020 | 360 | 360 | 317 | 360 | 290 | 80.56% |
| 2021 | 348 | 348 | 298 | 348 | 261 | 75.0% |
| 2022 | 367 | 367 | 329 | 367 | 300 | 81.74% |
| 2023 | 362 | 362 | 313 | 362 | 296 | 81.77% |
| 2024 | 378 | 378 | 341 | 378 | 299 | 79.1% |
| 2025 | 317 | 317 | 281 | 317 | 256 | 80.76% |
| 2026 | 257 | 257 | 242 | 257 | 209 | 81.32% |

## Remaining work

Metadata pending: **0**; recorded errors: **1**. Metadata is optional enrichment, not a classifier prerequisite.
Lyrics without a disposition in this manifest: **0**. Do not restart a complete pass merely to improve acceptance. Unresolved outcomes remain explicit; no manual rescue or classifier is run by these commands.
```bash
python3 src/research.py validate
python3 src/lyrics_production.py validate
python3 -m unittest discover -s tests -v
```

Lyrics, caches and generated databases remain local and Git-ignored. See [completion record](../../docs/lyrics_completion.md) for acquisition, synchronization, validation and remaining limitations.
