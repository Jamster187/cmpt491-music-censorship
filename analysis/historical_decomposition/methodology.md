# Historical change and genre decomposition

This bounded, exploratory analysis uses the existing monthly public dataset.
The design below was fixed before calculating the new comparison results. The
population has already been inspected; no previously used regression test set is
treated as independent confirmation. No data acquisition or classifier/genre
revision is part of this analysis.

## Population and weighting

Use complete calendar years 1960–2025. Exclude partial 1958 and 2026 and leave
1959 outside the predefined decade comparisons. Reuse the validated moving-average
preparation: identical duplicate song-month rows contribute once, with the mean
of their source rank weights. A score is a fixed song-level measurement, not a
new model judgment each month. Retain all 16 original primary-genre labels.
The separate teammate preprocessing exports are preserved but are not inputs:
they threshold LyricLens scores, restrict genre confidence and merge labels.

Primary period comparisons give each distinct song-month equal weight. Rank
sensitivity weights it by `101 - monthly_rank`, averaging weights for duplicate
source rows. Unique-song sensitivity counts each song once within each comparison
period; a song present in both periods remains in both. These respectively measure
chart presence, rank-emphasized presence, and the repertoire represented in a
period. They are not equivalent to release cohorts or independent observations.

The seven fixed comparisons are 1960–1969/1970–1979, 1970–1979/1980–1989,
1980–1989/1990–1999, 1990–1999/2000–2009, 2000–2009/2010–2019,
2010–2019/2020–2025, and 1990–1999/2015–2024. The six-year recent period is
explicitly shorter than the preceding decade. All 42 scores receive descriptive
decompositions. Formal uncertainty is restricted to the eleven requested scores:
four LyricLens scores, Detoxify toxicity, positive/negative sentiment, and joy,
love, sadness and anger. All remain on their separate original 0–1 scales.

## Exact symmetric accounting

For period t and genre g, let p(g,t) be its share of available-score weight and
mu(g,t) its weighted observed mean. M(t) = sum_g p(g,t) mu(g,t). Then

    within(g)      = (p(g,0) + p(g,1))/2 * (mu(g,1) - mu(g,0))
    composition(g) = (mu(g,0) + mu(g,1))/2 * (p(g,1) - p(g,0))
    M(1) - M(0)    = sum_g within(g) + sum_g composition(g).

