# Financial and macroeconomic discovery

Research snapshot: **2026-10-28**. This is a research-only catalog for comparison with the US Billboard Hot 100 population. No observations were acquired, datasets altered, regressions fitted, predictive models trained, or COVID breakpoint selected by this campaign. Existing acquisition work by another session was inspected read-only and is separately attributed.

Start with [research findings](research_findings.md), the [top 25 and proposed acquisition sprint](recommended_acquisition_plan.md), and the [literature review](academic_literature.md). The latter includes directly relevant results that point in different directions and a 2026 replication reporting instability in earlier music–market associations.

| Measure | Count | Meaning |
|---|---:|---|
| Candidate provider inputs | 325 | Evidence-supported constructs, including surveys, published indexes, estimates and event registers; not 325 independent measurements |
| Overlap/redundancy groups | 289 | Conservative grouping of obvious alternatives and components; remaining groups are not assumed independent |
| Derived definition rows | 61 | 60 non-alias families plus one explicit duplicate alias; formulas proposed, none computed |
| Source records | 81 | 74 live primary documentation verifications, 6 primary indexed/alternate-documentation verifications, 1 unverified archival lead |
| Histories reported to start by 1958 | 82 | Potential full-span inputs, subject to endpoints, gaps, definitions and access |
| Histories reported to start after 1958 | 195 | Partial-span inputs |
| Start date unknown | 48 | Must resolve before a coverage claim |
| Fully audited 1958–2026 histories | 0 | Metadata research is not a complete observation audit |
| No-fee candidate routes | 274 | Published/free-research routes; some require registration, keys, extraction or unresolved reuse checks |
| Free viewing with restricted/unclear reuse | 23 | Not an open redistribution grant |
| Paid/restricted complete-history routes | 22 | No purchase or restricted download attempted |
| Mixed access | 6 | Product or historical slice determines access |

The current local music snapshot reaches **2026-09-19**, not the end of 2026. Economic releases also stop at different periods. “1958–2026” describes the research scope, not complete calendar-year availability. An early source start does not establish an uninterrupted or freely accessible series. `UNKNOWN` is deliberate.

| File | Purpose |
|---|---|
| [indicator_inventory.csv](indicator_inventory.csv) | Every candidate's definition, exact source/series reference, frequency, geography, history, access, rights, revisions, publication lag, redundancy and verification |
| [source_inventory.csv](source_inventory.csv) | Provider/product routes, terms and source evidence; mirrors do not confer rights |
| [derived_indicators.csv](derived_indicators.csv) | Formulas, dependencies and timing limits; alternative regime definitions remain unselected |
| [historical_coverage.csv](historical_coverage.csv) | Reported coverage, unknown endpoints and explicit absence of full-history validation |
| [feasibility_matrix.csv](feasibility_matrix.csv) | Overall top 25 plus ten separate qualitative priority lists |
| [academic_literature.md](academic_literature.md) | Peer-reviewed evidence and a clearly separated undergraduate thesis |
| [rejected_sources.md](rejected_sources.md) | Excluded, deferred, duplicate and access-constrained routes |
| [recommended_acquisition_plan.md](recommended_acquisition_plan.md) | Small, reviewable first sprint and subsequent optional blocks |
| [research_findings.md](research_findings.md) | Audit, taxonomy, coverage gaps, source conclusions and strongest comparisons |
| [temporal_alignment.md](temporal_alignment.md) | Chart/release joins, vintage requirements and statistical design concerns |
| [search_log.csv](search_log.csv) | Search families, primary routes, discoveries and saturation rationale |
| [source_checks.csv](source_checks.csv) | Documentation checks and failures; no observation values retained |
| [existing_local_series.csv](existing_local_series.csv) | Read-only metadata snapshot of the separate session's 89 existing external series |
| [counts.json](counts.json) | Machine-readable counts derived from these inventories |
| [validation_report.md](validation_report.md) | Integrity, scope, runtime and verification evidence |
| [publication_manifest.json](publication_manifest.json) | File hashes and protected baseline hashes |
| [verify.py](verify.py) | Offline schema, reference, count, hash and link validation |

Run `python3 analysis/external_historical/financial_research/verify.py` from the repository root. It performs no network acquisition or analysis.

“Raw” means a provider-published input to a future study, not necessarily raw respondent microdata. For example, a stress index is already a composite and a forecast-error uncertainty index is a model estimate. `measurement_class` distinguishes these. Alternative encodings, lookback windows and threshold grids are not expanded into new raw discoveries. Panel vectors count once. Ranks are qualitative shortlist positions, not estimated effect sizes or a total ordering of every candidate; `UNRANKED` means no supported priority position assigned.

The existing [feature expansion research](../../feature_expansion_research/README.md) remains unchanged. Its sources and hypotheses are not replaced by this more detailed economic catalog. Publication of this package does not authorize the proposed acquisition or statistical-testing campaigns.
