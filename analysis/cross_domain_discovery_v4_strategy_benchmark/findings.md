# Measured strategy findings

**Recommendation: E: None.** No measured policy jointly meets the prespecified per-family recall, null-behavior and full-universe resource criteria. A hybrid has not been benchmarked and is not presented as a proven solution.

The policies are compared under the same elapsed-time allowance and model families. The 4,096-combination cap is a safety ceiling; partial prefixes at the time boundary remain valid, explicitly counted benchmark outcomes. The initial 96-candidate attempt was archived during calibration before final scoring; it is excluded from comparison results but included in resource accounting. No search heuristic was retuned on final synthetic outcomes.

## Recovery is mechanism-specific

| Stable mechanism | A | B | C |
| --- | ---: | ---: | ---: |
| linear | 66.7% | 8.3% | 2.8% |
| nonlinear | 47.2% | 19.4% | 22.2% |
| interaction | 0.0% | 0.0% | 0.0% |
| conditional | 25.0% | 0.0% | 0.0% |
| temporal | 83.3% | 0.0% | 0.0% |

These family-level rates credit complete source-family support, including redundant proxies; they are more permissive than exact variable identification. The detailed table reports both. The [oracle diagnostics](oracle_diagnostics.csv) expose fit status, support and later-period performance; passing that empirical gate is distinct from theoretical model representability. A model containing only part of a multivariable mechanism may have real predictive value while failing the complete-mechanism precision criterion. Conversely, shared family membership alone is insufficient: the frozen model must pass later-period skill, support, uncertainty and independent calibration gates.

All adjusted-monthly searches produced empty selections. The [estimator audit](estimator_limitations.json) independently checks training control ranks in a real case and a final synthetic case across all four folds: rank 18 of 19. A zero genre-share control is present in the synthetic template; the real example has a linear dependency among controls. The strict full-rank rule therefore blocks candidate qualification throughout this path. This is a shared estimator limitation, not evidence that each search policy independently missed those mechanisms. The overall table retains these failed experiments; oracle-conditional results separate them. The interaction and resource failures also occur outside this path, so repairing it alone would not establish a production solution.

Additive OLS cannot represent a centered pure product in general. The polynomial path includes pair/triple products and squares, but cannot represent arbitrary oscillatory or threshold relationships. Hidden-oracle fits measure achievable transfer using the same data, preprocessing and assessment. The explicitly labelled oracle-conditional recall column excludes cases failing that empirical gate; the overall results retain them. A failed oracle check can also reflect missingness, noise, rank deficiency or inadequate support. Regime flips are unstable-control cases, not failures to find a stable relationship.

## Previously validated observational references

| Strategy | Reference tasks | Sampled family recovery | Selected family recovery | Calibrated family recovery | Oracle transfer pass fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 5 | 0.0% | 0.0% | 0.0% | 40.0% |
| B | 5 | 13.3% | 0.0% | 0.0% | 40.0% |
| C | 5 | 13.3% | 0.0% | 0.0% | 40.0% |

These rates use the union of the two estimators within each seeded search. The five reference tasks were selected mechanically from earlier provenance-separated, positive-every-period results. They are observations from previously inspected data, not causal ground truth or independent confirmation. The oracle column tests whether their original predictor support passes this benchmark's transfer and uncertainty requirements; it does not assume that previous validation guarantees success under every new criterion.

## Null and shared-trend behavior

| Strategy | Control | Track | Worlds with any accepted model | Rate | 95% Wilson interval |
| --- | --- | --- | ---: | ---: | ---: |
| A | null | adjusted | 0/6 | 0.0% | 0.0%–39.0% |
| A | null | raw | 1/6 | 16.7% | 3.0%–56.4% |
| A | spurious_trend | adjusted | 2/6 | 33.3% | 9.7%–70.0% |
| A | spurious_trend | raw | 6/6 | 100.0% | 61.0%–100.0% |
| B | null | adjusted | 0/6 | 0.0% | 0.0%–39.0% |
| B | null | raw | 0/6 | 0.0% | 0.0%–39.0% |
| B | spurious_trend | adjusted | 2/6 | 33.3% | 9.7%–70.0% |
| B | spurious_trend | raw | 6/6 | 100.0% | 61.0%–100.0% |
| C | null | adjusted | 0/6 | 0.0% | 0.0%–39.0% |
| C | null | raw | 1/6 | 16.7% | 3.0%–56.4% |
| C | spurious_trend | adjusted | 2/6 | 33.3% | 9.7%–70.0% |
| C | spurious_trend | raw | 6/6 | 100.0% | 61.0%–100.0% |

The unit is a complete world, taking the maximum over three search seeds and both estimators; repeated seeds are not independent null samples. Calibration uses 24 separate development-null variants from 12 generator seeds; raw and adjusted variants are paired, not independent. Each reported final track/control has six independent generator seeds. The intervals are consequently wide. Raw shared trends can predict well without providing a nontrivial mechanism. Adjusted results and the trend controls are needed to distinguish this failure from ordinary null overfitting. No real-data false-discovery rate is identified from these simulations.

## Coverage, stability and resource limits

All original eligibility rules are preserved. The task ledger distinguishes the full 10,097-task universe from the bounded real-data sample. Domain inclusion, unique-variable coverage and estimable-model coverage are different quantities. Semantic blocks remain available even where sample size or the bounded polynomial encoder prevents a fitted model. Domain and feature-family exposure tables, near-duplicate signatures and search-progress-quartile distributions expose concentration rather than hiding it in a single score.

Seed stability is measured by exact-variable and family-signature Jaccard overlap of the frozen selected sets. Two empty sets receive Jaccard 1 by convention; the comparison table also reports their count and a mean excluding those pairs. Historical stability is measured on two later periods, with mean period-score ranges and 24-month/credit-or-genre resampling diagnostics. High overlap can reflect repeatedly finding obvious relationships and is not evidence of novelty. Different exact variants from the same family can yield low exact overlap but higher family overlap.

| Strategy | Projected full-target hours | Measured-rate storage projection (GB) | Safety-cap storage envelope (GB) |
| --- | ---: | ---: | ---: |
| A | 33.79 | 67.73 | 103.24 |
| B | 31.68 | 63.54 | 103.24 |
| C | 31.70 | 56.72 | 103.24 |

These projections target all 10,097 original tasks with one search seed, both model families, the same per-target time allowance and three later-assessed models per family. They use the 90th-percentile measured real-task cost per population/track, pay full preparation per target, and add a 1.5× runtime allowance plus 900 seconds. No unmeasured cohort-sharing or parallel speedup is assumed. Storage uses measured checkpoint bytes per combination and 90th-percentile observed candidate counts, with a separate cap envelope. They are extrapolations, not measured full-campaign costs or guarantees. A hard four-hour/15 GB stop can leave coverage incomplete.

No production configuration is presented as solved when recall or the resource gate fails. A justified future optimization would need its own bounded, blind benchmark; a hybrid assembled after inspecting these final worlds would need new worlds for evaluation. Neither manual variable shortlisting nor dropping difficult signal families is an acceptable way to claim success.
