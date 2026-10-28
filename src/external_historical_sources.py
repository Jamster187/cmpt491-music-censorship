"""Original-provider downloads and strict parsers for historical data layer v1."""
from __future__ import annotations
from collections import defaultdict
import calendar
import datetime as dt
from html import unescape
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pandas as pd

from enrichment_common import EXTERNAL, HISTORY, fetch, fetch_post, fetch_form, sha, write_csv, write_json

BLS={
 'LNS14000000':('US_UNEMPLOYMENT','Unemployment rate, age 16+','percent','SA'),
 'LNS11300000':('US_LABOR_PARTICIPATION','Labor force participation rate, age 16+','percent','SA'),
 'LNS12300000':('US_EMPLOYMENT_POPULATION','Employment-population ratio, age 16+','percent','SA'),
 'LNS14000012':('US_YOUTH_UNEMPLOYMENT','Unemployment rate, age 16-19','percent','SA'),
 'CES0000000001':('US_NONFARM_EMPLOYMENT','Total nonfarm employees','thousand persons','SA'),
 'CES0500000008':('US_HOURLY_EARNINGS_PRODUCTION','Private production/nonsupervisory average hourly earnings','USD/hour','SA'),
 'CES0500000002':('US_WEEKLY_HOURS_ALL_PRIVATE','Private all-employee average weekly hours','hours/week','SA'),
 'CUSR0000SA0':('US_CPI_SA','CPI-U all items','index 1982-1984=100','SA'),
 'CUUR0000SA0':('US_CPI_NSA','CPI-U all items','index 1982-1984=100','NSA')}
H15={
 'RIFSPFF_N.M':('US_FED_FUNDS','Federal funds effective rate'),
 'RIFSPBLP_N.M':('US_PRIME_RATE','Bank prime loan rate'),
 'RIFSGFSM03_N.M':('US_TBILL_3M_DISCOUNT','3-month Treasury bill secondary-market discount rate'),
 'RIFSGFSM06_N.M':('US_TBILL_6M_DISCOUNT','6-month Treasury bill secondary-market discount rate'),
 'RIFLGFCM03_N.M':('US_TREASURY_3M','3-month Treasury constant maturity yield'),
 'RIFLGFCY01_N.M':('US_TREASURY_1Y','1-year Treasury constant maturity yield'),
 'RIFLGFCY02_N.M':('US_TREASURY_2Y','2-year Treasury constant maturity yield'),
 'RIFLGFCY05_N.M':('US_TREASURY_5Y','5-year Treasury constant maturity yield'),
 'RIFLGFCY10_N.M':('US_TREASURY_10Y','10-year Treasury constant maturity yield'),
 'RIFLGFCY20_N.M':('US_TREASURY_20Y','20-year Treasury constant maturity yield'),
 'RIFLGFCY30_N.M':('US_TREASURY_30Y','30-year Treasury constant maturity yield'),
 'RIFLGFCY05_XII_N.M':('US_TIPS_5Y','5-year inflation-indexed Treasury constant maturity yield'),
 'RIFLGFCY10_XII_N.M':('US_TIPS_10Y','10-year inflation-indexed Treasury constant maturity yield'),
 'RIFSPPNAAD90_N.M':('US_AA_NONFINANCIAL_CP_3M','3-month AA nonfinancial commercial paper rate'),
 'RIFSPPFAAD90_N.M':('US_AA_FINANCIAL_CP_3M','3-month AA financial commercial paper rate')}
WB={
 'IT.NET.USER.ZS':('US_INTERNET_USERS','Individuals using the Internet','percent of population'),
 'IT.NET.BBND.P2':('US_FIXED_BROADBAND','Fixed broadband subscriptions','subscriptions per 100 people'),
 'IT.CEL.SETS.P2':('US_MOBILE_SUBSCRIPTIONS','Mobile cellular subscriptions','subscriptions per 100 people'),
 'SP.POP.TOTL':('US_POPULATION_ANNUAL','Population total','persons'),
 'SP.POP.0014.TO.ZS':('US_CHILD_POPULATION_SHARE','Population ages 0-14','percent of population'),
 'SP.POP.65UP.TO.ZS':('US_OLDER_POPULATION_SHARE','Population ages 65+','percent of population'),
 'SP.URB.TOTL.IN.ZS':('US_URBAN_POPULATION_SHARE','Urban population share','percent of population'),
 'SP.DYN.TFRT.IN':('US_FERTILITY_RATE','Total fertility rate','births per woman'),
 'SP.DYN.LE00.IN':('US_LIFE_EXPECTANCY','Life expectancy at birth','years'),
 'VC.IHR.PSRC.P5':('US_INTENTIONAL_HOMICIDE_RATE','Intentional homicides','per 100000 people'),
 'SI.POV.GINI':('US_GINI','Gini index','index 0-100')}
