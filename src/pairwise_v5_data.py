"""V5 inventory and aligned views, built only from frozen local releases."""
from __future__ import annotations
import copy
import hashlib
import json
import numpy as np
import pandas as pd
import pairwise_v5_common as c


def numeric_hash(values):
    a=np.asarray(values,dtype='<f8').copy(); a[np.isnan(a)]=np.nan; a[a==0]=0.
    return hashlib.sha256(a.tobytes()).hexdigest()


def native_change(values,rule):
    if rule in ['identity_rate_change_or_event','categorical_identity']: return values.copy()
    previous=values.shift(1)
    if rule=='log_growth_positive_endpoints': return 100*np.log(values.where(values>0)/previous.where(previous>0))
    if rule=='first_difference_native_period': return values-previous
    raise ValueError('Unregistered transformation '+rule)


def external_catalog():
    raw=c.load(c.PARENT/'external_raw.pkl').copy()
    ends=c.load(c.PARENT/'external_period_end.pkl').copy()
    metadata=copy.deepcopy(c.read_json(c.PARENT/'external_registry.json'))
    platform=pd.read_csv(c.ROOT/'data/external_historical/derived/all_observations.csv.xz',keep_default_na=False,low_memory=False)
    platform['value']=pd.to_numeric(platform.value.replace('',np.nan),errors='raise')
    finance=pd.read_csv(c.ROOT/'data/external_historical/financial/processed/acquisition_v1/native_local.csv.xz',keep_default_na=False,low_memory=False)
    finance['value']=pd.to_numeric(finance.value.replace('',np.nan),errors='raise')
    definitions={}
    for name in ['series_dictionary','derived_series_dictionary']:
        definitions.update(pd.read_csv(c.ROOT/f'analysis/external_historical/{name}.csv',keep_default_na=False).set_index('series_id').to_dict('index'))
    financial={}
    for name in ['series_dictionary','derived_feature_dictionary']:
        financial.update(pd.read_csv(c.ROOT/f'analysis/external_historical/financial_acquisition/{name}.csv',keep_default_na=False).set_index('series_id').to_dict('index'))
    alignment=[]; exclusions=[]
    daily={}
    for sid,group in platform.loc[platform.frequency.eq('D')].groupby('series_id'):
        if 'NBER' in sid: continue  # Existing explicit as-of event context is retained below.
        daily[sid]=pd.Series(group.value.to_numpy(),index=pd.to_datetime(group.date)).sort_index()
    for sid,group in finance.loc[finance.native_frequency.eq('D')].groupby('series_id'):
        if 'NBER' in sid: continue
        candidate=pd.Series(group.value.to_numpy(),index=pd.to_datetime(group.observation_date)).sort_index()
        if sid in daily:
            common=daily[sid].dropna().index.intersection(candidate.dropna().index)
            np.testing.assert_allclose(daily[sid].loc[common],candidate.loc[common],rtol=1e-12,atol=1e-12)
            daily[sid]=daily[sid].combine_first(candidate)
        else: daily[sid]=candidate
    for sid,series in sorted(daily.items()):
        if series.index.duplicated().any(): raise ValueError('Duplicate daily date '+sid)
        series=series.dropna(); group=series.groupby(series.index.to_period('M'))
        values=group.last(); dates=series.index.to_series().groupby(series.index.to_period('M')).max()
        name=sid+'__month_end'
        raw[name]=values.reindex(raw.index); ends[name]=dates.dt.strftime('%Y-%m-%d').reindex(raw.index)
        definition=definitions.get(sid,financial.get(sid,{}))
        category=definition.get('category') or ('financial' if sid.startswith('FF_') else 'macroeconomic')
        rule='identity_rate_change_or_event' if sid.startswith('FF_') else 'first_difference_native_period'
        metadata[name]=dict(name=name,kind='numeric',domain=category,family='daily_endpoint:'+sid,
            source=[definition.get('source') or definition.get('provider','unknown')],dependencies=[sid],
            frequency='D',view_frequency='M',units=definition.get('units','source units'),
            definition='Last available observed daily value in the month; daily returns remain daily returns, not monthly returns',
            availability=definition.get('availability_status') or definition.get('vintage_availability','retrospective_snapshot'),
            public=str(definition.get('redistribution_permitted')).lower()=='true',
            transformation=rule,origin='external',source_records=['daily_endpoint:'+sid])
        for month in values.index:
            if str(month)<'1956-08' or str(month)>'2026-09': continue
            alignment.append(dict(series_id=name,month=str(month),last_observed_date=dates.loc[month].date().isoformat(),
                                  source_observations=int(group.size().loc[month]),method='last_observed_daily_value',source_series=sid))
    inventory=[]; retained={}; seen={}; adjusted={}
    for name,definition in sorted(metadata.items()):
        d=copy.deepcopy(definition); frequency=d.get('view_frequency',d['frequency'])
        d['analysis_frequency']=frequency if frequency in ['Q','A','term','event'] else 'M'
        records=[]
        for tag in d.get('source_records',[]):
            sid=tag.split(':',1)[-1]
            records.append(definitions.get(sid,financial.get(sid,{})))
        if name.endswith('__month_end'):
            sid=name[:-11]; records.append(definitions.get(sid,financial.get(sid,{})))
        d['methodological_breaks']=' | '.join(sorted({str(r.get('methodological_breaks') or r.get('notes') or 'Not exhaustively documented') for r in records if r}))
        d['publication_information']=json.dumps([dict(source=tag,
            publication_date=r.get('publication_date') or r.get('original_publication_date',''),
            vintage_date=r.get('vintage_date') or r.get('snapshot_vintage_date',''),
            availability=r.get('availability_status') or r.get('vintage_availability',''))
            for tag,r in zip(d.get('source_records',[]),records)],sort_keys=True)
        d['source_urls']=sorted({r.get('source_url','') for r in records if r.get('source_url')})
        values=raw[name]; selected=values.loc[(raw.index>=pd.Period('1956-08','M'))&(raw.index<=pd.Period('2026-09','M'))]
        observed=selected.notna() & selected.astype(str).ne('')
        reason=''; alias=''
        if not observed.any(): reason='No observed value in the analysis/lag support window'
        elif selected.loc[observed].nunique()<2: reason='Constant in the analysis/lag support window'
        if d['kind']=='numeric':
            selected=pd.to_numeric(selected,errors='raise'); key=('numeric',numeric_hash(selected))
        else: key=('categorical',c.digest(selected.where(observed,None).tolist()))
        if not reason and key in seen: reason='Exact value and missingness duplicate in the complete lag-support window'; alias=seen[key]
        if not reason:
            seen[key]=name; retained[name]=d
            if d['kind']=='categorical': adjusted[name]=values.copy()
            else:
                f=d['analysis_frequency']
                if f in ['Q','A']:
                    periods=raw.index.asfreq('Q-DEC' if f=='Q' else 'Y-DEC')
                    native=pd.Series(values.to_numpy(float),index=periods).groupby(level=0).first()
                    native=native.reindex(pd.period_range(native.index.min(),native.index.max(),freq=native.index.freq))
                    changed=native_change(native,d['transformation'])
                    adjusted[name]=pd.Series(changed.reindex(periods).to_numpy(),index=raw.index)
                elif f in ['event']:
                    adjusted[name]=values.copy()
                else: adjusted[name]=native_change(pd.to_numeric(values,errors='raise'),d['transformation'])
        else: exclusions.append(dict(origin='external',population='all',variable=name,reason=reason,canonical_alias=alias))
        inventory.append(dict(variable=name,origin='external',population='all',domain=d['domain'],family=d['family'],
            kind=d['kind'],source=json.dumps(d['source']),units=d['units'],frequency=d['frequency'],analysis_frequency=d['analysis_frequency'],
            observed=int(observed.sum()),missing=int((~observed).sum()),coverage=float(observed.mean()),
            first_observed=str(selected.loc[observed].index.min()) if observed.any() else '',
            last_observed=str(selected.loc[observed].index.max()) if observed.any() else '',
            dependencies=json.dumps(d.get('dependencies',[])),temporal_availability=d['availability'],
            transformation=d['transformation'],definition=d.get('definition',''),
            methodological_breaks=d['methodological_breaks'],publication_and_vintage=d['publication_information'],
            source_urls=json.dumps(d['source_urls']),eligible=not bool(reason),exclusion_reason=reason,canonical_alias=alias))
    # Preserve the earlier verified crosswalk and explicit source exclusions in V5.
    crosswalk=pd.read_csv(c.ROOT/'analysis/cross_domain_discovery_v4/series_crosswalk.csv',keep_default_na=False)
    for row in crosswalk.loc[crosswalk.status.eq('verified_alias')].to_dict('records'):
        exclusions.append(dict(origin='external_source_alias',population='all',variable=row['financial_id'],
                               reason=row['rule'],canonical_alias=row['canonical_id']))
    c.write_csv(c.PUBLIC/'daily_alignment.csv',alignment)
    c.write_csv(c.PUBLIC/'external_source_crosswalk.csv',crosswalk)
    return raw[list(retained)],pd.DataFrame(adjusted,index=raw.index),ends[list(retained)],retained,inventory,exclusions


