# Rejected, deferred and unresolved routes

These decisions apply to the proposed use, not to every possible use of a provider. See the matching `source_id` in [source_inventory.csv](source_inventory.csv) for primary URLs and exact verification scope. UNKNOWN is retained rather than replaced with assumed access, coverage or permission.

| Route | Decision | Evidence / reason | What could change the decision |
|---|---|---|---|
| S16 LFM-2b | Reject current acquisition | [Provider](https://www.cp.jku.at/datasets/LFM-2b/) explicitly says downloads withdrawn for license issues | New official licensed release |
| S09 Spotify new-app audio features | Reject assumed pipeline | [2024 API change](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api), 2026 access/field changes and [ML restrictions](https://developer.spotify.com/terms) | Explicit compatible entitlement and research permission; no workaround scraping |
| S09 current popularity/followers as historical predictors | Reject forecast use | Present counters include later success and may be inaccessible in development mode | Genuine permitted archived pre-cutoff observations |
| S10/S11 named Kaggle Spotify collections | Reject as ready sources | Pages located, but schema, collection timestamps and upstream license chain unverified | Original collection provenance and permissions independently established |
| S26 WhoSampled | Reject automated extraction | No open research API/rights verified; terms page blocked | Explicit licensed export/API and reliable recording/work links |
| S56 Songview/BMI/ASCAP | Reject scraping | [BMI terms](https://www.bmi.com/legal/terms-and-conditions-of-use) do not provide an open bulk research grant | Written compatible data agreement; meanwhile prefer open work credits |
| S49 LRCLIB/new lyrics | Reject this campaign | New lyric acquisition is outside scope; lyrics rights unresolved | Separate approval and compatible text rights |
| S53 setlist.fm permanent research archive | Reject proposed persistent archive | [Terms](https://www.setlist.fm/help/terms) impose noncommercial/caching restrictions; access is not a permanent-data license | Explicit retention/research permission or another lawful archive |
| Song-level advertising/promotion budgets | Unverified/speculative | No inspected public provider establishes consistent historical song-level spend | Dated label/agency ledger access; do not estimate from success |
| Historical slang prevalence | Unverified construct | Modern OOV, profanity and book frequency are not validated slang labels | Licensed era/dialect lexicon and human validation |
| Listener-country concentration from ListenBrainz | Unverified field | Inspected public listen documentation did not establish required country coverage | Verified permitted aggregate geography source |
| S17 YouTube historical public counts | Defer/reject assumed history | Public video stats are current; owner Analytics differs; [policy](https://developers.google.com/youtube/terms/developer-policies) restricts retention/derived uses | Authorized owner reports and explicitly compatible research use |
| S19 TikTok timestamped videos | Defer restricted modern subset | Video creation date does not date current counters; approved research access required | Approved scope and valid counter vintages |
| S20 Shazam/Apple all-song history | Defer | Artist-team dashboards are not a public universal history API | Rights-owner participation or compatible provider license |
| S18 Google Trends general API access | Defer | Official [alpha announcement](https://developers.google.com/search/blog/2025/07/trends-api) is not proof of our entitlement; API/website windows differ | Approved access and stable normalization design |
| S15 Last.fm | Defer | [Terms](https://www.last.fm/api/tos) require appropriate academic/commercial arrangements; current totals are retrospective | Permission, retention terms and actual historical timestamps |
| S21/S22/S23/S24 paid providers | Defer | Useful documented products; exact song/date coverage and contracts UNKNOWN | Approved narrow scope, quote and storage/redistribution terms |
| S12 Discogs | Defer API route, not all core facts | Core CC0 versus API conditions must be distinguished; developer/dump pages blocked | Verified endpoint access and applicable use conditions |
| S25 SecondHandSongs | Defer | Beta API documented; full terms/license not verified | Explicit compatible terms and exact performance mapping |
| S03 Essentia pretrained models | Defer artifact selection | Licensing page and model catalog give differing summaries | Pin artifact license, intended use and lawful audio source |
| S05 MSD | Defer broad merge | Static snapshot; license endpoint not fully inspected; audio not supplied | Per-component rights and exact recording crosswalk |
| S06/S07 FMA/MTG-Jamendo | Keep as method resources | Independent/open-music selection; Billboard overlap UNKNOWN | Measured valid overlap; do not claim catalog size as coverage |
| S08 Music4All | Defer | Request-based bundled data; platform/audio/lyrics rights unresolved | Authorized access and component-specific licensing |
| S50 Lakh MIDI | Defer to validation | Transcriptions and probabilistic MSD links can mismatch versions; underlying rights uncertain | Verified exact-work/performance relationships and rights |
| S38 RIAA | Defer redistribution | Public viewing is not a reuse grant; format/basis changes | Permission and consistent revenue-basis crosswalk |
| S44/S45 GSS/Pew | Defer selected fields pending review | Public-use access verified, exact reuse and item comparability unresolved | Selected dataset terms, weights and consistent questions |
| S48 archival scans | Manual evidence only initially | Item-specific rights; capture date differs from publication date | Permitted item scope and verified dated facts |

## Ideas investigated but not counted as new discoveries

- **Duration:** median, minimum, maximum and duration-variant counts already exist. A validated original-version duration might improve provenance, but another generic duration column adds no new construct.
- **Raw type-token ratio and many readability formulas:** raw TTR is determined by token/type counts and strongly length-dependent. MATTR represents the preferred separate diversity construct. One readability index is enough to investigate feasibility; a dozen formulas would pad the list.
- **More synonymous emotions/sentiment/toxicity scores:** the current 42 outputs already cover these broadly. Valence in lyrics overlaps sentiment. Audio affect is a distinct modality. Religious/economic references and stress are retained only as targeted future constructs with redundancy checks.
- **Relationship/breakup/social-identity topic labels:** plausible, but overlap existing love/grief/sadness/identity-attack outputs and require a validated codebook. The topic-mixture candidate covers open thematic structure without inventing a ready classifier for every label. No classifier was created.
- **Instrumentalness versus vocal activity:** largely complementary under a given definition; one vocal-activity construct is counted. Silence, speech-versus-singing and instrument families address different questions.
- **Current artist genre, present-day label parent and lifetime chart success:** do not represent original song genre, historical label ownership or prior success. Artist tags remain entity-level evidence.
- **ISRC, MBID, provider IDs, hashes, retrieval timestamps, confidence and missingness flags:** essential provenance/controls, not padded substantive feature counts. An ISRC's embedded year is not proof of original release.
- **Every embedding/MFCC/topic dimension as a “new column”:** one vector is one candidate construct. Exact export schemas are deliberately undecided.
- **Final peak, longevity, total points and future chart re-entry:** already existing outcomes or future information; not new forecasting predictors. Prior-only history and fixed-landmark nowcasting are separately defined.
- **Chart points as revenue or streams:** 101 minus rank is an ordinal-derived score, not a measured commercial quantity.
- **Artist influence:** performer collaboration, listener homophily and musical similarity are different mechanisms; none establishes a causal influence network. A18 concerns listener ties, not artist inspiration. No broad dated influence ground truth was established.
- **Distributor and international rollout:** release-country sets and labels do not establish original distributors or territory launch sequences. Those require dated company-role/release evidence; no ready broad field was verified.
- **All-release hit prediction:** our population contains charting songs. Without a separately authorized non-charted release population, this target cannot be claimed.

## Unresolved claims retained explicitly

Exact song-level coverage is UNKNOWN for every external source. Official documentation supports field existence or product claims, not our exact-identity join. Fixed rate limits remain UNKNOWN when not established by current provider documentation. Blocked pages were not bypassed. No API key, account approval, license negotiation, paid trial or bulk download was obtained. Primary source URLs, inspection dates and partial-verification flags make these uncertainties reviewable instead of hiding them behind headline catalog counts.
