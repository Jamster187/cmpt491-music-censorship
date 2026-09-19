# Phase 2A: inspected examples and limitations

These notes describe the cached experiment, not an independently labeled accuracy
study. No decisions were manually promoted or forced. Every example below can be
found by title/artist in `data/experiments/phase2a/matches.csv`; its `song_id` locates
the complete candidate evidence and response-cache references under `results/`.

## Clear title/credit agreements

- **“Break My Stride” / Matthew Wilder:** the accepted recording has the same title
  and credit, a 1983-07-01 first release, and duration 182,226 ms. The first Billboard
  appearance is 1983-09-17. It has eight raw recording genres, all retained.
- **“Once You Get Started” / Rufus Featuring Chaka Khan:** both credited performers
  are retained in the external credit. The 1974 release precedes the 1975 chart
  appearance. This illustrates a successful featured-credit match.
- **“Wild Horses” / Susan Boyle:** the accepted credit is Susan Boyle, with a
  2009-11-23 release before the 2009-12-12 chart appearance. The asset stays attached
  to that performer; it is not merged with another performer's version.
- **“Secreto” / Anuel AA & Karol G:** the external credit includes both artists;
  its 2019-01-15 date supports the February 2019 Billboard appearance. Both artist
  IDs and their separate raw tag lists are retained.

These are strong metadata agreements, not proof that the selected recording is
the exact radio/single version represented by Billboard.

## Ambiguities and restrictive rules

- **“Call Me” / Le Click:** several identically credited recordings have compatible
  1997/1998 dates and different durations. No recording is selected. The separate
  Billboard asset **“Call Me” / Blondie** is also in the sample; it is not merged
  with Le Click and has its own competing recordings.
- **“A Brand New Me” / Dusty Springfield:** title and artist agree, but retrieved
  dates are much later than the 1969 chart appearance. The matcher cannot establish
  whether those dates reflect incomplete original-release metadata or a different
  version, so it leaves the match ambiguous.
- **“As Long As You Love Me” / Justin Bieber Featuring Big Sean:** the fallback
  search retrieves full-credit/title agreements with compatible 2012 dates, but
  their search scores are 88, below the experimental threshold of 95. This shows
  why a query-relative relevance score can unnecessarily reduce recall; the
  threshold should be evaluated on labeled cases before scaling.
- **“Pretty In Pink” / Psychedelic Furs** and **“Make Me Feel” / Janelle Monae:**
  the returned credits include “The Psychedelic Furs” and “Janelle Monáe”. The
  matcher preserves leading articles and accents rather than silently equating
  these names. A reviewed artist-ID/alias crosswalk could help.

## Retrieval failures and edge cases

- **“Vincent (Starry, Starry Night)/Castles In The Air” / Don McLean:** both searches
  return no candidates. A combined Billboard title need not have a corresponding
  combined MusicBrainz recording title. Splitting it would require an explicit
  mapping policy; the original asset is unchanged.
- **“Try My Love Again” / Bobby Moore's Rhythm Aces featuring Chico** and
  **“Shell Shocked” / Juicy J, Wiz Khalifa & Ty Dolla $ign Featuring Kill The Noise &
  Madsonik:** the bounded searches return no candidates. This does not establish
  that the recordings are absent from MusicBrainz; retrieval of unusual credits
  needs separate investigation.
- **“It's Beginning To Look A Lot Like Christmas” / Perry Como And The Fontane
  Sisters With Mitchell Ayres And His Orchestra:** a first chart appearance in
  2018 places it in the 2010s sample, while one candidate has a 1951 release date.
  Three candidates pass the basic evidence checks, so the result remains ambiguous.
  Chart period and recording age must not be treated as the same variable.
- **“Who Found Who” / Jellybean Featuring Elisa Fiorillo:** the accepted recording
  has a 1988 date while the asset first charted in 1987. It passes the documented
  one-year tolerance. That tolerance and incomplete/reissue dates deserve review;
  acceptance is not an assertion that the song was first released in 1988.
- **“Black & Chinese” / Huncho Jack:** the accepted recording has a raw `hip-hop`
  tag but no formal MusicBrainz genre. Keeping both raw fields matters; this pilot
  neither drops the tag nor maps it into a finalized genre taxonomy.

## Implications before a larger run

The largest obstacle is requiring one recording MBID for a research asset defined
as a title/artist pair. An explicit, reviewed one-to-many recording association may
be more appropriate than loosening scores until something matches. Artist linkage,
recording/version linkage, and genre evidence should remain separate decisions.

Genre sparsity and coverage differences across periods make this run unsuitable
as the final study population. Establish acceptable matching precision using a
human-labeled review set, refine retrieval/alias rules, and then check them on a
fresh sample. Any proposed artist- or release-group genre proxy needs its own
justification; current artist tags may reflect an artist's whole career rather
than a particular historical recording. No content-trend analysis was performed.
