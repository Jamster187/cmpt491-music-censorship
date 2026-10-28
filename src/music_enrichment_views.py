"""Versioned song and chart-period views; frozen public fields remain exact."""
from __future__ import annotations
from collections import Counter
import datetime as dt
import gzip
import json
import re

import numpy as np
import pandas as pd

from enrichment_common import ROOT, LOCAL, MUSIC, DATA, sha, write_csv, write_json
from feature_expansion_common import SCORES
from music_enrichment_audio import SCALARS, HIGH


def chart_features(weekly):
    """Features measured at each published chart; duplicate source rows survive."""
    original=weekly.copy()
    if original[['source_chart_index','source_row_index']].duplicated().any():raise ValueError('Source location duplicated')
    week=weekly.groupby(['song_id','chart_date'],sort=True).agg(rank=('weekly_rank','min'),points=('weekly_rank',lambda s:(101-s).sum())).reset_index()
    week['date']=pd.to_datetime(week.chart_date);week=week.sort_values(['song_id','date'])
    dates={day:i for i,day in enumerate(sorted(week.chart_date.unique()))}
    week['chart_index']=week.chart_date.map(dates)
    grouped=week.groupby('song_id',sort=False)
    previous_rank=grouped['rank'].shift();elapsed=grouped.date.diff().dt.days/7
    week['chart_rank_improvement_per_elapsed_week']=(previous_rank-week['rank'])/elapsed
    week['chart_prior_absent_chart_count']=grouped.chart_index.diff()-1
    debut=grouped.date.transform('min');end=debut+pd.Timedelta(days=28)
    partial=week.points.where(week.date<end,0)
    first4=partial.groupby(week.song_id).cumsum()
    week['chart_first4w_points_after_window']=first4.where(week.date>=end)
    columns=['chart_rank_improvement_per_elapsed_week','chart_prior_absent_chart_count','chart_first4w_points_after_window']
    return original.merge(week[['song_id','chart_date']+columns],on=['song_id','chart_date'],how='left',validate='many_to_one'),columns


