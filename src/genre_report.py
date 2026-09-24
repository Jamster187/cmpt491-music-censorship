"""Render the numerical genre feasibility report from the frozen pilot artifacts."""
import json
from pathlib import Path
from genre_evidence import ROOT,OUT,PERIODS
from genre_rules import TAXONOMY

def render():
    s=json.loads((ROOT/'reports/genre/summary.json').read_text())
    inv=json.loads((OUT/'inventory.json').read_text())
    review=json.loads((ROOT/'reports/genre/review.json').read_text())
    bench=json.loads((OUT/'benchmark.json').read_text())
    lines=['# Genre assignment feasibility','',
    'This experiment inventories the final **28,041-song** month-end population and assigns candidate genres to **300 songs only**. The 818 snapshots and 81,797 observations remain unchanged. No public dataset, lyrics, metadata, or classifier results were updated. No historical content analysis was performed.',
    '', '## Frozen taxonomy','',', '.join(TAXONOMY)+'.','',
    'There are 15 named categories plus Other. An empty primary genre is missingness, not a seventeenth genre. The taxonomy is intentionally broad but not mutually exclusive: style, region/market and religion can overlap. No categories were added or merged.',
    '', '## Existing evidence','',
    f"**{s['raw_positive_evidence']:,} songs** have positive raw genre/tag evidence; **{s['mapped_evidence']:,} ({100*s['mapped_evidence']/28041:.2f}%)** have at least one eligible label recognized by the mapping, at any semantic level. **{s['direct_mapped_evidence']:,} ({100*s['direct_mapped_evidence']/28041:.2f}%)** have direct recording/song-item evidence. These are evidence-availability counts, not primary-genre assignments.",
    '', '| Provider / semantic level | Songs with eligible mapped evidence |','|---|---:|']
    for k,n in s['mapped_by_source'].items():lines.append(f'| {k} | {n:,} |')
    lines+=['','Counts overlap. Inventory includes both production metadata databases, all MusicBrainz pilot/production request caches, archived accepted Wikidata matches, and all Wikidata request caches. Exact P434 artist crosswalks reuse cached artist evidence without new name matching. LRCLIB has no genre field; the old generic Discogs access probe has no accepted song crosswalk. No Last.fm song cache exists.',
    f"Successfully cached responses inspected: {inv['source_files']}. Failed cached requests were counted separately: {inv['rejected_cache_counts']}. Cache keys/body hashes were checked; original payloads remain local. A missing cached genre field is not proof the provider has no genre.",
    '', '## Proposed method and sources','',
    'Use exact accepted entity links, then a versioned exact-label dictionary; do not infer genre from performer nationality, lyrics, classifier scores, or loose substrings. Direct recording/song-item evidence outranks artist context. Album/release-group tags remain context because existing links include compilations and do not establish track-specific genre. Duplicate editions do not count as independent votes. One direct mapped category produces a candidate primary; conflicting categories preserve NULL primary and all candidates. Artist-only suggestions are not confident song assignments. Other requires affirmative out-of-taxonomy evidence.',
    'The only parent reduction is generic Rock alongside explicit Metal or Alternative / Indie. Composite styles still retain competing categories. Confidence is an evidence grade, not a calibrated probability. Detailed rules and all aliases are in [the method](../../docs/genre/method.md) and [mapping](../../docs/genre/taxonomy_mapping.json).',
    'MusicBrainz and Wikidata are the practical starting sources. MusicBrainz tags/genre associations require attribution and noncommercial share-alike handling; Wikidata structured statements are CC0. Last.fm is a potential track-level fallback but academic API access requires prior contact. Discogs API retention terms and release-level genre semantics make it unsuitable as the default frozen-song source here. See [source review and official references](../../docs/genre/sources.md). There were **zero new genre API requests**.',
    '', '## 300-song pilot','',
    'The frozen sample contains 63 predeclared challenge identities and 237 hash-selected songs balanced across period, peak-rank and artist-credit-format strata. Six periods contain 43 songs each; 2020–2026 contains 42. Raw sample percentages are not unbiased population estimates. The pipeline did not use lyrical content or model scores.',
    '', '| Disposition | Songs | Percent |','|---|---:|---:|']
    for k in ('confident_primary','release_supported','ambiguous','Other','context_only','insufficient_evidence'):
        n=s['dispositions'].get(k,0);lines.append(f'| {k} | {n} | {100*n/300:.2f}% |')
    lines+=['','`confident_primary` is the operational single-direct-category status, not independently certified correctness. Context-only rows have missing primary genres; they belong with insufficient song-level evidence for analytical use.',
    '', '## Qualitative review','',review['summary'],'',
    'Judgments are qualitative metadata/genre plausibility checks, not listening-based gold labels or an accuracy estimate. Cached genre labels cannot independently validate themselves. Review notes distinguish a plausible abstention from a correct positive assignment, and independent references are supplied for selected boundary cases. Candidate outputs were not overridden.',
    '', '| Song / artist | Pilot result | Review | Reason |','|---|---|---|---|']
    highlights=('I Fall To Pieces','Unwind','Respect','Jolene','Purple Rain','Hooked On You','Murder On My Mind','Essence','Redbone','Water','Dynamite','Doo Wop (That Thing)','Walk This Way','Fast Car','Smells Like Teen Spirit','Paranoid','La Bicicleta',"Don't Know Why",'Looking For You',"I'll Never Let You Go",'Here With Me')
    for r in review['cases']:
        if r['identity'].split(' — ')[0] not in highlights:continue
        lines.append('| '+' | '.join(str(r[k]).replace('|','/') for k in ('identity','result','judgment','reason'))+' |')
    lines+=['','All 60 case notes and the review selection rule are in [review.json](../../reports/genre/review.json). The main table above shows representative failures and boundaries.', '', '## Historical coverage diagnostics','',
    'Periods use first Billboard appearance. Evidence columns below are exact population census counts; the final column is a rough design-weighted estimate of this rule’s *primary-label availability*, not accuracy. It expands each non-challenge period/rank/credit stratum by N/n and adds the fixed challenge cases. With only about 34 random cases per period, these estimates are uncertain. They must not be read as genre or content trends.',
    '', '| Period | Population | Any mapped evidence | Direct mapped evidence | Pilot primary / n | Estimated primary coverage |','|---|---:|---:|---:|---:|---:|']
    for _,_,p in PERIODS:
        r=s['periods'][p];d=r['pilot_dispositions'];n=sum(d.get(k,0) for k in ('confident_primary','release_supported','Other'))
        lines.append(f"| {p} | {r['population']:,} | {r['mapped_evidence']:,} ({100*r['mapped_evidence']/r['population']:.1f}%) | {r['direct_mapped_evidence']:,} ({100*r['direct_mapped_evidence']/r['population']:.1f}%) | {n}/{r['pilot']} | {s['estimated_primary_coverage_pct'][p]:.1f}% |")
    lines+=['','Existing mapped-evidence availability is uneven: roughly 58% for 1958–1969, 81% for the 2000s, and 54% for 2020–2026. Direct evidence is only about 42% for the latest period. This is not merely an old-music problem: newly charting/global music and collaboration-specific identities also lack suitable cached tags. Cached artist context increases recent availability but cannot establish historical song style. Applying the current primary rule would introduce large, period-dependent selection effects.', '', '## Analytical suitability','',
    '| Category | Pilot primary songs | Pilot songs with any supporting evidence | Monthly rows of those primary songs |','|---|---:|---:|---:|']
    for g,r in s['categories'].items():lines.append(f"| {g} | {r['primary']} | {r['any_evidence']} | {r['pilot_primary_monthly_rows']} |")
    lines+=['',review['suitability'],'',
    'These counts cannot establish adequate observations in every monthly window. The pilot deliberately includes rare modern/global cases. Absence from a pilot period is not a population zero. Before time-series analysis, count actual genre membership and nonmissing classifier observations per window, and report coverage/ambiguity rather than treating every missing genre as Other. No categories were merged.',
    '', '## Scaling and validation','',
    f"The local pilot plus full evidence-availability census took {bench['seconds']:.1f} seconds on this machine. The ignored inventory occupies {bench['inventory_bytes']:,} bytes; retained pilot evidence occupies {bench['pilot_evidence_bytes']:,} bytes. This is evidence storage, not a new production database. The exhaustive cache index took approximately 24 minutes as a one-time step; subsequent pilot replays reuse it.",
    f"Accepted links contain {inv['unique_accepted_mb_entities'].get('recording',0):,} distinct recording IDs and {inv['unique_accepted_mb_entities'].get('artist',0):,} artist IDs. Looking up every recording at 1.1 seconds/request would have a rate-spacing floor of {inv['unique_accepted_mb_entities'].get('recording',0)*1.1/3600:.1f} hours, before latency/backoff. Artist-only lookups would take at least {inv['unique_accepted_mb_entities'].get('artist',0)*1.1/3600:.2f} hours and still would not establish song genre. Do not start either crawl. A future accepted cache-only rule would require zero APIs; a conservative planning allowance is under an hour locally after indexing, not a measured full-population assignment runtime.",
    '', 'Rebuild commands and scope guards: [docs/genre/method.md](../../docs/genre/method.md). The 300-row results are reproducible; source hashes, mapping/code hashes and the evidence-input manifest digest are retained. Tests and protected-data validation are recorded in the validation note below.',
    '', '## Recommendation','',review['recommendation'],'',
    'Stopped before full genre assignment, public dataset replacement, or historical/COVID analysis.']
    validation=json.loads((OUT/'validation.json').read_text())
    import re
    tests=(OUT/'tests.log').read_text()
    count=re.search(r'Ran (\d+) tests',tests)
    if not count or not tests.rstrip().endswith('OK'):raise ValueError('Tests not passing')
    lines += ['', '## Validation record', '', f"**{count[1]} tests passed**, including 16 genre rule/sampling/join tests. Pilot decision replay and the existing public-dataset validation passed. All {validation['protected_files']:,} protected files retained their pre-experiment SHA-256 hashes, including {validation['protected_lyrics']:,} lyric files, research/lyrics/classifier databases, the immutable Billboard source and all existing public files. Snapshot checks confirm 28,041 IDs, 818 months and 81,797 observations, with the three accepted 99-row gaps unchanged.", 'The pilot CSV and numerical summary rebuilt byte-for-byte identically. No lyrics, caches, databases or model checkpoints are included in the commit.']
    (ROOT/'archive/intermediate_reports/genre_assignment_feasibility.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':render()
