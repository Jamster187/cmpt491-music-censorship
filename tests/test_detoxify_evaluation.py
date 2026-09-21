"""Regression checks for bounded, paired, raw-score-preserving evaluation."""
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from detoxify_evaluation import join_predictions, validate_scores, LABELS, SAMPLE_SHA, LL_SHA
from detoxify_diagnostics import pearson, select_review, joined, diagnostics
from lyriclens_evaluation import sha, REPORTS
from lyriclens_diagnostics import spearman

class DetoxifyEvaluationTests(unittest.TestCase):
    def test_exact_frozen_inputs(self):
        self.assertEqual(sha(REPORTS/'lyriclens_sample.csv'),SAMPLE_SHA)
        self.assertEqual(sha(REPORTS/'lyriclens_predictions.csv'),LL_SHA)

    def test_pair_by_id_not_order(self):
        a=[{'song_id':'a'},{'song_id':'b'}]
        b=[{'song_id':'b','v':2},{'song_id':'a','v':1}]
        self.assertEqual([r['v'] for _,r in join_predictions(a,b)],[1,2])

    def test_pair_rejects_missing_extra_duplicate(self):
        a=[{'song_id':'a'},{'song_id':'b'}]
        for b in ([{'song_id':'a'}],[{'song_id':'a'},{'song_id':'a'}],[{'song_id':'a'},{'song_id':'b'},{'song_id':'c'}]):
            with self.assertRaises(ValueError):join_predictions(a,b)

    def test_all_raw_heads_required(self):
        validate_scores([0.0]*16,[0.5]*16)
        with self.assertRaises(ValueError):validate_scores([0.0]*7,[0.5]*7)

    def test_scores_no_silent_transform(self):
        with self.assertRaises(ValueError):validate_scores([0.0]*16,[0.0]*16)
        with self.assertRaises(ValueError):validate_scores([float('nan')]*16,[0.5]*16)
        with self.assertRaises(ValueError):validate_scores([0.0]*16,[1.01]*16)
        validate_scores([-1000.0]*16,[0.0]*16)

    def test_pair_correlation_and_ties(self):
        self.assertAlmostEqual(pearson([1,2,3],[6,4,2]),-1)
        self.assertAlmostEqual(spearman([1,1,2,3],[2,2,4,6]),1)
        self.assertIsNone(pearson([1,1],[2,3]))
        with self.assertRaises(ValueError):pearson([1],[2,3])

    def test_review_deterministic_and_bounded(self):
        rows=joined();a=select_review(rows);b=select_review(list(reversed(rows)))
        self.assertEqual(a,b)
        self.assertEqual(len(a),50)
        self.assertEqual(len({r['song_id'] for r in a}),50)
        self.assertEqual({r['period'] for r in a},{r['period'] for r in rows})
        self.assertEqual(sum(r['sample_component']!='stratified_core' for r in a),20)

    def test_diagnostics_separate_core_and_sentinels(self):
        d=diagnostics(joined())
        for k in LABELS:
            self.assertEqual(d['all_200']['distributions'][k]['n'],200)
            self.assertEqual(d['core_180']['distributions'][k]['n'],180)
        self.assertEqual(sum(v['n'] for v in d['period_core'].values()),180)
        self.assertEqual(d['truncation']['all_200'],65)

if __name__=='__main__':unittest.main()
