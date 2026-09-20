"""Synthetic production-manifest synchronization; no real lyric text."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import lyrics_import as importer
import lyrics_production as production
import lyrics_resume as resume
import research
import research_report
from lyrics_lrclib import digest


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'data/processed').mkdir(parents=True);(self.root/'data/lyrics').mkdir()
        (self.root/'data/processed/lyrics.db').touch()
        self.local=production.connect(self.root)
        self.local.execute('CREATE TABLE production_result_implementations (song_id TEXT PRIMARY KEY,pipeline_sha256 TEXT,payload_sha256 TEXT)')
        self.local.execute("INSERT INTO production_settings VALUES ('current_pipeline_sha256','new')")
        class Connection(sqlite3.Connection):
            fail=False
            def execute(self,sql,*args):
                if self.fail and sql.startswith('INSERT INTO build_metadata'):raise sqlite3.OperationalError('Injected publication failure')
                return super().execute(sql,*args)
        self.c=sqlite3.connect(':memory:',factory=Connection)
        self.c.execute('PRAGMA foreign_keys=ON')
        original=research.SCHEMA.replace(",\n  'quarantined','wrong_identity','bad_missing_text'",'')
        self.c.executescript(original)
        self.c.execute("INSERT INTO build_metadata VALUES ('schema_version','1')")
        for status in production.STATUSES:
            sid='fixture_'+status;title='Example';artist='Synthetic Artist';date='2000-01-01'
            self.c.execute('INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?)',(sid,title+status,artist,title.lower()+status,artist.lower(),date,date,1,1,1,100))
            # Each exact synthetic identity is distinct.
            title+=status
            self.c.execute('INSERT INTO study_population VALUES (?,?,?,?)',(sid,'2000-01','2000-01',1))
            self.c.execute('INSERT INTO lyrics_manifest(song_id) VALUES (?)',(sid,))
            a=dict(song_id=sid,title=title,artist=artist,first_chart_date=date)
            r=dict(a,status=status,matched={'id':1,'trackName':title,'artistName':artist},matcher_version='synthetic-v1',
                   decision_basis='automatic',identity_confidence='identity_high_confidence',text_quality='synthetic',
                   processed_at='2026-09-20T00:00:00Z',retrievals=[{'url':'https://example.invalid/fixture','sha256':'cached-hash','retrieved_at':'2026-09-19T00:00:00Z','body':'MUST NOT COPY'}],
                   lyrics_path=None,lyrics_sha256=None,reason='Synthetic disposition')
            if status=='accepted':
                path=self.root/'data/lyrics'/(sid+'.txt');path.write_text('Synthetic test fixture only.\n')
                r.update(lyrics_path=str(path.relative_to(self.root)),lyrics_sha256=digest(path.read_bytes()))
            payload=json.dumps(r,sort_keys=True)
            self.local.execute('INSERT INTO production_assets VALUES (?,?)',(sid,json.dumps(a)))
            self.local.execute('INSERT INTO production_results VALUES (?,?)',(sid,payload))
            self.local.execute('INSERT INTO production_result_implementations VALUES (?,?,?)',(sid,resume.OLD_PIPELINE,digest(payload.encode())))
        self.local.commit();self.c.commit()

    def tearDown(self):
        self.local.close();self.c.close();self.temp.cleanup()

    def test_exact_dispositions_provenance_no_text_and_idempotence(self):
        identities=self.c.execute('SELECT * FROM songs').fetchall()
        self.assertEqual(importer.synchronize(self.c,self.local,self.root),6)
        statuses={x[0] for x in self.c.execute('SELECT lyrics_status FROM lyrics_manifest')}
        self.assertEqual(statuses,{'success','quarantined','wrong_identity','bad_missing_text','not_found','error'})
        self.assertEqual(research.validate_lyrics_files(self.c,self.root),1)
        self.assertEqual(identities,self.c.execute('SELECT * FROM songs').fetchall())
        for p, in self.c.execute('SELECT provenance_json FROM lyrics_manifest'):
            self.assertNotIn('MUST NOT COPY',p)
            self.assertNotIn('Synthetic test fixture only',p)
            self.assertEqual(json.loads(p)['pipeline_sha256'],resume.OLD_PIPELINE)
        before=list(self.c.iterdump())
        self.assertEqual(importer.synchronize(self.c,self.local,self.root),0)
        self.assertEqual(list(self.c.iterdump()),before)

    def test_incomplete_population_refused_before_migration(self):
        self.local.execute("DELETE FROM production_results WHERE song_id='fixture_not_found'");self.local.commit()
        before=list(self.c.iterdump())
        with self.assertRaisesRegex(ValueError,'entire exact study'):importer.synchronize(self.c,self.local,self.root)
        self.assertEqual(list(self.c.iterdump()),before)

    def test_existing_success_cannot_be_overwritten(self):
        self.c.execute("UPDATE lyrics_manifest SET lyrics_status='success',lyrics_source='Synthetic',match_status='high_confidence',lyrics_path='different.txt',lyrics_sha256='different',retrieved_at='now' WHERE song_id='fixture_accepted'")
        self.c.commit();before=list(self.c.iterdump())
        with self.assertRaisesRegex(ValueError,'Conflicting existing'):importer.synchronize(self.c,self.local,self.root)
        self.assertEqual(list(self.c.iterdump()),before)

    def test_schema_and_rows_rollback_on_write_failure(self):
        before=list(self.c.iterdump());self.c.fail=True
        with self.assertRaisesRegex(sqlite3.OperationalError,'Injected'):importer.synchronize(self.c,self.local,self.root)
        self.assertEqual(list(self.c.iterdump()),before)

    def test_research_identity_drift_refused(self):
        self.c.execute("UPDATE songs SET artist='Different' WHERE song_id='fixture_accepted'");self.c.commit()
        with self.assertRaisesRegex(ValueError,'identity mismatch'):importer.synchronize(self.c,self.local,self.root)

    def test_report_uses_synchronized_dispositions_not_historical_access_block(self):
        importer.synchronize(self.c,self.local,self.root)
        summary=research_report.collect(self.c)
        self.assertEqual(summary['source_selected'],['LRCLIB'])
        self.assertEqual(summary['lyrics_stage'],'dispositioned')
        self.assertEqual(summary['lyrics_attempted'],6)
        text=research_report.render(summary)
        self.assertNotIn('Source: none selected',text)
        self.assertNotIn('Full acquisition did not proceed',text)
        self.assertIn('wrong_identity',text)
