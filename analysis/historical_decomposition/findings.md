# Historical change and genre decomposition findings

This completed analysis describes the existing Billboard month-end population.
It does not identify COVID effects, recover missing lyrics, or independently
confirm findings from a new dataset. All 42 classifier scores and all 16 original
genres remain in the descriptive accounting; formal uncertainty covers the 11
prespecified dimensions.

## 1. Audit of the Milestone 2 claims

**The original five percentages remain unverified.** Their provenance is the
group's Milestone 2 report, Question 4, as supplied by the user. Original code,
the exact six-genre set, weighting and reference-period convention were unavailable
and were not found in the repository/history. Consequently this is an independent
recalculation, not a claim to have reproduced an unknown original implementation.
Methods were not adjusted to match those percentages.

The primary comparison uses all 16 genres, distinct scored song-months, unchanged
continuous scores and symmetric Kitagawa accounting:

| Dimension | Preliminary within | 1990s mean | 2015–2024 mean | Change | Within share | Composition share | 95% change interval | Change BY q | Within BY q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Toxicity | 74% | 0.1457 | 0.3629 | 0.2171 | 83.4% | 16.6% | [0.1676, 0.2666] | 0.03007 | 0.03007 |
| Sexual content | 69% | 0.5199 | 0.6326 | 0.1128 | 84.2% | 15.8% | [0.0539, 0.1669] | 0.06135 | 0.07574 |
| Explicit language | 65% | 0.2774 | 0.5597 | 0.2823 | 77.6% | 22.4% | [0.2152, 0.3520] | 0.03007 | 0.03007 |
| Substance use | 61% | 0.1847 | 0.5018 | 0.3171 | 66.3% | 33.7% | [0.2556, 0.3798] | 0.03007 | 0.03007 |
| Violence | 46% | 0.2093 | 0.3137 | 0.1044 | 69.1% | 30.9% | [0.0543, 0.1541] | 0.07574 | 0.21586 |

Toxicity, explicit language and substance use pass the global BY threshold for
both total change and within-genre contribution. Sexual-content and violence
changes have positive marginal intervals but do not pass global BY. Percentage
allocations also have substantial uncertainty:

| Dimension | Within share | Marginal 95% within-share interval |
| --- | --- | --- |
| Toxicity | 83.4% | [69.6%, 101.4%] |
| Sexual content | 84.2% | [48.5%, 137.5%] |
| Explicit language | 77.6% | [60.0%, 96.7%] |
| Substance use | 66.3% | [54.6%, 77.3%] |
| Violence | 69.1% | [34.5%, 109.4%] |

Values above 100% are possible because the composition component can offset the
within component. These intervals concern the observed-score population and do
not include missing-data or measurement uncertainty.

The new within-genre shares differ from the preliminary claims. The exact reason
for each original discrepancy cannot be established without its code. Weighting,
omitted genres, score thresholding and one-sided reference choices can change the
estimand. The current teammate preprocessing exports threshold LyricLens scores
and change genre inclusion; they were preserved and not used here. This is not
evidence that the unavailable original report used those exports.

The [reference-path audit](reference_path_audit.csv) records both sequential
standardization paths. Their average exactly equals the symmetric result.
The six-largest-genre sensitivity is explicitly selected by population counts;
it is not asserted to be the report's unknown six genres.

## 2. Long-run change and its decomposition

Changes are not uniformly monotonic. The following reports every requested period
comparison on the original score scale; 2020–2025 is six complete years, not a decade.

| Comparison | Toxicity | Sexual content | Explicit language | Substance use | Violence | Love |
| --- | --- | --- | --- | --- | --- | --- |
| 1960s → 1970s | 0.0075 | 0.0111 | 0.0502 | 0.0655 | 0.0218 | -0.0391 |
| 1970s → 1980s | 0.0008 | 0.0411 | -0.0241 | -0.0450 | 0.0273 | -0.0089 |
| 1980s → 1990s | 0.0691 | 0.0701 | 0.1685 | 0.0891 | 0.0543 | 0.0032 |
| 1990s → 2000s | 0.0529 | 0.0114 | 0.1469 | 0.1034 | 0.0461 | -0.0710 |
| 2000s → 2010s | 0.1041 | 0.0899 | 0.0668 | 0.1674 | 0.0361 | -0.0086 |
| 2010s → 2020–2025 | 0.0496 | -0.0179 | 0.0741 | 0.0394 | 0.0252 | -0.0298 |
| 1990s → 2015–2024 | 0.2171 | 0.1128 | 0.2823 | 0.3171 | 0.1044 | -0.1001 |

For 1990s versus 2015–2024, all five content dimensions increase substantially on
their own classifier scales. Within-genre changes account for most of each observed
increase, with a meaningful additional composition component. Love changes by
-0.1001, of which 76.6% is within-genre under the same accounting.
These are classifier-output changes, not calibrated prevalence or severity of
human-judged lyrical content. Cross-classifier magnitudes are not interchangeable.

