# LRCLIB exclusion audit

**Diagnostic only. Zero HTTP requests, zero disposition changes, zero lyric-file changes.**
All 25,363 assets remain attempted; the usable corpus stays at 19,372 (76.38%).
The corpus is not demonstrated to be at its safe ceiling. Recommendation: **C — build and independently validate a focused second-pass matcher**, after authorization. Do not bulk-promote this diagnostic shortlist.

## What caused quarantine

Production identity is high-confidence for 2,637/3,519 (74.94%); 882 remain identity-ambiguous. A high-confidence identity does not certify its text. The latter group includes five preserved manual pilot exclusions.
The production first-failure reasons are 2,332 text disagreements, 877 incomplete title/credit matches, 292 text/version review flags, 13 duration conflicts, and five prior reviewed exclusions. Album mismatch is never a sole rejection reason; matching album is a selection preference.
Multiple LRCLIB records already pass if their texts agree. Clean/explicit labels alone already pass; actual masking is a separate question. Warning unions can describe rejected alternatives, not defects in a selected text.
The table below assigns every quarantined asset exactly one primary stratum. `text_substantive_conflict` is an internal sampling label for **wider disagreement**, not a finding that all its texts are substantively wrong. Near agreement requires every safe text group to have sequence ratio ≥0.85 and word-set overlap ≥0.90 against the longest group. These thresholds are diagnostic strata, not proposed acceptance rules. Repeat-only means identical first-occurrence line sequences, not proven recording-length equivalence. All groups are examined, including those beyond the production matcher’s first failing pair.

| Primary category | Assets | % quarantine |
|---|---|---|
| text_substantive_conflict | 1744 | 49.56% |
| text_near_agreement | 574 | 16.31% |
| identity_incomplete_credit | 312 | 8.87% |
| identity_title_variant | 252 | 7.16% |
| identity_other_credit_or_song | 223 | 6.34% |
| quality_mixed_script_words | 112 | 3.18% |
| identity_separator_variant | 90 | 2.56% |
| quality_material_censorship | 57 | 1.62% |
| quality_short_text_requires_review | 52 | 1.48% |
| quality_embedded_credits | 39 | 1.11% |
| text_repeat_count_only | 14 | 0.40% |
| duration_conflict | 13 | 0.37% |
| quality_unstructured_text | 12 | 0.34% |
| quality_version_only | 10 | 0.28% |
| quality_possible_non_lyric_material | 5 | 0.14% |
| quality_multiple_blockers | 5 | 0.14% |
| prior_review_quarantined | 5 | 0.14% |

Secondary flags overlap; counts below use only identity-eligible candidates for text/version flags. Identity flags can describe competing unrelated candidates. A version flag does not itself establish why the asset failed.

| Secondary flag | Assets | % quarantine |
|---|---|---|
| variant_or_other_performer_credit | 576 | 16.37% |
| version_live | 413 | 11.74% |
| missing_credit_components | 336 | 9.55% |
| title_variant_same_credit | 263 | 7.47% |
| version_risk_in_candidates | 207 | 5.88% |
| text_mixed_script_words | 132 | 3.75% |
| version_remix | 106 | 3.01% |
| credit_separator_only_candidate | 90 | 2.56% |
| text_material_censorship | 74 | 2.10% |
| extra_credit_components | 56 | 1.59% |
| text_short_text_requires_review | 54 | 1.53% |
| text_embedded_credits | 39 | 1.11% |
| version_instrumental | 33 | 0.94% |
| version_acoustic | 29 | 0.82% |
| version_karaoke | 23 | 0.65% |
| text_unstructured_text | 12 | 0.34% |
| text_possible_non_lyric_material | 5 | 0.14% |
| version_demo | 4 | 0.11% |
| version_medley | 3 | 0.09% |

## Representative cache review

