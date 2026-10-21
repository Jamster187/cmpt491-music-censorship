# Full Phase 1 relationship-discovery findings

**Exploratory full search, not independent confirmation or causation.** All
9,159 approved candidates were attempted: 2,775 pairwise, 3,192 nonlinear and
3,192 genre interactions. Previous analyses and datasets remain unchanged.
No additional discovery family was launched.

## Execution and evidence

The run performed 279,725 fitting calls and evaluated 9,159
primary candidate hypotheses in 64.59 minutes
of execution-session wall time (63.76 minutes
inside candidate calculations). Peak process RSS was
730.9 MiB. All candidate checkpoints
were retained. See [execution accounting](full_phase1/execution.json) and
[validation](full_phase1/validation.json). Replay and artist-sensitivity refits
are additional validation/interpretation work, recorded separately.

| Family | Candidates | Fits | Global BY ≤0.05 | Non-reconstruction BY | Priority cross-domain BY | Positive/stable performance tier | Negative outer R² |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pairwise | 2775 | 0 | 1331 | 1321 | 485 | 0 | 0 |
| nonlinear | 3192 | 254189 | 1342 | 1336 | 346 | 709 | 2071 |
| genre_interaction | 3192 | 25536 | 256 | 255 | 142 | 159 | 1408 |

Global Benjamini–Yekutieli adjustment used all **9,159** candidates, including
reconstruction controls and unavailable tests at p=1. **2,929** candidates
meet the exploratory global q≤0.05 threshold. This is the denominator for this
approved campaign, not an omnibus correction over every previous project
analysis. No hypothesis is independently confirmed. The fixed permutation
resolution, artist dependence, overlapping training histories and selection
uncertainty remain limitations; a low q-value is not proof of scientific novelty.

Raw p-values, global and family q-values, uncertainty and failed/null rows are in
the three [complete result tables](full_phase1/README.md). All secondary measures,
subgroup comparisons and signs are descriptive. Exact frozen support rules and
[methodology](full_phase1/methodology.md) are unchanged.

## What the rankings mean

Statistical evidence, predictive usefulness and scientific interest are different.
Predictive presentation rows first require positive pooled absolute R² and mean-baseline
skill, improvement in all four periods, and a positive temporal interval lower
bound. Within that tier, worst-period relative improvement precedes the lower
interval bound. Rows outside the tier remain in the complete rankings. This
presentation order does not choose/refit models using outer outcomes.
The positive/stable tier is a presentation screen, not a practical-usefulness
threshold. Tiny positive R² or error reductions can still be of little use.
It does not require positive R² within every period. For the leading calendar-to-
duration example, all four period-specific R² values are negative despite pooled
R² 0.0756; pooling includes between-period variation. Its large gain over
an extrapolating linear baseline does not establish useful within-period prediction.

Pairwise effects are ranked within their own effect type. The cross-domain table
below is a fixed coverage shortlist: five numerical associations, two categorical
associations, three predictive relationships. These blocks do not have a common
magnitude scale. Affect–content classifier comparisons remain in the original
C category but are excluded from this **priority cross-domain shortlist**.
All charts and ranks are descriptive post-hoc selections from the complete run.

For numerical pairwise rows, effect is pooled Spearman rho and the interval is a
two-year block interval. Categorical rows use eta-squared or corrected Cramér's V.
Their primary permutation statistic conditions on debut year and can differ from
the displayed pooled effect. Predictive effect is the equal-two-year-block mean
loss reduction divided by training target variance; it is **not** the MSE-gain
percentage. R², comparison R² and MSE gain use equal-song outer losses.

## Ten cross-domain presentation relationships

