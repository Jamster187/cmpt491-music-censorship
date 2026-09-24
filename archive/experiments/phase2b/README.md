# Phase 2B: alternative metadata pilot

Wikidata is the tested provider. Last.fm is the preferred direct tag lookup to
evaluate when academic access is arranged; Discogs was also researched. See the
[source decision](../../intermediate_reports/phase2b_source_research.md) and
[results](../../intermediate_reports/phase2b_metadata_feasibility.md).

## Reproduce

Python 3.9+ and the standard library are sufficient. From the repository root:

```bash
python3 src/phase2b.py run
python3 src/phase2b.py report
python3 -m unittest discover -s tests -v
```

The existing Phase 1 database and Phase 2A sample/results are prerequisites.
Phase 2B checks the frozen Phase 2A sample hash and copies its file byte-for-byte;
it does not draw another sample. There are exactly 200 identities with period
quotas 29, 29, 29, 29, 28, 28, 28. Period is first Billboard appearance, not release
year. The source and database hashes are checked before and after the run.

An interrupted run resumes with the same command, skipping completed songs.
`--limit 3` is a smoke test on the first three identities of that same sample.
The limit cannot exceed 200. Failed requests stay cached. After inspecting their
cause, `--retry-errors` explicitly retries song/API or optional metadata errors.
Three consecutive song errors stop a live run.

Replay decisions and rebuild the report with network access prohibited:

```bash
python3 src/phase2b.py run --offline --replay
python3 src/phase2b.py report
```

Retain the ignored Phase 2A sample/results and both provider caches in the local
experiment archive to reproduce this exact response snapshot. A new live run can
see different provider data. If regenerating Phase 1 on another Python/SQLite
version changes its file hash, retain the original snapshot for exact replay;
do not replace the frozen sample to work around the check. The Phase 2A sampling
code documents how its identities were originally selected.

## Files and provenance

- `data/experiments/phase2b/sample.json`: exact copy of Phase 2A's sample.
- `data/experiments/phase2b/results/<song_id>.json`: one checkpoint per identity,
  search/candidate evidence, decisions, selected item revisions, raw statements,
  artist/parent context and response-cache keys.
- `data/experiments/phase2b/summary.json` and `matches.csv`: reproducible summaries.
  The JSON records, not the compact CSV, hold the complete evidence.
- `data/cache/wikidata/requests/<hash>.json`: request parameters, identifying
  User-Agent, headers, complete JSON response text, timestamps and every attempt.
  Gzip bodies are decompressed before storage and checksum calculation.
- `archive/intermediate_reports/phase2b_metadata_feasibility.md`: generated report; do not edit by hand.

Cache and experimental outputs are ignored by Git. A lock allows only one client;
request spacing of at least 1.1 seconds survives restarts. Requests use `maxlag=5`,
gzip, Retry-After and exponential backoff. HTTP-200 API errors remain errors.
Entity lookups are batched in groups of at most 50, and the earliest cached entity
revision is reused across batches and restarts. Body checksums are verified before
use. No credentials are required or stored. No Phase 1 or Phase 2A data is modified.

## Matching rule: `phase2b-wikidata-asset-v1`

1. Query Wikidata text search with quoted title and full artist credit (up to 20
   hits). Also query entity-label search with the title (up to 50 hits), retaining
   exact title label/alias hits for entity lookup. Cache both complete searches.
2. Compare title against returned English/language-neutral labels and aliases,
   and explicit title statements. Use the Phase 2A comparison normalization:
   NFC, casefold, whitespace cleanup and typographic quote/dash equivalence.
   Preserve punctuation, accents and version descriptors.
3. Check all non-deprecated performer statements. Match the entire Billboard
   credit against performer labels/aliases, permitting standard credit separators
   (`featuring`/`feat.`/`ft.`, `and`/`&`, `with`, commas, slash, `x`, `vs`, `+`).
   Whole ensemble names are tested intact; every performer must match and every
   part of the credit must be consumed. No missing guest is silently dropped.
4. Require a supported song, single, audio-track, musical-composition or recording
   type, directly or through up to four subclass links. Retain that path. Missing
   types, unknown performers and unexpected explicit remix/remaster/live-recording
   descriptors do not pass. Album-only matches do not pass.
5. Accept all qualifying items if their performer-ID sets agree. These are several
   associations for one Billboard asset, not one selected recording or a merge of
   provider entities. Competing same-name **different artist IDs** stay ambiguous.
   A work listing additional cover performers cannot supply accepted metadata to
   a single-performer asset merely because its title agrees.

Score = 50 × title similarity + 45 for a complete credit match (20 for partial
performer-name evidence) + 5 for a supported item type. Acceptance requires the
explicit checks, not a score threshold; scores are not probabilities. Publication
dates are supporting audit evidence, not mandatory. Later dates remain flagged
because they can describe an edition or a distinct release.

Capped retrieval remains visible. Without an eligible candidate, an incomplete
search stays ambiguous; an observed exact full-credit/type match can still be
accepted. This does not guarantee that no unobserved homonym exists. It differs
from Phase 2A's recording-uniqueness rule, so the comparison measures the combined
provider/matcher approach rather than isolating a provider effect.

Statuses: `high_confidence`, `ambiguous`, `not_found`, `error`. Candidate-found is a
retrieval measure and may include album or incomplete-credit candidates. The report
also gives song-candidate-found and accepted coverage; only accepted links count
toward metadata yield. Missing API responses never count as not-found.

## Metadata scope

Raw genres retain their Wikidata IDs and exact returned labels plus the full
statement, entity revision/type, qualifiers, references and rank. Deprecated and
qualified claims are preserved. Coverage counts non-deprecated value statements
and separately reports unqualified/referenced statements. These are genres of
Wikidata song/work/single/track items, not verified recording-level classifications.
Wikidata has no comparable free-form track-tag endpoint.

The report also separates genre evidence by supported recording/track, single,
composition and generic-song types. These counts can overlap; they are not a
final genre taxonomy. Current annotations describe historical assets as cataloged
now, not necessarily how those assets were described when they first charted.

Artist and parent-album genres remain contextual. Parent links count as album
context only with an album type or a type whose English label ends in “album”.
All other parent relations remain in the detailed record. Publication dates retain
precision and calendar; durations retain amount and unit. External IDs, composers,
producers, labels and work language remain available when returned. The client
does not follow lyrics links or collect audio.

Phase 2B code and reports must remain uncommitted until the user reviews the
results and approves the approach. No full enrichment, final genre taxonomy,
lyrical classifier, COVID breakpoint or statistical analysis is authorized here.