The fixed seed `lrclib-exclusion-audit-v1` orders SHA-256(seed + song_id) within status/primary strata. Review takes 20 per stratum, 40 for wider disagreement, or every asset when fewer exist. Prior reviewed pilot exclusions are preserved separately and excluded from this new sample.
The 360 selected cases comprise 279 quarantined, 21 wrong-identity, 20 bad/missing-text, 20 empty-search, and 20 transport-error records. Transport errors were assessed from response evidence; other review used candidate metadata, text boundaries, flagged lines, lengths and sequence differences. This is one assistant’s diagnostic review, not audio verification, independent adjudication, or a line-by-line transcription certification. There are 17 quarantined sample cases from 2015–2019 and 50 from 2020–2026. The versioned [review ledger](../../reports/lyrics_exclusion_review.json) binds decisions to exact result, candidate and retrieval hashes. The [local, ignored exclusion census](../../data/processed/lyrics_exclusion_categories.csv) covers all 5,991 non-accepted assets.
“Possible deterministic” means a concrete rule family warrants development/testing, not that it has passed a precision test. “Manual review” means existing evidence does not justify such a rule. Short genuine vocal tracks and instrumental recordings cannot be made complete by lowering the word-count threshold.

| Sample stratum | n | Safe candidate | Possible rule | Manual | Remain excluded / query / transport |
|---|---|---|---|---|---|
| bad_missing_text/bad_missing_text | 20 | 0 | 0 | 0 | 20 |
| error/error | 20 | 0 | 0 | 0 | 20 |
| not_found/not_found | 20 | 0 | 0 | 0 | 20 |
| quarantined/duration_conflict | 13 | 0 | 0 | 13 | 0 |
| quarantined/identity_incomplete_credit | 20 | 0 | 0 | 20 | 0 |
| quarantined/identity_other_credit_or_song | 20 | 0 | 8 | 11 | 1 |
| quarantined/identity_separator_variant | 20 | 11 | 7 | 2 | 0 |
| quarantined/identity_title_variant | 20 | 0 | 11 | 6 | 3 |
| quarantined/quality_embedded_credits | 20 | 1 | 17 | 1 | 1 |
| quarantined/quality_material_censorship | 20 | 0 | 5 | 15 | 0 |
| quarantined/quality_mixed_script_words | 20 | 0 | 18 | 2 | 0 |
| quarantined/quality_multiple_blockers | 5 | 0 | 5 | 0 | 0 |
| quarantined/quality_possible_non_lyric_material | 5 | 2 | 3 | 0 | 0 |
| quarantined/quality_short_text_requires_review | 20 | 0 | 0 | 15 | 5 |
| quarantined/quality_unstructured_text | 12 | 0 | 6 | 6 | 0 |
| quarantined/quality_version_only | 10 | 2 | 5 | 2 | 1 |
| quarantined/text_near_agreement | 20 | 0 | 20 | 0 | 0 |
| quarantined/text_repeat_count_only | 14 | 0 | 14 | 0 | 0 |
| quarantined/text_substantive_conflict | 40 | 0 | 24 | 16 | 0 |
| wrong_identity/identity_other_credit_or_song | 20 | 0 | 0 | 2 | 18 |
| wrong_identity/identity_title_variant | 1 | 0 | 1 | 0 | 0 |

Concrete findings (metadata/title references only; no lyric text):

- **Explicit credit syntax:** 90 assets retain all normalized name tokens in a separator variant. An offline in-memory probe normalizes Unicode punctuation, explicit “with”/slash separators, and commas before Jr., then applies the unchanged production matcher. Exactly **44** pass all existing text/version/duration checks. All 44 proposed credit mappings were inspected. No missing-guest inference or artist alias is part of this shortlist; absent separators and other conflicts still fail.
- **Five contextual false alarms:** Blac Youngsta’s *Booty* and 50 Cent’s *Disco Inferno* trigger metadata words used lyrically; Alan Jackson’s *www.memory* triggers the URL detector on its own title/refrain; *Sleazy Remix 2.0 Get Sleazier* explicitly includes Remix in the Billboard title but the matcher subtracts only parenthetical target labels; *4 AM* has “Live” in the NBA Live soundtrack album name. These are low-risk review candidates, not a general permission to ignore copyright/URL/version warnings.
- **Text disagreement:** all 20 near-agreement samples and all 14 repeated-line cases merit stronger deterministic review. In the wider-disagreement sample, 24/40 are promising; other cases include materially different narratives, omissions, and performance variants. Examples worth investigation include *Breathe* (LRC metadata/contraction artifacts), *I Will Be There* (annotations), and *Lonely Nights* (an abbreviated alternate alongside an expanded existing text). Never synthesize repeats or choose the longest text blindly.
- **Real protections:** *@ MEH* and *Meh* collapse under current punctuation normalization despite very different texts/albums/durations. *Get Away*, *Think Twice*, and *They Like It Slow* have near-unrelated texts under compatible metadata. *My Coloring Book* carries Kitty Kallen metadata but a Barbra Streisand text header; *Exodus* wraps a Hall and Oates text header. These cannot be recovered by simple threshold relaxation or header removal.
- **Mixed scripts:** 112 assets are primarily blocked by mixed Latin/Cyrillic words; sampled defects are often localized lookalikes. A narrow, logged character-normalization policy is plausible but not yet validated. Some also have masking, truncation, or remix questions. No text was repaired during this audit.
- **Credits/versions:** missing guests, alternative performers, covers, and remix guests are distinct questions. *Till The World Ends* and *Whole Lotta Choppas* must not inherit a solo text for a guest-bearing Billboard asset. Conversely, some full guest credits identify a remix even when Billboard omits that title suffix; this warrants explicit asset-level evidence, not a universal ban or universal suffix removal.
- **Text quality:** the short-text sample includes likely sparse-vocal songs as well as an apology placeholder (*There Goes My Heart Again*) and opening fragments (*Wat Da Hook Gon Be*, *What Have I Done To Deserve This?*). Collapsed layout ranges from intact prose-like text to merged words and credits. Censorship masks and clean/explicit labels can disagree. The audit does not reconstruct censored words or certify the charted radio edit.

