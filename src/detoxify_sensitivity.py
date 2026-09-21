"""Eight fixed pilot songs: prefix/tail and repetition diagnostics, never new songs."""
import json
import os
import time
from detoxify_evaluation import WORK, REPORTS, LABELS, frozen_sample, sha
from lyriclens_evaluation import read_csv, write_csv

TITLES = ('Foolish Heart','Cry Just A Little','How Country Feels','Because I Got High',
          'Murder On My Mind','Smack That','Overnight Celebrity','Survivor')

def main():
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    import torch
    from transformers import RobertaConfig, RobertaTokenizer, RobertaForSequenceClassification
    torch.set_num_threads(4)
    pins=json.loads((REPORTS/'detoxify_artifacts.json').read_text())
    checkpoint=WORK/'toxic_debiased-c7548aa0.ckpt'
    if sha(checkpoint)!=pins['checkpoint_sha256']:raise ValueError('Checkpoint changed')
    model=RobertaForSequenceClassification(RobertaConfig.from_pretrained(WORK/'tokenizer',num_labels=16,local_files_only=True))
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)['state_dict']
    if not torch.equal(state.pop('roberta.embeddings.position_ids'),model.roberta.embeddings.position_ids):raise ValueError('Legacy buffer changed')
    model.load_state_dict(state,strict=True);del state;model.eval()
    tokenizer=RobertaTokenizer.from_pretrained(WORK/'tokenizer',local_files_only=True)
    rows=[r for r in frozen_sample() if r['title'] in TITLES]
    if len(rows)!=8:raise ValueError('Fixed eight-song sensitivity set changed')
    baseline={r['song_id']:r for r in read_csv(REPORTS/'detoxify_predictions.csv')}
    results=[]
    for row in rows:
        text=(WORK.parents[1]/'lyrics'/f"{row['song_id']}.txt").read_text()
        tokens=tokenizer.encode(text,add_special_tokens=False,truncation=False,verbose=False)
        unique='\n'.join(dict.fromkeys(line for line in text.splitlines() if line.strip()))
        for variant in ('original_replay','unique_lines','tail_510_tokens'):
            if variant=='tail_510_tokens':
                inputs={'input_ids':torch.tensor([tokenizer.build_inputs_with_special_tokens(tokens[-510:])])}
                inputs['attention_mask']=torch.ones_like(inputs['input_ids'])
            else:inputs=tokenizer(text if variant=='original_replay' else unique,return_tensors='pt',truncation=True,padding=True)
            start=time.perf_counter()
            with torch.no_grad():scores=torch.sigmoid(model(**inputs).logits)[0].tolist()
            elapsed=time.perf_counter()-start
            if variant=='original_replay' and any(abs(scores[i]-float(baseline[row['song_id']][k]))>1e-6 for i,k in enumerate(LABELS)):
                raise ValueError('Original replay mismatch')
            results.append(dict(song_id=row['song_id'],title=row['title'],artist=row['artist'],variant=variant,
                                input_tokens=inputs['input_ids'].shape[1],**dict(zip(LABELS,scores[:7])),inference_seconds=elapsed))
    write_csv(REPORTS/'detoxify_sensitivity.csv',results)
    print('Eight original replays agree within 1e-6; 16 diagnostic variants saved separately. No corpus files changed.')

if __name__=='__main__':main()
