"""Read-only source reconciliation and three private, versioned V4 analysis views."""
from __future__ import annotations
import json,re,sqlite3,time
from pathlib import Path
import numpy as np
import pandas as pd
import cross_domain_v4_common as c

# Exact source/formula crosswalk, not similarity-based merging. Every overlapping
# nonmissing value is independently checked before a single canonical column exists.
ALIASES={
'US_FINANCIAL_CP_3M':'US_AA_FINANCIAL_CP_3M','US_IP_GROWTH_INIT':'US_IP_TOTAL_GROWTH_INIT','US_IP_GROWTH_REV1':'US_IP_TOTAL_GROWTH_REV1',
'US_NBER_RECESSION_CLOSED_CYCLES':'US_NBER_DATED_RECESSION','US_NBER_ANNOUNCEMENT_EVENT':'US_NBER_LAST_ANNOUNCED_TURNING_POINT',
'US_MARKET_TOTAL_RETURN':'US_EQUITY_TOTAL_RETURN','US_MARKET_RETURN_3M':'US_EQUITY_RETURN_3M','US_MARKET_RETURN_12M':'US_EQUITY_RETURN_12M',
'US_MARKET_DRAWDOWN':'US_EQUITY_DRAWDOWN','US_MARKET_DAILY_COMPOUND_RETURN':'US_EQUITY_DAILY_RETURN','US_MARKET_DAILY_COUNT':'US_EQUITY_DAILY_OBSERVED_TRADING_DAYS',
'US_CPI_INFLATION_MOM':'US_CPI_MOM','US_CPI_INFLATION_YOY':'US_CPI_YOY','US_PCE_INFLATION_MOM':'US_PCE_PRICE_MOM','US_PCE_INFLATION_YOY':'US_PCE_PRICE_YOY',
'US_REAL_DISPOSABLE_INCOME_PC_GROWTH_YOY':'US_REAL_DISPOSABLE_INCOME_PC_YOY','US_IP_GROWTH_YOY':'US_IP_TOTAL_YOY',
'US_NONFARM_EMPLOYMENT_GROWTH_YOY':'US_NONFARM_EMPLOYMENT_YOY','US_SLOPE_10Y_3M':'US_YIELD_SLOPE_10Y_3M','US_SLOPE_10Y_2Y':'US_YIELD_SLOPE_10Y_2Y','US_BREAKEVEN_10Y':'US_TREASURY_TIPS_10Y_SPREAD'}
# Algebraic identities removed in every direction. Shared concepts alone remain.
IDENTITIES=[['sentiment_positive','sentiment_negative','sentiment_neutral'],
 ['US_EQUITY_TOTAL_RETURN','FF_MKT_EXCESS','FF_RF'],
 ['US_YIELD_SLOPE_10Y_2Y','US_TREASURY_10Y','US_TREASURY_2Y'],
 ['US_YIELD_SLOPE_10Y_3M','US_TREASURY_10Y','US_TREASURY_3M'],
 ['US_TREASURY_TIPS_10Y_SPREAD','US_TREASURY_10Y','US_TIPS_10Y'],
 ['US_CP_FINANCIAL_NONFINANCIAL_SPREAD','US_AA_FINANCIAL_CP_3M','US_AA_NONFINANCIAL_CP_3M'],
 ['US_CP_TBILL_DISCOUNT_SPREAD','US_AA_NONFINANCIAL_CP_3M','US_TBILL_3M_DISCOUNT'],
 ['US_BAA_AAA_SPREAD','US_CORPORATE_BAA','US_CORPORATE_AAA'],
 ['US_BAA_TREASURY_SPREAD','US_CORPORATE_BAA','US_TREASURY_10Y'],
 ['US_SLOPE_10Y_TBILL_DISCOUNT','US_TREASURY_10Y','US_TBILL_3M_DISCOUNT'],
 ['US_MISERY_INDEX','US_UNEMPLOYMENT','US_CPI_YOY'],
 ['US_MARKET_MONTHLY_DAILY_DIFFERENCE','US_EQUITY_TOTAL_RETURN','US_EQUITY_DAILY_RETURN'],
 ['US_REAL_HOURLY_EARNINGS','US_HOURLY_EARNINGS_PRODUCTION','US_CPI_SA'],
 ['US_REAL_HOURLY_EARNINGS_PRODUCTION','US_HOURLY_EARNINGS_PRODUCTION','US_CPI_NSA']]
