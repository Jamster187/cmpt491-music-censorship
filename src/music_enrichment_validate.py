"""Read-only integrity and replay checks for published enrichment/history layers."""
from __future__ import annotations
import argparse
import json

import numpy as np
import pandas as pd

from enrichment_common import ROOT, LOCAL, MUSIC, DATA, HISTORY, HISTORY_DATA, EXTERNAL, sha, write_json
from external_historical_features import compounded


def public_checks():
    manifest=json.loads((DATA/'manifest.json').read_text())
    for name,expected in manifest['artifacts'].items():
        if sha(DATA/name)!=expected:raise ValueError('Published music hash changed: '+name)
    for name,expected in manifest['code_sha256'].items():
        if sha(ROOT/'src'/name)!=expected:raise ValueError('Published music code differs: '+name)
    original=pd.read_csv(ROOT/'data/public/songs.csv',dtype=str,keep_default_na=False)
    songs=pd.read_csv(DATA/'songs.csv.xz',dtype=str,keep_default_na=False)
    if len(songs)!=28041 or songs.song_id.duplicated().any():raise ValueError('Study identities changed')
    if not songs[original.columns].equals(original):raise ValueError('Original source fields changed')
    missing=pd.read_csv(DATA/'song_missingness.csv.xz').set_index('song_id')
    dictionary=pd.read_csv(MUSIC/'feature_dictionary.csv',keep_default_na=False)
    if dictionary.feature.duplicated().any():raise ValueError('Repeated dictionary feature')
    for col in dictionary.feature:
        expected=songs.set_index('song_id')[col].eq('').astype(int)
        if not expected.equals(missing[col+'_missing']):raise ValueError('Missingness differs: '+col)
    for col in songs.filter(regex=r'^(lyric_.*share|lyric_.*coverage|audio_model_.*probability)$'):
        val=pd.to_numeric(songs[col].replace('',np.nan),errors='raise')
        if ((val.dropna() < -1e-12)|(val.dropna()>1+1e-12)).any():raise ValueError('Ratio outside [0,1]: '+col)
    for col in ['lyric_semantic_novelty_prior_hits','lyric_semantic_drift_from_credit']:
        val=pd.to_numeric(songs[col].replace('',np.nan),errors='raise').dropna()
        if not val.between(0,2).all():raise ValueError('Cosine distance invalid')
    audio=songs.audio_mapping_status.str.startswith('exact_')
    if songs.loc[~audio,'audio_bpm'].ne('').any():raise ValueError('Audio identity gate bypassed')
    weekly=pd.read_csv(ROOT/'data/public/master_weekly.csv.xz',usecols=['song_id','chart_date','weekly_rank','source_chart_index','source_row_index'])
    chart=pd.read_csv(DATA/'chart_period_features.csv.xz')
    pd.testing.assert_frame_equal(weekly.reset_index(drop=True),chart[weekly.columns].reset_index(drop=True),check_dtype=False)
    first=pd.to_datetime(chart.groupby('song_id').chart_date.transform('min'))
    early=pd.to_datetime(chart.chart_date)<first+pd.Timedelta(days=28)
    if chart.loc[early,'chart_first4w_points_after_window'].notna().any():raise ValueError('Future first-four-week points leaked')
    monthly=pd.read_csv(DATA/'monthly_overall.csv.xz')
    old=pd.read_csv(ROOT/'data/public/master_monthly.csv',usecols=['month','song_id'])
    if monthly.month.duplicated().any() or monthly.chart_source_row_count.sum()!=len(old):raise ValueError('Monthly denominator differs')
    expected=old.groupby('month').song_id.nunique()
    pd.testing.assert_series_equal(monthly.set_index('month').chart_distinct_song_count,expected,check_names=False)
    external_manifest=json.loads((HISTORY_DATA/'manifest.json').read_text())
    for name,expected in external_manifest['artifacts'].items():
        if sha(HISTORY_DATA/name)!=expected:raise ValueError('Published external hash changed: '+name)
    for name,expected in external_manifest['code_sha256'].items():
        if sha(ROOT/'src'/name)!=expected:raise ValueError('Published external code differs: '+name)
    allowed=pd.read_csv(HISTORY_DATA/'observations.csv.xz',low_memory=False)
    if not allowed.redistribution_permitted.all():raise ValueError('Restricted source in permitted export')
    if allowed[['series_id','date','vintage_date']].duplicated().any():raise ValueError('Published external duplicate')
    if not np.isfinite(allowed.value.dropna()).all():raise ValueError('Nonfinite external values')
    return {'status':'PASS','exact_song_identities':len(songs),'source_columns_preserved':len(original.columns),
        'missingness_fields_checked':len(dictionary),'chart_source_rows_preserved':len(chart),'monthly_units':len(monthly),
        'permitted_external_rows':len(allowed),'permitted_external_series':allowed.series_id.nunique()}


