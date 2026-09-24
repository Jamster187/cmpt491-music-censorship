# Four-model classifier panel

The frozen production panel is **LyricLens, Detoxify Unbiased, GoEmotions and Cardiff sentiment**. BART is excluded. We retain 42 separate numerical features, without CSI, MCR, hardness or consensus. The [200-song readiness report](../archive/intermediate_reports/classifier_production_readiness.md) records the evidence and benchmark. The full corpus is now classified. The user accepted two deterministic LyricLens
normalization failures as documented missingness: 19,370 songs have all four
models and two retain their other three models. See the
[accepted-missingness policy](classifier_accepted_missingness.json). Do not retry
these unchanged inputs. The 42 features are published in the master CSV. The
original failure records remain unchanged; accepted completeness is validated
by the public exporter rather than rewriting the frozen runner’s strict validator.

## Outputs

The authoritative [JSON schema](classifier_production_schema.json) includes exact checkpoint revisions, model/tokenizer SHA-256 hashes, label order, activation and raw-head mapping.

| Model | Numerical columns |
|---|---|
| LyricLens | `ll_sexual_content`, `ll_violence`, `ll_explicit_language`, `ll_substance_use` |
| Detoxify | `detox_toxicity`, `detox_severe_toxicity`, `detox_obscene`, `detox_threat`, `detox_insult`, `detox_identity_attack`, `detox_sexual_explicit` |
| GoEmotions | `emotion_admiration`, `emotion_amusement`, `emotion_anger`, `emotion_annoyance`, `emotion_approval`, `emotion_caring`, `emotion_confusion`, `emotion_curiosity`, `emotion_desire`, `emotion_disappointment`, `emotion_disapproval`, `emotion_disgust`, `emotion_embarrassment`, `emotion_excitement`, `emotion_fear`, `emotion_gratitude`, `emotion_grief`, `emotion_joy`, `emotion_love`, `emotion_nervousness`, `emotion_optimism`, `emotion_pride`, `emotion_realization`, `emotion_relief`, `emotion_remorse`, `emotion_sadness`, `emotion_surprise`, `emotion_neutral` |
| Cardiff | `sentiment_negative`, `sentiment_neutral`, `sentiment_positive` |

LyricLens, Detoxify and GoEmotions return sigmoid scores; Cardiff returns a softmax distribution. These are classifier judgments, not demonstrated calibrated severity probabilities. All raw logits and activated heads are preserved per chunk. Detoxify's nine auxiliary identity heads remain in the raw 16-head arrays, but are **not** nine extra production analytical features. Label mappings explicitly account for the upstream LyricLens substance/language ordering and Detoxify identity-attack/threat ordering.

## Whole-song inputs and aggregation

Each model uses its own pinned tokenizer, with `truncation=False`. Content budgets are 1,022 tokens for LyricLens and 510 for each other model, reserving two special tokens. We divide the complete token sequence into the minimum number of contiguous chunks that fit, distributing tokens as evenly as possible. There is no overlap or omitted tail. Context boundaries can still separate related phrases.

Every production feature uses a **content-token-weighted mean** of its chunk scores. This provides a whole-song profile and retains Cardiff's sum-to-one property. A brief extreme verse can be diluted; its original score is still available in the chunk table. Mean, maximum and q90 alternatives remain in the earlier pilot, not additional production columns. We do not interpret a chunk average as the probability that content occurs anywhere in a song.

Coverage is complete **after each model's normalization**. LyricLens retains its original lowercasing, contraction expansion, English tokenization/lemmatization and alphabetic filtering. It therefore removes some original language information; chunking cannot repair this. Cardiff retains the model-card mention/URL substitution. Detoxify and GoEmotions receive the stored text directly. None of these operations modifies the source files.

## Local environment and provenance

Use the existing isolated `data/experiments/classifier_panel/venv` (Python 3.11.8, torch 2.7.1, transformers 4.51.3). Its dependency lock is [classifier_panel_requirements.lock](classifier_panel_requirements.lock). This runner reuses the four already downloaded checkpoints, requires no installation/network calls, and does not load or validate a BART checkpoint. Artifact locations in the JSON schema are repository-relative, ignored local locations.

