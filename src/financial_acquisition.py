"""Financial panel v1: retrospective monthly features and strictly gated vintage views.

No fitting, interpolation, or statistical music/finance relationship search.
"""
from __future__ import annotations
import argparse
import calendar
import json
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
from financial_acquisition_common import ROOT,REPORT,PROCESSED,MANIFESTS,write_csv,write_json,sha,atomic,snapshots,source_path

START='1958-01'
END='2026-09'  # Frozen latest complete chart month in the existing music snapshot.
MUSIC=ROOT/'data/public/master_monthly.csv'
PERIODS=[('1958-2026',START,END),('1958-1979',START,'1979-12'),('1980-1999','1980-01','1999-12'),('2000-2019','2000-01','2019-12'),('2020-2026','2020-01',END)]


def boolean(v):return str(v).lower() in {'true','1'}

def strict_native(frame):
    keys=['series_id','observation_date','historical_vintage_date']
    if frame[keys].fillna('').duplicated().any():raise ValueError('Duplicate native observations')
    if not frame.native_frequency.isin(['M','Q','W','D']).all():raise ValueError('Unsupported native frequency')
    for field in ['observation_date','period_end']:
        pd.to_datetime(frame[field],format='%Y-%m-%d',errors='raise')
    if (frame.observation_date>frame.period_end).any():raise ValueError('Reversed observation period')
    if not np.isfinite(frame.value.dropna()).all():raise ValueError('Nonfinite values')
    for sid,g in frame.groupby('series_id'):
        if g.native_frequency.nunique()!=1:raise ValueError('Frequency changes within '+sid)
        if g.observation_date.duplicated().any():raise ValueError('Multiple vintages must have separate series identifiers')
        f=g.native_frequency.iloc[0]
        if f in ['M','Q']:
            p=pd.DatetimeIndex(g.observation_date).to_period(f)
            if not np.array_equal(p.start_time.strftime('%Y-%m-%d'),g.observation_date):raise ValueError('Native period start changed')
            if not np.array_equal(p.end_time.strftime('%Y-%m-%d'),g.period_end):raise ValueError('Native period end changed')
    return frame


def monthly_native(native,specs):
    """One row per calendar month; weekly completeness enforced; Q stays separate."""
    first=min('1926-07',native.observation_date.min()[:7]);months=pd.period_range(first,END,freq='M')
    columns={};availability=[];quarterly=[]
    for sid,g in native.groupby('series_id',sort=True):
        spec=specs[sid];freq=spec['native_frequency'];g=g.sort_values('observation_date').copy()
        g['month']=pd.DatetimeIndex(g.observation_date).to_period('M')
        if freq=='Q':
            for month in pd.period_range(START,END,freq='M'):
                q=month.asfreq('Q');completed=q if month.month%3==0 else q-1
                selected=g.loc[pd.DatetimeIndex(g.observation_date).to_period('Q')==completed]
                row=selected.iloc[0] if len(selected) else None
                quarterly.append(dict(month=str(month),series_id=sid,reference_quarter=str(completed),
                    reference_period_end=str(completed.end_time.date()),age_months=month.ordinal-completed.asfreq('M','end').ordinal,
                    quarter_end_value=row.value if row is not None and month.month%3==0 else np.nan,
                    latest_completed_quarter_value=row.value if row is not None else np.nan,
                    native_frequency='Q',alignment='retrospective; calendar completion is not publication availability',point_in_time_valid=False,
                    source_key=row.source_key if row is not None else spec['source_key'],
                    snapshot_vintage_date=spec['snapshot_vintage_date'],redistribution_permitted=spec['redistribution_permitted']))
            continue
        if sid.startswith('FF_') and freq=='D' or spec['monthly_aggregation'].startswith('event_only'):continue
        values=pd.Series(np.nan,index=months,dtype=float)
        for month,sub in g.groupby('month'):
            if month not in months:continue
            valid=sub.value.dropna();count=len(valid)
            expected=1 if freq=='M' else sum(d.dayofweek==(5 if 'CLAIMS' in sid else 4) for d in pd.date_range(month.start_time,month.end_time)) if freq=='W' else month.days_in_month
            if len(sub)>expected:raise ValueError('Too many source observations for '+sid+' '+str(month))
            complete=count==expected
            # Daily economic news mean has explicitly incomplete calendar coverage.
            value=valid.mean() if count and (complete or freq=='D') else np.nan
            values.loc[month]=value
            if START<=str(month)<=END:
                availability.append(dict(month=str(month),series_id=sid,native_frequency=freq,source_rows=len(sub),valid_source_rows=count,
                    expected_source_rows=expected,calendar_complete=complete,monthly_value_available=pd.notna(value),
                    aggregation=spec['monthly_aggregation'],source_keys=';'.join(sorted(sub.source_key.unique())),
                    source_hashes=';'.join(sorted(sub.source_sha256.unique())),
                    historical_publication_dates=';'.join(sorted(x for x in sub.original_publication_date.fillna('').unique() if x)),
                    snapshot_vintage_date=spec['snapshot_vintage_date'],retrieved_at=sub.retrieved_at.max()))
        columns[sid]=values
    return pd.DataFrame(columns,index=months),pd.DataFrame(availability),pd.DataFrame(quarterly)