| ID | Target | Predictor | Family | Category | N | Effect | 95% temporal block interval | Outer R² | Comparison R² | MSE gain % | Global BY q | Positive-period/annual-sign fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42a76ca99294178bbdac | mb_release_count | best_chart_rank | pairwise | C | 21871 | -0.4818 | [-0.5124, -0.4534] | — | — | n/a | 0.03125 | 1.00 |
| 1255df89825bc66bac71 | total_chart_points | mb_release_count | pairwise | C | 21871 | 0.4517 | [0.4251, 0.4777] | — | — | n/a | 0.03125 | 1.00 |
| d82a5870464c6537c149 | mb_recording_count | best_chart_rank | pairwise | C | 21871 | -0.3542 | [-0.3876, -0.3193] | — | — | n/a | 0.03125 | 1.00 |
| e449f4900f6c7f9a02b9 | mb_distinct_duration_count | best_chart_rank | pairwise | C | 21871 | -0.3458 | [-0.3829, -0.3034] | — | — | n/a | 0.03125 | 1.00 |
| 4845e6ae2673f26c7dce | weekly_observation_count | mb_release_count | pairwise | C | 21871 | 0.3431 | [0.3093, 0.3846] | — | — | n/a | 0.03125 | 1.00 |
| cbf9d771aa2cc4f9962f | primary_genre | detox_obscene | pairwise | C | 20597 | 0.4936 | [0.4061, 0.5554] | — | — | n/a | 0.03125 | — |
| e4778fe15c92d42cd876 | primary_genre | detox_toxicity | pairwise | C | 20597 | 0.3889 | [0.2677, 0.4649] | — | — | n/a | 0.03125 | — |
| ee05f1faa5c56965d221 | mb_duration_median_seconds | first_snapshot_month | nonlinear | C | 9848 | 1.0555 | [0.8223, 1.2925] | 0.0756 | -1.6458 | 65.06 | 0.00351 | 1.00 |
| 7fb9a3d4d574bd088eb6 | mb_duration_median_seconds | last_snapshot_month | nonlinear | C | 9848 | 1.0671 | [0.8341, 1.3437] | 0.1015 | -1.6392 | 65.96 | 0.00351 | 1.00 |
| 77fec98ca2d7cbd8c70a | mb_duration_median_seconds | first_chart_date | nonlinear | C | 9848 | 1.0557 | [0.8057, 1.2728] | 0.0763 | -1.6455 | 65.08 | 0.00558 | 1.00 |

## Ten nonlinear presentation relationships

| ID | Target | Predictor | Family | Category | N | Effect | 95% temporal block interval | Outer R² | Comparison R² | MSE gain % | Global BY q | Positive-period/annual-sign fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cfaad9e0a36407488acb | detox_toxicity | detox_severe_toxicity | nonlinear | B | 8915 | 2.1285 | [1.8065, 2.4705] | 0.8879 | 0.1581 | 86.68 | 0.00351 | 1.00 |
| 62fbcd241ef4bdde9414 | detox_obscene | detox_severe_toxicity | nonlinear | B | 8915 | 4.3937 | [3.5330, 5.5902] | 0.8944 | 0.2867 | 85.20 | 0.00558 | 1.00 |
| ee05f1faa5c56965d221 | mb_duration_median_seconds | first_snapshot_month | nonlinear | C | 9848 | 1.0555 | [0.8223, 1.2925] | 0.0756 | -1.6458 | 65.06 | 0.00351 | 1.00 |
| 7fb9a3d4d574bd088eb6 | mb_duration_median_seconds | last_snapshot_month | nonlinear | C | 9848 | 1.0671 | [0.8341, 1.3437] | 0.1015 | -1.6392 | 65.96 | 0.00351 | 1.00 |
| 77fec98ca2d7cbd8c70a | mb_duration_median_seconds | first_chart_date | nonlinear | C | 9848 | 1.0557 | [0.8057, 1.2728] | 0.0763 | -1.6455 | 65.08 | 0.00558 | 1.00 |
| 7acef6a742b46e97698a | mb_duration_median_seconds | last_chart_date | nonlinear | C | 9848 | 1.0661 | [0.8180, 1.2910] | 0.1012 | -1.6378 | 65.93 | 0.00772 | 1.00 |
| b09dac08bd739affe3a7 | ll_explicit_language | detox_severe_toxicity | nonlinear | B | 8915 | 1.4781 | [1.3300, 1.6035] | 0.5232 | -0.1757 | 59.44 | 0.00351 | 1.00 |
| 25ffaf8b240434fb83dc | detox_severe_toxicity | detox_obscene | nonlinear | B | 8915 | 9.2756 | [4.5407, 15.3692] | 0.6768 | 0.3789 | 47.95 | 0.00558 | 1.00 |
| d377549f5ed7211e63d3 | emotion_grief | emotion_remorse | nonlinear | B | 8915 | 0.2119 | [0.1841, 0.2401] | 0.4169 | -0.0038 | 41.91 | 0.00351 | 1.00 |
| c529d3628bad611de935 | emotion_sadness | emotion_remorse | nonlinear | B | 8915 | 0.2295 | [0.1975, 0.2662] | 0.4222 | 0.0232 | 40.85 | 0.00351 | 1.00 |

