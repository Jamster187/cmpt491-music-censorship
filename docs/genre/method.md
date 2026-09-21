# Genre feasibility experiment (v1)

This is a pilot, authorized separately from the earlier acquisition stages. It
must not update production tables or the public master dataset.

## Rebuild

With the existing local metadata databases and caches present:

```sh
python3 src/genre_evidence.py
python3 src/genre_sample.py
python3 src/genre_pilot.py
python3 src/genre_validate.py
python3 -m unittest discover -s tests -v
```

The first command inventories evidence and refuses to replace an existing frozen
inventory. On replay, skip it and reuse `data/experiments/genre_pilot/evidence.db`.
The second command refuses a changed sample. The third only assigns the frozen
300 IDs. The validation command checks a local pre-experiment protection manifest; retain
that manifest when reproducing this run. No command makes network requests. Cached acquisition payloads, revisions,
entity levels, matching basis and source hashes stay in ignored local artifacts.
The mapping and code hashes are recorded in the pilot summary. Manual review
notes are a separate qualitative artifact, never score overrides.

## Taxonomy and mapping

`taxonomy_mapping.json` is the exact 16-value taxonomy and versioned alias table.
NFKC, case and whitespace normalization precede exact lookup. There is no substring,
fuzzy, nationality, language or artist-name genre inference. Unknown labels remain
unmapped. Ballad, oldies, party, vocal, chart-year tags and numeric tags are not
musical genres. Other requires affirmative evidence of an out-of-taxonomy style;
missing evidence leaves `primary_genre` empty, with an explicit status.

Composite styles can support multiple categories: pop rock supports Pop and Rock;
country rock supports Country and Rock; bossa nova supports Latin and Jazz / Blues.
Disco maps to Electronic / Dance, funk to R&B / Soul, and doo-wop to R&B / Soul.
These are operational broad-group choices, not universally correct definitions.
Amapiano supports both Electronic / Dance and Afrobeats / African Pop. Singular
Afrobeat is deliberately unmapped: it must not be mistaken for modern Afrobeats.

The taxonomy mixes musical styles with cultural/market categories (Latin, K-Pop,
Afrobeats) and a religious category. Real overlap is expected. K-Pop does not follow
from Korean nationality, Latin does not follow from Spanish lyrics, and African
nationality is not sufficient for Afrobeats. Singer-songwriter tags describe a
style here; a songwriting credit alone is not genre evidence.

## Evidence and primary genre

Only accepted production MusicBrainz entity links and accepted archived Wikidata
song crosswalks are used. Previously unselected cached search results can supply
tags only through the *same external entity ID*, never a new title match. Exact
Wikidata P434 crosswalks can provide artist context. Positive MusicBrainz votes are
required. Deprecated or qualified Wikidata P136 statements are not automatically
eligible. Raw statements remain preserved for review.

1. Recording or accepted song-item evidence is strongest. Preserve all mapped
   categories at this tier; repeated releases/cache responses do not get extra votes.
2. A single-specific release could support a fallback, but the existing asset links
   do not reliably establish that specificity. Release/release-group/album tags
   therefore remain context in this pilot, not automatic primary labels.
3. Artist-only evidence produces suggestions and an explicit context-only status,
   not a confident primary song genre. Collaborator styles are not silently assigned
   to every collaboration.

One supported category at the strongest eligible direct tier yields a candidate
primary. Multiple categories yield NULL primary, retained candidates, and ambiguity.
Weaker evidence cannot break a stronger tie. Generic `rock`/`rock music` is treated
as a parent when Metal or Alternative / Indie is explicitly supported; other rock
substyles/composites still create ambiguity. All tags remain visible either way.
`genre_confidence` is a categorical evidence grade, not a numerical probability or
validated accuracy claim. `confident_primary` means a single direct mapped category,
subject to source and mapping error; it is not a human-certified label.

Keep `song_id`, `primary_genre`, `mapped_genres`, `primary_candidates`,
`genre_confidence`, `genre_source`, `genre_ambiguous`, disposition, mapping version,
and a link to the evidence manifest. Artist/release context must be distinguishable
from direct evidence in any future production export.

## Sample and interpretation

Period is assigned from first Billboard appearance, not release date. Period quotas
are 43 each through 2019 and 42 for 2020–2026. The 63 predeclared challenge cases
exercise crossovers and global styles. The other 237 use a fixed SHA-256 ordering
and balanced peak-rank/credit-complexity strata within each period. Credit complexity
is a formatting proxy, not a reliable count of performers. The challenge sample and
unequal sampling fractions mean raw pilot percentages are not population estimates.
Full-population counts in this experiment measure *evidence availability only*;
no population-wide primary genres are assigned.
