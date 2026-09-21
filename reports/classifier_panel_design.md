# Five-classifier judge panel: design and 200-song test

**The five-model pilot is operational, but not yet approved for full-corpus classification.** All five judges evaluated the exact frozen 200 songs with deterministic whole-input chunking. Keep the individual outputs and aggregation alternatives. The immediate methodological blocker is BART's neutral-dominant high theme scores; validate neutral handling and label-specific aggregation with a blinded content/context review. BART memory must also be bounded before a long run. No consensus or hardness score was created.

## Classifiers and conceptual scope

[Complete specification, exact checkpoints, training data, licenses, limitations, concept mapping and rebuild commands](../docs/classifier_panel_specification.md). [Pinned file hashes](classifier_panel/artifacts.json).

| Judge | Input | Numerical outputs retained | Principal limitation |
|---|---|---|---|
| LyricLens | English-normalized lyric; Longformer, 1,024 tokens/chunk | Four logits/sigmoids: sexual, violence, language, substance | Lossy normalization; saturation/metaphor errors; training-label provenance limits |
| Detoxify unbiased | Original lyric; RoBERTa, 512 tokens/chunk | Seven main logits/sigmoids plus nine auxiliary outputs | Comment toxicity differs from lyrical content; threat is not narrated violence |
| SamLowe GoEmotions | Original lyric; RoBERTa, 512 tokens/chunk | 28 emotion/neutral logits and independent sigmoids | Reddit emotions; rare labels and narrator/context ambiguity |
| Cardiff multilingual sentiment | Mention/URL-normalized lyric; XLM-R, 512 tokens/chunk | Negative, neutral, positive logits and joint softmax | Tweet polarity, not harmfulness; uneven language transfer |
| BART-large-MNLI | Lyric premise plus each theme hypothesis; BART, 1,024 total pair tokens | Three NLI logits/softmax per theme and independent two-class theme confidence | Prompt-dependent entailment, not supervised lyric-theme truth; English |

The panel has **59 model-label outputs**, not 59 independent dimensions or five interchangeable raters. Concept families group sexual content, violence, explicit language, substance use, hostility/negative affect, emotion, sentiment and themes without equating their labels. All original outputs survive; no cross-model averaging is performed.

## Frozen BART themes

Frozen in commit `88eb28b` before new panel inference. Template: `This song contains {}.`. `multi_label=True` semantics score every theme independently. [Versioned labels and rationale](../docs/classifier_panel_themes.json).

| Stable theme ID | Hypothesis label |
|---|---|
| romance | romantic love |
| heartbreak | heartbreak or romantic separation |
| sexual | sexual content |
| violence | physical violence |
| profanity | profanity or obscene language |
| drugs | drug use |
| alcohol | alcohol use |
| crime | crime or illegal activity |
| wealth | money or wealth |
| partying | partying or nightlife |
| family | family relationships |
| friendship | friendship or companionship |
| spirituality | religion or spirituality |
| politics | politics or social issues |
| distress | emotional distress or mental health struggles |
| empowerment | empowerment or resilience |
| grief | death or grief |

The themes come from the research scope, not historical results. Profanity was added for a third language-content judge; drug and alcohol themes remain separate. Changing wording or deleting a theme later requires a new version and validation, not selection for interesting time patterns.

## Chunking and aggregation

Tokenize the complete model-specific input once; reserve special tokens and, for BART, the longest hypothesis. Partition into the minimum number of balanced contiguous chunks that fit. There is no overlap or dropped tail. Exact per-chunk token spans and input hashes make coverage auditable. Chunk boundaries can split syntax, and LyricLens normalization still discards some raw information; whole-token coverage is not proof of semantic completeness.

For every label retain **mean, token-weighted mean, maximum and q90** separately. Weighted mean is a candidate for overall affect/polarity; MAX is a candidate for any-occurrence content but is vulnerable to one false positive and song length. q90 is not robust with only one or two chunks. No universal aggregation is finalized. MAX/q90 sentiment vectors are not probability distributions.

