# Command guide

Run from the repository root. Public-data analysis uses the existing `requirements.txt`.

| Task | Command | Inputs / effects |
|---|---|---|
| Descriptive outputs | `python3 src/descriptive_analysis.py` | Public monthly CSV → analysis/milestone2 |
| Moving averages | `python3 src/moving_average_analysis.py` | Public monthly CSV → analysis/moving_averages |
| Preferred all-genres overlays | `python3 src/moving_average_all_genres.py` | Saved series; run after moving averages |
| All analytical figure presentation | `python3 src/figure_audit.py` | Existing public data/saved results → figures and audit only; no numerical outputs rewritten |
| Published figure validation | `python3 src/figure_audit.py --validate` | Read-only image catalog, numerical and code hashes |
| Repository integrity/navigation | `python3 src/repository_layout.py` | Read-only hashes, frozen code, links, paths and ignore rules |
| All regression tests | `python3 -m unittest discover -s tests -v` | Fixtures plus public-data integrity checks |
| Public dataset build | `python3 src/final_dataset.py build` | Offline frozen private inputs; replaces public exports only after validation |
| Public dataset validation | `python3 src/final_dataset.py validate` | Offline reconstruction/comparison; no acquisition or inference |
| Phase 1 foundation check | `python3 src/phase1.py validate` | Existing raw snapshot and immutable chart foundation |

The final exporter is the current dataset entry point. `public_dataset.py` and
`public_classifier_features.py` belong to earlier export stages and are not substitutes.
`build`/`validate` need retained private chart/enrichment stores, sidecars and audits;
using the public datasets or rebuilding analysis does not.

Source modules remain in `src/` because imports and frozen hashes depend on them.
Phase 2A/2B/2A-R, lyric acquisition, model pilots and genre production runners are
historical or operational modules, not routine student commands. Their experiment
guides are archived. Do not restart network acquisition or classification for cleanup,
validation or figure regeneration.
