# V5 exhaustive pairwise protocol

This is retrospective exploratory association and chronological transfer, with no
causal interpretation and no untouched historical confirmation period. The user
explicitly authorized this pairwise campaign after V4's strategy benchmark. No
three-predictor, nonlinear, interaction, clustering or acquisition campaign is
included. The exact executable specification, runtime versions, code and input
hashes are in [frozen_protocol.json](frozen_protocol.json).

## Population and inventory

The immutable enriched music views contain **818 overall months** (August 1958 to
September 2026) and **7,173 observed genre-month rows** across 16 genres. One
overall series and 16 separate genre series are analyzed. No regression stacks
genres into independent economic observations. The last supplied Billboard chart
in each month defines the snapshot; September 2026 stops on September 19 and is
incomplete. Chart dates are not release dates or lyric-writing dates.

The music views preserve 81,797 source song-month rows, including three repeated
song/month identities. Feature means use available source rows; distinct song
counts are retained separately. These means need not equal the older moving
averages, which used 81,794 distinct song-months. The supplied upstream chart
snapshot is reported as originating from mhollingshead/billboard-hot-100; this
campaign does not independently authenticate Billboard's historical records.

[variable_inventory.csv](variable_inventory.csv) records variables, domains,
families, units, sources, dependencies, temporal availability, frequencies,
coverage, exclusions and transformations. [exclusion_log.csv](exclusion_log.csv)
retains source aliases, identifiers, exact duplicates, constants and unsupported
encodings. Private embedding coordinates do not have a meaningful individual
scalar interpretation; cyclical phase coordinates require a joint directional
model outside this pairwise scope. These exclusions are declared before fits.
Low sample size remains an attempted test rather than disappearing from the
denominator. Per-view empty/constant variables are structurally excluded.

There are **544 distinct retained music variables**, including coverage measures
and 114 pairs of fixed/matched-composition lyrical summaries; **196 external
variables**; and **3,876 distinct music-variable/view combinations**. These
produce **759,696 eligible population-specific pairs**, **4,558,176 lagged pairs**,
**9,116,352 pair/track rows** and **18,046,656 method hypotheses**. Shared sources,
derived transformations and aliases are not claims of independent constructs.
See [search_space.csv](search_space.csv) for all 39,984 deterministic work units.

## Fixed composition, observation support and weighting

An observed feature mean requires at least five available source song rows in
that genre/month. Coverage/count variables retain their actual values. For each
lyrical measure, fixed composition uses genres with at least 60 supported months
before January 1983, preceding the first validation period and its embargo.
Weights are the average baseline genre shares normalized once. The matched
composition comparator uses contemporaneous shares over exactly the same genre
subset and complete months. Missing genres are never silently renormalized from
month to month. [fixed_composition.json](fixed_composition.json) gives every
feature's genre set and weights. Comparisons are conditional on this supported
subset, not estimates for all genres or missing lyrics.

Primary fits weight native periods equally. A sensitivity fit weights each
period by its distinct chart-song counts, summed over contributing months; after
differencing it uses the smaller adjacent-period count. This is a chart
population size weighting, not a pooled mean of feature-observed unique songs.
No second inferential p-value is claimed for this descriptive weighting check.
Monthly means already include repeated songs across months and shared artist
credits. Time-series uncertainty addresses serial dependence, not every source
of measurement error or artist-level dependence.

## Calendar and frequency alignment

The exact lags are **0, 1, 3, 6, 12 and 24 months**. Positive lag means the external
reference month precedes the target music month. A positive-lag source period
must end strictly before the target month begins. Quarterly and annual values
are collapsed to one analytical row per source quarter/year. Within each such
unit, music is averaged over the target months admitted by the lag rule. Thus a
one-month annual lag uses the following January, while a 12-month lag can use
all 12 months of the next year. This does not fabricate 12 independent annual
economic observations. At least 75% of the expected target months must be
observed. No missing source periods are interpolated.

