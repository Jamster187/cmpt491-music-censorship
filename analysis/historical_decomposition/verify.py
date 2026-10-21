"""Read-only published-result checks and optional deterministic resampling replay."""
from pathlib import Path
import argparse
import json
import sys
import time
import subprocess

import numpy as np
import pandas as pd
from scipy import stats
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import historical_decomposition as hd


def verify(replay=False):
    started=time.perf_counter()
    guard=json.loads((hd.PUBLIC/'preservation_manifest.json').read_text())
    for name,expected in guard['sha256'].items():
        if hd.descriptive.sha(ROOT/name)!=expected:raise ValueError('Baseline differs: '+name)
    for name,record in guard.get('approved_verification_revisions',{}).items():
        content=subprocess.check_output(['git','show',guard['baseline_commit']+':'+name],cwd=ROOT)
        if hd.hashlib.sha256(content).hexdigest()!=record['original_sha256']:
            raise ValueError('Historical verification source differs: '+name)
        if hd.descriptive.sha(ROOT/name)!=record['current_sha256']:
            raise ValueError('Revised verification source differs: '+name)
    artifact=json.loads((hd.PUBLIC/'artifact_manifest.json').read_text())
    for section in ['sha256','sources_sha256']:
        for name,expected in artifact[section].items():
            if hd.descriptive.sha(ROOT/name)!=expected:raise ValueError('Publication differs: '+name)
    data,genres,_=hd.load_data()
    h=pd.read_csv(hd.PUBLIC/'historical_comparisons.csv',float_precision='round_trip')
    d=pd.read_csv(hd.PUBLIC/'decomposition_results.csv',float_precision='round_trip')
    t=pd.read_csv(hd.PUBLIC/'primary_tests.csv',float_precision='round_trip')
    b=pd.read_csv(hd.PUBLIC/'breakpoint_results.csv',float_precision='round_trip')
    assert len(h)==882 and len(d)==14112 and len(b)==242
    assert not h.duplicated(['comparison','weighting','classifier']).any()
    assert not d.duplicated(['comparison','weighting','classifier','genre']).any()
    assert len(t)==hd.HYPOTHESES and t.test_id.nunique()==hd.HYPOTHESES
    np.testing.assert_allclose(t.q_by_global,stats.false_discovery_control(t.p_value,method='by'),atol=1e-15)
    grouped=d.groupby(['comparison','weighting','classifier'])[['within','composition']].sum()
    indexed=h.set_index(['comparison','weighting','classifier'])
    np.testing.assert_allclose(grouped.sort_index(),indexed[['within','composition']].sort_index(),atol=2e-12)
    np.testing.assert_allclose(h.within+h.composition,h.delta,atol=2e-12)
    # Directly reproduce the previous moving-average monthly means and counts.
    previous=pd.read_csv(ROOT/'analysis/moving_averages/data/monthly_classifier_overall.csv.xz')
    previous=previous[previous.month.str[:4].astype(int).between(1960,2025)].set_index(['month','classifier']).sort_index()
    means=data.groupby('month')[hd.FEATURES].mean().stack().sort_index()
    counts=data.groupby('month')[hd.FEATURES].count().stack().sort_index()
    weights=data[hd.FEATURES].notna().multiply(data.rank_weight,axis=0).groupby(data.month).sum()
    numerator=data[hd.FEATURES].multiply(data.rank_weight,axis=0).groupby(data.month).sum()
    rank=(numerator/weights).stack().sort_index()
    np.testing.assert_array_equal(counts,previous.n)
    np.testing.assert_allclose(means,previous['mean'],atol=1e-10,rtol=1e-10)
    np.testing.assert_allclose(rank,previous.rank_weighted_mean,atol=1e-10,rtol=1e-10)
    # Check all published intervals for the fixed legacy decomposition and the
    # earliest/latest genre-adjusted breakpoint windows from fresh resamples.
    replayed=[]
    if replay:
        a,z=hd.COMPARISONS[-1];key=hd.comparison_id(a,z)
        draws=hd.decomposition_bootstrap(data,genres,a,z)
        selected=h[(h.comparison==key)&(h.weighting=='song_month')].set_index('classifier').loc[hd.PRIMARY]
        points=selected[['delta','within','composition']].to_numpy()
        u=hd.uncertainty(points,draws)
        for k,term in enumerate(['delta','within','composition']):
            for field in ['low','high','p','se']:
                np.testing.assert_allclose(u[field][:,k],selected[term+'_'+field],atol=2e-12,rtol=1e-10)
        replayed.append(dict(kind='decomposition',comparison=key,draws=len(draws),scores=len(hd.PRIMARY)))
        for year in [1970,2020]:
            window=data[data.year.between(year-6,year+5)]
            for frame,features in hd.score_groups(window):
                result=hd.breakpoint_group(frame,features,year,True)
                u=hd.uncertainty(result['beta'],result['draws'])
                selected=b[(b.break_year==year)&(b.model=='genre_adjusted')].set_index('classifier').loc[features]
                for k,term in enumerate(['level','slope']):
                    np.testing.assert_allclose(result['beta'][:,k],selected[term],atol=2e-12,rtol=1e-10)
                    for field in ['low','high','p','se']:
                        np.testing.assert_allclose(u[field][:,k],selected[term+'_'+field],atol=2e-12,rtol=1e-10)
                replayed.append(dict(kind='breakpoint',year=year,model='genre_adjusted',draws=len(result['draws']),scores=len(features)))
    return dict(status='PASS',protected_files=len(guard['sha256']),published_comparisons=len(h),
        unique_primary_tests=len(t),previous_monthly_score_cells_checked=len(previous),
        previous_equal_and_rank_means_match=True,resampling_replays=replayed,
        private_cache_required=False,seconds=time.perf_counter()-started)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--replay',action='store_true');args=parser.parse_args()
    with threadpool_limits(limits=1):print(json.dumps(verify(args.replay),indent=2))
