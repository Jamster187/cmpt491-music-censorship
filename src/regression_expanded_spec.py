"""Frozen predictor inventory, as-of outcome cohorts and preservation for OLS v2."""
from __future__ import annotations
from collections import Counter
from functools import lru_cache
import itertools
import json
import math
from pathlib import Path
import platform
import sqlite3
import subprocess
import time

import numpy as np
import pandas as pd
import scipy

from feature_expansion_common import ROOT,sha,digest,clean,write_json,read_json,write_csv,atomic_bytes,SCORES

PUBLIC=ROOT/'analysis/regression_expanded_v2'
LOCAL=ROOT/'data/experiments/regression_expanded_v2'
V1=ROOT/'analysis/feature_expansion_v1'
DATA=ROOT/'data/public/feature_expansion_v1'
SEED=4912026
FOLDS=[('1990-01-01','2000-01-01'),('2000-01-01','2010-01-01'),('2010-01-01','2018-01-01')]
TARGETS=['best_rank','chart_weeks','chart_points']
CONFIG=dict(version='exhaustive-regression-expanded-v2',seed=SEED,prediction_moment='After publication of first observed chart for exact original title/full artist credit',
    tracks=['strict','retrospective'],retrospective_authorization='User explicitly requested strict campaign plus retrospective sensitivity',
    horizon_26='[debut, debut + 182 days); global source endpoint must reach exclusive window end; V1 definitions unchanged',
    observed_lifetime='Observed chart history strictly before each label cutoff; not true completed careers',
    lifetime_maturity_years=5,lifetime_inactivity_years=2,lifetime_caution='Eligibility is a selected mature/inactive cohort; unobserved future returns remain possible. Historical eligibility never uses events after that cutoff.',
    burn_in_end='1960-01-01',folds=FOLDS,test_start='2018-01-01',
    final_refit='All eligible labels available strictly before 2018; fixed-horizon labels require window end <=2018. Lifetime labels rebuilt as of 2018.',
    matched_v1_refit='Selected 26-week winners also refit on the exact V1 pre-2010 training cohort for an identical-training comparison',
    candidate_counts=[1,2,3],estimator='Additive OLS with intercept; no interactions or regularization',
    variable_count='One original construct per variable; season sine/cosine together; categorical or multilabel blocks count as one',
    selection='Equal-period mean training-mean-relative MSE skill over three rolling validation folds; then fewer original variables; then lexicographic predictor tuple',
    cohorts='One exact identity per row; fixed cohort per track/target/fold, shared by every predictor combination',
    preprocessing='Training-only median imputation without missing flags; numeric standardization; training-observed categories and multilabel vocabulary; remove constant encoded columns but retain their conceptual combinations',
    unknown_categories='All-zero categorical block; unsupported rows reported',
    no_screening=True,retain_rank_deficient=True,
    overlap_flags='Descriptive flags only; overlapping eligible predictors remain enumerated. No current-song future outcomes are predictors.',
    final_test='All validation winners and rankings locked before evaluating any candidate on the 2018+ population; every eligible candidate then receives evaluation metrics',
    prior_test_inspected=True,independent_confirmation=False,bootstrap_repeats=499,
    uncertainty='Paired fixed-prediction resampling by exact full artist credit and debut year; excludes model-selection/refit uncertainty',
    batch_size=256,blas_threads=1,full_launch_budget_seconds=7200,minimum_disk_headroom_bytes=3*1024**3,
    source='Supplied Billboard snapshot, reported upstream mhollingshead/billboard-hot-100; no independent verification',
    external_acquisition=False,new_content_inference=False)


def environment():
    return dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,sqlite=sqlite3.sqlite_version,platform=platform.platform())