## 200-song panel

| Model | Successful / failed | Content chunks | Songs with >1 chunk | Maximum chunks/song | Content tokens/chunk budget | Model inputs including themes |
|---|---:|---:|---:|---:|---:|---:|
| lyriclens | 200 / 0 | 202 | 2 | 2 | 1022 | 202 |
| detoxify | 200 / 0 | 281 | 65 | 3 | 510 | 281 |
| emotion | 200 / 0 | 281 | 65 | 3 | 510 | 281 |
| sentiment | 200 / 0 | 279 | 64 | 3 | 510 | 279 |
| bart | 200 / 0 | 216 | 16 | 2 | 1010 | 3672 |

All 1,000 song/model dispositions are successful. Numerical chunk evidence, four summaries per label, processing metadata and run fingerprints are in [the experimental output directory](classifier_panel/). Token IDs, lyric text, checkpoints and caches are excluded. The 81,800-row public master and all 19,372 accepted lyric files remain unchanged.

### Distributions and low-information outputs

[Full distributions](classifier_panel/distributions.csv) contain min, max, mean, median, sample SD, Q05/Q25/Q75/Q95 and floor/ceiling counts for all 59 labels × four aggregations, separately for the core 180 and all 200. [Highest/lowest identities](classifier_panel/extremes.csv) contain top/bottom three for every token-weighted label. Below are all-200 token-weighted summaries for the overlapping outputs, all sentiment outputs and selected emotions.

| Model / label | Mean | Median | Q95 | Min | Max | <.01 / 200 | >.99 / 200 |
|---|---:|---:|---:|---:|---:|---:|---:|
| lyriclens.sexual | 0.51392 | 0.6104 | 0.99772 | 0.00085862 | 0.99926 | 41 | 53 |
| lyriclens.violence | 0.20812 | 0.0073632 | 0.99693 | 0.00049914 | 0.99924 | 117 | 29 |
| lyriclens.substance | 0.23457 | 0.0068281 | 0.99665 | 0.00039458 | 0.9994 | 121 | 28 |
| lyriclens.explicit_language | 0.2841 | 0.024677 | 0.99735 | 0.00076516 | 0.99962 | 84 | 37 |
| detoxify.toxicity | 0.21182 | 0.036925 | 0.95871 | 0.00035255 | 0.9953 | 71 | 3 |
| detoxify.severe_toxicity | 0.0094286 | 4.4171e-05 | 0.049009 | 1.2836e-06 | 0.43901 | 179 | 0 |
| detoxify.obscene | 0.12554 | 0.0032464 | 0.9105 | 3.2385e-05 | 0.97983 | 127 | 0 |
| detoxify.identity_attack | 0.019866 | 0.0011416 | 0.097945 | 5.3379e-05 | 0.73767 | 165 | 0 |
| detoxify.insult | 0.090073 | 0.0032497 | 0.53735 | 0.00010439 | 0.87222 | 128 | 0 |
| detoxify.threat | 0.0082782 | 0.00026343 | 0.01937 | 1.552e-05 | 0.55344 | 184 | 0 |
| detoxify.sexual_explicit | 0.037884 | 0.0013103 | 0.2164 | 1.373e-05 | 0.88553 | 151 | 0 |
| emotion.anger | 0.028008 | 0.0052898 | 0.1388 | 0.00059537 | 0.45302 | 132 | 0 |
| emotion.disgust | 0.0058595 | 0.0026657 | 0.023594 | 0.00051996 | 0.081176 | 173 | 0 |
| emotion.grief | 0.0026442 | 0.0011324 | 0.010216 | 0.00024455 | 0.038659 | 189 | 0 |
| emotion.love | 0.19193 | 0.0084914 | 0.90186 | 0.00040477 | 0.97189 | 105 | 0 |
| emotion.pride | 0.0023855 | 0.00082121 | 0.0056052 | 9.9384e-05 | 0.17244 | 195 | 0 |
| emotion.relief | 0.0029419 | 0.0015276 | 0.0089765 | 0.0002572 | 0.063596 | 190 | 0 |
| emotion.sadness | 0.069931 | 0.0083973 | 0.43331 | 0.00074141 | 0.83197 | 105 | 0 |
| emotion.neutral | 0.37503 | 0.28972 | 0.92743 | 0.0096283 | 0.96574 | 1 | 0 |
| sentiment.negative | 0.26737 | 0.25956 | 0.41354 | 0.10829 | 0.50533 | 0 | 0 |
| sentiment.neutral | 0.42394 | 0.42388 | 0.47922 | 0.3098 | 0.53887 | 0 | 0 |
| sentiment.positive | 0.30869 | 0.30387 | 0.45868 | 0.13956 | 0.56608 | 0 | 0 |
| bart.romance | 0.88358 | 0.95293 | 0.99603 | 0.085241 | 0.99963 | 0 | 34 |
| bart.sexual | 0.79457 | 0.82989 | 0.97531 | 0.064062 | 0.99693 | 0 | 2 |
| bart.violence | 0.45187 | 0.38654 | 0.9796 | 0.023368 | 0.99965 | 0 | 4 |
| bart.profanity | 0.7524 | 0.79048 | 0.98687 | 0.080186 | 0.99674 | 0 | 8 |
| bart.drugs | 0.53818 | 0.52625 | 0.9592 | 0.041379 | 0.99812 | 0 | 3 |
| bart.alcohol | 0.63137 | 0.63107 | 0.96235 | 0.095875 | 0.98585 | 0 | 0 |
| bart.distress | 0.86238 | 0.92198 | 0.99242 | 0.24641 | 0.99867 | 0 | 14 |

