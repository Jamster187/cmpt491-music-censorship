"""Explicit natural-frequency and publication-time joins; no implicit interpolation."""
from __future__ import annotations
import argparse
import json
import re

import numpy as np
import pandas as pd

from enrichment_common import ROOT, EXTERNAL, HISTORY, HISTORY_DATA, DATA, sha, write_csv, write_json, atomic_bytes
from feature_expansion_common import SCORES


def read_observations(permitted=False):
    path=EXTERNAL/'derived'/('permitted_observations.csv.xz' if permitted else 'all_observations.csv.xz')
    data=pd.read_csv(path,keep_default_na=False,low_memory=False)
    data['value']=pd.to_numeric(data.value.replace('',np.nan),errors='raise')
    return data


def period_panel(frame,frequency):
    subset=frame.loc[frame.frequency.eq(frequency)]
    if subset[['series_id','date']].duplicated().any():raise ValueError('Multiple vintages need explicit selection')
    result=subset.pivot(index='date',columns='series_id',values='value')
    freq={'M':'M','Q':'Q-DEC','A':'Y-DEC'}[frequency]
    result.index=pd.PeriodIndex(result.index,freq=freq).astype(str)
    if result.index.duplicated().any():raise ValueError('Frequency collapse would duplicate periods')
    result.index.name={'M':'month','Q':'quarter','A':'year'}[frequency]
    return result.rename(columns=lambda s:'external__'+s).reset_index()


def music_summary(frequency='M',genre=False):
    source=pd.read_csv(ROOT/'data/public/master_monthly.csv',low_memory=False)
    # Preserve the three known repeated song/month pairs. Match existing
    # descriptive observation weighting, and report distinct identities too.
    if source[['source_chart_index','source_row_index']].duplicated().any():raise ValueError('Repeated source location')
    source['duplicate_song_month_row']=source.duplicated(['month','song_id']).astype(int)
    period={'M':'month','Q':'quarter','A':'year'}[frequency]
    dates=pd.PeriodIndex(source.month,freq='M')
    source[period]=dates.asfreq({'M':'M','Q':'Q-DEC','A':'Y-DEC'}[frequency]).astype(str)
    keys=[period]+(['primary_genre'] if genre else [])
    groups=source.groupby(keys,dropna=False,sort=True)
    result=groups.size().rename('music_source_row_count').to_frame()
    result['music_distinct_songs']=groups.song_id.nunique()
    result['music_repeated_song_month_rows']=groups.duplicate_song_month_row.sum()
    result['music_weighting']='equal_source_rows_available_per_score'
    result['music_observed_months']=groups.month.nunique()
    result['music_snapshot_date_first']=groups.snapshot_chart_date.min()
    result['music_snapshot_date_last']=groups.snapshot_chart_date.max()
    result['music_lyrics_available_n']=groups.lyrics_available.sum()
    means=groups[SCORES].mean().rename(columns=lambda x:'music__'+x+'_mean')
    counts=groups[SCORES].count().rename(columns=lambda x:'music__'+x+'_n')
    result=pd.concat([result,means,counts],axis=1).reset_index()
    expected={'M':1,'Q':3,'A':12}[frequency]
    result['music_calendar_period_complete']=result.music_observed_months.eq(expected)
    return result


def asof_series(observations,cutoffs,series_id):
    """Fail closed for latest-revised snapshots lacking original release vintages."""
    rows=observations.loc[observations.series_id.eq(series_id)].copy()
    if rows.empty:raise ValueError('Unknown series: '+series_id)
    if not rows.availability_status.eq('historical_release_vintage').all():
        raise ValueError('Series lacks a historical-vintage guarantee: '+series_id)
    rows=rows.loc[rows.publication_date.ne('')&rows.value.notna()]
    if rows.publication_date.duplicated().any():raise ValueError('Multiple releases on one date require an explicit ordering rule')
    rows['released']=pd.to_datetime(rows.publication_date)
    rows=rows.sort_values('released')
    left=pd.DataFrame({'cutoff_date':pd.to_datetime(sorted(set(cutoffs)))})
    # Intraday chart/release times are unknown. Require a strictly earlier day.
    result=pd.merge_asof(left,rows,left_on='cutoff_date',right_on='released',direction='backward',allow_exact_matches=False)
    result['series_id']=series_id
    valid=result.value.notna()
    if (result.loc[valid,'released']>=result.loc[valid,'cutoff_date']).any():raise ValueError('Future or same-day release leaked')
    if (pd.to_datetime(result.loc[valid,'period_end'])>result.loc[valid,'cutoff_date']).any():raise ValueError('Future observation leaked')
    result['age_days']=(result.cutoff_date-pd.to_datetime(result.period_end)).dt.days
    result['cutoff_date']=result.cutoff_date.dt.strftime('%Y-%m-%d')
    return result[['cutoff_date','series_id','date','period_end','publication_date','vintage_date','value','units','age_days','source_url','retrieval_date','license']]


