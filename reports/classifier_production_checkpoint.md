# Four-model production checkpoint validation

The final code passed `python3 -m unittest discover -s tests -v`: **218 tests**, including 15 new production regression tests. These cover atomic initialization, frozen configuration, rejection of unapproved IDs, exact namespaces/head mappings, finite outputs, token coverage, independent model failure persistence, interrupted chunk resume, successful-job skipping, duplicate-write rejection, source-hash protection, concurrent locks, protected database paths/symlink aliases, and isolation of preprocessing failures between songs.

The final 200-song run and its separate replay both completed 800 song/model jobs. The replay was deliberately interrupted with SIGTERM and resumed under the same frozen configuration. All 513 already completed jobs and 646 saved chunks survived unchanged; the final song features and raw chunk predictions exactly match the uninterrupted run. A completed-run invocation launched no model workers and changed no persisted table. Detailed proofs, input/code hashes and counts are in [validation.json](classifier_production/validation.json).

The following validations passed:

- `python3 src/research.py validate`: 32,723 Billboard identities, 355,487 weekly observations, 81,800 monthly observations, 25,363 study identities and synchronized 25,363-row lyrics manifest.
- `python3 src/public_dataset.py validate`: existing public tables and master CSV, joins, row counts, safety checks and deterministic rebuilds.
- `python3 src/lyriclens_validate.py`: original 200 predictions, 47 reviews, pinned artifacts, all 19,372 unchanged lyric files and unchanged public/research inputs.
- `python3 src/detoxify_validate.py`: pinned artifacts, original predictions, 50 review rows, 24 sensitivity rows and two deterministic diagnostic rebuilds.
- The four-model production report independently validates all chunk ranges, activations and aggregates, and compares the exact sample/input hashes and raw logits against the archived four-model whole-song pilot. Maximum prior-pilot logit difference: **0**.

Protected file SHA-256 values remain:

| File | SHA-256 |
|---|---|
| `data/processed/research.db` | `d31bf1343c17a9716e81d8f9c0d7a8980504a5f57db8d13af32139bdb013d40d` |
| `data/public/master_dataset.csv` | `4a18d97d4f117c4f6ce261ad4d035233e5401952b09dcd2e4e377bacf5a0df24` |

The master still has 81,800 rows and 31 columns; there are 818 monthly baskets and 19,372 canonical local lyrics files. The full-corpus `data/processed/classifier_results.db` has **not** been created. Only the exact original 200 songs were passed through inference. BART was not loaded or benchmarked, and no classifier features were imported into the research/public datasets.

Git excludes lyrics, caches, local model files/environments and private databases. This checkpoint publishes code, schema/documentation, and numerical-only pilot evidence. Raw text and token-ID arrays are absent from the exported chunk records. The production report rebuild is checked for byte-identical output from its persisted inputs. No historical/COVID test or combined content score was calculated.
