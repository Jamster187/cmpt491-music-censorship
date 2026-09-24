"""Refine only the frozen 300-song pilot; audit all 150 prior ambiguous cases."""
from collections import Counter,defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
from genre_evidence import ROOT,OUT,ro,DATABASE,sha
from genre_pilot import load_sample
from genre_rules import eligible,mapping,TAXONOMY
from genre_sample import complex_credit
from genre_refined_rules import assign,CONFIG
DEST=ROOT/'archive/intermediate_reports/genre_refinement'
LOCAL=ROOT/'data/experiments/genre_refinement'


def write_csv(path,rows):
    f=io.StringIO();w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader()
    for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict,bool)) else v for k,v in r.items()})
    tmp=path.with_suffix('.tmp');tmp.write_text(f.getvalue());tmp.replace(path)


def audit_ambiguity(old,rows,new):
    # Non-exclusive flags are evidence diagnostics, not independent gold genres.
    strong=new['mapped_genres'];flags=[]
    selected={g for r in rows if eligible(r) and r['level'] in ('recording','song_item') for g in mapping(r['label'])}
    candidates=set(json.loads(old['primary_candidates']))
    if len(candidates)<2:flags.append('same_category_only')
    if any(x['supporting_tag_count']>=2 for x in new['support']['direct_song'].values()):flags.append('compatible_tags_within_category')
    if any(x['max_tag_votes']==1 for x in new['support']['direct_song'].values()):flags.append('isolated_low_support_category')
    if 'Pop' in candidates and len(candidates)>1:flags.append('pop_with_specific_genre')
    for name,gs in [('rock_alternative',{'Rock','Alternative / Indie'}),('rock_metal',{'Rock','Metal'}),('rap_soul',{'Hip-Hop / Rap','R&B / Soul'})]:
        if gs<=candidates:flags.append(name)
    if 'Latin' in candidates:flags.append('latin_crossover')
    if 'Electronic / Dance' in candidates:flags.append('electronic_crossover')
    artist=set(new['support']['artist_context'])
    if artist-selected:flags.append('artist_context_adds_other_categories')
    sources=defaultdict(set)
    for r in rows:
        if eligible(r) and r['level'] in ('recording','song_item'):sources[r['provider']].update(mapping(r['label']))
    if len(sources)>1 and len({tuple(sorted(s)) for s in sources.values()})>1:flags.append('direct_providers_differ')
    if len(new['genre_candidates'])>1:flags.append('multiple_strong_candidates')
    if new['disposition']=='ambiguous':flags.append('competing_strong_categories')
    if 'same_category_only' in flags:reason='same_category_only'
    elif len(new['genre_candidates'])>1:reason='cross_genre_strong_evidence'
    else:reason='weak_or_conflicting_evidence'
    return dict(song_id=old['song_id'],title=old['title'],artist=old['artist'],old_candidates=sorted(candidates),primary_reason=reason,flags=flags,strong_categories=strong,new_disposition=new['disposition'],new_primary=new['primary_genre'])


def estimates(sample,decisions):
    c=ro(DATABASE);c.row_factory=__import__('sqlite3').Row
    population=[dict(r) for r in c.execute('SELECT * FROM songs')];c.close()
    anchor_ids={s['song_id'] for s in sample if s['sample_role']=='challenge'}
    def stratum(r):return (r['period'],('high' if int(r['best_rank'])<=25 else 'lower')+('_complex' if complex_credit(r['artist']) else '_simple'))
    counts=Counter(stratum(r) for r in population if r['song_id'] not in anchor_ids)
    ns=Counter((r['period'],r['sample_stratum']) for r in sample if r['sample_role']!='challenge')
    known=json.loads((ROOT/'reports/genre/summary.json').read_text())['periods'];out={};tot=Counter()
    for period,k in known.items():
        weighted=Counter();denom=0;sample_counts=Counter()
        for r in sample:
            if r['period']!=period:continue
            d=decisions[r['song_id']];sample_counts[d['disposition']]+=1
            mapped=any(d['support'].values())
            if not mapped:continue
            w=1 if r['song_id'] in anchor_ids else counts[stratum(r)]/ns[stratum(r)]
            weighted[d['disposition']]+=w;denom+=w
        if not denom:raise ValueError('No mapped-evidence sample in period')
        expected={status:k['mapped_evidence']*weighted[status]/denom for status in ('primary','ambiguous','Other','insufficient')}
        expected['insufficient']+=k['population']-k['mapped_evidence']
        tot.update(expected)
        out[period]=dict(population=k['population'],mapped_evidence=k['mapped_evidence'],pilot_counts=dict(sample_counts),expected_pct={s:round(100*n/k['population'],2) for s,n in expected.items()})
    return dict(periods=out,expected_population_counts={s:round(n) for s,n in tot.items()},expected_population_pct={s:round(100*n/28041,2) for s,n in tot.items()},method='N/n rank-credit-period design weights; challenge cases weight 1; calibrate mapped/nonmapped evidence separately in each period to the exact v1 evidence census. Approximate availability, not accuracy.')