def release_context_keys(songs):
    rows=[]
    for r in songs.to_dict('records'):
        new=r.get('mb_v2_recording_first_release_candidate','')
        value=new if isinstance(new,str) and new else r.get('mb_earliest_release_date','')
        source='unique_recording_first_release' if isinstance(new,str) and new else 'earliest_associated_release_candidate'
        row={'song_id':r['song_id'],'release_date_candidate':value,'release_date_source':source,
            'release_original_edition_verified':False,'release_month':'','release_year':'','chart_debut_month':r['first_chart_date'][:7]}
        if not value:row['release_join_status']='missing_release_date'
        elif not re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?',str(value)):row['release_join_status']='unsupported_source_date'
        else:
            precision={4:'year',7:'month',10:'day'}[len(value)];row['release_date_precision']=precision;row['release_year']=value[:4]
            try:
                start=pd.Period(value,freq={'year':'Y-DEC','month':'M','day':'D'}[precision]).start_time
                debut=pd.Timestamp(r['first_chart_date'])
                if start>debut:row['release_join_status']='candidate_after_chart_debut_review_required'
                elif precision=='year':row['release_join_status']='year_precision_no_month_join'
                else:
                    row['release_month']=value[:7];row['release_join_status']='retrospective_candidate_month_only_original_unverified'
            except (ValueError,OverflowError):row['release_join_status']='invalid_calendar_date'
        rows.append(row)
    return pd.DataFrame(rows)


def build():
    all_data=read_observations();cleared=read_observations(True);summary={}
    for allowed,frame in [(False,all_data),(True,cleared)]:
        suffix='_permitted' if allowed else ''
        for frequency in ['M','Q','A']:
            panel=period_panel(frame,frequency);period=panel.columns[0]
            write_csv(EXTERNAL/'joins'/f'external_{frequency}{suffix}.csv.xz',panel)
            for genre in [False,True]:
                music=music_summary(frequency,genre)
                result=music.merge(panel,on=period,how='left',validate='many_to_one')
                result['context_temporal_mode']='retrospective_observation_period_not_asof'
                if len(result)!=len(music):raise ValueError('Join inflated music analytical units')
                scope='genre' if genre else 'overall';name=f'{period}_{scope}{suffix}.csv.xz'
                write_csv(EXTERNAL/'joins'/name,result)
                if allowed:write_csv(HISTORY_DATA/name.replace('_permitted',''),result)
                fields=[c for c in result if c.startswith('external__')]
                summary[name]={'rows':len(result),'external_columns':len(fields),'units_with_any_external_value':int(result[fields].notna().any(axis=1).sum()),
                    'unit':period+(' x primary genre' if genre else ''),'temporal_mode':'retrospective_observation_period'}
    monthly=music_summary();cutoffs=monthly.music_snapshot_date_last.tolist()
    ids=sorted(all_data.loc[all_data.availability_status.eq('historical_release_vintage'),'series_id'].unique())
    asof=pd.concat([asof_series(all_data,cutoffs,sid) for sid in ids],ignore_index=True)
    asof=asof.merge(monthly[['month','music_snapshot_date_last']],left_on='cutoff_date',right_on='music_snapshot_date_last',validate='many_to_one').drop(columns='music_snapshot_date_last')
    write_csv(EXTERNAL/'joins/asof_monthly_releases.csv.xz',asof)
    allowed_ids=set(cleared.series_id)
    write_csv(HISTORY_DATA/'asof_monthly_releases.csv.xz',asof.loc[asof.series_id.isin(allowed_ids)])
    songs=pd.read_csv(DATA/'songs.csv.xz',keep_default_na=False,low_memory=False)
    release=release_context_keys(songs);write_csv(EXTERNAL/'joins/release_context_keys.csv.xz',release)
    write_csv(HISTORY_DATA/'release_context_keys.csv.xz',release)
    weekly=pd.read_csv(ROOT/'data/public/master_weekly.csv.xz',usecols=['song_id','chart_date','source_chart_index','source_row_index'])
    weekly['month']=weekly.chart_date.str[:7];weekly['quarter']=pd.to_datetime(weekly.chart_date).dt.to_period('Q').astype(str);weekly['year']=weekly.chart_date.str[:4]
    write_csv(EXTERNAL/'joins/chart_context_keys.csv.xz',weekly)
    write_csv(HISTORY_DATA/'chart_context_keys.csv.xz',weekly)
    summary['asof']={'series':len(ids),'rows':len(asof),'nonnull':int(asof.value.notna().sum()),'music_months_with_any':asof.loc[asof.value.notna(),'month'].nunique(),
        'missing_before_archive_start':int(asof.value.isna().sum()),'latest_snapshot_series_excluded':all_data.series_id.nunique()-len(ids)}
    summary['release_statuses']=release.release_join_status.value_counts().to_dict();summary['chart_rows']=len(weekly)
    summary['music_months']=len(monthly);summary['source_song_months']=int(monthly.music_source_row_count.sum())
    summary['preserved_repeated_song_month_rows']=int(monthly.music_repeated_song_month_rows.sum())
    summary['monthly_series_coverage']={sid:int(monthly.month.isin(all_data.loc[all_data.series_id.eq(sid)&all_data.value.notna(),'date'].str[:7]).sum())
        for sid in sorted(all_data.loc[all_data.frequency.eq('M'),'series_id'].unique())}
    summary['code_sha256']=sha(__file__);write_json(HISTORY/'join_validation.json',summary)
    atomic_bytes(HISTORY_DATA/'observations.csv.xz',(EXTERNAL/'derived/permitted_observations.csv.xz').read_bytes())
    write_json(HISTORY_DATA/'manifest.json',{'version':'external-historical-v1.1','restricted_values_excluded':True,
        'source_observations_and_derived_features_independent':True,'music_months':len(monthly),
        'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [EXTERNAL/'derived/permitted_observations.csv.xz',ROOT/'data/public/master_monthly.csv',DATA/'songs.csv.xz']},
        'artifacts':{p.name:sha(p) for p in sorted(HISTORY_DATA.glob('*.csv.xz'))},
        'code_sha256':{p.name:sha(p) for p in sorted((ROOT/'src').glob('external_historical_*.py'))},
        'license_selection':'Only observations explicitly marked redistribution_permitted=True; restricted sources have coverage/provenance only in public reports'})
    print(json.dumps({k:v for k,v in summary.items() if k!='monthly_series_coverage'},indent=2),flush=True)


