"""Offline diagnostic census. Never writes acquisition state or lyric text."""
import csv
from collections import Counter, defaultdict
import difflib
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from lyrics_lrclib import normalize, digest
from lyrics_lrclib_r import clean, raw_text
from lyrics_production_match import RISK, REVIEW_TEXT, artist_credit, title_artist

ROOT = Path(__file__).resolve().parents[1]
SEED = 'lrclib-exclusion-audit-v1'
PRIVATE = ROOT/'data/processed/lyrics_exclusion_audit.json'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def read_results(root=ROOT):
    c = sqlite3.connect((root/'data/processed/lyrics.db').as_uri()+'?mode=ro', uri=True)
    try:
        return {sid: json.loads(p) for sid, p in c.execute('SELECT song_id,payload FROM production_results')}
    finally:
        c.close()


def cached_candidates(r, root=ROOT):
    """Bind each candidate to the exact persisted retrieval and candidate revision."""
    candidates = {}
    for ref in r['retrievals']:
        path = root/'data/cache/lrclib'/(digest(ref['url'].encode())+'.json')
        rec = json.loads(path.read_text())
        if rec['url'] != ref['url'] or digest(rec['body'].encode()) != rec['sha256'] or rec['sha256'] != ref['sha256']:
            raise ValueError('Cache provenance mismatch: '+r['song_id'])
        if rec['status'] != 200:
            continue
        for candidate in json.loads(rec['body']):
            key = candidate['id']
            if key in candidates and candidates[key] != candidate:
                raise ValueError('Conflicting candidate revisions')
            candidates[key] = candidate
    for e in r['candidates']:
        c = candidates[e['id']]
        if digest(json.dumps(c, ensure_ascii=False, sort_keys=True).encode()) != e['candidate_sha256']:
            raise ValueError('Candidate checksum mismatch')
    return candidates


def eligible(e):
    return e['title_compatible'] and e['artist_compatible']


def safe_text(e):
    return e['text_quality'] not in ('text_bad','text_missing') and not set(e['text_warnings']) & REVIEW_TEXT and not set(e['version_warnings']) & RISK


def line_signature(text):
    return tuple(x for x in (normalize(line) for line in text.splitlines()) if x)


def unique_order(seq):
    return tuple(dict.fromkeys(seq))


def text_profile(texts):
    """Describe ALL safe text groups, never just the matcher's first failing pair.

    These are sampling strata, not acceptance rules. Even line-set agreement can
    hide an abridged refrain, and high lexical overlap can hide changed meaning.
    """
    texts = list(dict.fromkeys(texts))
    lines = [line_signature(t) for t in texts]
    tokens = [normalize(t).split() for t in texts]
    longest = max(tokens, key=len)
    ratios = [difflib.SequenceMatcher(None, longest, t, autojunk=False).ratio() for t in tokens]
    wordsets = [set(t) for t in tokens]
    overlap = min(len(s & set(longest))/max(1,len(s | set(longest))) for s in wordsets)
    if len({unique_order(x) for x in lines}) == 1:
        category = 'text_repeat_count_only'
    elif len({frozenset(x) for x in lines}) == 1:
        category = 'text_same_lines_reordered'
    elif min(ratios) >= .85 and overlap >= .90:
        category = 'text_near_agreement'
    else:
        category = 'text_substantive_conflict'
    return dict(primary=category, text_groups=len(texts), min_sequence_ratio=round(min(ratios),5),
                min_wordset_overlap=round(overlap,5), min_words=min(map(len,tokens)),max_words=max(map(len,tokens)))


def identity_flags(r, raw):
    flags = set()
    target = artist_credit(r['artist'])
    for e in r['candidates']:
        c = raw[e['id']]
        title, artist, _ = title_artist(c)
        source = artist_credit(artist)
        if e['title_compatible']:
            if set(source) < set(target): flags.add('missing_credit_components')
            elif set(target) < set(source): flags.add('extra_credit_components')
            elif source != target: flags.add('variant_or_other_performer_credit')
            # This feature preserves every normalized name token and order; not an alias inference.
            a = re.sub(r'\b(?:and|with|featuring|feat|ft)\b', '', normalize(r['artist'])).split()
            b = re.sub(r'\b(?:and|with|featuring|feat|ft)\b', '', normalize(artist)).split()
            if a == b and source != target: flags.add('credit_separator_only_candidate')
        if e['artist_compatible'] and not e['title_compatible']:
            flags.add('title_variant_same_credit')
        if set(e['version_warnings']) & RISK: flags.add('version_risk_in_candidates')
    if not flags: flags.add('no_compatible_identity_evidence')
    return flags


