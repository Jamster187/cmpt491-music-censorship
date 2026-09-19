"""Resumable study-only MusicBrainz acquisition using the approved asset matcher."""
import argparse
import hashlib
import json
import shutil
import time
from collections import Counter
from pathlib import Path

from metadata_match import artist_credit, comparison_key, search_queries
from musicbrainz import APIError, MusicBrainzClient, utc_now, write_json
from musicbrainz_asset_match import VERSION
from phase2ar import read_cache, replay_song
from research import ROOT, connect, sha

CACHE = ROOT / "data/cache/musicbrainz_production"
RESULTS = ROOT / "data/processed/metadata_results"
SEED = ROOT / "data/cache/musicbrainz/requests"


class BudgetReached(Exception):
    pass


def response_record(path):
    envelope=json.loads(Path(path).read_text())
    key=hashlib.sha256(envelope['url'].encode()).hexdigest()
    if key!=envelope['cache_key'] or Path(path).stem!=key:
        raise APIError('Cache key/URL mismatch',key)
    attempt=envelope['attempts'][-1]
    if attempt['status']!=200 or attempt.get('error'):
        raise APIError('Cached request unsuccessful',key)
    if hashlib.sha256(attempt['body'].encode()).hexdigest()!=attempt['body_sha256']:
        raise APIError('Cache body checksum mismatch',key)
    return {'provider':'MusicBrainz','cache_key':key,'url':envelope['url'],
            'retrieved_at':attempt['received_at'],'body_sha256':attempt['body_sha256'],
            'payload':json.loads(attempt['body'])}


class ProductionClient(MusicBrainzClient):
    def __init__(self,*args,max_seconds=0,**kwargs):
        super().__init__(*args,**kwargs)
        self.deadline=time.monotonic()+max_seconds if max_seconds else float('inf')

    def _wait(self):
        remaining=self.deadline-time.monotonic()
        if remaining<=0 or max(0,self.next_allowed-self.clock())>remaining:
            raise BudgetReached()
        super()._wait()

    def get(self,entity,**params):
        if time.monotonic()>=self.deadline:
            raise BudgetReached()
        key=hashlib.sha256(self.request_url(entity,params).encode()).hexdigest()
        path=self.cache_dir/'requests'/(key+'.json')
        if path.exists():
            envelope=json.loads(path.read_text())
            if envelope['attempts'][-1]['status']==200 and not envelope['attempts'][-1].get('error'):
                response_record(path)
        return super().get(entity,**params)


def acquire(song,client,entities):
    responses={r['cache_key']:r for r in entities.values()}
    searches=[]
    for query in search_queries(song):
        payload,key=client.get('recording',query=query,limit=100,offset=0)
        if not isinstance(payload.get('recordings'),list) or type(payload.get('count')) is not int:
            raise APIError('Unexpected recording search schema',key)
        if any(not r.get('id') for r in payload['recordings']):
            raise APIError('Recording missing ID',key)
        responses[key]=response_record(client.cache_dir/'requests'/(key+'.json'))
        searches.append({'query':query,'count':payload['count'],'returned':len(payload['recordings']),'cache_key':key})
        # Preserve the original Phase 2A retrieval stop rule; all candidates are
        # decided by Phase 2A-R, not the original unique-recording matcher.
        if any(comparison_key(r.get('title',''))==comparison_key(song['title']) and
               comparison_key(artist_credit(r),True)==comparison_key(song['artist'],True) for r in payload['recordings']):
            break
    old={'searches':searches,'status':'not_attempted','reason':'production_retrieval'}
    result=replay_song(song,old,responses,entities)
    result['processed_at']=utc_now()
    result['production_method']='approved-asset-search-pass-v1'
    # Full response bodies already reside in the cache. Do not replicate every
    # raw candidate and release list in each decision file.
    result.pop('raw_candidate_variants')
    result.pop('phase2a_status')
    result.pop('phase2a_reason')
    result.pop('newly_accepted')
    return result