def period_growth(x,n):
    # An n-month level change needs its two observed endpoints; no forward fill.
    return 100*(x/x.shift(n)-1)


def compound(x,n):return 100*((1+x/100).rolling(n,min_periods=n).apply(np.prod,raw=True)-1)


def wealth(x):
    """After first valid return, any missing month invalidates the cumulative path."""
    out=pd.Series(np.nan,index=x.index,dtype=float);valid=x.first_valid_index()
    if valid is not None:out.loc[valid:]=(1+x.loc[valid:]/100).cumprod(skipna=False)
    return out


def window_mdd(w):
    return float(np.min(w/np.maximum.accumulate(w)-1)*100)


def online_regime(w):
    """No backdating: bear begins at 20% drawdown, ends at 20% rise from bear low."""
    result=pd.Series(np.nan,index=w.index);peak=1.;low=np.nan;bear=False
    for key,value in w.items():
        if pd.isna(value):continue
        peak=max(peak,value)
        if not bear and value/peak-1<=-.2:bear=True;low=value
        if bear:
            low=min(low,value)
            if value/low-1>=.2:bear=False;peak=value
        result.loc[key]=int(bear)
    return result


def derive(raw,native,specs):
    out={};dictionary=[]
    def add(sid,value,unit,formula,parents,caveat='Latest revised source snapshot; trailing by observation time only, not point-in-time.'):
        if not all(p in specs or p in out for p in parents):return
        out[sid]=value
        pinfo=[specs[p] if p in specs else next(d for d in dictionary if d['series_id']==p) for p in parents]
        dictionary.append(dict(series_id=sid,name=sid.replace('_',' ').title(),units=unit,native_frequency='M',
            formula=formula,input_series=';'.join(parents),redistribution_permitted=all(boolean(d['redistribution_permitted']) for d in pinfo),
            point_in_time_eligible=False,coverage_calendar_verified=all(boolean(d.get('coverage_calendar_verified',d.get('native_frequency')!='D')) for d in pinfo),methodological_breaks=caveat))
    if {'FF_MKT_EXCESS','FF_RF'}<=set(raw):
        total=raw.FF_MKT_EXCESS+raw.FF_RF
        if (total.dropna()<=-100).any():raise ValueError('Market return <= -100 percent')
        add('US_MARKET_TOTAL_RETURN',total,'percent per month','MKT_EXCESS + matching monthly RF (percent)', ['FF_MKT_EXCESS','FF_RF'])
        for n in [3,6,12]:add(f'US_MARKET_RETURN_{n}M',compound(total,n),'percent',f'100*(product(1+r/100) over last {n} consecutive months - 1)',['US_MARKET_TOTAL_RETURN'])
        w=wealth(total);high=w.cummax().clip(lower=1)
        add('US_MARKET_DRAWDOWN',100*(w/high-1),'percent <=0','100*(wealth / max(1, all prior and current wealth) - 1); starts July 1926',['US_MARKET_TOTAL_RETURN'])
        add('US_MARKET_MAX_DRAWDOWN_TO_DATE',out['US_MARKET_DRAWDOWN'].cummin(),'percent <=0','Minimum running drawdown up to current month',['US_MARKET_DRAWDOWN'])
        add('US_MARKET_MAX_DRAWDOWN_12M',w.rolling(13,min_periods=13).apply(window_mdd,raw=True),'percent <=0','Worst chronological peak-to-trough loss within last 12 monthly returns, including preceding wealth level',['US_MARKET_TOTAL_RETURN'])
        for n in [12,60]:add(f'US_MARKET_VOLATILITY_{n}M',total.rolling(n,min_periods=n).std(ddof=1)*np.sqrt(12),'annualized percent',f'sample SD of last {n} monthly percent returns * sqrt(12)',['US_MARKET_TOTAL_RETURN'])
        add('US_MARKET_ONLINE_BEAR',online_regime(w),'0/1','Enter bear at <=-20% from running high; exit when >=20% above bear low; no retrospective relabeling',['US_MARKET_TOTAL_RETURN'],
            'Operational 20% hysteresis convention; not an official label; monthly closes can miss intramonth crossings.')
        ratio=w/w.rolling(10,min_periods=10).mean()-1
        state=pd.Series(np.select([ratio>.01,ratio<-.01],[1,-1],default=0),index=w.index,dtype=float).where(ratio.notna())
        add('US_MARKET_TREND_REGIME',state,'-1 bear / 0 consolidation / 1 bull','Current wealth versus inclusive trailing 10-month mean: above +1%=bull, below -1%=bear, else consolidation',['US_MARKET_TOTAL_RETURN'],
            'Predeclared descriptive convention; distinct from drawdown hysteresis; no threshold optimization.')
        daily=native[native.series_id.isin(['FF_MKT_EXCESS_DAILY','FF_RF_DAILY'])].pivot(index='observation_date',columns='series_id',values='value')
        if set(daily)=={'FF_MKT_EXCESS_DAILY','FF_RF_DAILY'}:
            dr=(daily.FF_MKT_EXCESS_DAILY+daily.FF_RF_DAILY)/100
            di=pd.DatetimeIndex(dr.index).to_period('M');values={k:{} for k in ['REALIZED_VOL','DOWNSIDE_VOL','DAILY_COMPOUND_RETURN','DAILY_COUNT']}
            for month,g in dr.groupby(di):
                # Exact calendar is unavailable: count is explicit, no invented holiday list.
                if g.isna().any() or len(g)<15:continue
                values['REALIZED_VOL'][month]=100*np.sqrt(252*np.mean(g*g))
                values['DOWNSIDE_VOL'][month]=100*np.sqrt(252*np.mean(np.minimum(g,0)**2))
                values['DAILY_COMPOUND_RETURN'][month]=100*(np.prod(1+g)-1)
                values['DAILY_COUNT'][month]=len(g)
            forms={'REALIZED_VOL':'100*sqrt(252*mean(daily decimal total return squared))',
                'DOWNSIDE_VOL':'100*sqrt(252*mean(min(daily decimal total return,0)^2)); all observed days in denominator',
                'DAILY_COMPOUND_RETURN':'100*(product(1+daily total return)-1); differs from provider monthly construction',
                'DAILY_COUNT':'Number of daily source observations; >=15 and all valid; trading calendar completeness unverified'}
            for k,d in values.items():add('US_MARKET_'+k,pd.Series(d).reindex(raw.index),'days' if k=='DAILY_COUNT' else 'percent',forms[k],['FF_MKT_EXCESS_DAILY','FF_RF_DAILY'],
                'Observed source trading days; official exchange calendar not independently reconstructed. FIZ/CIZ break and daily/monthly construction difference retained.')
            add('US_MARKET_MONTHLY_DAILY_DIFFERENCE',total-out['US_MARKET_DAILY_COMPOUND_RETURN'],'percentage points','Provider monthly total return minus compounded source daily total return',['US_MARKET_TOTAL_RETURN','US_MARKET_DAILY_COMPOUND_RETURN'])
    for source,prefix in [('US_CPI_SA','CPI'),('US_CPI_NSA','CPI_NSA'),('US_PCE_PRICE_INDEX','PCE')]:
        if source not in raw:continue
        for n,label in [(1,'MOM'),(12,'YOY')]:add(f'US_{prefix}_INFLATION_{label}',period_growth(raw[source],n),'percent',f'100*(index_t/index_t-{n}-1); requires observed current and lagged endpoints',[source])
        add(f'US_{prefix}_INFLATION_ACCELERATION',out[f'US_{prefix}_INFLATION_YOY'].diff(),'percentage points','Current YoY inflation minus prior month YoY inflation',[f'US_{prefix}_INFLATION_YOY'])
    if {'US_HOURLY_EARNINGS_PRODUCTION','US_CPI_SA'}<=set(raw):
        real=100*raw.US_HOURLY_EARNINGS_PRODUCTION/raw.US_CPI_SA
        add('US_REAL_HOURLY_EARNINGS',real,'1982-1984 USD/hour','100*nominal production/nonsupervisory hourly earnings / CPI-U SA',['US_HOURLY_EARNINGS_PRODUCTION','US_CPI_SA'])
        add('US_REAL_WAGE_GROWTH_YOY',period_growth(real,12),'percent','100*(real hourly earnings_t / real hourly earnings_t-12 - 1); requires observed current and lagged endpoints',['US_REAL_HOURLY_EARNINGS'])
    for source,label in [('US_REAL_DISPOSABLE_INCOME','REAL_DISPOSABLE_INCOME'),('US_REAL_DISPOSABLE_INCOME_PC','REAL_DISPOSABLE_INCOME_PC'),('US_IP_TOTAL','IP'),('US_NONFARM_EMPLOYMENT','NONFARM_EMPLOYMENT'),('WB_WTI','WTI'),('WB_GOLD','GOLD')]:
        if source in raw:add('US_'+label+'_GROWTH_YOY',period_growth(raw[source],12),'percent','100*(level_t / level_t-12 - 1); requires observed current and lagged endpoints',[source])
    for sid,a,b in [('US_SLOPE_10Y_TBILL_DISCOUNT','US_TREASURY_10Y','US_TBILL_3M_DISCOUNT'),('US_SLOPE_10Y_3M','US_TREASURY_10Y','US_TREASURY_3M'),('US_SLOPE_10Y_2Y','US_TREASURY_10Y','US_TREASURY_2Y'),('US_BAA_AAA_SPREAD','US_CORPORATE_BAA','US_CORPORATE_AAA'),('US_BAA_TREASURY_SPREAD','US_CORPORATE_BAA','US_TREASURY_10Y'),('US_BREAKEVEN_10Y','US_TREASURY_10Y','US_TIPS_10Y')]:
        if {a,b}<=set(raw):add(sid,raw[a]-raw[b],'percentage points',a+' minus '+b,[a,b],
             'Mixed quote bases/maturity/composition; Treasury bill uses discount basis where explicitly labelled; breakeven includes liquidity/risk premia, not pure expected inflation.')
    if 'US_UNEMPLOYMENT' in raw and 'US_CPI_INFLATION_YOY' in out:add('US_MISERY_INDEX',raw.US_UNEMPLOYMENT+out['US_CPI_INFLATION_YOY'],'percentage points','Unemployment percent SA + CPI-U SA YoY inflation percent',['US_UNEMPLOYMENT','US_CPI_INFLATION_YOY'])
    if 'US_CONSUMER_SENTIMENT' in raw:
        for n in [1,12]:add(f'US_CONSUMER_SENTIMENT_CHANGE_{n}M',raw.US_CONSUMER_SENTIMENT.diff(n),
            'index points',f'Current sentiment index minus value {n} months earlier; requires observed current and lagged endpoints',['US_CONSUMER_SENTIMENT'])
    for sid in ['US_EXCESS_BOND_PREMIUM','US_FCI_G','US_NFCI','US_POLICY_UNCERTAINTY_NEWS','US_BAA_AAA_SPREAD']:
        x=raw[sid] if sid in raw else out.get(sid)
        if x is None:continue
        past=x.shift(1);mean=past.rolling(120,min_periods=60).mean();std=past.rolling(120,min_periods=60).std(ddof=1)
        # Reject gaps within the most recent 60 months; use up to 120 observed consecutive months.
        valid=past.notna().rolling(60,min_periods=60).sum().eq(60)
        add(sid+'_TRAILING_Z',(x-mean).div(std.where(std>0)).where(valid),'trailing standard deviations',
            '(current minus mean of prior up-to-120 months) / prior sample SD; >=60 prior values and last 60 months gap-free; current excluded',[sid],
            'Uses past observations for standardization; provider inputs may be revised/full-sample estimated, so not point-in-time.')
    return pd.DataFrame(out,index=raw.index),pd.DataFrame(dictionary)


