# Genre assignment feasibility

This experiment inventories the final **28,041-song** month-end population and assigns candidate genres to **300 songs only**. The 818 snapshots and 81,797 observations remain unchanged. No public dataset, lyrics, metadata, or classifier results were updated. No historical content analysis was performed.

## Frozen taxonomy

Pop, Rock, Hip-Hop / Rap, R&B / Soul, Country, Latin, Electronic / Dance, Alternative / Indie, Metal, Folk / Singer-Songwriter, Jazz / Blues, Reggae / Dancehall, Gospel / Christian, K-Pop, Afrobeats / African Pop, Other.

There are 15 named categories plus Other. An empty primary genre is missingness, not a seventeenth genre. The taxonomy is intentionally broad but not mutually exclusive: style, region/market and religion can overlap. No categories were added or merged.

## Existing evidence

**19,401 songs** have positive raw genre/tag evidence; **18,759 (66.90%)** have at least one eligible label recognized by the mapping, at any semantic level. **18,093 (64.52%)** have direct recording/song-item evidence. These are evidence-availability counts, not primary-genre assignments.

| Provider / semantic level | Songs with eligible mapped evidence |
|---|---:|
| MusicBrainz/artist | 618 |
| MusicBrainz/recording | 18,081 |
| MusicBrainz/release | 134 |
| MusicBrainz/release-group | 69 |
| Wikidata/album | 13 |
| Wikidata/artist | 3,652 |
| Wikidata/song_item | 75 |

Counts overlap. Inventory includes both production metadata databases, all MusicBrainz pilot/production request caches, archived accepted Wikidata matches, and all Wikidata request caches. Exact P434 artist crosswalks reuse cached artist evidence without new name matching. LRCLIB has no genre field; the old generic Discogs access probe has no accepted song crosswalk. No Last.fm song cache exists.
Successfully cached responses inspected: {'MusicBrainz': 34214, 'Wikidata': 835}. Failed cached requests were counted separately: {'failed_mb_cache': 1}. Cache keys/body hashes were checked; original payloads remain local. A missing cached genre field is not proof the provider has no genre.

## Proposed method and sources

Use exact accepted entity links, then a versioned exact-label dictionary; do not infer genre from performer nationality, lyrics, classifier scores, or loose substrings. Direct recording/song-item evidence outranks artist context. Album/release-group tags remain context because existing links include compilations and do not establish track-specific genre. Duplicate editions do not count as independent votes. One direct mapped category produces a candidate primary; conflicting categories preserve NULL primary and all candidates. Artist-only suggestions are not confident song assignments. Other requires affirmative out-of-taxonomy evidence.
The only parent reduction is generic Rock alongside explicit Metal or Alternative / Indie. Composite styles still retain competing categories. Confidence is an evidence grade, not a calibrated probability. Detailed rules and all aliases are in [the method](../../docs/genre/method.md) and [mapping](../../docs/genre/taxonomy_mapping.json).
MusicBrainz and Wikidata are the practical starting sources. MusicBrainz tags/genre associations require attribution and noncommercial share-alike handling; Wikidata structured statements are CC0. Last.fm is a potential track-level fallback but academic API access requires prior contact. Discogs API retention terms and release-level genre semantics make it unsuitable as the default frozen-song source here. See [source review and official references](../../docs/genre/sources.md). There were **zero new genre API requests**.

## 300-song pilot

The frozen sample contains 63 predeclared challenge identities and 237 hash-selected songs balanced across period, peak-rank and artist-credit-format strata. Six periods contain 43 songs each; 2020–2026 contains 42. Raw sample percentages are not unbiased population estimates. The pipeline did not use lyrical content or model scores.

| Disposition | Songs | Percent |
|---|---:|---:|
| confident_primary | 40 | 13.33% |
| release_supported | 0 | 0.00% |
| ambiguous | 150 | 50.00% |
| Other | 1 | 0.33% |
| context_only | 3 | 1.00% |
| insufficient_evidence | 106 | 35.33% |

`confident_primary` is the operational single-direct-category status, not independently certified correctness. Context-only rows have missing primary genres; they belong with insufficient song-level evidence for analytical use.

## Qualitative review

