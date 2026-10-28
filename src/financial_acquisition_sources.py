"""Source acquisition and strict native-frequency parsers; no music modelling."""
from __future__ import annotations
import argparse
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from html import unescape
import numpy as np
import pandas as pd
from financial_acquisition_common import ROOT,REPORT,PROCESSED,MANIFESTS,source_path,snapshots,snapshot,write_json,write_csv,sha,restore_snapshots

BLS={
 'LNS14000000':('US_UNEMPLOYMENT','Unemployment rate','percent SA'),
 'LNS14000012':('US_YOUTH_UNEMPLOYMENT','Unemployment rate age 16-19','percent SA'),
 'LNS11300000':('US_LABOR_PARTICIPATION','Labor force participation rate','percent SA'),
 'LNS12300000':('US_EMPLOYMENT_POPULATION','Employment-population ratio','percent SA'),
 'CES0000000001':('US_NONFARM_EMPLOYMENT','Nonfarm employment','thousand persons SA'),
 'CES0500000008':('US_HOURLY_EARNINGS_PRODUCTION','Production/nonsupervisory hourly earnings','USD/hour SA'),
 'CES0500000002':('US_WEEKLY_HOURS_ALL_PRIVATE','Private all-employee weekly hours','hours SA'),
 'CUSR0000SA0':('US_CPI_SA','CPI-U all items','index 1982-1984=100 SA'),
 'CUUR0000SA0':('US_CPI_NSA','CPI-U all items NSA','index 1982-1984=100 NSA')}
H15={
 'RIFSPFF_N.M':('US_FED_FUNDS','Effective federal funds rate'),
 'RIFSPBLP_N.M':('US_PRIME_RATE','Bank prime loan rate'),
 'RIFSGFSM03_N.M':('US_TBILL_3M_DISCOUNT','3-month Treasury bill discount yield'),
 'RIFLGFCM03_N.M':('US_TREASURY_3M','3-month Treasury constant maturity yield'),
 'RIFLGFCY02_N.M':('US_TREASURY_2Y','2-year Treasury constant maturity yield'),
 'RIFLGFCY10_N.M':('US_TREASURY_10Y','10-year Treasury constant maturity yield'),
 'RIFLGFCY10_XII_N.M':('US_TIPS_10Y','10-year TIPS real yield'),
 'RIFSPPFAAD90_N.M':('US_FINANCIAL_CP_3M','3-month financial commercial paper yield'),
 'RIMLPAAAR_N.M':('US_CORPORATE_AAA','Moody seasoned Aaa corporate yield'),
 'RIMLPBAAR_N.M':('US_CORPORATE_BAA','Moody seasoned Baa corporate yield')}
BEA=[
 (1,'T10106-Q','A191RX','US_REAL_GDP','Real GDP','million chained 2017 USD SAAR'),
 (1,'T10105-Q','A191RC','US_NOMINAL_GDP','Nominal GDP','million USD SAAR'),
 (1,'T10109-Q','A191RD','US_GDP_DEFLATOR','GDP implicit price deflator','index 2017=100 SA'),
 (2,'T20600-M','A065RC','US_PERSONAL_INCOME','Personal income','million USD SAAR'),
 (2,'T20600-M','A067RC','US_DISPOSABLE_INCOME','Disposable personal income','million USD SAAR'),
 (2,'T20600-M','A067RX','US_REAL_DISPOSABLE_INCOME','Real disposable income','million chained 2017 USD SAAR'),
 (2,'T20600-M','A229RX','US_REAL_DISPOSABLE_INCOME_PC','Real disposable income per capita','chained 2017 USD SAAR'),
 (2,'T20600-M','A072RC','US_PERSONAL_SAVING_RATE','Personal saving rate','percent SA'),
 (2,'T20600-M','W825RC','US_UNEMPLOYMENT_BENEFITS','Unemployment insurance benefits','million USD SAAR'),
 (2,'T20804-M','DPCERG','US_PCE_PRICE_INDEX','PCE price index','index 2017=100 SA'),
 (2,'T20805-M','DPCERC','US_PCE_NOMINAL','Personal consumption expenditures','million USD SAAR'),
 (2,'T20806-M','DPCERX','US_PCE_REAL','Real personal consumption expenditures','million chained 2017 USD SAAR'),
 (2,'T20806-M','DREQRX','US_RECREATION_GOODS_REAL','Real recreation goods/vehicles consumption','million chained 2017 USD SAAR'),
 (2,'T20806-M','DRCARX','US_RECREATION_SERVICES_REAL','Real recreation services consumption','million chained 2017 USD SAAR')]