CPU float32, batch size one, four threads, evaluation mode, fixed seed 491 and deterministic PyTorch algorithms are fixed. Exact reruns are checked on this environment; bitwise equivalence is not promised across different hardware or dependency versions. A run fingerprints its source modules, schema, dependencies, NLTK resources, target lyric hashes and scope. Different configuration must use a separately versioned artifact, not overwrite an existing run.

## Archived inference commands

The full-scope invocation below has already completed. These commands document
the resumable infrastructure; **do not retry the two accepted LyricLens exceptions**:

```sh
data/experiments/classifier_panel/venv/bin/python src/classifier_production.py run --scope full
```

Run that exact command again to resume. Successful song/model combinations skip without loading that model when it has no remaining work. Pending or interrupted jobs resume from persisted chunks. Recorded errors remain visible and are retried only when requested:

```sh
data/experiments/classifier_panel/venv/bin/python src/classifier_production.py run --scope full --retry-errors
data/experiments/classifier_panel/venv/bin/python src/classifier_production.py status --scope full
data/experiments/classifier_panel/venv/bin/python src/classifier_production.py validate --scope full
```

Use `validate --scope full --allow-incomplete` to validate successful results in an unfinished run. Use Ctrl-C to interrupt the parent and worker. Database transactions also preserve committed work if a process exits unexpectedly. A surviving worker holds a model lock; do not delete lock files to bypass an active process. Exceptions store only the exception type, never potentially lyric-containing error messages.

The bounded validation commands use **exactly the original 200 songs**:

```sh
data/experiments/classifier_panel/venv/bin/python src/classifier_production.py run --scope pilot
data/experiments/classifier_panel/venv/bin/python src/classifier_production.py run --scope pilot --db data/experiments/classifier_production/replay.db
data/experiments/classifier_panel/venv/bin/python src/classifier_production.py validate --scope pilot
data/experiments/classifier_panel/venv/bin/python src/classifier_production_noop.py
python3 src/classifier_production_report.py
```

The report command compares the two fresh runs and the archived four-model whole-song pilot, then deterministically exports numerical evidence. It never invokes inference.

## Local database

Full results will be stored at `data/processed/classifier_results.db`. Pilot results are at `data/experiments/classifier_production/pilot.db` and `replay.db`. All are ignored by Git.

- `targets`: exact approved usable-lyrics manifest, stable `song_id`, source hash and word count. Full scope requires 19,372 high-confidence successes in the 25,363-song study population; every source file hash is checked before starting.
- `jobs`: one row per song/model, status, attempt count, token/chunk counts, normalization hash and failure type. One model's failure does not discard another's success.
- `chunk_predictions`: offsets, input-token count/hash, raw logits, activated outputs and mapped scores, persisted after each chunk. No text or token-ID arrays.
- `song_results`: one row per `song_id`, 42 nullable scores and processing metadata. Metadata includes classifier version, lyric hash/word count, and each model's status, token/chunk counts, normalization hash, checkpoint revision/hash. Unfinished/failed models have null scores; they are never replaced with zero.
- `run_config` and `executions`: frozen configuration and measured worker timings/status/memory. SQLite uses WAL, full synchronization and transactions, with process locks against concurrent writers.

`song_results` joins to `master_dataset.csv` by `song_id` through the public exporter. No inference command modifies that CSV, research.db, Billboard data or lyrics.
The separately authorized public exporter now performs the score join. Incremental
inference output and processing evidence remain local; only the approved 42
features are included in the public master. The committed pilot artifacts contain only numerical predictions, hashes and processing metadata.

The completed-run no-op proof records unchanged table digests in the ignored pilot directory. The committed `reports/classifier_production/validation.json` preserves that evidence alongside replay and artifact hashes. When the original local `interrupt_before.json` snapshot is present, report rebuilding also verifies preservation of all jobs and chunks recorded before the deliberate SIGTERM test. Report rebuilding requires the original local pilot databases and this proof; public readers can inspect the committed numerical artifacts without possessing the lyrics or model weights.