BEA=[
 ('BEA_Section1.xlsx','T10101-Q','A191RL','US_REAL_GDP_GROWTH','Real GDP growth','percent change SAAR','macroeconomic'),
 ('BEA_Section1.xlsx','T10106-Q','A191RX','US_REAL_GDP','Real GDP','million chained 2017 USD SAAR','macroeconomic'),
 ('BEA_Section1.xlsx','T10109-Q','A191RD','US_GDP_DEFLATOR','GDP implicit price deflator','index 2017=100 SA','macroeconomic'),
 ('BEA_Section2.xlsx','T20600-M','A065RC','US_PERSONAL_INCOME','Personal income','million USD SAAR','macroeconomic'),
 ('BEA_Section2.xlsx','T20600-M','A034RC','US_WAGES_SALARIES','Wages and salaries','million USD SAAR','macroeconomic'),
 ('BEA_Section2.xlsx','T20600-M','W825RC','US_UNEMPLOYMENT_BENEFITS','Unemployment insurance benefits','million USD SAAR','macroeconomic'),
 ('BEA_Section2.xlsx','T20600-M','A067RC','US_DISPOSABLE_INCOME','Disposable personal income','million USD SAAR','macroeconomic'),
 ('BEA_Section2.xlsx','T20600-M','A067RX','US_REAL_DISPOSABLE_INCOME','Real disposable personal income','million chained 2017 USD SAAR','macroeconomic'),
 ('BEA_Section2.xlsx','T20600-M','A229RX','US_REAL_DISPOSABLE_INCOME_PC','Real disposable income per capita','chained 2017 USD SAAR','macroeconomic'),
 ('BEA_Section2.xlsx','T20600-M','A072RC','US_PERSONAL_SAVING_RATE','Personal saving / disposable income','percent SA','macroeconomic'),
 ('BEA_Section2.xlsx','T20804-M','DPCERG','US_PCE_PRICE_INDEX','PCE price index','index 2017=100 SA','macroeconomic'),
 ('BEA_Section2.xlsx','T20805-M','DPCERC','US_PCE_NOMINAL','Personal consumption expenditures','million USD SAAR','macroeconomic'),
 ('BEA_Section2.xlsx','T20806-M','DPCERX','US_PCE_REAL','Real personal consumption expenditures','million chained 2017 USD SAAR','macroeconomic'),
 ('BEA_Section2.xlsx','T20805-M','DREQRC','US_RECREATION_GOODS_NOMINAL','Recreational goods and vehicles PCE','million USD SAAR','cultural'),
 ('BEA_Section2.xlsx','T20805-M','DRCARC','US_RECREATION_SERVICES_NOMINAL','Recreation services PCE','million USD SAAR','cultural'),
 ('BEA_Section2.xlsx','T20806-M','DREQRX','US_RECREATION_GOODS_REAL','Real recreational goods and vehicles PCE','million chained 2017 USD SAAR','cultural'),
 ('BEA_Section2.xlsx','T20806-M','DRCARX','US_RECREATION_SERVICES_REAL','Real recreation services PCE','million chained 2017 USD SAAR','cultural')]


def metadata(path):return json.loads(path.with_name(path.name+'.provenance.json').read_text())


def period_dates(period,frequency):
    p=pd.Period(period,freq={'D':'D','M':'M','Q':'Q-DEC','A':'Y-DEC'}[frequency])
    return p.start_time.date().isoformat(),p.end_time.date().isoformat()


def numeric(value):
    if value is None or pd.isna(value):return None
    if str(value).strip().lower() in {'','-','na','nan','.....','...','(na)','(d)','-99.99','-999','-9999'}:return None
    result=float(str(value).replace(',',''))
    if not np.isfinite(result):raise ValueError('Nonfinite source observation')
    return result


class Catalog:
    def __init__(self):self.series={};self.rows=[];self.anomalies=[]
    def register(self,series_id,name,frequency,units,source,path,category,*,geography='USA',source_code='',license='US government data; public domain, attribution requested',
                 publication_date='',vintage_date='',availability='retrieved_snapshot_original_release_unknown',transformation='none',redistribute=True,notes=''):
        meta=metadata(path)
        self.series[series_id]={'series_id':series_id,'name':name,'frequency':frequency,'units':units,'geography':geography,
            'source':source,'source_url':meta['url'],'source_code':source_code,'retrieval_date':meta['retrieval_date'],
            'publication_date':publication_date,'vintage_date':vintage_date,'availability_status':availability,
            'license':license,'transformation':transformation,'category':category,'redistribution_permitted':redistribute,
            'raw_path':str(path.relative_to(EXTERNAL.parent.parent)),'raw_sha256':sha(path),'notes':notes}
    def add(self,series_id,period,value,*,publication_date=None,vintage_date=None,source_status='',frequency=None):
        spec=self.series[series_id];freq=frequency or spec['frequency'];date,end=period_dates(period,freq)
        row={k:spec[k] for k in ['series_id','frequency','units','geography','source','source_url','source_code','raw_path','raw_sha256','retrieval_date','publication_date','vintage_date','availability_status','license','transformation','category','redistribution_permitted']}
        row.update(date=date,period_end=end,value=numeric(value),source_status=source_status)
        if publication_date is not None:row['publication_date']=publication_date
        if vintage_date is not None:row['vintage_date']=vintage_date
        self.rows.append(row)