def acquire():
    ext=ROOT/'data/external_historical'
    for relative in ['financial/raw/H15.zip','financial/raw/ff_monthly.zip','financial/raw/ff_daily.zip',
            'macroeconomic/raw/BEA_Section1.xlsx','macroeconomic/raw/BEA_Section2.xlsx',
            'macroeconomic/raw/g17_ip_sa.txt','macroeconomic/raw/g17_revisions.txt','macroeconomic/raw/g17_release_dates.html',
            'macroeconomic/raw/g17_dictionary.txt','macroeconomic/raw/umich_monthly_1.csv','macroeconomic/raw/umich_Q_1.csv',
            'macroeconomic/raw/umich_terms.html','macroeconomic/raw/nber_cycles.xlsx','macroeconomic/raw/nber_faq.html']:
        p=ext/relative;meta=json.loads(p.with_name(p.name+'.provenance.json').read_text())
        snapshot(p.stem,meta['url'],reuse=str(p.relative_to(ROOT)),extension=p.suffix,
                 form=meta.get('request') if 'umich_' in p.stem else None)
    for start in range(1958,2027,10):
        p=ext/f'macroeconomic/raw/bls_{start}_{min(start+9,2026)}.json'
        meta=json.loads(p.with_name(p.name+'.provenance.json').read_text())
        snapshot(p.stem,meta['url'],reuse=str(p.relative_to(ROOT)),extension='.json',post=meta.get('request'))
    # Earlier observations supply trailing-feature warm-up; never overwrite caches.
    snapshot('bls_warmup','https://api.bls.gov/publicAPI/v2/timeseries/data/',extension='.json',
             post={'seriesid':list(BLS),'startyear':'1956','endyear':'1957'})
    sources=[
      ('nfci','https://api.data.chicagofed.org/NFCI/nfci-data-series-csv.csv','.csv'),
      ('ebp','https://www.federalreserve.gov/econresdata/notes/feds-notes/2016/files/ebp_csv.csv','.csv'),
      ('fci_g','https://www.federalreserve.gov/econres/notes/feds-notes/fci_g_public_monthly_3yr.csv','.csv'),
      ('news_sentiment','https://www.frbsf.org/wp-content/uploads/news_sentiment_data.xlsx','.xlsx'),
      ('epu','https://www.policyuncertainty.com/media/US_Policy_Uncertainty_Data.xlsx','.xlsx'),
      ('pink','https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx','.xlsx'),
      ('dsr','https://www.federalreserve.gov/releases/dsr/data/FRB_dsr_xml.zip','.zip'),
      ('delinquency','https://www.federalreserve.gov/releases/chargeoff/data/FRB_CHGDEL_xml.zip','.zip')]
    for key,url,suffix in sources:snapshot(key,url,extension=suffix)
    snapshot('nfci_manifest','https://data.chicagofed.org/cfed-drm-chicago/NFCI',extension='.json',max_bytes=2_000_000)
    nfci_url=json.loads(source_path('nfci_manifest').read_text())['data']['nfciDataSeriesCsvCsv']
    snapshot('nfci',nfci_url,extension='.csv')
    snapshot('claims','https://oui.doleta.gov/unemploy/wkclaims/report.asp',extension='.xml',
             form={'level':'us','strtdate':'1967','enddate':'2026','final_yr':'2027','filetype':'xml','submit':'Submit'})


def number(value):
    if value is None or pd.isna(value):return np.nan
    text=str(value).strip()
    if text.lower() in {'','-','.','na','n/a','nan','.....','...','…','(na)','(d)','-99.99','-999','-9999','nd'}:return np.nan
    result=float(text.replace(',',''))
    if not np.isfinite(result):raise ValueError('Nonfinite numeric value')
    return result


class Catalog:
    def __init__(self):self.specs={};self.rows=[];self.anomalies=[];self.sources=snapshots()
    def register(self,sid,name,freq,unit,provider,key,code,*,public=True,rights='US federal-authored statistical data; attribution; third-party exceptions excluded',
                 method_breaks='',lag='UNKNOWN; original release dates not reconstructed',snapshot_vintage='',pit=False,aggregation=None):
        source=self.sources[key]
        self.specs[sid]=dict(series_id=sid,name=name,native_frequency=freq,units=unit,geography='USA',provider=provider,
            source_key=key,source_identifier=code,source_url=source['url'],retrieved_at=source['retrieved_at'],
            snapshot_vintage_date=snapshot_vintage,original_publication_date='UNKNOWN',publication_lag=lag,
            vintage_availability='HISTORICAL_INITIAL_OR_REVISION_VALUES_WITH_RELEASE_DATES' if pit else 'LATEST_SNAPSHOT_ONLY',
            point_in_time_eligible=pit,license=rights,redistribution_permitted=public,methodological_breaks=method_breaks,
            monthly_aggregation=aggregation or {'M':'native_month','Q':'none; separate quarter-end and carry alignment views','D':'mean_daily','W':'mean_week_ending'}[freq],
            reported_original_start='UNKNOWN; actual downloaded start audited',reported_original_end='UNKNOWN; actual downloaded end audited',
            raw_path=source['raw_path'],raw_sha256=source['sha256'])
    def add(self,sid,date,value,*,key=None,published='',vintage='',status=''):
        s=self.specs[sid];key=key or s['source_key'];raw=self.sources[key]
        freq=s['native_frequency'];p=pd.Period(date,freq={'M':'M','Q':'Q-DEC','D':'D','W':'D'}[freq])
        self.rows.append(dict(series_id=sid,observation_date=p.start_time.date().isoformat(),period_end=p.end_time.date().isoformat(),
            native_frequency=freq,value=number(value),original_publication_date=published,historical_vintage_date=vintage,
            snapshot_vintage_date=s['snapshot_vintage_date'],retrieved_at=raw['retrieved_at'],source_key=key,
            source_sha256=raw['sha256'],source_status=status,point_in_time_eligible=s['point_in_time_eligible'] and bool(published and vintage),
            redistribution_permitted=s['redistribution_permitted']))


