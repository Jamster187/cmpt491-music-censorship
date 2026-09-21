# Full classifier run: post-run audit

**INCOMPLETE BUT RESUMABLE: all 77,488 song/model jobs were attempted; 77,486 succeeded and two LyricLens jobs have deterministic preprocessing errors.** No workers remain active. No inference or retry was started during this audit.

## Completion

| Model | Target | Completed | Errors | Unprocessed | Saved chunks |
|---|---:|---:|---:|---:|---:|
| LyricLens | 19,372 | 19,370 | 2 | 0 | 19,517 |
| Detoxify Unbiased | 19,372 | 19,372 | 0 | 0 | 26,301 |
| GoEmotions | 19,372 | 19,372 | 0 | 0 | 26,301 |
| Cardiff sentiment | 19,372 | 19,372 | 0 | 0 | 25,730 |

All four models are available for **19,370 songs**. The 19,372-row song results table has the expected 42 numerical feature columns: 813,616 finite values in [0,1], with eight null LyricLens values across the two failed songs. There are 97,849 saved chunks and no duplicate song/model jobs or chunk keys. Successful outputs from other models remain available for both affected songs.

## Failure diagnosis

| Song | Artist | Alphabetic content of stored input | Normalized characters |
|---|---|---:|---:|
| Chinese Checkers | Booker T. & The MG's | 287 Cyrillic letters; zero ASCII letters | 0 |
| Snap Shot | Slave | 1,229 Thai letters; zero ASCII letters | 0 |

Both jobs failed before tokenization and inference with `ValueError`. Normalization-only diagnostic replays reproduced the failure twice for each input. Direct inspection of the unchanged cleaner confirmed empty normalized text and zero NLTK fallback failures. No model predictions were rerun or saved during diagnosis. These are deterministic incompatibilities with the frozen LyricLens normalization, not observed transient/runtime errors.

The language/credit combinations warrant targeted source-identity and text-quality review. Script alone does not prove a wrong match. Neither lyrics nor acquisition dispositions were changed. Do not alter the frozen model methodology to make these inputs pass.

## Integrity and frozen configuration

- `python3 -m unittest discover -s tests -v`: **218 passed**.
- Existing classifier validation with `--allow-incomplete`: **PASS** for all completed predictions, including raw activations, aggregation and complete token-range coverage.
- Strict classifier validation: **expected FAIL**, solely because two jobs are incomplete; the supervisor also correctly recorded `needs_review` rather than success.
- Independent audit: target IDs and lyric hashes exactly reconcile to all 19,372 approved assets; stored configuration matches the launch baseline and frozen commit `11ae781`; all four checkpoint/tokenizer artifact hashes match.
- Every completed job has the exact balanced contiguous token partitions, reserved special-token budget, model revision and checkpoint hash. Token-weighted means are verified from retained chunk scores. Coverage refers to model-normalized text; LyricLens retains its documented lossy English normalization.
- All approved lyric hashes were checked. Launch SHA-256 values still match the Billboard source JSON, music.db, research.db, lyrics.db and every public dataset file, including songs.csv, monthly_top100.csv and master_dataset.csv.
- Research and public-dataset validations passed: 355,487 weekly observations, 81,800 monthly observations, 818 monthly baskets and 25,363 study identities remain intact.
- Exactly the four production models occur in the job records. No BART, CSI, MCR, hardness or consensus columns occur in the production table. Frozen source/schema files are unchanged; no historical/COVID analysis or master join was performed. Earlier pilot artifacts remain preserved.

## Performance

Inference ran from 2026-09-21T05:39:07.102417+00:00 through 2026-09-21T11:10:41.724103+00:00 (about **5 h 31 m 35 s**). Including supervisor validation and integrity checks: **5 h 31 m 53 s**. This is about 2% faster than the approximately 5.65-hour estimate.

| Model | Worker elapsed seconds | Peak worker RSS (GiB) |
|---|---:|---:|
| lyriclens | 12078.69 | 1.413 |
| detoxify | 2705.58 | 1.287 |
| goemotions | 2619.42 | 1.105 |
| cardiff | 2486.12 | 1.255 |

Results database: **234,561,536 bytes (223.70 MiB)**. Peak worker RSS: **1.413 GiB**, excluding the lightweight parent/supervisor. Results remain local at `data/processed/classifier_results.db`.

## Next step

**Review the identity/language and usability of the two affected lyric assets, then explicitly decide their disposition and handling of missing LyricLens scores before joining.** The saved successful predictions are structurally valid, but the requested complete 42-feature matrix is not yet available for every song.

There are no unprocessed jobs to resume. The existing retry command below skips every successful model job and targets only the two errors, but it was **not executed and is not recommended for unchanged inputs**:

```sh
data/experiments/classifier_panel/venv/bin/python src/classifier_production.py run --scope full --retry-errors
```

An unchanged retry would take only startup/preflight/normalization time (seconds to tens of seconds) and reproduce both errors. There is no meaningful remaining runtime estimate for successful completion until the input-quality/disposition issue is resolved. No configuration, corpus or source-text change is authorized by this audit.
