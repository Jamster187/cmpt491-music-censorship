# Final genre audit

**COMPLETE.** No active genre worker; no restart or reclassification performed.

Target/completed: 28,041 / 28,041. Remaining: 0. Outstanding errors: 0. Duplicate/missing IDs: 0 / 0.

Last classification: Not Meant To Be — Theory Of A Deadman, 2026-09-23T03:13:53.146494+00:00. Completion marker: 2026-09-23T03:13:53.704812+00:00.
The marker, all 2,805 completed batches, log ending and complete local export agree. The operating-system exit code was not retained.

Attempts: {'completed': 2774, 'error': 13, 'recovered': 1}. 12 malformed responses, 10 unaccepted response rows; all affected songs later resolved. These historical failures are not outstanding song errors.
The recovered attempt retains its old transport error. Private events confirm a WebSocket-to-HTTPS fallback; the capacity failure contains no completed response. No tool calls or alternate model/API path were accepted.

## Confidence

| Confidence | Count |
|---|---:|
| high | 18,621 |
| medium | 7,538 |
| low | 1,882 |

## Genre distribution

Unique assets; denominator 28,041. Percentages are descriptive, not population-weighted trend estimates.

| Genre | Count | Percent |
|---|---:|---:|
| Pop | 6,492 | 23.15% |
| Rock | 5,028 | 17.93% |
| Hip-Hop / Rap | 3,401 | 12.13% |
| R&B / Soul | 5,935 | 21.17% |
| Country | 3,032 | 10.81% |
| Latin | 381 | 1.36% |
| Electronic / Dance | 963 | 3.43% |
| Alternative / Indie | 762 | 2.72% |
| Metal | 144 | 0.51% |
| Folk / Singer-Songwriter | 477 | 1.70% |
| Jazz / Blues | 698 | 2.49% |
| Reggae / Dancehall | 144 | 0.51% |
| Gospel / Christian | 64 | 0.23% |
| K-Pop | 51 | 0.18% |
| Afrobeats / African Pop | 13 | 0.05% |
| Other | 456 | 1.63% |

## Counts by first-chart period

Each asset is counted once by its first Billboard chart date, not release date or every later chart appearance. Zero cells are explicit. No historical interpretation.

| Genre | 1958–1969 | 1970s | 1980s | 1990s | 2000s | 2010–2019 | 2020–2026 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pop | 2158 | 989 | 1112 | 532 | 485 | 776 | 440 |
| Rock | 1317 | 1495 | 1453 | 399 | 277 | 66 | 21 |
| Hip-Hop / Rap | 0 | 1 | 54 | 595 | 701 | 990 | 1060 |
| R&B / Soul | 2007 | 1442 | 671 | 831 | 540 | 267 | 177 |
| Country | 418 | 405 | 145 | 214 | 667 | 676 | 507 |
| Latin | 31 | 4 | 11 | 29 | 43 | 66 | 197 |
| Electronic / Dance | 1 | 210 | 206 | 287 | 58 | 167 | 34 |
| Alternative / Indie | 0 | 6 | 141 | 256 | 179 | 96 | 84 |
| Metal | 0 | 2 | 47 | 43 | 43 | 5 | 4 |
| Folk / Singer-Songwriter | 174 | 202 | 30 | 9 | 14 | 21 | 27 |
| Jazz / Blues | 484 | 106 | 65 | 21 | 4 | 8 | 10 |
| Reggae / Dancehall | 9 | 14 | 17 | 58 | 35 | 8 | 3 |
| Gospel / Christian | 14 | 13 | 4 | 11 | 10 | 6 | 6 |
| K-Pop | 0 | 0 | 0 | 0 | 1 | 9 | 41 |
| Afrobeats / African Pop | 1 | 1 | 0 | 1 | 0 | 0 | 10 |
| Other | 194 | 118 | 44 | 43 | 8 | 7 | 42 |
| Total | 6808 | 5008 | 4000 | 3329 | 3065 | 3168 | 2663 |

## Bounded qualitative review

Reviewed: 160. Plausible: 129. Questionable: 29. Clearly wrong: 2.

The unchanged `genre-post-run-review-v1` selector takes two per available genre, 15 per confidence level, five per period, then hash-fills the union to 160. All 16 genres, three confidence levels and seven periods are covered. Exact coverage is in validation.json.

Review was performed by the Codex assistant using exact identities, model reasons, retained evidence and targeted external checks. It is not an independent human/musicologist review or a listening study. Plausible means broadly defensible, not verified ground truth; questionable includes inadequate evidence and legitimate boundaries. This stratified diagnostic sample is not an accuracy estimate.

The two clearly wrong primary choices are José Feliciano’s anthem as Other, despite its [folk arrangement](https://www.pbs.org/wgbh/americanexperience/features/woodstock-star-spangled-banner/), and Lil Wayne’s Knockout as Rap, despite a contemporary review describing its [power-pop/punk style](https://www.rapreviews.com/2010/02/lil-wayne-rebirth/). These are review judgments; production labels remain unchanged.

Systemic concerns: artist identity and broad tags can override song-specific arrangements; scene categories compete with musical styles (including the two Jung Kook singles); novelty/anthem/soundtrack function can displace style; sparse older/recent identities encourage uncertain default labels. Pop/Rock, Latin/Rock, Jazz/Pop and alternative-R&B boundaries remain inconsistent. Secondary labels remain provisional. This sample cannot establish time-invariant or genre-invariant error rates.

All 160 judgments and supporting notes are in [review.csv](genre_final_audit/review.csv). No individual production label was rewritten.

## Validation

321 tests passed. SQLite integrity, exact population/batch/export coverage, all structured outputs, response provenance, frozen request bytes/model/config/taxonomy, 45-word prompt limit and protected hashes pass. 21,706 protected files remain identical, including 21,693 lyric files, Billboard, metadata, both classifier databases and existing public datasets.

Phase 1, the combined corpus audit and both production classifier validators passed. Classifier coverage remains 20,981 songs, including 20,979 with all 42 features. The original classifier validator requires `--allow-incomplete` for the two documented LyricLens exceptions; the strict combined corpus audit checks those exceptions explicitly. The catch-up validator requires its documented classifier virtual environment (system Python lacks torch). Initial invocations without those requirements failed; no model or data changes were needed. Logs are private. The 42-feature methodology is unchanged. The frozen model name is an alias rather than an immutable service checkpoint; request manifests record the requested configuration, not an independently attested server checkpoint.

Repository artifact inspection found no historical/COVID trend analysis or final weekly/monthly master build. Existing descriptive quality reports and earlier monthly experiments remain preserved. No such analysis or dataset construction was performed in this audit.

Reproduce: `python3 src/genre_final_audit.py` after `python3 -m unittest discover -s tests -v > data/experiments/genre_production/final_tests.log 2>&1`. The script opens production SQLite read-only, validates the authored review against the deterministic sample, and regenerates this report and aggregate JSON.
