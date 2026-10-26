"""Optional classroom-interface tests in the existing Streamlit environment."""
import importlib.util
from pathlib import Path
import unittest
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
AVAILABLE=importlib.util.find_spec('streamlit') is not None and (ROOT/'analysis/feature_expansion_v1/historical_sensitivity.csv').exists()


@unittest.skipUnless(AVAILABLE,'Requires optional Streamlit and published feature-expansion results')
class FeatureDemoTests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest
        return AppTest.from_file(str(ROOT/'src/feature_expansion_demo.py'),default_timeout=45).run()

    def test_default_replays_real_models_and_baseline_tables(self):
        app=self.app();self.assertFalse(app.exception);self.assertEqual(len(app.metric),5)
        self.assertEqual(app.radio[0].value,'Known at chart publication');self.assertTrue(app.warning)
        self.assertTrue(any('baseline' in list(d.value.columns) for d in app.dataframe))

    def test_retrospective_and_numerical_views(self):
        app=self.app();app.radio[0].set_value('Retrospective content comparison').run();self.assertFalse(app.exception)
        app.selectbox[0].set_value('new_only').run();app.selectbox[2].set_value('chart_weeks').run()
        self.assertFalse(app.exception);self.assertTrue(app.info);self.assertTrue(any('mae' in list(d.value.columns) for d in app.dataframe))

    def test_top10_debut_is_already_known(self):
        app=self.app();f=pd.read_csv(ROOT/'data/public/feature_expansion_v1/song_features.csv.xz')
        o=pd.read_csv(ROOT/'data/public/feature_expansion_v1/song_outcomes.csv.xz');f=f.merge(o,on='song_id')
        sid=f[f.first_chart_date.ge('2018-01-01')&f.eligible_26&f.debut_rank.le(10)].sort_values('first_chart_date').song_id.iloc[0]
        app.selectbox[1].set_value(sid).run();self.assertFalse(app.exception);self.assertEqual(app.metric[0].value,'Known at debut')


if __name__=='__main__':unittest.main()