def dictionary(columns):
    definitions=pd.read_csv(MUSIC/'new_feature_dictionary.csv',keep_default_na=False).to_dict('records')
    known={d['feature'] for d in definitions}
    metadata={
        'mb_v2_recording_ids':'All recording MBIDs retained under original high-confidence mapping; may contain multiple unresolved editions',
        'mb_v2_artist_ids':'Retained linked artist MBIDs; not new person-identity inference',
        'mb_v2_isrc_set':'Union of ISRC identifiers on linked recordings; not verified original issue',
        'mb_v2_artist_type_set':'Source artist-entity types across retained linked entities',
        'mb_v2_artist_country_set':'MusicBrainz artist.country values; not necessarily birthplace, nationality or formation country',
        'mb_v2_release_group_primary_types':'Source primary album/single/etc. types across associated release groups',
        'mb_v2_release_group_secondary_types':'Source secondary types across associated release groups',
        'mb_v2_release_country_set':'Countries of associated release editions; not artist origin',
        'mb_v2_release_status_set':'Release status labels on associated editions',
        'mb_v2_catalog_language_set':'Release text-representation language; not lyric language',
        'mb_v2_cached_format_set':'Media formats in retained release lookups; not original format verification',
        'mb_v2_cached_label_ids':'Label MBIDs in retained release lookups; not original-label verification',
        'mb_v2_work_ids':'Performance-linked work MBIDs in retained source cache',
        'mb_v2_cover_evidence':'1 if an explicit cover attribute exists; missing otherwise, never evidence of non-cover',
        'mb_v2_known_producer_count':'Distinct producer artist MBIDs in retained recording lookup relationships; null if none documented',
        'mb_v2_remix_relationships':'Explicit retained relationship type labels mentioning remix; missing does not establish original version',
        'mb_v2_recording_mapping_status':'Original pipeline canonical-recording status; high-confidence asset mapping can still have unresolved editions',
        'mb_v2_mapping_review_flags':'Original mapping caveats preserved as a JSON list',
        'mb_v2_mapping_processed_at':'Timestamp of original metadata mapping decision',
        'mb_v2_external_status':'Retrieval and exact MBID/artist-credit consistency gate result',
        'mb_v2_external_retrieved_at':'UTC retrieval timestamp of new recording response',
        'mb_v2_external_artist_country_set':'Country values of source recording-credit artists from new exact-MBID lookup; not formation-country verification',
        'mb_v2_external_artist_type_set':'Entity types of source recording-credit artists from new exact-MBID lookup',
        'mb_v2_external_isrc_set':'ISRCs on newly retrieved recording; not original-edition verification',
        'mb_v2_external_work_ids':'Newly retrieved performance work MBIDs for a unique retained recording',
        'mb_v2_work_language_set':'Language codes on performance-linked works; closer to lyric language, may remain mixed/unknown',
        'mb_v2_known_writer_count':'Distinct MBIDs with composer, lyricist or writer roles on performance-linked works; incomplete credit count',
        'mb_v2_known_composer_count':'Distinct composer MBIDs on linked works; null if none documented',
        'mb_v2_known_lyricist_count':'Distinct lyricist MBIDs on linked works; null if none documented',
        'mb_v2_external_producer_count':'Distinct explicit recording producer MBIDs; null if none documented',
        'mb_v2_external_cover_evidence':'1 for explicit cover-performance relation; absence remains null',
        'mb_v2_external_remix_relationships':'Explicit remix type, direction and target recording MBID list',
        'mb_v2_recording_first_release_candidate':'MusicBrainz recording first-release-date; source date candidate with variable precision, original Billboard edition unverified',
        'mb_v2_recording_video':'Source recording video boolean; missing remains missing',
        'mb_v2_external_release_list_truncated':'True when provider release-count exceeds returned release list; a truncated list is never treated as a full discography'}
    nlp={
        'lyric_nlp_token_count':'Nonspace/nonpunctuation tokens from pinned English spaCy parser',
        'lyric_parser_sentence_length_mean':'Mean nonspace/nonpunctuation tokens in parser-defined sentences; lyric line breaks are not validated sentences',
        'lyric_dependency_depth_mean':'Mean number of ancestors per lexical token in English parser dependency trees',
        'lyric_verb_past_share':'Past-tagged tokens / VERB+AUX tokens; null if no verbs',
        'lyric_verb_present_share':'Present-tagged tokens / VERB+AUX tokens; null if no verbs',
        'lyric_named_entity_token_share':'Distinct lexical tokens in parser named entities / lexical tokens; diagnostic only',
        'lyric_geographic_entity_token_share':'Distinct lexical tokens in GPE/LOC entities / lexical tokens',
        'lyric_modern_wordfreq_coverage':'Fraction of normalized lexical tokens with positive modern English wordfreq Zipf frequency',
        'lyric_modern_wordfreq_mean':'Mean positive modern English wordfreq Zipf frequency; missing words excluded and coverage reported; not historical rarity',
        'lyric_semantic_wordpieces':'Full tokenized lyric WordPiece count before chunking',
        'lyric_semantic_chunks':'Number of 254-WordPiece chunks needed for full lyric',
        'lyric_semantic_status':'Full-chunk embedding completion or explicit resource-limit status; no silent truncation',
        'lyric_semantic_novelty_prior_hits':'1-cosine(song vector, centroid of earlier songs already reaching Top 10); no same-date songs in reference',
        'lyric_semantic_prior_hit_reference_n':'Number of prior Top 10 identities with complete vectors used in novelty centroid',
        'lyric_semantic_drift_from_credit':'1-cosine(song vector, centroid of earlier same-exact-credit identities); modern model and lyric versions remain retrospective',
        'lyric_semantic_prior_credit_reference_n':'Number of earlier same-exact-credit identities with complete vectors'}
    for col in columns:
        if col in known or col=='song_id':continue
        if col in metadata:definition=metadata[col];group='metadata';source='MusicBrainz CC0 core data';unit='count' if col.endswith('count') else 'source field'
        elif col in nlp or col.startswith('lyric_pos_'):
            definition=nlp.get(col,'English spaCy '+col.removeprefix('lyric_pos_').removesuffix('_share').upper()+' POS tokens / all lexical parser tokens')
            group='nlp';source='Local pinned spaCy, MiniLM and wordfreq';unit='ratio or documented count/distance'
        elif col in SCALARS:
            path,unit=SCALARS[col];definition='AcousticBrainz offset-0 '+path+'; edition unverified, source extractor version retained';group='audio';source='AcousticBrainz CC0'
        elif col.startswith('audio_'):
            group='audio';source='AcousticBrainz CC0';unit='diagnostic'
            if col.startswith('audio_tag_'):
                group='audio_catalog_metadata';unit='source tag set'
                definition='Crowd-submitted associated edition '+col.removeprefix('audio_tag_')+' tags; recording identity gate passed, release/label/format not independently verified; never original-issue metadata'
            elif re.fullmatch(r'audio_(mfcc|gfcc)_\d+_mean',col):definition='Time-mean '+col.split('_')[1].upper()+' coefficient '+col.split('_')[2]+' from source Essentia extractor'
            elif col.startswith('audio_spectral_contrast_'):definition='Time-mean spectral-contrast band '+col.split('_')[-2]+' from source extractor'
            elif col.startswith('audio_model_'):
                classifier=col.removeprefix('audio_model_').removesuffix('_probability');definition=f'Source high-level classifier {classifier} probability for {HIGH[classifier]}; uncalibrated on this Billboard sample';unit='probability'
            else:definition={
                'audio_beat_interval_cv':'Sample SD / mean of adjacent detected beat intervals; at least four detected beats',
                'audio_mapping_status':'Exact MBID tag + exact artist-ID set + duration within max(2 sec,2%) gate; original edition always unverified',
                'audio_recording_id':'Retained uniquely linked recording MBID queried, including unsuccessful queries',
                'audio_submission_count':'Number of crowd-submitted analyses for MBID; only earliest offset 0 used',
                'audio_source_retrieved_at':'UTC metadata retrieval date; not original recording measurement date',
                'audio_extractor_version':'Source Essentia/extractor build versions as JSON'}[col]
        else:raise ValueError('Undocumented new column: '+col)
        support=col.endswith(('_status','_retrieved_at','_processed_at','_version','_reference_n','_wordpieces','_chunks')) or col in {
            'lyric_nlp_token_count','audio_recording_id','audio_submission_count','mb_v2_mapping_review_flags','mb_v2_external_release_list_truncated','mb_v2_recording_mapping_status'}
        support=support or col.endswith(('_ids','_isrc_set','_coverage')) or col=='audio_length_seconds'
        definitions.append({'feature':col,'definition':definition,'group':group,'candidate_id':'','historical_availability':'F',
            'units':unit,'source':source,'measurement_version':'music-enrichment-v2.1','missingness':'No imputation; null means unavailable, undocumented or failed quality gate',
            'column_role':'provenance_or_quality' if support else 'analytical_construct'})
    for d in definitions:d.setdefault('column_role','quality_diagnostic' if any(s in d['feature'] for s in ['coverage','known_syllable']) else 'analytical_construct')
    return definitions


