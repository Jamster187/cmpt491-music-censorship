"""Replay five existing pilot inputs on CPU and Apple MPS; never score new songs."""
import json
import os
import re
import time
from lyriclens_evaluation import WORK,ROOT,REPORTS,extract_definitions,read_csv,sha,digest


def main():
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    os.environ['NLTK_DATA']=str(WORK/'nltk_data')
    import torch,nltk,numpy as np,pandas as pd
    from transformers import LongformerTokenizer,LongformerForSequenceClassification,AutoConfig
    from safetensors.torch import load_file
    torch.set_num_threads(4);torch.use_deterministic_algorithms(True)
    nltk.data.path[:]=[str(WORK/'nltk_data')]
    class UI:
        def warning(self,*a,**kw):raise ValueError('Preprocessor warning')
    env=dict(nltk=nltk,re=re,pd=pd,np=np,st=UI())
    exec(extract_definitions(WORK/'source/app.py',{'LongformerPreprocessor'}),env)
    pre=env['LongformerPreprocessor']()
    tokenizer=LongformerTokenizer.from_pretrained(WORK/'model',local_files_only=True)
    model=LongformerForSequenceClassification(AutoConfig.from_pretrained(WORK/'model',local_files_only=True))
    weights=load_file(str(WORK/'model/model.safetensors'));model.load_state_dict(weights,strict=True);del weights
    model.eval()
    rows=sorted(read_csv(REPORTS/'lyriclens_predictions.csv'),key=lambda r:(int(r['token_count']),r['song_id']))
    if len(rows)!=200:raise ValueError('Missing bounded pilot')
    chosen=[rows[i] for i in (0,49,99,149,199)];encodings=[]
    for r in chosen:
        p=ROOT/'data/lyrics'/f"{r['song_id']}.txt"
        if sha(p)!=r['lyrics_sha256']:raise ValueError('Changed lyric')
        text=pre.clean_and_lemmatize(p.read_text())
        enc=tokenizer(text,max_length=1024,truncation=True,padding='max_length',return_tensors='pt')
        enc['global_attention_mask']=torch.zeros_like(enc['input_ids']);enc['global_attention_mask'][:,0]=1
        encodings.append(enc)
    result=dict(song_ids=[r['song_id'] for r in chosen],devices={})
    for device in ('cpu','mps'):
        if device=='mps' and not torch.backends.mps.is_available():continue
        try:
            model.to(device)
            inputs=[{k:v.to(device) for k,v in enc.items()} for enc in encodings]
            def sync():
                if device=='mps':torch.mps.synchronize()
            with torch.no_grad():
                start=time.perf_counter();model(**inputs[0]);sync();warm=time.perf_counter()-start
                outputs=[];timings=[]
                for enc in inputs:
                    sync();start=time.perf_counter();out=model(**enc).logits;sync()
                    timings.append(time.perf_counter()-start)
                    outputs.append(torch.sigmoid(out).cpu().tolist()[0])
            result['devices'][device]=dict(warmup_seconds=warm,forward_seconds=timings,probabilities=outputs)
        except Exception as e:
            # Record only exception type; no lyric-containing exception strings.
            result['devices'][device]=dict(error_type=type(e).__name__)
    if all('probabilities' in result['devices'].get(d,{}) for d in ('cpu','mps')):
        result['max_probability_delta']=max(abs(a-b) for x,y in zip(result['devices']['cpu']['probabilities'],result['devices']['mps']['probabilities']) for a,b in zip(x,y))
    original=json.loads((WORK/'run_provenance.json').read_text())
    raw={r['song_id']:r for r in (json.loads(line) for line in (WORK/'raw_predictions.jsonl').read_text().splitlines())}
    result['cpu_repeat_max_delta']=max(abs(a-b) for r,values in zip(chosen,result['devices']['cpu']['probabilities']) for a,b in zip(values,raw[r['song_id']]['raw_probabilities']))
    result['benchmark_code_sha256']=sha(__file__)
    (WORK/'benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