def review_set(results):
    rare={'Metal','Alternative / Indie','Jazz / Blues','Latin','Reggae / Dancehall','K-Pop','Afrobeats / African Pop','Gospel / Christian','Folk / Singer-Songwriter'}
    def key(r):return (r['sample_role']!='challenge',r['primary_genre'] not in rare,r['old_disposition']!='ambiguous',hashlib.sha256(('genre-refinement-review-v1'+r['song_id']).encode()).hexdigest())
    primaries=[r for r in results if r['primary_genre']]
    selected=[]
    for i,p in enumerate(sorted({r['period'] for r in results})):
        selected+=sorted([r for r in primaries if r['period']==p],key=key)[:9 if i<6 else 6]
    ids={r['song_id'] for r in selected}
    selected+=sorted([r for r in primaries if r['song_id'] not in ids],key=key)[:max(0,60-len(selected))]
    return sorted(selected,key=lambda r:(r['period'],r['song_id']))


def build():
    sample=load_sample();old={r['song_id']:r for r in csv.DictReader((ROOT/'reports/genre/pilot.csv').open())}
    evidence={r['song_id']:r['evidence'] for r in json.loads((OUT/'pilot_evidence.json').read_text())}
    ids={r['song_id'] for r in sample}
    if len(ids)!=300 or ids!=set(evidence) or ids!=set(old):raise ValueError('Frozen sample mismatch')
    decisions={sid:assign(evidence[sid]) for sid in sorted(ids)}
    results=[dict(s,**{k:v for k,v in decisions[s['song_id']].items() if k!='support'},old_disposition=old[s['song_id']]['disposition']) for s in sample]
    audits=[audit_ambiguity(old[sid],evidence[sid],decisions[sid]) for sid in sorted(ids) if old[sid]['disposition']=='ambiguous']
    if len(audits)!=150:raise ValueError('Prior ambiguity cohort changed')
    DEST.mkdir(exist_ok=True);LOCAL.mkdir(parents=True,exist_ok=True)
    write_csv(DEST/'pilot.csv',results);write_csv(DEST/'ambiguity_audit.csv',audits)
    review=review_set(results)
    write_csv(DEST/'human_review_template.csv',[dict({k:r[k] for k in ('song_id','title','artist','period','primary_genre')},human_judgment='',human_notes='') for r in review])
    if (DEST/'review.csv').exists():
        checked=list(csv.DictReader((DEST/'review.csv').open()))
        if {r['song_id'] for r in checked}!={r['song_id'] for r in review}:raise ValueError('Review set drifted')
    (LOCAL/'support.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    transition=Counter((old[sid]['disposition'],decisions[sid]['disposition']) for sid in ids)
    summary=dict(version=CONFIG['version'],sample=300,counts=dict(Counter(r['disposition'] for r in results)),ambiguity_primary_reasons=dict(Counter(r['primary_reason'] for r in audits)),ambiguity_flags=dict(Counter(flag for r in audits for flag in r['flags'])),transitions=[dict(old=a,new=b,count=n) for (a,b),n in sorted(transition.items())],categories={g:dict(primary=sum(r['primary_genre']==g for r in results),strong_support=sum(g in r['mapped_genres'] for r in results)) for g in TAXONOMY},estimates=estimates(sample,decisions),hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'reports/genre/sample.csv',ROOT/'reports/genre/pilot.csv',OUT/'pilot_evidence.json',ROOT/'docs/genre/taxonomy_mapping.json',ROOT/'docs/genre/refinement_rules.json',ROOT/'src/genre_refined_rules.py',Path(__file__).resolve()]})
    (DEST/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:summary[k] for k in ('counts','ambiguity_primary_reasons','ambiguity_flags','transitions')},indent=2));print(summary['estimates']['expected_population_pct'])

if __name__=='__main__':build()
