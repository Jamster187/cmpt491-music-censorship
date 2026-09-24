# Public classifier feature release

**COMPLETE with documented model-specific missingness.** The user accepted both LyricLens preprocessing failures. No retries, lyric edits or inference changes were made. Historical failure records stay intact in the private classifier database; the public exporter applies the explicit accepted-missingness policy.

The master contains **81,800 song-month observations**, **818 months × 100 rows**, and **73 columns**: the original 31 followed by the 42 model features. File size: **79,253,713 bytes (75.58 MiB)**.

| Classifier availability | Monthly observations | Unique songs |
|---|---:|---:|
| Any classifier data | 65,175 | 19,372 |
| All 42 features | 65,173 | 19,370 |
| Other 38 features; four LyricLens values missing | 2 | 2 |
| All 42 features missing (no usable lyrics) | 16,625 | 5,991 |

“Any classifier data” includes the complete and partial groups; it is not an additional disjoint group. Blank cells mean NULL/missing, not zero. All 2,737,342 populated feature cells are finite and within [0,1].

The two partial records are “Chinese Checkers” by Booker T. & The MG's and “Snap Shot” by Slave, each appearing in one monthly basket. Their reason is `unsupported/empty-after-LyricLens-normalization`. All valid Detoxify, GoEmotions and Cardiff features remain populated. See the [accepted-missingness policy](../../docs/classifier_accepted_missingness.json).

## Validation

- The original 31-column projection serializes to exactly the pre-join SHA-256: `4a18d97d4f117c4f6ce261ad4d035233e5401952b09dcd2e4e377bacf5a0df24`. Every original value, row and row order is preserved.
- Every public feature value independently reconciles to the correct private classifier row through `song_id`. No extra or missing study observations; no duplicate monthly keys.
- The deterministic exporter validates the full approved 19,372-song population, frozen model configuration/checkpoint metadata, complete balanced chunks, raw activations and token-weighted aggregates. Only the two explicitly named errors may yield missing model scores.
- Two independently generated exports must match byte-for-byte before publication. `validate` regenerates and compares all public files and manifest checksums.
- Normalized songs/monthly tables are unchanged. Source research/classifier databases and lyrics are not modified or distributed. No raw text, token IDs, local paths, caches or credentials are projected.
- The feature list is explicit and namespaced; no CSI, MCR, hardness, consensus or combined outcome is exported. No historical/COVID analysis was performed.

## Rebuild

```sh
python3 src/public_dataset.py build
python3 src/public_dataset.py validate
python3 src/public_classifier_report.py
python3 -m unittest discover -s tests -v
```

Rebuilding requires the retained local research and classifier databases. Downloads do not require these private inputs. The model-derived features are not ground-truth content measurements. Exact columns and source checksums are in [manifest.json](../../data/public/manifest.json) and [the release evidence](../../reports/classifier_public_release.json).

The reviewed master exceeds GitHub’s 50 MiB warning threshold but is below its 100 MiB hard limit. It is committed directly to retain the requested simple raw CSV download and full numerical precision; no LFS is introduced. [GitHub size limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).
