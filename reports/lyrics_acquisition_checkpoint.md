# Lyrics acquisition checkpoint — Codex B

Reviewed 2026-09-19. **Outcome B: acquisition remains blocked by unresolved
underlying-content permission.** LRCLIB is the preferred technical candidate;
no source has been selected for acquisition. No pilot or full-corpus lyrics
requests were made. This is not a claim that LRCLIB prohibits academic analysis.

## Existing infrastructure and exact previous blocker

Read `AGENTS.md`, `README.md`, `docs/research_database.md`, both existing lyrics
assessments, `src/lyrics_plan.py`, and its tests before pursuing acquisition.
The planner selects 200 deterministic study assets, covers every first-chart year,
and preserves the frozen selection. It contains no acquisition client. The unified
database already has the required identity, path, hash, provenance, status, and
pilot structures. No replacement sample, matcher, or database was created.

The previous assessment accepted automated API access and offline local downloads.
Its blocker was the absence of an established basis for retaining and processing
the underlying lyrics in this research corpus. Neither metadata enrichment nor
recording-level identification caused the block.

## New primary-source findings

The earlier browser could not render the dump page. This review inspected the
JavaScript actually served by [LRCLIB](https://lrclib.net/db-dumps):
[`index-a8f56a9e.js`](https://lrclib.net/assets/index-a8f56a9e.js), SHA-256
`794ec905e50880622614fcd68e2fd3b47c878feb6d911793ebc321539b1a3973`.
Documentation assets were read in memory; they were not saved as corpus files.

| Question | Finding and classification |
|---|---|
| Automated access | Explicitly supported: public API for applications, no registration/key. This is affirmative service-use evidence. |
| Batch use | Explicitly contemplated in API guidance for full-library scans. No published fixed request quota or 25,363-asset ceiling was found. |
| Local storage | Official [LRCGET](https://github.com/tranxuanthang/lrcget) and offered database dumps support downloading and retaining local copies. This is stronger evidence than technical accessibility alone. No research-specific retention deadline was found. |
| Rate behavior | [Current docs](https://lrclib.net/docs) require an identifying application name/version and project URL or email; sequential requests, an additional 200–500 ms delay, and honoring HTTP 429/Retry-After. The delay is guidance, not a numeric quota. This resolves the follow-up report's inability to verify that delay. |
| Title/artist lookup | Current `/api/get` requires title and artist; album and duration are optional aids. `/api/search` supports structured title/artist queries, returns at most 20 results, and has no pagination. Metadata enrichment is unnecessary. |
| Offline availability | The actual dump page fetches a JSON object list from the [listing endpoint](https://lrclib-db-dumps.bu3nnyut4y9jfkdg.workers.dev), then constructs download links under `https://db-dumps.lrclib.net/`. The listing returned HTTP 403 to this environment; the research browser also failed. No current filename, size, snapshot date, or completeness was established; no dump was downloaded. This does not prove global unavailability or a prohibition. |
| Dump terms | The inspected dump component contains a file listing, sizes, upload times, and download links, but no content-license statement. An unavailable listing is not evidence of terms granting or denying research use. |
| Underlying content | Unclear: no adopted content grant establishing this research use was found. Repository MIT licensing applies to software. The website's CC0 statement applies to the Lyricsfile specification/documentation, not the lyrics catalogue. |
| Provenance | Anonymous contributions are documented by `/api/publish`. The maintainer also confirms non-public external-provider implementations in [discussion #53](https://github.com/tranxuanthang/lrclib/discussions/53), citing DMCA concerns. Thus community submission is not an adequate description of all upstream provenance, and publisher authorization was not established. |
| Maintainer permission | The same discussion supports commercial service use subject to client identification. It does not establish rights to third-party content. This is positive service-use evidence, not a blanket research-content license. |
| Adopted legal policy | [PR #74](https://github.com/tranxuanthang/lrclib/pull/74) is still open/unmerged. [Issue #111](https://github.com/tranxuanthang/lrclib/issues/111) has no maintainer answer establishing a content license; commenters' speculation is not policy. |
| Private computational processing and numerical publication | No prohibition was found, but the underlying-content basis remains unclear. Absence of a research-specific clause alone is not the blocker: broad applicable permission could suffice. Here the software/service permissions do not resolve the catalogue's third-party content rights. |

No new verified entitlement for Musixmatch, LyricFind, or Genius was established.
The [prior comparison](lyrics_permissions_followup.md) remains applicable: licensed
provider arrangements are possible, but none is available to this project. No
provider was contacted. No website scraping or access-control bypass was attempted.

## Decision

The project instruction says to stop if suitable permissions/access cannot be
established. The narrow unresolved requirement is an applicable basis covering the
underlying lyrics for private local retention and computational research. A
provider clarification identifying any separate rightsholder requirements, or an
institutionally assessed legal basis, could resolve it. A special contract naming
exactly 25,363 songs is not asserted to be universally required. The existing
[draft inquiry](lyrics_permissions_followup.md#concrete-way-to-resolve-the-blocker)
can be used; this session was not authorized to send it.

If resolved, use the frozen pilot with title/artist matching. Prefer an accessible,
dated official dump for local matching when its size and freshness are practical;
otherwise use the documented API. Review alternate texts, missing collaborators,
covers, medleys, live/remix and clean/explicit variants before accepting files.
An API search returning 20 candidates must retain a possible-truncation flag.
Nothing in this report requires recording-level metadata as a prerequisite.

## Pilot and full-corpus status

Read-only database inspection found 200 pilot members and 25,363 manifest rows,
all `blocked_source_access`. Pilot attempted **0/200**; successful, ambiguous,
not found, and retrieval errors **0 each**. Full acquisition has **not started**:
attempted **0/25,363**, successful, ambiguous, not found, and retrieval errors
**0 each**. The dump-listing 403 is a source-research failure, not a song retrieval
error. Overall acquired coverage is **0%**; provider coverage is unmeasured.

Counts below use first Billboard chart year, not release year. The 2015–2019 row
overlaps 2010–2019 and must not be added to the period totals.

| First-chart period | Study assets | Frozen pilot assets | Pilot successes | Corpus successes | Acquired coverage |
|---|---:|---:|---:|---:|---:|
| 1958–1969 | 5,863 | 29 | 0 | 0 | 0% |
| 1970s | 4,364 | 29 | 0 | 0 | 0% |
| 1980s | 3,786 | 29 | 0 | 0 | 0% |
| 1990s | 3,053 | 29 | 0 | 0 | 0% |
| 2000s | 2,911 | 28 | 0 | 0 | 0% |
| 2010–2019 | 2,997 | 28 | 0 | 0 | 0% |
| 2015–2019 | 1,553 | 8 | 0 | 0 | 0% |
| 2020–2026 | 2,389 | 28 | 0 | 0 | 0% |

Matching quality, ambiguity rates, missingness, and modern/historical source
coverage cannot be evaluated without retrieval. There is no corpus to judge
suitable for classifier design. No content inspection or classifier work occurred.

## Storage, concurrency, and resume

- Intended corpus: `data/lyrics/<song_id>.txt`; directory does not yet exist.
- Existing manifest: `data/processed/research.db`, table `lyrics_manifest`.
- Existing frozen sample: table `lyrics_pilot` and `data/processed/lyrics_pilot.json`.
- Verified `git check-ignore -v` covers `data/lyrics/`, `data/cache/`, and
  `data/processed/`; `git ls-files` found no tracked files under those paths.
- Observed active metadata process PID 42837. All project-database inspection used
  SQLite `mode=ro`, short queries, and closed connections. No database writes,
  rebuilds, metadata edits, process signals, or generated-state updates occurred.
- Future acquisition should use `data/processed/lyrics.db` while metadata writes
  continue, followed by a validated deterministic import. This is not implemented
  because no source passed the acquisition gate.
- **Resume command: none exists for acquisition.** `src/lyrics_plan.py` only
  prepares a sample and writes planning status; do not mistake it for a downloader
  or rerun it against the concurrently active database. Resolve the content basis
  first, then implement the selected source using the existing sample/manifest.

Only this new assessment is intended for the Codex B checkpoint. Earlier reports
are preserved as historical assessments; no data semantics or rebuild commands
changed.

Validation: `python3 -m unittest discover -s tests -v` passed all 106 tests.
A separate read-only check reconciled the frozen SQLite pilot and existing JSON
against `lyrics_plan.select` and verified zero canonical lyrics files with
`validate_lyrics_files`. No source-processing behavior changed, so no generated
quality report was regenerated.
