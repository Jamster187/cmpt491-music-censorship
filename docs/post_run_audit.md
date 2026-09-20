# Post-run audit decisions — 2026-09-20

The [reproducible aggregate audit](../reports/post_run_audit.md) supersedes the
running checkpoints. The earlier reports are historical records. No acquisition
was restarted, no matching rule changed, and neither database was migrated.

## Completion and failure

**MusicBrainz: COMPLETE first pass.** The final production run ended at
2026-09-20 08:13:23 UTC with `complete`, 24,436 new decisions and 30,396 network
requests. Together with 927 prior decisions, every one of the 25,363 study assets
has a persisted outcome: 20,450 accepted, 3,410 ambiguous, 1,502 not found, one
error. Thus completion does not imply that every lookup succeeded. No unprocessed
assets remain and no restart is needed to improve acceptance. The one terminal
API/cache error remains distinct from not found; its cache ends with HTTP 503.

**LRCLIB: FAILED invocation, intact resumable data.** The final run ended at
2026-09-20 06:54:16 UTC after 21,446 new decisions and 24,655 requests. Adding the
200 seeded pilot outcomes gives 21,646 attempted assets; 3,717 are unprocessed.
There are 16,572 usable files, 2,999 quarantined outcomes, 1,181 wrong identities,
159 bad/missing texts, 735 not found, and zero persisted API-error outcomes.
Zero recorded API errors does not negate the process failure.

The traceback in ignored `data/cache/lrclib/production.log` identifies
`src/lyrics_lrclib.py`, `Client.search`: the loop checks `time.time() < until`,
then calls `time.time()` again to calculate sleep. The deadline can pass between
those calls, producing a negative argument to `time.sleep`. This is a transport
wait race, not evidence of a matching or lyric-file failure. The run table records
`failed`; the exception occurred before the next asset was persisted.

Process-list inspection found no acquisition worker or associated `caffeinate`
process. Completion classifications also use run tables, log endings, queue
counts and file validation, not missing PIDs alone. The saved lyrics worker PID
45335 and metadata PID 42837 are absent. `metadata_worker_checkpoint.json` still
shows the historical 1,859-song running checkpoint; it is stale, not the final
state. The study identities still account for 338,706 of 355,487 weekly rows
(95.28%); the full weekly foundation remains available.

## Resume decision

Do not resume either job as part of this audit. MusicBrainz has no remaining first
pass. LRCLIB's data-preserving resume command, from the repository root, is:

```bash
python3 src/lyrics_production.py run
```

It skips all persisted outcomes and reuses verified caches. Do not use
`--retry-errors`: there are no recorded lyrics errors to retry. This command is
safe for the existing saved outcomes, but the **unchanged code can hit the same
sleep bug again**; it is not a fault-free remedy. Before recommending execution,
fix and regression-test the wait race, then explicitly handle the production code
fingerprint transition. `initialize` refuses changed code; merely editing the wait
and rerunning, rerunning the gate, or silently replacing the stored fingerprint is
not an adequate migration. Preserve old provenance and review a narrow version
transition. This audit deliberately leaves that work and the resume decision open.

Observed throughput was 21,446 new decisions in 7 h 39 m 11 s. The 3,717 remaining
assets would take approximately **80 minutes (1.33 hours)** at that rate, plus
validation; allow roughly 1–2 hours with similar provider behavior. Network delays
can make it longer. The queue is ordered by deterministic identity hash, not era
or popularity; it is not a newly designed random sample.

## Integrity and validation

Executed during the audit:

```bash
python3 -m unittest discover -s tests -v
python3 src/phase1.py validate
python3 src/lyrics_production.py validate
python3 src/research.py validate
python3 src/post_run_audit.py
```

- All 142 tests passed (139 existing plus three focused audit regressions for exact cross-store identities and population membership).
- Phase 1 validation passed, including immutable source SHA-256, original rows,
  exports and generated quality report. Source anomalies remain preserved.
- Production lyrics validation passed: 16,572 canonical file hashes and exact
  asset identities; no missing/orphan canonical files.
- The standard unified validator **fails** with `Unmanifested lyrics files or
  unexpected layout`. The existing documentation predicts this: its manifest
  remains at pre-acquisition `blocked_source_access`, while production owns the
  files through the sidecar. Do not describe this command as passing.
