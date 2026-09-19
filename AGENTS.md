# CMPT 491 music research

## Research objective and current scope

Investigate whether the lyrical/content characteristics of mainstream popular music
changed unusually after COVID relative to their long-run historical trajectory.
Billboard Hot 100 history defines the chart population, with a prospective baseline
from 1958 to approximately 2019/2020 and subsequent coverage through 2026. The exact
breakpoint, sampling/weighting choices, classifier, and statistical methods remain
undecided. Chart dates are not song release dates.

Phase 1 is complete. Phase 2A was accepted and committed. The current authorized
scope is local analysis-population construction: preserve all weekly observations
and derive monthly Top-100 baskets using summed `101 - rank` points. No external
requests or enrichment are authorized. Preserve Phase 2A, Phase 2A-R, and Phase 2B
results. Keep derived population tables and exports
separate from the canonical Phase 1 database, which
must be opened read-only. Do not enrich the whole dataset, retrieve lyrics, implement
classifiers, finalize a genre taxonomy, or run statistical analysis. Do not invent
genre, metadata, or measurements. Show the population results and obtain the user's
approval before committing or pushing this work.

## Source and data model

- Billboard is the canonical chart-history authority; the supplied local snapshot
  comes from <https://github.com/mhollingshead/billboard-hot-100>. Record this as the
  reported upstream source, not as proof of independent verification.
- `data/raw/` is immutable source data. Never edit, overwrite, repair, or delete its
  contents. Diagnose source anomalies in reports and preserve the original values.
- SQLite at `data/processed/music.db` is the canonical working representation.
  CSVs are reproducible exports, not separately maintained datasets.
- `songs` holds one row per **exact original title + artist credit**. Song-level
  metadata belongs separately from the time-varying `chart_observations` table.
- The research asset is this Billboard title/artist pair; the same title performed
  by different artists is a different asset. External recording links are evidence
  for that asset, not permission to redefine or merge its Phase 1 identity.
- Prefer precision over recall in enrichment. Preserve all returned raw genres/tags
  with their entity level (recording, work, single, release group, artist); artist tags are not
  automatically song genres. Dates may support matching but are not chart dates.
- Preserve Billboard title and artist strings exactly. Artist credits may include
  collaborations; a distinct credit is not necessarily a distinct person or act.
- IDs must be deterministic from the exact identity, independent of input order.
  Normalized text is only a matching aid, never an automatic merge key. Keep
  punctuation, accents, credits, and version descriptors; document all rules.
- Retain every source observation, including repeated song/date pairs. Preserve
  source chart/row locations and a source file hash. Do not assume 100 rows per chart.
- Future lyrics and external metadata must retain provider, external identifiers,
  retrieval time, source/version, and the mapping decision to internal song IDs.
  Keep enrichment in separate linked tables/files; do not overwrite source text.
- Fuzzy/entity matching must never silently accept uncertain matches. Retain
  candidates, scores, method/version, review status, and unresolved cases. Any
  approved crosswalk must be explicit, versioned, and reversible.

## Pipeline and development

- Keep Phase 1 simple: Python standard library, SQLite, scripts under `src/`.
  Preserve existing work and dependencies unless a change is justified.
- Pipeline steps must be deterministic, restartable, and auditable. Generated data
  must be reproducible from the immutable source and versioned code. Record source
  and pipeline hashes and relevant runtime/normalization versions.
- Build in temporary files, validate before publishing, and fail clearly on
  unsupported schemas or lossy conversions. Do not silently skip bad records.
- Report source anomalies separately from transformation/integrity failures.
  Preserve anomalies rather than making speculative corrections.
- Changes to ingestion, identity, or validation require focused regression tests.
  Run `python3 -m unittest discover -s tests -v` and the relevant pipeline validation.
- Update `README.md` when rebuild instructions or data semantics change. Regenerate
  the quality report when source-processing behavior changes. Do not hand-edit
  generated reports or derived datasets.
- Never include environments, caches, credentials, temporary builds, or large
  generated databases/exports in Git. Do not choose a COVID breakpoint or sampling
  methodology as an incidental implementation detail.
