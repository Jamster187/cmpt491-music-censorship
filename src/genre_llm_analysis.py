"""Rebuild numerical pilot diagnostics, without changing any model judgments."""
import csv
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from genre_llm import ROOT, OUT, LOCAL, dump, check_predictions, digest


def load(name):
    return {r['song_id']:r for r in json.loads((OUT/f'{name}.json').read_text())}


def analyze():
    sample=list(csv.DictReader((ROOT/'reports/genre/sample.csv').open()))
    ids=[r['song_id'] for r in sample]
    a,b,repeat,exact=[load(x) for x in ('metadata','identity','repeat','exact_repeat')]
    check_predictions({'predictions':list(a.values())},ids)
    old={r['song_id']:r for r in csv.DictReader((ROOT/'archive/intermediate_reports/genre_refinement/pilot.csv').open())}
    direct={sid:r for sid,r in old.items() if r['primary_genre']}
    strong={sid:r for sid,r in old.items() if json.loads(r['mapped_genres'])}
    summary={'assigned':len(a), 'confidence':dict(Counter(r['confidence'] for r in a.values())),
             'genres':dict(Counter(r['primary_genre'] for r in a.values())),
             'strong_primary_n':len(direct),'strong_primary_agree':sum(a[s]['primary_genre']==r['primary_genre'] for s,r in direct.items()),
             'strong_set_n':len(strong),'strong_set_agree':sum(a[s]['primary_genre'] in json.loads(r['mapped_genres']) for s,r in strong.items()),
             'identity_n':len(b),'identity_agree':sum(r['primary_genre']==a[s]['primary_genre'] for s,r in b.items()),
             'repeat_n':len(repeat),'repeat_agree':sum(r['primary_genre']==a[s]['primary_genre'] for s,r in repeat.items()),
             'exact_repeat_n':len(exact),'exact_repeat_agree':sum(r['primary_genre']==a[s]['primary_genre'] for s,r in exact.items())}
    evidence={r['song_id']:r['genre_evidence'] for r in json.loads((OUT/'inputs.json').read_text())}
    summary['identity_by_evidence']={}
    for has_tags in (False,True):
        paired=[sid for sid in b if bool(evidence[sid])==has_tags]
        summary['identity_by_evidence']['tags' if has_tags else 'no_tags']={'n':len(paired),'agree':sum(a[sid]['primary_genre']==b[sid]['primary_genre'] for sid in paired)}
    summary['periods']={}
    for p in sorted({r['period'] for r in sample}):
        selected=[a[r['song_id']] for r in sample if r['period']==p]
        summary['periods'][p]={'n':len(selected),'confidence':dict(Counter(r['confidence'] for r in selected))}
    runs=[]
    for mode in ('metadata','identity','repeat','exact_repeat'):
        for f in sorted((LOCAL/mode).glob('*/complete.json')):
            r=json.loads(f.read_text());runs.append({'mode':mode,'batch':int(f.parent.name),**r})
    dump(OUT/'runs.json',runs)
    summary['performance']={}
    for mode in ('metadata','identity','repeat','exact_repeat'):
        r=[x for x in runs if x['mode']==mode]
        summary['performance'][mode]={'seconds':sum(x['elapsed_seconds'] for x in r),
                                     'songs':sum(len(x['song_ids']) for x in r),
                                     'tokens':{k:sum(x['usage'].get(k,0) for x in r) for k in ('input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens')}}
    retired=[json.loads(f.read_text()) for f in (LOCAL/'pre_input_screen_v1/requests').glob('*/*/complete.json')]
    summary['performance']['superseded_requests']={'batches':len(retired),'seconds':sum(r['elapsed_seconds'] for r in retired)}
    summary['performance']['full_serial_hours']=summary['performance']['metadata']['seconds']/300*28041/3600
    start=min(datetime.fromisoformat(r['date']) for r in runs)
    end=max(datetime.fromisoformat(r['date'])+timedelta(seconds=r['elapsed_seconds']) for r in runs)
    summary['performance']['elapsed_wall_seconds']=(end-start).total_seconds()
    t=summary['performance']['metadata']['tokens']
    output=t['output_tokens']+t.get('reasoning_output_tokens',0)
    summary['performance']['full_api_uncached_usd_upper']=(t['input_tokens']*5+output*30)/1e6*28041/300
    summary['performance']['full_api_observed_cache_usd_upper']=((t['input_tokens']-t['cached_input_tokens'])*5+t['cached_input_tokens']*.5+output*30)/1e6*28041/300
    summary['performance']['prediction_bytes_per_song']=(OUT/'metadata.json').stat().st_size/300
    # Review paired cases, strong-tag disagreements, earlier failure examples,
    # low-confidence predictions and anchors; hash-fill to at least 140.
    chosen=set(b)
    chosen.update(sid for sid,r in direct.items() if a[sid]['primary_genre']!=r['primary_genre'])
    chosen.update(r['song_id'] for r in sample if r['title'] in ('I Feel For You','Hooked On You'))
    for r in sample:
        sid=r['song_id']
        if a[sid]['confidence']=='low' or r['sample_role']=='challenge':
            chosen.add(sid)
    # Roles are checked explicitly; challenge anchors may be named differently.
    anchors=[r for r in sample if r['sample_role']!='stratified_hash']
    chosen.update(r['song_id'] for r in anchors)
    ranked=sorted(sample,key=lambda r:digest(('review-v1'+r['song_id']).encode()))
    for r in ranked:
        if len(chosen)>=140:break
        chosen.add(r['song_id'])
    # Additional diagnostic checks surfaced during inspection; not a random audit.
    chosen.update(r['song_id'] for r in sample if r['title'] in ('Sincerely Yours','You Give Love A Bad Name','Scared To Start'))
    review=[]
    for r in sample:
        sid=r['song_id']
        if sid not in chosen:continue
        review.append({'song_id':sid,'title':r['title'],'artist':r['artist'],'period':r['period'],
                       'primary_genre':a[sid]['primary_genre'],'confidence':a[sid]['confidence'],
                       'reason':a[sid]['reason'],'identity_primary':b.get(sid,{}).get('primary_genre',''),
                       'review':'','identity_review':'','review_note':'','review_source':''})
    with (OUT/'review_template.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(review[0]),lineterminator='\n');w.writeheader();w.writerows(review)
    review_file=OUT/'review.csv'
    if review_file.exists():
        judgments=list(csv.DictReader(review_file.open()))
        if {r['song_id'] for r in judgments}!={r['song_id'] for r in review}:raise ValueError('Review selection changed')
        if any(r['review'] not in ('plausible','questionable','clearly wrong') for r in judgments):raise ValueError('Incomplete review')
        summary['review']={'n':len(judgments),'counts':dict(Counter(r['review'] for r in judgments)),
                           'identity_counts':dict(Counter(r['identity_review'] for r in judgments if r['identity_primary'])),
                           'paired_metadata_counts':dict(Counter(r['review'] for r in judgments if r['identity_primary'])),
                           'by_confidence':{c:dict(Counter(r['review'] for r in judgments if r['confidence']==c)) for c in ('high','medium','low')},
                           'by_period':{p:dict(Counter(r['review'] for r in judgments if r['period']==p)) for p in summary['periods']}}
    dump(OUT/'summary.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':analyze()