def parse_bls(c):
    keys=sorted(k for k,v in snapshots().items() if k.startswith('bls_') and v['status']=='ok')
    registered=set()
    for key in keys:
        data=json.loads(source_path(key).read_text())
        if data.get('status')!='REQUEST_SUCCEEDED':raise ValueError('BLS request failed: '+str(data.get('message')))
        for message in data.get('message',[]):c.anomalies.append(dict(source_key=key,kind='source_message',detail=message))
        for series in data['Results']['series']:
            code=series['seriesID']
            if code not in BLS:raise ValueError('Unexpected BLS series')
            sid,name,units=BLS[code]
            if sid not in registered:
                c.register(sid,name,'M',units,'US Bureau of Labor Statistics',key,code,
                           method_breaks='CPS population controls, CES benchmarking, seasonal revisions; preserve source missing values and footnotes.')
                registered.add(sid)
            for obs in series['data']:
                if obs['period']=='M13':continue
                if not re.fullmatch(r'M(?:0[1-9]|1[0-2])',obs['period']):raise ValueError('Invalid BLS month')
                c.add(sid,obs['year']+'-'+obs['period'][1:],obs['value'],key=key,status=json.dumps(obs.get('footnotes',[]),sort_keys=True))
    if registered!={s[0] for s in BLS.values()}:raise ValueError('Missing BLS series')


def xml_root(key):
    with zipfile.ZipFile(source_path(key)) as z:
        names=[n for n in z.namelist() if n.lower().endswith('_data.xml')]
        if len(names)!=1:raise ValueError('Unexpected XML archive structure: '+key)
        return ET.fromstring(z.read(names[0]))


def parse_h15(c):
    root=xml_root('H15');found=set()
    prepared=next(e.text for e in root.iter() if e.tag.endswith('Prepared'))[:10]
    for series in root.iter():
        code=series.attrib.get('SERIES_NAME')
        if code not in H15:continue
        if series.attrib.get('FREQ')!='129' or series.attrib.get('UNIT_MULT')!='1':raise ValueError('H15 units/frequency changed')
        sid,name=H15[code];found.add(code);moody='CORPORATE' in sid
        c.register(sid,name,'M','percent per year','Federal Reserve H.15'+(' / Moody\'s' if moody else ''),'H15',code,
            public=not moody,rights='Moody\'s copyrighted yields publicly distributed by Federal Reserve; local research, redistribution not cleared' if moody else 'US federal statistical data; attribution',
            snapshot_vintage=prepared,method_breaks='H.15 Moody corporate history ends September 2016; no splice to current licensed FRED values; monthly average yield, not holding-period return; maturity/issuer composition varies.' if moody else 'Rate bases differ; source gaps retained; no LIBOR/SOFR splice.')
        for obs in series:
            if obs.tag.endswith('Obs'):c.add(sid,obs.attrib['TIME_PERIOD'][:7],obs.attrib.get('OBS_VALUE') if obs.attrib['OBS_STATUS']=='A' else None,status=obs.attrib['OBS_STATUS'])
    if found!=set(H15):raise ValueError('Missing H15 requested code')


