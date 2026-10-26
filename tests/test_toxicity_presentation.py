"""Verify saved-model equations, complete held-out plots and presentation provenance."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "analysis/regression_search/presentation/render.py"
module_spec = importlib.util.spec_from_file_location("toxicity_presentation", MODULE)
presentation = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(presentation)


class EquationTests(unittest.TestCase):
    def test_unscaling_preserves_intercept_reference_genre_missingness_and_column_order(self):
        numeric = dict(keep=[0], train_absent_columns=[1], constant_values=[0.0],
                       mean=[.4], std=[.2], median=.3)
        genre = dict(keep=list(range(15)), train_absent_columns=[15], constant_values=[0.0],
                     mean=[.02] * 15, std=[.1] * 15, median=0.0)
        # Deliberately use predictor order different from the serialized encoder keys.
        model = dict(predictors=["emotion_annoyance", "emotion_anger", "primary_genre"],
                     encoder={"primary_genre": genre, "emotion_anger": numeric,
                              "emotion_annoyance": numeric},
                     coefficients=[.25, .6, -.2] + [.1] * 15, target_center=.5)
        equation = presentation.original_equation(model)
        self.assertAlmostEqual(equation["intercept"], -.35)
        self.assertAlmostEqual(equation["numeric"]["emotion_annoyance"], 3)
        self.assertAlmostEqual(equation["numeric"]["emotion_anger"], -1)
        self.assertEqual(equation["reference_genre"], "Pop")
        self.assertEqual(equation["genre_offsets"]["Pop"], 0)
        self.assertTrue(all(v == 1 for k, v in equation["genre_offsets"].items() if k != "Pop"))
        frame = pd.DataFrame(dict(emotion_annoyance=[.2, np.nan, .2, .2],
                                  emotion_anger=[.1, .1, .1, .1],
                                  primary_genre=["Pop", "Rock", None, "Afrobeats / African Pop"]))
        result = presentation.equation_predictions(equation, frame)
        np.testing.assert_allclose(result, [.15, 1.45, .15, 1.15], atol=1e-14, rtol=0)
        encoder = presentation.core.Encoder({p: model["encoder"][p] for p in model["predictors"]})
        saved = encoder.transform(frame) @ model["coefficients"] + model["target_center"]
        np.testing.assert_allclose(saved, result, atol=1e-14, rtol=0)
        frame.loc[0, "primary_genre"] = "Invented"
        with self.assertRaisesRegex(ValueError, "Unknown primary genre"):
            presentation.equation_predictions(equation, frame)
        changed = copy.deepcopy(model)
        changed["encoder"]["primary_genre"]["keep"] = list(range(14))
        with self.assertRaisesRegex(ValueError, "Unsupported genre encoding"):
            presentation.original_equation(changed)

    def test_metric_check_detects_prediction_corruption_and_clipping(self):
        frame = pd.DataFrame(dict(actual=[0., .5, 1.], predicted=[.1, .4, 1.2], weight=[1., 1., 1.]))
        expected = dict(r2=.88, mae=2 / 15, rmse=np.sqrt(.02))
        presentation.check_metrics(presentation.prediction_metrics(frame), expected)
        frame.predicted = frame.predicted.clip(0, 1)
        with self.assertRaisesRegex(ValueError, "Published metric not reproduced"):
            presentation.check_metrics(presentation.prediction_metrics(frame), expected)


class PublishedPresentationTests(unittest.TestCase):
    def test_catalog_registration_preserves_all_original_entries_and_historical_provenance(self):
        guard_name = "analysis/historical_decomposition/preservation_manifest.json"
        guard = presentation.read_json(ROOT / guard_name)
        catalog_name = "analysis/figure_manifest.json"
        baseline_bytes = subprocess.check_output(
            ["git", "show", guard["baseline_commit"] + ":" + catalog_name], cwd=ROOT)
        current = presentation.read_json(ROOT / catalog_name)
        image_name = str((presentation.OUT / (presentation.STEM + ".png")).relative_to(ROOT))
        presentation.check_catalog_addition(current, json.loads(baseline_bytes), image_name)
        self.assertEqual(guard["sha256"][catalog_name], presentation.sha(ROOT / catalog_name))
        revision = guard["approved_verification_revisions"][catalog_name]
        self.assertEqual(revision["original_sha256"], presentation.hashlib.sha256(baseline_bytes).hexdigest())
        self.assertEqual(revision["added_figures"], {image_name: current["figure_sha256"][image_name]})
        artifact = presentation.read_json(ROOT / "analysis/historical_decomposition/artifact_manifest.json")
        self.assertEqual(artifact["sha256"][guard_name], presentation.sha(ROOT / guard_name))
        existing_image = next(iter(json.loads(baseline_bytes)["figure_sha256"]))
        current["figure_sha256"][existing_image] = "corrupt"
        with self.assertRaisesRegex(ValueError, "Existing image catalog"):
            presentation.check_catalog_addition(current, json.loads(baseline_bytes), image_name)

    def test_image_dimensions_hashes_equations_and_complete_genre_catalog(self):
        record = presentation.read_json(presentation.OUT / "verification.json")
        png = presentation.OUT / (presentation.STEM + ".png")
        self.assertEqual(record["image_sha256"], presentation.sha(png))
        self.assertEqual(record["renderer_sha256"], presentation.sha(MODULE))
        self.assertFalse(record["fit_or_selection_performed"])
        self.assertFalse(record["artifact_recovery_needed"])
        self.assertTrue(record["all_evaluated_songs_plotted"])
        with Image.open(png) as im:
            self.assertEqual(im.size, (4800, 2700))
            self.assertEqual(im.width / im.height, 16 / 9)
            im.verify()
        catalog = presentation.read_json(ROOT / "analysis/figure_manifest.json")
        self.assertEqual(catalog["figure_sha256"][str(png.relative_to(ROOT))], record["image_sha256"])
        a, b = record["models"]
        self.assertEqual(set(a["equation"]["genre_offsets"]), set(presentation.spec.original.GENRE_TAXONOMY))
        for result in (a, b):
            self.assertEqual(result["equation"], presentation.original_equation(result["saved_parameterization"]))
            self.assertEqual(result["n_songs"], 2729)
            self.assertEqual(result["n_refit"], 18106)
            self.assertLessEqual(result["equation_max_absolute_error"], presentation.TOLERANCE)


class LocalSavedArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        record = presentation.read_json(presentation.OUT / "verification.json")
        if any(not (ROOT / r["model_path"]).exists() for r in record["models"]):
            raise unittest.SkipTest("Retained local fitted models/predictions are required for replay")
        with patch.object(presentation.core.Encoder, "fit", side_effect=AssertionError("No refitting")), \
             patch.object(presentation.core.Fold, "fit_batch", side_effect=AssertionError("No refitting")):
            cls.results, cls.hashes = presentation.load_verified()

    def test_every_saved_prediction_replays_and_matches_both_published_evaluations(self):
        record = presentation.read_json(presentation.OUT / "verification.json")
        self.assertEqual(record["source_sha256"], self.hashes)
        for actual, saved in zip(self.results, record["models"]):
            presentation.check_metrics(actual["metrics"], saved["metrics"])
            self.assertEqual(actual["equation"], saved["equation"])
            self.assertEqual(actual["replay_max_absolute_error"], 0)
            self.assertTrue(all(n == 0 for n in actual["missing_inputs"].values()))
        note = presentation.OUT / (presentation.STEM + ".md")
        self.assertEqual(note.read_text(), presentation.markdown(self.results))

    def test_scatterplots_contain_all_original_unclipped_predictions_and_shared_axes(self):
        fig = presentation.make_figure(self.results)
        try:
            presentation.validate_figure(fig, self.results)
            for axis, result in zip(fig.axes, self.results):
                points = axis.collections[0].get_offsets()
                self.assertEqual(len(points), 2729)
                self.assertGreater(points[:, 1].max(), 1)
                np.testing.assert_array_equal(points[:, 1], result["predictions"].predicted)
            fig.axes[0].set_ylim(0, 1)
            with self.assertRaisesRegex(ValueError, "clipped"):
                presentation.validate_figure(fig, self.results)
        finally:
            presentation.plt.close(fig)


if __name__ == "__main__":
    unittest.main()
