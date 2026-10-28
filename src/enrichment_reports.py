"""Generate measured inventories, documentation and coverage figures; no modelling."""
from __future__ import annotations
from collections import defaultdict
import json
import gzip
import re
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from enrichment_common import ROOT,LOCAL,MUSIC,DATA,HISTORY,HISTORY_DATA,EXTERNAL,sha,write_csv,write_json,atomic_bytes


def md(path,text):atomic_bytes(path,(text.strip()+'\n').encode())

def load(path):return json.loads(path.read_text())


def construct_key(feature):
    if feature.startswith('lyric_pos_'):return 'lyric_pos_distribution'
    if feature.startswith('lyric_verb_'):return 'lyric_verb_tense_distribution'
    for family in ['mfcc','gfcc','spectral_contrast']:
        if feature.startswith('audio_'+family+'_'):return 'audio_'+family+'_profile'
    if feature.startswith('audio_silence_'):return 'audio_silence_threshold_profile'
    if feature in ['audio_key','audio_mode','audio_key_strength']:return 'audio_key_mode_strength'
    if feature.startswith('audio_model_mood_'):return 'audio_model_mood_probability_profile'
    aliases={'mb_v2_external_producer_count':'mb_v2_known_producer_count','mb_v2_external_cover_evidence':'mb_v2_cover_evidence',
        'mb_v2_external_remix_relationships':'mb_v2_remix_relationships','mb_v2_external_artist_country_set':'mb_v2_artist_country_set',
        'mb_v2_external_artist_type_set':'mb_v2_artist_type_set'}
    return aliases.get(feature,feature)


MAPPING={
36:['lyric_marked_section_count'],37:['lyric_marked_chorus_token_share'],53:['mb_v2_release_group_primary_types'],
54:['mb_v2_release_group_secondary_types'],55:['mb_v2_release_country_set'],56:['mb_v2_release_status_set'],57:['mb_v2_artist_type_set'],
58:['mb_v2_artist_country_set','mb_v2_external_artist_country_set'],67:['mb_v2_known_writer_count'],
68:['mb_v2_known_producer_count','mb_v2_external_producer_count'],70:['mb_v2_work_language_set'],71:['mb_v2_cover_evidence','mb_v2_external_cover_evidence'],
73:['audio_tag_media_set'],77:['artist_prior_collaborator_count'],79:['artist_prior_collaborator_success_mean'],83:['collaboration_prior_genre_distance'],
84:['lyric_syllable_count_complete'],85:['lyric_syllables_per_covered_word'],86:['lyric_adjacent_end_rhyme_share'],87:['lyric_multisyllabic_adjacent_rhyme_share'],
89:['lyric_pos_.*_share'],90:['lyric_parser_sentence_length_mean'],91:['lyric_dependency_depth_mean'],92:['lyric_verb_.*_share'],
93:['lyric_named_entity_token_share'],94:['lyric_geographic_entity_token_share'],98:['lyric_modern_wordfreq_mean'],
103:['lyric_semantic_novelty_prior_hits'],105:['lyric_semantic_drift_from_credit'],
106:['audio_bpm'],107:['audio_key','audio_mode'],108:['audio_average_loudness_essentia'],109:['audio_mfcc_.*_mean'],
110:['audio_onset_rate'],111:['audio_beat_interval_cv'],112:['audio_spectral_centroid_mean'],113:['audio_bark_flatness_db_mean'],
114:['audio_spectral_flux_mean'],115:['audio_spectral_contrast_.*_mean'],116:['audio_dissonance_mean'],117:['audio_key_strength'],
118:['audio_chroma_entropy_mean'],119:['audio_danceability_essentia','audio_model_danceability_probability'],
121:['audio_spectral_rms_mean'],122:['audio_model_mood_acoustic_probability'],124:['audio_dynamic_complexity'],125:['audio_silence_.*_fraction']}
EXTERNAL_MAP={159:['US_UNEMPLOYMENT'],160:['US_CPI_YOY'],161:['US_REAL_DISPOSABLE_INCOME_PC_YOY'],162:['US_NBER_DATED_RECESSION'],
163:['US_CONSUMER_SENTIMENT'],164:['US_RECREATION_GOODS_REAL_YOY','US_RECREATION_SERVICES_REAL_YOY'],165:['US_CHILD_POPULATION_SHARE'],
166:['US_URBAN_POPULATION_SHARE'],168:['US_INTERNET_USERS'],170:['US_FEDERAL_ELECTION_MONTH'],171:['GLOBAL_STATE_CONFLICTS'],
172:['GLOBAL_BATTLE_DEATHS_BEST'],173:['US_OXCGRT_STRINGENCY_MONTHLY_MEAN'],177:['US_CONTIGUOUS_TEMPERATURE_ANOMALY']}
QUALIFICATIONS={58:'Source artist.country is not verified formation country.',71:'Explicit positive cover evidence only; absent relationship is unknown, never non-cover.',
73:'Associated edition media tags, not verified original-release format.',84:'Only complete English dictionary coverage yields full syllable count; unknown words remain missing.',
85:'Mean among dictionary-covered words, with coverage diagnostics.',86:'Adjacent end-word phonetic proxy, not annotated performed rhyme.',87:'Dictionary phonetic proxy, not performed or multi-line rhyme annotation.',
89:'English-trained parser diagnostic, not language-independent grammatical truth.',90:'Parser segmentation on normalized lyric lines, not prose sentences.',
91:'English parser depth diagnostic.',92:'Parser morphological tags, not exhaustive semantic tense.',93:'English model NER diagnostic.',94:'English GPE/LOC NER diagnostic.',
98:'Modern English frequency list, not historical rarity.',105:'Prior exact Billboard artist-credit centroid, not resolved individual-artist history.',
108:'Essentia average loudness; not standardized integrated LUFS.',113:'Bark-band flatness dB summary, not generic flatness of full spectrum.',
119:'Essentia heuristic and uncalibrated source classifier; not Spotify scale.',122:'Uncalibrated source acoustic-mood classifier, not standardized acousticness.',
124:'Dynamic complexity proxy, not peak-to-RMS or standardized short-term dynamic range.',
159:'Latest revised snapshot, no as-of guarantee.',160:'Latest revised CPI inflation, no as-of guarantee.',161:'Real per-capita DPI growth snapshot, no as-of guarantee.',
163:'Final Michigan archive, no original-vintage guarantee; local values only.',165:'Age 0-14 population share, not the proposed youth age band.',
170:'Scheduled election-month flag; no bespoke daily proximity score.',177:'Contiguous-US monthly land-area temperature anomaly, not weekly listener-weighted exposure.'}


