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
An unfinished batch retains its original ten-song context when retried; any
previously completed rows remain unchanged. Only one worker can hold the lock.

After stopping a worker, confirm its Codex child has also exited before resuming.
Inspect errors before using `python3 src/genre_production.py run --retry-errors`.
This retries failed batches with identical requests and preserves their successful
rows. It does not bypass a quality stop. Do not introduce a separately billed API
fallback to resolve access limits.

## Monitoring and completion

After each batch, persist counts by genre, confidence and historical period.
Recent windows of 200 new results stop production if one genre reaches 80%, Other
reaches 50%, low confidence reaches 60%, or a confidence share changes by 40
percentage points versus the preceding 200. These are coarse operational alarms,
not evidence that smaller changes are necessarily errors. Any malformed response,
taxonomy violation, unexpected tool call or transport failure also stops the run.
Individually valid rows survive another row's schema failure.

Inference completion requires all 28,041 rows to pass the frozen output validator.
A completion marker explicitly leaves qualitative review pending. Before dataset
publication, rerun the protected-file validator and full tests, then perform a
bounded deterministic review spanning confidence levels, genres and periods.
Do not manually overwrite labels during review. Confidence is qualitative;
secondary genres are provisional. No public master rebuild is part of this run.
