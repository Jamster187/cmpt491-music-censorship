"""Synchronize completed production dispositions into a staged research database.

Copies metadata/path references only; never imports lyric text or cache bodies.
"""
from contextlib import ExitStack
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

import lyrics_production as production
import lyrics_resume
import research
from lyrics_lrclib import ROOT, digest, stamp

COLUMNS = ('song_id','lyrics_status','lyrics_source','source_identifier','match_status',
           'matched_title','matched_artist','lyrics_path','lyrics_sha256','retrieved_at',
           'failure_reason','provenance_json')


def manifest_row(r, payload_sha256, pipeline):
    if r['status'] not in production.STATUSES:
        raise ValueError('Unsupported production disposition')
    ok=r['status']=='accepted'
    matched=r.get('matched') or {}
    retrievals=[{k:v[k] for k in ('url','sha256','status','retrieved_at') if k in v} for v in r.get('retrievals',[])]
    provenance=dict(sidecar='data/processed/lyrics.db',table='production_results',
                    production_disposition=r['status'],payload_sha256=payload_sha256,
                    pipeline_sha256=pipeline,matcher_version=r['matcher_version'],
                    run_id=r.get('run_id'),decision_basis=r['decision_basis'],
                    identity_confidence=r['identity_confidence'],text_quality=r['text_quality'],
                    processed_at=r['processed_at'],retrievals=retrievals,
                    source_text_sha256=r.get('source_text_sha256'),
                    reviewed_ledger_sha256=r.get('reviewed_ledger_sha256'),
                    text_warnings=r.get('text_warnings',[]),version_warnings=r.get('version_warnings',[]))
    retrieved=max((v['retrieved_at'] for v in retrievals if v.get('retrieved_at')),default=r['processed_at'])
    if ok and (not r.get('lyrics_path') or not r.get('lyrics_sha256') or matched.get('id') is None):
        raise ValueError('Incomplete successful provenance')
    if not ok and (r.get('lyrics_path') is not None or r.get('lyrics_sha256') is not None):
        raise ValueError('Unsuccessful disposition has canonical text pointer')
    return (r['song_id'],'success' if ok else r['status'],'LRCLIB',
            str(matched['id']) if matched.get('id') is not None else None,
            'high_confidence' if ok else r['identity_confidence'],
            matched.get('trackName'),matched.get('artistName'),r.get('lyrics_path'),r.get('lyrics_sha256'),
            retrieved,None if ok else r['reason'],json.dumps(provenance,sort_keys=True,ensure_ascii=False))


