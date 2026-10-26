# Dataset expansion research

Research and feasibility review, dated **2026-10-26**, for the exact Billboard title/full-artist-credit research population. This directory contains specifications and evidence, not acquired feature values, new classifiers, a changed methodology, or new COVID/statistical results. Implementation requires a subsequent approval.

Start with [findings](research_findings.md) and the [recommended expansion plan](recommended_expansion_plan.md). There are **188 inventory rows: 182 substantive research candidates and 6 Tier 4 ideas excluded from that count**. A vector/set is one construct; embedding dimensions, genre categories and alternate numerical encodings are not counted separately. A credible candidate means a meaningful, evidence-supported construct, **not** a validated predictor or guaranteed acquisition route.

| Tier | Candidates | Meaning |
|---|---:|---|
| 1 | 59 | Derivable from existing assets; extraction/definition validation still required |
| 2 | 66 | Plausible free credible source and matching route; actual field/song coverage remains unmeasured |
| 3 | 57 | Incomplete, restricted, costly, or substantial unresolved feasibility work |
| 4 | 6 | Speculative/unavailable/unsuitable; excluded from 182 substantive candidates |

The **62 source records** comprise **58 external source families and 4 existing local asset families**. External verification: 41 documentation-verified, 1 live-sample-verified, 11 partially verified, 4 access/unverified, and 1 confirmed withdrawn. Thus 42 external sources have primary documentation or a live sample verified; that is not 42 production-ready sources. Twenty academic studies are reviewed separately and are not added to the source-family count.

## Files

| File | Contents |
|---|---|
| [source_inventory.csv](source_inventory.csv) | Fields, access, history/geography, API, cost/rate limits, rights, matching, gaps and source verification |
| [candidate_columns.csv](candidate_columns.csv) | All proposed constructs, definitions, source links, temporal status, value, redundancy and feasibility |
| [feasibility_matrix.csv](feasibility_matrix.csv) | One row per candidate; separate top-20 commercial and historical ranks, access/rights gates and next decisions |
| [reconstructable_features.csv](reconstructable_features.csv) | All 59 Tier 1 definitions, existing input assets, historical cutoffs and required checks |
| [academic_evidence.md](academic_evidence.md) | Twenty studies with dataset, method, evaluation, findings and limitations |
| [rejected_sources.md](rejected_sources.md) | Rejections, deferred routes, duplicate ideas and unresolved claims |
| [research_findings.md](research_findings.md) | Existing-data audit, source conclusions, feasibility checks and leakage assessment |
| [recommended_expansion_plan.md](recommended_expansion_plan.md) | Top additions, separate objective priorities, effort and proposed first sprint |
| [existing_columns.csv](existing_columns.csv) | Actual 80-name union of current public-export headers, provenance and duplication/leakage guard |
| [search_log.csv](search_log.csv) | Search strategies, representative exact queries, provider inspections and outcomes |
| [feasibility_checks.csv](feasibility_checks.csv) | Fourteen bounded AcousticBrainz access/field-presence probes; no audio or feature values |
| [local_metadata_audit.csv](local_metadata_audit.csv) | Fourteen matching metadata field-name inspections; no private lyric text |
| [validation_report.md](validation_report.md) | Scope, integrity and repository checks before publication |

## Reading the inventories

`candidate_id` and `source_id` are research references, not dataset song identifiers. CSVs are UTF-8 with standard quoted fields. `UNKNOWN` means evidence is insufficient; `NOT_APPLICABLE` means the concept does not apply. A blank rank is not used: `UNRANKED` means outside the small prioritized list, not tied for last. Ranks are qualitative research judgments balancing historical coverage, access, rights, leakage, incremental information and effort; there are no estimated percentage gains.

Every candidate has a primary source URL. `licensing`, `source_storage_permissions` and `redistribution_permissions` reference the exact source record containing the detailed conditions and terms URL. A reference is not a permission grant. For Tier 4 budget/slang ideas the provider is explicitly UNKNOWN and the linked source documents the failed route, not a claimed field. The search log records an inspection for every source family, study follow-ups, and representative literal queries; it is a research audit, not a claim to reproduce every search-engine result. Academic IDs `A01`–`A20` resolve in the evidence review. “Hypothesis” identifies proposed reasoning rather than an established finding for the exact variable.

Temporal classes follow the requested definitions: **A** before release; **B** at release; **C** at chart debut; **D** during chart run; **E** after chart run; **F** present-day retrospective measurement. The inventory uses a conservative **primary** class and an additional `intrinsic_availability` field. An old recording or lyric may have existed at release, but a newly measured version with no original-version proof remains F. It is not silently promoted to B. There are 2 A, 43 C, 12 D and 131 F rows, including Tier 4. No new candidate is assigned B or E: original-version evidence has not been established, and full-run outcomes already exist. Existing outcome columns are separately marked E/F in the baseline inventory.

For every A–C proposal, the availability label is conditional on the stated historical source/vintage requirements. A missing archived value never permits replacement by today's total. Tier 1 does not mean forecasting-safe: local lyrics and catalog metadata remain retrospective. Tier 2 does not mean whole-population coverage: McGill/SALAMI are useful free subsets. Source status, feasibility tier and temporal status answer different questions.

This directory is intentionally self-contained. Existing downloadable datasets, published analyses, raw source files and Phase 1 data remain at their canonical paths. No external account was contacted and no paid API was used.
