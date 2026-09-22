import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import genre_production as g

class RetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.local=Path(self.tmp.name)
        self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
        self.c.executescript('''CREATE TABLE songs(song_id PRIMARY KEY,status,primary_genre,secondary_genres,confidence,reason,model,prompt_version,source,error,completed_at,batch_id,input_json);
        CREATE TABLE batches(batch_id PRIMARY KEY,status,song_ids,request_sha256);
        CREATE TABLE attempts(attempt_id INTEGER PRIMARY KEY,batch_id,started_at,finished_at,seconds,status,error,folder,usage_json,response_sha256);
        ''')
        for sid in ['a','b']:
            self.c.execute("INSERT INTO songs(song_id,status,batch_id,input_json) VALUES (?,'pending',1,?)",(sid,json.dumps({'song_id':sid})))
        self.batch=g.subset_request(self.c,1,['a','b'])
        self.c.execute("INSERT INTO batches VALUES (1,'pending',?,?)",(self.batch['song_ids'],self.batch['request_sha256']))
        self.calls=[];self.responses=[]

    def tearDown(self):self.c.close();self.tmp.cleanup()

    def row(self,sid):return dict(song_id=sid,primary_genre='Rock',secondary_genres=[],confidence='medium',reason='Recording evidence.')

    def transport(self,cmd,**kwargs):
        prompt=kwargs['input'];payload=json.loads(prompt[len((g.DOC/'prompt.txt').read_text()):]);self.calls.append([r['song_id'] for r in payload])
        response=self.responses.pop(0)
        Path(cmd[cmd.index('-o')+1]).write_text(json.dumps(response))
        kwargs['stdout'].write(json.dumps({'type':'turn.completed','usage':{}})+'\n');kwargs['stdout'].flush()
        return type('Result',(),{'returncode':0})()

    def run_batch(self):
        with patch.object(g,'LOCAL',self.local),patch.object(g.subprocess,'run',side_effect=self.transport),patch.object(g,'monitor',return_value={}):
            g.execute_resilient_batch(self.c,self.batch)

    def test_missing_id_duplicate_foreign_and_incomplete_never_guess(self):
        cases=[([self.row('a'),{k:v for k,v in self.row('b').items() if k!='song_id'}],['a']),
               ([self.row('a'),self.row('b'),self.row('b')],['a']),
               ([self.row('a'),self.row('foreign')],['a']),
               ([self.row('a')],['a']),
               ([self.row('b'),self.row('a')],['a','b'])]
        for rows,accepted in cases:
            with self.subTest(rows=rows):
                self.c.execute("UPDATE songs SET status='pending'")
                (self.local/'response.json').write_text(json.dumps({'predictions':rows}))
                (self.local/'events.jsonl').write_text(json.dumps({'type':'turn.completed','usage':{}}))
                if accepted==['a','b']:g.ingest_response(self.c,self.batch,self.local)
                else:
                    with self.assertRaises(g.MalformedResponse):g.ingest_response(self.c,self.batch,self.local)
                actual=[r[0] for r in self.c.execute("SELECT song_id FROM songs WHERE status='completed' ORDER BY song_id")]
                self.assertEqual(actual,accepted)

    def test_valid_retry_only_requests_unresolved(self):
        self.responses=[{'predictions':[self.row('a')]},{'predictions':[self.row('b')]}]
        self.run_batch()
        self.assertEqual(self.calls,[['a','b'],['b']])
        self.assertEqual(self.c.execute("SELECT count(*) FROM songs WHERE status='completed'").fetchone()[0],2)
        before=[tuple(r) for r in self.c.execute('SELECT * FROM songs')]
        self.run_batch()
        self.assertEqual(len(self.calls),2)
        self.assertEqual(before,[tuple(r) for r in self.c.execute('SELECT * FROM songs')])

    def test_repeated_group_failure_falls_back_to_singletons(self):
        self.responses=[{'predictions':[]},{'predictions':[]},{'predictions':[self.row('a')]},{'predictions':[self.row('b')]}]
        self.run_batch()
        self.assertEqual(self.calls,[['a','b'],['a','b'],['a'],['b']])
        self.assertEqual(self.c.execute("SELECT count(*) FROM songs WHERE status='completed'").fetchone()[0],2)

    def test_persisted_budget_and_independent_terminal_failure(self):
        self.responses=[{'predictions':[]}]*4+[{'predictions':[self.row('b')]}]
        self.run_batch()
        self.assertEqual(self.calls,[['a','b'],['a','b'],['a'],['a'],['b']])
        self.assertEqual(dict(self.c.execute('SELECT song_id,status FROM songs')),{'a':'error','b':'completed'})
        before=[tuple(r) for r in self.c.execute("SELECT * FROM songs WHERE song_id='b'")]
        self.run_batch()
        self.assertEqual(len(self.calls),5)
        self.assertEqual(before,[tuple(r) for r in self.c.execute("SELECT * FROM songs WHERE song_id='b'")])

    def test_duplicate_rows_never_choose_a_winner(self):
        self.responses=[{'predictions':[self.row('a'),{**self.row('a'),'primary_genre':'Pop'},self.row('b')]},{'predictions':[self.row('a')]}]
        self.run_batch()
        self.assertEqual(self.calls,[['a','b'],['a']])
        self.assertEqual(self.c.execute("SELECT primary_genre FROM songs WHERE song_id='a'").fetchone()[0],'Rock')