def acquire():
    from external_historical_political import acquire as acquire_political
    failures=[]
    def get(url,relative,limit=20_000_000):
        try:fetch(url,EXTERNAL/relative,limit=limit,timeout=60);print(relative,flush=True)
        except Exception as e:failures.append({'url':url,'path':relative,'error':str(e)})
    for start in range(1958,2027,10):
        end=min(start+9,2026)
        fetch_post('https://api.bls.gov/publicAPI/v2/timeseries/data/',{'seriesid':list(BLS),'startyear':str(start),'endyear':str(end)},
            EXTERNAL/f'macroeconomic/raw/bls_{start}_{end}.json')
    get('https://www.federalreserve.gov/datadownload/Output.aspx?filetype=zip&rel=H15','financial/raw/H15.zip',100_000_000)
    for section in [1,2]:get(f'https://apps.bea.gov/national/Release/XLS/Survey/Section{section}All_xls.xlsx',f'macroeconomic/raw/BEA_Section{section}.xlsx')
    for code in WB:
        get('https://api.worldbank.org/v2/country/USA/indicator/'+code+'?format=json&per_page=1000',f'social/raw/{code}_data.json')
        get('https://api.worldbank.org/v2/indicator/'+code+'?format=json',f'social/raw/{code}_metadata.json')
    get('https://ucdp.uu.se/downloads/ucdpprio/ucdp-prio-acd-261-csv.zip','political/raw/ucdp_26_1.zip')
    for url,name in [
        ('https://www.federalreserve.gov/releases/g17/Current/ipdisk/ip_sa.txt','g17_ip_sa.txt'),
        ('https://www.federalreserve.gov/releases/g17/Current/ipdisk/revh_sa.txt','g17_revisions.txt'),
        ('https://www.federalreserve.gov/releases/g17/release_dates.htm','g17_release_dates.html'),
        ('https://www.federalreserve.gov/releases/g17/Current/ipdisk/g17tab1.txt','g17_dictionary.txt')]:get(url,'macroeconomic/raw/'+name)
    for suffix,name in [('','ff_monthly.zip'),('_daily','ff_daily.zip')]:
        get(f'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors{suffix}_CSV.zip','financial/raw/'+name)
    get('https://history.house.gov/Institution/Presidents-Coinciding/Party-Government/','political/raw/party_government.html')
    for year in range(1956,2025,4):get(f'https://www.archives.gov/electoral-college/{year}',f'political/raw/election_{year}.html')
    get('https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions','macroeconomic/raw/nber_cycles.html')
    get('https://www.nber.org/sites/default/files/2023-03/BCDC_spreadsheet_for_website.xlsx','macroeconomic/raw/nber_cycles.xlsx')
    get('https://www.nber.org/research/business-cycle-dating/business-cycle-dating-procedure-frequently-asked-questions','macroeconomic/raw/nber_faq.html')
    get('https://data.sca.isr.umich.edu/agreement.php','macroeconomic/raw/umich_terms.html')
    for table,freq,year,name in [(1,'M','1978','umich_monthly_1.csv'),(5,'M','1978','umich_M_5.csv'),
                                (32,'M','1978','umich_M_32.csv'),(34,'M','1978','umich_M_34.csv'),(1,'Q','1960','umich_Q_1.csv')]:
        fetch_form('https://data.sca.isr.umich.edu/data-archive/mine.php',{'table':str(table),'year':year,'qorm':freq,'order':'asc','format':'Comma-Separated (CSV)'},EXTERNAL/'macroeconomic/raw'/name)
    get('https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/national/time-series/110/tavg/1/0/1958-2026.json?base_prd=true&begbaseyear=1901&endbaseyear=2000','social/raw/noaa_us_temperature.json')
    acquire_political()
    write_json(HISTORY/'acquisition_failures.json',failures)


def parse_bls(catalog):
    for path in sorted((EXTERNAL/'macroeconomic/raw').glob('bls_*.json')):
        if '.provenance.' in path.name:continue
        data=json.loads(path.read_text())
        if data.get('status')!='REQUEST_SUCCEEDED':raise ValueError('BLS API failure: '+str(data.get('message')))
        for message in data.get('message',[]):catalog.anomalies.append({'source':'BLS','file':path.name,'message':message})
        returned=set()
        for series in data['Results']['series']:
            code=series['seriesID'];returned.add(code);sid,name,units,adjustment=BLS[code]
            if sid not in catalog.series:catalog.register(sid,name,'M',units,'US Bureau of Labor Statistics',path,'macroeconomic',source_code=code,notes=adjustment+'; source footnotes retained per observation. Multiple date-block raw files listed in manifest.')
            for obs in series['data']:
                if obs['period']=='M13':continue  # Explicit annual average, not a 13th month.
                if not re.fullmatch(r'M(?:0[1-9]|1[0-2])',obs['period']):raise ValueError('Unknown BLS period')
                catalog.add(sid,obs['year']+'-'+obs['period'][1:],obs['value'],source_status=json.dumps(obs.get('footnotes',[]),sort_keys=True))
                catalog.rows[-1]['retrieval_date']=metadata(path)['retrieval_date']
                catalog.rows[-1]['raw_path']=str(path.relative_to(EXTERNAL.parent.parent))
                catalog.rows[-1]['raw_sha256']=sha(path)
        if returned!=set(BLS):raise ValueError('BLS omitted requested series')