def registry():
    definitions=pd.read_csv(V1/'feature_dictionary.csv').fillna('');rows=[]
    for r in definitions.to_dict('records'):
        if r['feature']=='debut_season_cos':continue
        name='debut_season_phase' if r['feature']=='debut_season_sin' else r['feature']
        fields=['debut_season_sin','debut_season_cos'] if name=='debut_season_phase' else [name]
        rows.append(dict(name=name,source_columns=fields,origin='new',family=r['group'],availability=r['historical_availability'],
            kind='categorical' if name=='chart_weekday' else 'numeric_block' if len(fields)>1 else 'numeric',
            definition='Joint circular phase; both frozen sine/cosine components form ONE variable' if len(fields)>1 else r['definition']))
    originals=[
        ('debut_rank','debut_chart','C','numeric','Minimum rank on published first chart'),
        ('debut_time_years','historical_time','C','numeric','Source first-chart date as days since 1970-01-01 / 365.2425; deterministic known-date representation'),
        ('debut_reported_last_week_rank','debut_chart','C','numeric','Minimum nonmissing source-reported last-week rank on first observed chart; does not merge identities'),
        ('debut_reported_peak_position','debut_chart','C','numeric','Minimum source-reported peak on first observed chart; known then, distinct from a future attained peak'),
        ('debut_reported_weeks_on_chart','debut_chart','C','numeric','Maximum source-reported weeks on first observed chart; source identity/history anomalies retained'),
        ('primary_genre','genre_information','F','categorical','Existing modern primary genre label'),
        ('secondary_genres','genre_information','F','multilabel','Existing modern secondary genre label set, one original variable'),
        ('genre_confidence','genre_information','F','categorical','Existing modern genre annotation confidence; measurement-process proxy, not intrinsic certainty'),
        ('duration_seconds','recording_metadata','F','numeric','V1 accepted consistent duration; all retained durations agree; other duration summaries are aliases on this mask')]
    for name,family,available,kind,definition in originals:
        rows.append(dict(name=name,source_columns=[name],origin='original',family=family,availability=available,kind=kind,definition=definition))
    for name in SCORES:rows.append(dict(name=name,source_columns=[name],origin='original',family='lyrical_scores',availability='F',kind='numeric',definition='Existing frozen '+name+' content-classifier score'))
    return {r['name']:r for r in sorted(rows,key=lambda r:r['name'])}


REGISTRY=registry()


def predictors(track,configuration='combined'):
    return [name for name,r in REGISTRY.items() if (track=='retrospective' or r['availability']=='C') and (configuration=='combined' or r['origin']==('original' if configuration=='original' else 'new'))]


def candidates(track):
    names=predictors(track)
    return [(i,c) for i,c in enumerate(itertools.chain.from_iterable(itertools.combinations(names,k) for k in [1,2,3]))]


def configuration_mask(combo):
    return sum(bit for origin,bit in [('original',1),('new',2)] if any(REGISTRY[n]['origin']==origin for n in combo))


def overlap_flags(combo):
    names=set(combo);families=Counter(REGISTRY[n]['family'] for n in combo);flags=[]
    if max(families.values())>1:flags.append('same_family')
    if len(names&{'debut_rank','debut_reported_peak_position'})>1:flags.append('near_duplicate_debut_rank_report')
    if len(names&{'credit_prior_song_count','credit_prior_chart_weeks','credit_prior_chart_points','credit_chart_career_days'})>1:flags.append('overlapping_history_volume')
    if len(names&{'lyric_word_count','lyric_vocabulary_size','lyric_mean_line_length'})>1:flags.append('overlapping_lyric_length')
    if sum(n.startswith('sentiment_') for n in combo)>1:flags.append('sentiment_simplex')
    if len(names&{'primary_genre','secondary_genres','genre_confidence'})>1:flags.append('overlapping_genre_annotation')
    return ';'.join(flags)


def debut_reports(weekly):
    first=weekly.groupby('song_id').chart_date.min().rename('debut')
    d=weekly.merge(first,on='song_id',validate='many_to_one');d=d[d.chart_date.eq(d.debut)]
    return d.groupby('song_id').agg(debut_reported_last_week_rank=('reported_last_week_rank','min'),
        debut_reported_peak_position=('reported_peak_position','min'),debut_reported_weeks_on_chart=('reported_weeks_on_chart','max')).reset_index()


