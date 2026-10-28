# Publication validation

Research date: 2026-10-28. Canonical baseline: `57da4c4533919b929ad5fa0062c235f9a509fb18` on `main`. This package is research metadata and authored interpretation only. Its publication commit can be found with `git log -1 -- analysis/external_historical/financial_research/`.

The inventory contains 325 provider-input candidates, 289 overlap groups, 61 derived definitions (60 non-alias families), 81 source records, 221 source checks and 13 literature summaries (12 peer-reviewed studies and one senior thesis). The separate local-series audit captures 89 series already present in another session's work. These counts do not imply independent measurements, acquisition completeness or validated predictors.

Validation includes:

- CSV structure, unique IDs/names, all required metadata, source references and derived dependency references.
- Coverage/count reconciliation, one top-25 ordering and ten independent qualitative shortlist columns.
- Consistent `UNKNOWN`, unverified whole-history flags, no-computation flags and no saved observation values in source checks.
- File hashes, local Markdown links and protected baseline SHA-256 comparison.
- Manual review of exact series identities, source access failures, direct versus indexed documentation, the PPI code correction and old/new debt-service definitions.
- Full repository suite: `python3 -m unittest discover -s tests -v` passed **554 tests in 82.574 seconds**, with **16 skips**. This is an engineering regression check, not empirical validation of economic/music relationships.
- Repository integrity check: frozen release hashes passed, **1,070 immutable artifacts** and **739 local links** checked, zero private tracked files and zero stale active paths.
- Package verification passed: **17 publication files hashed**, **nine protected baselines unchanged**, 325 candidate inputs, 81 source records, 61 derived definitions, 25 recommendations and 27 local Markdown links. The check caught and prompted correction of a duplicated research inventory ID before publication; all IDs and references now pass.

`python3 analysis/external_historical/financial_research/verify.py` verifies the publication hashes, metadata relationships, counts, local links and nine protected baseline hashes. It is read-only and uses the Python standard library. Source pages are not re-requested by this command; temporal research findings remain a dated snapshot. The manifest preserves baseline hashes for AGENTS.md, README.md, both repository guides, public manifest/monthly/weekly/song exports and the Phase 1 database.

The campaign began at 18:23:25 UTC. The publication manifest records the final validation timestamp and elapsed research runtime. Browsing was restricted to source documentation and small verification requests. No bulk acquisition, paid/restricted download, model training, regression, classification rerun, new join, source-data edit or methodology change was performed by this campaign. Concurrent enrichment/acquisition files were preserved and excluded from this publication.

Limits: successful documentation reads do not prove download access, licensing, exact first/last nonmissing observations or historical release-vintage coverage. No full-history completeness audit was performed. Several source endpoints failed direct access and remain explicitly qualified. The proposed acquisition sprint and every statistical/regime choice require later review.
