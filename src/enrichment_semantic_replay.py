"""Bounded local semantic replay and independent temporal-prefix fixture."""
from __future__ import annotations
import json
import sqlite3
import numpy as np
import pandas as pd
from enrichment_common import ROOT,LOCAL,MUSIC,sha,write_json


def verify():
    from music_enrichment_nlp import model_bundle,analyze,semantic_history,protocol
    active=json.loads((LOCAL/'nlp/active.json').read_text())
    if protocol()!=active['protocol']:raise ValueError('NLP runtime/model/source protocol changed')
    conn=sqlite3.connect('file:'+str(LOCAL/'nlp'/active['key']/'results.db')+'?mode=ro',uri=True)
    sources={r['song_id']:r for r in json.loads((ROOT/'data/experiments/feature_expansion_v1/lyric_input_provenance.json').read_text())}
    nlp,tokenizer,model=model_bundle();count=0
    for sid,input_sha,features,blob in conn.execute('SELECT song_id,input_sha,features,embedding FROM results ORDER BY song_id LIMIT 8'):
        row=sources[sid];path=ROOT/row['path']
        if sha(path)!=row['sha256'] or input_sha!=row['sha256']:raise ValueError('Input changed')
        replay,vector=analyze(path.read_text(),nlp,tokenizer,model)
        if replay!=json.loads(features):raise ValueError('Linguistic scalar replay differs')
        np.testing.assert_allclose(vector,np.frombuffer(blob,dtype='<f8'),atol=1e-12,rtol=0);count+=1
    conn.close()
    x=np.zeros(384);x[0]=1;y=np.zeros(384);y[1]=1
    study=pd.DataFrame({'song_id':['a','b','c','d'],'artist':['X','X','X','Y']})
    weekly=pd.DataFrame([['a','2000-01-01',1],['b','2000-01-01',2],['c','2000-01-08',30],['d','2000-01-15',1]],columns=['song_id','chart_date','weekly_rank'])
    embeddings={'a':x,'b':y,'c':x,'d':y}
    result=semantic_history(weekly,study,embeddings).set_index('song_id')
    if result.loc['a','lyric_semantic_prior_hit_reference_n']!=0 or result.loc['b','lyric_semantic_prior_credit_reference_n']!=0:raise ValueError('Simultaneous entrant leaked')
    expected=1-1/np.sqrt(2)
    np.testing.assert_allclose(result.loc['c',['lyric_semantic_novelty_prior_hits','lyric_semantic_drift_from_credit']].to_numpy(dtype=float),[expected,expected],atol=1e-14)
    prefix=semantic_history(weekly.iloc[:3],study,embeddings).set_index('song_id')
    pd.testing.assert_frame_equal(result.loc[prefix.index],prefix)
    report={'status':'PASS','saved_songs_replayed':count,'embedding_tolerance_absolute':1e-12,'simultaneous_and_future_reference_leaks':0,'protocol_key':active['key'],'code_sha256':sha(__file__)}
    write_json(MUSIC/'semantic_replay.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':verify()