This symmetric Kitagawa accounting averages the two reference-period paths.
Reversing the periods reverses both contributions. It is an arithmetic allocation,
not a causal mediation analysis. The equations apply to weighted means as well as
rates; see [Das Gupta's Census manual](https://www2.census.gov/library/publications/1993/demographics/p23-186.pdf).

No genre is removed from the primary accounting. Means based on fewer than 30
distinct scored songs are flagged. If a genre has available scores in only one
period, its unobserved opposite-period mean is not identifiable. For a clearly
labelled entry/exit convention only, use the observed period's mean on both sides:
within is zero and its observed contribution is allocated to composition. Original
missing means remain blank in the cell table. Bounds obtained by allowing each
unobserved opposite-period mean anywhere in [0,1] show the unidentified allocation.
No missing song score is replaced with zero. A zero-share genre in both periods
has zero contributions. Shares and means are always calculated for the same
score-available population.

Report absolute changes and contributions before their ratios to total change.
Percent contributions may be negative or exceed 100%. A ratio is unstable when
the total-change interval includes zero; such ratios are not substantive shares
of a reliably established increase. Tiny absolute differences are not made
important merely by a large percentage.

## Dependence and uncertainty

Use 9,999 deterministic crossed multiplier-bootstrap replicates for primary
comparisons and breakpoint coefficients. Each replicate gives an exact artist
credit an independent mean-one exponential weight, shared by all its songs and
months, and multiplies this by an independent mean-one exponential calendar-block
weight. Calendar blocks are 24 consecutive months; their origin is randomly
shifted within 24 months for each replicate to avoid fixing a special boundary.
Weights remain positive, preserving sparse-cell support. This extends the
crossed-factor reweighting idea in [Owen and Eckles (2012)](https://arxiv.org/abs/1106.2125)
to short-range calendar dependence. It is an approximate resampling model, not
an exact finite-sample test or a theorem guaranteeing coverage for arbitrary trends.

Recompute means, shares, both decomposition components and regression coefficients
under these weights. Do not resample song-month rows independently. Exact artist
credits include collaborations and can split the same performer across clusters.
The block model does not cover unlimited temporal dependence. A six-year period
contains only about three 24-month blocks; intervals and p-values therefore have
limited precision and are explicitly exploratory. For the legacy and recent
comparisons and the 2020 models, also assess 12-/36-month blocks and artist-only
or calendar-only weighting as uncertainty sensitivities (499 replicates).

Publish percentile 95% bootstrap intervals and two-sided centered-bootstrap
p-values `(1 + count(abs(bootstrap - estimate) >= abs(estimate)))/(B + 1)`.
Their minimum resolution is 0.0001. Apply one Benjamini–Yekutieli correction to all
715 planned primary terms: 7 comparisons × 11 scores × 3 components, plus
11 break dates × 11 scores × 2 models × 2 break terms. Retain failed/unidentified
primary tests with p=1 in this denominator. Additional weighting/missingness and
uncertainty scenarios are disclosed sensitivity descriptions, without new
significance declarations. Intervals are marginal, not simultaneous confidence
sets, and cover neither classifier measurement error nor missing-not-at-random bias.

The first completed pass used 999 replicates. Its 0.001 p-value floor produced a
minimum global q of approximately 0.165, making the correction poorly resolved.
The precision refinement reran **every** planned primary test with 9,999 replicates;
it changed no dates, populations, estimands, models or correction family. The
[precision audit](precision_audit.json) retains that first pass's protocol and
[all coarse-resolution tests](precision_999_primary_tests.csv). This operational
refinement was disclosed after the first pass; it is not an independently
preregistered analysis. There was no selective refinement of attractive results.

## Fixed breakpoint comparisons

Fit the same segmented regression at January of 1970, 1975, 1980, 1985, 1990,
1995, 2000, 2005, 2010, 2015 and 2020. Each uses January of year b−6 through
December of year b+5: six complete years before and after. Terms are intercept,
time in years centered at b, post-break indicator, post-break time, and eleven
month-of-year indicators. A second specification adds primary-genre fixed effects.
Genre adjustment removes additive genre mean differences, not arbitrary
genre-specific trends or all changes in sample composition.

Each scored song-month receives weight inverse to its month's scored-song count,
so each calendar month has equal total weight. Rank sensitivity normalizes rank
weights within month. Thus the unadjusted fit is equivalent to regression on
monthly available-score means. Complete-case masks are score-specific. Artist and
calendar multipliers apply to these fixed point-estimate weights, and each
bootstrap regression is refitted. Also report 24-lag Bartlett/Newey–West uncertainty
from monthly sums of regression scores as a distinct autocorrelation diagnostic.
Seasonality, trend specification and dependence follow standard segmented-series
considerations described by [Lopez Bernal et al.](https://doi.org/10.1093/ije/dyw098).

Report level change (score units) and slope change (score units/year) separately.
Compare 2020's absolute estimated changes with the ten fixed historical alternatives.
Those windows overlap and ten placebos provide coarse empirical ranks, not an
independent randomization test. Sensitivities for 2020 include March instead of
January (same 2014–2025 observation window), rank weighting, exclusion of low-
confidence genres, and a quadratic background trend. They do not select a winner.
No interruption is assumed to be caused by COVID; concurrent changes, nonlinearity,
coverage and genre measurement can all matter.

## Missingness and genre sensitivity

Publish score and lyric coverage by year/period and genre using both observations
and distinct songs. Restricting to high-confidence, high-or-medium confidence,
the six most represented genres over 1960–2025, or genres with at least 30 distinct
scored songs in both periods changes the target population; report the retained
fractions and renormalize explicitly. The six-genre rule uses counts, not outcomes,
and is not asserted to be the unknown Milestone 2 selection.

Complete-case means need not represent unscored songs. Evaluate a stated
missing-at-random-within-period-and-genre scenario: unavailable songs have their
cell's observed mean, and genre shares use the full population. A cell with no
scored song uses its period's overall observed mean under an explicit coarsening
assumption; report the weight affected. Pattern-mixture scenarios shift expected
missing scores by ±0.10, clipped to [0,1], including opposite shifts between the
two periods. These are sensitivity assumptions, not recovered measurements.
Also report assumption-free [0,1] bounds on each population mean and its change.
Zeros used as lower bounds are not zero imputation in the analysis dataset.

## Preliminary-report provenance

The user identifies the five preliminary percentages as Milestone 2 report,
Question 4 (1990s versus 2015–2024, six genres). Original code and exact weighting
are unavailable and may have been calculated outside the repository. They are
unverified claims, not accepted reference values. Search of the current repository
and relevant Git history found no original decomposition implementation. Audit
the new arithmetic independently and compare the stated claims without changing
methods to match them. Preserve previous reports and teammate preprocessing.

## Reproduction bookkeeping

A complete resume test found that Python tuples in the identity became lists
when written to JSON, causing an unchanged run to reject its saved protocol.
The identity now canonicalizes that representation before comparison. The
[resume-fix audit](resume_fix_audit.json) retains the original protocol and records
the new source fingerprint. Only the source hash changed; dates, parameters,
random streams, estimates and inference code did not. Every retained bootstrap
array was hash-checked while updating its identity metadata, and all scientific
tables reproduced byte for byte with new bootstrap calculations forbidden.
Original local cache files and the original execution timing remain preserved.