Category B rows are related measurements, often classifier overlap; they are useful
model-behavior demonstrations, not major independent musical discoveries.
Some original-category C content–affect pairs also share the same lyrics and
classification pipeline. The complete tables explicitly flag shared lyrical
measurement; C alone is not evidence of independent measurement or novelty.

## Ten genre-interaction presentation relationships

| ID | Target | Predictor | Family | Category | N | Effect | 95% temporal block interval | Outer R² | Comparison R² | MSE gain % | Global BY q | Positive-period/annual-sign fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 869074148b3574f9dae8 | mb_distinct_duration_count | mb_recording_count | genre_interaction | B | 9886 | 0.0024 | [0.0016, 0.0033] | 0.9655 | 0.9572 | 19.44 | 0.00772 | 1.00 |
| cac276674aed61916df2 | detox_obscene | detox_toxicity | genre_interaction | B | 8915 | 0.7188 | [0.5225, 0.9201] | 0.8075 | 0.7353 | 27.30 | 0.00351 | 1.00 |
| ba117702853f6d74878a | detox_identity_attack | detox_toxicity | genre_interaction | B | 8915 | 1.4535 | [1.0793, 1.9246] | 0.5080 | 0.3628 | 22.78 | 0.00351 | 1.00 |
| 59b5f45beffcbbdae4f5 | mb_recording_count | mb_distinct_duration_count | genre_interaction | B | 9886 | 0.0020 | [0.0014, 0.0026] | 0.9652 | 0.9568 | 19.58 | 0.00351 | 1.00 |
| ac8fb04fcb9f5569401d | detox_identity_attack | detox_insult | genre_interaction | B | 8915 | 1.6223 | [1.1117, 2.1384] | 0.6171 | 0.4256 | 33.35 | 0.00351 | 1.00 |
| c207d33d6603f9722b5e | mb_recording_count | mb_release_count | genre_interaction | B | 9886 | 0.0152 | [0.0106, 0.0206] | 0.1817 | 0.1161 | 7.42 | 0.00351 | 1.00 |
| 28ee9734fb60806a6756 | mb_distinct_duration_count | mb_release_count | genre_interaction | B | 9886 | 0.0135 | [0.0085, 0.0181] | 0.2085 | 0.1612 | 5.64 | 0.00351 | 1.00 |
| fe4daee52cc2bee66e20 | detox_obscene | detox_insult | genre_interaction | B | 8915 | 0.5147 | [0.3894, 0.6749] | 0.6456 | 0.5856 | 14.47 | 0.00351 | 1.00 |
| 6283a8bc2226eb18fe67 | detox_identity_attack | emotion_anger | genre_interaction | C | 8915 | 0.4614 | [0.2290, 0.6813] | 0.3648 | 0.3183 | 6.82 | 0.03125 | 1.00 |
| b3735c5f181fd89d09d8 | emotion_love | emotion_neutral | genre_interaction | B | 8915 | 0.0229 | [0.0180, 0.0286] | 0.2769 | 0.2426 | 4.54 | 0.00351 | 1.00 |

Genre models compare genre-specific slopes against the same predictor plus genre
main effects. Adequate support is determined from training only. A positive gain
can coexist with poor absolute prediction. Complete held-out genre coverage and
four-period metrics are available through the classroom demo.

## Substantive examples beyond shared measurements

The top raw rankings above deliberately retain related classifiers and metadata
counts. The following examples use the same existing order, restricted to
(1) broader-domain genre interactions and (2) metadata predicting chart outcomes.
These are disclosed post-hoc presentation choices, with no additional hypotheses.

