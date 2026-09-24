# Classifier documentation

- [Production method](../classifier_production.md) and [frozen schema](../classifier_production_schema.json).
- [Accepted missingness](../classifier_accepted_missingness.json): two LyricLens exceptions, with the other 38 scores retained.
- [LyricLens methodology](../lyriclens_methodology.md).
- [Detoxify methodology](../detoxify_methodology.md).
- [Final dataset guide](../../data/public/README.md): the 42 distributed dimensions and coverage.

The old five-model panel (including BART) was a pilot, not the final four-model
release. Its [specification](../../archive/old_methodology/classifier_panel_specification.md)
and [results](../../archive/intermediate_reports/classifier_panel_design.md) are historical.
Model environments, weights and source snapshots remain ignored under `data/experiments/`;
do not move them or run inference to reproduce the public-data analyses.
