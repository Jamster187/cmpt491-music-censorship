# CMPT 491: canonical project handoff

Reconciled on **2026-10-28** in `/Users/jamster187/Desktop/cmpt491-music-censorship`, on `main`, for [Jamster187/cmpt491-music-censorship](https://github.com/Jamster187/cmpt491-music-censorship). This document consolidates existing releases and findings. It does not authorize acquisition, feature changes, a new COVID breakpoint, or music–economy modelling.

## Repository and workstream status

The verified data/code HEAD before this documentation commit is **`988aea1e804606f26d677a309d3bd372278bd4b9`**; `origin/main` matched it after a normal fetch, with zero divergence. Both requested commits are ancestors of this HEAD:

| Workstream | Commit | Verified state |
| --- | --- | --- |
| Financial indicator discovery | `fb3fc0d5519c3cf78574c35f7dd32ec829f7d660` | Complete and pushed; 17 publication files and nine protected baselines verify |
| Music enrichment and external history | `ab1c96ff232310bd68adfe22b6911dcdaba27e13` | Complete and pushed; additive public data, local evidence and prior outputs preserved |
| Financial/macroeconomic acquisition v1 | `988aea1e804606f26d677a309d3bd372278bd4b9` | Complete and pushed; 48 manifest-listed publication files, 32 source snapshots and offline tables verify |
| This consolidation | `git log -1 -- docs/PROJECT_STATE_HANDOFF.md` | Documentation-only milestone following the three releases |

The acquisition work was inspected before publication: its processes had finished and its 49 staged files belonged to this session's already authorized financial release. That release was committed separately and pushed normally. No new acquisition was launched during consolidation. The other enrichment session's release was already committed. At the handoff audit there were no tracked changes, nonignored untracked files, local-only commits, or visible acquisition/model/Git mutation processes. Only this handoff is added by consolidation.

There are two registered Git worktrees. The canonical workspace above is the only working repository for this task. The pre-existing detached validation checkout at `data/experiments/financial_acquisition_validation`, based on `fb3fc0d`, contains the financial release used for isolated verification. Its local files are preserved; it is not an alternative source of truth. No other clone was created, no consolidation backup was changed, and no reset, cleanup, destructive checkout or force-push was used.

Existing README/navigation files are dependencies of frozen publication hashes. This new document links the completed releases without changing those canonical bytes. Start with [repository structure](repository_structure.md), [commands](commands.md), and [additive enrichment instructions](music_enrichment_v2.md).

## Completed work and where to find it

| Completed component | Canonical entry point | Scope and interpretation |
| --- | --- | --- |
| Billboard construction and final dataset | [Public data guide](../data/public/README.md) | 3,555 charts, 355,487 source observations and 32,723 exact title/artist identities in the immutable foundation; 28,041 identities in the monthly study population |
| Metadata, lyrics, genre and classifiers | [Final public schema](../data/public/README.md), [genre audit](../reports/genre_final_audit.md) | Original strings, mapping dispositions, 16 genres and 42 separate continuous scores retained; lyric text remains private |
| Descriptive statistics | [Milestone 2](../analysis/milestone2/README.md) | Existing numerical summaries, coverage and figures |
| Historical moving averages | [Moving averages](../analysis/moving_averages/README.md) | Existing overall/genre trajectories and all-genres presentation figures |
| Original exhaustive OLS | [Regression search](../analysis/regression_search/README.md), [meaningful-result view](../analysis/regression_search/meaningful/README.md) | 59 targets, 1,998,901 combinations, 5,996,703 validation fits; complete hierarchies remain local |
| Relationship discovery | [Full Phase 1](../analysis/relationship_discovery/full_phase1/README.md) | 9,159 pairwise, nonlinear and genre-interaction candidates; exploratory results and retained nulls |
| Classification, patterns and clustering | [Course methods](../analysis/course_methods/README.md) | Chronological classification, association rules, 99 cluster configurations and 198 resample comparisons |
| Historical genre decomposition | [Findings](../analysis/historical_decomposition/findings.md) | 882 accounting comparisons, dependence/missingness sensitivities and fixed historical/2020 comparisons |
| Feature expansion v1 | [Feature expansion](../analysis/feature_expansion_v1/README.md) | 57 engineered constructs, point-in-time chart features, bounded predictive evaluation and portable models |
| Expanded OLS v2 | [V2 findings](../analysis/regression_expanded_v2/findings.md) | 1,311,090 task/candidate pairs, 5,244,360 fits; strict and retrospective tracks separated |
| Cross-domain OLS v3 | [V3 findings](../analysis/regression_cross_domain_v3/findings.md) | 40,884,781 valid target/combination pairs, 123 targets, 129 predictor constructs, 163,539,124 fits |
| Music enrichment v2 | [Enrichment report](../analysis/music_enrichment_v2/README.md) | 182 credible candidates among 188 audit rows; 91 new construct groups plus 57 prior groups = 148 engineered constructs; the original 42 scores are separate |
| External historical platform | [Historical platform](../analysis/external_historical/README.md) | 101 source + 36 derived series; natural-frequency and narrowly eligible publication-time joins |
| Financial indicator research | [Research catalog](../analysis/external_historical/financial_research/README.md) | 325 candidate inputs, 289 overlap groups, 60 non-alias derived families; research inventory, not 325 acquired series |
| Financial acquisition v1 | [Financial release](../analysis/external_historical/financial_acquisition/README.md) | 70 native series, a monthly panel, source/coverage audits and a sample music join; no cross-domain fit |

The financial catalog contains **81 source records**: 80 documented source-evidence records and one unverified archival lead. Its 61 derived-definition rows represent 60 non-alias families. The 274 potential no-fee routes and 82 reported starts by 1958 are research leads, not claims of fully audited 1958–2026 coverage. The catalog's earlier snapshot of 89 local series is historical evidence, superseded for current platform counts by the 137-series release.

## Current datasets

Sizes below are measured on disk, in MiB (1,048,576 bytes); CSV/XZ sizes are compressed sizes. Columns include identifiers, counts and provenance, so they are not counts of independent predictors. Paths are relative to the canonical repository.

Table labels use these roots: `public/` = `data/public/`; `music-v2/` = `data/public/music_enrichment_v2/`; `history-public/` = `data/public/external_historical_v1/`; `history-local/` = `data/external_historical/`; `finance/` = `data/external_historical/financial/processed/acquisition_v1/`. Local-only rows are intentionally not download links.

| Dataset | Rows | Columns | MiB | Access |
| --- | ---: | ---: | ---: | --- |
| [public/songs.csv](../data/public/songs.csv) | 28,041 | 70 | 24.885 | Public |
| [public/master_monthly.csv](../data/public/master_monthly.csv) | 81,797 | 78 | 78.333 | Public |
| [public/master_weekly.csv.xz](../data/public/master_weekly.csv.xz) | 355,487 | 77 | 14.422 | Public |
| [public/feature_expansion_v1/song_features.csv.xz](../data/public/feature_expansion_v1/song_features.csv.xz) | 32,723 | 107 | 10.757 | Public |
| [music-v2/chart_period_features.csv.xz](../data/public/music_enrichment_v2/chart_period_features.csv.xz) | 355,487 | 8 | 3.279 | Public |
| [music-v2/monthly_by_genre.csv.xz](../data/public/music_enrichment_v2/monthly_by_genre.csv.xz) | 7,173 | 346 | 3.968 | Public |
| [music-v2/monthly_overall.csv.xz](../data/public/music_enrichment_v2/monthly_overall.csv.xz) | 818 | 345 | 0.860 | Public |
| [music-v2/song_missingness.csv.xz](../data/public/music_enrichment_v2/song_missingness.csv.xz) | 28,041 | 182 | 0.981 | Public |
| [music-v2/songs.csv.xz](../data/public/music_enrichment_v2/songs.csv.xz) | 28,041 | 311 | 21.931 | Public |
| [history-public/asof_monthly_releases.csv.xz](../data/public/external_historical_v1/asof_monthly_releases.csv.xz) | 6,544 | 13 | 0.017 | Public |
| [history-public/chart_context_keys.csv.xz](../data/public/external_historical_v1/chart_context_keys.csv.xz) | 355,487 | 7 | 2.076 | Public |
| [history-public/month_genre.csv.xz](../data/public/external_historical_v1/month_genre.csv.xz) | 7,173 | 175 | 2.013 | Public |
| [history-public/month_overall.csv.xz](../data/public/external_historical_v1/month_overall.csv.xz) | 818 | 174 | 0.419 | Public |
| [history-public/observations.csv.xz](../data/public/external_historical_v1/observations.csv.xz) | 56,469 | 24 | 0.409 | Public |
| [history-public/quarter_genre.csv.xz](../data/public/external_historical_v1/quarter_genre.csv.xz) | 2,676 | 99 | 0.774 | Public |
| [history-public/quarter_overall.csv.xz](../data/public/external_historical_v1/quarter_overall.csv.xz) | 273 | 98 | 0.090 | Public |
| [history-public/release_context_keys.csv.xz](../data/public/external_historical_v1/release_context_keys.csv.xz) | 28,041 | 9 | 1.016 | Public |
| [history-public/year_genre.csv.xz](../data/public/external_historical_v1/year_genre.csv.xz) | 812 | 118 | 0.259 | Public |
| [history-public/year_overall.csv.xz](../data/public/external_historical_v1/year_overall.csv.xz) | 69 | 117 | 0.027 | Public |
| `finance/aggregation_metadata_local.csv.xz` | 37,891 | 14 | 0.047 | Local only |
| [finance/aggregation_metadata_public.csv.xz](../data/external_historical/financial/processed/acquisition_v1/aggregation_metadata_public.csv.xz) | 29,949 | 14 | 0.036 | Public |
| `finance/missingness_local.csv.xz` | 825 | 103 | 0.002 | Local only |
| [finance/missingness_public.csv.xz](../data/external_historical/financial/processed/acquisition_v1/missingness_public.csv.xz) | 825 | 70 | 0.002 | Public |
| `finance/monthly_local.csv.xz` | 825 | 103 | 0.345 | Local only |
| [finance/monthly_public.csv.xz](../data/external_historical/financial/processed/acquisition_v1/monthly_public.csv.xz) | 825 | 70 | 0.227 | Public |
| [finance/music_join_sample.csv](../data/external_historical/financial/processed/acquisition_v1/music_join_sample.csv) | 54 | 15 | 0.009 | Public |
| `finance/native_local.csv.xz` | 176,476 | 14 | 1.039 | Local only |
| [finance/native_public.csv.xz](../data/external_historical/financial/processed/acquisition_v1/native_public.csv.xz) | 39,426 | 14 | 0.254 | Public |
| `finance/point_in_time_local.csv.xz` | 784 | 13 | 0.006 | Local only |
| [finance/point_in_time_public.csv.xz](../data/external_historical/financial/processed/acquisition_v1/point_in_time_public.csv.xz) | 228 | 13 | 0.004 | Public |
| `finance/quarterly_alignment_local.csv.xz` | 8,250 | 13 | 0.046 | Local only |
| [finance/quarterly_alignment_public.csv.xz](../data/external_historical/financial/processed/acquisition_v1/quarterly_alignment_public.csv.xz) | 7,425 | 13 | 0.040 | Public |
| `history-local/derived/all_observations.csv.xz` | 184,845 | 24 | 1.155 | Local only |
| `history-local/joins/month_overall.csv.xz` | 818 | 197 | 0.491 | Local only |
| `history-local/joins/month_genre.csv.xz` | 7,173 | 198 | 2.095 | Local only |
| `history-local/joins/asof_monthly_releases.csv.xz` | 7,362 | 13 | 0.022 | Local only |

The immutable `data/processed/music.db` is 94.715 MiB; `data/raw/billboard-hot-100.json` is its unchanged source. Database table counts are described above; the CSV table lists exported row/column dimensions.

The original weekly release includes all 32,723 foundation identities. Its 4,682 identities outside the final monthly population are retained with explicit scope/missingness flags; they must not be silently treated as newly enriched songs. Monthly coverage is **1958-08 through 2026-09: 818 months**, ending at the available chart of **2026-09-19**. The financial calendar starts in January 1958 and therefore has **825 rows**, including seven months before the music study starts.

Music v2 preserves all **70 original song fields** exactly, adds **60 reused v1 columns** and **181 new columns**, and supplies a missingness sidecar for every new field. The 149 new fields classified as analytical columns are grouped into constructs; vectors, related probabilities and components are not independent discoveries. Linguistic/semantic features cover **20,981 songs (74.82%)**; **22,290** have reused accepted metadata, **1,048** have newly accepted MusicBrainz matches, and **1,405 (5.01%)** have audio features passing the exact-recording/artist/duration gate. These metadata counts overlap and must not be added. Dense 384-dimensional vectors stay local. The [feature dictionary](../analysis/music_enrichment_v2/feature_dictionary.csv), [construct inventory](../analysis/music_enrichment_v2/construct_inventory.csv), [coverage](../analysis/music_enrichment_v2/coverage_report.csv) and [provenance](../analysis/music_enrichment_v2/provenance.md) define the measurements.

The historical platform contains **184,845 native/derived observations across 137 series**, with nonmissing values spanning **1919 through October 2026** across different sources. Sixteen blank G.17 source placeholders extend date labels through December 2026; they are preserved missing entries, not future measurements. Source frequencies are 66 monthly, four quarterly, 22 annual and nine daily series. The releasable subset is **56,469 observations across 108 series**. Public overall monthly joins contain 79 external series; the full local version contains 102. These broad source dates do not extend music coverage beyond September 2026 or guarantee continuous series coverage. Full local monthly availability includes 818 market-return months, 817 unemployment months and 585 Michigan sentiment months.

Financial v1 separately contains **176,476 native rows**: 176,169 valid values and 307 explicit source missing values. Its full monthly panel has **55 native/aggregated inputs + 47 derived columns = 102 numerical columns**; its public panel has **69 numerical columns**, sourced from 53 public native series. Ten quarterly series are preserved separately. Only 29 monthly columns meet the strict full-panel completeness check; the other 73 have gaps, shorter histories or unresolved daily-calendar completeness. Missing cells are 13.29% locally and 15.77% publicly. The [coverage report](../analysis/external_historical/financial_acquisition/coverage_report.csv), [missing intervals](../analysis/external_historical/financial_acquisition/missingness_report.csv), [source dictionary](../analysis/external_historical/financial_acquisition/series_dictionary.csv) and [derived dictionary](../analysis/external_historical/financial_acquisition/derived_feature_dictionary.csv) govern interpretation.

### Provenance and redistribution

Billboard is the chart-history authority; the local snapshot is **reported** as coming from [mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100). This attribution is not independent verification of the upstream archive. Exact original title and artist credit define each asset. Artist credits can describe collaborations; they are not resolved individual performers. `data/raw/` and `data/processed/music.db` remain immutable.

Public music enrichment exports factual MusicBrainz core metadata and qualified AcousticBrainz features with their documented CC0 source terms, plus derived numerical diagnostics. It does not distribute lyrics, dense embeddings or audio recordings. Billboard and lyric rights are not replaced by a blanket repository license. Modern language models, current lyric versions and retrospective catalog metadata do not become historically available features merely because chart-date ordering was enforced.

The historical exports include only rows explicitly cleared for redistribution, retaining source-specific attribution/terms for government statistics, World Bank, UCDP, Oxford and other documented sources. French market factors, Michigan survey values and NBER values stay local in the platform. Financial v1 also keeps NFCI, SF news sentiment, archived proprietary corporate-yield values and dependent restricted transforms local. Its market-drawdown figure remains local; four other financial SVGs are public. Consult each release's rights fields, [source manifest](../data/external_historical/manifests/source_manifest.json), [financial source manifest](../data/external_historical/financial/manifests/acquisition_v1/sources.json) and [blocked/deferred routes](../analysis/external_historical/financial_acquisition/blocked_sources.md). A publicly reachable download is not a redistribution grant.

## Integration rules verified during handoff

1. **Identity and denominator preservation.** Original song strings, IDs, genres and 42 classifier fields match the frozen release. Weekly source coordinates and all 355,487 rows survive. Monthly views retain all 81,797 source rows and separately report distinct songs and score-specific available counts. Three repeated song/month pairs are source observations, not accidental join multiplication. No external join increases its music analytical-unit count; economic observations have unique declared keys.
2. **Weighting differences remain explicit.** Descriptive/enrichment/external-platform/financial sample views retain the 81,797 source rows. Moving averages use 81,794 distinct song-months. Historical decomposition also uses distinct song-months, restricted to 1960–2025 (79,194 rows). Their means answer different questions; do not force equality by rewriting one pipeline. Repeated songs across months and shared artist credits remain dependent observations.
3. **Frequency is preserved.** Monthly economic values join on calendar month; quarterly and annual variables stay in natural-frequency views. Daily/weekly aggregation retains observation counts and source-completeness qualifications. Financial v1's separate quarter-alignment views are retrospective reference-period conveniences, not proof of publication availability. No quarterly/annual rows are interpolated into the main monthly platforms.
4. **Observation dates differ from availability dates.** Most panels contain latest/revised snapshots. A full calendar-month return can include dates after that month's Billboard snapshot. The historical platform admits only nine documented release-vintage/event series to its local as-of view: eight G.17 growth series and one NBER announcement series, giving 1,468 nonmissing values over 556 music months. Publication must be strictly before the chart cutoff day; same-day releases are excluded. Financial v1 uses a different month-end cutoff and only two G.17 growth series plus the NBER event view. These are not interchangeable forecasting panels. G.17 vintage coverage starts in 2017; an NBER announcement event is not current recession membership.
5. **Release-date uncertainty is retained.** There are 5,738 month/day-precision release candidates usable only for retrospective candidate-month context; none is verified as the original Billboard edition. Another 14,754 have year precision only, 5,947 are missing, and 1,602 candidates occur after chart debut and are excluded. No invented month is assigned to year-only dates. Chart dates are never substituted for release dates.
6. **The two external releases overlap.** The 137 platform series and 70 financial native series are not 207 distinct economic constructs. A read-only comparison of 43 identically named native series found agreement within floating-point tolerance across 135,781 common nonmissing observations. This checks overlapping values, not equivalence of every series or derived definition. Preserve each namespace, source identifier, units, frequency and formula before choosing a future analysis crosswalk. In particular, `US_EQUITY_*` platform transforms and `US_MARKET_*` financial transforms need definition-level review. The platform's realized measure is `100 × sqrt(sum(log(1+r)^2))` within each month, without annualization; financial v1 uses `100 × sqrt(252 × mean(r^2))`, with simple daily decimal returns `r`. Each downside variant clips its respective daily return at zero before squaring. These differ in return definition and scaling. The financial BLS warm-up starts in 1956 and can produce earlier growth values than the platform's 1958 inputs. `US_IP_MANUFACTURING` denotes G.17 B00004 SIC manufacturing; it must not be silently relabelled as the NAICS FRED IPMAN series.
7. **Missingness and endpoint limits remain visible.** No source gaps are repaired by interpolation. BLS October 2025 missing values survive. Monthly Michigan history starts in 1978; earlier quarterly observations stay quarterly. Archived Aaa/Baa history ends in September 2016; no restricted modern continuation is spliced in. The acquired broad-market French return is not a literal S&P 500 series. NBER closed-cycle membership is right-censored after the last dated trough, rather than filled with assumed zeros.

The historical manifest field `source_observations_and_derived_features_independent` describes separation of storage layers. It is **not a statement of statistical independence**. Source overlap, shared formulas and economic common causes remain material.

## Research findings that can be carried forward

**The strongest historical result concerns long-run observed classifier changes.** Comparing the 1990s with 2015–2024 under symmetric genre accounting, the within-genre component accounts for 83.4% of toxicity change, 77.6% of explicit-language change and 66.3% of substance-use change. Both total change and within contribution for these three dimensions pass the declared global BY correction (q≈0.0301). Sexual content and violence have positive marginal change intervals but do not pass that global correction. These are results for observed classifier scores, not calibrated human-content prevalence or causal genre effects. The preliminary report's five older percentages remain unreproduced because their original specification/code was unavailable. Weighting and missing-data assumptions materially change the shares. See [historical findings and sensitivities](../analysis/historical_decomposition/findings.md).

**A distinctive genre-independent COVID disruption has not been established.** None of the 22 January-2020 score/model combinations has a primary break term passing global BY; none of the 484 primary breakpoint terms passes. Concurrent events, trend shape, coverage and the short post-2020 interval limit interpretation. This is not proof that no pandemic-associated change occurred, and it does not authorize choosing a new breakpoint during engineering maintenance.

**Song-level prediction often generalizes weakly.** In the course-method campaign's 2018–2025 period, tree/Bayes balanced accuracy is 0.510/0.479 for Top 10 and 0.485/0.445 for longevity, against 0.500 baselines. Broad genre classification is somewhat informative but limited (balanced accuracy 0.262/0.242; macro F1 0.228/0.214). Stable K-means profiles have weak separation: K=3 resample ARI 0.958 versus test silhouette 0.137; family balancing selects K=2. These are exploratory score profiles, not a unique natural taxonomy. See [course findings](../analysis/course_methods/findings.md).

**Expanded information helps selected outcomes, without establishing a general hit predictor.** V1 improves strict Top-10 balanced accuracy from 0.549 to 0.666 and AUC from 0.618 to 0.724, but precision is 4.81% at 79.3% recall in a 2.85%-prevalence evaluation cohort. Its Brier score is worse than the baseline. V2's validation-selected strict 26-week best-rank model has evaluation R² 0.305; weeks and points have R² −0.511 and −0.621. The best-rank incremental R² gain over the original-only model is 0.011, with exact-credit interval [−0.006, 0.030]. In V3, 34/123 selected primary models have positive R² across every validation and evaluation period, but these are exploratory stability counts, not corrected discoveries. Near-perfect unrestricted debut-rank models largely recover a near-copy source field. The [V1](../analysis/feature_expansion_v1/findings.md), [V2](../analysis/regression_expanded_v2/findings.md) and [V3](../analysis/regression_cross_domain_v3/findings.md) reports retain failures, cohort definitions and comparison limits.

**External comparisons are technically available; relationships have not been established.** Market returns/drawdowns, labor/inflation, financial stress, consumer sentiment and political/social context can be joined at their documented frequencies. The releases performed data engineering and join validation, not music–economy hypothesis tests. The newly enriched music/audio fields were not evaluated by the earlier V3 campaign. Historical evaluation periods have already been inspected repeatedly and are not a fresh holdout for future claims.

## Limitations and local preservation

There are **7,060 study songs without usable lyric/classifier data** and two additional songs missing four LyricLens scores; 20,979 have all 42 scores. Missingness varies by decade and genre. Audio coverage is sparse and strongly uneven; a passed recording gate still does not verify the original release edition. Metadata is incomplete and selected toward matchable assets. English parsing, modern lexical resources and modern semantic models introduce language/time-domain limitations. Genre labels and classifier scores are model measurements with uncertainty, not ground truth.

Future inference must address temporal autocorrelation, shared artist/song dependence, nonstationary trends, changing chart/genre composition, changing coverage, multiple comparisons and previously inspected periods. Revised economic measurements and unknown publication vintages limit historical forecasting claims. Seasonal adjustments, definitional changes and benchmark substitutions must retain their source flags.

The following valuable local directories remain ignored and untouched. Sizes are approximate and overlap where one directory contains another; they are not additive backup requirements.

| Local location | Approximate size | Preserved contents |
| --- | --- | --- |
| `data/lyrics/` | 86 MiB | Private acquired lyric text and provider/mapping evidence |
| `data/cache/` | 11 GiB | MusicBrainz/audio/provider caches, model assets and retained responses |
| `data/processed/` | 5.3 GiB | Immutable Phase 1 database, working research/acquisition stores and linked evidence |
| `data/experiments/` | 22 GiB | Full regression hierarchies, fitted models, checkpoints, enrichment features/vectors, preservation baselines and campaign environments |
| `data/external_historical/` | 65 MiB | Original historical/financial responses, restricted observations, local joins and finance v1 raw/processed snapshots |
| `.venv/`, `.venv-regression-demo/` | 602 / 690 MiB | Existing pipeline/demo environments; additional campaign environments are under experiments |

No private lyric text, raw restricted economic values, credentials, acquisition databases, dense vectors, fitted-model caches or environments are added to Git by this handoff. The local acquisition checkpoints remain restartable but inactive; MusicBrainz's bounded campaign ended with unresolved provider requests after repeated errors, rather than silently accepting matches. Financial v1 has no unresolved normalization/download failures among its 32 retained snapshots; deferred sources and rights issues remain documented.

The filesystem had approximately **14 GiB free (97% used)** at inspection. A second local copy of the 38.2 GB preservation baseline would not fit. No new backup was attempted and no local artifacts were deleted. Off-device backup coverage was not verified; Git alone does not preserve these ignored assets. Any later backup needs sufficient storage, verified copies and appropriate handling of restricted data. Existing backups and the noncanonical Desktop project copy were not modified.

## Validation and reproduction

Current consolidation checks completed successfully on the integrated `988aea1` data/code state:

| Check | Result |
| --- | --- |
| Full unittest suite | **576 tests ran: 560 passed, 16 skipped**, 84.275 seconds; no failures |
| Complete pre-enrichment preservation baseline | **248,030 files / 38,203,701,082 bytes unchanged**, including prior databases, regressions, models, checkpoints and analytical outputs |
| Original foundation and final exports | Phase 1 validates 3,555 charts / 355,487 rows / 32,723 identities; final exporter independently reconstructs and compares the current release offline |
| Enrichment and history | All 28,041 identities, 70 original fields, 181 new-field missingness indicators and 355,487 chart rows verify; public/private source and temporal gates pass |
| Monthly enrichment replay | Both 818-row overall and 7,173-row genre tables reproduce **byte for byte** in temporary storage |
| Historical join replay | All **12** full/permitted monthly, quarterly and annual overall/genre joins reproduce in memory; strict publication gates replay 1,468 eligible local values |
| Additional provenance | 32 music and 14 historical report artifacts, nine declared data-input hashes, ten pinned NLP assets and all **82** historical source/provenance records verify; the 41 raw files supplying observation values also pass the dedicated private validator |
| Financial release | 48 publication files and 1,731 protected files verify; all 32 source snapshots match; all **16** local/public tables reconstruct offline |
| Earlier regression publications | V2's **99** and V3's **84** manifest-listed files match; broader preservation also covers the original OLS, meaningful results, discovery and v1 artifacts |
| Course saved-output replay | 28,152 itemset rows, 62,784 rule/split metrics, 133,725 classifier checks, 185,355 cluster assignments and 120 local checkpoints verify; no refit flag used |
| Historical accounting | 882 comparisons, 715 primary terms, 1,692 protected files and 33,264 prior monthly score cells verify; no new resampling run |
| Existing figure catalog | **952** figures and **32** protected numerical files verify |
| Repository layout | **1,070** immutable artifacts, frozen releases, navigation and ignore rules pass; zero private tracked files |

The initial extra join checker compared annual string keys with automatically parsed integer years and rejected that representation difference. Reading the saved year key explicitly as text resolved the check; no dataset, formula or aggregation changed. The subsequent 12-view replay passed. Existing numerical outputs and manifests were not rewritten by consolidation. Logs were kept locally under `/tmp/cmpt491_handoff_*`; the commands and existing release manifests below are the durable verification entry points.

All commands below run from the canonical root. Use the release-specific recorded requirements and existing environments; do not replace historical dependencies merely to satisfy a newer pipeline. Validation success establishes reproducibility of declared transformations, not independent accuracy of every provider measurement or a substantive economic relationship.

```bash
# Original foundation and publication: offline, retained private inputs required.
python3 src/phase1.py validate
python3 src/final_dataset.py validate

# Music/history validation without rewriting its recorded validation.json.
PYTHONPATH=src python3 -c 'import json; from music_enrichment_validate import public_checks, private_checks; print(json.dumps({"public": public_checks(), "private": private_checks()}, indent=2))'
python3 src/enrichment_common.py verify

# Financial catalog, public release, and full retained-snapshot reconstruction.
python3 analysis/external_historical/financial_research/verify.py
python3 analysis/external_historical/financial_acquisition/verify.py --private
python3 src/financial_acquisition.py validate --private

# Existing results: hash checks and saved-output replay; no campaign refits.
python3 src/regression_expanded_validate.py verify-publication
python3 src/regression_cross_domain_validate.py verify-publication
python3 src/course_verify.py
python3 analysis/historical_decomposition/verify.py
python3 src/figure_audit.py --validate
python3 src/repository_layout.py
python3 -m unittest discover -s tests -v
```

Public-only music/history checking can call `public_checks()` alone. Financial validation without `--private` reconstructs six public tables from committed inputs. The music validation script's CLI writes its audit JSON even though its checks are read-only; the function invocation above preserves the published report. Ordinary course verification uses saved outputs; do not add `--replay`, which invokes refits, for a handoff check.

For an explicitly requested offline rebuild, follow [music provenance](../analysis/music_enrichment_v2/provenance.md), [historical alignment](../analysis/external_historical/temporal_alignment.md) and [financial reproduction](../analysis/external_historical/financial_acquisition/README.md). Music view commands are `python3 src/music_enrichment_views.py chart` then `python3 src/music_enrichment_views.py build`; history uses `python3 src/external_historical_joins.py build`. The existing full offline replay command, `python3 src/enrichment_reproduce.py`, previously reproduced 38 artifacts byte for byte in 297.5 seconds. It republishes outputs, so consolidation instead rebuilt monthly music tables into a temporary directory and historical joins in memory. Finance `build --public` uses pinned public native inputs; full source normalization/build requires retained immutable snapshots. None of these commands authorizes a live source refresh or a new modelling campaign.

## Exact next research action

**Draft a versioned time-series protocol for review, then obtain explicit approval before executing the music–economy campaign.** Keep the first hypothesis family small and substantively motivated. Candidate comparisons are market returns/drawdowns with sentiment, unemployment/inflation with lyrical themes, financial stress with emotional scores, consumer sentiment with music, and political/social conditions with genre-specific change. These are candidate questions, not selected significant associations.

The protocol should specify the estimand (retrospective association or forecasting), source version/alias crosswalk, timing cutoff, natural frequency, outcomes and predictor families; choose one declared song/month weighting rule with composition/missingness sensitivities; predeclare transformations, finite lag sets, trend/seasonality treatment and autocorrelation-robust uncertainty. It should separate genre composition from within-genre change, avoid treating copied economic context on many songs as independent observations, define chronological evaluation and leakage guards, and state multiplicity control and negative-control/placebo checks. Previously examined years must be labelled exploratory; any untouched future confirmation period needs a prospective rule. A pandemic breakpoint, if proposed, needs its own justification and approval.

No unresolved Git merge conflict was found. Outstanding issues are scientific design, source rights/vintages, incomplete metadata/audio and backup verification. **Stop here: no new acquisition, features, unrestricted regression search or music–economy modelling is part of this handoff.**