def parse_h15(catalog):
    path=EXTERNAL/'financial/raw/H15.zip'
    with zipfile.ZipFile(path) as z:root=ET.fromstring(z.read('H15_data.xml'))
    found=set();prepared=next(e.text for e in root.iter() if e.tag.endswith('Prepared'))[:10]
    for series in root.iter():
        code=series.attrib.get('SERIES_NAME')
        if code not in H15:continue
        found.add(code);sid,name=H15[code]
        if series.attrib['FREQ']!='129' or series.attrib['UNIT_MULT']!='1':raise ValueError('Unexpected H15 frequency/scale')
        catalog.register(sid,name,'M','percent per year','Federal Reserve Board H.15',path,'financial',source_code=code,
            publication_date=prepared,vintage_date=prepared,notes='Published monthly average; yield/rate, not a realized holding-period return. Latest snapshot, original publication dates not supplied.')
        for obs in series:
            if not obs.tag.endswith('Obs'):continue
            status=obs.attrib['OBS_STATUS'];value=obs.attrib.get('OBS_VALUE') if status=='A' else None
            catalog.add(sid,obs.attrib['TIME_PERIOD'][:7],value,source_status=status)
    if found!=set(H15):raise ValueError('H15 requested series missing: '+str(set(H15)-found))


def parse_bea(catalog):
    sheets={}
    for filename,sheet,code,sid,name,units,category in BEA:
        path=EXTERNAL/'macroeconomic/raw'/filename
        if (filename,sheet) not in sheets:sheets[filename,sheet]=pd.read_excel(path,sheet_name=sheet,header=None)
        data=sheets[filename,sheet]
        unit_header=str(data.iloc[1,0]).lower()
        if 'million' in units and 'millions' not in unit_header:raise ValueError('BEA dollar scale changed')
        if 'index 2017=100' in units and '2017=100' not in unit_header:raise ValueError('BEA index base changed')
        if 'chained 2017' in units and sheet!='T20600-M' and 'chained (2017)' not in unit_header:raise ValueError('BEA chained-dollar base changed')
        published=str(data.iloc[4,0])
        if not published.startswith('Data published '):raise ValueError('BEA release date missing')
        publication=pd.Timestamp(published.replace('Data published ','')).date().isoformat()
        header=data.iloc[7];selected=data.loc[data[2].eq(code)]
        if len(selected)!=1:raise ValueError('BEA code missing/duplicated: '+code)
        frequency=sheet[-1]
        catalog.register(sid,name,frequency,units,'US Bureau of Economic Analysis',path,category,source_code=sheet+':'+code,
            publication_date=publication,vintage_date=publication,notes='Latest released workbook; historical values revised. SAAR levels are annualized flow rates, not actual monthly/quarterly totals. Workbook original units and line labels validated.')
        catalog.series[sid]['source_table_units']=str(data.iloc[1,0])
        catalog.series[sid]['source_line_label']=str(selected.iloc[0,1])
        for column in range(3,len(header)):
            label=str(header[column]);expected=r'\d{4}Q[1-4]' if frequency=='Q' else r'\d{4}M(?:0[1-9]|1[0-2])'
            if not re.fullmatch(expected,label):raise ValueError('Unexpected BEA period: '+label)
            period=label if frequency=='Q' else label.replace('M','-')
            catalog.add(sid,period,selected.iloc[0,column])


def parse_worldbank(catalog):
    for code,(sid,name,units) in WB.items():
        path=EXTERNAL/f'social/raw/{code}_data.json';mp=EXTERNAL/f'social/raw/{code}_metadata.json'
        data=json.loads(path.read_text());meta=json.loads(mp.read_text())
        if not isinstance(data,list) or len(data)!=2 or data[0].get('pages')!=1:raise ValueError('Incomplete World Bank response')
        details=meta[1][0]
        catalog.register(sid,name,'A',units,'World Bank WDI; '+details.get('sourceOrganization',''),path,'social',source_code=code,
            license='CC BY 4.0 with World Bank additional terms; original provider attribution retained',vintage_date=data[0].get('lastupdated',''),
            notes=details.get('sourceNote','')+'; annual observation only; no monthly interpolation; publication date unknown.')
        for obs in data[1]:
            if obs['countryiso3code']!='USA' or obs['indicator']['id']!=code:raise ValueError('Wrong World Bank identity')
            catalog.add(sid,obs['date'],obs['value'],source_status=str(obs.get('obs_status','')))


