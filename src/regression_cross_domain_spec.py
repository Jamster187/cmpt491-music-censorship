"""Complete V3 inventory, source-dependency policy and chronological populations."""
from __future__ import annotations
from collections import Counter
from functools import lru_cache
import copy
import itertools
import json
import math
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
import regression_expanded_spec as v2
import regression_spec as original
from feature_expansion_common import ROOT,sha,digest,clean,write_json,read_json,write_csv,atomic_bytes,SCORES

PUBLIC=ROOT/'analysis/regression_cross_domain_v3'
LOCAL=ROOT/'data/experiments/regression_cross_domain_v3'
SEED=4913003
FOLDS=v2.FOLDS
MB_EXTRA=['mb_duration_min_seconds','mb_duration_median_seconds','mb_duration_max_seconds','mb_recording_count','mb_release_count','mb_distinct_duration_count','mb_release_year']
COMMERCIAL=[f'{name}_{h}' for h in [12,26] for name in ['best_rank','chart_weeks','chart_points','top10','long_chart']]+['observed_lifetime_best_rank','observed_lifetime_chart_weeks','observed_lifetime_chart_points','observed_return_after_26weeks']
LIFETIME=[n for n in COMMERCIAL if n.startswith('observed_')]+['last_chart_date']
SENTIMENT=['sentiment_negative','sentiment_neutral','sentiment_positive']
DISTANCES=['lyric_content_distance_prior_hits','lyric_content_distance_recent_chart']
DURATIONS=['duration_seconds','mb_duration_min_seconds','mb_duration_median_seconds','mb_duration_max_seconds']
CALENDAR=['debut_time_years','debut_season_phase','christmas_proximity_days','chart_weekday']
RATIO_WORD_DEPENDENCIES=['lyric_mattr','lyric_mean_line_length','lyric_repeated_bigram_share','lyric_first_person_singular_share','lyric_second_person_share','lyric_first_person_plural_share','lyric_negation_token_share','lyric_temporal_deixis_share','lyric_title_phrase_repetition']
CATEGORIES={1:'A: direct reconstruction or target dependency',2:'B: same measurement family',3:'C: different families with conceptual overlap',4:'D: distinct domains with shared recorded provenance',5:'E: distinct domains and disjoint recorded measurement provenance'}
RULES={1:'self_target',2:'same_calendar_encoding_or_career_endpoint',4:'same_physical_duration_measurement',8:'same_commercial_measurement_across_windows_or_threshold',16:'focal_classifier_score_reused_in_content_distance',32:'explicit_scalar_reused_in_lyric_formula',64:'focal_genre_reused_in_genre_context',128:'career_endpoint_or_postwindow_presence_proxy',256:'sentiment_two_component_complement',512:'focal_chart_date_used_in_genre_annotation_input'}
VIEWS={'unrestricted_valid':2,'different_family_audit':3,'cross_domain':4,'provenance_separated':5}
CONFIG=dict(version='exhaustive-cross-domain-regression-v3',seed=SEED,parent_commit='23908fa31eec4454584d675d96bf391a3732c2b6',
    objective='Cross-domain variable prediction; not a commercial-forecast-only campaign',
    population='Existing V2 retrospective cohort: complete 42 scores and nonempty existing lyric structure; post-1960 debut; complete 26-week window; observed target only. Same target cohort across every configuration/view/candidate.',
    population_reason='Prevents absent content acquisition/final monthly-selection status from becoming a predictor of chart success; still a selected enriched cohort, not all entrants.',
    target_missingness='Never impute targets. All predictor combinations share the target-specific observed-label cohort.',
    support='At least 100 training and 30 validation identities and nonconstant target in all three validation folds; no evaluation-score screening',
    minimum_training=100,minimum_validation=30,
    folds=FOLDS,test_start='2018-01-01',burn_in_end='1960-01-01',
    final_refit='All eligible labels available before 2018; retrospective modern content/metadata remain explicitly retrospective',
    commercial_windows='Existing 12/26-week columns only; all populations use complete 26-week windows to equalize maximum fixed-window predictor availability',
    lifetime='Existing V2 prefix-at-cutoff definition; age >=5 calendar years and inactivity >=2 years. Other rows have missing lifetime predictors; lifetime targets require observed eligible labels. Not verified completed careers.',
    binary_targets='Existing meaningful 0/1 indicators retained; OLS is an unclipped linear-probability diagnostic, not calibrated classification. Top10 outcomes exclude already Top10 debuts, as in V1.',
    new_features='None created; reuse all 57 existing constructs, V2 debut/date encodings, and the original campaign release-year/last-date encodings',
    registry='All original raw MB duration summaries retained with distinct populations and uncertainty; their relationships to each other/consistent duration are A, not independent measurements. Catalog counts measure retained linked catalog coverage, not artist merit.',
    relationship_precedence='Worst pair category determines combination; any compound reconstruction overrides to A. Mixed same-family/cross-domain models remain B.',
    categories=CATEGORIES,exclusion_rules=RULES,views=VIEWS,
    cross_domain='D/E only: all predictors in different substantive families and no prespecified conceptual-overlap proxy. The broader C/D/E different-family audit is also retained.',
    provenance='E requires disjoint recorded measurement-source sets and no overlap/dependency rule. Common identity joins and selection are not proof of statistical independence. Unknown pretrained knowledge remains a limitation.',
    genre_provenance='Frozen genre prompt uses Billboard identity and first chart date, MB/Wikidata tags and learned genre knowledge; explicitly forbids lyrics/content scores/chart performance. Genre is not provenance-separated from Billboard or MB.',
    estimator='Additive OLS with intercept, all unordered 1/2/3-variable combinations, no screening, no interactions/regularization/clipping',
    preprocessing='Training medians, numeric/dummy standardization, observed training categorical/multilabel vocabulary; constant encoded columns removed but conceptual candidates retained; no missingness flags; unseen categories raw all zero',
    counts='One categorical/multilabel variable; season sine/cosine jointly one construct, not two targets',
    selection='Equal-period mean validation R2; then fewer original variables; then lexicographic tuple. Baseline MSE skill is reported separately. All selections locked before any evaluation.',
    leaderboard='Top relationships ranked by validation R2 only; preserve global top combinations and one-winner-per-target views separately. No evaluation performance used to select figures or winners.',
    configurations=['original','new','combined','classifier_only'],bootstrap_repeats=499,
    uncertainty='Paired fixed-prediction bootstrap by exact artist credit and debut year; excludes refitting/search uncertainty. Artist aliases and collaboration overlap remain.',
    prior_test_inspected=True,independent_confirmation=False,
    batch_size=256,checkpoint_rows=8192,blas_threads=1,
    runtime_limit_seconds=4*3600,temporary_storage_limit_bytes=15_000_000_000,minimum_disk_headroom_bytes=2*1024**3,
    storage='Float64 dense disk arrays for all period MAE/MSE; uint16 rank/fallback, global candidate catalog, full relationship audit, validation order. Metrics derived losslessly from fold constants. No duplicate giant CSV or millions of fitted models.',
    external_acquisition=False,new_feature_engineering=False,new_classification=False)