def inventories(songs,dictionary):
    old=pd.read_csv(MUSIC/'feature_gap_audit_initial.csv',keep_default_na=False)
    cov=pd.read_csv(MUSIC/'coverage_report.csv').query("debut_decade == 'all'").set_index('feature')
    ext=pd.read_csv(HISTORY/'coverage_report.csv').set_index('series_id')
    for i,row in old.iterrows():
        number=int(row.candidate_id[1:]);fields=[];status=row.implementation_status;reason=row.decision_reason;count=''
        if row.audit_classification=='already_implemented':status='reused_frozen_v1'
        elif number in MAPPING:
            patterns=MAPPING[number];fields=[c for c in songs if any(re.fullmatch(p,c) for p in patterns)]
            count=int(songs[fields].replace('',np.nan).notna().any(axis=1).sum()) if fields else 0
            status='implemented_qualified_proxy' if number in QUALIFICATIONS else 'implemented_versioned_feature'
            if not count:status='implemented_schema_no_observed_values'
            reason=QUALIFICATIONS.get(number,'Available under documented source, mapping and missingness gates.')
        elif number==102:status='implemented_private_embedding';count=load(MUSIC/'nlp_summary.json')['complete_embeddings'];reason='Dense vectors retained privately; public derived semantic distances only.'
        elif number in [156,157,158]:
            fields=[{156:'chart_rank_improvement_per_elapsed_week',157:'chart_first4w_points_after_window',158:'chart_prior_absent_chart_count'}[number]]
            status='implemented_chart_period_view';reason='Available only at required chart dates; preserve duplicate source rows; not a predebut feature.'
        elif number in EXTERNAL_MAP:
            fields=[s for s in EXTERNAL_MAP[number] if s in ext.index];count=int(ext.loc[fields,'nonnull'].sum()) if fields else 0
            status='implemented_external_qualified' if number in QUALIFICATIONS else 'implemented_external_natural_frequency'
            reason=QUALIFICATIONS.get(number,'Separate external layer with native frequency, original units and retrospective/publication rules.')
        elif number==179:status='reused_frozen_v1';fields=['chart_calendar_regime'];reason='Frozen V1 chart methodology calendar already retained; no new regime selection.'
        elif row.audit_classification=='not_worth_automatic_implementation':status='deferred_quality_or_redundancy'
        else:status='deferred_access_or_evidence';reason=reason or 'No verified sufficiently complete lawful source or operational definition in this bounded campaign.'
        old.loc[i,'implementation_status']=status;old.loc[i,'implemented_fields']=';'.join(fields)
        old.loc[i,'observed_support_count']=count;old.loc[i,'decision_reason']=reason
        old.loc[i,'support_unit']='external native observations' if number in EXTERNAL_MAP else 'songs with any mapped value' if number not in [156,157,158] else 'chart-period view; see dictionary'
    write_csv(MUSIC/'feature_inventory.csv',old)
    write_csv(MUSIC/'implementation_queue.csv',old.loc[old.priority.astype(int)>0].sort_values(['priority','candidate_id']))
    groups=defaultdict(list)
    for row in dictionary.to_dict('records'):
        if row['column_role']!='analytical_construct':continue
        feature=row['feature']
        if feature not in cov.index or cov.loc[feature,'nonnull_songs']==0:continue
        groups[construct_key(feature)].append(feature)
    records=[]
    for key,fields in sorted(groups.items()):
        count=int(songs[fields].replace('',np.nan).notna().any(axis=1).sum())
        records.append({'construct_id':key,'component_columns':';'.join(fields),'columns':len(fields),'songs_with_any_component':count,
                        'count_rule':'Descriptive construct grouping; not a statistical independence claim'})
    for name in ['chart_rank_improvement_per_elapsed_week','chart_prior_absent_chart_count','chart_first4w_points_after_window']:
        records.append({'construct_id':name,'component_columns':name,'columns':1,'songs_with_any_component':'','count_rule':'Chart-period construct; availability gated by date'})
    records.append({'construct_id':'lyric_semantic_embedding_private','component_columns':'384 private dimensions','columns':384,
                    'songs_with_any_component':load(MUSIC/'nlp_summary.json')['complete_embeddings'],'count_rule':'One representation; not 384 discoveries; private only'})
    write_csv(MUSIC/'construct_inventory.csv',records)
    return old,records