def project_entities(result):
    """Every returned tag/genre stays raw, with an explicit entity scope."""
    projected={}
    def add(kind,obj,reference,role):
        eid=obj.get('id')
        if not eid:
            return
        fields={k:v for k,v in obj.items() if k in (
            'id','title','name','sort-name','type','disambiguation','artist-credit','length',
            'first-release-date','date','status','country','text-representation','isrcs',
            'genres','tags','primary-type','secondary-types','life-span','aliases')}
        if kind=='recording':
            fields['artist-credit']=[{'name':p.get('name',p.get('artist',{}).get('name')), 'joinphrase':p.get('joinphrase',''),
                                     'artist_id':p.get('artist',{}).get('id')} if isinstance(p,dict) else p for p in obj.get('artist-credit',[])]
        item=projected.setdefault((kind,eid),{'variants':[], 'provenance':[], 'role':role})
        if fields not in item['variants']:
            item['variants'].append(fields)
        if reference not in item['provenance']:
            item['provenance'].append(reference)
    for m in result.get('metadata_evidence',[]):
        obj=m['raw']; kind=m['level']
        ref={k:m[k] for k in ('cache_key','retrieved_at','response_kind')}
        add(kind,obj,ref,'supports_asset' if kind=='recording' else 'context')
        if kind=='recording':
            for p in obj.get('artist-credit',[]):
                if isinstance(p,dict):
                    add('artist',p.get('artist',{}),ref,'credited_artist')
            for release in obj.get('releases',[]):
                add('release',release,ref,'release_manifestation')
                add('release-group',release.get('release-group',{}),ref,'release_context')
    return projected


def persist(conn,result,directory=RESULTS):
    sid=result['song']['song_id']
    member=conn.execute('SELECT s.title,s.artist FROM songs s JOIN study_population p USING(song_id) WHERE song_id=?',(sid,)).fetchone()
    if member!=(result['song']['title'],result['song']['artist']):
        raise ValueError('Refusing identity change or non-study enrichment')
    status=result['asset_match_status']
    if status!='high_confidence' and result.get('metadata_evidence'):
        raise ValueError('Unaccepted metadata cannot become accepted links')
    projected=project_entities(result)
    evidence={k:v for k,v in result.items() if k not in ('metadata_evidence',)}
    evidence['entity_links']=[{'entity_type':k,'entity_id':i} for k,i in sorted(projected)]
    # Content-addressed decisions make file publication + SQLite commit safe:
    # interruptions can leave an unused evidence file, never a mismatched pointer.
    serialized=json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    checksum=hashlib.sha256(serialized.encode()).hexdigest()
    path=Path(directory)/(sid+'_'+checksum+'.json')
    if not path.exists():
        write_json(path,evidence)
    if sha(path)!=checksum:
        raise ValueError('Persisted metadata evidence checksum differs')
    with conn:
        conn.execute('DELETE FROM song_external_links WHERE song_id=?',(sid,))
        for (kind,eid),data in projected.items():
            existing=conn.execute('SELECT metadata_json,provenance_json FROM external_entities WHERE provider=? AND entity_type=? AND entity_id=?',('MusicBrainz',kind,eid)).fetchone()
            variants=data['variants']; provenance=data['provenance']
            if existing:
                variants=json.loads(existing[0])+[v for v in variants if v not in json.loads(existing[0])]
                provenance=json.loads(existing[1])+[v for v in provenance if v not in json.loads(existing[1])]
            conn.execute('INSERT INTO external_entities VALUES (?,?,?,?,?) ON CONFLICT(provider,entity_type,entity_id) DO UPDATE SET metadata_json=excluded.metadata_json,provenance_json=excluded.provenance_json',
                         ('MusicBrainz',kind,eid,json.dumps(variants,ensure_ascii=False,sort_keys=True),json.dumps(provenance,sort_keys=True)))
            conn.execute('INSERT INTO song_external_links VALUES (?,?,?,?,?)',(sid,'MusicBrainz',kind,eid,data['role']))
        compact={k:result.get(k) for k in ('canonical_recording_status','supporting_recording_ids','supporting_artist_ids','review_flags','cached_identity_conflicts','error_cache_key')}
        conn.execute('INSERT INTO metadata_matches VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(song_id) DO UPDATE SET match_status=excluded.match_status,reason=excluded.reason,matcher_version=excluded.matcher_version,result_path=excluded.result_path,result_sha256=excluded.result_sha256,processed_at=excluded.processed_at,evidence_json=excluded.evidence_json',
                     (sid,'MusicBrainz',status,result['reason'],VERSION,str(path.relative_to(ROOT)),checksum,result['processed_at'],json.dumps(compact,sort_keys=True)))


