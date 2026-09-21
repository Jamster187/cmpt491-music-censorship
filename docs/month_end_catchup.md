# Month-end acquisition and classifier catch-up

**Completed and audited.** The [final audit](../reports/month_end_catchup_audit.md)
confirms all 3,654 acquisition dispositions and four successful model results for
each of the 2,321 new usable lyrics. The commands below document the completed
run; they are not instructions to restart acquisition or retry exclusions.

The scope is exactly the **3,654 added identities** in the approved month-end
population: 28,041 songs, 818 snapshots and 81,797 observations. The three charts
missing rank 100 are accepted source gaps. No source rows are invented.

The scoped adapter imports the existing production functions. Matching, cleaning,
provider clients, rate limits, model checkpoints, chunking, aggregation and the
42-column feature schema are unchanged. It does not widen the old production
population or rewrite any original result. Current public CSVs remain unchanged.

## Storage and frozen inputs

Ignored local state is under `data/processed/month_end_catchup/`:

- `population.json`: sorted identities, independent old/new population check,
  code hashes, protected file hashes, all 19,372 original lyric hashes, and the
  19 archived MusicBrainz pilot evidence hashes.
- `metadata.db` and `metadata_results/`: scoped MusicBrainz dispositions and
  content-addressed evidence, using the existing production persistence schema.
- `lyrics.db`: scoped production assets, dispositions, history and run records.
- `classifier_results.db`: the unchanged production classifier schema, including
  independent jobs, raw chunk outputs, song scores and execution measurements.
- `metadata.log`, `lyrics.log`, `classifier.log`: independent incremental logs.
- `children.json`, `completion.json`, validation logs: live PIDs and final checks.

Successful lyrics remain local at `data/lyrics/<song_id>.txt`. Shared production
provider caches and their locks are reused. Neither original acquisition database
nor the original classifier database is written. Records for removed songs remain
preserved. A future explicit consolidation can join these sidecars by song_id;
this catch-up does not publish a new master dataset.

The original 19-song MusicBrainz pilot is replayed offline through the production
matcher, with disposition and supporting IDs checked against archived evidence.
The lyrics input snapshot then freezes the metadata already available from that
replay. Later concurrent metadata progress cannot change a lyrics decision.
MusicBrainz metadata remains supplementary, as in the first production pass.

Acquisition uses the original Python 3.9.6/Unicode 13 runtime. Classifiers use the
existing Python 3.11 model environment. Before model work, the adapter requires
an exact match to the original full-run dependency/source configuration hash;
only scope identity, target list and adapter provenance differ. It calls the
unchanged worker, inference, chunk persistence and validation functions.

## Run and resume

From the repository root, using the existing acquisition `python3`:

```bash
# Idempotent preparation; offline pilot replay only.
python3 src/month_end_catchup.py prepare
# Concurrent metadata + lyrics; classifier starts after all lyrics dispositions.
python3 -u src/month_end_catchup.py supervise
# Read live counts; generate a non-lyrical checkpoint report.
python3 src/month_end_catchup.py status
python3 src/month_end_catchup.py report
```

The supervisor can be detached with standard streams redirected to
`data/processed/month_end_catchup/supervisor.log`. The launch record stores its PID;
`children.json` stores child PIDs. A macOS `caffeinate -i -w PID` guard may prevent
idle sleep. Check existing PIDs and locks before starting another supervisor.
No automatic infinite restart loop is used.

Each stage also resumes independently:

```bash
python3 -u src/month_end_catchup.py metadata
python3 -u src/month_end_catchup.py lyrics
data/experiments/classifier_panel/venv/bin/python src/month_end_catchup_classifier.py run
```

Acquisition skips every saved disposition. Three consecutive MusicBrainz request
failures stop that worker for inspection, as before. Existing bounded HTTP retries
and Retry-After handling remain unchanged. The scoped commands do not retry
terminal errors, quarantine or deterministic model failures automatically.

Classifier jobs skip saved successes and errors, and resume interrupted jobs
from saved chunks. Every model's result persists independently. Failed models
retain NULL scores, exception type and processing stage in the validation ledger;
no lyrics are altered to force predictions. An unexpected overlap with the old
classifier target list stops for inspection/reuse rather than reclassifying it.

SIGINT/SIGTERM lets acquisition finish its current asset. The supervisor stops its
children on interruption; model transactions/chunk checkpoints make interruption
recoverable. Do not delete lock files to bypass a live worker.

## Completion and validation

```bash
python3 src/month_end_catchup.py validate
data/experiments/classifier_panel/venv/bin/python src/month_end_catchup_classifier.py validate
python3 -m unittest discover -s tests -v
python3 src/public_dataset.py validate
```

The supervisor performs these checks after workers exit and writes
`completion.json` plus the non-copyrighted catch-up report. It does not commit
background changes automatically. Inspect worker exit codes and completion
validation, not just missing PIDs or live disposition counts.

Validation checks original database/public/source hashes, every original lyric,
the union of original and catch-up lyric files, all new dispositions, exact target
IDs, model versions, finite/ranged numerical outputs, complete chunks and frozen
weighted aggregation. It also reconciles the original research relations using
`research.validate(..., check_files=False)`: the old standalone file census expects
exactly 19,372 files and is superseded here by the combined corpus census. Do not
rebuild research.db or weaken that historical validator to hide the new sidecar.

Coverage uses first Billboard appearance. The 2015–2019 subset overlaps the
2010–2019 group. Coverage is descriptive acquisition reporting, not a historical
content analysis. Genre assignment and public replacement remain outside scope.

## Reproduce the final audit

The audit only reads the databases and writes non-copyrighted reports. It requires
idle workers and the complete frozen catch-up scope. Capture a fresh test log,
then generate the independent census and integrity report:

```bash
python3 -m unittest discover -s tests -v > data/processed/month_end_catchup/post_run_tests.log 2>&1
python3 src/month_end_catchup_audit.py
```

The acquisition, classifier and public-export validation commands above were also
rerun for the audit. The final public release still awaits separately authorized
genre work and publication; no current public CSV was changed.
