"""Run only the frozen 300-song genre pilot; census evidence, not assignments."""
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import sqlite3
import time
from genre_evidence import ROOT, OUT, DATABASE, ro, sha
from genre_rules import assign, eligible, mapping, TAXONOMY
from genre_sample import complex_credit

REPORTS=ROOT/'reports/genre'


def load_sample(path=REPORTS/'sample.csv'):
    rows=list(csv.DictReader(path.open()))
    if len(rows)!=300 or len({r['song_id'] for r in rows})!=300:
        raise ValueError('Only the frozen 300-song sample is allowed')
    frozen=json.loads((OUT/'sample_design.json').read_text())
    if sha(path)!=frozen['sample_sha256']:raise ValueError('Frozen sample changed')
    return rows


def collect(c,sid):
    # Release groups and albums remain context. Existing links do not establish
    # that a release genre describes this track rather than its compilation.
    return [dict(r) for r in c.execute('SELECT e.* FROM links l JOIN evidence e USING(provider,level,entity_id) WHERE l.song_id=? ORDER BY e.provider,e.level,e.entity_id,e.label,e.field,e.reference',(sid,))]


def build():
    start=time.monotonic();sample=load_sample();c=ro(DATABASE);c.row_factory=sqlite3.Row
    population={r['song_id']:dict(r) for r in c.execute('SELECT * FROM songs')}
    if len(population)!=28041 or not {r['song_id'] for r in sample}<=population.keys():raise ValueError('Population mismatch')
    results=[];raw=[]
    for song in sample:
        evidence=collect(c,song['song_id']);decision=assign(evidence)
        results.append(dict(song,**decision))
        raw.append(dict(song_id=song['song_id'],evidence=evidence))
    path=REPORTS/'pilot.csv'
    f=io.StringIO()
    w=csv.DictWriter(f,fieldnames=list(results[0]),lineterminator='\n');w.writeheader()
    for row in results:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,bool)) else v for k,v in row.items()})
    temp=path.with_suffix('.tmp');temp.write_text(f.getvalue());temp.replace(path)
    (OUT/'pilot_evidence.json').write_text(json.dumps(raw,ensure_ascii=False,sort_keys=True)+'\n')
    # Full-population inventory counts evidence availability only: never call
    # assign outside the 300-song loop and never persist population genre labels.
    entities=defaultdict(set)
    for r in c.execute('SELECT provider,level,entity_id,song_id FROM links'):entities[tuple(r)[:3]].add(r['song_id'])
    any_raw=set();mapped=set();direct=set();by_source=defaultdict(set)
    seen=set()
    for r in c.execute('SELECT provider,level,entity_id,label,votes,raw FROM evidence WHERE votes>0'):
        key=(r['provider'],r['level'],r['entity_id']);sids=entities[key];any_raw.update(sids)
        # Duplicate cached editions cannot increase availability counts.
        marker=tuple(r)
        if marker in seen:continue
        seen.add(marker)
        if eligible(r):
            mapped.update(sids);by_source[r['provider']+'/'+r['level']].update(sids)
            if r['level'] in ('recording','song_item'):direct.update(sids)
    periods={}
    for p in dict.fromkeys(s['period'] for s in sample):
        ids={sid for sid,s in population.items() if s['period']==p};ss=[s for s in results if s['period']==p]
        periods[p]=dict(population=len(ids),raw_evidence=len(ids&any_raw),mapped_evidence=len(ids&mapped),direct_mapped_evidence=len(ids&direct),pilot=len(ss),pilot_dispositions=dict(Counter(s['disposition'] for s in ss)))
    estimates={}
    challenges={r['song_id'] for r in results if r['sample_role']=='challenge'}
    for p in periods:
        total=sum(r['primary_genre'] is not None for r in results if r['period']==p and r['sample_role']=='challenge')
        for group in ('high_complex','high_simple','lower_complex','lower_simple'):
            frame=[r for sid,r in population.items() if sid not in challenges and r['period']==p and ('high' if r['best_rank']<=25 else 'lower')+('_complex' if complex_credit(r['artist']) else '_simple')==group]
            sampled=[r for r in results if r['period']==p and r['sample_stratum']==group]
            if frame and not sampled:raise ValueError('Unrepresented estimation stratum')
            if sampled:total+=len(frame)*sum(r['primary_genre'] is not None for r in sampled)/len(sampled)
        estimates[p]=round(100*total/periods[p]['population'],2)
    from month_end_snapshots import select_snapshots
    monthly,_=select_snapshots(json.loads((ROOT/'data/raw/billboard-hot-100.json').read_text()))
    monthly_counts=Counter(r[3] for r in monthly)
    categories={g:dict(primary=sum(s['primary_genre']==g for s in results),any_evidence=sum(g in s['mapped_genres'] for s in results),pilot_primary_monthly_rows=sum(monthly_counts[s['song_id']] for s in results if s['primary_genre']==g),primary_periods=dict(Counter(s['period'] for s in results if s['primary_genre']==g))) for g in TAXONOMY}
    summary=dict(population=28041,pilot=300,raw_positive_evidence=len(any_raw),mapped_evidence=len(mapped),direct_mapped_evidence=len(direct),mapped_by_source={k:len(v) for k,v in sorted(by_source.items())},dispositions=dict(Counter(s['disposition'] for s in results)),by_sample_role={role:dict(Counter(s['disposition'] for s in results if s['sample_role']==role)) for role in ('challenge','stratified_hash')},periods=periods,estimated_primary_coverage_pct=estimates,categories=categories,evidence_input_manifest_sha256=hashlib.sha256(json.dumps([tuple(r) for r in c.execute('SELECT * FROM inputs ORDER BY path')],separators=(',',':')).encode()).hexdigest(),input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (REPORTS/'sample.csv',ROOT/'docs/genre/taxonomy_mapping.json',ROOT/'src/genre_rules.py',ROOT/'src/genre_pilot.py',ROOT/'src/genre_evidence.py',ROOT/'src/genre_sample.py',OUT/'inventory.json')},output_sha256=sha(path))
    (REPORTS/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    elapsed=time.monotonic()-start
    (OUT/'benchmark.json').write_text(json.dumps(dict(seconds=elapsed,inventory_bytes=DATABASE.stat().st_size,pilot_evidence_bytes=(OUT/'pilot_evidence.json').stat().st_size),indent=2)+'\n')
    c.close();print(json.dumps({k:v for k,v in summary.items() if k not in ('periods','categories','input_sha256')},indent=2));print('Seconds',elapsed)

if __name__=='__main__':build()
