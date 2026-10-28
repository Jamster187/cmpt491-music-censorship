"""Reuse approved MusicBrainz links, preserving entity level and ambiguity."""
from __future__ import annotations
from collections import Counter, defaultdict
from contextlib import closing
import gzip
import json
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlsplit

import pandas as pd

from enrichment_common import ROOT, LOCAL, MUSIC, sha, write_csv, write_json, fetch

DATABASES = [ROOT/'data/processed/research.db', ROOT/'data/processed/month_end_catchup/metadata.db']


def ro(path):
    return sqlite3.connect('file:'+str(path.resolve())+'?mode=ro', uri=True)


def cached_entities():
    """Keep raw variants and exact provenance locally; never merge song identities."""
    output=LOCAL/'metadata_entities.json.gz'
    if output.exists():
        return json.loads(gzip.decompress(output.read_bytes()))
    study=pd.read_csv(ROOT/'data/public/songs.csv', keep_default_na=False)
    wanted=set(study.loc[study.musicbrainz_match_status.eq('high_confidence'),'song_id'])
    entities={};links=defaultdict(lambda: defaultdict(list));matches={}
    for database in DATABASES:
        with closing(ro(database)) as conn:
            conn.row_factory=sqlite3.Row
            for row in conn.execute("SELECT * FROM metadata_matches WHERE match_status='high_confidence'"):
                if row['song_id'] in wanted:
                    if row['song_id'] in matches: raise ValueError('Duplicate approved metadata identity')
                    matches[row['song_id']]=dict(row)
            for row in conn.execute("""SELECT l.song_id,l.entity_type,l.entity_id,l.role FROM song_external_links l
                         JOIN metadata_matches m USING(song_id) WHERE m.match_status='high_confidence'"""):
                if row['song_id'] in wanted:
                    links[row['song_id']][row['entity_type']].append(row['entity_id'])
            keys={(kind,eid) for sid in matches for kind,ids in links[sid].items() for eid in ids}
            for row in conn.execute('SELECT entity_type,entity_id,metadata_json,provenance_json FROM external_entities'):
                key=(row['entity_type'],row['entity_id'])
                if key in keys:
                    name=':'.join(key)
                    record=entities.setdefault(name,{'variants':[], 'provenance':[]})
                    for field,column in [('variants','metadata_json'),('provenance','provenance_json')]:
                        for item in json.loads(row[column]):
                            if item not in record[field]:record[field].append(item)
        print(database.name, len(entities), 'linked entities', flush=True)
    result={'entities':entities,'links':links,'matches':matches,
            'inputs':{str(p.relative_to(ROOT)):sha(p) for p in DATABASES}}
    write_json(output,result)
    return result


def cache_details():
    """Recover work relations and core fields omitted from the published DB model."""
    output=LOCAL/'metadata_details.json.gz'
    if output.exists():return json.loads(gzip.decompress(output.read_bytes()))
    detail={};census=Counter();inputs={}
    roots=[ROOT/'data/cache/musicbrainz', ROOT/'data/cache/musicbrainz_production', ROOT/'data/processed/month_end_catchup']
    for base in roots:
        for i,path in enumerate(sorted(base.rglob('*.json'))):
            if path.name in {'rate_state.json','background-process.json'}:continue
            try:record=json.loads(path.read_text())
            except (UnicodeDecodeError,json.JSONDecodeError):continue
            if not isinstance(record,dict) or 'attempts' not in record or 'musicbrainz.org/ws/2/' not in record.get('url',''):continue
            parts=urlsplit(record['url']).path.strip('/').split('/')
            census['requests']+=1
            if len(parts)!=4:continue  # Queries have no canonical entity id.
            kind,eid=parts[2:];census['lookups_'+kind]+=1
            successes=[a for a in record['attempts'] if a.get('status')==200 and a.get('body')]
            if not successes:continue
            a=successes[-1];body=json.loads(a['body'])
            if body.get('id')!=eid:raise ValueError('Lookup response identity differs')
            # These are source responses, not filtered/accepted crosswalk decisions.
            detail[kind+':'+eid]={'data':body,'cache_path':str(path.relative_to(ROOT)),
                'source_url':record['url'],'retrieved_at':a['received_at'],'body_sha256':a['body_sha256']}
            inputs[str(path.relative_to(ROOT))]=sha(path)
            if i and i%5000==0:print('cache scan',base.name,i,len(detail),flush=True)
    result={'details':detail,'census':dict(census),'inputs':inputs}
    write_json(output,result);write_json(MUSIC/'cache_audit.json',{'census':dict(census),'lookup_entities':len(detail),
        'work_relation_recordings':sum(k.startswith('recording:') and any(r.get('target-type')=='work' for r in v['data'].get('relations',[])) for k,v in detail.items())})
    return result


