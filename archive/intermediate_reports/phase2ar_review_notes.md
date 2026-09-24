# Phase 2A-R review findings

This is a qualitative review of cached matching evidence, not an independent
ground-truth precision estimate. The deterministic packet includes **all 124 newly
accepted assets**, exceeding the requested 40. I inspected their original and
candidate credits, date ranges, recording multiplicity, and version descriptions,
then examined weak chronology, truncated searches, remaining ambiguous cases, and
extreme durations more closely. No external requests or manual promotions were
used. The complete packet is [phase2ar_review.md](phase2ar_review.md).

## Clear improvements

| Billboard asset | Evidence and interpretation |
|---|---|
| Holland Road — Mumford & Sons | First chart 2012-10-13; two compatible recordings, with 2012 release evidence including 2012-09-13. Phase 2A's multiple-recording veto did not establish asset ambiguity. |
| No Pressure — Justin Bieber Featuring Big Sean | First chart 2015-12-05; full `Justin Bieber feat. Big Sean` credit and 2015 releases, including 2015-11-12. Both performers remain required; ordinary and Atmos recordings support one asset. |
| It's Your Love — Tim McGraw With Faith Hill | First chart 1997-05-17; structured `Tim McGraw feat. Faith Hill`, with 1997 and 1997-06-03 release evidence. `With` is recognized at the two known artist boundaries, without changing either artist. |
| Pretty In Pink — Psychedelic Furs | First chart 1986-04-12; `The Psychedelic Furs`, with 1981 original-version evidence. Leading article variation is superficial. This identifies the asset, not the particular 1986 soundtrack recording; that version remains unresolved. |
| Make Me Feel — Janelle Monae | First chart 2018-03-10; `Janelle Monáe`, including 2018-02-22 release evidence. Latin accent folding recovers the credit; clean/explicit variants remain distinct evidence. |
| Master Of Puppets — Metallica | First chart 2022-07-16; returned recording evidence includes 1986-09-26. A much older release is entirely compatible with a later chart appearance. The search is truncated, so catalogue completeness is not claimed. |
| Call Me — Blondie; Call Me — Le Click | Separate Billboard assets remain separate: different complete credits and artist IDs, with 1980 and 1997 release evidence respectively. A shared title never merges them. |
| As Long As You Love Me — Justin Bieber Featuring Big Sean | Full-credit candidates had search relevance below Phase 2A's threshold but agree directly on title, both performers, and 2012 release evidence. Query relevance is not identity probability; a Bieber-only credit cannot replace the full credit. |

## Borderline or suspicious evidence

- **All Through The Night — Tone-Loc:** first chart 1991-12-14, cached exact-credit
  `Tone‐Lōc` recordings first dated 1992. Accent/dash normalization and the explicitly
  retained following-year tolerance allow it. This is a newly accepted weak temporal
  case, not proof of a 1991 original release.
- **At The Zoo — Simon & Garfunkel:** first chart 1967-03-18, earliest returned
  compatible dates 1968. Also newly accepted under the following-year tolerance.
  These two new links should receive independent review before scaling. A third
  following-year-only case, **Who Found Who — Jellybean Featuring Elisa Fiorillo**,
  was already accepted in Phase 2A. Tightening this tolerance would remove three
  accepted assets, not repair or invalidate every later reissue.
- **Six truncated-search recoveries:** Lambada — Kaoma; Don't Leave Me This Way —
  The Communards; More And More — Captain Hollywood Project; You — Lloyd Featuring
  Lil Wayne; Master Of Puppets — Metallica; I'm Gonna Get You — Bizarre Inc.
  Observed compatible title/full-credit/artist-ID groups have release support, but
  unreturned candidates could still reveal a competing identity. The asset rule
  does not claim to have reviewed the entire catalogue.
