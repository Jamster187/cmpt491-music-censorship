"""Deterministic, allowlisted public summaries of the frozen research database.

No HTTP, lyrics-file/cache access, database writes, or classifier computation.
"""
import argparse
import csv
from collections import defaultdict
from contextlib import closing
from datetime import date
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import statistics
import tempfile

from billboard import song_id as identity_id
from public_classifier_features import COLUMNS as CLASSIFIER_COLUMNS, load_features, DATABASE as CLASSIFIER_DATABASE

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT/'data/public'
DATABASE = ROOT/'data/processed/research.db'
VERSION = 'classifier-features-v2.0'
SONG_COLUMNS = (
    'song_id','title','artist','first_chart_date','last_chart_date','best_chart_rank',
    'weekly_observation_count','chart_weeks','total_chart_points',
    'first_selected_month','last_selected_month','months_selected',
    'musicbrainz_match_status','mb_recording_count','mb_release_count',
    'mb_earliest_release_date','mb_release_date_precision','mb_release_title',
    'mb_duration_median_seconds','mb_duration_min_seconds','mb_duration_max_seconds',
    'mb_distinct_duration_count','lyrics_status','lyrics_available')
MONTHLY_COLUMNS = ('month','monthly_rank','song_id','monthly_points','weeks_present',
                   'best_weekly_rank','average_weekly_rank','weekly_observations')
# Keep normalized tables and the original 31-column prefix unchanged.
BASE_MASTER_COLUMNS = MONTHLY_COLUMNS + tuple(c for c in SONG_COLUMNS if c != 'song_id')
MASTER_COLUMNS = BASE_MASTER_COLUMNS + CLASSIFIER_COLUMNS
OUTPUT_NAMES = ('songs.csv','monthly_top100.csv','master_dataset.csv','manifest.json')
MONTHLY_SQL = 'SELECT '+','.join(MONTHLY_COLUMNS)+' FROM monthly_top100 ORDER BY month,monthly_rank'
LYRICS_STATUSES = {'success','quarantined','wrong_identity','bad_missing_text','not_found','error'}
METADATA_STATUSES = {'high_confidence','ambiguous','not_found','error'}
PRIVATE_MARKERS = re.compile(
    r'/Users/|/home/|/private/|/tmp/|file://|(?<!\S)[A-Za-z]:[\\/]|data[/\\](?:lyrics|cache|processed)[/\\]|'
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})\b|'
    r'\b(?:api[_ -]?key|access[_ -]?token)\s*[:=]\s*\S+|\b(?:password|secret)\s*=\s*\S+', re.I)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def public_cell(value):
    if value is None:return ''
    if isinstance(value,float) and not math.isfinite(value):raise ValueError('Nonfinite public value')
    text=str(value)
    if PRIVATE_MARKERS.search(text) or any(ord(c)<32 and c not in '\r\n\t' for c in text):
        raise ValueError('Private path, credential pattern, or control character in an export cell')
    # Do not echo a rejected value into a public report or log.
    return text


def partial_date(value):
    """Preserve source precision; never impute January 1 as an actual release date."""
    if value in (None,''):return ''
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?',value):
        raise ValueError('Unsupported MusicBrainz release date')
    parts=list(map(int,value.split('-')))
    date(*(parts+[1]*(3-len(parts))))
    return value


def duration_summary(milliseconds):
    values=sorted(set(milliseconds))
    if not values:return ('','','',0)
    # Each distinct observed positive duration has one vote, regardless of reissue count.
    return tuple(format(v/1000,'.4f').rstrip('0').rstrip('.') for v in
                 (statistics.median(values),values[0],values[-1]))+(len(values),)


def release_key(release):
    # A date-bearing manifestation precedes undated ones; partial prefixes sort first.
    identifier,release_date,title=release
    return (not bool(release_date),release_date,title,identifier)


