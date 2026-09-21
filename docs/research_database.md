# Unified research database

Acquisition is frozen as of September 20, 2026. All 25,363 study assets have
metadata and lyrics dispositions: 20,450 high-confidence MusicBrainz matches and
19,372 usable lyrics. The unified lyrics manifest is synchronized. A separate
[four-model classifier runner](classifier_production.md) is prepared and tested on the existing 200-song
pilot. Full-corpus inference has not started; classifier results are not imported
into this database or the public master CSV. Earlier acquisition instructions and
reports below remain as a record of the work; they are not instructions to restart acquisition.

The public release contains [song and monthly CSVs](../data/public/README.md),
generated with `python3 src/public_dataset.py build` from this retained local
database. `python3 src/public_dataset.py validate` verifies the frozen export,
including deterministic serialization. It exports only allowlisted factual
summaries and status fields, never lyrics, local paths, or raw provider evidence.
The private enriched database is not distributed; downloading the public CSVs
does not require rebuilding it. The public release documents why no additional
weekly CSV is published and how to regenerate weekly data locally.

Build or validate locally:

```bash
python3 src/research.py build
python3 src/research.py validate
python3 -m unittest discover -s tests -v
```

`data/processed/research.db` is the working research database. Phase 1's
`data/processed/music.db`, raw Billboard JSON, and the approved population database
are read-only inputs. The unified database contains one self-contained copy of
the chart tables; it does not duplicate titles/artists on observations or copy
API response caches into each song. This modest source copy keeps joins and
foreign keys usable without connection-specific attached views.

| Table/view | Purpose |
|---|---|
| songs | All 32,723 exact Billboard identities; original/normalized strings plus first/last chart, observed best rank, row count, distinct weeks, total chart points |
| chart_observations | All 355,487 original weekly rows and source coordinates |
| weekly_top100 | View adding weekly points to the original weekly fields |
| monthly_top100 | The 81,800 approved monthly rows, including duplicate-aware observation counts |
| study_population | The 25,363 selected identities and first/last/month-count membership |
| metadata_matches | One current MusicBrainz asset decision per study song, with evidence-file checksum and matcher version |
| external_entities | Provider entities with metadata and cache provenance, stored once per provider/type/ID |
| song_external_links | One-to-many asset links to recordings, artists, releases, and release groups |
| lyrics_manifest | One row per study song; initial status is not_attempted, with fields for source, identity, file, checksum, timestamp, and failure reason |
| lyrics_pilot | Deterministic pilot membership from the actual study population |
| acquisition_runs | Incremental run start/finish/state and parameters |
| build_metadata | Schema, code, and immutable input fingerprints |

`best_chart_rank` is computed from observed ranks, not inconsistent source peak
fields. Original `peak_position` remains unchanged on weekly observations.
Original duplicate song/week rows remain distinct by source row coordinates.
Study membership never depends on successful enrichment or lyrics retrieval.

Existing research databases are **validated, never overwritten**, by `build`.
This protects partially completed acquisition. To create a new version, explicitly
archive the current database and associated manifests first; the command has no
destructive rebuild option. Future schema changes should be explicit migrations.
Every row is reconciled against the source in both directions during validation,
including derived song history and study membership. All relationships use foreign
keys. Classifier schemas and results remain in a separate local artifact; no
classifier schema is introduced into this research database.

The database, provider responses, and lyrics are ignored in Git. Source code,
schemas, tests, reports, and these instructions are the reproducible deliverables.
Lyrics paths and source rights must be established before any acquisition; a
populated empty manifest is not evidence that lyrics have been attempted.

The earlier [source-access assessment](../reports/lyrics_source_assessment.md)
records the pre-pilot decision. The user subsequently authorized a local-only
LRCLIB technical pilot of exactly the existing 200 assets; full acquisition is
not authorized by that pilot instruction.
`python3 src/lyrics_plan.py` prepares the deterministic 200-song pilot from the
actual monthly population and records `blocked_source_access` for unattempted
manifest rows. This command has no HTTP implementation. It preserves an existing
pilot and any successful canonical file/manifest entry. The pilot covers all 69
first-chart years with quotas 29/29/29/29/28/28/28 across historical periods.

Use `python3 src/research_report.py` for overall, historical-period, individual-year,
and recent-period coverage. The report distinguishes pending metadata, attempted
API failures, and unattempted lyrics blocked on access. It never treats an access
block as a failed identity lookup. [Production metadata instructions](production_metadata.md)
explain cache/resume behavior and runtime limits.

## Lyrics pilot sidecar