For the more recent comparison, report absolute components before percentages:

| Dimension | 2010s → 2020–2025 change | Within | Composition | 95% change interval | Global BY q |
| --- | --- | --- | --- | --- | --- |
| Explicit language | 0.0741 | 0.0738 | 0.0003 | [-0.0024, 0.1404] | 1.00000 |
| Violence | 0.0252 | 0.0303 | -0.0051 | [-0.0271, 0.0786] | 1.00000 |
| Sexual content | -0.0179 | -0.0228 | 0.0049 | [-0.0753, 0.0399] | 1.00000 |
| Substance use | 0.0394 | 0.0176 | 0.0218 | [-0.0355, 0.1127] | 1.00000 |
| Toxicity | 0.0496 | 0.0558 | -0.0062 | [-0.0184, 0.1091] | 1.00000 |
| Positive sentiment | -0.0093 | -0.0101 | 0.0008 | [-0.0175, -0.0007] | 1.00000 |
| Negative sentiment | 0.0131 | 0.0148 | -0.0017 | [0.0047, 0.0211] | 0.21586 |
| Joy | -0.0033 | -0.0007 | -0.0026 | [-0.0127, 0.0076] | 1.00000 |
| Love | -0.0298 | -0.0244 | -0.0054 | [-0.0565, -0.0019] | 1.00000 |
| Sadness | 0.0079 | 0.0125 | -0.0046 | [-0.0059, 0.0219] | 1.00000 |
| Anger | 0.0100 | 0.0117 | -0.0017 | [-0.0017, 0.0211] | 1.00000 |

Some recent point ratios exceed 100% because composition offsets within-genre
change. Many total-change intervals include zero, making percent shares unstable.
Even a recent-period mean above the 2010s mean can coexist with a downward slope
after 2020. Period means and breakpoint coefficients answer different questions.

## 3. Which genres contributed most?

Signed score-unit contributions for 1990s versus 2015–2024:

| Dimension | Three largest within contributions | Largest positive composition | Largest negative composition |
| --- | --- | --- | --- |
| Toxicity | Hip-Hop / Rap 0.0615; R&B / Soul 0.0570; Pop 0.0331 | Hip-Hop / Rap 0.1005 | R&B / Soul -0.0479 |
| Sexual content | Pop 0.0412; R&B / Soul 0.0212; Hip-Hop / Rap 0.0195 | Hip-Hop / Rap 0.1438 | R&B / Soul -0.1223 |
| Explicit language | R&B / Soul 0.0687; Pop 0.0582; Country 0.0456 | Hip-Hop / Rap 0.1568 | R&B / Soul -0.0781 |
| Substance use | Country 0.0649; Pop 0.0449; R&B / Soul 0.0438 | Hip-Hop / Rap 0.1154 | R&B / Soul -0.0380 |
| Violence | R&B / Soul 0.0315; Pop 0.0137; Alternative / Indie 0.0100 | Hip-Hop / Rap 0.0979 | Rock -0.0385 |

Hip-Hop/Rap's growing share makes a large positive composition contribution to
these five dimensions, offset by declining shares of some other genres. R&B/Soul,
Pop and Country often make substantial within-genre contributions. A genre can
have increasing within-genre scores while its declining share offsets that increase
in the aggregate. These allocations are not causal genre effects or judgments
about artists or listeners.

No original genre is silently discarded. For the legacy comparison the sparse
toxicity cells are:

| Genre | Scored songs in 1990s | Scored songs in 2015–2024 | Entry/exit convention |
| --- | --- | --- | --- |
| Afrobeats / African Pop | 1 | 8 | False |
| Folk / Singer-Songwriter | 8 | 21 | False |
| Gospel / Christian | 8 | 2 | False |
| Jazz / Blues | 10 | 10 | False |
| K-Pop | 0 | 23 | True |
| Latin | 25 | 167 | False |
| Metal | 39 | 4 | False |
| Other | 17 | 10 | False |
| Reggae / Dancehall | 34 | 3 | False |

An absent counterperiod mean cannot identify a unique within/composition split.
The primary convention assigns entry/exit contributions to composition; the complete
comparison table also reports the range of within allocations over unknown means
in [0,1]. Sparse observed means are retained and flagged, not treated as precise.

## 4. Weighting, genre confidence and missing lyrics

The legacy within-genre percentages depend on the population being summarized:

| Dimension | Song-month equal weight | Rank-weighted song-months | Unique songs within period |
| --- | --- | --- | --- |
| Toxicity | 83.4% | 83.4% | 72.6% |
| Sexual content | 84.2% | 84.3% | 59.0% |
| Explicit language | 77.6% | 77.4% | 64.8% |
| Substance use | 66.3% | 67.4% | 59.7% |
| Violence | 69.1% | 75.0% | 54.3% |