def music_catalog():
    overall=c.load(c.PARENT/'monthly.pkl'); genre=c.load(c.PARENT/'genre_month.pkl')
    registry=copy.deepcopy(c.read_json(c.PARENT/'music_registry.json'))
    if len(overall)!=818 or len(genre)!=7173 or overall.month.duplicated().any() or genre[['month','primary_genre']].duplicated().any():
        raise ValueError('Unexpected or duplicated music analytical units')
    agreement=[]
    for label,frame,path,keys in [('monthly',overall,'monthly_overall.csv.xz',['month']),('genre_month',genre,'monthly_by_genre.csv.xz',['month','primary_genre'])]:
        public=pd.read_csv(c.ROOT/'data/public/music_enrichment_v2'/path)
        merged=frame.merge(public,on=keys,suffixes=('','__published'),validate='one_to_one')
        if len(merged)!=len(frame): raise ValueError('Public/enriched view key disagreement')
        checked=0
        for name in public:
            target=name[:-5] if name.endswith('_mean') else name[:-2]+'__available_n' if name.endswith('_n') else None
            if target and target in frame:
                np.testing.assert_allclose(merged[target],merged[name],rtol=1e-12,atol=1e-12,equal_nan=True); checked+=1
        agreement.append(dict(population=label,rows=len(frame),published_measurements_reproduced=checked))
    candidates={n:copy.deepcopy(d) for n,d in registry.items() if d['kind']=='numeric' and n in overall and (n in genre or n.startswith('genre_share__'))}
    for name in overall:
        if name.endswith('__available_n'):
            parent=name[:-13]
            candidates[name]=dict(name=name,kind='numeric',domain='measurement_quality',family='feature_sample_size',
                source=['billboard','feature_availability'],dependencies=[parent],units='observed source rows',frequency='M',
                availability='retrospective_measurement_coverage',definition='Feature-specific nonmissing source-row count',origin='music')
    for name in ['source_row_count','distinct_song_count']:
        candidates[name]=dict(name=name,kind='numeric',domain='measurement_quality',family='population_size',source=['billboard'],dependencies=[],
            units='source rows' if name=='source_row_count' else 'distinct exact study songs',frequency='M',availability='at_chart',definition=name,origin='music')
    exclusions=[]; inventory=[]; kept={}; seen={}
    # Prefer original analytical names to exact duplicate coverage columns.
    ordering=sorted(candidates,key=lambda n:(n.endswith('__available_n'),n))
    for name in ordering:
        d=candidates[name]; portions=[pd.to_numeric(overall[name],errors='raise').to_numpy(float)]
        if name in genre: portions.append(pd.to_numeric(genre[name],errors='raise').to_numpy(float))
        all_values=np.concatenate(portions); finite=np.isfinite(all_values); reason=''; alias=''
        if not finite.any(): reason='No finite music observations'
        elif len(np.unique(all_values[finite]))<2: reason='Constant across original monthly and genre-month observations'
        signature=(tuple(len(a) for a in portions),numeric_hash(all_values))
        if not reason and signature in seen: reason='Exact values and missingness duplicate across all available music views'; alias=seen[signature]
        if not reason:
            seen[signature]=name; d['count_column']=name+'__available_n' if name+'__available_n' in overall else ''
            d['profile']='composition' if d['domain'].startswith('lyric') else 'time'
            d['role']='sample_size' if name.endswith('__available_n') or name in ['source_row_count','distinct_song_count'] else 'genre_composition' if name.startswith('genre_share__') else 'measurement'
            kept[name]=d
        else: exclusions.append(dict(origin='music',population='all',variable=name,reason=reason,canonical_alias=alias))
        for pop,frame in [('monthly',overall),('genre_month',genre)]:
            if name not in frame: continue
            values=pd.to_numeric(frame[name],errors='raise'); observed=values.notna()
            inventory.append(dict(variable=name,origin='music',population=pop,domain=d['domain'],family=d['family'],kind='numeric',
                source=json.dumps(d['source']),units=d.get('units','source units; see definition'),frequency='M',analysis_frequency='M',
                observed=int(observed.sum()),missing=int((~observed).sum()),coverage=float(observed.mean()),
                first_observed=frame.loc[observed,'month'].min() if observed.any() else '',last_observed=frame.loc[observed,'month'].max() if observed.any() else '',
                dependencies=json.dumps(d.get('dependencies',[])),temporal_availability=d.get('availability','retrospective'),
                transformation=c.CONFIG['music_adjustment'],definition=d.get('definition',name),eligible=not bool(reason),exclusion_reason=reason,canonical_alias=alias))
    assigned=set(candidates)
    for name in overall:
        if name in assigned: continue
        reason='Private embedding coordinate: no meaningful scalar pairwise estimand' if name.startswith('private_embedding_') else 'Circular phase coordinates require a joint directional model' if name.startswith('debut_season_') else 'Identity, date, categorical label or provenance key'
        exclusions.append(dict(origin='music_column',population='monthly',variable=name,reason=reason,canonical_alias=''))
    months=pd.period_range(*c.CONFIG['months'],freq='M'); dates=months.astype(str)
    shares=overall.set_index('month')[[n for n in overall if n.startswith('genre_share__')]].reindex(dates)
    views=[]
    for label,frame,scope in [('overall',overall,'overall')]+[(str(g),part,'within_genre') for g,part in genre.groupby('primary_genre',sort=True)]:
        f=frame.set_index('month').reindex(dates)
        names=[n for n in kept if n in f]
        y=f[names].astype(float).copy()
        for name in names:
            count=kept[name]['count_column']
            if count and kept[name]['role']=='measurement': y[name]=y[name].where(f[count]>=c.CONFIG['minimum_feature_songs'])
        views.append(dict(name=label,scope=scope,genre='' if scope=='overall' else label,values=y,
            counts=f['distinct_song_count'].to_numpy(float),source_counts=f['source_row_count'].to_numpy(float),
            snapshot_dates=f['snapshot_chart_date'].fillna('').tolist(),metadata={n:copy.deepcopy(kept[n]) for n in names}))
    fixed_definitions=[]; derived_columns={}; baseline=months<pd.Period(c.CONFIG['fixed_composition_training_end'],'M')
    for name,d in sorted(kept.items()):
        if not d['domain'].startswith('lyric') or d['role']!='measurement': continue
        selected=[view for view in views[1:] if name in view['values'] and view['values'].loc[baseline,name].notna().sum()>=c.CONFIG['fixed_composition_minimum_months']]
        if len(selected)<2:
            exclusions.append(dict(origin='fixed_composition',population='monthly',variable=name,reason='Fewer than two genres with 60 measured months before the first training cutoff',canonical_alias=''));continue
        weights=np.array([shares.loc[baseline,'genre_share__'+view['genre']].mean() for view in selected],float); weights/=weights.sum()
        a=np.column_stack([view['values'][name] for view in selected]); complete=np.isfinite(a).all(axis=1)
        current=np.column_stack([shares['genre_share__'+view['genre']] for view in selected]); denom=current.sum(axis=1)
        fixed=np.where(complete,a@weights,np.nan); matched=np.where(complete & (denom>0),np.sum(a*current,axis=1)/np.where(denom>0,denom,np.nan),np.nan)
        for prefix,values in [('fixed_composition__',fixed),('matched_composition__',matched)]:
            new=prefix+name; meta=copy.deepcopy(d); meta.update(name=new,dependencies=[name]+['genre_share__'+v['genre'] for v in selected],
                definition='Fixed genre-weight mean, weights learned before the first training cutoff' if prefix.startswith('fixed') else 'Contemporaneous genre-weight mean on the identical supported-genre cohort',
                profile='time' if prefix.startswith('fixed') else 'composition',composition_variant=prefix[:-2],count_column='')
            derived_columns[new]=values; views[0]['metadata'][new]=meta
            inventory.append(dict(variable=new,origin='music',population='monthly',domain=meta['domain'],family=meta['family'],kind='numeric',
                source=json.dumps(meta['source']),units=meta.get('units','source units'),frequency='M',analysis_frequency='M',
                observed=int(np.isfinite(values).sum()),missing=int((~np.isfinite(values)).sum()),coverage=float(np.isfinite(values).mean()),
                dependencies=json.dumps(meta['dependencies']),temporal_availability='Weights fitted before 1983; retrospective source measurements',
                transformation=c.CONFIG['music_adjustment'],definition=meta['definition'],eligible=bool(np.isfinite(values).any()),exclusion_reason='' if np.isfinite(values).any() else 'No complete fixed-genre months'))
        fixed_definitions.append(dict(base_variable=name,genres=[v['genre'] for v in selected],weights=weights.tolist(),training_end=str(pd.Period(c.CONFIG['fixed_composition_training_end'],'M')-1),
                                      observed_complete_months=int(complete.sum()),missing_genres_not_renormalized=True))
    views[0]['values']=pd.concat([views[0]['values'],pd.DataFrame(derived_columns,index=views[0]['values'].index)],axis=1)
    # Per-view constants are structurally invalid; low sample size stays attempted.
    for number,view in enumerate(views):
        view['id']=number
        retained=[]
        for name in view['values']:
            values=view['values'][name].dropna()
            if values.nunique()<2:
                exclusions.append(dict(origin='music_view',population=view['name'],variable=name,reason='Empty or constant after declared observation-support mask',canonical_alias=''))
            else: retained.append(name)
        view['values']=view['values'][retained]; view['metadata']={n:view['metadata'][n] for n in retained}
    c.write_json(c.PUBLIC/'fixed_composition.json',fixed_definitions)
    c.write_json(c.PUBLIC/'music_view_validation.json',dict(status='PASS',original_monthly_rows=818,original_genre_month_rows=7173,
        first_month=str(months[0]),last_month=str(months[-1]),published_view_agreement=agreement,
        latest_observed_chart=overall.snapshot_chart_date.max(),chart_dates_are_not_release_dates=True,
        month_snapshot_rule='Last supplied Billboard chart in each calendar month; September 2026 ends at September 19 and is incomplete',
        source_rows=int(overall.source_row_count.sum()),distinct_row_ids_unchanged=True))
    return views,shares,inventory,exclusions