Congressional categories are analyzed on their two-year term grid. The explicit
NBER turning-point announcement series groups by its source announcement month;
other event series retain their declared grid and are subject to support gates.
Every categorical series uses labels and an omnibus test, never arbitrary
numeric party codes. Inconsistent values copied within a declared native unit
raise an error.

Existing monthly returns and aggregates retain their original definitions.
Nine additional endpoint variables use the last observed daily value in each
month from the already retained snapshots. Daily factor returns are identified
as one-day endpoint returns, not market closing prices or monthly total returns.
The acquired sources do not supply a literal S&P 500 closing-price series.
[daily_alignment.csv](daily_alignment.csv) records the actual endpoint dates and
observation counts; there is no new acquisition. Source publication/vintage
information is retained where available, but most observations are latest or
revised historical snapshots. Even a positive reference-period lag does not
establish point-in-time availability. Current-month context can follow the last
Billboard chart within that month. All transfer results remain retrospective.

## Raw and adjusted estimands

Raw fits include an intercept only and report direct Pearson correlation,
Spearman rank correlation and the simple OLS slope. Adjusted music is first
differenced on the aligned native grid without crossing missing periods, then
controlled for time, sine/cosine calendar season and, for overall lyrical means,
the changes in all declared genre shares. Within-genre and fixed-composition
means use time/season controls without an extra composition adjustment.

External transformations are source/type-specific: native-period first
differences, positive-endpoint log growth multiplied by 100, or identity for
already defined returns/growth rates/event indicators and categorical labels.
Quarterly/annual changes are calculated on the native grid before alignment.
Exact formulas and dependencies appear in the inventory. Adjusted Pearson/OLS
estimates are partial relationships after the fixed controls. The adjusted rank
method ranks both numeric variables, then projects on the same declared nuisance
control space; it is a rank-regression association, not an ordinary unadjusted
Spearman coefficient. Additional nuisance controls do not constitute a search
over multivariate predictor combinations.

## V4 control-rank failure and repair

The reproduced V4 training design for `lyric_pos_aux_share` has 293 rows and 19
declared controls but rank 18: **`genre_share__K-Pop` is identically zero before
1983**. V4 rejected the entire design. V5 uses a column-scaled SVD basis for the
complete nuisance column space, retaining every identifiable control direction.
It uses numerical rank for degrees of freedom and does not select controls
according to attractive outcomes. The residual degrees of freedom are 274,
rather than 273 from nominal column count. Predictions agree with an independent
full-design SVD solve to approximately **5.13 × 10⁻¹⁶**. See
[adjusted_monthly_fix.json](adjusted_monthly_fix.json).

The basis is fitted only on training controls for chronological transfer.
Validation rows outside the training control row space are explicitly unsupported;
no invented coefficient is assigned to a genre absent throughout training.
The external effect must retain residual variation after those controls.

## Uncertainty, stationarity and validation gates

Numeric slopes use Bartlett/Newey–West HAC covariance on the original equally
spaced native grid, putting zero scores at missing grid positions rather than
compressing gaps. Residual degrees-of-freedom correction is `n/(n-rank(C)-1)`.
Nominal 95% slope intervals and two-sided tests use a conservative t reference
with degrees of freedom `min(residual_df, floor(n/(bandwidth+1))-1)`. The second
method uses the analogous rank-regression test. Pearson and its simple OLS slope
test are the same hypothesis and are counted once. Categorical variables use a
HAC Wald omnibus F test, partial eta squared, and separately retained descriptive
category contrasts. The omnibus contributes one hypothesis; contrast intervals
are not individually corrected discoveries.

The original HAC horizons (24 monthly, eight quarterly and three annual periods)
failed the declared strong-AR null tolerance: nominal 5% rejection was 8.43% at
AR=0.85. The failed result is retained in
[synthetic_validation_initial.json](synthetic_validation_initial.json). Before
examining discovery rankings, V5 doubled those horizons to **48 months, 16
quarters and six years**; term/event horizons are three/six native steps. The
same minimum of six bandwidth blocks and residual df ≥12 remains. Initial native
N minima are 120 monthly, 40 quarterly, 30 annual, 24 term and 30 event observations;
the six-block rule is often stricter. Binary exposures require at least ten
periods per value; every categorical level requires at least five.

