"""Read-only music weighting and aligned sensitivity views for the fixed pairs."""
from __future__ import annotations
import collections
import copy
import numpy as np
import pandas as pd
import pairwise_v5_common as v5
import pairwise_v5_stats as old
import robustness_v51_common as c
import robustness_v51_stats as s


def replace_music(workspace,task,name,values,profile=None):
    other=copy.copy(workspace);other.cache=collections.OrderedDict();other.views=list(workspace.views)
    view=dict(workspace.views[task['view_id']]);meta=dict(view['metadata'][name])
    if profile is not None:meta['profile']=profile
    view['values']=pd.DataFrame({name:np.asarray(values,float)},index=view['values'].index)
    view['metadata']={name:meta};other.views[task['view_id']]=view
    return s.from_workspace(other,task,name)


class SongViews:
    def __init__(self,workspace,candidates):
        self.workspace=workspace;self.cache={};self.validation=[]
        self.master=pd.read_csv(c.ROOT/'data/public/master_monthly.csv',low_memory=False)
        columns=set(pd.read_csv(c.ROOT/'data/public/music_enrichment_v2/songs.csv.xz',nrows=0).columns)
        requested=set(candidates.base_music_variable)|set(c.CONFIG['classifier_comparators'].values())
        extra=sorted((requested & columns)-set(self.master))
        if extra:
            songs=pd.read_csv(c.ROOT/'data/public/music_enrichment_v2/songs.csv.xz',usecols=['song_id']+extra)
            if songs.song_id.duplicated().any():raise ValueError('Duplicate exact song identity in song enrichment')
            self.master=self.master.merge(songs,on='song_id',how='left',validate='many_to_one',sort=False)
        if len(self.master)!=81797:raise ValueError('Monthly source-observation population changed')
        self.months=workspace.months.astype(str)
        self.source_monthly=v5.load(v5.PARENT/'monthly.pkl')
        self.source_genre=v5.load(v5.PARENT/'genre_month.pkl')

    def aggregate(self,name,view,weighting='source_equal',minimum=5,confidence='all'):
        key=(name,view,weighting,minimum,confidence)
        if key in self.cache:return self.cache[key]
        if name not in self.master:return None,'No song-level source column for this aggregate/derived measure'
        frame=self.master if view=='overall' else self.master.loc[self.master.primary_genre.eq(view)]
        if confidence=='high':frame=frame.loc[frame.genre_confidence.eq('high')]
        elif confidence=='medium_or_high':frame=frame.loc[frame.genre_confidence.isin(['medium','high'])]
        if weighting=='unique_song':
            # Only three repeated source song-months; retain a deterministic first source row.
            frame=frame.sort_values(['source_chart_index','source_row_index'],kind='stable').drop_duplicates(['month','song_id'])
        values=pd.to_numeric(frame[name],errors='coerce')
        observed=values.notna();frame=frame.loc[observed].copy();values=values.loc[observed]
        weights=(101-pd.to_numeric(frame.monthly_rank,errors='raise')).to_numpy(float) if weighting=='rank' else np.ones(len(frame))
        if np.any(weights<=0):raise ValueError('Nonpositive rank weight')
        groups=pd.DataFrame({'month':frame.month.to_numpy(),'sum':values.to_numpy(float)*weights,'weight':weights,'n':np.ones(len(frame),int)})
        grouped=groups.groupby('month',sort=True).sum()
        result=(grouped['sum']/grouped.weight).where(grouped.n>=minimum).reindex(self.months).to_numpy(float)
        output=(result,'ok');self.cache[key]=output;return output

    def verify_base(self,name,view_id):
        view=self.workspace.views[view_id];label=view['name'];values,status=self.aggregate(name,label)
        if values is None:return False,status
        if name not in view['values']:return False,'Base music column excluded/absent in this V5 population'
        expected=view['values'][name].to_numpy(float);finite=np.isfinite(values)&np.isfinite(expected)
        equal=bool(np.array_equal(np.isfinite(values),np.isfinite(expected)) and np.allclose(values[finite],expected[finite],rtol=1e-9,atol=1e-12))
        self.validation.append(dict(music_variable=name,view=label,matched=equal,common_months=int(finite.sum()),
            maximum_absolute_error=float(np.max(abs(values[finite]-expected[finite]))) if finite.any() else None,
            mask_agreement=bool(np.array_equal(np.isfinite(values),np.isfinite(expected)))))
        return equal,'ok' if equal else 'Song-level aggregation does not reproduce this V5 time-varying measure; no substitute weighting invented'

    def threshold(self,name,view_id,minimum):
        view=self.workspace.views[view_id];meta=view['metadata'][name];count=meta.get('count_column')
        source=self.source_monthly if view_id==0 else self.source_genre.loc[self.source_genre.primary_genre.eq(view['name'])]
        if count and count in source:
            n=source.set_index('month')[count].reindex(self.months).to_numpy(float)
            return np.where(n>=minimum,view['values'][name].to_numpy(float),np.nan),'ok'
        return None,'No valid feature-specific available-song denominator; aggregate/count measure'