def point_in_time(native):
    rows=[];eligible=native[native.point_in_time_eligible.map(boolean)&native.value.notna()].copy()
    for month in pd.period_range(START,END,freq='M'):
        cutoff=(month+1).start_time.date().isoformat()
        for sid,g in eligible.groupby('series_id'):
            available=g[(g.original_publication_date<cutoff)&(g.historical_vintage_date<cutoff)]
            if available.empty:continue
            # Latest observation known before next-month start; latest value within that series.
            r=available.sort_values(['observation_date','original_publication_date']).iloc[-1]
            rows.append(dict(month=str(month),decision_cutoff_exclusive=cutoff,series_id=sid,value=r.value,
                observation_date=r.observation_date,period_end=r.period_end,publication_date=r.original_publication_date,
                historical_vintage_date=r.historical_vintage_date,retrieved_at=r.retrieved_at,source_key=r.source_key,
                source_sha256=r.source_sha256,age_months=month.ordinal-pd.Period(r.observation_date,'M').ordinal,
                interpretation='latest announced event type, not actual recession state' if 'NBER' in sid else 'provider-retained historical growth value'))
    return pd.DataFrame(rows)


def longest_gap(mask):
    best=run=0
    for v in mask:
        run=run+1 if v else 0;best=max(best,run)
    return best