def describe(r, raw):
    es = [e for e in r['candidates'] if eligible(e)]
    safe = [e for e in es if safe_text(e)]
    flags = identity_flags(r,raw) if not es else set()
    flags |= {'text_'+w for e in es for w in set(e['text_warnings']) & REVIEW_TEXT}
    flags |= {'version_'+w for e in es for w in set(e['version_warnings']) & RISK}
    out = dict(song_id=r['song_id'], title=r['title'], artist=r['artist'], year=int(r['first_chart_date'][:4]),
               status=r['status'], reason=r['reason'], identity=r['identity_confidence'],
               eligible_candidates=len(es), safe_text_candidates=len(safe), candidate_count=len(raw),
               flags=sorted(flags), prior_review=r.get('decision_basis')=='reviewed_pilot',
               retrieval_sha256=[ref['sha256'] for ref in r['retrievals']])
    reason=r['reason']
    if out['prior_review']:
        out['primary']='prior_review_'+r['status']
    elif reason=='Materially different plausible lyric texts':
        texts=[clean(raw_text(raw[e['id']]),r['title'],r['artist'])[0] for e in safe]
        out.update(text_profile(texts))
    elif reason=='No full compatible title and artist credit':
        if 'credit_separator_only_candidate' in flags: p='identity_separator_variant'
        elif 'missing_credit_components' in flags: p='identity_incomplete_credit'
        elif 'title_variant_same_credit' in flags: p='identity_title_variant'
        else: p='identity_other_credit_or_song'
        out['primary']=p
    elif reason=='All safe candidates conflict with available durations': out['primary']='duration_conflict'
    elif reason=='Identity established; text or version requires review':
        # Multi-reason rows stay explicit; a primary singles out only unanimous blockers.
        blockers=[set(e['text_warnings']) & REVIEW_TEXT | {'version_'+v for v in set(e['version_warnings']) & RISK} for e in es if e['text_quality'] not in ('text_bad','text_missing')]
        common=set.intersection(*blockers) if blockers else set()
        order=['material_censorship','mixed_script_words','short_text_requires_review','embedded_credits','unstructured_text','possible_non_lyric_material']
        p=next((x for x in order if x in common),None)
        out['primary']='quality_'+p if p else ('quality_version_only' if all(b and all(x.startswith('version_') for x in b) for b in blockers) else 'quality_multiple_blockers')
    else: out['primary']=r['status']
    return out


def sample(rows, n=20):
    strata=defaultdict(list)
    for r in rows: strata[(r['status'],r['primary'])].append(r)
    selected=[]
    for key, group in sorted(strata.items()):
        k=n
        if key[1]=='text_substantive_conflict': k=40
        if key[1].startswith('prior_review_'): k=0 # separately preserved reviewed ledger
        for row in sorted(group,key=lambda r:digest((SEED+r['song_id']).encode()))[:k]:
            selected.append(dict(row,stratum_size=len(group)))
    return selected


def main():
    before={p:sha(ROOT/p) for p in ('data/processed/lyrics.db','data/processed/research.db','data/processed/music.db')}
    rs=read_results();rows=[]
    for r in rs.values():
        if r['status']=='accepted':continue
        rows.append(describe(r,cached_candidates(r)))
    rows.sort(key=lambda r:r['song_id'])
    if before!={p:sha(ROOT/p) for p in before}: raise ValueError('Database changed during audit')
    result=dict(version=SEED, database_sha256=before, rows=rows,sample=sample(rows))
    PRIVATE.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    if (ROOT/'reports/lyrics_exclusion_review.json').exists():
        publish(result, rs)
    if before != {p:sha(ROOT/p) for p in before}:
        raise ValueError('Database changed during publication/probe')
    print(json.dumps({'counts':dict(Counter(r['status'] for r in rows)),
                      'strata':dict(Counter(r['status']+'/'+r['primary'] for r in rows)),
                      'sample':dict(Counter(r['status']+'/'+r['primary'] for r in result['sample']))},indent=2))