Reviewed 60 cases: all 41 non-null primary labels plus 19 boundary cases. Judgments: {'plausible': 37, 'questionable': 16, 'unassessed': 3, 'clearly_wrong': 4}. Three clearly misleading primary assignments were found (Murder On My Mind, Hooked On You, Essence); Redbone also has a clearly misleading candidate set despite abstention. These are qualitative findings, not an estimated error rate. Single-vote tags can produce false confidence, while noisy minor tags can block sensible primaries. Recording IDs and performer credits were checked for the most conspicuous failures; this is a genre-evidence problem, not evidence that the existing lyric matches should be changed.

Judgments are qualitative metadata/genre plausibility checks, not listening-based gold labels or an accuracy estimate. Cached genre labels cannot independently validate themselves. Review notes distinguish a plausible abstention from a correct positive assignment, and independent references are supplied for selected boundary cases. Candidate outputs were not overridden.

| Song / artist | Pilot result | Review | Reason |
|---|---|---|---|
| Unwind — Ray Stevens | Other | questionable | A lone comedy tag creates Other. Ray Stevens also made serious recordings; no song-specific independent corroboration was established. |
| Respect — Aretha Franklin | ambiguous | questionable | Abstention is safe, but soul has nine votes while ambient/gospel/jazz/rock have one. Presence-only union lets weak tags swamp strong soul evidence. |
| I Fall To Pieces — Patsy Cline | Country | plausible | Country, Nashville sound and traditional-country evidence agree; appropriate broad primary. |
| Jolene — Dolly Parton | ambiguous | questionable | Country has eight votes and bluegrass/country-pop four; single reggae, punk and big-beat tags inflate the candidate set on the same Dolly recording. |
| Paranoid — Black Sabbath | insufficient_evidence | unassessed | No accepted mapped song evidence in this inventory; missingness must not be treated as absence of Metal in the population. |
| Fast Car — Tracy Chapman | ambiguous | plausible | Folk, folk-rock, rock and alternative evidence genuinely overlap; no single compulsory category is defensible from tags alone. |
| Purple Rain — Prince And The Revolution | R&B / Soul | questionable | Only a one-vote funk tag survives. An exclusive R&B primary underrepresents this rock/soul ballad. |
| Walk This Way — Run-D.M.C. | ambiguous | plausible | Direct rap and rock support reflect the documented Run-D.M.C./Aerosmith crossover; keep both. [Review reference](https://rockhall.com/inductees/run-dmc/). |
| Hooked On You — Silk | Pop | clearly_wrong | Pop alone is misleading for this R&B performance; one pop tag overrides absence of better song evidence. Independent catalogue/chart references identify R&B. [Review reference](https://www.officialcharts.com/songs/silk-hooked-on-you/). |
| Doo Wop (That Thing) — Lauryn Hill | ambiguous | plausible | R&B/Soul and Hip-Hop/Rap are both directly well supported; preserving genuine ambiguity is appropriate. |
| I'll Never Let You Go — Steelheart | Rock | plausible | Rock is a defensible broad label; a Metal secondary label would require explicit supporting song evidence. |
| Smells Like Teen Spirit — Nirvana | ambiguous | questionable | Grunge has 24 votes and alternative rock six; a one-vote pop tag prevents primary assignment. Generic-parent reduction alone does not solve weak-tag contamination. [Review reference](https://rockhall.com/inductees/nirvana/?field_induction_category=All). |
| Looking For You — Kirk Franklin | ambiguous | plausible | Gospel and R&B reflect overlapping religious and stylistic categories; ambiguity is sensible. |
| Don't Know Why — Norah Jones | ambiguous | plausible | Jazz and Pop overlap is credible. Genre-specific award context also demonstrates why one exclusive label is not ground truth. [Review reference](https://www.grammy.com/artists/norah-jones/13227/). |
| Redbone — Childish Gambino | ambiguous | clearly_wrong | The retained candidate set is rap/house and omits R&B/Soul. The song won Traditional R&B Performance; correct external identity does not guarantee correct tags. [Review reference](https://www.grammy.com/awards/categories/best-traditional-rb-performance/2018/). |
| La Bicicleta — Carlos Vives & Shakira | Pop | questionable | Pop is a possible broad description but one generic tag loses the Latin crossover. Do not infer Latin solely from language. [Review reference](https://www.sonymusic.es/eventos/carlos-vives-y-shakira-estrenan-el-video-oficial-de-la-bicicleta/). |
| Murder On My Mind — YNW Melly | Pop | clearly_wrong | A single pop tag produces a misleading primary for this rap song. Song-level catalogue genre is Hip-Hop/Rap. [Review reference](https://www.shazam.com/en-us/song/1419601421/murder-on-my-mind). |
| Here With Me — Marshmello Featuring CHVRCHES | Pop | plausible | Pop is defensible under the frozen dance-pop/electropop mapping; Electronic overlap remains a taxonomy boundary. |
| Water — Tyla | ambiguous | questionable | Pop/R&B is plausible but missing amapiano/African-pop evidence hides the key global crossover. Independent source describes that fusion. [Review reference](https://www.grammy.com/news/tyla-winner-best-african-music-performance-water-2024-grammys-meaning/). |
| Essence — Wizkid Featuring Justin Bieber & Tems | Electronic / Dance | clearly_wrong | One house tag yields Electronic / Dance; cached singular afrobeat is unmapped. This is a misleading primary for the Wizkid/Tems/Bieber Afrobeats/R&B crossover. [Review reference](https://time.com/6125601/best-songs-2021/). |
| Dynamite — BTS | ambiguous | plausible | Pop and K-Pop ambiguity is appropriate; the artist label calls the song disco pop. K-Pop is not mutually exclusive with Pop. [Review reference](https://ibighit.com/legacy/bts/dynamite-en.html). |

All 60 case notes and the review selection rule are in [review.json](../../reports/genre/review.json). The main table above shows representative failures and boundaries.

## Historical coverage diagnostics

Periods use first Billboard appearance. Evidence columns below are exact population census counts; the final column is a rough design-weighted estimate of this rule’s *primary-label availability*, not accuracy. It expands each non-challenge period/rank/credit stratum by N/n and adds the fixed challenge cases. With only about 34 random cases per period, these estimates are uncertain. They must not be read as genre or content trends.

| Period | Population | Any mapped evidence | Direct mapped evidence | Pilot primary / n | Estimated primary coverage |
|---|---:|---:|---:|---:|---:|
| 1958–1969 | 6,808 | 3,935 (57.8%) | 3,898 (57.3%) | 6/43 | 15.9% |
| 1970s | 5,008 | 3,402 (67.9%) | 3,368 (67.3%) | 3/43 | 15.5% |
| 1980s | 4,000 | 2,882 (72.0%) | 2,838 (71.0%) | 3/43 | 8.3% |
| 1990s | 3,329 | 2,232 (67.0%) | 2,201 (66.1%) | 3/43 | 17.6% |
| 2000s | 3,065 | 2,484 (81.0%) | 2,425 (79.1%) | 5/43 | 11.6% |
| 2010–2019 | 3,168 | 2,395 (75.6%) | 2,246 (70.9%) | 13/43 | 39.2% |
| 2020–2026 | 2,663 | 1,429 (53.7%) | 1,117 (41.9%) | 8/42 | 14.0% |

Existing mapped-evidence availability is uneven: roughly 58% for 1958–1969, 81% for the 2000s, and 54% for 2020–2026. Direct evidence is only about 42% for the latest period. This is not merely an old-music problem: newly charting/global music and collaboration-specific identities also lack suitable cached tags. Cached artist context increases recent availability but cannot establish historical song style. Applying the current primary rule would introduce large, period-dependent selection effects.

## Analytical suitability

| Category | Pilot primary songs | Pilot songs with any supporting evidence | Monthly rows of those primary songs |
|---|---:|---:|---:|
| Afrobeats / African Pop | 0 | 2 | 0 |
| Alternative / Indie | 0 | 24 | 0 |
| Country | 11 | 30 | 53 |
| Electronic / Dance | 3 | 61 | 16 |
| Folk / Singer-Songwriter | 0 | 14 | 0 |
| Gospel / Christian | 0 | 6 | 0 |
| Hip-Hop / Rap | 7 | 50 | 37 |
| Jazz / Blues | 2 | 21 | 8 |
| K-Pop | 0 | 1 | 0 |
| Latin | 1 | 9 | 5 |
| Metal | 0 | 7 | 0 |
| Other | 1 | 3 | 2 |
| Pop | 9 | 143 | 43 |
| R&B / Soul | 4 | 72 | 10 |
| Reggae / Dancehall | 0 | 8 | 0 |
| Rock | 3 | 95 | 10 |

Supporting evidence is common for Pop (143 pilot songs), Rock (95), R&B / Soul (72), Hip-Hop / Rap (50) and Country (30), so these look plausible for broad pooled comparisons after evidence quality is fixed. The current primary rule is too sparse: only three Rock and four R&B primaries, and no Alternative, Metal, Folk, Reggae, Gospel, K-Pop or Afrobeats primaries. These zeros describe this method and sample, not absence of those genres. Latin, Metal, Reggae, Gospel and Jazz/Blues need special coverage checks. K-Pop and Afrobeats are likely concentrated in recent periods and will not support a continuous 1958–2026 series; earlier empty periods would be expected, but exact population/window counts have not been assigned. Folk/Alternative/Rock and Gospel/R&B overlap can make primary-only series selectively exclude crossovers.

These counts cannot establish adequate observations in every monthly window. The pilot deliberately includes rare modern/global cases. Absence from a pilot period is not a population zero. Before time-series analysis, count actual genre membership and nonmissing classifier observations per window, and report coverage/ambiguity rather than treating every missing genre as Other. No categories were merged.

## Scaling and validation

The local pilot plus full evidence-availability census took 11.3 seconds on this machine. The ignored inventory occupies 6,450,876,416 bytes; retained pilot evidence occupies 4,129,068 bytes. This is evidence storage, not a new production database. The exhaustive cache index took approximately 24 minutes as a one-time step; subsequent pilot replays reuse it.
Accepted links contain 235,264 distinct recording IDs and 6,095 artist IDs. Looking up every recording at 1.1 seconds/request would have a rate-spacing floor of 71.9 hours, before latency/backoff. Artist-only lookups would take at least 1.86 hours and still would not establish song genre. Do not start either crawl. A future accepted cache-only rule would require zero APIs; a conservative planning allowance is under an hour locally after indexing, not a measured full-population assignment runtime.

Rebuild commands and scope guards: [docs/genre/method.md](../../docs/genre/method.md). The 300-row results are reproducible; source hashes, mapping/code hashes and the evidence-input manifest digest are retained. Tests and protected-data validation are recorded in the validation note below.

## Recommendation

**B — METHOD NEEDS ONE SPECIFIC IMPROVEMENT: a validated song-level evidence-strength gate.** Replace “one recognized positive tag = confident” and the indiscriminate union of all positive tags with a bounded corroboration/dominance pilot. Preserve per-recording vote support, distinguish isolated one-vote tags from strongly supported direct evidence, and corroborate single-vote or conflicting cases with a song-specific reference (prefer existing accepted Wikidata song items or targeted MusicBrainz detail lookups). Do not count duplicated editions or synonymous labels as independent votes; genuine genre crossovers must still abstain. Select and freeze candidate support rules before replaying this same pilot, then check primary precision and period-specific availability on independently reviewed cases. No threshold is approved here, and artist-only fallback must remain explicitly provisional. The existing cache-only rule is NOT READY for production. Broad source coverage is useful, but it cannot by itself establish primary-genre reliability.

Stopped before full genre assignment, public dataset replacement, or historical/COVID analysis.

## Validation record

**267 tests passed**, including 16 genre rule/sampling/join tests. Pilot decision replay and the existing public-dataset validation passed. All 21,706 protected files retained their pre-experiment SHA-256 hashes, including 21,693 lyric files, research/lyrics/classifier databases, the immutable Billboard source and all existing public files. Snapshot checks confirm 28,041 IDs, 818 months and 81,797 observations, with the three accepted 99-row gaps unchanged.
The pilot CSV and numerical summary rebuilt byte-for-byte identically. No lyrics, caches, databases or model checkpoints are included in the commit.
