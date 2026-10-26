# Recommended expansion plan

**Recommendation:** approve a small local-only implementation sprint first, then separate free metadata/phonology and audio feasibility pilots. This document is a proposal. No feature engineering, classifier production, new statistical study, paid access or bulk acquisition has begun.

Rankings below balance incremental information, historical breadth, source reliability, rights, leakage and effort. They are qualitative judgments, not predicted accuracy gains. Exact candidate definitions are in [candidate_columns.csv](candidate_columns.csv); separate commercial and historical top-20 ranks are in [feasibility_matrix.csv](feasibility_matrix.csv).

## Top 15 additions overall

| Order | Proposed column | Why it earns a place | Timing / tier |
|---:|---|---|---|
| 1 | `credit_prior_top10_song_count` | Direct prior-success signal with clear historical cutoff | C / 1 |
| 2 | `credit_prior_song_count` | Experience and observed chart familiarity | C / 1 |
| 3 | `credit_recent_chart_presence` | Current career activity beyond lifetime totals | C / 1 |
| 4 | `credit_chart_career_days` | Separates new chart credits from established ones | C / 1 |
| 5 | `credit_prior_chart_points` | Prior cumulative success, truncated before debut | C / 1 |
| 6 | `previous_chart_credit_concentration` | Competition and attention concentration | C / 1 |
| 7 | `lyric_word_count` | Basic linguistic length and a necessary control | F / 1 |
| 8 | `lyric_compression_ratio` | Repetition/complexity with substantial historical literature | F / 1 |
| 9 | `lyric_mattr` | Length-controlled lexical diversity | F / 1 |
| 10 | `lyric_repeated_line_share` | Interpretable structure complementing compression | F / 1 |
| 11 | `work_lyric_language_set` | Necessary comparability and missingness context | F / 2 |
| 12 | `original_release_date_verified` | Resolves release-versus-chart timing and reissue ambiguity | F / 2 |
| 13 | `original_record_label` | Industry organization and institutional support | F / 2 |
| 14 | `hot100_methodology_regime` | Essential historical measurement context | C / 2 |
| 15 | `lyric_end_rhyme_density` | New formal linguistic information from a free lexicon | F / 2 |

F is deliberate: these are currently retrospective content/catalog measures. Original-version evidence may support a later release-time interpretation, but this campaign did not establish it. None of the F rows is advertised as a genuine historical forecasting predictor. The methodology register requires completion of a cited rule chronology; known announcements alone do not fill every interval.

## Top 10 immediately derivable features

1. `credit_prior_top10_song_count`
2. `credit_prior_song_count`
3. `credit_recent_chart_presence`
4. `credit_chart_career_days`
5. `previous_chart_credit_concentration`
6. `lyric_word_count`
7. `lyric_compression_ratio`
8. `lyric_mattr`
9. `lyric_repeated_line_share`
10. `credited_artist_entity_count` from already-retained structured metadata, only where compatible variants agree.

These need no new external acquisition. The final item is not a split on commas or “&”: bands remain entities, and ambiguous versions stay missing. Lyrics need a provider-format audit before counts are comparable. The full 59-row local list includes other useful options, but the first sprint should not implement all of them.

## Top 10 feasible free external features

| Priority | Column | Route and feasibility gate |
|---:|---|---|
| 1 | `work_lyric_language_set` | MusicBrainz work relationships; incomplete/multiple languages preserved |
| 2 | `original_release_date_verified` | MusicBrainz original-performance evidence, corroborated where needed; no reissue substitution |
| 3 | `artist_entity_type` | MusicBrainz artist entity; mixed credits require explicit representation |
| 4 | `original_record_label` | Original release label, with date and entity evidence |
| 5 | `label_major_affiliation_at_release` | Referenced Wikidata ownership intervals; current ownership excluded |
| 6 | `credited_writer_count` | Work-level composer/lyricist roles; role deduplication |
| 7 | `credited_producer_count` | Recording-level producer roles; sparse missing credits |
| 8 | `artist_formation_country` | Entity-type-appropriate origin evidence; never inferred ethnicity |
| 9 | `lyric_end_rhyme_density` | Local CMU pronunciations; report dictionary/dialect coverage |
| 10 | `hot100_methodology_regime` | Small cited manual chronology of chart-effective rules |

“Feasible” identifies an accessible mechanism, not measured song coverage. MusicBrainz field-level completeness and original-version matching are UNKNOWN. A local retained-field extraction should precede new MusicBrainz calls. Free expert chord/structure annotations are useful validation subsets but have less coverage potential than the above. Open pageviews/listens are useful modern attention experiments, not long-run replacements for industry data.

## Commercial prediction priorities

For a future **debut-time task**, the strongest practical first block is prior-credit Top-10 count, entries, recent presence, prior points and recent momentum. Next come previous-chart competition, concurrent same-credit entries and independently sourced chart-rule context. Evidence includes prior artist-success findings and historical chart dynamics, with substantial transfer limits; see A03, A05, A15 and A16 in the [academic review](academic_evidence.md).

True predebut consumption, archived editorial placements and archived artist audiences may be strong signals, but access, vintage coverage and rights are unresolved and usually modern/paid. They rank below local history in implementation priority despite potentially direct relevance. Current Spotify popularity or lifetime video views are not acceptable substitutes.