def parse_bea(c):
    books={i:pd.read_excel(source_path('BEA_Section'+str(i)),sheet_name=sorted({b[1] for b in BEA if b[0]==i}),header=None) for i in [1,2]}
    for section,sheet,code,sid,name,unit in BEA:
        data=books[section][sheet];label=str(data.iloc[1,0]);published=str(data.iloc[4,0])
        if not published.startswith('Data published '):raise ValueError('BEA publication date missing')
        if 'million' in unit and 'millions' not in label.lower():raise ValueError('BEA dollar scale changed')
        if 'index 2017=100' in unit and '2017=100' not in label:raise ValueError('BEA index base changed')
        if 'chained 2017' in unit and sheet!='T20600-M' and 'chained (2017)' not in label:raise ValueError('BEA chain base changed')
        selected=data.loc[data[2].eq(code)]
        if len(selected)!=1:raise ValueError('BEA series missing or duplicated: '+code)
        freq=sheet[-1];key='BEA_Section'+str(section)
        c.register(sid,name,freq,unit,'US Bureau of Economic Analysis',key,sheet+':'+code,
                   snapshot_vintage=pd.Timestamp(published.replace('Data published ','')).date().isoformat(),
                   method_breaks='Latest NIPA comprehensive/revised estimates; SAAR flows are annualized; chained components not additive. Source table: '+label)
        for column in range(3,len(data.iloc[7])):
            period=str(data.iloc[7,column]);pat=r'\d{4}Q[1-4]' if freq=='Q' else r'\d{4}M(?:0[1-9]|1[0-2])'
            if not re.fullmatch(pat,period):raise ValueError('Invalid BEA period: '+period)
            c.add(sid,period.replace('M','-'),selected.iloc[0,column])


def french_rows(key,daily=False):
    with zipfile.ZipFile(source_path(key)) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        if len(names)!=1:raise ValueError('Unexpected French archive')
        text=z.read(names[0]).decode('utf-8-sig')
    rows=[]
    for line in text.splitlines():
        cells=[s.strip() for s in line.split(',')]
        if not re.fullmatch(r'\d{8}' if daily else r'\d{6}',cells[0]):continue
        if len(cells)!=5:raise ValueError('French columns changed')
        rows.append((pd.to_datetime(cells[0],format='%Y%m%d' if daily else '%Y%m'),[number(v) for v in cells[1:]]))
    if not rows:raise ValueError('No French return observations')
    return rows


def parse_french(c):
    for key,daily in [('ff_monthly',False),('ff_daily',True)]:
        freq='D' if daily else 'M'
        for i,code in enumerate(['MKT_EXCESS','SMB','HML','RF']):
            sid='FF_'+code+('_DAILY' if daily else '')
            c.register(sid,'Fama/French '+code,freq,'percent per trading day' if daily else 'percent per month',
                'Kenneth French Data Library',key,code,public=False,rights='Public academic research download; raw redistribution not established; CRSP inputs; values local',
                method_breaks='FIZ/CIZ transition 2025; revised history; broad CRSP equity universe, not S&P 500; monthly and daily return constructions differ.',
                aggregation='native_month' if not daily else 'no direct monthly average; return/volatility transformations only')
            for date,values in french_rows(key,daily):c.add(sid,date,values[i])


def year_lines(key):
    for line in source_path(key).read_text().splitlines():
        match=re.match(r'^"([^"]+)"\s+(\d{4})\s+(.+)$',line)
        if not match:continue
        values=match[3].split()
        if len(values)>12:raise ValueError('Too many monthly fields')
        for month,value in enumerate(values,1):yield match[1],f'{match[2]}-{month:02d}',value


def release_calendar(text):
    text=unescape(re.sub('<[^>]+>',' ',text));out={}
    for month,year,date in re.findall(r'([A-Za-z]+)\s+(\d{4})\s+(\d{1,2}-[A-Za-z]+-\d{4})',text):
        key=pd.Timestamp(month+' 1 '+year).strftime('%Y-%m');value=pd.Timestamp(date).date().isoformat()
        if key in out and out[key]!=value:raise ValueError('Ambiguous release calendar')
        out[key]=value
    if len(out)<800:raise ValueError('Incomplete release calendar')
    return out


def parse_g17(c):
    codes={'B50001':'TOTAL','B00004':'MANUFACTURING','G21':'MINING','G2211A2':'UTILITIES'}
    for code,name in codes.items():
        c.register('US_IP_'+name,'Industrial production '+('MANUFACTURING (SIC)' if name=='MANUFACTURING' else name),'M','index 2017=100 SA','Federal Reserve G.17','g17_ip_sa',code,
                   method_breaks='Latest revised index; benchmark/base-year revisions. Not an original-release vintage.'+(' B00004 is SIC manufacturing; do not silently substitute NAICS IPMAN.' if name=='MANUFACTURING' else ''))
    for code,period,value in year_lines('g17_ip_sa'):
        if code in codes:c.add('US_IP_'+codes[code],period,value)
    calendar=release_calendar(source_path('g17_release_dates').read_text())
    for prefix in ['init','rev1']:
        c.register('US_IP_GROWTH_'+prefix.upper(),'Industrial production total monthly growth '+prefix,'M','percent MoM SA',
            'Federal Reserve G.17 historical release values','g17_revisions',prefix+'.b50001.pct',pit=True,
            method_breaks='Provider-retained initial/rev1 growth; release date known to day; no intraday claim.',lag='Official release calendar; next month init, second month rev1')
    for code,period,value in year_lines('g17_revisions'):
        if code not in ['init.b50001.pct','rev1.b50001.pct']:continue
        prefix=code.split('.')[0];release_month=str(pd.Period(period,'M')+(1 if prefix=='init' else 2));pub=calendar.get(release_month,'')
        c.add('US_IP_GROWTH_'+prefix.upper(),period,value,published=pub,vintage=pub,status='release_calendar_mapped' if pub else 'release_date_unavailable')


