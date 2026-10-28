"""Small, versioned conflict and policy supplements; no event-intensity invention."""
from __future__ import annotations
import json
import re
import zipfile

import pandas as pd

from enrichment_common import EXTERNAL, fetch

OX_REVISION='e7f66ee39654293b5c068efd2f195bd591dc27f6'
OX_INDICES={'Stringency':'STRINGENCY','GovernmentResponse':'GOVERNMENT_RESPONSE',
            'ContainmentHealth':'CONTAINMENT_HEALTH','EconomicSupport':'ECONOMIC_SUPPORT'}


def acquire():
    for url,name in [('https://ucdp.uu.se/downloads/brd/ucdp-brd-conf-261-csv.zip','ucdp_battle_deaths.zip'),
        ('https://ucdp.uu.se/downloads/vpp/UCDP_VPP_Dataset_v26_1.xlsx','ucdp_violent_protest.xlsx'),
        ('https://ucdp.uu.se/downloads/brd/ucdp-brd-codebook-261.pdf','ucdp_brd_codebook.pdf'),
        ('https://ucdp.uu.se/downloads/vpp/vpp_codebook_v20_1.pdf','ucdp_vpp_codebook.pdf')]:
        fetch(url,EXTERNAL/'political/raw'/name,limit=5_000_000)
    for name in OX_INDICES:
        fetch(f'https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/{OX_REVISION}/data/timeseries_indices/OxCGRT_timeseries_{name}Index_v1.csv',
              EXTERNAL/f'political/raw/oxcgrt_{name}.csv',limit=4_000_000)
    for name in ['documentation_and_codebook.md','LICENSE.txt']:
        fetch(f'https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/{OX_REVISION}/{name}',EXTERNAL/'political/raw'/('oxcgrt_'+name))


def contains_us(value):
    return '2' in {x.strip().removesuffix('.0') for x in str(value).split(',')}


def parse(catalog):
    path=EXTERNAL/'political/raw/ucdp_battle_deaths.zip'
    with zipfile.ZipFile(path) as z:data=pd.read_csv(z.open('BattleDeaths_v26_1_conf.csv'))
    if data[['conflict_id','year']].duplicated().any() or set(data.version)!={26.1}:raise ValueError('UCDP battle-death identity/version differs')
    if not ((data.bd_low<=data.bd_best)&(data.bd_best<=data.bd_high)&(data.bd_low>=0)).all():raise ValueError('Invalid fatality uncertainty interval')
    us=pd.concat([data[k].map(contains_us) for k in ['gwno_a','gwno_b','gwno_a_2nd','gwno_b_2nd']],axis=1).any(axis=1)
    for scope,selection in [('GLOBAL',pd.Series(True,index=data.index)),('US_INVOLVED_CONFLICTS',us)]:
        for bound in ['low','best','high']:
            sid=scope+'_BATTLE_DEATHS_'+bound.upper()
            catalog.register(sid,scope.replace('_',' ').title()+' battle-related deaths, '+bound+' estimate','A','battle-related deaths',
                'UCDP Battle-Related Deaths v26.1, conflict-year',path,'political',geography='WORLD',source_code='bd_'+bound,
                license='CC BY 4.0; cite Davies, Pettersson & Oberg (2026), Pettersson BRD codebook v26.1',
                transformation='Sum conflict-year '+bound+' estimates; '+('all conflicts' if scope=='GLOBAL' else 'conflicts with US GW-code 2 troop involvement'),
                notes='Low/best/high are source uncertainty bounds, not statistical confidence intervals. US-involved conflict deaths are NOT US deaths or deaths caused by the US. Direct combat-related deaths only; historical estimates revised; not a within-US geographic measure.')
            for year in range(int(data.year.min()),int(data.year.max())+1):
                catalog.add(sid,str(year),int(data.loc[data.year.eq(year)&selection,'bd_'+bound].sum()))
    path=EXTERNAL/'political/raw/ucdp_violent_protest.xlsx';data=pd.read_excel(path)
    if data[['Dyad ID','Year']].duplicated().any() or set(data.Version)!={'Version 26.1'}:raise ValueError('VPP identity/version differs')
    for scope in ['GLOBAL','US']:
        sid=scope+'_VIOLENT_POLITICAL_PROTEST_DYADS'
        catalog.register(sid,scope+' violent political-protest dyads above UCDP inclusion threshold','A','distinct dyads',
            'UCDP Violent Political Protest Dataset v26.1',path,'political',geography='WORLD' if scope=='GLOBAL' else 'USA',
            license='CC BY 4.0; cite Svensson, Schaftenaar & Allansson (2022), UCDP VPP v26.1',
            transformation='Count source dyad-year rows; '+('all locations' if scope=='GLOBAL' else 'GWNOLoc=2'),
            notes='Violent political protests meeting the source >=25-death threshold; not all protest events, peaceful protest, or general unrest. Source actor/incompatibility/outcome taxonomy retained in original workbook, including original spelling. Codebook linked by provider remains v20.1; dataset version is 26.1.')
        for year in range(int(data.Year.min()),int(data.Year.max())+1):
            selection=data.Year.eq(year)
            if scope=='US':selection&=data.GWNOLoc.map(contains_us)
            catalog.add(sid,str(year),int(selection.sum()))
    for name,stem in OX_INDICES.items():
        path=EXTERNAL/f'political/raw/oxcgrt_{name}.csv';data=pd.read_csv(path)
        selected=data.loc[data.CountryCode.eq('USA')&data.Jurisdiction.eq('NAT_TOTAL')&data.RegionCode.isna()&data.CityCode.isna()]
        if len(selected)!=1:raise ValueError('Ambiguous US national policy row')
        sid='US_OXCGRT_'+stem+'_DAILY'
        catalog.register(sid,'US OxCGRT '+name+' source Average index, NAT_TOTAL','D','index points 0-100',
            'Oxford COVID-19 Government Response Tracker final v1',path,'political',source_code='USA:NAT_TOTAL:'+name+'Index_Average',
            vintage_date=OX_REVISION,license='CC BY 4.0; Hale et al. (2021), Oxford COVID-19 Government Response Tracker, Blavatnik School of Government, University of Oxford',
            notes='Final retrospective coding; no original publication dates. Source Average vaccination-group convention; national total includes policies from multiple levels, not a US state/population average and not compliance or effectiveness. Version '+OX_REVISION+'. Dates outside source coverage are missing, never zero.')
        date_columns=[c for c in data if re.fullmatch(r'\d{2}[A-Za-z]{3}\d{4}',c)]
        if len(date_columns)!=len(data.columns)-7:raise ValueError('Unknown policy date columns')
        for col in date_columns:
            date=pd.to_datetime(col,format='%d%b%Y').date().isoformat();value=selected.iloc[0][col]
            if pd.notna(value) and not 0<=value<=100:raise ValueError('Policy index outside source scale')
            catalog.add(sid,date,value)


if __name__=='__main__':acquire()
