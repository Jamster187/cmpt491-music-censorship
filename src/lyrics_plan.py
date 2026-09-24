"""Prepare a reproducible lyrics pilot; no HTTP or lyrics retrieval is implemented."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from research import ROOT, connect, sha
from musicbrainz import write_json

VERSION='study-lyrics-pilot-v1'
PERIODS=[(1958,1969,'1958–1969',29),(1970,1979,'1970s',29),(1980,1989,'1980s',29),
         (1990,1999,'1990s',29),(2000,2009,'2000s',28),(2010,2019,'2010–2019',28),(2020,2026,'2020–2026',28)]
BLOCKER='No verified project entitlement for automated full-lyrics acquisition, retention, and intended research reuse; see archive/intermediate_reports/lyrics_source_assessment.md'


def select(songs):
    chosen=[]
    key=lambda s:hashlib.sha256((VERSION+s['song_id']).encode()).hexdigest()
    for start,end,label,quota in PERIODS:
        pool=sorted([s for s in songs if start<=int(s['first_chart_date'][:4])<=end],key=key)
        if len(pool)<quota:
            raise ValueError('Insufficient study members for pilot period: '+label)
        local={}
        for year in range(start,end+1):
            yearly=[s for s in pool if int(s['first_chart_date'][:4])==year]
            if yearly:
                local[yearly[0]['song_id']]=yearly[0]
        for s in pool:
            if len(local)>=quota:
                break
            local[s['song_id']]=s
        chosen.extend(dict(s,period=label) for s in sorted(local.values(),key=key))
    if len(chosen)!=200 or len({s['song_id'] for s in chosen})!=200:
        raise ValueError('Pilot must have 200 unique study members')
    return chosen


def prepare(conn):
    columns=('song_id','title','artist','first_chart_date')
    songs=[dict(zip(columns,r)) for r in conn.execute('SELECT s.song_id,s.title,s.artist,s.first_chart_date FROM songs s JOIN study_population p USING(song_id)')]
    selected=select(songs)
    expected=[(s['song_id'],s['period'],i,VERSION) for i,s in enumerate(selected,1)]
    existing=conn.execute('SELECT * FROM lyrics_pilot ORDER BY selection_order').fetchall()
    if existing and existing!=expected:
        raise ValueError('Existing lyrics pilot differs; refuse to replace it')
    report=ROOT/'archive/intermediate_reports/lyrics_source_assessment.md'
    provenance=json.dumps({'assessment_path':str(report.relative_to(ROOT)),'assessment_sha256':sha(report),'retrieval_attempted':False},sort_keys=True)
    with conn:
        if not existing:
            conn.executemany('INSERT INTO lyrics_pilot VALUES (?,?,?,?)',expected)
        conn.execute("UPDATE lyrics_manifest SET lyrics_status='blocked_source_access',failure_reason=?,provenance_json=? WHERE lyrics_status='not_attempted'",(BLOCKER,provenance))
    payload={'selection_version':VERSION,'population_count':len(songs),'sample_size':200,
             'period_counts':dict(Counter(s['period'] for s in selected)),
             'selection_rule':'One hashed asset per available first-chart year, then hash-order quota fill within periods',
             'assessment_sha256':sha(report),'songs':selected,'retrieval_attempted':False}
    write_json(ROOT/'data/processed/lyrics_pilot.json',payload)
    return payload


if __name__=='__main__':
    with connect() as conn:
        result=prepare(conn)
    print(json.dumps({k:v for k,v in result.items() if k!='songs'},indent=2))