At least 180/200 weighted scores are below .01 for: detoxify.threat, emotion.embarrassment, emotion.gratitude, emotion.grief, emotion.pride, emotion.relief. Keep these raw outputs, but do not treat numerical rank differences within a compressed floor as strong evidence. Sparsity alone is not proof that a label is useless or truly absent.

**BART neutral ambiguity:** 2,562 chunk/theme pairs have three-way neutral probability above .5; 1,743 of these still have two-class theme confidence above .5. This follows the zero-shot ratio's omission of neutral, not lost data. Such responses cannot be treated as confident theme presence without further validation.

[Aggregation sensitivity](classifier_panel/aggregation_sensitivity.csv) reports mean-versus-MAX rank correlations and changes. Largest average MAX increases (not cross-model scores):

| Model / label | Mean increase | Largest increase | Songs increasing >.1 | Mean–MAX Spearman |
|---|---:|---:|---:|---:|
| emotion.neutral | 0.033 | 0.411 | 26 | 0.985 |
| detoxify.toxicity | 0.023 | 0.426 | 17 | 0.996 |
| detoxify.obscene | 0.019 | 0.420 | 12 | 0.998 |
| detoxify.insult | 0.016 | 0.266 | 14 | 0.997 |
| detoxify.sexual_explicit | 0.014 | 0.402 | 12 | 0.997 |
| emotion.love | 0.012 | 0.310 | 8 | 0.995 |
| emotion.annoyance | 0.009 | 0.133 | 3 | 0.992 |
| bart.spirituality | 0.008 | 0.237 | 7 | 0.990 |

## Agreement

Core 180 results below use token-weighted means and the same song IDs. [All 160 comparisons](classifier_panel/agreement.csv) also include the full 200 and all four aggregations. Percentiles are tied midranks on the stated reference sample. “High overlap” is the number shared by both top-quintile sets; Jaccard divides their intersection by their union. No significance tests or period summaries are calculated.

