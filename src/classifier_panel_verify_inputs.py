"""Retokenize the local 200 lyrics and verify every public chunk input hash, without inference."""
import json
import os
from collections import defaultdict
from classifier_panel import ROOT,REPORTS,OUT,WORK,THEMES,MODELS,LIMITS,ll_preprocessor
from classifier_panel_core import chunk_ranges
from detoxify_evaluation import frozen_sample
from lyriclens_evaluation import digest

def main():
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    from transformers import AutoTokenizer,LongformerTokenizer,RobertaTokenizer
    sample=frozen_sample();themes=json.loads(THEMES.read_text())
    checked=0
    for m in MODELS:
        if m=='lyriclens':
            tokenizer=LongformerTokenizer.from_pretrained(ROOT/'data/experiments/lyriclens/model',local_files_only=True);clean=ll_preprocessor()
        elif m=='detoxify':
            tokenizer=RobertaTokenizer.from_pretrained(ROOT/'data/experiments/detoxify/tokenizer',local_files_only=True);clean=lambda t:t
        else:
            tokenizer=AutoTokenizer.from_pretrained(WORK/m,local_files_only=True,use_fast=False)
            clean=(lambda text:' '.join('@user' if t.startswith('@') and len(t)>1 else 'http' if t.startswith('http') else t for t in text.split(' '))) if m=='sentiment' else (lambda t:t)
        hypotheses={t['id']:tokenizer.encode(themes['hypothesis_template'].format(t['label']),add_special_tokens=False) for t in themes['themes']} if m=='bart' else {}
        budget=LIMITS[m]-tokenizer.num_special_tokens_to_add(pair=m=='bart')-(max(map(len,hypotheses.values())) if hypotheses else 0)
        raw=defaultdict(list)
        for line in (OUT/(m+'_chunks.jsonl')).read_text().splitlines():
            r=json.loads(line);raw[r['song_id']].append(r)
        for s in sample:
            text=clean((ROOT/'data/lyrics'/f"{s['song_id']}.txt").read_text())
            ids=tokenizer.encode(text,add_special_tokens=False,truncation=False,verbose=False)
            spans=chunk_ranges(len(ids),budget)
            for r in raw[s['song_id']]:
                start,end=spans[r['chunk_index']]
                if (start,end)!=(r['content_start'],r['content_end']):raise ValueError('Retokenized span mismatch')
                built=tokenizer.build_inputs_with_special_tokens(ids[start:end],hypotheses[r['theme']] if m=='bart' else None)
                if len(built)!=r['input_tokens'] or digest(json.dumps(built))!=r['input_ids_sha256']:raise ValueError('Actual model input changed')
                checked+=1
    print('Independently retokenized all 200 local lyrics for five models; verified',checked,'exact chunk/pair input hashes. No inference performed.')

if __name__=='__main__':main()
