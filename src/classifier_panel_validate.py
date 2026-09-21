"""Validate panel coverage, model activations, song summaries and bounded inputs."""
import json
import math
from collections import defaultdict
from classifier_panel import OUT,ROOT,REPORTS,WORK,MODELS,LIMITS,THEMES,artifacts
from classifier_panel_core import AGGREGATIONS,validate_ranges,aggregate,softmax,sigmoid,bart_score
from detoxify_evaluation import frozen_sample
from lyriclens_evaluation import read_csv,sha
from public_dataset import public_cell

def close(a,b,tolerance=1e-7):
    if not math.isfinite(float(a)) or not math.isfinite(float(b)) or abs(float(a)-float(b))>tolerance:raise ValueError('Numeric reconciliation failed')

def validate():
    sample=frozen_sample();ids={r['song_id'] for r in sample};meta={r['song_id']:r for r in sample}
    old_ll={r['song_id']:r for r in read_csv(REPORTS/'lyriclens_predictions.csv')}
    old_dt={r['song_id']:r for r in read_csv(REPORTS/'detoxify_predictions.csv')}
    dimensions={'lyriclens':4,'detoxify':16,'emotion':28,'sentiment':3,'bart':3}
    single_replays=defaultdict(int)
    for m in MODELS:
        artifacts(m)
        songs=read_csv(OUT/(m+'_songs.csv'));run=json.loads((OUT/(m+'_run.json')).read_text())
        if len(songs)!=200 or {r['song_id'] for r in songs}!=ids:raise ValueError('Song IDs/count changed')
        if run['status']!='complete' or run['successful']!=200 or run['failed']!=0:raise ValueError('Incomplete model')
        if sha(OUT/(m+'_songs.csv'))!=run['song_sha256'] or sha(OUT/(m+'_chunks.jsonl'))!=run['chunks_sha256']:raise ValueError('Output changed')
        fp=run['fingerprint']
        if fp['runner_sha256']!=sha(ROOT/'src/classifier_panel.py') or fp['core_sha256']!=sha(ROOT/'src/classifier_panel_core.py') or fp['themes_sha256']!=sha(THEMES):raise ValueError('Implementation/themes changed')
        if fp['sample_sha256']!=sha(REPORTS/'lyriclens_sample.csv'):raise ValueError('Sample changed')
        raw=[json.loads(line) for line in (OUT/(m+'_chunks.jsonl')).read_text().splitlines()]
        if len(raw)!=run['model_input_pairs']:raise ValueError('Raw count changed')
        grouped=defaultdict(list)
        for r in raw:
            allowed={'song_id','chunk_index','content_start','content_end','content_tokens','input_tokens','theme','input_ids_sha256','logits','scores','nli_softmax','raw_activated_outputs'}
            if set(r)-allowed:raise ValueError('Unexpected raw field (potential text leak)')
            if r['song_id'] not in ids or len(r['logits'])!=dimensions[m]:raise ValueError('Invalid raw identity/dimensions')
            if any(not math.isfinite(x) for x in r['logits']):raise ValueError('Invalid logit')
            if not 2<=r['input_tokens']<=LIMITS[m]:raise ValueError('Window overflow')
            if r['content_tokens']!=r['content_end']-r['content_start']:raise ValueError('Wrong content length')
            if m=='bart':
                if list(r['scores'])!=[r['theme']] or r['theme'] not in run['labels']:raise ValueError('Theme changed')
                for a,b in zip(r['nli_softmax'],softmax(r['logits'])):close(a,b)
                close(r['scores'][r['theme']],bart_score(r['logits']))
            else:
                expected=softmax(r['logits']) if m=='sentiment' else [sigmoid(x) for x in r['logits']]
                if len(expected)!=len(r['raw_activated_outputs']):raise ValueError('Raw activation dimension')
                for a,b in zip(expected,r['raw_activated_outputs']):close(a,b)
                if set(r['scores'])!=set(run['labels']):raise ValueError('Missing output label')
                for label,v in zip(run['labels'],expected):close(r['scores'][label],v)
            grouped[r['song_id']].append(r)
        for song in songs:
            sid=song['song_id'];n=int(song['chunk_count']);budget=int(song['content_budget']);total=int(song['content_token_count'])
            if song['status']!='success' or song['lyrics_sha256']!=meta[sid]['lyrics_sha256']:raise ValueError('Input/status changed')
            g=grouped[sid];spans={}
            for r in g:
                span=(r['content_start'],r['content_end'])
                if r['chunk_index'] in spans and spans[r['chunk_index']]!=span:raise ValueError('Theme-dependent coverage')
                spans[r['chunk_index']]=span
            if set(spans)!=set(range(n)):raise ValueError('Missing/duplicate chunk index')
            validate_ranges([spans[i] for i in range(n)],total,budget)
            if len(g)!=n*(17 if m=='bart' else 1):raise ValueError('Repeated/missing predictions')
            for label in run['labels']:
                entries=[r for r in g if label in r['scores']]
                if {r['chunk_index'] for r in entries}!=set(range(n)) or len(entries)!=n:raise ValueError('Missing label/chunk')
                expected=aggregate([r['scores'][label] for r in entries],[r['content_tokens'] for r in entries])
                for agg in AGGREGATIONS:close(song[label+'__'+agg],expected[agg])
            if m=='sentiment':
                for agg in ('mean','token_weighted_mean'):close(sum(float(song[l+'__'+agg]) for l in run['labels']),1,tolerance=3e-7)
            if n==1 and m in ('lyriclens','detoxify'):
                mapping={'sexual':'sexual_content_score','violence':'violence_score','substance':'substance_use_score','explicit_language':'explicit_language_score'} if m=='lyriclens' else {l:l for l in run['labels']}
                old=old_ll[sid] if m=='lyriclens' else old_dt[sid]
                for label,column in mapping.items():
                    if abs(float(song[label+'__mean'])-float(old[column]))>1e-6:raise ValueError('Single-chunk old-pilot replay mismatch')
                single_replays[m]+=1
            for v in song.values():public_cell(v)
        if sum(int(r['chunk_count']) for r in songs)!=run['content_chunks']:raise ValueError('Chunk total changed')
    print('Validated 1,000 song/model dispositions; exact frozen 200 IDs; whole-token span coverage; all logits/activations/aggregates; no raw text fields; pinned artifacts.')
    print('Single-chunk previous-pilot replays within 1e-6:',dict(single_replays))

if __name__=='__main__':validate()
