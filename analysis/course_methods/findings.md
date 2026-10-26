# Findings: completed course-method campaign

All requested major method families were implemented and executed. The clearest result is a limit: the lyrical scores do not provide useful, stable chronological chart-success classification in this population. Stable broad score profiles exist, while many impressive association rules still reflect overlapping measurements or historical composition. No result identifies a COVID effect.

## Eight findings worth discussing

1. **Chart success remains difficult.** In 2018–2025, tree/Bayes balanced accuracy is 0.510/0.479 for Top 10 and 0.485/0.445 for long longevity, against 0.500 majority baselines. More flexible multivariate classifiers do not rescue the weak lyrical-to-chart signal found in earlier work.
2. **Lyrics help distinguish broad genres, with large limitations.** Latest tree/Bayes balanced accuracy is 0.262/0.242, versus 0.143; macro F1 is only 0.228/0.214. Bayes accuracy is 50.3%, but the largest test class alone contains 40.4% of songs. Minority-class failures remain visible in the confusion matrices; the training-majority baseline's 17.7% accuracy should not make this look like a general genre solution.
3. **Three broad score profiles are reproducible, not sharply separated.** Standardized K-means selects K=3, mean resample ARI 0.958, and test silhouette 0.137. PCA also selects K=3 and agrees with those test assignments at ARI 0.965. Family balancing instead selects K=2 (ARI stability 0.980; test silhouette 0.127). Stable assignments do not establish a unique natural taxonomy.
4. **An affect profile spans genres.** Standardized cluster 0 has elevated disappointment, sadness and grief scores. Its largest genre shares are Pop 28.1%, Rock 23.3%, R&B / Soul 19.4%, Country 13.2%. The high content-score cluster 2 is 68.7% Hip-Hop / Rap, leaving a substantial share from other genres. These are classifier profiles, not human-validated lyrical categories.
5. **Cluster prevalence changes substantially over historical cohorts.** The high content-score cluster's raw share is 8.4% before 2020 and 41.1% after, a +32.7 percentage points contrast (fixed-cluster artist interval +27.4 percentage points to +38.2 percentage points). A fixed genre mixture gives 7.7% to 26.6%, but retains only 72.0% of training genre mass. Unequal historical spans, missingness, genre composition and right-boundary selection prevent a COVID or breakpoint interpretation.
6. **A multidimensional chart association is measurable but modest.** Low caring AND low love scores imply ≤17 observed chart weeks for 76.0% of 684 recent songs, versus 68.1% overall. Improvement over the strongest immediate parent is only +2.6 percentage points (global BY q=2.33e-05). This is a retrospective conditional association; it does not overturn the poor full-classifier results.
7. **Aggregation can conceal a genre reversal.** High MusicBrainz release count is associated with a -25.1 percentage points change in high substance-use-score prevalence overall, but +8.0 percentage points within Pop: 52.1% versus a Pop baseline of 44.1% (71 antecedent songs among 422 Pop songs). This is a post-hoc descriptive screen, not a separately confirmed subgroup test or proof of Simpson's paradox. Catalog exposure and era/artist composition are plausible confounders.
8. **Recording metadata has cross-domain associations, not demonstrated forecasting value.** Among 174 recent songs above the training duration Q75 (255.44 seconds), 71.3% have high violence scores versus 54.6% overall (lift 1.31; BY q=0.000139). MusicBrainz metadata is present-day evidence and was deliberately excluded from pre-chart prediction models. Genre and catalog matching can explain part of this association.

## Frequent patterns and rules

| support_threshold | itemsets | closed | maximal | algorithms | identical |
|---|---|---|---|---|---|
| 0.05 | 22993 | 22982 | 7137 | 3 | True |
| 0.08 | 4087 | 4087 | 1564 | 3 | True |
| 0.12 | 1072 | 1072 | 362 | 3 | True |

All three algorithms agree on every itemset and integer support count. The primary 8% set generates 11,783 rules; 3,874 supplemental rare positive pairs and 5,271 negative rules bring the complete search to 20,928. Of these, 10,980 have strict cross-domain direction and 11,510 have global BY q≤0.05 under the declared assumptions. That count includes many redundant/expected relationships and is not a discovery count.

For a concrete negative pattern, low obscenity scores imply an observed non-Hip-Hop genre for 100.0% of 104 test songs, against a 59.6% baseline. This is unsurprising genre separation, not a scientific breakthrough. Rare rules retain nulls and inadequate test support. The conditional scan retains 44,928 genre cells and flags 69 descriptive sign reversals; no independent significance claim is made for those subgroup screens.

All itemsets include globally valid closed/maximal flags within the size-four output cap. Complete raw rules, parent comparisons, BY values and subgroup diagnostics are linked in the [README](README.md).

## Latest chronological classification

All rows use 2,382 Billboard-study songs whose observed chart histories fit wholly within 2018–2025. Long longevity here means more than 18 weeks; association transactions separately use more than 17 weeks. These training-derived thresholds must not be conflated.

