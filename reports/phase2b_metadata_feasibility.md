# Phase 2B: alternative metadata pilot

Generated from cached Wikidata responses. Last.fm and Discogs were researched but not queried for song enrichment. See [source research](phase2b_source_research.md) and [reproduction and matching rules](../experiments/phase2b/README.md).

## Scope and definitions

Exactly 200 Billboard identities, copied byte-for-byte from the Phase 2A sample; 200 processed, 0 pending. The same first-chart period buckets and deliberate difficult cases are retained. These balanced pilot rates are not population estimates.

Candidate-found means an exact title with performer-name support or a hit in the joint title/artist search. It can still be an album, incomplete credit, or mixed work item. Song-candidate-found additionally requires a supported music-item type. High-confidence requires a complete performer-set match and the documented type/version checks. These are operational rules, not a measured precision estimate.

## Overall results

| Measure | Count | % of sample |
| --- | ---: | ---: |
| Candidate found | 132 | 66.00% |
| Song candidate found | 127 | 63.50% |
| high_confidence | 99 | 49.50% |
| ambiguous | 39 | 19.50% |
| not_found | 62 | 31.00% |
| error | 0 | 0.00% |

Not-found means no plausible pair in the bounded searches, not proven absence from Wikidata. An inconclusive capped search stays ambiguous. API errors are separate from negative matches.

## Comparison on the same sample

| Measure | Phase 2A: MusicBrainz | Phase 2B: Wikidata |
| --- | ---: | ---: |
| High-confidence assets | 45/200 (22.50%) | 99/200 (49.50%) |
| Accepted assets with genre evidence | 22/200 recording genres | 84/200 song/work/single/track-item genres |
| Accepted assets with genre or tag evidence | 26/200 recording genres/tags | 84/200 item genres; no free-form tag endpoint |

Both provider and matcher changed: Phase 2A required a unique recording and supporting date, whereas Phase 2B links title/performer assets, permits multiple same-performer items and does not require dates. The yield difference cannot be attributed to the provider alone. Wikidata genres on work/single items and MusicBrainz recording genres also have different scopes.

Accepted by both: 14; only MusicBrainz: 31; only Wikidata: 85; accepted by either: 130/200. Genre evidence at either source's stated level reaches 99/200; including MusicBrainz raw tags reaches 103/200. These unions are audit comparisons, not merged genre assignments.

## Historical coverage

Percentages below use each period's full sample. Metadata counts require an accepted link.

| First-chart period | N | Found candidates | Accepted (% of N) | Ambiguous | Not found | Error | Item genres | Dates | Albums | Duration | MB accepted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1958–1969 | 29 | 10 | 6 (20.69%) | 5 | 18 | 0 | 6 | 6 | 1 | 1 | 2 |
| 1970s | 29 | 10 | 7 (24.14%) | 5 | 17 | 0 | 7 | 7 | 2 | 1 | 10 |
| 1980s | 29 | 22 | 18 (62.07%) | 4 | 7 | 0 | 18 | 18 | 2 | 1 | 6 |
| 1990s | 29 | 23 | 17 (58.62%) | 6 | 6 | 0 | 15 | 17 | 4 | 1 | 3 |
| 2000s | 28 | 27 | 23 (82.14%) | 5 | 0 | 0 | 20 | 23 | 3 | 0 | 4 |
| 2010s | 28 | 18 | 15 (53.57%) | 4 | 9 | 0 | 12 | 15 | 2 | 2 | 11 |
| 2020–2026 | 28 | 22 | 13 (46.43%) | 10 | 5 | 0 | 6 | 9 | 5 | 8 | 9 |

## Metadata coverage

Denominators: 99 accepted assets and 200 sampled assets. An asset contributes once per field even when it links to several items. Only non-deprecated value statements count toward coverage; all returned raw statements remain cached.

| Field / scope | Count | % accepted | % sample |
| --- | ---: | ---: | ---: |
| song_item_genres | 84 | 84.85% | 42.00% |
| recording_or_track_item_genres | 6 | 6.06% | 3.00% |
| single_release_item_genres | 68 | 68.69% | 34.00% |
| composition_item_genres | 16 | 16.16% | 8.00% |
| generic_song_item_genres | 8 | 8.08% | 4.00% |
| song_item_genres_unqualified | 84 | 84.85% | 42.00% |
| song_item_genres_with_references | 74 | 74.75% | 37.00% |
| publication_date | 95 | 95.96% | 47.50% |
| album_context | 19 | 19.19% | 9.50% |
| duration_quantity | 14 | 14.14% | 7.00% |
| wikidata_song_item_id | 99 | 100.00% | 49.50% |
| performer_ids | 99 | 100.00% | 49.50% |
| musicbrainz_recording_id | 16 | 16.16% | 8.00% |
| musicbrainz_work_id | 47 | 47.47% | 23.50% |
| musicbrainz_release_group_id | 32 | 32.32% | 16.00% |
| isrc | 16 | 16.16% | 8.00% |
| composer_ids | 11 | 11.11% | 5.50% |
| producer_ids | 40 | 40.40% | 20.00% |
| record_label_ids | 77 | 77.78% | 38.50% |
| work_language | 24 | 24.24% | 12.00% |
| artist_context_genres | 97 | 97.98% | 48.50% |
| album_context_genres | 18 | 18.18% | 9.00% |