Rank weighting generally changes these shares less than switching to unique-song
weighting. Monthly weights describe chart presence, while unique-song weights
reduce the influence of long-running hits. Repeated observations are not treated
as independent songs in uncertainty estimation.

Genre restrictions also change the target population:

| Dimension | High confidence | High or medium | Six largest genres | ≥30 scored songs in both periods |
| --- | --- | --- | --- | --- |
| Toxicity | 84.2% | 83.8% | 83.6% | 80.7% |
| Sexual content | 83.3% | 85.5% | 99.0% | 81.0% |
| Explicit language | 79.0% | 78.0% | 79.6% | 74.6% |
| Substance use | 66.9% | 66.6% | 68.9% | 66.9% |
| Violence | 74.5% | 70.6% | 59.4% | 63.8% |

Retained population fractions are reported for each restriction in
[sensitivity_results.csv](sensitivity_results.csv). Confidence is an existing
categorical evidence grade, not a calibrated probability of correct classification.

Toxicity-score coverage among all song-months by period:

| Period | Coverage |
| --- | --- |
| 1960s | 72.2% |
| 1970s | 76.2% |
| 1980s | 82.1% |
| 1990s | 73.6% |
| 2000s | 81.4% |
| 2010s | 85.5% |
| 2020–2025 | 84.1% |
| 2015–2024 | 84.5% |

The historical population is selected differently across periods and genres.
For the legacy comparison, observed-score coverage is
73.6% versus 84.5%.
Complete-case analysis is not established to be unbiased. Genre-period MAR and
±0.10 expected-missing-score scenarios preserve the direction of the five legacy
content increases, but the unrestricted bounds are much wider:

| Dimension | MAR / ±0.10 scenario change range | Unrestricted [0,1] change bounds |
| --- | --- | --- |
| Toxicity | 0.1768 to 0.2585 | [-0.0644, 0.3546] |
| Sexual content | 0.0602 to 0.1439 | [-0.1121, 0.3069] |
| Explicit language | 0.2258 to 0.3047 | [0.0049, 0.4239] |
| Substance use | 0.2670 to 0.3485 | [0.0242, 0.4432] |
| Violence | 0.0594 to 0.1411 | [-0.1528, 0.2662] |

These scenario ranges and bounds are **not confidence intervals**. The outer
bounds deliberately allow worst-case period means and can be wider than bounds
that additionally impose cross-period shared-song constraints. No missing score
was replaced with zero in observed analyses. Only explicit-language and substance-
use increases have positive lower outer bounds in this particular monthly
comparison; that does not establish their decomposition percentages for missing
songs. All other directions require assumptions about the unobserved population.

## 5. Were changes around 2020 unusual?

The fixed January-2020 models use 2014–2025, six years on either side, monthly
seasonal indicators and separate level/slope changes. The table below adds genre
fixed effects. Slopes are changes in score units per year, not total period changes.

| Dimension | Level change | 95% level interval | Level BY q | Slope change/year | 95% slope interval | Slope BY q | Absolute slope rank |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Explicit language | 0.0381 | [-0.0449, 0.1588] | 1.00000 | 0.0031 | [-0.0300, 0.0358] | 1.00000 | 10/11 |
| Violence | 0.0082 | [-0.0676, 0.1070] | 1.00000 | -0.0048 | [-0.0349, 0.0237] | 1.00000 | 7/11 |
| Sexual content | -0.0143 | [-0.0918, 0.0687] | 1.00000 | 0.0150 | [-0.0116, 0.0388] | 1.00000 | 6/11 |
| Substance use | -0.0236 | [-0.1248, 0.0599] | 1.00000 | 0.0038 | [-0.0219, 0.0290] | 1.00000 | 8/11 |
| Toxicity | -0.0045 | [-0.0588, 0.0750] | 1.00000 | -0.0059 | [-0.0277, 0.0152] | 1.00000 | 4/11 |
| Positive sentiment | 0.0071 | [-0.0055, 0.0184] | 1.00000 | 0.0034 | [-0.0005, 0.0073] | 1.00000 | 3/11 |
| Negative sentiment | -0.0046 | [-0.0166, 0.0089] | 1.00000 | -0.0032 | [-0.0074, 0.0009] | 1.00000 | 5/11 |
| Joy | 0.0036 | [-0.0109, 0.0203] | 1.00000 | 0.0041 | [-0.0005, 0.0097] | 1.00000 | 1/11 |
| Love | -0.0009 | [-0.0503, 0.0434] | 1.00000 | 0.0045 | [-0.0108, 0.0201] | 1.00000 | 8/11 |
| Sadness | 0.0022 | [-0.0208, 0.0292] | 1.00000 | -0.0062 | [-0.0143, 0.0021] | 1.00000 | 4/11 |
| Anger | -0.0037 | [-0.0210, 0.0175] | 1.00000 | 0.0010 | [-0.0052, 0.0069] | 1.00000 | 4/11 |