| Model-label pair | Pearson | Spearman | Mean absolute percentile gap | High overlap | High Jaccard | Opposite quintiles |
|---|---:|---:|---:|---:|---:|---:|
| lyriclens.sexual / detoxify.sexual_explicit | 0.363 | 0.648 | 0.192 | 23 | 0.469 | 1 |
| lyriclens.sexual / bart.sexual | 0.466 | 0.612 | 0.195 | 17 | 0.309 | 1 |
| detoxify.sexual_explicit / bart.sexual | 0.287 | 0.507 | 0.222 | 22 | 0.440 | 1 |
| lyriclens.violence / detoxify.threat | 0.102 | 0.437 | 0.243 | 20 | 0.385 | 3 |
| lyriclens.violence / bart.violence | 0.535 | 0.308 | 0.274 | 21 | 0.412 | 7 |
| detoxify.threat / bart.violence | -0.011 | 0.518 | 0.215 | 19 | 0.358 | 3 |
| lyriclens.explicit_language / detoxify.obscene | 0.708 | 0.617 | 0.192 | 30 | 0.714 | 1 |
| lyriclens.explicit_language / bart.profanity | 0.493 | 0.507 | 0.226 | 24 | 0.500 | 0 |
| detoxify.obscene / bart.profanity | 0.440 | 0.511 | 0.223 | 24 | 0.500 | 1 |
| lyriclens.substance / bart.drugs | 0.403 | 0.365 | 0.256 | 18 | 0.333 | 4 |
| lyriclens.substance / bart.alcohol | 0.401 | 0.400 | 0.252 | 17 | 0.309 | 4 |
| detoxify.toxicity / emotion.anger | 0.553 | 0.589 | 0.205 | 21 | 0.412 | 0 |
| detoxify.toxicity / emotion.disgust | 0.432 | 0.527 | 0.221 | 18 | 0.333 | 1 |
| detoxify.insult / emotion.anger | 0.672 | 0.577 | 0.207 | 20 | 0.385 | 2 |
| detoxify.insult / emotion.disgust | 0.469 | 0.515 | 0.221 | 16 | 0.286 | 2 |
| emotion.love / bart.romance | 0.314 | 0.621 | 0.200 | 16 | 0.286 | 0 |
| emotion.sadness / bart.heartbreak | 0.260 | 0.542 | 0.213 | 18 | 0.333 | 3 |
| emotion.grief / bart.grief | 0.252 | 0.279 | 0.286 | 13 | 0.220 | 6 |
| sentiment.negative / emotion.sadness | 0.255 | 0.347 | 0.259 | 13 | 0.220 | 4 |
| sentiment.negative / emotion.anger | 0.329 | 0.441 | 0.240 | 18 | 0.333 | 3 |

[Selected agreements/disagreements](classifier_panel/agreement_cases.csv) preserve raw scores, percentiles and song identities for 160 pair-specific selections. These are diagnostic selections, not independent ground truth. Rank normalization removes scale units but cannot repair domain mismatch, label inequivalence or a nearly constant output. The core/full-sample distinction also shows that percentile positions depend on the reference set.

### Interpretation of cases

These interpretations use the new numerical profiles and the retained LyricLens/Detoxify qualitative review notes. They are not a new independently labelled accuracy study. Quoted scores below are token-weighted means, unless identified as a single chunk's NLI probability.