INPUTS=['data/public/songs.csv','data/public/master_monthly.csv','data/public/master_weekly.csv.xz',
'data/public/music_enrichment_v2/songs.csv.xz','data/public/music_enrichment_v2/chart_period_features.csv.xz',
'data/public/music_enrichment_v2/manifest.json','data/public/external_historical_v1/manifest.json',
'data/external_historical/derived/all_observations.csv.xz',
'data/external_historical/financial/processed/acquisition_v1/monthly_local.csv.xz',
'data/external_historical/financial/processed/acquisition_v1/native_local.csv.xz',
'analysis/music_enrichment_v2/feature_dictionary.csv','analysis/music_enrichment_v2/construct_inventory.csv',
'analysis/feature_expansion_v1/feature_dictionary.csv','analysis/regression_cross_domain_v3/predictor_inventory.csv',
'analysis/external_historical/series_dictionary.csv','analysis/external_historical/derived_series_dictionary.csv',
'analysis/external_historical/financial_acquisition/series_dictionary.csv','analysis/external_historical/financial_acquisition/derived_feature_dictionary.csv',
'data/experiments/music_enrichment_v2/nlp/active.json']

def bool_value(v):return str(v).lower() in ['true','1']
def roots_for(r):
 text=(str(r.get('source',''))+' '+str(r.get('provider',''))+' '+str(r.get('source_url',''))).lower()
 for pattern,label in [('french','french_crsp'),('bls.gov','bls'),('bea.gov','bea'),('federalreserve','federal_reserve'),('mich','michigan'),('nber','nber'),('ucdp','ucdp'),('oxford','oxcgrt'),('oxcgrt','oxcgrt'),('worldbank','world_bank'),('noaa','noaa'),('chicago','chicago_fed'),('frbsf','sf_fed'),('dol.gov','us_dol'),('policyuncertainty','epu')]:
  if pattern in text:return [label]
 return ['provider:'+str(r.get('source') or r.get('provider') or r.get('source_key','unknown'))]
def domain_for(sid,r):
 if r.get('category'):return r['category']
 if sid.startswith('WB_') or any(x in sid for x in ['MARKET','TREASURY','TIPS','SLOPE','SPREAD','NFCI','ANFCI','BOND','FCI','CORPORATE','FED_FUNDS','PRIME','TBILL','BREAKEVEN']):return 'financial'
 if 'RECREATION' in sid:return 'cultural'
 return 'macroeconomic'
def transformation(sid,r):
 upper=sid.upper();unit=str(r.get('units','')).lower()
 if upper.startswith('FF_') or upper in {'US_NFCI','US_ANFCI','US_FCI_G','US_EXCESS_BOND_PREMIUM','US_ECONOMIC_NEWS_SENTIMENT','US_CONTIGUOUS_TEMPERATURE_ANOMALY'} or 'VOL' in upper or any(x in upper for x in ['RETURN','INFLATION','GROWTH','_MOM','_YOY','CHANGE','SLOPE','SPREAD','BREAKEVEN','TRAILING_Z','ANNOUNC','ELECTION','RECESSION','ONLINE_BEAR','REGIME']):return 'identity_rate_change_or_event'
 if any(x in upper for x in ['CPI_','PRICE_INDEX','INCOME','EARNINGS','WAGES','EMPLOYMENT','POPULATION','GDP','PCE_','RECREATION','WB_GOLD','WB_WTI','WB_COPPER','WB_WHEAT','WB_NATURAL','IP_TOTAL','IP_MANUFACTURING','IP_MINING','IP_UTILITIES']) and not any(x in upper for x in ['UNEMPLOYMENT','EMPLOYMENT_POPULATION','CHILD_','OLDER_','SHARE']):return 'log_growth_positive_endpoints'
 return 'first_difference_native_period'