def recession_episodes(workspace):
    name='US_NBER_DATED_RECESSION'
    # Lagged music comparisons can use recession observations before the first
    # chart month. Preserve the available prefix rather than truncating it.
    values=workspace.external['raw'][name].loc[:workspace.months[-1]]
    months=values.index;first_observed=values.first_valid_index()
    yes=values.eq(1).to_numpy();episodes=[]
    for start in np.flatnonzero(yes&~np.r_[False,yes[:-1]]):
        end=start+1
        while end<len(yes) and yes[end]:end+=1
        episodes.append(dict(name=f'recession_{months[start]}',start=str(months[start]),end=str(months[0]+end),
            source=name,left_censored_observed_fragment=bool(months[start]==first_observed),
            before_first_music_month=bool(months[0]+end<=workspace.months[0]),
            definition='Frozen retrospectively dated recession membership; ending boundary exclusive; initial observed fragment may have an unknown earlier start; later unknown membership not assumed expansion'))
    return episodes


def overlap_reproduction(workspace,candidates):
    platform=pd.read_csv(c.ROOT/'data/external_historical/derived/all_observations.csv.xz',low_memory=False)
    finance=pd.read_csv(c.ROOT/'data/external_historical/financial/processed/acquisition_v1/native_local.csv.xz',low_memory=False)
    rows=[]
    for external in sorted(set(candidates.external_variable)):
        meta=workspace.external['metadata'][external]
        records=meta.get('source_records',[]);p=[x.split(':',1)[1] for x in records if x.startswith('platform:')]
        f=[x.split(':',1)[1] for x in records if x.startswith('finance:')]
        row=dict(external_variable=external,source_records=';'.join(records),status='no_second_measurement',independent=False)
        if p and f:
            a=platform.loc[platform.series_id.isin(p),['date','value']].copy();b=finance.loc[finance.series_id.isin(f),['observation_date','value']].rename(columns={'observation_date':'date'})
            a.value=pd.to_numeric(a.value,errors='coerce');b.value=pd.to_numeric(b.value,errors='coerce')
            if a.date.duplicated().any() or b.date.duplicated().any():row['status']='multiple_native_keys_no_unambiguous_comparison'
            else:
                joined=a.merge(b,on='date',suffixes=('_platform','_financial')).dropna()
                error=abs(joined.value_platform-joined.value_financial)
                row.update(status='no_common_native_observations' if not len(joined) else 'same_provider_overlap_reproduced' if np.allclose(joined.value_platform,joined.value_financial,rtol=1e-10,atol=1e-10) else 'overlap_definition_or_revision_difference',
                    common_native_observations=len(joined),maximum_absolute_difference=float(error.max()) if len(error) else None,
                    interpretation='Two project releases share upstream observations; agreement is source reproduction, not independent economic replication')
        rows.append(row)
    return rows