def private_checks():
    from external_historical_joins import read_observations
    observations=read_observations()
    keys=['series_id','date','vintage_date']
    if observations[keys].duplicated().any():raise ValueError('Duplicate private external observation')
    # Check every source observation against its immutable response hash.
    checked={}
    for path,expected in observations.loc[observations.raw_path.fillna('').ne(''),['raw_path','raw_sha256']].drop_duplicates().itertuples(index=False,name=None):
        if path in checked and checked[path]!=expected:raise ValueError('Conflicting raw hash')
        if sha(ROOT/path)!=expected:raise ValueError('External raw input changed: '+path)
        checked[path]=expected
    asof=pd.read_csv(EXTERNAL/'joins/asof_monthly_releases.csv.xz',keep_default_na=False)
    asof['value']=pd.to_numeric(asof.value.replace('',np.nan),errors='raise');valid=asof.loc[asof.value.notna()]
    if not (valid.publication_date<valid.cutoff_date).all():raise ValueError('Same-day or future publication leakage')
    if not (valid.period_end<=valid.cutoff_date).all():raise ValueError('Future observation leakage')
    comparison=valid.merge(observations[['series_id','date','publication_date','value']],on=['series_id','date','publication_date'],how='left',validate='many_to_one',suffixes=('','_source'))
    np.testing.assert_allclose(comparison.value,comparison.value_source,rtol=0,atol=1e-12)
    monthly=pd.read_csv(EXTERNAL/'joins/month_overall.csv.xz')
    if monthly.month.duplicated().any():raise ValueError('Duplicate joined months')
    quarterly=set(observations.loc[observations.frequency.eq('Q'),'series_id'])
    annual=set(observations.loc[observations.frequency.eq('A'),'series_id'])
    if any('external__'+sid in monthly for sid in quarterly|annual):raise ValueError('Lower-frequency data copied into months')
    wide=observations.loc[observations.frequency.eq('M')].pivot(index='date',columns='series_id',values='value')
    market=wide.FF_MKT_EXCESS+wide.FF_RF
    np.testing.assert_allclose(wide.US_EQUITY_TOTAL_RETURN.dropna(),market.loc[wide.US_EQUITY_TOTAL_RETURN.dropna().index],atol=1e-12,rtol=1e-12)
    # Rolling replay on explicit calendar months prevents a missing month being
    # mistaken for a one-month lag.
    market.index=pd.PeriodIndex(market.index,freq='M');market=market.reindex(pd.period_range(market.index.min(),market.index.max(),freq='M'))
    replay=compounded(market,12);stored=wide.US_EQUITY_RETURN_12M.dropna();stored.index=pd.PeriodIndex(stored.index,freq='M')
    np.testing.assert_allclose(stored,replay.reindex(stored.index),rtol=1e-12,atol=1e-10)
    release=pd.read_csv(EXTERNAL/'joins/release_context_keys.csv.xz',keep_default_na=False)
    if release.song_id.duplicated().any():raise ValueError('Release join inflated songs')
    permitted=release.release_month.ne('')
    if not release.loc[permitted,'release_date_precision'].isin(['day','month']).all():raise ValueError('Year-only date assigned a month')
    if not (release.loc[permitted,'release_month']<=release.loc[permitted,'chart_debut_month']).all():raise ValueError('Future release candidate accepted')
    return {'status':'PASS','source_raw_files_checked':len(checked),'all_external_rows':len(observations),
        'all_external_series':observations.series_id.nunique(),'asof_values_replayed':len(valid),'joined_months':len(monthly),
        'release_candidate_month_links':int(permitted.sum()),'same_day_and_future_release_leaks':0,'quarterly_annual_monthly_inflation':0}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private',action='store_true');a=p.parse_args()
    result={'public':public_checks()}
    if a.private:result['private']=private_checks()
    write_json(MUSIC/'validation.json',result);print(json.dumps(result,indent=2),flush=True)
