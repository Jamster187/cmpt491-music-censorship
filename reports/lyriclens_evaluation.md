# LyricLens evaluation: 200-song pilot

**Recommendation C: consider raw category probabilities only as one candidate feature set alongside a separately validated model. Do not adopt CSI/MCR as the project outcome or proceed to full-corpus scoring on this evidence.**

The model is fast and often detects obvious content, but confidence in category presence is not continuous severity. Figurative language and ordinary romance produce clear errors; mild references can saturate scores. A blinded human rubric and an independent severity/context measure are needed before a production decision. This pilot does not establish historical or COVID effects.

[Inspection, licensing, output definitions, limitations, and reproduction commands](../docs/lyriclens_methodology.md). Full-paper access was blocked; the accessible abstract, complete repository, and checkpoint metadata were inspected.

## Scope and provenance

- 200/200 successful predictions; zero missing/failed predictions and 0 preprocessing fallbacks.
- 180 stratified diagnostic songs plus 20 preselected sentinels; 200 unique identities, no new corpus acquisition.
- 47 qualitative read-throughs by the assistant, not an independent human-labelled test set.
- Git revision `71a40996c1021c62d12dc004cbafa3f1c5560162`; weights SHA-256 `d272696293bc75d5a82cca2e624800456f734f57382cd9472b5974993ef860cc`.
- [Sample](lyriclens_sample.csv), [experimental predictions](lyriclens_predictions.csv), [review decisions](lyriclens_review.csv), [artifact provenance](lyriclens_artifacts.json), [run provenance](lyriclens_run.json), [CPU/MPS replay](lyriclens_benchmark.json). Lyrics and model files are excluded.
- Raw logits, probabilities, and complete app outputs remain in ignored local JSONL; their SHA-256 is `1cdb717916bc793ce82db8d1f58e61b39613a7210bc5c7f9dc81a70b59eccd80`.

## Score distributions

Category scores are raw sigmoid values in [0,1]. CSI is the README formula (100 times their mean); app_CSI is the actual app formula after clipping/rescaling. SD uses n−1; quantiles use linear interpolation. Neither CSI is a trained severity output.

| Score (all 200) | Min | P05 | P25 | Median | Mean | SD | P75 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| sexual_content_score | 0.000859 | 0.003090 | 0.015559 | 0.610395 | 0.514824 | 0.447776 | 0.991672 | 0.997719 | 0.999258 |
| violence_score | 0.000499 | 0.001113 | 0.003487 | 0.007363 | 0.209674 | 0.377217 | 0.085817 | 0.996935 | 0.999237 |
| explicit_language_score | 0.000765 | 0.001765 | 0.004575 | 0.024677 | 0.284094 | 0.404457 | 0.619836 | 0.997351 | 0.999619 |
| substance_use_score | 0.000395 | 0.001018 | 0.002818 | 0.006828 | 0.234928 | 0.403646 | 0.160358 | 0.996651 | 0.999405 |
| CSI | 0.568793 | 0.685753 | 5.133137 | 25.252289 | 31.087982 | 29.971498 | 44.217904 | 98.763430 | 99.440959 |
| app_CSI | 0.000000 | 0.000000 | 0.000000 | 22.455059 | 26.734363 | 30.112574 | 36.048875 | 97.526859 | 98.881918 |

| Raw category | Below 0.01 | Above 0.99 |
|---|---:|---:|
| sexual_content_score | 41/200 | 53/200 |
| violence_score | 117/200 | 30/200 |
| explicit_language_score | 84/200 | 37/200 |
| substance_use_score | 121/200 | 28/200 |

No raw probability equals exactly zero or one, but the tails are heavily saturated. The app transform makes CSI exactly zero for 69/200 songs, discarding real differences below its threshold. MCR counts: M-AO 97, M-E 70, M-P 6, M-R 21, M-T 6.

The 180-song core has mean raw CSI 29.579 (all 200: 31.088). Sentinel selection therefore affects the combined distribution; neither is a weighted corpus estimate.

## Highest and lowest identities

Extremes include sentinels and are diagnostic examples, not population rankings.