## Other failure buckets

| Status | Assets |
|---|---|
| wrong_identity | 1365 |
| bad_missing_text | 184 |
| not_found | 872 |
| error | 51 |

- **Wrong identity:** 1,350 automatic outcomes are based on absence of the heuristic’s plausible overlap, not necessarily affirmative contradiction; 15 are prior manual exclusions. The 21-case sample includes plausible *Dog + Butterfly* versus *Dog & Butterfly*, 4/Four Seasons credits, and *Whatcha Wanna Do?* with Mia X. These show that the label overstates certainty in some cases. 1070 wrong-identity results carry the search-cap warning; returned candidates are not an exhaustive catalogue. Most sampled failures offer other performers or other songs. No recovery yield is extrapolated for this bucket.
- **Bad/missing text:** 182 text_missing and 2 text_bad. All 20 random samples had empty/instrumental target records. *Wonderland* is a preserved reviewed truncation; *Constant Rain (Chove Chuva)* is the other bad-text result. Correct performer identity cannot supply nonexistent text; another artist’s vocal cover is not a rescue.
- **Not found:** all cached retrievals were verified locally. Empty full-title/artist and title-only searches do not prove catalogue absence. 160 titles contain “from” (a broad query-research flag, not all soundtrack annotations). The sample exposes several literal film/soundtrack suffixes and a combined *Beginnings/Colour My World* identity. Removing only descriptive soundtrack context is worth a small controlled query pilot; never split/merge a combined Billboard asset implicitly. No new requests or yield assumptions were made.
- **API errors:** all 51 are HTTP 503 after bounded production retries. They are retry candidates, not 51 promised lyrics. Existing `run --retry-errors` behavior archives failures and retains provenance, but was not invoked. Even a 100% usable retry yield would add only 0.20 percentage points.

## Recovery potential and projected coverage

**A: 49 enumerated low-risk candidates** (44 explicit syntax + 5 contextual false alarms). This is a conservative shortlist, not an extrapolation or independently measured precision guarantee. Production evidence/text gates remain necessary; no mapping is approved by this report.
**B: approximately 2,066 additional possible recoveries**, beyond A, in a conditional second-pass scenario. Each quarantine stratum’s reviewed “possible deterministic” fraction is expanded to its remaining population after removing the exact low-risk shortlist. Manual/query/transport/prior-review cases contribute zero; no yield is projected for the other failure buckets. The detailed expansion is below. This estimates the size of a promising work queue, **not how many songs a yet-unbuilt rule will safely accept**. The scenario is optimistic wherever a proposed rule remains unvalidated; rejected candidates can be correlated copies of one transcription.
Under this planning allocation, approximately 3,876 of all 5,991 exclusions remain excluded or unresolved. Of these, approximately 1,404 are quarantined and 2,472 are in the other failure buckets. “Remain excluded” is a current evidence decision, not proof they are permanently unrecoverable.

| Scenario | Additional lyrics | Usable total | % of 25,363 |
|---|---|---|---|
| Current | 0 | 19372 | 76.38% |
| A: enumerated low risk | 49 | 19421 | 76.57% |
| B: A + conditional possible | ≈2,115 | ≈21,487 | ≈84.72% |

