# Research findings

The best first expansion is a small historical-prefix feature layer over existing Billboard data, paired with local lyric-form measures. Prior artist-credit success and competition have stronger practical commercial rationale than another large set of emotion classifiers. For historical/cultural research, lyric structure, recording provenance, language, sound production and chart-methodology context add more distinct information. These are research judgments, not new empirical results.

The inventory contains **182 substantive candidates** across the requested domains, with **6 rejected/speculative ideas** retained separately. There are **59 Tier 1, 66 Tier 2, 57 Tier 3 and 6 Tier 4** rows. The source inventory contains **58 external families plus 4 existing-data families**. Documentation/live access is verified for **42 external families**; **11** are partially verified, **4** remain access/unverified, and **1** is confirmed withdrawn. Verification means only the stated scope. Population coverage is UNKNOWN unless tied to an explicitly audited existing denominator.

## Existing repository and data

The canonical checkout is `/Users/jamster187/Desktop/cmpt491-music-censorship`, on `main`. At research start, the working tree was clean and fetching origin showed no ahead/behind divergence; baseline commit was `2979f0d`. No old nested checkout or consolidation backup was used. Repository structure/commands, dataset definitions, acquisition modules and current findings were inspected first.

| Asset | Audited scope | Consequence |
|---|---|---|
| `data/public/songs.csv` | 28,041 exact study identities; 70 columns | Final monthly-selected population, not every weekly-chart identity |
| `data/public/master_weekly.csv.xz` | 355,487 source rows; 32,723 identities; 3,555 charts; 77 columns | Use the complete chart history for prior-credit events |
| `data/public/master_monthly.csv` | 81,797 rows; 818 selected snapshots; 78 columns | Snapshot dates/ranks are not release dates or monthly average ranks |
| Chart span | 1958-08-04 through 2026-09-19 | 1958 histories are left-censored; 2026 outcomes/current year are incomplete |
| Metadata | 22,290 high-confidence matches | Upper bound for some linkable metadata, not field-level completeness |
| Lyrics | 20,981 usable texts; text remained private | Upper bound for local language/structure features, not guaranteed parser coverage |
| Existing scores | 20,979 complete rows of 42 scores; 16-category genre layer | Additional synonyms for sentiment/toxicity/emotion are weak expansion choices |

The [existing-column inventory](existing_columns.csv) records the **80 unique column names** across the three actual headers. Existing fields already include duration median/minimum/maximum, matched-recording/release counts, earliest matched manifestation date and precision, primary/secondary genres, full-run chart summaries, acquisition flags and 42 classifier scores. Those are not counted again as proposed additions.

`mb_earliest_release_date` is not a verified original release date. Multiple accepted recording links may represent different versions. Structured artist credits, release country/status and release-group types can sometimes be recovered from already-retained payloads without new network acquisition. The small audit verifies their presence, not agreement across all links.

The research unit remains the exact original Billboard title plus full artist credit. A full credit is not necessarily a person or act. Every proposed `credit_*` history is explicitly credit-level; resolving individual collaborators later requires an approved reversible crosswalk. IDs remain deterministic and original strings unchanged. Source anomalies and repeated song/date pairs are preserved. Distinct-song counts and distinct-chart-date counts must be defined separately from source-row point totals.

Current repository findings reinforce the need for new information without promising a gain: the course-method Top-10 models report balanced accuracy near chance (0.5101 and 0.4791); previous regression exploration identifies many high-fit relationships as duplicate features or outcome reconstruction. These are existing results, not rerun experiments. See [course findings](../course_methods/findings.md) and [regression findings](../../docs/regression_search_results.md). No new statistical/COVID analysis was performed.

## What the source research establishes

| Domain | Most practical routes | Main constraint |
|---|---|---|
| Artist history/competition | Existing full weekly observations | Exact-credit fragmentation and strict cutoff rules |
| Lyric form | Existing private text; later CMU/local NLP | Missingness, transcription format, dialect and original version |
| Artist/release/credits | Retained MusicBrainz, then core MusicBrainz/Wikidata | Incomplete dated roles; work/recording/release distinctions |
| Collaboration networks | Dated open credits plus existing chart history | Sparse graph and entity resolution; whole-career edges leak |
| Audio | AcousticBrainz archive; expert annotation subsets; lawful local audio | Incomplete coverage, ceased submissions and original-master validation |
| Promotion/consumption | Licensed Luminate/Chartmetric/Soundcharts; limited open attention proxies | Cost, rights, modern-only history and endogeneity |
| Economic/social context | Government series and vintage releases | Publication lags, revised history and few independent time units |
| Industry context | Documented rule chronology and format mix | Fragmented announcements and restricted revenue database reuse |
| Unconventional variables | Titles, entry clusters, turnover, concentration, prior novelty | Hypotheses require later validation; no estimated predictive gain |

