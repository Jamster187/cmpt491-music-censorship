# Detoxify evaluation: same 200-song pilot

**Recommendation C: retain selected outputs from both models as complementary candidate features, not as a validated primary severity measure.** Detoxify obscene is a useful independent language benchmark; sexual_explicit offers a narrower sexual-content comparison. LyricLens addresses broader sexual themes, violence and substance use, but retains documented errors. Detoxify toxicity, threat and severe_toxicity should not replace these lyrical constructs. Neither model establishes a continuous severity scale.

## Model

English Detoxify **unbiased**, repository 0.5.3, pinned commit `d5376446b6accee5dd2d346f2d3050f9d8a69af1`; RoBERTa-base sequence classifier, 124,657,936 parameters. Official Apache-2.0 distribution; trained on the first two Jigsaw comment datasets, not lyrics. Upstream reports **93.74** on its composite toxicity/bias AUC benchmark, not accuracy or lyric performance. [Inspection, sources, label definitions, license and reproduction](../../docs/detoxify_methodology.md).

Seven returned sigmoid confidence scores: toxicity, severe_toxicity, obscene, threat, insult, identity_attack, sexual_explicit. They are not calibrated severity probabilities. No substance score, CSI, MCR or combined hardness score is introduced.

## Scope and evidence

- **200/200 successful, zero failed/missing predictions** on the exact frozen LyricLens sample (180 stratified core plus 20 preselected sentinels). No new sample was selected.
- [Predictions](../../reports/detoxify_predictions.csv), [all raw logits/sigmoids](../../reports/detoxify_raw_outputs.jsonl), [run provenance](../../reports/detoxify_run.json), [artifact hashes](../../reports/detoxify_artifacts.json), [full diagnostics](../../reports/detoxify_diagnostics.json). Raw outputs include nine auxiliary identity heads for reproducibility only.
- [50 deterministic qualitative reviews](../../reports/detoxify_review.csv): all 20 sentinels, directional differences for five overlapping pairs, each Detoxify minimum/maximum, period midpoints, Spanish cases and deterministic supplementation. Selection is score-informed, so review counts are not accuracy estimates.
- Existing accepted lyrics, all acquisition databases, the LyricLens pilot and public master remain unchanged. Only these 200 unique songs received Detoxify predictions; eight were replayed in separate input-sensitivity diagnostics.

## Score distributions: all 200

Sample standard deviation (n−1); quantiles use linear interpolation. Scientific notation preserves small nonzero values.

| Score | Min | Q05 | Q25 | Median | Mean | SD | Q75 | Q95 | Max | <.01 | >.99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| toxicity | 0.00035255 | 0.0011386 | 0.0051478 | 0.036733 | 0.21509 | 0.32232 | 0.27979 | 0.95275 | 0.99513 | 66 | 3 |
| severe_toxicity | 1.2836e-06 | 3.5842e-06 | 1.426e-05 | 5.4541e-05 | 0.0087096 | 0.044032 | 0.0002821 | 0.035184 | 0.48184 | 181 | 0 |
| obscene | 3.2385e-05 | 8.6507e-05 | 0.00062615 | 0.0036619 | 0.12752 | 0.27678 | 0.040814 | 0.89751 | 0.9837 | 123 | 0 |
| identity_attack | 5.3379e-05 | 0.00011922 | 0.00043667 | 0.0013003 | 0.017607 | 0.069641 | 0.0043211 | 0.083016 | 0.6621 | 168 | 0 |
| insult | 0.00010439 | 0.00021678 | 0.00086479 | 0.0033141 | 0.084246 | 0.18149 | 0.039513 | 0.50672 | 0.86721 | 127 | 0 |
| threat | 1.552e-05 | 3.0116e-05 | 8.7375e-05 | 0.00026155 | 0.0075795 | 0.048157 | 0.0012733 | 0.014806 | 0.55344 | 182 | 0 |
| sexual_explicit | 1.373e-05 | 4.3895e-05 | 0.00033343 | 0.0016429 | 0.037746 | 0.11502 | 0.01089 | 0.24305 | 0.88553 | 149 | 0 |

No outputs equal exactly zero or one. Threat (182/200 below .01) and severe_toxicity (181/200 below .01) are strongly compressed near zero. Sexual_explicit is below .01 for 149/200. Toxicity has three values above .99. This is not a failed model run: all logits are finite and match upstream sigmoid outputs. These sparse/confident responses still offer poor resolution for broad content severity.

### Highest and lowest identities

Full top/bottom three per label are in [the extremes table](../../reports/detoxify_extremes.csv). These are model extremes, not rankings of actual harmfulness.