| Quarantine stratum after A | Population | Reviewed | Possible | Expanded possible |
|---|---|---|---|---|
| duration_conflict | 13 | 13 | 0 | 0.0 |
| identity_incomplete_credit | 312 | 20 | 0 | 0.0 |
| identity_other_credit_or_song | 223 | 20 | 8 | 89.2 |
| identity_separator_variant | 46 | 9 | 7 | 35.8 |
| identity_title_variant | 252 | 20 | 11 | 138.6 |
| prior_review_quarantined | 5 | 0 | 0 | 0.0 |
| quality_embedded_credits | 38 | 19 | 17 | 34.0 |
| quality_material_censorship | 57 | 20 | 5 | 14.2 |
| quality_mixed_script_words | 112 | 20 | 18 | 100.8 |
| quality_multiple_blockers | 5 | 5 | 5 | 5.0 |
| quality_possible_non_lyric_material | 3 | 3 | 3 | 3.0 |
| quality_short_text_requires_review | 52 | 20 | 0 | 0.0 |
| quality_unstructured_text | 12 | 12 | 6 | 6.0 |
| quality_version_only | 8 | 8 | 5 | 5.0 |
| text_near_agreement | 574 | 20 | 20 | 574.0 |
| text_repeat_count_only | 14 | 14 | 14 | 14.0 |
| text_substantive_conflict | 1744 | 40 | 24 | 1046.4 |

## Missingness and conditional representation

Unadjusted descriptive comparisons only. Cohorts use first Billboard chart year, not release year. Credit complexity uses the same prior audit separator heuristic (including band names). “Q share of missing” attributes missingness to the quarantine bucket; it is not a causal claim. Scenario B applies a uniform reviewed yield within each stratum, so its within-period/popularity differences are assumptions, not separately validated recovery rates.

| Group | Target | Current % | Quarantine | Q share of missing | A % | B conditional % |
|---|---|---|---|---|---|---|
| 1958–1969 | 5863 | 71.21% | 683 | 40.46% | 71.35% | ≈76.97% |
| 1970s | 4364 | 74.47% | 490 | 43.99% | 74.59% | ≈81.14% |
| 1980s | 3786 | 79.98% | 503 | 66.36% | 80.14% | ≈89.09% |
| 1990s | 3053 | 72.68% | 532 | 63.79% | 72.78% | ≈83.33% |
| 2000s | 2911 | 79.22% | 500 | 82.64% | 79.46% | ≈89.47% |
| 2010–2019 | 2997 | 82.85% | 413 | 80.35% | 83.28% | ≈91.21% |
| 2020–2026 | 2389 | 79.99% | 398 | 83.26% | 80.28% | ≈91.18% |
| 2015–2019 | 1553 | 82.81% | 217 | 81.27% | 83.45% | ≈91.56% |
| Weekly peak 1–10 | 5305 | 84.30% | 648 | 77.79% | 84.39% | ≈91.78% |
| Weekly peak 11–40 | 9150 | 78.24% | 1349 | 67.75% | 78.46% | ≈87.22% |
| Weekly peak 41–100 | 10908 | 70.97% | 1522 | 48.06% | 71.19% | ≈79.18% |
| 1 monthly basket | 5202 | 69.32% | 700 | 43.86% | 69.63% | ≈77.09% |
| 2–3 baskets | 10635 | 74.56% | 1509 | 55.76% | 74.76% | ≈82.97% |
| 4–6 baskets | 8128 | 81.43% | 1157 | 76.67% | 81.53% | ≈90.26% |
| 7+ baskets | 1398 | 87.12% | 153 | 85.00% | 87.34% | ≈94.14% |
| Complex credit False | 20530 | 79.31% | 2515 | 59.22% | 79.33% | ≈87.54% |
| Complex credit True | 4833 | 63.91% | 1004 | 57.57% | 64.87% | ≈72.73% |

Additive missingness decomposition (descriptive, not causal):