The [original pilot results](../reports/lyrics_pilot_results.md) describe the first
review. [LRCLIB-R](#offline-lrclib-r-review) provides the revised coverage separately.
Acquisition writes only `data/processed/lyrics.db`, with
frozen pilot identities/available metadata in `settings` and incremental results
in `results`. Canonical successes are `data/lyrics/<song_id>.txt`; HTTP responses,
attempt logs, and rejected texts stay under ignored `data/cache/lrclib/`.
The structured results preserve original Billboard identity, candidate evidence,
source identifiers, retrieval timestamps, selected album/duration, file hashes,
and review decisions. `review_history` preserves pre-review results.

```bash
python3 src/lyrics_lrclib.py run       # resume only the frozen 200; skips persisted results
python3 src/lyrics_lrclib.py validate
python3 src/lyrics_lrclib.py summary
python3 src/lyrics_pilot_report.py     # apply checksum-bound reviews and regenerate report
```

These commands never start the 25,363-asset workload. Error responses remain
cached; a normal resume does not retry terminal errors. A nonblocking file lock
prevents concurrent lyrics writers. Text comparison preserves word order and
repetition, ignores case/accents/punctuation, and treats conflicting normalized
texts as ambiguous. Artist comparison requires the complete credit; it does not
infer missing guests. Album and duration metadata support selection only when
available. Candidate truncation is recorded, so agreement covers returned
candidates, not an exhaustive catalogue search.

The unified `lyrics_manifest` intentionally remains at its pre-pilot state while
Codex A writes metadata. Consequently `research_report.py` does not include the
sidecar's coverage, and unified canonical-file validation will report these
sidecar-owned files as unmanifested. Use the sidecar validator until import;
do not rebuild the unified database to address that discrepancy.

After the metadata writer has stopped, the deterministic import command is:

```bash
python3 src/lyrics_lrclib.py import --metadata-stopped
python3 src/research.py validate
```

Import was **not run** during the pilot. It validates text checksums and exact
pilot identities, refuses conflicting successful files, and updates only lyrics
manifest rows in one transaction. A busy SQLite writer causes immediate failure;
no waiting write transaction is imposed on metadata acquisition. It preserves
the sidecar and its history. The `--metadata-stopped` flag is an operator assertion,
not an automatic process-control action.

## Offline LRCLIB-R review

[Phase LRCLIB-R](../reports/lyrics_lrclib_r_results.md) separates identity confidence
from text quality for all 83 originally ambiguous assets. The 112 original usable
files and five not-found cases are carried forward unchanged. It uses no network
requests and does not alter either acquisition database or canonical lyrics files.

```bash
python3 src/lyrics_lrclib_r.py build
```

The versioned [review ledger](../reports/lyrics_lrclib_r_review.json) is the explicit
case-by-case crosswalk, bound to exact cached candidate hashes. Build checks every
case, regenerates the aggregate report and case CSV, and prepares 59 recoverable
texts under ignored `data/cache/lrclib-r/texts/`. The combined 171-asset corpus
manifest is `data/processed/lyrics_lrclib_r.json`; its `corpus` array references
both the original 112 files and the 59 reviewed files with exact hashes.

The manifest retains independent identity/text grades, source retrievals,
alternative candidate diagnostics, warnings, and reversible cleaning provenance.
Minor transcription or repetition differences do not imply a wrong identity.
Explicit version/censorship uncertainty remains visible even when text is usable.
No missing words, repetitions, or censored content are reconstructed.

The original `lyrics_lrclib.py import` command imports only the original pilot
sidecar, not the revised LRCLIB-R manifest. No Phase LRCLIB-R import or full-scale
matcher is implemented by this focused review. The reviewed crosswalk is not an
automatic acceptance rule for unseen songs. Earlier reports remain historical
records rather than being rewritten to erase the initial conservative result.

## Production lyrics consolidation (schema 2)

After all study assets have a production disposition and both writers are idle:

```bash
python3 src/lyrics_import.py
python3 src/research.py validate
python3 src/lyrics_production.py validate
python3 src/research_report.py
```

This production-aware command supersedes the historical pilot-only import above.
It requires the complete, exact frozen study population, validates canonical files
and preserved pre-resume decisions, and holds the lyrics and MusicBrainz client
locks. It uses a temporary SQLite copy, validates before publishing, checks that the
original database has not changed, and retains an ignored checksum-bound backup.
An unchanged re-import performs no publication or timestamp update.

Schema 2 extends only the allowed manifest disposition names: production
`accepted` maps to existing `success`; `quarantined`, `wrong_identity`,
`bad_missing_text`, `not_found`, and `error` remain distinct. Legacy status names
remain supported. No chart, identity, metadata or pilot table is rebuilt.
`build_metadata` records the schema transition and deterministic source-result
set hash, importer hash and import timestamp.

The manifest stores provider ID, selected title/artist, local canonical path/hash,
retrieval time, failure reason and a small provenance allowlist. Provenance includes
the exact production disposition, matching and text grades, implementation bundle
hash, sidecar payload hash, run ID when available, review-ledger hash, and cache
URL/hash/time references. Raw lyric text, cache bodies and candidate texts are
excluded. The sidecar preserves the full decision evidence and original history.
The ordinary `research.py validate` checks canonical files after synchronization;
`lyrics_import.py` additionally reconciles every manifest field with the sidecar.
