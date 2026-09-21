# Final month-end catch-up audit

**Status: COMPLETE.** No acquisition or inference was restarted.

All 3,654 added songs have terminal metadata and lyrics dispositions. All 2,321 newly usable lyrics have four successful model results. Completion means the authorized acquisition pass finished; it does not imply every song has usable lyrics.

## Population and process evidence

28,041 final song_ids; 818 snapshots; 81,797 observations. Each date independently matches the latest available chart in its calendar month in both the raw JSON and immutable weekly database. The 355,487 weekly observations are unchanged.
815 snapshots have ranks 1–100. The charts dated 1976-12-25, 1977-01-29 and 1977-02-26 retain ranks 1–99. No invented observations, alternative chart selection or deduplication.
No catch-up worker remains active. Both metadata runs finished complete (19 offline replayed cases plus 3,635 online dispositions); lyrics finished 10 bounded-start plus 3,644 continuation dispositions. The first lyrics run’s interrupted flag is its intentional ten-asset limit, not lost work. All four classifier executions finished complete. Supervisor exit codes and independently queried databases agree.

## Metadata

| Disposition | Catch-up | Full month-end population |
|---|---:|---:|
| high_confidence | 2,662 | 22,290 |
| ambiguous | 655 | 3,963 |
| not_found | 337 | 1,787 |
| error | 0 | 1 |

Attempted: 3,654/3,654; unprocessed: 0. Catch-up acceptance: 72.85%. Full-population metadata acceptance: **22,290/28,041 (79.49%)**. The one full-population metadata error predates catch-up.

## Lyrics

| Disposition | Catch-up | Full month-end population |
|---|---:|---:|
| accepted | 2,321 | 20,981 |
| quarantined | 455 | 3,817 |
| wrong_identity | 527 | 1,809 |
| bad_missing_text | 18 | 201 |
| not_found | 289 | 1,140 |
| error | 44 | 93 |

Attempted: 3,654/3,654; unprocessed: 0. Catch-up usable coverage: 63.52%. Final usable lyrics: **20,981/28,041 (74.82%)**; unavailable/excluded: **7,060**.
All 44 catch-up API errors are terminal HTTP 503 responses, retained separately from not-found and identity/text exclusions. They may be retryable in a separately authorized pass, but no retries were executed or needed to finish this attempted-disposition scope.
Exactly 2,321 new lyric files reconcile to accepted records. There are 21,693 canonical files overall: 19,372 preserved originals plus 2,321 new files. Of these, 712 belong to removed old-population songs and remain preserved; they are excluded from final-population coverage.

## Classifiers

| Model | New successes | New errors | Final successes | Final model-specific missingness |
|---|---:|---:|---:|---:|
| lyriclens | 2,321 | 0 | 20,979 | 2 |
| detoxify | 2,321 | 0 | 20,981 | 0 |
| goemotions | 2,321 | 0 | 20,981 | 0 |
| cardiff | 2,321 | 0 | 20,981 | 0 |

New target songs and songs with all 42 features: **2,321**. Final songs with classifier data: **20,981**; with all 42 features: **20,979**. All newly usable lyrics received all four model attempts; none failed.
The only model-specific gaps remain the two accepted original LyricLens exceptions: Chinese Checkers — Booker T. & The MG's, and Snap Shot — Slave. Their four LyricLens values remain NULL because normalization becomes empty; their other 38 values are retained. No lyrics were altered and no unchanged failures were retried.
The unchanged 42-column schema, per-model checkpoint revisions, configuration/source hashes, finite/ranged scores, raw activations, exact balanced token partitions and token-weighted means were verified. No BART, CSI/MCR, hardness, consensus or combined features exist in the production outputs.

## Full-population coverage

Periods use first Billboard appearance, not release dates. Any-classifier coverage equals usable-lyrics coverage. The 2015–2019 subset overlaps 2010–2019; no historical content trends were analyzed.

| Period | Songs | Usable / any classifier | Coverage | All 42 | All-42 coverage |
|---|---:|---:|---:|---:|---:|
| 1958–1969 | 6,808 | 4,635 | 68.08% | 4,634 | 68.07% |
| 1970s | 5,008 | 3,617 | 72.22% | 3,617 | 72.22% |
| 1980s | 4,000 | 3,167 | 79.17% | 3,166 | 79.15% |
| 1990s | 3,329 | 2,399 | 72.06% | 2,399 | 72.06% |
| 2000s | 3,065 | 2,422 | 79.02% | 2,422 | 79.02% |
| 2010–2019 | 3,168 | 2,595 | 81.91% | 2,595 | 81.91% |
| 2015–2019 | 1,650 | 1,342 | 81.33% | 1,342 | 81.33% |
| 2020–2026 | 2,663 | 2,146 | 80.59% | 2,146 | 80.59% |

## Runtime and integrity

New classifier inference workers used 2358.43 seconds total (about 39.3 minutes). Peak worker RSS: 1.438 GiB. Saved chunk predictions: 12,209. Classifier database: 29,159,424 bytes.
Online metadata ran 18:23:42–20:15:40 UTC; lyrics continuation ran 18:23:42–20:38:40 UTC; classifier workers ran 20:38:42–21:18:02 UTC on September 21, 2026. The supervisor completed validation/reporting around 21:20:40 UTC: approximately 2 hours 57 minutes after launch.
**251 tests passed.** Fresh acquisition, frozen-classifier and public-export validations passed. Old lyrics, source/research/acquisition/classifier databases and all current public files match their pre-run hashes. New database hashes also remain unchanged through this audit. Identity joins, schema primary keys, foreign keys, stored evidence and file hashes were reconciled. No lyrics, caches, private databases or checkpoints are tracked by Git.
The expanded canonical file census is validated as the union of the old and catch-up manifests. The historical research validator is used with its old file-count check disabled, then the strict combined census is enforced; no database or validator is modified.

Reproduce the report with `python3 src/month_end_catchup_audit.py` after the validation commands in [the catch-up guide](../docs/month_end_catchup.md). All audit database connections are read-only. The generated JSON includes exact counts, hashes and execution records; no lyric text or private absolute paths are included.

## Next

**Month-end population acquisition/classification is complete. Ready for genre assignment on the final 28,041-song population.**
Results remain in the original databases and separate catch-up sidecars, joined by song_id for this audit. No genre assignment, public master replacement, or historical/COVID analysis was performed.
