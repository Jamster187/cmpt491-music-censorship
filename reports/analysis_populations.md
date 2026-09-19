# Billboard analysis populations

Generated locally with `python3 src/populations.py`. No external metadata, lyrics, or content analysis.

The weekly view remains **3,555 charts, 355,487 observations, and 32,723 exact title/artist identities**, from 1958-08-04 through 2026-09-19.
There are **818 months**, **818 complete 100-song baskets**, **81,800 song-month rows**, and **25,363 unique monthly-basket songs**.
Months with fewer than 100 eligible songs: []. The reduction is **7,360 assets (22.49%)**. No weekly rows or identities are removed.

## Definition and interpretation

Each source row contributes `101 - rank` points to its chart date's calendar month. Sum by month/song_id; order by points descending, best weekly rank ascending, average weekly rank ascending, then stable song_id in binary ascending order. Select exactly the first 100 eligible identities, or all if fewer. No prorating or week-spanning allocation is used.
`weeks_present` counts distinct chart dates. `average_weekly_rank` is the arithmetic mean over source observations; `weekly_observations` separately records the number of contributing rows. Source duplicate song-week rows each contribute points, as requested for every observation. They are not silently deduplicated or interpreted as distinct weeks.
There are 13 duplicate source song-week groups; 3 selected song-month rows contain duplicates. These source anomalies can affect points and selection; they remain visible in the inventory and extra observation-count field.
A complete 100-song basket does not mean complete calendar-month coverage. The snapshot ends on 2026-09-19: September 2026 contains only three chart dates and is provisional. August 1958 is the beginning of the supplied history, so first-entry counts are left-censored. Months are not normalized for having four versus five chart dates. Chart points are a rank-derived popularity proxy, not measured consumption.

## Weekly representation

Songs selected in at least one month account for **338,706/355,487 weekly rows (95.28%)**, including their weekly appearances outside selected months.
For a different denominator interpretation, weekly rows whose song is selected in that same month total 311,259 (87.56%).

## Historical periods

Appearing counts use any selected month in the period; a song can appear in multiple periods. First-entry counts are disjoint and sum to the overall unique population.

| Period | Unique songs appearing | First monthly entry in period |
|---|---:|---:|
| 1958–1969 | 5,848 | 5,848 |
| 1970s | 4,436 | 4,363 |
| 1980s | 3,876 | 3,798 |
| 1990s | 3,136 | 3,049 |
| 2000s | 2,977 | 2,896 |
| 2010s | 3,110 | 3,000 |
| 2020–2026 | 2,541 | 2,409 |

## New unique monthly-basket songs each year

Year of first selected monthly basket, not release year or first weekly Billboard appearance. 1958 and 2026 are partial years.

| Year | New songs |
|---|---:|
| 1958 | 248 |
| 1959 | 446 |
| 1960 | 457 |
| 1961 | 514 |
| 1962 | 475 |
| 1963 | 507 |
| 1964 | 534 |
| 1965 | 540 |
| 1966 | 551 |
| 1967 | 550 |
| 1968 | 521 |
| 1969 | 505 |
| 1970 | 473 |
| 1971 | 476 |
| 1972 | 462 |
| 1973 | 428 |
| 1974 | 424 |
| 1975 | 436 |
| 1976 | 433 |
| 1977 | 398 |
| 1978 | 399 |
| 1979 | 434 |
| 1980 | 418 |
| 1981 | 378 |
| 1982 | 409 |
| 1983 | 407 |
| 1984 | 397 |
| 1985 | 369 |
| 1986 | 362 |
| 1987 | 359 |
| 1988 | 346 |
| 1989 | 353 |
| 1990 | 349 |
| 1991 | 350 |
| 1992 | 305 |
| 1993 | 295 |
| 1994 | 292 |
| 1995 | 294 |
| 1996 | 275 |
| 1997 | 283 |
| 1998 | 321 |
| 1999 | 285 |
| 2000 | 282 |
| 2001 | 270 |
| 2002 | 278 |
| 2003 | 282 |
| 2004 | 283 |
| 2005 | 287 |
| 2006 | 291 |
| 2007 | 288 |
| 2008 | 314 |
| 2009 | 321 |
| 2010 | 320 |
| 2011 | 320 |
| 2012 | 257 |
| 2013 | 273 |
| 2014 | 278 |
| 2015 | 277 |
| 2016 | 288 |
| 2017 | 299 |
| 2018 | 368 |
| 2019 | 320 |
| 2020 | 357 |
| 2021 | 354 |
| 2022 | 366 |
| 2023 | 363 |
| 2024 | 379 |
| 2025 | 320 |
| 2026 | 270 |

## Months per selected song

Minimum 1; median 3; mean 3.2252; maximum 35. Excludes the 7,360 original identities selected in zero months.

| Months selected | Songs |
|---:|---:|
| 1 | 5,202 |
| 2 | 5,612 |
| 3 | 5,023 |
| 4 | 3,934 |
| 5 | 3,062 |
| 6 | 1,132 |
| 7 | 503 |
| 8 | 320 |
| 9 | 182 |
| 10 | 127 |
| 11 | 80 |
| 12 | 68 |
| 13 | 53 |
| 14 | 18 |
| 15 | 16 |
| 16 | 9 |
| 17 | 6 |
| 18 | 3 |
| 19 | 3 |
| 20 | 2 |
| 21 | 3 |
| 22 | 1 |
| 26 | 2 |
| 32 | 1 |
| 35 | 1 |

## Example baskets (first five rows)

### 1958-08 — 4 chart dates

