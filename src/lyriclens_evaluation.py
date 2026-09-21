"""Bounded, local LyricLens evaluation. Never writes research databases/public data.

Upstream inference code is loaded from a pinned, locally inspected CC BY 4.0
source snapshot; no third-party source, checkpoint, or lyric text is redistributed.
"""
import argparse
import ast
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import sqlite3
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'data/experiments/lyriclens'
REPORTS=ROOT/'reports'
REVISION='71a40996c1021c62d12dc004cbafa3f1c5560162'
VERSION='lyriclens-evaluation-v1'
SEED='cmpt491-lyriclens-200-v1'
PERIODS=('1958–1969','1970s','1980s','1990s','2000s','2010–2019','2020–2026')
SAMPLE=REPORTS/'lyriclens_sample.csv'
SCORE_NAMES=('sexual_content_score','violence_score','explicit_language_score','substance_use_score')
# Ten expected-mild and ten expected-content sentinels, chosen before prediction.
# These are diagnostic expectations, not ground-truth labels or random estimates.
SENTINELS=(
 ('What A Wonderful World','Louis Armstrong','expected_mild'),
 ('Rainbow Connection','Kermit (Jim Henson)','expected_mild'),
 ("You've Got A Friend",'James Taylor','expected_mild'),
 ('Happy','Pharrell Williams','expected_mild'),
 ('Lean On Me','Bill Withers','expected_mild'),
 ('My Girl','The Temptations','expected_mild'),
 ('You Are The Sunshine Of My Life','Stevie Wonder','expected_mild'),
 ('ABC','Jackson 5','expected_mild'),
 ('Let It Be','The Beatles','expected_mild'),
 ('Imagine','John Lennon/Plastic Ono Band','expected_mild'),
 ('WAP','Cardi B Featuring Megan Thee Stallion','expected_content'),
 ('Anaconda','Nicki Minaj','expected_content'),
 ('Closer','Nine Inch Nails','expected_content'),
 ('Murder On My Mind','YNW Melly','expected_content'),
 ('Gin And Juice','Snoop Doggy Dogg','expected_content'),
 ('Because I Got High','Afroman','expected_content'),
 ('Smack That','Akon Featuring Eminem','expected_content'),
 ('Super Freak (Part I)','Rick James','expected_content'),
 ("Let's Get It On",'Marvin Gaye','expected_content'),
 ('The Hills','The Weeknd','expected_content'))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def digest(value):return hashlib.sha256(value.encode()).hexdigest()