@lru_cache(maxsize=1)
def weekly():
    return pd.read_csv(ROOT/'data/public/master_weekly.csv.xz',usecols=['song_id','chart_date','weekly_rank','reported_last_week_rank','reported_peak_position','reported_weeks_on_chart'])


@lru_cache(maxsize=1)
def source_frame():
    f=pd.read_csv(DATA/'song_features.csv.xz');o=pd.read_csv(DATA/'song_outcomes.csv.xz')
    extras=pd.read_csv(ROOT/'data/public/songs.csv',usecols=['song_id','secondary_genres','genre_confidence'])
    f=f.merge(o,on='song_id',validate='one_to_one').merge(extras,on='song_id',how='left',validate='one_to_one')
    f=f.merge(debut_reports(weekly()),on='song_id',how='left',validate='one_to_one')
    f['debut_time_years']=(pd.to_datetime(f.first_chart_date)-pd.Timestamp('1970-01-01')).dt.days/365.2425
    if f.song_id.duplicated().any() or len(f)!=32723:raise ValueError('Exact identity population changed')
    return f.sort_values('song_id').reset_index(drop=True)


def population(track):
    f=source_frame()
    if track=='retrospective':f=f[f[SCORES].notna().all(axis=1)&f.lyric_word_count.notna()]
    elif track!='strict':raise ValueError('Unknown track')
    return f[f.first_chart_date.ge(CONFIG['burn_in_end'])].copy()


def lifetime_at(data,cutoff):
    """No row after cutoff can influence a label or its maturity/inactivity status."""
    q=data[data.chart_date.lt(cutoff)].copy();q['points']=101-q.weekly_rank
    result=q.groupby('song_id').agg(first_observed=('chart_date','min'),last_observed=('chart_date','max'),
        best_rank=('weekly_rank','min'),chart_weeks=('chart_date','nunique'),chart_points=('points','sum'))
    date=pd.Timestamp(cutoff)
    result['mature']=(pd.to_datetime(result.first_observed)+pd.DateOffset(years=CONFIG['lifetime_maturity_years'])).le(date)
    result['inactive']=(pd.to_datetime(result.last_observed)+pd.DateOffset(years=CONFIG['lifetime_inactivity_years'])).le(date)
    return result.reset_index()


@lru_cache(maxsize=10)
def labels_at(cutoff):return lifetime_at(weekly(),cutoff)


def end_date():return (pd.Timestamp(weekly().chart_date.max())+pd.Timedelta(days=1)).date().isoformat()


def partition(track,horizon,target,start,end):
    f=population(track);end=end or end_date()
    if horizon=='26':
        complete=f.eligible_26.astype(bool)
        train=f[complete&f.window_end_26.le(start)].copy()
        validation=f[complete&f.first_chart_date.ge(start)&f.window_end_26.le(end)].copy()
        # Last source date must reach the end, as in V1, even for final evaluation.
        train['outcome']=train[target+'_26'];validation['outcome']=validation[target+'_26']
    elif horizon=='observed_lifetime':
        def cohort(cutoff,after=None):
            labels=labels_at(cutoff);labels=labels[labels.mature&labels.inactive]
            subset=f[f.first_chart_date.lt(cutoff)]
            if after is not None:subset=subset[subset.first_chart_date.ge(after)]
            return subset.merge(labels[['song_id',target]].rename(columns={target:'outcome'}),on='song_id',validate='one_to_one')
        train=cohort(start);validation=cohort(end,start)
    else:raise ValueError('Unknown outcome window')
    if set(train.song_id)&set(validation.song_id):raise ValueError('Identity crosses partitions')
    if min(len(train),len(validation))<2:raise ValueError('Insufficient cohort support')
    for frame in [train,validation]:
        if not np.isfinite(frame.outcome.to_numpy(float)).all():raise ValueError('Missing/nonfinite outcome')
    return train.sort_values('song_id').reset_index(drop=True),validation.sort_values('song_id').reset_index(drop=True)


