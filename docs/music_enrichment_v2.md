# Additive music enrichment and historical data

Existing navigation files are hash-pinned by prior publications and remain unchanged. Current entry points and complete reproduction instructions are maintained in the versioned release READMEs below.

The [music enrichment v2 report](../analysis/music_enrichment_v2/README.md) documents the completed feature audit, local text/semantic diagnostics, metadata and qualified audio enrichment. The [versioned song/month datasets](../data/public/music_enrichment_v2/README.md) preserve all frozen original fields and identities.

The separate [historical-data platform](../analysis/external_historical/README.md) provides financial, macroeconomic, political, social and cultural series with native-frequency and historical-release joins. [Permitted public observations and joins](../data/public/external_historical_v1/README.md) exclude restricted source values. These are additive data releases; the completed regression campaigns and prior public datasets remain unchanged. No new cross-domain model search is part of this release.

## Music enrichment v2 and external history v1

| Task | Command | Scope |
|---|---|---|
| Verify published additive layers | `python3 src/music_enrichment_validate.py` | Public-only hashes, exact identities, missingness and temporal gates |
| Verify private source/release joins | `python3 src/music_enrichment_validate.py --private` | Requires retained local source snapshots; no network or inference |
| Verify original artifact preservation | `python3 src/enrichment_common.py verify` | Requires the local baseline; checks original data/analysis bytes |
| Replay bounded semantic diagnostics | `data/experiments/music_enrichment_v2/venv/bin/python src/enrichment_semantic_replay.py` | Eight cached texts and independent temporal-prefix fixtures, offline |
| Rebuild music views | `python3 src/music_enrichment_views.py chart` then `python3 src/music_enrichment_views.py build` | Retained enrichment outputs; no classification/acquisition |
| Rebuild historical joins | `python3 src/external_historical_joins.py build` | Existing native/derived tables; no model fitting |
| Refresh measured reports | `python3 src/enrichment_reports.py` | Existing versioned outputs and local provenance; deterministic SVG coverage figures |

Full offline reproduction and optional initial-acquisition commands are documented in the [music provenance guide](../analysis/music_enrichment_v2/provenance.md) and [historical alignment guide](../analysis/external_historical/temporal_alignment.md). Live source revisions are new snapshots, not byte-identical replays.

For a complete offline determinism check, run `python3 src/enrichment_reproduce.py`. It rebuilds the new views, source normalization, transformations, joins, CSV inventories and SVG figures from retained inputs, then requires unchanged artifact hashes. It performs no network requests or model inference.
