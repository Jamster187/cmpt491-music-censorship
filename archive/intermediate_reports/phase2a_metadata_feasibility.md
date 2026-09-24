# Phase 2A: metadata feasibility

Generated from the cached MusicBrainz experiment. No manual match overrides were applied.

MusicBrainz is the only provider tested. See [source research](phase2a_source_research.md) for fields, authentication, rate limits, terms, and possible complements; see [experiment instructions](../experiments/phase2a/README.md) for reproduction and exact matching rules.

## Sample and scope

The fixed sample has 200 unique Billboard title/artist pairs from 32723 identities. Periods use first Billboard appearance, not release year. Every first-appearance year from 1958 through 2026 is represented. The sample deliberately balances periods and oversamples difficult credits; its aggregate rates are descriptive pilot results, not population estimates.

Difficulty flags overlap: `{"common_title": 34, "early_chart_era": 29, "featured_artists": 26, "punctuation_heavy": 19, "unusual_credit": 40}`. Selection reasons: `{"challenge:common_title": 14, "challenge:featured_artists": 14, "challenge:punctuation_heavy": 14, "challenge:unusual_credit": 14, "hash_fill": 75, "year_coverage": 69}`.

## Matching results

| Status | Count | % of sample |
| --- | ---: | ---: |
| high_confidence | 45 | 22.50% |
| ambiguous | 141 | 70.50% |
| not_found | 14 | 7.00% |
| error | 0 | 0.00% |
| pending | 0 | 0.00% |

High-confidence means a unique recording link passing the documented rule, not independently measured matching accuracy. A Billboard asset can legitimately have several recordings: this strict pilot leaves those ambiguous rather than selecting one arbitrarily. `not_found` means no candidates from the two bounded searches, not proof that MusicBrainz lacks the song.

| First-chart period | Sample | High confidence | Ambiguous | Not found | Error | Match rate | Recording genres / sample |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1958–1969 | 29 | 2 | 20 | 7 | 0 | 6.90% | 0/29 |
| 1970s | 29 | 10 | 18 | 1 | 0 | 34.48% | 5/29 |
| 1980s | 29 | 6 | 22 | 1 | 0 | 20.69% | 2/29 |
| 1990s | 29 | 3 | 23 | 3 | 0 | 10.34% | 2/29 |
| 2000s | 28 | 4 | 23 | 1 | 0 | 14.29% | 4/28 |
| 2010s | 28 | 11 | 16 | 1 | 0 | 39.29% | 5/28 |
| 2020–2026 | 28 | 9 | 19 | 0 | 0 | 32.14% | 4/28 |

## Metadata coverage on accepted links

The first percentage uses the 45 high-confidence matches; the second uses all 200 sampled identities. Unmatched/ambiguous songs do not contribute metadata coverage. Raw tags can describe things other than genre, and contextual release-group/artist genres are not song-level genre assignments.

| Field / entity level | Count | % of matches | % of sample |
| --- | ---: | ---: | ---: |
| recording_genres | 22 | 48.89% | 11.00% |
| recording_positive_vote_genres | 22 | 48.89% | 11.00% |
| recording_tags | 26 | 57.78% | 13.00% |
| recording_genres_or_tags | 26 | 57.78% | 13.00% |
| release_group_genres | 35 | 77.78% | 17.50% |
| release_group_tags | 36 | 80.00% | 18.00% |
| artist_genres | 39 | 86.67% | 19.50% |
| artist_tags | 39 | 86.67% | 19.50% |
| first_release_date | 45 | 100.00% | 22.50% |
| album_or_release | 45 | 100.00% | 22.50% |
| album_context | 40 | 88.89% | 20.00% |
| duration | 45 | 100.00% | 22.50% |
| recording_id | 45 | 100.00% | 22.50% |
| artist_ids | 45 | 100.00% | 22.50% |
| release_group_ids | 45 | 100.00% | 22.50% |
| isrcs | 29 | 64.44% | 14.50% |
| work_ids | 21 | 46.67% | 10.50% |
| artist_type | 45 | 100.00% | 22.50% |
| artist_country | 45 | 100.00% | 22.50% |
| release_country | 43 | 95.56% | 21.50% |
| release_text_language | 43 | 95.56% | 21.50% |
| recording_rating | 20 | 44.44% | 10.00% |

Dates are required by the acceptance rule, so their coverage among accepted links is conditional by construction. Dates may have only year/month precision. Durations are milliseconds. Release text language is not lyric language. Album/release coverage includes singles and reissues; no canonical album is inferred. Release-group lookups are bounded to three eligible groups and recording lookups return only the provider's linked-release subset.

## Decision reasons and API reliability

| Reason | Count |
| --- | ---: |
| competing_plausible_recordings | 16 |
| multiple_eligible_recordings | 88 |
| no_candidate_passes_strict_rule | 31 |
| no_search_candidates | 14 |
| search_results_truncated | 6 |
| unique_exact_credit_with_date_support | 45 |

Cached requests: 396. HTTP/transport attempts: `{"200": 396, "503": 11}`. Optional contextual-lookup errors affected 0 songs. Retries and failures are retained, including failures recovered before a song completed.

