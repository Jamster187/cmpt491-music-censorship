# CMPT 491: popular music content over time

This university data-mining project will investigate whether popular music's
lyrical/content characteristics changed unusually after COVID relative to the
historical trajectory from 1958. The historical baseline may end around 2019/2020;
the breakpoint and analysis design are still undecided. Later phases may add
lyrics, content measurements, genre, and other documented metadata.

**Phase 1 only:** preserve Billboard chart history and establish an auditable
research dataset. No lyrics, APIs, scraping, enrichment, classifier, or statistical
analysis is implemented.

## Reproduce Phase 1

From the repository root, use **Python 3.9 or newer** with SQLite support:

```bash
python3 src/phase1.py build
python3 src/phase1.py validate
python3 -m unittest discover -s tests -v
```

Phase 1 uses only the standard library; no dependency installation is required.
The existing `requirements.txt` is retained as the original notebook/scientific
environment snapshot. It is optional for this phase. The existing `.venv/` can be
used, but neither it nor its contents belongs in Git.

The build reads `data/raw/billboard-hot-100.json`, validates the actual schema,
creates a fresh SQLite database, validates every transformed row, exports CSVs,
and generates the reports. Running it again replaces only these derived outputs;
it does not append duplicate data. Treat this as a rebuild, not an incremental
database migration. Keep future manually reviewed decisions/enrichment outside
these generated Phase 1 outputs.

`validate` is read-only: it checks the existing database, both CSVs, both reports,
source hash, and pipeline version against the source. It fails on mismatches.
Source anomalies are reported and retained; transformation failures exit nonzero.

Paths default to the repository location even when invoked from another directory.
For an isolated build, specify **all output locations**:

```bash
python3 src/phase1.py build --output-dir /tmp/music-phase1/data --report /tmp/music-phase1/quality.md
python3 src/phase1.py validate --output-dir /tmp/music-phase1/data --report /tmp/music-phase1/quality.md
```

`--source PATH` can select another local snapshot. No network requests are made.
Never modify the repository's `data/raw/`. The program rejects output paths in it.

## Layout and provenance

```text
AGENTS.md                           project scope and development rules
data/raw/billboard-hot-100.json      immutable supplied snapshot; included in Git
src/billboard.py                     schema checks, exact identities, normalization
src/quality.py                       source diagnostics, integrity checks, reporting
src/phase1.py                        build/validate CLI, SQLite, CSV exports
tests/test_phase1.py                 ingestion and integrity regression tests
data/processed/music.db              canonical working database (generated, ignored)
data/processed/songs.csv             reproducible export (generated, ignored)
data/processed/chart_observations.csv reproducible export (generated, ignored)
reports/phase1_data_quality.md        concise generated report, included in Git
reports/phase1_data_quality.json      full generated audit/anomaly details (ignored)
```

The existing `notebooks/` and `results/` directories are available for later work.
Reported source: [mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100).
Billboard is the chart-history authority; this file is a supplied third-party
snapshot. Its upstream commit and acquisition date are unknown. Phase 1 records
that uncertainty rather than inventing provenance. No independent upstream
verification or source licensing assessment has been performed.

The database's auxiliary `build_metadata` table and the reports record the source
SHA-256/size, source chart inventory, pipeline-code SHA-256, schema/identity rules,
and Python/SQLite/Unicode versions. Source coordinates are zero-based JSON array
indices: `raw[source_chart_index]["data"][source_row_index]`. Coordinates identify a
record within a snapshot; they are not stable observation IDs across new snapshots.

## Canonical data model

| Table | Grain | Fields |
| --- | --- | --- |
| `songs` | One exact original title + artist credit | `song_id` (primary key), `title`, `artist`, `normalized_title`, `normalized_artist` |
| `chart_observations` | One source song-week entry, including repeats | `song_id` (foreign key), `chart_date`, `rank`, `last_week`, `peak_position`, `weeks_on_chart`, `source_chart_index`, `source_row_index` |
| `build_metadata` | One audit property | `key`, `value` |

`chart_observations` uses `(source_chart_index, source_row_index)` as its primary
key. Neither `(song_id, chart_date)` nor `(chart_date, rank)` is constrained unique:
source duplicates must remain representable. Source `this_week` maps to `rank`.
Reported rank/peak/week values are preserved, even when inconsistent. Enable
`PRAGMA foreign_keys = ON` when opening SQLite connections for future writes.

Song IDs are `song_` plus a full SHA-256 digest. Hash UTF-8 bytes of the version
prefix `billboard-song-v1`, a NUL separator, and compact JSON `[title,artist]`
(`ensure_ascii=False`, `separators=(",", ":")`). Only exact original strings define
identity; IDs are stable across reordering, appended charts, and repeat builds.
Hash collisions cause a hard failure.

Normalization is Unicode NFC → casefold → trim/collapse Unicode whitespace into
single ASCII spaces → NFC. It retains punctuation, accents, version descriptors,
and collaborator credits. Normalized equality **never** merges song IDs. The
Unicode runtime version is recorded. Exact title/artist identity does not guarantee
a unique recording; different recordings may share a source credit.

CSVs use UTF-8, deterministic row order, and standard CSV quoting with CRLF record
terminators. SQL NULL exports as an empty cell. Absent numeric source fields also
map to NULL; missing-key and explicit-null counts remain separate in the audit,
with original distinctions recoverable from raw JSON and source coordinates.
Unsupported fields/types, ambiguous JSON keys, and invalid identities/dates fail
clearly, before replacing existing outputs.

All outputs are staged and checked before individual atomic replacements. An OS
interruption between replacements can leave mixed artifacts; `validate` detects
this and rerunning `build` repairs it. Do not run concurrent builds. Identical input,
pipeline code, and runtime produce identical outputs. Across SQLite/Python versions,
binary database bytes or normalization may differ; original text and exact IDs
remain stable. There is intentionally no wall-clock timestamp in generated outputs.

## Quality and next decisions

See [the generated quality report](reports/phase1_data_quality.md) for exact counts,
missingness, all short charts, repeated song/week entries, normalization candidates,
and peak/rank inconsistencies. The local snapshot covers 1958-08-04 to 2026-09-19;
2026 is partial. Distinct artists means distinct credited strings, not resolved
individual artists. No rows are discarded or source anomalies repaired.

Before Phase 2, resolve recording/composition identity, review uncertain matches,
verify source/provider provenance and reuse terms, and decide how to handle source
anomalies. Population/sampling, chart exposure weighting, COVID breakpoints, and
classifier methodology remain research decisions. Phase 2 requires explicit approval.

Project remote: [Jamster187/cmpt491-music-censorship](https://github.com/Jamster187/cmpt491-music-censorship).
The primary branch is `main`. Raw data is kept in Git; generated databases/CSVs,
environments, caches, and local credentials/configuration are ignored.