def period(year):
    if not 1958<=year<=2026:raise ValueError('Year outside frozen study')
    if year<1970:return PERIODS[0]
    return PERIODS[min((year-1970)//10+1,6)]


def read_csv(path):
    with Path(path).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def write_csv(path,rows):
    if not rows:raise ValueError('Empty export')
    temp=Path(str(path)+'.tmp')
    with temp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    temp.replace(path)


def select_core(rows,quota):
    """Within-period rank halves x lyric-length thirds; rotate six seeded cells."""
    ranked=sorted(rows,key=lambda r:(int(r['best_chart_rank']),r['song_id']))
    rank_band={r['song_id']:min(1,2*i//len(ranked)) for i,r in enumerate(ranked)}
    lengths=sorted(rows,key=lambda r:(int(r['word_count']),r['song_id']))
    length_band={r['song_id']:min(2,3*i//len(lengths)) for i,r in enumerate(lengths)}
    bins=defaultdict(list)
    for r in rows:bins[(rank_band[r['song_id']],length_band[r['song_id']])].append(r)
    for group in bins.values():group.sort(key=lambda r:digest(SEED+r['song_id']))
    result=[]
    while len(result)<quota:
        progress=False
        for cell in sorted(bins):
            if bins[cell] and len(result)<quota:
                r=dict(bins[cell].pop(0));r.update(sample_component='stratified_core',
                    sampling_cell=f'rank{cell[0]}_length{cell[1]}')
                result.append(r);progress=True
        if not progress:raise ValueError('Insufficient population for sample')
    return result


def sample():
    WORK.mkdir(parents=True,exist_ok=True)
    rows=[r for r in read_csv(ROOT/'data/public/songs.csv') if r['lyrics_status']=='success']
    if len(rows)!=19372:raise ValueError('Frozen usable population changed')
    c=sqlite3.connect((ROOT/'data/processed/research.db').as_uri()+'?mode=ro',uri=True)
    hashes=dict(c.execute("SELECT song_id,lyrics_sha256 FROM lyrics_manifest WHERE lyrics_status='success'"));c.close()
    eligible=[]
    for r in rows:
        sid=r['song_id'];path=ROOT/'data/lyrics'/f'{sid}.txt'
        if sha(path)!=hashes[sid]:raise ValueError('Lyric checksum changed')
        text=path.read_text(encoding='utf-8')
        eligible.append(dict(song_id=sid,title=r['title'],artist=r['artist'],
            period=period(int(r['first_chart_date'][:4])),first_chart_date=r['first_chart_date'],
            best_chart_rank=r['best_chart_rank'],months_selected=r['months_selected'],
            word_count=len(text.split()),lyrics_sha256=hashes[sid]))
    by_identity={(r['title'],r['artist']):r for r in eligible}
    sentinels=[]
    for title,artist,kind in SENTINELS:
        r=dict(by_identity[(title,artist)]);r.update(sample_component=kind,sampling_cell='sentinel');sentinels.append(r)
    excluded={r['song_id'] for r in sentinels}
    core=[]
    for i,p in enumerate(PERIODS):
        core.extend(select_core([r for r in eligible if r['period']==p and r['song_id'] not in excluded],26 if i<5 else 25))
    result=sorted(core+sentinels,key=lambda r:(PERIODS.index(r['period']),r['sample_component'],digest(SEED+r['song_id'])))
    if len(result)!=200 or len({r['song_id'] for r in result})!=200:raise ValueError('Pilot must have exactly 200 unique songs')
    write_csv(SAMPLE,result)
    (WORK/'sample_provenance.json').write_text(json.dumps(dict(version=VERSION,seed=SEED,
        sample_sha256=sha(SAMPLE),songs_csv_sha256=sha(ROOT/'data/public/songs.csv'),
        corpus_sha256=digest(json.dumps(sorted(hashes.items()))),eligible=19372,core=180,sentinels=20),indent=2)+'\n')
    print('Sample:',dict(Counter(r['period'] for r in result)))


def validate_sample(rows):
    if len(rows)!=200 or len({r['song_id'] for r in rows})!=200:raise ValueError('Only the fixed 200-song pilot is authorized')
    if any(not re.fullmatch(r'song_[0-9a-f]{64}',r['song_id']) for r in rows):raise ValueError('Invalid song identity')
    if Counter(r['sample_component'] for r in rows)!={'stratified_core':180,'expected_mild':10,'expected_content':10}:
        raise ValueError('Sample components changed')


def extract_definitions(path,names):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    selected=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
    if {n.name for n in selected}!=set(names):raise ValueError('Upstream definitions changed')
    return compile(ast.Module(body=selected,type_ignores=[]),str(path),'exec')


def score_summary(probabilities,upstream_output):
    if len(probabilities)!=4 or any(not math.isfinite(p) or not 0<=p<=1 for p in probabilities):
        raise ValueError('Invalid model probabilities')
    result=dict(zip(SCORE_NAMES,(probabilities[0],probabilities[1],probabilities[3],probabilities[2])))
    result.update(CSI=100*statistics.mean(probabilities),app_CSI=upstream_output['severity'],
                  MCR=upstream_output['mcr_rating'])
    return result


def run():
    # No sample-size/all-corpus flag and no database-writing code.
    rows=read_csv(SAMPLE);validate_sample(rows)
    provenance=json.loads((WORK/'sample_provenance.json').read_text())
    if sha(SAMPLE)!=provenance['sample_sha256']:raise ValueError('Sample changed')
    setup=json.loads((WORK/'setup_provenance.json').read_text())
    for group in ('source','model'):
        for name,h in setup[group].items():
            if sha(WORK/group/name)!=h:raise ValueError('Upstream artifact changed')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    os.environ['NLTK_DATA']=str(WORK/'nltk_data')
    import numpy as np
    import pandas as pd
    import nltk
    import torch
    from transformers import AutoConfig,LongformerTokenizer,LongformerForSequenceClassification
    from safetensors.torch import load_file
    nltk.data.path[:]=[str(WORK/'nltk_data')]
    # Make upstream silent fallbacks fatal during this evaluation.
    from nltk.stem import WordNetLemmatizer
    nltk.word_tokenize('A simple test.');nltk.pos_tag(['testing']);WordNetLemmatizer().lemmatize('testing','v')
    class SilentUI:
        def warning(self,*args,**kwargs):raise RuntimeError('Upstream preprocessing warning')
    fallback_errors=[]
    def monitored(fn):
        def call(*args,**kwargs):
            try:return fn(*args,**kwargs)
            except Exception:
                fallback_errors.append(fn.__name__);raise
        return call
    nltk.word_tokenize=monitored(nltk.word_tokenize);nltk.pos_tag=monitored(nltk.pos_tag)
    WordNetLemmatizer.lemmatize=monitored(WordNetLemmatizer.lemmatize)
    env={'pd':pd,'np':np,'nltk':nltk,'torch':torch,'re':re,'st':SilentUI()}
    exec(extract_definitions(WORK/'source/music_content_rating.py',{'MusicContentRatingSystem'}),env)
    exec(extract_definitions(WORK/'source/app.py',{'LongformerPreprocessor','analyze_lyrics_longformer',
         'calculate_content_severity','classify_lyrics'}),env)
    torch.set_num_threads(4);torch.manual_seed(491);torch.use_deterministic_algorithms(True)
    start=time.perf_counter()
    modeldir=WORK/'model'
    tokenizer=LongformerTokenizer.from_pretrained(modeldir,local_files_only=True)
    model=LongformerForSequenceClassification(AutoConfig.from_pretrained(modeldir,local_files_only=True))
    weights=load_file(str(modeldir/'model.safetensors'));model.load_state_dict(weights,strict=True);del weights
    model=model.cpu().eval();preprocessor=env['LongformerPreprocessor']()
    load_seconds=time.perf_counter()-start
    capture=[]
    model.register_forward_hook(lambda module,args,output:capture.append(output.logits.detach().cpu().tolist()[0]))
    rawpath=WORK/'raw_predictions.jsonl'
    if rawpath.exists():raise ValueError('Run evidence already exists; preserve it before a separately versioned rerun')
    results=[]
    with rawpath.open('x',encoding='utf-8') as raw:
        for i,r in enumerate(rows):
            path=ROOT/'data/lyrics'/f"{r['song_id']}.txt"
            if sha(path)!=r['lyrics_sha256']:raise ValueError('Pilot lyric changed')
            text=path.read_text(encoding='utf-8');start=time.perf_counter()
            cleaned=preprocessor.clean_and_lemmatize(text)
            if not cleaned:raise ValueError('Empty preprocessed input; do not impute zero scores')
            token_count=len(tokenizer.encode(cleaned,truncation=False))
            capture.clear()
            prediction=env['classify_lyrics'](text,tokenizer,model,preprocessor)
            elapsed=time.perf_counter()-start
            if fallback_errors:raise ValueError('Silent upstream preprocessing fallback detected')
            if len(capture)!=1:raise ValueError('Missing model forward pass')
            probabilities=prediction['raw_probabilities']
            if len(probabilities)!=4 or any(not math.isfinite(p) or not 0<=p<=1 for p in probabilities):
                raise ValueError('Invalid model probabilities')
            record=dict(song_id=r['song_id'],logits=capture[0],raw_probabilities=probabilities,
                upstream_output=prediction,elapsed_seconds=elapsed,token_count=token_count,
                cleaned_sha256=digest(cleaned),lyrics_sha256=r['lyrics_sha256'])
            # Raw model values are durably preserved before exporting derived summaries.
            raw.write(json.dumps(record,allow_nan=False)+'\n');raw.flush()
            out=dict(r)
            out.update(score_summary(probabilities,prediction))
            out.update(token_count=token_count,truncated=int(token_count>1024),
                inference_seconds=elapsed,inference_version=VERSION,model_commit=REVISION,
                model_sha256=setup['model']['model.safetensors'])
            results.append(out)
            if (i+1)%10==0:print('Predicted',i+1,'/200',flush=True)
    write_csv(REPORTS/'lyriclens_predictions.csv',results)
    runinfo=dict(version=VERSION,model_commit=REVISION,sample_sha256=sha(SAMPLE),
        raw_outputs_sha256=sha(rawpath),predictions_sha256=sha(REPORTS/'lyriclens_predictions.csv'),
        python=platform.python_version(),architecture=platform.machine(),torch=torch.__version__,
        wrapper_sha256=sha(Path(__file__)),preprocessing_fallbacks=len(fallback_errors),
        cpu_threads=torch.get_num_threads(),cuda_available=torch.cuda.is_available(),
        mps_available=torch.backends.mps.is_available(),device='cpu',dtype='float32',
        model_parameters=sum(p.numel() for p in model.parameters()),load_seconds=load_seconds,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        inference_seconds=sum(r['inference_seconds'] for r in results),predictions=len(results))
    (WORK/'run_provenance.json').write_text(json.dumps(runinfo,indent=2)+'\n')
    print(json.dumps(runinfo,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('sample','run'))
    args=parser.parse_args()
    {'sample':sample,'run':run}[args.command]()