Retrieval window (UTC): 2026-09-19T08:04:48+00:00 through 2026-09-19T08:14:55+00:00.

## Examples


### high_confidence

| Billboard identity | Period | Evidence / reason |
| --- | --- | --- |
| Where Did I Go Wrong / Dee Dee Sharp | 1958–1969 | unique_exact_credit_with_date_support; Where Did I Go Wrong / Dee Dee Sharp; first release 1964; [recording](https://musicbrainz.org/recording/e3069be7-b443-4877-8068-eeb3783ac0fe) |
| The Man / Lorne Greene | 1958–1969 | unique_exact_credit_with_date_support; The Man / Lorne Greene; first release 1965; [recording](https://musicbrainz.org/recording/a6eb21c6-d554-45ca-bb68-b0be6d3b79d3) |
| I Found My Dad / Joe Simon | 1970s | unique_exact_credit_with_date_support; I Found My Dad / Joe Simon; first release 1972; [recording](https://musicbrainz.org/recording/586dab58-1edf-4835-ac6b-b623b5670281) |
| (I Don't Want To Love You But) You Got Me Anyway / Sutherland Brothers And Quiver | 1970s | unique_exact_credit_with_date_support; (I Don’t Want to Love You but) You Got Me Anyway / Sutherland Brothers & Quiver; first release 1973; [recording](https://musicbrainz.org/recording/bc43920b-fc33-442d-827c-20fba34893bf) |

### ambiguous

| Billboard identity | Period | Evidence / reason |
| --- | --- | --- |
| A Brand New Me / Dusty Springfield | 1958–1969 | no_candidate_passes_strict_rule; 6 candidates; 0 eligible; top: A Brand New Me / Dusty Springfield (2003) |
| All I Have To Offer You (Is Me) / Charley Pride | 1958–1969 | competing_plausible_recordings; 38 candidates; 1 eligible; top: All I Have To Offer You (Is Me) / Charley Pride (1969) |
| Help The Poor / B.B. King | 1958–1969 | competing_plausible_recordings; 27 candidates; 1 eligible; top: Help the Poor / B.B. King (1964) |
| Jenny Lou / Sonny James | 1958–1969 | no_candidate_passes_strict_rule; 7 candidates; 0 eligible; top: Jenny Lou / Sonny James (2010) |

### not_found

| Billboard identity | Period | Evidence / reason |
| --- | --- | --- |
| Suddenly / Nickey DeMatteo | 1958–1969 | no_search_candidates; no results from title + full credit or title + lead artist search |
| Darling Take Me Back / Lenny Welch | 1958–1969 | no_search_candidates; no results from title + full credit or title + lead artist search |
| Try My Love Again / Bobby Moore's Rhythm Aces featuring Chico | 1958–1969 | no_search_candidates; no results from title + full credit or title + lead artist search |
| Dear Lady Twist / Gary U.S. Bonds | 1958–1969 | no_search_candidates; no results from title + full credit or title + lead artist search |

### error

| Billboard identity | Period | Evidence / reason |
| --- | --- | --- |
| None in this run | — | — |

### Deliberately difficult cases

| Billboard identity | Difficulty | Outcome |
| --- | --- | --- |
| Try My Love Again / Bobby Moore's Rhythm Aces featuring Chico | featured_artists | not_found: no_search_candidates |
| I Can't Go On Livin' Baby Without You / Nino Tempo & April Stevens | punctuation_heavy | ambiguous: no_candidate_passes_strict_rule |
| Suddenly / Nickey DeMatteo | common_title | not_found: no_search_candidates |
| I Can't Go On Livin' Baby Without You / Nino Tempo & April Stevens | unusual_credit | ambiguous: no_candidate_passes_strict_rule |

See [review notes](phase2a_review_notes.md) for additional inspected examples, including covers, featured credits, older recordings charting recently, and restrictive search-score thresholds. These notes do not override any match decision.

## Recommendation

Do not scale this matcher to all 32,723 identities yet. Direct recording-genre coverage in this pilot is 22/200 (11.00%); accepted recording links with raw genres are 22/45 (48.89%). Artist/release-group tags offer context but cannot be silently substituted for song genres. This measures the yield of this strict matcher, not the maximum metadata coverage MusicBrainz could provide for title/artist assets.

Before scaling, independently review a labeled set of accepted and rejected candidates to measure precision, decide how a title/artist asset should link to multiple legitimate recordings, improve artist-credit/alias retrieval without dropping contributors, and investigate dated reissues and early/new-release gaps. Evaluate an additional genre source or an explicitly labeled contextual-genre strategy on this same frozen sample, then validate on a fresh holdout sample. Keep every match decision and entity-level tag provenance. No major-genre taxonomy is chosen here.

This run retrieves no lyrics and makes no classifier, COVID-breakpoint, or content-trend inference. Phase 1 remains separate and unchanged. The source snapshot and canonical database hashes, code hashes, full candidate evidence, original responses, per-song results, and CSV export are retained locally in the documented locations.
