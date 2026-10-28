# Provenance, licenses and reproduction

Billboard defines chart identities and dates. The local snapshot reports upstream `mhollingshead/billboard-hot-100`; that attribution does not establish independent verification. Exact title and artist strings remain unchanged. Artist credits may refer to collaborations; neither normalized strings nor external IDs merge study identities.

Sources are the frozen approved private lyric inputs; retained MusicBrainz core-data caches and exact-MBID queries (CC0); AcousticBrainz numerical metadata (CC0); pinned CMUdict (BSD-style); spaCy en_core_web_sm 3.8.0 (MIT); all-MiniLM-L6-v2 at a fixed revision (Apache-2.0); and wordfreq 3.1.1 (Apache-2.0 software, source data may carry CC BY-SA attribution obligations). The [asset manifest](asset_manifest.json) records exact URLs and hashes; [runtime lock](requirements.lock.txt) records versions. Source attribution follows [MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_Database), [AcousticBrainz](https://acousticbrainz.org/), [CMUdict](https://github.com/cmusphinx/cmudict), [spaCy model](https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0), [MiniLM model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) and [wordfreq](https://github.com/rspeer/wordfreq). No newly acquired lyrics or recordings are used and no private text leaves the machine.

The local benchmark preceded full inference. Semantic vectors use all 254-wordpiece chunks up to a bounded 64-chunk limit, normalized mean pooling, and token-count weighting; oversized texts would be marked missing, not truncated. English parser/lexicon features are diagnostics and include coverage. Modern model training can include historical songs; prior-only comparison sets do not remove that limitation. Prior-hit references are updated only after scoring new entrants on the same chart. Artist-history graphs preserve exact credit or retained entity scope.

Original-issue label/date, formation-country and exhaustive role claims are not inferred from associated editions. MusicBrainz response IDs and artist-ID sets must agree with retained approved mappings. AcousticBrainz requires the exact recording-ID tag, exact artist-ID set and duration within max(2 seconds,2%). The earliest submission is fixed without feature-based selection. Source extractors, mapping outcomes and sparse associated media/label tags remain explicit. Audio versions still may differ by master or edition; these 1,405 assets are a selective subset.

Published data are directly usable without private inputs. Verify with:

```bash
python3 src/music_enrichment_validate.py
python3 -m unittest discover -s tests -v
```

A full offline rebuild requires the retained private lyric/source caches and the pinned local environment. It does not trigger acquisition or text inference:

```bash
python3 src/music_enrichment_features.py
python3 src/music_enrichment_metadata.py
python3 src/music_enrichment_acquire.py summarize
python3 src/music_enrichment_audio.py summarize
data/experiments/music_enrichment_v2/venv/bin/python src/music_enrichment_nlp.py export
python3 src/music_enrichment_views.py chart
python3 src/music_enrichment_views.py build
python3 src/external_historical_sources.py normalize
python3 src/external_historical_features.py
python3 src/external_historical_joins.py build
python3 src/enrichment_reports.py
python3 src/music_enrichment_validate.py --private
python3 src/enrichment_common.py verify
```

The environment path is local and ignored. Asset installation, initial NLP run and bounded metadata acquisition are separate opt-in commands in their source modules; do not reacquire for ordinary validation. Live providers can revise history, so fresh downloads are a new snapshot, not a byte-identical reconstruction. Preserve local snapshot hashes and do not overwrite frozen responses. The public manifests allow exact validation even when private reproduction inputs cannot be shared.
