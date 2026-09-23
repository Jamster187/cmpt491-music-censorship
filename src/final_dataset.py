"""Final weekly/month-end public exports. Offline, read-only inputs; no inference."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
import lzma
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import tempfile
import unicodedata

from billboard import song_id
from genre_evidence import ro
import genre_production as genre
from month_end_snapshots import select_snapshots, KNOWN_GAPS
from public_dataset import (ROOT, PUBLIC, metadata_summaries, public_cell, sha,
                            SONG_COLUMNS as OLD_SONG_COLUMNS)
from public_classifier_features import COLUMNS, load_features, project_song, EXCEPTIONS
from month_end_catchup_audit import validate_chunks
from classifier_production_store import chunks, MODELS

VERSION = 'final-snapshots-v3.0'
LOCAL = ROOT / 'data/processed/final_dataset'
SONG_COLUMNS = tuple({'first_selected_month':'first_snapshot_month',
                      'last_selected_month':'last_snapshot_month',
                      'months_selected':'snapshot_months_selected'}.get(k,k)
                     for k in OLD_SONG_COLUMNS) + (
    'in_final_study_population', 'primary_genre', 'genre_confidence', 'secondary_genres') + COLUMNS
CHART_FIELDS = ('reported_last_week_rank','reported_peak_position','reported_weeks_on_chart',
                'source_chart_index','source_row_index')
WEEKLY_COLUMNS = ('chart_date','weekly_rank') + CHART_FIELDS + SONG_COLUMNS
MONTHLY_COLUMNS = ('month','snapshot_chart_date','monthly_rank') + CHART_FIELDS + SONG_COLUMNS
LEGACY = 'legacy_classifier_v2'
BASELINE = ROOT / 'data/experiments/genre_pilot/protected.json'
GENRE_AUDIT = ROOT / 'reports/genre_final_audit/validation.json'
PIPELINE_FILES = ('src/final_dataset.py','src/public_dataset.py','src/public_classifier_features.py',
                  'src/month_end_snapshots.py','src/month_end_catchup_audit.py',
                  'src/genre_production.py','src/genre_llm.py','src/billboard.py',
                  'src/classifier_production_store.py','docs/classifier_production_schema.json',
                  'docs/classifier_accepted_missingness.json')


def checked_sources():
    """Public files are authorized outputs now; all frozen private inputs stay fixed."""
    baseline = json.loads(BASELINE.read_text())
    protected = {p:h for p,h in baseline.items() if not p.startswith('data/public/')}
    audit = json.loads(GENRE_AUDIT.read_text())
    if audit['status'] != 'COMPLETE' or audit['completed'] != 28041:
        raise ValueError('Final genre audit is not complete')
    protected['data/processed/genre_results.db'] = audit['genre_database_sha256']
    for rel,expected in protected.items():
        path=ROOT/rel
        if path.is_symlink() or sha(path)!=expected:
            raise ValueError('Frozen source changed: '+rel)
    return protected


def combine(old, added, population):
    if set(old)&set(added):
        raise ValueError('Overlapping source identities')
    merged=dict(old,**added)
    if not set(population)<=set(merged):
        raise ValueError('Missing enrichment disposition')
    return {sid:merged[sid] for sid in population}


def check_feature_nulls(sid, values, usable):
    if len(values)!=42:
        raise ValueError('Wrong classifier width')
    missing={i for i,v in enumerate(values) if v is None}
    expected=(set(range(42)) if not usable else set(range(4)) if (sid,'lyriclens') in EXCEPTIONS else set())
    if missing!=expected:
        raise ValueError('Unexpected classifier missingness')
    for v in values:
        if v is not None and (type(v) not in (float,int) or not 0<=v<=1):
            raise ValueError('Invalid classifier score')


def make_song_rows(history, monthly, metadata, statuses, lyrics, features, genres):
    membership=defaultdict(set)
    for row in monthly:membership[row[3]].add(row[0])
    population=set(membership)
    if any(set(d)!=population for d in (metadata,statuses,lyrics,genres)):
        raise ValueError('Final population join differs')
    if set(features)!={sid for sid in population if lyrics[sid]=='success'}:
        raise ValueError('Lyrics/classifier join differs')
    output={}
    for sid,hist in sorted(history.items()):
        if sid!=song_id(hist[1],hist[2]):raise ValueError('Identity mismatch')
        if sid in population:
            months=membership[sid];primary,confidence,secondary=genres[sid]
            if primary not in genre.TAXONOMY or confidence not in ('high','medium','low'):
                raise ValueError('Invalid genre/confidence')
            if not isinstance(secondary,list) or len(set(secondary))!=len(secondary) or any(x not in genre.TAXONOMY or x==primary for x in secondary):
                raise ValueError('Invalid secondary genres')
            values=features.get(sid,(None,)*42)
            check_feature_nulls(sid,values,lyrics[sid]=='success')
            if statuses[sid] not in ('high_confidence','ambiguous','not_found','error'):
                raise ValueError('Invalid metadata status')
            if lyrics[sid] not in ('success','quarantined','wrong_identity','bad_missing_text','not_found','error'):
                raise ValueError('Invalid lyrics status')
            output[sid]=hist+(min(months),max(months),len(months),statuses[sid])+metadata[sid]+(
                lyrics[sid],int(lyrics[sid]=='success'),1,primary,confidence,
                json.dumps(secondary,ensure_ascii=False,separators=(',',':')))+values
        else:
            # Retained weekly identity/history; no old-population enrichment leaks in.
            output[sid]=hist+('','','','outside_final_study_population')+('',)*9+(
                'outside_final_study_population',None,0,None,None,None)+(None,)*42
        if len(output[sid])!=len(SONG_COLUMNS):raise ValueError('Song schema mismatch')
    if not population<=set(output):raise ValueError('Missing song identity')
    return output,population


def validate_charts(charts, weekly, monthly):
    source=[]
    for ci,chart in enumerate(charts):
        for ri,r in enumerate(chart['data']):
            source.append((chart['date'],r['this_week'],r['last_week'],r['peak_position'],
                           r['weeks_on_chart'],ci,ri,song_id(r['song'],r['artist'])))
    source.sort(key=lambda r:(r[0],r[1],r[5],r[6]))
    if source!=weekly:raise ValueError('Weekly source row/rank/identity mismatch')
    selected,gaps=select_snapshots(charts)
    if selected!=monthly:raise ValueError('Monthly snapshot mismatch')
    return gaps


def prepare():
    protected=checked_sources()
    charts=json.loads((ROOT/'data/raw/billboard-hot-100.json').read_text())
    monthly,gaps=select_snapshots(charts)
    population={r[3] for r in monthly}
    if (len(charts),len(monthly),len(population),gaps)!=(3555,81797,28041,KNOWN_GAPS):
        raise ValueError('Frozen snapshot population changed')
    with closing(ro(ROOT/'data/processed/music.db')) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Chart DB integrity failure')
        weekly=c.execute('SELECT chart_date,rank,last_week,peak_position,weeks_on_chart,source_chart_index,source_row_index,song_id FROM chart_observations ORDER BY chart_date,rank,source_chart_index,source_row_index').fetchall()
        sql_monthly=c.execute("""WITH dates AS (SELECT substr(chart_date,1,7) month,max(chart_date) dt FROM chart_observations GROUP BY 1)
            SELECT dates.month,o.chart_date,o.rank,o.song_id,o.last_week,o.peak_position,o.weeks_on_chart,o.source_chart_index,o.source_row_index
            FROM dates JOIN chart_observations o ON o.chart_date=dates.dt ORDER BY 1,3""").fetchall()
        if sql_monthly!=monthly:raise ValueError('SQL maximum dates differ from raw monthly snapshots')
        history={r[0]:r for r in c.execute('''SELECT s.song_id,s.title,s.artist,min(o.chart_date),max(o.chart_date),min(o.rank),count(*),count(DISTINCT o.chart_date),sum(101-o.rank)
            FROM songs s JOIN chart_observations o USING(song_id) GROUP BY s.song_id''')}
    if len(weekly)!=355487 or len(history)!=32723:raise ValueError('Weekly universe changed')
    validate_charts(charts,weekly,monthly)
    del charts
    base=ROOT/'data/processed/month_end_catchup'
    catchup=json.loads((base/'population.json').read_text())
    if population!=set(catchup['new_population']):raise ValueError('Catch-up population differs')
    with closing(ro(ROOT/'data/processed/research.db')) as c:
        original={r[0]:r for r in c.execute('SELECT song_id,title,artist,first_chart_date,last_chart_date,best_chart_rank,chart_observation_count,distinct_chart_dates,total_chart_points FROM songs')}
        if original!=history:raise ValueError('Whole-history summaries differ')
        old_meta=metadata_summaries(c)
        old_status=dict(c.execute('SELECT song_id,match_status FROM metadata_matches'))
        old_lyrics=dict(c.execute('SELECT song_id,lyrics_status FROM lyrics_manifest'))
        old_features,feature_provenance=load_features(c)
    with closing(ro(base/'metadata.db')) as c:
        new_meta=metadata_summaries(c)
        new_status=dict(c.execute('SELECT song_id,match_status FROM metadata_matches'))
    with closing(ro(base/'lyrics.db')) as c:
        new_lyrics={}
        for sid,payload in c.execute('SELECT song_id,payload FROM production_results'):
            r=json.loads(payload)
            if (r['song_id'],r['title'],r['artist'])!=(sid,history[sid][1],history[sid][2]):raise ValueError('Catch-up lyric identity differs')
            new_lyrics[sid]='success' if r['status']=='accepted' else r['status']
    new_features={}
    with closing(ro(base/'classifier_results.db')) as c:
        c.row_factory=sqlite3.Row
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Catch-up classifier integrity failure')
        for row in c.execute('SELECT * FROM song_results'):
            sid=row['song_id'];jobs={r['model']:r for r in c.execute('SELECT * FROM jobs WHERE song_id=?',(sid,))}
            new_features[sid]=project_song(row,jobs,{})
            for model,job in jobs.items():validate_chunks(job,chunks(c,sid,model),row)
    if set(new_features)!={s for s,v in new_lyrics.items() if v=='success'}:raise ValueError('Catch-up feature population differs')
    genres={}
    with closing(ro(genre.DB)) as c:
        c.row_factory=sqlite3.Row;settings=genre.verify(c)
        for r in c.execute('SELECT * FROM songs'):
            if r['status']!='completed' or (r['title'],r['artist'])!=history[r['song_id']][1:3]:raise ValueError('Genre disposition/identity differs')
            genres[r['song_id']]=(r['primary_genre'],r['confidence'],json.loads(r['secondary_genres']))
    metadata=combine(old_meta,new_meta,population);statuses=combine(old_status,new_status,population)
    lyrics=combine(old_lyrics,new_lyrics,population)
    if set(old_features)&set(new_features):raise ValueError('Overlapping classifier identities')
    features={s:v for s,v in dict(old_features,**new_features).items() if s in population}
    songs,population=make_song_rows(history,monthly,metadata,statuses,lyrics,features,genres)
    if (sum(s=='high_confidence' for s in statuses.values()),len(features),sum(all(x is not None for x in v) for v in features.values()))!=(22290,20981,20979):
        raise ValueError('Frozen enrichment coverage changed')
    return songs,population,weekly,monthly,protected,feature_provenance,settings


def table_rows(kind,songs,population,weekly,monthly):
    if kind=='songs':
        for sid in sorted(population):yield songs[sid]
    elif kind=='weekly':
        for r in weekly:
            if r[7] not in songs:raise ValueError('Weekly orphan')
            yield r[:7]+songs[r[7]]
    elif kind=='monthly':
        for r in monthly:
            if r[3] not in population:raise ValueError('Monthly orphan')
            yield r[:3]+r[4:9]+songs[r[3]]
    else:raise ValueError('Unknown table')


def serialized_rows(kind,songs,population,weekly,monthly):
    # Strings in the enrichment projection were checked once, before repetition.
    if kind=='songs':
        yield from table_rows(kind,songs,population,weekly,monthly)
    elif kind=='weekly':
        for r in weekly:yield tuple(public_cell(v) for v in r[:7])+songs[r[7]]
    elif kind=='monthly':
        for r in monthly:yield tuple(public_cell(v) for v in r[:3]+r[4:9])+songs[r[3]]


def write_table(path,columns,rows):
    count=0
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(columns)
        for row in rows:
            if len(row)!=len(columns):raise ValueError('Schema width changed')
            w.writerow(row);count+=1
    return count


def reconcile(path,columns,rows):
    with path.open(encoding='utf-8',newline='') as f:
        reader=csv.reader(f)
        if next(reader,None)!=list(columns):raise ValueError('Header changed')
        for expected,actual in itertools.zip_longest(rows,reader):
            if expected is None or actual is None or list(expected)!=actual:raise ValueError('CSV source reconciliation failed')


def deterministic_xz(source,dest):
    with source.open('rb') as src,dest.open('wb') as target:
        with lzma.LZMAFile(target,mode='wb',format=lzma.FORMAT_XZ,preset=6) as out:
            shutil.copyfileobj(src,out)
    h=hashlib.sha256()
    with lzma.open(dest,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    if h.hexdigest()!=sha(source):raise ValueError('XZ round-trip differs')


def distribution_name(name,size):
    if name=='master_weekly.csv' and size>=95*1024*1024:return name+'.xz'
    if size>=95*1024*1024:raise ValueError('Public file requires distribution review: '+name)
    return name


def coverage(songs,ids):
    indexes={k:SONG_COLUMNS.index(k) for k in SONG_COLUMNS}
    rows=[songs[s] for s in ids]
    def n(k,value):return sum(r[indexes[k]]==value for r in rows)
    return dict(rows=len(rows),unique_songs=len(set(ids)),in_final_study_population=n('in_final_study_population',1),
                musicbrainz_high_confidence=n('musicbrainz_match_status','high_confidence'),
                genre_available=sum(bool(r[indexes['primary_genre']]) for r in rows),
                classifier_available=sum(any(v is not None for v in r[-42:]) for r in rows),
                all_42_available=sum(all(v is not None for v in r[-42:]) for r in rows))


def archive_sources():
    baseline=json.loads(BASELINE.read_text());result={}
    for name in ('songs.csv','manifest.json','README.md'):
        archived=PUBLIC/LEGACY/name
        original=PUBLIC/name
        src=archived if archived.exists() else original
        expected=baseline['data/public/'+name]
        if sha(src)!=expected:raise ValueError('Legacy archive differs from frozen release')
        result[name]=src
    for name in ('master_dataset.csv','monthly_top100.csv'):
        if sha(PUBLIC/name)!=baseline['data/public/'+name]:raise ValueError('Legacy table changed')
    return result


def render_report(m):
    lines=['# Final analysis-ready dataset build','',f"Release: `{VERSION}`. Dataset construction only; no historical/COVID analysis, moving averages or combined content scores.", '',
           '| Table | Rows | Columns | Bytes (CSV) | Unique songs | Final-population rows | Metadata matched rows | Genre rows | Classifier rows | All-42 rows |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for kind in ('songs','weekly','monthly'):
        d=m['tables'][kind];c=d['coverage'];lines.append(f"| {kind} | {c['rows']:,} | {len(d['columns'])} | {d['csv_bytes']:,} | {c['unique_songs']:,} | {c['in_final_study_population']:,} | {c['musicbrainz_high_confidence']:,} | {c['genre_available']:,} | {c['classifier_available']:,} | {c['all_42_available']:,} |")
    lines+=['','Weekly: all 3,555 physical charts and 355,487 source rows, including repeated song/date pairs. Monthly: the latest chart in each of 818 calendar months, 81,797 rows. The three rank-100 gaps remain unchanged. Chart dates are not release dates.', '',
            'Enrichment is deliberately restricted to the final 28,041-song population. Other weekly identities keep their exact Billboard identity and whole-history summaries; metadata/genre/features and lyrics availability remain blank, with explicit outside-population statuses. Historical enrichment for removed old-population assets remains preserved in the legacy stores/exports and is not silently incorporated.', '',
            'Genre confidence: high 18,621; medium 7,538; low 1,882. Classifier songs: 20,981; all 42 features: 20,979. The two documented LyricLens exceptions retain only their four NULLs; 7,060 final-population songs lack all 42 features. Secondary genres are JSON arrays of provisional model labels; reasons are excluded.', '',
            'Validation: raw JSON and immutable SQL rows reconcile by source coordinates; whole-history summaries independently reconcile; every CSV cell reconciles to the allowlisted projection; independent serializations have equal SHA-256 checksums; XZ round-trips exactly. Frozen input databases, canonical lyrics and raw Billboard source retain their hashes. Both classifier stores reconcile scores to saved chunks. No inference is run.', '',
            'Publication:']
    for kind,d in m['tables'].items():lines.append(f"- `{d['published_file']}`: {d['published_bytes']:,} bytes; SHA-256 `{d['published_sha256']}`.")
    lines+=['', 'The uncompressed weekly CSV is generated locally but excluded from Git when above the reviewed 95 MiB threshold. Its XZ copy preserves full precision and every row. Monthly and song CSVs are direct downloads. No Git LFS.', '',
            'Earlier aggregate-month CSVs remain historical artifacts, not current inputs; their old song table and manifest are preserved in `data/public/legacy_classifier_v2/`. The new `manifest.json` is the current release contract. Pre-publication audits that freeze the old public-file hashes remain historical checks; use `src/final_dataset.py validate` for this authorized release.', '',
            'Reproduce: `python3 src/final_dataset.py build`; validate: `python3 src/final_dataset.py validate`; tests: `python3 -m unittest discover -s tests -v`. Exact reconstruction requires the retained private enrichment stores; downloading and using the public CSVs does not.', '']
    return '\n'.join(lines)


def run(action):
    pipeline = {p:sha(ROOT/p) for p in PIPELINE_FILES}
    print('Validating frozen sources and loading exact song-level projections',flush=True)
    songs,population,weekly,monthly,protected,feature_provenance,settings=prepare()
    legacy=archive_sources()
    LOCAL.mkdir(parents=True,exist_ok=True)
    if PUBLIC.is_symlink():raise ValueError('Public output symlink')
    serial={sid:tuple(public_cell(v) for v in row) for sid,row in songs.items()}
    tables={}
    specs=(('songs','songs.csv',SONG_COLUMNS,sorted(population)),('weekly','master_weekly.csv',WEEKLY_COLUMNS,[r[7] for r in weekly]),('monthly','master_monthly.csv',MONTHLY_COLUMNS,[r[3] for r in monthly]))
    with tempfile.TemporaryDirectory(dir=LOCAL,prefix='build-') as td:
        stage=Path(td)
        for kind,name,columns,ids in specs:
            print('Writing, reconciling and repeat-building '+name,flush=True)
            def values():return serialized_rows(kind,serial,population,weekly,monthly)
            count=write_table(stage/name,columns,values())
            reconcile(stage/name,columns,values())
            repeat=stage/('repeat-'+name);write_table(repeat,columns,values())
            if sha(stage/name)!=sha(repeat):raise ValueError('Nondeterministic CSV')
            repeat.unlink()
            size=(stage/name).stat().st_size;published=distribution_name(name,size)
            if published!=name:
                deterministic_xz(stage/name,stage/published)
            print(f'{name}: {size:,} CSV bytes; {published}: {(stage/published).stat().st_size:,} published bytes',flush=True)
            if (stage/published).stat().st_size>=95*1024*1024:raise ValueError('Published artifact too large')
            tables[kind]=dict(csv_file=name,columns=columns,csv_rows=count,csv_bytes=size,csv_sha256=sha(stage/name),
                              published_file=published,published_bytes=(stage/published).stat().st_size,published_sha256=sha(stage/published),coverage=coverage(songs,ids))
        # Every frozen input, including lyric files, is checked again before publishing.
        if checked_sources()!=protected:raise ValueError('Sources changed during build')
        if {p:sha(ROOT/p) for p in PIPELINE_FILES} != pipeline:raise ValueError('Exporter implementation changed during build; rerun')
        manifest=dict(version=VERSION,source_repository='https://github.com/mhollingshead/billboard-hot-100',source_commit='unknown; reported upstream, not independently verified',
                      billboard_snapshot_sha256=protected['data/raw/billboard-hot-100.json'],weekly_charts=3555,monthly_snapshots=818,source_rank_gaps=KNOWN_GAPS,
                      tables=tables,enrichment_population=28041,genre_confidence=dict(Counter(v[26] for s,v in songs.items() if s in population)),
                      genre=dict(model=settings['model'],config=settings['config'],frozen_commit=settings['frozen_commit'],taxonomy=settings['taxonomy'],frozen_files=settings['frozen_files']),
                      classifier=feature_provenance,source_database_sha256={p.removeprefix('data/processed/').replace('/','__'):h for p,h in protected.items() if p.endswith('.db')},
                      protected_file_count=len(protected),protected_baseline_sha256=sha(BASELINE),genre_audit_sha256=sha(GENRE_AUDIT),
                      pipeline_sha256=pipeline,runtime=dict(python=platform.python_version(),unicode=unicodedata.unidata_version,compression='XZ preset 6, CRC64'),
                      deterministic_rebuild=True,integrity='PASS',legacy_release={str((Path(LEGACY)/n)):sha(p) for n,p in legacy.items()})
        if manifest['genre_confidence']!={'high':18621,'medium':7538,'low':1882}:raise ValueError('Confidence census changed')
        (stage/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        (stage/'final_dataset_build.md').write_text(render_report(manifest))
        # Compare every candidate before any mutation in validate mode.
        outputs=[(stage/d['published_file'],PUBLIC/d['published_file']) for d in tables.values()]
        outputs += [(stage/'manifest.json',PUBLIC/'manifest.json'),(stage/'final_dataset_build.md',ROOT/'reports/final_dataset_build.md')]
        for name,src in legacy.items():
            staged=stage/LEGACY/name;staged.parent.mkdir(exist_ok=True);shutil.copyfile(src,staged)
            outputs.append((staged,PUBLIC/LEGACY/name))
        for d in tables.values():
            if d['published_file']!=d['csv_file']:outputs.append((stage/d['csv_file'],PUBLIC/d['csv_file']))
        # Preserve the previous release first; publish the manifest last as the commit marker.
        outputs.sort(key=lambda pair: (0 if LEGACY in pair[1].parts else 2 if pair[1] == PUBLIC/'manifest.json' else 1))
        for src,dest in outputs:
            if any(parent.is_symlink() for parent in (dest, dest.parent)):raise ValueError('Output file symlink')
            if action=='validate' and (not dest.exists() or sha(src)!=sha(dest)):raise ValueError('Published/local output differs: '+str(dest.relative_to(ROOT)))
        if action=='build':
            for src,dest in outputs:
                dest.parent.mkdir(parents=True,exist_ok=True);os.replace(src,dest)
    print(json.dumps(dict(version=VERSION,integrity='PASS',deterministic=True,tables={k:{x:v[x] for x in ('csv_rows','csv_bytes','published_file','published_bytes','coverage')} for k,v in tables.items()}),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('build','validate'))
    run(parser.parse_args().action)