def audit_coverage(panel,specs,quarterly):
    result=[];missing=[]
    for sid in panel:
        if sid=='month':continue
        s=panel.set_index('month')[sid];spec=specs[sid]
        for label,lo,hi in PERIODS:
            part=s.loc[lo:hi];ok=part.notna();valid=part[ok]
            result.append(dict(series_id=sid,period=label,frequency='monthly_native_or_explicit_aggregation',expected_observations=len(part),
                valid_observations=int(ok.sum()),missing_observations=int((~ok).sum()),coverage_percent=100*ok.mean(),
                first_valid=valid.index.min() if len(valid) else '',last_valid=valid.index.max() if len(valid) else '',
                longest_missing_gap_months=longest_gap(~ok),full_history_complete=bool(ok.all() and label=='1958-2026' and boolean(spec.get('coverage_calendar_verified',spec.get('native_frequency')!='D'))),
                redistribution_permitted=spec['redistribution_permitted'],methodological_breaks=spec['methodological_breaks']))
        valid=s.dropna();start=end=None
        for month,value in list(s.items())+[('END',0.)]:
            if pd.isna(value):
                if start is None:start=month
                end=month
            elif start is not None:
                missing.append(dict(series_id=sid,start_month=start,end_month=end,months=pd.Period(end,'M').ordinal-pd.Period(start,'M').ordinal+1,
                    gap_class='outside_downloaded_valid_range' if valid.empty or end<valid.index.min() or start>valid.index.max() else 'internal_or_transform_window_gap'))
                start=end=None
    return pd.DataFrame(result),pd.DataFrame(missing)