def parse_french_file(path,daily=False):
    with zipfile.ZipFile(path) as archive:
        names=[n for n in archive.namelist() if n.lower().endswith('.csv')]
        if len(names)!=1:raise ValueError('Unexpected French archive')
        text=archive.read(names[0]).decode('utf-8-sig')
    rows=[];pattern=r'\d{8}' if daily else r'\d{6}'
    for line in text.splitlines():
        cells=[c.strip() for c in line.split(',')]
        if not cells or not re.fullmatch(pattern,cells[0]):continue
        if len(cells)!=5:raise ValueError('French factor schema changed')
        date=pd.to_datetime(cells[0],format='%Y%m%d' if daily else '%Y%m').date().isoformat()
        rows.append({'date':date,**{k:numeric(v) for k,v in zip(['MKT_EXCESS','SMB','HML','RF'],cells[1:])}})
    if not rows or pd.DataFrame(rows).date.duplicated().any():raise ValueError('French observations missing or duplicated')
    return pd.DataFrame(rows)


def parse_french(catalog):
    for daily,name in [(False,'ff_monthly.zip'),(True,'ff_daily.zip')]:
        path=EXTERNAL/'financial/raw'/name;frequency='D' if daily else 'M'
        data=parse_french_file(path,daily)
        for code in ['MKT_EXCESS','SMB','HML','RF']:
            sid='FF_'+code+('_DAILY' if daily else '')
            catalog.register(sid,'Fama/French '+code,frequency,'percent return per period','Eugene F. Fama and Kenneth R. French Data Library',path,'financial',source_code=code,
                license='Provider copyright; publicly offered research download; raw/derived return values retained locally, redistribution not established',redistribute=False,
                notes='Current research-return vintage, not original real-time releases. MKT_EXCESS is value-weighted US CRSP market return less RF. RF source changes June 2024. From January 2025 data release, CIZ daily compounding/ex-date dividends replace FIZ month-end dividend convention; history is reconstructed and may revise. Annual footer excluded.')
            for row in data.to_dict('records'):catalog.add(sid,row['date'],row[code])


def parse_year_lines(path):
    rows=[]
    for line in path.read_text().splitlines():
        m=re.match(r'^"([^"]+)"\s+(\d{4})\s+(.+)$',line)
        if not m:continue
        values=m[3].split()
        if len(values)>12:raise ValueError('Expected at most 12 monthly observations')
        for month,value in enumerate(values,1):rows.append((m[1],f'{m[2]}-{month:02d}',numeric(value)))
    return rows


def parse_release_calendar(path):
    text=unescape(re.sub('<[^>]+>',' ',path.read_text()))
    result={}
    pattern=r'([A-Za-z]+)\s+(\d{4})\s+(\d{1,2}-[A-Za-z]+-\d{4})'
    for month,year,date in re.findall(pattern,text):
        try:key=pd.Timestamp(month+' 1 '+year).strftime('%Y-%m');value=pd.Timestamp(date).date().isoformat()
        except ValueError:continue
        if key in result and result[key]!=value:raise ValueError('Ambiguous G17 release month')
        result[key]=value
    if len(result)<800:raise ValueError('Release calendar parse incomplete')
    return result


def parse_g17(catalog):
    codes={'B50001':'TOTAL','B00004':'MANUFACTURING','G21':'MINING','G2211A2':'UTILITIES'}
    path=EXTERNAL/'macroeconomic/raw/g17_ip_sa.txt'
    for code,name in codes.items():
        catalog.register('US_IP_'+name,'Industrial production '+name.lower(),'M','index 2017=100 SA','Federal Reserve Board G.17',path,'macroeconomic',source_code=code,
            notes='Latest revised index, not original releases. Base year checked in G17 current documentation.')
    for code,period,value in parse_year_lines(path):
        if code in codes:catalog.add('US_IP_'+codes[code],period,value)
    path=EXTERNAL/'macroeconomic/raw/g17_revisions.txt';calendar=parse_release_calendar(EXTERNAL/'macroeconomic/raw/g17_release_dates.html')
    for prefix in ['init','rev1']:
        for code,name in codes.items():
            sid='US_IP_'+name+'_GROWTH_'+prefix.upper()
            catalog.register(sid,'Industrial production '+name.lower()+' monthly growth '+prefix,'M','percent month-over-month SA','Federal Reserve Board G.17 real-time history',path,'macroeconomic',
                source_code=prefix+'.'+code.lower()+'.pct',availability='historical_release_vintage',
                notes='Provider-published growth, not growth computed across rebased initial indexes. Observation month released next month for init, two months later for rev1, mapped to the official release calendar. No dates guessed when calendar missing.')
    for code,period,value in parse_year_lines(path):
        parts=code.split('.')
        if len(parts)!=3 or parts[0] not in {'init','rev1'} or parts[2]!='pct' or parts[1].upper() not in codes:continue
        prefix=parts[0];sid='US_IP_'+codes[parts[1].upper()]+'_GROWTH_'+prefix.upper()
        release_month=(pd.Period(period,freq='M')+(1 if prefix=='init' else 2)).strftime('%Y-%m')
        publication=calendar.get(release_month,'')
        catalog.add(sid,period,value,publication_date=publication,vintage_date=publication,
            source_status='official_release_calendar' if publication else 'release_date_missing')


