# Month-end catch-up checkpoint

Generated 2026-09-21T21:20:40.308527+00:00. Status: **COMPLETE**.

Scope: exactly 3,654 newly added identities; the 24,387 overlapping songs and all old results remain untouched.
Source gaps are accepted: 818 months, 81,797 observations, 28,041 final identities. No rank-100 rows are invented.

## Acquisition

| Disposition | Metadata | Lyrics |
|---|---:|---:|
| Accepted | 2662 | 2321 |
| Ambiguous/quarantined | 655 | 455 |
| Wrong identity | — | 527 |
| Bad/missing text | — | 18 |
| Not found | 337 | 289 |
| API error | 0 | 44 |

Unprocessed: metadata 0; lyrics 0.
Accepted metadata coverage: 72.85%; usable lyrics: 63.52% of the 3,654-song scope.

## Classifiers

New usable targets: 2,321. All 42 features: 2,321.

| Model | Successful | Errors |
|---|---:|---:|
| lyriclens | 2321 | 0 |
| detoxify | 2321 | 0 |
| goemotions | 2321 | 0 |
| cardiff | 2321 | 0 |

Only new approved lyrics are classified, after acquisition finishes. Each failed model retains NULL features; other model results are kept.

## Final population coverage

Usable lyrics: 20,981; any classifier data: 20,981; all 42 features: 20,979.
Coverage below uses first Billboard appearance and the full 28,041-song denominator, including pending catch-up work. The 2015–2019 subset overlaps 2010–2019.

| Period | Songs | Usable lyrics | Lyrics % | Any classifier % | All 42 % |
|---|---:|---:|---:|---:|---:|
| 1958–1969 | 6808 | 4635 | 68.08 | 68.08 | 68.07 |
| 1970s | 5008 | 3617 | 72.22 | 72.22 | 72.22 |
| 1980s | 4000 | 3167 | 79.17 | 79.17 | 79.15 |
| 1990s | 3329 | 2399 | 72.06 | 72.06 | 72.06 |
| 2000s | 3065 | 2422 | 79.02 | 79.02 | 79.02 |
| 2010–2019 | 3168 | 2595 | 81.91 | 81.91 | 81.91 |
| 2015–2019 | 1650 | 1342 | 81.33 | 81.33 | 81.33 |
| 2020–2026 | 2663 | 2146 | 80.59 | 80.59 | 80.59 |

See [catch-up commands and storage](../../docs/month_end_catchup.md). Current public CSVs and research databases are unchanged. No genre assignment or longitudinal/COVID analysis is performed.

MusicBrainz replays the archived 19-song evidence before network work. Lyrics use the fixed pre-run metadata snapshot, so concurrent metadata progress cannot change matching inputs. The original matchers, clients, rates, cleaning, classifier checkpoints and token-weighted aggregation are unchanged.

Completion requires all acquisition dispositions, all four attempted model jobs per new usable lyric, verified files/outputs and protected-input hashes. Live counts alone do not establish successful completion.

Ready for genre assignment on the final 28,041-song population.
