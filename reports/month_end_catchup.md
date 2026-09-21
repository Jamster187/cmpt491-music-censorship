# Month-end catch-up checkpoint

Generated 2026-09-21T18:24:17.381147+00:00. Status: **INCOMPLETE**.

Scope: exactly 3,654 newly added identities; the 24,387 overlapping songs and all old results remain untouched.
Source gaps are accepted: 818 months, 81,797 observations, 28,041 final identities. No rank-100 rows are invented.

## Acquisition

| Disposition | Metadata | Lyrics |
|---|---:|---:|
| Accepted | 29 | 15 |
| Ambiguous/quarantined | 4 | 2 |
| Wrong identity | — | 4 |
| Bad/missing text | — | 0 |
| Not found | 3 | 3 |
| API error | 0 | 0 |

Unprocessed: metadata 3,618; lyrics 3,630.
Accepted metadata coverage: 0.79%; usable lyrics: 0.41% of the 3,654-song scope.

## Classifiers

New usable targets: 15. All 42 features: 0.

| Model | Successful | Errors |
|---|---:|---:|
| lyriclens | 0 | 0 |
| detoxify | 0 | 0 |
| goemotions | 0 | 0 |
| cardiff | 0 | 0 |

Only new approved lyrics are classified, after acquisition finishes. Each failed model retains NULL features; other model results are kept.

## Final population coverage

Usable lyrics: 18,675; any classifier data: 18,660; all 42 features: 18,658.
Coverage below uses first Billboard appearance and the full 28,041-song denominator, including pending catch-up work. The 2015–2019 subset overlaps 2010–2019.

| Period | Songs | Usable lyrics | Lyrics % | Any classifier % | All 42 % |
|---|---:|---:|---:|---:|---:|
| 1958–1969 | 6808 | 4127 | 60.62 | 60.52 | 60.5 |
| 1970s | 5008 | 3230 | 64.5 | 64.5 | 64.5 |
| 1980s | 4000 | 3011 | 75.28 | 75.22 | 75.2 |
| 1990s | 3329 | 2209 | 66.36 | 66.36 | 66.36 |
| 2000s | 3065 | 2247 | 73.31 | 73.25 | 73.25 |
| 2010–2019 | 3168 | 2236 | 70.58 | 70.55 | 70.55 |
| 2015–2019 | 1650 | 1146 | 69.45 | 69.39 | 69.39 |
| 2020–2026 | 2663 | 1615 | 60.65 | 60.53 | 60.53 |

See [catch-up commands and storage](../docs/month_end_catchup.md). Current public CSVs and research databases are unchanged. No genre assignment or longitudinal/COVID analysis is performed.

MusicBrainz replays the archived 19-song evidence before network work. Lyrics use the fixed pre-run metadata snapshot, so concurrent metadata progress cannot change matching inputs. The original matchers, clients, rates, cleaning, classifier checkpoints and token-weighted aggregation are unchanged.

Completion requires all acquisition dispositions, all four attempted model jobs per new usable lyric, verified files/outputs and protected-input hashes. Live counts alone do not establish successful completion.