| ID | Target | Predictor | Family | Category | N | Effect | 95% temporal block interval | Outer R² | Comparison R² | MSE gain % | Global BY q | Positive-period/annual-sign fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7e02554737b82c7c4df6 | detox_insult | mb_recording_count | genre_interaction | C | 8915 | 0.0383 | [0.0221, 0.0539] | 0.3206 | 0.3031 | 2.51 | 0.00558 | 1.00 |
| d1418f32d03c3f37147b | total_chart_points | mb_release_count | nonlinear | C | 11440 | 0.0996 | [0.0814, 0.1172] | 0.0467 | 0.0074 | 3.96 | 0.00351 | 1.00 |

The metadata-to-chart example has only modest absolute performance despite its
strong pooled pairwise association: nonlinear R² 0.0467,
MSE gain 3.96%, with all four periods
improving on OLS. Catalog release counts can accumulate after a song succeeds;
this is retrospective prediction, not a deployable debut-time popularity forecast.
The broader-domain genre interaction improves MSE by
2.51% over the additive model,
with worst-period gain 0.65%.
Its absolute R² includes genre main effects. It does not establish that catalog
counts cause lyrical content. Both examples have separate artist-credit checks.

## Sign reversals, attenuation and historical consistency

The following are descriptive candidates, with no new subgroup significance claim.
Opposed genre signs require adequate genres with rho ≤−0.10 and ≥+0.10. A pooled
to adjusted reversal requires |pooled rho|≥0.10 and |adjusted rho|≥0.05. Attenuation
means |adjusted rho|≤25% of |pooled rho| with |pooled rho|≥0.10. These are disclosed
presentation cutoffs, not evidence of a causal Simpson's paradox.
Chart weeks and weekly-observation counts are aliases here; their repeated rows
represent the same substantive pattern, not independent discoveries.

| Target | Predictor | Period | Pooled rho | Genre-adjusted rho | Reversal | Attenuation | Most negative adequate genre | Most positive adequate genre |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| weekly_observation_count | detox_obscene | [2018, 2026] | -0.1634 | 0.0532 | True | False | Latin -0.0238 (N=162) | R&B / Soul 0.1722 (N=152) |
| detox_obscene | chart_weeks | [2018, 2026] | -0.1634 | 0.0532 | True | False | Latin -0.0238 (N=162) | R&B / Soul 0.1722 (N=152) |
| detox_insult | weekly_observation_count | [2018, 2026] | -0.1618 | 0.0523 | True | False | Latin -0.0549 (N=162) | R&B / Soul 0.1945 (N=152) |
| chart_weeks | detox_insult | [2018, 2026] | -0.1618 | 0.0523 | True | False | Latin -0.0549 (N=162) | R&B / Soul 0.1945 (N=152) |
| chart_weeks | detox_toxicity | [2018, 2026] | -0.1593 | 0.0546 | True | False | Latin -0.0546 (N=162) | R&B / Soul 0.1997 (N=152) |
| weekly_observation_count | detox_toxicity | [2018, 2026] | -0.1593 | 0.0546 | True | False | Latin -0.0546 (N=162) | R&B / Soul 0.1997 (N=152) |
| detox_sexual_explicit | chart_weeks | [2018, 2026] | -0.1294 | 0.0739 | True | False | Latin -0.0622 (N=162) | Pop 0.1645 (N=422) |
| detox_sexual_explicit | weekly_observation_count | [2018, 2026] | -0.1294 | 0.0739 | True | False | Latin -0.0622 (N=162) | Pop 0.1645 (N=422) |
| snapshot_months_selected | detox_obscene | [2018, 2026] | -0.1387 | 0.0541 | True | False | Latin 0.0014 (N=162) | R&B / Soul 0.1634 (N=152) |
| detox_toxicity | snapshot_months_selected | [2018, 2026] | -0.1336 | 0.0572 | True | False | Latin -0.0330 (N=162) | R&B / Soul 0.1952 (N=152) |

All four historical windows are shown for every predictive candidate. They are
reused observations, not four independent confirmation studies. A stable sign
alone does not guarantee useful predictions. No breakpoint or 2020 effect was
newly tested in Phase 1.