| Rank | Title | Artist | Points | Weeks | Best rank | Mean rank |
|---:|---|---|---:|---:|---:|---:|
| 1 | Poor Little Fool | Ricky Nelson | 392 | 4 | 1 | 3.00 |
| 2 | Patricia | Perez Prado And His Orchestra | 387 | 4 | 2 | 4.25 |
| 3 | My True Love | Jack Scott | 382 | 4 | 3 | 5.50 |
| 4 | When | Kalin Twins | 377 | 4 | 5 | 6.75 |
| 5 | Just A Dream | Jimmy Clanton And His Rockets | 373 | 4 | 4 | 7.75 |

### 1977-06 — 4 chart dates

| Rank | Title | Artist | Points | Weeks | Best rank | Mean rank |
|---:|---|---|---:|---:|---:|---:|
| 1 | Got To Give It Up (Pt. I) | Marvin Gaye | 394 | 4 | 1 | 2.50 |
| 2 | Dreams | Fleetwood Mac | 392 | 4 | 1 | 3.00 |
| 3 | Gonna Fly Now | Bill Conti | 390 | 4 | 2 | 3.50 |
| 4 | Feels Like The First Time | Foreigner | 382 | 4 | 4 | 5.50 |
| 5 | Lucille | Kenny Rogers | 381 | 4 | 5 | 5.75 |

### 1995-07 — 5 chart dates

| Rank | Title | Artist | Points | Weeks | Best rank | Mean rank |
|---:|---|---|---:|---:|---:|---:|
| 1 | Waterfalls | TLC | 494 | 5 | 1 | 2.20 |
| 2 | One More Chance/Stay With Me | The Notorious B.I.G. | 493 | 5 | 2 | 2.40 |
| 3 | Don't Take It Personal (Just One Of Dem Days) | Monica | 492 | 5 | 2 | 2.60 |
| 4 | Have You Ever Really Loved A Woman? | Bryan Adams | 478 | 5 | 1 | 5.40 |
| 5 | Total Eclipse Of The Heart | Nicki French | 478 | 5 | 4 | 5.40 |

### 2019-06 — 5 chart dates

| Rank | Title | Artist | Points | Weeks | Best rank | Mean rank |
|---:|---|---|---:|---:|---:|---:|
| 1 | Old Town Road | Lil Nas X Featuring Billy Ray Cyrus | 500 | 5 | 1 | 1.00 |
| 2 | Bad Guy | Billie Eilish | 493 | 5 | 2 | 2.40 |
| 3 | Talk | Khalid | 487 | 5 | 3 | 3.60 |
| 4 | I Don't Care | Ed Sheeran & Justin Bieber | 485 | 5 | 2 | 4.00 |
| 5 | Sucker | Jonas Brothers | 481 | 5 | 4 | 4.80 |

### 2020-04 — 4 chart dates

| Rank | Title | Artist | Points | Weeks | Best rank | Mean rank |
|---:|---|---|---:|---:|---:|---:|
| 1 | Blinding Lights | The Weeknd | 399 | 4 | 1 | 1.25 |
| 2 | The Box | Roddy Ricch | 394 | 4 | 2 | 2.50 |
| 3 | Don't Start Now | Dua Lipa | 390 | 4 | 3 | 3.50 |
| 4 | Circles | Post Malone | 382 | 4 | 4 | 5.50 |
| 5 | Life Is Good | Future Featuring Drake | 380 | 4 | 5 | 6.00 |

### 2026-08 — 5 chart dates

| Rank | Title | Artist | Points | Weeks | Best rank | Mean rank |
|---:|---|---|---:|---:|---:|---:|
| 1 | Choosin' Texas | Ella Langley | 500 | 5 | 1 | 1.00 |
| 2 | I Knew It, I Knew You | Taylor Swift | 490 | 5 | 2 | 3.00 |
| 3 | Boston | Stella Lefty | 485 | 5 | 2 | 4.00 |
| 4 | Hate That I Made You Love Me | Ariana Grande | 480 | 5 | 2 | 5.00 |
| 5 | I Can't Love You Anymore | Ella Langley & Morgan Wallen | 478 | 5 | 4 | 5.40 |

### 2026-09 — 3 chart dates

| Rank | Title | Artist | Points | Weeks | Best rank | Mean rank |
|---:|---|---|---:|---:|---:|---:|
| 1 | Choosin' Texas | Ella Langley | 300 | 3 | 1 | 1.00 |
| 2 | Boston | Stella Lefty | 297 | 3 | 2 | 2.00 |
| 3 | I Knew It, I Knew You | Taylor Swift | 294 | 3 | 3 | 3.00 |
| 4 | Been By Now | Morgan Wallen | 290 | 3 | 4 | 4.33 |
| 5 | Hate That I Made You Love Me | Ariana Grande | 289 | 3 | 4 | 4.67 |

## Validation and reproduction

All monthly rows, statistics, and top-100 selection reconcile to an independent Python aggregation using exact rational average-rank comparisons. Monthly ranks are unique and contiguous, basket sizes never exceed 100, and every song_id resolves to the canonical songs table. Both CSV exports were read back and reconciled row-for-row. Source JSON and canonical database hashes were unchanged across the build.
The derived SQLite database, weekly/monthly CSVs, complete month inventory, yearly entrant counts, frequency distribution, and JSON report are under `data/processed/populations/` (ignored and rebuildable). See [population instructions](../docs/analysis_populations.md) for joins and commands. Song metadata is not duplicated in the derived database or weekly/monthly exports. No classifier or COVID breakpoint is implemented.