def parse_michigan(c):
    for key,freq in [('umich_monthly_1','M'),('umich_Q_1','Q')]:
        frame=pd.read_csv(source_path(key),skiprows=1);field='Month' if freq=='M' else 'Quarter'
        if list(frame.columns)!=[field,'Year','Index','Unnamed: 3'] or frame['Unnamed: 3'].notna().any():raise ValueError('Michigan schema changed')
        sid='US_CONSUMER_SENTIMENT'+('_QUARTERLY' if freq=='Q' else '')
        c.register(sid,'Michigan consumer sentiment',freq,'index 1966Q1=100','University of Michigan Surveys of Consumers',key,'Table 1',public=False,
            rights='Regents copyright; noncommercial/internal research permitted by retained agreement; redistribution needs separate permission',
            method_breaks='Monthly 1978 onward; earlier quarterly archive separate; 2024 telephone-to-web transition; final values not original vintages.')
        for row in frame.to_dict('records'):
            period=f"{int(row['Year'])}-{int(row[field]):02}" if freq=='M' else f"{int(row['Year'])}Q{int(row[field])}"
            c.add(sid,period,row['Index'])


def parse_fed_quarterly(c):
    for key in ['dsr','delinquency']:
        root=xml_root(key);prepared=next(e.text for e in root.iter() if e.tag.endswith('Prepared'))[:10];found=0
        for series in root.iter():
            attrs=series.attrib;code=attrs.get('SERIES_NAME','')
            if key=='dsr':
                mapping={'DSR_RATIO':('US_HOUSEHOLD_DEBT_SERVICE','Total household debt service'),
                         'MORTGAGE_DSR_RATIO':('US_MORTGAGE_DEBT_SERVICE','Mortgage debt service'),
                         'CONSUMER_DSR_RATIO':('US_CONSUMER_DEBT_SERVICE','Consumer debt service')}
                if code not in mapping:continue
                sid,name=mapping[code];units='percent disposable personal income'
                breaks='Credit-bureau method starts 2005; old 1980-2024 method is separate and not spliced.'
            else:
                if not all(attrs.get(k)==v for k,v in {'CHGDEL':'DEL','COMPONENT':'RATIO','SA':'SA','SIZE':'ALL'}.items()):continue
                mapping={'CONCC':('US_CREDIT_CARD_DELINQUENCY','Credit-card delinquency'),
                         'RERES':('US_MORTGAGE_DELINQUENCY','Residential real-estate delinquency'),
                         'CI':('US_BUSINESS_LOAN_DELINQUENCY','Commercial/industrial loan delinquency')}
                if attrs.get('LOANTYPE') not in mapping:continue
                sid,name=mapping[attrs['LOANTYPE']];units='percent loans at all commercial banks SA'
                breaks='Reporting/composition changes and seasonal revisions; quarter-end delinquency ratio, not monthly flow.'
            if attrs.get('FREQ')!='162' or attrs.get('UNIT_MULT')!='1':raise ValueError('Federal quarterly frequency/scale changed')
            found+=1;c.register(sid,name,'Q',units,'Federal Reserve Board',key,code,snapshot_vintage=prepared,method_breaks=breaks)
            for obs in series:
                if obs.tag.endswith('Obs'):c.add(sid,obs.attrib['TIME_PERIOD'],obs.attrib.get('OBS_VALUE') if obs.attrib['OBS_STATUS']=='A' else None,status=obs.attrib['OBS_STATUS'])
        if found!=3:raise ValueError('Expected three selected '+key+' series')