def registry():
    result=copy.deepcopy(v2.REGISTRY);result.pop('genre_confidence')
    for n in MB_EXTRA:
        definition=('First four characters of retained earliest matched release date; existing original-campaign encoding; NOT verified original release year' if n=='mb_release_year' else
                    'Summary of retained positive recording lengths; different manifestations can disagree' if n.startswith('mb_duration_') else 'Count of retained linked catalog entities/durations; capped and incomplete provider coverage, not total true versions')
        result[n]=dict(name=n,source_columns=[n],origin='original',family='recording_metadata',availability='F',kind='numeric',definition=definition)
    for n in COMMERCIAL:
        definition=('Any observed chart appearance at or after debut +182 days; does not require an absence/re-entry' if n=='observed_return_after_26weeks' else
                    'Existing observed chart-history '+n if n.startswith('observed_') else 'Existing fixed-window '+n+'; rank=min, weeks=distinct dates, points=sum(101-rank), Top10=min<=10, long_chart=weeks>=ceil(horizon/2)')
        result[n]=dict(name=n,source_columns=[n],origin='original',family='commercial_performance',availability='P',kind='numeric',definition=definition)
    result['last_chart_date']=dict(name='last_chart_date',source_columns=['last_chart_date'],origin='original',family='historical_time',availability='P',kind='numeric',definition='Existing original-campaign days-since-1970 encoding of last observed chart date; recomputed from each cutoff prefix, mature/inactive mask')
    for n,r in result.items():
        old=r['family'];r['engineering_family']=old
        if n.startswith(('ll_','detox_')):family='lyrical_content';sources=['lyrics'];model='lyriclens' if n.startswith('ll_') else 'detoxify';sources.append(model)
        elif n.startswith(('emotion_','sentiment_')):family='lyrical_affect';sources=['lyrics','goemotions' if n.startswith('emotion_') else 'sentiment_model']
        elif n in DISTANCES:family='content_reference';sources=['lyrics','billboard','lyriclens','detoxify','goemotions','sentiment_model']
        elif old=='lyric_structure':family='lyric_structure';sources=['lyrics']+(['billboard'] if n=='lyric_title_phrase_repetition' else [])
        elif n in DURATIONS:family='recording_duration';sources=['musicbrainz']
        elif n=='mb_release_year':family='release_calendar';sources=['musicbrainz']
        elif n.startswith('mb_'):family='catalog_coverage';sources=['musicbrainz']
        elif n=='credited_artist_entity_count':family='collaboration_entities';sources=['musicbrainz']
        elif old=='entity_credit':family='entity_history';sources=['billboard','musicbrainz']
        elif old=='relative_content':family='artist_genre_history' if n=='credit_prior_genre_diversity' else 'genre_context';sources=['billboard','musicbrainz','wikidata','genre_model']
        elif n in ['primary_genre','secondary_genres']:family='genre_annotation';sources=['billboard','musicbrainz','wikidata','genre_model']
        elif n in CALENDAR or n=='last_chart_date':family='calendar';sources=['billboard']
        elif n=='artist_credit_feature_marker':family='credit_syntax';sources=['billboard']
        elif n=='song_title_prior_usage_count':family='title_history';sources=['billboard']
        elif n.startswith('song_title_'):family='title_form';sources=['billboard']
        elif old=='artist_history':family='artist_chart_history';sources=['billboard']
        elif old=='chart_competition':family='chart_context';sources=['billboard']
        elif n in COMMERCIAL:family='commercial_performance';sources=['billboard']
        elif n.startswith('debut_'):family='debut_chart';sources=['billboard']
        else:raise ValueError('Unclassified variable '+n)
        r.update(family=family,provenance=sorted(sources),meaningful_numerical=r['kind']=='numeric',
                 target_encoding_caveat='Existing calendar/categorical/circular encoding; not a scalar numerical target' if r['kind']!='numeric' else '')
    return dict(sorted(result.items()))