| Score | End | Song — artist | Value |
|---|---|---|---:|
| sexual_content_score | lowest | Have A Nice Day — Bon Jovi | 0.000859 |
| sexual_content_score | lowest | Gallant Men — Senator Everett McKinley Dirksen | 0.000978 |
| sexual_content_score | lowest | Little Bird — Annie Lennox | 0.001463 |
| sexual_content_score | highest | Closer — Nine Inch Nails | 0.999258 |
| sexual_content_score | highest | Plastic Off The Sofa — Beyonce | 0.998859 |
| sexual_content_score | highest | Let's Get The Mood Right — Johnny Gill | 0.998849 |
| violence_score | lowest | Deja Vu — Olivia Rodrigo | 0.000499 |
| violence_score | lowest | Rockabye — Clean Bandit Featuring Sean Paul & Anne-Marie | 0.000596 |
| violence_score | lowest | Rosones — Tito Double P | 0.000612 |
| violence_score | highest | Highwire — The Rolling Stones | 0.999237 |
| violence_score | highest | Vigilante Shit — Taylor Swift | 0.999119 |
| violence_score | highest | Paint The Town Red — Doja Cat | 0.998852 |
| explicit_language_score | lowest | Flashdance...What A Feeling — Irene Cara | 0.000765 |
| explicit_language_score | lowest | Mary Ann Regrets — Burl Ives | 0.000959 |
| explicit_language_score | lowest | River Deep - Mountain High — The Supremes & Four Tops | 0.001167 |
| explicit_language_score | highest | Flava In Ya Ear — Craig Mack | 0.999619 |
| explicit_language_score | highest | Crushed Up — Future | 0.999576 |
| explicit_language_score | highest | Money Ain't A Thang — JD Featuring Jay-Z | 0.998507 |
| substance_use_score | lowest | Not Nice — PARTYNEXTDOOR | 0.000395 |
| substance_use_score | lowest | Over It — Katharine McPhee | 0.000477 |
| substance_use_score | lowest | I'll Take Good Care Of You — Garnet Mimms | 0.000481 |
| substance_use_score | highest | If I Were A Boy — Beyonce | 0.999405 |
| substance_use_score | highest | New Rules — Dua Lipa | 0.999102 |
| substance_use_score | highest | Touch The Sky — Kanye West Featuring Lupe Fiasco | 0.998565 |
| CSI | lowest | Cindy's Birthday — Johnny Crawford | 0.568793 |
| CSI | lowest | Foolish Heart — Steve Perry | 0.575393 |
| CSI | lowest | There's Nothing I Can Say — Rick Nelson | 0.575781 |
| CSI | highest | America Has A Problem — Beyonce Featuring Kendrick Lamar | 99.440959 |
| CSI | highest | Anaconda — Nicki Minaj | 99.431498 |
| CSI | highest | Need It — Migos Featuring YoungBoy Never Broke Again | 99.420959 |

## Qualitative review

Of 47 selected cases, 29 were broadly plausible category-presence detections, 13 were questionable, and 5 had clear face-validity failures. This outcome-selected review is not an accuracy estimate. Correct presence can still imply a misleading severity or adult rating. Scores were not adjusted.

Examples of the distinction: a beer mention in *If I Were A Boy*, a cigarette in *Lipstick Traces*, and mild profanity in *Keep Me In Mind* trigger near-one probabilities. These observations support detection, not a claim of extreme severity. Antiwar discussion in *Highwire* and *What Is Truth* is detected without representing stance. *Imagine* raises both violence and language scores near one despite negation/peace and a literal religious reference.

*My Girl*, *Georgy Girl*, and *Fading Away* have unsupported sexual-content responses for the intended explicitness measurement. *River Deep – Mountain High* has a clear figurative-height/substance error. *Smack That* also raises a separate clean/transcription-quality concern; the local text was preserved unchanged.