- Complex versus simple credits: 15.40 percentage-point missingness gap; 8.52 points (55.4%) attributable arithmetically to different quarantine rates.
- Weekly peaks 41–100 versus 1–10: 13.33 percentage-point missingness gap; 1.74 points (13.0%) attributable arithmetically to different quarantine rates.
- One monthly basket versus 7+: 17.80 percentage-point missingness gap; 2.51 points (14.1%) attributable arithmetically to different quarantine rates.
- Earliest-cohort missingness is largely outside quarantine: only 40.46% of missing 1958–1969 assets are quarantined, versus 81.27% in 2015–2019 and 83.26% in 2020–2026. Quarantine recovery therefore addresses modern missingness more directly; it cannot by itself remove historical or popularity selection.
- In scenario B, the 2015–2019 versus 2020–2026 coverage gap narrows from 2.83 to about 0.38 points. The earliest-cohort versus 2020–2026 gap instead widens from 8.78 to about 14.21 points. The popularity and longevity gaps shrink only modestly; the credit gap remains about 14.81 points. Recovery improves counts, not uniformly representativeness.

Monthly-rank comparisons below count song-month observations; songs repeat across bins. Calendar-period rows likewise differ from first-chart cohorts.

| Group | Target | Current % | Quarantine | Q share of missing | A % | B conditional % |
|---|---|---|---|---|---|---|
| Monthly rank 1–10 | 8180 | 85.17% | 962 | 79.31% | 85.24% | ≈92.44% |
| Monthly rank 11–25 | 12270 | 83.59% | 1540 | 76.46% | 83.69% | ≈91.36% |
| Monthly rank 26–50 | 20450 | 80.89% | 2790 | 71.41% | 81.08% | ≈89.38% |
| Monthly rank 51–100 | 40900 | 76.79% | 5810 | 61.22% | 76.97% | ≈85.39% |
| Calendar 2015–2019 | 6000 | 85.82% | 733 | 86.13% | 86.02% | ≈93.45% |
| Calendar 2020–2026 | 8100 | 84.07% | 1130 | 87.60% | 84.36% | ≈93.76% |

Interpretation: the enumerated safe shortlist is too small to materially repair overall representation. A broader successful text pass could add meaningful historical and modern coverage, but it need not reduce all gaps: credit matching and provider/query availability remain separate sources of loss. Use the group-specific scenario above, not a claim that every recovery improves bias.

## Reproduction and evidence preservation

Run `python3 src/lyrics_exclusion_audit.py` to regenerate the read-only census, verify every non-accepted result’s referenced cache/candidate revision, replay the syntax counterfactual, bind the review ledger, and generate this report/CSV. The in-memory counterfactual never replaces original title/artist strings in storage. Audit-only modules are outside the production implementation bundle.
Database fingerprints at audit start/end:

| Protected database | SHA-256 |
|---|---|
| data/processed/lyrics.db | c387ad8c64957c321a5da24ade47105a0a2af9f06908f2227b5035407d296433 |
| data/processed/research.db | d31bf1343c17a9716e81d8f9c0d7a8980504a5f57db8d13af32139bdb013d40d |
| data/processed/music.db | b40d522da1b5aa971e987e4e852b2b01b979f2e71cc034ab0152b85ca1405503 |

| Implementation file | SHA-256 |
|---|---|
| src/lyrics_exclusion_audit.py | 9bd6549817368450127fa2414accfb1a041503e7c8d177be4f535e9cceca636b |
| src/lyrics_production_match.py | 811427ad1d03956c0fe4544e448638aa9fdb295837b46fd41e8d413dc0a08594 |
| src/lyrics_lrclib_r.py | fdb7089341561f61ecc9c3cb152819b89be0a540d085a8fc96a36c64529388ae |

Runtime: Python 3.9.6, Unicode 13.0.0; audit version lrclib-exclusion-audit-v1.

Cached development-pilot counterfactual (original decisions/files untouched):

| Measure | Cases |
|---|---|
| cases | 200 |
| baseline_accepted | 154 |
| probe_accepted | 153 |
| probe_accepts_reviewed_exclusion | 0 |

| Title | Reviewed | Original automatic | Syntax counterfactual |
|---|---|---|---|
| Party To Damascus | accepted | accepted | quarantined |

The probe accepts no reviewed exclusion, but loses one prior automatic acceptance by exposing another conflicting full-credit text for Party To Damascus. This reinforces the scope: audit excluded assets; do not rerun or overwrite the accepted corpus. Zero observed false accepts on 29 development exclusions is not an independent precision guarantee.

See [audit scope and validation](../../docs/lyrics_exclusion_audit.md) for checks and limits. No lyrics were copied into the research manifest. No classifier, content scores, COVID breakpoint, or hypothesis analysis was produced.
