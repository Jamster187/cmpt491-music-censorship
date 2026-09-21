"""Within-pilot distributions and pairwise agreement, without consensus or time analysis."""
import json
import statistics
from collections import defaultdict
from classifier_panel import OUT,REPORTS,ROOT,MODELS,save_json
from classifier_panel_core import AGGREGATIONS
from lyriclens_evaluation import read_csv,write_csv
from lyriclens_diagnostics import summary,ranks,spearman
from detoxify_diagnostics import pearson

PAIRS=[
 ('sexual','lyriclens','sexual','detoxify','sexual_explicit'),('sexual','lyriclens','sexual','bart','sexual'),('sexual','detoxify','sexual_explicit','bart','sexual'),
 ('violence','lyriclens','violence','detoxify','threat'),('violence','lyriclens','violence','bart','violence'),('violence','detoxify','threat','bart','violence'),
 ('explicit_language','lyriclens','explicit_language','detoxify','obscene'),('explicit_language','lyriclens','explicit_language','bart','profanity'),('explicit_language','detoxify','obscene','bart','profanity'),
 ('substance','lyriclens','substance','bart','drugs'),('substance','lyriclens','substance','bart','alcohol'),
 ('hostility','detoxify','toxicity','emotion','anger'),('hostility','detoxify','toxicity','emotion','disgust'),('hostility','detoxify','insult','emotion','anger'),('hostility','detoxify','insult','emotion','disgust'),
 ('romance','emotion','love','bart','romance'),('loss','emotion','sadness','bart','heartbreak'),('loss','emotion','grief','bart','grief'),
 ('negative_affect','sentiment','negative','emotion','sadness'),('negative_affect','sentiment','negative','emotion','anger')]

def percentiles(values):
    if len(values)<2:raise ValueError('Reference needs at least two songs')
    return [(r-1)/(len(values)-1) for r in ranks(values)]

def overlap(a,b):
    return dict(a_count=len(a),b_count=len(b),intersection=len(a&b),union=len(a|b),jaccard=len(a&b)/len(a|b) if a|b else None)

def agreement(xs,ys):
    if len(xs)!=len(ys):raise ValueError('Unpaired scores')
    px,py=percentiles(xs),percentiles(ys)
    result=dict(n=len(xs),pearson=pearson(xs,ys),spearman=spearman(xs,ys),mean_absolute_percentile_gap=statistics.mean(abs(a-b) for a,b in zip(px,py)),
                within_10_percentile_points=sum(abs(a-b)<=.1 for a,b in zip(px,py)),opposite_quintiles=sum((a>=.8 and b<=.2) or (a<=.2 and b>=.8) for a,b in zip(px,py)))
    for name,compare in [('high',lambda x:x>=.8),('low',lambda x:x<=.2)]:
        for k,v in overlap({i for i,x in enumerate(px) if compare(x)},{i for i,x in enumerate(py) if compare(x)}).items():result[name+'_'+k]=v
    return result

def load():
    sample=read_csv(REPORTS/'lyriclens_sample.csv');ids=[r['song_id'] for r in sample]
    models={m:{r['song_id']:r for r in read_csv(OUT/(m+'_songs.csv'))} for m in MODELS}
    for m,index in models.items():
        if set(index)!=set(ids) or len(index)!=200:raise ValueError('Model sample mismatch')
    return sample,models

