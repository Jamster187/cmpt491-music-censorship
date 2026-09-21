"""Read-only reconciliation of the bounded LyricLens experiment and corpus."""
import json
import math
import sqlite3
from collections import Counter
from lyriclens_evaluation import ROOT,WORK,REPORTS,SAMPLE,sha,digest,read_csv,validate_sample,score_summary
from lyriclens_diagnostics import select_review
from public_dataset import public_cell


def validate():
    sample=read_csv(SAMPLE);validate_sample(sample)
    run=json.loads((WORK/'run_provenance.json').read_text())
    source=json.loads((WORK/'sample_provenance.json').read_text())
    if sha(SAMPLE)!=source['sample_sha256'] or sha(SAMPLE)!=run['sample_sha256']:raise ValueError('Sample changed')
    if sha(ROOT/'src/lyriclens_evaluation.py')!=run['wrapper_sha256']:raise ValueError('Inference implementation changed')
    pins=json.loads((REPORTS/'lyriclens_artifacts.json').read_text())
    for group in ('source','model','nltk'):
        folder=WORK/('nltk_data' if group=='nltk' else group)
        for name,h in pins[group].items():
            if sha(folder/name)!=h:raise ValueError('Artifact changed')
    rawpath=WORK/'raw_predictions.jsonl'
    raw=[json.loads(line) for line in rawpath.read_text().splitlines()]
    predictions=read_csv(REPORTS/'lyriclens_predictions.csv')
    if len(raw)!=200 or len(predictions)!=200:raise ValueError('Not exactly 200 predictions')
    if sha(rawpath)!=run['raw_outputs_sha256'] or sha(REPORTS/'lyriclens_predictions.csv')!=run['predictions_sha256']:
        raise ValueError('Prediction evidence changed')
    for a,b,c in zip(sample,raw,predictions):
        if a['song_id']!=b['song_id'] or a['song_id']!=c['song_id']:raise ValueError('Prediction identity/order changed')
        if any(c[k]!=v for k,v in a.items()):raise ValueError('Sample metadata changed')
        if sha(ROOT/'data/lyrics'/f"{a['song_id']}.txt")!=a['lyrics_sha256']:raise ValueError('Lyric changed')
        probs=b['raw_probabilities'];logits=b['logits']
        if len(logits)!=4 or any(not math.isfinite(x) for x in logits):raise ValueError('Invalid logits')
        if any(abs(1/(1+math.exp(-x))-p)>1e-7 for x,p in zip(logits,probs)):raise ValueError('Sigmoid mismatch')
        if probs!=b['upstream_output']['raw_probabilities']:raise ValueError('Raw probability changed')
        for k,v in score_summary(probs,b['upstream_output']).items():
            if c[k]!=str(v):raise ValueError('Score transformation changed')
        scaled=[max(0,2*p-1) for p in probs]
        if not math.isclose(sum(scaled)*25,float(c['app_CSI']),abs_tol=1e-7):raise ValueError('App CSI mismatch')
        maximum=max(scaled)
        rating=('M-AO' if maximum>.95 or sum(p>.85 for p in scaled)>=2 else
                'M-E' if maximum<=.05 else 'M-P' if maximum<=.40 else 'M-T' if maximum<=.70 else 'M-R')
        if rating!=c['MCR']:raise ValueError('MCR mapping changed')
        for v in c.values():public_cell(v)
    public=json.loads((ROOT/'data/public/manifest.json').read_text())
    for name,spec in public['files'].items():
        if sha(ROOT/'data/public'/name)!=spec['sha256']:raise ValueError('Public dataset changed')
    if sha(ROOT/'data/processed/research.db')!=public['research_database_sha256']:raise ValueError('Research database changed')
    c=sqlite3.connect((ROOT/'data/processed/research.db').as_uri()+'?mode=ro',uri=True)
    hashes=dict(c.execute("SELECT song_id,lyrics_sha256 FROM lyrics_manifest WHERE lyrics_status='success'"));c.close()
    if len(hashes)!=19372 or digest(json.dumps(sorted(hashes.items())))!=source['corpus_sha256']:raise ValueError('Corpus manifest changed')
    files=list((ROOT/'data/lyrics').glob('*.txt'))
    if {p.stem for p in files}!=set(hashes):raise ValueError('Local corpus file set changed')
    for p in files:
        if sha(p)!=hashes[p.stem]:raise ValueError('Local lyric file changed')
    review=read_csv(REPORTS/'lyriclens_review.csv')
    if len(review)!=47 or {r['song_id'] for r in review}!={r['song_id'] for r in select_review(predictions)}:
        raise ValueError('Review selection changed')
    if run['preprocessing_fallbacks']!=0:raise ValueError('Preprocessing fallback')
    print('Validated: 200 predictions, 47 reviews, all 19,372 unchanged lyric files, unchanged public exports/research.db, pinned artifacts and score formulas.')

if __name__=='__main__':validate()