def metadata_summaries(c):
    durations=defaultdict(set);recordings=defaultdict(set);releases=defaultdict(set);selected={}
    # SQL projects only core factual fields. Never serialize entity/provenance JSON.
    base=''' FROM song_external_links l JOIN metadata_matches m USING(song_id)
      JOIN external_entities e ON (e.provider,e.entity_type,e.entity_id)=(l.provider,l.entity_type,l.entity_id),
      json_each(e.metadata_json) v
      WHERE m.match_status='high_confidence' AND m.provider=l.provider
        AND l.provider='MusicBrainz' AND l.entity_type=?'''
    for sid,rid,length in c.execute("SELECT l.song_id,l.entity_id,json_extract(v.value,'$.length')"+base,('recording',)):
        recordings[sid].add(rid)
        if length is None or length==0:continue
        if type(length) is not int or length<0:raise ValueError('Invalid recording length')
        durations[sid].add(length)
    for sid,rid,dt,title in c.execute("SELECT l.song_id,l.entity_id,json_extract(v.value,'$.date'),json_extract(v.value,'$.title')"+base,('release',)):
        releases[sid].add(rid)
        if not isinstance(title,str) or not title.strip():raise ValueError('Missing linked release title')
        candidate=(rid,partial_date(dt),public_cell(title))
        if sid not in selected or release_key(candidate)<release_key(selected[sid]):selected[sid]=candidate
    output={}
    for sid,status in c.execute('SELECT song_id,match_status FROM metadata_matches'):
        if status not in METADATA_STATUSES:raise ValueError('Unsupported metadata status')
        if status!='high_confidence':
            output[sid]=('',)*9
            continue
        if not recordings[sid] or not releases[sid]:raise ValueError('Accepted metadata lacks linked evidence')
        _,dt,title=selected[sid]
        precision={0:'',4:'year',7:'month',10:'day'}[len(dt)]
        output[sid]=(len(recordings[sid]),len(releases[sid]),dt,precision,title)+duration_summary(durations[sid])
    return output


def song_rows(c):
    metadata=metadata_summaries(c)
    query='''SELECT s.song_id,s.title,s.artist,s.first_chart_date,s.last_chart_date,
      s.best_chart_rank,s.chart_observation_count,s.distinct_chart_dates,s.total_chart_points,
      p.first_selected_month,p.last_selected_month,p.months_selected,m.match_status,l.lyrics_status
      FROM study_population p JOIN songs s USING(song_id)
      JOIN metadata_matches m USING(song_id) JOIN lyrics_manifest l USING(song_id)
      ORDER BY s.song_id COLLATE BINARY'''
    rows=[]
    for r in c.execute(query):
        sid,title,artist=r[:3]
        if sid!=identity_id(title,artist):raise ValueError('Noncanonical song identity')
        if r[-1] not in LYRICS_STATUSES:raise ValueError('Unattempted or unsupported lyrics status')
        rows.append(tuple(r[:-1])+metadata[sid]+(r[-1],int(r[-1]=='success')))
    return rows


def write_csv(path,columns,rows):
    count=0
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(columns)
        for row in rows:
            if len(row)!=len(columns):raise ValueError('Export schema width differs')
            w.writerow([public_cell(v) for v in row]);count+=1
    return count


def reconcile_csv(path,columns,expected_rows):
    with Path(path).open(encoding='utf-8',newline='') as f:
        r=csv.reader(f)
        if next(r,None)!=list(columns):raise ValueError('Unexpected public columns')
        count=0
        for expected,actual in itertools.zip_longest(expected_rows,r):
            if expected is None or actual is None or [public_cell(v) for v in expected]!=actual:
                raise ValueError('Export does not match the source projection')
            count+=1
    return count


