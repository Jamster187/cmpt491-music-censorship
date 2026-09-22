import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import genre_llm as g

class GenreLLMTests(unittest.TestCase):
    def row(self):
        return dict(song_id='a',primary_genre='Pop',secondary_genres=['Rock'],confidence='medium',reason='Crossover evidence.')

    def test_valid(self):
        self.assertEqual(len(g.check_predictions({'predictions':[self.row()]},['a'])),1)

    def test_invalid_outputs(self):
        for change in ({'primary_genre':'unknown'},{'confidence':0.9},
                       {'secondary_genres':['Pop']},{'secondary_genres':['Rock','Rock']},
                       {'song_id':'b'},{'reason':''},{'extra':'not allowed'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                g.check_predictions({'predictions':[{**self.row(),**change}]},['a'])

    def test_duplicate(self):
        with self.assertRaises(ValueError):
            g.check_predictions({'predictions':[self.row(),self.row()]},['a','b'])

    def test_input_whitelist_and_duplicate_tags(self):
        row=dict(song_id='a',title='title',artist='artist',first_chart_date='1960-01-01',
                 primary_genre='Rock',best_rank=1,ll_violence=.9)
        ev=dict(provider='MusicBrainz',level='recording',label='rap',votes=1,entity_id='x')
        out=g.evidence_input(row,[ev,ev,{**ev,'votes':3},{**ev,'entity_id':'y'}])
        self.assertEqual(set(out),{'song_id','title','artist','first_chart_date','genre_evidence'})
        self.assertEqual(out['genre_evidence'],[dict(provider='MusicBrainz',level='recording',raw_tag='rap',max_support=3,entity_count=2)])

    def test_separate_levels_and_unmapped_retained(self):
        r=dict(song_id='a',title='x',artist='y',first_chart_date='1960-01-01')
        e=dict(provider='MusicBrainz',level='artist',label='unmapped style',votes=1,entity_id='x')
        self.assertEqual(len(g.evidence_input(r,[e,{**e,'level':'recording'}])['genre_evidence']),2)

    def test_subset_stable_balanced(self):
        rows=[dict(song_id=str(i),period=str(i%7)) for i in range(300)]
        a=g.subset(rows,77,'x')
        self.assertEqual(a,g.subset(list(reversed(rows)),77,'x'))
        self.assertEqual(len(set(a)),77)
        self.assertEqual([sum(int(x)%7==p for x in a) for p in range(7)],[11]*7)

    def test_schema_taxonomy(self):
        self.assertEqual(len(g.TAXONOMY),16)
        self.assertEqual(g.schema()['properties']['predictions']['items']['properties']['primary_genre']['enum'],list(g.TAXONOMY))

class GenreLLMResumeTests(unittest.TestCase):
    def test_completed_batch_skips_network_and_detects_tampering(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); local=root/'local'; out=root/'out'; doc=root/'doc';doc.mkdir()
            (doc/'prompt.txt').write_text('Explicit prompt\n')
            inputs=[dict(song_id='a',title='x',artist='y',first_chart_date='1960-01-01',genre_evidence=[])]
            prompt=(doc/'prompt.txt').read_text()+json.dumps(inputs,ensure_ascii=False,sort_keys=True)+'\n'
            folder=local/'metadata'/'000';folder.mkdir(parents=True)
            response={'predictions':[dict(song_id='a',primary_genre='Pop',secondary_genres=[],confidence='low',reason='Sparse evidence.')]}
            g.dump(folder/'response.json',response)
            g.dump(folder/'complete.json',dict(prompt_sha256=g.digest(prompt.encode()),response_sha256=g.digest((folder/'response.json').read_bytes())))
            with patch.object(g,'prepare',return_value=(inputs,{})),patch.object(g,'LOCAL',local),patch.object(g,'OUT',out),patch.object(g,'DOC',doc),patch.object(g.subprocess,'run') as network:
                g.run('metadata')
                network.assert_not_called()
                self.assertEqual(json.loads((out/'metadata.json').read_text()),response['predictions'])
                response['predictions'][0]['primary_genre']='Rock';g.dump(folder/'response.json',response)
                with self.assertRaisesRegex(ValueError,'response changed'):g.run('metadata')

class GenreLLMSubsetBounds(unittest.TestCase):
    def test_unavailable_subset_fails_instead_of_looping(self):
        with self.assertRaises(ValueError):g.subset([dict(song_id='a',period='p')],2,'x')

class GenreLLMInputIsolation(unittest.TestCase):
    def test_raw_tags_cannot_leak_performance_or_research_outcomes(self):
        row=dict(song_id='a',title='Chart Song',artist='Rank Band',first_chart_date='2020-01-01')
        tags=['billboard no 1','top 40','jahrescharts 2025','offizielle charts','covid era','pandemic pop','soul','hip hop']
        ev=[dict(provider='MusicBrainz',level='recording',label=t,votes=1,entity_id='x') for t in tags]
        out=g.evidence_input(row,ev)
        self.assertEqual([e['raw_tag'] for e in out['genre_evidence']],['hip hop','soul'])
        self.assertEqual(out['title'],'Chart Song')
