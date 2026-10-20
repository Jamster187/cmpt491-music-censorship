"""Search coverage, numerical accuracy, leakage boundaries and crash/resume regressions."""
import itertools
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
import regression_core as c
import regression_search as run
import regression_spec as s
from regression_store import Store


def fixture():
    rng = np.random.default_rng(42)
    rows = []
    for year in (1980, 1995, 2005, 2012, 2016, 2020):
        for song in range(12):
            x = rng.normal()
            for repeat in range(1+song % 3):
                rows.append(dict(song_id=f"{year}-{song}", first_chart_date=f"{year}-01-01",
                    last_chart_date=f"{year}-09-01", first_snapshot_month=f"{year}-01",
                    last_snapshot_month=f"{year}-09", mb_earliest_release_date=str(year),
                    x=x, duplicate=x, absent=np.nan, constant=4.,
                    z=np.nan if song % 4 == 0 else rng.normal(),
                    primary_genre="Pop" if song % 2 else "Rock",
                    secondary_genres="[]" if song % 2 else '["Pop"]',
                    y=3*x + repeat*.2 + rng.normal(scale=.1)))
    return pd.DataFrame(rows)


def task():
    return dict(task_id="songs:y", table="songs", target="y", model_family="regression",
                predictors=["absent", "duplicate", "primary_genre", "x", "z"], forbidden_subsets=[])


class RegressionSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = threadpool_limits(limits=1)

    @classmethod
    def tearDownClass(cls):
        cls.threads.restore_original_limits()

    def tearDown(self):
        run.read_table.cache_clear()

    def test_current_counts_exactly_match_enumeration_and_only_three_sizes(self):
        totals = {1: 0, 2: 0, 3: 0}
        plans = s.specs()
        self.assertEqual(sum(t["model_family"] == "regression" for t in plans), 59)
        self.assertEqual(len(plans), 73)
        for plan in plans:
            counts = {k: 0 for k in (1, 2, 3)}
            for combo in s.combinations(plan):
                counts[len(combo)] += 1
                self.assertNotIn(plan["target"], combo)
            self.assertEqual(counts, {k: s.count(plan, k) for k in (1, 2, 3)})
            if plan["model_family"] == "regression":
                for k in counts:
                    totals[k] += counts[k]
        self.assertEqual(totals, {1: 3466, 2: 100118, 3: 1895317})

    def test_leakage_restrictions_retained_and_ordinary_correlations_allowed(self):
        plans = {p["task_id"]: p for p in s.specs()}
        self.assertIn("detox_insult", plans["songs:detox_toxicity"]["predictors"])
        for table in ("monthly", "weekly"):
            self.assertFalse(set(s.original.FINAL_HISTORY) & set(plans[table+":reported_weeks_on_chart"]["predictors"]))
        sentiment = plans["songs:sentiment_positive"]
        self.assertNotIn(("sentiment_negative", "sentiment_neutral"), list(s.combinations(sentiment)))
        self.assertTrue(set(s.original.SCORES).isdisjoint(plans["songs:lyrics_status"]["predictors"]))

    def test_all_rank_deficient_and_genre_fits_match_direct_svd(self):
        t = task()
        fold = c.prepare(fixture(), t, *s.FOLDS[2])
        combos = list(s.combinations(t))
        result, timing = fold.evaluate(combos, row_batch=3)
        self.assertGreater(timing["qr_svd_fallbacks"], 0)
        for i, combo in enumerate(combos):
            check = fold.reference_check(combo)
            self.assertLess(check["max_prediction_scaled_error"], 1e-9)
            B, _, _ = fold.fit_batch([combo])
            exact = c.metrics(fold.z, fold.V@B[:, 0]+fold.mean, fold.u, fold.mean, fold.median)
            for key in ("r2", "mae", "mse", "skill"):
                self.assertAlmostEqual(result[key][i], exact[key], places=10)

    def test_near_collinearity_uses_qr_and_retains_rank(self):
        raw = fixture()
        raw["duplicate"] = raw.x + np.random.default_rng(7).normal(scale=1e-10, size=len(raw))
        fold = c.prepare(raw, task(), *s.FOLDS[2])
        combo = ("duplicate", "x")
        _, rank, fallback = fold.fit_batch([combo])
        self.assertTrue(fallback[0])
        # Extremely ill-conditioned coefficients are allowed; predictions are
        # tested at a scale-aware tolerance against original-row direct SVD.
        fold.reference_check(combo)
        self.assertEqual(rank[0], 3)

    def test_encoder_learns_only_training_and_preserves_genre_group(self):
        train = pd.DataFrame(dict(x=[1., np.nan, 3.], absent=[np.nan]*3,
            primary_genre=["Pop", "Rock", "Pop"], secondary_genres=['[]', '["Rock"]', '[]']))
        val = pd.DataFrame(dict(x=[np.nan, 10000.], absent=[5., 6.],
            primary_genre=["K-Pop", None], secondary_genres=['[]', None]))
        enc = c.Encoder().fit(train, list(train))
        a = enc.transform(train)
        b = enc.transform(val)
        self.assertEqual(enc.state["x"]["median"], 2.)
        self.assertEqual(enc.groups["absent"], [])
        self.assertEqual(b[0, enc.groups["x"][0]], 0.)
        self.assertGreater(enc.unsupported(val)["primary_genre"], 0)
        self.assertGreater(enc.unsupported(val)["secondary_genres"], 0)
        val.x = [-9999., np.nan]
        enc.transform(val)
        np.testing.assert_array_equal(a, enc.transform(train))
        loaded = c.Encoder(json.loads(json.dumps(enc.state)))
        np.testing.assert_array_equal(a, loaded.transform(train))

    def test_song_group_temporal_boundaries_and_common_target_masks(self):
        raw = fixture()
        raw.loc[raw.song_id == "2005-1", "last_chart_date"] = "2011-01-01"
        raw.loc[raw.song_id == "2012-1", "y"] = np.nan
        tr, va = c.partition(raw, "2010-01-01", "2018-01-01")
        self.assertFalse(tr[raw.song_id == "2005-1"].any())
        self.assertFalse(va[raw.song_id == "2005-1"].any())
        fold = c.prepare(raw, task(), "2010-01-01", "2018-01-01")
        self.assertNotIn("2012-1", set(fold.validation.song_id))
        self.assertFalse(set(fold.train.song_id) & set(fold.validation.song_id))
        for group in (fold.train, fold.validation):
            w = c.weights(group)
            sums = pd.Series(w, index=group.song_id).groupby(level=0).sum()
            np.testing.assert_allclose(sums, sums.iloc[0])

    def test_final_test_values_do_not_change_training_or_validation(self):
        raw = fixture()
        before = c.prepare(raw, task(), *s.FOLDS[2])
        raw.loc[raw.first_chart_date.ge("2018-01-01"), ["x", "y", "z"]] = 1e20
        after = c.prepare(raw, task(), *s.FOLDS[2])
        np.testing.assert_array_equal(before.X, after.X)
        np.testing.assert_array_equal(before.V, after.V)
        np.testing.assert_array_equal(before.y, after.y)
        np.testing.assert_array_equal(before.z, after.z)

    def test_constant_outcomes_have_undefined_r2(self):
        metrics = c.metrics(np.ones(3), np.ones(3), np.ones(3), 1., 1.)
        self.assertIsNone(metrics["r2"])
        self.assertIsNone(metrics["skill"])

    def test_resume_exact_coverage_and_changed_inputs_rejected(self):
        # Exhaustive small universe, with a deliberate transaction interruption;
        # this verifies traversal independently of the larger bounded pilot.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/"fixture.csv"
            fixture().drop_duplicates("song_id").to_csv(source, index=False)
            t = task()
            candidates = list(enumerate(s.combinations(t)))
            with patch.dict(s.FILES, songs=str(source)):
                first = run.run_task(t, root/"resumed", s.configuration(), batch_size=3, stop_batches=2)
                self.assertEqual(first["interrupted_after_batches"], 2)
                resumed = run.run_task(t, root/"resumed", s.configuration(), batch_size=3)
                run.run_task(t, root/"clean", s.configuration(), batch_size=7)
                paths = [run.task_path(root/folder, t) for folder in ("resumed", "clean")]
                records = []
                for path in paths:
                    with sqlite3.connect(path/"results.sqlite") as db:
                        records.append(db.execute("SELECT * FROM scores ORDER BY id,fold").fetchall())
                # Batch shapes can change last-bit BLAS summation, but indices,
                # counts, ranks and numeric results must agree tightly.
                np.testing.assert_allclose(records[0], records[1], atol=1e-12, rtol=1e-12)
                self.assertEqual(len(records[0]), len(candidates)*3)
                self.assertEqual(resumed["completed_combinations"], len(candidates))
                a, b = [json.loads((p/"selection.json").read_text())["winner"] for p in paths]
                self.assertEqual(a["predictors"], b["predictors"])
                no_op = run.run_task(t, root/"resumed", s.configuration())
                self.assertTrue(no_op["already_complete"])
                old_spec = (paths[0]/"specification.json").read_bytes()
                with self.assertRaisesRegex(ValueError, "Resume identity mismatch"):
                    run.run_task(t, root/"resumed", dict(s.configuration(), changed=True))
                self.assertEqual((paths[0]/"specification.json").read_bytes(), old_spec)
                source.write_text(source.read_text()+"\n")
                with self.assertRaisesRegex(ValueError, "Resume identity mismatch"):
                    run.run_task(t, root/"resumed", s.configuration())

    def test_partial_transaction_rollback_does_not_create_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            with Store(Path(tmp)/"checkpoint.sqlite", {"version": 1}, [(0, ("x",))], ["x"]) as store:
                with self.assertRaises(RuntimeError):
                    with store.db:
                        store.db.execute("INSERT INTO scores VALUES (0,0,1,0,0,1,2,0)")
                        raise RuntimeError("simulate interruption")
                self.assertEqual(store.completed(0), set())
                self.assertFalse(store.complete())

    def test_finalization_freezes_winner_replays_model_and_checks_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/"fixture.csv"
            raw = fixture().drop_duplicates("song_id").reset_index(drop=True)
            raw.to_csv(source, index=False)
            t = task()
            with patch.dict(s.FILES, songs=str(source)), patch.object(s, "specs", return_value=[t]):
                with self.assertRaisesRegex(ValueError, "Every target search"):
                    run.finalize(root/"incomplete")
                run.run_task(t, root/"complete", s.configuration())
                result = run.finalize(root/"complete")
                self.assertEqual(result, run.finalize(root/"complete"))
                dest = run.task_path(root/"complete", t)
                model = json.loads((dest/"selected_model.json").read_text())
                prediction = pd.read_csv(dest/"test_predictions.csv.gz")
                frame = s.original.convert(raw.loc[prediction.source_row])
                replay = c.Encoder(model["encoder"]).transform(frame) @ np.array(model["coefficients"]) + model["target_center"]
                np.testing.assert_allclose(replay, prediction.predicted, atol=1e-10)
                self.assertTrue(model["selected_before_test"])
                self.assertEqual(result[0]["n_test"], 12)
                (dest/"selected_model.json").write_text("corrupt")
                with self.assertRaisesRegex(ValueError, "integrity"):
                    run.finalize(root/"complete")

    def test_non_regression_tasks_and_four_predictors_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "numerical OLS"):
                run.run_task(dict(task(), model_family="ordinal_rank"), tmp, s.configuration())
            with self.assertRaisesRegex(ValueError, "Invalid candidate"):
                run.run_task(task(), tmp, s.configuration(), [(0, ("absent", "duplicate", "x", "z"))])

    def test_cli_launch_gate_does_not_start_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(s.ROOT/"src/regression_search.py"),
                "campaign", "--folder", str(Path(tmp)/"campaign")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("gated", result.stderr)
            self.assertFalse((Path(tmp)/"campaign").exists())

    def test_pilot_is_deterministic_stratified_bounded_and_excludes_final_test(self):
        task_spec = next(t for t in s.specs() if t["task_id"] == "songs:detox_toxicity")
        a, b = s.sample(task_spec), s.sample(task_spec)
        self.assertEqual(a, b)
        self.assertLessEqual(len(a), 131)
        self.assertEqual({len(c) for _, c in a}, {1, 2, 3})
        self.assertEqual({s.stratum(c) for _, c in a}, {"numeric", "primary", "secondary", "both"})
        self.assertEqual(s.configuration(True)["test_end"], "2018-01-01")

    def test_cluster_bootstrap_is_deterministic_and_finite(self):
        fold = c.prepare(fixture(), task(), *s.FOLDS[2])
        pred = fold.V @ fold.fit_batch([("x",)])[0][:, 0] + fold.mean
        a = run.bootstrap(fold, pred, repeats=30)
        self.assertEqual(a, run.bootstrap(fold, pred, repeats=30))
        self.assertTrue(all(np.isfinite(bounds).all() for bounds in a.values()))
        limited = run.bootstrap(fold, pred, repeats=30, calendar_blocks=True)
        self.assertEqual(limited["blocks"], 2)
        self.assertIsNone(limited["intervals"])
        # Use several actual calendar blocks, preserving repeated-song grouping.
        raw = fixture()
        extra = raw[raw.first_chart_date.eq("2012-01-01")].copy()
        extra.song_id = extra.song_id+"extra"
        extra.first_chart_date = "2014-01-01"
        extra.last_chart_date = "2014-09-01"
        fold = c.prepare(pd.concat([raw, extra], ignore_index=True), task(), *s.FOLDS[2])
        pred = fold.V @ fold.fit_batch([("x",)])[0][:, 0] + fold.mean
        block = run.bootstrap(fold, pred, repeats=30, calendar_blocks=True)
        self.assertEqual(block["blocks"], 3)
        self.assertEqual(block, run.bootstrap(fold, pred, repeats=30, calendar_blocks=True))
        self.assertTrue(all(np.isfinite(bounds).all() for bounds in block["intervals"].values()))


if __name__ == "__main__":
    unittest.main()
