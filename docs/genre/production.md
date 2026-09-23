# Frozen primary-genre production

The approved 300-song pilot is being extended to the final 28,041-song population.
This produces model-derived genres, not ground truth. Public datasets remain unchanged.

## Frozen inference

Use `gpt-5.5`, medium reasoning, Codex CLI 0.155.1 and the exact prompt, schema,
input preparation and taxonomy from commit `0514c2cdd1a3f52b9fe5cca704fe88a0d68c961e`.
The runner checks those files against the commit before inference. The CLI model
alias does not identify an immutable checkpoint; exact future replication is not
guaranteed. No temperature or seed setting is exposed by this interface.

Inputs contain only exact identity, first chart date and screened existing raw
genre evidence, preserving provider and semantic level. They exclude chart
performance tags, content scores and earlier genre decisions. All 300 pilot inputs
were checked against the frozen evidence, allowing their approved results to be
reused. The remaining 27,741 identities are ordered by a fixed song-ID hash and
batched in tens (2,775 new requests). Every request has its own empty working
directory, ephemeral session and disabled tools, web, memory and project context.
The prompt/schema are never changed in response to production labels.

## Access and billing

Production uses the existing **ChatGPT-authenticated Codex CLI**, as the pilot did.
The runner refuses API-key or endpoint overrides, requires that authentication
mode, and has no API fallback. Subscription usage limits still apply. The earlier
API-equivalent dollar estimate is not a charge estimate for this execution path.
A quota/access failure stops the worker for inspection.

## Commands and storage

```sh
python3 src/genre_production.py prepare
python3 src/genre_production.py run
python3 src/genre_production.py status
python3 src/genre_production.py validate
```

Results are incrementally committed to ignored `data/processed/genre_results.db`.
Exact inputs, request hashes, immutable successful labels, failures and attempts
are retained. Private request/response logs and progress/completion JSON are in
`data/experiments/genre_production/`. Completed batches are skipped; a complete
saved response from an interrupted attempt is recovered without inference.
Malformed responses are retried only for unresolved songs; previously completed
rows remain unchanged. Each subset request retains its exact input list, hash and
runner/model configuration in a private manifest. Only one worker holds the lock.

After stopping a worker, confirm its Codex child has also exited before resuming.
Inspect errors before using `python3 src/genre_production.py run --retry-errors`.
This retries unresolved songs from failed batches with unchanged individual inputs
and preserves successful rows. It does not bypass a quality stop. Do not introduce a separately billed API
fallback to resolve access limits.

## Monitoring and completion

After each batch, persist counts by genre, confidence and historical period.
Recent windows of 200 new results stop production if one genre reaches 80%, Other
reaches 50%, low confidence reaches 60%, or a confidence share changes by 40
percentage points versus the preceding 200. These are coarse operational alarms,
not evidence that smaller changes are necessarily errors. Malformed/schema-invalid responses receive bounded retries. Two failures for an
exact unresolved subset trigger single-song fallback, also limited to two failures
per song. Retry budgets persist across interruptions. Exhausted songs retain errors
while other batches continue; they are never assigned guessed labels. Ten malformed
responses among the last 20 requests stop the run as a possible systemic problem.
Unexpected tool calls or unrecognized transport failures still stop for inspection. Individually
valid rows with exact unique requested IDs survive another row's schema failure;
duplicate or foreign IDs are never repaired, mapped by position or accepted.

Inference completion requires all 28,041 rows to pass the frozen output validator.
A completion marker explicitly leaves qualitative review pending. Before dataset
publication, rerun the protected-file validator and full tests, then perform a
bounded deterministic review spanning confidence levels, genres and periods.
Do not manually overwrite labels during review. Confidence is qualitative;
secondary genres are provisional. No public master rebuild is part of this run.

The read-only `python3 src/genre_production_audit.py` command regenerates the
aggregate checkpoint report. Once inference is complete, it also creates a local
160-song review template: two per available genre, 15 per confidence level, five
per historical period, then hash-fills the union to 160. Selection is deterministic
and includes rare genres. It never assigns review judgments or changes labels.

### Transport interruption recovery

A 2026-09-22 interruption exposed a CLI event-handling false positive: the exact
notice `Falling back from WebSockets to HTTPS transport. request timed out` was
classified as tool use. The runner now permits that transport notice only when
normal completed-turn and response validation also succeed. Real tool events
remain rejected. A saved response rejected for the old event error can be
recovered by `run --retry-errors`, without another inference request; successful
rows are never overwritten. The original error stays in the attempt audit trail.
This changes transport handling, not the frozen genre methodology.

Batch 1591 stopped on a model-capacity rejection with no response or completed
turn. Exact `Selected model is at capacity. Please try a different model.` failures
now receive bounded retries on the same model: at most three capacity failures per
exact requested subset, with 30- and 60-second backoffs. Attempts and retry budgets
persist across restarts. Only unresolved IDs are requested. This narrow exception
requires no saved response and no tool or other unexpected events; unknown runtime,
quota and authentication errors still stop for inspection. Capacity exhaustion also
stops for inspection, without falling back to another model or billing path.

## Final audit

Production completed all 28,041 identities. See the [final audit](../../reports/genre_final_audit.md) and its [160 authored review judgments](../../reports/genre_final_audit/review.csv). The original completion marker remains untouched and records that qualitative review was pending at inference completion; the separate final audit records its later completion.

Regenerate the final audit with `python3 src/genre_final_audit.py` after running the full tests into `data/experiments/genre_production/final_tests.log`. The audit reconciles exact response provenance, the frozen configuration, all protected file hashes and the deterministic review membership. It never changes production predictions or builds public datasets.
