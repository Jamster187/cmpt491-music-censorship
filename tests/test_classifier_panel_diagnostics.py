import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from classifier_panel_diagnostics import percentiles,agreement,overlap

class PanelAgreementTests(unittest.TestCase):
    def test_frozen_theme_contract(self):
        import hashlib,json
        path=Path(__file__).resolve().parents[1]/'docs/classifier_panel_themes.json'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),'40d10924a9ebf27be2b2f1bf4884aa5004863e758e4d166937dbb8204bc13b8c')
        spec=json.loads(path.read_text())
        self.assertEqual(len(spec['themes']),17)
        self.assertTrue(spec['multi_label'])
        self.assertEqual(spec['hypothesis_template'],'This song contains {}.')

    def test_midrank_ties(self):
        self.assertEqual(percentiles([1,1,2]),[.25,.25,1])
        self.assertEqual(percentiles([3,3,3]),[.5,.5,.5])
    def test_identical_order_not_identical_units(self):
        x=[i/10 for i in range(10)];y=[v*v for v in x]
        a=agreement(x,y)
        self.assertAlmostEqual(a['spearman'],1)
        self.assertEqual(a['mean_absolute_percentile_gap'],0)
        self.assertEqual(a['high_jaccard'],1)
    def test_constant_outputs_have_no_forced_extremes(self):
        a=agreement([.001]*10,[.002]*10)
        self.assertIsNone(a['spearman'])
        self.assertEqual(a['high_a_count'],0)
        self.assertIsNone(a['high_jaccard'])
        self.assertEqual(a['within_10_percentile_points'],10)
    def test_opposite_rankings(self):
        a=agreement(list(range(10)),list(reversed(range(10))))
        self.assertAlmostEqual(a['spearman'],-1)
        self.assertEqual(a['opposite_quintiles'],4)
        self.assertEqual(a['high_intersection'],0)
    def test_mismatched_rows_rejected(self):
        with self.assertRaises(ValueError):agreement([1,2],[1])

if __name__=='__main__':unittest.main()
