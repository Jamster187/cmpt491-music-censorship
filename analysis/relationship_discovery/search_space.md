# Finite search space

Only the **137-candidate pilot** has run. Counts below are exhaustive proposed
universes, including reconstruction controls. The existing 59-target OLS campaign
is unchanged. This design has 57 cardinal song-level targets, 57 cardinal
predictors per pool (self removed per task), one ordinal measurement and 17 nominal
encodings: 75 variables. Observation-level extensions are explicitly deferred.

| Family | Proposed candidates/comparisons | Maximum fits or estimates | Pilot candidates |
| --- | --- | --- | --- |
| pairwise | 2,775 | 2,775 primary permutation tests | 24 |
| nonlinear | 3,192 | 255,360 | 28 |
| genre_interaction | 3,192 | 25,536 | 28 |
| numeric_interaction | 87,780 | 702,240 | 12 |
| threshold_interaction | 526,680 | 4,213,440 | 18 |
| temporal | 140,505 | 337,212 rolling + 1,910,868 annual estimates | 15 |
| structure | 3 panels × (3 PCA ranks + 4 cluster counts) | 360 fits including stability refits | 12 |

Numeric pair counts: 1,596 cardinal–cardinal plus 57 ordinal–cardinal;
986 numerical/ordinal–categorical and 136 categorical–categorical pairs.
The pairwise methods total 8,799 statistics (1,596 Pearson, 1,653 Spearman,
2,775 MI, 1,653 capped distance correlations, 986 eta-squared and 136 Cramér V),
plus 990 continuous-variable kNN MI diagnostics on capped hash samples. There is one primary test
per pair, not an uncorrected claim for each method.

For p=57 cardinal variables, univariate directed pairs are p(p−1)=3,192.
Product interactions are p×choose(p−1,2)=87,780. Threshold interactions are
p(p−1)(p−2)×3=526,680 because the threshold conditioner is directional.
Genre conditioning adds 3,192 models. Four outer periods, two inner periods
and nine univariate methods give an upper bound of 80 fits per nonlinear
candidate; fixed conditional alternatives need at most eight fits per candidate.

The proposed predictive total is **5,196,576 fits**; adding the proposed 360
multivariate fit/stability calls gives **5,196,936**. There are **623,619 proposed
primary inferential hypotheses**, before any separately approved temporal tests.
A marginal descriptive subgroup scope contains 38,019 pair/group cells.
The implemented temporal family additionally crosses genre and period, giving
196,707 pair × genre × period cells in the full proposed grid (1,785 in this
pilot). Its 1,910,868 unadjusted annual estimates are supplemented by 112,404
global genre-adjusted annual estimates and 8,265 genre-adjusted breakpoint
contrasts. These diagnostics do not create certified additional p-values.
See [expanded_workload.json](expanded_workload.json) for these exact bounds. The optional
full numeric-threshold subgroup grid would add 1,053,360 cells and is counted
separately from model fits. Temporal comparisons span 1,653 numerical/ordinal
pairs × 17 strata × 5 breakpoints. Rolling windows overlap and are not independent
tests. PCA ranks share decompositions in the proposed efficient implementation.

The threshold-triple family is the main combinatorial bottleneck. No heuristic
screening is substituted for these counts. Approving only a predefined family
(e.g. univariate nonlinear plus genre interactions) is a transparent scope
choice; approving every threshold triple is a substantially larger campaign.

Runtime estimates retain pilot resampling settings. Full-search inference may
need much finer Monte Carlo resolution: an isolated rejection under global BY
at q=.05 across 623,619 hypotheses would require a p-value around
5.8e-09. Pilot permutation/sign-flip
resolution cannot support that isolated-tail guarantee. Many simultaneous
rejections change the step-up threshold, but do not remove the need for a
predeclared precision and null-calibration plan. Approve inference design and
budget before launching a full search.
