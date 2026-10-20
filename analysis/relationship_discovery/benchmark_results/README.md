# Measured performance and bounded extrapolation

| Family | Pilot candidates | Measured seconds | Candidates/s | Estimated full serial minutes | Factor-two budget minutes | Detailed uncompressed GB |
| --- | --- | --- | --- | --- | --- | --- |
| genre_interaction | 28 | 15.62 | 1.79 | 29.7 | 59.3 | 0.06 |
| nonlinear | 28 | 7.01 | 4.00 | 13.3 | 26.6 | 0.14 |
| numeric_interaction | 12 | 1.47 | 8.18 | 178.8 | 357.7 | 1.43 |
| pairwise | 24 | 13.13 | 1.83 | 25.3 | 50.6 | 0.01 |
| structure | 12 | 11.14 | 1.08 | 0.4 | 0.9 | 0.00 |
| temporal | 15 | 5.55 | 2.70 | 10.2 | 20.4 | 0.14 |
| threshold_interaction | 18 | 2.09 | 8.61 | 1019.0 | 2038.0 | 8.22 |

Combined point estimate: **21.28 hours**;
factor-two planning allowance: **42.56 hours**.
These are extrapolations from a small domain-stratified pilot, not measured full
campaign times. They retain pilot resampling precision; calibrated full-search
inference can require substantially more work. Sample size, knots, categories,
conditioning dimensions and BLAS implementation affect throughput.

Measured peak resident memory for the single-process pilot was
**750.1 MiB** (process-lifetime high
water mark, not incremental model memory). A two-worker run has separate data
copies; summing worker peaks is an upper-bound estimate rather than a measured
simultaneous aggregate peak. Read [parallel.json](parallel.json) for the actual
one-versus-two-worker microbenchmark, including startup. It is too small to
promise linear scaling. BLAS is capped at one thread per worker.

[Method throughput](method_throughput.csv) measures all nine univariate alternatives,
additive/interaction fits, PCA and k-means/refits. Candidate timings include the
associated statistics and resampling. Proposed detailed uncompressed diagnostics
would occupy approximately **10.01 GB**
if retained at the pilot's density; compact summaries and compressed diagnostics
are much smaller. Model databases or row-level predictions are not committed.

A future full runner should batch pair statistics, reuse design/fold caches,
checkpoint atomic candidate records with input/code hashes, and avoid writing
repeated subgroup metadata. That engineering can improve performance without
screening away candidates. The current CLI deliberately cannot run the full grid.
