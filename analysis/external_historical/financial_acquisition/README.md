# Financial and macroeconomic acquisition — Phase 1

A reproducible, validated **825-month panel (1958-01–2026-09)** is built from **70 native series**. The local panel has **55 native/aggregated inputs + 47 derived columns**; the downloadable public panel has **69 numerical columns**. Original music data and prior analyses are preserved. No cross-domain modelling was performed.

Read [findings](findings.md), [priority acquisition status](priority_acquisition_status.csv), [coverage](coverage_report.csv), [native-frequency coverage](native_coverage_report.csv), [missing intervals](missingness_report.csv), [temporal alignment](temporal_alignment.md) and [blocked/deferred routes](blocked_sources.md). Source fields and formulas are in [series_dictionary.csv](series_dictionary.csv) and [derived_feature_dictionary.csv](derived_feature_dictionary.csv). [Acquisition log](acquisition_log.md), [source manifest](source_manifest.csv), [calculation checks](calculation_crosschecks.csv), [data-quality validation](data_quality_validation.json) and [music-join validation](music_join_validation.json) provide the audit trail.

## Files

The [dataset directory](../../../data/external_historical/financial/README.md) contains small redistribution-permitted CSV/XZ files. The native table retains source frequency, observation period, original publication/vintage where known, retrieval, source key/hash, source-status flags and rights. The wide monthly table has one row per month; `missingness_public.csv.xz` has corresponding 0/1 missing indicators. `aggregation_metadata_public.csv.xz` contains source-day/week counts and provenance. Quarter alignment and limited historical-vintage views are separate. No quarterly values are inserted into the main monthly table.

The six-month [sample music join](../../../data/external_historical/financial/processed/acquisition_v1/music_join_sample.csv) includes all-genres and genre summaries with source-row/distinct-song/available-score counts. It is a correctness example, not a fitted result or approved future weighting choice.

Raw source bytes, full local numerical panels and the market-drawdown figure remain ignored under `data/external_historical/financial/`. Their hashes and retrieval recipes are public; restricted series values are not committed. Source availability and a public download link do not by themselves confer bulk redistribution permission.

## Reproduce and validate

Run from the repository root with Python 3.9+ and the [pinned focused dependencies](requirements.txt). Existing repository dependencies are unchanged.

```bash
python3 -m pip install -r analysis/external_historical/financial_acquisition/requirements.txt
python3 src/financial_acquisition.py validate
python3 analysis/external_historical/financial_acquisition/verify.py
python3 -m unittest discover -s tests -p 'test_financial_acquisition.py' -v
```

The default validator uses committed public native data and reconstructs every public panel, metadata table, quarter view, point-in-time view and sample join offline. It verifies hashes and code. `python3 src/financial_acquisition.py build --public` republishes those exact public tables from pinned native inputs; it does not fetch sources or generate local values.

For the retained local source snapshots:

```bash
python3 src/financial_acquisition_sources.py normalize
python3 src/financial_acquisition.py build
python3 src/financial_acquisition_report.py
python3 src/financial_acquisition.py validate --private
python3 -m unittest discover -s tests -v
```

`normalize` verifies immutable SHA-256 bytes and fails before replacing native datasets on unsupported source schemas. Build outputs are staged, shape/finite/key checked, and published atomically per file with the build manifest last. Interrupted publication is detectable by the manifest; rerun from unchanged inputs. `restore` on the source script attempts only missing pinned source bytes, at a bounded rate; a newer provider revision fails hash validation and never replaces v1. Numeric CSV exports use 17 significant digits and native replay uses round-trip float parsing; original provider bytes and precision remain in immutable raw snapshots. Source archives must be retained for exact private reproduction. The published normalized public snapshot permits offline reproducibility even after providers revise their live downloads. `acquire` is the original acquisition recipe and can reuse the explicitly listed local caches; it does not refresh an already successful v1 snapshot.

The broader reproduction environment and each byte-level source version are part of the release. Historical release availability is only asserted for the limited G.17/NBER event views documented above. Full retrospective panels are not forecasting-ready.

## Figures

- [Priority-source historical coverage](figures/historical_coverage.svg)
- [Unemployment and inflation](figures/unemployment_inflation.svg)
- [Financial stress](figures/financial_stress.svg)
- [Missingness by period](figures/missingness_by_period.svg)

The fifth figure, market drawdowns, is produced locally at `data/external_historical/financial/processed/acquisition_v1/figures_local/market_drawdowns.svg` because bulk/derived redistribution permission for its market source is unresolved. [figure_inventory.csv](figure_inventory.csv) records all five figure hashes. Existing figure catalogs and PNGs are unchanged.

The final validation/preservation publication record is in [validation_report.md](validation_report.md). This release ends at dataset review; it does not authorize regressions or predictive searches.