def tasks():
    return [dict(task_id=f'{track}__{horizon}__{target}',track=track,horizon=horizon,target=target) for track,horizon,target in itertools.product(CONFIG['tracks'],['26','observed_lifetime'],TARGETS)]


def input_hashes():
    return {str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'data/public/songs.csv',ROOT/'data/public/master_weekly.csv.xz',DATA/'song_features.csv.xz',DATA/'song_outcomes.csv.xz',DATA/'manifest.json',V1/'feature_dictionary.csv',V1/'model_comparison.csv',V1/'selected_models.csv',V1/'selected_predictions.csv.gz']}


def freeze():
    record=dict(configuration=CONFIG,predictors=REGISTRY,environment=environment(),input_sha256=input_hashes())
    path=PUBLIC/'protocol.json'
    if path.exists() and read_json(path)!=clean(record):raise ValueError('Frozen V2 protocol/input/environment changed; use a new version')
    if not path.exists():write_json(path,record)
    return digest(record)


def provenance():
    paths=list(sorted((ROOT/'src').glob('regression_expanded*.py')))+[ROOT/'src/regression_core.py',ROOT/'src/regression_spec.py',ROOT/'analysis/planning/regression_search/audit.py',ROOT/'src/feature_expansion_common.py']
    # Report/validation code is outside numerical checkpoint identity.
    paths=[p for p in paths if not p.name.endswith(('_report.py','_validate.py'))]
    return dict(protocol_sha256=freeze(),code_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},environment=environment())


def preservation(initialize=False):
    path=LOCAL/'preservation.json'
    if not path.exists():
        if not initialize:raise ValueError('Missing preservation snapshot')
        names=set(subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines())
        for base in [ROOT/'data',ROOT/'analysis']:
            for p in base.rglob('*'):
                if p.is_file() and '__pycache__' not in p.parts and not any(x==p or x in p.parents for x in [PUBLIC,LOCAL]):names.add(str(p.relative_to(ROOT)))
        files={name:dict(bytes=(ROOT/name).stat().st_size,sha256=sha(ROOT/name)) for name in sorted(names) if (ROOT/name).is_file() and not any(x==ROOT/name or x in (ROOT/name).parents for x in [PUBLIC,LOCAL])}
        write_json(path,dict(baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files=files))
        return dict(status='SNAPSHOT_CREATED',files=len(files),bytes=sum(r['bytes'] for r in files.values()))
    record=read_json(path)
    for name,expected in record['files'].items():
        p=ROOT/name
        if not p.is_file() or p.stat().st_size!=expected['bytes'] or sha(p)!=expected['sha256']:raise ValueError('Protected input/result changed: '+name)
    return dict(status='PASS',files=len(record['files']),bytes=sum(r['bytes'] for r in record['files'].values()),baseline_commit=record['baseline_commit'])


def source_inventory():
    rows=[]
    aliases=dict(first_chart_date='debut_time_years',chart_date='debut_time_years',weekly_rank='debut_rank',reported_last_week_rank='debut_reported_last_week_rank',reported_peak_position='debut_reported_peak_position',reported_weeks_on_chart='debut_reported_weeks_on_chart',
        mb_duration_median_seconds='duration_seconds',mb_duration_min_seconds='duration_seconds',mb_duration_max_seconds='duration_seconds',debut_season_sin='debut_season_phase',debut_season_cos='debut_season_phase')
    for path in [ROOT/'data/public/songs.csv',ROOT/'data/public/master_weekly.csv.xz',DATA/'song_features.csv.xz',DATA/'song_outcomes.csv.xz']:
        for column in pd.read_csv(path,nrows=0).columns:
            canonical=aliases.get(column,column);r=REGISTRY.get(canonical)
            if path.name=='song_outcomes.csv.xz':status='excluded';reason='Outcome, censoring or post-debut audit field';r=None
            elif r:status='eligible_strict_and_retrospective' if r['availability']=='C' else 'retrospective_only';reason='Complete registered variable; aliases counted once; date-specific chart fields use first publication only'
            elif column in ['song_id','title','artist','source_chart_index','source_row_index','mb_release_title']:status='excluded';reason='Identifier or asset label; no identity memorization'
            elif column in ['mb_earliest_release_date','mb_release_date_precision']:status='excluded';reason='Matched manifestations do not establish original release timing'
            elif column in ['mb_recording_count','mb_release_count','mb_distinct_duration_count']:status='excluded';reason='Modern accumulated catalog/version coverage; not a debut-time intrinsic measurement'
            elif column in ['musicbrainz_match_status','lyrics_status','lyrics_available','in_final_study_population']:status='excluded';reason='Acquisition/provenance or future-selected population indicator'
            else:status='excluded';reason='Whole-history outcome, observation count or later monthly-selection information'
            rows.append(dict(source=str(path.relative_to(ROOT)),column=column,canonical_predictor=canonical if r else '',status=status,reason=reason,availability=r['availability'] if r else 'E_or_operational'))
    return rows


