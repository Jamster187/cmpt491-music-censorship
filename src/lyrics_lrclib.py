"""LRCLIB pilot only. Private responses/state; never writes research.db during acquisition."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'lrclib-pilot-v1'
USER_AGENT = 'CMPT491-LyricsPilot/1.0 (https://github.com/Jamster187/cmpt491-music-censorship)'
PERIODS = [(1958,1969,'1958–1969'),(1970,1979,'1970s'),(1980,1989,'1980s'),
           (1990,1999,'1990s'),(2000,2009,'2000s'),(2010,2019,'2010–2019'),
           (2015,2019,'2015–2019'),(2020,2026,'2020–2026')]


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('Symlink output refused')
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.lyrics-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def save_json(path, obj):
    atomic(path, (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode())


def guards(root=ROOT):
    paths = ['data/lyrics/probe.txt','data/cache/lrclib/probe.json','data/processed/lyrics.db']
    for path in paths:
        subprocess.run(['git','check-ignore','-q','--',path], cwd=root, check=True)
        for p in (root/path).parents:
            if p == root: break
            if p.is_symlink(): raise ValueError('Symlink storage directory refused')
    tracked = subprocess.check_output(['git','ls-files','--','data/lyrics','data/cache','data/processed'],cwd=root)
    if tracked.strip(): raise ValueError('Private data paths contain tracked files')


def normalize(value):
    value = unicodedata.normalize('NFKD', value.casefold())
    value = ''.join(c for c in value if not unicodedata.combining(c))
    value = value.replace('&',' and ')
    value = re.sub(r"['’‘`ʼ]", '', value)
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in value).split())


def credit(value):
    # Full credit must agree: no missing guests or person-name token sorting.
    value = re.sub(r'\b(?:feat\.?|ft\.?|featuring)\s+', ' and ', value, flags=re.I)
    value = re.sub(r'[,;&]|\s+[xX]\s+', ' and ', value)
    return tuple(sorted(normalize(p) for p in re.split(r'\band\b', value, flags=re.I) if normalize(p)))


def lyrics_text(candidate):
    plain = candidate.get('plainLyrics')
    if not plain and candidate.get('syncedLyrics'):
        plain = re.sub(r'\[[^\]\n]*\]', '', candidate['syncedLyrics'])
    if not isinstance(plain,str): return None
    plain = plain.replace('\r\n','\n').strip()
    if len(plain.split()) < 8 or '<html' in plain.casefold() or '\x00' in plain:
        return None
    return plain+'\n'


def decide(song, candidates):
    evidence=[]; eligible=[]
    durations=song['metadata']['durations']
    albums={normalize(x) for x in song['metadata']['albums']}
    for c in candidates:
        same_title=normalize(c['trackName'])==normalize(song['title'])
        same_artist=credit(c['artistName'])==credit(song['artist'])
        # Preserve version descriptors, including album-only warnings.
        flags=set(re.findall(r'\b(?:live|remix|clean|explicit|edited|karaoke|instrumental|medley)\b',
                             normalize(c['trackName']+' '+(c.get('albumName') or ''))))
        expected=set(re.findall(r'\b(?:live|remix|clean|explicit|edited|karaoke|instrumental|medley)\b',normalize(song['title'])))
        delta=min((abs(c['duration']-d) for d in durations),default=None) if isinstance(c.get('duration'),(int,float)) else None
        item={'id':c['id'],'matched_title':c['trackName'],'matched_artist':c['artistName'],
              'album':c.get('albumName'),'duration':c.get('duration'), 'title_equal':same_title,
              'artist_equal':same_artist,'version_flags':sorted(flags-expected),
              'duration_delta':delta,'duration_support':delta is not None and delta<=2,
              'album_support':normalize(c.get('albumName') or '') in albums,
              'instrumental':bool(c.get('instrumental')), 'usable_text':lyrics_text(c) is not None}
        evidence.append(item)
        if same_title and same_artist: eligible.append((c,item))
    base={'candidates':evidence,'candidate_count':len(candidates),'possible_truncation':len(candidates)>=20}
    if not candidates: return dict(base,status='not_found',reason='No search candidates',selected=None)
    if not eligible: return dict(base,status='ambiguous',reason='No candidate agrees with full title and artist credit',selected=None)
    safe=[(c,e) for c,e in eligible if not e['version_flags'] and not c.get('instrumental') and e['usable_text']]
    if not safe: return dict(base,status='ambiguous',reason='Identity candidates have version/instrumental/empty-text warnings',selected=None)
    # A short/long alternate recording does not veto the asset, but cannot supply its text.
    safe=[(c,e) for c,e in safe if e['duration_delta'] is None or e['duration_delta']<=15]
    if not safe: return dict(base,status='ambiguous',reason='All eligible durations differ from available metadata by >15 seconds',selected=None)
    groups={normalize(lyrics_text(c)) for c,e in safe}
    if len(groups)>1: return dict(base,status='ambiguous',reason='Conflicting lyric texts for matching identity',selected=None)
    c,e=sorted(safe,key=lambda ce:(not ce[1]['duration_support'],not ce[1]['album_support'],ce[0]['id']))[0]
    return dict(base,status='success',reason='Full normalized title/credit agreement; one unflagged text group',selected=c['id'])


def snapshot():
    from lyrics_plan import select, VERSION as SELECTION_VERSION
    c=sqlite3.connect((ROOT/'data/processed/research.db').as_uri()+'?mode=ro',uri=True,timeout=2)
    c.row_factory=sqlite3.Row
    try:
        songs=[dict(r) for r in c.execute('SELECT s.song_id,s.title,s.artist,s.first_chart_date FROM songs s JOIN study_population p USING(song_id)')]
        selected=select(songs)
        frozen=[tuple(r) for r in c.execute('SELECT song_id,period,selection_order,selection_version FROM lyrics_pilot ORDER BY selection_order')]
        if frozen!=[(s['song_id'],s['period'],i,SELECTION_VERSION) for i,s in enumerate(selected,1)]:
            raise ValueError('Frozen study pilot mismatch')
        if json.loads((ROOT/'data/processed/lyrics_pilot.json').read_text())['songs']!=selected:
            raise ValueError('Frozen JSON pilot mismatch')
        for s in selected:
            entities=[]
            for r in c.execute("SELECT e.entity_type,e.entity_id,e.metadata_json,e.provenance_json FROM song_external_links l JOIN external_entities e ON e.provider=l.provider AND e.entity_type=l.entity_type AND e.entity_id=l.entity_id JOIN metadata_matches m ON m.song_id=l.song_id WHERE l.song_id=? AND m.match_status='high_confidence' AND e.provider='MusicBrainz' AND e.entity_type IN ('recording','release','release-group')",(s['song_id'],)):
                entities.append(dict(r))
            durations=set(); albums=set(); dates=set()
            for e in entities:
                for v in json.loads(e['metadata_json']):
                    if e['entity_type']=='recording' and isinstance(v.get('length'),(int,float)) and v['length']>0:
                        durations.add(v['length']/1000)
                    if e['entity_type'] in ('release','release-group') and v.get('title'): albums.add(v['title'])
                    if v.get('date') or v.get('first-release-date'): dates.add(v.get('date') or v['first-release-date'])
            s['metadata']={'durations':sorted(durations),'albums':sorted(albums),'dates':sorted(dates),'entities':entities}
        return selected
    finally: c.close()


class Client:
    def __init__(self, root=ROOT, user_agent=USER_AGENT):
        self.root=root; self.cache=root/'data/cache/lrclib'; self.requests=0
        self.user_agent=user_agent
        self.cache.mkdir(parents=True,exist_ok=True)
        self.clock=self.cache/'cooldown.json'

    def search(self, params):
        url='https://lrclib.net/api/search?'+urllib.parse.urlencode(sorted(params.items()))
        path=self.cache/(digest(url.encode())+'.json')
        if path.exists():
            record=json.loads(path.read_text())
            if record['url']!=url or digest(record['body'].encode())!=record['sha256']: raise ValueError('Cache integrity failed')
            return record
        for attempt in range(3):
            until=json.loads(self.clock.read_text())['until'] if self.clock.exists() else 0
            while True:
                remaining=until-time.time()
                if remaining<=0: break
                time.sleep(min(1,remaining))
            start=time.time(); code=None
            try:
                req=urllib.request.Request(url,headers={'User-Agent':self.user_agent,'Accept':'application/json'})
                self.requests+=1
                with urllib.request.urlopen(req,timeout=30) as response:
                    code=response.status; body=response.read().decode('utf-8'); headers=dict(response.headers)
            except urllib.error.HTTPError as ex:
                code=ex.code;body=ex.read().decode('utf-8',errors='replace');headers=dict(ex.headers)
            except (urllib.error.URLError,TimeoutError,OSError) as ex:
                body=json.dumps({'error':type(ex).__name__,'message':str(ex)});headers={}
            retry=0.5
            raw=headers.get('Retry-After',headers.get('retry-after'))
            if code==429 or raw is not None:
                raw=raw or '60'
                try: retry=max(0.5,float(raw))
                except ValueError:
                    try: retry=max(0.5,parsedate_to_datetime(raw).timestamp()-time.time())
                    except (ValueError,TypeError,OverflowError): retry=60
            elif code is None or code>=500: retry=2**(attempt+1)
            save_json(self.clock,{'until':time.time()+retry})
            record={'url':url,'status':code,'body':body,'sha256':digest(body.encode()),'retrieved_at':stamp(),
                    'seconds':time.time()-start,'user_agent':self.user_agent,'retry_after':raw}
            # Preserve every attempt without putting raw lyrics into tracked locations.
            save_json(self.cache/(path.stem+'-attempt-'+str(time.time_ns())+'.json'),record)
            if code==200 or (code is not None and code<500 and code!=429): break
        save_json(path,record)
        return record


def parse(record):
    if record['status']!=200: raise ValueError('LRCLIB HTTP '+str(record['status']))
    rows=json.loads(record['body'])
    if not isinstance(rows,list): raise ValueError('Search response must be an array')
    for r in rows:
        if not isinstance(r,dict) or not isinstance(r.get('id'),int) or not all(isinstance(r.get(k),str) for k in ('trackName','artistName')):
            raise ValueError('Unsupported LRCLIB candidate schema')
        for k in ('plainLyrics','syncedLyrics'):
            if r.get(k) is not None and not isinstance(r[k],str): raise ValueError('Unsupported lyric field type')
    return rows


def database(root=ROOT):
    c=sqlite3.connect(root/'data/processed/lyrics.db')
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS results (song_id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    return c


def persist(c, result, text=None, root=ROOT):
    if text is not None:
        path=root/'data/lyrics'/(result['song_id']+'.txt')
        data=text.encode(); result['lyrics_sha256']=digest(data)
        result['lyrics_path']=str(path.relative_to(root))
        if path.exists() and (path.is_symlink() or path.read_bytes()!=data):
            raise ValueError('Refuse to overwrite differing existing lyrics')
        if not path.exists(): atomic(path,data)
    with c:
        c.execute('INSERT INTO results VALUES (?,?) ON CONFLICT(song_id) DO UPDATE SET payload=excluded.payload',
                  (result['song_id'],json.dumps(result,ensure_ascii=False,sort_keys=True)))


def validate(c, root=ROOT):
    songs=json.loads(c.execute("SELECT value FROM settings WHERE key='pilot'").fetchone()[0])
    ids={s['song_id'] for s in songs}; expected=set()
    for sid,payload in c.execute('SELECT * FROM results'):
        r=json.loads(payload)
        if sid not in ids or r['song_id']!=sid: raise ValueError('Nonpilot result')
        if r['status']=='success':
            path=root/'data/lyrics'/(sid+'.txt'); expected.add(path)
            if path.is_symlink() or r['lyrics_path']!=str(path.relative_to(root)) or digest(path.read_bytes())!=r['lyrics_sha256']:
                raise ValueError('Lyrics file integrity failed')
    actual=set((root/'data/lyrics').glob('*.txt'))
    if actual!=expected: raise ValueError('Unmanifested/missing canonical lyrics')
    return len(expected)


def run():
    guards(); c=database()
    existing=c.execute("SELECT value FROM settings WHERE key='pilot'").fetchone()
    if existing: songs=json.loads(existing[0])
    else:
        songs=snapshot()
        with c:
            c.executemany('INSERT INTO settings VALUES (?,?)',[
                ('pilot',json.dumps(songs,ensure_ascii=False,sort_keys=True)),('version',VERSION),
                ('started_at',stamp()),('code_sha256',digest(Path(__file__).read_bytes())),
                ('runtime',sys.version),('unicode_version',unicodedata.unidata_version),
                ('authorization','User authorized local-only 200-song LRCLIB technical pilot; full population prohibited')])
    if len(songs)!=200 or len({s['song_id'] for s in songs})!=200: raise ValueError('Pilot must have exactly 200 assets')
    if c.execute("SELECT value FROM settings WHERE key='version'").fetchone()[0]!=VERSION: raise ValueError('Version mismatch')
    client=Client()
    for i,s in enumerate(songs,1):
        old=c.execute('SELECT payload FROM results WHERE song_id=?',(s['song_id'],)).fetchone()
        if old: continue
        records=[]; candidates=[]
        try:
            record=client.search({'track_name':s['title'],'artist_name':s['artist']});records.append(record)
            candidates=parse(record)
            # A title-only fallback can recover formatting differences without guessing artists.
            if not candidates:
                record=client.search({'track_name':s['title']});records.append(record);candidates=parse(record)
            decision=decide(s,candidates)
        except (ValueError,KeyError,TypeError) as ex:
            decision={'status':'error','reason':str(ex),'selected':None,'candidates':[]}
        result=dict(s,**decision,source='LRCLIB',matcher_version=VERSION,processed_at=stamp(),
                    retrievals=[{k:v for k,v in r.items() if k!='body'} for r in records],
                    lyrics_path=None,lyrics_sha256=None,review_status='pending')
        chosen=next((x for x in candidates if x['id']==decision['selected']),None)
        result['matched']=({k:chosen.get(k) for k in ('id','trackName','artistName','albumName','duration','instrumental')} if chosen else None)
        persist(c,result,lyrics_text(chosen) if chosen else None)
        print(json.dumps({'completed':i,'status':result['status'],'title':s['title'],'requests_this_run':client.requests}),flush=True)
    validate(c)
    with c: c.execute("INSERT OR IGNORE INTO settings VALUES ('finished_at',?)",(stamp(),))
    c.close()


def summary():
    c=database();validate(c)
    rows=[json.loads(p) for p, in c.execute('SELECT payload FROM results')]
    result={'attempted':len(rows),'counts':dict(Counter(r['status'] for r in rows)),'periods':[]}
    for lo,hi,label in PERIODS:
        group=[r for r in rows if lo<=int(r['first_chart_date'][:4])<=hi]
        result['periods'].append({'period':label,'attempted':len(group),'counts':dict(Counter(r['status'] for r in group)),
                                  'usable_percent':round(100*sum(r['status']=='success' for r in group)/len(group),2) if group else None})
    print(json.dumps(result,ensure_ascii=False,indent=2));c.close()


def import_results():
    """Explicit later import only, after metadata acquisition stops; one all-or-nothing transaction."""
    guards(); local=database();validate(local)
    rows=[json.loads(p) for p, in local.execute('SELECT payload FROM results ORDER BY song_id')];local.close()
    c=sqlite3.connect((ROOT/'data/processed/research.db').as_uri()+'?mode=rw',uri=True,timeout=0)
    c.execute('PRAGMA foreign_keys=ON')
    try:
        c.execute('BEGIN IMMEDIATE')
        for r in rows:
            s=c.execute('SELECT title,artist FROM songs JOIN lyrics_pilot USING(song_id) WHERE song_id=?',(r['song_id'],)).fetchone()
            if s!=(r['title'],r['artist']): raise ValueError('Import identity mismatch')
            old=c.execute('SELECT lyrics_status,lyrics_sha256 FROM lyrics_manifest WHERE song_id=?',(r['song_id'],)).fetchone()
            if old is None: raise ValueError('Missing manifest row')
            if old[0]=='success' and old[1]!=r['lyrics_sha256']: raise ValueError('Existing success conflicts')
            matched=r['matched'] or {}
            c.execute('UPDATE lyrics_manifest SET lyrics_status=?,lyrics_source=?,source_identifier=?,match_status=?,matched_title=?,matched_artist=?,lyrics_path=?,lyrics_sha256=?,retrieved_at=?,failure_reason=?,provenance_json=? WHERE song_id=?',
                      (r['status'],'LRCLIB',str(matched['id']) if matched else None,'high_confidence' if r['status']=='success' else r['status'],matched.get('trackName'),matched.get('artistName'),r['lyrics_path'],r['lyrics_sha256'],r['retrievals'][-1]['retrieved_at'] if r['retrievals'] else r['processed_at'],None if r['status']=='success' else r['reason'],json.dumps(r,ensure_ascii=False,sort_keys=True),r['song_id']))
        c.commit()
    except BaseException:
        c.rollback();raise
    finally: c.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['run','summary','validate','import'])
    parser.add_argument('--metadata-stopped',action='store_true',help='Operator confirms metadata writer has stopped; required for import')
    args=parser.parse_args()
    if args.command=='import' and not args.metadata_stopped: parser.error('Stop metadata writer before using import --metadata-stopped')
    (ROOT/'data/processed').mkdir(parents=True,exist_ok=True)
    with (ROOT/'data/processed/lyrics.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.command=='run': run()
        elif args.command=='summary': summary()
        elif args.command=='validate':
            c=database();print('Validated successful files:',validate(c));c.close()
        else: import_results()
