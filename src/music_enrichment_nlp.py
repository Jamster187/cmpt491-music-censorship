"""Pinned local linguistic/semantic diagnostics with a bounded benchmark and cache."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import sqlite3
import time

os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['TOKENIZERS_PARALLELISM']='false'

import numpy as np
import pandas as pd
import spacy
import torch
from transformers import AutoTokenizer, AutoModel
from wordfreq import zipf_frequency

from enrichment_common import ROOT, LOCAL, MUSIC, sha, write_json, write_csv
from music_enrichment_features import token_lines

POS=['ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART','PRON','PROPN','SCONJ','VERB','X','SYM']
CONFIG={'version':'music-enrichment-nlp-v2.1','spacy_model':'en_core_web_sm','spacy_version':'3.8.0',
        'embedding_model':'sentence-transformers/all-MiniLM-L6-v2','wordpiece_chunk_length':254,
        'maximum_chunks_per_song':64,'pooling':'attention-mask token mean including special tokens, normalized chunk vectors, lexical-token-count weighted mean, L2 song normalization',
        'device':'cpu','threads':4,'benchmark_songs':64,'wall_budget_seconds':5400,
        'scope':'Retrospective English-trained diagnostic; not validated English-language identification or historical availability',
        'wordfreq':'3.1.1 English large list; positive-frequency words only; explicit coverage'}


def model_bundle():
    torch.set_num_threads(4);torch.manual_seed(491);torch.use_deterministic_algorithms(True)
    directory=LOCAL/'models/all-MiniLM-L6-v2'
    tokenizer=AutoTokenizer.from_pretrained(directory,local_files_only=True,trust_remote_code=False)
    model=AutoModel.from_pretrained(directory,local_files_only=True,trust_remote_code=False).eval()
    nlp=spacy.load('en_core_web_sm')
    if nlp.meta['version']!='3.8.0':raise ValueError('Unexpected spaCy model version')
    return nlp,tokenizer,model


def analyze(text,nlp,tokenizer,model):
    lines=token_lines(text);words=[w for line in lines for w in line]
    normalized='\n'.join(' '.join(line) for line in lines)
    doc=nlp(normalized);lexical=[t for t in doc if not t.is_space and not t.is_punct]
    if not lexical:return {},None
    counts=Counter(t.pos_ for t in lexical);n=len(lexical)
    r={f'lyric_pos_{p.lower()}_share':counts[p]/n for p in POS}
    r['lyric_nlp_token_count']=n
    r['lyric_pos_other_share']=sum(c for p,c in counts.items() if p not in POS)/n
    sentences=[sum(not t.is_space and not t.is_punct for t in sent) for sent in doc.sents]
    r['lyric_parser_sentence_length_mean']=float(np.mean([x for x in sentences if x]))
    r['lyric_dependency_depth_mean']=float(np.mean([sum(1 for _ in t.ancestors) for t in lexical]))
    verbs=[t for t in lexical if t.pos_ in {'VERB','AUX'}]
    past=sum('Past' in t.morph.get('Tense') for t in verbs);present=sum('Pres' in t.morph.get('Tense') for t in verbs)
    r['lyric_verb_past_share']=past/len(verbs) if verbs else None
    r['lyric_verb_present_share']=present/len(verbs) if verbs else None
    entity_tokens={t.i for entity in doc.ents for t in entity if not t.is_space and not t.is_punct}
    geo_tokens={t.i for entity in doc.ents if entity.label_ in {'GPE','LOC'} for t in entity if not t.is_space and not t.is_punct}
    r['lyric_named_entity_token_share']=len(entity_tokens)/n
    r['lyric_geographic_entity_token_share']=len(geo_tokens)/n
    frequencies=[zipf_frequency(w,'en',wordlist='large') for w in words]
    supported=[x for x in frequencies if x>0]
    r['lyric_modern_wordfreq_coverage']=len(supported)/len(words)
    r['lyric_modern_wordfreq_mean']=float(np.mean(supported)) if supported else None
    ids=tokenizer(normalized,add_special_tokens=False,truncation=False)['input_ids']
    chunks=[ids[i:i+254] for i in range(0,len(ids),254)]
    r['lyric_semantic_wordpieces']=len(ids);r['lyric_semantic_chunks']=len(chunks)
    if len(chunks)>64:
        r['lyric_semantic_status']='resource_limit_no_truncation';return r,None
    vecs=[];weights=[]
    for start in range(0,len(chunks),8):
        batch=chunks[start:start+8]
        encoded=[tokenizer.prepare_for_model(x,add_special_tokens=True,return_attention_mask=True) for x in batch]
        inputs=tokenizer.pad(encoded,padding=True,return_tensors='pt')
        with torch.inference_mode():
            hidden=model(**inputs).last_hidden_state
            mask=inputs['attention_mask'].unsqueeze(-1).to(hidden.dtype)
            mean=(hidden*mask).sum(dim=1)/mask.sum(dim=1)
            vectors=torch.nn.functional.normalize(mean,p=2,dim=1).cpu().numpy()
        vecs.extend(vectors);weights.extend(map(len,batch))
    vector=np.average(np.array(vecs,dtype=np.float64),axis=0,weights=weights)
    vector=vector/np.linalg.norm(vector)
    r['lyric_semantic_status']='complete_all_chunks'
    return r,vector.astype('<f8')


def protocol():
    versions={name:importlib.metadata.version(name) for name in ['spacy','torch','transformers','wordfreq','numpy','pandas']}
    models={str(p.relative_to(LOCAL)):sha(p) for p in sorted((LOCAL/'models/all-MiniLM-L6-v2').rglob('*')) if p.is_file() and '.cache' not in p.parts}
    models['en_core_web_sm']=importlib.metadata.version('en-core-web-sm')
    return {'config':CONFIG,'versions':versions,'model_hashes':models,'code_sha256':sha(__file__),
            'text_provenance_sha256':sha(ROOT/'data/experiments/feature_expansion_v1/lyric_input_provenance.json')}


def run(benchmark_only=False):
    start=time.monotonic();spec=protocol();key=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()
    directory=LOCAL/'nlp'/key;directory.mkdir(parents=True,exist_ok=True);write_json(directory/'protocol.json',spec)
    write_json(LOCAL/'nlp/active.json',{'key':key,'protocol':spec})
    conn=sqlite3.connect(directory/'results.db');conn.execute('CREATE TABLE IF NOT EXISTS results(song_id TEXT PRIMARY KEY,input_sha TEXT,features TEXT,embedding BLOB)')
    provenance=json.loads((ROOT/'data/experiments/feature_expansion_v1/lyric_input_provenance.json').read_text())
    provenance=sorted(provenance,key=lambda r:hashlib.sha256(r['song_id'].encode()).hexdigest())
    existing={r[0]:r[1] for r in conn.execute('SELECT song_id,input_sha FROM results')}
    nlp,tokenizer,model=model_bundle();bench=[];processed=0
    for row in provenance:
        sid=row['song_id']
        if sid in existing:
            if existing[sid]!=row['sha256']:raise ValueError('Checkpoint input differs')
            continue
        path=ROOT/row['path']
        if path.is_symlink() or sha(path)!=row['sha256']:raise ValueError('Approved lyric input changed')
        tick=time.monotonic();features,vector=analyze(path.read_text(),nlp,tokenizer,model)
        conn.execute('INSERT INTO results VALUES (?,?,?,?)',(sid,row['sha256'],json.dumps(features,sort_keys=True),None if vector is None else vector.tobytes()))
        processed+=1;bench.append(time.monotonic()-tick)
        if processed==64:
            estimate=float(np.mean(bench))*len(provenance)
            audit={'sample_songs':64,'seconds':sum(bench),'projected_full_inference_seconds':estimate,'songs':len(provenance),
                'maximum_seconds':CONFIG['wall_budget_seconds'],'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'protocol_key':key,'status':'PASS' if estimate<=CONFIG['wall_budget_seconds'] else 'BUDGET_EXCEEDED'}
            write_json(MUSIC/'nlp_benchmark.json',audit);conn.commit();print(audit,flush=True)
            if benchmark_only or estimate>CONFIG['wall_budget_seconds']:break
        if processed%200==0:
            conn.commit();print('NLP',len(existing)+processed,'/',len(provenance),'seconds',round(time.monotonic()-start),flush=True)
        if time.monotonic()-start>CONFIG['wall_budget_seconds']:
            print('Wall budget reached; checkpoint retained',flush=True);break
    conn.commit();conn.close()
    write_json(directory/'execution.json',{'seconds_this_run':time.monotonic()-start,'new_songs':processed,
        'cached_before':len(existing),'planned_songs':len(provenance),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    export()


def semantic_history(weekly,study,embeddings):
    meta=study.set_index('song_id');credits=defaultdict(list);seen=set();hits=set();hit_sum=np.zeros(384);hit_n=0;rows=[]
    def distance(vector,total,n):
        norm=np.linalg.norm(total)
        return float(np.clip(1-np.dot(vector,total/norm),0,2)) if n and norm>0 else None
    for date,chart in weekly.groupby('chart_date',sort=True):
        current=chart.groupby('song_id',sort=True).weekly_rank.min();new=sorted(set(current.index)-seen)
        for sid in new:
            if sid not in embeddings:continue
            v=embeddings[sid];artist=meta.loc[sid,'artist'];prior=credits[artist]
            rows.append({'song_id':sid,'lyric_semantic_novelty_prior_hits':distance(v,hit_sum,hit_n),
                'lyric_semantic_prior_hit_reference_n':hit_n,
                'lyric_semantic_drift_from_credit':distance(v,np.sum(prior,axis=0),len(prior)) if prior else None,
                'lyric_semantic_prior_credit_reference_n':len(prior)})
        for sid in new:
            if sid in embeddings:credits[meta.loc[sid,'artist']].append(embeddings[sid])
        for sid,rank in current.items():
            if rank<=10 and sid not in hits and sid in embeddings:
                hits.add(sid);hit_sum+=embeddings[sid];hit_n+=1
        seen.update(new)
    return pd.DataFrame(rows)


def export():
    active=json.loads((LOCAL/'nlp/active.json').read_text());directory=LOCAL/'nlp'/active['key']
    conn=sqlite3.connect('file:'+str((directory/'results.db').resolve())+'?mode=ro',uri=True)
    records=[];embeddings={}
    for sid,raw,blob in conn.execute('SELECT song_id,features,embedding FROM results ORDER BY song_id'):
        records.append(dict(song_id=sid,**json.loads(raw)))
        if blob is not None:embeddings[sid]=np.frombuffer(blob,dtype='<f8').copy()
    conn.close()
    study=pd.read_csv(ROOT/'data/public/songs.csv')
    weekly=pd.read_csv(ROOT/'data/public/master_weekly.csv.xz',usecols=['song_id','chart_date','weekly_rank'])
    history=semantic_history(weekly,study,embeddings)
    frame=pd.DataFrame(records).merge(history,on='song_id',how='left',validate='one_to_one')
    write_csv(LOCAL/'nlp_features.csv.xz',frame)
    write_json(MUSIC/'nlp_summary.json',{'completed_songs':len(records),'complete_embeddings':len(embeddings),'protocol':active['protocol'],
        'embedding_storage':'private local checkpoint only; raw vectors not distributed','feature_columns':list(frame.columns),
        'limitations':'English-trained web-text models are diagnostic on lyrics; modern model training may contain historical songs. Prefix restriction does not imply genuine past availability.'})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['benchmark','run','export']);a=parser.parse_args()
    export() if a.action=='export' else run(a.action=='benchmark')