- **Call Me — Blondie:** supporting recording
  `b44c41ff-50f1-41eb-abdf-6b4da42b47d0` has an implausible **3,000 ms** duration.
  **Thinkin' Problem — David Ball:** recording
  `d3935516-522c-4ea6-bfd4-3061343e3795` has **2,191,402 ms** (about 36.5 minutes).
  These look like bad metadata, a fragment, or an incorrect recording-level link.
  Other recordings support each asset; the suspicious values are preserved and
  explicitly flagged, never selected as the song's duration. Asset acceptance
  must not be interpreted as certification of every supporting recording field.
- **Lost In This Moment — Big & Rich:** a returned first-release date of 2005-03
  coexists with 2007 album/release evidence. The cache alone does not resolve this
  discrepancy. Earliest returned dates must not automatically become original
  release dates; the 2007 evidence independently supports the 2007 chart asset.
- **Clean/explicit variants:** 15 accepted assets have an explicit content-version
  flag. For example, Wasted Times, Can't Take A Joke, and Make Me Feel retain those
  distinctions. They are reasonable asset links but not interchangeable inputs
  for future lyrical content measurements.
- **Meet Me At Our Spot — THE ANXIETY: WILLOW & Tyler Cole:** the candidate uses
  `THE ANXIETY, WILLOW & Tyler Cole`. Separator normalization preserves the whole
  credit. Group/person credit modelling remains worth checking when later sources
  represent the collaboration as only the group or only the individuals.

The initial version filter caught explicit live/remix labels but still admitted
descriptions such as `club mix`, `Simplified version`, `2 Meter Sessie`, and
`DJ Blazita mix`. Review exposed that unsafe pattern. The final general rule
requires an explicit allowed edition descriptor or an empty description; unknown
descriptions cannot contribute supporting metadata. Regression tests cover this.
This correction removed questionable supporting recordings without removing the
well-supported asset identities. No case-specific acceptance overrides exist.

## Ambiguity that should remain

- **Magic — Pilot** and **Tweaker — Gelo** each expose competing artist-ID sets.
  They might reflect catalogue duplication rather than different performers, but
  the cache cannot prove that. Both remain ambiguous rather than silently merging
  artist entities. These are the two unrecovered cases among the original 104
  multiple-recording ambiguities.
- **Ten compatible credits lack a temporal anchor.** A Brand New Me — Dusty
  Springfield, Malayisha — Miriam Makeba, and Jenny Lou — Sonny James are examples.
  Their later compilations are not evidence of impossibility. They remain unresolved
  because there is no sufficiently compatible earlier anchor in the observed
  candidates. For Jenny Lou, a 1959 candidate adds `(The Southern Gentleman)` to
  the credit; the matcher does not silently strip an arbitrary nickname.
- **We Can Make It Together — Steve & Eydie Featuring The Osmonds:** a dated 1972
  candidate adds The Mike Curb Congregation, while the matching full credit is dated
  2024. An extra credited contributor cannot be silently discarded to obtain an
  earlier anchor.
- Other unresolved cases include missing/full-credit differences and title spelling
  differences. **I Lost My Baby — Joey Dee** is not silently changed to Joey Dee &
  the Starliters. The original 14 zero-candidate searches, such as **Suddenly —
  Nickey DeMatteo**, remain zero-candidate results, not proof of catalogue absence.

## Assessment

No clear wrong-title/wrong-performer asset acceptance was established in this
cached review. That is not a claim of 100% precision: it lacks independent labels,
searches are bounded, and some supporting recording metadata is visibly suspect.
Removing the unique-recording requirement explains most of the gain: **102 of
124 new acceptances** came from the original multiple-recording cases.

MusicBrainz is now a strong candidate for asset identity and release context. Its
cached recording tags cover 133/200 assets, but structured recording genres remain
22/200 because detailed lookups exist for only the original 45 accepted assets.
Wikidata's 84 genre-bearing assets use mixed song/single/composition scopes, so
these figures are not equivalent genre measurements. Keep both sources with clear
provenance; do not infer that either has solved the genre problem.

Before scaling, independently review the flagged cases and a blinded set of new
links, test bounded detailed lookups for recovered assets, and establish policies
for conflicting dates, duration outliers, and content versions. The current work
does not choose a canonical recording, final genre taxonomy, or lyrics version.
