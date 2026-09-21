# LyricLens pilot: inspection and interpretation

This is a bounded classifier evaluation, not a historical result or approval for
full-corpus scoring. The public dataset and accepted lyrics remain unchanged.
Only 200 distinct study assets were classified, with five of those replayed for
hardware/reproducibility checks. No new content or hardness index was invented.

## Inspected sources and access limits

- [LyricLens repository, pinned commit](https://github.com/su1zihan/LyricLens/tree/71a40996c1021c62d12dc004cbafa3f1c5560162): inspected all five source files.
- [Paper: LyricLens: An Interactive System for Multi-Label Music Content Rating](https://openreview.net/pdf?id=UzDOCp6R40): its indexed abstract/first-page text was accessible. The PDF and OpenReview API returned HTTP 403/browser challenges; **full-paper inspection was not possible**. Do not present the findings below as a complete paper replication.
- [Workshop programme](https://aiformusicworkshop.github.io/neurips2025/): lists this work as an accepted NeurIPS 2025 AI4Music demo, not a main-conference model benchmark.
- [Author-linked checkpoint folder](https://drive.google.com/drive/folders/1EQlMFnAieKLeGEQR0ViQdk1Su2P8mjPy): inspected configuration, tokenizer files, weights, and trainer-state JSON. No optimizer or executable pickle files were loaded.
- [Repository license](https://github.com/su1zihan/LyricLens/blob/71a40996c1021c62d12dc004cbafa3f1c5560162/LICENSE): CC BY 4.0, attributed to Kai Yu Lu, Malhar Sham Ghogare, Zihan Su, and Shanu Sushmita. This is the stated license for the authors' work and the basis for the local research evaluation. The linked model folder has no separate license/model card; base-model and training-data provenance are not fully documented. This is not a license claim over third-party lyrics. Model/source files are not redistributed here.

The paper's accessible abstract describes a dataset of over 60,000 Spotify songs
and four categories. Exact training subset, annotation source/process, annotation
agreement, category definitions, class balance, split strategy, deduplication,
artist overlap, and overlap with our Billboard corpus were **not verified**.
Neither training code nor labelled training/test data is in the inspected GitHub
repository. Absence from inspected artifacts is not proof of absence from the
unavailable paper. There is no verified temporal holdout or probability-calibration
result in the material we could inspect.

## Architecture and preprocessing

The actual checkpoint is `LongformerForSequenceClassification`: 12 layers,
768 hidden dimensions, 12 attention heads, attention windows of 512, four outputs,
and 148,662,532 parameters. Config declares `multi_label_classification` and
float32 weights, with Transformers 4.51.3. The
[Longformer implementation](https://huggingface.co/docs/transformers/v4.51.3/en/model_doc/longformer)
uses local attention plus selected globally attending tokens. The checkpoint's
base-pretraining identity is not explicitly recorded; do not infer an exact
base-model revision from architecture alone.

The app expands contractions, lowercases, tokenizes each line, keeps alphabetic
tokens, POS-tags and lemmatizes them, joins lines, and removes non-ASCII letters.
It retains repetition but loses punctuation, line structure, some censored-token
structure, and non-English orthography. Silent NLTK fallbacks in the UI can change
preprocessing; this pilot checked resources and monitored failures (none occurred).
English lemmatization and slang handling need validation rather than an assumption
of temporal neutrality. No controlled clean/explicit or slang substitutions were
performed, and source lyrics were never edited.

Inference pads/truncates to **1,024 tokens**, despite the configuration supporting
longer positions. Only the first token has global attention. Dropout is disabled;
batch size is one. Empty normalized input is returned as zeros by the app; our
wrapper refuses to treat such a case as a successful prediction. The pilot loads
only inspected definitions, not the Streamlit application's top-level code.

## What the outputs mean

Raw outputs are four independent sigmoid transforms of logits, mathematically in
[0,1] and not constrained to sum to one. They are **model confidence scores for
category presence**, not demonstrated calibrated probabilities of an externally
defined event, and not measured intensity/frequency of content. Binary-label
confidence can saturate after a single mention. A high-confidence mild mention
can outrank a more severe but uncertain example.

The authors' code maps output indices as sexual, violence, substance, language.
The checkpoint itself uses generic `LABEL_0` through `LABEL_3`; we preserved the
code's mapping, and face checks support it, but no semantic training-label mapping
was supplied independently.

The experimental CSV exposes raw sigmoid scores as `sexual_content_score`,
`violence_score`, `explicit_language_score`, and `substance_use_score`. The local
JSONL also retains the original ordered logits, raw probabilities, and complete
upstream result object, without text.

**There are two different CSI formulas in the repository:**

- README-described `CSI` = 100 × mean(raw category probabilities). We record this exact formula as `CSI`.
- App `app_CSI` = mean(100 × max(0, 2p − 1)). Each raw probability below 0.5 becomes zero; the rest is linearly rescaled. We retain the app's actual result separately.

Neither CSI is a learned model head. Both are derived averages, with equal category
weights and no validated interval-scale severity interpretation. They also combine
number of categories with confidence, not necessarily explicitness intensity.

`MCR` is the **actual app rating**, computed from the rescaled scores divided by
100. It uses the maximum score: M-E ≤0.05; M-P up to 0.40; M-T up to 0.70; M-R up
to 0.95; M-AO above 0.95, or when at least two scores exceed 0.85. These thresholds
therefore differ from applying the same rating helper to raw probabilities. They
are rule-based age-rating categories, not learned clinical/developmental standards.
The separate CSV rating utility coerces missing/nonnumeric scores to zero; it was
not used, because failed predictions must not be silently labelled clean.

## Reported performance and reproducibility limits

The downloaded trainer log records a best validation `eval_f1` of **0.878742** at
step 2392 (epoch 4), precision 0.882606, recall 0.874911, `eval_accuracy` 0.723618,
and Hamming loss 0.081180. At step 3588 (epoch 6), logged F1 is 0.876314. These are
**checkpoint-log metrics, not independently reproduced test results**. The F1
averaging method, exact accuracy definition, and evaluation labels/split cannot
be established from this log. The state names step 2392 as best but ends at 3588;
without a weight manifest we cannot independently identify which epoch's weights
were published. We identify the downloaded weights by SHA-256 instead.

Weights occupy 594,684,336 bytes; only inference assets and trainer JSON were
needed, not the README's advertised multi-gigabyte training bundle. Exact Git
revision, Drive file IDs, and hashes are in [the artifact manifest](../reports/lyriclens_artifacts.json).
The complete resolved environment is [pinned here](lyriclens_requirements.lock).
Core versions are Python 3.11.8 (native arm64), PyTorch 2.7.1, Transformers 4.51.3,
Safetensors 0.5.3, NLTK 3.8.1, NumPy 1.24.3, and pandas 2.1.0. Streamlit and
unused plotting/classical-ML dependencies were not installed. A pre-existing
Intel Python could not install the chosen PyTorch version; a separate native
Python environment solved this without changing project environments. Certificate
verification used certifi; TLS verification was not disabled.

## Sample and review design

Period means first Billboard appearance, not release year. Select 180 songs from
19,372 checksum-verified usable assets: 26 per period through the 2000s, then 25
each for 2010–2019 and 2020–2026. Within each period, cross rank halves with lyric
word-count thirds, order candidates by SHA-256 of a fixed seed plus song ID, and
rotate through the six cells. Add 10 expected-mild and 10 expected-content named
sentinels, fixed before prediction and excluded from the random core. Expectations
are not ground truth. This balanced diagnostic design is **not** a population-
weighted sample. No selection depends on a model score.

Post-inference review selects 45 songs: all sentinels, each category's extremes,
low/middle/high CSI, period representatives, and intermediate CSI examples.
Two additional Spanish-text/version checks (Rosones and Macarena) bring the total
to 47. The assistant read every unique nonblank line of these local lyrics (repeated
lines displayed once). The review is qualitative and **not independent human
annotation**. It cannot estimate accuracy or replace a blinded, multi-rater
validation set. `correct` means broadly plausible category-presence detection;
it does not endorse CSI/MCR severity. Cases can be correct for presence yet
misleading when interpreted as severe content. Notes flag questionable category
responses and supplied-text problems without changing lyrics or scores.

## Reproduce this pilot only

Use a native Python 3.11 executable and keep everything in the ignored directory:

```bash
python3.11 -m venv data/experiments/lyriclens/venv-arm64
data/experiments/lyriclens/venv-arm64/bin/python -m pip install -r docs/lyriclens_requirements.lock
data/experiments/lyriclens/venv-arm64/bin/python src/lyriclens_setup.py
python3 src/lyriclens_evaluation.py sample
data/experiments/lyriclens/venv-arm64/bin/python src/lyriclens_evaluation.py run
data/experiments/lyriclens/venv-arm64/bin/python src/lyriclens_benchmark.py
python3 src/lyriclens_diagnostics.py
python3 src/lyriclens_validate.py
python3 -m unittest discover -s tests -v
```

The first `python3.11` must report `arm64` on this Mac. On this machine the native
interpreter is the Python framework installation, whereas the `/usr/local` one is
Intel. Existing raw prediction evidence causes `run` to refuse a rerun; preserve
it before a separately versioned replication. This is deliberately not a
full-corpus command. All lyrics/checkpoints/NLTK data stay local. Timing fields
are measured and will vary; deterministic sample IDs and CPU score reproducibility
are checked separately. No command writes `master_dataset.csv` or research.db.
