# Genre sources reviewed, 21 September 2026

The pilot uses existing caches only. Web requests in this task were for source
policies/documentation and qualitative review, not a song-population crawl.
No source guarantees complete coverage of every year from 1958–2026.

| Source | Level and identity | Access / reuse | Use in this experiment |
| --- | --- | --- | --- |
| MusicBrainz | Recording, release, release group, artist; exact accepted MBIDs preserve the Billboard asset crosswalk | Public metadata API; identify client and stay at or below one request/second; cache and back off. Genre/tag associations are supplementary CC BY-NC-SA 3.0 data, not CC0 core metadata. | Main cached direct evidence. Keep entity level and positive vote count. Votes indicate community support, not calibrated confidence. |
| Wikidata | P136 on song/work/single, album or artist items; accepted full-performer crosswalks and exact artist P434 IDs | Structured data CC0. Action API supports batched entity reads; use serial requests, descriptive User-Agent, maxlag and backoff. | Small archived song-level supplement and wider artist context; preserve statement ID, revision, qualifiers and references. |
| Last.fm | Track tags via title + artist or MBID; social tags include non-genres and popularity effects | API key required, although user authentication is not. Academic/research use requires prior contact; default data cap is 100 MB and exceeding it requires written consent. No guaranteed numeric rate allowance established here. | Potential later fallback, not queried. No academic access arrangement is on record. Disable autocorrection or explicitly revalidate any changed identity. |
| Discogs | Release/master genres and styles; track identity is secondary to release identity | API terms constrain caching and displaying stale content; they are problematic for frozen reproducible research. The developer page returned 403 during this review, so no current numeric rate is asserted. | Existing generic access probe is not song-linked evidence. Compilation genres cannot simply become every track's genre. Not selected. |

MusicBrainz covers older catalogue releases as well as recent recordings, but cached
search responses are not exhaustive genre lookups. Repeated editions are not
independent corroboration. Wikidata can describe composition or original-single
genre rather than a particular performance; the semantic level matters. Both
sources are community-edited and can share underlying references, so their apparent
agreement is not automatically independent validation. Last.fm track tagging may
help coverage but has not been measured here. Discogs is attractive for older
physical releases, but neither that nor its broad styles solve track specificity.

Sources:

- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) and [rate limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting).
- [MusicBrainz database components](https://musicbrainz.org/doc/MusicBrainz_Database), [data license](https://musicbrainz.org/doc/About/Data_License), and [folksonomy tagging](https://musicbrainz.org/doc/Folksonomy_Tagging).
- [Wikidata licensing](https://www.wikidata.org/wiki/Wikidata:Licensing) and [MediaWiki API etiquette](https://www.mediawiki.org/wiki/API:Etiquette).
- [Last.fm track.getTopTags](https://www.last.fm/api/show/track.getTopTags) and [API terms](https://www.last.fm/api/tos).
- [Discogs API terms](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use).
