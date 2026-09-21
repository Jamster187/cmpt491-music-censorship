"""Five-model, whole-input pilot; hard-bounded to the frozen 200-song sample."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import resource
import time
from classifier_panel_core import VERSION, AGGREGATIONS, chunk_ranges, aggregate, softmax, bart_score
from detoxify_evaluation import frozen_sample, LABELS as DETOX_LABELS
from lyriclens_evaluation import ROOT, REPORTS, sha, digest, write_csv, extract_definitions

WORK=ROOT/'data/experiments/classifier_panel'
OUT=REPORTS/'classifier_panel'
THEMES=ROOT/'docs/classifier_panel_themes.json'
MODELS=('lyriclens','detoxify','emotion','sentiment','bart')
LIMITS={'lyriclens':1024,'detoxify':512,'emotion':512,'sentiment':512,'bart':1024}

def save_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
    temp.replace(path)

def ll_preprocessor():
    import nltk
    import pandas as pd
    from nltk.stem import WordNetLemmatizer
    folder=ROOT/'data/experiments/lyriclens'
    nltk.data.path[:]=[str(folder/'nltk_data')]
    nltk.word_tokenize('Test.');nltk.pos_tag(['test']);WordNetLemmatizer().lemmatize('tests')
    failures=[]
    def monitored(fn):
        def call(*a,**kw):
            try:return fn(*a,**kw)
            except Exception:
                failures.append(fn.__name__);raise
        return call
    nltk.word_tokenize=monitored(nltk.word_tokenize);nltk.pos_tag=monitored(nltk.pos_tag)
    WordNetLemmatizer.lemmatize=monitored(WordNetLemmatizer.lemmatize)
    class UI:
        def warning(self,*a,**kw):raise ValueError('Preprocessing fallback')
    env={'nltk':nltk,'pd':pd,'re':re,'st':UI()}
    exec(extract_definitions(folder/'source/app.py',{'LongformerPreprocessor'}),env)
    obj=env['LongformerPreprocessor']()
    def clean(text):
        result=obj.clean_and_lemmatize(text)
        if not result or failures:raise ValueError('Empty normalized lyric or preprocessing fallback')
        return result
    return clean

def load_model(key):
    import torch
    from transformers import AutoConfig,AutoTokenizer,AutoModelForSequenceClassification,LongformerTokenizer,LongformerForSequenceClassification,RobertaConfig,RobertaTokenizer,RobertaForSequenceClassification
    from safetensors.torch import load_file
    clean=lambda text:text
    if key=='lyriclens':
        folder=ROOT/'data/experiments/lyriclens/model'
        tok=LongformerTokenizer.from_pretrained(folder,local_files_only=True)
        model=LongformerForSequenceClassification(AutoConfig.from_pretrained(folder,local_files_only=True))
        model.load_state_dict(load_file(str(folder/'model.safetensors')),strict=True)
        labels=['sexual','violence','substance','explicit_language'];clean=ll_preprocessor()
    elif key=='detoxify':
        folder=ROOT/'data/experiments/detoxify'
        tok=RobertaTokenizer.from_pretrained(folder/'tokenizer',local_files_only=True)
        model=RobertaForSequenceClassification(RobertaConfig.from_pretrained(folder/'tokenizer',num_labels=16,local_files_only=True))
        state=torch.load(folder/'toxic_debiased-c7548aa0.ckpt',map_location='cpu',weights_only=True)['state_dict']
        if not torch.equal(state.pop('roberta.embeddings.position_ids'),model.roberta.embeddings.position_ids):raise ValueError('Unexpected buffer')
        model.load_state_dict(state,strict=True)
        labels=list(DETOX_LABELS)
    else:
        folder=WORK/key
        tok=AutoTokenizer.from_pretrained(folder,local_files_only=True,use_fast=False)
        model=AutoModelForSequenceClassification.from_pretrained(folder,local_files_only=True,weights_only=True)
        labels=[model.config.id2label[i].lower() for i in range(model.config.num_labels)]
        if key=='sentiment':
            # The model-card's mention/URL substitution; no implicit language conversion.
            clean=lambda text:' '.join('@user' if t.startswith('@') and len(t)>1 else 'http' if t.startswith('http') else t for t in text.split(' '))
        if key=='bart':
            if labels!=['contradiction','neutral','entailment']:raise ValueError('Unexpected NLI label order')
            labels=[x['id'] for x in json.loads(THEMES.read_text())['themes']]
    return model.eval(),tok,labels,clean

def artifacts(key):
    pins=json.loads((OUT/'artifacts.json').read_text())
    spec=pins[key]
    folder=ROOT/spec['local_relative_directory']
    for name,h in spec['sha256'].items():
        if sha(folder/name)!=h:raise ValueError('Artifact changed: '+name)
    return spec

def encode_batches(tok,ids,spans,hypotheses,key):
    """Token IDs stay local. Persist only offsets, token counts and input hashes."""
    records=[]
    for ci,(start,end) in enumerate(spans):
        for label,hyp in (hypotheses if key=='bart' else [(None,None)]):
            built=tok.build_inputs_with_special_tokens(ids[start:end],hyp)
            if len(built)>LIMITS[key]:raise ValueError('Input overflow')
            records.append(dict(chunk_index=ci,content_start=start,content_end=end,content_tokens=end-start,
                                input_tokens=len(built),theme=label,input_ids_sha256=digest(json.dumps(built)),ids=built))
    return records

def run(key,device='cpu',batch_size=1):
    rows=frozen_sample();spec=artifacts(key)
    themes=json.loads(THEMES.read_text())
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    import torch
    import transformers
    torch.set_num_threads(4);torch.manual_seed(491)
    if device=='cpu':torch.use_deterministic_algorithms(True)
    if device=='mps' and not torch.backends.mps.is_available():raise ValueError('MPS unavailable')
    start=time.perf_counter();model,tok,labels,clean=load_model(key);model=model.to(device)
    def sync():
        if device=='mps':torch.mps.synchronize()
    sync();load_seconds=time.perf_counter()-start
    hypotheses=[(t['id'],tok.encode(themes['hypothesis_template'].format(t['label']),add_special_tokens=False)) for t in themes['themes']] if key=='bart' else []
    budget=LIMITS[key]-tok.num_special_tokens_to_add(pair=key=='bart')-(max(len(h) for _,h in hypotheses) if hypotheses else 0)
    fingerprint=dict(version=VERSION,runner_sha256=sha(Path(__file__)),core_sha256=sha(ROOT/'src/classifier_panel_core.py'),
                     themes_sha256=sha(THEMES),sample_sha256=sha(REPORTS/'lyriclens_sample.csv'),model=key,
                     artifact_digest=digest(json.dumps(spec,sort_keys=True)),device=device,batch_size=batch_size,content_budget=budget,
                     torch=torch.__version__,transformers=transformers.__version__)
    journal=WORK/'runs'/key;journal.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter();processed=0
    for index,row in enumerate(rows):
        path=journal/(row['song_id']+'.json')
        if path.exists():
            saved=json.loads(path.read_text())
            if saved['fingerprint']!=fingerprint or saved['lyrics_sha256']!=row['lyrics_sha256']:raise ValueError('Resume implementation/input mismatch')
            continue
        started_song=time.perf_counter()
        text=(ROOT/'data/lyrics'/f"{row['song_id']}.txt").read_text()
        normalized=clean(text)
        if not normalized.strip():raise ValueError('Empty input')
        ids=tok.encode(normalized,add_special_tokens=False,truncation=False,verbose=False)
        spans=chunk_ranges(len(ids),budget)
        entries=encode_batches(tok,ids,spans,hypotheses,key)
        gpu_peak=0
        for offset in range(0,len(entries),batch_size):
            batch=entries[offset:offset+batch_size]
            pad=LIMITS[key] if key=='lyriclens' else max(len(r['ids']) for r in batch)
            encoded={'input_ids':torch.tensor([r['ids']+[tok.pad_token_id]*(pad-len(r['ids'])) for r in batch],device=device),
                     'attention_mask':torch.tensor([[1]*len(r['ids'])+[0]*(pad-len(r['ids'])) for r in batch],device=device)}
            if key=='lyriclens':
                encoded['global_attention_mask']=torch.zeros_like(encoded['input_ids']);encoded['global_attention_mask'][:,0]=1
            with torch.no_grad():output=model(**encoded).logits
            sync()
            if device=='mps':gpu_peak=max(gpu_peak,torch.mps.driver_allocated_memory())
            logits=output.detach().cpu().tolist()
            for entry,logit in zip(batch,logits):
                entry.pop('ids')
                entry['logits']=logit
                if key=='bart':
                    entry['nli_softmax']=softmax(logit)
                    entry['scores']={entry['theme']:bart_score(logit)}
                else:
                    values=torch.softmax(torch.tensor(logit),dim=-1).tolist() if key=='sentiment' else torch.sigmoid(torch.tensor(logit)).tolist()
                    entry['raw_activated_outputs']=values
                    entry['scores']=dict(zip(labels,values[:len(labels)]))
        elapsed=time.perf_counter()-started_song
        scores={}
        for label in labels:
            selected=[r for r in entries if label in r['scores']]
            scores[label]=aggregate([r['scores'][label] for r in selected],[r['content_tokens'] for r in selected])
        result=dict(song_id=row['song_id'],status='success',lyrics_sha256=row['lyrics_sha256'],normalized_sha256=digest(normalized),
                    source_words=len(text.split()),normalized_words=len(normalized.split()),content_token_count=len(ids),chunk_count=len(spans),
                    content_budget=budget,labels=labels,fingerprint=fingerprint,seconds=elapsed,chunks=entries,aggregates=scores,
                    peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,gpu_driver_bytes=gpu_peak)
        save_json(path,result);processed+=1
        if (index+1)%10==0:print(key,index+1,'/200',f'{time.perf_counter()-started:.1f}s this invocation',flush=True)
    # Validate every complete journal before publishing numeric-only artifacts.
    results=[json.loads((journal/(r['song_id']+'.json')).read_text()) for r in rows]
    if any(r['fingerprint']!=fingerprint or r['status']!='success' for r in results):raise ValueError('Mixed/incomplete run')
    song_rows=[];chunk_rows=[]
    for result in results:
        song=dict(song_id=result['song_id'],status=result['status'],model=key,classifier_version=VERSION,content_token_count=result['content_token_count'],
                  chunk_count=result['chunk_count'],content_budget=budget,source_words=result['source_words'],normalized_words=result['normalized_words'],
                  lyrics_sha256=result['lyrics_sha256'],normalized_sha256=result['normalized_sha256'])
        for label,values in result['aggregates'].items():
            for agg,v in values.items():song[f'{label}__{agg}']=v
        song_rows.append(song)
        chunk_rows.extend(dict(song_id=result['song_id'],**r) for r in result['chunks'])
    OUT.mkdir(exist_ok=True)
    write_csv(OUT/(key+'_songs.csv'),song_rows)
    rawpath=OUT/(key+'_chunks.jsonl');tmp=rawpath.with_suffix('.tmp')
    tmp.write_text(''.join(json.dumps(r,sort_keys=True,allow_nan=False)+'\n' for r in chunk_rows));tmp.replace(rawpath)
    info=dict(fingerprint=fingerprint,labels=labels,status='complete',successful=200,failed=0,load_seconds=load_seconds,
              inference_seconds=sum(r['seconds'] for r in results),seconds_per_song=sum(r['seconds'] for r in results)/200,
              model_parameters=sum(p.numel() for p in model.parameters()),content_chunks=sum(r['chunk_count'] for r in results),
              model_input_pairs=len(chunk_rows),peak_rss_bytes=max(r['peak_rss_bytes'] for r in results),gpu_driver_bytes=max(r['gpu_driver_bytes'] for r in results),
              python=platform.python_version(),machine=platform.machine(),song_sha256=sha(OUT/(key+'_songs.csv')),chunks_sha256=sha(rawpath),
              newly_processed=processed,load_excluded_from_inference=True)
    save_json(OUT/(key+'_run.json'),info)
    print(json.dumps(info,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model',choices=MODELS)
    parser.add_argument('--device',choices=['cpu','mps'],default='cpu')
    parser.add_argument('--batch-size',type=int,default=1)
    args=parser.parse_args()
    if not 1<=args.batch_size<=8:parser.error('Pilot batch size must be 1–8')
    run(args.model,args.device,args.batch_size)
