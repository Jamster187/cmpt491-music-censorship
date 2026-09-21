"""Audit joins must reject conflicting IDs; saved chunks must match the frozen rule."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from month_end_catchup_audit import merge_population,validate_chunks
from classifier_production_store import SPEC


class CatchupAuditTests(unittest.TestCase):
    def test_merge_excludes_removed_without_mutating_inputs(self):
        old={'keep':1,'removed':2};new={'added':3}
        self.assertEqual(merge_population(old,new,{'keep','added'}),{'added':3,'keep':1})
        self.assertEqual(old,{'keep':1,'removed':2})
        self.assertEqual(new,{'added':3})

    def test_overlap_and_missing_identity_refused(self):
        with self.assertRaises(ValueError):merge_population({'same':1},{'same':1},{'same'})
        with self.assertRaises(ValueError):merge_population({'old':1},{'new':2},{'missing'})

    def fixture(self):
        model='lyriclens';columns=SPEC['models'][model]['columns']
        row=dict(chunk_index=0,content_start=0,content_end=4,input_tokens=6,logits=[0.0]*4,activated=[.5]*4,scores={k:.5 for k in columns},seconds=0.1)
        job=dict(model=model,content_budget=1022,token_count=4,chunk_count=1)
        return job,[row],{k:.5 for k in columns}

    def test_exact_chunks_and_aggregation(self):
        job,rows,song=self.fixture();validate_chunks(job,rows,song)
        song['ll_violence']=.6
        with self.assertRaises(ValueError):validate_chunks(job,rows,song)

    def test_omitted_tail_refused(self):
        job,rows,song=self.fixture();job['token_count']=5
        with self.assertRaises(ValueError):validate_chunks(job,rows,song)

    def test_wrong_budget_and_special_tokens_refused(self):
        job,rows,song=self.fixture();job['content_budget']=510
        with self.assertRaises(ValueError):validate_chunks(job,rows,song)
        job['content_budget']=1022;rows[0]['input_tokens']=7
        with self.assertRaises(ValueError):validate_chunks(job,rows,song)

if __name__=='__main__':unittest.main()
