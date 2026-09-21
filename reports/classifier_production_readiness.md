# Four-model production readiness

**READY for a separately authorized full-corpus run. Only the frozen 200-song sample has been classified by this production runner.**

BART is excluded from the production schema, executable model choices, replays and performance estimates. Earlier five-model experiments remain archived. The production panel preserves 42 separate content, emotion and sentiment features; it does not calculate CSI, MCR, hardness or consensus.

## Frozen panel and schema

The machine-readable [schema](../docs/classifier_production_schema.json) fixes labels, raw-head indices, artifact hashes, checkpoint revisions, windows and aggregation. The [operating guide](../docs/classifier_production.md) describes the local results database and resume commands. Model cards, licenses and training-domain limitations are retained in the [model specification](../docs/classifier_panel_specification.md); only its four retained models apply here.

| Model | Outputs | Context including special tokens | Aggregation |
|---|---:|---:|---|
| lyriclens | 4 | 1024 | Content-token-weighted chunk mean |
| detoxify | 7 | 512 | Content-token-weighted chunk mean |
| goemotions | 28 | 512 | Content-token-weighted chunk mean |
| cardiff | 3 | 512 | Content-token-weighted chunk mean |

All four models use their own pinned tokenizer. Balanced, contiguous, non-overlapping partitions cover every normalized token exactly once. No truncation is enabled. Limits reserve two special tokens: 1,022 content tokens for LyricLens; 510 for the other models. LyricLens retains its upstream lossy English normalization; complete coverage refers to **normalized tokens**, not preservation of all original punctuation, inflections or non-English text. The original files are untouched. Cardiff retains its documented mention/URL substitution.

The weighted mean is the production summary for every output, including emotions and sentiment. It is an average of local classifier judgments, not a calibrated severity or whole-song occurrence probability. It avoids letting one noisy chunk determine the entire song. It can dilute a single extreme verse; the unmodified chunk logits and activated scores remain available for later, separately justified alternatives. Cardiff’s weighted mean preserves its three-class sum (float32 tolerance 3e-7).

The earlier pilot compared mean, weighted mean, maximum and q90. Maximum increased Detoxify toxicity by more than 0.10 in 17 songs and obscene in 12; with only two multi-chunk LyricLens songs it is not strong evidence for a category-specific maximum rule. Longer songs also have more opportunities for a high maximum. No cross-model averaging is performed.

## Exact 200-song validation

All four models completed **200/200** songs: **800 successful song/model jobs**, **1,043 chunks**, zero failed jobs. The 180 stratified songs and 20 pre-existing sentinel songs are unchanged. Two fresh database runs reproduce all 42 song scores, processing metadata, chunk input hashes, raw logits and activated outputs **exactly** on this CPU configuration. Prior whole-song pilot maximum absolute logit difference: **0**. The coverage checks reconstruct every contiguous token range and verify the earlier independently persisted input hashes. No NaN/inf or out-of-range scores were accepted.

| Model | Chunks | Songs needing >1 chunk | Maximum chunks/song |
|---|---:|---:|---:|
| lyriclens | 202 | 2 | 2 |
| detoxify | 281 | 65 | 3 |
| goemotions | 281 | 65 | 3 |
| cardiff | 279 | 64 | 3 |

All score distributions (min/max, mean/median/SD, quantiles and saturation counts) are in [distributions.csv](classifier_production/distributions.csv). Whole-song coverage does not repair domain mismatch or model saturation. Neither agreement nor numerical reproducibility establishes construct validity.

At least 90% of sample scores are below 0.01 for: detox_threat (184/200), emotion_embarrassment (193/200), emotion_gratitude (196/200), emotion_grief (189/200), emotion_pride (195/200), emotion_relief (190/200). These can be sparse or domain-sensitive features; they are retained rather than silently dropped.

Scores above 0.99 occur in: ll_sexual_content (53/200), ll_violence (29/200), ll_explicit_language (37/200), ll_substance_use (28/200), detox_toxicity (3/200). Saturation is not cured by whole-song chunking.

Cardiff largest-score classes: negative 15/200, neutral 163/200, positive 22/200. This neutral dominance is a domain diagnostic, not a historical finding.

### Differences from prefix-only inference

| Feature | Mean absolute change | Maximum absolute change | Songs changing >0.10 | Largest-change identity | Prefix → whole |
|---|---:|---:|---:|---|---|
| ll_sexual_content | 0.0009 | 0.1272 | 1 | Macarena — Los Del Rio | 0.3148 → 0.1876 |
| ll_violence | 0.0016 | 0.3107 | 1 | Money Ain't A Thang — JD Featuring Jay-Z | 0.9970 → 0.6863 |
| ll_explicit_language | 0.0000 | 0.0018 | 0 | Macarena — Los Del Rio | 0.1063 → 0.1081 |
| ll_substance_use | 0.0007 | 0.1078 | 1 | Money Ain't A Thang — JD Featuring Jay-Z | 0.9706 → 0.8628 |
| detox_toxicity | 0.0171 | 0.3351 | 10 | No Scrubs — TLC | 0.7092 → 0.3741 |
| detox_severe_toxicity | 0.0033 | 0.1477 | 1 | Anaconda — Nicki Minaj | 0.0886 → 0.2363 |
| detox_obscene | 0.0143 | 0.3124 | 9 | America Has A Problem — Beyonce Featuring Kendrick Lamar | 0.6367 → 0.3243 |
| detox_threat | 0.0015 | 0.1294 | 1 | Skoal, Chevy, And Browning — Morgan Wallen | 0.0306 → 0.1600 |
| detox_insult | 0.0140 | 0.2406 | 12 | iPHONE — DaBaby & Nicki Minaj | 0.4227 → 0.6634 |
| detox_identity_attack | 0.0071 | 0.1959 | 5 | Gin And Juice — Snoop Doggy Dogg | 0.4567 → 0.2607 |
| detox_sexual_explicit | 0.0107 | 0.3979 | 4 | MEGATRON — Nicki Minaj | 0.0464 → 0.4443 |

