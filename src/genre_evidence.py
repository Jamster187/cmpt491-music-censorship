"""Offline genre-evidence inventory. Does not assign genres to the population."""
from collections import Counter,defaultdict
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/experiments/genre_pilot'
DATABASE=OUT/'evidence.db'
PERIODS=((1958,1969,'1958–1969'),(1970,1979,'1970s'),(1980,1989,'1980s'),(1990,1999,'1990s'),(2000,2009,'2000s'),(2010,2019,'2010–2019'),(2020,2026,'2020–2026'))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def ro(path):return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
def period(year):return next(label for lo,hi,label in PERIODS if lo<=int(year)<=hi)


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    if DATABASE.exists():raise ValueError('Existing inventory preserved; use its frozen evidence rather than overwrite')
    final=set(json.loads((ROOT/'data/processed/month_end_catchup/population.json').read_text())['new_population'])
    temp=OUT/'evidence.building.db'
    if temp.exists():temp.unlink()
    c=sqlite3.connect(temp)
    c.executescript('''CREATE TABLE songs(song_id TEXT PRIMARY KEY,title TEXT,artist TEXT,first_chart_date TEXT,best_rank INTEGER,weekly_rows INTEGER,period TEXT);
      CREATE TABLE links(song_id TEXT,provider TEXT,level TEXT,entity_id TEXT,identity_basis TEXT,PRIMARY KEY(song_id,provider,level,entity_id));
      CREATE INDEX entity_links ON links(provider,level,entity_id);
      CREATE TABLE evidence(provider TEXT,level TEXT,entity_id TEXT,label TEXT,field TEXT,votes INTEGER,reference TEXT,raw TEXT,
        PRIMARY KEY(provider,level,entity_id,label,field,reference));
      CREATE INDEX evidence_entity ON evidence(provider,level,entity_id);
      CREATE TABLE entity_context(provider TEXT,level TEXT,entity_id TEXT,payload TEXT,reference TEXT,PRIMARY KEY(provider,level,entity_id,reference));
      CREATE TABLE inputs(path TEXT PRIMARY KEY,sha256 TEXT);''')
    selected=defaultdict(set);wd_selected=defaultdict(set);rejected=Counter();source_files=Counter()
    def inp(path):
        h=sha(path);c.execute('INSERT OR IGNORE INTO inputs VALUES (?,?)',(str(path.relative_to(ROOT)),h));return h
    def link(sid,provider,level,eid,basis):
        c.execute('INSERT OR IGNORE INTO links VALUES (?,?,?,?,?)',(sid,provider,level,eid,basis))
    def evidence(provider,level,eid,label,field,votes,ref,raw):
        if not isinstance(label,str) or not label.strip():return
        c.execute('INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?,?,?)',(provider,level,eid,label,field,votes,ref,json.dumps(raw,ensure_ascii=False,sort_keys=True)))
    def mb_object(level,obj,ref):
        eid=obj.get('id')
        if eid not in selected[level]:return
        context={k:obj[k] for k in ('title','name','primary-type','secondary-types','artist-credit','type','disambiguation') if k in obj}
        if context:c.execute('INSERT OR IGNORE INTO entity_context VALUES (?,?,?,?,?)',('MusicBrainz',level,eid,json.dumps(context,ensure_ascii=False,sort_keys=True),ref))
        for field in ('genres','tags'):
            for tag in obj.get(field,[]):
                if isinstance(tag,dict):evidence('MusicBrainz',level,eid,tag.get('name'),field,tag.get('count',0),ref,tag)
    for path in (ROOT/'data/processed/research.db',ROOT/'data/processed/month_end_catchup/metadata.db'):
        fingerprint=inp(path)
        with closing(ro(path)) as db:
            for sid,title,artist,dt,rank,rows in db.execute('SELECT song_id,title,artist,first_chart_date,best_chart_rank,chart_observation_count FROM songs'):
                if sid in final:c.execute('INSERT OR IGNORE INTO songs VALUES (?,?,?,?,?,?,?)',(sid,title,artist,dt,rank,rows,period(dt[:4])))
            for sid,level,eid in db.execute("SELECT l.song_id,l.entity_type,l.entity_id FROM song_external_links l JOIN metadata_matches m USING(song_id) WHERE m.match_status='high_confidence' AND l.provider='MusicBrainz'"):
                if sid in final:
                    selected[level].add(eid);link(sid,'MusicBrainz',level,eid,'production_high_confidence')
            for level,eid,payload,provenance in db.execute('SELECT entity_type,entity_id,metadata_json,provenance_json FROM external_entities WHERE provider="MusicBrainz"'):
                if eid not in selected[level]:continue
                ref=json.dumps(dict(path=str(path.relative_to(ROOT)),database_sha256=fingerprint,provenance=json.loads(provenance)),sort_keys=True)
                for variant in json.loads(payload):mb_object(level,dict(variant,id=eid),ref)
        c.commit();print('Read database',path.name,flush=True)
    # Reuse exact accepted entity IDs from ALL cached MusicBrainz responses, including
    # previously unselected candidates. New name-based identities are never inferred.
    seen=set()
    for folder in (ROOT/'data/cache/musicbrainz/requests',ROOT/'data/cache/musicbrainz_production/requests'):
        for path in sorted(folder.glob('*.json')):
            d=json.loads(path.read_text());key=d['cache_key']
            if hashlib.sha256(d['url'].encode()).hexdigest()!=key or path.stem!=key:raise ValueError('MB cache key mismatch')
            for a in d['attempts']:
                if a.get('body') is not None and hashlib.sha256(a['body'].encode()).hexdigest()!=a['body_sha256']:raise ValueError('MB body mismatch')
            ok=[a for a in d['attempts'] if a['status']==200 and not a.get('error')]
            if not ok:rejected['failed_mb_cache']+=1;continue
            a=ok[-1];marker=(key,a['body_sha256'])
            if marker in seen:continue
            seen.add(marker);inp(path);source_files['MusicBrainz']+=1
            ref=json.dumps(dict(path=str(path.relative_to(ROOT)),cache_key=key,body_sha256=a['body_sha256'],retrieved_at=a['received_at'],url=d['url']),sort_keys=True)
            payload=json.loads(a['body']);parts=urlparse(d['url']).path.strip('/').split('/')
            kind=parts[2] if len(parts)>2 else ''
            if payload.get('id'):mb_object(kind,payload,ref)
            for r in payload.get('recordings',[]):
                mb_object('recording',r,ref)
                for ac in r.get('artist-credit',[]):
                    if isinstance(ac,dict):mb_object('artist',ac.get('artist',{}),ref)
                for rel in r.get('releases',[]):
                    mb_object('release',rel,ref)
                    mb_object('release-group',rel.get('release-group',{}),ref)
            if source_files['MusicBrainz']%1000==0:c.commit();print('MB caches',source_files['MusicBrainz'],flush=True)
    # Accepted Wikidata crosswalks only. Genre statements on rejected candidate
    # song items cannot silently become song evidence.
    wd_entities={}
    def remember(entity):
        eid=entity.get('id')
        if eid and entity.get('lastrevid',0)>=wd_entities.get(eid,{}).get('lastrevid',0):wd_entities[eid]=entity
    for path in sorted((ROOT/'data/experiments/phase2b/results').glob('*.json')):
        d=json.loads(path.read_text());inp(path)
        for entity in (d.get('metadata') or {}).get('referenced_entities',{}).values():remember(entity)
        if d['song']['song_id'] not in final or d['status']!='high_confidence':continue
        sid=d['song']['song_id'];meta=d['metadata'] or {}
        for key,level in (('entities','song_item'),('artists','artist'),('parents','album')):
            for ent in meta.get(key,[]):
                remember(ent)
                if level=='album' and ent['id'] not in meta.get('album_ids',[]):continue
                wd_selected[level].add(ent['id']);link(sid,'Wikidata',level,ent['id'],'archived_complete_performer_match')
    # Enumerate all Wikidata cache entities; exact P434 artist crosswalks can reuse
    # cached artist evidence for songs outside the original 200-song experiment.
    for path in sorted((ROOT/'data/cache/wikidata/requests').glob('*.json')):
        d=json.loads(path.read_text())
        if hashlib.sha256(d['url'].encode()).hexdigest()!=d['cache_key']:raise ValueError('WD cache key mismatch')
        for a in d['attempts']:
            if a.get('body') is not None and hashlib.sha256(a['body'].encode()).hexdigest()!=a['body_sha256']:raise ValueError('WD body mismatch')
        ok=[a for a in d['attempts'] if a['status']==200 and not a.get('error')]
        if not ok:rejected['failed_wd_cache']+=1;continue
        inp(path);source_files['Wikidata']+=1
        for entity in json.loads(ok[-1]['body']).get('entities',{}).values():remember(entity)
    mb_artist_songs=defaultdict(set)
    for sid,eid in c.execute("SELECT song_id,entity_id FROM links WHERE provider='MusicBrainz' AND level='artist'"):mb_artist_songs[eid].add(sid)
    def claims(ent,prop):
        return [s for s in ent.get('claims',{}).get(prop,[]) if s.get('rank')!='deprecated' and s.get('mainsnak',{}).get('snaktype')=='value']
    for eid,ent in wd_entities.items():
        for s in claims(ent,'P434'):
            if s.get('qualifiers'):continue
            mbid=s['mainsnak'].get('datavalue',{}).get('value')
            for sid in mb_artist_songs.get(mbid,()):
                wd_selected['artist'].add(eid);link(sid,'Wikidata','artist',eid,'exact_P434_to_accepted_MusicBrainz_artist')
    for level,ids in wd_selected.items():
        for eid in sorted(ids):
            ent=wd_entities[eid]
            for s in claims(ent,'P136'):
                qid=s['mainsnak'].get('datavalue',{}).get('value',{}).get('id')
                labels=wd_entities.get(qid,{}).get('labels',{})
                label=next((labels[k]['value'] for k in ('en','mul') if k in labels),None)
                ref=json.dumps(dict(entity_id=eid,revision=ent.get('lastrevid'),statement_id=s.get('id'),genre_id=qid),sort_keys=True)
                evidence('Wikidata',level,eid,label,'P136',1,ref,s)
    c.commit()
    counts={};by_period={}
    for provider,level,field in c.execute('SELECT DISTINCT provider,level,field FROM evidence'):
        ids={r[0] for r in c.execute('SELECT DISTINCT l.song_id FROM links l JOIN evidence e USING(provider,level,entity_id) WHERE e.provider=? AND e.level=? AND e.field=? AND e.votes>0',(provider,level,field))}
        counts[f'{provider}/{level}/{field}']=len(ids)
        by_period[f'{provider}/{level}/{field}']=dict(Counter(p for sid,p in c.execute('SELECT song_id,period FROM songs') if sid in ids))
    raw_labels=[dict(provider=p,level=l,label=label,songs=n) for p,l,label,n in c.execute('SELECT e.provider,e.level,e.label,count(DISTINCT l.song_id) FROM evidence e JOIN links l USING(provider,level,entity_id) WHERE votes>0 GROUP BY 1,2,3 ORDER BY 4 DESC,1,2,3')]
    summary=dict(population=len(final),source_files=dict(source_files),rejected_cache_counts=dict(rejected),raw_positive_evidence_by_level=counts,raw_positive_by_period=by_period,unique_accepted_mb_entities={k:len(v) for k,v in selected.items()},raw_label_inventory=raw_labels)
    c.close();temp.replace(DATABASE)
    (OUT/'inventory.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('raw_label_inventory','raw_positive_by_period')},indent=2))

if __name__=='__main__':build()