def parse_research(c):
    frame=pd.read_csv(source_path('ebp'))
    if list(frame.columns)!=['date','gz_spread','ebp','est_prob']:raise ValueError('EBP columns changed')
    c.register('US_EXCESS_BOND_PREMIUM','Excess bond premium','M','percentage points','Federal Reserve Board','ebp','ebp',
               method_breaks='Model residual reconstructed/revised historically; not a contemporaneously published 1973 signal.')
    for r in frame.to_dict('records'):c.add('US_EXCESS_BOND_PREMIUM',r['date'],r['ebp'])
    fci=pd.read_csv(source_path('fci_g'))
    if 'FCI-G Index (baseline)' not in fci:raise ValueError('FCI-G schema changed')
    c.register('US_FCI_G','Financial conditions impulse on growth, baseline','M','index as published; model-implied growth headwind',
               'Federal Reserve Board','fci_g','FCI-G Index (baseline)',method_breaks='Model-estimated baseline with three-year lookback; revised history.')
    for r in fci.to_dict('records'):c.add('US_FCI_G',r['date'],r['FCI-G Index (baseline)'])
    news=pd.read_excel(source_path('news_sentiment'),sheet_name='Data')
    if list(news.columns)!=['date','News Sentiment']:raise ValueError('News-sentiment columns changed')
    c.register('US_ECONOMIC_NEWS_SENTIMENT','Economic-news sentiment','D','news sentiment regression day effects',
               'Federal Reserve Bank of San Francisco','news_sentiment','Data:News Sentiment',public=False,
               rights='Public research series; FRBSF copyright and third-party news inputs; redistribution not established',
               method_breaks='Retrospective newspaper composition adjustment; days without observations remain absent; monthly mean of available source days only.',
               aggregation='mean_observed_news_days; source-day count and calendar gaps retained')
    for r in news.to_dict('records'):c.add('US_ECONOMIC_NEWS_SENTIMENT',r['date'],r['News Sentiment'])
    epu=pd.read_excel(source_path('epu'),sheet_name='Main News Index')
    if list(epu.columns)!=['Year','Month','News_Based_Policy_Uncert_Index']:raise ValueError('EPU schema changed')
    c.register('US_POLICY_UNCERTAINTY_NEWS','News-based economic policy uncertainty','M','index, published normalization',
               'Baker, Bloom and Davis','epu','Main News Index:News_Based_Policy_Uncert_Index',public=True,
               rights='Creative Commons Attribution 4.0; Baker, Bloom and Davis (2016), Measuring Economic Policy Uncertainty; PolicyUncertainty.com; transformed values labelled',
               method_breaks='Historical newspaper/search design differs before 1985; normalization revised to 101.8 baseline mean; not legacy three-component index.')
    for r in epu.to_dict('records'):
        if str(r['Year']).startswith('Source: ') and pd.isna(r['Month']) and pd.isna(r['News_Based_Policy_Uncert_Index']):
            c.anomalies.append(dict(source_key='epu',kind='source_footer',detail=str(r['Year'])))
            continue
        c.add('US_POLICY_UNCERTAINTY_NEWS',f"{int(r['Year'])}-{int(r['Month']):02}",r['News_Based_Policy_Uncert_Index'])


def parse_pink(c):
    path=source_path('pink');data=pd.read_excel(path,sheet_name='Monthly Prices',header=None)
    if 'World Bank Commodity Price Data' not in str(data.iloc[0,0]):raise ValueError('Pink Sheet identity changed')
    updated=pd.Timestamp(str(data.iloc[3,0]).replace('Updated on ','')).date().isoformat()
    description=pd.read_excel(path,sheet_name='Description',header=None).iloc[:,1].dropna().astype(str).tolist()
    mapping={'Gold':('WB_GOLD','Gold reference price','($/troy oz)','USD per troy ounce'),
             'Crude oil, WTI':('WB_WTI','WTI crude oil monthly reference price','($/bbl)','USD per barrel'),
             'Natural gas, US':('WB_NATURAL_GAS_US','US natural gas reference price','($/mmbtu)','USD per million BTU'),
             'Copper':('WB_COPPER','Copper reference price','($/mt)','USD per metric ton'),
             'Wheat, US HRW':('WB_WHEAT_HRW','US hard red winter wheat reference price','($/mt)','USD per metric ton')}
    for label,(sid,name,expected_unit,units) in mapping.items():
        columns=[i for i,v in enumerate(data.iloc[4]) if str(v).strip()==label]
        if len(columns)!=1:raise ValueError('Pink Sheet missing/duplicate column '+label)
        col=columns[0]
        if str(data.iloc[5,col]).strip()!=expected_unit:raise ValueError('Pink Sheet units changed')
        terms=[s for s in description if (label.split(',')[0] in s or ('West Texas' in s and sid=='WB_WTI'))]
        c.register(sid,name,'M',units,'World Bank Pink Sheet', 'pink',label,
                   rights='World Bank open data CC BY 4.0 with additional terms; original sources and exceptions retained',
                   method_breaks='Source benchmark history retained; gold fixed/dual/floating regimes; '+ ' '.join(terms[:2]),snapshot_vintage=updated)
        c.specs[sid]['geography']='International benchmark; US reference for WTI/gas/wheat'
        for _,r in data.iloc[6:].iterrows():
            period=str(r[0])
            if not re.fullmatch(r'\d{4}M(?:0[1-9]|1[0-2])',period):raise ValueError('Unexpected Pink Sheet period')
            c.add(sid,period.replace('M','-'),r[col])
    sheets=pd.ExcelFile(path).sheet_names
    if 'Mismatch Details' in sheets:
        detail=pd.read_excel(path,sheet_name='Mismatch Details',header=3)
        c.anomalies.append(dict(source_key='pink',kind='provider_workbook_audit_sheet',detail=f'Original workbook includes {len(detail)} mismatch-detail rows; retained unchanged; no corrective edits inferred.'))


