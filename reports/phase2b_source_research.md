# Phase 2B source research

Documentation checked on 2026-09-19, before implementing a new API client.
The research unit remains the exact Billboard title + artist pair. No provider
promises complete coverage of Billboard, either historically or through 2026.
Coverage must be measured on the unchanged Phase 2A sample.

## Decision

**Last.fm is the best functional fit for a title/artist tag lookup. Wikidata is
selected for the pilot that can run with the access currently available.** No
Last.fm key or Discogs token is configured. The user confirmed that Last.fm academic
access has not been arranged. Discogs also
has API retention/display conditions that need clarification for frozen research
snapshots. Wikidata's public structured data is CC0 and needs no key.

This is an access-constrained choice, not a claim that Wikidata has the best genre
coverage. Last.fm and Discogs are researched, not empirically compared on 200 songs.
No API keys from examples or third-party projects are used. No provider is scraped.
One Discogs API access check, described below, is not a song-enrichment pilot.

## Last.fm

- `track.getInfo` accepts artist + track, or a MusicBrainz ID. It returns track and
  artist names/URLs, optional MBIDs, duration (milliseconds), album context, top
  tags, listeners, and play counts. These last two are current aggregates, not
  historical Billboard popularity. The wiki publication timestamp is **not** a
  release date. Reliable original-release dates are not part of this method's
  documented response. [Track metadata](https://www.last.fm/api/show/track.getInfo)
- `track.getTopTags` returns track-level community tag strings, counts and URLs.
  They can include genre, mood, decade or personal labels. Preserve all returned
  values and their track scope; artist/album tags from other methods have different
  scopes. Autocorrection must be recorded and validated, never silently accepted.
  [Track tags](https://www.last.fm/api/show/track.getTopTags)
- Both reads require an application API key, but no signed user session. There
  is no documented historical-year cutoff in these methods, so older recordings
  and new songs are addressable. Availability of tags for either era, including
  2026 releases, is unmeasured; an addressable track need not have useful tags.
- The current terms ask commercial **and research/academic** users to contact
  `partners@last.fm` before use. They specify attribution/linking, a 100 MB total
  usage/storage cap without prior written consent, caching according to response
  headers, and restrictions on redistribution. They leave rate limits to Last.fm's
  discretion; no fixed numerical quota is stated there. Error 29 signals excessive
  requests. A future pilot should use one slow client and backoff, and agree on
  snapshot retention and eventual dataset sharing before scaling.
  [API terms](https://www.last.fm/api/tos)

## Discogs

- Release/master records offer titles, artist credits, years/dates, labels,
  formats, country, track lists and identifiers. Track durations may be present.
  Genres and styles describe the **release/master**, not independently every track.
  A genre on a multi-artist compilation cannot be assigned to each song. Raw genres
  and styles should stay separate. [Genre/style guidelines](https://support.discogs.com/hc/en-us/articles/360005055213-Database-Guidelines-9-Genres-Styles)
- Search supports release searches with artist and other filters, followed by
  track-list verification. This is less direct than Last.fm's track lookup. Discogs'
  own archived client documents identifying User-Agents, personal tokens and OAuth.
  [Search examples](https://github.com/discogs/discogs_client/blob/master/docs/quickstart.md),
  [authentication](https://github.com/discogs/discogs_client/blob/master/docs/authentication.md)
- Its release-oriented catalog makes physical singles and historical releases
  plausible strengths; this is an inference, not a measured coverage advantage.
  Modern physical/digital releases can be represented, but neither availability
  nor completeness through 2026 has been established on this sample.
- The current developer specification returned HTTP 403 here. A subsequent direct
  access check to `https://api.discogs.com/database/search?type=release&per_page=1`
  returned HTTP 200 **without credentials**, with `X-Discogs-Ratelimit: 25` and
  remaining/used counters. Its one catalog result included year, release title,
  genres, styles, format, country, labels and identifiers. This is evidence that
  this public search works currently, not a guarantee for all endpoints. The exact
  reset window and authenticated quota remain unverified from current primary
  documentation; inspect headers and confirm the specification before a larger
  run. The complete access-check response is retained locally at
  `data/cache/phase2b_source_checks/discogs_search_access.json`. No sampled assets
  were enriched with Discogs.
- Terms distinguish CC0 catalog fields from restricted user/marketplace/image
  data. They require attribution and links, restrict storage to what is necessary
  for the application's service, and restrict display of content more than six
  hours older than current site information. Frozen, shareable academic snapshots
  need clarification; the general CC0 field list does not erase API conditions.
  [API terms](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use)

## Wikidata

- Song/track/single items can have performer IDs (`P175`), genre statements
  (`P136`), publication dates (`P577`), duration quantities (`P2047`), parent album
  links (`P361`), labels, composers, producers, language and external identifiers.
  The entity's `P31` types matter: the music project explicitly warns that work,
  track and single concepts are often combined. A song item's genre is not a
  demonstrated recording-level genre, and artist genres remain artist context.
  [Music data model](https://www.wikidata.org/wiki/Wikidata:MUSIC),
  [publication date](https://www.wikidata.org/wiki/Property:P577),
  [duration](https://www.wikidata.org/wiki/Property:P2047)
- There is no dedicated artist + track endpoint. Text searches retrieve candidates;
  structured performer claims and entity labels/aliases can then verify the pair.
  Public reads need no login, API key or research permission. Labels, claims,
  qualifiers, references, statement ranks and revision IDs can be cached together.
  [Wikibase API](https://www.mediawiki.org/wiki/Wikibase/API),
  [search](https://www.mediawiki.org/wiki/Help:Extension:WikibaseCirrusSearch)
- Historical and contemporary songs are eligible for entries, including 2026, but
  editorial coverage is uneven. No completeness guarantee or annual coverage
  percentage follows from the data model. This pilot measures retrieval and
  matching yield, not the total number of songs that exist somewhere in Wikidata.
- Structured data is CC0. Send an identifying User-Agent, cache requests, use
  `maxlag`, and respect 429/503 and Retry-After. The current global table allows
  200 requests/minute for unauthenticated bots with a compliant User-Agent and
  recommends at most three concurrent requests. This pilot will use one client
  with at least 1.1 seconds between requests. [Data access](https://www.wikidata.org/wiki/Wikidata:Data_access),
  [current rate limits](https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits),
  [Action API etiquette](https://www.mediawiki.org/wiki/API:Etiquette)
- SPARQL is an alternative, with a 60-second query deadline, 60 seconds of CPU
  allowance per minute per client, 30 error queries/minute and five parallel
  queries/IP. We use the Action API for bounded text retrieval and entity lookups,
  avoiding broad text scans through SPARQL. [Query-service limits](https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual#Query_limits)

## Pilot boundaries

Reuse the exact Phase 2A sample and first-chart period buckets. Preserve raw genre
statements with entity ID/type, label, qualifiers, references, rank and retrieval
provenance. Resolve performers before accepting a title match. Multiple covers
on one work item need particular care; no genre transfers between performers or
from artists/albums to tracks. Retain unaccepted candidates for review.

No final genre categories, lyrics, classifier, full-population enrichment or
canonical database changes are part of this pilot. A Last.fm comparison remains
valuable if academic access and a project key become available.
