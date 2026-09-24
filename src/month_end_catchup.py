"""Scoped orchestration for the 3,654 added assets; frozen matchers are unchanged."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import unicodedata

import lyrics_production as lp
import production_metadata as mp
from classifier_production import lock
from classifier_production_store import ROOT, sha, canonical, digest, now, MODELS
from month_end_snapshots import select_snapshots, KNOWN_GAPS, protected_hashes
from research import SCHEMA

BASE=ROOT/'data/processed/month_end_catchup'
MANIFEST=BASE/'population.json'
METADATA=BASE/'metadata.db'
LYRICS=BASE/'lyrics.db'
CLASSIFIERS=BASE/'classifier_results.db'
VENV=ROOT/'data/experiments/classifier_panel/venv/bin/python'
STOP=False
FROZEN_FILES=('production_metadata.py','musicbrainz.py','metadata_match.py','musicbrainz_asset_match.py','phase2ar.py',*lp.BUNDLE)
ADAPTER_FILES=('month_end_catchup.py','month_end_catchup_classifier.py')
LYRIC_TABLES=('production_settings','production_assets','production_results','production_history','production_runs')


def read(path):return json.loads(Path(path).read_text())
def save(path,obj):lp.save_json(path,obj)
def connect(path,readonly=False):
    c=sqlite3.connect(Path(path).resolve().as_uri()+('?mode=ro' if readonly else '?mode=rw'),uri=True,timeout=30)
    c.execute('PRAGMA foreign_keys=ON')
    return c


def manifest():
    m=read(MANIFEST)
    if m['population_sha256']!=digest(canonical(m['songs'])):raise ValueError('Catch-up population altered')
    if len(m['songs'])!=3654 or len({s['song_id'] for s in m['songs']})!=3654:raise ValueError('Wrong catch-up population')
    for name,h in m['implementation_sha256'].items():
        if sha(ROOT/'src'/name)!=h:raise ValueError('Frozen implementation changed: '+name)
    return m


def freeze():
    lp.guards();BASE.mkdir(parents=True,exist_ok=True)
    if MANIFEST.exists():
        verify_protected();return manifest()
    before=protected_hashes()
    monthly,gaps=select_snapshots(read(ROOT/'data/raw/billboard-hot-100.json'))
    if gaps!=KNOWN_GAPS or len(monthly)!=81797 or len({r[0] for r in monthly})!=818:raise ValueError('Snapshot definition changed')
    new={r[3] for r in monthly}
    with closing(connect(ROOT/'data/processed/research.db',True)) as c:
        c.row_factory=sqlite3.Row
        old={r[0] for r in c.execute('SELECT song_id FROM study_population')}
        added=new-old
        history=[dict(r) for r in c.execute('SELECT * FROM songs ORDER BY song_id') if r['song_id'] in added]
        old_lyrics=dict(c.execute("SELECT song_id,lyrics_sha256 FROM lyrics_manifest WHERE lyrics_status='success'"))
    if (len(new),len(old),len(new&old),len(old-new),len(added))!=(28041,25363,24387,976,3654):raise ValueError('Population mismatch')
    with (ROOT/'reports/month_end_population_changes.csv').open() as f:
        if {r['song_id'] for r in csv.DictReader(f) if r['change']=='added'}!=added:raise ValueError('Reviewed ledger mismatch')
    if len(old_lyrics)!=19372:raise ValueError('Old approved lyrics changed')
    for sid,h in old_lyrics.items():
        p=ROOT/'data/lyrics'/f'{sid}.txt'
        if p.is_symlink() or sha(p)!=h:raise ValueError('Old lyric checksum mismatch')
    if {p.stem for p in (ROOT/'data/lyrics').glob('*.txt')}!=set(old_lyrics):raise ValueError('Unexpected existing lyrics')
    with closing(connect(ROOT/'data/processed/lyrics.db',True)) as c:
        settings=dict(c.execute('SELECT * FROM production_settings'))
    if settings['current_pipeline_sha256']!=lp.fingerprint() or settings['python']!=sys.version or settings['unicode']!=unicodedata.unidata_version:
        raise ValueError('Use the frozen acquisition Python/Unicode implementation')
    pilot={}
    for sid in sorted(added):
        p=ROOT/'data/experiments/phase2ar/results'/f'{sid}.json'
        if p.exists():pilot[sid]=sha(p)
    if len(pilot)!=19:raise ValueError('Unexpected pilot overlap')
    months=defaultdict(set)
    for r in monthly:months[r[3]].add(r[0])
    songs=[dict(s,snapshot_months=sorted(months[s['song_id']])) for s in history]
    m=dict(version='month-end-catchup-v1',created_at=now(),songs=songs,population_sha256=digest(canonical(songs)),
           old_population_sha256=digest(canonical(sorted(old))),new_population=sorted(new),
           protected_sha256=before,old_lyrics_sha256=old_lyrics,pilot_sha256=pilot,
           implementation_sha256={n:sha(ROOT/'src'/n) for n in dict.fromkeys(FROZEN_FILES+ADAPTER_FILES)},
           lyrics_pipeline_sha256=lp.fingerprint(),acquisition_python=sys.version,unicode=unicodedata.unidata_version,
           source_gaps=KNOWN_GAPS,snapshot_observations=81797)
    if protected_hashes()!=before:raise ValueError('Protected inputs changed')
    save(MANIFEST,m)
    return m


def verify_protected(check_files=True):
    m=manifest()
    if protected_hashes()!=m['protected_sha256']:raise ValueError('Protected source/database/public file changed')
    if check_files:
        for sid,h in m['old_lyrics_sha256'].items():
            path=ROOT/'data/lyrics'/f'{sid}.txt'
            if path.is_symlink() or sha(path)!=h:raise ValueError('Old lyrics modified')
    return m


def initialize_metadata(m):
    if not METADATA.exists():
        temp=BASE/'metadata.initializing.db'
        if temp.exists():temp.unlink()
        with closing(sqlite3.connect(temp)) as c:
            c.executescript(SCHEMA)
            fields=[r[1] for r in c.execute('PRAGMA table_info(songs)')]
            with c:
                c.executemany('INSERT INTO songs VALUES ('+','.join('?' for _ in fields)+')',[[s[k] for k in fields] for s in m['songs']])
                c.executemany('INSERT INTO study_population VALUES (?,?,?,?)',[(s['song_id'],s['snapshot_months'][0],s['snapshot_months'][-1],len(s['snapshot_months'])) for s in m['songs']])
                c.execute('INSERT INTO build_metadata VALUES (?,?)',('catchup_population_sha256',m['population_sha256']))
        os.replace(temp,METADATA)
    with closing(connect(METADATA,True)) as c:
        if {r[0] for r in c.execute('SELECT song_id FROM study_population')}!={s['song_id'] for s in m['songs']}:raise ValueError('Metadata population changed')


def metadata_run(offline=False,pilot_only=False,max_assets=0):
    m=manifest();initialize_metadata(m)
    if sys.version!=m['acquisition_python']:raise ValueError('Acquisition Python changed')
    with lock(BASE/'metadata.lock'),closing(connect(METADATA)) as c:
        run_id='catchup-mb-'+str(time.time_ns());processed=errors=0;state='running'
        with c:c.execute('INSERT INTO acquisition_runs VALUES (?,?,?,?,?,?,?)',(run_id,'MusicBrainz',now(),None,state,canonical(dict(offline=offline,pilot_only=pilot_only)),'{}'))
        try:
            _,entities,_=mp.read_cache(mp.SEED)
            with mp.ProductionClient(mp.CACHE,offline=offline) as client:
                target=mp.CACHE/'requests';target.mkdir(exist_ok=True)
                for p in sorted(mp.SEED.glob('*.json')):
                    if not (target/p.name).exists():shutil.copyfile(p,target/p.name)
                for song in mp.queue(c):
                    if pilot_only and song['song_id'] not in m['pilot_sha256']:continue
                    if STOP or (max_assets and processed>=max_assets):state='interrupted';break
                    try:result=mp.acquire(song,client,entities)
                    except mp.APIError as exc:
                        if offline:raise
                        result=dict(song=song,asset_match_status='error',reason='api_or_cache_error',error=str(exc),error_cache_key=exc.cache_key,processed_at=mp.utc_now(),matcher_version=mp.VERSION)
                    sid=song['song_id']
                    if pilot_only:
                        p=ROOT/'data/experiments/phase2ar/results'/f'{sid}.json'
                        if sha(p)!=m['pilot_sha256'][sid]:raise ValueError('Pilot evidence changed')
                        archived=read(p)
                        for key in ('asset_match_status','supporting_recording_ids','supporting_artist_ids'):
                            if result.get(key)!=archived.get(key):raise ValueError('Frozen pilot replay differs')
                    result['catchup_population_sha256']=m['population_sha256']
                    mp.persist(c,result,directory=BASE/'metadata_results')
                    processed+=1;errors=errors+1 if result['asset_match_status']=='error' else 0
                    print(canonical(dict(song_id=sid,status=result['asset_match_status'],processed=processed,requests=client.network_requests,cache_hits=client.cache_hits)),flush=True)
                    if errors>=3:state='three_consecutive_errors';break
                else:state='complete'
                stats=dict(processed=processed,requests=client.network_requests,cache_hits=client.cache_hits)
        except BaseException:
            state='interrupted' if STOP else 'failed';raise
        finally:
            with c:c.execute('UPDATE acquisition_runs SET finished_at=?,status=?,summary_json=? WHERE run_id=?',(now(),state,canonical(locals().get('stats',dict(processed=processed))),run_id))


def lyric_assets(c):
    """Same supplementary-field projection as production snapshot; scoped DB only."""
    c.row_factory=sqlite3.Row
    songs={r['song_id']:dict(r,metadata=dict(durations=[],albums=[],dates=[],entities=[])) for r in c.execute('SELECT s.song_id,s.title,s.artist,s.first_chart_date FROM songs s JOIN study_population p USING(song_id) ORDER BY song_id')}
    for e in c.execute("""SELECT l.song_id,e.entity_type,e.entity_id,e.metadata_json,e.provenance_json
      FROM song_external_links l JOIN external_entities e ON e.provider=l.provider AND e.entity_type=l.entity_type AND e.entity_id=l.entity_id
      JOIN metadata_matches m ON m.song_id=l.song_id WHERE m.match_status='high_confidence' AND e.provider='MusicBrainz' AND e.entity_type IN ('recording','release','release-group')"""):
        if e['song_id'] not in songs:continue
        meta=songs[e['song_id']]['metadata']
        meta['entities'].append(dict(type=e['entity_type'],id=e['entity_id'],metadata_sha256=lp.digest(e['metadata_json'].encode()),provenance_sha256=lp.digest(e['provenance_json'].encode())))
        for v in json.loads(e['metadata_json']):
            if e['entity_type']=='recording' and isinstance(v.get('length'),(int,float)) and v['length']>0:meta['durations'].append(v['length']/1000)
            if e['entity_type'] in ('release','release-group') and v.get('title'):meta['albums'].append(v['title'])
            if v.get('date') or v.get('first-release-date'):meta['dates'].append(v.get('date') or v['first-release-date'])
    for song in songs.values():
        for k in ('durations','albums','dates'):song['metadata'][k]=sorted(set(song['metadata'][k]))
        song['metadata']['entities'].sort(key=lambda x:(x['type'],x['id']))
    c.row_factory=None
    return list(songs.values())


def initialize_lyrics(m):
    if LYRICS.exists():
        with closing(connect(LYRICS,True)) as c:check_lyrics_settings(c,m)
        return
    with closing(connect(METADATA,True)) as c:
        # Only the already replayed archived pilot may inform this fixed snapshot.
        if {r[0] for r in c.execute('SELECT song_id FROM metadata_matches')}!=set(m['pilot_sha256']):raise ValueError('Freeze lyrics assets before online metadata starts')
        songs=lyric_assets(c)
    gate=read(ROOT/'data/processed/lyrics_production_gate.json')
    if not gate['passed'] or gate['pipeline_sha256']!=lp.fingerprint():raise ValueError('Frozen reviewed gate mismatch')
    temp=BASE/'lyrics.initializing.db'
    if temp.exists():temp.unlink()
    with closing(connect(ROOT/'data/processed/lyrics.db',True)) as original,closing(sqlite3.connect(temp)) as c:
        for t in LYRIC_TABLES:c.execute(original.execute('SELECT sql FROM sqlite_master WHERE name=?',(t,)).fetchone()[0])
        with c:
            c.executemany('INSERT INTO production_assets VALUES (?,?)',[(s['song_id'],json.dumps(s,sort_keys=True,ensure_ascii=False)) for s in songs])
            c.executemany('INSERT INTO production_settings VALUES (?,?)',dict(population_sha256=m['population_sha256'],pipeline_sha256=lp.fingerprint(),assets_sha256=digest(canonical(songs)),gate=canonical(gate),metadata_policy='frozen pre-run archived pilot evidence only; later metadata cannot change lyrics decisions').items())
    os.replace(temp,LYRICS)


def check_lyrics_settings(c,m):
    settings=dict(c.execute('SELECT * FROM production_settings'))
    assets=[json.loads(r[0]) for r in c.execute('SELECT payload FROM production_assets ORDER BY song_id')]
    if settings['population_sha256']!=m['population_sha256'] or settings['pipeline_sha256']!=lp.fingerprint() or settings['assets_sha256']!=digest(canonical(assets)):raise ValueError('Lyrics configuration changed')
    if {s['song_id'] for s in assets}!={s['song_id'] for s in m['songs']}:raise ValueError('Lyrics population changed')
    return assets


def pending_assets(c,assets):
    done={r[0] for r in c.execute('SELECT song_id FROM production_results')}
    if not done<={s['song_id'] for s in assets}:raise ValueError('Out-of-scope acquisition result')
    return [s for s in assets if s['song_id'] not in done]


def lyrics_run(max_assets=0):
    m=manifest();lp.guards()
    if sys.version!=m['acquisition_python'] or unicodedata.unidata_version!=m['unicode']:raise ValueError('Acquisition runtime changed')
    with lock(ROOT/'data/processed/lyrics.lock'),closing(connect(LYRICS)) as c:
        assets=check_lyrics_settings(c,m);client=lp.legacy.Client(ROOT,user_agent=lp.UA)
        run_id=str(time.time_ns());processed=0;state='running'
        with c:c.execute('INSERT INTO production_runs VALUES (?,?,NULL,?,0,0)',(run_id,lp.stamp(),state))
        try:
            for s in pending_assets(c,assets):
                if STOP or (max_assets and processed>=max_assets):state='interrupted';break
                result,text=lp.acquire(s,client)
                result.update(pipeline_sha256=lp.fingerprint(),run_id=run_id,catchup_population_sha256=m['population_sha256'])
                lp.persist(c,result,text,ROOT);processed+=1
                with c:c.execute('UPDATE production_runs SET requests=?,processed=? WHERE run_id=?',(client.requests,processed,run_id))
                print(canonical(dict(time=now(),song_id=s['song_id'],status=result['status'],processed=processed,requests=client.requests)),flush=True)
            else:state='completed'
        except BaseException:state='failed';raise
        finally:
            with c:c.execute('UPDATE production_runs SET finished_at=?,state=?,requests=?,processed=? WHERE run_id=?',(lp.stamp(),state,client.requests,processed,run_id))


def lyric_results():
    with closing(connect(LYRICS,True)) as c:
        check_lyrics_settings(c,manifest())
        return {sid:json.loads(p) for sid,p in c.execute('SELECT * FROM production_results')}


def validate_acquisition(require_complete=False):
    from research import validate as validate_research
    with closing(connect(ROOT/'data/processed/research.db',True)) as original:
        validate_research(original,check_files=False)
    # The combined old+catch-up file census below replaces the old closed-corpus census.
    m=verify_protected();ids={s['song_id'] for s in m['songs']}
    with closing(connect(METADATA,True)) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Metadata DB invalid')
        matches=list(c.execute('SELECT song_id,result_path,result_sha256 FROM metadata_matches'))
        if not {r[0] for r in matches}<=ids:raise ValueError('Out-of-scope metadata')
        for sid,p,h in matches:
            if sha(ROOT/p)!=h:raise ValueError('Metadata evidence changed')
    rows=lyric_results();assets={s['song_id']:s for s in m['songs']};expected=set(m['old_lyrics_sha256'])
    if not set(rows)<=ids:raise ValueError('Out-of-scope lyric result')
    with closing(connect(LYRICS,True)) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Lyrics DB invalid')
    for sid,r in rows.items():
        if r['song_id']!=sid or (r['title'],r['artist'])!=(assets[sid]['title'],assets[sid]['artist']) or r['status'] not in lp.STATUSES:raise ValueError('Invalid lyric result')
        if r['pipeline_sha256']!=m['lyrics_pipeline_sha256'] or r['catchup_population_sha256']!=m['population_sha256']:raise ValueError('Unversioned result')
        if r['status']=='accepted':
            p=ROOT/'data/lyrics'/f'{sid}.txt'
            if p.is_symlink() or r['lyrics_path']!=str(p.relative_to(ROOT)) or sha(p)!=r['lyrics_sha256'] or r['identity_confidence']!='identity_high_confidence':raise ValueError('New lyric integrity failed')
            expected.add(sid)
        elif r['lyrics_path'] is not None or r['lyrics_sha256'] is not None:raise ValueError('Failed lyrics point to a file')
    if {p.stem for p in (ROOT/'data/lyrics').glob('*.txt')}!=expected:raise ValueError('Unmanifested/missing lyric files; resume interrupted acquisition')
    if require_complete and (len(matches)!=3654 or len(rows)!=3654):raise ValueError('Acquisition incomplete')
    return dict(metadata=len(matches),lyrics=len(rows),new_usable=len(expected)-len(m['old_lyrics_sha256']),protected_integrity='PASS')


def status():
    m=manifest();rows=lyric_results() if LYRICS.exists() else {};counts=Counter(r['status'] for r in rows.values())
    with closing(connect(METADATA,True)) as c:metadata=dict(c.execute('SELECT match_status,count(*) FROM metadata_matches GROUP BY match_status'))
    jobs={};all_features=set();any_features=set();failures=[]
    if CLASSIFIERS.exists():
        with closing(connect(CLASSIFIERS,True)) as c:
            for model,state,n in c.execute('SELECT model,status,count(*) FROM jobs GROUP BY model,status'):jobs.setdefault(model,{})[state]=n
            for sid,state in c.execute('SELECT song_id,processing_status FROM song_results'):
                if state=='complete':all_features.add(sid)
                if state in ('complete','partial'):any_features.add(sid)
            failures=[dict(song_id=s,model=model,error_type=e) for s,model,e in c.execute("SELECT song_id,model,error_type FROM jobs WHERE status='error'")]
    with closing(connect(ROOT/'data/processed/research.db',True)) as c:
        old_usable={r[0] for r in c.execute("SELECT song_id FROM lyrics_manifest WHERE lyrics_status='success'")}
        years={sid:int(dt[:4]) for sid,dt in c.execute('SELECT song_id,first_chart_date FROM songs')}
    final=set(m['new_population']);new_usable={s for s,r in rows.items() if r['status']=='accepted'}
    usable=(old_usable|new_usable)&final
    with closing(connect(ROOT/'data/processed/classifier_results.db',True)) as c:
        old_all={s for s,state in c.execute('SELECT song_id,processing_status FROM song_results') if state=='complete'}
    full=(old_all|all_features)&final;some=(old_usable|any_features)&final
    periods=[]
    for lo,hi,label in lp.PERIODS:
        pop={s for s in final if lo<=years[s]<=hi}
        periods.append(dict(period=label,songs=len(pop),usable=len(pop&usable),usable_percent=round(100*len(pop&usable)/len(pop),2),any_classifier=len(pop&some),any_classifier_percent=round(100*len(pop&some)/len(pop),2),all_42=len(pop&full),all_42_percent=round(100*len(pop&full)/len(pop),2)))
    terminal=all(sum(jobs.get(model,{}).get(s,0) for s in ('success','error'))==len(new_usable) for model in MODELS)
    complete=sum(metadata.values())==3654 and len(rows)==3654 and terminal
    return dict(generated_at=now(),status='COMPLETE' if complete else 'INCOMPLETE',population=3654,
                metadata=metadata,metadata_unprocessed=3654-sum(metadata.values()),metadata_accepted_percent=round(100*metadata.get('high_confidence',0)/3654,2),
                lyrics=dict(counts),lyrics_unprocessed=3654-len(rows),lyrics_usable_percent=round(100*len(new_usable)/3654,2),
                classifier_targets=len(new_usable),classifier_jobs=jobs,classifier_all_42=len(all_features),model_failures=failures,
                final_population=28041,snapshot_observations=81797,final_usable=len(usable),final_any_classifier=len(some),final_all_42=len(full),periods=periods)


def write_report():
    result=status()
    if result['status']=='COMPLETE' and not (BASE/'completion.json').exists():
        result['status']='INCOMPLETE';result['validation_pending']=True
    if (BASE/'completion.json').exists():
        result['completion_validation']=read(BASE/'completion.json')
        if result['completion_validation']['status']!='COMPLETE':result['status']='INCOMPLETE'
    save(ROOT/'reports/month_end_catchup.json',result)
    lines=['# Month-end catch-up checkpoint','',f"Generated {result['generated_at']}. Status: **{result['status']}**.",
      '', 'Scope: exactly 3,654 newly added identities; the 24,387 overlapping songs and all old results remain untouched.',
      'Source gaps are accepted: 818 months, 81,797 observations, 28,041 final identities. No rank-100 rows are invented.',
      '', '## Acquisition', '', '| Disposition | Metadata | Lyrics |','|---|---:|---:|']
    for label,meta,lyric in [('Accepted','high_confidence','accepted'),('Ambiguous/quarantined','ambiguous','quarantined'),('Wrong identity',None,'wrong_identity'),('Bad/missing text',None,'bad_missing_text'),('Not found','not_found','not_found'),('API error','error','error')]:
        lines.append(f"| {label} | {result['metadata'].get(meta,0) if meta else '—'} | {result['lyrics'].get(lyric,0)} |")
    lines += ['',f"Unprocessed: metadata {result['metadata_unprocessed']:,}; lyrics {result['lyrics_unprocessed']:,}.",
      f"Accepted metadata coverage: {result['metadata_accepted_percent']}%; usable lyrics: {result['lyrics_usable_percent']}% of the 3,654-song scope.",
      '', '## Classifiers', '',f"New usable targets: {result['classifier_targets']:,}. All 42 features: {result['classifier_all_42']:,}.",
      '', '| Model | Successful | Errors |','|---|---:|---:|']
    for model in MODELS:lines.append(f"| {model} | {result['classifier_jobs'].get(model,{}).get('success',0)} | {result['classifier_jobs'].get(model,{}).get('error',0)} |")
    lines += ['', 'Only new approved lyrics are classified, after acquisition finishes. Each failed model retains NULL features; other model results are kept.',
      '', '## Final population coverage', '',f"Usable lyrics: {result['final_usable']:,}; any classifier data: {result['final_any_classifier']:,}; all 42 features: {result['final_all_42']:,}.",
      'Coverage below uses first Billboard appearance and the full 28,041-song denominator, including pending catch-up work. The 2015–2019 subset overlaps 2010–2019.',
      '', '| Period | Songs | Usable lyrics | Lyrics % | Any classifier % | All 42 % |','|---|---:|---:|---:|---:|---:|']
    for r in result['periods']:lines.append(f"| {r['period']} | {r['songs']} | {r['usable']} | {r['usable_percent']} | {r['any_classifier_percent']} | {r['all_42_percent']} |")
    lines += ['', 'See [catch-up commands and storage](../../docs/month_end_catchup.md). Current public CSVs and research databases are unchanged. No genre assignment or longitudinal/COVID analysis is performed.',
      '', 'MusicBrainz replays the archived 19-song evidence before network work. Lyrics use the fixed pre-run metadata snapshot, so concurrent metadata progress cannot change matching inputs. The original matchers, clients, rates, cleaning, classifier checkpoints and token-weighted aggregation are unchanged.',
      '', 'Completion requires all acquisition dispositions, all four attempted model jobs per new usable lyric, verified files/outputs and protected-input hashes. Live counts alone do not establish successful completion.']
    if result['status']=='COMPLETE':lines += ['', 'Ready for genre assignment on the final 28,041-song population.']
    lp.atomic(ROOT/'archive/intermediate_reports/month_end_catchup.md',('\n'.join(lines)+'\n').encode())
    return result


def supervisor():
    manifest()
    with lock(BASE/'supervisor.lock'):
        children={};handles=[]
        try:
            for stage in ('metadata','lyrics'):
                f=(BASE/(stage+'.log')).open('a');handles.append(f)
                children[stage]=subprocess.Popen([sys.executable,'-u',str(Path(__file__)),stage],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
            save(BASE/'children.json',{k:dict(pid=p.pid,log=str((BASE/(k+'.log')).relative_to(ROOT))) for k,p in children.items()})
            code=children['lyrics'].wait()
            if code==0 and len(lyric_results())==3654:
                f=(BASE/'classifier.log').open('a');handles.append(f)
                children['classifier']=subprocess.Popen([str(VENV),'-u',str(ROOT/'src/month_end_catchup_classifier.py'),'run'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
                save(BASE/'children.json',{k:dict(pid=p.pid,log=str((BASE/(k+'.log')).relative_to(ROOT))) for k,p in children.items()})
            for p in children.values():p.wait()
            result=status();result['worker_exit_codes']={k:p.returncode for k,p in children.items()}
            result['validation']=validate_acquisition(result['status']=='COMPLETE')
            if CLASSIFIERS.exists():
                with (BASE/'classifier_validation.log').open('w') as f:
                    check=subprocess.run([str(VENV),str(ROOT/'src/month_end_catchup_classifier.py'),'validate'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
                result['classifier_validation_exit_code']=check.returncode
                if check.returncode:result['status']='INCOMPLETE'
            with (BASE/'tests.log').open('w') as f:
                check=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
            result['tests_exit_code']=check.returncode
            if check.returncode:result['status']='INCOMPLETE'
            with (BASE/'public_validation.log').open('w') as f:
                check=subprocess.run([sys.executable,'src/public_dataset.py','validate'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
            result['public_validation_exit_code']=check.returncode
            if check.returncode:result['status']='INCOMPLETE'
            save(BASE/'completion.json',result)
            write_report()
        except BaseException as exc:
            for p in children.values():
                if p.poll() is None:p.terminate()
            for p in children.values():p.wait()
            save(BASE/'supervisor_failure.json',dict(time=now(),error_type=type(exc).__name__))
            raise
        finally:
            for f in handles:f.close()


def main():
    def stop(signum,frame):
        global STOP
        STOP=True
        if args.command=='supervise':raise KeyboardInterrupt()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('prepare','metadata','lyrics','status','validate','report','supervise'))
    p.add_argument('--offline',action='store_true');p.add_argument('--pilot-only',action='store_true');p.add_argument('--max-assets',type=int,default=0)
    args=p.parse_args();signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    if args.command=='prepare':
        with lock(BASE/'prepare.lock'):
            m=freeze();initialize_metadata(m);metadata_run(True,True);initialize_lyrics(m)
            print(canonical(dict(population=3654,population_sha256=m['population_sha256'])))
    elif args.command=='metadata':metadata_run(args.offline,args.pilot_only,args.max_assets)
    elif args.command=='lyrics':lyrics_run(args.max_assets)
    elif args.command=='report':print(json.dumps(write_report(),indent=2))
    elif args.command=='status':print(json.dumps(status(),indent=2))
    elif args.command=='validate':print(json.dumps(validate_acquisition(True),indent=2))
    else:supervisor()

if __name__=='__main__':main()
