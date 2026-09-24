# Phase 2A source decision

Documentation checked on 2026-09-19. **Test MusicBrainz only** in this pilot. It
provides public recording searches and persistent identifiers without requiring
credentials, so it is a practical starting point for the 200-song experiment.

## Available metadata

| Entity | Useful returned fields |
| --- | --- |
| Recording | Title, full artist credit, MBID, duration in milliseconds, first release date, ISRCs, disambiguation, video flag, genres/tags, ratings, linked works |
| Artist | MBID, credited/canonical names, aliases, type, country/area, life-span, genres/tags |
| Release | MBID, title, date, status, country, text language/script, release-group reference; other returned fields remain in raw responses |
| Release group | MBID, title, first release date, primary/secondary types, genres/tags |

These are community-maintained fields, not guaranteed values. Search responses
give candidate metadata; entity lookups request richer data. Dates can be partial
and can describe a reissue. A title/artist pair may have several recording MBIDs.
The search index supports combined artist credit, individual artist names, title,
duration, ISRC, and release-date fields. Search scores rank retrieval relevance;
they are not match probabilities. [Recording search documentation](https://musicbrainz.org/doc/MusicBrainz_API/Search#Recording)

Public `genres` and `tags` are available through lookup includes. Genres are a
subset of community tags; unrestricted tags can describe moods, eras, or other
non-genre properties. Their votes and entity level must be preserved. Recording
genres, album/release-group genres, and artist genres answer different questions.
Lookup includes return at most 25 linked entities; a full discography would require
browse requests. This bounded pilot does not claim exhaustive release coverage.
[API documentation](https://musicbrainz.org/doc/MusicBrainz_API)

## Access and etiquette

Public metadata reads need no API key or login. Authentication is needed for
submissions and user-specific data, which this project does not request.
Non-commercial API use is free. [API access documentation](https://musicbrainz.org/doc/MusicBrainz_API#General_FAQ)

MusicBrainz requires no more than one request per second and an identifying
User-Agent with a contact URL/email. Our client uses
`CMPT491MusicMetadata/0.1 (https://github.com/Jamster187/cmpt491-music-censorship)`.
It spaces requests by at least 1.1 seconds, prevents simultaneous client runs,
caches all responses, honors Retry-After, and backs off on 429/503 and other
transient errors. Three consecutive failed songs stop the run for inspection.
[Rate limiting and identification](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)

## Terms relevant to this class project

Core MusicBrainz metadata is CC0. Supplementary data, including user tags,
genre associations, and ratings, is CC BY-NC-SA 3.0. Non-commercial use therefore
still needs appropriate attribution and compatible sharing of derivative
supplementary data. We credit MusicBrainz and retain raw provider information;
cached/enriched data is kept out of Git while the approach is reviewed.
[Data license](https://musicbrainz.org/doc/About/Data_License),
[core/supplementary breakdown](https://musicbrainz.org/doc/MusicBrainz_Database)

## Possible complements, not tested

Wikidata is a freely accessible candidate for additional genre statements linked
through identifiers rather than fuzzy text. Its structured data is CC0; it has
[genre statements (P136)](https://www.wikidata.org/wiki/Property:P136) and
[MusicBrainz release-group identifiers (P436)](https://www.wikidata.org/wiki/Property:P436).
The inference is that these could supplement release-group context; their coverage
and consistency for our songs have not been measured. It is not a substitute for
song-level validation. [Wikidata data access](https://www.wikidata.org/wiki/Wikidata:Data_access)

Discogs also distinguishes raw genres and styles on releases, making it a possible
later comparison. No Discogs API calls or integration were made, and its access
requirements/terms need a separate check before use.
[Discogs genre/style guidelines](https://support.discogs.com/hc/en-us/articles/360005055213-Database-Guidelines-9-Genres-Styles)
