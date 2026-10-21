"""Optional classroom checks against complete Phase 1 measured results."""
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'analysis/relationship_discovery/full_phase1/demo_results.json.gz'
AVAILABLE=importlib.util.find_spec('streamlit') is not None and RESULTS.exists()


@unittest.skipUnless(AVAILABLE,'Requires optional Streamlit and completed Phase 1 results')
class PhaseOneDemoTests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'src/relationship_demo.py'),default_timeout=40).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['displayed_collection'],'Full Phase 1')
        return app
    def test_three_families_show_saved_full_campaign_values(self):
        rows=json.loads(gzip.decompress(RESULTS.read_bytes()));lookup={r['candidate_id']:r for r in rows};app=self.app()
        self.assertEqual(len(rows),9159)
        for family in ['pairwise','nonlinear','genre_interaction']:
            app.selectbox(key='family').select(family).run()
            self.assertFalse(app.exception)
            row=lookup[app.session_state['displayed_candidate_id']]
            self.assertEqual(app.session_state['displayed_effect'],row.get('effect'))
            self.assertEqual(app.session_state['displayed_r2'],row.get('r2'))
            self.assertEqual(row['family'],family)
    def test_cross_source_filter_and_supporting_filters_preserve_metrics(self):
        rows=json.loads(gzip.decompress(RESULTS.read_bytes()));lookup={r['candidate_id']:r for r in rows};app=self.app()
        app.checkbox(key='cross_only').check().run()
        app.checkbox(key='different_sources').check().run()
        self.assertFalse(app.exception)
        candidate=app.session_state['displayed_candidate_id'];value=app.session_state['displayed_effect']
        self.assertTrue(lookup[candidate]['category'].startswith('C'))
        self.assertTrue(lookup[candidate]['priority_cross_domain'])
        app.selectbox(key='genre').select('Rock').run()
        app.slider(key='years').set_range(2010,2025).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['displayed_candidate_id'],candidate)
        self.assertEqual(app.session_state['displayed_effect'],value)
    def test_previous_pilot_remains_accessible(self):
        app=self.app();app.selectbox(key='collection').select('Preserved pilot').run()
        app.selectbox(key='family').select('temporal').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['displayed_collection'],'Preserved pilot')
        self.assertTrue(any('No breakpoint is called significant' in w.value for w in app.warning))
    def test_pairwise_view_can_select_the_ordinal_variable_from_either_side(self):
        rows=json.loads(gzip.decompress(RESULTS.read_bytes()));lookup={r['candidate_id']:r for r in rows};app=self.app()
        app.selectbox(key='family').select('pairwise').run()
        self.assertIn('best_chart_rank',app.selectbox(key='target').options)
        self.assertEqual(len(app.selectbox(key='target').options),75)
        app.selectbox(key='target').select('best_chart_rank').run()
        self.assertFalse(app.exception)
        row=lookup[app.session_state['displayed_candidate_id']]
        self.assertIn('best_chart_rank',[row['target'],*row['predictors']])
        self.assertIsNone(row.get('pearson'))
        self.assertIsNone(row.get('r2'))
        self.assertIn(row['primary_statistic_name'],{'absolute Spearman rho','rank eta squared'})


if __name__=='__main__':unittest.main()
