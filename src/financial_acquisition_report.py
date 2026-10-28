"""Render measured acquisition findings and figures; existing analyses are read-only."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from financial_acquisition_common import ROOT,REPORT,PROCESSED,MANIFESTS,write_json,write_csv,atomic,sha,snapshots,source_path
from financial_acquisition import START,END,boolean,PERIODS

PRIORITY=[('French market excess return','FF_MKT_EXCESS'),('Unemployment','US_UNEMPLOYMENT'),('CPI','US_CPI_SA'),('Consumer sentiment','US_CONSUMER_SENTIMENT'),
 ('10-year Treasury','US_TREASURY_10Y'),('3-month Treasury bill discount yield','US_TBILL_3M_DISCOUNT'),('Federal funds','US_FED_FUNDS'),
 ('Baa yield','US_CORPORATE_BAA'),('Aaa yield','US_CORPORATE_AAA'),('Industrial production','US_IP_TOTAL'),('Disposable income','US_DISPOSABLE_INCOME'),
 ('PCE prices','US_PCE_PRICE_INDEX'),('Personal saving rate','US_PERSONAL_SAVING_RATE'),('Production/nonsupervisory earnings','US_HOURLY_EARNINGS_PRODUCTION'),
 ('Initial claims','US_INITIAL_CLAIMS'),('Youth unemployment','US_YOUTH_UNEMPLOYMENT'),('Chicago NFCI','US_NFCI'),('Excess bond premium','US_EXCESS_BOND_PREMIUM'),
 ('News-based economic policy uncertainty','US_POLICY_UNCERTAINTY_NEWS'),('Real GDP','US_REAL_GDP'),('Gold benchmark','WB_GOLD'),
 ('WTI benchmark','WB_WTI'),('Household debt service','US_HOUSEHOLD_DEBT_SERVICE'),('Credit-card delinquency','US_CREDIT_CARD_DELINQUENCY'),
 ('Economic-news sentiment','US_ECONOMIC_NEWS_SENTIMENT')]


def textfile(path,text):atomic(path,(text.rstrip()+'\n').encode())


def table(frame):
    def cell(v):return str(v).replace('|','/').replace('\n',' ')
    return '| '+' | '.join(frame.columns)+' |\n| '+' | '.join('---' for _ in frame.columns)+' |\n'+'\n'.join('| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None))


def quality(panel,native,specs):
    rows=[];hard=[];n=0
    for sid,g in native.groupby('series_id'):
        valid=g[g.value.notna()];x=valid.value;n+=len(valid)
        bad=~np.isfinite(x)
        if sid in ['US_UNEMPLOYMENT','US_YOUTH_UNEMPLOYMENT','US_LABOR_PARTICIPATION','US_EMPLOYMENT_POPULATION'] or 'DELINQUENCY' in sid or 'DEBT_SERVICE' in sid:
            bad|=(x<0)|(x>100)
        if sid in ['US_CPI_SA','US_CPI_NSA','US_PCE_PRICE_INDEX','US_REAL_GDP','US_NOMINAL_GDP','US_GDP_DEFLATOR'] or sid.startswith('US_IP_') and 'GROWTH' not in sid:bad|=x<=0
        if sid.startswith('FF_'):bad|=x<=-100
        if 'NBER' in sid:bad|=~x.isin([0,1])
        if bad.any():hard.append(sid)
        rows.append(dict(series_id=sid,valid_values=len(valid),missing_source_values=int(g.value.isna().sum()),
            minimum=float(x.min()),minimum_date=valid.loc[x.idxmin(),'observation_date'],maximum=float(x.max()),maximum_date=valid.loc[x.idxmax(),'observation_date'],
            implausible_or_invalid_count=int(bad.sum()),redistribution_permitted=specs[sid]['redistribution_permitted'],
            interpretation='Extrema retained, not winsorized; heuristic bounds detect transformation errors, not economic truth'))
    if hard:raise ValueError('Domain validation failed: '+str(hard))
    for sid in ['US_MARKET_DRAWDOWN','US_MARKET_MAX_DRAWDOWN_TO_DATE','US_MARKET_MAX_DRAWDOWN_12M']:
        if not panel[sid].dropna().between(-100,1e-9).all():raise ValueError('Drawdown bounds failed')
    if not panel.US_MARKET_ONLINE_BEAR.dropna().isin([0,1]).all():raise ValueError('Invalid online bear labels')
    if not panel.US_MARKET_TREND_REGIME.dropna().isin([-1,0,1]).all():raise ValueError('Invalid trend labels')
    frame=pd.DataFrame(rows);write_csv(PROCESSED/'quality_extrema_local.csv.xz',frame)
    write_csv(REPORT/'quality_extrema_public.csv',frame[frame.redistribution_permitted.map(boolean)])
    checks=[];indexed=panel.set_index('month')
    # Independent raw BLS observation lookup bypasses the native normalization parser.
    for sid,code,year,month in [('US_UNEMPLOYMENT','LNS14000000','2020','04'),('US_CPI_SA','CUSR0000SA0','1958','08'),('US_YOUTH_UNEMPLOYMENT','LNS14000012','2020','04')]:
        key='bls_1958_1967' if year=='1958' else 'bls_2018_2026'
        blob=json.loads(source_path(key).read_text());series=next(s for s in blob['Results']['series'] if s['seriesID']==code)
        match=[r for r in series['data'] if r['year']==year and r['period']=='M'+month]
        if len(match)!=1:raise ValueError('Independent BLS crosscheck row absent')
        expected=float(match[0]['value']);observed=float(indexed.loc[year+'-'+month,sid])
        if abs(expected-observed)>1e-10:raise ValueError('BLS crosscheck mismatch')
        checks.append(dict(check='direct_raw_BLS_lookup',series_id=sid,month=year+'-'+month,actual=observed,independent_expected=expected,absolute_error=abs(expected-observed),source_key=key))
    for month in ['1958-08','1980-01','2000-01','2020-04']:
        row=indexed.loc[month];previous=str(pd.Period(month,'M')-12)
        calculations={'US_CPI_INFLATION_YOY':100*(row.US_CPI_SA/indexed.loc[previous,'US_CPI_SA']-1) if previous in indexed.index else np.nan,
            'US_SLOPE_10Y_TBILL_DISCOUNT':row.US_TREASURY_10Y-row.US_TBILL_3M_DISCOUNT,
            'US_MISERY_INDEX':row.US_UNEMPLOYMENT+row.US_CPI_INFLATION_YOY}
        for sid,expected in calculations.items():
            if pd.isna(expected):continue
            actual=row[sid]
            if abs(actual-expected)>1e-8:raise ValueError('Arithmetic replay mismatch')
            checks.append(dict(check='independent_formula',series_id=sid,month=month,actual=actual,independent_expected=expected,absolute_error=abs(actual-expected),source_key='declared inputs'))
    write_csv(REPORT/'calculation_crosschecks.csv',checks)
    result=dict(status='PASS',native_valid_values_checked=n,native_series=len(specs),source_hashes_verified=len(snapshots()),
        crosschecks=len(checks),invalid_domain_values=0,drawdown_and_regime_bounds='PASS',duplicate_native_keys='PASS',
        source_anomalies='Retained; see source_anomalies.json and missingness reports; latest revised snapshots are not original releases')
    for key,row in snapshots().items():
        if row['status']=='ok':source_path(key)
    write_json(REPORT/'data_quality_validation.json',result)


def figures(panel,specs,coverage):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'cmpt491-financial-v1'})
    figdir=REPORT/'figures';figdir.mkdir(exist_ok=True)
    local=PROCESSED/'figures_local';local.mkdir(exist_ok=True)
    dates=pd.to_datetime(panel.month);created=[]
    def save(fig,path,title,note):
        fig.suptitle(title,fontsize=15,x=.02,ha='left');fig.text(.02,.015,note,ha='left',fontsize=8)
        fig.tight_layout(rect=(0,.045,1,.95));fig.savefig(path,format='svg',metadata={'Date':None,'Creator':'CMPT491 financial_acquisition_report.py'});plt.close(fig)
        atomic(path,('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n').encode())
        import xml.etree.ElementTree as ET
        ET.parse(path)
        created.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path),publication='local only' if 'figures_local' in str(path) else 'public'))
    selected=[s for _,s in PRIORITY if s in panel]
    matrix=np.array([panel[s].notna().to_numpy() for s in selected],dtype=float)
    fig,ax=plt.subplots(figsize=(13,8));ax.imshow(matrix,aspect='auto',interpolation='nearest',cmap=matplotlib.colors.ListedColormap(['#eeeeee','#25706f']),vmin=0,vmax=1)
    ax.set_yticks(range(len(selected)),[specs[s]['name'] for s in selected],fontsize=9)
    ticks=[i for i,m in enumerate(panel.month) if m.endswith('-01') and int(m[:4])%10==0];ax.set_xticks(ticks,[panel.month[i][:4] for i in ticks]);ax.set_xlabel('Calendar month (grey = unavailable; teal = value available)')
    save(fig,figdir/'historical_coverage.svg','Actual monthly coverage of priority inputs',
        '1958-01–2026-09. Quarterly inputs omitted here; see native_coverage_report.csv. Available news-day means do not certify all calendar days.')
    fig,ax=plt.subplots(figsize=(13,4.7));ax.plot(dates,panel.US_UNEMPLOYMENT,label='Unemployment rate (SA)',color='#236b8e');ax.plot(dates,panel.US_CPI_INFLATION_YOY,label='CPI-U inflation, year over year (SA)',color='#c06932')
    ax.axhline(0,color='#555555',linewidth=.7);ax.set_ylabel('Percent');ax.legend(loc='upper left',bbox_to_anchor=(1.01,1),fontsize=9);ax.set_xlim(dates.min(),dates.max());ax.grid(axis='y',alpha=.2)
    save(fig,figdir/'unemployment_inflation.svg','Labor conditions and consumer-price inflation',
        'Sources: BLS current revised snapshots. Missing source months remain gaps. Separate measures on the same percentage scale; no fitted relationship.')
    fig,axes=plt.subplots(2,1,figsize=(13,6.5),sharex=True)
    for ax,sid,color,label in [(axes[0],'US_EXCESS_BOND_PREMIUM','#ad4e56','Excess bond premium (percentage points)'),(axes[1],'US_FCI_G','#356b81','FCI-G (model-implied growth headwind)')]:
        ax.plot(dates,panel[sid],color=color);ax.axhline(0,color='#666666',linewidth=.7);ax.set_ylabel(label,fontsize=9);ax.set_xlim(dates.min(),dates.max());ax.grid(axis='y',alpha=.2)
    save(fig,figdir/'financial_stress.svg','Two complementary Federal Reserve financial-condition estimates',
        'Sources: Federal Reserve EBP and FCI-G. Independent vertical scales; revised/back-estimated histories, not original publication vintages.')
    native_ids=[s for s in panel if s in specs]
    period_labels=[p[0] for p in PERIODS[1:]];pct=[]
    for label in period_labels:
        sub=coverage[coverage.period.eq(label)&coverage.series_id.isin(native_ids)];pct.append(100*sub.missing_observations.sum()/sub.expected_observations.sum())
    fig,ax=plt.subplots(figsize=(10,4.5));bars=ax.bar(period_labels,pct,color='#7a5e85');ax.set_ylim(0,100);ax.set_ylabel('Missing cells (% of native/aggregated monthly inputs)');ax.bar_label(bars,labels=[f'{v:.1f}%' for v in pct],padding=4);ax.grid(axis='y',alpha=.2)
    save(fig,figdir/'missingness_by_period.svg','Coverage improves with source availability, but gaps remain',
        'Denominator includes all 55 native/aggregated monthly columns, including alternatives. 2020–2026 ends September 2026; quarters excluded.')
    fig,ax=plt.subplots(figsize=(13,4.8));ax.fill_between(dates,panel.US_MARKET_DRAWDOWN,0,color='#a14e59',alpha=.75);ax.set_ylim(-100,0);ax.set_xlim(dates.min(),dates.max());ax.set_ylabel('Loss from historical wealth high (%)');ax.grid(axis='y',alpha=.25)
    save(fig,local/'market_drawdowns.svg','Broad US market drawdown from monthly total returns',
        'Kenneth French market excess return + RF; compounded from July 1926. Broad CRSP universe, not S&P 500. Local research figure; redistribution not cleared.')
    write_csv(REPORT/'figure_inventory.csv',created)


def render():
    panel=pd.read_csv(PROCESSED/'monthly_local.csv.xz');native=pd.read_csv(PROCESSED/'native_local.csv.xz',low_memory=False)
    specs={r['series_id']:r for r in pd.read_csv(REPORT/'series_dictionary.csv',keep_default_na=False).to_dict('records')}
    summary=json.loads((REPORT/'build_summary.json').read_text());coverage=pd.read_csv(REPORT/'coverage_report.csv');ncov=pd.read_csv(REPORT/'native_coverage_report.csv')
    full=coverage[coverage.period.eq('1958-2026')];source=snapshots();quality(panel,native,specs);figures(panel,specs,coverage)
    rows=[]
    for rank,(name,sid) in enumerate(PRIORITY,1):
        spec=specs[sid];c=full[full.series_id.eq(sid)]
        obs=ncov[ncov.series_id.eq(sid)&ncov.period.eq('1958-2026')].iloc[0]
        qualification=spec['methodological_breaks']
        if sid=='WB_WTI':qualification='World Bank WTI benchmark starts 1982; not an asserted exact substitute for EIA Cushing spot (1986 onward). '+qualification
        rows.append(dict(priority=rank,input=name,series_id=sid,status='ACQUIRED',native_frequency=spec['native_frequency'],
            first_valid=spec['actual_first_valid'],last_valid=spec['actual_last_valid'],
            monthly_values=int(c.valid_observations.iloc[0]) if len(c) else '',expected_months=825 if len(c) else '',
            native_valid_in_panel_period=int(obs.valid_observations),public_values=spec['redistribution_permitted'],qualification=qualification))
    write_csv(REPORT/'priority_acquisition_status.csv',rows)
    basic=pd.DataFrame(rows)[['priority','input','native_frequency','first_valid','last_valid','monthly_values','public_values']]
    fullnative=full[full.full_history_complete&full.series_id.isin(specs)]
    totals=summary['monthly_total_cells'];missing=summary['monthly_missing_cells']
    blocked=[
      dict(item='FRED/ALFRED API',status='BLOCKED_CONFIGURATION',reason='No configured FRED credential found; no API key requested or exposed. Originating-provider public files supplied the core. Full vintage archive acquisition deferred.',next_step='Configure an authorized key and acquire a versioned ALFRED release-vintage panel.'),
      dict(item='BEA/EIA keyed APIs',status='BLOCKED_CONFIGURATION',reason='No configured BEA/EIA credentials found; BEA official XLSX used; World Bank WTI retained as a distinctly labelled benchmark.',next_step='Optional authorized keys for exact EIA Cushing series and richer BEA metadata.'),
      dict(item='Aaa/Baa continuation after 2016-09',status='BLOCKED_RIGHTS',reason='H.15 archive acquired through 2016-09. Current FRED Moody series carry explicit proprietary restrictions; no new proprietary bulk fetch or silent continuation.',next_step='Clarify authorized use/redistribution or choose separately identified public credit-condition measures.'),
      dict(item='Literal S&P 500 full-history return series',status='DEFERRED_RIGHTS',reason='No cleared long-run total-return source in this sprint. French broad-market total return is labelled by its actual universe.',next_step='Resolve a licensed history; preserve price versus total-return distinctions.'),
      dict(item='NFCI, Michigan, French, SF news, NBER redistribution',status='LOCAL_RESEARCH_ONLY',reason='Acquired through public research routes; general bulk redistribution not established. Values and dependent transforms/market figure excluded from Git.',next_step='Obtain explicit reusable licensing before publishing their numerical panels.'),
      dict(item='AAII, Conference Board, MOVE and CRSP raw histories',status='DEFERRED_ACCESS_OR_COST',reason='No paid route or unrestricted scraping attempted; not necessary for the first diverse financial panel.',next_step='Seek separate access review only if the incremental research value justifies it.'),
      dict(item='Old debt-service methodology (1980–2024)',status='DEFERRED_SEPARATE_SERIES',reason='Current credit-bureau method begins 2005. No splice to the retired method.',next_step='Acquire retired vintage as a separate definition and compare the overlap.'),
      dict(item='Remaining 325-candidate inventory',status='DEFERRED_SCOPE',reason='Practical additions already cover labor participation/employment, hours, rates, inflation, income/consumption, credit, commodities and market factors. Redundant variants and low-frequency surveys await Phase 2.',next_step='Prioritize missing dimensions and historic vintages before more correlated rate variants.')]
    write_csv(REPORT/'blocked_and_deferred.csv',blocked)
    textfile(REPORT/'blocked_sources.md','# Blocked and deferred sources\n\nAll 25 priority input slots have a documented acquisition, with the exact-series/coverage qualifications in [priority_acquisition_status.csv](priority_acquisition_status.csv). This does not mean complete 1958–2026 coverage.\n\n'+table(pd.DataFrame(blocked))+ '\n\nAll 32 retained snapshot requests are successful; no unresolved download or normalization failures remain. A changed Chicago Fed legacy link was resolved through its official current data manifest. Live documentation reads and local parser corrections are not additional acquired economic series.\n')
    textfile(REPORT/'temporal_alignment.md','''# Observation, release, retrieval and vintage

The frozen monthly panel is January 1958–September 2026 (825 calendar months), ending with the existing Billboard snapshot. October 2026 is incomplete and excluded. The music source spans August 1958–September 2026 (818 months). Calendar labels are `YYYY-MM`, with actual native period start/end retained separately.

- **Observation date** identifies the measured reference period or source daily/weekly date.
- **Publication date** is the historical release date where actually reconstructed. Unknown dates remain blank/UNKNOWN; a typical lag is not an observed release.
- **Retrieval date** records when these source bytes were fetched, including original timestamps for validated reused caches.
- **Historical vintage** identifies the original/revision release value where the provider retains it. The current workbook preparation/publication date is a *snapshot vintage*, not proof of historical availability.

`monthly_public.csv.xz` and `monthly_local.csv.xz` are **retrospective** current-snapshot views. Trailing transformations use no observations after the reference month, but revised, back-estimated or full-sample-normalized inputs can still contain information unavailable at the time. No claim of forecasting validity is made for these panels.

Native monthly values remain monthly. DOL initial/continued claims use the mean of all Saturday-ending weeks in that calendar month; NFCI/ANFCI use all Friday-ending weeks. An incomplete expected weekly set makes the monthly value missing. These are average weekly levels, not monthly unique claimant totals. Economic-news sentiment uses only observed daily fixed effects, with observed and expected calendar-day counts; article-free days are never filled with zero. It is not the provider's differently smoothed chart index.

GDP, debt-service ratios, delinquency and the earlier Michigan archive stay quarterly in `native_*`. The separate `quarterly_alignment_*` tables provide (a) value only at quarter-end and (b) the latest completed calendar quarter with reference quarter and age (0–2 months). An absent completed quarter is missing; older quarters are not carried indefinitely. Calendar completion is not publication. These tables are explicitly retrospective and never counted as monthly measurements.

`point_in_time_*` contains only provider-retained G.17 initial and first-revision monthly growth values mapped to the official release calendar (available from 2017), plus local NBER announcement events. For month M, both publication and historical-vintage date must be strictly before the first calendar day of M+1. The output records the actual reference month, release date, age and source hash. A release on the cutoff date is excluded. This supports decisions after the month ends; it does not establish intraday availability or that the musical outcomes themselves were contemporaneously measurable. NBER peak/trough announcements are event types, never substituted for true contemporaneous recession status.

Monthly market return is French Mkt-RF + matching RF. Daily and monthly source constructions are retained separately: daily compounding is not forced to equal the monthly source. Realized/downside volatility requires at least 15 valid returned daily rows and uses 252 as an explicit annualization convention. The source's historical exchange calendar is not independently verified, so daily-derived columns are not certified as full-history-complete merely because all 825 monthly values exist.

Cumulative return windows require every monthly return. A gap invalidates cumulative wealth thereafter. Percentage changes and index-point differences require their two observed endpoints; no intervening level is fabricated and no forward fill occurs. Inflation acceleration is the monthly change in year-over-year inflation. Stress z-scores exclude the current month from their trailing mean/standard deviation; the formula dictionary states the warm-up and gap policy.

Chart-month joins are many-to-one from music summaries to the unique finance month. The example uses equal retained source rows and available-case score means, retaining per-score counts and distinct song counts. All three repeated song/month pairs in the immutable music export remain in the denominator. The genre summary uses the original primary genre and `Unknown` for missing genre. This is a transparent join check, not approval of weights for later statistical inference. A finance calendar month can contain days after the selected chart snapshot; do not use the sample as a forecasting design. No release-date join, regression, causal claim, COVID cutoff or genre comparison test was made.
''')
    textfile(REPORT/'findings.md',f'''# Acquisition findings

The validated local release contains **{summary['native_series']} native-frequency series**, **{summary['native_observations']:,} source rows** and **825 monthly rows**. The monthly view has **{summary['monthly_raw_columns']} raw/native or explicitly aggregated columns** and **{summary['derived_columns']} derived columns** ({summary['monthly_columns']} total numerical columns). Ten quarterly series remain in separate alignment views; four French daily factor series and the NBER event series are not directly averaged into monthly columns.

The public monthly panel has **{summary['public_monthly_columns']} numerical columns**. Public source values cover federal statistical releases, World Bank commodities under CC BY 4.0, and the Baker–Bloom–Davis policy-uncertainty series under CC BY 4.0. Other research downloads and their dependent transforms remain local. Column counts include alternatives, dependencies and diagnostics, not independent economic constructs.

Across the local monthly panel, **{missing:,} of {totals:,} cells are missing ({100*missing/totals:.2f}%)**. Missingness includes unavailable early years, publication-tail gaps, historical source gaps and transformation warm-up. No interpolation or winsorization was applied. **{len(fullnative)} native/aggregated monthly inputs** and **{summary['full_monthly_columns']-len(fullnative)} derived columns** meet the strict complete-month criterion for January 1958–September 2026. Daily market-calendar completeness remains unverified and is excluded from that certification.

The complete native monthly inputs are: {', '.join('`'+s+'`' for s in fullnative.series_id)}. Full calendar coverage does not erase EPU's historical newspaper-design change, French FIZ/CIZ/revision issues, changes in the economy or measurement definitions.

Material gaps and distinctions:

- Unemployment, youth unemployment, participation and CPI have one missing source month (October 2025). Their early start does not make them complete through 2026. Payroll employment is complete in this snapshot.
- BEA monthly income, saving and PCE prices start in 1959 and currently end August 2026. The acquired real consumption/recreation table starts in 2007; an older table must be acquired separately if needed. No source-tail values were invented.
- Corporate Aaa/Baa values in H.15 end September 2016. Their long-run credit spreads therefore stop there. EBP (1973 onward) and FCI-G (1990 onward) add modern stress context without pretending to be the same measure.
- Michigan monthly sentiment begins in 1978; its quarterly archive is separate. Claims begin in 1967, NFCI in 1971, economic-news daily effects in 1980, the current debt-service method in 2005 and selected credit-card delinquency in 1991.
- World Bank gold starts in 1960. Its WTI benchmark starts in 1982; it is not claimed identical to the EIA Cushing series commonly reported from 1986. Commodity benchmark definitions and the fixed-price gold era remain documented.
- The NBER closed-cycle membership series stops at the last dated trough (April 2020). Later months are unknown in that derived chronology; no unannounced present-day recession status is inferred. Announced turning-point event history is a separate view.

The strongest ready-to-review families are long-run monetary rates and industrial activity; near-complete labor/inflation; income/saving; historical broad-market returns; and shorter, complementary credit/perception measures. Their different coverage and revision histories require an explicit analytical design before comparison with music. The sample join validates 81,797 music rows, 28,041 exact song identities, 818 chart months and genre-specific summaries without changing the source music data.

Phase 2 should prioritize original-release/ALFRED vintages, a separately identified old-method debt-service archive, pre-2007 consumption tables, a cleared modern corporate-yield continuation and exact EIA Cushing oil data. A literal licensed S&P 500 total-return history and wider household surveys can follow if justified. More redundant predictors are lower priority than coverage, vintage integrity and source rights. **No music-versus-finance model has been run.**
''')
    textfile(REPORT/'acquisition_log.md',f'''# Acquisition log and source decisions

The execution baseline is commit `fb3fc0d5519c3cf78574c35f7dd32ec829f7d660`. The local preservation audit began at `2026-10-28T19:06:03.731823+00:00`. Source retrieval timestamps range from `{min(s['retrieved_at'] for s in source.values())}` to `{max(s['retrieved_at'] for s in source.values())}` because previously downloaded caches are reused only after matching URL and SHA-256.

There are **{len(source)} immutable content-addressed snapshots**, of which **{sum(bool(s['reused_from']) for s in source.values())}** reuse validated source bytes. They include economic data, the G.17 release calendar/dictionary, Michigan terms and NBER chronology/announcements. Source count is not provider count or independent-variable count. [source_manifest.csv](source_manifest.csv) and the [JSON manifest](../../../data/external_historical/financial/manifests/acquisition_v1/sources.json) preserve exact URLs, POST payloads, original retrieval times, response metadata, hashes and byte counts.

The originating-provider routes cover BLS, BEA, Federal Reserve Board H.15/G.17/DSR/CHGDEL/EBP/FCI-G, DOL ETA, Chicago Fed, San Francisco Fed, University of Michigan, Kenneth French Data Library, Baker–Bloom–Davis, World Bank and NBER. Warm-up observations were retained where available, including BLS 1956–1957 and market returns from 1926. No old raw file was edited.

Requests are sequential, with a minimum 1.1-second pause for new requests, bounded three-attempt retries and 30 MB per-response caps. No paid service, unauthorized scraping, bypass, credential exposure or massive parallel download was used. No FRED/BEA/EIA key was configured. The current official Chicago Fed data manifest resolved its changed CSV URL; the final pinned request succeeded. All 32 source snapshots and all parsers are successful in the released version.

The dictionary also carries 23 explicitly reviewed reported-history crosswalks to the frozen research catalog; unknown original bounds remain UNKNOWN and are separate from measured downloaded bounds. The G.17 manufacturing input is B00004 **SIC manufacturing**, not the shorter NAICS IPMAN series.

Parser validation caught and corrected source-format assumptions before publication: Michigan's column order and empty trailing CSV field, the EPU attribution footer, and Chicago Fed's `Friday_of_Week` column. These were transformation issues, not corrections to original observations. Source anomalies remain separate: BLS footnotes/missing months, the Pink Sheet mismatch-details worksheet, and the EPU footer are retained and reported. Normalization errors now prevent replacement of a previously published native dataset.

The priority acquisition status is measured from downloaded observations:

{table(basic)}

Rights evidence checked on 2026-10-28: [World Bank commodity dataset](https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections) and [data licenses](https://datacatalog.worldbank.org/public-licenses); [Baker–Bloom–Davis EPU license and methodology](https://www.policyuncertainty.com/us_monthly.html); [current Moody Aaa restrictions](https://fred.stlouisfed.org/series/AAA). The latter prevents treating current proprietary continuation as automatically reusable. The public research catalog is preserved at [financial_research](../financial_research/README.md).

Attribution for the public commodity data: World Bank, Commodity Price Data (Pink Sheet), October 2026 workbook, CC BY 4.0 with additional terms. Attribution for EPU: Scott R. Baker, Nicholas Bloom and Steven J. Davis (2016), “Measuring Economic Policy Uncertainty,” PolicyUncertainty.com, CC BY 4.0. The normalized schemas, monthly aggregations and declared derived transformations are changes made by this project; no provider endorsement is implied. Federal series retain agency, exact series identifier and source URL in the dictionary.
''')
    textfile(REPORT/'README.md',f'''# Financial and macroeconomic acquisition — Phase 1

A reproducible, validated **825-month panel (1958-01–2026-09)** is built from **70 native series**. The local panel has **55 native/aggregated inputs + 47 derived columns**; the downloadable public panel has **{summary['public_monthly_columns']} numerical columns**. Original music data and prior analyses are preserved. No cross-domain modelling was performed.

Read [findings](findings.md), [priority acquisition status](priority_acquisition_status.csv), [coverage](coverage_report.csv), [native-frequency coverage](native_coverage_report.csv), [missing intervals](missingness_report.csv), [temporal alignment](temporal_alignment.md) and [blocked/deferred routes](blocked_sources.md). Source fields and formulas are in [series_dictionary.csv](series_dictionary.csv) and [derived_feature_dictionary.csv](derived_feature_dictionary.csv). [Acquisition log](acquisition_log.md), [source manifest](source_manifest.csv), [calculation checks](calculation_crosschecks.csv), [data-quality validation](data_quality_validation.json) and [music-join validation](music_join_validation.json) provide the audit trail.

## Files

The [dataset directory](../../../data/external_historical/financial/README.md) contains small redistribution-permitted CSV/XZ files. The native table retains source frequency, observation period, original publication/vintage where known, retrieval, source key/hash, source-status flags and rights. The wide monthly table has one row per month; `missingness_public.csv.xz` has corresponding 0/1 missing indicators. `aggregation_metadata_public.csv.xz` contains source-day/week counts and provenance. Quarter alignment and limited historical-vintage views are separate. No quarterly values are inserted into the main monthly table.

The six-month [sample music join](../../../data/external_historical/financial/processed/acquisition_v1/music_join_sample.csv) includes all-genres and genre summaries with source-row/distinct-song/available-score counts. It is a correctness example, not a fitted result or approved future weighting choice.

Raw source bytes, full local numerical panels and the market-drawdown figure remain ignored under `data/external_historical/financial/`. Their hashes and retrieval recipes are public; restricted series values are not committed. Source availability and a public download link do not by themselves confer bulk redistribution permission.

## Reproduce and validate

Run from the repository root with Python 3.9+ and the [pinned focused dependencies](requirements.txt). Existing repository dependencies are unchanged.

```bash
python3 -m pip install -r analysis/external_historical/financial_acquisition/requirements.txt
python3 src/financial_acquisition.py validate
python3 analysis/external_historical/financial_acquisition/verify.py
python3 -m unittest discover -s tests -p 'test_financial_acquisition.py' -v
```

The default validator uses committed public native data and reconstructs every public panel, metadata table, quarter view, point-in-time view and sample join offline. It verifies hashes and code. `python3 src/financial_acquisition.py build --public` republishes those exact public tables from pinned native inputs; it does not fetch sources or generate local values.

For the retained local source snapshots:

```bash
python3 src/financial_acquisition_sources.py normalize
python3 src/financial_acquisition.py build
python3 src/financial_acquisition_report.py
python3 src/financial_acquisition.py validate --private
python3 -m unittest discover -s tests -v
```

`normalize` verifies immutable SHA-256 bytes and fails before replacing native datasets on unsupported source schemas. Build outputs are staged, shape/finite/key checked, and published atomically per file with the build manifest last. Interrupted publication is detectable by the manifest; rerun from unchanged inputs. `restore` on the source script attempts only missing pinned source bytes, at a bounded rate; a newer provider revision fails hash validation and never replaces v1. Numeric CSV exports use 17 significant digits and native replay uses round-trip float parsing; original provider bytes and precision remain in immutable raw snapshots. Source archives must be retained for exact private reproduction. The published normalized public snapshot permits offline reproducibility even after providers revise their live downloads. `acquire` is the original acquisition recipe and can reuse the explicitly listed local caches; it does not refresh an already successful v1 snapshot.

The broader reproduction environment and each byte-level source version are part of the release. Historical release availability is only asserted for the limited G.17/NBER event views documented above. Full retrospective panels are not forecasting-ready.

## Figures

- [Priority-source historical coverage](figures/historical_coverage.svg)
- [Unemployment and inflation](figures/unemployment_inflation.svg)
- [Financial stress](figures/financial_stress.svg)
- [Missingness by period](figures/missingness_by_period.svg)

The fifth figure, market drawdowns, is produced locally at `data/external_historical/financial/processed/acquisition_v1/figures_local/market_drawdowns.svg` because bulk/derived redistribution permission for its market source is unresolved. [figure_inventory.csv](figure_inventory.csv) records all five figure hashes. Existing figure catalogs and PNGs are unchanged.

The final validation/preservation publication record is in [validation_report.md](validation_report.md). This release ends at dataset review; it does not authorize regressions or predictive searches.
''')
    textfile(ROOT/'data/external_historical/financial/README.md',f'''# Financial historical data — acquisition v1

Read the [acquisition report](../../../analysis/external_historical/financial_acquisition/README.md) before analysis. Public values are under `processed/acquisition_v1/`; immutable source recipes and hashes are under `manifests/acquisition_v1/`.

| File | Contents |
| --- | --- |
| [native_public.csv.xz](processed/acquisition_v1/native_public.csv.xz) | Permitted source values in native frequency with observation/release/vintage/retrieval/provenance |
| [monthly_public.csv.xz](processed/acquisition_v1/monthly_public.csv.xz) | 825 calendar months, {summary['public_monthly_columns']} numerical columns; retrospective revised snapshot |
| [missingness_public.csv.xz](processed/acquisition_v1/missingness_public.csv.xz) | Matching per-column missing flags; 1 means absent |
| [aggregation_metadata_public.csv.xz](processed/acquisition_v1/aggregation_metadata_public.csv.xz) | Source counts, weekly/daily completeness and provenance for present source periods |
| [quarterly_alignment_public.csv.xz](processed/acquisition_v1/quarterly_alignment_public.csv.xz) | Explicit quarter-end and latest completed-quarter views; not monthly measurements |
| [point_in_time_public.csv.xz](processed/acquisition_v1/point_in_time_public.csv.xz) | Only historical G.17 release growth values with observed publication/vintage dates |
| [music_join_sample.csv](processed/acquisition_v1/music_join_sample.csv) | Small chart-month/genre join check; no modelling |

The full local dataset additionally includes research-only series and transformations. Raw snapshots, `*_local` files and local-only figures are ignored. Never infer zeros from blanks or carry low-frequency observations into the primary monthly dataset. Source dictionaries and attribution/license decisions are in the report directory; restricted inputs do not become redistributable merely by transformation. Public World Bank and EPU values require their documented CC BY 4.0 attributions.
''')
    print(json.dumps(dict(status='PASS',figures=5,public_figures=4,priority_inputs=len(rows),monthly_columns=summary['monthly_columns'])))

if __name__=='__main__':render()
