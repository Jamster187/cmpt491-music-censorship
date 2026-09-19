# Full-population LRCLIB corpus

The user approved the reviewed pilot and authorized acquisition for all 25,363
monthly-population assets. The automatic matcher is checked against the cached
200-song pilot before starting. No other provider, classifier, or historical
analysis is involved. LRCLIB inputs and caches remain private and ignored.

```bash
python3 src/lyrics_production.py gate
python3 -m unittest discover -s tests -v
python3 src/lyrics_production.py run
```

The gate must pass with the exact current code and review-ledger hashes. It
requires no observed false accepts, compatible selected texts compared with the
reviewed sources, and at least 145 automatically accepted assets. This threshold
is an engineering check on the development sample, not independent validation.
The [generated comparison](../reports/lyrics_production_pilot.md) measures automatic
performance separately from the manually reviewed pilot mappings.

## Deterministic acceptance

- Preserve exact Billboard identity and first-chart date. Matching normalization
  removes superficial case, accent, punctuation and spacing differences only.
  Compare complete artist credits; support featuring notation, reordered complete
  collaboration credits, explicit separators, provider NUL separators, and a
  trailing feature credit moved into the title. Do not infer missing guests or
  generalize the pilot's manually reviewed name aliases.
- Require compatible title and full artist credit. A title match with partial
  artist evidence is quarantined; unrelated candidates are rejected. Version
  descriptors are retained. Clean/dirty/explicit title suffixes can match the
  base title, with warnings. A song actually titled Clean remains that identity.
- A plain lyric is preferred. Timestamp-stripped synchronized text is a flagged
  fallback only when plain text is absent. Reuse LRCLIB-R's narrow formatting
  cleaner, preserving raw text hashes and cleaning operations. It never rewrites
  words, repairs encoding by guessing, reconstructs repetitions, or uncensors.
- Reject missing/instrumental or clearly malformed/severely corrupted texts.
  Quarantine texts under 60 words, with inadequate structure, substantial masking,
  mixed Latin/Cyrillic words, or suspected embedded non-lyric material. Shortness
  is uncertainty, not proof of truncation; legitimate short songs can be lost.
  Localized encoding noise and annotations can remain with warnings.
- Censorship markers are flagged; at least three markers or more than 0.5% of
  words triggers review. Five encoding markers or more than 2% triggers a bad-text
  grade. These are conservative heuristics, not measured transcription accuracy.
- Live/remix (including Remixes)/acoustic/demo/karaoke/medley alternatives do not
  supply an unmarked studio asset's text. A usable unflagged candidate can still
  establish that asset. Explicit/clean labels do not themselves reject text;
  source labels and text-mask warnings are retained separately.
- Multiple records are allowed. Distinct eligible texts must agree in sequence:
  token ratio at least 0.92 with no edit block over 12 tokens, or whitespace-free
  character ratio at least 0.97 with no edit block over 30 characters. Bag-of-words
  agreement never suffices. Substantial conflicts are quarantined. These rules
  intentionally lose some acceptable repetition differences from the pilot.
- Available high-confidence MusicBrainz durations and albums support selection.
  A safe duration must be within 15 seconds of at least one available duration;
  otherwise quarantine rather than forcing a recording identity. Within two
  seconds and matching album are preferences. Metadata is not required. First
  chart dates and release dates are retained as context, never equated or used
  to reject reissues. Selection is deterministic, ending with LRCLIB numeric ID.

`identity_confidence` and `text_quality` are separate from the final disposition.
`text_unassessed` is used when no target text has been selected/evaluated; it is
not mislabeled missing. Candidate-specific diagnostics are retained. A provisional
minor-noise text grade on a quarantined asset does not authorize classifier use.
Only an `accepted` result with a validated canonical file belongs to the corpus.
Version/text warnings include alternative-candidate evidence, so warning counts
are not counts of defective selected texts.

## State, concurrency, and resumption

`data/processed/lyrics.db` has separate `production_*` tables. Original pilot
`results`, `settings`, and review history remain unchanged. All 171 approved pilot
texts are carried forward without HTTP calls; the additional 59 are copied to
`data/lyrics/<song_id>.txt`. Original 112 canonical files are never overwritten.
The pilot's other 29 reviewed outcomes are also preserved. Automatic decisions
for new assets never depend on the manual pilot ledger.

Production freezes all 25,363 identities and the already available MusicBrainz
evidence from **read-only** queries to `research.db`. The connection closes before
network acquisition. No unified database import or metadata update is performed.
Code/source/review hashes, runtime, Unicode version, source URLs, candidate hashes,
retrieval times, selected metadata, cleaning, and decision evidence are persisted.
No raw lyric text appears in Git-tracked reports.

Each successful file is atomically written and fsynced before its per-song SQLite
commit. Interrupted writes are recovered deterministically from cached responses.
A different existing successful file is an integrity error, never overwritten.
The shared nonblocking `lyrics.lock` prevents simultaneous pilot/production writers.
SIGINT or SIGTERM finishes the current asset before stopping. Unexpected process
termination is recoverable using the same command. Already persisted results are
skipped, including terminal API errors unless explicitly retried:

```bash
python3 src/lyrics_production.py run
python3 src/lyrics_production.py run --retry-errors
python3 src/lyrics_production.py validate
python3 src/lyrics_production.py report
```

Retry-errors archives only failed final response cache entries; successful response
caches are reused. Historical HTTP attempts and replaced error decisions remain
local. The client identifies this academic project, sends requests sequentially,
waits an extra 500 ms, respects Retry-After including 503 responses, and retries
transient failures up to three times. It searches title+artist first and uses a
title-only fallback only when the initial response is empty, as in the pilot.
Returned search results may be capped by LRCLIB; this is recorded, not treated as
an exhaustive catalogue search. No expensive alternate-provider or fuzzy-query
campaign is attempted to force coverage.

After production begins, old pilot validators that demand exactly 112 canonical
files are historical commands. Use the production validator for the expanded
corpus. The standalone LRCLIB-R case ledger remains reproducible; its original
build command's old canonical-file validation no longer describes the corpus.
Do not rebuild `research.db` or run the original pilot import to fix this expected
sidecar separation. A later unified import requires a separate production-aware
migration after metadata writing has stopped.

The [status report](../reports/lyrics_production_status.md) contains all requested
periods and individual years. During a running acquisition, distinguish usable
coverage of attempted assets from usable coverage of the whole population.
The [startup review](../reports/lyrics_production_startup_review.json) records a
checksum-bound spot check of the first 20 automatic acceptances. It does not
replace automatic rules or require every future asset to be manually reviewed.
Run the exhaustive canonical-file validator when the worker is idle; while it is
writing, a file can briefly precede its manifest commit. Progress reports are
readable during the run, and the worker validates the corpus when it exits.