def parse_claims(c):
    root=ET.fromstring(source_path('claims').read_bytes())
    if root.tag!='r539cyNational':raise ValueError('Not national DOL claims XML')
    updated=pd.Timestamp(root.attrib['rundate']).date().isoformat()
    for name,sid in [('InitialClaims','US_INITIAL_CLAIMS'),('ContinuedClaims','US_CONTINUED_CLAIMS')]:
        c.register(sid,name.replace('Claims',' claims'),'W','persons/claims per source week SA','US Department of Labor ETA','claims',name+'/SA',
                   snapshot_vintage=updated,method_breaks='Regular UI claims; pandemic special programs separate; seasonal/reporting revisions; monthly average weekly level, not unique monthly claimants.',
                   aggregation='mean_week_ending_Saturday; require every expected Saturday')
        for week in root.findall('week'):
            date=pd.Timestamp(week.findtext('weekEnded'))
            if date.dayofweek!=5:raise ValueError('Claims week no longer ends Saturday')
            c.add(sid,date,week.findtext(name+'/SA'))


def parse_nfci(c):
    frame=pd.read_csv(source_path('nfci'))
    if not {'Friday_of_Week','NFCI','ANFCI'}<=set(frame):raise ValueError('NFCI columns changed: '+str(list(frame)))
    for column,sid in [('NFCI','US_NFCI'),('ANFCI','US_ANFCI')]:
        c.register(sid,column,'W','index, zero mean/unit SD over provider estimation history','Federal Reserve Bank of Chicago','nfci',column,
                   public=False,rights='Public research download; Chicago Fed copyright; redistribution not established',
                   method_breaks='Re-estimated/revised full history; dates before index launch not real-time releases; adjusted and unadjusted alternatives overlap.',
                   aggregation='mean_week_ending_Friday; require every expected Friday')
        for r in frame.to_dict('records'):
            date=pd.Timestamp(r['Friday_of_Week'])
            if date.dayofweek!=4:raise ValueError('NFCI date not Friday')
            c.add(sid,date,r[column])


def parse_nber(c):
    data=pd.read_excel(source_path('nber_cycles'),header=None);events=[]
    for _,row in data.iterrows():
        peak=re.fullmatch(r'([A-Za-z]+)\s+(\d{4})\s+\((\d{4}Q[1-4])\)',str(row[2]).strip())
        trough=re.fullmatch(r'([A-Za-z]+)\s+(\d{4})\s+\((\d{4}Q[1-4])\)',str(row[3]).strip())
        if not peak or not trough:continue
        begin=pd.Timestamp(peak[1]+' 1 '+peak[2]).to_period('M');end=pd.Timestamp(trough[1]+' 1 '+trough[2]).to_period('M')
        if end<=begin or end.ordinal-begin.ordinal!=int(row[6]):raise ValueError('NBER interval inconsistent')
        events.append((begin,end))
    if len(events)<30:raise ValueError('Incomplete NBER chronology')
    c.register('US_NBER_RECESSION_CLOSED_CYCLES','NBER recession membership through last closed cycle','M','binary retrospective',
               'NBER Business Cycle Dating Committee','nber_cycles','peak<trough-month<=trough',public=False,
               rights='Public factual chronology; raw redistribution not established',
               method_breaks='1 strictly after peak through trough; after last closed trough left unclassified, not certified expansion.')
    for month in pd.period_range('1956-01',max(t for _,t in events),freq='M'):
        c.add('US_NBER_RECESSION_CLOSED_CYCLES',month,int(any(p<month<=t for p,t in events)))
    tables=pd.read_html(io.StringIO(source_path('nber_faq').read_text()),header=0)
    table=next((t for t in tables if 'Announcement Date' in t),None)
    if table is None:raise ValueError('NBER announcement table absent')
    sid='US_NBER_ANNOUNCEMENT_EVENT'
    c.register(sid,'NBER announced turning point: peak=1 trough=0','D','binary event type','NBER Business Cycle Dating Committee',
               'nber_faq','Month of Turning Point / Announcement Date',pit=True,public=False,
               rights='Public factual chronology; raw redistribution not established',
               method_breaks='Announcement event, not actual contemporaneous recession state; day-level time only.',aggregation='event_only_no_monthly_mean')
    kind=None
    for r in table.to_dict('records'):
        period=str(r['Month of Turning Point'])
        if 'Peaks' in period:kind=1;continue
        if 'Troughs' in period:kind=0;continue
        if kind is None:raise ValueError('Unknown NBER event type')
        date=pd.Timestamp(str(r['Announcement Date']).replace(',',' ')).date().isoformat()
        c.add(sid,date,kind,published=date,vintage=date,status='turning_point_month='+pd.Timestamp(period).strftime('%Y-%m'))


