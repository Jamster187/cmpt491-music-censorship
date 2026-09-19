"""Production acquisition preserves approved matching and restart semantics."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import SCHEMA
from production_metadata import BudgetReached, ProductionClient, acquire, persist, project_entities, queue, response_record
from musicbrainz import MusicBrainzClient, APIError, write_json


class FixtureClient:
    def __init__(self,root,payload):
        self.cache_dir=root; self.payload=payload; self.calls=0
    def get(self,entity,**params):
        self.calls+=1
        url=MusicBrainzClient.request_url(entity,params)
        key=hashlib.sha256(url.encode()).hexdigest()
        body=json.dumps(self.payload)
        write_json(self.cache_dir/'requests'/(key+'.json'),{'url':url,'cache_key':key,'attempts':[
            {'status':200,'error':None,'body':body,'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'received_at':'2026-09-19T00:00:00+00:00'}]})
        return self.payload,key


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.conn=sqlite3.connect(':memory:'); self.conn.execute('PRAGMA foreign_keys=ON'); self.conn.executescript(SCHEMA)
        self.song={'song_id':'song_test','title':'Example','artist':'Artist','first_chart_date':'1980-05-01'}
        for sid in ('song_test','song_outside'):
            self.conn.execute('INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?)',(sid,'Example' if sid=='song_test' else 'Other','Artist','example','artist','1980-05-01','1980-05-01',1,1,1,100))
        self.conn.execute("INSERT INTO study_population VALUES ('song_test','1980-05','1980-05',1)")
        self.conn.commit()
        self.payload={'count':2,'recordings':[{'id':rid,'title':'Example','score':100,'first-release-date':'1980',
            'artist-credit':[{'artist':{'id':'a','name':'Artist','genres':[{'name':'artist genre'}]}}],
            'tags':[{'name':'raw tag','count':-1}],'length':180000,
            'releases':[{'id':'release','title':'Album','date':'1980','release-group':{'id':'group','genres':[{'name':'group genre'}]}}]} for rid in ('r1','r2')]}

    def tearDown(self):
        self.conn.close(); self.tmp.cleanup()

    def result(self):
        return acquire(self.song,FixtureClient(self.root/'cache',self.payload),{})

    def test_asset_acceptance_preserves_multiple_ids(self):
        r=self.result()
        self.assertEqual(r['asset_match_status'],'high_confidence')
        self.assertEqual(r['supporting_recording_ids'],['r1','r2'])
        self.assertEqual(r['canonical_recording_status'],'unresolved_multiple')

    def test_entity_projection_preserves_scope_and_votes(self):
        p=project_entities(self.result())
        self.assertEqual(p['recording','r1']['variants'][0]['tags'],[{'name':'raw tag','count':-1}])
        self.assertNotIn('genres',p['recording','r1']['variants'][0])
        self.assertEqual(p['artist','a']['variants'][0]['genres'],[{'name':'artist genre'}])
        self.assertEqual(p['release-group','group']['variants'][0]['genres'],[{'name':'group genre'}])

    def test_persist_then_resume_skips_success_and_keeps_identity(self):
        before=self.conn.execute('SELECT * FROM songs').fetchall()
        with patch('production_metadata.ROOT',self.root):
            persist(self.conn,self.result(),self.root/'results')
        self.assertEqual(queue(self.conn),[])
        self.assertEqual(self.conn.execute('SELECT * FROM songs').fetchall(),before)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM song_external_links').fetchone()[0],5)
        path,checksum=self.conn.execute('SELECT result_path,result_sha256 FROM metadata_matches').fetchone()
        self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),checksum)

    def test_nonstudy_identity_is_rejected(self):
        r=self.result(); r['song']=dict(self.song,song_id='song_outside',title='Other')
        with self.assertRaises(ValueError):
            persist(self.conn,r,self.root/'results')

    def test_ambiguous_metadata_is_not_persisted_as_accepted(self):
        r=self.result(); r['asset_match_status']='ambiguous'
        with self.assertRaises(ValueError):
            persist(self.conn,r,self.root/'results')

    def test_cache_corruption_fails_before_reuse(self):
        self.result(); p=next((self.root/'cache/requests').glob('*.json'))
        e=json.loads(p.read_text()); e['attempts'][0]['body']='{}'; write_json(p,e)
        with self.assertRaises(APIError):
            response_record(p)

    def test_deadline_does_not_bypass_provider_cooldown(self):
        client=ProductionClient(self.root,max_seconds=1)
        client.next_allowed=client.clock()+30
        with self.assertRaises(BudgetReached):
            client._wait()


if __name__=='__main__':
    unittest.main()