- **Agreement on obvious content:** WAP has sexual scores .998 (LyricLens), .859 (Detoxify) and .993 (BART), and language/obscenity/profanity .997/.980/.996. Closer also has high sexual scores .999/.886/.989. Prior lyric review supports direct sexual/profane material. Agreement here is useful, but does not establish calibration or independent votes.
- **Strongly misleading BART absolute scores:** My Girl has BART sexual .858 and profanity .763, despite prior review finding ordinary affection. Its single-chunk three-way sexual NLI is contradiction .009, **neutral .936**, entailment .055. Profanity NLI is similarly neutral-dominant. Happy has sexual .795 and alcohol .803 despite low LyricLens content scores; Let It Be has sexual .728 with neutral .933 and entailment .049. The high two-class ratios are not evidence of confident theme presence. Do not silently replace or threshold them; validate neutral-aware alternatives separately with the frozen themes.
- **Violence is not threat:** Murder On My Mind has LyricLens violence .997 and BART violence .988, while Detoxify threat remains .032 after whole-input chunking. Prior review found explicit violent storytelling. Highwire similarly yields violence .999/.927 but threat .004 for an antiwar narrative. Chunking fixes coverage, not construct mismatch.
- **False agreement and different context readings:** Imagine retains LyricLens violence/language .995/.993; BART profanity is .872, while Detoxify obscene is .001 and GoEmotions optimism .476. Prior review identified negation and peace-oriented imagery. Two models giving high content responses does not establish severity. Cry Just a Little has Detoxify threat .553, but BART violence .112 and GoEmotions love .972; prior review identified figurative heartbreak.
- **Self-address versus insult:** Foolish Heart retains Detoxify insult .867/toxicity .916, but GoEmotions anger is .032. Disappointment (.213) is its largest emotion response and Cardiff negative is .488. This supports a different affective reading rather than an additional hostile vote; prior review identified address to the narrator's own heart.
- **Emotion-neutral is not content-clean:** WAP has GoEmotions neutral .883 despite the explicit-content agreement above. Because I Got High has amusement .611 and BART drugs .948, while LyricLens substance is .998. Happy has joy .751. Emotion describes a different aspect; neither neutral nor positive affect cancels explicit content.
- **Language remains a validity limit:** Rosones receives GoEmotions neutral .956 and very low Detoxify explicitness despite prior Spanish-text review finding explicit material. BART sexual/profanity are .931/.969, but several unrelated themes are also high (family .995, romance .986); this is not proof of validated Spanish theme detection. Cardiff supports Spanish but sentiment is not an explicit-content check.
- **Sentiment compression:** Cardiff's weighted neutral score wins for 163/200 songs (negative 15, positive 22). Neutral ranges .310–.539; positive .140–.566; negative .108–.505. These are finite, nonconstant responses, not a failed prediction batch. Mixed lyrics and tweet-to-song domain shift may contribute; the pilot does not identify a causal explanation or establish polarity accuracy.
- **Aggregation has consequences:** Detoxify obscene for Because I Got High changes from the old prefix-only .275 to whole-input weighted mean .424. This does not validate either mean or MAX as severity. Across the panel, MAX raises Detoxify toxicity by more than .1 for 17 songs and GoEmotions neutral for 26. Balanced chunks make mean and weighted mean close, but MAX can change the interpretation and ranking.

Percentile normalization makes different numerical scales easier to compare, and core sexual/language rank correlations are moderate. It does **not** repair BART's high neutral-dominant absolute scores, English-model language failures, or figurative readings. A rank near the top of a compressed rare-emotion distribution may still be a tiny, unreliable response. Keep original scores beside any ranks and validate common constructs before proposing consensus.

## Retained outputs and future panel design

Retain all 59 raw model-label outputs, all chunk evidence and all four within-label summaries. Emotion and sentiment add distinct affective information; they are not substitutes for sexual/violent/substance content. Highly correlated language judgments may be redundant evidence rather than independent confirmation. Low-range rare emotions and threat/severe-toxicity outputs need reliability checks before influencing an outcome; no label is deleted based on this pilot.

A future agreement representation could include separate per-judge empirical-CDF percentiles, a mean normalized rank and a dispersion statistic (SD/range/MAD), with judge count and missingness. These are **proposals only**: no consensus columns are created. Fit and freeze a suitable reference distribution rather than ranking within each era. Do not give missing judges zero votes or count related models as independent votes. Blinded labels are needed to assess reliability and any weights.

