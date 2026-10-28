"""Deterministic historical transformations; natural frequencies, no implicit fills."""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

from enrichment_common import EXTERNAL, HISTORY, sha, write_csv, write_json


def source_observations():
    paths=[EXTERNAL/category/'observations.csv.xz' for category in ['financial','macroeconomic','political','social','cultural']]
    frame=pd.concat([pd.read_csv(p,keep_default_na=False,low_memory=False) for p in paths],ignore_index=True)
    frame['value']=pd.to_numeric(frame.value.replace('',np.nan),errors='raise')
    if frame[['series_id','date','vintage_date']].duplicated().any():raise ValueError('Duplicate external observation')
    return frame


def monthly_matrix(frame):
    subset=frame.loc[frame.frequency.eq('M')]
    if subset[['series_id','date']].duplicated().any():raise ValueError('Select a vintage explicitly before pivoting')
    wide=subset.pivot(index='date',columns='series_id',values='value')
    wide.index=pd.PeriodIndex(wide.index,freq='M')
    # Missing calendar months stay missing, including inside rolling windows.
    return wide.reindex(pd.period_range(wide.index.min(),wide.index.max(),freq='M'))


def compounded(series,periods):
    if (series.dropna()<=-100).any():raise ValueError('Total return must exceed -100 percent')
    return (1+series/100).rolling(periods,min_periods=periods).apply(np.prod,raw=True).sub(1).mul(100)


def drawdown(series):
    """Running total-return drawdown; no restart across missing months."""
    first=series.first_valid_index()
    if first is None:return series.copy()
    valid=series.loc[first:]
    if valid.isna().any():raise ValueError('Cumulative wealth cannot silently bridge missing returns')
    wealth=(1+valid/100).cumprod()
    peak=wealth.cummax().clip(lower=1.)
    return (wealth/peak-1).mul(100).reindex(series.index)


