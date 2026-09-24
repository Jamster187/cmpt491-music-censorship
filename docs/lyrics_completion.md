# Finishing the original LRCLIB acquisition

This continuation was explicitly authorized after the accepted post-run audit.
It addresses the 3,717 unattempted members of the existing 25,363-asset study
population. All earlier dispositions are frozen; there is no quarantine review,
manual rescue, classifier, new sampling rule, or changed acceptance methodology.

## Timing fix and provenance

The old client checked the cooldown with one clock read and calculated the sleep
with a second. The deadline could pass between them. The smallest fix calculates
remaining time once per loop and sleeps only if positive. Retry-After handling,
500 ms extra delay, bounded retries, searches and matching rules are unchanged.
A synthetic advancing-clock regression reproduces the exact deadline crossing.

Original bundle:
`e82352325fa3efc854819458c10c79a14902175303d556656b2247cbfaeecb42`.
Resumed bundle:
`931073fded92dcdcf3a78272a1f4b6fcf1636c3c1cd17b22b70680d552f015b4`.
The matcher remains `lrclib-production-v1`; matcher/cleaner source hashes are
unchanged. The 200-song cached replay retains exactly the same per-case decisions:
154 automatic acceptances, zero false accepts against reviewed exclusions, 182
exact disposition agreements, and zero incompatible selected sources. No requests
were made by the replay.

The explicit offline transition backed up `lyrics.db` and bound all 21,646 existing
result payload hashes to the original implementation without rewriting them.
Original settings and pilot gate remain retained. New results carry their bundle
hash and run ID. A normal resume skips all prior statuses, including errors; tests
cover that behavior. The baseline checksum ledger protects all 16,572 original
lyrics plus existing cached evidence and chart inputs. It contains 66,083 paths
and is stored only under ignored `data/processed/`.

Commands used for the continuation:

```bash
python3 src/lyrics_production.py gate
python3 -m unittest discover -s tests -v
python3 src/lyrics_resume.py
python3 -u src/lyrics_production.py run
```

The run began at 2026-09-20 19:55:20 UTC. Its separate ignored log is
`data/cache/lrclib/completion-run.log`; existing logs and evidence remain intact.
HTTP 503 failures are retried under the original policy and, if terminal, become
explicit API-error dispositions. They are not relabeled not found.

## Consolidation and final checks

After the worker finished all study assets, the production-aware importer and
final checks were executed:

```bash
python3 src/lyrics_import.py
python3 src/research.py validate
python3 src/lyrics_production.py validate
python3 src/phase1.py validate
python3 src/lyrics_completion_check.py --manifest-synchronized
python3 -m unittest discover -s tests -v
python3 src/research_report.py
python3 src/post_run_audit.py --output archive/intermediate_reports/lyrics_completion_audit.md --decisions ../docs/lyrics_completion.md
```

It builds a temporary research copy, extends the manifest status constraint to
retain all production dispositions, imports metadata/path references only, and
runs standard validation before atomic publication. The pre-import research file
is backed up. The importer checks that re-import is idempotent and will not
replace a conflicting success. Unknown schemas, incomplete populations or identity
drift fail explicitly. No lyric text or cache body is copied into the database.
The complete sidecar remains the detailed evidence store.

The final suite passes 155 tests, including exact status retention, file
reconciliation, identity checks, rollback, no text copying, idempotence, and
refusal to call an incomplete or running population complete.

## Completed run and corpus

The worker ended with `completed` at **2026-09-20 21:52:59 UTC**, after **117.66
minutes**, 5,112 requests and exactly **3,717 new dispositions**. The original
21,646 dispositions were not retried or overwritten. The added outcomes were
2,800 accepted, 520 quarantined, 184 wrong identity, 25 bad/missing text, 137 not
found, and 51 API errors. Every terminal API error was HTTP 503 after the unchanged
bounded retry policy; errors are separate from missing candidates. No quarantine,
wrong-identity or not-found case was manually rescued.

| Final disposition | Assets |
|---|---:|
| Total population / dispositioned | 25,363 / 25,363 |
| Usable | 19,372 |
| Quarantined | 3,519 |
| Wrong identity | 1,365 |
| Bad/missing text | 184 |
| Not found | 872 |
| API errors | 51 |
| Unprocessed | 0 |

Usable coverage is **76.38%**. All **19,372 canonical local files** reconcile with
the sidecar and synchronized research manifest. See the [generated final audit](../archive/intermediate_reports/lyrics_completion_audit.md)
for periods, every first-chart year, metadata fields, descriptive missingness and
persisted runs; the [production report](../archive/intermediate_reports/lyrics_production_status.md)
retains detailed loss/warning counts.

All 21,646 pre-resume result payloads retain their hashes. All 66,083 protected
baseline paths retain their hashes, with the original research file checked via
its checksum-bound pre-import backup after publication. This includes all 16,572
original canonical lyrics and existing cached evidence. The final preservation
check also reconciles every non-lyrics research table against that backup in both
directions. No metadata, source identity, chart row or study membership changed.

The standard published `research.py validate` now passes, as do production lyrics
validation, Phase 1 validation, the complete test suite and the final audit's
independent monthly reconstruction, SQLite checks, file/evidence checksums and
cache-envelope checks. Re-import is deterministic and idempotent. Schema 2 retains
all six production outcomes distinctly (`accepted` becomes `success`); no blocked
or unattempted manifest rows remain. The downloader still never writes the
research database; the explicit separate importer performs synchronization.

No raw lyric text or cache body was copied into `research.db`. Generated databases,
lyrics, caches and the checksum ledger remain ignored; none is committed to Git.
No classifier results, content scores or COVID hypothesis test were produced.

## Missingness remains descriptive and systematic

The earlier pattern remains after removing the unfinished queue from the picture:

- Weekly Top-10 peak assets have **84.30%** usable coverage versus **70.97%** for
  peaks 41–100.
- Assets selected in 7+ monthly baskets have **87.12%** coverage versus **69.32%**
  for those selected in one month.
- Credits containing collaboration-like separators have **63.91%** coverage versus
  **79.31%** without them. This is a text heuristic, not a person/act count; band
  names can contain separators.
- Historical coverage ranges from **71.21%** in 1958–1969 to **82.85%** in
  2010–2019. Coverage is **82.81%** for 2015–2019 and **79.99%** for 2020–2026.
  These are first-chart cohorts, not release years or a COVID effect estimate.

Popularity, longevity, credit complexity and historical period therefore still
matter for corpus availability. These are unadjusted descriptive associations,
not causal or hypothesis-test results. Precision-first identity, version and text
quality exclusions remain in place. Metadata remains optional enrichment. This
completion task ends before classifier design.