def parse_ucdp(catalog):
    path=EXTERNAL/'political/raw/ucdp_26_1.zip'
    with zipfile.ZipFile(path) as z:data=pd.read_csv(z.open('UcdpPrioConflict_v26_1.csv'))
    if data[['conflict_id','year']].duplicated().any():raise ValueError('UCDP conflict/year duplicate')
    if set(data.version)!={26.1}:raise ValueError('UCDP version mismatch')
    from external_historical_political import contains_us
    us=pd.concat([data[k].map(contains_us) for k in ['gwno_a','gwno_b','gwno_a_2nd','gwno_b_2nd']],axis=1).any(axis=1)
    # Codes are explicit Gleditsch-Ward country identifiers, not actor IDs.
    for sid,name,geography in [('GLOBAL_STATE_CONFLICTS','Active state-based armed conflicts','WORLD'),
        ('GLOBAL_HIGH_INTENSITY_CONFLICTS','State-based conflicts with >=1000 battle deaths that year','WORLD'),
        ('US_TROOP_INVOLVEMENT_CONFLICTS','State-based conflicts with US primary/secondary troop involvement','USA')]:
        catalog.register(sid,name,'A','distinct conflicts','UCDP/PRIO Armed Conflict Dataset v26.1',path,'political',geography=geography,
            license='CC BY 4.0; cite Davies, Pettersson & Oberg (2026), Gleditsch et al. (2002), Pettersson codebook v26.1',
            notes='Annual >=25 battle-death threshold; original conflict type/actor/date-precision taxonomy preserved in raw file. US GW country code 2; not all forms of military involvement. Source historical coding is retrospective.')
    for year in range(int(data.year.min()),int(data.year.max())+1):
        frame=data.loc[data.year.eq(year)];catalog.add('GLOBAL_STATE_CONFLICTS',str(year),len(frame))
        catalog.add('GLOBAL_HIGH_INTENSITY_CONFLICTS',str(year),int(frame.intensity_level.eq(2).sum()))
        catalog.add('US_TROOP_INVOLVEMENT_CONFLICTS',str(year),int((data.year.eq(year)&us).sum()))


def federal_election_day(year):
    """Statutory Tuesday following first Monday of November; not voting-window dates."""
    first=dt.date(year,11,1)
    return first+dt.timedelta(days=(0-first.weekday())%7+1)


