"""CPU/MPS BART comparison on one frozen pilot song, no new identities."""
import os
import json
import time
from classifier_panel import WORK,OUT,THEMES,load_model,artifacts,save_json,encode_batches,LIMITS
from classifier_panel_core import chunk_ranges
from detoxify_evaluation import frozen_sample
from lyriclens_evaluation import ROOT

def main():
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    import torch
    torch.set_num_threads(4);torch.manual_seed(491)
    artifacts('bart');model,tok,labels,clean=load_model('bart')
    row=frozen_sample()[0];text=(ROOT/'data/lyrics'/f"{row['song_id']}.txt").read_text()
    themes=json.loads(THEMES.read_text())
    hypotheses=[(t['id'],tok.encode(themes['hypothesis_template'].format(t['label']),add_special_tokens=False)) for t in themes['themes']]
    budget=1024-tok.num_special_tokens_to_add(pair=True)-max(len(h) for _,h in hypotheses)
    ids=tok.encode(text,add_special_tokens=False,truncation=False)
    entries=encode_batches(tok,ids,chunk_ranges(len(ids),budget),hypotheses,'bart')[:4]
    results=[];reference=None
    for device in ['cpu']+(['mps'] if torch.backends.mps.is_available() else []):
        model=model.to(device).eval();pad=max(len(e['ids']) for e in entries)
        inputs={'input_ids':torch.tensor([e['ids']+[tok.pad_token_id]*(pad-len(e['ids'])) for e in entries],device=device),
                'attention_mask':torch.tensor([[1]*len(e['ids'])+[0]*(pad-len(e['ids'])) for e in entries],device=device)}
        times=[];logits=[]
        for i in range(3):
            if device=='mps':torch.mps.synchronize()
            start=time.perf_counter()
            with torch.no_grad():out=model(**inputs).logits
            if device=='mps':torch.mps.synchronize()
            times.append(time.perf_counter()-start);logits=out.cpu().tolist()
        if reference is None:reference=logits
        results.append(dict(device=device,batch_size=4,input_tokens=pad,seconds=times,
                            max_absolute_cpu_logit_difference=max(abs(x-y) for a,b in zip(logits,reference) for x,y in zip(a,b)),
                            gpu_driver_bytes=torch.mps.driver_allocated_memory() if device=='mps' else 0))
    save_json(OUT/'bart_device_benchmark.json',dict(song_id=row['song_id'],scope='First four frozen themes on first frozen sample song, three replays per device; speed selection only.',results=results))
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
