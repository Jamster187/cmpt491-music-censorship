"""Descriptive same-song comparison; no trend tests or combined content score."""
import json
import math
import statistics
from collections import Counter
from detoxify_evaluation import LABELS, REPORTS, ROOT, join_predictions
from lyriclens_evaluation import read_csv, write_csv, PERIODS, digest
from lyriclens_diagnostics import summary, spearman

PAIRS = (('explicit_language_score','obscene'),('explicit_language_score','toxicity'),
         ('sexual_content_score','sexual_explicit'),('violence_score','threat'),('violence_score','severe_toxicity'))

def pearson(xs, ys):
    if len(xs) != len(ys) or not xs: raise ValueError('Unpaired data')
    a,b=statistics.mean(xs),statistics.mean(ys)
    den=math.sqrt(sum((x-a)**2 for x in xs)*sum((y-b)**2 for y in ys))
    return sum((x-a)*(y-b) for x,y in zip(xs,ys))/den if den else None

def joined():
    ll=read_csv(REPORTS/'lyriclens_predictions.csv')
    dt=read_csv(REPORTS/'detoxify_predictions.csv')
    return [dict(a, **{k:v for k,v in b.items() if k in LABELS or k.startswith('detoxify_')}) for a,b in join_predictions(ll,dt)]

def select_review(rows):
    result={}
    def add(r, why):
        if r['song_id'] not in result: result[r['song_id']]=dict(r,review_selection=why)
        else: result[r['song_id']]['review_selection']+='; '+why
    for r in rows:
        if r['sample_component']!='stratified_core':add(r,r['sample_component'])
    for a,b in PAIRS:
        ordered=sorted(rows,key=lambda r:(float(r[a])-float(r[b]),r['song_id']))
        for r in ordered[:2]:add(r,f'{b} exceeds {a}')
        for r in ordered[-2:]:add(r,f'{a} exceeds {b}')
    for k in LABELS:
        ordered=sorted(rows,key=lambda r:(float(r[k]),r['song_id']))
        add(ordered[0],k+' minimum');add(ordered[-1],k+' maximum')
    for p in PERIODS:
        group=sorted([r for r in rows if r['period']==p],key=lambda r:(float(r['toxicity']),r['song_id']))
        add(group[len(group)//2],'period toxicity midpoint')
    for r in rows:
        if r['title'] in ('Rosones','Macarena'):add(r,'Spanish language diagnostic')
    for r in sorted(rows,key=lambda r:digest('detoxify-review-v1:'+r['song_id'])):
        if len(result)>=50:break
        add(r,'deterministic supplementary review')
    if not 40<=len(result)<=60:raise ValueError('Unexpected review size')
    return sorted(result.values(),key=lambda r:(r['period'],r['song_id']))

def diagnostics(rows):
    core=[r for r in rows if r['sample_component']=='stratified_core']
    d={}
    for name,group in [('all_200',rows),('core_180',core)]:
        d[name]={'distributions':{k:summary([float(r[k]) for r in group]) for k in LABELS},
                 'correlations':[{ 'lyriclens':a,'detoxify':b,'pearson':pearson([float(r[a]) for r in group],[float(r[b]) for r in group]),
                                   'spearman':spearman([float(r[a]) for r in group],[float(r[b]) for r in group])} for a,b in PAIRS],
                 'word_count_spearman':{k:spearman([float(r['word_count']) for r in group],[float(r[k]) for r in group]) for k in LABELS}}
    d['period_core']={p:{'n':len(g),'truncated':sum(r['detoxify_truncated']=='True' for r in g),
                             'means':{k:statistics.mean(float(r[k]) for r in g) for k in LABELS},
                             'medians':{k:statistics.median(float(r[k]) for r in g) for k in LABELS}}
                      for p in PERIODS for g in [[r for r in core if r['period']==p]]}
    d['truncation']={'all_200':sum(r['detoxify_truncated']=='True' for r in rows),'core_180':sum(r['detoxify_truncated']=='True' for r in core),
                     'tokens':summary([int(r['detoxify_token_count']) for r in rows]),
                     'by_status':{flag:{'n':len(g),'mean_scores':{k:statistics.mean(float(r[k]) for r in g) for k in LABELS}}
                                  for flag in ('True','False') for g in [[r for r in rows if r['detoxify_truncated']==flag]]}}
    return d

def main():
    rows=joined();d=diagnostics(rows)
    (REPORTS/'detoxify_diagnostics.json').write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    review=select_review(rows)
    path=ROOT/'docs/detoxify_review_notes.json'
    if path.exists():
        notes=json.loads(path.read_text())['annotations']
        if set(notes)!={r['song_id'] for r in review}:raise ValueError('Review notes mismatch')
        for r in review:r.update(notes[r['song_id']])
        write_csv(REPORTS/'detoxify_review.csv',review)
    else:
        write_csv(ROOT/'data/experiments/detoxify/review_selection.csv',review)
    print('Descriptive diagnostics generated; selected',len(review),'reviews')

if __name__=='__main__':main()
