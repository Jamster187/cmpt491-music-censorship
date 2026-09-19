# Unified research database

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
keys. No classifier schema or scoring choices are introduced.

The database, provider responses, and lyrics are ignored in Git. Source code,
schemas, tests, reports, and these instructions are the reproducible deliverables.
Lyrics paths and source rights must be established before any acquisition; a
populated empty manifest is not evidence that lyrics have been attempted.

Current lyrics acquisition is blocked by the [source-access assessment](../reports/lyrics_source_assessment.md).
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