def change_native(values,rule):
 if rule=='identity_rate_change_or_event':return values.copy()
 prior=values.shift(1)
 if rule=='log_growth_positive_endpoints':return 100*np.log(values.where(values>0)/prior.where(prior>0))
 return values-prior

def native_to_month(series,frequency,months):
 freq={'M':'M','Q':'Q-DEC','A':'Y-DEC'}[frequency]
 s=series.copy();s.index=pd.PeriodIndex(s.index,freq=freq)
 if s.index.duplicated().any():raise ValueError('Duplicate native economic period')
 grid=pd.period_range(s.index.min(),s.index.max(),freq=freq);s=s.reindex(grid)
 keys=months.asfreq(freq);result=pd.Series(s.reindex(keys).to_numpy(),index=months)
 ends=pd.Series([x.end_time.date().isoformat() for x in keys],index=months)
 return result,ends

def external():
 frame=pd.read_csv(c.ROOT/INPUTS[7],keep_default_na=False,low_memory=False);frame['value']=pd.to_numeric(frame.value.replace('',np.nan),errors='raise')
 if frame[['series_id','date','vintage_date']].duplicated().any():raise ValueError('Duplicate source observation key')
 dictionaries=pd.concat([pd.read_csv(c.ROOT/p,keep_default_na=False) for p in INPUTS[14:16]],ignore_index=True).fillna('').set_index('series_id').to_dict('index')
 # Explicitly versioned native table selection: each source series has a single
 # chosen measurement vintage; initial and revised G.17 are separate series.
 months=pd.period_range('1919-01','2026-09',freq='M');raw={};adjusted={};ends={};meta={};exclusions=[]
 for sid,g in frame.groupby('series_id',sort=True):
  r=dictionaries[sid];freq=r['frequency']
  if freq not in ['M','Q','A']:
   exclusions.append(dict(source='platform',variable=sid,reason='Daily observations retained as source; corresponding published monthly factors/explicit monthly aggregate represent this family in the three monthly-keyed populations'));continue
  s=pd.Series(g.value.to_numpy(),index=g.date);freqrule=transformation(sid,r)
  period=pd.PeriodIndex(s.index,freq={'M':'M','Q':'Q-DEC','A':'Y-DEC'}[freq]);s.index=period
  if s.index.duplicated().any():raise ValueError(sid)
  s=s.reindex(pd.period_range(s.index.min(),s.index.max(),freq=period.freq))
  raw[sid],ends[sid]=native_to_month(s,freq,months);adjusted[sid],_=native_to_month(change_native(s,freqrule),freq,months)
  parents=json.loads(r.get('parent_series') or '[]')
  meta[sid]=dict(name=sid,kind='numeric',source_columns=[sid],domain=domain_for(sid,r),family='external:'+sid,source=roots_for(r),dependencies=parents,
   frequency=freq,units=r['units'],definition=r.get('transformation') or r.get('name'),availability=r.get('availability_status','retrospective_snapshot'),
   public=bool_value(r['redistribution_permitted']),transformation=freqrule,origin='external',source_records=['platform:'+sid])
 finance=pd.read_csv(c.ROOT/INPUTS[8],float_precision='round_trip').set_index('month');finance.index=pd.PeriodIndex(finance.index,freq='M')
 native=pd.read_csv(c.ROOT/INPUTS[9],float_precision='round_trip',low_memory=False)
 fd=pd.read_csv(c.ROOT/INPUTS[16],keep_default_na=False).set_index('series_id').to_dict('index')
 dd=pd.read_csv(c.ROOT/INPUTS[17],keep_default_na=False).set_index('series_id').to_dict('index')
 crosswalk=[]
 for sid in sorted(set(finance)|set(native.loc[native.native_frequency.eq('Q'),'series_id'])):
  r=fd.get(sid,dd.get(sid));freq='M' if sid in finance else 'Q'
  if freq=='M':s=finance[sid].reindex(months)
  else:
   g=native.loc[native.series_id.eq(sid)];s=pd.Series(g.value.to_numpy(),index=pd.PeriodIndex(g.observation_date,freq='Q-DEC'))
   if s.index.duplicated().any():raise ValueError('Financial duplicate '+sid)
   s=s.reindex(pd.period_range(s.index.min(),s.index.max(),freq='Q-DEC'))
  candidate,period_end=native_to_month(s,freq,months)
  dest=ALIASES.get(sid,sid)
  if dest in raw:
   both=raw[dest].notna()&candidate.notna()
   if not np.allclose(raw[dest][both],candidate[both],rtol=1e-10,atol=1e-9):raise ValueError('Crosswalk not equivalent: '+sid+' -> '+dest)
   extra=int((raw[dest].isna()&candidate.notna()).sum())
   crosswalk.append(dict(financial_id=sid,canonical_id=dest,status='verified_alias',common_months=int(both.sum()),additional_months=extra,rule='Declared same source or formula; overlap equality verified; platform value preferred, explicit finance gap/warmup extension'))
   raw[dest]=raw[dest].combine_first(candidate);meta[dest]['source_records'].append('finance:'+sid)
   # Changes are computed once from the reconciled native value, except derived
   # growth/return identities which are already rates and must not be differenced.
   f=meta[dest]['frequency'];native_keys=months.asfreq({'M':'M','Q':'Q-DEC','A':'Y-DEC'}[f]);z=pd.Series(raw[dest].to_numpy(),index=native_keys).groupby(level=0).first()
   adjusted[dest],_=native_to_month(change_native(z,meta[dest]['transformation']),f,months)
   meta[dest]['public']=meta[dest]['public'] and bool_value(r['redistribution_permitted'])
  else:
   parents=[ALIASES.get(x,x) for x in r.get('input_series','').split(';') if x]
   rule=transformation(sid,r);raw[dest]=candidate;ends[dest]=period_end
   adjusted[dest],_=native_to_month(change_native(s,rule),freq,months)
   meta[dest]=dict(name=dest,kind='numeric',source_columns=[dest],domain=domain_for(sid,r),family='external:'+dest,source=roots_for(r),dependencies=parents,
    frequency=r.get('native_frequency',freq),view_frequency=freq,units=r['units'],definition=r.get('formula') or r.get('name'),
    availability='historical_release_vintage' if bool_value(r.get('point_in_time_eligible')) else 'retrospective_snapshot',public=bool_value(r['redistribution_permitted']),transformation=rule,origin='external',source_records=['finance:'+sid])
   crosswalk.append(dict(financial_id=sid,canonical_id=dest,status='distinct_definition',common_months=0,additional_months=int(candidate.notna().sum()),rule='Retained distinct source/formula; no name-only merge'))
 for r in meta.values():r['dependencies']=[ALIASES.get(x,x) for x in r['dependencies']]
 # Propagate provider provenance through derived variables, including finance
 # derived definitions whose dictionary contains only input series IDs.
 for _ in range(8):
  for r in meta.values():
   if r['dependencies']:
    providers=set(p for dep in r['dependencies'] if dep in meta for p in meta[dep]['source'])
    if providers:r['source']=sorted(providers)
 asof_path=c.ROOT/'data/external_historical/joins/asof_monthly_releases.csv.xz'
 asof=pd.read_csv(asof_path,keep_default_na=False);sid='US_NBER_LAST_ANNOUNCED_TURNING_POINT';g=asof.loc[asof.series_id.eq(sid)].copy()
 if len(g):
  vals=pd.to_numeric(g.value.replace('',np.nan),errors='raise');idx=pd.PeriodIndex(g.month,freq='M');raw[sid]=pd.Series(vals.to_numpy(),index=idx).reindex(months);adjusted[sid]=raw[sid].copy();ends[sid]=pd.Series(g.period_end.to_numpy(),index=idx).reindex(months)
  r=dictionaries[sid];meta[sid]=dict(name=sid,kind='numeric',source_columns=[sid],domain='macroeconomic',family='nber_announcement_event',source=['nber'],dependencies=[],frequency='event',units=r['units'],definition='Last actually announced NBER turning point before Billboard snapshot; not current recession state',availability='historical_release_vintage',public=False,transformation='identity_rate_change_or_event',origin='external',source_records=['platform:asof:'+sid])
 # Additional retained political tables are part of the inventory, without
 # inventing daily party control or an election-result publication vintage.
 congress=pd.read_csv(c.ROOT/'data/external_historical/political/congress_party_context.csv',keep_default_na=False)
 for field in ['house_majority_source','senate_majority_source','presidency_source','party_government_source']:
  sid='US_CONGRESS_'+field.upper();v=pd.Series(np.nan,index=months,dtype=object);e=pd.Series('',index=months)
  for row in congress.to_dict('records'):
   eligible=(months.end_time>=pd.Timestamp(row['period_start']))&(months.end_time<pd.Timestamp(row['period_end_exclusive']))
   v.loc[eligible]=re.sub(r'\([^)]*\)','',row[field]).strip();e.loc[eligible]=(pd.Timestamp(row['period_end_exclusive'])-pd.Timedelta(days=1)).date().isoformat()
  raw[sid]=v;adjusted[sid]=v.copy();ends[sid]=e;meta[sid]=dict(name=sid,kind='categorical',source_columns=[sid],domain='political',family='congress_term_context',source=['us_house_history'],dependencies=[],frequency='term',units='nominal source party summary',definition='Retrospective Congress-term source party label; parenthetical person names omitted; within-term mixed labels retained; not daily control',availability='retrospective_term_summary',public=True,transformation='categorical_identity',origin='external',source_records=['congress_party_context:'+field])
 elections=pd.read_csv(c.ROOT/'data/external_historical/political/presidential_election_results.csv',keep_default_na=False)
 for field in ['winner_electoral_votes','main_opponent_electoral_votes','total_electoral_votes']:
  sid='US_ELECTION_'+field.upper();idx=pd.PeriodIndex(elections.scheduled_election_date,freq='M');v=pd.Series(pd.to_numeric(elections[field]).to_numpy(),index=idx).reindex(months)
  raw[sid]=v;adjusted[sid]=v.copy();ends[sid]=pd.Series(months.end_time.strftime('%Y-%m-%d'),index=months);meta[sid]=dict(name=sid,kind='numeric',source_columns=[sid],domain='political',family='presidential_election_result',source=['nara'],dependencies=[],frequency='event',units='electoral votes',definition='Retrospectively certified result in election month only; other months missing, no holding or zero fill',availability='retrospective_certified_result',public=True,transformation='identity_rate_change_or_event',origin='external',source_records=['presidential_election_results:'+field])
 c.write_csv(c.PUBLIC/'series_crosswalk.csv',crosswalk);c.write_csv(c.PUBLIC/'source_exclusions.csv',exclusions)
 c.save_frame(c.LOCAL/'external_raw.pkl',pd.DataFrame(raw));c.save_frame(c.LOCAL/'external_adjusted.pkl',pd.DataFrame(adjusted));c.save_frame(c.LOCAL/'external_period_end.pkl',pd.DataFrame(ends))
 daily=frame.loc[frame.series_id.eq('FF_MKT_EXCESS_DAILY')&frame.value.notna()].copy();daily['month']=daily.date.str[:7]
 c.write_csv(c.PUBLIC/'daily_market_endpoints.csv',daily.groupby('month').agg(last_observed_trading_date=('date','max'),observed_days=('date','size')).reset_index())
 return meta,dict(platform_series=frame.series_id.nunique(),platform_rows=len(frame),canonical_external_series=len(meta),verified_aliases=sum(r['status']=='verified_alias' for r in crosswalk),release_original_dates_verified=0)

