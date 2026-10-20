# Statistical relationship discovery: frozen pilot protocol

**Exploratory pilot, not independent confirmation.** The 2018-onward population
and the earlier historical data have already informed previous analyses. Nested
chronological evaluation measures transfer within this known resource; it does
not make any of these data newly untouched. No full discovery campaign is run.

## Population, variables and interpretation

The unit is one exact original title/artist song identity in `data/public/songs.csv`.
There are no repeated weekly/monthly observations in this pilot. The substantive
inventory contains all 57 cardinal numerical song variables from the original
specification, the ordinal best-chart-rank variable, primary genre, and the 16
existing secondary-genre membership flags. Secondary flags encode the existing
set, retain missingness, and do not change the genre classifier or taxonomy.

Ordinal rank participates in Spearman/dependence/historical analysis, not a
cardinal-response OLS search. Nominal genres use contingency tables and fixed
one-hot indicators. Their integer table indices never imply musical distance.
Counts retain their cardinal meaning. Partial MusicBrainz dates supply only the
existing release-year conversion. Dates remain chart-history measurements,
not assumed release dates.

This first bounded design uses the song table. The two observation-level
reported-weeks targets from the 59-target campaign are deferred: adding their
repeated observations requires a separately specified clustered longitudinal
search, not silently treating rows as independent songs. Artist/title identifiers,
source coordinates and acquisition status remain identity/coverage diagnostics;
no arbitrary text-to-number encoding is introduced. The existing
[variable exclusions and definitions](../../docs/regression_search_plan.md) remain
available. All substantive variables in the stated song-level scope are retained,
including apparently obvious relationships.

The original definition/provenance-based A/B/C policy is reused without revision:
A is circular/reconstruction, B is overlapping/same-family, and C requires every
predictor and substantive conditioner to differ from the target's domain.
The original policy includes conservative episode/duration reconstruction scope
choices beyond exact algebraic equality; these are interpretation choices, not
claims that endpoints or duration summaries are universally identical.
A records remain in the complete pilot inventory and diagnostics. Separate
nontrivial leaderboards omit A and label B. Nonlinear/conditional (D) and
historical/genre-specific (E) are additional family tags, not mutually exclusive
replacements for A/B/C. Correlation magnitude never determines novelty.

## Outcome-blind pilot and finite search

The complete proposed universes are defined by deterministic generators and
counted in [search_space.json](search_space.json). The pilot takes the smallest
seeded candidate hashes within predefined domain/type/category strata. Numeric
triple samples are smaller; every selected threshold triple is evaluated at
all three fixed quantiles. The manifest contains every pilot candidate before
new fits begin. This is an explicitly bounded feasibility sample, **not a claim
that the proposed full search has been completed**. No outcome-based screening
substitutes for future exhaustive enumeration.

`pilot_protocol.json` locks source/data/code hashes, exact candidates, methods,
periods, seeds, support rules and resampling settings. Checkpoints reject changed
identities. The CLI exposes audit, pilot, benchmark and validation operations;
it has no full-campaign operation and enforces a 200-candidate pilot cap.

## Discovery and chronological evaluation

Outer evaluation periods are 1990–1999, 2000–2009, 2010–2017, and 2018–2025.
For each outer start, two inner five-year periods immediately before it select
among nine predefined univariate methods. Each inner/outer training set expands
backward through available history. The exact original `regression_core.partition`
logic requires an entire song's observed chart window to fit a partition.
Training songs end before the evaluation starts; evaluation songs debut within
its period and end before its exclusive endpoint. Boundary-crossing songs are
purged and split counts are published. The final incomplete 2026 calendar year
is not used as an evaluation year.

Preprocessing, medians, scales, spline knots, thresholds, genre interaction
support and method selection use their training rows only. Target-missing rows
are removed separately per target; predictors retain training-only imputation
and missing indicators. At least 500 training and 200 evaluation songs are
required. All refits use the frozen historical enrichment values, so they are
**retrospective association/generalization analyses, not as-of forecasts**.
Whole-history chart outcomes and later-acquired enrichment would not necessarily
be available at a song's debut. The split safeguards do not repair that timing.

