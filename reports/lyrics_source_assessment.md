# Lyrics source assessment

Checked 2026-09-19. **No lyrics source is selected for acquisition yet.** No lyrics
API payloads were requested, no lyric pages were scraped, and no full acquisition
started. This is a project access/permission blocker, not a finding that legitimate
academic access cannot exist. The user's required acquisition/storage permission
has not been established for this project and corpus.

## Candidates

| Source | Full text / title + artist lookup | Authentication and rate limits | Storage/reuse decision |
|---|---|---|---|
| Musixmatch | Official API supports catalogue matching and lyrics retrieval, subject to the account's access and restrictions | API key required; applicable quota and full-text entitlement must be agreed/verified | No project key or agreement is configured. API access alone does not establish persistent corpus storage or later classifier-use rights. |
| LyricFind | Licensed static and synchronized lyrics products; catalogue integration requires provider arrangements | No project credentials; operational API quota/authentication must come from the licensed integration | A promising licensing route, but no academic corpus/storage agreement is present. Do not substitute website scraping. |
| LRCLIB | Public API returns plain/synchronized lyrics; search accepts track_name and artist_name; signature lookup additionally uses album and duration | No key; identifying User-Agent, sequential requests, 200–500 ms extra delay, respect 429/Retry-After; no fixed numeric public quota found | Automated access and offline downloads are explicitly supported. A grant covering the underlying lyrics for this academic corpus and planned downstream use was not established. Do not confuse its MIT software license with a lyrics-content license. |
| Genius / LyricsGenius | Search/artist/song metadata is available; the wrapper obtains full lyrics by scraping song webpages | Developer API uses a token; scraping is not an acceptable workaround for unavailable full-text entitlement | Not selected. The wrapper's own documentation says its scraping violates Genius terms. |

Musixmatch's [official SDK specification](https://github.com/musixmatch/musixmatch-sdk/blob/master/swagger/swagger.json)
documents matching, lyrics retrieval, API-key authentication, and licensed content.
Its [current official API workspace](https://www.postman.com/musixmatch-dev/musixmatch-apis/collection/pqm8o6w/lyrics-api)
also requires an API key. The linked API-terms/FAQ pages were not accessible through
the research browser here. Consequently no historic free-tier quota, percentage
of available lyrics, or cache-retention allowance is asserted as current fact.
Those details need provider confirmation for this project's entitlement.

LyricFind describes [lyrics and data licensing](https://www.lyricfind.com/),
[full-text display formats](https://www.lyricfind.com/products/lyric-display), and
[search products](https://www.lyricfind.com/products/lyric-search). These are
evidence of a possible licensed route, not an active research license. Its
[website terms](https://www.lyricfind.com/terms-and-conditions) do not provide a
general corpus reproduction grant. An academic precedent, the
[NUS LyricFind corpus](https://smcnus.org/lyrics/), distributes bag-of-words data
rather than the full ordered lyrics required here; it cannot simply replace the
requested text files or establish modern coverage through 2026.

LRCLIB's [API documentation](https://www.lrclib.net/docs) supports automated reads,
full-text search responses, caching-friendly IDs, and request etiquette. Its
[official LRCGET client](https://github.com/tranxuanthang/lrcget) explicitly saves
downloaded lyrics for offline music libraries. Thus there is **no finding that
LRCLIB prohibits automation or local storage**. The unresolved question is
permission for this project's large academic corpus and intended reuse of the
underlying lyrics. Its [server repository](https://github.com/tranxuanthang/lrclib)
provides an MIT software license, not a verified publisher-content license. A
[legal-documentation proposal](https://github.com/tranxuanthang/lrclib/pull/74) was
still open when inspected; it is not adopted policy. No assumption that academic
use is automatically authorized, or automatically unlawful, is made here.

For Genius, [LyricsGenius's own implementation documentation](https://lyricsgenius.readthedocs.io/en/master/how_it_works.html)
explains that full text comes from page scraping rather than its developer API.
Direct Genius terms/API documentation were inaccessible in the research browser;
this project does not attempt to bypass that or use an unofficial scraper.

## Coverage and access limits

None of the checked sources establishes exhaustive Billboard coverage for either
1958–1969 or 2020–2026. Historical and modern percentages are **not measured**:
no lyrics pilot ran. In particular, 0% acquired for 2015–2019 and 2020–2026 means
not acquired, not absent from those providers. Search/signature services can
address old and new tracks but community/licensed catalogues change over time.
Country restrictions, missing full-text entitlements, covers, live/remix versions,
clean/explicit versions, and omitted guests would need pilot review.

Only credential *presence* was checked: no Musixmatch/LyricFind/Genius credentials
were configured in the relevant environment variables and no local `.env` exists.
No credential values were printed. No provider was contacted on the user's behalf.

## Exact blocker and next step

Establish a source entitlement that covers automated retrieval of roughly 25,363
title/artist assets, retention of the full texts in a private research corpus,
and the intended subsequent classifier processing. Clarify permitted duration,
territory, attribution, derivative measurements, third-party processing, deletion,
and whether summaries can be published without texts. Musixmatch or LyricFind are
the clearest licensed avenues; LRCLIB remains a technically practical candidate
if an appropriate basis for this research use is established.

The deterministic 200-song **study-population** pilot is prepared locally, but
its retrieval and quality gates are not passed. No acquisition client is invented
for an unapproved source. Once access is resolved, implement the chosen provider's
documented API, run that pilot, inspect matches/content versions, and only then
consider the already-authorized automatic full run. Current manifest statuses
are `blocked_source_access`, never fabricated `not_found` results.