Wikidata supplies structured genre IDs/labels, not Last.fm-style free-form tags. Genre scope rows overlap when an asset has several item types or links; they are not additive. The generic song type does not resolve composition versus recording scope. Publication dates preserve precision, qualifiers and calendar; they are not automatically original release dates. Durations retain quantities and units. Album coverage requires an explicit parent relation and album type. Artist/album genres are separate context and never counted as song-item genres. A statement reference may merely be an import from a wiki; it is not independent validation.

## Examples

### high_confidence

| Billboard identity | Evidence |
| --- | --- |
| All I Have To Offer You (Is Me) / Charley Pride | exact_title_and_complete_performer_set; [Q4728845](https://www.wikidata.org/wiki/Q4728845) / Charley Pride; raw genres: country music |
| Rocky Mountain Way / Joe Walsh | exact_title_and_complete_performer_set; [Q2370451](https://www.wikidata.org/wiki/Q2370451) / Joe Walsh; raw genres: rock music |
| Early In The Morning / The Gap Band | exact_title_and_complete_performer_set; [Q5326830](https://www.wikidata.org/wiki/Q5326830) / The Gap Band; raw genres: funk |
| Anything But Down / Sheryl Crow | exact_title_and_complete_performer_set; [Q4778343](https://www.wikidata.org/wiki/Q4778343) / Sheryl Crow; raw genres: country music |
| Get My Drink On / Toby Keith | exact_title_and_complete_performer_set; [Q16839957](https://www.wikidata.org/wiki/Q16839957) / Toby Keith; raw genres: country rock |

### ambiguous

| Billboard identity | Evidence |
| --- | --- |
| Suddenly / Nickey DeMatteo | bounded_search_incomplete |
| Once You Get Started / Rufus Featuring Chaka Khan | incomplete_credit_type_or_version_evidence; [Q17041469](https://www.wikidata.org/wiki/Q17041469) / Rufus |
| Notorious / Loverboy | bounded_search_incomplete; [Q107388964](https://www.wikidata.org/wiki/Q107388964) /  |
| Get Money / Junior M.A.F.I.A. Featuring The Notorious B.I.G. | incomplete_credit_type_or_version_evidence; [Q5554041](https://www.wikidata.org/wiki/Q5554041) / Junior M.A.F.I.A. |
| Flipside / Freeway Featuring Peedi Crakk | incomplete_credit_type_or_version_evidence; [Q111938756](https://www.wikidata.org/wiki/Q111938756) /  |

### not_found

| Billboard identity | Evidence |
| --- | --- |
| Help The Poor / B.B. King | no_plausible_title_performer_candidate |
| Move Your Boogie Body / Bar-Kays | no_plausible_title_performer_candidate |
| Computer Game "Theme From The Circus" / Yellow Magic Orchestra | no_plausible_title_performer_candidate |
| Spend My Life / Slaughter | no_plausible_title_performer_candidate |
| Falling Slowly / Lee DeWyze & Crystal Bowersox | no_plausible_title_performer_candidate |

### error

| Billboard identity | Evidence |
| --- | --- |
| None in this run | — |

See [inspected examples and review notes](phase2b_review_notes.md) for additional cover, alias, featured-credit and entity-scope cases.

## Limitations and next step

Wikidata can provide auditable genre and identity statements for some title/performer assets, but is not a complete music catalog. Albums sharing a song title, compositions with several cover performers, missing featured credits, missing item types, sparse older/new entries, and bounded English-language retrieval can all reduce yield. An absent genre is not evidence of a genre-free song.

Last.fm remains the most promising direct title/artist tag interface from documentation; its coverage is untested here. Academic access, a project key, snapshot retention and sharing conditions should be resolved before that comparison. Discogs may add release context, but release styles should not be silently transferred to tracks and its API retention terms need clarification.

Do not scale to all 32,723 assets yet. Review accepted and ambiguous links against independent evidence, evaluate a fresh holdout, and test Last.fm on this same sample if access is obtained. MusicBrainz remains useful for identifiers, dates, release context and duration, especially with a separately evaluated asset-level association rule. Keep provider disagreements and semantic levels explicit. No taxonomy or final study population is chosen here.

## Audit

Decision reasons: `{"bounded_search_incomplete": 13, "exact_title_and_complete_performer_set": 99, "incomplete_credit_type_or_version_evidence": 26, "no_plausible_title_performer_candidate": 62}`.

Capped searches: 34; accepted assets with multiple items: 15; selected items whose reported publication years are all later than chart year + 1: 0; assets with optional metadata lookup errors: 0.

Cached unique requests: 835; attempts by HTTP status: `{"200": 835}`. Retrieval window (UTC): 2026-09-19T08:48:08+00:00 through 2026-09-19T09:09:11+00:00.

Sample SHA-256: `fb9c0e171b75666c1ef893df00659bc55a49fe0ddc14babfa537c94ca6d3ff69`. Matcher: `phase2b-wikidata-asset-v1`. Full source/code hashes and runtime versions are in the local summary JSON. Original responses, revision IDs, claims, references and candidate decisions are retained under the documented ignored cache/experiment paths. Phase 1 and the Phase 2A sample are checked against their frozen hashes. No lyrics, content classifier, taxonomy collapse or statistical analysis is included.