Univariate alternatives are OLS, quadratic OLS, three linear-hinge models with
training 25th/50th/75th-percentile knots, cubic splines with 4 or 6 training-quantile
knots and linear extrapolation, and depth-2/depth-3 trees with at least 100 training
songs per leaf. Inner mean baseline-relative MSE skill selects one method,
including OLS itself; ties follow the frozen method order. Outer outcomes never
select the method. OLS, training-mean RMSE and training-median MAE baselines are
reported. Spline, polynomial and tree methods describe finite alternatives;
this is not a claim to exhaust all nonlinear functions. Implementation follows
[scikit-learn's spline API](https://scikit-learn.org/1.5/modules/generated/sklearn.preprocessing.SplineTransformer.html).

Conditional OLS compares an additive model with the same inputs against an
additional product, genre-specific slope, or threshold-specific slope. A
threshold's main effect belongs to the comparison baseline, so an apparent
interaction cannot merely be a missing step intercept. Numeric thresholds come
from training rows. Genre interactions require 100 training songs and five debut
years; unsupported groups retain the additive baseline and are disclosed.
Threshold sides require the same training support. Descriptive evaluation
subgroups require 100 songs and five debut years. All predefined groups remain
in the coverage tables, including failures; small groups are never presented
as reliable effects. Partial rank correlations and sign reversals are logged
as descriptive diagnostics, not independently tested subgroup discoveries.

## Dependence and uncertainty

Pairwise analysis uses complete pairs among songs whose observed history ends
before 2026. It reports Pearson where both variables are cardinal, Spearman for
numerical/ordinal pairs, empirical 10-quantile-bin mutual information, nominal
eta-squared/Cramér's V, and distance correlation on an outcome-blind hash sample
of at most 512 songs. Continuous-score pairs also receive five-neighbour MI on
at most 5,000 hash-selected songs. Distance correlation and MI estimates are
finite-sample biased; their values are not interchangeable effect-size scales.
The fixed hash caps are explicit computational approximations to effect
estimation, not screens that remove variable pairs. Tied quantile bins collapse.
See the [MI estimator documentation](https://scikit-learn.org/1.5/modules/generated/sklearn.feature_selection.mutual_info_regression.html).

The pairwise primary test permutes the response **within debut year** 999 times.
Its statistic is absolute Spearman rho, rank eta-squared, or bias-corrected
Cramér's V. The null is conditional independence under within-year song
exchangeability. The displayed pooled effect and that calendar-conditioned
null answer different questions. The +1 Monte Carlo correction prevents zero
p-values; minimum possible p is 0.001. Shared artists, genre composition and
correlated classifier errors can violate simple exchangeability. These are
exploratory p-values, not a certification that every assumption holds.
Pooled-effect intervals resample two-year debut blocks 499 times. Numerical
ranks are fixed before that bootstrap. Annual correlations and their block
intervals expose changes obscured by a pooled statistic.

For predictive improvements, paired outer squared-error differences are divided
by their fold's training-target variance. They are averaged within two-year
calendar blocks and then equally across blocks. This dimensionless effect has
a different weighting from the pooled equal-song R²/MAE/RMSE, all of which are
also reported. With at least eight blocks, 499 block resamples provide a fixed-
model interval and 32,767 block sign flips provide a one-sided improvement test.
The latter assumes a symmetric block-level loss-difference null and sufficiently
short dependence. Four-year block intervals are a prespecified sensitivity
check. Shared training histories and residual longer-range dependence remain
limitations. Intervals exclude selection/refit uncertainty; a fully nested
block-refit uncertainty campaign would require additional computation.

## Multiple testing and ranking

The primary inferential family is all 110 attempted pilot pairwise and predictive
hypotheses, including reconstruction controls. Failed or unavailable tests count
as p=1. Benjamini–Yekutieli adjustment is applied globally; family-specific BY is
also displayed. BY accommodates dependence between valid p-values but does not
make a misspecified null valid. See [SciPy's FDR documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html).

Historical contrasts and multivariate structure are descriptive in this pilot
and have no certified p-value or q-value. Their many subgroup cells are not
quietly folded into an inferential claim. If future campaigns add subgroup or
breakpoint tests, those hypotheses must be included in a newly frozen correction
family before running them. Pilot BY values are never carried over as full-search
q-values. A full search's much larger multiplicity and Monte Carlo resolution
need explicit power/calibration work; rerunning a few attractive tests alone
would not provide valid campaign-wide correction.

There is no weighted novelty score. The complete inventory preserves effects,
units, baselines, intervals, N, warnings and categories. Statistical/cross-domain
views sort computed pilot q-values first, then period stability;
this is evidence ordering, not a common magnitude scale. Nonlinear/conditional
views sort the lower improvement-interval bound, then observed improvement.
Stable-model views require all four outer periods and sort the worst-period
improvement first. Temporal views sort the magnitude of the recorded historical
contrast and remain explicitly descriptive. Every leaderboard retains weak or
negative results; a rank does not confer scientific importance or causation.

## Historical comparisons

Annual rank correlations require 30 complete songs. Ten-year rolling windows
advance every five years and overlap; they are plots of association, not
independent replicated tests. Global and all 16 fixed genre strata are evaluated.
Period-specific correlations and missingness are also reported.

The five fixed breakpoints are **1980, 1990, 2000, 2010 and 2020**. Each compares
five annual correlations before versus five after, with at least 200 songs per
side and all five annual estimates present. Global contrasts additionally show
annual partial rank associations after removing genre intercepts. The contrast
is the change in average annual Fisher-z Spearman association. Length-two moving
blocks within each side provide descriptive intervals. Five annual observations
per side are too few for a confident independent-block test, so p-values are
withheld even if a displayed interval excludes zero. This explicit limitation
prevents an attractive 2020 plot from becoming a causal or confirmed claim.
No post-hoc breakpoint search or change-point optimization is performed. A
calibrated change-point null and longer follow-up are additional work, not
silently implemented methods.

## Multivariate structure

PCA and k-means use three predefined panels: content scores, affect scores, and
all 42 lyric scores. Only complete-panel rows participate; coverage is recorded.
Training means/scales are applied to chronological evaluation songs. The pilot
uses PCA ranks 2 and 5 and k-means k=2 and 3; the proposed full grid adds rank 10
and k=4/5. K-means uses ten deterministic initializations. Evaluation reports
reconstruction/distortion reduction, silhouette on at most 1,500 fixed-hash
songs, genre profiles, and debut-year profiles. Each fold has three two-year-
block training resamples with full rescaling/refitting: principal-angle cosines
measure PCA subspace stability and adjusted Rand index measures cluster stability.
These three repeats are diagnostics, not precise confidence intervals. No
hand-weighted composite score is invented. Sentiment closure and related model
outputs can dominate latent dimensions; this structure is not an independent
human construct validation. See the [PCA](https://scikit-learn.org/1.5/modules/generated/sklearn.decomposition.PCA.html)
and [k-means](https://scikit-learn.org/1.5/modules/generated/sklearn.cluster.KMeans.html) implementations.

## What would count as confirmation

The current sprint can identify candidates for a later frozen study and measure
historical transport. It cannot provide independent confirmation from reused
outcomes. Before a full run, approve the family scope, inference/null assumptions,
resampling precision, correction family and computational budget. Freeze any
claimed effects and their evaluation rules before obtaining genuinely new future
song cohorts or an independently sourced, non-overlapping validation resource.
Require adequate completed label windows and verified input availability for a
forecast claim. No new data is acquired in this sprint. A future replication
should also assess artist dependence, genre-composition shifts, missingness and
sensitivity to longer temporal blocks. Causation requires a separate design.