| Score | Minimum identity (score) | Maximum identity (score) |
|---|---|---|
| toxicity | Hold On — Ian Gomm (0.00035255) | I Don't Like — Chief Keef Featuring Lil Reese (0.99513) |
| severe_toxicity | Are We Ourselves? — The Fixx (1.2836e-06) | I Don't Like — Chief Keef Featuring Lil Reese (0.48184) |
| obscene | It's So Hard To Say Goodbye To Yesterday — Boyz II Men (3.2385e-05) | I Don't Like — Chief Keef Featuring Lil Reese (0.9837) |
| identity_attack | Hold On — Ian Gomm (5.3379e-05) | I Don't Like — Chief Keef Featuring Lil Reese (0.6621) |
| insult | Hold On — Ian Gomm (0.00010439) | Foolish Heart — Steve Perry (0.86721) |
| threat | Are We Ourselves? — The Fixx (1.552e-05) | Cry Just A Little — Paul Davis (0.55344) |
| sexual_explicit | Hold On — Ian Gomm (1.373e-05) | Closer — Nine Inch Nails (0.88553) |

## Comparison with LyricLens

Pearson compares numerical covariation; Spearman compares ranks with ties averaged. They are descriptive correlations, without significance tests. Different label definitions, calibration and tokenization mean neither agreement nor disagreement establishes correctness.

| LyricLens | Detoxify | Pearson, 200 | Spearman, 200 | Pearson, core 180 | Spearman, core 180 |
|---|---|---:|---:|---:|---:|
| explicit_language_score | obscene | 0.729 | 0.661 | 0.722 | 0.621 |
| explicit_language_score | toxicity | 0.668 | 0.600 | 0.647 | 0.554 |
| sexual_content_score | sexual_explicit | 0.326 | 0.678 | 0.349 | 0.641 |
| violence_score | threat | 0.073 | 0.472 | 0.074 | 0.434 |
| violence_score | severe_toxicity | 0.263 | 0.440 | 0.262 | 0.416 |

- **Low agreement:** Rainbow Connection, Let It Be and What A Wonderful World are low in overlapping categories. **High agreement:** WAP, Closer and Anaconda contain direct sexual/profane material detected by both.
- **LyricLens high, Detoxify low:** My Girl sexual .632 versus .001 suggests a LyricLens romance false positive. Imagine violence .995/language .993 versus Detoxify threat .006/obscene .001 reflects negation/context. Highwire violence .999 versus threat .004 instead reflects legitimate construct differences: narrated weapons/war are not directed threats.
- **Detoxify high, LyricLens low:** Foolish Heart toxicity .916/insult .867 despite self-address and very low LyricLens scores is an obvious Detoxify construct error. He's A Liar has insult .808 but LyricLens language .002: accusation without profanity can explain that difference, rather than either model being universally wrong.
- **Narrative violence:** Murder On My Mind has LyricLens violence .997 and Detoxify threat .022; even its tail-only threat is .043. Using threat as violence would miss this narrative. Severe_toxicity is also not a violence-intensity label.
- **Sexual theme versus explicit wording:** Let's Get It On is .995 LyricLens sexual versus .011 Detoxify sexual_explicit. The narrower Detoxify target and comment domain explain why low scores cannot rule out sexual subject matter. Rosones is a clearer language-domain failure for both.

## Qualitative review

| Focus-specific judgment | LyricLens | Detoxify |
|---|---:|---:|
| plausible | 24 | 33 |
| questionable | 24 | 13 |
| clearly_wrong | 2 | 4 |

**These are not accuracy estimates or a model leaderboard.** Review was unblinded, assistant-authored and deliberately enriched for disagreements. Twenty-six cases reuse earlier full-text review evidence; 24 received targeted context and lexical inspection rather than exhaustive semantic annotation. Each row states the category focus, rationale and evidence scope; judgments across different focuses are not directly comparable. No scores were edited.

Detoxify's clear construct errors include Foolish Heart (self-address), Cry Just a Little (figurative heartbreak; threat .553), How Country Feels (courtship; threat .381), and Rosones (Spanish explicit content missed). LyricLens's clear errors in this selected set are My Girl and Rosones; its numerous questionable cases include romance/innuendo, mild language saturation and metaphor. This is compatible with useful features, not validated severity outcomes.

## Domain and input sensitivity

- **Toxicity is not content severity:** profanity in consensual sexual material, storytelling and in-group dialogue can raise toxicity without an interpersonal attack. Identity_attack requires review of target/context; auxiliary identity scores are not hate indicators.
- **Quoted speech/fictional narrators:** neither inference interface distinguishes singer, narrator, quotation or endorsement. This pilot does not independently isolate quotation effects. Narrative violence is visibly different from a directed-threat label.
- **Historical language and slang:** romance/euphemism can be nearly certain sexual presence for LyricLens but near zero for Detoxify. English profanity is often detected, but Spanish Rosones is missed by both. Macarena also has language/version ambiguity. The small sample cannot establish equal sensitivity across eras, dialects or languages.
- **Clean/version effects:** existing Smack That and Vigilante Shit texts are clean-looking/noisy relative to expectations from their titles or reputation. We evaluate the retained local text, not assumed lyrics from another release; no files were repaired or replaced.

**Truncation:** 65/200 lyrics (56/180 core) exceed Detoxify's 512-token input, compared with 2/200 for LyricLens's differently preprocessed 1,024-token input. Detoxify always sees at most 510 content tokens. The unmatched input coverage is a major confound in comparing models.