0 of the 22 January-2020 score/model combinations have either primary
break term passing global BY. The original unadjusted toxicity slope change is
-0.0505/year (absolute rank 1/11),
but becomes -0.0059/year after additive genre adjustment
(rank 4/11). Several large-looking
unadjusted changes weaken markedly after genre adjustment. This makes composition
a substantive explanation to investigate, not proof of a causal mechanism.

Ten fixed historical alternatives use identical windows; they overlap and provide
coarse descriptive ranks. A first-place rank among eleven dates is not an
independent significance test. March-2020, rank-weighted, confidence-restricted
and quadratic-background alternatives are all retained in the sensitivity table.
No most-dramatic alternative is promoted to a prespecified result.

All genre-adjusted 2020 intervals also include zero under the 12- and 36-month
crossed-block sensitivities. Artist-only or calendar-only sensitivities exclude
zero for some terms; neither accounts for both dependence sources, and these
diagnostic intervals are not multiplicity-corrected discoveries.

The results do not support a reliable, genre-independent COVID-breakpoint claim.
There are only six post-2020 years and few effective two-year calendar blocks.
Artist-credit dependence, non-linear historical trends, changing coverage, genre
classification and concurrent events limit causal and breakpoint interpretation.

## 6. Statistical status and validation

One global BY family contains all **715** prespecified primary terms. **23**
pass q≤0.05; this does not make the analysis independently confirmed.

| Family | Primary terms | Global BY passes |
| --- | --- | --- |
| breakpoint | 484 | 0 |
| decomposition | 231 | 23 |

The uniform refinement from 999 to 9,999 resamples is documented in the
[precision audit](precision_audit.json); all original coarse tests are retained.
No candidate-specific precision refinement occurred. Crossed artist/calendar
resampling preserves repeated songs within exact artist credits and models
short-range temporal dependence. Separate 12-/36-month, artist-only and calendar-
only sensitivities and HAC intervals are published. Neither this approximate
resampling scheme nor BY eliminates selection bias or classifier measurement error.
For all five legacy content-score increases, marginal total-change intervals
remain positive in each of the four dependence sensitivities; this does not
upgrade the sexual-content or violence results to corrected significance.

All **882** weighted comparisons reconcile; maximum absolute arithmetic discrepancy
is 2.22e-16.
Independent direct weighted means and the two reference-period paths agree.
The analysis contains **79,194 distinct song-months**, **27,039 song identities**,
and **9,558 exact artist credits** across 1960–2025. All protected source and prior
artifact hashes match. No dataset, score, genre or earlier result was rewritten.
The full precision analysis took **311.7 seconds** with peak
process RSS **988.0 MiB**; test/render time is separate.

## 7. Figures and term-paper recommendations

| Figure | Use |
| --- | --- |
| [01_historical_trajectories](figures/01_historical_trajectories.svg) | Annual complete-case trajectories for all eleven named dimensions |
| [02_genre_trajectories](figures/02_genre_trajectories.svg) | Four dimensions and six genres selected by overall population counts; sparse years remain gaps |
| [03_decomposition_legacy](figures/03_decomposition_legacy.svg) | Exact symmetric components; total-change intervals use crossed artist/calendar resampling |
| [04_genre_contributions](figures/04_genre_contributions.svg) | Every original genre; common color scale; signed contributions can offset |
| [05_genre_shares_and_coverage](figures/05_genre_shares_and_coverage.svg) | Changing representation and uneven score coverage; six individual series plus explicitly grouped remainder |
| [06_weighting_missingness_sensitivity](figures/06_weighting_missingness_sensitivity.svg) | Percent shares are not invariant to weighting; bound intervals are assumptions, not confidence intervals |
| [07_breakpoint_2020](figures/07_breakpoint_2020.svg) | Prespecified level and slope changes, with and without additive genre adjustment |
| [08_historical_placebo_comparison](figures/08_historical_placebo_comparison.svg) | Identical six-year-before/six-year-after windows at eleven fixed dates |

Lead with the legacy decomposition and all-genre contributions, then show weighting
and missingness sensitivity. Use the 2020 forest plot alongside its historical
placebo comparison so a large raw change is not presented without context.
The trajectory panels establish the broader, non-monotonic history.

The defensible conclusion is that large long-run observed changes reflect both
within-genre movement and changing representation, with the within component
usually larger in the legacy comparison. Exact percentages depend on weighting
and coverage. A distinctive, genre-independent 2020 disruption is not established.
No additional data acquisition or discovery campaign was launched.