REGISTRY=registry()
NAMES=list(REGISTRY)


def commercial_measure(name):
    if name not in COMMERCIAL:return None
    if 'best_rank' in name or 'top10' in name:return 'peak_attainment'
    if 'chart_weeks' in name or 'long_chart' in name:return 'chart_duration'
    if 'chart_points' in name:return 'chart_points'
    return 'postwindow_presence'


def pair(target,predictor):
    a,b=REGISTRY[target],REGISTRY[predictor];names={target,predictor};reason=0
    if target==predictor:reason|=1
    if names<=set(CALENDAR) or names=={'last_chart_date','debut_time_years'}:reason|=2
    if names<=set(DURATIONS):reason|=4
    m1,m2=commercial_measure(target),commercial_measure(predictor)
    if m1 is not None and m1==m2:reason|=8
    if (target in DISTANCES and predictor in SCORES) or (predictor in DISTANCES and target in SCORES):reason|=16
    if 'lyric_word_count' in names and len(names&set(RATIO_WORD_DEPENDENCIES)) or names=={'lyric_vocabulary_size','lyric_hapax_share'}:reason|=32
    if names&{'primary_genre'} and names&{'prior_year_primary_genre_share','debut_chart_same_genre_share'}:reason|=64
    if 'last_chart_date' in names and names&set(COMMERCIAL):reason|=128
    if 'debut_time_years' in names and names&{'primary_genre','secondary_genres','prior_year_primary_genre_share','debut_chart_same_genre_share'}:reason|=512
    if reason:return 1,reason,'Explicit reconstruction/target-dependency rule; retained in audit only'
    if a['family']==b['family']:return 2,0,'Same substantive measurement family'
    fa,fb=a['family'],b['family'];fs={fa,fb}
    lyric={'lyrical_content','lyrical_affect','lyric_structure','content_reference'}
    overlap=(fa in lyric and fb in lyric or fs<={'calendar','release_calendar'} or
             bool(fs&{'title_form','title_history'}) and bool(fs&lyric) or
             fs=={'credit_syntax','collaboration_entities'} or
             bool(names&set(DURATIONS)) and bool(names&{'lyric_word_count','lyric_vocabulary_size'}) or
             fs<={'debut_chart','commercial_performance'} or
             fa in {'artist_chart_history','entity_history','artist_genre_history'} and fb in {'artist_chart_history','entity_history','artist_genre_history'} or
             fa in {'genre_annotation','genre_context','artist_genre_history'} and fb in {'genre_annotation','genre_context','artist_genre_history'})
    if overlap:return 3,0,'Different families but prespecified shared construct/obvious proxy'
    shared=set(a['provenance'])&set(b['provenance'])
    if shared:return 4,0,'Distinct domains with shared recorded sources: '+','.join(sorted(shared))
    return 5,0,'Distinct substantive domains and disjoint recorded measurement sources; common selection/identity and unrecorded learned priors remain'


