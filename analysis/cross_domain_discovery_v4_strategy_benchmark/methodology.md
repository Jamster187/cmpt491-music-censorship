# Methods and interpretation

The exact protocol, allocation, hidden-truth construction, estimators, chronology, uncertainty and error-calibration rules are in [benchmark_design.md](benchmark_design.md) and [protocol.json](protocol.json). The original [V4 source and eligibility definitions](../cross_domain_discovery_v4/methodology.md) and [hierarchical checkpoint](../cross_domain_discovery_v4_hierarchical/README.md) remain unchanged.

## Search versus model-family failure

A candidate is an exact original predictor set of size one, two or three, paired with an estimator. Categorical/embedding encodings do not become separately selectable scalar variables. Algebraic reconstructions are excluded by the original graph/hypergraph rules. Same-family redundancy, shared source, cross-domain and target-provenance-separated categories remain explicit; all-source disjointness is a separate stronger flag. None of these metadata categories establishes statistical independence.

A uses exhaustive Pearson/Spearman and quantile eta-squared screening within visited tasks. These are training-era ranking diagnostics, not IID significance tests. A wide block's maximum-column score can be optimistic; null calibration and held-out assessment expose that selection effect. B preserves exact conditional random-draw probabilities within structural strata; these are not unconditional inclusion probabilities. C's adaptive inclusion probabilities are unknown and are labelled as such. Its exploitation decisions use only early-fold validation rewards and worst-period behavior.

Polynomial products expand representational capacity, as illustrated by the [PolynomialFeatures documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.PolynomialFeatures). This implementation uses its explicitly declared subset of polynomial terms and is not a universal nonlinear model. Every sampled combination is attempted with both estimators; unsupported width, rank deficiency and inadequate degrees of freedom remain attempted failures. The same hidden mechanism is fitted by an oracle after search freeze to separate missing a candidate from inability to represent it.

## Temporal and clustered uncertainty

Training-only preprocessing and the fixed 84-month embargo preserve chronological separation. Whole-song IDs do not cross the song-level split. Month and genre-month views retain their original weighting and repeated source observations. Repeated economic values across songs are not treated as independent replicates for uncertainty: all observations in a 24-month calendar block move together, jointly with exact artist-credit clusters for song rows or genre clusters for the panel. Exact credits are not resolved individual musicians, so collaboration dependence can remain.

The crossed resampling follows the principle of the [pigeonhole bootstrap](https://doi.org/10.1214/07-AOAS122), but a fixed 24-month block choice and a small number of clusters are approximations. Native reference periods and minimum support remain visible. These diagnostic intervals condition on fitted/selected models, do not refit every resample, and are not valid post-selection confidence sets. Their role is to penalize fragile transfer, not to certify discoveries.

## Multiplicity and adaptation

Earlier analyses inspected the historical evaluation years. Later-fold performance is chronological transfer evidence, not independent confirmation. The [adaptive-data-analysis literature](https://arxiv.org/abs/1506.02629) explains why adaptively chosen hypotheses cannot inherit ordinary unselected-test guarantees. This benchmark does not claim to implement its differential-privacy guarantees.

All attempted candidates and unsuccessful outcomes remain in private checkpoints. Calibration reruns the complete policy and selection procedure on independent null worlds, then takes its maximum across both estimators and all search seeds. The order-statistic rule is fixed before final scoring. Calibration variants share generator seeds across raw/adjusted tracks; no independent-exchangeable-sample guarantee is claimed. Final null and shared-trend controls measure the observed acceptance behavior. This is a multiplicity safeguard for the simulated procedure, not a general FWER/FDR theorem for dependent music/economic data. No adjusted p-values are calculated over only successful selections; no p-values are used to label scientific discoveries.

Synthetic precision means recovery of the complete injected mechanism or declared redundant source families among accepted models. It is not causal precision on real data. Real observational reference models establish reproducibility of previously observed relationships, not truth about causal mechanisms. Background families, missingness and genre/temporal dependence are deliberately retained or approximated; there is no claim that a finite synthetic suite spans every possible relationship.

## Reproducibility and stopping

Fixed seeds, exact task hashes, source/package hashes and immutable checksummed event records support deterministic candidate-prefix recovery. Wall-time boundaries can yield different prefix lengths on different hardware; exact saved prefixes replay in order and no duplicate within-search evaluation is allowed. Restarted processes retain cumulative runtime, including interrupted segments. A failed strategy allocation stops that strategy while others continue. The global resource gate and free-space reserve are also enforced. No full-campaign command exists.

Common encoding/preparation is shared and charged equally. Individual policy and assessment RSS is sampled at 10 ms using native macOS/Linux facilities; the whole-process OS high-water mark is separately reported. Timing includes measured policy bookkeeping and checkpoint work, with initialization/oracle/generation costs also visible in the cumulative campaign ledger. Temporary bytes include development and archived initial calibration attempts. Numerical and input-integrity tests accompany independent reference-fit and checkpoint checks.
