"""Bounded CC0 AcousticBrainz metadata only; no audio transfer or title search."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import time
import urllib.request
from urllib.parse import urlencode, urlsplit, parse_qs

import numpy as np
import pandas as pd

from enrichment_common import ROOT, LOCAL, MUSIC, UA, sha, write_json, write_csv, atomic_bytes

BASE='https://acousticbrainz.org/api/v1/'
BATCH=25
SCALARS={
 'audio_bpm':('rhythm.bpm','beats/minute'),
 'audio_onset_rate':('rhythm.onset_rate','onsets/second'),
 'audio_danceability_essentia':('rhythm.danceability','Essentia detrended fluctuation statistic'),
 'audio_beats_count':('rhythm.beats_count','beats'),
 'audio_beats_loudness_mean':('rhythm.beats_loudness.mean','linear energy'),
 'audio_average_loudness_essentia':('lowlevel.average_loudness','Essentia normalized statistic; not LUFS'),
 'audio_dynamic_complexity':('lowlevel.dynamic_complexity','dB loudness deviation'),
 'audio_replay_gain':('metadata.audio_properties.replay_gain','dB'),
 'audio_length_seconds':('metadata.audio_properties.length','seconds'),
 'audio_key':('tonal.key_key','pitch-class name'),
 'audio_mode':('tonal.key_scale','major/minor label'),
 'audio_key_strength':('tonal.key_strength','correlation strength'),
 'audio_chord_change_rate':('tonal.chords_changes_rate','changes per frame'),
 'audio_tuning_frequency':('tonal.tuning_frequency','Hz'),
 'audio_spectral_centroid_mean':('lowlevel.spectral_centroid.mean','Hz'),
 'audio_spectral_flux_mean':('lowlevel.spectral_flux.mean','Essentia spectral flux'),
 'audio_spectral_entropy_mean':('lowlevel.spectral_entropy.mean','spectral entropy'),
 'audio_spectral_rolloff_mean':('lowlevel.spectral_rolloff.mean','Hz'),
 'audio_spectral_energy_mean':('lowlevel.spectral_energy.mean','linear spectral energy; gain sensitive'),
 'audio_spectral_rms_mean':('lowlevel.spectral_rms.mean','RMS of spectrum; gain sensitive'),
 'audio_bark_flatness_db_mean':('lowlevel.barkbands_flatness_db.mean','dB Bark-band spectral flatness'),
 'audio_spectral_complexity_mean':('lowlevel.spectral_complexity.mean','spectral peaks'),
 'audio_chroma_entropy_mean':('tonal.hpcp_entropy.mean','HPCP entropy statistic'),
 'audio_silence_20db_fraction':('lowlevel.silence_rate_20dB.mean','fraction of frames below -20 dB'),
 'audio_silence_30db_fraction':('lowlevel.silence_rate_30dB.mean','fraction of frames below -30 dB'),
 'audio_silence_60db_fraction':('lowlevel.silence_rate_60dB.mean','fraction of frames below -60 dB'),
 'audio_zero_crossing_rate_mean':('lowlevel.zerocrossingrate.mean','crossings per sample'),
 'audio_dissonance_mean':('lowlevel.dissonance.mean','sensory dissonance statistic')}
HIGH={'voice_instrumental':'voice','mood_acoustic':'acoustic','mood_aggressive':'aggressive',
      'mood_electronic':'electronic','mood_happy':'happy','mood_party':'party','mood_relaxed':'relaxed',
      'mood_sad':'sad','tonal_atonal':'tonal','timbre':'bright','danceability':'danceable'}


def download(url,path):
    """Cache exact response and obey server-provided rate headers after each call."""
    meta=path.with_name(path.name+'.provenance.json')
    if path.exists():
        record=json.loads(meta.read_text())
        if record['url']!=url or record['sha256']!=sha(path):raise ValueError('Audio cache mismatch')
        return
    start=time.monotonic()
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=45) as response:
        raw=response.read(5_000_001)
        if len(raw)>5_000_000:raise ValueError('Acoustic response byte budget exceeded')
        headers={k:response.headers.get(k) for k in ['X-RateLimit-Limit','X-RateLimit-Remaining','X-RateLimit-Reset-In']}
    json.loads(raw)  # Validate transport before publishing.
    atomic_bytes(path,raw)
    write_json(meta,{'url':url,'retrieval_date':dt.datetime.now(dt.timezone.utc).isoformat(),
        'bytes':len(raw),'sha256':sha(path),'rate_headers':headers,'license':'CC0'})
    wait=max(0,1.1-(time.monotonic()-start))
    if headers['X-RateLimit-Remaining'] is not None and int(headers['X-RateLimit-Remaining'])<=1:
        wait=max(wait,float(headers['X-RateLimit-Reset-In'] or 10)+.1)
    time.sleep(wait)


def acquire():
    ids=json.loads((LOCAL/'metadata_acquisition_queue.json').read_text())['single_recording_ids']
    start=time.monotonic();errors=[];consecutive=0
    for begin in range(0,len(ids),BATCH):
        batch=ids[begin:begin+BATCH]
        for kind in ['count','low-level','high-level']:
            path=LOCAL/'acousticbrainz'/kind/f'{begin:05d}.json'
            url=BASE+kind+'?'+urlencode({'recording_ids':';'.join(batch)})
            try:download(url,path);consecutive=0
            except Exception as e:
                errors.append({'url':url,'error':str(e),'kind':kind,'batch_start':begin});consecutive+=1
                time.sleep(10)
                if consecutive>=3:raise RuntimeError('Three consecutive AcousticBrainz failures; checkpoint retained') from e
        if begin%250==0:print('AcousticBrainz',begin+len(batch),'/',len(ids),round(time.monotonic()-start),flush=True)
        if time.monotonic()-start>3600:break
    write_json(MUSIC/'audio_acquisition.json',{'planned_recording_ids':len(ids),'maximum_batch_ids':BATCH,
        'errors':errors,'seconds':time.monotonic()-start,'license':'CC0','license_url':'https://acousticbrainz.org/',
        'selection':'all retained single-observed-candidate MBIDs; first submission offset 0; no feature-based selection',
        'collection_ended':'2022','no_audio_downloaded':True})


def lookup(body,path):
    for part in path.split('.'):
        if not isinstance(body,dict) or part not in body:return None
        body=body[part]
    if isinstance(body,(int,float)) and not np.isfinite(body):raise ValueError('Nonfinite acoustic feature')
    return body


def accept(body,recording_id,artist_ids,duration):
    tags=body.get('metadata',{}).get('tags',{})
    if set(tags.get('musicbrainz_recordingid',[]))!={recording_id}:return 'recording_tag_mismatch'
    if not artist_ids or set(tags.get('musicbrainz_artistid',[]))!=set(artist_ids):return 'artist_tag_mismatch_or_missing'
    seconds=lookup(body,'metadata.audio_properties.length')
    if seconds is None or not np.isfinite(duration):return 'duration_evidence_missing'
    if abs(seconds-duration)>max(2.,duration*.02):return 'duration_disagrees_review_required'
    return 'exact_mbid_credit_duration_consistent_edition_unverified'


def summarize():
    records={kind:{} for kind in ['count','low-level','high-level']};sources={};queried={kind:set() for kind in records};review=[]
    for kind in records:
        for path in sorted((LOCAL/'acousticbrainz'/kind).glob('*.json')):
            if '.provenance.' in path.name:continue
            meta=json.loads(path.with_name(path.name+'.provenance.json').read_text())
            if sha(path)!=meta['sha256']:raise ValueError('Changed acoustic input')
            queried[kind].update(parse_qs(urlsplit(meta['url']).query)['recording_ids'][0].split(';'))
            for eid,data in json.loads(path.read_text()).items():
                if eid=='mbid_mapping':continue
                if eid in records[kind]:raise ValueError('Repeated audio recording in batches')
                records[kind][eid]=data if kind=='count' else data.get('0')
                sources[kind,eid]=dict(meta,source_file=str(path.relative_to(ROOT)))
    songs=pd.read_csv(ROOT/'data/public/songs.csv').set_index('song_id')
    meta=pd.read_csv(LOCAL/'metadata_features.csv.xz',keep_default_na=False);rows=[];provenance=[]
    for r in meta.to_dict('records'):
        out={'song_id':r['song_id'],'audio_mapping_status':'no_unique_approved_recording'}
        ids=json.loads(r['mb_v2_recording_ids']) if r['mb_v2_recording_ids'] else []
        if len(ids)==1 and r['mb_v2_recording_mapping_status']=='single_observed_candidate':
            eid=ids[0];body=records['low-level'].get(eid);out['audio_recording_id']=eid
            out['audio_mapping_status']='no_lowlevel_response' if eid in queried['low-level'] else 'not_retrieved'
            if body:
                artists=json.loads(r['mb_v2_artist_ids']) if r['mb_v2_artist_ids'] else []
                status=accept(body,eid,artists,songs.loc[r['song_id'],'mb_duration_median_seconds'])
                out['audio_mapping_status']=status
                out['audio_submission_count']=records['count'].get(eid,{}).get('count')
                out['audio_source_retrieved_at']=sources['low-level',eid]['retrieval_date']
                if not status.startswith('exact_'):
                    review.append({'song_id':r['song_id'],'recording_id':eid,'status':status,'expected_artist_ids':artists,
                        'tag_artist_ids':body.get('metadata',{}).get('tags',{}).get('musicbrainz_artistid',[]),
                        'expected_duration_seconds':songs.loc[r['song_id'],'mb_duration_median_seconds'],
                        'audio_duration_seconds':lookup(body,'metadata.audio_properties.length'),
                        'raw_sha256':sources['low-level',eid]['sha256'],'source_url':sources['low-level',eid]['url']})
                if status.startswith('exact_'):
                    tags=body.get('metadata',{}).get('tags',{})
                    for key,tag in [('label_set','label'),('media_set','media'),('release_ids','musicbrainz_albumid'),
                                    ('releasegroup_ids','musicbrainz_releasegroupid'),('catalog_language_set','language')]:
                        value=tags.get(tag,[])
                        if not isinstance(value,list):raise ValueError('Acoustic tag must be a list')
                        out['audio_tag_'+key]=sorted({x for x in value if isinstance(x,str) and x}) or None
                    for field,(path,unit) in SCALARS.items():out[field]=lookup(body,path)
                    for family in ['mfcc','gfcc']:
                        vector=lookup(body,'lowlevel.'+family+'.mean')
                        if vector is not None:
                            if len(vector)!=13 or not np.isfinite(vector).all():raise ValueError('Unexpected cepstral vector')
                            for i,value in enumerate(vector):out[f'audio_{family}_{i:02d}_mean']=value
                    contrast=lookup(body,'lowlevel.spectral_contrast_coeffs.mean')
                    if contrast is not None:
                        if len(contrast)!=6 or not np.isfinite(contrast).all():raise ValueError('Unexpected contrast vector')
                        for i,value in enumerate(contrast):out[f'audio_spectral_contrast_{i:02d}_mean']=value
                    beats=lookup(body,'rhythm.beats_position')
                    if beats is not None and len(beats)>=4:
                        gaps=np.diff(beats)
                        if (gaps<=0).any():raise ValueError('Non-increasing beat times')
                        out['audio_beat_interval_cv']=float(np.std(gaps,ddof=1)/np.mean(gaps))
                    high=records['high-level'].get(eid)
                    if high:
                        for classifier,label in HIGH.items():out['audio_model_'+classifier+'_probability']=lookup(high,'highlevel.'+classifier+'.all.'+label)
                    out['audio_extractor_version']=json.dumps(body.get('metadata',{}).get('version',{}),sort_keys=True)
                    provenance.append({'song_id':r['song_id'],'recording_id':eid,'offset':0,'mapping_status':status,
                        'sources':{kind:sources[kind,eid] for kind in records if (kind,eid) in sources},
                        'lowlevel_version':body.get('metadata',{}).get('version',{}),
                        'highlevel_version':high.get('metadata',{}).get('version',{}) if high else {},
                        'submission_measurement_date':None,'original_chart_edition_verified':False})
        rows.append(out)
    write_csv(LOCAL/'audio_features.csv.xz',rows);write_json(LOCAL/'audio_provenance.json.gz',provenance)
    write_csv(LOCAL/'audio_review_queue.csv.xz',review)
    frame=pd.DataFrame(rows)
    write_json(MUSIC/'audio_coverage.json',{'songs':len(frame),'statuses':frame.audio_mapping_status.value_counts().to_dict(),
        'feature_nonnull':frame.notna().sum().to_dict(),'submission_rule':'earliest offset 0, no cherry-picking',
        'temporal_availability':'retrospective 2015-2022 collection; not an original historical recording measurement'})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['acquire','summarize']);a=p.parse_args()
    acquire() if a.action=='acquire' else summarize()