def validate_relations(rows,monthly):
    ids=[r[0] for r in rows]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate public song_id')
    ids=set(ids);baskets=defaultdict(list);months=defaultdict(list)
    for month,rank,sid,points,weeks,best,average,observations in monthly:
        if sid not in ids:raise ValueError('Monthly orphan')
        if not 1<=best<=average<=100 or weeks<1 or observations<weeks or points<=0:
            raise ValueError('Invalid monthly measurement')
        # Sum(101-rank) and mean rank must describe the same contributing rows.
        if not math.isclose(101-points/observations,average,abs_tol=1e-10):raise ValueError('Inconsistent monthly mean/points')
        baskets[month].append((rank,sid));months[sid].append(month)
    for group in baskets.values():
        if [x[0] for x in group]!=list(range(1,len(group)+1)) or len(set(s for _,s in group))!=len(group):
            raise ValueError('Invalid monthly rank/identity key')
    for row in rows:
        selected=sorted(months[row[0]])
        if not selected or (row[9],row[10],row[11])!=(selected[0],selected[-1],len(selected)):
            raise ValueError('Song monthly membership mismatch')
    return len(baskets)


def check_source(c):
    if c.execute("SELECT value FROM build_metadata WHERE key='schema_version'").fetchone()!=('2',):
        raise ValueError('Public freeze requires research schema 2')
    counts={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in
            ('songs','chart_observations','study_population','monthly_top100','metadata_matches','lyrics_manifest')}
    expected={'songs':32723,'chart_observations':355487,'study_population':25363,
              'monthly_top100':81800,'metadata_matches':25363,'lyrics_manifest':25363}
    if counts!=expected:raise ValueError('Unexpected frozen population counts')
    if dict(c.execute('SELECT lyrics_status,count(*) FROM lyrics_manifest GROUP BY lyrics_status'))!={
        'success':19372,'quarantined':3519,'wrong_identity':1365,'bad_missing_text':184,'not_found':872,'error':51}:
        raise ValueError('Lyrics freeze changed; create an explicit new dataset version')
    if dict(c.execute('SELECT match_status,count(*) FROM metadata_matches GROUP BY match_status'))!={
        'high_confidence':20450,'ambiguous':3410,'not_found':1502,'error':1}:
        raise ValueError('Metadata freeze changed')
    if c.execute('PRAGMA foreign_key_check').fetchall() or c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
        raise ValueError('Research database integrity failed')
    return counts


def master_rows(directory,classifier_features):
    """Left join the public CSVs, failing if a monthly key has no unique match.

    Preserve serialized values (including blanks), monthly order, and repeated
    songs across months. Only explicitly approved public columns can propagate.
    """
    with (directory/'songs.csv').open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=list(SONG_COLUMNS):raise ValueError('Unexpected song columns')
        songs={}
        for row in reader:
            if None in row or None in row.values():raise ValueError('Malformed song CSV row')
            sid=row['song_id']
            if sid in songs:raise ValueError('Duplicate public song_id')
            songs[sid]=row
    available={sid for sid,row in songs.items() if row['lyrics_available']=='1'}
    if set(classifier_features)!=available:raise ValueError('Classifier coverage differs from usable public lyrics')
    for values in classifier_features.values():
        if len(values)!=len(CLASSIFIER_COLUMNS):raise ValueError('Wrong classifier feature count')
        if any(v is not None and (type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1) for v in values):raise ValueError('Invalid classifier value')
    if set(SONG_COLUMNS)&set(MONTHLY_COLUMNS)!={'song_id'}:
        raise ValueError('Public columns collide outside the join key')
    with (directory/'monthly_top100.csv').open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=list(MONTHLY_COLUMNS):raise ValueError('Unexpected monthly columns')
        for row in reader:
            if None in row or None in row.values():raise ValueError('Malformed monthly CSV row')
            song=songs.get(row['song_id'])
            if song is None:raise ValueError('Monthly row has no song match')
            yield tuple(row[c] for c in MONTHLY_COLUMNS)+tuple(song[c] for c in SONG_COLUMNS if c!='song_id')+classifier_features.get(row['song_id'],(None,)*len(CLASSIFIER_COLUMNS))