def values(entities,kind,ids,field):
    result=set()
    for eid in ids:
        for row in entities.get(kind+':'+eid,{}).get('variants',[]):
            val=row.get(field)
            if isinstance(val,list):result.update(x for x in val if isinstance(x,(str,int,float)) and x!='')
            elif val not in (None,''):result.add(val)
    return sorted(result)


def extract():
    start=time.monotonic();cache=cached_entities();details=cache_details()['details'];entities=cache['entities']
    study=pd.read_csv(ROOT/'data/public/songs.csv',keep_default_na=False)
    rows=[];provenance=[];works=set();recordings=set()
    for song in study.itertuples(index=False):
        sid=song.song_id;links=cache['links'].get(sid,{})
        recs=sorted(set(links.get('recording',[])));artists=sorted(set(links.get('artist',[])))
        releases=sorted(set(links.get('release',[])));groups=sorted(set(links.get('release-group',[])))
        r={'song_id':sid,'mb_v2_recording_ids':recs or None,'mb_v2_artist_ids':artists or None,
           'mb_v2_isrc_set':values(entities,'recording',recs,'isrcs') or None,
           'mb_v2_artist_type_set':values(entities,'artist',artists,'type') or None,
           'mb_v2_artist_country_set':values(entities,'artist',artists,'country') or None,
           'mb_v2_release_group_primary_types':values(entities,'release-group',groups,'primary-type') or None,
           'mb_v2_release_group_secondary_types':values(entities,'release-group',groups,'secondary-types') or None,
           'mb_v2_release_country_set':values(entities,'release',releases,'country') or None,
           'mb_v2_release_status_set':values(entities,'release',releases,'status') or None}
        languages=set();formats=set();labels=set();workids=set();covers=set();producers=set();remix=set()
        for relid in releases:
            variants=entities.get('release:'+relid,{}).get('variants',[])
            for v in variants:
                language=v.get('text-representation',{}).get('language')
                if language:languages.add(language)
            data=details.get('release:'+relid,{}).get('data',{})
            formats.update(m['format'] for m in data.get('media',[]) if m.get('format'))
            labels.update(m['label']['id'] for m in data.get('label-info',[]) if m.get('label',{}).get('id'))
        for recid in recs:
            recordings.add(recid)
            for rel in details.get('recording:'+recid,{}).get('data',{}).get('relations',[]):
                if rel.get('target-type')=='work' and rel.get('type')=='performance':
                    workids.add(rel['work']['id']);covers.update(a for a in rel.get('attributes',[]) if a=='cover')
                if rel.get('target-type')=='artist' and rel.get('type')=='producer':producers.add(rel['artist']['id'])
                if 'remix' in rel.get('type',''):remix.add(rel.get('type'))
        works.update(workids)
        r.update(mb_v2_catalog_language_set=sorted(languages) or None,mb_v2_cached_format_set=sorted(formats) or None,
                 mb_v2_cached_label_ids=sorted(labels) or None,mb_v2_work_ids=sorted(workids) or None,
                 mb_v2_cover_evidence=1 if covers else None,mb_v2_known_producer_count=len(producers) if producers else None,
                 mb_v2_remix_relationships=sorted(remix) or None)
        # Mapping evidence is retained even when a unique source recording is unverified.
        match=cache['matches'].get(sid)
        if match:
            evidence=json.loads(match['evidence_json'])
            r['mb_v2_recording_mapping_status']=evidence.get('canonical_recording_status')
            r['mb_v2_mapping_review_flags']=evidence.get('review_flags',[])
            r['mb_v2_mapping_processed_at']=match['processed_at']
            provenance.append({'song_id':sid,'provider':'MusicBrainz','entity_ids':links,'mapping':match,
                'license':'CC0 core fields; original tags are not exported in this enrichment',
                'measurement_availability':'F: retrospective metadata, no original-edition verification'})
        rows.append(r)
    write_csv(LOCAL/'metadata_features.csv.xz',rows)
    write_json(LOCAL/'metadata_provenance.json.gz',provenance)
    write_json(LOCAL/'metadata_acquisition_queue.json',{'work_ids':sorted(works),'recording_ids':sorted(recordings),
        'single_recording_ids':sorted({r['mb_v2_recording_ids'][0] for r in rows if r.get('mb_v2_recording_mapping_status')=='single_observed_candidate' and len(r['mb_v2_recording_ids'] or [])==1})})
    summary={'study_songs':len(rows),'high_confidence_songs':len(provenance),'cached_work_ids':len(works),
             'linked_recording_ids':len(recordings),'seconds':time.monotonic()-start}
    write_json(MUSIC/'metadata_cache_extraction.json',summary);print(summary,flush=True)


if __name__=='__main__':extract()
