# Genre production checkpoint

As of 2026-09-22T00:15:40.271207+00:00. **INCOMPLETE: production checkpoint, not final results.**

Target: 28,041. Completed: 370 (includes 300 reused approved pilot labels). Errors: 0. Remaining: 27,671.

Execution: ChatGPT-authenticated Codex CLI 0.155.1, GPT-5.5, medium reasoning. No separately billed API fallback.
Frozen pilot: `0514c2cdd1a3f52b9fe5cca704fe88a0d68c961e`. Runner launch commit: `fc412879fab834e50f1db720bbf31dcdbb70d1c6`.

New request attempts: 9; recorded request time: 0.053 hours. This excludes pilot inference and time between requests.
Recorded failed attempts: 1. Failures remain in the audit trail even when an identical-request retry fills the missing result.
Results database: 35,155,968 bytes, excluding active WAL. Final predictions export: pending completion.

## Confidence

| Confidence | Count | % completed |
|---|---:|---:|
| high | 260 | 70.27% |
| medium | 87 | 23.51% |
| low | 23 | 6.22% |

## Genres

Percentages use completed predictions only; these are not final population estimates. Confidence columns are counts.

| Genre | Count | % completed | High | Medium | Low |
|---|---:|---:|---:|---:|---:|
| Pop | 90 | 24.32% | 52 | 32 | 6 |
| Rock | 52 | 14.05% | 42 | 10 | 0 |
| Hip-Hop / Rap | 52 | 14.05% | 43 | 8 | 1 |
| R&B / Soul | 66 | 17.84% | 40 | 22 | 4 |
| Country | 36 | 9.73% | 28 | 5 | 3 |
| Latin | 9 | 2.43% | 9 | 0 | 0 |
| Electronic / Dance | 15 | 4.05% | 13 | 2 | 0 |
| Alternative / Indie | 10 | 2.70% | 6 | 3 | 1 |
| Metal | 2 | 0.54% | 2 | 0 | 0 |
| Folk / Singer-Songwriter | 7 | 1.89% | 6 | 0 | 1 |
| Jazz / Blues | 9 | 2.43% | 6 | 3 | 0 |
| Reggae / Dancehall | 3 | 0.81% | 3 | 0 | 0 |
| Gospel / Christian | 4 | 1.08% | 4 | 0 | 0 |
| K-Pop | 3 | 0.81% | 2 | 1 | 0 |
| Afrobeats / African Pop | 4 | 1.08% | 4 | 0 | 0 |
| Other | 8 | 2.16% | 0 | 1 | 7 |

## Period counts

Data-quality counts only; no historical interpretation.

| Period | Genre | Completed |
|---|---|---:|
| 1958–1969 | Country | 4 |
| 1958–1969 | Folk / Singer-Songwriter | 3 |
| 1958–1969 | Jazz / Blues | 6 |
| 1958–1969 | Other | 3 |
| 1958–1969 | Pop | 21 |
| 1958–1969 | R&B / Soul | 14 |
| 1958–1969 | Rock | 12 |
| 1970s | Country | 7 |
| 1970s | Electronic / Dance | 3 |
| 1970s | Folk / Singer-Songwriter | 3 |
| 1970s | Hip-Hop / Rap | 1 |
| 1970s | Jazz / Blues | 2 |
| 1970s | Metal | 1 |
| 1970s | Other | 1 |
| 1970s | Pop | 11 |
| 1970s | R&B / Soul | 13 |
| 1970s | Rock | 10 |
| 1980s | Alternative / Indie | 1 |
| 1980s | Country | 5 |
| 1980s | Electronic / Dance | 1 |
| 1980s | Folk / Singer-Songwriter | 1 |
| 1980s | Hip-Hop / Rap | 2 |
| 1980s | Latin | 1 |
| 1980s | Other | 1 |
| 1980s | Pop | 15 |
| 1980s | R&B / Soul | 10 |
| 1980s | Reggae / Dancehall | 1 |
| 1980s | Rock | 14 |
| 1990s | Alternative / Indie | 3 |
| 1990s | Country | 1 |
| 1990s | Electronic / Dance | 5 |
| 1990s | Hip-Hop / Rap | 14 |
| 1990s | Latin | 2 |
| 1990s | Metal | 1 |
| 1990s | Other | 1 |
| 1990s | Pop | 4 |
| 1990s | R&B / Soul | 14 |
| 1990s | Reggae / Dancehall | 1 |
| 1990s | Rock | 5 |
| 2000s | Alternative / Indie | 1 |
| 2000s | Country | 5 |
| 2000s | Gospel / Christian | 3 |
| 2000s | Hip-Hop / Rap | 9 |
| 2000s | Jazz / Blues | 1 |
| 2000s | Latin | 1 |
| 2000s | Pop | 11 |
| 2000s | R&B / Soul | 9 |
| 2000s | Reggae / Dancehall | 1 |
| 2000s | Rock | 10 |
| 2010–2019 | Alternative / Indie | 3 |
| 2010–2019 | Country | 8 |
| 2010–2019 | Electronic / Dance | 6 |
| 2010–2019 | Gospel / Christian | 1 |
| 2010–2019 | Hip-Hop / Rap | 13 |
| 2010–2019 | K-Pop | 1 |
| 2010–2019 | Latin | 2 |
| 2010–2019 | Pop | 14 |
| 2010–2019 | R&B / Soul | 2 |
| 2020–2026 | Afrobeats / African Pop | 4 |
| 2020–2026 | Alternative / Indie | 2 |
| 2020–2026 | Country | 6 |
| 2020–2026 | Hip-Hop / Rap | 13 |
| 2020–2026 | K-Pop | 2 |
| 2020–2026 | Latin | 3 |
| 2020–2026 | Other | 2 |
| 2020–2026 | Pop | 14 |
| 2020–2026 | R&B / Soul | 4 |
| 2020–2026 | Rock | 1 |

## Validation and remaining work

Latest stored test log: 305 tests; final OK marker: True. Protected-file check: 21706 files; unchanged: True. These are launch/checkpoint checks, not the final post-run audit.

Population IDs, input/request hashes, frozen configuration and completed structured outputs pass the production validator. Public datasets are not rebuilt by this runner.

Post-run protected-file validation, complete test suite and qualitative audit remain required. No post-run plausible/questionable/wrong counts are claimed before that review.

Rebuild this checkpoint with `python3 src/genre_production_audit.py`. Run/resume instructions are in [production.md](../../docs/genre/production.md).
