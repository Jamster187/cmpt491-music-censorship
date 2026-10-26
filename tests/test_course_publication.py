"""Public-only completeness, leakage, evidence and result-provenance regressions."""
import itertools
import json
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
from scipy import stats

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import course_common as c
import course_demo_model as demo


class CoursePublicationTests(unittest.TestCase):
    def test_complete_rule_search_and_global_correction(self):
        rules=pd.read_csv(c.PUBLIC/"association_rules/all_rules.csv.gz",float_precision="round_trip")
        self.assertEqual(len(rules),20928);self.assertEqual(rules.rule_id.nunique(),20928)
        self.assertEqual(rules.family.value_counts().to_dict(),{"primary":11783,"negative":5271,"rare_pair":3874})
        np.testing.assert_allclose(stats.false_discovery_control(rules.p_value,method="by"),rules.q_by_global,rtol=5e-12,atol=1e-14)
        self.assertTrue((rules.loc[~rules.test_supported,"p_value"]==1).all())
        self.assertTrue((rules.q_by_global>.05).any())
        self.assertTrue((rules.test_lift<1).any())
        self.assertFalse(rules[(rules.antecedent=='["emotion_grief=high", "top10=no"]')&(rules.consequent=="emotion_sadness=high")].strict_cross_domain.any())

    def test_all_algorithms_supports_and_bounded_size_are_published(self):
        table=pd.read_csv(c.PUBLIC/"frequent_patterns/algorithm_comparison.csv")
        self.assertEqual(set(zip(table.algorithm,table.support_threshold)),set(itertools.product(["apriori","fpgrowth","eclat"],[.05,.08,.12])))
        for support,count in [(.05,22993),(.08,4087),(.12,1072)]:
            rows=pd.read_csv(c.PUBLIC/f"frequent_patterns/itemsets_support_{support:.2f}.csv.gz")
            self.assertEqual(len(rows),count);self.assertLessEqual(rows["size"].max(),4)
            self.assertTrue(rows.closed.any());self.assertTrue(rows.maximal.any())
            self.assertTrue(rows.loc[rows.maximal,"closed"].all())
            self.assertEqual(table[table.support_threshold==support].result_sha256.nunique(),1)

    def test_classification_uses_only_lyrics_and_training_quantiles(self):
        frame=c.data();exports=demo.read_json(c.PUBLIC/"classification/models.json.gz")
        self.assertEqual(len(exports),12)
        for record in exports.values():
            start,end=record["period"];train,test=c.partitions(frame,start,end);inner,val=c.partitions(frame,start-5,start)
            self.assertEqual(record["threshold"],float(inner.chart_weeks.quantile(.75)))
            self.assertEqual(record["split_hashes"]["train"],c.digest(train.song_id.tolist()))
            self.assertEqual(record["split_hashes"]["test"],c.digest(test.song_id.tolist()))
            self.assertFalse(set(train.song_id)&set(test.song_id));self.assertFalse(set(inner.song_id)&set(val.song_id))
            for model in record["models"].values():self.assertEqual(model["features"],c.SCORES)
            self.assertEqual(sum(r["training_n"] for r in record["models"]["tree"]["rules"]),len(train))
            np.testing.assert_allclose(record["models"]["naive_bayes"]["mean"],train[c.SCORES].to_numpy().mean(axis=0),atol=1e-13)

    def test_complete_clustering_grid_and_unsupported_results_remain(self):
        grid=pd.read_csv(c.PUBLIC/"clustering/grid.csv")
        self.assertEqual(len(grid),99)
        self.assertEqual(set(zip(grid.method,grid.representation,grid.k)),set(itertools.product(c.CONFIG["clustering_methods"],c.CONFIG["clustering_representations"],range(2,13))))
        self.assertTrue((grid.loc[grid.method!="kmeans","fit_n"]==1200).all())
        selected=pd.read_csv(c.PUBLIC/"clustering/selected_configurations.csv")
        self.assertFalse(selected[selected.method=="kmedoids"].selection_supported.any())
        assignments=pd.read_csv(c.PUBLIC/"clustering/assignments.csv.gz")
        self.assertTrue(assignments.song_id.is_unique);self.assertEqual(len(assignments.columns),11)
        self.assertIn("purged_boundary",set(assignments.split))
        self.assertEqual(len(assignments),20595)

    def test_publication_hashes_and_verified_replay(self):
        manifest=demo.read_json(c.PUBLIC/"artifact_manifest.json")
        for section in ("sha256","sources_sha256"):
            for name,digest in manifest[section].items():self.assertEqual(c.sha(ROOT/name),digest,name)
        protocol=demo.read_json(c.PUBLIC/"protocol.json")
        self.assertEqual(c.sha(c.INPUT),protocol["input_sha256"])
        replay=demo.read_json(c.PUBLIC/"replay_validation.json")
        self.assertEqual(replay["status"],"PASS")
        self.assertEqual(replay["refit_replay"]["classification_folds_refit"],12)
        self.assertEqual(replay["refit_replay"]["cluster_configurations_refit"],27)
        self.assertTrue(replay["refit_replay"]["exact_logical_replay"])
        figures=demo.read_json(c.PUBLIC/"figure_index.json")
        self.assertEqual(len(figures),7)
        self.assertTrue(all((c.PUBLIC/f["file"]).is_file() for f in figures))


if __name__=="__main__":unittest.main()
