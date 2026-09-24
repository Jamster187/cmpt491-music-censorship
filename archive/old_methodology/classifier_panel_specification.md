# Five-model panel specification

This is a bounded design/test using the frozen LyricLens sample: 200 songs, including 180 stratified diagnostic songs and 20 preselected sentinels. It does not choose an outcome, consensus formula, COVID breakpoint or historical estimator. All five judges see the same song identities, but their preprocessing, tokenization, context windows and training targets differ.

## Inputs and outputs

| Judge / exact checkpoint | Architecture and domain | Input / tokenizer / window used | Outputs and activation | Language / license |
|---|---|---|---|---|
| LyricLens; existing author checkpoint SHA `d272696293bc75d5a82cca2e624800456f734f57382cd9472b5974993ef860cc` | Longformer, 12 layers, hidden 768, 148.7M parameters; song-content classification | Whole lyric after the original contraction expansion, English lemmatization and ASCII filtering; Longformer byte-level BPE; 1,024 tokens including specials | Four logits and independent sigmoids: sexual, violence, substance, explicit_language; no CSI/MCR aggregation | English-oriented; author repository CC BY 4.0, linked weights lack a separate model license/card |
| Detoxify unbiased, official `toxic_debiased-c7548aa0.ckpt` | RoBERTa-base, 12 layers, hidden 768, 124.7M parameters; comment toxicity | Original lyric, case/punctuation/repetition retained; RoBERTa byte-level BPE; 512 including specials | Seven main logits/sigmoids: toxicity, severe_toxicity, obscene, identity_attack, insult, threat, sexual_explicit; all nine auxiliary-head logits/sigmoids also retained | English; Apache-2.0 official repository |
| `SamLowe/roberta-base-go_emotions` | RoBERTa-base, 12 layers, hidden 768; Reddit emotion classification | Original lyric; RoBERTa byte-level BPE; 512 including specials | 28 independent logits/sigmoids: 27 emotions plus neutral; not a softmax | English; MIT |
| `cardiffnlp/twitter-xlm-roberta-base-sentiment` | XLM-R-base, 12 layers, hidden 768; multilingual Twitter sentiment | Lyric with model-card mention/URL placeholders; XLM-R SentencePiece; 512 including specials | Three logits and joint softmax: negative, neutral, positive | Eight sentiment-training languages; wider multilingual pretraining; official XLM-T repository Apache-2.0, hub checkpoint has no separate license field/file |
| `facebook/bart-large-mnli` | BART-large, 12 encoder + 12 decoder layers, hidden 1,024; natural-language inference | Lyric chunk as premise + each frozen hypothesis; BART byte-level BPE; 1,024 **total pair** tokens | Per theme: contradiction, neutral, entailment logits and three-way softmax; theme confidence uses softmax over contradiction/entailment only (`multi_label=True` semantics) | English; MIT model card |

Full immutable revisions and SHA-256 files are in [the artifact manifest](../intermediate_reports/classifier_panel/artifacts.json). The original LyricLens Git revision is `71a40996c1021c62d12dc004cbafa3f1c5560162`; Detoxify is `d5376446b6accee5dd2d346f2d3050f9d8a69af1`. The three new hub revisions are respectively `d75048347613a25d77de8cf6412eaae9fa7b26be`, `f2f1202b1bdeb07342385c3f807f9c07cd8f5cf8`, and `d7645e127eaf1aefc7862fd59a17a5aa8558b8ce`. No third-party weights, token IDs or lyric text are distributed.

Architectural limits were checked against the downloaded configurations: RoBERTa/XLM-R have 514 position embeddings for a 512-token usable sequence; BART supports 1,024 total tokens. LyricLens has 4,098 position embeddings (roughly a 4,096-token architectural window), but its deployed inference uses 1,024; this pilot keeps that setting. Its tokenizer advertises a sentinel rather than a usable maximum, so relying on that value would be unsafe.

Every score is a model response, **not a calibrated severity measurement**. Sentiment probabilities sum to one within a chunk. Multi-label sigmoid scores do not. BART's two-class ratio can be high even when its three-way neutral probability dominates, which is why the neutral output must remain available.

## Training, intended use and limitations