| Song — artist | Assessment | Evidence summary (no lyric excerpts) |
|---|---|---|
| My Girl — The Temptations | clearly_wrong | Affection and happiness, without sexual acts or erotic description; sexual probability 0.632 is not face-valid for explicit-content measurement. |
| Let's Get It On — Marvin Gaye | questionable | Sexual invitation is correctly detected; language probability 0.620 has no clear strong-profanity support in this text. One unusual threatening phrase may be a transcription issue; not verified against audio. |
| Lean On Me — Bill Withers | correct | Support and friendship; low scores fit the supplied text. |
| You Are The Sunshine Of My Life — Stevie Wonder | correct | Affection with figurative tears; low category scores fit. |
| Rainbow Connection — Kermit (Jim Henson) | correct | Dreaming and wonder; low scores fit. |
| ABC — Jackson 5 | questionable | Playful courtship and dancing; sexual 0.728 and language 0.314 overstate the apparent explicitness. A broad romance label might explain part of this. |
| Imagine — John Lennon/Plastic Ono Band | questionable | Negated killing and a literal religious reference support keyword presence, but violence 0.995 and language 0.993 do not establish severe or endorsing content in this peace song. |
| Let It Be — The Beatles | correct | Consolation and spiritual support; low scores fit. |
| You've Got A Friend — James Taylor | questionable | Figurative emotional hurt and abandonment; violence 0.600 is questionable as a content-severity signal. |
| Super Freak (Part I) — Rick James | correct | Sexual themes and an alcohol mention are present. Near-one substance probability should not be read as extreme drug severity. |
| What A Wonderful World — Louis Armstrong | correct | Nature, friendship, and children; low scores fit. |
| Gin And Juice — Snoop Doggy Dogg | correct | Direct sexual, profanity, alcohol, and cannabis content; high scores in those categories fit. |
| Closer — Nine Inch Nails | correct | Direct sexual language and profanity; strong sexual and language detection fits. |
| Smack That — Akon Featuring Eminem | questionable | Sexual content and alcohol are present; near-one violence and language scores are poorly supported by this particular local text. Several lines appear garbled and strong profanity is absent; clean/version/transcription uncertainty needs separate review, not a score correction. |
| Because I Got High — Afroman | correct | Direct drug use, profanity, and sexual content; corresponding high probabilities fit. |
| Murder On My Mind — YNW Melly | correct | Explicit homicide narrative, weapons, drugs, sexual content, and profanity; all four high probabilities fit. |
| Anaconda — Nicki Minaj | correct | Direct sexual content, gun/shooting references, drugs, and profanity; all four high probabilities fit. |
| The Hills — The Weeknd | correct | Sex, profanity, and explicit drug/rehabilitation references; high corresponding scores and low violence fit. |
| Happy — Pharrell Williams | correct | Celebratory text; low overall scores fit, with only a small language response. |
| WAP — Cardi B Featuring Megan Thee Stallion | correct | Graphic sex and profanity, alcohol/cannabis, and violent sexual imagery are present. Whether consensual sexual imagery should count as violence requires a rubric. |
| Have A Nice Day — Bon Jovi | correct | Defiance and hardship without explicit sexual or substance content; low sexual score fits. |
| Deja Vu — Olivia Rodrigo | correct | Relationship jealousy; low scores fit this supplied text rather than an assumed explicit recording version. Local wording contains no strong profanity; do not infer what an uncensored alternative recording would score. |
| Highwire — The Rolling Stones | correct | Weapons, warfare, and arms trading are explicitly discussed; violence detection fits. The critical stance is not captured by the probability. |
| Flashdance...What A Feeling — Irene Cara | correct | Dancing and aspiration; very low language score fits. |
| Flava In Ya Ear — Craig Mack | questionable | Profanity and violent battle metaphors are present; substance 0.885 appears to treat praise slang and figurative smoke as literal use. |
| Not Nice — PARTYNEXTDOOR | questionable | Dancehall/patois courtship; sexual 0.468 may reflect suggestive dancing, but the score is not a reliable measure of its intensity. English-only normalization loses some stylistic distinctions; no controlled slang intervention was performed. |
| If I Were A Boy — Beyonce | correct | A brief alcohol reference supports substance presence. Substance 0.999 does not imply more severe use than a song about sustained intoxication. |
| Cindy's Birthday — Johnny Crawford | correct | Birthday gift and school themes; all low scores fit. |
| Foolish Heart — Steve Perry | correct | Cautious romance and heartbreak; all low scores fit. |
| Feels So Good — Xscape | correct | Sensual touching and loss of control support sexual-content presence, without strong profanity or drug content. |
| Floy Joy — The Supremes | questionable | Flirtation, pleasure, and giving oneself are suggestive; sexual 0.993 is plausible as presence but not evidence of extreme explicitness. |
| America Has A Problem — Beyonce Featuring Kendrick Lamar | correct | Sexual and drug imagery, threats, and profanity are present; all-category detection fits, with figurative and literal content mixed. |
| Georgy Girl — The Seekers | clearly_wrong | Loneliness, appearance, and courtship advice without explicit sexual content; sexual 0.753 is unsupported as explicitness. |
| River Deep - Mountain High — The Supremes & Four Tops | clearly_wrong | Love compared with increasing height/depth; no literal substance use. Substance 0.871 is a clear metaphor-related false positive. |
| Cry Just A Little — Paul Davis | questionable | Heartbreak and figurative dying; violence 0.382 should not be interpreted as measured violent intensity. |
| It's Your Body — Johnny Gill Featuring Roger Troutman | correct | Direct bedroom invitation and undressing support high sexual-content probability. |
| Read Your Mind — Avant | correct | Sexual fantasy, touching, and a bed invitation support high sexual-content probability. |
| Keep Me In Mind — Zac Brown Band | correct | A mild profanity is present, so language presence is plausible. Language 0.997 and the resulting adult rating exaggerate severity. |
| One Of The Girls — The Weeknd, Jennie & Lily Rose Depp | questionable | Sexual domination and physical harm are explicit; language 0.621 lacks clear profanity support. |
| Fading Away — Will To Power | clearly_wrong | Romantic longing, touch, and reconciliation without clear erotic acts; sexual 0.984 is unsupported as explicit content. |
| If I Ever Fall In Love — Shai | questionable | Physical attraction is mentioned but the focus is friendship and commitment. Sexual 0.983 illustrates the presence-versus-severity problem. |
| Go, Jimmy, Go — Jimmy Clanton | questionable | Kissing and a school-based innuendo support a suggestive reading; sexual 0.991 cannot establish graphic explicitness. |
| Midnight At The Oasis — Maria Muldaur | correct | Sustained sexual innuendo supports sexual-content detection; no claim of graphic intensity is justified by the probability alone. |
| Lipstick Traces (On A Cigarette) — The O'Jays | correct | A cigarette is explicitly referenced; substance presence fits. Saturated probability cannot distinguish this from severe drug use. |
| What Is Truth — Johnny Cash | correct | War, fighting, and death are explicitly discussed; violence presence fits, while its questioning/antiwar stance is not represented. |
| Macarena — Los Del Rio | questionable | Spanish courtship/sexual innuendo and infidelity are present; sexual 0.315 is uncertain rather than a validated intensity measure. The supplied text is Spanish and has repeated choruses; token count 1,027 exceeds the app limit by three. Exact title/artist identity alone does not resolve the Spanish-original versus bilingual-remix question. |
| Rosones — Tito Double P | clearly_wrong | Spanish text contains clear sexual and strong-profanity references; sexual 0.277 and language 0.050 are falsely reassuring. Substance 0.866 does capture some drug/alcohol content. English normalization and an unverified training-language mix limit cross-language validity; no translation or text replacement was made. |

