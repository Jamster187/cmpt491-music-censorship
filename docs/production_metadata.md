# Production MusicBrainz enrichment

Only the 25,363 monthly-population identities are eligible. Unmatched songs remain
in the database and study population. The unchanged approved `phase2ar-asset-v1`
matcher evaluates complete title/artist credits, consistent artist IDs, versions,
and temporal support. Multiple recordings may support one asset; none is chosen
as a canonical recording.

```bash
# First build the unified database (safe if it already exists).
python3 src/research.py build
# Import only pilot identities that actually belong to the study, without requests.
python3 src/production_metadata.py --offline --import-pilot
# Continue missing songs; choose an explicit wall-time budget if desired.
python3 src/production_metadata.py --max-seconds 28800
# Inspect/retry API errors explicitly, without rerunning successful decisions.
python3 src/production_metadata.py --retry-errors --max-seconds 3600
python3 src/research.py validate
```

Without limits the run processes all remaining study members. `--max-songs N`
counts new decisions this invocation, not existing ones. Songs are ordered by
deterministic per-year hashes, round-robin across first-chart years, newest year
first. This covers every era while reaching recent years early. Partial-run
acceptance rates are not full-population coverage estimates.

## Retrieval and cost

This first pass uses one full-title/full-credit search and at most one original
Phase 2A retrieval fallback (100 candidates per query, no pagination or tail rescue).
It calls the approved Phase 2A-R decision implementation. Existing detailed entity
lookups are reused; new optional recording/artist/release-group lookups are deferred
to keep identity enrichment from consuming several additional nights. Search
responses already contain release context, durations, ISRCs, and raw tags when
available. Absent detailed genres are unmeasured, not demonstrated absent.

At 1.1 seconds per request, 25,363 uncached single searches alone have a theoretical
minimum of 7.75 hours, before latency, fallbacks, or retries. Fetching every
supporting recording/artist/release group would be much slower. Time-budget exits
preserve progress and do not mark an interrupted song as unmatched.

One cached HTTP client uses an identifying project User-Agent, a process lock,
at least 1.1 seconds between requests, provider Retry-After, and exponential retry
delays. Three consecutive failed songs stop the run. Errors are distinct from
not_found; all attempts remain cached. No proxy, parallel API workers, credentials,
or bypass is used. See the [MusicBrainz rules](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)
and [data license](https://musicbrainz.org/doc/About/Data_License).

## Persistence and provenance

`data/cache/musicbrainz_production/` starts from verified copies of frozen pilot
responses and never changes those original experiment caches. URL and body hashes
are checked before cache reuse. One request may be replayed from cache after an
interruption without a new network request.

Each completed decision is committed in its own SQLite transaction. Decision
files under `data/processed/metadata_results/` are content-addressed; an interrupted
file/DB publication can leave an unused file, never a pointer to altered evidence.
SQLite stores the decision, file hash, all supporting entity links, and compact
entity metadata. Raw API responses remain in the cache. Entity variants and cache
references are preserved rather than overwriting contradictory values.

Recordings, releases, release groups, and artists have distinct entity types.
Raw tags/genres and vote counts are retained without a taxonomy or artist-to-song
inheritance. Recording links are asset evidence, not a guarantee that all durations
or clean/explicit variants are interchangeable. Existing review flags remain.

Reruns skip completed successful/ambiguous/not-found decisions; `--retry-errors`
only adds failed decisions to the pending queue. They never edit Billboard identity,
monthly selection, or lyrics. All generated data remains ignored in Git.

## Independent full-population run

The continuation session started the existing script without song/time limits as
an independent process. It resumes pending study assets and retains the existing
three-consecutive-errors stop safeguard. It does not retry ambiguous/not-found
assets or relax the matcher. Current launch details/PID are saved locally in
`data/cache/musicbrainz_production/background-process.json`; progress is appended
to `data/cache/musicbrainz_production/production-background.log`.

Check the process and log before starting another worker:

```bash
pgrep -fl production_metadata.py
tail -n 5 data/cache/musicbrainz_production/production-background.log
```

If no worker is running, start/resume from the repository root:

```bash
mkdir -p data/cache/musicbrainz_production
nohup python3 -u src/production_metadata.py \
  >> data/cache/musicbrainz_production/production-background.log 2>&1 < /dev/null &
metadata_pid=$!
# macOS: prevent idle sleep while this process runs.
/usr/bin/caffeinate -i -w "$metadata_pid" >/dev/null 2>&1 < /dev/null &
```

The current session used Python's `start_new_session=True` with detached standard
streams for the equivalent independent launch; its process was verified reparented
to PID 1 and making progress. No service or new pipeline architecture was added.
The sleep guard does not protect against shutdown, forced sleep, or network loss.
To stop safely, verify the PID belongs to this command, then send `kill -INT PID`.
After a stop or completion, inspect the last `Run finished:` log entry, validate,
and regenerate the report:

```bash
python3 src/research.py validate
python3 src/research_report.py
```

The database is the live progress record; committed reports are dated snapshots.
Logs, process state, caches, and generated databases remain ignored. Automatic
restart loops are intentionally absent: repeated provider errors should be
inspected before explicitly resuming. Use `--retry-errors` only for failed requests.