def generate(c,directory,classifier_features):
    rows=song_rows(c);monthly=c.execute(MONTHLY_SQL).fetchall()
    if len(rows)!=c.execute('SELECT count(*) FROM study_population').fetchone()[0]:
        raise ValueError('Missing manifest/metadata relationship')
    baskets=validate_relations(rows,monthly)
    for name,columns,values in [('songs.csv',SONG_COLUMNS,rows),('monthly_top100.csv',MONTHLY_COLUMNS,monthly)]:
        write_csv(directory/name,columns,values)
        reconcile_csv(directory/name,columns,values)
    master_count=write_csv(directory/'master_dataset.csv',MASTER_COLUMNS,master_rows(directory,classifier_features))
    reconcile_csv(directory/'master_dataset.csv',MASTER_COLUMNS,master_rows(directory,classifier_features))
    if master_count!=len(monthly):raise ValueError('Master join changed the monthly row count')
    return dict(songs=len(rows),monthly=len(monthly),master=master_count,baskets=baskets)


def build(validate_only=False):
    # Output is deliberately fixed. No option can redirect publication into data/raw.
    if PUBLIC.is_symlink():raise ValueError('Public output directory is a symlink')
    PUBLIC.mkdir(parents=True,exist_ok=True)
    for name in OUTPUT_NAMES:
        if (PUBLIC/name).is_symlink():raise ValueError('Public output file is a symlink')
    before=sha(DATABASE)
    with closing(sqlite3.connect(DATABASE.resolve().as_uri()+'?mode=ro',uri=True)) as c:
        c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
        check_source(c)
        features,classifier_provenance=load_features(c)
        # Both independent serializations are compared byte-for-byte before publication.
        with tempfile.TemporaryDirectory(dir=ROOT/'data/processed',prefix='public-export-') as temp:
            stage=Path(temp);one=stage/'one';two=stage/'two';one.mkdir();two.mkdir()
            counts=generate(c,one,features)
            if counts!={'songs':25363,'monthly':81800,'master':81800,'baskets':818}:raise ValueError('Public counts differ')
            if c.execute('SELECT min(n),max(n) FROM (SELECT count(*) n FROM monthly_top100 GROUP BY month)').fetchone()!=(100,100):
                raise ValueError('Expected exactly 100 songs per basket')
            if generate(c,two,features)!=counts:raise ValueError('Nondeterministic row counts')
            files={}
            for name,columns,count in [('songs.csv',SONG_COLUMNS,counts['songs']),('monthly_top100.csv',MONTHLY_COLUMNS,counts['monthly']),
                                       ('master_dataset.csv',MASTER_COLUMNS,counts['master'])]:
                fingerprint=sha(one/name)
                if fingerprint!=sha(two/name):raise ValueError('Nondeterministic CSV bytes')
                size=(one/name).stat().st_size
                # The expanded, full-precision master is explicitly reviewed below GitHub's 100 MiB hard limit.
                limit=95*1024*1024 if name=='master_dataset.csv' else 25*1024*1024
                if size>=limit:raise ValueError('Review distribution method before publishing this file size')
                files[name]=dict(rows=count,bytes=size,sha256=fingerprint,columns=columns)
            inputs=json.loads(c.execute("SELECT value FROM build_metadata WHERE key='input_sha256'").fetchone()[0])
            manifest=dict(version=VERSION,source_repository='https://github.com/mhollingshead/billboard-hot-100',
                          source_commit='unknown; supplied snapshot',billboard_snapshot_sha256=inputs['data/raw/billboard-hot-100.json'],
                          research_database_sha256=before,exporter_sha256=sha(Path(__file__)),research_schema_version=2,
                          monthly_baskets=818,weekly_csv_published=False,classifier=classifier_provenance,files=files)
            (one/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
            if sha(DATABASE)!=before:raise ValueError('Source database changed during export')
            if sha(CLASSIFIER_DATABASE)!=classifier_provenance['database_sha256']:raise ValueError('Classifier database changed during export')
            for name in OUTPUT_NAMES:
                if validate_only:
                    if not (PUBLIC/name).is_file() or sha(PUBLIC/name)!=sha(one/name):raise ValueError('Published export is stale or modified: '+name)
                else:os.replace(one/name,PUBLIC/name)
    print(json.dumps(dict(version=VERSION,validation='passed',deterministic=True,counts=counts,files=files),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('build','validate'))
    build(validate_only=parser.parse_args().command=='validate')
