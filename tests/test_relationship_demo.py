"""Optional Streamlit checks against measured public discovery artifacts."""
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
AVAILABLE=importlib.util.find_spec('streamlit') is not None and (ROOT/'analysis/relationship_discovery/pilot_results/results.json.gz').exists()


@unittest.skipUnless(AVAILABLE,'Requires optional Streamlit and published discovery results')
class DiscoveryDemoTests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'src/relationship_demo.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        return app
    def test_each_family_displays_actual_saved_effect(self):
        rows=json.loads(gzip.decompress((ROOT/'analysis/relationship_discovery/pilot_results/results.json.gz').read_bytes()))
        lookup={r['candidate_id']:r for r in rows};app=self.app()
        for family in sorted({r['family'] for r in rows}):
            app.selectbox(key='family').select(family).run()
            self.assertFalse(app.exception,family)
            expected=lookup[app.session_state['displayed_candidate_id']]
            self.assertEqual(app.session_state['displayed_effect'],expected['effect'])
            self.assertEqual(app.session_state['displayed_r2'],expected.get('r2'))
    def test_filters_do_not_reselect_or_relabel_global_metrics(self):
        app=self.app();app.selectbox(key='family').select('nonlinear').run()
        before=app.session_state['displayed_effect'];candidate=app.session_state['displayed_candidate_id']
        app.selectbox(key='genre').select('Rock').run()
        app.slider(key='years').set_range(2010,2025).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['displayed_effect'],before)
        self.assertEqual(app.session_state['displayed_candidate_id'],candidate)
        self.assertTrue(any('complete-cohort' in x.value for x in app.info))
    def test_reconstruction_controls_are_explicit_and_temporal_is_descriptive(self):
        app=self.app();app.checkbox(key='include_reconstruction').check().run()
        app.selectbox(key='family').select('temporal').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('No breakpoint is called significant' in x.value for x in app.warning))
        self.assertTrue(any('already been inspected' in x.value for x in app.warning))


if __name__=='__main__':unittest.main()