def music_meta(songs):
 new=pd.read_csv(c.ROOT/INPUTS[10],keep_default_na=False).set_index('feature').to_dict('index');old=pd.read_csv(c.ROOT/INPUTS[13],keep_default_na=False).set_index('name').to_dict('index')
 result={};excluded=[]
 keys={'song_id','title','artist','first_chart_date','last_chart_date','first_snapshot_month','last_snapshot_month','window_end_26','label_available_date'}
 for name in songs:
  if name in keys or name.endswith(('_ids','_isrc_set','_version','_retrieved_at','_processed_at','_review_flags')) or name in ['audio_recording_id','mb_release_title','mb_earliest_release_date','mb_release_date_precision','mb_v2_recording_first_release_candidate']:
   excluded.append(dict(variable=name,reason='Identity/date/provenance key; not an intrinsic numerical target or predictor'));continue
  series=songs[name].replace('',np.nan)
  if len(series.dropna()) and set(series.dropna().astype(str)) <= {'True','False'}:series=series.map({'True':1.,'False':0.,True:1.,False:0.})
  numeric=pd.to_numeric(series,errors='coerce')
  if int(series.notna().sum())==int(numeric.notna().sum()) and numeric.notna().any():kind='numeric';songs[name]=numeric
  elif name in ['primary_genre','secondary_genres','audio_key','audio_mode'] or name.endswith('_set') or name in ['title_version_marker']:
   kind='multilabel' if name.endswith('_set') or name=='secondary_genres' else 'categorical';songs[name]=series
  else:excluded.append(dict(variable=name,reason='Retrieval/status/quality text or unsupported empty field; no meaningful numerical/categorical measurement'));continue
  if name in old:
   d=old[name];family=d['family'];sources=json.loads(d['provenance']);availability=d['availability'];definition=d['definition']
  elif name in new:
   d=new[name];family=d['group'];sources=(['lyrics','modern_nlp'] if name.startswith('lyric_') else ['acousticbrainz','audio'] if name.startswith('audio_') else ['musicbrainz','billboard'] if name.startswith('artist_') else ['musicbrainz'] if name.startswith('mb_') else ['billboard']);availability=d['historical_availability'];definition=d['definition']
  else:
   family='commercial_performance' if name in ['best_chart_rank','weekly_observation_count','chart_weeks','total_chart_points','snapshot_months_selected'] else 'measurement_coverage';sources=['billboard'] if family=='commercial_performance' else ['acquisition'];availability='retrospective';definition='Preserved source field '+name
  domain='lyrical_content' if name.startswith(('ll_','detox_')) else 'lyrical_affect' if name.startswith(('emotion_','sentiment_')) else 'lyric_structure' if name.startswith('lyric_') else 'audio' if name.startswith('audio_') else 'genre' if 'genre' in name else 'artist_history' if name.startswith(('credit_','artist_','first_credited','credited_')) else 'metadata' if name.startswith(('mb_','duration')) else 'chart' if family!='measurement_coverage' else 'measurement_quality'
  result[name]=dict(name=name,kind=kind,source_columns=[name],domain=domain,family=family,source=sources,dependencies=[],frequency='song',units=new.get(name,{}).get('units','source units'),definition=definition,availability=availability,public=True,transformation='training_only_time_and_optional_genre_residual',origin='music')
 # Keep original circular coordinates together; component columns are not scalar targets.
 if {'debut_season_sin','debut_season_cos'}<=set(result):
  r=result.pop('debut_season_sin');result.pop('debut_season_cos');r.update(name='debut_season_phase',kind='block',source_columns=['debut_season_sin','debut_season_cos']);result[r['name']]=r
 c.write_csv(c.PUBLIC/'music_source_exclusions.csv',excluded)
 return result

