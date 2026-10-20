"""Definition-based filtering and actual model-interface regressions."""
import sys
import csv
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import regression_relationships as rel
import regression_spec as spec
import regression_core as core
import regression_demo_model as model_api


class RelationshipTests(unittest.TestCase):
    def test_definition_aliases_are_circular(self):
        for target,predictor in [("chart_weeks","weekly_observation_count"),
            ("last_chart_date","last_snapshot_month"),("first_chart_date","first_snapshot_month"),
            ("mb_duration_median_seconds","mb_duration_min_seconds")]:
            self.assertEqual(rel.classify(target,[predictor])["category"],rel.A)

    def test_component_rule_needs_both_endpoints_and_retains_other_count_predictors(self):
        self.assertFalse(rel.circular_reasons("chart_weeks",["first_chart_date"]))
        self.assertIn("career_interval_exposure",rel.circular_reasons("chart_weeks",["first_chart_date","last_snapshot_month"]))
        self.assertEqual(rel.classify("chart_weeks",["snapshot_months_selected"])["category"],rel.B)
        self.assertEqual(rel.classify("total_chart_points",["chart_weeks","best_chart_rank"])["category"],rel.B)

    def test_correlated_same_family_scores_and_counts_remain_eligible(self):
        for target,predictor in [("detox_toxicity","detox_insult"),("ll_explicit_language","detox_obscene"),
            ("emotion_joy","sentiment_positive"),("mb_recording_count","mb_release_count")]:
            self.assertEqual(rel.classify(target,[predictor])["category"],rel.B)

    def test_cross_domain_requires_every_predictor_to_differ_from_target(self):
        self.assertEqual(rel.classify("ll_violence",["primary_genre","mb_release_year","sentiment_negative"])["category"],rel.C)
        mixed=rel.classify("detox_toxicity",["detox_insult","primary_genre"])
        self.assertEqual(mixed["category"],rel.B)
        self.assertTrue(mixed["mixed_domains"])
        self.assertFalse(mixed["pure_cross_domain"])

    def test_all_campaign_variables_have_explicit_domains_and_policy_has_no_data_threshold(self):
        for t in spec.specs():
            if t["model_family"]=="regression":
                for n in [t["target"]]+t["predictors"]:self.assertIsInstance(rel.domain(n),str)
        with self.assertRaisesRegex(ValueError,"reviewed domain"):rel.domain("new_unreviewed_feature")
        self.assertEqual(rel.policy(),rel.policy())


class PredictionInterfaceTests(unittest.TestCase):
    def model(self):
        raw=pd.DataFrame(dict(first_chart_date=["1971-01-01","1972-01-01","1973-01-01"],
            first_snapshot_month=["1971-01","1972-01","1973-01"],
            secondary_genres=['[]','["Rock"]',None]))
        predictors=list(raw)
        frame=model_api.convert_inputs(raw,predictors)
        enc=core.Encoder().fit(frame,predictors)
        x=enc.transform(frame)
        model=dict(predictors=predictors,encoder=enc.state,coefficients=np.arange(x.shape[1],dtype=float).tolist(),
            target_center=7.,input_ranges={p:dict(min=None,max=None) for p in predictors})
        return raw,model,x

    def test_manual_and_dataset_inputs_use_same_date_genre_and_coefficient_order(self):
        raw,model,x=self.model()
        expected=x@np.array(model['coefficients'])+7
        np.testing.assert_allclose(model_api.predict_frame(model,raw),expected)
        # Force JSON-like alphabetic key ordering different from the requested order.
        model['encoder']=dict(sorted(model['encoder'].items(),reverse=True))
        for i,row in raw.iterrows():self.assertAlmostEqual(model_api.predict_values(model,row.to_dict()),expected[i])
        converted=model_api.convert_inputs(raw,list(raw))
        self.assertEqual(converted.first_snapshot_month.iloc[0],12)
        self.assertEqual(converted.first_chart_date.iloc[0],365)

    def test_missing_empty_and_unknown_genres_are_distinct_and_invalid_inputs_fail(self):
        raw,model,_=self.model()
        a=raw.iloc[0].to_dict();b=dict(a,secondary_genres=None)
        self.assertNotEqual(model_api.predict_values(model,a),model_api.predict_values(model,b))
        with self.assertRaisesRegex(ValueError,"Invalid secondary genre"):
            model_api.predict_values(model,dict(a,secondary_genres='["Invented"]'))
        with self.assertRaisesRegex(ValueError,"exactly"):
            model_api.predict_values(model,dict(a,outcome=999))

    def test_scenario_warnings_precede_unavailable_inputs(self):
        predictors=['chart_weeks','primary_genre','first_chart_date']
        self.assertEqual(model_api.availability_warnings(predictors,'Retrospective frozen-release analysis'),[])
        warnings=model_api.availability_warnings(predictors,'At first chart appearance')
        self.assertTrue(any('chart_weeks' in w and 'unavailable' in w for w in warnings))
        self.assertTrue(any('primary_genre' in w and 'unverified' in w for w in warnings))


class PublishedMeaningfulTests(unittest.TestCase):
    def test_complete_counts_locks_and_all_best_by_size_models(self):
        folder=ROOT/'analysis/regression_search/meaningful'
        audit=json.loads((folder/'filter_audit.json').read_text())
        self.assertEqual(audit['source_combinations'],1998901)
        self.assertEqual(audit['eligible_combinations']+audit['excluded_combinations'],1998901)
        self.assertEqual(audit['excluded_combinations'],32619)
        self.assertEqual(audit['cross_domain_combinations'],789225)
        policy=json.loads((folder/'relationship_policy.json').read_text())
        selected=json.loads((folder/'selected_candidates.json').read_text())
        self.assertEqual(spec.digest(policy),selected['policy_sha256'])
        self.assertEqual(spec.original.sha(folder/'selected_candidates.json'),audit['selection_sha256'])
        self.assertFalse(selected['selection_uses_test'])
        self.assertEqual(policy['new_test_evaluations_at_lock'],0)
        with (folder/'best_by_predictor_count.csv').open() as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),354)
        self.assertEqual(len({(r['task_id'],r['view'],r['k']) for r in rows}),354)
        for target in selected['targets']:
            for mode in ['filtered','cross_domain']:
                self.assertEqual({r['k'] for r in target['best_by_k'][mode]},{1,2,3})
                self.assertIsNotNone(target['winners'][mode])

    def test_leaderboards_match_frozen_validation_choices_and_keep_posthoc_labels(self):
        folder=ROOT/'analysis/regression_search/meaningful'
        selected={r['task_id']:r for r in json.loads((folder/'selected_candidates.json').read_text())['targets']}
        for mode in ['filtered','cross_domain']:
            rows=json.loads((folder/(mode+'_leaderboard.json')).read_text())
            self.assertEqual(len(rows),59)
            self.assertEqual(len({r['task_id'] for r in rows}),59)
            for row in rows:
                winner=selected[row['task_id']]['winners'][mode]
                self.assertEqual(row['candidate_id'],winner['id'])
                self.assertEqual(row['predictors'],winner['predictors'])
                self.assertEqual(row['validation_r2'],winner['validation_r2'])
                self.assertEqual(row['test_minus_validation_r2'],row['r2']-row['validation_r2'])
                self.assertEqual(row['evaluation_label'],'POST-HOC EXPLORATORY')
                self.assertTrue(row['test_previously_inspected'])
                self.assertNotEqual(row['category'],rel.A)
                if mode=='cross_domain':self.assertEqual(row['category'],rel.C)


if __name__=="__main__":unittest.main()
