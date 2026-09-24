"""Render the refined pilot report without altering experiment decisions."""
from collections import Counter
import csv,json,re
from genre_evidence import ROOT
from genre_rules import TAXONOMY

def render():
    base=ROOT/'archive/intermediate_reports/genre_refinement';s=json.loads((base/'summary.json').read_text())
    review=list(csv.DictReader((base/'review.csv').open()));q=Counter(r['judgment'] for r in review)
    tests=(ROOT/'data/experiments/genre_refinement/tests.log').read_text()
    n=re.search(r'Ran (\d+) tests',tests)
    if not n or not tests.rstrip().endswith('OK'):raise ValueError('Tests must pass')
    reasons=s['ambiguity_primary_reasons'];counts=s['counts'];est=s['estimates']
    lines=['# Broad genre assignment refinement','',
    '**Recommendation C: the existing evidence is insufficient for reliable population-wide genre analysis; add song-level corroborating evidence in a separately approved step.** Broad aggregation improves this pilot, but does not solve sparse recent/global evidence or every incorrect tag. No new production source was added, and no full assignment was performed.',
    '', '## Scope and comparison','',
    'The original 300 song IDs, 16-category taxonomy, raw evidence, accepted identity links and alias dictionary are unchanged. The final population remains 28,041 songs, 818 month-end snapshots and 81,797 observations. V1 artifacts remain intact.',
    '', '| Disposition | V1 | Refined |','|---|---:|---:|',
    f"| Named primary | 40 | {counts.get('primary',0)} |",
    f"| Ambiguous | 150 | {counts.get('ambiguous',0)} |",
    f"| Other | 1 | {counts.get('Other',0)} |",
    f"| Insufficient song-level evidence | 109 | {counts.get('insufficient',0)} |",
    '', 'Of the old 150 ambiguous cases, **80 gain a primary**, 28 remain ambiguous and 42 are withheld for insufficient support. Ten of the original 40 named primaries survive; 30 lose their unsupported confidence. The old Other assignment is also withheld. All three previously misleading primaries (Murder On My Mind, Hooked On You, Essence) and the misleading Redbone candidate set now lack strong direct support and receive no primary.',
    '', '## Audit of all 150 ambiguous cases','',
    '| Primary evidence diagnosis | Songs |','|---|---:|',
    f"| Fake ambiguity caused only by synonyms within one broad category | {reasons.get('same_category_only',0)} |",
    f"| Multiple strongly supported non-parent categories | {reasons.get('cross_genre_strong_evidence',0)} |",
    f"| Weak/isolated evidence, unequal support or generic-parent noise | {reasons.get('weak_or_conflicting_evidence',0)} |",
    '', 'V1 already used broad-category sets. Compatible subgenre tags occur in 127 cases, but every old ambiguous case also had another mapped category: different spellings alone never caused ambiguity. Of the 47 cases with strong multi-category evidence, 19 have a dominant primary and 28 remain tied. These are evidence diagnoses, not independent proof of musical genre. Some strong tags may still be wrong.',
    '', '| Non-exclusive flag | Songs / 150 |','|---|---:|']
    for flag in ('compatible_tags_within_category','isolated_low_support_category','pop_with_specific_genre','rock_alternative','rock_metal','rap_soul','latin_crossover','electronic_crossover','artist_context_adds_other_categories','direct_providers_differ'):
        lines.append(f"| {flag} | {s['ambiguity_flags'].get(flag,0)} |")
    lines+=['', 'Every case and its flags are in [ambiguity_audit.csv](genre_refinement/ambiguity_audit.csv). Artist-context differences are not automatically direct-song contradictions. No differing direct-provider genre sets were observed in this cohort; cross-source corroboration is too sparse to rescue most cases.',
    '', '## Candidate evidence rule','',
    'Raw evidence and source revisions remain unchanged. For each category and semantic level, count distinct canonical tag families, providers, entities, backed families (at least two votes) and the maximum support of each family. Duplicate cache records, recording editions and genres/tags copies do not add votes. Hip-hop/rap spelling synonyms count once; trap and southern hip-hop can add compatible support. Label counts are not independent voters, and provider agreement is not proof of independent sources.',
    'Strong direct support requires one of: a tag with at least three votes; two compatible tag families each with at least two votes; three compatible families with at least one two-vote family; or two direct providers agreeing. All-one-vote clusters remain weak: Redbone demonstrates why a cluster of related house tags can still be misleading. These are interpretable pilot gates, not confidence probabilities.',
    'Recording/accepted song-item evidence controls primary assignment. Release and artist counts remain separate context; compilation ambiguity prevents automatic release-to-song inheritance. One strong category produces a primary. Multiple strong categories require a twofold maximum-support advantage and no smaller backed-family count; otherwise leave the primary missing. Other uses the same gate. Category order never breaks a tie.',
    'Generic Pop cannot veto a strong specific category. The parent check considers backed labels, so a stray one-vote pop-rock tag cannot defeat the rule. Explicit supported Pop styles and compound genres remain competitors. Generic Rock is a parent for strongly supported Metal/Alternative; hard rock is not automatically Metal. This parent rule still produces questionable boundary decisions, such as Elvis’s Can’t Help Falling In Love.',
    'Full definitions, thresholds and development history: [method](../old_methodology/genre_refinement.md), [configuration](../../docs/genre/refinement_rules.json). The successive development trials yielded 75, 80 and 90 primaries. Threshold development used this pilot, so subsequent face review is not held-out validation. No historical content results informed these choices.',
    '', '## Qualitative review and human review readiness','',
    f"Reviewed **{len(review)} primaries**: **{q['plausible']} plausible, {q['questionable']} questionable, {q['clearly_wrong']} clearly misleading**. Fifty-eight were recovered from the previous ambiguous cohort. Selection takes up to nine per period, (six for the latest period), prioritizing predeclared challenge identities, uncommon genres and recovered cases, then fills to 60 using a fixed hash order. This is error discovery, not an unbiased accuracy estimate.",
    '**These are assistant qualitative metadata judgments, not completed human labels or listening-based ground truth.** Independent human adjudication remains outstanding. A [human review template](genre_refinement/human_review_template.csv) is supplied for those exact 60 cases. The [review ledger](genre_refinement/review.csv) identifies the reviewer and distinguishes external review references from production evidence. No reference or review verdict is read by the assignment engine.',
    '', '| Case | Refined result | Finding |','|---|---|---|',
    '| Respect / Aretha Franklin | R&B / Soul | Strong soul evidence survives weak tag noise. |',
    '| Jolene / Dolly Parton | Country; Pop secondary | Compatible country subgenres converge without deleting crossover evidence. |',
    '| I Can Only Imagine / MercyMe | Gospel / Christian | Several compatible Christian/gospel/worship labels now support a broad category. |',
    '| Smells Like Teen Spirit / Nirvana | Alternative / Indie | Strong grunge/alternative evidence outweighs isolated Pop. |',
    '| Stayin\' Alive / Bee Gees | Electronic / Dance; Pop retained | Consistent with the declared disco mapping. |',
    '| Doo Wop (That Thing) / Lauryn Hill | Ambiguous | Rap and R&B/Soul remain similarly supported. |',
    '| I Feel For You / Chaka Khan | Pop | Clearly misleading as the sole strong label for the R&B/funk crossover. |',
    '| Can\'t Help Falling In Love / Elvis Presley | Rock | Questionable: generic-Pop suppression is not proof that a ballad is primarily Rock. |',
    '| Livin\' La Vida Loca / Ricky Martin | Pop; Latin secondary | Defensible crossover but no objectively established exclusive winner. |',
    '', 'The Chaka Khan review uses the Recording Academy’s [R&B performance award record](https://www.grammy.com/video/27th-annual-grammy-awards-best-rb-vocal-performance-female/); award categories are supporting context rather than universal ground truth. The [Ricky Martin discussion](https://www.grammy.com/news/ricky-martins-vida-loca/) supports retaining the Latin crossover. These factual lookups were review-only, not a new genre source in the pipeline.',
    '', '## Multi-genre design and taxonomy','',
    'Retain both `primary_genre` and `mapped_genres`, with `secondary_genres` derived by removing the primary. Here mapped genres means all **strong direct** categories; weak/context labels remain in separate support records. It differs deliberately from v1’s union of all mapped evidence. A primary does not erase secondary styles or uncertainty. Even strong secondary labels can be wrong: isolated recording-tag problems remain, so these are candidate features rather than certified genres. Future multi-label summaries must explain overlapping denominators; do not double-count them as disjoint groups.',
    'Older Soul/R&B terms and disco aggregate sensibly in reviewed examples. Older Pop/Rock boundaries remain subjective. Alternative and Metal require direct genre evidence, not an artist stereotype; hard rock can remain Rock. Latin and K-Pop cannot follow merely from language or nationality. Singular Afrobeat remains distinct from modern Afrobeats in the unchanged mapping. No taxonomy categories were changed.',
    '', '| Category | Pilot primary | Strong support, including secondary |','|---|---:|---:|']
    for g in TAXONOMY:
        r=s['categories'][g];lines.append(f"| {g} | {r['primary']} | {r['strong_support']} |")
    lines+=['','## Estimated full-population availability','',
    'These are rough projections, not full assignments or accuracy estimates. Weight non-challenge sample rows by their population/sample period × peak-rank × credit-format stratum sizes; challenge cases initially have weight one. Calibrate within each period to the exact mapped-evidence census (18,759 total). The 9,282 songs with no mapped evidence must remain insufficient under this cache-only method. Balanced challenge sampling makes simple 90/300 extrapolation inappropriate.',
    '', '| Outcome | Estimated percent | Approximate songs |','|---|---:|---:|']
    for k in ('primary','ambiguous','Other','insufficient'):lines.append(f"| {k} | {est['expected_population_pct'][k]:.2f}% | {est['expected_population_counts'][k]:,} |")
    lines+=['','| First-chart period | Pilot primary / sampled | Estimated primary | Ambiguous | Insufficient |','|---|---:|---:|---:|---:|']
    for p,r in est['periods'].items():
        e=r['expected_pct'];d=r['pilot_counts'];lines.append(f"| {p} | {d.get('primary',0)}/{sum(d.values())} | {e['primary']:.1f}% | {e['ambiguous']:.1f}% | {e['insufficient']:.1f}% |")
    lines+=['', 'The period samples are small and the estimates have substantial sampling and source-quality uncertainty; the decimals are computational output, not forecast precision. Zero Other (or zero ambiguous modern cases) is an observed pilot result, not proof of population absence. All three modern-period primaries in the review were questionable. Sparse modern votes can reflect recent/community annotation activity rather than weak musical genre membership. Vote thresholds can favor older, well-known and frequently annotated songs: vote strength is community attention, not a validated measure of genre correctness.',
    'Major Pop/Rock/R&B/Country/Rap groups have more candidate assignments than before, but reliable genre-specific moving averages are **not demonstrated**. The extreme period imbalance would select older well-tagged catalogue songs disproportionately. Metal, Latin, Folk, K-Pop and Afrobeats have too few or no pilot primaries; this cannot be interpreted as their absence from the population. Exact per-window genre/classifier counts require a later validated production assignment. No moving averages or historical content tests were computed.',
    '', '## Recommendation and validation','',
    '**C — EXISTING EVIDENCE IS INSUFFICIENT; ADD A SECOND GENRE SOURCE.** Keep this broad-support prototype and multi-genre representation, but obtain independent song-specific corroboration in a future bounded pilot before scaling. Further lowering thresholds would re-admit demonstrated single-tag and coherent-but-wrong tag clusters. A Pop-only adjustment would not fill the 9,282 evidence-free songs or solve the modern/global gap. No additional source was acquired in this task.',
    f"**{n[1]} tests passed**, including 17 new support-rule regression tests. The original protected-data validation passed. Replays reproduce the refined pilot, audit and summary byte-for-byte. All original v1 tracked artifacts and all public datasets, source/research/classifier databases and 21,693 lyrics remain unchanged. No new full-population genre table was generated.",
    '', 'Rebuild: `python3 src/genre_refinement.py`, then `python3 src/genre_refinement_report.py`. See the method for tests and integrity checks. Stopped before production assignment, public export changes or historical/COVID analysis.']
    (ROOT/'archive/intermediate_reports/genre_assignment_refinement.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':render()
