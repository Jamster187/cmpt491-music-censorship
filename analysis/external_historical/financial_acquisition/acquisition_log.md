# Acquisition log and source decisions

The execution baseline is commit `fb3fc0d5519c3cf78574c35f7dd32ec829f7d660`. The local preservation audit began at `2026-10-28T19:06:03.731823+00:00`. Source retrieval timestamps range from `2026-10-28T18:23:47.813516+00:00` to `2026-10-28T19:12:12.677213+00:00` because previously downloaded caches are reused only after matching URL and SHA-256.

There are **32 immutable content-addressed snapshots**, of which **21** reuse validated source bytes. They include economic data, the G.17 release calendar/dictionary, Michigan terms and NBER chronology/announcements. Source count is not provider count or independent-variable count. [source_manifest.csv](source_manifest.csv) and the [JSON manifest](../../../data/external_historical/financial/manifests/acquisition_v1/sources.json) preserve exact URLs, POST payloads, original retrieval times, response metadata, hashes and byte counts.

The originating-provider routes cover BLS, BEA, Federal Reserve Board H.15/G.17/DSR/CHGDEL/EBP/FCI-G, DOL ETA, Chicago Fed, San Francisco Fed, University of Michigan, Kenneth French Data Library, Baker–Bloom–Davis, World Bank and NBER. Warm-up observations were retained where available, including BLS 1956–1957 and market returns from 1926. No old raw file was edited.

Requests are sequential, with a minimum 1.1-second pause for new requests, bounded three-attempt retries and 30 MB per-response caps. No paid service, unauthorized scraping, bypass, credential exposure or massive parallel download was used. No FRED/BEA/EIA key was configured. The current official Chicago Fed data manifest resolved its changed CSV URL; the final pinned request succeeded. All 32 source snapshots and all parsers are successful in the released version.

The dictionary also carries 23 explicitly reviewed reported-history crosswalks to the frozen research catalog; unknown original bounds remain UNKNOWN and are separate from measured downloaded bounds. The G.17 manufacturing input is B00004 **SIC manufacturing**, not the shorter NAICS IPMAN series.

Parser validation caught and corrected source-format assumptions before publication: Michigan's column order and empty trailing CSV field, the EPU attribution footer, and Chicago Fed's `Friday_of_Week` column. These were transformation issues, not corrections to original observations. Source anomalies remain separate: BLS footnotes/missing months, the Pink Sheet mismatch-details worksheet, and the EPU footer are retained and reported. Normalization errors now prevent replacement of a previously published native dataset.

The priority acquisition status is measured from downloaded observations:

| priority | input | native_frequency | first_valid | last_valid | monthly_values | public_values |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | French market excess return | M | 1926-07-01 | 2026-09-01 | 825 | False |
| 2 | Unemployment | M | 1956-01-01 | 2026-09-01 | 824 | True |
| 3 | CPI | M | 1956-01-01 | 2026-09-01 | 824 | True |
| 4 | Consumer sentiment | M | 1978-01-01 | 2026-09-01 | 585 | False |
| 5 | 10-year Treasury | M | 1953-04-01 | 2026-09-01 | 825 | True |
| 6 | 3-month Treasury bill discount yield | M | 1934-01-01 | 2026-09-01 | 825 | True |
| 7 | Federal funds | M | 1954-07-01 | 2026-09-01 | 825 | True |
| 8 | Baa yield | M | 1919-01-01 | 2016-09-01 | 705 | False |
| 9 | Aaa yield | M | 1919-01-01 | 2016-09-01 | 705 | False |
| 10 | Industrial production | M | 1919-01-01 | 2026-09-01 | 825 | True |
| 11 | Disposable income | M | 1959-01-01 | 2026-08-01 | 812 | True |
| 12 | PCE prices | M | 1959-01-01 | 2026-08-01 | 812 | True |
| 13 | Personal saving rate | M | 1959-01-01 | 2026-08-01 | 812 | True |
| 14 | Production/nonsupervisory earnings | M | 1964-01-01 | 2026-09-01 | 753 | True |
| 15 | Initial claims | W | 1967-01-07 | 2026-09-26 | 717 | True |
| 16 | Youth unemployment | M | 1956-01-01 | 2026-09-01 | 824 | True |
| 17 | Chicago NFCI | W | 1971-01-08 | 2026-10-23 | 668 | False |
| 18 | Excess bond premium | M | 1973-01-01 | 2026-09-01 | 645 | True |
| 19 | News-based economic policy uncertainty | M | 1900-01-01 | 2026-09-01 | 825 | True |
| 20 | Real GDP | Q | 1947-01-01 | 2026-04-01 |  | True |
| 21 | Gold benchmark | M | 1960-01-01 | 2026-09-01 | 801 | True |
| 22 | WTI benchmark | M | 1982-01-01 | 2026-09-01 | 537 | True |
| 23 | Household debt service | Q | 2005-01-01 | 2026-04-01 |  | True |
| 24 | Credit-card delinquency | Q | 1991-01-01 | 2026-04-01 |  | True |
| 25 | Economic-news sentiment | D | 1980-01-01 | 2026-10-25 | 561 | False |

Rights evidence checked on 2026-10-28: [World Bank commodity dataset](https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections) and [data licenses](https://datacatalog.worldbank.org/public-licenses); [Baker–Bloom–Davis EPU license and methodology](https://www.policyuncertainty.com/us_monthly.html); [current Moody Aaa restrictions](https://fred.stlouisfed.org/series/AAA). The latter prevents treating current proprietary continuation as automatically reusable. The public research catalog is preserved at [financial_research](../financial_research/README.md).

Attribution for the public commodity data: World Bank, Commodity Price Data (Pink Sheet), October 2026 workbook, CC BY 4.0 with additional terms. Attribution for EPU: Scott R. Baker, Nicholas Bloom and Steven J. Davis (2016), “Measuring Economic Policy Uncertainty,” PolicyUncertainty.com, CC BY 4.0. The normalized schemas, monthly aggregations and declared derived transformations are changes made by this project; no provider endorsement is implied. Federal series retain agency, exact series identifier and source URL in the dictionary.
