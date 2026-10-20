"""Independent publication audit catches incomplete/corrupt campaign coverage."""
import sys
import csv
import json
import tempfile
from pathlib import Path
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"analysis/regression_search"))
import campaign_report as report
import publish_campaign as publication
from regression_store import Store


class CampaignAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.task = dict(predictors=["a", "b", "c"], forbidden_subsets=[])
        self.candidates = list(enumerate(report.spec.combinations(self.task)))
        self.store = Store(Path(self.temp.name)/"results.sqlite", {}, self.candidates, self.task["predictors"])
        self.addCleanup(self.store.close)
        self.addCleanup(self.store.db.rollback)
        # Exact ties exercise the frozen k/id ordering independently of row order.
        n = len(self.candidates)
        result = dict(r2=np.full(n,.4), mae=np.full(n,.2), mse=np.full(n,.1),
                      skill=np.full(n,.5), rank=np.ones(n,int), fallback=np.zeros(n,int))
        for fold in (2,0,1):
            self.store.save(fold, self.candidates, result, {}, {})

    def test_complete_catalog_all_folds_and_deterministic_ties(self):
        candidates, ranks, audit = report.catalog_and_scores(self.store.db, self.task)
        self.assertEqual(candidates, self.candidates)
        self.assertEqual([r["id"] for r in ranks], list(range(7)))
        self.assertEqual(audit["by_k"], {"1":3,"2":3,"3":1})
        self.assertEqual(audit["validation_fits"], 21)
        self.assertEqual(audit, report.catalog_and_scores(self.store.db, self.task)[2])

    def test_missing_validation_fold_is_rejected(self):
        self.store.db.execute("DELETE FROM scores WHERE id=2 AND fold=1")
        with self.assertRaisesRegex(ValueError, "Incomplete validation"):
            report.catalog_and_scores(self.store.db,self.task)

    def test_wrong_or_duplicate_combination_is_rejected(self):
        self.store.db.execute("UPDATE candidates SET i1=0 WHERE id=1")
        with self.assertRaisesRegex(ValueError, "eligible combinations"):
            report.catalog_and_scores(self.store.db,self.task)

    def test_nonfinite_metric_is_rejected(self):
        self.store.db.execute("UPDATE scores SET mae=? WHERE id=0 AND fold=0", (float("inf"),))
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            report.catalog_and_scores(self.store.db,self.task)

    def test_changed_metric_changes_logical_hash(self):
        original = report.catalog_and_scores(self.store.db,self.task)[2]
        self.store.db.execute("UPDATE scores SET mae=mae+.1 WHERE id=0 AND fold=0")
        changed = report.catalog_and_scores(self.store.db,self.task)[2]
        self.assertNotEqual(original["score_rows_sha256"], changed["score_rows_sha256"])
        self.assertNotEqual(original["ranking_sha256"], changed["ranking_sha256"])


class PublishedCampaignTests(unittest.TestCase):
    def test_units_match_actual_frozen_calendar_conversions(self):
        import pandas as pd
        frame=pd.DataFrame(dict(mb_earliest_release_date=["2000"],
            first_chart_date=["1971-01-01"],last_chart_date=["1971-01-01"],
            first_snapshot_month=["1971-01"],last_snapshot_month=["1971-01"]))
        converted=report.spec.original.convert(frame)
        self.assertEqual(converted.first_chart_date.iloc[0],365)
        self.assertEqual(converted.first_snapshot_month.iloc[0],12)
        self.assertEqual(publication.target_unit("first_chart_date"),"days since 1970-01-01")
        self.assertEqual(publication.target_unit("first_snapshot_month"),"months since 1970-01")
        self.assertEqual(publication.target_unit("last_snapshot_month"),"months since 1970-01")

    def test_public_results_preserve_coverage_selection_and_metrics(self):
        folder=ROOT/"analysis/regression_search/campaign"
        before=json.loads((folder/"coverage_before_test.json").read_text())
        after=json.loads((folder/"coverage_after_test.json").read_text())
        self.assertEqual(before["selection_sha256"],after["selection_sha256"])
        self.assertEqual(after["combinations"],1998901)
        self.assertEqual(after["validation_fits"],5996703)
        self.assertEqual(after["target_count"],59)
        self.assertFalse(before["final_test_evaluated"])
        self.assertTrue(after["final_test_evaluated"])
        for a,b in zip(before["targets"],after["targets"]):
            self.assertEqual(a["task_id"],b["task_id"])
            self.assertEqual(a["ranking_sha256"],b["ranking_sha256"])
            self.assertEqual(a["score_rows_sha256"],b["score_rows_sha256"])
            self.assertTrue(b["final"]["encoder_train_only"])
        with (folder/"target_leaderboard.csv").open() as stream:
            rows=list(csv.DictReader(stream))
        results=json.loads((folder/"target_leaderboard.json").read_text())
        self.assertEqual(len(rows),59)
        self.assertEqual(len({r["task_id"] for r in rows}),59)
        for r,saved in zip(rows,results):
            self.assertEqual(r["task_id"],saved["task_id"])
            self.assertEqual(r["units"],publication.target_unit(saved["target"]))
            self.assertEqual(json.loads(r["predictors"]),saved["predictors"])
            for short in ("r2","mae","rmse"):
                self.assertEqual(float(r["test_"+short]),saved[short])
            self.assertEqual(float(r["test_minus_validation_r2"]),saved["r2"]-saved["validation_r2"])
        with (folder/"best_by_predictor_count.csv").open() as stream:
            best=list(csv.DictReader(stream))
        self.assertEqual(len(best),177)
        self.assertEqual({(r["task_id"],int(r["k"])) for r in best},
                         {(r["task_id"],k) for r in rows for k in (1,2,3)})
        hierarchy=json.loads((folder/"hierarchy_manifest.json").read_text())
        self.assertEqual(len(hierarchy["files"]),59)
        self.assertEqual(sum(r["rows"] for r in hierarchy["files"]),1998901)
        models=json.loads((folder/"selected_models.json").read_text())["models"]
        self.assertEqual(len(models),59)
        for model,row in zip(models,rows):
            self.assertEqual(model["task_id"],row["task_id"])
            self.assertEqual(model["predictors"],json.loads(row["predictors"]))
            self.assertLessEqual(model["k"],3)


if __name__ == "__main__":
    unittest.main()