def queue(conn,retry_errors=False):
    conn.row_factory=__import__('sqlite3').Row
    rows=[dict(r) for r in conn.execute('SELECT s.* FROM songs s JOIN study_population p USING(song_id) LEFT JOIN metadata_matches m USING(song_id) WHERE m.song_id IS NULL'+(" OR m.match_status='error'" if retry_errors else ''))]
    conn.row_factory=None
    # Round-robin across first-chart years, modern years first; no era is starved.
    groups={}
    for song in rows:
        groups.setdefault(song['first_chart_date'][:4],[]).append(song)
    for values in groups.values():
        values.sort(key=lambda s:hashlib.sha256(('production-metadata-v1'+s['song_id']).encode()).hexdigest())
    return [groups[y][i] for i in range(max((len(v) for v in groups.values()),default=0)) for y in sorted(groups,reverse=True) if i<len(groups[y])]


def run(args):
    conn=connect()
    run_id='musicbrainz-'+utc_now().replace(':','-')
    params=vars(args).copy()
    with conn:
        conn.execute('INSERT INTO acquisition_runs VALUES (?,?,?,?,?,?,?)',(run_id,'MusicBrainz',utc_now(),None,'running',json.dumps(params,sort_keys=True),'{}'))
    completed=0; errors=0; finish='complete'
    CACHE.mkdir(parents=True,exist_ok=True)
    try:
        # A distinct cache protects frozen pilot artifacts; seed responses are
        # verified, copied once, and then reused by the ordinary cached client.
        _,entities,_=read_cache(SEED)
        with ProductionClient(CACHE,offline=args.offline,retry_errors=args.retry_errors,max_seconds=args.max_seconds) as client:
            target=CACHE/'requests'; target.mkdir(exist_ok=True)
            for path in sorted(SEED.glob('*.json')):
                if not (target/path.name).exists():
                    shutil.copyfile(str(path),str(target/path.name))
            songs=queue(conn,args.retry_errors)
            if args.import_pilot:
                pilot_ids={json.loads(p.read_text())['song']['song_id'] for p in (ROOT/'data/experiments/phase2ar/results').glob('*.json')}
                songs=[s for s in songs if s['song_id'] in pilot_ids]
            for song in songs:
                if args.max_songs and completed>=args.max_songs:
                    finish='song_limit'; break
                try:
                    result=acquire(song,client,entities)
                except APIError as exc:
                    result={'song':song,'asset_match_status':'error','reason':'api_or_cache_error',
                            'error':str(exc),'error_cache_key':exc.cache_key,'processed_at':utc_now(),'matcher_version':VERSION}
                persist(conn,result)
                completed+=1
                errors=errors+1 if result['asset_match_status']=='error' else 0
                print(json.dumps({'processed_this_run':completed,'song_id':song['song_id'],'status':result['asset_match_status'],
                                  'network_requests':client.network_requests,'cache_hits':client.cache_hits}),flush=True)
                if errors>=3:
                    finish='three_consecutive_errors'; break
            stats={'processed_this_run':completed,'network_requests':client.network_requests,'cache_hits':client.cache_hits}
    except BudgetReached:
        finish='time_budget'; stats={'processed_this_run':completed,'network_requests':client.network_requests,'cache_hits':client.cache_hits}
    except KeyboardInterrupt:
        finish='interrupted'; stats={'processed_this_run':completed}
    except Exception:
        with conn:
            conn.execute('UPDATE acquisition_runs SET finished_at=?,status=? WHERE run_id=?',(utc_now(),'failed',run_id))
        raise
    with conn:
        conn.execute('UPDATE acquisition_runs SET finished_at=?,status=?,summary_json=? WHERE run_id=?',(utc_now(),finish,json.dumps(stats,sort_keys=True),run_id))
    print('Run finished:',finish,stats,flush=True)
    conn.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--import-pilot',action='store_true',help='Replay only existing pilot members of the actual study population')
    parser.add_argument('--retry-errors',action='store_true')
    parser.add_argument('--max-songs',type=int,default=0,help='0 means all remaining study songs')
    parser.add_argument('--max-seconds',type=int,default=0,help='0 means no time limit; stops safely before a request')
    run(parser.parse_args())