## Temporal and length diagnostics — not a historical analysis

Means below use only the stratified core; periods are first chart appearance. These differences cannot distinguish actual content mix, sample selection, length, language style, or model error. No COVID breakpoint, hypothesis test, or causal conclusion was applied.

| Period | n | Sexual | Violence | Language | Substance | Raw CSI | App CSI |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1958–1969 | 26 | 0.360 | 0.158 | 0.080 | 0.045 | 16.100 | 12.674 |
| 1970s | 26 | 0.522 | 0.045 | 0.079 | 0.157 | 20.061 | 16.874 |
| 1980s | 26 | 0.337 | 0.172 | 0.123 | 0.095 | 18.152 | 15.139 |
| 1990s | 26 | 0.509 | 0.187 | 0.181 | 0.116 | 24.831 | 20.579 |
| 2000s | 26 | 0.459 | 0.223 | 0.383 | 0.226 | 32.264 | 26.147 |
| 2010–2019 | 25 | 0.708 | 0.106 | 0.413 | 0.288 | 37.873 | 32.403 |
| 2020–2026 | 25 | 0.680 | 0.511 | 0.574 | 0.603 | 59.230 | 53.851 |

Core Spearman correlations with raw lyric word count: sexual_content_score 0.351, violence_score 0.249, explicit_language_score 0.563, substance_use_score 0.323, CSI 0.569, app_CSI 0.506.

