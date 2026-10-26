# Local feature expansion: navigation and commands

The completed [campaign README](../analysis/feature_expansion_v1/README.md) is the current entry point for this additive experiment. Read the [measured findings](../analysis/feature_expansion_v1/findings.md), [methodology](../analysis/feature_expansion_v1/methodology.md), and separate [versioned dataset](../data/public/feature_expansion_v1/README.md).

The root README, `docs/commands.md`, `docs/repository_structure.md` and `src/README.md` are hash-pinned inputs of the frozen historical-decomposition publication. Their original paths and bytes remain intact. This separate navigation index documents the deliberate exception: new commands and dataset semantics are described here and in the new campaign/dataset READMEs, without refreshing a previous experiment's publication manifest. Existing public datasets and experiments keep their previous definitions and reproduction instructions.

| Task | Command from repository root |
|---|---|
| Snapshot existing artifacts and check frozen protocol | `python3 src/feature_expansion_common.py prepare` |
| Build local debut features | `python3 src/feature_expansion_features.py` |
| Run the bounded model comparison | `python3 src/feature_expansion_models.py all` |
| Validate features, splits and preservation | `python3 src/feature_expansion_validate.py --prefix --preservation` |
| Render measured findings and SVG figures | `python3 src/feature_expansion_report.py` |
| Run all regression tests | `python3 -m unittest discover -s tests -v` |
| Open the professor demonstration | `.venv-regression-demo/bin/streamlit run src/feature_expansion_demo.py --server.address 127.0.0.1 --server.port 8503 --browser.gatherUsageStats false` |

The feature rebuild reads retained private approved lyrics and metadata without modifying them. Model fitting uses the published new feature tables and [campaign-specific pinned dependencies](../analysis/feature_expansion_v1/requirements.txt); no acquisition or new content scores are generated. The professor demo uses portable saved model specifications in the existing Streamlit environment and performs no training. See the campaign README for the frozen-environment guard, public-only replay, diagnostics and optional interface tests.
