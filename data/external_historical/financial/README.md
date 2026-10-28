# Financial historical data — acquisition v1

Read the [acquisition report](../../../analysis/external_historical/financial_acquisition/README.md) before analysis. Public values are under `processed/acquisition_v1/`; immutable source recipes and hashes are under `manifests/acquisition_v1/`.

| File | Contents |
| --- | --- |
| [native_public.csv.xz](processed/acquisition_v1/native_public.csv.xz) | Permitted source values in native frequency with observation/release/vintage/retrieval/provenance |
| [monthly_public.csv.xz](processed/acquisition_v1/monthly_public.csv.xz) | 825 calendar months, 69 numerical columns; retrospective revised snapshot |
| [missingness_public.csv.xz](processed/acquisition_v1/missingness_public.csv.xz) | Matching per-column missing flags; 1 means absent |
| [aggregation_metadata_public.csv.xz](processed/acquisition_v1/aggregation_metadata_public.csv.xz) | Source counts, weekly/daily completeness and provenance for present source periods |
| [quarterly_alignment_public.csv.xz](processed/acquisition_v1/quarterly_alignment_public.csv.xz) | Explicit quarter-end and latest completed-quarter views; not monthly measurements |
| [point_in_time_public.csv.xz](processed/acquisition_v1/point_in_time_public.csv.xz) | Only historical G.17 release growth values with observed publication/vintage dates |
| [music_join_sample.csv](processed/acquisition_v1/music_join_sample.csv) | Small chart-month/genre join check; no modelling |

The full local dataset additionally includes research-only series and transformations. Raw snapshots, `*_local` files and local-only figures are ignored. Never infer zeros from blanks or carry low-frequency observations into the primary monthly dataset. Source dictionaries and attribution/license decisions are in the report directory; restricted inputs do not become redistributable merely by transformation. Public World Bank and EPU values require their documented CC BY 4.0 attributions.