@lru_cache(maxsize=1)
def catalog():
    values=[]
    for k in [1,2,3]:values.extend((*c,*([255]*(3-k))) for c in itertools.combinations(range(len(NAMES)),k))
    return np.asarray(values,dtype=np.uint8)


def relations(target):
    pairs=[pair(target,n) for n in NAMES];cat=np.asarray([p[0] for p in pairs]+[5]*(256-len(NAMES)),np.uint8)
    reason=np.asarray([p[1] for p in pairs]+[0]*(256-len(NAMES)),np.uint16)
    c=catalog();categories=cat[c].min(axis=1);bits=np.bitwise_or.reduce(reason[c],axis=1)
    if target in SENTIMENT:
        others=[NAMES.index(n) for n in SENTIMENT if n!=target];invalid=(c==others[0]).any(axis=1)&(c==others[1]).any(axis=1)
        categories[invalid]=1;bits[invalid]|=256
    return categories,bits


def origin_masks():
    lookup=np.zeros(256,np.uint8)
    for i,n in enumerate(NAMES):lookup[i]=1 if REGISTRY[n]['origin']=='original' else 2
    return np.bitwise_or.reduce(lookup[catalog()],axis=1)


def configuration_filter(configuration):
    if configuration=='combined':return np.ones(len(catalog()),bool)
    if configuration=='classifier_only':
        lookup=np.asarray([n in SCORES for n in NAMES]+[True]*(256-len(NAMES)),bool)
        return lookup[catalog()].all(axis=1)
    if configuration in ['original','new']:return origin_masks()==(1 if configuration=='original' else 2)
    raise ValueError('Unknown configuration')


