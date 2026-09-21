# Detoxify pilot: model inspection and reproduction

This is a bounded evaluation of the **same 200 songs** already evaluated with LyricLens. It does not authorize full-corpus scoring or change the public dataset. Results describe model responses, not historical trends or COVID effects.

## Model and provenance

We selected English **Detoxify unbiased**, repository version 0.5.3 at commit `d5376446b6accee5dd2d346f2d3050f9d8a69af1`. The official checkpoint is [`v0.3-alpha/toxic_debiased-c7548aa0.ckpt`](https://github.com/unitaryai/detoxify/releases/download/v0.3-alpha/toxic_debiased-c7548aa0.ckpt). Full hashes, file sizes, checkpoint configuration and tokenizer revision are in [the artifact manifest](../reports/detoxify_artifacts.json). Code and model are offered through the [Apache-2.0 repository](https://github.com/unitaryai/detoxify/blob/d5376446b6accee5dd2d346f2d3050f9d8a69af1/LICENSE); we do not redistribute either. The [base RoBERTa model card](https://huggingface.co/FacebookAI/roberta-base) lists MIT. The base tokenizer/config is pinned to `e2da8e2f811d1448a5b465c236feacd80ffbac7b`.

The model is RoBERTa-base with a sequence-classification head: 12 transformer layers, 768 hidden dimensions, 12 attention heads, 124,657,936 parameters in this checkpoint. It has 16 output logits: seven main labels followed by nine auxiliary identity labels. Only the seven main labels are returned by upstream `predict`; our raw artifact also preserves the auxiliary outputs, without using them as analytical features. These are identity-mention training targets, not additional hate ratings. [Architecture/configuration](https://github.com/unitaryai/detoxify/blob/d5376446b6accee5dd2d346f2d3050f9d8a69af1/configs/Unintended_bias_toxic_comment_classification_RoBERTa_combined.json).

## Training and performance

The updated checkpoint combines the 2018 Jigsaw Wikipedia-comment dataset and the 2019 Jigsaw unintended-bias Civil Comments dataset. The latter contains news-site comments from 2015–2017; its seven annotations are fractions of crowd workers assigning each attribute. The published Civil Comments training split has 1,804,874 examples. This is the source dataset size, not an independently reproduced count of checkpoint training examples. [Civil Comments documentation](https://www.tensorflow.org/datasets/catalog/civil_comments).

The checkpoint's combined-data configuration does not enable soft labels. The inspected loader defaults to thresholding annotations at 0.5, marking missing labels separately. It weights examples using toxicity and identity membership, and trains auxiliary identity targets. Therefore, annotation fractions in the source dataset must not be mistaken for calibrated continuous outputs from this checkpoint. We did not retrain the model or independently reproduce its original training split. [Loader and weighting implementation](https://github.com/unitaryai/detoxify/blob/d5376446b6accee5dd2d346f2d3050f9d8a69af1/src/data_loaders.py).

Upstream reports **93.74** for the updated unbiased checkpoint on the competition test set. This is **not 93.74% accuracy**, not seven-label F1, and not a lyric-domain result. The metric combines 25% overall toxicity ROC-AUC with 75% bias metrics: subgroup, background-positive/subgroup-negative, and background-negative/subgroup-positive AUCs, aggregated with power means (power −5). No per-label lyric validation or score calibration is established. [Reported benchmark](https://github.com/unitaryai/detoxify#readme), [metric implementation](https://github.com/unitaryai/detoxify/blob/d5376446b6accee5dd2d346f2d3050f9d8a69af1/model_eval/compute_bias_metric.py), [Borkan et al., 2019](https://arxiv.org/abs/1903.04561).

## What the scores mean

Each returned value is a separate sigmoid of a classifier logit. Labels can overlap and scores do not sum to one. They are **uncalibrated classification confidence scores**, not amounts of harmful content or calibrated severity probabilities.

| Output | Intended comment construct | Limit for lyrics |
|---|---|---|
| toxicity | Broad rude/disrespectful/unreasonable comment response | Profanity, self-address and fictional speakers need not be interpersonal toxicity |
| severe_toxicity | Particularly toxic comments | Not physical violence severity |
| obscene | Obscene/profane language | Useful overlap with language content; misses some clean/slang/non-English forms |
| threat | Threatening comments | Narrated violence, negation and metaphor are different constructs |
| insult | Insulting comments | Self-criticism or a character's dialogue can be misread |
| identity_attack | Attacks concerning identity | Identity mention, reclaimed slurs and in-group address require context |
| sexual_explicit | Explicit sexual comment content | Narrower than romance or general sexual subject matter |

There is **no substance-use output** and no CSI/MCR. We calculate no combined score. Label meanings follow the [Jigsaw data schema](https://www.kaggle.com/competitions/jigsaw-unintended-bias-in-toxicity-classification/data); the lyric limitations are our interpretation. The model is independently trained from LyricLens, but neither is independent ground truth for the other.

## Input behavior and domain limits

Upstream passes the original string to `RobertaTokenizer` with padding and truncation. Our pinned tokenizer limits sequences to **512 tokens including two special tokens** (510 content tokens); right truncation keeps the prefix. Case, punctuation, line breaks, repeated choruses and non-English text are retained. No LyricLens lemmatization or ASCII filtering is applied. This differs materially from LyricLens's normalized 1,024-token input, so disagreements cannot all be attributed to model weights. [Inference implementation](https://github.com/unitaryai/detoxify/blob/d5376446b6accee5dd2d346f2d3050f9d8a69af1/detoxify/detoxify.py).

Comment moderation is a major domain mismatch for lyrics. Narrators, quotation, fictional violence, consensual sexual language, humor and reclaimed language need contextual interpretation. Older euphemisms, modern slang and non-English songs lack demonstrated comparable sensitivity. Upstream explicitly warns that swearing can trigger toxicity regardless of tone or intent and that minority groups may be disproportionately affected. “Unbiased” names the training objective; it is not a guarantee. Upstream positions the models for research and representative-data fine-tuning, not unquestioned automated decisions. [Intended use and limitations](https://github.com/unitaryai/detoxify#limitations-and-ethical-considerations).

## Reproduction

Dependencies live in an ignored, separate native-arm64 Python 3.11 environment. The project environment is unchanged. From the repository root, with the existing private lyric corpus:

```bash
python3.11 -m venv data/experiments/detoxify/venv-arm64
data/experiments/detoxify/venv-arm64/bin/pip install -r docs/detoxify_requirements.lock
data/experiments/detoxify/venv-arm64/bin/python src/detoxify_setup.py
python3 src/detoxify_evaluation.py validate
python3 src/detoxify_diagnostics.py
python3 src/detoxify_report.py
```

Use a native Python executable on Apple Silicon; the measured run used Python 3.11.8. `setup` downloads only pinned official model/source/tokenizer artifacts into ignored storage, verifies full SHA-256 checksums and reuses matching files. No lyrics are downloaded.

For a **fresh experimental workspace without existing Detoxify prediction artifacts**, the one-time inference command is:

```bash
data/experiments/detoxify/venv-arm64/bin/python src/detoxify_evaluation.py run
data/experiments/detoxify/venv-arm64/bin/python src/detoxify_sensitivity.py
```

`run` refuses to overwrite existing predictions. An intentional rerun requires first archiving the existing Detoxify evaluation outputs outside tracked report paths. The runner pins the original sample and LyricLens prediction hashes, checks every sampled lyric hash and has no full-corpus option. Inference is offline, CPU float32, four threads, one song per call. It calls upstream `predict` unchanged through a local safe loader (`torch.load(weights_only=True)`). The only compatibility adjustment removes an old serialized position-ID buffer after verifying exact equality with the current deterministic buffer; all learned weights load strictly. The initial strict-load attempt stopped before prediction because of this legacy buffer, then the verified adapter completed 200/200.

The raw JSONL contains all 16 logits/sigmoids and seven upstream scores, **no input text**. CSVs retain song identities, sample metadata, input lengths, timing and version fields. Run provenance records hashes, dependencies and measured resource use. The eight-song sensitivity experiment repeats original inference and separately tests unique-line and tail inputs; it never changes stored lyrics or original scores. Removing repeated lines is a diagnostic intervention, not an approved preprocessing rule.

The review is a deterministic, unblinded assistant qualitative assessment: 26 prior full-text review records plus 24 targeted context/lexical inspections, not 50 new exhaustive human annotations. Judgments are provisional and focus-specific. A blinded, independently annotated rubric remains necessary before selecting a primary research outcome.