def native_coverage(native,specs):
    rows=[]
    for sid,g in native.groupby('series_id'):
        f=specs[sid]['native_frequency'];d=pd.to_datetime(g.observation_date)
        for label,lo,hi in PERIODS:
            a=pd.Period(lo,'M').start_time;b=pd.Period(hi,'M').end_time
            sub=g[(d>=a)&(d<=b)];valid=sub[sub.value.notna()]
            freq={'M':'MS','Q':'QS','W':'W-SAT' if 'CLAIMS' in sid else 'W-FRI','D':'D'}[f]
            grid=pd.date_range(a,b,freq=freq);expected=len(grid)
            exact=f!='D' or sid=='US_ECONOMIC_NEWS_SENTIMENT'
            rows.append(dict(series_id=sid,period=label,native_frequency=f,first_valid=valid.observation_date.min() if len(valid) else '',
                last_valid=valid.observation_date.max() if len(valid) else '',downloaded_rows=len(sub),valid_observations=len(valid),
                expected_observations=expected if exact else '',expected_basis='calendar days, including article-free days' if f=='D' and exact else 'event/trading calendar unknown' if not exact else 'native periods',
                missing_observations=expected-len(valid) if exact else '',coverage_percent=100*len(valid)/expected if exact else '',
                longest_missing_gap_native_periods=longest_gap(~grid.isin(pd.to_datetime(valid.observation_date))) if exact else '',
                complete_native_history=bool(exact and len(valid)==expected and label=='1958-2026')))
    return pd.DataFrame(rows)