def syntax_credit(value):
    """Hypothesis only: explicit separators/Unicode punctuation; no name aliases."""
    import unicodedata
    value=unicodedata.normalize('NFKC',value)
    value=re.sub(r',\s*(Jr\.?)(?=\s*$)',r' \1',value,flags=re.I)
    value=re.sub(r'\bwith\b',' & ',value,flags=re.I)
    return value.replace('/', ' & ')


def syntax_probe(r, raw):
    """In-memory counterfactual; original identities and candidates remain intact."""
    from lyrics_production_match import decide
    s=dict(r,artist=syntax_credit(r['artist']))
    cs=[dict(c,artistName=syntax_credit(c['artistName'])) for c in raw.values()]
    result=decide(s,cs)
    return {k:result[k] for k in ('status','reason','selected')}


def validate_review(data, results, ledger):
    if ledger['version'] != SEED:
        raise ValueError('Review version mismatch')
    expected=[s['song_id'] for s in data['sample']]
    if [s['song_id'] for s in ledger['sample']] != expected:
        raise ValueError('Sample changed')
    sampled={r['song_id']:r for r in data['sample']}
    allowed={'safe_candidate','possible_deterministic','manual_review','remain_excluded','query_research_only','retryable_transport'}
    for s in ledger['sample']:
        if s['primary'] != sampled[s['song_id']]['primary'] or s['outcome'] not in allowed:
            raise ValueError('Invalid review stratum/outcome')
        r=results[s['song_id']]
        if digest(json.dumps(r,sort_keys=True,ensure_ascii=False).encode()) != s['result_sha256']:
            raise ValueError('Reviewed result changed')
        evidence=[dict(id=e['id'],sha256=e['candidate_sha256']) for e in r['candidates']]
        if s['candidate_ids'] != [e['id'] for e in evidence] or s['candidate_evidence_sha256'] != digest(json.dumps(evidence,sort_keys=True,ensure_ascii=False).encode()):
            raise ValueError('Review candidate provenance changed')
        if s['retrieval_sha256'] != [x['sha256'] for x in r['retrievals']]:
            raise ValueError('Review retrieval provenance changed')
        if (s['title'],s['artist'],s['status']) != (r['title'],r['artist'],r['status']):
            raise ValueError('Reviewed identity/disposition changed')
    ids=[r['song_id'] for r in ledger['low_risk_candidates']]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate low-risk candidate')
    for s in ledger['low_risk_candidates']:
        r=results[s['song_id']]
        if r['status']!='quarantined': raise ValueError('Shortlist is not quarantined')
        e=next(e for e in r['candidates'] if e['id']==s['candidate_id'])
        if (e['candidate_sha256'],e['diagnostics']['sha256']) != (s['candidate_sha256'],s['text_sha256']):
            raise ValueError('Shortlist candidate changed')


def recovery_weights(rows, reviews, safe):
    """Conditional planning scenario, NOT a prediction of validated acceptances.

    Remove the enumerated safe candidates before stratified expansion so they
    cannot be counted twice. Never project retries/query-only cases as usable.
    """
    population=Counter((r['status'],r['primary']) for r in rows if r['song_id'] not in safe)
    tested=Counter((r['status'],r['primary']) for r in reviews if r['song_id'] not in safe)
    possible=Counter((r['status'],r['primary']) for r in reviews if r['song_id'] not in safe and r['outcome']=='possible_deterministic')
    rates={key:possible[key]/tested[key] if tested[key] and key[0]=='quarantined' else 0.0 for key in population}
    weights={r['song_id']:0.0 if r['song_id'] in safe else rates[(r['status'],r['primary'])] for r in rows}
    return weights,[(key,population[key],tested[key],possible[key],population[key]*rates[key]) for key in sorted(population)]