- The audit separately runs existing research validation with `check_files=False`
  for source hashes, complete row reconciliation, counts, SQLite and foreign keys;
  then independently checks every metadata evidence-file hash and uses the
  production lyrics validator. It also reruns independent monthly aggregation,
  reconciles the frozen lyrics identities with the study population, checks pilot
  success preservation, and checks cache envelope URL/body hashes. This avoids
  skipping metadata validation merely because the old manifest is stale.
- Both working databases are opened read-only and their file hashes are compared
  before/after the aggregate audit. MusicBrainz evidence, chart foundation and
  lyrics corpus all reconcile; no evidence of cross-worker corruption was found.
- `git ls-files data/lyrics data/cache data/processed .env` is empty; ignore checks
  cover those paths. Only the original raw Billboard snapshot is tracked under
  `data/`. No classifier/scoring table or generated classifier/rawness/hardness
  artifact was found in the inspected schemas and project file inventory.

The background MusicBrainz completion-validation log had the same expected
unified-manifest failure. It is not evidence that the metadata pass stopped early.
No substantial lyric text is included in these reports.

## Unified representation

The architecture already preserves a clean shared key: exact Billboard `song_id`
connects songs, weekly observations, monthly baskets and metadata in `research.db`
to `production_assets`/`production_results` in `lyrics.db`. The latter's JSON
payload contains disposition, provider identifier, path, checksum, timestamps,
match/text decisions and provenance. A read-only SQLite `ATTACH` and join on
`song_id` is sufficient for an audit or later research query; no text copy is
needed. The audit verifies the exact title, artist and first-chart date across
both stores.

It is **not yet a current self-contained unified lyrics manifest**. A later
production-aware deterministic import (or explicitly supported read-only view)
should populate/reference lyrics metadata and paths, preserve all dispositions
without collapsing wrong identity into missing text, validate hashes/identities,
and retain provenance/history. The current manifest status constraint does not
name every production disposition. The original pilot-only import is unsuitable
for this corpus. Do not run it, rebuild the database, or copy lyrics into
`research.db` to eliminate the validator error. No such migration was performed.

Metadata is useful enrichment, not a prerequisite for eventual content
classification. No classifier, content scores, genre taxonomy or COVID hypothesis
test was designed or run.

## Missingness interpretation and next step

The available corpus is not obviously representative without qualification.
Among attempted assets, success ranges from 71.33% in 1958–1969 to 83.10% in
2010–2019. It is 82.92% for first-chart years 2015–2019 and 80.13% for 2020–2026;
the latter includes a 75.59% low in 2021. About 14–15% of each recent cohort is
still unprocessed, so current target coverage (71.28% versus 68.69%) is not final
source availability.

Selection favors popular and persistent songs: success among attempted assets is
84.20% for weekly Top-10 peaks versus 71.27% for peaks 41–100, and 87.36% for
7+ selected months versus 69.71% for one month. Monthly observation success also
falls from 85.03% at ranks 1–10 to 77.07% at ranks 51–100. Mean weekly points are
746.25 for usable assets versus 552.27 for attempted unsuccessful assets.

Credits containing collaboration-like separators have 64.46% attempted success
versus 79.40% without them. This is an imperfect text heuristic and can flag band
names. These descriptive associations are not adjusted causal effects. The
precision-first full-credit matcher plausibly contributes; this audit does not
relax it. Content-dependent shortness, instrumental/missing text, censorship and
version/conflicting-text rules also mean missingness cannot be assumed independent
of the eventual content measurements. Pilot accuracy is development evidence,
not independent validation of the entire production corpus.

The corpus covers 68.21% of all monthly observations and 69.70% of monthly points.
For calendar baskets in 2015–2019 versus 2020–2026, row coverage is 74.25% versus
71.48% and point coverage is 75.89% versus 72.01%. These calendar-basket measures
include older songs and must not be confused with first-chart cohort coverage.
No hypothesis test was performed.

**One concrete task should precede classifier design:** prepare a tested fix for
the LRCLIB wait race with a provenance-preserving code-version transition. Then
make the requested decision on whether to spend approximately 80 minutes finishing
the 3,717 unprocessed assets, or explicitly freeze the partial corpus. Neither
restarting nor that choice was authorized by this audit request. Metadata need not
be retried and is not a classifier prerequisite. A production-aware lyrics manifest
integration remains a separate deterministic consolidation task, not a reason to
copy lyric text or redo acquisition.