def build():
    source=source_observations();matrix=monthly_matrix(source)
    specifications=pd.read_csv(HISTORY/'series_dictionary.csv',keep_default_na=False).set_index('series_id')
    rows=[];definitions=[]
    def add(sid,name,values,units,parents,formula,category=None):
        parentspec=specifications.loc[parents];permitted=bool(parentspec.redistribution_permitted.all())
        spec={'series_id':sid,'name':name,'frequency':'M','units':units,'geography':'USA',
            'source':'Derived from '+ '; '.join(sorted(set(parentspec.source))),
            'source_url':'; '.join(sorted(set(parentspec.source_url))),
            'retrieval_date':max(parentspec.retrieval_date),'publication_date':'','vintage_date':'',
            'availability_status':'retrospective_derived_snapshot','license':'; '.join(sorted(set(parentspec.license))),
            'transformation':formula,'category':category or parentspec.category.iloc[0],
            'redistribution_permitted':permitted,'parent_series':json.dumps(parents),
            'notes':'No historical availability assumed; each transformation requires all stated observations. Null inputs stay null.'}
        definitions.append(spec)
        for period,value in values.items():
            rows.append(dict(spec,date=period.start_time.date().isoformat(),period_end=period.end_time.date().isoformat(),value=value,
                source_status='complete_required_inputs' if pd.notna(value) else 'missing_required_input_or_window'))
    market=(matrix.FF_MKT_EXCESS+matrix.FF_RF)
    # Only the source return span belongs to this cumulative index, not later
    # calendar indicators for which market returns have not yet been released.
    market=market.loc[matrix.FF_MKT_EXCESS.first_valid_index():matrix.FF_MKT_EXCESS.last_valid_index()]
    add('US_EQUITY_TOTAL_RETURN','US value-weighted equity total return',market,'percent per month',
        ['FF_MKT_EXCESS','FF_RF'],'Mkt-RF + RF in source percent units; CRSP universe, dividends included')
    for n in [3,12,60]:
        add(f'US_EQUITY_RETURN_{n}M',f'Trailing {n}-month equity total return',compounded(market,n),'percent over trailing window',
            ['FF_MKT_EXCESS','FF_RF'],f'100*(product(1+(Mkt-RF+RF)/100) over {n} contiguous months - 1)')
    add('US_EQUITY_DRAWDOWN','Total-return drawdown from running wealth peak',drawdown(market),'percent below running peak',
        ['FF_MKT_EXCESS','FF_RF'],'100*(cumulative wealth / max(1, cumulative wealth history) - 1); base wealth=1 before first source month')
    for n in [12,60]:
        add(f'US_EQUITY_LOG_VOL_{n}M',f'Trailing {n}-month annualized equity volatility',
            np.log1p(market/100).rolling(n,min_periods=n).std(ddof=1)*np.sqrt(12)*100,'percent annualized log-return SD',
            ['FF_MKT_EXCESS','FF_RF'],f'sample SD of {n} contiguous monthly log total returns * sqrt(12)*100')
    daily=source.loc[source.series_id.isin(['FF_MKT_EXCESS_DAILY','FF_RF_DAILY'])].pivot(index='date',columns='series_id',values='value')
    daily.index=pd.to_datetime(daily.index);daily['total']=daily.FF_MKT_EXCESS_DAILY+daily.FF_RF_DAILY
    daily['month']=daily.index.to_period('M');group=daily.groupby('month')
    monthly=pd.DataFrame(index=sorted(set(daily.month)&set(market.dropna().index)))
    for month in monthly.index:
        block=group.get_group(month)['total']
        if block.isna().any() or (block<=-100).any():raise ValueError('Incomplete/invalid daily research returns')
        logs=np.log1p(block/100)
        monthly.loc[month,'return']=np.expm1(logs.sum())*100
        monthly.loc[month,'realized_vol']=np.sqrt((logs**2).sum())*100
        monthly.loc[month,'downside_vol']=np.sqrt((np.minimum(logs,0)**2).sum())*100
        monthly.loc[month,'observed_trading_days']=len(block)
    for name,label,unit,formula in [
        ('return','Daily-compounded equity total return','percent per month','100*(product(1+(daily Mkt-RF+RF)/100)-1)'),
        ('realized_vol','Monthly realized equity volatility','percent log return, not annualized','100*sqrt(sum(daily log total return squared))'),
        ('downside_vol','Monthly downside realized equity volatility','percent log return, not annualized','100*sqrt(sum(min(daily log total return,0) squared))'),
        ('observed_trading_days','Daily equity observations in source month','days','Count source daily rows; only months also present in monthly source; not a trading-calendar completeness certification')]:
        add('US_EQUITY_DAILY_'+name.upper(),label,monthly[name],unit,['FF_MKT_EXCESS_DAILY','FF_RF_DAILY'],formula)
    daily_check=pd.DataFrame({'month':monthly.index.astype(str),'daily_compounded_percent':monthly['return'].values,
        'published_monthly_percent':market.reindex(monthly.index).values})
    daily_check['difference_percentage_points']=daily_check.daily_compounded_percent-daily_check.published_monthly_percent
    write_csv(EXTERNAL/'derived/daily_monthly_return_comparison.csv.xz',daily_check)
    for sid,left,right,name in [
        ('US_YIELD_SLOPE_10Y_2Y','US_TREASURY_10Y','US_TREASURY_2Y','10-year minus 2-year constant maturity Treasury yield'),
        ('US_YIELD_SLOPE_10Y_3M','US_TREASURY_10Y','US_TREASURY_3M','10-year minus 3-month constant maturity Treasury yield'),
        ('US_CP_FINANCIAL_NONFINANCIAL_SPREAD','US_AA_FINANCIAL_CP_3M','US_AA_NONFINANCIAL_CP_3M','3-month financial minus nonfinancial AA commercial paper rate'),
        ('US_CP_TBILL_DISCOUNT_SPREAD','US_AA_NONFINANCIAL_CP_3M','US_TBILL_3M_DISCOUNT','3-month AA nonfinancial CP minus Treasury bill discount rate'),
        ('US_TREASURY_TIPS_10Y_SPREAD','US_TREASURY_10Y','US_TIPS_10Y','10-year nominal minus inflation-indexed Treasury yield')]:
        add(sid,name,matrix[left]-matrix[right],'percentage points',[left,right],left+' minus '+right+'; liquidity and instrument differences remain; not pure credit risk or inflation expectations')
    for parent,stem,label in [('US_CPI_SA','US_CPI','CPI-U'),('US_PCE_PRICE_INDEX','US_PCE_PRICE','PCE prices'),
        ('US_REAL_DISPOSABLE_INCOME_PC','US_REAL_DISPOSABLE_INCOME_PC','Real disposable income per capita'),
        ('US_IP_TOTAL','US_IP_TOTAL','Industrial production'),('US_NONFARM_EMPLOYMENT','US_NONFARM_EMPLOYMENT','Nonfarm employment'),
        ('US_RECREATION_GOODS_REAL','US_RECREATION_GOODS_REAL','Real recreation goods expenditure'),
        ('US_RECREATION_SERVICES_REAL','US_RECREATION_SERVICES_REAL','Real recreation services expenditure')]:
        for lag,term in [(1,'MOM'),(12,'YOY')]:
            add(stem+'_'+term,label+' '+term.lower()+' growth',matrix[parent].pct_change(lag,fill_method=None)*100,
                'percent change',[parent],f'100*(x[t]/x[t-{lag}]-1); calendar month lag; no fill')
    real_hourly=matrix.US_HOURLY_EARNINGS_PRODUCTION/(matrix.US_CPI_NSA/100)
    add('US_REAL_HOURLY_EARNINGS_PRODUCTION','CPI-deflated private production hourly earnings',real_hourly,'1982-1984 purchasing-power USD/hour',
        ['US_HOURLY_EARNINGS_PRODUCTION','US_CPI_NSA'],'SA nominal earnings / (NSA CPI-U/100); mixed seasonal adjustment is explicit; use YoY change for seasonal comparison','macroeconomic')
    add('US_REAL_HOURLY_EARNINGS_YOY','Real private production hourly earnings YoY change',real_hourly.pct_change(12,fill_method=None)*100,'percent change year-over-year',
        ['US_HOURLY_EARNINGS_PRODUCTION','US_CPI_NSA'],'100*((earnings[t]/CPI[t])/(earnings[t-12]/CPI[t-12])-1)','macroeconomic')
    for sid in sorted(source.loc[source.series_id.str.startswith('US_OXCGRT_'),'series_id'].unique()):
        data=source.loc[source.series_id.eq(sid)].copy();data['month']=pd.to_datetime(data.date).dt.to_period('M')
        values={}
        for month,block in data.groupby('month',sort=True):
            if block.date.nunique()!=month.days_in_month or block.value.isna().any():continue
            values[month]=float(block.value.mean())
        add(sid.removesuffix('_DAILY')+'_MONTHLY_MEAN',specifications.loc[sid,'name']+' monthly mean',pd.Series(values),'index points 0-100',
            [sid],'Arithmetic mean of source daily index only when every calendar day has a value; no filling outside coverage','political')
    derived=pd.DataFrame(rows)
    # Empty dates outside a feature's parent-source span carry no observation.
    derived=derived.loc[derived.value.notna()].sort_values(['series_id','date']).reset_index(drop=True)
    all_data=pd.concat([source,derived],ignore_index=True).sort_values(['series_id','date','vintage_date']).reset_index(drop=True)
    write_csv(EXTERNAL/'derived/all_observations.csv.xz',all_data)
    cleared=all_data.loc[all_data.redistribution_permitted.eq(True)]
    write_csv(EXTERNAL/'derived/permitted_observations.csv.xz',cleared)
    write_csv(HISTORY/'derived_series_dictionary.csv',definitions)
    coverage=[]
    for sid,group in all_data.groupby('series_id',sort=True):
        valid=group.loc[group.value.notna()];spec=group.iloc[0]
        coverage.append({'series_id':sid,'category':spec.category,'frequency':spec.frequency,'rows':len(group),
            'nonnull':len(valid),'missing_source_values':int(group.value.isna().sum()),'first_date':valid.date.min() if len(valid) else '',
            'last_date':valid.date.max() if len(valid) else '',
            'original_publication_dated':int((valid.availability_status.eq('historical_release_vintage')&valid.publication_date.fillna('').ne('')).sum()),
            'redistribution_permitted':bool(spec.redistribution_permitted)})
    write_csv(HISTORY/'coverage_report.csv',coverage)
    write_json(HISTORY/'transformation_summary.json',{'source_series':source.series_id.nunique(),'source_rows':len(source),
        'derived_series':len(definitions),'derived_rows':len(derived),'all_rows':len(all_data),'permitted_rows':len(cleared),
        'daily_monthly_comparison_months':len(daily_check),'daily_monthly_max_absolute_difference_pp':float(daily_check.difference_percentage_points.abs().max()),
        'daily_monthly_disagreement_note':'Daily and monthly RF and historical FIZ/CIZ construction differ; preserve both, never silently replace published monthly returns',
        'code_sha256':sha(__file__)})
    return all_data


if __name__=='__main__':build()