| target | method | accuracy | balanced_accuracy | precision_macro | recall_macro | f1_macro | f1_weighted |
|---|---|---|---|---|---|---|---|
| top10 | tree | 0.5768 | 0.5101 | 0.5057 | 0.5101 | 0.4723 | 0.632 |
| top10 | naive_bayes | 0.6192 | 0.4791 | 0.4868 | 0.4791 | 0.469 | 0.6611 |
| top10 | majority | 0.8401 | 0.5 | 0.42 | 0.5 | 0.4565 | 0.767 |
| long_chart | tree | 0.3799 | 0.4846 | 0.4814 | 0.4846 | 0.3763 | 0.3575 |
| long_chart | naive_bayes | 0.4412 | 0.4453 | 0.4535 | 0.4453 | 0.4258 | 0.4627 |
| long_chart | majority | 0.6961 | 0.5 | 0.348 | 0.5 | 0.4104 | 0.5713 |
| broad_genre | tree | 0.4572 | 0.2621 | 0.2642 | 0.2621 | 0.228 | 0.4522 |
| broad_genre | naive_bayes | 0.5029 | 0.2416 | 0.2519 | 0.2416 | 0.2136 | 0.4462 |
| broad_genre | majority | 0.1772 | 0.1429 | 0.0253 | 0.1429 | 0.043 | 0.0533 |

Binary confusion matrices below use actual rows and predicted columns, both ordered [no, yes]. Full seven-class genre matrices and all historical folds are in [confusion_matrices.json](classification/confusion_matrices.json).

- top10, tree: `[[1217, 784], [224, 157]]`.
- top10, naive_bayes: `[[1371, 630], [277, 104]]`.
- long_chart, tree: `[[361, 1297], [180, 544]]`.
- long_chart, naive_bayes: `[[721, 937], [394, 330]]`.

One compact learned rule (the full-precision thresholds and every leaf are saved):

```text
IF ll_explicit_language <= 0.93930095 AND detox_obscene > 0.00030394217 AND emotion_optimism > 0.0068846999 THEN yes
```

It covers 429 test songs and is correct on 38.7%. Interpretable rules can still be weak. The rule classifier reproduces the tree exactly; it is not an independent success.

## Clustering comparison and null results

| configuration | selection_supported | validation_silhouette | test_silhouette | test_silhouette_original42 | stability_mean | minimum_cluster_share |
|---|---|---|---|---|---|---|
| kmeans_standardized42_k3 | True | 0.1416 | 0.1373 | 0.1373 | 0.9579 | 0.049 |
| kmedoids_standardized42_k11 | False | 0.1049 | 0.1335 | 0.1335 | 0.3428 | 0.0012 |
| hierarchical_standardized42_k2 | True | 0.4776 | 0.4003 | 0.4003 | 0.8117 | 0.0155 |
| kmeans_pca90_k3 | True | 0.1487 | 0.1522 | 0.1365 | 0.958 | 0.0544 |
| kmedoids_pca90_k12 | False | 0.0897 | 0.0996 | 0.08 | 0.3933 | 0.0013 |
| hierarchical_pca90_k2 | False | 0.4597 | 0.3981 | 0.3788 | 0.2925 | 0.0213 |
| kmeans_family_balanced_k2 | True | 0.1713 | 0.1272 | 0.0937 | 0.9802 | 0.2815 |
| kmedoids_family_balanced_k12 | False | 0.0734 | 0.0877 | 0.0315 | 0.3334 | 0.0006 |
| hierarchical_family_balanced_k2 | True | 0.5113 | 0.4254 | 0.3953 | 0.772 | 0.0153 |

No sampled k-medoids configuration satisfies both predefined stability/size criteria. The strongest hierarchical silhouette values mainly isolate a small outlier group, and the PCA hierarchical family has no qualifying configuration. These are retained unsuccessful outcomes. They do not establish that medoid/hierarchical methods can never work; the result applies to this fixed representation, sample, initialization and bounded algorithm grid.

## Reliability, limitations and follow-up

The full search is exploratory and uses previously examined outcomes. Complete-case inclusion, frozen model errors, genre-label noise, same-artist dependence, catalog coverage, discrete-bin ties, retrospective metadata, whole-history purging and incomplete lifetime follow-up limit interpretation. Sparse CMH cells weaken asymptotic inference. Artist/block intervals are marginal fixed-analysis sensitivities, not simultaneous post-selection guarantees. The clustering bootstrap holds preprocessing fixed and has only two refit comparisons per configuration.

A worthwhile next step is a frozen replication on genuinely new, mature chart cohorts, together with a small human-labelled audit of the score profiles and genre labels. Conditional catalog/genre reversals deserve replication before causal interpretation. More classifier tuning or another exhaustive relationship search is not justified by these results. This campaign does not justify new bulk data acquisition; annotation quality and an independent evaluation set are more pressing.

## Selected figures

- [algorithm_comparison.svg](figures/algorithm_comparison.svg): One measured run per algorithm/threshold; implementations and shared data preparation are described in methodology.
- [classification_generalization.svg](figures/classification_generalization.svg): Chronological outer evaluations; inner validation selects tree settings. Chance-level binary balanced accuracy is 0.5.
- [latest_confusion_matrices.svg](figures/latest_confusion_matrices.svg): 2018–2025 counts and row-normalized percentages. Every class remains visible, including classes with zero recall.
- [clustering_comparison.svg](figures/clustering_comparison.svg): All 99 configurations. High hierarchical silhouettes can reflect small outlier clusters; medoid solutions fail the predefined stability/size criteria.
- [cluster_profiles.svg](figures/cluster_profiles.svg): Up to four displayed features per classifier family, selected by absolute profile contrast. Profiles describe all eligible historical songs; scaling is training-only.
- [cluster_history.svg](figures/cluster_history.svg): Pre/post contrasts span unequal historical periods, not a breakpoint design. Genre-standardized values retain only 72.0% of the training genre mass; the bar difference is not a decomposition.
- [association_baselines.svg](figures/association_baselines.svg): Retrospective display examples. The multidimensional rule also adds only about 2.6 percentage points over its strongest immediate parent.

This report is generated by `src/course_report.py`; do not hand-edit its measured values.