def sample_music_join(panel):
    cols=['month','snapshot_chart_date','song_id','primary_genre','detox_toxicity','ll_violence','sentiment_negative']
    music=pd.read_csv(MUSIC,usecols=cols);music.primary_genre=music.primary_genre.fillna('Unknown')
    if not (pd.to_datetime(music.snapshot_chart_date).dt.strftime('%Y-%m')==music.month).all():raise ValueError('Music snapshot month inconsistent')
    if music.month.max()!=END:raise ValueError('Music snapshot changed; choose a new version explicitly')
    scores=['detox_toxicity','ll_violence','sentiment_negative'];frames=[]
    for genre,sub in [('All genres',music)]+list(music.groupby('primary_genre',sort=True)):
        grouped=sub.groupby('month');summary=grouped.song_id.agg(source_rows='size',distinct_song_ids='nunique')
        for score in scores:
            summary[score+'_mean']=grouped[score].mean();summary[score+'_n']=grouped[score].count()
        summary=summary.reset_index();summary['genre']=genre;frames.append(summary)
    summaries=pd.concat(frames,ignore_index=True)
    keep=['month']+[s for s in ['US_UNEMPLOYMENT','US_CPI_INFLATION_YOY','US_FED_FUNDS','US_IP_TOTAL','US_EXCESS_BOND_PREMIUM'] if s in panel]
    joined=summaries.merge(panel[keep],on='month',how='left',validate='many_to_one',indicator=True)
    if not joined._merge.eq('both').all():raise ValueError('Unmatched music calendar month')
    if joined.duplicated(['month','genre']).any():raise ValueError('Duplicate music summary key')
    selected=['1958-08','1980-01','2000-01','2020-01','2020-04','2026-09']
    sample=joined[joined.month.isin(selected)].drop(columns='_merge').sort_values(['month','genre'])
    audit=dict(source_rows=len(music),distinct_songs=music.song_id.nunique(),source_duplicate_song_month_rows=int(music.duplicated(['song_id','month']).sum()),
        months=music.month.nunique(),first_month=music.month.min(),last_month=music.month.max(),summary_rows=len(summaries),
        joined_rows=len(joined),sample_rows=len(sample),music_sha256=sha(MUSIC),weighting='Equal retained source rows; available-case mean per score; count and distinct song count separate',
        calendar='Chart snapshot month; calendar-month retrospective finance may include dates after snapshot chart day; not a forecasting dataset')
    return sample,audit