def sources():
    specs=pd.read_csv(HISTORY/'series_dictionary.csv',keep_default_na=False)
    rows=[]
    for (provider,url),g in specs.groupby(['source','source_url'],sort=True):
        rows.append({'source':provider,'url':url,'series_count':len(g),'series_ids':';'.join(sorted(g.series_id)),
            'frequencies':';'.join(sorted(set(g.frequency))),'geographies':';'.join(sorted(set(g.geography))),
            'retrieval_date':g.retrieval_date.max(),'licenses':'; '.join(sorted(set(g.license))),
            'redistribution_permitted':bool(g.redistribution_permitted.all()),'raw_sha256':';'.join(sorted(set(g.raw_sha256))),
            'temporal_modes':';'.join(sorted(set(g.availability_status)))})
    write_csv(HISTORY/'source_inventory.csv',rows)
    # All original response provenance stays auditable; exclude the independent
    # financial-acquisition campaign's content-addressed subdirectory.
    manifests=[]
    for p in sorted(EXTERNAL.glob('*/raw/*.provenance.json')):
        record=load(p);record['local_raw_path']=str(p.with_name(p.name.removesuffix('.provenance.json')).relative_to(ROOT))
        record['provenance_path']=str(p.relative_to(ROOT));manifests.append(record)
    write_json(EXTERNAL/'manifests/source_manifest.json',manifests)
    return specs


def period_coverage():
    observations=pd.read_csv(EXTERNAL/'derived/all_observations.csv.xz',keep_default_na=False,low_memory=False)
    observations['value']=pd.to_numeric(observations.value.replace('',np.nan),errors='raise')
    rows=[]
    for sid,g in observations.groupby('series_id',sort=True):
        freq=g.frequency.iloc[0]
        if freq not in ['M','Q','A']:continue
        pf={'M':'M','Q':'Q-DEC','A':'Y-DEC'}[freq]
        valid=set(pd.PeriodIndex(g.loc[g.value.notna(),'date'],freq=pf))
        for label,begin,end in [('1958-2026','1958-01','2026-12'),('1958-1979','1958-01','1979-12'),
                               ('1980-1999','1980-01','1999-12'),('2000-2019','2000-01','2019-12'),('2020-2026','2020-01','2026-12')]:
            grid=pd.period_range(begin,end,freq=pf);missing=[p not in valid for p in grid];run=longest=0
            for absent in missing:
                run=run+1 if absent else 0;longest=max(longest,run)
            rows.append({'series_id':sid,'frequency':freq,'period':label,'expected_native_periods':len(grid),
                'valid_native_periods':len(grid)-sum(missing),'missing_native_periods':sum(missing),
                'coverage_fraction':1-sum(missing)/len(grid),'longest_missing_native_periods':longest,
                'denominator_note':'Full requested calendar period including future/unreleased 2026 tail; no monthly fabrication for Q/A'})
    write_csv(HISTORY/'coverage_by_period.csv',rows)