MusicBrainz offers reusable core data, but its supplemental tags have different terms; an artist tag is not a song genre. Discogs' core-data CC0 designation must be distinguished from API access conditions, images and marketplace data. Wikidata statements need references and time qualifiers for original labels/ownership. [MusicBrainz license](https://musicbrainz.org/doc/About/Data_License), [Discogs API terms](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use), [Wikidata access](https://www.wikidata.org/wiki/Help:Data_access).

AcousticBrainz stopped collecting submissions in 2022 but still served some sampled low-level records. Its CC0 features are not a guarantee of the correct charted performance. FMA/MTG-Jamendo are useful MIR resources with uncertain Billboard overlap, not substitutes for the target population. McGill and SALAMI offer open annotations for limited subsets. Essentia/librosa supply computation, not rights to music. Essentia documentation presents conflicting model-license summaries, requiring artifact-level resolution. [AcousticBrainz](https://acousticbrainz.org/), [Essentia licensing](https://essentia.upf.edu/licensing_information.html), [model catalog](https://essentia.upf.edu/models.html).

Spotify's restricted audio endpoints and 2026 development-mode field changes make an assumed new-app feature pipeline unreliable. Developer terms also restrict ML uses; a Kaggle uploader cannot grant upstream rights they do not possess. The two named Kaggle listings were located but their provenance/license chains were not verified. [Spotify changes](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api), [2026 migration](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide), [terms](https://developer.spotify.com/terms).

LFM-2b's official page now states that downloads were withdrawn for license issues. ListenBrainz is a different open source with a self-selected panel and imported-listen timing problems; it is not a replacement national streaming census. [LFM-2b status](https://www.cp.jku.at/datasets/LFM-2b/), [MetaBrainz dumps](https://metabrainz.org/datasets/postgres-dumps).

YouTube public counters are current cumulative values; historical owner Analytics requires authorization and API restrictions still apply. TikTok video creation timestamps do not turn current view counts into historical values. Google Trends' announced API alpha uses a rolling 1,800-day window, while website history is different; broad present access was not established. Shazam artist dashboards do not imply a public all-song history API. [YouTube policy](https://developers.google.com/youtube/terms/developer-policies), [TikTok Research API](https://developers.tiktok.com/docs/en/about-research-api), [Trends announcement](https://developers.google.com/search/blog/2025/07/trends-api), [Shazam support](https://artists.apple.com/support/1109-shazam-in-apple-music-for-artists).

Paid providers are plausible for a narrow modern-period study, not a 1958–2026 exposure backfill. Inspected advertised API entry prices were $350/month for Chartmetric and $50/month for Soundcharts; actual endpoint history, retention, exports and research rights require a current quote. Luminate has detailed modern histories and some older cumulative totals, but those totals do not establish old weekly series. No purchase or account contact was made. [Chartmetric plans](https://chartmetric.com/plans/api), [Soundcharts pricing](https://developers.soundcharts.com/pricing), [Luminate coverage](https://support.luminatedata.com/portal/en/kb/articles/methodology-faqs).

Government contextual series offer broad dates without song matching. Their values still require release-vintage joins for forecasting. ALFRED supports this distinction; latest FRED values do not automatically do so. Third-party FRED series can have additional rights restrictions. Historical context joins cannot explain causal mechanisms by themselves. [ALFRED documentation](https://fred.stlouisfed.org/docs/api/fred/alfred.html), [FRED terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html).

## Bounded feasibility evidence

The sample used two assets per period: 1958–1969, then each decade through 2010–2019, then 2020–2026. Within each period, one asset had final peak <=10 and one peak >40; selection was deterministic by lexicographic song ID among high-confidence metadata matches. **This is a diagnostic stratified sample conditioned on metadata success, not a random representative coverage survey.** Outcome strata were used only to test access across examples, not to train or evaluate a predictor.

For each of the 14 assets, one lexicographically selected accepted recording MBID was queried once at AcousticBrainz's low-level endpoint. Requests were sequential, paced at least 1.2 seconds apart, with a 12-second timeout and descriptive project User-Agent; errors were not retried. **Five returned HTTP 200 and nine HTTP 404.** Successful payloads exposed BPM, key/mode, average loudness and MFCC-related fields. No descriptor values, audio or lyrics were retained. See [probe log](feasibility_checks.csv).

The arbitrary accepted MBID is **not** a canonical recording selection. The successful examples were “No, No, No,” “I Want To Pay You Back,” “Dirty Laundry,” “Fire With Fire,” and “Love Lockdown.” A failed recording lookup does not prove the study song is absent; another version might exist. A successful lookup does not prove it is the originally charted version. High-level danceability/affect fields were documented but not live-probed. Consequently **5/14 is not an estimated population coverage rate** and has no extrapolated confidence interval.

A read-only inspection of stored metadata for the same 14 assets found structured recording credits, ISRC/date/length fields and release/release-group metadata in at least some variants. Accepted recording links ranged from one to dozens (up to 57 in this sample), making version ambiguity substantive. No metadata facts or feature values were exported, only already-public identities, link counts and field names. No private lyric content was read or sent to any service. See [metadata audit](local_metadata_audit.csv).

## Temporal leakage and study-design limits

1. **Choose the decision time before choosing predictors.** A debut model is evaluated after the debut chart is available; it cannot claim to forecast whether a song charts at all. Songs debuting in the Top 10 already have that outcome resolved. The future target, eligible cohort and prediction horizon must be specified later. No horizon is selected here.
2. **Use prefixes, not completed careers.** Count earlier Top-10 achievements only if they had happened before the target cutoff. Earlier songs still running contribute only observations already seen. Final prior-song longevity is future information too. Do not use final chart points, peak or last date for the focal song as predictors.
3. **Preserve the chart population distinction.** The 28,041 month-end-selected study assets are not all weekly entrants. Selection can depend on future chart survival. Build chart-history inputs from all 32,723 weekly identities, retain cohort-selection flags, and make no all-release hit-probability claim.
4. **Separate intrinsic content from measurement time.** Lyrics/audio may have existed at release, but today's retrieved version, remaster, dictionary, topic model or embedding remains F unless a version and availability audit justifies a different use. Retrospective content association is legitimate when labelled as such; it is not demonstrated historical deployment.
5. **Treat D as nowcasting.** Early ranks, four-week accumulated points and contemporary streams can be useful only at a fixed landmark. Predict remaining performance or explicitly account for the already-observed part. Contemporaneous chart components may mathematically reconstruct a ranking rather than provide an independent discovery.
6. **Archive timestamps matter.** Current followers, views, streams, tags and playlist placement do not predict original performance. A dated listen imported years later was not available at its event date. Event time, ingestion time, publication time and retrieval time are distinct.
7. **Control reference fitting.** Genre prevalence, vocabulary, topic mixtures, scaling, embeddings adapted to this corpus and network edges must not use future evaluation songs. Artist-disjoint sensitivity checks address repeated-artist dependence; a chronological split answers a different question from an artist-disjoint split.
8. **Respect time-series units.** Monthly/annual context repeated across thousands of rows does not create thousands of independent exposures. Trend, serial dependence, repeated songs and era-dependent missingness require later methodological decisions. Associations with elections, wars or policy are not causal estimates.
9. **Retain censoring and measurement changes.** Career history before August 1958 is unavailable here, and future success after September 2026 is unobserved. Recurrent holiday songs complicate run endpoints. Chart rule changes must be sourced independently; no rule chronology or COVID breakpoint is inferred from fitted outcomes.

All future feature tables should carry a sidecar provenance record: source/entity IDs, exact mapping decision/version, reference period, measurement/observation time, ingestion/publication time where available, retrieval time, source/model/pipeline version, license identifier, uncertainty/missingness reason and original-recording evidence. These are required audit fields, not padded candidate discoveries.

## Coverage gaps and uncertainty

No source establishes uniform 1958–2026 song-level radio, sales, streaming, promotion spending, social following or playlist history. Older credits and versions are incomplete; recent platform data are richer but less comparable. No lawfully acquired, correctly versioned full-waveform collection has been established. No validated historical slang lexicon was found. Global platform users, US chart consumers and survey respondents are different populations. Missingness can depend on fame, decade, genre, language and survival.

The research is broad but not proof that every possible source has been found. Several terms pages were blocked or dynamic, exact provider contracts remain UNKNOWN, and a source may change after this date. [Rejected/deferred routes](rejected_sources.md) and [search log](search_log.csv) preserve those limits. Further acquisition, feature engineering, training and new statistical analyses remain outside the completed research scope.
