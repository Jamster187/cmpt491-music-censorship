# Audits and production evidence

Student-facing results have moved to [analysis/](../analysis/README.md).

## Current audit entry points

- [Final dataset build](final_dataset_build.md): current public release reconciliation.
- [Final genre audit](genre_final_audit.md) and [validation receipt](genre_final_audit/validation.json).
- [Final catch-up audit](month_end_catchup_audit.md): completed month-end enrichment.
- [Phase 1 quality](phase1_data_quality.md): immutable chart foundation and source anomalies.

## Retained production dependencies

Several historical-looking machine-readable files remain at their original paths:
`genre/`, `genre_llm/`, `classifier_production/`, LyricLens/Detoxify prediction and
artifact files, lyric review ledgers, and month-end comparison/catch-up receipts.
Frozen scripts, review gates, model pins or private manifests still reference them.
They are reproducibility evidence, not additional current analysis datasets.
The month-end population comparison is historical, but its frozen producer and
receipt paths remain intact. Do not move these assets merely to simplify this directory.

Completed checkpoint narratives, source research, metadata feasibility studies,
classifier-panel reports and genre-refinement reports are preserved in
[archive/intermediate_reports/](../archive/intermediate_reports/).
The indexes in [final_audits/](final_audits/README.md) and
[methodology/](methodology/README.md) provide navigation without duplicating pinned files.

`reports/classifier_panel` is a documented compatibility symlink to the archived
pilot assets, required by the hash-pinned original runner. LyricLens evaluation
and its shared diagnostics module retain their canonical paths/bytes because
production fingerprints include them. These are deliberate reproducibility exceptions.
