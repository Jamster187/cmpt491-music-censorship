"""Catch-up boundaries, snapshot parity and use of the frozen production engine."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import month_end_catchup as c
import month_end_catchup_classifier as cc
import classifier_production as runner
from classifier_production_store import canonical,digest,sha
from research import SCHEMA


class CatchupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()

    def test_skip_every_persisted_disposition(self):
        db=sqlite3.connect(':memory:');db.execute('CREATE TABLE production_results(song_id TEXT,payload TEXT)')
        assets=[dict(song_id=str(i)) for i in range(7)]
        for i,state in enumerate(c.lp.STATUSES):db.execute('INSERT INTO production_results VALUES (?,?)',(str(i),json.dumps(dict(status=state))))
        self.assertEqual(c.pending_assets(db,assets),[assets[-1]])
        db.execute("INSERT INTO production_results VALUES ('old-population','{}')")
        with self.assertRaises(ValueError):c.pending_assets(db,assets)
        db.close()

    def test_metadata_sidecar_contains_only_selected_identities(self):
        m=dict(population_sha256='frozen',songs=[dict(song_id='new',title='New',artist='Artist',normalized_title='new',normalized_artist='artist',first_chart_date='2000-01-01',last_chart_date='2000-02-01',best_chart_rank=1,chart_observation_count=2,distinct_chart_dates=2,total_chart_points=200,snapshot_months=['2000-01','2000-02'])])
        dest=self.root/'metadata.db'
        with patch.object(c,'BASE',self.root),patch.object(c,'METADATA',dest):
            c.initialize_metadata(m);before=sha(dest);c.initialize_metadata(m);self.assertEqual(before,sha(dest))
            with sqlite3.connect(dest) as db:
                self.assertEqual(db.execute('SELECT song_id FROM songs').fetchall(),[('new',)])
                self.assertEqual(db.execute('SELECT * FROM study_population').fetchall(),[('new','2000-01','2000-02',2)])

    def test_supplementary_projection_matches_frozen_runner(self):
        folder=self.root/'data/processed';folder.mkdir(parents=True)
        db=sqlite3.connect(folder/'research.db');db.executescript(SCHEMA)
        db.execute("INSERT INTO songs VALUES ('s','Title','Artist','title','artist','2000-01-01','2000-02-01',1,2,2,200)")
        db.execute("INSERT INTO study_population VALUES ('s','2000-01','2000-02',2)")
        db.execute("INSERT INTO metadata_matches VALUES ('s','MusicBrainz','high_confidence','reason','v','p','h','time','{}')")
        for kind,identifier,metadata in [('recording','r',[dict(length=123456,**{'first-release-date':'1999'})]),('release','a',[dict(title='Album',date='1999-12')])]:
            db.execute('INSERT INTO external_entities VALUES (?,?,?,?,?)',('MusicBrainz',kind,identifier,json.dumps(metadata),'[]'))
            db.execute('INSERT INTO song_external_links VALUES (?,?,?,?,?)',('s','MusicBrainz',kind,identifier,'context'))
        db.commit()
        with patch.object(c.lp,'POPULATION',1):expected=c.lp.snapshot(self.root)
        self.assertEqual(c.lyric_assets(db),expected);db.close()

    def test_lyrics_snapshot_is_checksum_frozen(self):
        db=sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE production_assets(song_id TEXT,payload TEXT); CREATE TABLE production_settings(key TEXT,value TEXT);')
        assets=[dict(song_id='new',metadata=dict(durations=[]))];m=dict(population_sha256='p',songs=assets)
        db.execute('INSERT INTO production_assets VALUES (?,?)',('new',json.dumps(assets[0])))
        db.executemany('INSERT INTO production_settings VALUES (?,?)',dict(population_sha256='p',pipeline_sha256=c.lp.fingerprint(),assets_sha256=digest(canonical(assets))).items())
        self.assertEqual(c.check_lyrics_settings(db,m),assets)
        db.execute("UPDATE production_assets SET payload=?",(json.dumps(dict(song_id='new',metadata=dict(durations=[123]))),))
        with self.assertRaises(ValueError):c.check_lyrics_settings(db,m)
        db.close()

    def test_classifier_adapter_changes_scope_only_and_restores(self):
        old=dict(scope='full',dependencies={'torch':'frozen'},files={'engine':'hash'})
        dbpath=self.root/'original.db'
        with sqlite3.connect(dbpath) as db:
            db.execute('CREATE TABLE run_config(id INTEGER,configuration TEXT)');db.execute('INSERT INTO run_config VALUES (1,?)',(canonical(old),))
        m=dict(population_sha256='population',implementation_sha256={n:'adapter' for n in c.ADAPTER_FILES})
        orig_targets=runner.targets;orig_worker=runner.worker;orig_process=runner.process
        with patch.object(runner,'configuration',return_value=old) as conf,patch.object(c,'manifest',return_value=m),patch.object(c,'connect',side_effect=lambda *args:sqlite3.connect(dbpath)),patch.object(c,'read',return_value={'configuration_sha256':digest(canonical(old))}):
            with cc.scoped_runner() as result:
                self.assertEqual(result['dependencies'],old['dependencies']);self.assertEqual(result['files'],old['files'])
                self.assertIs(runner.worker,orig_worker);self.assertIs(runner.process,orig_process)
                self.assertEqual(runner.configuration('month-end-catchup-v1'),result)
                with self.assertRaises(ValueError):runner.targets('full')
            self.assertIs(runner.targets,orig_targets);self.assertIs(runner.configuration,conf)

    def test_classifier_refuses_changed_frozen_runtime(self):
        dbpath=self.root/'original.db'
        with sqlite3.connect(dbpath) as db:
            db.execute('CREATE TABLE run_config(id INTEGER,configuration TEXT)');db.execute('INSERT INTO run_config VALUES (1,?)',(canonical({'scope':'full'}),))
        with patch.object(runner,'configuration',return_value={'scope':'changed'}),patch.object(c,'connect',side_effect=lambda *args:sqlite3.connect(dbpath)):
            with self.assertRaises(ValueError):
                with cc.scoped_runner():pass

    def test_classifier_targets_only_new_accepted_and_verified_lyrics(self):
        ids=[f'new{i:04}' for i in range(3654)];rows={sid:dict(status='not_found') for sid in ids}
        folder=self.root/'data/lyrics';folder.mkdir(parents=True);path=folder/(ids[0]+'.txt');path.write_text('synthetic fixture')
        rows[ids[0]]=dict(status='accepted',identity_confidence='identity_high_confidence',pipeline_sha256='frozen',lyrics_path=str(path.relative_to(self.root)),lyrics_sha256=sha(path))
        m=dict(songs=[dict(song_id=s) for s in ids],lyrics_pipeline_sha256='frozen')
        original=self.root/'original.db'
        with sqlite3.connect(original) as db:db.execute('CREATE TABLE targets(song_id TEXT)');db.execute("INSERT INTO targets VALUES ('old')")
        with patch.object(cc,'ROOT',self.root),patch.object(c,'manifest',return_value=m),patch.object(c,'lyric_results',return_value=rows),patch.object(c,'connect',side_effect=lambda *args:sqlite3.connect(original)):
            self.assertEqual(cc.targets(),[dict(song_id=ids[0],lyrics_sha256=sha(path),source_words=2)])
            path.write_text('changed')
            with self.assertRaises(ValueError):cc.targets()

    def test_classifier_waits_for_final_lyrics_population(self):
        with patch.object(c,'manifest',return_value={}),patch.object(c,'lyric_results',return_value={}):
            with self.assertRaises(ValueError):cc.targets()

    def test_no_protected_result_destinations(self):
        for path in (c.METADATA,c.LYRICS,c.CLASSIFIERS):
            self.assertEqual(path.parent,c.BASE)
            self.assertNotIn(path,[c.ROOT/'data/processed/research.db',c.ROOT/'data/processed/lyrics.db',runner.DEFAULT_FULL])

if __name__=='__main__':unittest.main()