def build():
 started=time.time();c.LOCAL.mkdir(parents=True,exist_ok=True);c.PUBLIC.mkdir(parents=True,exist_ok=True)
 paths=list(INPUTS)+['data/public/feature_expansion_v1/song_outcomes.csv.xz','data/external_historical/joins/asof_monthly_releases.csv.xz','data/external_historical/political/congress_party_context.csv','data/external_historical/political/presidential_election_results.csv'];active=c.read_json(c.ROOT/INPUTS[-1]);db=c.ROOT/'data/experiments/music_enrichment_v2/nlp'/active['key']/'results.db';paths.append(str(db.relative_to(c.ROOT)))
 c.write_json(c.PUBLIC/'input_manifest.json',{p:c.sha(c.ROOT/p) for p in paths})
 external_meta,summary=external()
 songs=pd.read_csv(c.ROOT/INPUTS[3],keep_default_na=False,low_memory=False);original=pd.read_csv(c.ROOT/INPUTS[0],dtype=str,keep_default_na=False)
 original_again=pd.read_csv(c.ROOT/INPUTS[3],dtype=str,keep_default_na=False)
 if not original.equals(original_again[original.columns]) or songs.song_id.duplicated().any():raise ValueError('Music identity or original columns changed')
 outcomes=pd.read_csv(c.ROOT/'data/public/feature_expansion_v1/song_outcomes.csv.xz',keep_default_na=False)
 outcome_aliases={'observed_lifetime_best_rank':'best_chart_rank','observed_lifetime_chart_weeks':'chart_weeks','observed_lifetime_chart_points':'total_chart_points'}
 comparison=songs.merge(outcomes[['song_id']+list(outcome_aliases)],on='song_id',validate='one_to_one')
 for a,b in outcome_aliases.items():np.testing.assert_allclose(pd.to_numeric(comparison[a]),pd.to_numeric(comparison[b]),rtol=0,atol=0)
 for h in [12,26]:
  valid=outcomes['eligible_'+str(h)].map(bool_value)
  for field in ['top10','long_chart','best_rank','chart_weeks','chart_points']:
   outcomes[field+'_'+str(h)]=pd.to_numeric(outcomes[field+'_'+str(h)]).where(valid)
 extra=['observed_return_after_26weeks']+[f'{field}_{h}' for h in [12,26] for field in ['top10','long_chart','best_rank','chart_weeks','chart_points']]
 songs=songs.merge(outcomes[['song_id','window_end_26']+extra],on='song_id',how='left',validate='one_to_one')
 songs['label_available_date']=pd.concat([songs.last_chart_date,songs.window_end_26],axis=1).max(axis=1)
 registry=music_meta(songs)
 # Vector coordinates are one private representation predictor, never 384 scalar discoveries.
 with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as conn:
  vectors={sid:np.frombuffer(blob,dtype='<f8').copy() for sid,blob in conn.execute('SELECT song_id,embedding FROM results WHERE embedding IS NOT NULL')}
 fields=[f'private_embedding_{i:03d}' for i in range(384)];array=np.full((len(songs),384),np.nan)
 for i,sid in enumerate(songs.song_id):
  if sid in vectors:
   if vectors[sid].shape!=(384,):raise ValueError('Unsupported embedding shape')
   array[i]=vectors[sid]
 songs=pd.concat([songs,pd.DataFrame(array,columns=fields)],axis=1)
 registry['lyric_semantic_embedding_private']=dict(name='lyric_semantic_embedding_private',kind='block',source_columns=fields,domain='lyric_semantics',family='embedding',source=['lyrics','minilm'],dependencies=[],frequency='song',units='normalized vector',definition='Existing complete private MiniLM 384-dimensional representation',availability='retrospective',public=False,transformation='training_only_time_residual',origin='music')
 songs['month']=songs.first_chart_date.str[:7];songs['row_id']=songs.song_id
 monthly=pd.read_csv(c.ROOT/INPUTS[1],usecols=['month','snapshot_chart_date','song_id','primary_genre','monthly_rank','source_chart_index','source_row_index'])
 if monthly[['source_chart_index','source_row_index']].duplicated().any():raise ValueError('Duplicate source chart location')
 chart=pd.read_csv(c.ROOT/INPUTS[4]);extra=[x for x in chart if x.startswith('chart_') and x!='chart_date']
 merged=monthly.merge(songs[['song_id']+[x for r in registry.values() if r['kind'] in ['numeric','block'] for x in r['source_columns']]],on='song_id',how='left',validate='many_to_one')
 merged=merged.merge(chart[['source_chart_index','source_row_index']+extra],on=['source_chart_index','source_row_index'],how='left',validate='one_to_one')
 assert len(merged)==81797
 numeric=list(dict.fromkeys([x for r in registry.values() if r['kind'] in ['numeric','block'] for x in r['source_columns']]+extra+['monthly_rank']))
 for field in extra+['monthly_rank']:
  registry[field]=dict(name=field,kind='numeric',source_columns=[field],domain='chart',family='chart_period',source=['billboard'],dependencies=[],frequency='chart',units='source units',definition='Current snapshot chart measurement '+field,availability='at_chart',public=True,transformation='training_only_time_residual',origin='music',song_unavailable=True)
 views={'song':songs}
 for pop,keys in [('monthly',['month']),('genre_month',['month','primary_genre'])]:
  g=merged.groupby(keys,sort=True,dropna=False);view=g[numeric].mean();counts=g[numeric].count().add_suffix('__available_n')
  view['source_row_count']=g.size();view['distinct_song_count']=g.song_id.nunique();view['snapshot_chart_date']=g.snapshot_chart_date.max();view=pd.concat([view,counts],axis=1).reset_index()
  view['row_id']=view['month'] if pop=='monthly' else view['month']+'::'+view.primary_genre
  views[pop]=view
 shares=pd.crosstab(monthly.month,monthly.primary_genre,normalize='index')
 for genre in shares:
  name='genre_share__'+genre
  views['monthly'][name]=views['monthly'].month.map(shares[genre]);registry[name]=dict(name=name,kind='numeric',source_columns=[name],domain='genre',family='genre_composition',source=['billboard','musicbrainz','wikidata','genre_model'],dependencies=[],frequency='M',units='share',definition='Retained source-row share of '+genre,availability='retrospective',public=True,transformation='training_only_time_residual',origin='music',monthly_only=True)
 for pop,view in views.items():
  if view.row_id.duplicated().any():raise ValueError('Duplicated analytical unit: '+pop)
  c.save_frame(c.LOCAL/(pop+'.pkl'),view)
  summary[pop]=dict(rows=len(view),months=view.month.nunique(),first_month=view.month.min(),last_month=view.month.max())
 summary.update(exact_study_songs=len(songs),original_columns_preserved=len(original.columns),source_song_month_rows=len(monthly),source_repeated_song_month_rows=int(monthly.duplicated(['month','song_id']).sum()),private_embeddings=len(vectors),seconds=time.time()-started)
 c.write_json(c.LOCAL/'music_registry.json',registry);c.write_json(c.LOCAL/'external_registry.json',external_meta)
 c.write_json(c.PUBLIC/'view_validation.json',dict(status='PASS',**summary))
 c.write_json(c.PUBLIC/'analysis_protocol.json',c.CONFIG)
 print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':build()