def synchronize(c, local, root=ROOT):
    """One transaction, called on a temporary copy; safe to rerun unchanged."""
    identities={sid:(title,artist,date) for sid,title,artist,date in c.execute(
        'SELECT s.song_id,s.title,s.artist,s.first_chart_date FROM songs s JOIN study_population p USING(song_id)')}
    assets={sid:json.loads(payload) for sid,payload in local.execute('SELECT * FROM production_assets')}
    payloads=dict(local.execute('SELECT * FROM production_results'))
    if not (set(identities)==set(assets)==set(payloads)):
        raise ValueError('Production must disposition the entire exact study population')
    if local.execute("SELECT count(*) FROM production_runs WHERE state='running'").fetchone()[0]:
        raise ValueError('Production worker is still running')
    production.validate(local,root)
    lyrics_resume.verify_preserved(local)
    old_versions=dict(local.execute('SELECT song_id,pipeline_sha256 FROM production_result_implementations'))
    current=dict(local.execute('SELECT * FROM production_settings'))['current_pipeline_sha256']
    desired=[]
    for sid in sorted(identities):
        r=json.loads(payloads[sid]);a=assets[sid]
        expected=identities[sid]
        if r['song_id']!=sid or a['song_id']!=sid or expected!=(r['title'],r['artist'],r['first_chart_date']) or expected!=(a['title'],a['artist'],a['first_chart_date']):
            raise ValueError('Production/research identity mismatch')
        pipeline=old_versions.get(sid) or r.get('pipeline_sha256')
        if pipeline not in (lyrics_resume.OLD_PIPELINE,current):raise ValueError('Unknown result implementation')
        desired.append(manifest_row(r,digest(payloads[sid].encode()),pipeline))
    existing={row[0]:row for row in c.execute('SELECT '+','.join(COLUMNS)+' FROM lyrics_manifest')}
    if set(existing)!=set(identities):raise ValueError('Manifest identity set differs')
    for row in desired:
        old=existing[row[0]]
        if old[1]=='success' and (row[1]!='success' or old[7:9]!=row[7:9]):
            raise ValueError('Conflicting existing successful lyrics')
    version=c.execute("SELECT value FROM build_metadata WHERE key='schema_version'").fetchone()
    if version is None or version[0] not in ('1','2'):raise ValueError('Unsupported research schema')
    if version[0]=='2' and all(existing[row[0]]==row for row in desired):return 0
    try:
        c.execute('BEGIN IMMEDIATE')
        if version[0]=='1':
            ddl=research.SCHEMA.split('CREATE TABLE lyrics_manifest (',1)[1].split(';',1)[0]
            c.execute('CREATE TABLE lyrics_manifest_next ('+ddl)
            c.execute('INSERT INTO lyrics_manifest_next SELECT * FROM lyrics_manifest')
            c.execute('DROP TABLE lyrics_manifest')
            c.execute('ALTER TABLE lyrics_manifest_next RENAME TO lyrics_manifest')
            c.execute("UPDATE build_metadata SET value='2' WHERE key='schema_version'")
        c.executemany('UPDATE lyrics_manifest SET '+','.join(k+'=?' for k in COLUMNS[1:])+' WHERE song_id=?',
                      [row[1:]+row[:1] for row in desired])
        metadata=dict(at=stamp(),importer_sha256=digest(Path(__file__).read_bytes()),
                      source='data/processed/lyrics.db:production_results',rows=len(desired),
                      result_set_sha256=digest(json.dumps(sorted((sid,digest(p.encode())) for sid,p in payloads.items())).encode()),
                      schema_from=version[0],schema_to='2')
        c.execute('INSERT INTO build_metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                  ('lyrics_production_import',json.dumps(metadata,sort_keys=True)))
        if c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Imported foreign key failure')
        c.commit()
    except BaseException:
        c.rollback();raise
    return len(desired)


def main():
    production.guards()
    with ExitStack() as stack:
        for path in ('data/processed/lyrics.lock','data/cache/musicbrainz_production/client.lock'):
            lock=stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        local=production.connect(readonly=True);stack.callback(local.close)
        source=research.connect(readonly=True);stack.callback(source.close)
        if source.execute("SELECT count(*) FROM acquisition_runs WHERE status='running'").fetchone()[0]:
            raise ValueError('Metadata run still marked running')
        original=research.sha(research.DATABASE)
        with tempfile.TemporaryDirectory(prefix='.lyrics-import-',dir=ROOT/'data/processed') as temp:
            staged=Path(temp)/'research.db'
            with sqlite3.connect(str(staged)) as c:source.backup(c)
            c=research.connect(staged)
            try:
                changed=synchronize(c,local)
                print('Standard staged research validation:',research.validate(c))
                # Also proves every manifest field reconciles deterministically.
                if synchronize(c,local)!=0:raise ValueError('Import is not idempotent')
            finally:c.close()
            if research.sha(research.DATABASE)!=original:raise ValueError('Research changed during import')
            if changed:
                archive=ROOT/'data/processed/backups'/('research-before-lyrics-'+original+'.db')
                archive.parent.mkdir(parents=True,exist_ok=True)
                if not archive.exists():shutil.copy2(research.DATABASE,archive)
                if research.sha(archive)!=original:raise ValueError('Backup integrity failure')
                with staged.open('rb') as f:os.fsync(f.fileno())
                source.close()
                os.replace(staged,research.DATABASE)
            print('Synchronized production manifest rows:',changed)


if __name__=='__main__':main()