Substantial sign changes across the same four approved windows are shown below.
Each displayed window has at least 200 complete pairs; both signs must reach
absolute rho 0.10. Changing genre composition and coverage can contribute.

| Target | Predictor | Negative period | Negative rho | Positive period | Positive rho |
| --- | --- | --- | --- | --- | --- |
| mb_release_count | emotion_love | [1990, 2000] | -0.1286 | [2018, 2026] | 0.1696 |

## Null and generalization results

The following summary retains all 42 lyric predictors for every eligible chart
outcome, including weak and adverse results. “No BY evidence” means this analysis
did not establish the specified improvement; it does not establish no association.
Genre-interaction R² includes genre main effects as well as the lyric predictor;
it cannot be attributed to lyrics alone. Its improvement compares with the same
lyric predictor plus genre main effects, isolating the additional genre slopes.

| Family | Chart target | Lyric predictors | Global BY passes | Positive R² | Positive/stable performance tier | Best R² | Median R² | Median MSE gain % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nonlinear | chart_weeks | 42 | 6 | 0 | 0 | -0.1314 | -0.1361 | 0.02 |
| nonlinear | snapshot_months_selected | 42 | 7 | 0 | 0 | -0.1504 | -0.1564 | 0.06 |
| nonlinear | total_chart_points | 42 | 7 | 0 | 0 | -0.0382 | -0.0414 | 0.07 |
| nonlinear | weekly_observation_count | 42 | 6 | 0 | 0 | -0.1314 | -0.1361 | 0.02 |
| genre_interaction | chart_weeks | 42 | 0 | 0 | 0 | -0.1271 | -0.1383 | 0.02 |
| genre_interaction | snapshot_months_selected | 42 | 0 | 0 | 0 | -0.1428 | -0.1536 | 0.00 |
| genre_interaction | total_chart_points | 42 | 0 | 0 | 0 | -0.0371 | -0.0440 | -0.01 |
| genre_interaction | weekly_observation_count | 42 | 0 | 0 | 0 | -0.1271 | -0.1383 | 0.02 |

3,479 predictive candidates have
negative pooled outer R². Their values and period failures remain visible.
Calendar targets and extreme extrapolations can produce large relative gains from
an even worse linear comparator. They must not be described as successful prediction.

These models have positive pooled R² and positive pooled improvement, yet worsen
comparison MSE by more than 5% in at least one outer period. Pooled success alone
therefore does not establish historical consistency.

| Target | Predictor | Family | Pooled R² | Pooled MSE gain % | Worst-period gain % | Global BY q |
| --- | --- | --- | --- | --- | --- | --- |
| mb_distinct_duration_count | first_chart_date | nonlinear | 0.1357 | 1.74 | -100.64 | 1.00000 |
| mb_distinct_duration_count | first_snapshot_month | nonlinear | 0.1366 | 1.86 | -95.69 | 1.00000 |
| detox_insult | first_chart_date | genre_interaction | 0.3135 | 0.86 | -33.56 | 1.00000 |
| detox_insult | first_snapshot_month | genre_interaction | 0.3136 | 0.89 | -33.42 | 1.00000 |
| detox_insult | last_snapshot_month | genre_interaction | 0.3146 | 1.06 | -32.33 | 1.00000 |

## Artist-credit sensitivity

29 selected leading relationships were checked with 499 exact-artist-credit
cluster bootstrap replicates, retaining fitted models and the original effect
weighting. Selection was post-hoc; these checks have no new p-values or q-values.
See [all artist checks](full_phase1/artist_sensitivity.csv). The temporal interval
and artist interval are separate sensitivities, not a joint dependence correction.

