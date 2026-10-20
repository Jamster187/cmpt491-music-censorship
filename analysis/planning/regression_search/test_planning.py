"""Known-answer safeguards for planning arithmetic, leakage rules and timing code."""
import itertools
import json
import math
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge

import audit as a
import benchmark as b
import estimate as e


class SearchSpecificationTests(unittest.TestCase):
    def test_inclusion_exclusion_matches_independent_bruteforce(self):
        pool = list("abcdefg")
        forbidden = [["a","b"], ["b","c","d"]]
        for k in range(1,5):
            expected = sum(not any(set(s) <= set(c) for s in forbidden)
                           for c in itertools.combinations(pool,k))
            self.assertEqual(a.count_combinations(pool,forbidden,k), expected)
        self.assertEqual(a.count_combinations(pool,[],4),math.comb(7,4))

    def test_complete_eligible_target_coverage_no_target_as_predictor(self):
        specs = a.target_specs()
        self.assertEqual(len(specs),73)
        self.assertEqual(len({s["task_id"] for s in specs}),73)
        for c in a.SONG_POOL+a.DIAGNOSTIC:
            self.assertIn("songs:"+c, {s["task_id"] for s in specs})
        for s in specs:
            self.assertNotIn(s["target"], s["predictors"])
            self.assertNotIn("song_id",s["predictors"])
            self.assertNotIn("source_row_index",s["predictors"])
        for c in a.SCORES:
            self.assertEqual(a.candidate_plan("songs",c)["model_family"],"regression")
        self.assertEqual(a.candidate_plan("songs","best_chart_rank")["model_family"],"ordinal_rank")
        self.assertEqual(a.candidate_plan("songs","primary_genre")["model_family"],"multiclass")

    def test_correlations_retained_but_affine_target_leakage_blocked(self):
        p = a.candidate_plan("songs","detox_toxicity")
        self.assertIn("detox_insult",p["predictors"])
        self.assertIn("detox_severe_toxicity",p["predictors"])
        self.assertTrue(a.allowed(["mb_duration_min_seconds","mb_duration_max_seconds"],
                                  p["forbidden_subsets"]))
        self.assertFalse(a.allowed(a.SENTIMENT,p["forbidden_subsets"]))
        for c in a.SENTIMENT:
            p = a.candidate_plan("songs",c)
            other = sorted(set(a.SENTIMENT)-{c})
            self.assertTrue(set(other) <= set(p["predictors"]))
            self.assertFalse(a.allowed(other,p["forbidden_subsets"]))
            self.assertTrue(a.allowed(other[:1],p["forbidden_subsets"]))

    def test_chart_and_acquisition_leakage_restrictions(self):
        for table,rank in [("weekly","weekly_rank"),("monthly","monthly_rank")]:
            p = a.candidate_plan(table,rank)["predictors"]
            self.assertFalse(set(a.FINAL_HISTORY) & set(p))
            self.assertNotIn("reported_peak_position",p)
            self.assertIn("reported_last_week_rank",p)
            previous = a.candidate_plan(table,"reported_last_week_rank")["predictors"]
            self.assertNotIn(rank,previous)
            self.assertNotIn("reported_weeks_on_chart",previous)
        for c in ["lyrics_status","lyrics_available"]:
            self.assertFalse(set(a.SCORES) & set(a.candidate_plan("songs",c)["predictors"]))
        first=a.candidate_plan("songs","first_chart_date")["predictors"]
        self.assertFalse(set(a.MB_FIELDS+a.GENRES)&set(first))

    def test_split_purges_long_careers_and_never_shares_song(self):
        d = pd.DataFrame(dict(
            song_id=["a","a","b","b","c","d","e"],
            first_chart_date=["2001-01-01"]*2+["2011-01-01"]*2+
                             ["2018-01-01","2009-01-01","2017-01-01"],
            last_chart_date=["2002-01-01"]*2+["2013-01-01"]*2+
                            ["2020-01-01","2011-01-01","2019-01-01"]))
        labels = a.split_labels(d)
        self.assertEqual(labels.tolist(),["train","train","validation","validation",
                                          "test","purged_boundary_song","purged_boundary_song"])
        groups = [set(d.loc[labels.eq(x),"song_id"]) for x in ["train","validation","test"]]
        self.assertTrue(all(not left&right for left,right in itertools.combinations(groups,2)))

    def test_sample_is_bounded_deterministic_and_all_sizes_present(self):
        p = a.candidate_plan("songs","detox_toxicity")
        sample = b.sample_sets(p)
        self.assertEqual(sample,b.sample_sets(p))
        self.assertEqual(len(sample),64)
        self.assertEqual(len(set(sample)),64)
        for k in range(1,5):
            self.assertEqual(sum(len(c)==k for c in sample),16)
        self.assertTrue(all(a.allowed(c,p["forbidden_subsets"]) for c in sample))
        self.assertTrue(any(set(a.GENRES) <= set(c) for c in sample))

    def test_encoder_is_train_only_and_genre_remains_one_variable(self):
        tr = pd.DataFrame(dict(x=[1.,np.nan,3.],primary_genre=["Pop","Rock","Pop"],
                               secondary_genres=['[]','["Rock"]','[]']))
        va = pd.DataFrame(dict(x=[np.nan,999.],primary_genre=["Afrobeats / African Pop",None],
                               secondary_genres=['[]',None]))
        x,v,g = b.encode(tr,va,list(tr))
        # Imputed 2 lies at train mean. Validation outlier must not change it.
        self.assertAlmostEqual(v[0,g["x"][0]],0.)
        va2=va.copy();va2.loc[1,"x"]=-999999.
        x2,_,_=b.encode(tr,va2,list(tr))
        np.testing.assert_array_equal(x,x2)
        self.assertEqual(set(g),set(tr))
        self.assertEqual(a.encoded_width("primary_genre"),16)
        self.assertEqual(a.encoded_width("secondary_genres"),17)

    def test_cached_ols_ridge_match_direct_with_weights_and_intercept(self):
        rng=np.random.default_rng(491)
        X=np.column_stack([np.ones(50),rng.normal(size=(50,4))])
        y=rng.normal(size=50);w=rng.uniform(.1,2.,size=50)
        G=X.T@(w[:,None]*X);h=X.T@(w*y)
        for alpha in [0.,2.]:
            model=LinearRegression() if alpha==0 else Ridge(alpha=alpha)
            model.fit(X[:,1:],y,sample_weight=w)
            beta,fallback,_=b.gram_fit(G,h,alpha,X,y,w)
            np.testing.assert_allclose(X@beta,model.predict(X[:,1:]),atol=1e-10)
            self.assertFalse(fallback)
        # Exact duplicate must trigger robust OLS, not discard the combination.
        X[:,4]=X[:,3]
        beta,fallback,_=b.gram_fit(X.T@(w[:,None]*X),X.T@(w*y),0.,X,y,w)
        self.assertTrue(fallback)
        reference=np.linalg.lstsq(X*np.sqrt(w)[:,None],y*np.sqrt(w),rcond=None)[0]
        np.testing.assert_allclose(X@beta,X@reference,atol=1e-10)

    def test_saved_counts_match_specifications_and_input_hashes(self):
        specs=json.loads((a.OUT/"predictor_sets.json").read_text())
        counts=pd.read_csv(a.OUT/"search_counts.csv").set_index("task_id")
        for s in specs:
            expected=[a.count_combinations(s["predictors"],s["forbidden_subsets"],k)
                      for k in range(1,5)]
            self.assertEqual(counts.loc[s["task_id"],["k1","k2","k3","k4"]].tolist(),expected)
            self.assertEqual(counts.loc[s["task_id"],"total"],sum(expected))
        totals=json.loads((a.OUT/"search_totals.json").read_text())
        self.assertEqual(int(counts.total.sum()),totals["all_target_predictor_specifications"])
        manifest=json.loads((a.OUT/"audit_manifest.json").read_text())
        for rel,digest in manifest["input_hashes"].items():
            self.assertEqual(a.sha(a.ROOT/rel),digest,rel)
        self.assertEqual(a.sha(a.OUT/"audit.py"),manifest["audit_script_sha256"])
        targets=pd.read_csv(a.OUT/"target_inventory.csv").set_index("task_id")
        self.assertEqual(targets.loc["songs:snapshot_months_selected","target_encoding"],"original values")
        self.assertEqual(targets.loc["songs:first_snapshot_month","target_encoding"],"month index since 1970-01")

    def test_runtime_strata_partition_every_task_without_dropping_candidates(self):
        for s in a.target_specs():
            for k in range(1,5):
                actual=sum(e.stratum_count(s,k,g) for ng in range(3)
                           for g in itertools.combinations(a.GENRES,ng))
                self.assertEqual(actual,a.count_combinations(s["predictors"],s["forbidden_subsets"],k))

    def test_every_public_field_has_a_target_or_explicit_nontarget_disposition(self):
        fields=set(pd.read_csv(a.OUT/"schema_inventory.csv").query(
            "table.str.startswith('data/public/')",engine="python").field)
        targets=set(pd.read_csv(a.OUT/"target_inventory.csv").source_field)
        excluded=set(a.GLOBAL_EXCLUSIONS)|{"chart_date","snapshot_chart_date"}
        self.assertFalse(fields-targets-excluded)

    def test_benchmark_is_bounded_test_free_and_matches_current_code(self):
        result=json.loads((a.OUT/"benchmark_results.json").read_text())
        self.assertEqual(result["actual_sets"],192)
        self.assertEqual(result["test_rows_used"],0)
        self.assertFalse(result["full_campaign_run"])
        self.assertEqual(result["benchmark_script_sha256"],a.sha(a.OUT/"benchmark.py"))
        for r in result["summaries"]:
            self.assertLess(r["max_direct_cached_prediction_abs_difference"],1e-6)


if __name__=="__main__":
    unittest.main()