def audit():
    freeze();write_csv(PUBLIC/'predictor_inventory.csv',list(REGISTRY.values()));write_csv(PUBLIC/'source_column_eligibility.csv',source_inventory())
    search=[];cohorts=[]
    for task in tasks():
        for configuration in ['original','new','combined']:
            n=len(predictors(task['track'],configuration));counts={f'k{k}':math.comb(n,k) if n>=k else 0 for k in [1,2,3]}
            search.append(dict(**task,configuration=configuration,predictors=n,**counts,total=sum(counts.values()),note='Original/new are filtered subsets of the combined enumeration; not additional duplicate fits'))
        for fold,(start,end) in enumerate(FOLDS+[('2018-01-01',None)]):
            tr,va=partition(task['track'],task['horizon'],task['target'],start,end)
            cohorts.append(dict(**task,fold=fold,role='evaluation' if fold==3 else 'validation',start=start,end=end or end_date(),
                n_train=len(tr),n_validation=len(va),train_ids_sha256=digest(tr.song_id.tolist()),validation_ids_sha256=digest(va.song_id.tolist())))
    write_csv(PUBLIC/'search_space.csv',search);write_csv(PUBLIC/'cohorts.csv',cohorts)
    f=source_frame();eligible=f[f.first_chart_date.ge(CONFIG['burn_in_end'])]
    censor=[]
    for cutoff in sorted(set([x for p in FOLDS for x in p]+['2018-01-01',end_date()])):
        q=labels_at(cutoff);q=q[q.first_observed.ge(CONFIG['burn_in_end'])]
        censor.append(dict(cutoff=cutoff,observed=len(q),mature=int(q.mature.sum()),inactive=int(q.inactive.sum()),mature_and_inactive=int((q.mature&q.inactive).sum())))
    write_csv(PUBLIC/'lifetime_censoring_audit.csv',censor)
    total=sum(r['total'] for r in search if r['configuration']=='combined')
    record=dict(status='AUDITED',predictors={track:{c:len(predictors(track,c)) for c in ['original','new','combined']} for track in CONFIG['tracks']},
        tasks=len(tasks()),unique_combinations=total,validation_fits=3*total,all_candidate_evaluation_fits=total,total_candidate_fits=4*total,
        raw_weekly_identities=len(f),post_burn_in_identities=len(eligible),source_endpoint=weekly().chart_date.max(),
        debut_report_anomalies=dict(nonmissing_prior_week_rank=int(eligible.debut_reported_last_week_rank.notna().sum()),reported_weeks_above_one=int(eligible.debut_reported_weeks_on_chart.gt(1).sum()),reported_peak_differs_from_observed_debut=int(eligible.debut_reported_peak_position.ne(eligible.debut_rank).sum())),
        full_search_started=False,previous_results_modified=False)
    write_json(PUBLIC/'audit.json',record);print(json.dumps(record,indent=2),flush=True)
    return record


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['audit','preserve','verify-preservation']);args=p.parse_args()
    if args.action=='audit':audit()
    else:print(json.dumps(preservation(args.action=='preserve'),indent=2),flush=True)
