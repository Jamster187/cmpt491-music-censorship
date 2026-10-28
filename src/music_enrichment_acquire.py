"""Bounded, restartable MusicBrainz core-data acquisition on retained exact IDs."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from urllib.error import HTTPError
from urllib.parse import urlencode

import pandas as pd

from enrichment_common import ROOT, LOCAL, MUSIC, fetch, sha, write_json, write_csv

INCLUDE='artist-credits+isrcs+releases+release-groups+artist-rels+work-rels+work-level-rels+recording-rels'


def acquire(limit=4000):
    start=time.monotonic();queue=json.loads((LOCAL/'metadata_acquisition_queue.json').read_text())
    # Original approved single-observed-candidate MBIDs. Unresolved editions are not
    # selected by title, score, or convenience. Hash order disperses a partial run.
    import hashlib
    ids=sorted(queue['single_recording_ids'],key=lambda x:hashlib.sha256(x.encode()).hexdigest())
    tasks=[('recording',i,INCLUDE) for i in ids]+[('work',i,'artist-rels') for i in queue['work_ids']]
    errors=[];success=0;attempted=0;consecutive=0;pending_tasks=[];starts=[]
    checkpoint=LOCAL/'musicbrainz_v2/checkpoint.json'
    if checkpoint.exists():
        archive=LOCAL/'musicbrainz_v2/prior_checkpoints';archive.mkdir(parents=True,exist_ok=True)
        target=archive/f'{len(list(archive.glob("*.json"))):04d}.json'
        target.write_bytes(checkpoint.read_bytes())
    for kind,eid,include in tasks:
        p=LOCAL/'musicbrainz_v2'/kind/(eid+'.json')
        if p.exists():
            meta=json.loads(p.with_name(p.name+'.provenance.json').read_text())
            if sha(p)!=meta['sha256']:raise ValueError('Changed MusicBrainz response cache')
            json.loads(p.read_text());success+=1;continue
        pending_tasks.append((kind,eid,include))
    cached_before=success;gate=threading.Lock();next_allowed=[time.monotonic()+1.1];stop=threading.Event()
    def request(task):
        kind,eid,include=task;p=LOCAL/'musicbrainz_v2'/kind/(eid+'.json')
        url='https://musicbrainz.org/ws/2/'+kind+'/'+eid+'?'+urlencode({'fmt':'json','inc':include})
        # Two requests can be in flight, but every actual start passes one gate.
        # Backoff is shared across workers. No burst is allowed after a pause.
        with gate:
            time.sleep(max(0,next_allowed[0]-time.monotonic()))
            if stop.is_set():return {'cancelled':True}
            tick=time.monotonic();next_allowed[0]=tick+1.1;starts.append(tick)
        try:
            fetch(url,p,limit=5_000_000,timeout=30)
            body=json.loads(p.read_text())
            if body.get('id')!=eid:raise ValueError('Provider returned a different MBID; quarantined')
            return {'success':True}
        except Exception as exc:
            error={'kind':kind,'entity_id':eid,'url':url,'error_type':type(exc).__name__,'message':str(exc),
                   'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat()}
            write_json(LOCAL/'musicbrainz_v2/errors'/(kind+'_'+eid+'.json'),error)
            if isinstance(exc,HTTPError) and exc.code in {401,403,429,503}:
                delay=5.
                try:delay=max(delay,float(exc.headers.get('Retry-After','5')))
                except ValueError:delay=60.
                with gate:next_allowed[0]=max(next_allowed[0],time.monotonic()+delay)
                if exc.code in {401,403,429}:stop.set()
            return {'error':error}
    selected=iter(pending_tasks[:limit]);futures={}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for task in selected:
            futures[pool.submit(request,task)]=task
            if len(futures)==2:break
        while futures:
            done,_=wait(futures,return_when=FIRST_COMPLETED)
            for future in sorted(done,key=lambda f:futures[f]):
                futures.pop(future);result=future.result()
                if result.get('cancelled'):continue
                attempted+=1
                if result.get('success'):success+=1;consecutive=0
                else:errors.append(result['error']);consecutive+=1
                if consecutive>=3:stop.set()
                if attempted%50==0 or stop.is_set():
                    status={'planned_entities':len(tasks),'cached_before':cached_before,'cached_successes':success,'requests_this_run':attempted,
                            'errors_this_run':errors,'seconds':time.monotonic()-start,'limit':limit}
                    write_json(checkpoint,status);print('MusicBrainz',attempted,success,round(time.monotonic()-start),flush=True)
                if not stop.is_set():
                    task=next(selected,None)
                    if task:futures[pool.submit(request,task)]=task
    minimum=min((b-a for a,b in zip(starts,starts[1:])),default=None)
    if minimum is not None and minimum<1.1:raise ValueError('MusicBrainz request-start rate violated')
    status={'planned_entities':len(tasks),'cached_successes':success,'requests_this_run':attempted,'errors_this_run':errors,
            'seconds':time.monotonic()-start,'limit':limit,'rate_limit':'at least 1.1 seconds between starts',
            'maximum_inflight':2,'cached_before':cached_before,'minimum_observed_start_interval_seconds':minimum,'stopped_on_errors':stop.is_set(),
            'selection':'All retained high-confidence single-observed-candidate recording IDs; unresolved editions excluded',
            'license_url':'https://musicbrainz.org/doc/MusicBrainz_Database','license':'CC0 core data'}
    write_json(MUSIC/'acquisition_summary.json',status);write_json(checkpoint,status)
    print(json.dumps({k:v for k,v in status.items() if k!='errors_this_run'},indent=2),flush=True)


def summarize():
    cached=pd.read_csv(LOCAL/'metadata_features.csv.xz',keep_default_na=False)
    rows=[];provenance=[]
    for record in cached.to_dict('records'):
        recs=json.loads(record['mb_v2_recording_ids']) if record['mb_v2_recording_ids'] else []
        r={'song_id':record['song_id']}
        if len(recs)!=1 or record['mb_v2_recording_mapping_status']!='single_observed_candidate':
            r['mb_v2_external_status']='unresolved_recording' if recs else 'no_approved_mapping';rows.append(r);continue
        eid=recs[0];p=LOCAL/'musicbrainz_v2/recording'/(eid+'.json')
        if not p.exists():r['mb_v2_external_status']='not_retrieved';rows.append(r);continue
        body=json.loads(p.read_text());meta=json.loads(p.with_name(p.name+'.provenance.json').read_text())
        if sha(p)!=meta['sha256']:raise ValueError('MusicBrainz cached response hash differs')
        old_artists=set(json.loads(record['mb_v2_artist_ids'])) if record['mb_v2_artist_ids'] else set()
        artists=[x['artist']['id'] for x in body.get('artist-credit',[]) if isinstance(x,dict) and x.get('artist',{}).get('id')]
        if body.get('id')!=eid or not artists or set(artists)!=old_artists:
            r['mb_v2_external_status']='identity_changed_review_required';rows.append(r);continue
        producers=set();writers=set();lyricists=set();composers=set();languages=set();works=set();covers=False;remixes=[];roles=[]
        for rel in body.get('relations',[]):
            if rel.get('target-type')=='artist' and rel.get('type')=='producer':producers.add(rel['artist']['id'])
            if rel.get('target-type')=='work' and rel.get('type')=='performance':
                work=rel['work'];works.add(work['id']);covers|='cover' in rel.get('attributes',[])
                languages.update(work.get('languages',[]))
                if work.get('language'):languages.add(work['language'])
                for wr in work.get('relations',[]):
                    role=wr.get('type')
                    if wr.get('target-type')=='artist' and role in {'composer','lyricist','writer'}:
                        person=wr['artist']['id'];writers.add(person)
                        if role=='composer':composers.add(person)
                        if role=='lyricist':lyricists.add(person)
                        roles.append({'work_id':work['id'],'artist_id':person,'role':role,'attributes':wr.get('attributes',[])})
            if 'remix' in rel.get('type',''):remixes.append({'type':rel['type'],'direction':rel.get('direction'),'target':rel.get('recording',{}).get('id')})
        r.update(mb_v2_external_status='exact_mbid_credit_consistent',mb_v2_external_retrieved_at=meta['retrieval_date'],
            mb_v2_external_artist_country_set=sorted({x['artist']['country'] for x in body.get('artist-credit',[]) if isinstance(x,dict) and x.get('artist',{}).get('country')}) or None,
            mb_v2_external_artist_type_set=sorted({x['artist']['type'] for x in body.get('artist-credit',[]) if isinstance(x,dict) and x.get('artist',{}).get('type')}) or None,
            mb_v2_external_isrc_set=sorted(set(body.get('isrcs',[]))) or None,
            mb_v2_external_work_ids=sorted(works) or None,mb_v2_work_language_set=sorted(languages) or None,
            mb_v2_known_writer_count=len(writers) if writers else None,mb_v2_known_composer_count=len(composers) if composers else None,
            mb_v2_known_lyricist_count=len(lyricists) if lyricists else None,mb_v2_external_producer_count=len(producers) if producers else None,
            mb_v2_external_cover_evidence=1 if covers else None,mb_v2_external_remix_relationships=remixes or None,
            mb_v2_recording_first_release_candidate=body.get('first-release-date') or None,
            mb_v2_recording_video=body.get('video'),mb_v2_external_release_list_truncated=body.get('release-count',len(body.get('releases',[])))>len(body.get('releases',[])))
        provenance.append({'song_id':record['song_id'],'recording_id':eid,'source':meta,'mapping_status':r['mb_v2_external_status'],
            'writer_roles':roles,'producer_ids':sorted(producers),'release_ids':[x['id'] for x in body.get('releases',[])],
            'original_edition_verified':False,'license':'CC0','source_file':str(p.relative_to(ROOT))})
        rows.append(r)
    write_csv(LOCAL/'external_metadata_features.csv.xz',rows);write_json(LOCAL/'external_metadata_provenance.json.gz',provenance)
    write_json(MUSIC/'external_metadata_coverage.json',{'songs':len(rows),'exact_consistent_songs':len(provenance),
        'field_counts':{k:sum(r.get(k) is not None and r.get(k)!='' for r in rows) for k in sorted(set().union(*(r.keys() for r in rows)))}})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['acquire','summarize']);parser.add_argument('--limit',type=int,default=4000);a=parser.parse_args()
    acquire(a.limit) if a.action=='acquire' else summarize()
