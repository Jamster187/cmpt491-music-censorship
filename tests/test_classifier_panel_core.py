import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from classifier_panel_core import *

class PanelCoreTests(unittest.TestCase):
    def test_all_tokens_exactly_once(self):
        for budget in (1,8,510,1022):
            for n in (1,8,510,511,1022,1023,2301):
                spans=chunk_ranges(n,budget)
                self.assertEqual([x for a,b in spans for x in range(a,b)],list(range(n)))
                self.assertLessEqual(max(b-a for a,b in spans),budget)
                self.assertLessEqual(max(b-a for a,b in spans)-min(b-a for a,b in spans),1)
    def test_never_silently_drop_tail_or_overlap(self):
        for spans in ([(0,5)],[(0,5),(4,10)],[(0,5),(6,10)],[]):
            with self.assertRaises(ValueError):validate_ranges(spans,10,5)
        with self.assertRaises(ValueError):chunk_ranges(0,10)
    def test_mean_max_quantile_and_weights(self):
        a=aggregate([.1,.9],[9,1])
        self.assertAlmostEqual(a['mean'],.5)
        self.assertAlmostEqual(a['token_weighted_mean'],.18)
        self.assertEqual(a['max'],.9)
        self.assertAlmostEqual(a['q90'],.82)
        self.assertEqual(set(aggregate([.4],[3]).values()),{.4})
    def test_failure_never_zero_imputed(self):
        for v,w in [([],[]),([float('nan')],[1]),([.1],[0]),([1.1],[1]),([.1],[1,2])]:
            with self.assertRaises(ValueError):aggregate(v,w)
    def test_nli_neutral_not_silently_lost(self):
        self.assertAlmostEqual(bart_score([0,100,0]),.5)
        self.assertLess(softmax([0,100,0])[2],1e-40)
        self.assertAlmostEqual(sum(softmax([1,2,3])),1)
        self.assertEqual(sigmoid(-1000),0)

if __name__=='__main__':unittest.main()