def combo(candidate_id):return tuple(NAMES[i] for i in catalog()[candidate_id] if i!=255)


@lru_cache(maxsize=1)
def source_frame():
    f=v2.population('retrospective').copy()
    raw=pd.read_csv(ROOT/'data/public/songs.csv',keep_default_na=False,na_values=[''])
    converted=original.original.convert(raw)
    f=f.merge(converted[['song_id']+MB_EXTRA],on='song_id',how='left',validate='one_to_one')
    exact=pd.read_csv(v2.DATA/'song_features.csv.xz',usecols=['song_id','title','artist'],keep_default_na=False,na_values=['']).set_index('song_id')
    for name in ['title','artist']:f[name]=f.song_id.map(exact[name])
    if f.song_id.duplicated().any() or f.artist.isna().any():raise ValueError('Invalid exact identity population')
    return f.sort_values('song_id').reset_index(drop=True)


@lru_cache(maxsize=5)
def asof(cutoff):
    f=source_frame();f=f[f.eligible_26.astype(bool)&f.window_end_26.le(cutoff)].copy()
    labels=v2.labels_at(cutoff).set_index('song_id');eligible=labels.mature&labels.inactive;labels=labels[eligible]
    for target in ['best_rank','chart_weeks','chart_points']:f['observed_lifetime_'+target]=f.song_id.map(labels[target])
    late=pd.to_datetime(labels.last_observed).ge(pd.to_datetime(labels.first_observed)+pd.Timedelta(days=182)).astype(float)
    f['observed_return_after_26weeks']=f.song_id.map(late)
    f['last_chart_date']=f.song_id.map((pd.to_datetime(labels.last_observed)-pd.Timestamp('1970-01-01')).dt.days.astype(float))
    return f


def partition(target,start,end):
    train=asof(start);valid=asof(end or v2.end_date());valid=valid[valid.first_chart_date.ge(start)]
    train=train[train[target].notna()].copy();valid=valid[valid[target].notna()].copy()
    if target.startswith('top10_'):
        train=train[train.debut_rank.gt(10)];valid=valid[valid.debut_rank.gt(10)]
    for f in [train,valid]:
        f['outcome']=f[target].to_numpy(float)
        if not np.isfinite(f.outcome).all():raise ValueError('Nonfinite target '+target)
    if set(train.song_id)&set(valid.song_id):raise ValueError('Song identity crosses partitions')
    return train.reset_index(drop=True),valid.reset_index(drop=True)


def targets():
    inventory=pd.read_csv(PUBLIC/'target_inventory.csv')
    return inventory.loc[inventory.status.eq('eligible'),'name'].tolist()


def freeze():
    inputs={name:sha(ROOT/name) for name in ['data/public/songs.csv','data/public/master_weekly.csv.xz','data/public/feature_expansion_v1/song_features.csv.xz','data/public/feature_expansion_v1/song_outcomes.csv.xz','analysis/feature_expansion_v1/feature_dictionary.csv','docs/genre/llm/prompt.txt']}
    record=dict(configuration=CONFIG,registry=REGISTRY,input_sha256=inputs,environment=v2.environment())
    p=PUBLIC/'protocol.json'
    if p.exists() and read_json(p)!=clean(record):raise ValueError('Frozen V3 specification/input/environment changed')
    if not p.exists():write_json(p,record)
    return digest(record)


def provenance():
    files=[p for p in (ROOT/'src').glob('regression_cross_domain*.py') if not p.name.endswith(('_report.py','_validate.py'))]
    files+=[ROOT/n for n in ['src/regression_core.py','src/regression_expanded_core.py','src/regression_expanded_spec.py','src/regression_spec.py','analysis/planning/regression_search/audit.py','src/feature_expansion_common.py','src/feature_expansion_features.py','src/genre_llm.py','docs/genre/llm/prompt.txt']]
    return dict(protocol_sha256=freeze(),code_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},environment=v2.environment())