**LyricLens:** accessible paper material describes over 60,000 Spotify songs; detailed annotation/split provenance remains unverified because full-paper access was blocked in the earlier evaluation. Checkpoint logs report F1 .878742 with averaging/split limitations. It loses punctuation, line structure, censored-token structure and non-English orthography. Saturation and metaphor/romance errors remain. We retain its deployed 1,024-token window rather than assuming its larger architecture window was validated for this task. [Prior inspection and sources](../../docs/lyriclens_methodology.md).

**Detoxify:** trained on the first two Jigsaw comment datasets (Wikipedia and Civil Comments). The reported 93.74 is a composite toxicity/bias AUC benchmark, not lyric accuracy. Profanity, fictional speakers, self-address, identity mention and reclaimed language can diverge from comment toxicity. Threat is not narrated violence; severe_toxicity is not violence intensity. “Unbiased” is an objective, not a guarantee. [Prior inspection and sources](../../docs/detoxify_methodology.md).

**GoEmotions:** fine-tuned from RoBERTa-base for three epochs on English Reddit annotations. The model card reports threshold-.5 test precision .575, recall .396 and F1 .450; performance varies sharply by label, with rare grief/pride/relief labels especially weak at that threshold. These are author-reported comment-domain metrics, not our lyric test. [Model card and license](https://huggingface.co/SamLowe/roberta-base-go_emotions), [training/evaluation notebook](https://github.com/samlowe/go_emotions-dataset). The source dataset describes 58k manually annotated English Reddit comments and 27 emotions plus neutral. Emotions perceived in text are not necessarily the performer's emotions or the listener's experience; irony, role-play and repetition are difficult. [Dataset paper](https://aclanthology.org/2020.acl-main.372/).

All 28 GoEmotions labels: admiration, amusement, anger, annoyance, approval, caring, confusion, curiosity, desire, disappointment, disapproval, disgust, embarrassment, excitement, fear, gratitude, grief, joy, love, nervousness, optimism, pride, realization, relief, remorse, sadness, surprise, neutral. “Neutral” here is not Cardiff's neutral sentiment, and anger/disgust are not automatically hostility or harmfulness.

**Cardiff:** XLM-R continued pretraining on roughly 198M tweets, followed by sentiment training in Arabic, English, French, German, Hindi, Italian, Portuguese and Spanish. It can tokenize more languages than those eight, but uniform accuracy is not established. [Model card](https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment). The official XLM-T repository releases these models and UMSAB, combining eight tweet-sentiment datasets; its multilingual XLM-T result is macro-F1 69.4 averaged across languages, not a lyric benchmark or an independently reproduced checkpoint score. [Official repository, licensing and results](https://github.com/cardiffnlp/xlm-t), [paper](https://aclanthology.org/2022.lrec-1.27/). Sentiment is affective polarity, not explicitness, morality or severity. A happy song can contain explicit content; grief need not be toxicity. We do not infer the author's mental health.

**BART:** BART-large fine-tuned on MultiNLI sentence-pair entailment; no supervised training on these 17 lyric themes. [Official model card](https://huggingface.co/facebook/bart-large-mnli). MultiNLI contains approximately 433k annotated pairs across written/spoken genres, not a lyric theme dataset. [Original dataset](https://cims.nyu.edu/~sbowman/multinli/). Zero-shot theme scoring reframes each label as a hypothesis; wording and neutral handling matter, and label overlap is allowed. The model card does not provide a lyric-theme accuracy or calibration result. [Zero-shot pipeline semantics](https://huggingface.co/docs/transformers/v4.51.3/en/main_classes/pipelines#transformers.ZeroShotClassificationPipeline). BART is not a multilingual judge merely because its tokenizer can encode foreign words.

The panel is not five independent experts: LyricLens/Detoxify/GoEmotions use related encoder families and broad language-model pretraining can overlap. Different fine-tuning sources do not guarantee independent errors. More agreement may mean shared lexical shortcuts, not truth.

## Frozen BART themes

[The machine-readable theme specification](../../docs/classifier_panel_themes.json) was committed before new panel inference. It freezes **17** themes, their rationale and the hypothesis template `This song contains {}.`:

romantic love; heartbreak or romantic separation; sexual content; physical violence; profanity or obscene language; drug use; alcohol use; crime or illegal activity; money or wealth; partying or nightlife; family relationships; friendship or companionship; religion or spirituality; politics or social issues; emotional distress or mental health struggles; empowerment or resilience; death or grief.

These reflect the project's content interests and the user's proposed list, not observed time patterns. Drugs and alcohol remain distinct; profanity gives an independent language comparison. Themes are allowed to overlap and are not a moral hierarchy. Any later wording/category change requires a new version and separate validation, never removal because a historical trend looks uninteresting.

## Deterministic whole-input chunking

1. Verify the original sample and lyric SHA-256 hashes. Preprocess according to each model above; reject empty output or preprocessing failures instead of returning zeros.
2. Tokenize the complete preprocessed lyric **once**, without specials and without truncation. No token IDs or decoded chunks are exported.
3. Deduct special-token overhead. For BART also deduct the longest frozen hypothesis, yielding the same premise budget for every theme.
4. Let `k = ceil(number_of_content_tokens / budget)`. Split into `k` balanced, consecutive token ranges whose sizes differ by at most one. Every token appears exactly once, including the tail; there is no overlap. Add model-specific special tokens afterward and validate the actual encoded length.
5. Save offsets, original/normalized hashes, source and normalized word counts, per-model token counts, chunk counts, input hashes, status, logits and activated chunk outputs. Repeated choruses remain repeated.

Balanced token partitions avoid a very short final fragment dominating MAX. They can still split a sentence or subword sequence across chunks and lose cross-boundary context. This is a transparent baseline, not proof that chunking preserves every semantic relation. LyricLens's original cleaning remains lossy: coverage of **all normalized tokens** does not mean every raw character survives. Cardiff placeholders also alter mention/URL strings; the other three receive raw text.

The runner keeps LyricLens's fixed 1,024 padding/global first-token attention, and dynamically pads the other models. No automatic model truncation is used. BART chunks are evaluated against every hypothesis, preserving all three NLI logits. Per-song checkpoints are resumable only with identical input/model/code/theme fingerprints.

## Aggregation alternatives, not final outcomes

Every label retains four song-level summaries:

- `mean`: average chunk response; transparent, but gives equal weight to small and large chunks.
- `token_weighted_mean`: average weighted by the number of content tokens. A reasonable descriptive candidate for overall sentiment/emotion, not a token-wise likelihood or severity measure.
- `max`: strongest detected chunk; useful as a candidate for “any occurrence” content, but sensitive to one false positive and to more opportunities in longer songs.
- `q90`: linear-interpolated 90th percentile over chunk responses. With one chunk it equals that score; with two it is near MAX, so it is not strong robust evidence.

Mean/weighted mean sentiment vectors still sum to one; MAX/q90 vectors generally do not and must not be presented as probability distributions. Chunk summaries are computed **within each model and label only**, never across models. Agreement diagnostics compare matching aggregation types and explicitly inspect mean-versus-MAX sensitivity.

## Concept families

[Machine-readable concept mapping](../../docs/classifier_panel_concepts.json) preserves original output names. Sexual content groups LyricLens sexual, Detoxify sexual_explicit and BART sexual; violence groups LyricLens violence, Detoxify threat and BART violence, with the threat/narrative distinction retained. Explicit language groups LyricLens explicit_language, Detoxify obscene and BART profanity. Substance use links LyricLens substance separately to BART drugs and alcohol. Hostility/negative affect links Detoxify toxicity/severe_toxicity/insult/identity_attack and selected GoEmotions anger/disgust/annoyance/disapproval, without equating them. Emotion, sentiment and themes also remain distinct families.

## Future agreement design (not finalized)

Use pairwise Pearson and Spearman, empirical percentile differences and top/bottom-quintile overlap to diagnose the panel. Percentiles use tied midranks `(rank−1)/(n−1)` on a declared reference set. Report the 180-song core separately from all 200 because the sentinels intentionally enrich the tails. Tiny scores can receive very different ranks: check score range/floor compression before treating rank disagreement as meaningful.

A future candidate could map each eligible model-label to an empirical CDF fitted on a frozen reference corpus, then retain the mean normalized rank **and separately** its spread (SD, range or median absolute deviation), judge count and missingness. No such consensus column is created here. The reference must not be re-ranked within each historical period, which would erase differences by construction. Missing/inapplicable judges must not become zero votes. Several labels from one model are not separate independent judges. Correlated judges should not gain credibility merely by voting together; weights or reliability adjustments require independent labelled evidence.

Kendall-style concordance could summarize rankings, but assumes judges rank a sufficiently common construct. ICC would need a defensible common interval scale; kappa would require justified categorical thresholds and is prevalence-sensitive. These model outputs are not interchangeable human raters. Pairwise rank agreement is the more transparent starting diagnostic; it still does not establish accuracy, uncertainty calibration or measurement invariance.

## Eventual output tables

Keep a run registry (`classifier_version`, model revision/checksum, tokenizer/preprocessing/chunking/theme versions, device/dtype, environment and status), a linked chunk-output table, and a song-score table keyed by **song_id + run/version**. In the experimental CSVs each model has one row per sampled song and columns `label__mean`, `label__token_weighted_mean`, `label__max`, `label__q90`. There are 59 distinct analytical model-label outputs; choosing one aggregation per construct later would yield 59 score columns, not 59 independent measurements.

A future wide view could expose `ll_sexual`, `detox_obscene`, `emotion_anger`, `sentiment_negative`, `theme_romance`, etc., once aggregation choices are approved and named in its version. Use **model-specific** token/chunk counts (`ll_token_count`, `detox_chunk_count`, etc.); a single `lyrics_token_count` is ambiguous across tokenizers. Shared metadata can include lyric hash and source word count. Preserve failed/missing status as missing values. No consensus, agreement-as-confidence, CSI, hardness or severity-index column is approved. The eventual one-row-per-song view can LEFT JOIN the unchanged master on song_id; this pilot performs no production join.

## Reproduction and local storage

Use the separate native Python 3.11 environment; do not install into the project's base Python:

```bash
python3.11 -m venv data/experiments/classifier_panel/venv
data/experiments/classifier_panel/venv/bin/pip install -r docs/classifier_panel_requirements.lock
data/experiments/classifier_panel/venv/bin/python src/classifier_panel_setup.py
```

The setup command verifies the existing pinned LyricLens and Detoxify artifacts (their earlier setup commands remain available), then fetches/checks the other three exact revisions. Everything third-party stays under ignored `data/experiments/`. The model files occupy roughly 4.0 GiB together; environments/cache need additional disk space. Only one model process runs at a time. Full measured resource use is in the generated panel report.

These commands run **only the frozen 200** and safely resume matching per-song checkpoints. They cannot select a different sample or enumerate the full corpus:

```bash
data/experiments/classifier_panel/venv/bin/python src/classifier_panel.py lyriclens
data/experiments/classifier_panel/venv/bin/python src/classifier_panel.py detoxify
data/experiments/classifier_panel/venv/bin/python src/classifier_panel.py emotion
data/experiments/classifier_panel/venv/bin/python src/classifier_panel.py sentiment
data/experiments/classifier_panel/venv/bin/python src/classifier_panel.py bart --device mps --batch-size 4
python3 src/classifier_panel_diagnostics.py
python3 src/classifier_panel_report.py
python3 src/classifier_panel_validate.py
python3 src/classifier_panel_rebuild_check.py
data/experiments/classifier_panel/venv/bin/python src/classifier_panel_verify_inputs.py
```

The BART command reproduces this Mac's device choice. CPU inference is available using `--device cpu`; use a separate archived experiment/journal when changing device or batch size, because the resumability fingerprint deliberately rejects mixed settings. The optional `classifier_panel_benchmark.py` measures CPU/MPS on four fixed theme pairs from the first sampled song, not a new sample. Model arithmetic can differ slightly by hardware; recorded CPU/MPS discrepancies and single-chunk replays quantify this rather than promising bitwise cross-device equality.

The raw public JSONL stores numerical outputs and token-span offsets/hashes, never token IDs or lyric chunks. The local journal additionally stores normalized text hashes and timings, also without text. Rebuilding diagnostics is deterministic; inference timing naturally varies. Run the complete stdlib tests and existing research/public/corpus validations before publishing. No command in this panel writes `master_dataset.csv`, a database, or a lyric file.

The measured BART MPS run emitted PyTorch's CPU-fallback warning for the `nonzero` operation used in EOS selection on this macOS version. Timing includes that fallback; it is not a pure GPU-throughput benchmark.
