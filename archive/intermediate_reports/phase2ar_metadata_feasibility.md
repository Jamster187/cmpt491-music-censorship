# Phase 2A-R: offline MusicBrainz asset matching

Generated from the frozen Phase 2A cache. No new requests, manual promotions, or changes to the canonical database or previous archive/experiments.

The same 200 assets yield **169/200 high-confidence links (84.5%)**, compared with Phase 2A's 45/200 (22.5%).
Newly accepted: 124; still ambiguous: 17; no cached candidates: 14. Previously accepted but now excluded: 0. Unresolved input/API errors: 0; network requests: 0.
No cached candidates means the original bounded searches returned nothing; it does not establish absence from MusicBrainz.

Of the 104 original multiple-recording ambiguity cases, 102 are newly accepted. Original reasons for all new links: `{"competing_plausible_recordings": 16, "multiple_eligible_recordings": 86, "no_candidate_passes_strict_rule": 16, "search_results_truncated": 6}`.
Accepted recording status: `{"single_observed_candidate": 41, "unresolved_multiple": 128}`. No recording is arbitrarily selected.

## Historical coverage

| First chart period | N | Phase 2A high | Phase 2A-R high (%) | Ambiguous | No candidates | Wikidata high | Recording genres / tags |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1958–1969 | 29 | 2 | 14 (48.28%) | 8 | 7 | 6 | 0 / 12 |
| 1970s | 29 | 10 | 23 (79.31%) | 5 | 1 | 7 | 5 / 16 |
| 1980s | 29 | 6 | 28 (96.55%) | 0 | 1 | 18 | 2 / 22 |
| 1990s | 29 | 3 | 26 (89.66%) | 0 | 3 | 17 | 2 / 23 |
| 2000s | 28 | 4 | 26 (92.86%) | 1 | 1 | 23 | 4 / 24 |
| 2010s | 28 | 11 | 26 (92.86%) | 1 | 1 | 15 | 5 / 21 |
| 2020–2026 | 28 | 9 | 26 (92.86%) | 2 | 0 | 13 | 4 / 15 |

## Available metadata

Coverage counts assets with at least one supporting cached value; multiple conflicting values remain separate. These are not canonical recording attributes or verified original-release dates. Album includes compilations.

| Field / semantic level | Assets | % accepted | % sample |
|---|---:|---:|---:|
| release_date | 169 | 100.0 | 84.5 |
| duration | 168 | 99.41 | 84.0 |
| release | 169 | 100.0 | 84.5 |
| release_group | 169 | 100.0 | 84.5 |
| album_release | 164 | 97.04 | 82.0 |
| recording_ids | 169 | 100.0 | 84.5 |
| artist_ids | 169 | 100.0 | 84.5 |
| isrc | 140 | 82.84 | 70.0 |
| work_relations | 21 | 12.43 | 10.5 |
| recording_genres | 22 | 13.02 | 11.0 |
| recording_tags | 133 | 78.7 | 66.5 |
| recording_lookup_available | 45 | 26.63 | 22.5 |
| release_group_genres | 35 | 20.71 | 17.5 |
| release_group_tags | 36 | 21.3 | 18.0 |
| release_group_lookup_available | 42 | 24.85 | 21.0 |
| artist_genres | 40 | 23.67 | 20.0 |
| artist_tags | 40 | 23.67 | 20.0 |
| artist_lookup_available | 46 | 27.22 | 23.0 |

Genres/tags retain their original objects, counts, entity IDs, cache references, timestamps, and recording/release-group/artist scope. Tags are not necessarily genres. No taxonomy or inheritance is applied.
Detailed lookups were originally requested only after Phase 2A acceptance. New links primarily have search metadata. Lookup availability above is at least one lookup per asset, not complete coverage of all its linked entities. Missing genre values on unfetched entities are **unknown**, not proven absent. Thus this replay measures recoverable cached coverage, not the ceiling after targeted lookups.

## Temporal evidence

`{"accepted_only_following_year_anchor": 3, "accepted_with_later_or_undated_support": 97, "compatible_but_no_anchor": 10, "impossible_artist_chronology_candidates": 0, "invalid_date_evidence": 0}`

At least one compatible recording must have a returned release date no later than first-chart year + 1. Partial dates are intervals. The one-year allowance retains Phase 2A's heuristic and is flagged separately when it is the only support; it does not infer an original release date. Later/undated recordings can support the same artist-ID group once that asset has an anchor. Late dates alone are not called impossible, but they cannot establish temporal support in this precision-first replay.
An artist's cached birth/formation after first-chart year + 1 is negative evidence. Unexpected live/remix/re-recorded/demo/karaoke/instrumental/acoustic/video/DJ-mix markers cannot supply support. Unrecognized disambiguation text is also excluded; only an explicit list of edition descriptors is allowed. No new biography lookup is made. Absence of impossible evidence is not proof of chronology.

## Matching and review

The exact rule and normalization are documented in [the experiment instructions](../experiments/phase2ar/README.md). Full normalized title and artist credit must agree, with one consistent artist-ID set and a release anchor. Search relevance is recorded, not treated as identity probability. Multiple recordings do not veto the asset. Search truncation remains a visible risk flag rather than proof that the observed asset is ambiguous.
All 124 newly accepted assets are included in a deterministic [review packet](phase2ar_review.md); see [review findings](phase2ar_review_notes.md) for the qualitative audit. Acceptance is algorithmic, never manually promoted. Counts are algorithmic coverage, not measured precision; there is no independent labelled gold standard.
Accepted review flags: `{"anchor_only_in_following_year": 3, "bounded_search_truncated": 6, "content_version_requires_future_resolution": 15, "duration_outlier_review": 2, "formatting_normalization_used": 83, "later_or_undated_recordings_supported_by_asset_anchor": 97, "no_date_definitely_before_chart": 46, "version_descriptors_retained": 40}`.

## Comparison and recommendation

Unchanged Wikidata Phase 2B accepted 99/200 (49.5%) and exposed genre statements for 84/200 (42%). MusicBrainz asset matching and Wikidata overlap on 95 assets; their provisional union is 173/200 (86.5%). This is a union of algorithmically accepted assets, not a validated merged crosswalk.
Wikidata genres span recordings, singles, compositions, and generic song items. Its 42% cannot be compared as if all were recording genres. MusicBrainz now offers substantially more usable identity/release evidence, while Wikidata can contribute complementary song-level context. Neither source justifies silently borrowing artist or compilation genres.
Do not scale yet. Independently review the new links, resolve flagged chronology/version cases, then test bounded detailed MusicBrainz lookups for the recovered assets and compare raw genre coverage at explicit semantic levels. Keep recordings/editions unresolved for identity enrichment; choose a defensible version policy before lyrics or version-sensitive measurements.

## Reproduction and limits

Run `python3 src/phase2ar.py` and `python3 -m unittest discover -s tests -v` from the repository root. Full commands and cache prerequisites are in the experiment instructions. The ignored summary stores input, cache, and code fingerprints. Outputs contain no run timestamp, so the frozen-input replay is byte deterministic.
This deliberately balanced 200-asset stress sample is not a population estimate. Search limits and Phase 2A query design still constrain recall. Genre lookups are acceptance-biased; aggregating editions can mix durations, dates, clean/explicit variants, and compilation context. Precise numerical gains do not establish zero false positives.