Traditional inter-rater metrics are not automatically suitable: ICC assumes comparable interval measurements; kappa needs justified categories and depends on prevalence; concordance requires judges to rank a common construct. Pairwise rank correlation/quintile overlap are useful diagnostics but not confidence in truth.

Eventual storage: a versioned song-score table keyed by song_id and run/version; a run registry with exact artifacts/settings; linked chunk outputs. After aggregation choices are approved, expose one selected version per song for a stable LEFT JOIN to the public master. Keep model-specific token/chunk counts, because a single cross-model token count is undefined. No production join or schema migration occurred.

## Performance

| Model | Device / batch | Inference seconds | Seconds/song | Projected 19,372-song hours | Peak process RSS GiB | Peak MPS driver GiB |
|---|---|---:|---:|---:|---:|---:|
| lyriclens | cpu / 1 | 123.87 | 0.619 | 3.33 | 1.44 | 0.00 |
| detoxify | cpu / 1 | 27.81 | 0.139 | 0.75 | 1.25 | 0.00 |
| emotion | cpu / 1 | 27.87 | 0.139 | 0.75 | 0.88 | 0.00 |
| sentiment | cpu / 1 | 27.36 | 0.137 | 0.74 | 1.13 | 0.00 |
| bart | mps / 4 | 617.40 | 3.087 | 16.61 | 1.54 | 11.02 |

**Total measured model/preprocessing work: 13.74 minutes**, plus 11.50 seconds summed initialization. Sequential extrapolation: **22.18 hours** for the full corpus with this CPU/MPS allocation, same length distribution and 17 themes. Setup, report generation, journal writes and interruptions are excluded; longer corpus inputs and thermal load can increase runtime. CPU-only full-panel time was not measured.

The BART device benchmark used four theme pairs from the first sample song: warm CPU batches took about 1.05 s versus 0.239 s on MPS, with maximum logit difference about 1.1e-5. This small benchmark supports device selection, not a universal speed ratio. [Benchmark](classifier_panel/bart_device_benchmark.json). RSS and MPS driver allocations overlap on unified memory; do not add them as independent RAM requirements. Models ran sequentially on the 16-GiB machine.

Published raw chunk outputs and song-summary CSVs total **4,372,193 bytes (4.17 MiB)** for 200 songs. A proportional full-corpus estimate is **403.9 MiB**, plus journals/diagnostics. The five checkpoints total approximately 4.0 GiB locally; they are not committed. The measured speed makes the battery plausible locally, with BART dominating cost, but long-run memory stability is not established.

## Recommendation and validation

**Do not run the full corpus yet.** First validate a neutral-aware BART interpretation against a blinded content/context rubric using the frozen themes; the current two-class ratios falsely look confident for neutral-dominant mild-song examples. Separately, bound BART MPS memory (for example, a small fixed set of padding shapes or bounded worker lifetimes, with score-equivalence checks): driver allocation reached 11.02 GiB and full-corpus stability is untested. Then approve label-specific aggregation using disagreement and long/non-English cases. Distinguish content presence, severity, narrator/endorsement and affect. Repeated evidence from similar models must not be mistaken for validated severity.

**Validation completed:** 203 tests passed; 4,715 exact chunk/pair input hashes were independently reconstructed. All 198 single-chunk LyricLens and 135 single-chunk Detoxify cases reproduced the prior pilot within 1e-6. The research/public-data/corpus validators and two deterministic diagnostic rebuilds passed.

Validation includes exact sample identity, input hashes after independent retokenization, full token coverage, all raw-logit activations, every song summary, previous-pilot single-chunk replays, artifact/version pins, deterministic diagnostics, output safety, the complete test suite and existing corpus/research/public-dataset validators. See [reproduction commands](../docs/classifier_panel_specification.md). No full-corpus classifier run, master modification, consensus/hardness score or longitudinal/COVID analysis was performed.
