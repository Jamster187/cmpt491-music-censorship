"""Read-only release checks and independent point-in-time spot checks."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from feature_expansion_common import ROOT,PUBLIC,DATA,LOCAL,sha,read_json,write_json,write_csv,preservation,split_frame,SCORES
from feature_expansion_features import DEFINITIONS,chart_features
from feature_expansion_models import columns,load_population,task_splits


def validate(prefix=False,protect=False):
    f=pd.read_csv(DATA/'song_features.csv.xz');o=pd.read_csv(DATA/'song_outcomes.csv.xz');manifest=read_json(DATA/'manifest.json')
    for name,info in manifest['files'].items():
        if sha(DATA/name)!=info['sha256']:raise ValueError('Dataset hash mismatch '+name)
    w=pd.read_csv(ROOT/'data/public/master_weekly.csv.xz',usecols=['chart_date','weekly_rank','source_chart_index','source_row_index','song_id','title','artist'])
    ident=w[['song_id','title','artist']].drop_duplicates().sort_values('song_id').reset_index(drop=True)
    assert_frame_equal(f[['song_id','title','artist']],ident)
    if set(f.song_id)!=set(o.song_id) or len(f)!=len(o):raise ValueError('Feature/outcome population mismatch')
    first=w.groupby('song_id').chart_date.min();rank=w.merge(first.rename('debut'),on='song_id');rank=rank[rank.chart_date.eq(rank.debut)].groupby('song_id').weekly_rank.min()
    if not np.array_equal(f.debut_rank,rank.loc[f.song_id].to_numpy()):raise ValueError('Debut rank mismatch')
    w['chart_date']=pd.to_datetime(w.chart_date);w['points']=101-w.weekly_rank;bycredit={a:g for a,g in w.groupby('artist')}
    sample=f.sample(n=min(256,len(f)),random_state=4911026);checks=[]
    for row in sample.itertuples():
        prior=bycredit[row.artist];prior=prior[prior.chart_date.lt(row.first_chart_date)];best=prior.groupby('song_id').weekly_rank.min()
        expected=dict(credit_prior_song_count=prior.song_id.nunique(),credit_prior_top10_song_count=int(best.le(10).sum()),
            credit_prior_top40_song_count=int(best.le(40).sum()),credit_prior_chart_points=prior.points.sum(),
            credit_prior_chart_weeks=len(prior[['song_id','chart_date']].drop_duplicates()),credit_prior_best_rank=prior.weekly_rank.min())
        for name,value in expected.items():
            if not np.isclose(getattr(row,name),value,equal_nan=True):raise ValueError('Independent history mismatch '+row.song_id+' '+name)
        checks.append(dict(song_id=row.song_id,first_chart_date=row.first_chart_date,checks=len(expected),status='PASS'))
    write_csv(PUBLIC/'asof_spot_checks.csv',checks)
    prefix_result='not_requested'
    if prefix:
        short=w[w.chart_date.le('1990-01-01')].copy();rebuilt=chart_features(short);names=['song_id']+[n for n,d in DEFINITIONS.items() if d['historical_availability']=='C']
        original=f[f.song_id.isin(rebuilt.song_id)][names].sort_values('song_id').reset_index(drop=True)
        assert_frame_equal(original,rebuilt[names],check_dtype=False,rtol=1e-10,atol=1e-9)
        prefix_result=dict(status='PASS',cutoff='1990-01-01',identities=len(rebuilt),features=len(names)-1)
    populations=pd.read_csv(PUBLIC/'model_populations.csv') if (PUBLIC/'model_populations.csv').exists() else None
    split_audit=[]
    for track in ['strict','retrospective']:
        population=load_population(track)
        for target in ['top10','long_chart','best_rank','chart_weeks','chart_points']:
            parts=task_splits(population,target)
            for partition,part in parts.items():
                d=pd.to_datetime(part.first_chart_date);end=pd.to_datetime(part.window_end_26)
                if partition=='train' and not end.le('2010-01-01').all():raise ValueError('Training window crosses boundary')
                if partition=='validation' and not (d.ge('2010-01-01')&end.le('2018-01-01')).all():raise ValueError('Validation window crosses boundary')
                if partition=='test' and not d.ge('2018-01-01').all():raise ValueError('Test date before cutoff')
                split_audit.append(dict(track=track,target=target,partition=partition,n=len(part)))
                if populations is not None:
                    records=populations[(populations.track==track)&(populations.target==target)&(populations.partition==partition)]
                    if len(records)!=3 or records.song_ids_sha256.nunique()!=1 or not records.n.eq(len(part)).all():raise ValueError('Unfair configuration cohorts')
    dictionary=pd.read_csv(PUBLIC/'feature_dictionary.csv')
    if set(dictionary.feature)!=set(DEFINITIONS) or dictionary.feature.duplicated().any():raise ValueError('Dictionary mismatch')
    if not all(c=='debut_rank' or DEFINITIONS[c]['historical_availability']=='C' for c in columns('strict','combined')):raise ValueError('Retrospective feature in strict track')
    report=dict(status='PASS',identities=len(f),source_rows=len(w),independent_history_identities=len(checks),independent_history_assertions=sum(x['checks'] for x in checks),
        prefix_invariance=prefix_result,split_audit=split_audit,protected_artifacts=preservation() if protect else 'not_requested')
    write_json(PUBLIC/'validation_audit.json',report);print(report,flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prefix',action='store_true');p.add_argument('--preservation',action='store_true');args=p.parse_args();validate(args.prefix,args.preservation)
