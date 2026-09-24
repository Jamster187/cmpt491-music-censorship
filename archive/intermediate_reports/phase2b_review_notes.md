# Phase 2B: inspected matches and limitations

These examples come from the cached Wikidata pilot. They illustrate the rules and
data-model problems; they are not an independently labeled precision estimate.
No match was manually promoted.

## Useful asset associations

- **“Call Me” / Blondie** links to [a single](https://www.wikidata.org/wiki/Q124382593)
  and [a composition](https://www.wikidata.org/wiki/Q857507), both with Blondie's
  performer ID. **“Call Me” / Le Click** links separately to
  [Q5021532](https://www.wikidata.org/wiki/Q5021532). The identical titles do not
  merge their Billboard assets. Phase 2A left both ambiguous between recordings.
- **“Break My Stride” / Matthew Wilder** links to
  [a vocal track](https://www.wikidata.org/wiki/Q104162656) and
  [a single](https://www.wikidata.org/wiki/Q104162873). The track has the raw genre
  `new wave`. The broader [composition item](https://www.wikidata.org/wiki/Q903586)
  lists Matthew Wilder, Unique II and Blue Lagoon and is excluded from the accepted
  associations. Its additional performers cannot be discarded just to obtain tags.
- **“What Do You Say” / Reba** links to [Q7991060](https://www.wikidata.org/wiki/Q7991060).
  The source performer is Reba McEntire, whose returned artist entity explicitly
  includes `Reba` as an alias. The match retains this alias evidence; it does not
  rely on an undocumented substring or fuzzy match. The single's raw genre is
  `country pop`, preserved without collapsing it to a major genre.
- **“DJ Play a Love Song” / Jamie Foxx Featuring Twista** links to
  [Q5205404](https://www.wikidata.org/wiki/Q5205404), with both performer IDs required
  by the credit check. Neither the guest nor his identity is dropped.
- **“Wild Horses” / Susan Boyle** links to
  [Q107390439](https://www.wikidata.org/wiki/Q107390439) and
  [Q6167395](https://www.wikidata.org/wiki/Q6167395), both with Susan Boyle's performer
  ID. Those accepted items have no returned genre statements. Successful identity
  linkage does not guarantee useful genre coverage.
- **“Master of Puppets” / Metallica:** the asset first charted on 2022-07-16,
  but the accepted single and composition have 1986 publication years. Its
  [track](https://www.wikidata.org/wiki/Q124360203) has `thrash metal`, while the
  [composition](https://www.wikidata.org/wiki/Q383630) has `popular music`. Both raw
  values remain attached to their own subjects. This asset belongs to the pilot's
  2020–2026 **first-chart** bucket; that does not make it a newly recorded song.
- **“She Did It Again” / Tyla Featuring Zara Larsson:** the 2026-charting asset
  links to [Q139386733](https://www.wikidata.org/wiki/Q139386733), a composition
  item with both performers, a 2026 publication year and `new jack swing`. This
  demonstrates an available contemporary entry, not complete 2026 coverage.

## Ambiguous and missing cases

- **“A Brand New Me” / Dusty Springfield:** the title/artist candidate
  [Q4655609](https://www.wikidata.org/wiki/Q4655609) is an album. It contributes to
  candidate-found coverage but cannot be accepted as song metadata. This is why
  candidate-found and high-confidence song coverage are reported separately.
- **“Part of the Plan” / Dan Fogelberg:** the joint search retrieves
  [Q131629751](https://www.wikidata.org/wiki/Q131629751), but the cached item lacks
  the performer/type statements needed by this rule. Search relevance or a prose
  description is insufficient for automatic acceptance.
- **“All Through the Night” / Tone-Loc:**
  [Q4729815](https://www.wikidata.org/wiki/Q4729815) credits both Tone Lōc and
  El DeBarge. **“Love Makes Things Happen” / Pebbles:**
  [Q6691023](https://www.wikidata.org/wiki/Q6691023) credits Pebbles and Babyface.
  These likely merit human review of Billboard's shortened credits. The experiment
  retains them as ambiguous rather than ignoring additional performers.
- **“Vincent (Starry, Starry Night)/Castles in the Air” / Don McLean:** no acceptable
  combined title/artist candidate is retrieved. A combined Billboard chart credit
  may not correspond to one provider song item. No automatic title splitting or
  replacement of the original asset is performed.
- **“Suddenly” / Nickey DeMatteo:** the bounded title search returns many unrelated
  songs and other works. Its continuation flag prevents interpreting this search
  as a conclusive not-found result; it remains ambiguous.

## Implications

Some Wikidata genres describe compositions or single releases. Even when a single
has the right performer and title, its genres are not automatically proven for
each recording or B-side. All genre statements retain their subject's ID/type and
raw qualifiers/references; the report separates scope-specific coverage.

Current tags/genre statements are retrospective annotations, not a time series of
what listeners or catalogers believed in each chart year. Future enrichment needs
a documented policy for aliases, shortened credits, multi-title chart assets,
provider disagreements, and versions that materially change the eventual lyrics.
An independent review set and a new holdout are needed before claiming precision
or selecting the full study population. This pilot does not make those decisions.
