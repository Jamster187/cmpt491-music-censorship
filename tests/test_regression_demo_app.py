"""Actual-data Streamlit interaction tests in the optional isolated demo environment."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
AVAILABLE=importlib.util.find_spec("streamlit") is not None and (ROOT/"data/experiments/regression_search/meaningful_v1/models").exists()


@unittest.skipUnless(AVAILABLE,"Requires the optional demo environment and complete local campaign artifacts")
class ProfessorDemoTests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest
        at=AppTest.from_file(str(ROOT/"src/regression_demo.py"),default_timeout=90).run()
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        return at

    def test_real_example_manual_input_and_availability_warning(self):
        import regression_demo_model as api
        import regression_meaningful as m
        at=self.app()
        task=at.selectbox(key="target").value
        candidate=at.selectbox(key="candidate_select").value
        model,metrics,dest=api.fit_candidate(task,candidate)
        self.assertEqual(at.metric[0].value,f"{metrics['r2']:.4f}")
        raw=m.original.read_table(m.target_task(task)['table'])
        import pandas as pd
        pred=pd.read_csv(dest/'predictions.csv.gz',float_precision='round_trip')
        example=api.input_rows(raw.loc[[int(pred.source_row.iloc[0])]],model['predictors']).iloc[0].to_dict()
        self.assertAlmostEqual(at.session_state['last_prediction'],api.predict_values(model,example),places=9)
        at.radio(key='input_mode').set_value('Enter values').run()
        numeric=next(p for p in model['predictors'] if p.startswith('detox_'))
        widget=task+':'+str(candidate)+':'+numeric
        at.number_input(key=widget).set_value(.8)
        example[numeric]=.8
        next(b for b in at.button if b.label=='Generate prediction').click().run()
        self.assertFalse(at.exception);self.assertFalse(at.error)
        self.assertAlmostEqual(at.session_state['last_prediction'],api.predict_values(model,example),places=9)
        at.selectbox(key='scenario').set_value('At first chart appearance (availability check)').run()
        self.assertTrue(any('unverified' in w.value for w in at.warning))
        self.assertTrue(next(b for b in at.button if b.label=='Generate prediction').disabled)

    def test_all_three_views_and_actual_cross_domain_winner(self):
        import regression_meaningful as m
        at=self.app()
        at.radio(key='view').set_value('C · Cross-domain').run()
        self.assertFalse(at.exception);self.assertFalse(at.error)
        row=next(r for r in m.read_json(m.PUBLIC/'cross_domain_leaderboard.json') if r['task_id']=='songs:ll_violence')
        self.assertEqual(at.metric[0].value,f"{row['r2']:.4f}")
        self.assertEqual(len(at.dataframe[0].value),59)
        at.radio(key='view').set_value('B · Target predictability').run()
        at.radio(key='leaderboard_variant').set_value('Original unrestricted').run()
        self.assertFalse(at.exception);self.assertFalse(at.error)
        self.assertEqual(len(at.dataframe[0].value),59)
        at.selectbox(key='leaderboard_sort').set_value('Test R²: lowest first').run()
        frame=at.dataframe[0].value
        self.assertLessEqual(frame.r2.iloc[0],frame.r2.iloc[-1])

    def test_arbitrary_one_predictor_refit_and_circular_warning(self):
        at=self.app()
        at.selectbox(key='target').set_value('songs:chart_weeks').run()
        at.radio(key='hierarchy_mode').set_value('Unrestricted').run()
        self.assertTrue(any('reconstruction' in w.value for w in at.warning))
        at.selectbox(key='predictor_count').set_value(1).run()
        # Select a genuinely arbitrary model, not a published selected winner.
        import regression_meaningful as m
        candidate=list(m.hierarchy('songs:chart_weeks','unrestricted',k=1))[1]['id']
        at.selectbox(key='candidate_select').set_value(candidate).run()
        if any(b.key=='load_model' for b in at.button):at.button(key='load_model').click().run()
        self.assertFalse(at.exception);self.assertFalse(at.error)
        self.assertGreater(len(at.metric),4)
        self.assertIn('last_prediction',at.session_state)

    def test_manual_secondary_genres_and_missing_input_match_model(self):
        import regression_meaningful as m
        import regression_demo_model as api
        import pandas as pd
        at=self.app()
        at.radio(key='view').set_value('C · Cross-domain').run()
        at.selectbox(key='target').set_value('songs:ll_explicit_language').run()
        chosen=next(r for r in m.read_json(m.PUBLIC/'cross_domain_leaderboard.json') if r['task_id']=='songs:ll_explicit_language')
        task=chosen['task_id'];candidate=chosen['candidate_id']
        model,_,dest=api.fit_candidate(task,candidate)
        pred=pd.read_csv(dest/'predictions.csv.gz')
        raw=m.original.read_table('songs')
        values=api.input_rows(raw.loc[[int(pred.source_row.iloc[0])]],model['predictors']).iloc[0].to_dict()
        at.radio(key='input_mode').set_value('Enter values').run()
        prefix=task+':'+str(candidate)+':'
        at.checkbox(key=prefix+'secondary_genres:missing').set_value(False)
        at.multiselect(key=prefix+'secondary_genres').set_value(['Rock'])
        at.checkbox(key=prefix+'primary_genre:missing').set_value(True)
        next(b for b in at.button if b.label=='Generate prediction').click().run()
        self.assertFalse(at.exception);self.assertFalse(at.error)
        values.update(primary_genre=None,secondary_genres='["Rock"]')
        self.assertAlmostEqual(at.session_state['last_prediction'],api.predict_values(model,values),places=9)


if __name__=='__main__':unittest.main()