def parse_supplement(catalog):
    # Michigan explicitly permits noncommercial/internal research but requires
    # separate permission for redistribution. Every numeric value stays local.
    for filename,freq,fields in [
        ('umich_monthly_1.csv','M',{'Index':('US_CONSUMER_SENTIMENT','Consumer sentiment index','index 1966Q1=100')}),
        ('umich_Q_1.csv','Q',{'Index':('US_CONSUMER_SENTIMENT_QUARTERLY','Consumer sentiment, original quarterly archive','index 1966Q1=100')}),
        ('umich_M_5.csv','M',{'Current Index':('US_CONSUMER_CURRENT_CONDITIONS','Consumer current-conditions index','index 1966Q1=100'),
                             'Expected Index':('US_CONSUMER_EXPECTATIONS','Consumer expectations index','index 1966Q1=100')}),
        ('umich_M_32.csv','M',{'Median':('US_EXPECTED_INFLATION_1Y_MEDIAN','Median expected price change over next year','percent'),
                              'Interquartile Range (75th-25th)':('US_EXPECTED_INFLATION_1Y_IQR','Interquartile spread of expected next-year price change','percentage points')}),
        ('umich_M_34.csv','M',{'Good Job':('US_GOV_ECON_POLICY_GOOD_SHARE','Government economic-policy opinion: Good Job','percent of responses'),
                              'Poor Job':('US_GOV_ECON_POLICY_POOR_SHARE','Government economic-policy opinion: Poor Job','percent of responses')})]:
        path=EXTERNAL/'macroeconomic/raw'/filename;data=pd.read_csv(path,skiprows=1)
        period_field='Month' if freq=='M' else 'Quarter'
        if data[['Year',period_field]].duplicated().any():raise ValueError('Duplicate Michigan period')
        for column,(sid,name,unit) in fields.items():
            if column not in data:raise ValueError('Michigan schema changed: '+column)
            category='political' if sid.startswith('US_GOV_') else 'macroeconomic'
            catalog.register(sid,name,freq,unit,'Surveys of Consumers, Survey Research Center, University of Michigan',path,category,source_code=filename+':'+column,
                license='Copyright 1946-2026 Regents of University of Michigan; CC BY-NC-ND for noncommercial/internal research; redistribution requires separate permission; values local only',redistribute=False,
                notes='Final archive snapshot, not preliminary vintages. Original publication dates not provided. Monthly history starts 1978; quarterly archive is separate. Telephone-to-web collection transition in 2024 affects comparability; no automatic break adjustment.')
            for row in data.to_dict('records'):
                year=int(row['Year']);part=int(row[period_field])
                if not 1<=part<=(12 if freq=='M' else 4):raise ValueError('Invalid Michigan period')
                period=f'{year}-{part:02d}' if freq=='M' else f'{year}Q{part}'
                catalog.add(sid,period,row[column])
    path=EXTERNAL/'social/raw/noaa_us_temperature.json';data=json.loads(path.read_text())
    if data['description']!={'title':'Contiguous U.S. Average Temperature','units':'Degrees Fahrenheit','base_period':'1901-2000'}:raise ValueError('NOAA temperature definition changed')
    for field,sid,name,unit in [('value','US_CONTIGUOUS_TEMPERATURE','Contiguous-US monthly average temperature','degrees Fahrenheit'),
                              ('departure','US_CONTIGUOUS_TEMPERATURE_ANOMALY','Contiguous-US temperature anomaly vs 1901-2000 same-month baseline','degrees Fahrenheit departure')]:
        catalog.register(sid,name,'M',unit,'NOAA NCEI Climate at a Glance',path,'social',geography='USA contiguous 48 states',source_code='110/tavg/1/0:'+field,
            notes='Monthly nClimDiv national estimate; land-area aggregation, not audience weather exposure. Revised snapshot; source anomalies preserved in Fahrenheit; original release dates unknown.')
        for period,row in data['data'].items():
            if not re.fullmatch(r'\d{6}',period):raise ValueError('NOAA period changed')
            catalog.add(sid,period[:4]+'-'+period[4:],row[field])
    # Factual NBER turning points and their delayed announcements are distinct.
    path=EXTERNAL/'macroeconomic/raw/nber_cycles.xlsx';data=pd.read_excel(path,header=None);events=[]
    for _,row in data.iterrows():
        peak=re.fullmatch(r'([A-Za-z]+)\s+(\d{4})\s+\((\d{4}Q[1-4])\)',str(row[2]).strip())
        trough=re.fullmatch(r'([A-Za-z]+)\s+(\d{4})\s+\((\d{4}Q[1-4])\)',str(row[3]).strip())
        if not peak or not trough:continue
        begin=pd.Timestamp(peak[1]+' 1 '+peak[2]).to_period('M');end=pd.Timestamp(trough[1]+' 1 '+trough[2]).to_period('M')
        if end<=begin or end.ordinal-begin.ordinal!=int(row[6]):raise ValueError('NBER duration differs from month dates')
        events.append({'peak_month':str(begin),'trough_month':str(end),'peak_quarter_source':peak[3],'trough_quarter_source':trough[3]})
    if len(events)<30:raise ValueError('NBER chronology parse incomplete')
    write_csv(EXTERNAL/'macroeconomic/nber_turning_points.csv',events)
    sid='US_NBER_DATED_RECESSION'
    catalog.register(sid,'Membership in NBER dated recession intervals','M','binary retrospective dated interval','NBER Business Cycle Dating Committee',path,'macroeconomic',
        license='NBER publicly downloadable factual chronology; no general redistribution license established; values retained locally',redistribute=False,
        transformation='1 for months strictly after peak and through trough; 0 otherwise, only through latest closed cycle',
        notes='Right-censored at last dated trough. No assumption that subsequent months have been certified as expansion. Monthly peak and source quarterly peak may differ; source quarter labels retained separately.')
    end=max(e['trough_month'] for e in events)
    for month in pd.period_range('1958-01',end,freq='M'):
        value=int(any(pd.Period(e['peak_month'],'M')<month<=pd.Period(e['trough_month'],'M') for e in events))
        catalog.add(sid,str(month),value)
    path=EXTERNAL/'macroeconomic/raw/nber_faq.html';tables=pd.read_html(io.StringIO(path.read_text()),header=0)
    table=next((t for t in tables if 'Announcement Date' in t.columns),None)
    if table is None:raise ValueError('NBER announcement table missing')
    sid='US_NBER_LAST_ANNOUNCED_TURNING_POINT'
    catalog.register(sid,'Latest announced NBER turning-point type (peak=1, trough=0)','D','binary event type, not current recession truth','NBER Business Cycle Dating Committee',path,'macroeconomic',
        license='NBER publicly offered factual announcement dates; no general redistribution license established; values retained locally',redistribute=False,
        availability='historical_release_vintage',transformation='announcement event: peak=1, trough=0; as-of view carries last announced event with age',
        notes='Retrospective announcements occur months after turning points; event status is not actual contemporaneous recession membership. Date known to day, no intraday timing guarantee.')
    kind=None
    for row in table.to_dict('records'):
        period=str(row['Month of Turning Point'])
        if 'Peaks' in period:kind=1;continue
        if 'Troughs' in period:kind=0;continue
        if kind is None:raise ValueError('NBER event type not defined')
        announced=pd.Timestamp(str(row['Announcement Date']).replace(',',' ')).date().isoformat()
        catalog.add(sid,announced,kind,publication_date=announced,vintage_date=announced,source_status='turning_point_month='+pd.Timestamp(period).strftime('%Y-%m'))