[Eight-song sensitivity results](../../reports/detoxify_sensitivity.csv) preserve original replay, unique-line and final-510-token scores separately. All eight original replays agree within 1e-6. Because I Got High obscene changes .275 → .800 for the tail; Survivor .131 → .007. Removing repeated lines changes How Country Feels threat .381 → .158, while Foolish Heart insult remains high (.867 → .955). These probes change context as well as repetition/position, so they demonstrate input sensitivity without isolating a single causal mechanism. No alternative aggregation or preprocessing is approved here.

| Score | Spearman with word count, core 180 |
|---|---:|
| toxicity | 0.591 |
| severe_toxicity | 0.672 |
| obscene | 0.691 |
| identity_attack | 0.548 |
| insult | 0.527 |
| threat | 0.538 |
| sexual_explicit | 0.632 |

Positive length associations mix content, period, repetition and truncation; they are not estimates of length bias alone. A later validated chunking/context strategy would be needed before interpreting whole-song measures.

## Broad-period diagnostic only

Means below use **only the 180-song stratified core**, excluding the 20 content-selected sentinels. Period is first Billboard appearance, not release date. Full medians and all-200/core distributions are in the diagnostics JSON. These tiny, unweighted strata are not historical indices and support no COVID/trend claim.

| Period | n | Truncated | Toxicity | Severe | Obscene | Identity attack | Insult | Threat | Sexual explicit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1958–1969 | 26 | 0 | 0.0866 | 0.0001 | 0.0073 | 0.0051 | 0.0444 | 0.0009 | 0.0057 |
| 1970s | 26 | 3 | 0.0428 | 0.0001 | 0.0061 | 0.0013 | 0.0108 | 0.0022 | 0.0044 |
| 1980s | 26 | 4 | 0.2163 | 0.0001 | 0.0187 | 0.0030 | 0.1258 | 0.0226 | 0.0016 |
| 1990s | 26 | 8 | 0.1426 | 0.0008 | 0.0759 | 0.0034 | 0.0403 | 0.0014 | 0.0319 |
| 2000s | 26 | 13 | 0.2486 | 0.0036 | 0.1486 | 0.0155 | 0.0647 | 0.0037 | 0.0388 |
| 2010–2019 | 25 | 15 | 0.3252 | 0.0240 | 0.2357 | 0.0353 | 0.1220 | 0.0178 | 0.0458 |
| 2020–2026 | 25 | 13 | 0.3638 | 0.0091 | 0.2777 | 0.0358 | 0.1195 | 0.0079 | 0.0318 |

The 1980s threat mean is strongly affected by the Cry Just a Little false positive; the 2010s similarly include How Country Feels. Truncation is 0/26 in the earliest core stratum but 15/25 in 2010–2019 and 13/25 in 2020–2026. Differences in observed period means can therefore reflect content mix, input length and model artifacts; this evaluation cannot disentangle them.

## Performance

Native Apple Silicon CPU, four threads, float32, batch size one: **20.92 seconds for 200 songs**, mean **0.1046 seconds/song** including tokenization/predict, plus 2.10 seconds model initialization. Peak process RSS was **1.32 GiB** (includes loading and Python), on a 16-GiB machine.

Simple extrapolation to 19,372 songs: **33.8 minutes CPU** for the same prefix-only method, excluding setup and other pipeline work. Sample length mix, thermal load and any future chunking can change that estimate. GPU/MPS was not benchmarked; no GPU speedup is assumed. Full-corpus computation appears practical on this machine, but scientific validity remains the constraint.

The checkpoint occupies 498,707,273 bytes (~476 MiB). Pilot prediction CSV plus all-logit JSONL occupies 322,382 bytes; proportional full-corpus output would be about 29.8 MiB, before indexing or extra diagnostics. No model files or lyrics are distributed.

## Decision and next requirement

**C — selected complementary outputs.** Use Detoxify obscene as an independent language benchmark and sexual_explicit as a narrower comparison; retain LyricLens category scores only as experimental candidates for the broader constructs Detoxify lacks. Neither overall toxicity nor CSI/MCR should become the primary outcome. Before production, define a blinded human rubric for content presence, severity and context; evaluate truncation/language handling and category-specific validity against that rubric. This is a recommendation for the next decision, not implementation of a new classifier.

Validation completed: **192 tests passed**; research database, public exports, all 19,372 lyric files, original LyricLens artifacts, Detoxify score reconciliation and deterministic diagnostic rebuilds passed. No lyrics, caches, databases, model files or credentials are staged for publication.

Validation commands: `python3 -m unittest discover -s tests -v`, `python3 src/detoxify_evaluation.py validate`, `python3 src/detoxify_validate.py`, `python3 src/lyriclens_validate.py`, `python3 src/public_dataset.py validate`, and `python3 src/research.py validate`. Together, these validators check deterministic diagnostics/review/report regeneration, artifact and corpus integrity, raw-score reconciliation and public-output safety. Full-corpus classification and historical analysis have not started.
