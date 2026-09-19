# Research construction validation

Validated 2026-09-19T10:29:52+00:00.

- 106 automated tests passed (`python3 -m unittest discover -s tests -v`).
- Unified database build/validation passed: Existing research database validated; enrichment preserved: {'songs': 32723, 'chart_observations': 355487, 'monthly_top100': 81800, 'study_population': 25363, 'lyrics_manifest': 25363, 'lyrics_pilot': 200, 'metadata_matches': 927}.
- Re-running `python3 src/research.py build` left the enriched database byte-for-byte unchanged.
- Re-running `python3 src/production_metadata.py --offline --import-pilot` processed zero assets and made zero requests; existing decisions, entity links and metadata were unchanged.
- Re-running `python3 src/lyrics_plan.py` preserved the 200-member pilot file and all manifest rows. The pilot covers all 69 first-chart years.
- All 1,883 pre-existing files in the session's protected snapshot retained their hashes, including Phase 1 inputs and earlier experiments.
- `git check-ignore` confirmed exclusions for lyrics, lyrics caches and `.env`; `git ls-files data/lyrics data/cache .env` returned no tracked files.
- File/manifest validation found zero acquired lyrics, zero orphan lyrics and no invalid metadata evidence-file hashes. Synthetic fixture tests cover successful-file preservation, corruption and orphan detection.

## Live metadata pass

The bounded live run ended with status `time_budget` after 1200 seconds. It persisted 767 additional song decisions and reported 972 network attempts. HTTP response status counts for this run: `{"200": 912, "503": 60}`. Retried HTTP failures are distinct from unresolved per-song API errors in the coverage report.

At this run's measured throughput, the 24,436 pending songs would take roughly 10.6 additional hours, assuming similar response latency and candidate complexity. This is an estimate, not a completion guarantee; optional detailed entity requests would add work. No metadata process remains running after the bounded pass. Full-population enrichment is unfinished.

Lyrics acquisition remains unattempted because source access/storage/reuse terms have not been established. No pilot quality or provider coverage claim is made. See [source assessment](lyrics_source_assessment.md) and [complete coverage and resume report](research_dataset_status.md).