def parse_politics(catalog):
    path=EXTERNAL/'political/raw/party_government.html'
    table=pd.read_html(io.StringIO(path.read_text()))[0]
    if list(table)!=['Congress','House Majority','Senate Majority','Presidency','Party Government']:raise ValueError('House party table changed')
    rows=[]
    for row in table.to_dict('records'):
        match=re.search(r'(\d+)(?:st|nd|rd|th)\s*\((\d{4})[–-](\d{4})\)',row['Congress'])
        if not match:raise ValueError('Unknown Congress interval')
        number,start,end=map(int,match.groups())
        if end<1958:continue
        rows.append({'congress':number,'period_start':f'{start}-01-03','period_end_exclusive':f'{end}-01-03',
            'house_majority_source':row['House Majority'],'senate_majority_source':row['Senate Majority'],
            'presidency_source':row['Presidency'],'party_government_source':row['Party Government'],
            'frequency':'congress_term_summary','source_url':metadata(path)['url'],'retrieval_date':metadata(path)['retrieval_date'],
            'within_term_changes':'Source footnotes and multi-party cells retained verbatim; term summary is not a daily control series',
            'publication_date':'','vintage_date':'','license':'US government factual table; attribution requested'})
    write_csv(EXTERNAL/'political/congress_party_context.csv',rows)
    elections=[]
    for year in range(1956,2025,4):
        path=EXTERNAL/f'political/raw/election_{year}.html'
        if not path.exists():continue
        tables=pd.read_html(io.StringIO(path.read_text()))
        table=next((t for t in tables if t.astype(str).apply(lambda c:c.str.fullmatch('President').any()).any()),None)
        if table is None:raise ValueError('NARA election summary missing')
        lookup={str(row.iloc[0]).strip().rstrip('*:'):row for _,row in table.iterrows()}
        winner=str(lookup['President'].iloc[1]);votes=lookup['Electoral Vote']
        win=re.search(r'Winner:\s*(\d+)',str(votes.iloc[1]));opponent=re.search(r'Main Opponent:\s*(\d+)',str(votes.iloc[2]));total=re.search(r'Total/Majority:\s*(\d+)',str(votes.iloc[3]))
        if not all([win,opponent,total]):raise ValueError('NARA vote counts not parsed')
        elections.append({'election_year':year,'scheduled_election_date':federal_election_day(year).isoformat(),
            'winner_source':winner,'opponent_source':str(lookup['Main Opponent'].iloc[1]),'winner_electoral_votes':int(win[1]),
            'main_opponent_electoral_votes':int(opponent[1]),'total_electoral_votes':int(total[1]),'frequency':'election_event',
            'source_url':metadata(path)['url'],'retrieval_date':metadata(path)['retrieval_date'],'publication_date':'',
            'availability_status':'retrospective_certified_result_not_available_on_election_morning',
            'license':'US government factual table; attribution requested'})
    write_csv(EXTERNAL/'political/presidential_election_results.csv',elections)
    # Calendar indicators are not fitted event sentiment/intensity scores.
    path=EXTERNAL/'political/raw/election_calendar_law_current.html'
    if not path.exists():fetch('https://uscode.house.gov/us/usc/119-136/t2/s7/',path)
    if 'Tuesday next after the 1st Monday in November' not in path.read_text():
        raise ValueError('Election calendar source lacks the statutory timing rule')
    for sid,name in [('US_FEDERAL_ELECTION_MONTH','Scheduled federal general-election month'),('US_PRESIDENTIAL_ELECTION_MONTH','Scheduled presidential-election month')]:
        catalog.register(sid,name,'M','binary calendar indicator','US statutory election calendar',path,'political',
            availability='known_calendar_rule',
            transformation='Tuesday after first Monday in November in even years; presidential election every fourth year',
            notes='Scheduled general-election day only; excludes early voting, special elections and result announcement timing. Presidential timing corroborated by National Archives election records.')
        for month in pd.period_range('1958-01','2026-10',freq='M'):
            divisor=4 if sid=='US_PRESIDENTIAL_ELECTION_MONTH' else 2
            catalog.add(sid,str(month),int(month.month==11 and month.year%divisor==0))


def normalize():
    from external_historical_political import parse as parse_political_extra
    catalog=Catalog()
    for parser in [parse_bls,parse_h15,parse_bea,parse_worldbank,parse_french,parse_g17,parse_ucdp,parse_politics,parse_supplement,parse_political_extra]:
        parser(catalog);print(parser.__name__,len(catalog.series),len(catalog.rows),flush=True)
    frame=pd.DataFrame(catalog.rows).sort_values(['series_id','date','vintage_date']).reset_index(drop=True)
    if frame[['series_id','date','vintage_date']].duplicated().any():raise ValueError('Duplicate normalized source observations')
    for category,group in frame.groupby('category'):
        write_csv(EXTERNAL/category/'observations.csv.xz',group)
    write_csv(HISTORY/'series_dictionary.csv',list(catalog.series.values()));write_json(HISTORY/'source_anomalies.json',catalog.anomalies)
    return frame,catalog.series


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['acquire','normalize']);args=p.parse_args()
    acquire() if args.action=='acquire' else normalize()
