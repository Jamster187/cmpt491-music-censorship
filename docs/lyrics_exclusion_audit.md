# Diagnostic exclusion review

This task audits existing LRCLIB exclusions only. It does not approve new mappings,
change acquisition/matching/cleaning code, modify accepted lyrics, or run a
classifier. Read the [generated report](../reports/lyrics_exclusion_audit.md),
[local per-asset categories](../data/processed/lyrics_exclusion_categories.csv), and
[review ledger](../reports/lyrics_exclusion_review.json).

## Reproduce

```bash
python3 src/lyrics_exclusion_audit.py
python3 -m unittest discover -s tests -v
python3 src/lyrics_production.py validate
python3 src/research.py validate
python3 src/phase1.py validate
```

The audit opens SQLite with `mode=ro`, verifies cache envelopes against retrieval
hashes and candidate objects against persisted candidate hashes, and emits only
metadata/aggregate reports. Its per-asset CSV and detailed local census are ignored under
`data/processed/`. The manually authored diagnostic review ledger contains no
lyrics and binds its 360 stratified cases to immutable evidence hashes. Never
hand-edit the generated Markdown or CSV. The audit has no HTTP client entry point.

All 5,991 non-accepted records receive primary/secondary categories; all 3,519
quarantined records are covered. Text/version blockers are evaluated on
identity-compatible candidates; warnings on unrelated alternatives cannot be
used as the reason for an asset's exclusion. For the 2,332 disagreement cases,
every eligible, quality-screened candidate text is examined structurally rather
than stopping at the matcher's first failing pair. These structural categories
are for sampling, not proposed automatic acceptance.

The artist-syntax probe is an in-memory counterfactual restricted to 90 flagged
quarantined cases. It changes explicit separator/punctuation interpretation,
then invokes the unchanged pure production matcher. It cannot write dispositions
or files. Its 44 passing cases plus five individually inspected contextual false
alarms form a 49-asset low-risk shortlist. That is a diagnostic finding, not a
production override ledger. Name aliases, absent guests, and general title-prefix
matches are not part of this syntax rule.

## Limits and interpretation

One assistant reviewer examined metadata, text boundaries, flagged text locations,
lengths and sequence differences. There was no listening, external source
confirmation, independent reviewer, or full transcription certification. The
review identifies promising deterministic rule families, genuine conflicts, and
cases needing manual evidence. It cannot measure a false-match rate for a
second-pass matcher that has not been implemented. The pilot is a development
set, not an independent precision benchmark.

The conditional estimate expands the sampled possible-rule fraction within each
quarantine stratum after removing all 49 enumerated low-risk assets. It estimates
roughly 2,066 additional promising cases. It is **not** a forecast of validated
acceptance and **not** a claim that 2,066 texts can already be safely promoted.
Sampling uncertainty, subjective boundary judgments, and correlated provider
transcriptions limit it. No retry or alternate-query successes are assumed.
With only half of the conditional queue eventually passing, coverage would be
about 80.65%, rather than the full scenario's 84.72%.

Bias projections apply the same stratum yield across demographics; those
within-stratum yields are not independently estimated by period or rank. The
additive decomposition of observed missingness is exact and descriptive.
Quarantine accounts for about 55% of the simple/complex credit coverage gap but
only about 13–14% of the popularity/longevity gaps. The 49-case shortlist alone
has little overall effect; broader text recovery can reduce the modern-period
gap while widening the earliest-versus-modern coverage gap.

## Validation record

- Full suite: **164 tests passed**, including nine synthetic audit regressions.
- Production lyrics validator: **19,372** canonical files, exact reconciliation.
- Standard unified validator and Phase 1 validator: passed; **355,487** weekly
  observations, **81,800** monthly observations, **818** baskets, and **25,363**
  study IDs retained. Manifest counts still match all six acquisition dispositions.
- All **19,372** canonical file hashes equal the pre-audit snapshot. Whole-file
  hashes of `music.db`, `research.db`, and `lyrics.db` are unchanged. Original
  source checksum still matches Phase 1 validation. The exhaustive audit verifies
  all non-accepted cached retrieval and candidate checksums without rewriting them.
- Matcher and cleaner hashes remain unchanged; no acquisition logic was edited.
- Cached 200-song development pilot: syntax probe accepts **153** versus the
  original automatic **154**, with **zero** accepts among the 29 reviewed
  exclusions. *Party To Damascus* becomes ambiguous when an additional full-credit
  candidate participates. No existing accepted disposition or file was touched.
  This is regression evidence, not independent precision measurement.
- No acquisition workers remain. No lyric files, caches, generated databases,
  private review packets, or per-asset exports are tracked. No classifier result
  tables/files were found or created.

No changes to canonical lyrics, dispositions, cache responses, source chart data,
metadata state, or the synchronized unified lyrics manifest are authorized here.

## Next authorized decision

Recommendation **C**: authorize a focused, separately versioned second-pass
matcher and an independent precision review before bulk use. Start with the
explicit syntax cases and contextual false positives; evaluate text-agreement,
formatting and version rules against held-out positive and hard negative cases.
Maintain all original records and compare proposed decisions without promotion.
Do not use majority voting, the longest text alone, universal guest removal,
blanket remix rejection/acceptance, or synthetic uncensoring. This audit stops
before implementing that pass or changing any production disposition.
