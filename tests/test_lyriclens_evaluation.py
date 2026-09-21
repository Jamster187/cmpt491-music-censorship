"""Pilot scope, sampling, and interpretation tests; no model/network dependency."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import lyriclens_evaluation as ev

class LyricLensEvaluationTests(unittest.TestCase):
    def test_period_boundaries(self):
        for year,p in [(1958,0),(1969,0),(1970,1),(1999,3),(2010,5),(2026,6)]:
            self.assertEqual(ev.period(year),ev.PERIODS[p])
        with self.assertRaises(ValueError):ev.period(2027)

    def test_sampling_stable_under_reordering(self):
        rows=[dict(song_id=ev.digest(str(i)),best_chart_rank=i%90+1,word_count=(i*37)%120+1) for i in range(120)]
        a=ev.select_core(rows,26);b=ev.select_core(list(reversed(rows)),26)
        self.assertEqual(a,b)
        self.assertEqual(len({r['song_id'] for r in a}),26)
        self.assertEqual(len({r['sampling_cell'] for r in a}),6)

    def test_small_stratum_fails_instead_of_repeating(self):
        with self.assertRaises(ValueError):ev.select_core([],1)

    def test_full_corpus_and_duplicate_samples_refused(self):
        rows=[dict(song_id='song_'+ev.digest(str(i)),sample_component=(
            'stratified_core' if i<180 else 'expected_mild' if i<190 else 'expected_content')) for i in range(200)]
        ev.validate_sample(rows)
        for invalid in (rows[:199],rows+rows,rows[:-1]+[rows[0]]):
            with self.assertRaises(ValueError):ev.validate_sample(invalid)

    def test_raw_label_order_and_distinct_csi_semantics(self):
        scores=ev.score_summary([0.1,0.2,0.3,0.9],{'severity':20,'mcr_rating':'M-R'})
        self.assertEqual(scores['substance_use_score'],0.3)
        self.assertEqual(scores['explicit_language_score'],0.9)
        self.assertEqual(scores['CSI'],37.5)
        self.assertEqual(scores['app_CSI'],20)
        for p in ([0,0,0],[-1,0,0,0],[float('nan'),0,0,0]):
            with self.assertRaises(ValueError):ev.score_summary(p,{'severity':0,'mcr_rating':'M-E'})

    def test_upstream_extraction_does_not_execute_application(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'app.py';p.write_text("raise RuntimeError('UI should not execute')\ndef selected():\n    return 7\n")
            env={};exec(ev.extract_definitions(p,{'selected'}),env)
            self.assertEqual(env['selected'](),7)
            with self.assertRaises(ValueError):ev.extract_definitions(p,{'missing'})


class LyricLensDiagnosticsTests(unittest.TestCase):
    def test_quantiles_and_rank_ties(self):
        from lyriclens_diagnostics import quantile,ranks,spearman
        self.assertEqual(quantile([0,10],.25),2.5)
        self.assertEqual(ranks([3,1,1]),[3,1.5,1.5])
        self.assertAlmostEqual(spearman([1,2,3],[3,2,1]),-1)
        self.assertIsNone(spearman([1,1],[1,2]))

if __name__=='__main__':unittest.main()