def preservation(initialize=False):
    p=LOCAL/'preservation.json'
    if not p.exists():
        if not initialize:raise ValueError('Missing V3 preservation snapshot')
        names=set(subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines())
        for base in [ROOT/'data',ROOT/'analysis']:
            for x in base.rglob('*'):
                if x.is_file() and '__pycache__' not in x.parts and not any(b==x or b in x.parents for b in [PUBLIC,LOCAL]):names.add(str(x.relative_to(ROOT)))
        files={name:dict(bytes=(ROOT/name).stat().st_size,sha256=sha(ROOT/name)) for name in sorted(names) if (ROOT/name).is_file() and not any(b==ROOT/name or b in (ROOT/name).parents for b in [PUBLIC,LOCAL])}
        write_json(p,dict(baseline_commit=CONFIG['parent_commit'],files=files));return dict(status='SNAPSHOT_CREATED',files=len(files),bytes=sum(r['bytes'] for r in files.values()))
    record=read_json(p)
    for name,expected in record['files'].items():
        x=ROOT/name
        if not x.is_file() or x.stat().st_size!=expected['bytes'] or sha(x)!=expected['sha256']:raise ValueError('Protected prior artifact changed: '+name)
    return dict(status='PASS',files=len(record['files']),bytes=sum(r['bytes'] for r in record['files'].values()),baseline_commit=record['baseline_commit'])


def source_inventory():
    rows=[]
    aliases={'first_chart_date':'debut_time_years','observed_last_chart_date':'last_chart_date','best_chart_rank':'observed_lifetime_best_rank','chart_weeks':'observed_lifetime_chart_weeks','total_chart_points':'observed_lifetime_chart_points','mb_earliest_release_date':'mb_release_year','debut_season_sin':'debut_season_phase','debut_season_cos':'debut_season_phase','reported_last_week_rank':'debut_reported_last_week_rank','reported_peak_position':'debut_reported_peak_position','reported_weeks_on_chart':'debut_reported_weeks_on_chart','weekly_rank':'debut_rank','chart_date':'debut_time_years'}
    for path in [ROOT/'data/public/songs.csv',ROOT/'data/public/master_weekly.csv.xz',v2.DATA/'song_features.csv.xz',v2.DATA/'song_outcomes.csv.xz']:
        for name in pd.read_csv(path,nrows=0).columns:
            canonical=aliases.get(name,name)
            if canonical in REGISTRY:status='eligible_or_canonical_alias';reason='Existing construct/encoding; target support audited separately; chart aliases use cutoff-specific canonical values'
            elif name in ['song_id','title','artist','source_chart_index','source_row_index','mb_release_title']:status='excluded';reason='Identifier, source coordinate or high-cardinality asset text'
            elif name in ['first_snapshot_month','last_snapshot_month','snapshot_months_selected','weekly_observation_count']:status='excluded';reason='Monthly selection bookkeeping or redundant source-row count; canonical distinct chart dates retained'
            elif name=='genre_confidence':status='excluded';reason='Annotation-process confidence, not a substantive musical variable; unlike V2 this discovery universe excludes bookkeeping'
            else:status='excluded';reason='Availability, matching/status, censoring or window-eligibility bookkeeping; no numerical category codes as targets'
            rows.append(dict(source=str(path.relative_to(ROOT)),column=name,canonical=canonical if canonical in REGISTRY else '',status=status,reason=reason))
    return rows


