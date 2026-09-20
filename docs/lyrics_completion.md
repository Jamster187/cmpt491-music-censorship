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

The production-aware importer is tested and is to be run only after the worker
has finished all study assets:

```bash
python3 src/lyrics_import.py
python3 src/research.py validate
python3 src/lyrics_production.py validate
python3 src/phase1.py validate
python3 src/lyrics_completion_check.py --manifest-synchronized
python3 -m unittest discover -s tests -v
python3 src/research_report.py
python3 src/post_run_audit.py --output reports/lyrics_completion_audit.md --decisions ../docs/lyrics_completion.md
```

It builds a temporary research copy, extends the manifest status constraint to
retain all production dispositions, imports metadata/path references only, and
runs standard validation before atomic publication. The pre-import research file
is backed up. The importer checks that re-import is idempotent and will not
replace a conflicting success. Unknown schemas, incomplete populations or identity
drift fail explicitly. No lyric text or cache body is copied into the database.
The complete sidecar remains the detailed evidence store.

The initial consolidation and completion-check suite passes 155 tests, including exact status
retention, file reconciliation, identity checks, rollback, no text copying, and
idempotence. Final execution results and corpus coverage will be recorded after
acquisition completes; this section does not claim that import has already run.