def build(public=False,publish=True):
    mode='public' if public else 'local';native=strict_native(pd.read_csv(PROCESSED/f'native_{mode}.csv.xz',keep_default_na=False,na_values={'value':['']},float_precision='round_trip'))
    specs={r['series_id']:r for r in pd.read_csv(REPORT/'series_dictionary.csv',keep_default_na=False).to_dict('records')}
    specs={k:v for k,v in specs.items() if k in set(native.series_id)}
    raw,availability,quarterly=monthly_native(native,specs);derived,dd=derive(raw,native,specs)
    allspec={**specs,**{r['series_id']:r for r in dd.to_dict('records')}}
    combined=pd.concat([raw,derived],axis=1).loc[START:END]
    if combined.columns.duplicated().any() or len(combined)!=825:raise ValueError('Panel dimensions changed')
    if not np.isfinite(combined.to_numpy()[~combined.isna()]).all():raise ValueError('Infinite derived values')
    panel=combined.rename_axis('month').reset_index();panel.month=panel.month.astype(str)
    coverage,missing=audit_coverage(panel,allspec,quarterly)
    sample,join_audit=sample_music_join(panel)
    pit=point_in_time(native)
    native_cov=native_coverage(native,specs)
    availability=availability.sort_values(['month','series_id']);quarterly=quarterly.sort_values(['month','series_id'])
    frames={}
    def output(suffix,allowed):
        ids={s for s in allspec if not allowed or boolean(allspec[s]['redistribution_permitted'])}
        sub=panel[['month']+[s for s in panel if s in ids]]
        frames[PROCESSED/f'monthly_{suffix}.csv.xz']=sub
        frames[PROCESSED/f'missingness_{suffix}.csv.xz']=pd.concat([sub[['month']],sub.drop(columns='month').isna().astype('int8')],axis=1)
        frames[PROCESSED/f'aggregation_metadata_{suffix}.csv.xz']=availability[availability.series_id.isin(ids)]
        frames[PROCESSED/f'quarterly_alignment_{suffix}.csv.xz']=quarterly[quarterly.series_id.isin(ids)]
        frames[PROCESSED/f'point_in_time_{suffix}.csv.xz']=pit[pit.series_id.isin(ids)]
    if not public:output('local',False)
    output('public',True)
    frames[PROCESSED/'music_join_sample.csv']=sample
    if not public:
        frames[REPORT/'derived_feature_dictionary.csv']=dd
        frames[REPORT/'coverage_report.csv']=coverage
        frames[REPORT/'missingness_report.csv']=missing
        frames[REPORT/'native_coverage_report.csv']=native_cov
        frames[REPORT/'source_manifest.csv']=pd.DataFrame(list(snapshots().values()))
    # Every table validates before any published file is replaced; manifest is written last.
    hashes={}
    if publish:
        with tempfile.TemporaryDirectory(prefix='financial-build-') as directory:
            staged=[]
            for i,(target,frame) in enumerate(frames.items()):
                temp=Path(directory)/(str(i)+('.csv.xz' if str(target).endswith('.xz') else '.csv'));write_csv(temp,frame)
                check=pd.read_csv(temp)
                if len(check)!=len(frame) or list(check)!=list(frame):raise ValueError('Round-trip shape changed')
                staged.append((target,temp));hashes[str(target.relative_to(ROOT))]=sha(temp)
            for target,temp in staged:atomic(target,temp.read_bytes())
        if not public:
            write_json(REPORT/'music_join_validation.json',join_audit)
            summary=dict(version='financial_acquisition_v1',start=START,end=END,monthly_rows=len(panel),native_series=len(specs),
                native_observations=len(native),monthly_raw_columns=len(raw.columns),derived_columns=len(dd),
                monthly_columns=len(panel.columns)-1,quarterly_series=int((pd.Series([s['native_frequency'] for s in specs.values()])=='Q').sum()),
                public_monthly_columns=sum(boolean(allspec[s]['redistribution_permitted']) for s in combined),
                monthly_missing_cells=int(combined.isna().sum().sum()),monthly_total_cells=int(combined.size),
                full_monthly_columns=int(coverage.loc[coverage.period.eq('1958-2026'),'full_history_complete'].sum()),
                point_in_time_series=sorted(pit.series_id.unique().tolist()),music_join=join_audit)
            write_json(REPORT/'build_summary.json',summary)
            write_json(MANIFESTS/'build.json',dict(summary=summary,artifacts=hashes,inputs={'native_local':sha(PROCESSED/'native_local.csv.xz'),
                'native_public':sha(PROCESSED/'native_public.csv.xz'),'series_dictionary':sha(REPORT/'series_dictionary.csv'),'music':sha(MUSIC)},
                code={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'src/financial_acquisition_common.py',ROOT/'src/financial_acquisition_sources.py']}))
    return panel,allspec,frames


def validate(private=False):
    manifest=json.loads((MANIFESTS/'build.json').read_text());checked=0
    for rel,digest in manifest['artifacts'].items():
        if '_local.' in rel and not private:continue
        if sha(ROOT/rel)!=digest:raise ValueError('Artifact hash mismatch: '+rel)
        checked+=1
    for rel,digest in manifest['code'].items():
        if sha(ROOT/rel)!=digest:raise ValueError('Code hash mismatch: '+rel)
    if sha(MUSIC)!=manifest['inputs']['music']:raise ValueError('Music input changed')
    for suffix in ['public']+(['local'] if private else []):
        if sha(PROCESSED/f'native_{suffix}.csv.xz')!=manifest['inputs']['native_'+suffix]:raise ValueError('Native input changed')
    if sha(REPORT/'series_dictionary.csv')!=manifest['inputs']['series_dictionary']:raise ValueError('Series dictionary changed')
    panel,_,frames=build(public=not private,publish=False)
    with tempfile.TemporaryDirectory() as tmp:
        for target,frame in frames.items():
            temp=Path(tmp)/target.name;write_csv(temp,frame)
            if sha(temp)!=sha(target):raise ValueError('Offline replay mismatch: '+str(target))
    if private:
        for key,row in snapshots().items():
            if row['status']=='ok':source_path(key)
    print(json.dumps(dict(status='PASS',artifacts=checked,offline_replay_tables=len(frames),rows=len(panel),private=private),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','validate']);p.add_argument('--public',action='store_true');p.add_argument('--private',action='store_true');a=p.parse_args()
    if a.action=='validate':validate(a.private)
    else:
        panel,_,_=build(public=a.public);print(json.dumps(dict(rows=len(panel),columns=len(panel.columns)-1,public=a.public)))