Independently seeded validation used 160 all-null worlds at each AR level
0/0.5/0.85, 40 numeric relationships and two methods per world. Nominal rejection
was **4.95%, 5.56%, 7.35%**; worlds with any global BY rejection were **0%, 0%,
1.875%**. These passed the prespecified ≤8% development tolerances. This is not
proof of exact 5% finite-sample calibration: marginal tests remain inflated under
strong dependence. The known 1.5-slope signal was recovered at 1.471, and redundant
controls did not remove it. [synthetic_validation.json](synthetic_validation.json)
also retains a unit-root example and its differenced counterpart. Simulation
changes were driven by synthetic null failure, not real-data effect sizes.

ADF diagnostics use a fixed 12/4/1/1/1 lag rule by monthly/quarterly/annual/term/event
frequency on the longest contiguous supported segment. Music diagnostics use
their own lag-zero native series after declared nuisance projection, without
selecting an external counterpart; external diagnostics use their source grid.
Diagnostics therefore are a broad assumption screen, not a stationarity proof
for every pair's overlap or lag. Missing, failed or nonrejecting (p>0.05) ADF
screens prevent formal inference; nominal estimates remain visible. Categorical
labels do not receive a numeric ADF test. The documented event fallback and the
full diagnostic cohorts are recorded in the code and diagnostic table. Trend
correlation, lag-one residual autocorrelation and an AR(1) effective-N diagnostic
are also retained. That effective N is descriptive and is not the inferential
sample size.

The HAC implementation is checked against
[statsmodels cov_hac](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html).
Native grid/gap handling is explicit because that API assumes equally spaced
consecutive time steps. The fixed ADF diagnostic follows
[statsmodels adfuller](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html).
These implementation checks do not guarantee the scientific assumptions of all
millions of comparisons.

## Chronological transfer and historical stability

Validation periods are **1990–2001**, **2002–2013** and **2014–September 2026**.
Each uses expanding earlier training data with an **84-month embargo**. No random
row split is used. For native periods, the entire training aggregate must precede
the embargo and the entire validation aggregate must lie within its block. All
learned control bases and regression coefficients use training rows only.
First differences and calendar mappings are fixed rules, not fitted using future
outcomes. Raw models compare against the training mean; adjusted models compare
against the training-fitted nuisance-controls prediction. Reported skill is
`1 - model_MSE / baseline_MSE`, alongside MAE and validation partial correlation.
Folds with insufficient support, unidentifiable effects, unsupported new control
space or unseen categories retain explicit failure codes. Successful transfer
can still depend on retrospectively observed controls and revised external data.

Historical stability records how many folds completed and how many have both
positive baseline-relative skill and the same correlation direction as the
full-sample numeric estimate. Categorical tests use positive skill without an
invented direction. Stability is descriptive, evaluated on repeatedly inspected
history, and is not a second confirmatory p-value.

## Multiplicity, complete rankings and presentation

