# Phase LRCLIB-R: offline ambiguity review

All 83 ambiguous pilot assets were reviewed using only existing cached LRCLIB responses. **Zero new network requests.** The original 112 accepted files, five not-found decisions, original pilot database, and MusicBrainz state were preserved.

## Recovery

| Result | Assets |
|---|---:|
| Original accepted | 112 |
| Ambiguous reviewed | 83 |
| Newly recoverable | 59 |
| Still identity ambiguous | 5 |
| Rejected for bad text, identity established | 1 |
| Missing/instrumental text, identity established | 3 |
| Rejected for wrong identity | 15 |
| Original not found | 5 |

The recovery outcomes partition the 83 reviewed assets; the other 117 retain their original decisions. Missing text is reported separately from defective text. A wrong-identity candidate can have well-formed text: its text grade does not make it usable for the target asset.

| Independent coverage metric | Assets / 200 | Coverage |
|---|---:|---:|
| Any LRCLIB candidate | 195 / 200 | 97.5% |
| High-confidence Billboard identity | 175 / 200 | 87.5% |
| Text usable for the intended content study | 171 / 200 | 85.5% |

Identity coverage includes confirmed instrumental/missing-text and bad-text assets. It carries forward the original 112 identity acceptances; those assets were not regraded in this focused review. Candidate availability includes unrelated search hits and must not be interpreted as correct-song coverage.

## Revised period coverage

| First-chart period | Pilot assets | Any candidate | Correct identity | Usable text | Usable coverage |
|---|---:|---:|---:|---:|---:|
| 1958–1969 | 29 | 28 | 23 | 22 | 75.86% |
| 1970s | 29 | 25 | 22 | 20 | 68.97% |
| 1980s | 29 | 29 | 25 | 24 | 82.76% |
| 1990s | 29 | 29 | 28 | 28 | 96.55% |
| 2000s | 28 | 28 | 23 | 23 | 82.14% |
| 2010–2019 | 28 | 28 | 28 | 28 | 100.0% |
| 2015–2019 | 8 | 8 | 8 | 8 | 100.0% |
| 2020–2026 | 28 | 28 | 26 | 26 | 92.86% |

2015–2019 overlaps 2010–2019 and contains only eight assets. Periods use first Billboard appearance, not release dates. Pilot results do not establish full-population coverage.

## Identity and text findings

- Multiple records and minor text differences are not identity failures. Many rejections reflected contractions, vocalizations, word boundaries, spelling, or refrain repetitions. Conflicting texts remain retained; neither majority count nor a similarity score proves correctness.
- Explicit reviewed crosswalks recover full credits separated differently, a featured artist moved into the title, an attached AKA name, and guest evidence present in another cached version. Missing collaborator evidence remains unresolved for Fame And Fortune, I Chose To Sing The Blues, Hot Dawgit, MJB Da MVP, and the composite-credit I'm A Flirt.
- Knife Talk has an existing substantially unmasked source with complete artist names separated by escaped null markers. Gangstas has an existing Dirty title variant, despite a contradictory Clean album label. These existing texts are selected without inventing or uncensoring words; version/censorship warnings remain. No claim is made that either is the exact radio edit heard during its chart run.
- Flooded The Face contains a spam candidate and a masked candidate alongside usable text. Rejecting those candidate texts does not require rejecting the matching asset.
- Steady Mobbin' has a 310-second cached record matching available duration evidence and sharing the exact text of the 165-second record. The original duration-only rejection is resolved without external queries.
- Wonderland remains text_bad: all matching cached texts terminate after 49 words with an unfinished continuation. All About My Girl, Popcorn and Theme From Magnum P.i. retain high-confidence identities with text_missing/instrumental status; no empty file is treated as a successful lyric.
- Our Lips Are Sealed retains its unique verses and bridge; an abbreviated final reprise is minor repetition uncertainty under this content-oriented review. Gone Till November has one localized encoding defect in 548 words, retained unchanged. When You're Mad retains its localized alternate wording with a version warning.

These are assistant reviews of cached metadata, excerpts and token differences, not audio-verified or independently transcribed ground truth. text_good means no material defect identified; text_usable_with_minor_noise means the substantive text is present with documented uncertainty. Exact lyric-frequency or performed-repetition studies may need stricter exclusions. No classifier or hardness scores were implemented.

## Conservative cleaning

The cleaner normalizes line endings and Unicode NFC, trims outer/trailing whitespace, removes narrowly recognized standalone bracketed section labels, and removes a leading title/artist/writer block only when all three lines structurally establish it as a header. It does not strip arbitrary parenthetical content, artist names inside lyrics, spoken outros, repetitions, or censored fragments. It does not repair mojibake, infer missing words, expand refrain instructions, or uncensor text.

An American Trilogy is recovered by removing its explicit metadata header. The raw source, raw-text hash, cleaning operations and cleaned-text hash are retained. The cleaner is applied only to selected newly recoverable texts, with every choice bound to a specific cached candidate revision.

## Reproduce and audit

```bash
python3 src/lyrics_lrclib_r.py build
python3 -m unittest discover -s tests -v
```

- [Versioned review ledger](../../reports/lyrics_lrclib_r_review.json): one explicit identity grade, text grade, selected candidate, source hash, reason and warning list for every ambiguous asset.
- [Generated case table](../../reports/lyrics_lrclib_r_cases.csv): 83 rows with original Billboard identity, matched LRCLIB identity, independent grades and review reasons; no lyrics.
- Local result/combined-corpus manifest: `data/processed/lyrics_lrclib_r.json`.
- Newly recoverable cleaned texts: `data/cache/lrclib-r/texts/<song_id>.txt`; original accepted files remain `data/lyrics/<song_id>.txt`. No canonical files were replaced and no unified-database import was run.
- Existing candidate responses remain under `data/cache/lrclib/`. Outputs reference their URLs, retrieval timestamps, response hashes and frozen metadata evidence. Rebuild validates all 83 ledger entries and their cached candidate hashes, and leaves both acquisition databases untouched.
- The ledger is an explicit pilot crosswalk, not a trained/general matcher. Full acquisition would need to carry forward the same independent grades and route uncertain identities, substantial text defects and version conflicts to review; these 83 decisions cannot simply be applied to new songs.

## Recommendation

**GO for a staged, reviewed full-population collection using LRCLIB**, subject to the user's next authorization. Revised usable coverage is 171/200 (85.5%). Identity mistakes were not traded for recall: unresolved credits and unrelated performers remain excluded. Preserve raw/cleaned variants and censorship warnings, and retain text-quality review instead of treating HTTP success as corpus acceptance. This is not approval of unattended acceptance or a claim that the original matcher generalizes.

No full acquisition, provider change, classifier, or statistical analysis was started.
