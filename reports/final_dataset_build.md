# Final analysis-ready dataset build

Release: `final-snapshots-v3.0`. Dataset construction only; no historical/COVID analysis, moving averages or combined content scores.

| Table | Rows | Columns | Bytes (CSV) | Unique songs | Final-population rows | Metadata matched rows | Genre rows | Classifier rows | All-42 rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| songs | 28,041 | 70 | 26,094,309 | 28,041 | 28,041 | 22,290 | 28,041 | 20,981 | 20,979 |
| weekly | 355,487 | 77 | 349,790,147 | 32,723 | 347,995 | 287,951 | 347,995 | 275,134 | 275,120 |
| monthly | 81,797 | 78 | 82,138,319 | 28,041 | 81,797 | 67,510 | 81,797 | 64,426 | 64,422 |

Weekly: all 3,555 physical charts and 355,487 source rows, including repeated song/date pairs. Monthly: the latest chart in each of 818 calendar months, 81,797 rows. The three rank-100 gaps remain unchanged. Chart dates are not release dates.

Enrichment is deliberately restricted to the final 28,041-song population. Other weekly identities keep their exact Billboard identity and whole-history summaries; metadata/genre/features and lyrics availability remain blank, with explicit outside-population statuses. Historical enrichment for removed old-population assets remains preserved in the legacy stores/exports and is not silently incorporated.

Genre confidence: high 18,621; medium 7,538; low 1,882. Classifier songs: 20,981; all 42 features: 20,979. The two documented LyricLens exceptions retain only their four NULLs; 7,060 final-population songs lack all 42 features. Secondary genres are JSON arrays of provisional model labels; reasons are excluded.

Validation: raw JSON and immutable SQL rows reconcile by source coordinates; whole-history summaries independently reconcile; every CSV cell reconciles to the allowlisted projection; independent serializations have equal SHA-256 checksums; XZ round-trips exactly. Frozen input databases, canonical lyrics and raw Billboard source retain their hashes. Both classifier stores reconcile scores to saved chunks. No inference is run.

Publication:
- `songs.csv`: 26,094,309 bytes; SHA-256 `cb9a9ddc6a40d54f36baced31227581a277f4d7a37a9410074ad0d0a0810e1c5`.
- `master_weekly.csv.xz`: 15,122,944 bytes; SHA-256 `60f1a27be135c6e862c3d8bb5e6193999f0a9b3f19e6ea89de1f77454cdfc477`.
- `master_monthly.csv`: 82,138,319 bytes; SHA-256 `507dd443d2f3f35a6b5546d11ece7758a44851898af71da95fd65d92830d1f7c`.

The uncompressed weekly CSV is generated locally but excluded from Git when above the reviewed 95 MiB threshold. Its XZ copy preserves full precision and every row. Monthly and song CSVs are direct downloads. No Git LFS.

Earlier aggregate-month CSVs remain historical artifacts, not current inputs; their old song table and manifest are preserved in `data/public/legacy_classifier_v2/`. The new `manifest.json` is the current release contract. Pre-publication audits that freeze the old public-file hashes remain historical checks; use `src/final_dataset.py validate` for this authorized release.

Reproduce: `python3 src/final_dataset.py build`; validate: `python3 src/final_dataset.py validate`; tests: `python3 -m unittest discover -s tests -v`. Exact reconstruction requires the retained private enrichment stores; downloading and using the public CSVs does not.