def music_source_links():
    rows=[]
    for name in ['external_metadata_provenance.json.gz','audio_provenance.json.gz']:
        records=json.loads(gzip.decompress((LOCAL/name).read_bytes()))
        for record in records:
            sources=record.get('sources',{'recording':record.get('source')})
            for kind,source in sources.items():
                if source is None:continue
                rows.append({'song_id':record['song_id'],'provider':'AcousticBrainz' if name.startswith('audio') else 'MusicBrainz',
                    'recording_id':record['recording_id'],'response_kind':kind,'source_url':source['url'],
                    'retrieved_at':source['retrieval_date'],'source_sha256':source['sha256'],
                    'mapping_status':record['mapping_status'],'original_edition_verified':False,'license':'CC0 core/analysis metadata'})
    write_csv(MUSIC/'metadata_source_provenance.csv.xz',rows)


def figures():
    plt.rcParams.update({'svg.hashsalt':'cmpt491-enrichment-v2','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    coverage=pd.read_csv(MUSIC/'coverage_report.csv');selected={'lyric_adjacent_end_rhyme_share':'Adjacent-line rhyme proxy','lyric_dependency_depth_mean':'Local linguistic models',
        'lyric_semantic_novelty_prior_hits':'Prior-hit semantic novelty','mb_v2_recording_ids':'Retained metadata IDs','audio_bpm':'Audio identity + duration gate'}
    figure,ax=plt.subplots(figsize=(10,5.5))
    for field,label in selected.items():
        d=coverage[coverage.feature.eq(field)&coverage.debut_decade.ne('all')].copy();d['decade']=d.debut_decade.astype(int)
        ax.plot(d.decade,d.coverage_fraction*100,marker='o',label=label)
    ax.set(ylim=(0,100),xlabel='Billboard debut decade',ylabel='Study songs with value (%)',title='Enrichment coverage varies by source and era')
    ax.set_xticks(sorted(coverage.loc[coverage.debut_decade.ne('all'),'debut_decade'].astype(int).unique()))
    ax.legend(loc='center left',bbox_to_anchor=(.01,.44),fontsize=9);ax.grid(axis='y',alpha=.2)
    figure.tight_layout();(MUSIC/'figures').mkdir(exist_ok=True);figure.savefig(MUSIC/'figures/coverage_by_decade.svg',metadata={'Date':None});plt.close(figure)
    cov=pd.read_csv(HISTORY/'coverage_report.csv');select=['FF_MKT_EXCESS','US_UNEMPLOYMENT','US_REAL_GDP','US_CONSUMER_SENTIMENT','US_IP_TOTAL','US_INTERNET_USERS',
        'US_INTENTIONAL_HOMICIDE_RATE','GLOBAL_STATE_CONFLICTS','GLOBAL_BATTLE_DEATHS_BEST','GLOBAL_VIOLENT_POLITICAL_PROTEST_DYADS',
        'US_OXCGRT_STRINGENCY_MONTHLY_MEAN','US_CONTIGUOUS_TEMPERATURE_ANOMALY','US_RECREATION_SERVICES_REAL']
    d=cov.set_index('series_id').loc[select].reset_index();fig,ax=plt.subplots(figsize=(11,7))
    for i,row in d.iterrows():
        first=pd.Timestamp(row.first_date);last=pd.Timestamp(row.last_date)
        a=max(1958,first.year+(first.month-1)/12);b=min(2026.99,last.year+(last.month-1)/12)
        ax.plot([a,b],[i,i],linewidth=7,color='#2166ac' if row.redistribution_permitted else '#b35806')
    ax.set_yticks(range(len(d)),[s.removeprefix('US_').replace('GLOBAL_','GLOBAL ').replace('_',' ').title() for s in select],fontsize=9)
    ax.set(xlim=(1958,2027),xlabel='Observation year (span does not imply gap-free coverage)',title='Selected external histories: blue public values; orange local values')
    ax.invert_yaxis();ax.grid(axis='x',alpha=.2);fig.tight_layout();(HISTORY/'figures').mkdir(exist_ok=True);fig.savefig(HISTORY/'figures/history_coverage.svg',metadata={'Date':None});plt.close(fig)


def reports():
    songs=pd.read_csv(DATA/'songs.csv.xz',keep_default_na=False,low_memory=False)
    dictionary=pd.read_csv(MUSIC/'feature_dictionary.csv',keep_default_na=False);inventory,constructs=inventories(songs,dictionary);specs=sources()
    music=load(DATA/'manifest.json');history=load(HISTORY/'transformation_summary.json');joins=load(HISTORY/'join_validation.json')
    audio=load(MUSIC/'audio_coverage.json');metadata=load(MUSIC/'external_metadata_coverage.json');acq=load(MUSIC/'acquisition_summary.json')
    summary={'audited_inventory_rows':len(inventory),'credible_candidates':int(inventory.credible_candidate.eq('yes').sum()),
        'candidate_statuses':inventory.implementation_status.value_counts().to_dict(),'new_construct_groups_including_chart_and_private_embedding':len(constructs),
        'prior_engineered_constructs':57,'total_engineered_construct_groups':57+len(constructs),'original_classifier_scores_separate':42,
        'music':music,'audio_accepted_songs':audio['statuses'].get('exact_mbid_credit_duration_consistent_edition_unverified',0),
        'new_metadata_exact_consistent_songs':metadata['exact_consistent_songs'],'historical':history,
        'source_series_by_category':specs.groupby('category').size().to_dict(),'source_series_by_frequency':specs.groupby('frequency').size().to_dict()}
    write_json(MUSIC/'campaign_summary.json',summary)
    md(MUSIC/'README.md',f'''# Music enrichment v2

This version retains all **28,041 exact Billboard title/artist identities**, all {music['original_columns_preserved']} original song fields, the frozen 57 engineered constructs, and 42 classifier scores. It adds {music['new_columns']} documented columns, including provenance and diagnostics. The [construct inventory](construct_inventory.csv) groups these into **{len(constructs)} new constructs** including three chart-period measures and one private embedding representation: **{57+len(constructs)} engineered groups in total**, separate from the original classifiers. These groups are not assumed statistically independent.

[Downloadable version](../../data/public/music_enrichment_v2/README.md) · [Feature audit](feature_inventory.csv) · [Dictionary](feature_dictionary.csv) · [Coverage](coverage_report.csv) · [Provenance and reproduction](provenance.md) · [Findings](findings.md).

The audit reconciles 188 rows, including 182 credible candidates, against the existing implementation. No frozen feature was recalculated. Local text inference finished for 20,981 approved texts. Audio characteristics passed the exact recording/credit/duration gate for {summary['audio_accepted_songs']:,} songs. Newly retrieved MusicBrainz data passed the exact ID/credit gate for {metadata['exact_consistent_songs']:,} songs. Original release editions remain unverified.

The monthly views contain {music['monthly_rows']} months and {music['genre_month_rows']:,} observed genre-month units. Means use available source rows, retain the three repeated source song/month pairs, and report distinct-song counts separately. Each feature has its own nonmissing denominator. These are retrospective measurements, including modern-model text diagnostics; chart-history prefix restrictions do not turn modern measurements into historical forecasts.

![Coverage by debut decade](figures/coverage_by_decade.svg)

The separate [historical layer](../external_historical/README.md) supplies contextual joins. No new cross-domain regressions, hypothesis tests, COVID breakpoint selection or causal claims were run.
''')
    md(MUSIC/'findings.md',f'''# Measured enrichment findings

- {music['new_columns']} new columns, with identifiers, quality fields and missingness distinguished from analytical quantities. The grouped inventory counts {len(constructs)} new constructs and {57+len(constructs)} total engineered groups; the 42 original classifiers remain separate.
- All 20,981 approved lyric texts have completed local linguistic diagnostics and complete 384-dimensional semantic vectors. Dense vectors and lyric text stay private. Modern English-trained models and lexicons are imperfect for historical lyrics, dialects, multilingual songs and sung pronunciation.
- Audio acquisition queried every one of 3,802 retained unique recording IDs. The strict mapping gate accepted {summary['audio_accepted_songs']:,} songs ({100*summary['audio_accepted_songs']/28041:.2f}% of the study). Coverage is selective, not a random audio sample. Submission offset 0 was chosen without inspecting feature values. No recordings were downloaded.
- MusicBrainz retained {acq['cached_successes']:,} successful entity responses from a planned {acq['planned_entities']:,}. The latest bounded retry stopped after repeated provider failures; remaining entities stay missing and restartable. {metadata['exact_consistent_songs']:,} study assets passed the new exact-credit gate. Sparse relationship counts are documented credits, not complete writer/producer censuses.
- Existing cache metadata covers many more assets but often has unresolved recording editions. First-release dates, source countries, associated label/media tags and cover evidence retain their precise source meanings. They do not establish original issue, artist nationality, definitive lyric language, or absence of a cover relationship.
- Original-label verification, comprehensive writer/producer histories, historic streaming/radio/social metrics, paywalled consumption data and standardized modern audio platform scores remain unavailable. Acoustic mood probabilities are not a valence scale; dynamic complexity is not standardized dynamic range. Every researched candidate has a final status and qualification in the audit.

The 1950s and 2020s bins are partial decades. Coverage figures use the frozen study-song denominator by first chart date. Monthly feature means are compositional summaries and require their own missingness sensitivity before inference.
''')
    md(MUSIC/'provenance.md',PROVENANCE)
    md(DATA/'README.md',f'''# Downloadable music enrichment v2

New additive version; original datasets remain unchanged. Files are compressed CSVs readable with `pandas.read_csv(path)`.

| File | Purpose |
|---|---|
| [songs.csv.xz](songs.csv.xz) | 28,041 song identities, exact original fields, frozen V1 features and new numeric/categorical metadata |
| [song_missingness.csv.xz](song_missingness.csv.xz) | Explicit missing indicator for every added field |
| [monthly_overall.csv.xz](monthly_overall.csv.xz) | {music['monthly_rows']} month-level means/counts; equal available source rows |
| [monthly_by_genre.csv.xz](monthly_by_genre.csv.xz) | {music['genre_month_rows']:,} observed genre-month units; same weighting |
| [chart_period_features.csv.xz](chart_period_features.csv.xz) | 355,487 exact original chart/source locations plus three availability-gated chart measures |
| [manifest.json](manifest.json) | Input, code and artifact SHA-256 fingerprints |

Definitions, licenses, model limitations, grouping rules and reproduction are in the [report](../../../analysis/music_enrichment_v2/README.md). Missing is not zero. Do not treat retrospective metadata as predebut information. No lyrics, audio, embeddings, credentials or private caches are distributed.
''')
    md(HISTORY/'README.md',f'''# External historical platform v1

The separate historical layer contains **{history['source_series']} source series** and **{history['derived_series']} explicitly derived series**, totaling **{history['all_rows']:,} native observations**. Financial, macroeconomic, political, social and cultural tables share one provenance schema. Original frequency is retained; dates span earlier warm-up history through available 2026 observations, with provider-specific end dates and gaps.

[Source inventory](source_inventory.csv) · [Source dictionary](series_dictionary.csv) · [Derived dictionary](derived_series_dictionary.csv) · [Coverage](coverage_report.csv) · [Alignment](temporal_alignment.md) · [Join validation](join_validation.md) · [Research opportunities](research_opportunities.md) · [Public downloads](../../data/public/external_historical_v1/README.md).

The public release contains **{history['permitted_rows']:,} permitted observations**. French market returns, Michigan survey values and NBER chronology values stay local pending redistribution permission. Official US statistical series, World Bank indicator data, UCDP and Oxford policy aggregates retain their respective attribution and source terms.

There are {joins['music_months']} overall music months, all with at least one external observation. This does not mean every series covers every month. Natural quarterly and annual views preserve lower-frequency information; the [coverage table](coverage_report.csv) lists each series. Daily series are not silently treated as monthly observations.

![Selected source spans](figures/history_coverage.svg)

This campaign builds data and joins only. The independently developed [financial research catalog](financial_research/README.md) and financial acquisition subdirectory are separate work; this release does not absorb their source snapshots or code.
''')
    md(HISTORY/'temporal_alignment.md',TEMPORAL)
    md(HISTORY/'join_validation.md',f'''# Join validation

The machine-readable [audit](join_validation.json) records {joins['music_months']} overall music months, {joins['source_song_months']:,} source song-month rows and {joins['chart_rows']:,} source chart locations. All source locations and the {joins['preserved_repeated_song_month_rows']} repeated song-month rows are retained. Score-specific denominators follow the existing descriptive series; genre cells are observed cells rather than a manufactured full grid.

Each monthly/quarterly/annual external panel has one row per natural period. Music summaries join many-to-one onto that panel. Quarterly GDP and annual population/conflict data are absent from monthly columns. Quarter/year music means aggregate original monthly source rows and flag incomplete calendar periods. They are not equal-song or exposure-weighted substitutes.

The as-of view includes {joins['asof']['series']} historical-release series and {joins['asof']['nonnull']:,} values across {joins['asof']['music_months_with_any']} music months. It excludes {joins['asof']['latest_snapshot_series_excluded']} other series. Only a release strictly earlier than the chart cutoff day is usable. Same-day ordering is unknown; no intraday availability is asserted. Original industrial-production initial/revised estimates and NBER announcement-event types remain distinct from latest estimates and actual recession state.

Release-context statuses: `{json.dumps(joins['release_statuses'],sort_keys=True)}`. Year-only dates never receive an invented month. A candidate after debut is flagged and excluded. Even accepted candidate months remain original-edition-unverified and unsuitable for an as-of release forecast.

Run `python3 src/music_enrichment_validate.py --private` for source hashes, temporal checks and independent return replay. The public-only command omits `--private` and verifies both published manifests and exact original music fields. The tests exercise duplicate preservation, missing-month lags, future publication rejection, edition matching and invalid values.
''')
    md(HISTORY/'research_opportunities.md',OPPORTUNITIES)
    md(HISTORY_DATA/'README.md',f'''# Public external historical data v1

This release contains {history['permitted_rows']:,} source and derived observations cleared for redistribution in this campaign. Restricted source values are excluded; coverage and reproduction details remain documented. [Full report](../../../analysis/external_historical/README.md).

| File | Meaning |
|---|---|
| [observations.csv.xz](observations.csv.xz) | Long native-frequency observations, units, dates, source URLs, hashes, licenses, transformations |
| [month_overall.csv.xz](month_overall.csv.xz) | Monthly original music-score summaries and monthly external columns |
| [month_genre.csv.xz](month_genre.csv.xz) | Genre-specific monthly summaries |
| [quarter_overall.csv.xz](quarter_overall.csv.xz), [quarter_genre.csv.xz](quarter_genre.csv.xz) | Natural quarterly views; incomplete music periods flagged |
| [year_overall.csv.xz](year_overall.csv.xz), [year_genre.csv.xz](year_genre.csv.xz) | Natural annual views |
| [asof_monthly_releases.csv.xz](asof_monthly_releases.csv.xz) | Only documented historical-release values strictly before chart cutoffs |
| [release_context_keys.csv.xz](release_context_keys.csv.xz) | Uncertain release candidates and explicit month-join eligibility |
| [chart_context_keys.csv.xz](chart_context_keys.csv.xz) | All original weekly chart/source locations |
| [manifest.json](manifest.json) | Artifact/input/code hashes and license selection |

Use the documented query command for selected chart/release context; do not duplicate all external columns into the song master. Dates refer to chart observation or explicit external measurement periods, never automatically lyric-writing dates.
''')
    md(EXTERNAL/'README.md','''# External historical storage

Original versioned provider responses live in ignored category `raw/` directories with per-response request/retrieval/hash sidecars. They are not edited, repaired or uploaded. All normalized mixed-license and joined working tables stay local; the permitted release is under `data/public/external_historical_v1/`.

`manifests/source_manifest.json` records this platform's original responses. The separately versioned financial acquisition directory has its own manifests and ownership. See `analysis/external_historical/README.md` for semantics and rebuild commands.
''')
    period_coverage();music_source_links();figures()
    for directory in [MUSIC,HISTORY]:
        files=[p for p in directory.iterdir() if p.is_file() and p.name!='report_manifest.json']+list((directory/'figures').glob('*.svg'))
        write_json(directory/'report_manifest.json',{'report_code_sha256':sha(__file__),
            'artifacts':{str(p.relative_to(directory)):sha(p) for p in sorted(files)}})
    print(json.dumps({k:v for k,v in summary.items() if k not in ['music']},indent=2))


PROVENANCE='''# Provenance, licenses and reproduction

Billboard defines chart identities and dates. The local snapshot reports upstream `mhollingshead/billboard-hot-100`; that attribution does not establish independent verification. Exact title and artist strings remain unchanged. Artist credits may refer to collaborations; neither normalized strings nor external IDs merge study identities.

Sources are the frozen approved private lyric inputs; retained MusicBrainz core-data caches and exact-MBID queries (CC0); AcousticBrainz numerical metadata (CC0); pinned CMUdict (BSD-style); spaCy en_core_web_sm 3.8.0 (MIT); all-MiniLM-L6-v2 at a fixed revision (Apache-2.0); and wordfreq 3.1.1 (Apache-2.0 software, source data may carry CC BY-SA attribution obligations). The [asset manifest](asset_manifest.json) records exact URLs and hashes; [runtime lock](requirements.lock.txt) records versions. Source attribution follows [MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_Database), [AcousticBrainz](https://acousticbrainz.org/), [CMUdict](https://github.com/cmusphinx/cmudict), [spaCy model](https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0), [MiniLM model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) and [wordfreq](https://github.com/rspeer/wordfreq). No newly acquired lyrics or recordings are used and no private text leaves the machine.

The local benchmark preceded full inference. Semantic vectors use all 254-wordpiece chunks up to a bounded 64-chunk limit, normalized mean pooling, and token-count weighting; oversized texts would be marked missing, not truncated. English parser/lexicon features are diagnostics and include coverage. Modern model training can include historical songs; prior-only comparison sets do not remove that limitation. Prior-hit references are updated only after scoring new entrants on the same chart. Artist-history graphs preserve exact credit or retained entity scope.

Original-issue label/date, formation-country and exhaustive role claims are not inferred from associated editions. MusicBrainz response IDs and artist-ID sets must agree with retained approved mappings. AcousticBrainz requires the exact recording-ID tag, exact artist-ID set and duration within max(2 seconds,2%). The earliest submission is fixed without feature-based selection. Source extractors, mapping outcomes and sparse associated media/label tags remain explicit. Audio versions still may differ by master or edition; these 1,405 assets are a selective subset.

Published data are directly usable without private inputs. Verify with:

```bash
python3 src/music_enrichment_validate.py
python3 -m unittest discover -s tests -v
```

A full offline rebuild requires the retained private lyric/source caches and the pinned local environment. It does not trigger acquisition or text inference:

```bash
python3 src/music_enrichment_features.py
python3 src/music_enrichment_metadata.py
python3 src/music_enrichment_acquire.py summarize
python3 src/music_enrichment_audio.py summarize
data/experiments/music_enrichment_v2/venv/bin/python src/music_enrichment_nlp.py export
python3 src/music_enrichment_views.py chart
python3 src/music_enrichment_views.py build
python3 src/external_historical_sources.py normalize
python3 src/external_historical_features.py
python3 src/external_historical_joins.py build
python3 src/enrichment_reports.py
python3 src/music_enrichment_validate.py --private
python3 src/enrichment_common.py verify
```

The environment path is local and ignored. Asset installation, initial NLP run and bounded metadata acquisition are separate opt-in commands in their source modules; do not reacquire for ordinary validation. Live providers can revise history, so fresh downloads are a new snapshot, not a byte-identical reconstruction. Preserve local snapshot hashes and do not overwrite frozen responses. The public manifests allow exact validation even when private reproduction inputs cannot be shared.
'''
TEMPORAL='''# Temporal alignment and reproduction

Each external record stores series ID, observation date/period end, native frequency, geography, value, units, provider/URL, retrieval time, publication/vintage information when available, license and transformation. Source rows carry original response path/hash. Derived rows identify every parent and formula; they do not fabricate original release times.

- Monthly values join on calendar chart month. Means use documented observed music source rows and score-specific denominators. Chart dates are not writing or recording dates.
- Quarterly and annual observations retain their native frequency and join only to quarterly/annual music summaries. No interpolation or repeated invented monthly GDP/population values.
- Daily French returns are separately compounded into months. Realized and downside volatility use sums of squared daily log returns, in monthly nonannualized percent units. Source-day counts are diagnostic; monthly and daily factor histories have different constructions and are retained separately. Their measured differences are reported, not repaired.
- Running drawdown includes the initial unit of wealth and refuses to bridge missing returns. Rolling returns require contiguous calendar months. Rate spreads retain instrument and quoting-basis differences. Nominal/real income, SAAR flows, index bases and mixed seasonal adjustment are explicit.
- Oxford monthly policy means require all calendar days. Values outside the 2020–2022 collection are missing. No COVID breakpoint or statistical design is selected. UCDP counts are threshold-defined source categories; US-involved conflict fatalities are not US deaths or US-caused deaths. Low/best/high counts are uncertainty bounds, not three independent discoveries.
- As-of queries fail closed unless the provider retains historical release values with original release dates. Releases must precede chart cutoffs by at least one day. Latest revised data remain retrospective even when a recent publication date is recorded. NBER announcement events are not contemporaneously known recession membership; undated periods after the last closed cycle remain unclassified.
- Original release candidates retain precision and source uncertainty. Year-only values have no month key. Candidates after chart debut are flagged. No candidate establishes lyric-writing date or verified original edition.

Offline rebuild: run `python3 src/external_historical_sources.py normalize`, then `python3 src/external_historical_features.py`, then `python3 src/external_historical_joins.py build`. Retained original caches are required. Public-only selective query:

```bash
python3 src/external_historical_joins.py query --permitted --view chart --series US_UNEMPLOYMENT US_CPI_YOY --output /tmp/chart_context.csv.xz
python3 src/external_historical_joins.py query --permitted --view release --series US_UNEMPLOYMENT --output /tmp/release_context.csv.xz
```

As-of chart queries require `--mode asof` and an eligible series from the source dictionary, such as the retained initial industrial-production growth series. A rejection for latest-snapshot unemployment is intentional. Queries repeat context across chart rows for convenience; they do not increase the number of independent economic observations.
'''
OPPORTUNITIES='''# Research opportunities awaiting review

The data support candidate comparisons of lyrical sentiment/anger/sadness with market returns and drawdowns; household conditions with substance-use or materialism scores; consumer perceptions versus measured economic activity; genre-specific trajectories versus demographic and internet adoption changes; lyrical structure versus cultural expenditure; and narrowly defined conflict/policy histories. These are hypotheses, not established associations.

Before any campaign, choose the estimand, musical weighting and unit, eligible sources, reference-period or publication-time mode, trend treatment, lag family, dependence-aware inference and multiple-testing correction. Assess autocorrelation, nonstationarity, shared calendar effects, genre composition, missing lyrics, selective audio matching, provider methodological changes, economic revisions and release-date uncertainty. Predeclare sensitivity analyses and distinguish explanatory association from forecasting. A hundred songs sharing a monthly economic value are not a hundred independent economic observations. Correlation does not establish causation.

Important gaps include verified original editions/labels, complete recording credits, historical listening-platform exposure, consistent music-format revenue, population-matched weekly weather exposure, broad social-platform/trust/religion histories and genuine historical vintages for most economic indicators. Avoid forcing a proxy where source meaning or access is unresolved. The separate financial research catalog proposes wider candidate families; its acquisition and any downstream modelling require their own reviewed dataset version.
'''

if __name__=='__main__':reports()
