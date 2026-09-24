# Repository structure

Open the root README, then the public data guide and the two analysis landing pages.
For presentation figures, go directly to the moving-average all-genres shortlist.

| Location | Purpose |
|---|---|
| [data/public/](../data/public/README.md) | Final downloadable datasets; unchanged paths and bytes |
| [analysis/milestone2/](../analysis/milestone2/README.md) | Descriptive statistics (`tables/`), figures and findings |
| [analysis/moving_averages/](../analysis/moving_averages/README.md) | Historical classifier/genre series; preferred `figures/all_genres/` |
| [docs/](README.md) | Methods, schemas and technical documentation |
| [src/](../src/README.md) | Reproducible pipeline/analysis code and current entry points |
| [tests/](../tests/) | Regression and integrity validation |
| [reports/](../reports/README.md) | Final audits and required production evidence |
| [archive/](../archive/README.md) | Superseded experiments, narratives and intermediate reports |

The cleanup uses Git moves and a [file relocation manifest](repository_cleanup_manifest.json).
No data or numerical results change. Analysis manifests are rebuilt for new output paths
and code hashes; tables and images must retain their previous SHA-256 values. Markdown
navigation may change, while historical machine-readable paths remain archival facts.

Some files deliberately stay put: final public/legacy exports, frozen classifier/genre
schemas and scripts, and audit/model/review inputs still consumed by production.
Topic indexes replace risky moves. Private environments and artifacts under ignored
`data/experiments/`, `data/processed/`, `data/cache/` and `data/lyrics/` remain local.
No `src/` modules are archived because their imports/provenance remain useful.

Figure shortlists link to canonical files; there are no ambiguous duplicate copies.
The full previous root README is retained in `archive/old_methodology/` as a dated
historical snapshot, including its original paths. See [commands](commands.md) before
rebuilding data; acquisition and classification are unnecessary for ordinary analysis.

`reports/classifier_panel` is a documented compatibility symlink to the archived
pilot assets, required by the hash-pinned original runner. LyricLens evaluation
and its shared diagnostics module retain their canonical paths/bytes because
production fingerprints include them. These are deliberate reproducibility exceptions.

Run `python3 src/repository_layout.py` to repeat the structural integrity checks.
