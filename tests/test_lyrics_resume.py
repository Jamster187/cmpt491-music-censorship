"""Transport race, immutable disposition resume, and explicit provenance migration."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import lyrics_lrclib as legacy
import lyrics_production as production
import lyrics_resume as resume


class ResumeTests(unittest.TestCase):
    def test_deadline_crossing_between_clock_reads_never_sleeps_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            client=legacy.Client(Path(directory))
            legacy.save_json(client.clock,{'until':100.0})
            readings=iter([99.999,100.001])
            def now():return next(readings,100.001)
            sleeps=[]
            def sleep(n):
                self.assertGreater(n,0)
                sleeps.append(n)
            class Response:
                status=200;headers={}
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def read(self):return b'[]'
            with patch('lyrics_lrclib.time.time',side_effect=now),patch('lyrics_lrclib.time.sleep',side_effect=sleep),patch('urllib.request.urlopen',return_value=Response()):
                self.assertEqual(client.search({'track_name':'Synthetic'})['status'],200)
            self.assertEqual(len(sleeps),1)
            self.assertAlmostEqual(sleeps[0],0.001)

    def fixture(self,root):
        (root/'data/processed').mkdir(parents=True)
        (root/'reports').mkdir()
        (root/'data/processed/lyrics.db').touch()
        c=production.connect(root)
        gate={'passed':True,'pipeline_sha256':'new','review_ledger_sha256':legacy.digest(b'ledger'),'cases':[{'synthetic':True}]}
        (root/'reports/lyrics_lrclib_r_review.json').write_bytes(b'ledger')
        (root/'data/processed/lyrics_production_gate.json').write_text(json.dumps(gate))
        c.executemany('INSERT INTO production_settings VALUES (?,?)',[('pipeline_sha256',resume.OLD_PIPELINE),('gate',json.dumps(gate))])
        c.execute('INSERT INTO production_results VALUES (?,?)',('old',json.dumps({'status':'not_found'})))
        c.commit()
        return c

    def test_transition_is_idempotent_and_old_payloads_cannot_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);c=self.fixture(root)
            original=c.execute('SELECT * FROM production_results').fetchall()
            with patch.object(production,'fingerprint',return_value='new'),patch.object(production,'validate'),patch.object(resume,'UNCHANGED',{}),patch.object(production,'BUNDLE',()):
                self.assertEqual(resume.migrate(c,root),1)
                self.assertEqual(resume.migrate(c,root),0)
            self.assertEqual(c.execute('SELECT * FROM production_results').fetchall(),original)
            self.assertEqual(dict(c.execute('SELECT * FROM production_settings'))['pipeline_sha256'],resume.OLD_PIPELINE)
            c.execute("UPDATE production_results SET payload='{}'")
            with self.assertRaisesRegex(ValueError,'disposition changed'):resume.verify_preserved(c)
            c.close()

    def test_changed_pilot_gate_refuses_transition_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);c=self.fixture(root)
            path=root/'data/processed/lyrics_production_gate.json'
            gate=json.loads(path.read_text());gate['cases']=[];path.write_text(json.dumps(gate))
            with patch.object(production,'fingerprint',return_value='new'),patch.object(resume,'UNCHANGED',{}):
                with self.assertRaisesRegex(ValueError,'replay differs'):resume.migrate(c,root)
            self.assertNotIn('current_pipeline_sha256',dict(c.execute('SELECT * FROM production_settings')))
            self.assertFalse(c.execute("SELECT name FROM sqlite_master WHERE name='production_result_implementations'").fetchall())
            c.close()

    def test_resume_skips_every_persisted_disposition_including_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data/processed').mkdir(parents=True);(root/'data/processed/lyrics.db').touch()
            c=production.connect(root)
            for status in production.STATUSES:
                s={'song_id':status,'title':'Synthetic','artist':'Fixture'}
                c.execute('INSERT INTO production_assets VALUES (?,?)',(status,json.dumps(s)))
                c.execute('INSERT INTO production_results VALUES (?,?)',(status,json.dumps(dict(s,status=status))))
            new={'song_id':'unattempted','title':'Synthetic','artist':'Fixture'}
            c.execute('INSERT INTO production_assets VALUES (?,?)',('unattempted',json.dumps(new)))
            c.commit();before=dict(c.execute('SELECT * FROM production_results'));c.close()
            with patch.object(production,'guards'),patch.object(production,'initialize'),patch.object(production,'seed_pilot'),patch.object(production,'validate'),patch.object(production,'report'),patch.object(production,'acquire',return_value=(dict(new,status='not_found'),None)) as acquire:
                production.run(root=root)
                self.assertEqual(acquire.call_count,1)
                self.assertEqual(acquire.call_args[0][0]['song_id'],'unattempted')
            c=production.connect(root,readonly=True);after=dict(c.execute('SELECT * FROM production_results'))
            self.assertTrue(all(after[sid]==payload for sid,payload in before.items()))
            self.assertEqual(json.loads(after['unattempted'])['pipeline_sha256'],production.fingerprint())
            self.assertEqual(c.execute('SELECT processed,state FROM production_runs').fetchone(),(1,'completed'))
            c.close()