| Candidate | Family | Exact credits | Largest credit share | Artist interval | Training-seen artist share |
| --- | --- | --- | --- | --- | --- |
| 42a76ca99294178bbdac | pairwise | 7442 | 0.006 | [-0.4964, -0.4670] | — |
| 1255df89825bc66bac71 | pairwise | 7442 | 0.006 | [0.4337, 0.4688] | — |
| d82a5870464c6537c149 | pairwise | 7442 | 0.006 | [-0.3710, -0.3362] | — |
| e449f4900f6c7f9a02b9 | pairwise | 7442 | 0.006 | [-0.3639, -0.3273] | — |
| 4845e6ae2673f26c7dce | pairwise | 7442 | 0.006 | [0.3229, 0.3636] | — |
| cbf9d771aa2cc4f9962f | pairwise | 7025 | 0.007 | [0.4609, 0.5233] | — |
| e4778fe15c92d42cd876 | pairwise | 7025 | 0.007 | [0.3572, 0.4197] | — |
| ee05f1faa5c56965d221 | nonlinear | 4280 | 0.014 | [1.0051, 1.1052] | 0.296 |
| 7fb9a3d4d574bd088eb6 | nonlinear | 4280 | 0.014 | [1.0134, 1.1189] | 0.296 |
| 77fec98ca2d7cbd8c70a | nonlinear | 4280 | 0.014 | [1.0050, 1.1107] | 0.296 |
| cfaad9e0a36407488acb | nonlinear | 4018 | 0.016 | [1.8751, 2.4307] | 0.296 |
| 62fbcd241ef4bdde9414 | nonlinear | 4018 | 0.016 | [3.5403, 5.4568] | 0.296 |

Exact credit strings preserve the dataset's identity convention. Collaborations
and spelling variants can split the same person across clusters. These checks do
not solve all artist dependence, refit uncertainty, temporal dependence or prior
data inspection.

## Eight presentation recommendations

1. Show the numerical pairwise cross-domain example in the first table row, its
   calendar-conditioned null, and its artist sensitivity. Explain why association
   with accumulated metadata is not a debut-time forecast.
2. Show the two categorical cross-domain examples to demonstrate appropriate
   genre/category comparisons without arbitrary integer distances.
3. Compare **total_chart_points ← mb_release_count** against
   its stronger-looking pooled association: outer R² 0.0467,
   MSE gain 3.96%. Discuss retrospective accumulation.
4. Show **detox_insult ← mb_recording_count × genre**:
   outer R² 0.3206, additive R² 0.3031.
   Display supported genre slopes, the modest extra gain and all four periods.
5. Show **mb_duration_median_seconds ← first_snapshot_month** as an example of a large
   baseline improvement with weak absolute performance. Its pooled R² is
   0.0756, but each individual period has negative R².
6. Use one aggregate/genre-adjusted example above to explain aggregation effects;
   call it a descriptive candidate, not a proven paradox or causal effect.
7. Use the lyric-to-chart null table to explain why extensive search and nonlinear
   flexibility need not produce a useful measure of commercial success.
8. Show the descriptive release-count/love-score sign change between 1990–1999
   and 2018–2025. Discuss coverage and composition; no COVID breakpoint was tested.

The strongest classifier-to-classifier nonlinear curve is a supporting method
demonstration only. Its predictive performance is not an independent musical discovery.

The 6 [selected figures](full_phase1/figure_index.json) are generated from saved
curves, replayed fitted predictions and recorded subgroup statistics. The
[classroom demo](full_phase1/README.md) exposes complete results, cross-domain
filters, actual effect sizes, uncertainty and warnings.

## Limitations and next work

The sample is Billboard-charting songs, not all music. Missing lyrics/enrichment,
linked-metadata coverage, changing genre composition and classifier measurement
error can all shape associations. Counts and whole-career outcomes can encode
exposure and retrospective accumulation. Whole-window purging removes boundary-
crossing and ongoing chart runs, changing cohort composition and potentially
underrepresenting recent long-running hits. Broadly different domains can still
share metadata, artists or classification inputs. No reclassification or dataset changes
were made. Confidence intervals hold selected models fixed and do not include
full model-selection uncertainty. The existing data have been inspected repeatedly.

Prioritize a bounded, explicitly approved follow-up on stable priority cross-domain and
aggregation candidates with stronger artist/time dependence handling and a frozen
replication plan. Historical stratification is a more directly motivated next
step than the very large numeric/threshold interaction universes; choose its
scope and correction family before running. Numeric interactions should require
a separate runtime/statistical design decision. **Neither follow-up was launched.**
