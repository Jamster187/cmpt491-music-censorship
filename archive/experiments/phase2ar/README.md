# Phase 2A-R: MusicBrainz asset-level replay

This experiment reuses exactly the 200 Phase 2A Billboard identities and its frozen
MusicBrainz cache. It matches title/artist assets, allowing several recording IDs
to support one asset. It does not select a canonical recording or change Phase 1,
Phase 2A, or Phase 2B. No API client is used and no credentials are needed.

## Run

From the repository root, with Python 3.9+ and the original local caches present:

```bash
python3 src/phase2ar.py
python3 -m unittest discover -s tests -v
python3 src/phase1.py validate
```

Required inputs are `data/processed/music.db`, the Phase 2A sample and result files,
`data/cache/musicbrainz/requests/`, and the existing Phase 2B results/summary for
comparison. A fresh Git clone does not include those ignored caches: retain the
frozen experiment archive to reproduce the numbers. This runner never falls back
to network requests. Missing or corrupt inputs fail explicitly.

The database is opened read-only. Every sample identity and first-chart date is
checked against a fresh `MIN(chart_date)` query. Cached URL/body checksums and
lookup IDs are validated. Original raw candidate objects, every supporting ID,
release/group details, full credits, dates, raw tags/genres, retrieval timestamps,
and cache references are retained. Detailed lookups already cached for other
sample assets can be reused only by the same linked entity ID.

Outputs are isolated under ignored `data/experiments/phase2ar/`: an exact sample
copy, one JSON result per asset, `summary.json`, and `review_sample.json`. Each
file is published by atomic replacement; interrupted runs can safely be rerun.
The short offline computation is replayed, so stale decisions are never skipped.
There are no processing timestamps. Identical frozen inputs/code produce identical
outputs. Reports are generated at `archive/intermediate_reports/phase2ar_metadata_feasibility.md` and
`archive/intermediate_reports/phase2ar_review.md`; qualitative review notes are maintained separately.

## Matching rule: phase2ar-asset-v1

Original Billboard identities and credits are untouched. Matching uses:

- **Title:** NFC Unicode normalization, casefold, collapsed whitespace, typographic
  apostrophe/dash equivalence. Apostrophes/full stops are removed; commas, colons,
  semicolons, dashes, and quotation marks become word separators. Other symbols,
  parentheses, numbers, wording, and version text remain. There is no fuzzy title
  threshold, translation, substring matching, or removal of title suffixes.
- **Artist:** the same rules, plus Latin accent folding; `&`, `and`, `feat.`, `ft.`,
  and `featuring` equivalence; optional `the` at the start or after an `and`
  separator. Structured artist names also allow `with`/`and` at contributor
  boundaries, with optional articles. Names remain in order and no contributor
  can be dropped. Arbitrary aliases, lead-artist-only matches, and rearrangements
  are not accepted. Group credits represented as one entity are allowed when the
  complete displayed credit matches. Symbolic names such as `P!nk` remain distinct.
- **Artist IDs:** all credited structured artists must have IDs. Compatible
  candidates must agree on one set of artist IDs. Homonymous IDs remain ambiguous,
  even if one has an earlier release. Text normalization never merges Phase 1 rows.
- **Time:** at least one compatible recording must expose a valid recording first
  release, release date, or release-group first release no later than first-chart
  year + 1. This retains Phase 2A's explicit experimental tolerance. Year/month-only
  dates remain intervals; before/on-chart, overlapping, later-in-year, following
  year, and later evidence are recorded separately. Later reissues and undated
  recordings may then support that same asset. Late-only identities remain
  ambiguous, not declared impossible. Cached artist birth/formation after the
  chart year + 1 is negative evidence; no new biography requests are made.
- **Versions:** live/remix/demo/instrumental/karaoke/acoustic/re-recording/video and
  DJ-mix markers cannot silently supply support. Unknown disambiguation text is
  also excluded conservatively. The explicit allowed descriptor list covers
  clean/explicit, original/album/single/main versions, radio/single edits,
  mono/stereo, remasters, Dolby Atmos, 5.1, DTS 6.1, and 360 Reality Audio mixes.
  Recognized clean/explicit variants support asset identity but require future
  content-version resolution. No duration is selected or averaged.

The matcher is an evidence gate, not a calibrated probability score. MusicBrainz
search relevance is retained for audit but is not an identity threshold. A
truncated search is flagged; a complete compatible asset with an anchor can still
be accepted without claiming the returned recordings exhaust the catalogue.

Statuses are `high_confidence`, `ambiguous`, and `not_found` (zero candidates in
the original searches only). Supporting multiple recordings sets
`canonical_recording_status=unresolved_multiple`; one observed recording is not
proof of catalogue uniqueness. Disagreement between cached identity variants
blocks acceptance. Raw candidates are retained even when excluded.

All newly accepted assets, rather than a chosen subset of 40, form the review
packet in deterministic hash order. Weak dates, truncated searches, normalization,
content versions, and duration outliers are explicit review flags. Durations below
45 seconds or above 15 minutes are flagged for inspection only; this is not a
final exclusion rule or an invented corrected value.

## Metadata interpretation

Coverage means at least one supporting cached value. Conflicting values and
editions remain separate. Album includes compilation context; no earliest date
is asserted to be the original release. Recording, release-group, and artist
genres/tags are distinct. Nothing is mapped to a final genre taxonomy.

Phase 2A requested full entity lookups only for accepted matches. Search responses
often contain tags without structured genres. Newly recovered entities lacking
lookups have unknown genre availability, not verified missing genres. The report
shows lookup availability alongside observed coverage so these denominators are
visible. Wikidata's various song/single/composition genre scopes are not equivalent
to MusicBrainz recording genres.

The feasibility results and review must be approved before committing this
experiment. They do not authorize full enrichment, lyrics collection, or analysis.