One global **Benjamini–Yekutieli family of 18,046,656 slots** covers every eligible
population/pair/lag/track/method combination. Invalid, underpowered and failed
stationarity slots enter as p=1. No correction is performed only on successful
fits. Nominal probabilities remain separate from formal q values. The algorithm
is checked against [statsmodels multipletests](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html);
the [original BY paper](https://www.math.tau.ac.il/~ybenja/depApr27.pdf) permits
arbitrary dependence **conditional on valid individual p-values**. The simulation
and assumption limitations above still apply; multiplicity correction cannot
repair a misspecified relationship or establish causality.

Ten complete local index rankings refer to the canonical result array. Public
CSV files contain the **first 200 rows** of each ranking, explicitly labeled as
summaries. Raw order prioritizes estimable fits then absolute Pearson r (or the
square root of partial eta squared for categorical tests), stability, native N
and deterministic row ID. Adjusted order first prioritizes stationarity-supported
fits. Domain/genre/lag lists include both tracks and prefer supported adjusted
fits before raw fits, then strength and stability. The stability list prioritizes
completed transfer folds, positive same-direction folds and effect size. The
corrected list includes every row with at least one q≤0.05 and ranks supported
effect sizes. Rankings are never solely a p-value sort. Absolute effect metrics
across different measurement types are descriptive ordering aids, not a common
causal scale. Sparse unsupported genre fits remain at the end, not on the leading
estimable rows. Counts and measurement-coverage associations remain visible and
are labeled as such rather than presented as changes in lyrical content.

Figures use saved coefficient/statistical summaries and fixed ranking rules,
with no restricted historical-value traces. Raw-versus-adjusted comparisons pair
the exact same music/external/population/lag and record unsupported adjusted
matches separately. A disappearing association is descriptive attenuation, not
proof that a causal effect was removed. Null findings constrain these particular
tests and coverage; they do not prove independence.

## Resources and restart

The preflight sampled four deterministic outcome-independent work units in every
view × native frequency × variable kind × track stratum: **680 chunks in 170
strata**. It measured cold-cache alignment, estimates, three transfer folds and
serialization. The conservative projection sums 1.5 times the maximum sampled
chunk cost per stratum, then adds 1,800 seconds for postprocessing and validation.
The total projected **5,148 seconds (86 minutes)** and **5.51 GB** fit within the
authorized four-hour/15 GB limits. Observed preflight peak process memory was
340 MB; planned peak was 1.5 GB. These are estimates, not final usage.

SQLite checkpoints commit complete work units atomically, hashing both the
typed result array and category contrasts. A protocol mismatch, corrupted record
or attempt to alter a completed chunk fails. A deliberate stop after 100 chunks
tests real campaign recovery. Final BY cannot run until all 39,984 IDs are present
exactly once. Temporary final arrays are validated and renamed atomically.
Resource accounting accumulates active command time; idle coding intervals are
not compute time. The free-space guard preserves 2 GiB in addition to the 15 GB
temporary-output limit. Complete rankings are compact index arrays, avoiding
ten duplicate multi-gigabyte CSV exports.

Original music, historical sources and previous analysis files are never
rewritten. Final validation checks the prior-file baseline, independent BY,
checkpoint recovery, complete coverage and deterministic sampled replays.
Retrospective data rights, sparse audio/metadata coverage, model-score error,
nonrandom missing lyrics, changing language/genre definitions and repeated
historical inspection remain limitations regardless of computational validation.

## Post-fit interpretation audit

After inspecting the completed rankings, a separate diagnostic audits **every
corrected numeric method** for concentrated temporal variation. On the same
native-grid bandwidth blocks, it computes `(sum E)^2 / sum(E^2)` for (a) residual
external-variable squared energy and (b) squared OLS-score energy. Fewer than six
effective blocks is flagged, using the existing six-block support floor as a
diagnostic reference. This is a post-fit sensitivity check, not a preregistered
test, a calibrated p-value, or a change to the frozen estimates/global BY family.
It exposes the distinction between hundreds of observed months and a relationship
whose identifying variation comes largely from one episode. Filtering on this
diagnostic does not create a new confirmatory claim.

Source-informed measurement roles are also propagated from the existing published
enrichment dictionary through fixed/matched-composition names. The original V5
pipeline role remains visible. In particular, semantic reference-corpus counts
are provenance/quality quantities; they are not semantic-content scores. All
tested rows remain in their complete original rankings. Calendar-context
associations such as Christmas proximity versus election month are retained as
expected shared-calendar patterns and are not interpreted as music discoveries.

Stored checkpoint bytes and published numerical summaries are verified exactly.
Fresh numerical replays require identical integer/status fields and floating
agreement at relative tolerance 1e-9 and absolute tolerance 1e-12, with the maximum
observed error published. This allows harmless low-order BLAS/SVD differences;
it does not permit changed candidate coverage, support decisions or material
effect sizes. The independent global BY check uses its own tighter tolerance.
