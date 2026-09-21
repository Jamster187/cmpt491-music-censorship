"""Four offline CPU adapters. Source lyrics are read-only; no NLI model is loaded."""
import json
import os
import re
import time
from classifier_production_store import ROOT, SPEC, sha, digest, chunk_ranges
from lyriclens_evaluation import extract_definitions


def lyriclens_cleaner():
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
        failures.clear()  # An upstream swallowed failure must not poison later songs.
        result=obj.clean_and_lemmatize(text)
        if not result or failures:raise ValueError('Empty normalization/preprocessing fallback')
        return result
    return clean


class Engine:
    def __init__(self,key):
        if key not in SPEC['model_order']:raise ValueError('Unknown production model')
        os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
        import torch
        from transformers import AutoConfig,AutoTokenizer,AutoModelForSequenceClassification,LongformerTokenizer,LongformerForSequenceClassification,RobertaConfig,RobertaTokenizer,RobertaForSequenceClassification
        from safetensors.torch import load_file
        torch.set_num_threads(4);torch.manual_seed(491);torch.use_deterministic_algorithms(True)
        self.torch=torch;self.key=key;self.spec=SPEC['models'][key]
        artifact=self.spec['artifact'];folder=ROOT/artifact['local_relative_directory']
        for name,h in artifact['sha256'].items():
            if sha(folder/name)!=h:raise ValueError('Model/tokenizer artifact hash mismatch')
        self.clean=lambda text:text
        if key=='lyriclens':
            tok=LongformerTokenizer.from_pretrained(folder,local_files_only=True)
            model=LongformerForSequenceClassification(AutoConfig.from_pretrained(folder,local_files_only=True))
            model.load_state_dict(load_file(str(folder/'model.safetensors')),strict=True)
            self.clean=lyriclens_cleaner()
        elif key=='detoxify':
            tok=RobertaTokenizer.from_pretrained(folder/'tokenizer',local_files_only=True)
            model=RobertaForSequenceClassification(RobertaConfig.from_pretrained(folder/'tokenizer',num_labels=16,local_files_only=True))
            state=torch.load(folder/'toxic_debiased-c7548aa0.ckpt',map_location='cpu',weights_only=True)['state_dict']
            if not torch.equal(state.pop('roberta.embeddings.position_ids'),model.roberta.embeddings.position_ids):raise ValueError('Unexpected buffer')
            model.load_state_dict(state,strict=True)
        else:
            tok=AutoTokenizer.from_pretrained(folder,local_files_only=True,use_fast=False)
            model=AutoModelForSequenceClassification.from_pretrained(folder,local_files_only=True,weights_only=True)
            if [model.config.id2label[i].lower() for i in range(model.config.num_labels)]!=self.spec['labels']:raise ValueError('Label mismatch')
            if key=='cardiff':self.clean=lambda text:' '.join('@user' if t.startswith('@') and len(t)>1 else 'http' if t.startswith('http') else t for t in text.split(' '))
        self.model=model.eval().to('cpu');self.tok=tok
        self.budget=self.spec['window']-tok.num_special_tokens_to_add(pair=False)

    def tokenize(self,text):
        normalized=self.clean(text)
        if not normalized.strip():raise ValueError('Empty normalized lyric')
        ids=self.tok.encode(normalized,add_special_tokens=False,truncation=False,verbose=False)
        spans=chunk_ranges(len(ids),self.budget)
        return ids,spans,digest(normalized)

    def input(self,ids,start,end):
        built=self.tok.build_inputs_with_special_tokens(ids[start:end])
        if len(built)>self.spec['window']:raise ValueError('Token overflow')
        return built,digest(json.dumps(built))

    def predict(self,ids,start,end,index):
        torch=self.torch;built,h=self.input(ids,start,end)
        pad=self.spec['window'] if self.key=='lyriclens' else len(built)
        encoded={'input_ids':torch.tensor([built+[self.tok.pad_token_id]*(pad-len(built))]),
                 'attention_mask':torch.tensor([[1]*len(built)+[0]*(pad-len(built))])}
        if self.key=='lyriclens':
            encoded['global_attention_mask']=torch.zeros_like(encoded['input_ids']);encoded['global_attention_mask'][:,0]=1
        started=time.perf_counter()
        with torch.no_grad():logits=self.model(**encoded).logits[0]
        values=(torch.softmax(logits,dim=-1) if self.key=='cardiff' else torch.sigmoid(logits)).tolist()
        return dict(chunk_index=index,content_start=start,content_end=end,input_tokens=len(built),input_sha256=h,
                    logits=logits.tolist(),activated=values,scores=dict(zip(self.spec['columns'],[values[i] for i in self.spec['raw_indices']])),seconds=time.perf_counter()-started)