def build():
    c.PUBLIC.mkdir(parents=True,exist_ok=True); c.LOCAL.mkdir(parents=True,exist_ok=True)
    views,shares,music_inventory,music_excluded=music_catalog()
    raw,adjusted,ends,external,external_inventory,external_excluded=external_catalog()
    c.save(c.LOCAL/'views.pkl',views); c.save(c.LOCAL/'shares.pkl',shares)
    c.save(c.LOCAL/'external.pkl',dict(raw=raw,adjusted=adjusted,ends=ends,metadata=external))
    c.write_csv(c.PUBLIC/'variable_inventory.csv',music_inventory+external_inventory)
    c.write_csv(c.PUBLIC/'exclusion_log.csv',music_excluded+external_excluded)
    plan=[]; offset=0
    for view in views:
        for name,d in sorted(external.items()):
            for lag in c.CONFIG['lags']:
                for track in c.CONFIG['tracks']:
                    methods=1 if d['kind']=='categorical' else 2
                    row=dict(chunk_id=len(plan),view_id=view['id'],population=view['scope'],genre=view['genre'],external=name,
                        external_domain=d['domain'],external_kind=d['kind'],frequency=d['analysis_frequency'],lag=lag,track=track,
                        music_variables=len(view['values'].columns),method_hypotheses=methods*len(view['values'].columns),offset=offset)
                    offset+=len(view['values'].columns); plan.append(row)
    c.write_csv(c.PUBLIC/'search_space.csv',plan); c.save(c.LOCAL/'plan.pkl',plan)
    counts=dict(music_variables=len(set(n for view in views for n in view['values'])),external_variables=len(external),
        music_view_variables=sum(len(v['values'].columns) for v in views),views=len(views),
        eligible_view_pairs=sum(len(v['values'].columns)*len(external) for v in views),
        lagged_pairs=offset//2,pair_track_rows=offset,method_hypotheses=sum(r['method_hypotheses'] for r in plan),
        chunks=len(plan),lag_count=len(c.CONFIG['lags']),tracks=2,external_domains=sorted({d['domain'] for d in external.values()}))
    c.write_json(c.PUBLIC/'search_counts.json',counts); c.write_json(c.PUBLIC/'protocol.json',c.CONFIG)
    return counts


if __name__=='__main__':
    budget=c.Budget('inventory')
    try:
        c.snapshot_previous(); print(json.dumps(build(),indent=2)); budget.check(True)
    finally: budget.close()
