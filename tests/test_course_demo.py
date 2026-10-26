"""Actual Streamlit interactions in the existing optional demo environment."""
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import course_demo_model as api
AVAILABLE=importlib.util.find_spec("streamlit") is not None


@unittest.skipUnless(AVAILABLE,"Requires the existing optional Streamlit demo environment")
class CourseDemoTests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/"src/course_demo.py"),default_timeout=60).run()
        self.assertFalse(app.exception);self.assertFalse(app.error)
        return app

    def test_tree_bayes_rule_examples_and_manual_input(self):
        app=self.app();models=api.read_json(api.PUBLIC/"classification/models.json.gz")
        frame=pd.read_csv(ROOT/"data/public/songs.csv").set_index("song_id")
        for choice,method in [("Decision tree","tree"),("Naïve Bayes","naive_bayes"),("IF–THEN rules","tree")]:
            app.radio(key="classifier").set_value(choice).run();self.assertFalse(app.exception)
            record=models["top10_2018"]["models"][method];values=frame.loc[app.session_state["input_song_id"],record["features"]].to_numpy(float)
            self.assertEqual(app.session_state["last_prediction"],api.predict(record,values)[0][0])
        app.checkbox(key="manual_input").set_value(True).run()
        app.number_input(key="manual_value").set_value(.75).run();self.assertFalse(app.exception)
        record=models["top10_2018"]["models"]["tree"];values=frame.loc[app.session_state["input_song_id"],record["features"]].to_numpy(float)
        values[record["features"].index(app.selectbox(key="manual_feature").value)]=.75
        self.assertEqual(app.session_state["last_prediction"],api.predict(record,values)[0][0])

    def test_all_views_and_unsupported_cluster_warning(self):
        app=self.app()
        app.radio(key="view").set_value("Frequent patterns").run();self.assertFalse(app.exception)
        app.radio(key="itemset_kind").set_value("Closed").run();self.assertFalse(app.exception)
        app.radio(key="view").set_value("Association rules").run();self.assertFalse(app.exception)
        self.assertIn("selected_rule",app.session_state)
        app.radio(key="view").set_value("Clustering").run();self.assertFalse(app.exception)
        self.assertIn("last_cluster",app.session_state)
        app.selectbox(key="cluster_configuration").set_value("kmedoids_standardized42_k11").run()
        self.assertFalse(app.exception);self.assertTrue(app.warning)


if __name__=="__main__":unittest.main()
