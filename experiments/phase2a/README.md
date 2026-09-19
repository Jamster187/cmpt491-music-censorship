# Phase 2A metadata pilot

This is a feasibility test, not enrichment of the full study population. It reads
the Phase 1 SQLite database in read-only mode. MusicBrainz is the only tested
provider. No lyrics are retrieved. See the [source decision](../../reports/phase2a_source_research.md)
and [results report](../../reports/phase2a_metadata_feasibility.md).

## Run or reproduce

Python 3.9+ and its standard library are sufficient. From the repository root:

```bash
python3 src/phase2a.py sample
python3 src/phase2a.py run
python3 src/phase2a.py report
python3 -m unittest discover -s tests -v
```

The `run` command makes live GET requests only for missing responses and skips
completed songs. An interrupted run resumes with the same command. It stops after
three consecutive song errors. Inspect the errors before using `--retry-errors`,
which explicitly retries failed requests and optional enrichment failures. The
cache keeps earlier failed attempts. No API credentials are needed.

To recompute all decisions and reports from the frozen cached responses, with
network requests prohibited:

```bash
python3 src/phase2a.py run --offline --replay
python3 src/phase2a.py report
```

`--limit N` processes only the first N songs of the same fixed sample, useful for a
smoke test. It cannot expand beyond 200. Do not run concurrent clients. A replay
updates processing timestamps; actual request/retrieval timestamps stay in the
cache. Results remain dependent on the frozen response snapshot, not future API
contents. Preserve the cache when archiving the experiment.

## Local files

- `data/experiments/phase2a/sample.json`: fixed sample, selection reasons, Phase 1
  source/database hashes, and period population counts.
- `data/experiments/phase2a/results/<song_id>.json`: one restartable result per song,
  all scored candidates, decisions, full selected-entity metadata, and cache keys.
- `data/experiments/phase2a/matches.csv`: convenient summary export; nested metadata
  fields are JSON strings. The detailed per-song JSON is the experimental record.
- `data/experiments/phase2a/summary.json`: counts, coverage, request audit, code and
  source hashes.
- `data/cache/musicbrainz/requests/<request_hash>.json`: complete JSON response text,
  headers, status, URL/query, User-Agent, retrieval timestamps, and every attempt.
  `rate_state.json` preserves throttling across restarts; a lock prevents concurrency.
- `reports/phase2a_metadata_feasibility.md`: generated results; do not edit manually.

The experiment and cache directories are ignored by Git. They are separate from
the canonical Phase 1 database. Nothing from Phase 2A is to be committed or pushed
until the user approves the results and approach.

## Fixed sample

The sampling unit is a Billboard title/artist pair. Its period comes from its first
chart appearance, not its external release date. The periods have 29, 29, 29, 29,
28, 28, and 28 songs, respectively, from 1958–1969 through 2020–2026.

Within each period, sort by SHA-256 of `cmpt491-phase2a-v1` followed by the stable
song ID. Select one identity per first-appearance year, then two additional
identities for each available challenge category: featured credit, at least three
punctuation characters across title/artist, title shared by at least three source
identities, and unusual/long credit. Fill the remaining quota from the same hash
order, never selecting an identity twice. Category definitions are in `population`
in `src/phase2a.py`; flags can overlap. This is a balanced feasibility/stress sample,
not a proportional random sample suitable for population inference.

## Matching rule (`phase2a-strict-v1`)

Search with the full original title and artist credit, retrieving up to 100
candidates. If none agrees on title and full credit, try title plus the lead artist
name; this affects retrieval only, never the acceptance rule. Preserve both raw
searches. More than 100 results in either query blocks automatic selection.

Comparison uses NFC/casefold/whitespace cleanup, typographic quote/dash equivalence,
and (for artists) `featuring`/`feat.`/`ft.` and spaced `and`/`&` equivalence. It does
not strip punctuation, accents, version text, leading articles, or featured artists.
Original Billboard values and IDs are never changed.

Score = 50 × title similarity + 40 × full-credit similarity + 10 for a known first
release year no later than first-chart year + 1. Similarities use SequenceMatcher
on the comparison keys. The score ranks candidates; it is not calibrated confidence.
The one-year date tolerance is an experimental matching heuristic, not a COVID
breakpoint or inferred song-release date.

A high-confidence candidate must have exact title and full-credit comparison keys,
MusicBrainz search score at least 95, supporting release-year evidence, no unexpected
live/remix/demo/instrumental/karaoke/acoustic/edit/mono/stereo/remaster/re-recording
marker, and no video flag. Missing dates block acceptance. Recording lookup must
confirm this evidence.

There must be exactly one eligible recording and no other plausible rival: title
similarity at least .90, artist similarity at least .95, provider score at least 90,
no unexpected version/video flag, and no known late release year. Unknown dates on
a rival do not rule it out. Multiple valid recordings remain ambiguous even if
they probably describe the same Billboard asset. No manual overrides are used.

Statuses are `high_confidence`, `ambiguous`, `not_found` (both searches empty), and
`error` (search/recording lookup failed). Artist/release-group lookup failures are
reported separately without erasing a confirmed recording match. Missing cache
responses in offline mode are errors, not negative search results.

## Metadata and genre coverage

For accepted links, request the recording, credited artists, and up to three
earliest dated non-compilation release groups available in returned releases.
Preserve complete returned objects, including all raw genres/tags and counts.
This bounded retrieval does not claim an exhaustive release inventory or original
album identification. Artists and release groups provide context, not song genres.

Coverage is reported both among accepted matches and across the whole sample.
Raw recording genres, positive-vote recording genres, unrestricted tags, and
artist/release-group tags are measured separately. No genre taxonomy, assignments
from artist tags, or lyrical-content measurements are created.