2/200 inputs exceeded the app's 1,024-token limit: Macarena (1027 tokens), Money Ain't A Thang (1071 tokens). Prefix-only processing can miss later content; none of the supplied texts were shortened on disk.

Modern slang is sometimes recognized (explicit drug/sex references in the sentinels), but the patois case *Not Nice* remains ambiguous. This is not a slang-robustness benchmark. Two additional language checks expanded the review to 47: Spanish *Rosones* has clear sexual/profane wording but language probability only 0.050, while *Macarena* raises Spanish/remix-version and repetition/truncation questions. Historical false positives in romance/metaphor, modern contextual errors, and loss of censored/non-English tokens justify a dedicated invariance check. No paired clean/explicit versions were rescored; low language scores apply to the supplied text only.

## Measured performance

CPU: native arm64 Python 3.11.8, PyTorch 2.7.1, four threads, float32, one 1,024-token padded input per forward pass. The 200 input runs took 122.585 seconds: mean 0.613 s/song, median 0.611, P95 0.644. These timings include preprocessing and diagnostic token counting; model/tokenizer loading took 2.247 seconds separately.

Linear estimate for 19,372 songs: **3.30 CPU hours**, plus loading/I/O and possible thermal/load variation. This is an estimate; the full corpus was not run.

CPU peak process RSS was 1,622,704,128 bytes (1.51 GiB) on this 16 GiB Mac. This is process RSS, not a general minimum-RAM guarantee. Inference weights occupy 594,684,336 bytes; seven downloaded inference/evaluation artifacts total 596,208,607 bytes. The isolated environment and NLTK resources need additional storage.

Five length-spread pilot inputs were replayed: CPU predictions matched the first run exactly (max probability difference 0.0).

Apple MPS forward-only mean was 0.369 s/song after a 4.217-second warm-up. A forward-only extrapolation is 1.98 hours; preprocessing, transfers and deployment overhead are additional. CPU/MPS maximum probability difference was 0.00000192. The upstream app selects CUDA or CPU, not MPS: this was a separate diagnostic device adapter, not the canonical pilot or a production GPU implementation. No CUDA GPU is available.

Experimental CSV: 99,548 bytes; raw JSONL: 240,185 bytes for 200 songs. Linear output-storage estimate for 19,372 songs is 31.4 MiB for both, excluding models and lyrics. Full-corpus inference is technically practical on this machine; measurement validity is the limiting issue.

## Integrity and validation

The dedicated validator reconciles all raw outputs and CSV scores, checks finite probabilities and label mapping, recomputes both CSI formulas, verifies sample/lyric/model hashes, confirms corpus and public-export fingerprints, and checks that reviews cover exactly their deterministic selection. The full unittest suite passed 184 tests; the standard research-database and dedicated pilot validations passed. See the reproduction commands for reruns. No accepted lyrics, research tables, or public dataset columns were changed.

Before any full-corpus decision: obtain the full paper and label/split documentation; define and independently annotate the intended content-intensity rubric across periods; compare raw category features with an independent context/severity model; and evaluate calibration, negation, metaphor, clean versions, and preprocessing/truncation effects. No such second model was implemented or run here.