These are changes in input coverage and chunk context, not evidence that higher scores are more accurate. Song-level text, identities and scores have not been manually corrected.

## Cross-model judge map

Sexual content: LyricLens sexual content ↔ Detoxify sexual explicit. Explicit/obscene language: LyricLens explicit language ↔ Detoxify obscene. Violence, threats and anger/disgust are adjacent concepts, not synonyms: a violent narrative need not threaten a reader or express anger. LyricLens alone supplies substance use. Detoxify supplies comment-domain toxicity, severe toxicity, insult and identity attack. GoEmotions supplies all 28 emotion outputs, including neutral. Cardiff supplies negative/neutral/positive sentiment. No output is discarded as redundant merely because it correlates with another.

| Pair | Pearson (200) | Spearman (200) | Pearson (core 180) | Spearman (core 180) |
|---|---:|---:|---:|---:|
| ll_sexual_content / detox_sexual_explicit | 0.330 | 0.684 | 0.363 | 0.648 |
| ll_explicit_language / detox_obscene | 0.720 | 0.655 | 0.708 | 0.617 |
| ll_violence / detox_threat | 0.104 | 0.476 | 0.102 | 0.437 |
| ll_violence / emotion_anger | 0.386 | 0.333 | 0.378 | 0.309 |
| ll_violence / emotion_disgust | 0.279 | 0.384 | 0.266 | 0.350 |
| detox_toxicity / emotion_anger | 0.562 | 0.619 | 0.553 | 0.589 |
| detox_toxicity / emotion_disgust | 0.490 | 0.566 | 0.432 | 0.527 |
| detox_insult / emotion_anger | 0.653 | 0.609 | 0.672 | 0.577 |
| detox_insult / emotion_disgust | 0.523 | 0.557 | 0.469 | 0.515 |
| sentiment_negative / emotion_sadness | 0.259 | 0.338 | 0.255 | 0.347 |

Correlations are diagnostic and sample-dependent; the sentinels affect the all-200 values. They do not establish a shared scale or independence of model errors. Weak violence/threat agreement is consistent with different constructs. Broad obscene/language agreement can coexist with disagreement over slang, narrative context and clean versions. Previous qualitative reviews still apply: comment toxicity is not lyrical content severity; emotion neutral is not a claim that lyrics are clean; tweet sentiment is not a measure of harmful content. No trend, COVID comparison or consensus outcome is estimated.

## Performance

| Model | Load (s) | Processing 200 (s) | Seconds/song | Projected 19,372 (hours) | Peak worker RSS (GiB) |
|---|---:|---:|---:|---:|---:|
| lyriclens | 5.02 | 125.32 | 0.627 | 3.37 | 1.46 |
| detoxify | 3.90 | 29.61 | 0.148 | 0.80 | 1.25 |
| goemotions | 1.93 | 28.18 | 0.141 | 0.76 | 0.88 |
| cardiff | 3.02 | 26.60 | 0.133 | 0.72 | 1.14 |

Sequential CPU float32 inference, four threads, batch size one: **3.73 minutes** across the four workers including their model loads and durable per-chunk writes. Projected full run: **5.65 hours** plus parent preflight/hash validation and orchestration. Peak worker RSS: **1.46 GiB**; the lightweight parent is additional. Memory is bounded by sequential worker processes on the 16-GiB machine. No GPU benchmark or speedup is claimed.

Pilot database: 2,523,136 bytes; simple 96.86× projection: 233.1 MiB. Projected wide CSV: 33.3 MiB; raw numerical chunk JSONL: 122.8 MiB. Allow extra space for SQLite WAL and temporary exports; existing local model weights/environments are separate. Runtime and size estimates inherit this small sample’s lyric-length mix and are approximate.

## Production safeguards and decision

The runner freezes an exact approved manifest, verifies all 19,372 source hashes and study membership, and opens research inputs read-only. It persists each completed chunk and finalizes each song/model independently in SQLite transactions. Pending/interrupted jobs resume; successful jobs skip; recorded errors require `--retry-errors`. Locks prevent concurrent writes by duplicate workers. Changed code, tokenizer/checkpoint, dependency versions, targets or lyric hashes fail closed rather than overwriting a prior run. Exception messages are not stored because they could contain input text.

The second fresh run was deliberately interrupted with SIGTERM and resumed: all 513 completed jobs and 646 persisted chunks remained byte-for-byte equivalent as database row values. A no-op rerun and interruption/failure regression tests verify resume behavior. Full population and public-dataset integrity validation is recorded in the accompanying checkpoint validation note. The separate `song_results` table joins through stable `song_id`; the public 31-column master remains unchanged. The runner has not been invoked with full scope.

**READY for the authorized panel as reproducible exploratory features**, not validated calibrated severity measurements. The next action requires a separate decision to start the full run. No further BART work is needed.