def main():
    sample,models=load();ids=[r['song_id'] for r in sample];meta={r['song_id']:r for r in sample}
    groups={'all_200':ids,'core_180':[r['song_id'] for r in sample if r['sample_component']=='stratified_core']}
    distributions=[];sensitivity=[];comparisons=[];cases=[];extremes=[]
    for m,index in models.items():
        labels=json.loads((OUT/(m+'_run.json')).read_text())['labels']
        for label in labels:
            for agg in AGGREGATIONS:
                for group,subset in groups.items():
                    vals=[float(index[s][label+'__'+agg]) for s in subset]
                    distributions.append(dict(model=m,label=label,aggregation=agg,sample=group,**summary(vals)))
            mean=[float(index[s][label+'__mean']) for s in ids];maximum=[float(index[s][label+'__max']) for s in ids]
            sensitivity.append(dict(model=m,label=label,mean_vs_max_spearman=spearman(mean,maximum),mean_increase=statistics.mean(b-a for a,b in zip(mean,maximum)),
                                    largest_increase=max(b-a for a,b in zip(mean,maximum)),songs_increase_over_01=sum(b-a>.1 for a,b in zip(mean,maximum))))
            ordered=sorted(ids,key=lambda s:(float(index[s][label+'__token_weighted_mean']),s))
            for side,subset in [('low',ordered[:3]),('high',list(reversed(ordered[-3:])) )]:
                for rank,s in enumerate(subset,1):extremes.append(dict(model=m,label=label,aggregation='token_weighted_mean',side=side,rank=rank,song_id=s,title=meta[s]['title'],artist=meta[s]['artist'],score=index[s][label+'__token_weighted_mean']))
    for family,ma,la,mb,lb in PAIRS:
        for agg in AGGREGATIONS:
            for group,subset in groups.items():
                xs=[float(models[ma][s][la+'__'+agg]) for s in subset];ys=[float(models[mb][s][lb+'__'+agg]) for s in subset]
                comparisons.append(dict(family=family,model_a=ma,label_a=la,model_b=mb,label_b=lb,aggregation=agg,sample=group,**agreement(xs,ys)))
                if agg=='token_weighted_mean' and group=='all_200':
                    px,py=percentiles(xs),percentiles(ys)
                    order=sorted(range(len(subset)),key=lambda i:(px[i]-py[i],subset[i]))
                    selected=[('a_ranks_lower',i) for i in order[:2]]+[('a_ranks_higher',i) for i in order[-2:]]
                    selected += [('both_high',i) for i in sorted(range(len(subset)),key=lambda i:(min(px[i],py[i]),subset[i]),reverse=True)[:2]]
                    selected += [('both_low',i) for i in sorted(range(len(subset)),key=lambda i:(max(px[i],py[i]),subset[i]))[:2]]
                    for why,i in selected:
                        s=subset[i];cases.append(dict(family=family,model_a=ma,label_a=la,model_b=mb,label_b=lb,selection=why,song_id=s,title=meta[s]['title'],artist=meta[s]['artist'],score_a=xs[i],score_b=ys[i],percentile_a=px[i],percentile_b=py[i],absolute_percentile_gap=abs(px[i]-py[i])))
    for name,rows in [('distributions',distributions),('aggregation_sensitivity',sensitivity),('agreement',comparisons),('agreement_cases',cases),('extremes',extremes)]:write_csv(OUT/(name+'.csv'),rows)
    neutral=[]
    for line in (OUT/'bart_chunks.jsonl').read_text().splitlines():
        r=json.loads(line)
        if r['nli_softmax'][1]>.5:
            neutral.append((r['scores'][r['theme']],r['theme'],r['song_id']))
    save_json(OUT/'diagnostic_counts.json',dict(sample_songs=200,core_songs=180,labels=59,comparisons=len(comparisons),
        bart_neutral_majority_pairs=len(neutral),bart_neutral_majority_and_theme_over_half=sum(v>.5 for v,_,_ in neutral),
        counts={m:dict(songs=200,multichunk=sum(int(r['chunk_count'])>1 for r in index.values()),chunks=sum(int(r['chunk_count']) for r in index.values()),
                      max_chunks=max(int(r['chunk_count']) for r in index.values()),max_tokens=max(int(r['content_token_count']) for r in index.values())) for m,index in models.items()}))
    concepts={
      'sexual_content':['lyriclens.sexual','detoxify.sexual_explicit','bart.sexual'],
      'violence':['lyriclens.violence','detoxify.threat','bart.violence'],
      'explicit_language':['lyriclens.explicit_language','detoxify.obscene','bart.profanity'],
      'substance_use':['lyriclens.substance','bart.drugs','bart.alcohol'],
      'hostility_and_negative_affect':['detoxify.toxicity','detoxify.severe_toxicity','detoxify.insult','detoxify.identity_attack','emotion.anger','emotion.disgust','emotion.annoyance','emotion.disapproval'],
      'emotion':['emotion.'+l for l in json.loads((OUT/'emotion_run.json').read_text())['labels']],
      'sentiment':['sentiment.negative','sentiment.neutral','sentiment.positive'],
      'themes':['bart.'+l for l in json.loads((OUT/'bart_run.json').read_text())['labels']]}
    save_json(ROOT/'docs/classifier_panel_concepts.json',dict(version='classifier-panel-concepts-v1',interpretation='Conceptual grouping only. No equivalence of labels, common units, weights or consensus implied.',families=concepts))
    print('Generated 59-label distributions, aggregation sensitivity, 160 pairwise comparisons and 160 selected agreement/disagreement rows. No period analysis.')

if __name__=='__main__':main()