def pilot_probe(results):
    """Counterfactual regression on the existing development pilot; no writes."""
    from lyrics_production_match import decide
    c=sqlite3.connect((ROOT/'data/processed/lyrics.db').as_uri()+'?mode=ro',uri=True)
    ids=[sid for sid, in c.execute('SELECT song_id FROM results ORDER BY song_id')];c.close()
    counts=Counter();changes=[]
    for sid in ids:
        r=results[sid];raw=cached_candidates(r)
        base=decide(r,list(raw.values()));probe=syntax_probe(r,raw)
        counts['cases']+=1
        counts['baseline_accepted']+=base['status']=='accepted'
        counts['probe_accepted']+=probe['status']=='accepted'
        counts['probe_accepts_reviewed_exclusion']+=probe['status']=='accepted' and r['status']!='accepted'
        if base['status']!=probe['status']:
            changes.append(dict(song_id=sid,title=r['title'],reviewed=r['status'],baseline=base['status'],probe=probe['status']))
    if counts['probe_accepts_reviewed_exclusion']:
        raise ValueError('Syntax probe accepts a reviewed pilot exclusion')
    return dict(counts=dict(counts),changes=changes)


def publish(data, results):
    from post_run_audit import PERIODS, pct, table
    ledger=json.loads((ROOT/'reports/lyrics_exclusion_review.json').read_text())
    validate_review(data,results,ledger)
    pilot=pilot_probe(results)
    safe={s['song_id'] for s in ledger['low_risk_candidates']}
    syntax={s['song_id']:s for s in ledger['low_risk_candidates'] if s['kind']=='explicit_credit_syntax'}
    for row in data['rows']:
        if row['primary']=='identity_separator_variant':
            r=results[row['song_id']];probe=syntax_probe(r,cached_candidates(r))
            if (probe['status']=='accepted') != (row['song_id'] in syntax):
                raise ValueError('Syntax probe changed')
            if row['song_id'] in syntax and probe['selected']!=syntax[row['song_id']]['candidate_id']:
                raise ValueError('Syntax candidate changed')
    weights,strata=recovery_weights(data['rows'],ledger['sample'],safe)
    accepted={sid for sid,r in results.items() if r['status']=='accepted'}
    q={sid for sid,r in results.items() if r['status']=='quarantined'}
    possible=sum(weights.values());total=len(results)
    statuses=Counter(r['status'] for r in results.values())
    qs=[r for r in data['rows'] if r['status']=='quarantined']
    primary=Counter(r['primary'] for r in qs);flags=Counter(f for r in qs for f in r['flags'])
    # Public per-asset census contains no candidate text/body or metadata JSON.
    with (ROOT/'data/processed/lyrics_exclusion_categories.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['song_id','title','artist','first_chart_year','status','primary','identity','eligible_candidates','safe_text_candidates','text_question','flags'])
        for r in data['rows']:
            w.writerow([r['song_id'],r['title'],r['artist'],r['year'],r['status'],r['primary'],r['identity'],r['eligible_candidates'],r['safe_text_candidates'],text_question(r),';'.join(r['flags'])])
    lines=['# LRCLIB exclusion audit','',
        '**Diagnostic only. Zero HTTP requests, zero disposition changes, zero lyric-file changes.**',
        'All 25,363 assets remain attempted; the usable corpus stays at 19,372 (76.38%).',
        'The corpus is not demonstrated to be at its safe ceiling. Recommendation: **C — build and independently validate a focused second-pass matcher**, after authorization. Do not bulk-promote this diagnostic shortlist.', '',
        '## What caused quarantine','',
        'Production identity is high-confidence for 2,637/3,519 (74.94%); 882 remain identity-ambiguous. A high-confidence identity does not certify its text. The latter group includes five preserved manual pilot exclusions.',
        'The production first-failure reasons are 2,332 text disagreements, 877 incomplete title/credit matches, 292 text/version review flags, 13 duration conflicts, and five prior reviewed exclusions. Album mismatch is never a sole rejection reason; matching album is a selection preference.',
        'Multiple LRCLIB records already pass if their texts agree. Clean/explicit labels alone already pass; actual masking is a separate question. Warning unions can describe rejected alternatives, not defects in a selected text.',
        'The table below assigns every quarantined asset exactly one primary stratum. `text_substantive_conflict` is an internal sampling label for **wider disagreement**, not a finding that all its texts are substantively wrong. Near agreement requires every safe text group to have sequence ratio ≥0.85 and word-set overlap ≥0.90 against the longest group. These thresholds are diagnostic strata, not proposed acceptance rules. Repeat-only means identical first-occurrence line sequences, not proven recording-length equivalence. All groups are examined, including those beyond the production matcher’s first failing pair.']
    table(lines,['Primary category','Assets','% quarantine'],[(k,v,pct(v,len(q))) for k,v in primary.most_common()])
    lines+=['','Secondary flags overlap; counts below use only identity-eligible candidates for text/version flags. Identity flags can describe competing unrelated candidates. A version flag does not itself establish why the asset failed.']
    table(lines,['Secondary flag','Assets','% quarantine'],[(k,v,pct(v,len(q))) for k,v in flags.most_common()])
    lines+=['','## Representative cache review','',
        'The fixed seed `'+SEED+'` orders SHA-256(seed + song_id) within status/primary strata. Review takes 20 per stratum, 40 for wider disagreement, or every asset when fewer exist. Prior reviewed pilot exclusions are preserved separately and excluded from this new sample.',
        'The 360 selected cases comprise 279 quarantined, 21 wrong-identity, 20 bad/missing-text, 20 empty-search, and 20 transport-error records. Transport errors were assessed from response evidence; other review used candidate metadata, text boundaries, flagged lines, lengths and sequence differences. This is one assistant’s diagnostic review, not audio verification, independent adjudication, or a line-by-line transcription certification. There are 17 quarantined sample cases from 2015–2019 and 50 from 2020–2026. The versioned [review ledger](lyrics_exclusion_review.json) binds decisions to exact result, candidate and retrieval hashes. The [local, ignored exclusion census](../data/processed/lyrics_exclusion_categories.csv) covers all 5,991 non-accepted assets.',
        '“Possible deterministic” means a concrete rule family warrants development/testing, not that it has passed a precision test. “Manual review” means existing evidence does not justify such a rule. Short genuine vocal tracks and instrumental recordings cannot be made complete by lowering the word-count threshold.']
    table(lines,['Sample stratum','n','Safe candidate','Possible rule','Manual','Remain excluded / query / transport'],
          [(st+'/'+p,sum(c.values()),c['safe_candidate'],c['possible_deterministic'],c['manual_review'],c['remain_excluded']+c['query_research_only']+c['retryable_transport'])
           for (st,p),c in sorted(_review_counts(ledger['sample']).items())])
    lines+=['','Concrete findings (metadata/title references only; no lyric text):','',
        '- **Explicit credit syntax:** 90 assets retain all normalized name tokens in a separator variant. An offline in-memory probe normalizes Unicode punctuation, explicit “with”/slash separators, and commas before Jr., then applies the unchanged production matcher. Exactly **44** pass all existing text/version/duration checks. All 44 proposed credit mappings were inspected. No missing-guest inference or artist alias is part of this shortlist; absent separators and other conflicts still fail.',
        '- **Five contextual false alarms:** Blac Youngsta’s *Booty* and 50 Cent’s *Disco Inferno* trigger metadata words used lyrically; Alan Jackson’s *www.memory* triggers the URL detector on its own title/refrain; *Sleazy Remix 2.0 Get Sleazier* explicitly includes Remix in the Billboard title but the matcher subtracts only parenthetical target labels; *4 AM* has “Live” in the NBA Live soundtrack album name. These are low-risk review candidates, not a general permission to ignore copyright/URL/version warnings.',
        '- **Text disagreement:** all 20 near-agreement samples and all 14 repeated-line cases merit stronger deterministic review. In the wider-disagreement sample, 24/40 are promising; other cases include materially different narratives, omissions, and performance variants. Examples worth investigation include *Breathe* (LRC metadata/contraction artifacts), *I Will Be There* (annotations), and *Lonely Nights* (an abbreviated alternate alongside an expanded existing text). Never synthesize repeats or choose the longest text blindly.',
        '- **Real protections:** *@ MEH* and *Meh* collapse under current punctuation normalization despite very different texts/albums/durations. *Get Away*, *Think Twice*, and *They Like It Slow* have near-unrelated texts under compatible metadata. *My Coloring Book* carries Kitty Kallen metadata but a Barbra Streisand text header; *Exodus* wraps a Hall and Oates text header. These cannot be recovered by simple threshold relaxation or header removal.',
        '- **Mixed scripts:** 112 assets are primarily blocked by mixed Latin/Cyrillic words; sampled defects are often localized lookalikes. A narrow, logged character-normalization policy is plausible but not yet validated. Some also have masking, truncation, or remix questions. No text was repaired during this audit.',
        '- **Credits/versions:** missing guests, alternative performers, covers, and remix guests are distinct questions. *Till The World Ends* and *Whole Lotta Choppas* must not inherit a solo text for a guest-bearing Billboard asset. Conversely, some full guest credits identify a remix even when Billboard omits that title suffix; this warrants explicit asset-level evidence, not a universal ban or universal suffix removal.',
        '- **Text quality:** the short-text sample includes likely sparse-vocal songs as well as an apology placeholder (*There Goes My Heart Again*) and opening fragments (*Wat Da Hook Gon Be*, *What Have I Done To Deserve This?*). Collapsed layout ranges from intact prose-like text to merged words and credits. Censorship masks and clean/explicit labels can disagree. The audit does not reconstruct censored words or certify the charted radio edit.',
        '', '## Other failure buckets']
    table(lines,['Status','Assets'],[(k,statuses[k]) for k in ('wrong_identity','bad_missing_text','not_found','error')])
    missing=Counter(r['text_quality'] for r in results.values() if r['status']=='bad_missing_text')
    soundtrack=sum(bool(re.search(r'\bfrom\b',r['title'],re.I)) for r in results.values() if r['status']=='not_found')
    capped=sum(r.get('search_may_be_truncated',False) for r in results.values() if r['status']=='wrong_identity')
    lines += ['',
        f'- **Wrong identity:** 1,350 automatic outcomes are based on absence of the heuristic’s plausible overlap, not necessarily affirmative contradiction; 15 are prior manual exclusions. The 21-case sample includes plausible *Dog + Butterfly* versus *Dog & Butterfly*, 4/Four Seasons credits, and *Whatcha Wanna Do?* with Mia X. These show that the label overstates certainty in some cases. {capped} wrong-identity results carry the search-cap warning; returned candidates are not an exhaustive catalogue. Most sampled failures offer other performers or other songs. No recovery yield is extrapolated for this bucket.',
        f'- **Bad/missing text:** {missing["text_missing"]} text_missing and {missing["text_bad"]} text_bad. All 20 random samples had empty/instrumental target records. *Wonderland* is a preserved reviewed truncation; *Constant Rain (Chove Chuva)* is the other bad-text result. Correct performer identity cannot supply nonexistent text; another artist’s vocal cover is not a rescue.',
        f'- **Not found:** all cached retrievals were verified locally. Empty full-title/artist and title-only searches do not prove catalogue absence. {soundtrack} titles contain “from” (a broad query-research flag, not all soundtrack annotations). The sample exposes several literal film/soundtrack suffixes and a combined *Beginnings/Colour My World* identity. Removing only descriptive soundtrack context is worth a small controlled query pilot; never split/merge a combined Billboard asset implicitly. No new requests or yield assumptions were made.',
        '- **API errors:** all 51 are HTTP 503 after bounded production retries. They are retry candidates, not 51 promised lyrics. Existing `run --retry-errors` behavior archives failures and retains provenance, but was not invoked. Even a 100% usable retry yield would add only 0.20 percentage points.',
        '', '## Recovery potential and projected coverage','',
        f'**A: {len(safe)} enumerated low-risk candidates** ({len(syntax)} explicit syntax + 5 contextual false alarms). This is a conservative shortlist, not an extrapolation or independently measured precision guarantee. Production evidence/text gates remain necessary; no mapping is approved by this report.',
        f'**B: approximately {possible:,.0f} additional possible recoveries**, beyond A, in a conditional second-pass scenario. Each quarantine stratum’s reviewed “possible deterministic” fraction is expanded to its remaining population after removing the exact low-risk shortlist. Manual/query/transport/prior-review cases contribute zero; no yield is projected for the other failure buckets. The detailed expansion is below. This estimates the size of a promising work queue, **not how many songs a yet-unbuilt rule will safely accept**. The scenario is optimistic wherever a proposed rule remains unvalidated; rejected candidates can be correlated copies of one transcription.',
        f'Under this planning allocation, approximately {len(data["rows"])-len(safe)-possible:,.0f} of all 5,991 exclusions remain excluded or unresolved. Of these, approximately {len(q)-len(safe)-possible:,.0f} are quarantined and 2,472 are in the other failure buckets. “Remain excluded” is a current evidence decision, not proof they are permanently unrecoverable.']
    table(lines,['Scenario','Additional lyrics','Usable total','% of 25,363'],[
        ('Current',0,len(accepted),pct(len(accepted),total)),
        ('A: enumerated low risk',len(safe),len(accepted)+len(safe),pct(len(accepted)+len(safe),total)),
        ('B: A + conditional possible',f'≈{len(safe)+possible:,.0f}',f'≈{len(accepted)+len(safe)+possible:,.0f}','≈'+pct(len(accepted)+len(safe)+possible,total))])
    table(lines,['Quarantine stratum after A','Population','Reviewed','Possible','Expanded possible'],[(p,n,t,k,f'{v:.1f}') for (st,p),n,t,k,v in strata if st=='quarantined'])
    # Chart/population reads only; descriptive conditional coverage, no COVID test.
    c=sqlite3.connect((ROOT/'data/processed/research.db').as_uri()+'?mode=ro',uri=True)
    assets=c.execute('SELECT s.song_id,s.first_chart_date,s.best_chart_rank,p.months_selected,s.artist FROM songs s JOIN study_population p USING(song_id)').fetchall()
    baskets=c.execute('SELECT song_id,monthly_rank,month FROM monthly_top100').fetchall();c.close()
    lines+=['','## Missingness and conditional representation','',
        'Unadjusted descriptive comparisons only. Cohorts use first Billboard chart year, not release year. Credit complexity uses the same prior audit separator heuristic (including band names). “Q share of missing” attributes missingness to the quarantine bucket; it is not a causal claim. Scenario B applies a uniform reviewed yield within each stratum, so its within-period/popularity differences are assumptions, not separately validated recovery rates.']
    header=['Group','Target','Current %','Quarantine','Q share of missing','A %','B conditional %']
    def group_row(label,ids):
        n=len(ids);ok=sum(s in accepted for s in ids);nq=sum(s in q for s in ids)
        plus=sum(s in safe for s in ids);future=sum(weights.get(s,0) for s in ids)
        return (label,n,pct(ok,n),nq,pct(nq,n-ok),pct(ok+plus,n),'≈'+pct(ok+plus+future,n))
    groups=[]
    for lo,hi,label in PERIODS:
        groups.append(group_row(label,[r[0] for r in assets if lo<=int(r[1][:4])<=hi]))
    for lo,hi,label in [(1,10,'Weekly peak 1–10'),(11,40,'Weekly peak 11–40'),(41,100,'Weekly peak 41–100')]:
        groups.append(group_row(label,[r[0] for r in assets if lo<=r[2]<=hi]))
    for lo,hi,label in [(1,1,'1 monthly basket'),(2,3,'2–3 baskets'),(4,6,'4–6 baskets'),(7,10000,'7+ baskets')]:
        groups.append(group_row(label,[r[0] for r in assets if lo<=r[3]<=hi]))
    complexity=lambda credit:bool(re.search(r'\b(featuring|feat\.?|with|and)\b|[&/,]',credit,re.I))
    for value in (False,True):groups.append(group_row('Complex credit '+str(value),[r[0] for r in assets if complexity(r[4])==value]))
    table(lines,header,groups)
    def gap(a,b):
        failure=lambda ids:sum(s not in accepted for s in ids)/len(ids)
        quarantine=lambda ids:sum(s in q for s in ids)/len(ids)
        total_gap=100*(failure(a)-failure(b));q_gap=100*(quarantine(a)-quarantine(b))
        return f'{total_gap:.2f} percentage-point missingness gap; {q_gap:.2f} points ({100*q_gap/total_gap:.1f}%) attributable arithmetically to different quarantine rates'
    lines+=['', 'Additive missingness decomposition (descriptive, not causal):', '',
        '- Complex versus simple credits: '+gap([r[0] for r in assets if complexity(r[4])],[r[0] for r in assets if not complexity(r[4])])+'.',
        '- Weekly peaks 41–100 versus 1–10: '+gap([r[0] for r in assets if r[2]>=41],[r[0] for r in assets if r[2]<=10])+'.',
        '- One monthly basket versus 7+: '+gap([r[0] for r in assets if r[3]==1],[r[0] for r in assets if r[3]>=7])+'.',
        '- Earliest-cohort missingness is largely outside quarantine: only 40.46% of missing 1958–1969 assets are quarantined, versus 81.27% in 2015–2019 and 83.26% in 2020–2026. Quarantine recovery therefore addresses modern missingness more directly; it cannot by itself remove historical or popularity selection.',
        '- In scenario B, the 2015–2019 versus 2020–2026 coverage gap narrows from 2.83 to about 0.38 points. The earliest-cohort versus 2020–2026 gap instead widens from 8.78 to about 14.21 points. The popularity and longevity gaps shrink only modestly; the credit gap remains about 14.81 points. Recovery improves counts, not uniformly representativeness.']
    lines+=['','Monthly-rank comparisons below count song-month observations; songs repeat across bins. Calendar-period rows likewise differ from first-chart cohorts.']
    monthly=[]
    for lo,hi,label in [(1,10,'Monthly rank 1–10'),(11,25,'Monthly rank 11–25'),(26,50,'Monthly rank 26–50'),(51,100,'Monthly rank 51–100')]:
        monthly.append(group_row(label,[sid for sid,rank,month in baskets if lo<=rank<=hi]))
    for lo,hi,label in [(2015,2019,'Calendar 2015–2019'),(2020,2026,'Calendar 2020–2026')]:
        monthly.append(group_row(label,[sid for sid,rank,month in baskets if lo<=int(month[:4])<=hi]))
    table(lines,header,monthly)
    lines+=['','Interpretation: the enumerated safe shortlist is too small to materially repair overall representation. A broader successful text pass could add meaningful historical and modern coverage, but it need not reduce all gaps: credit matching and provider/query availability remain separate sources of loss. Use the group-specific scenario above, not a claim that every recovery improves bias.',
        '', '## Reproduction and evidence preservation','',
        'Run `python3 src/lyrics_exclusion_audit.py` to regenerate the read-only census, verify every non-accepted result’s referenced cache/candidate revision, replay the syntax counterfactual, bind the review ledger, and generate this report/CSV. The in-memory counterfactual never replaces original title/artist strings in storage. Audit-only modules are outside the production implementation bundle.',
        'Database fingerprints at audit start/end:']
    table(lines,['Protected database','SHA-256'],data['database_sha256'].items())
    table(lines,['Implementation file','SHA-256'],[(name,sha(ROOT/name)) for name in ('src/lyrics_exclusion_audit.py','src/lyrics_production_match.py','src/lyrics_lrclib_r.py')])
    import platform, unicodedata
    lines+=['', f'Runtime: Python {platform.python_version()}, Unicode {unicodedata.unidata_version}; audit version {SEED}.']
    lines+=['', 'Cached development-pilot counterfactual (original decisions/files untouched):']
    table(lines,['Measure','Cases'],pilot['counts'].items())
    table(lines,['Title','Reviewed','Original automatic','Syntax counterfactual'],[(r['title'],r['reviewed'],r['baseline'],r['probe']) for r in pilot['changes']])
    lines+=['', 'The probe accepts no reviewed exclusion, but loses one prior automatic acceptance by exposing another conflicting full-credit text for Party To Damascus. This reinforces the scope: audit excluded assets; do not rerun or overwrite the accepted corpus. Zero observed false accepts on 29 development exclusions is not an independent precision guarantee.']
    lines+=['','See [audit scope and validation](../docs/lyrics_exclusion_audit.md) for checks and limits. No lyrics were copied into the research manifest. No classifier, content scores, COVID breakpoint, or hypothesis analysis was produced.']
    (ROOT/'reports/lyrics_exclusion_audit.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'low_risk':len(safe),'conditional_possible':possible,'remaining':len(data['rows'])-len(safe)-possible,'groups':groups,'monthly':monthly},ensure_ascii=False,indent=2))



def text_question(row):
    if not row['eligible_candidates']:
        return 'unassessed_for_target_identity'
    if row['primary'].startswith('text_'):
        return 'quality_screened_but_transcriptions_conflict'
    if row['primary']=='duration_conflict':
        return 'passes_text_screen_version_duration_unresolved'
    if row['status']=='bad_missing_text':
        return 'target_text_missing_or_bad'
    return 'target_text_or_version_requires_review'


def _review_counts(reviews):
    groups=defaultdict(Counter)
    for r in reviews:groups[(r['status'],r['primary'])][r['outcome']]+=1
    return groups


if __name__=='__main__':main()