def audit():
    freeze();LOCAL.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
    write_csv(PUBLIC/'predictor_inventory.csv',list(REGISTRY.values()));write_csv(PUBLIC/'source_column_inventory.csv',source_inventory())
    pair_rows=[];inventory=[];cohorts=[];spaces=[];k=np.sum(catalog()!=255,axis=1);origin=origin_masks()
    for name,r in REGISTRY.items():
        row=dict(r);row['status']='excluded_encoding';row['reason']=r['target_encoding_caveat']
        if r['meaningful_numerical']:
            failures=[]
            for fold,(start,end) in enumerate(FOLDS+[('2018-01-01',None)]):
                tr,va=partition(name,start,end)
                cohorts.append(dict(target=name,fold=fold,start=start,end=end or v2.end_date(),n_train=len(tr),n_validation=len(va),train_ids_sha256=digest(tr.song_id.tolist()),validation_ids_sha256=digest(va.song_id.tolist())))
                if fold<3:
                    if len(tr)<CONFIG['minimum_training'] or len(va)<CONFIG['minimum_validation']:failures.append(f'fold{fold}:insufficient_observed_support({len(tr)},{len(va)})')
                    elif tr.outcome.nunique()<2 or va.outcome.nunique()<2:failures.append(f'fold{fold}:constant_training_or_validation_target')
            row['status']='unsupported' if failures else 'eligible';row['reason']=';'.join(failures) if failures else 'Meaningful observed numerical target; all prespecified training/validation support conditions met'
            categories,bits=relations(name)
            for predictor in NAMES:
                cat,reason,explanation=pair(name,predictor);pair_rows.append(dict(target=name,predictor=predictor,category=CATEGORIES[cat],category_code=cat,rule_bits=reason,reason=explanation,target_family=r['family'],predictor_family=REGISTRY[predictor]['family'],shared_provenance=sorted(set(r['provenance'])&set(REGISTRY[predictor]['provenance']))))
            for view,minimum in VIEWS.items():
                for configuration in CONFIG['configurations']:
                    eligible=(categories>=minimum)&configuration_filter(configuration)
                    counts={f'k{i}':int((eligible&(k==i)).sum()) for i in [1,2,3]}
                    spaces.append(dict(target=name,status=row['status'],view=view,configuration=configuration,pair_eligible_predictors=sum(pair(name,p)[0]>=minimum and (configuration=='combined' or configuration=='classifier_only' and p in SCORES or REGISTRY[p]['origin']==configuration) for p in NAMES),**counts,total=sum(counts.values()),audit_universe=len(catalog()),A_excluded=int((categories==1).sum())))
        inventory.append(row)
    write_csv(PUBLIC/'target_inventory.csv',inventory);write_csv(PUBLIC/'relationship_pairs.csv',pair_rows);write_csv(PUBLIC/'cohorts.csv',cohorts);write_csv(PUBLIC/'search_space.csv',spaces)
    eligible=[r['name'] for r in inventory if r['status']=='eligible'];count=sum(r['total'] for r in spaces if r['status']=='eligible' and r['view']=='unrestricted_valid' and r['configuration']=='combined')
    summary=dict(status='AUDITED_NOT_EXECUTED',predictors=len(NAMES),new_constructs=sum(r['origin']=='new' for r in REGISTRY.values()),meaningful_numerical_targets=sum(r['meaningful_numerical'] for r in REGISTRY.values()),eligible_targets=len(eligible),unsupported_targets=[dict(name=r['name'],reason=r['reason']) for r in inventory if r['status']=='unsupported'],audit_combinations_per_target=len(catalog()),valid_task_candidate_pairs=count,validation_fits=3*count,evaluation_fits=count,total_fits=4*count,
        minimum_numeric_store_bytes=count*72,source_identities=len(v2.source_frame()),enriched_post_burnin_identities=len(source_frame()),benchmark_required=True,full_search_started=False)
    write_json(PUBLIC/'audit.json',summary);print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['audit','preserve','verify-preservation']);a=p.parse_args()
    if a.action=='audit':audit()
    else:print(json.dumps(preservation(a.action=='preserve'),indent=2),flush=True)