def normalize():
    catalog=Catalog();failures=[]
    for parser in [parse_bls,parse_h15,parse_bea,parse_french,parse_g17,parse_michigan,parse_fed_quarterly,parse_research,parse_pink,parse_claims,parse_nfci,parse_nber]:
        partial=Catalog()
        try:
            parser(partial)
            if set(catalog.specs)&set(partial.specs):raise ValueError('Duplicate series registration')
            catalog.specs.update(partial.specs);catalog.rows.extend(partial.rows);catalog.anomalies.extend(partial.anomalies)
        except Exception as e:
            failures.append({'parser':parser.__name__,'error':type(e).__name__+': '+str(e)})
    if failures:
        write_json(REPORT/'normalization_failures.json',failures)
        raise ValueError('Source normalization failed; published native datasets preserved: '+json.dumps(failures))
    frame=pd.DataFrame(catalog.rows).sort_values(['series_id','observation_date','historical_vintage_date']).reset_index(drop=True)
    if frame[['series_id','observation_date','historical_vintage_date']].duplicated().any():raise ValueError('Duplicate native observations; no silent deduplication')
    if frame.value.dropna().isin([np.inf,-np.inf]).any():raise ValueError('Nonfinite observations')
    for sid,group in frame.groupby('series_id'):
        spec=catalog.specs[sid];valid=group.loc[group.value.notna()]
        spec.update(downloaded_first=group.observation_date.min(),downloaded_last=group.observation_date.max(),
                    actual_first_valid=valid.observation_date.min(),actual_last_valid=valid.observation_date.max(),
                    source_rows=len(group),source_missing_values=int(group.value.isna().sum()),retrieved_at=group.retrieved_at.max(),
                    all_source_keys=';'.join(sorted(group.source_key.unique())))
    # Reviewed exact-construct crosswalks to the frozen research catalog. These are
    # reported metadata ranges, explicitly distinct from this download's audit.
    research_path=ROOT/'analysis/external_historical/financial_research/indicator_inventory.csv'
    research=pd.read_csv(research_path,keep_default_na=False).set_index('indicator_id')
    crosswalk={'US_UNEMPLOYMENT':'I056','US_LABOR_PARTICIPATION':'I060','US_EMPLOYMENT_POPULATION':'I061',
        'US_YOUTH_UNEMPLOYMENT':'I057','US_NONFARM_EMPLOYMENT':'I062','US_HOURLY_EARNINGS_PRODUCTION':'I068',
        'US_WEEKLY_HOURS_ALL_PRIVATE':'I069','US_CPI_SA':'I042','US_FED_FUNDS':'I001','US_PRIME_RATE':'I011',
        'US_TBILL_3M_DISCOUNT':'I005','US_TREASURY_2Y':'I006','US_TREASURY_10Y':'I008','US_REAL_GDP':'I026',
        'US_DISPOSABLE_INCOME':'I073','US_PERSONAL_SAVING_RATE':'I074','US_PCE_PRICE_INDEX':'I054','US_PCE_NOMINAL':'I075',
        'FF_MKT_EXCESS':'I123','FF_SMB':'I125','FF_HML':'I126','FF_RF':'I124','US_IP_TOTAL':'I033'}
    for sid,spec in catalog.specs.items():
        spec['reported_range_evidence']='UNKNOWN; downloaded bounds are measured separately'
        spec['research_catalog_identifier']=''
        if sid in crosswalk:
            r=research.loc[crosswalk[sid]]
            spec.update(reported_original_start=r.historical_start,reported_original_end=r.historical_end,
                reported_range_evidence='Financial research catalog fb3fc0d '+crosswalk[sid]+': '+r.exact_source_url,
                research_catalog_identifier=r.dataset_or_series_identifier)
    write_csv(PROCESSED/'native_local.csv.xz',frame)
    write_csv(PROCESSED/'native_public.csv.xz',frame.loc[frame.redistribution_permitted])
    write_csv(REPORT/'series_dictionary.csv',list(catalog.specs.values()))
    write_json(REPORT/'normalization_failures.json',failures)
    write_json(REPORT/'source_anomalies.json',catalog.anomalies)
    write_json(MANIFESTS/'normalization.json',{'source_manifest_sha256':sha(MANIFESTS/'sources.json'),'parser_sha256':sha(__file__),'research_metadata_sha256':sha(research_path),
               'series':len(catalog.specs),'rows':len(frame),'failures':len(failures),'native_local_sha256':sha(PROCESSED/'native_local.csv.xz'),
               'native_public_sha256':sha(PROCESSED/'native_public.csv.xz')})
    print(json.dumps({'series':len(catalog.specs),'rows':len(frame),'failures':failures},indent=2))
    return frame,catalog.specs


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['acquire','normalize','restore']);args=parser.parse_args()
    if args.action=='acquire':acquire()
    elif args.action=='restore':restore_snapshots()
    else:normalize()