def monthly_summaries(song_table,features):
    monthly=pd.read_csv(ROOT/'data/public/master_monthly.csv',keep_default_na=False)
    if monthly[['source_chart_index','source_row_index']].duplicated().any():raise ValueError('Duplicate source location')
    usable=[];numeric={'song_id':song_table.song_id}
    for col in features:
        values=song_table[col].replace('',np.nan)
        try:parsed=pd.to_numeric(values,errors='raise')
        except (ValueError,TypeError):continue
        if parsed.notna().any():numeric[col]=parsed;usable.append(col)
    numeric=pd.DataFrame(numeric)
    joined=monthly[['month','snapshot_chart_date','song_id','primary_genre']].merge(numeric,on='song_id',how='left',validate='many_to_one')
    def aggregate(keys):
        group=joined.groupby(keys,sort=True,dropna=False)
        result=group.size().rename('chart_source_row_count').to_frame()
        result['chart_distinct_song_count']=group.song_id.nunique()
        result['snapshot_chart_date']=group.snapshot_chart_date.first()
        result['weighting']='equal_source_rows_available_per_feature'
        return pd.concat([result,group[usable].mean().add_suffix('_mean'),group[usable].count().add_suffix('_n')],axis=1).reset_index()
    overall=aggregate(['month']);genres=aggregate(['month','primary_genre'])
    write_csv(DATA/'monthly_overall.csv.xz',overall);write_csv(DATA/'monthly_by_genre.csv.xz',genres)
    return overall,genres