def query(view,series,mode='retrospective',permitted=False):
    """Return selected context on demand; avoid duplicating every series per song."""
    if permitted:data=pd.read_csv(HISTORY_DATA/'observations.csv.xz',keep_default_na=False,low_memory=False);data['value']=pd.to_numeric(data.value.replace('',np.nan),errors='raise')
    else:data=read_observations()
    rows=data.loc[data.series_id.isin(series)]
    if set(rows.series_id)!=set(series):raise ValueError('Unknown requested series')
    if view=='release':
        if mode!='retrospective':raise ValueError('Unverified release dates cannot support an as-of forecasting view')
        keys=pd.read_csv((HISTORY_DATA if permitted else EXTERNAL/'joins')/'release_context_keys.csv.xz',keep_default_na=False)
        keys=keys.loc[keys.release_month.ne('')];keys=keys.rename(columns={'release_month':'month'})
    elif view=='chart':keys=pd.read_csv((HISTORY_DATA if permitted else EXTERNAL/'joins')/'chart_context_keys.csv.xz',keep_default_na=False)
    else:raise ValueError('Unknown view')
    music=pd.read_csv(DATA/'songs.csv.xz',usecols=['song_id','title','artist','primary_genre']+SCORES)
    keys=keys.merge(music,on='song_id',how='left',validate='many_to_one')
    if mode=='asof':
        values=pd.concat([asof_series(data,keys.chart_date.tolist(),sid) for sid in series],ignore_index=True)
        # One row per source chart location x requested series; repeated values are
        # context, never additional independent economic observations.
        return keys.merge(values,left_on='chart_date',right_on='cutoff_date',how='left',validate='many_to_many')
    if not rows.frequency.eq('M').all():raise ValueError('Month context requires monthly series; use natural quarterly/annual views')
    panel=period_panel(rows,'M')
    return keys.merge(panel,on='month',how='left',validate='many_to_one')


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True);sub.add_parser('build')
    q=sub.add_parser('query');q.add_argument('--view',choices=['release','chart'],required=True);q.add_argument('--series',nargs='+',required=True)
    q.add_argument('--mode',choices=['retrospective','asof'],default='retrospective');q.add_argument('--output',required=True)
    q.add_argument('--permitted',action='store_true',help='Use published permitted inputs only; works without private source caches')
    a=p.parse_args();build() if a.action=='build' else write_csv(a.output,query(a.view,a.series,a.mode,a.permitted))
