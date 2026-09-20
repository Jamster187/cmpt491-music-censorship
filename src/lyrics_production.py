"""Full-population LRCLIB acquisition. research.db is read-only; pilot tables are preserved."""
import argparse
from collections import Counter
import csv
import fcntl
import io
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import time
import urllib.parse

import lyrics_lrclib as legacy
import lyrics_lrclib_r as review
import lyrics_production_match as matcher
from lyrics_lrclib import ROOT, PERIODS, atomic, digest, guards, save_json, stamp

POPULATION=25363
UA='CMPT491-LyricsResearch/1.0 (https://github.com/Jamster187/cmpt491-music-censorship)'
STATUSES=('accepted','quarantined','wrong_identity','bad_missing_text','not_found','error')
BUNDLE=('lyrics_production.py','lyrics_production_match.py','lyrics_lrclib.py','lyrics_lrclib_r.py')
STOP=False


def fingerprint():
    return digest(b''.join((ROOT/'src'/p).read_bytes() for p in BUNDLE))


def connect(root=ROOT,readonly=False):
    c=sqlite3.connect((root/'data/processed/lyrics.db').as_uri()+('?mode=ro' if readonly else '?mode=rw'),uri=True,timeout=5)
    if not readonly:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS production_settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS production_assets (song_id TEXT PRIMARY KEY,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS production_results (song_id TEXT PRIMARY KEY,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS production_history (song_id TEXT NOT NULL,payload TEXT NOT NULL,replaced_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS production_runs (run_id TEXT PRIMARY KEY,started_at TEXT NOT NULL,finished_at TEXT,state TEXT NOT NULL,requests INTEGER NOT NULL,processed INTEGER NOT NULL);
        ''')
    return c


def gate(root=ROOT):
    rows=review.load(root);ledger=json.loads((root/'reports/lyrics_lrclib_r_review.json').read_text())
    reviews={v['song_id']:v for v in review.reconcile(rows,ledger)}
    cases=[]
    for s in rows:
        manual=reviews.get(s['song_id']);d=matcher.decide(s,s['raw_candidates'])
        expected='accepted' if s['status']=='success' else 'not_found' if s['status']=='not_found' else {'recoverable':'accepted','identity_ambiguous':'quarantined','wrong_identity':'wrong_identity','bad_text':'bad_missing_text','missing_text':'bad_missing_text'}[manual['outcome']]
        ref_id=manual['candidate_id'] if manual else (s.get('matched') or {}).get('id')
        comparison=None
        if d['status']=='accepted' and ref_id is not None:
            a=next(x for x in s['raw_candidates'] if x['id']==d['selected']);b=next(x for x in s['raw_candidates'] if x['id']==ref_id)
            compatible,ratio=matcher.compatible(review.raw_text(a),review.raw_text(b))
            comparison={'same_candidate':a['id']==b['id'],'normalized_sequence_ratio':ratio,'compatible':compatible}
        cases.append({'song_id':s['song_id'],'title':s['title'],'artist':s['artist'],'expected':expected,'automatic':d['status'],
                      'selected':d['selected'],'reviewed_candidate':ref_id,'reason':d['reason'],'source_comparison':comparison,
                      'false_accept':d['status']=='accepted' and expected!='accepted'})
    false=sum(x['false_accept'] for x in cases);accepted=sum(x['automatic']=='accepted' for x in cases)
    result={'matcher_version':matcher.VERSION,'pipeline_sha256':fingerprint(),
            'review_ledger_sha256':digest((root/'reports/lyrics_lrclib_r_review.json').read_bytes()),
            'pilot':200,'reviewed_usable':171,'automatic_accepted':accepted,'false_accepts':false,
            'automatic_precision_against_review':(accepted-false)/accepted if accepted else 0,
            'usable_recall_against_review':(accepted-false)/171,
            'exact_status_agreement':sum(x['expected']==x['automatic'] for x in cases),
            'counts':dict(Counter(x['automatic'] for x in cases)),
            'selected_candidate_changes':sum(x['source_comparison'] is not None and not x['source_comparison']['same_candidate'] for x in cases),
            'incompatible_selected_sources':sum(x['source_comparison'] is not None and not x['source_comparison']['compatible'] for x in cases),
            'cases':cases}
    result['passed']=false==0 and accepted>=145 and result['incompatible_selected_sources']==0
    save_json(root/'data/processed/lyrics_production_gate.json',result)
    text=['# LRCLIB production matcher: cached pilot safety check','',
          'This replay uses pure automatic rules, with no pilot-specific IDs or manual overrides. The approved reviews are comparison labels only. Zero LRCLIB requests.','',
          f"Automatic usable: **{accepted}/200**; reviewed usable: **171/200**. False accepts relative to the reviewed exclusions: **{false}**.",
          f"Acceptance precision against reviewed labels: **{100*result['automatic_precision_against_review']:.1f}%**; usable recall: **{100*result['usable_recall_against_review']:.2f}%**.",
          f"Exact disposition agreement: **{result['exact_status_agreement']}/200**; selected candidate changes: **{result['selected_candidate_changes']}**; incompatible selected texts against reviewed sources: **{result['incompatible_selected_sources']}**.",'',
          'Gate requires zero observed false accepts, no incompatible selected sources, and at least 145 automatic usable assets. This is a precision-first engineering check on the development pilot, not independent test-set evidence or a statistical guarantee. The 29 reviewed exclusions are a small negative set.','',
          'Candidate changes were inspected through metadata, word counts, sequence differences and short local text excerpts. Review found that a plural Remixes album label escaped the initial singular-only warning rule; plural detection was fixed and regression-tested before scaling. Final differences were limited transcription/formatting changes or compatible repetitions; no new obvious wrong-song/artist or materially defective acceptance was identified. Duration disagreements remain version uncertainty, not evidence of recording-level verification.','',
          'The production run carries forward all 171 approved usable pilot texts as reviewed decisions and preserves the other 29 reviewed dispositions. Automatic replay performance is reported separately; manual overrides do not inflate it.','',
          '## Disagreements','', '| Billboard title | Reviewed disposition | Automatic disposition | Reason |','|---|---|---|---|']
    for x in cases:
        if x['expected']!=x['automatic']:text.append('| '+' | '.join(str(x[k]).replace('|','/') for k in ('title','expected','automatic','reason'))+' |')
    atomic(root/'reports/lyrics_production_pilot.md',('\n'.join(text)+'\n').encode())
    buf=io.StringIO();fields=['song_id','title','artist','expected','automatic','selected','reviewed_candidate','reason','false_accept']
    writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for x in cases:writer.writerow({k:x[k] for k in fields})
    atomic(root/'reports/lyrics_production_pilot.csv',buf.getvalue().encode())
    return result


def snapshot(root=ROOT):
    c=sqlite3.connect((root/'data/processed/research.db').as_uri()+'?mode=ro',uri=True,timeout=2);c.row_factory=sqlite3.Row
    try:
        songs={r['song_id']:dict(r,metadata={'durations':[],'albums':[],'dates':[],'entities':[]}) for r in c.execute('SELECT s.song_id,s.title,s.artist,s.first_chart_date FROM songs s JOIN study_population p USING(song_id) ORDER BY s.song_id')}
        if len(songs)!=POPULATION:raise ValueError('Unexpected study population size')
        query="""SELECT l.song_id,e.entity_type,e.entity_id,e.metadata_json,e.provenance_json
        FROM song_external_links l JOIN external_entities e
        ON e.provider=l.provider AND e.entity_type=l.entity_type AND e.entity_id=l.entity_id
        JOIN metadata_matches m ON m.song_id=l.song_id
        WHERE m.match_status='high_confidence' AND e.provider='MusicBrainz'
        AND e.entity_type IN ('recording','release','release-group')"""
        for e in c.execute(query):
            if e['song_id'] not in songs:continue
            m=songs[e['song_id']]['metadata']
            m['entities'].append({'type':e['entity_type'],'id':e['entity_id'],'metadata_sha256':digest(e['metadata_json'].encode()),'provenance_sha256':digest(e['provenance_json'].encode())})
            for v in json.loads(e['metadata_json']):
                if e['entity_type']=='recording' and isinstance(v.get('length'),(int,float)) and v['length']>0:m['durations'].append(v['length']/1000)
                if e['entity_type'] in ('release','release-group') and v.get('title'):m['albums'].append(v['title'])
                if v.get('date') or v.get('first-release-date'):m['dates'].append(v.get('date') or v['first-release-date'])
        for s in songs.values():
            for k in ('durations','albums','dates'):s['metadata'][k]=sorted(set(s['metadata'][k]))
            s['metadata']['entities'].sort(key=lambda x:(x['type'],x['id']))
        return list(songs.values())
    finally:c.close()


def initialize(c,root=ROOT):
    setting=c.execute("SELECT value FROM production_settings WHERE key IN ('current_pipeline_sha256','pipeline_sha256') ORDER BY key LIMIT 1").fetchone()
    if setting:
        if setting[0]!=fingerprint():raise ValueError('Production code changed; explicit version migration required')
        if c.execute('SELECT count(*) FROM production_assets').fetchone()[0]!=POPULATION:raise ValueError('Incomplete population snapshot')
        return
    g=json.loads((root/'data/processed/lyrics_production_gate.json').read_text())
    if not g['passed'] or g['pipeline_sha256']!=fingerprint() or g['review_ledger_sha256']!=digest((root/'reports/lyrics_lrclib_r_review.json').read_bytes()):raise ValueError('Run current cached pilot gate first')
    songs=snapshot(root)
    with c:
        c.executemany('INSERT INTO production_assets VALUES (?,?)',[(s['song_id'],json.dumps(s,ensure_ascii=False,sort_keys=True)) for s in songs])
        values={'version':matcher.VERSION,'pipeline_sha256':fingerprint(),'snapshot_at':stamp(),'population_sha256':digest(json.dumps(songs,ensure_ascii=False,sort_keys=True).encode()),'gate':json.dumps(g,ensure_ascii=False),'authorization':'User approved full 25363-asset LRCLIB local research acquisition after reviewed pilot','python':sys.version,'unicode':matcher.unicodedata.unidata_version}
        c.executemany('INSERT INTO production_settings VALUES (?,?)',values.items())


def persist(c,r,text=None,root=ROOT):
    if r['status'] not in STATUSES:raise ValueError('Unsupported production status')
    if (r['status']=='accepted') != (text is not None):raise ValueError('Accepted rows require local text')
    if text is not None:
        if not text.strip():raise ValueError('Empty success refused')
        path=root/'data/lyrics'/(r['song_id']+'.txt');data=text.encode()
        if path.exists() and (path.is_symlink() or path.read_bytes()!=data):raise ValueError('Refuse differing canonical lyrics overwrite')
        if not path.exists():atomic(path,data)
        r['lyrics_path']=str(path.relative_to(root));r['lyrics_sha256']=digest(data)
    else:r.update(lyrics_path=None,lyrics_sha256=None)
    with c:
        old=c.execute('SELECT payload FROM production_results WHERE song_id=?',(r['song_id'],)).fetchone()
        if old:
            if json.loads(old[0])['status']=='accepted':raise ValueError('Successful result replacement refused')
            c.execute('INSERT INTO production_history VALUES (?,?,?)',(r['song_id'],old[0],stamp()))
        c.execute('INSERT INTO production_results VALUES (?,?) ON CONFLICT(song_id) DO UPDATE SET payload=excluded.payload',(r['song_id'],json.dumps(r,ensure_ascii=False,sort_keys=True)))


def seed_pilot(c,root=ROOT):
    if c.execute("SELECT value FROM production_settings WHERE key='pilot_seeded'").fetchone():return
    rows=review.load(root);ledger=json.loads((root/'reports/lyrics_lrclib_r_review.json').read_text())
    reviewed={v['song_id']:v for v in review.reconcile(rows,ledger)}
    old_reviews=json.loads((root/'reports/lyrics_pilot_review.json').read_text())
    # Pilot ledger format is a list of checksum-bound text inspections.
    if isinstance(old_reviews,dict):old_reviews=old_reviews.get('reviews',[])
    notes={v['song_id']:v for v in old_reviews}
    for s in rows:
        if c.execute('SELECT 1 FROM production_results WHERE song_id=?',(s['song_id'],)).fetchone():continue
        d=matcher.decide(s,s['raw_candidates']);manual=reviewed.get(s['song_id']);text=None
        basis='reviewed_pilot';selected=None;warnings=[];version=[];changes=[]
        if s['status']=='success':
            status='accepted';selected=s['matched']['id'];path=root/s['lyrics_path']
            if path.is_symlink() or digest(path.read_bytes())!=s['lyrics_sha256']:raise ValueError('Prior pilot success checksum mismatch')
            text=path.read_text();identity='identity_high_confidence';quality=d['text_quality'];warnings=d['text_warnings'];version=d['version_warnings'];reason='Carry forward approved original pilot success'
        elif manual:
            status={'recoverable':'accepted','identity_ambiguous':'quarantined','wrong_identity':'wrong_identity','bad_text':'bad_missing_text','missing_text':'bad_missing_text'}[manual['outcome']]
            selected=manual['candidate_id'];identity=manual['identity_confidence'];quality=manual['text_quality'];warnings=manual['warnings'];version=[w for w in warnings if 'version' in w or 'censorship' in w];changes=manual['cleaning_steps'];reason=manual['reason']
            if status=='accepted':text=manual['cleaned_text']
        else:status='not_found';identity='identity_ambiguous';quality='text_missing';reason='Carry forward reviewed empty search'
        chosen=next((x for x in s['raw_candidates'] if x['id']==selected),None)
        r={k:v for k,v in s.items() if k!='raw_candidates'}
        r.update(d,status=status,selected=selected,reason=reason,identity_confidence=identity,text_quality=quality,
                 text_warnings=warnings,version_warnings=version,cleaning_steps=changes,source='LRCLIB',decision_basis=basis,
                 matcher_version=matcher.VERSION,processed_at=stamp(),original_pilot_review=notes.get(s['song_id']),
                 reviewed_ledger_sha256=digest((root/'reports/lyrics_lrclib_r_review.json').read_bytes()),
                 matched={k:chosen.get(k) for k in ('id','trackName','artistName','albumName','duration','instrumental')} if chosen else None)
        if chosen:r['source_text_sha256']=digest(review.raw_text(chosen).encode())
        persist(c,r,text,root)
    with c:c.execute("INSERT INTO production_settings VALUES ('pilot_seeded',?)",(stamp(),))


def validate(c,root=ROOT):
    assets={sid:json.loads(p) for sid,p in c.execute('SELECT * FROM production_assets')};expected=set()
    for sid,payload in c.execute('SELECT * FROM production_results'):
        r=json.loads(payload)
        if sid!=r['song_id'] or sid not in assets or (r['title'],r['artist'])!=(assets[sid]['title'],assets[sid]['artist']):raise ValueError('Production asset identity mismatch')
        if r['status']=='accepted':
            path=root/'data/lyrics'/(sid+'.txt');expected.add(path)
            if r['lyrics_path']!=str(path.relative_to(root)) or path.is_symlink() or digest(path.read_bytes())!=r['lyrics_sha256']:raise ValueError('Canonical lyric integrity failed')
    actual=set((root/'data/lyrics').glob('*.txt'))
    # A crash between file and DB commit may leave one deterministic orphan; run recovers it before validation.
    if actual!=expected:raise ValueError('Unmanifested/missing canonical lyric files; resume acquisition to recover an interrupted write')
    return len(expected)


def acquire(s,client):
    records=[];candidates=[];failure=None
    for params in ({'track_name':s['title'],'artist_name':s['artist']},{'track_name':s['title']}):
        record=client.search(params);records.append(record)
        try:candidates=legacy.parse(record)
        except (ValueError,KeyError,TypeError) as ex:failure=str(ex);break
        if candidates:break
    if failure:d={'status':'error','reason':failure,'selected':None,'candidate_count':len(candidates),'candidate_found':bool(candidates),'identity_confidence':'identity_ambiguous','text_quality':'text_unassessed','version_warnings':[],'text_warnings':[],'candidates':[]}
    else:d=matcher.decide(s,candidates)
    chosen=next((x for x in candidates if x['id']==d['selected']),None)
    result=dict(s,**d,source='LRCLIB',matcher_version=matcher.VERSION,decision_basis='automatic',processed_at=stamp(),
                retrievals=[{k:v for k,v in rec.items() if k!='body'} for rec in records],
                matched={k:chosen.get(k) for k in ('id','trackName','artistName','albumName','duration','instrumental')} if chosen else None)
    if chosen:result['source_text_sha256']=digest(review.raw_text(chosen).encode())
    text=review.clean(review.raw_text(chosen),s['title'],s['artist'])[0] if d['status']=='accepted' else None
    return result,text


def retry_error_cache(r,root=ROOT):
    for ref in r['retrievals']:
        path=root/'data/cache/lrclib'/(digest(ref['url'].encode())+'.json')
        if path.exists():
            cached=json.loads(path.read_text())
            if cached['status']!=200:os.replace(path,path.with_name(path.stem+'-terminal-error-'+str(time.time_ns())+'.json'))


def run(max_assets=None,retry_errors=False,root=ROOT):
    global STOP
    guards(root);c=connect(root);initialize(c,root);seed_pilot(c,root)
    client=legacy.Client(root,user_agent=UA);run_id=str(time.time_ns());processed=0;started=stamp();state='running'
    with c:c.execute('INSERT INTO production_runs VALUES (?,?,NULL,?,0,0)',(run_id,started,state))
    try:
        songs=[json.loads(p) for p, in c.execute('SELECT payload FROM production_assets ORDER BY song_id')]
        for s in songs:
            if STOP or (max_assets is not None and processed>=max_assets):state='interrupted';break
            old=c.execute('SELECT payload FROM production_results WHERE song_id=?',(s['song_id'],)).fetchone()
            if old:
                old=json.loads(old[0])
                if not (retry_errors and old['status']=='error'):continue
                retry_error_cache(old,root)
            result,text=acquire(s,client)
            result.update(pipeline_sha256=fingerprint(),run_id=run_id)
            persist(c,result,text,root);processed+=1
            with c:c.execute('UPDATE production_runs SET requests=?,processed=? WHERE run_id=?',(client.requests,processed,run_id))
            print(json.dumps({'time':stamp(),'song_id':s['song_id'],'status':result['status'],'processed_this_run':processed,'requests_this_run':client.requests}),flush=True)
        else:state='completed'
        validate(c,root)
    except BaseException:
        state='failed';raise
    finally:
        with c:c.execute('UPDATE production_runs SET finished_at=?,state=?,requests=?,processed=? WHERE run_id=?',(stamp(),state,client.requests,processed,run_id))
        c.close()
        report(root)


def report(root=ROOT):
    c=connect(root,readonly=True)
    assets=[json.loads(p) for p, in c.execute('SELECT payload FROM production_assets')]
    rows=[json.loads(p) for p, in c.execute('SELECT payload FROM production_results')]
    runs=[dict(zip(('run_id','started_at','finished_at','state','requests','processed'),r)) for r in c.execute('SELECT * FROM production_runs ORDER BY run_id')]
    gate_data=json.loads(c.execute("SELECT value FROM production_settings WHERE key='gate'").fetchone()[0]);c.close()
    indexed={r['song_id']:r for r in rows};counts=Counter(r['status'] for r in rows);usable=[r for r in rows if r['status']=='accepted']
    def coverage(lo,hi,label):
        group=[s for s in assets if lo<=int(s['first_chart_date'][:4])<=hi];done=[indexed[s['song_id']] for s in group if s['song_id'] in indexed];ok=sum(r['status']=='accepted' for r in done)
        return {'period':label,'population':len(group),'attempted':len(done),'usable':ok,'population_coverage_percent':round(100*ok/len(group),2) if group else None,'attempted_coverage_percent':round(100*ok/len(done),2) if done else None}
    data={'generated_at':stamp(),'population':len(assets),'attempted':len(rows),'candidate_found':sum(r['candidate_found'] for r in rows),'counts':dict(counts),
          'automatically_accepted':sum(r['decision_basis']=='automatic' for r in usable),'reviewed_pilot_accepted':sum(r['decision_basis']=='reviewed_pilot' for r in usable),
          'usable':len(usable),'local_lyrics_files':len(list((root/'data/lyrics').glob('*.txt'))),
          'periods':[coverage(lo,hi,label) for lo,hi,label in PERIODS],'years':[coverage(y,y,str(y)) for y in range(1958,2027)],
          'accepted_version_warnings':dict(Counter(w for r in usable for w in set(r['version_warnings']))),
          'accepted_text_warnings':dict(Counter(w for r in usable for w in set(r['text_warnings']))),
          'accepted_text_quality':dict(Counter(r['text_quality'] for r in usable)),
          'loss_reasons':dict(Counter(r['reason'] for r in rows if r['status']!='accepted')),'runs':runs,
          'gate':{k:v for k,v in gate_data.items() if k!='cases'}}
    save_json(root/'data/processed/lyrics_production_summary.json',data)
    lines=['# LRCLIB full-population acquisition','',f"Generated {data['generated_at']}. Population: **{len(assets):,}**. Attempted: **{len(rows):,}**. Candidate found: **{data['candidate_found']:,}**.",'',
           f"Usable: **{len(usable):,}** ({data['automatically_accepted']:,} automatic, {data['reviewed_pilot_accepted']} approved pilot). Canonical local files: **{data['local_lyrics_files']:,}**.",'',
           '| Disposition | Assets |','|---|---:|']
    lines += [f'| {k} | {counts[k]} |' for k in STATUSES]
    lines += ['', '## Coverage','', 'Population coverage includes unattempted songs in the denominator. Attempted coverage is provisional and not a full-population estimate. Years and periods use first Billboard appearance. The 2015–2019 subset overlaps 2010–2019.','',
              '| Period | Population | Attempted | Usable | Population coverage | Attempted coverage |','|---|---:|---:|---:|---:|---:|']
    for p in data['periods']+data['years']:lines.append(f"| {p['period']} | {p['population']} | {p['attempted']} | {p['usable']} | {p['population_coverage_percent']}% | {p['attempted_coverage_percent']}% |")
    lines+=['','## Quality','',f"[Automatic pilot check](lyrics_production_pilot.md): {gate_data['automatic_accepted']}/200 automatic acceptances, {gate_data['false_accepts']} observed false accepts against reviewed labels. This is development-pilot evidence, not independent validation.",'',
            'Warning counts below are accepted assets carrying each warning, including alternative-candidate evidence; categories overlap. Formatting cleanup is not a content defect. Reviewed pilot warning names are preserved.','', '| Accepted version warning | Assets |','|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in sorted(data['accepted_version_warnings'].items())]
    lines += ['', '| Accepted text warning | Assets |','|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in sorted(data['accepted_text_warnings'].items())]
    lines += ['', '| Remaining loss reason | Assets |','|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in sorted(data['loss_reasons'].items())]
    lines += ['', '## Storage and resume','',
              '- Corpus: `data/lyrics/<song_id>.txt`.',
              '- State: `data/processed/lyrics.db`, `production_assets`, `production_results`, `production_history`, `production_runs`, `production_settings`. Original pilot tables are preserved.',
              '- Private responses and quarantine: `data/cache/lrclib/`. Result provenance references exact URL/cache hashes and retrieval times; raw lyric text is not duplicated in reports.',
              '- Resume: `python3 src/lyrics_production.py run`. Already persisted outcomes are skipped. Terminal API failures are retried only with `python3 src/lyrics_production.py run --retry-errors`.',
              '- Read-only corpus validation: `python3 src/lyrics_production.py validate`. Progress report: `python3 src/lyrics_production.py report`.',
              '- Sequential identified requests, 500 ms minimum extra delay, persistent Retry-After cooldown, bounded retries, per-song file then SQLite persistence, exclusive lyrics-worker lock. SIGINT/SIGTERM finish the current asset and stop; SIGKILL is recoverable from cache/deterministic files.',
              '- `research.db` is never written; metadata is a frozen read-only snapshot. No classifier or historical analysis is run.', '', '## Worker runs','', '| Started | Finished | State | New attempts | HTTP requests |','|---|---|---|---:|---:|']
    lines += [f"| {r['started_at']} | {r['finished_at'] or ''} | {r['state']} | {r['processed']} | {r['requests']} |" for r in runs]
    atomic(root/'reports/lyrics_production_status.md',('\n'.join(lines)+'\n').encode())
    return data


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('gate','run','validate','report'))
    parser.add_argument('--max-assets',type=int);parser.add_argument('--retry-errors',action='store_true');args=parser.parse_args()
    guards()
    def stop(signum,frame):
        global STOP
        STOP=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    if args.command=='report':print(json.dumps(report(),ensure_ascii=False,indent=2))
    elif args.command=='validate':
        c=connect(readonly=True);print('Validated production lyric files:',validate(c));c.close()
    else:
        with (ROOT/'data/processed/lyrics.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if args.command=='gate':print(json.dumps({k:v for k,v in gate().items() if k!='cases'},indent=2))
            else:run(args.max_assets,args.retry_errors)