def build():
    source=ROOT/'data/public/songs.csv';songs=pd.read_csv(source,dtype=str,keep_default_na=False)
    if songs.song_id.duplicated().any():raise ValueError('Duplicate canonical song identity')
    old=pd.read_csv(ROOT/'data/public/feature_expansion_v1/song_features.csv.xz',dtype=str,keep_default_na=False)
    extra=[c for c in old if c not in songs]
    songs=songs.merge(old[['song_id']+extra],on='song_id',how='left',validate='one_to_one')
    files=['local_features.csv.xz','metadata_features.csv.xz','external_metadata_features.csv.xz','nlp_features.csv.xz','audio_features.csv.xz']
    new=[];input_hashes={str(source.relative_to(ROOT)):sha(source)}
    for name in files:
        path=LOCAL/name;frame=pd.read_csv(path,keep_default_na=False,low_memory=False)
        if not set(frame.song_id)<=set(songs.song_id):raise ValueError('Enrichment contains nonstudy identities')
        if set(frame.columns)&set(songs.columns)!={'song_id'}:raise ValueError('Enrichment would overwrite existing fields')
        songs=songs.merge(frame,on='song_id',how='left',validate='one_to_one');new.extend(c for c in frame if c!='song_id')
        input_hashes[str(path.relative_to(ROOT))]=sha(path)
    original=pd.read_csv(source,dtype=str,keep_default_na=False)
    if not songs[original.columns].equals(original):raise ValueError('Frozen source fields changed in enriched view')
    definitions=dictionary(new);write_csv(MUSIC/'feature_dictionary.csv',definitions)
    # Explicit missingness sidecar covers every added field without doubling song master width.
    missing=pd.DataFrame({'song_id':songs.song_id,**{col+'_missing':(songs[col].isna()|songs[col].eq('')).astype(int) for col in new}})
    write_csv(DATA/'song_missingness.csv.xz',missing)
    write_csv(DATA/'songs.csv.xz',songs)
    analytical=[d['feature'] for d in definitions if d['column_role']=='analytical_construct']
    overall,genres=monthly_summaries(songs,SCORES+analytical)
    decade=(pd.to_datetime(songs.first_chart_date).dt.year//10*10).astype(int)
    coverage=[]
    for col in new:
        for period,index in [('all',songs.index)]+[(str(d),songs.index[decade.eq(d)]) for d in sorted(decade.unique())]:
            valid=~(songs.loc[index,col].isna()|songs.loc[index,col].eq(''))
            coverage.append({'feature':col,'debut_decade':period,'study_songs':len(index),'nonnull_songs':int(valid.sum()),'coverage_fraction':float(valid.mean())})
    write_csv(MUSIC/'coverage_report.csv',coverage)
    protocol_path=MUSIC/'build_protocol.json'
    if not protocol_path.exists():write_json(protocol_path,{'version':'music-enrichment-v2.1','measurement_run_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'population':'28,041 frozen exact original title + artist identities','source_chart_authority':'Billboard; reported local upstream mhollingshead/billboard-hot-100, not independently verified',
        'availability_codes':{'C':'Known at published chart (title only); no original release-date inference','F':'Retrospective metadata, text, corpus or modern-model measurement'},
        'licenses':'Original lyric rights unchanged; no lyric text or dense embeddings distributed. Source-specific metadata/model terms documented in provenance.md'})
    write_json(DATA/'manifest.json',{'version':'music-enrichment-v2.1','songs':len(songs),'original_columns_preserved':len(original.columns),
        'reused_v1_columns':len(extra),'new_columns':len(new),'new_analytical_columns':len(analytical),'monthly_rows':len(overall),'genre_month_rows':len(genres),
        'inputs':input_hashes,'code_sha256':{p.name:sha(p) for p in sorted((ROOT/'src').glob('music_enrichment_*.py'))},
        'artifacts':{p.name:sha(p) for p in sorted(DATA.glob('*.csv.xz'))},'protocol_sha256':sha(protocol_path),
        'frozen_v1_constructs':57,'feature_count_note':'Column counts are not counts of independent constructs: POS, MFCC/GFCC, keys/modes and model families are grouped in the construct inventory.'})
    print({'songs':len(songs),'new_columns':len(new),'monthly_rows':len(overall),'genre_month_rows':len(genres)},flush=True)


def build_chart():
    keys=['song_id','chart_date','weekly_rank','source_chart_index','source_row_index']
    weekly=pd.read_csv(ROOT/'data/public/master_weekly.csv.xz',usecols=keys)
    result,columns=chart_features(weekly)
    write_csv(DATA/'chart_period_features.csv.xz',result)
    write_json(MUSIC/'chart_period_features.json',{'rows':len(result),'columns':columns,'availability':'At current chart publication only; never use later rows for debut predictions',
        'definitions':{'chart_rank_improvement_per_elapsed_week':'(previous best observed rank - current best rank) / elapsed days*7; positive means improvement; first appearance null',
        'chart_prior_absent_chart_count':'Number of intervening source chart dates with no appearance; first appearance null',
        'chart_first4w_points_after_window':'Sum 101-rank over all source rows in [debut,debut+28 days); visible only on chart dates >=debut+28 days'},
        'duplicate_rule':'Rank minimum per song/date, points include every source row; final output retains every source location',
        'input_sha256':sha(ROOT/'data/public/master_weekly.csv.xz'),'code_sha256':sha(__file__)})


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','chart']);a=p.parse_args()
    build() if a.action=='build' else build_chart()
