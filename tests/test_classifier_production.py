"""Regression checks for bounded targets, chunk transactions and independent resume."""
import json
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import classifier_production_store as s
import classifier_production as runner

class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.c=s.connect(self.root/'run.db');self.target={'song_id':'test','lyrics_sha256':s.digest('abc def'),'source_words':2}
        s.initialize(self.c,[self.target],{'version':'test'})
    def tearDown(self):self.c.close();self.tmp.cleanup()
    def row(self,model,index=0,start=0,end=2):
        spec=s.SPEC['models'][model];logits=[0.0]*spec['raw_dimension'];activated=s.softmax(logits) if model=='cardiff' else [.5]*len(logits)
        return dict(chunk_index=index,content_start=start,content_end=end,input_tokens=end-start+2,input_sha256='hash',logits=logits,activated=activated,scores=dict(zip(spec['columns'],[activated[i] for i in spec['raw_indices']])),seconds=.1)
    def complete(self,model):
        s.claim(self.c,'test',model);s.prepare(self.c,'test',model,2,1,510,'normalized');s.save_chunk(self.c,'test',model,self.row(model));s.finish(self.c,'test',model)
    def test_schema_exact_and_no_combined_outputs(self):
        self.assertEqual(len(s.COLUMNS),42);self.assertEqual(len(set(s.COLUMNS)),42)
        self.assertEqual(s.MODELS,('lyriclens','detoxify','goemotions','cardiff'))
        for model in s.MODELS:self.assertEqual(len(s.SPEC['models'][model]['columns']),len(s.SPEC['models'][model]['raw_indices']))
        with self.assertRaises(ValueError):s.worklist(self.c,'bart')
    def test_resume_skips_success_and_retains_other_models(self):
        self.complete('lyriclens');s.claim(self.c,'test','detoxify');s.fail(self.c,'test','detoxify',ValueError('private input'))
        self.assertEqual(s.worklist(self.c,'lyriclens'),[]);self.assertFalse(s.claim(self.c,'test','lyriclens'))
        self.assertEqual(s.worklist(self.c,'detoxify'),[]);self.assertEqual(len(s.worklist(self.c,'detoxify',True)),1)
        row=self.c.execute('SELECT * FROM song_results').fetchone();self.assertEqual(row['ll_violence'],.5);self.assertEqual(row['processing_status'],'partial')
        self.assertEqual(self.c.execute("SELECT error_type FROM jobs WHERE model='detoxify'").fetchone()[0],'ValueError')
    def test_reconfiguration_refused(self):
        s.initialize(self.c,[self.target],{'version':'test'})
        with self.assertRaises(ValueError):s.initialize(self.c,[self.target],{'version':'changed'})
        with self.assertRaises(ValueError):s.initialize(self.c,[],{'version':'test'})
    def test_atomic_initialization_rollback(self):
        c=s.connect(self.root/'bad.db')
        with self.assertRaises(sqlite3.IntegrityError):s.initialize(c,[self.target,self.target],{})
        self.assertEqual(c.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0],0)
        s.initialize(c,[self.target],{});c.close()
    def test_no_nan_wrong_mapping_or_incomplete_coverage(self):
        row=self.row('lyriclens');row['logits'][0]=float('nan')
        with self.assertRaises(ValueError):s.save_chunk(self.c,'test','lyriclens',row)
        row=self.row('lyriclens');row['scores']['ll_violence']=.7
        with self.assertRaises(ValueError):s.validate_chunk('lyriclens',row)
        s.claim(self.c,'test','lyriclens');s.prepare(self.c,'test','lyriclens',3,1,1022,'n');s.save_chunk(self.c,'test','lyriclens',self.row('lyriclens'))
        with self.assertRaises(ValueError):s.finish(self.c,'test','lyriclens')
    def test_duplicate_chunk_not_overwritten(self):
        row=self.row('lyriclens');s.save_chunk(self.c,'test','lyriclens',row)
        with self.assertRaises(sqlite3.IntegrityError):s.save_chunk(self.c,'test','lyriclens',row)
    def test_interrupt_and_resume_partial_chunk(self):
        path=self.root/'data/lyrics/test.txt';path.parent.mkdir(parents=True);path.write_text('abc def')
        outer=self
        class Engine:
            budget=1
            calls=[]
            def tokenize(self,text):return [1,2],[(0,1),(1,2)],s.digest(text)
            def input(self,ids,start,end):return [0,ids[start],3],'hash'
            def predict(self,ids,start,end,index):
                self.calls.append(index)
                if self.calls==[0,1]:raise KeyboardInterrupt()
                return outer.row('lyriclens',index,start,end)
        e=Engine()
        with patch.object(runner,'ROOT',self.root):
            with self.assertRaises(KeyboardInterrupt):runner.process(self.c,self.target,'lyriclens',e)
            self.assertEqual(len(s.chunks(self.c,'test','lyriclens')),1)
            self.assertTrue(runner.process(self.c,self.target,'lyriclens',e))
            self.assertFalse(runner.process(self.c,self.target,'lyriclens',e))
        self.assertEqual(e.calls,[0,1,1]);self.assertEqual(path.read_text(),'abc def')
    def test_wrong_hash_records_failure_without_inference(self):
        path=self.root/'data/lyrics/test.txt';path.parent.mkdir(parents=True);path.write_text('changed')
        with patch.object(runner,'ROOT',self.root):self.assertFalse(runner.process(self.c,self.target,'lyriclens',None))
        self.assertEqual(self.c.execute("SELECT status FROM jobs WHERE model='lyriclens'").fetchone()[0],'error')
    def test_balanced_chunks_cover_tail_once(self):
        for budget in (510,1022):
            for length in (1,budget,budget+1,4000):
                spans=s.chunk_ranges(length,budget);self.assertEqual([i for a,b in spans for i in range(a,b)],list(range(length)))
    def test_unapproved_id_cannot_be_claimed(self):
        with self.assertRaises(ValueError):s.claim(self.c,'outside','lyriclens')
    def test_model_columns_all_persist_and_sentiment_sums_to_one(self):
        for model in s.MODELS:self.complete(model)
        row=self.c.execute('SELECT * FROM song_results').fetchone();self.assertEqual(row['processing_status'],'complete')
        self.assertAlmostEqual(sum(row[c] for c in s.SPEC['models']['cardiff']['columns']),1)
        self.assertTrue(all(row[c] is not None for c in s.COLUMNS))
    def test_protected_database_destinations_refused(self):
        for path in ('data/processed/research.db','data/processed/music.db','data/processed/lyrics.db','data/public/master_dataset.csv'):
            with self.assertRaises(ValueError):runner.result_path(runner.ROOT/path)
        self.assertEqual(runner.result_path(runner.DEFAULT_FULL),runner.DEFAULT_FULL)
        self.assertEqual(runner.result_path(runner.DEFAULT_PILOT),runner.DEFAULT_PILOT)
    def test_symlink_result_destination_cannot_alias_research(self):
        protected=self.root/'research.db';protected.write_bytes(b'protected')
        destination=self.root/'classifier_results.db';destination.symlink_to(protected)
        with patch.object(runner,'DEFAULT_FULL',destination):
            with self.assertRaises(ValueError):runner.result_path(destination)
        self.assertEqual(protected.read_bytes(),b'protected')
    def test_preprocessing_failure_does_not_poison_next_song(self):
        import classifier_production_engine as engine
        fake=types.ModuleType('nltk');fake.data=types.SimpleNamespace(path=[])
        def words(text):
            if text=='bad':raise LookupError('simulated tokenizer failure')
            return [text]
        fake.word_tokenize=words;fake.pos_tag=lambda words:words
        class Lemmatizer:
            def lemmatize(self,word):return word
        stem=types.ModuleType('nltk.stem');stem.WordNetLemmatizer=Lemmatizer
        code="class LongformerPreprocessor:\n def clean_and_lemmatize(self,text):\n  try:nltk.word_tokenize(text)\n  except LookupError:pass\n  return 'normalized'\n"
        with patch.dict(sys.modules,{'nltk':fake,'nltk.stem':stem,'pandas':types.ModuleType('pandas')}),patch.object(engine,'extract_definitions',return_value=code):
            clean=engine.lyriclens_cleaner()
            with self.assertRaises(ValueError):clean('bad')
            self.assertEqual(clean('good'),'normalized')
    def test_concurrent_lock_refused(self):
        with runner.lock(self.root/'lock'):
            with self.assertRaises(RuntimeError):
                with runner.lock(self.root/'lock'):pass

if __name__=='__main__':unittest.main()