For a separate **during-run nowcast**, early rank velocity and properly lagged streams/radio can be strong candidates. Their apparent strength may reflect chart construction. Four-week accumulated points cannot be offered as an independent explanation of total points containing those four weeks. A fixed landmark, surviving-song cohort and future outcome are required; no landmark or horizon is adopted here.

A debut model already knows whether the song has entered the Hot 100; it does not answer whether an arbitrary released song will become a hit. Songs already Top 10 at debut need a separately defined treatment. Final monthly selection also depends on chart survival. Before any training, approve population, target/horizon, recurrent-run treatment and censorship rules. Use chronological evaluation, artist-overlap sensitivity, simple baselines and prespecified feature-block ablations if subsequent modeling is authorized. Do not restart exhaustive regression search.

## Historical/cultural analysis priorities

Prioritize compression, length-controlled lexical diversity, repetition, pronoun perspective, language and rhyme. These extend form and narrative framing beyond the current emotional/content scores. Next, investigate timbre, tempo, harmonic structure, dynamics and instrumentation in a version-validated audio subset. Retrospective measurements are usable for clearly labelled historical description; their version/coverage biases still require reporting.

Verified original releases, labels and chart methodology help distinguish cultural change from changes in measurement and catalog selection. Economic and demographic indicators should be added sparingly with source vintages, uncertainty and explicit temporal units. Government data are more practical than a large collection of overlapping proprietary mood indices. Social-media adoption, news, conflict and policy offer contextual hypotheses, not causal explanations. No COVID breakpoint or new historical test is selected.

Existing classifier-relative novelty is a cheap exploratory option, but its reference corpus inherits modern labels and missing lyrics. Semantic embeddings and topic mixtures may add new information but should follow a small local-form baseline and model/data-license audit. Do not create many synonym themes or thousands of vector columns to inflate the feature count.

## Proposed first implementation sprint

Planning estimate: **4–6 person-days** for one engineer familiar with this repository, excluding any new statistical modeling or acquisition. This is an effort estimate, not a measured completion guarantee.

| Step | Proposed work | Reviewable result | Estimate |
|---|---|---|---:|
| 1 | Approve forecast issue time, candidate definitions and source-row versus distinct-date rules; inspect lyric formatting on a private stratified sample | Short definition contract, ambiguity/censoring policy and test cases | 0.5–1 day |
| 2 | Implement five local chart fields: prior Top-10 count, prior song count, recent presence, career days, prior-chart concentration | Separate reproducible feature artifact joined by unchanged `song_id` | 1–2 days |
| 3 | Implement four local lyric fields: word count, compression ratio, MATTR, repeated-line share | Private computation with only permitted non-reconstructive summary export | 1–1.5 days |
| 4 | Validate prefix invariance, exact identities, missingness and era/provider formatting; inspect retained structured-credit conflicts without new requests | Tests, field availability audit, preservation hashes and reviewed release notes | 1–1.5 days |

Acceptance criteria for that **future** sprint: appending future chart observations cannot change earlier features; a prior song's future Top-10 attainment cannot affect an earlier cutoff; no all-career statistics enter prefixes; duplicate source rows are preserved and aggregates follow documented rules; missing text is not zero; no private lyric fragments appear in artifacts; dates of partial precision are not fabricated; new outputs do not overwrite frozen inputs or prior analyses. Repository regression tests and relevant read-only validation must pass. This research has not implemented those features or tests.

## Later order and effort

1. **Free metadata/phonology pilot: 3–6 additional person-days.** Use approved MBIDs and a small decade/genre/confidence-stratified sample, record agreement and source coverage, then decide whether acquisition is justified. Complete a versioned historical rule register. Source waiting/review time is additional.
2. **Audio feasibility pilot: 3–7 person-days before any population work.** Validate exact original editions, field units/extractor versions and legal access. Compare archive matches with expert annotations where available. Do not buy or scrape audio. Full coverage effort is UNKNOWN until version-valid hit rates are measured.
3. **Context layer: 1–3 person-days for a few approved series.** Choose concepts, publication lags and vintages; use sparse shared temporal controls. This does not include a COVID or causal study.
4. **Credit networks: 5–10 person-days after clean role/entity/date links exist.** Graph coverage and boundary sensitivity are likely the main work. Free sources make a sparse graph possible; they do not make it representative.
5. **Licensed modern exposure: UNKNOWN procurement time, then 2–5 person-days for a scoped pilot.** Obtain exact history/territory/retention/derived-publication terms and a price quote first. No budget is authorized by this recommendation.

These phases share infrastructure and are not additive quotes for all 182 candidates. A useful small expansion could be reviewed after the first sprint; the broad inventory is a menu, not a request to engineer every row.

## Main obstacles and stop conditions

The largest gaps are original-version audio, long historical promotion/consumption data, dated writer/producer credits, artist entity resolution, historical social audiences and a validated historical slang resource. Contractual terms, archived metric timestamps, original-versus-remastered recordings, partial dates and selection-dependent missingness determine feasibility more than a source's headline catalog size. If a pilot cannot establish rights or exact identity, leave the value missing and defer that route.

This campaign ends after validated research artifacts are committed and pushed. Implementation, acquisition, modeling and new analyses remain pending the user's approval of these findings.
