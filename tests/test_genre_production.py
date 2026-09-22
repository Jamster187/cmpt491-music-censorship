import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import genre_production as g

class ProductionTests(unittest.TestCase):
    def row(self,sid='a',genre='Pop'):
        return dict(song_id=sid,primary_genre=genre,secondary_genres=[],confidence='high',reason='Supplied recording evidence supports this style.')

    def database(self):
        c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
        c.execute('CREATE TABLE songs(song_id PRIMARY KEY,status,primary_genre,secondary_genres,confidence,reason,model,prompt_version,source,error,completed_at)')
        c.executemany("INSERT INTO songs(song_id,status) VALUES (?,'pending')",[('a',),('b',)])
        return c

    def test_completed_rows_are_immutable(self):
        with self.database() as c:
            g.persist(c,self.row(),'production','date')
            g.persist(c,self.row(genre='Rock'),'production','later')
            self.assertEqual(c.execute("SELECT primary_genre FROM songs WHERE song_id='a'").fetchone()[0],'Pop')
            self.assertEqual(c.execute("SELECT status FROM songs WHERE song_id='b'").fetchone()[0],'pending')

    def test_partial_valid_results_survive_schema_failure(self):
        with tempfile.TemporaryDirectory() as tmp,self.database() as c:
            folder=Path(tmp)
            (folder/'response.json').write_text(json.dumps({'predictions':[self.row(),{**self.row('b'),'primary_genre':'Invalid'}]}))
            (folder/'events.jsonl').write_text(json.dumps({'type':'turn.completed','usage':{}}))
            with self.assertRaises(ValueError):g.ingest_response(c,{'song_ids':'["a","b"]'},folder)
            self.assertEqual(c.execute("SELECT status FROM songs WHERE song_id='a'").fetchone()[0],'completed')
            self.assertEqual(c.execute("SELECT status FROM songs WHERE song_id='b'").fetchone()[0],'pending')

    def test_tool_events_rejected_before_persisting(self):
        with tempfile.TemporaryDirectory() as tmp,self.database() as c:
            folder=Path(tmp)
            (folder/'response.json').write_text(json.dumps({'predictions':[self.row()]}))
            (folder/'events.jsonl').write_text(json.dumps({'type':'item.completed','item':{'type':'command_execution'}})+'\n'+json.dumps({'type':'turn.completed'}))
            with self.assertRaisesRegex(ValueError,'tool'):g.ingest_response(c,{'song_ids':'["a"]'},folder)
            self.assertEqual(c.execute("SELECT status FROM songs WHERE song_id='a'").fetchone()[0],'pending')

    def test_recovery_uses_saved_response_without_inference(self):
        with tempfile.TemporaryDirectory() as tmp,self.database() as c:
            folder=Path(tmp)/'saved';folder.mkdir()
            c.execute('ALTER TABLE songs ADD COLUMN input_json')
            c.execute('UPDATE songs SET input_json=?',(json.dumps({'song_id':'a'}),))
            c.execute('CREATE TABLE batches(batch_id,status)')
            c.execute("INSERT INTO batches VALUES (1,'running')")
            c.execute('CREATE TABLE attempts(attempt_id,batch_id,status,folder,finished_at,usage_json,response_sha256)')
            c.execute("INSERT INTO attempts(attempt_id,batch_id,status,folder) VALUES (1,1,'running','saved')")
            (folder/'response.json').write_text(json.dumps({'predictions':[self.row()]}))
            (folder/'events.jsonl').write_text(json.dumps({'type':'turn.completed','usage':{'input_tokens':1}}))
            batch={'batch_id':1,'song_ids':'["a"]','request_sha256':g.digest(g.request_text([{'song_id':'a'}]).encode())}
            with patch.object(g,'LOCAL',Path(tmp)),patch.object(g.subprocess,'run') as run:
                g.execute_batch(c,batch)
                run.assert_not_called()
            self.assertEqual(c.execute('SELECT status FROM attempts').fetchone()[0],'recovered')
            self.assertEqual(c.execute('SELECT status FROM batches').fetchone()[0],'completed')

    def test_drift_guards(self):
        balanced=[self.row(genre=g.TAXONOMY[i%16]) for i in range(200)]
        self.assertIsNone(g.drift(balanced))
        self.assertIsNone(g.drift([self.row()]*199))
        self.assertIn('Single genre',g.drift([self.row()]*200))
        self.assertIn('Other',g.drift([self.row(genre='Other')]*110+balanced[:90]))
        self.assertIn('Low confidence',g.drift([{**r,'confidence':'low'} for r in balanced]))
        self.assertIn('Confidence share',g.drift([{**r,'confidence':'medium'} for r in balanced],balanced))

    def test_no_api_fallback(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-not-a-real-key'}),patch.object(g.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'billing'):g.access()
            run.assert_not_called()

    def test_frozen_files_and_request(self):
        self.assertEqual(len(g.frozen()),4)
        rows=[{'song_id':'a','title':'é'}]
        self.assertEqual(g.request_text(rows), (g.DOC/'prompt.txt').read_text()+json.dumps(rows,ensure_ascii=False,sort_keys=True)+'\n')
