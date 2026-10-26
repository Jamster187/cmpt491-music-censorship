"""Replay two frozen toxicity regressions and render their classroom comparison.

No fitting, selection, acquisition, or modification of existing numerical results.
Only image-catalog/provenance metadata is updated to register the new PNG hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
import regression_core as core
import regression_spec as spec

OUT = Path(__file__).resolve().parent
STEM = "toxicity_regression_models_held_out_comparison"
TARGET = "detox_toxicity"
TOLERANCE = 1e-12
DEFINITIONS = (
    dict(label="A", name="Emotion + genre", kind="Cross-classifier prediction + genre",
         predictors=["emotion_anger", "emotion_annoyance", "primary_genre"],
         manifest="analysis/regression_search/meaningful/model_manifest.json", view="cross_domain",
         leaderboard="analysis/regression_search/meaningful/cross_domain_leaderboard.csv",
         prediction_file="predictions.csv.gz", metrics_file="metrics.json", split_file="split.csv.gz"),
    dict(label="B", name="Detoxify components", kind="Same-classifier redundancy",
         predictors=["detox_insult", "detox_obscene", "detox_severe_toxicity"],
         manifest="analysis/regression_search/campaign/selected_models.json", view=None,
         leaderboard="analysis/regression_search/campaign/target_leaderboard.csv",
         prediction_file="test_predictions.csv.gz", metrics_file="test_metrics.json",
         split_file="refit_split.csv.gz"),
)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def checked_hash(path, expected):
    actual = sha(path)
    if actual != expected:
        raise ValueError("Saved artifact changed: " + str(path))
    return actual


def check_catalog_addition(current, baseline, image_name):
    """The authorized addition must not revise any existing catalog information."""
    restored = json.loads(json.dumps(current))
    restored["figure_sha256"].pop(image_name, None)
    if restored != baseline:
        raise ValueError("Existing image catalog entries or metadata changed")


def catalog_registration(image_name, image_hash):
    """Register an additive figure while retaining the historical catalog baseline.

    The historical verifier already supports versioned verification-metadata
    revisions. Use that mechanism rather than alter its code or any result hashes.
    """
    catalog_name = "analysis/figure_manifest.json"
    guard_name = "analysis/historical_decomposition/preservation_manifest.json"
    artifact_name = "analysis/historical_decomposition/artifact_manifest.json"
    catalog, guard, artifact = (read_json(ROOT / name) for name in (catalog_name, guard_name, artifact_name))
    checked_hash(ROOT / guard_name, artifact["sha256"][guard_name])
    original_bytes = subprocess.check_output(
        ["git", "show", guard["baseline_commit"] + ":" + catalog_name], cwd=ROOT)
    original_hash = hashlib.sha256(original_bytes).hexdigest()
    existing_revision = guard.get("approved_verification_revisions", {}).get(catalog_name)
    expected_original = existing_revision["original_sha256"] if existing_revision else guard["sha256"][catalog_name]
    if original_hash != expected_original:
        raise ValueError("Historical image catalog baseline differs")
    check_catalog_addition(catalog, json.loads(original_bytes), image_name)
    catalog["figure_sha256"][image_name] = image_hash
    catalog_bytes = (json.dumps(catalog, indent=2, sort_keys=True) + "\n").encode()
    current_hash = hashlib.sha256(catalog_bytes).hexdigest()
    guard["sha256"][catalog_name] = current_hash
    guard.setdefault("approved_verification_revisions", {})[catalog_name] = dict(
        original_sha256=original_hash, current_sha256=current_hash,
        reason="Register the requested two-model toxicity presentation PNG only; every pre-existing "
               "image, numerical, code and audit hash is unchanged. Historical catalog bytes remain "
               "at baseline_commit; the presentation renderer verifies the addition is strictly additive.",
        added_figures={image_name: image_hash})
    guard_bytes = (json.dumps(guard, indent=2, sort_keys=True) + "\n").encode()
    artifact["sha256"][guard_name] = hashlib.sha256(guard_bytes).hexdigest()
    return {catalog_name: catalog_bytes, guard_name: guard_bytes,
            artifact_name: (json.dumps(artifact, indent=2, sort_keys=True) + "\n").encode()}


def original_equation(model):
    """Undo the saved standardization algebraically; never estimate coefficients."""
    beta = np.asarray(model["coefficients"], dtype=float)
    intercept = float(model["target_center"] + beta[0])
    numeric, genres, medians = {}, {}, {}
    offset = 1
    for predictor in model["predictors"]:
        state = model["encoder"][predictor]
        keep = state["keep"]
        expected_keep, expected_absent = (list(range(15)), [15]) if predictor == "primary_genre" else ([0], [1])
        if keep != expected_keep or state["train_absent_columns"] != expected_absent:
            kind = "genre" if predictor == "primary_genre" else "numeric"
            raise ValueError(f"Unsupported {kind} encoding; inspect the saved model")
        if len(state["std"]) != len(keep) or len(state["mean"]) != len(keep):
            raise ValueError("Encoder dimension mismatch")
        if not np.isfinite(state["std"]).all() or not (np.asarray(state["std"]) > 0).all():
            raise ValueError("Invalid saved standardization")
        coef = beta[offset:offset + len(keep)] / np.asarray(state["std"])
        intercept -= float(coef @ np.asarray(state["mean"]))
        offset += len(keep)
        if predictor == "primary_genre":
            # The exact frozen taxonomy, with Pop omitted and missing constant/dropped.
            genres = {spec.original.GENRE_TAXONOMY[0]: 0.0}
            genres.update(zip(spec.original.GENRE_TAXONOMY[1:], map(float, coef)))
        else:
            numeric[predictor] = float(coef[0])
            medians[predictor] = state["median"]
        if state["constant_values"] != [0.0]:
            raise ValueError("Unexpected dropped-column values")
    if offset != len(beta):
        raise ValueError("Coefficient/encoding width mismatch")
    return dict(intercept=intercept, numeric=numeric, genre_offsets=genres,
                reference_genre=spec.original.GENRE_TAXONOMY[0] if genres else None,
                numeric_missing_medians=medians, missing_genre_offset=0.0 if genres else None)


def equation_predictions(equation, frame):
    result = np.full(len(frame), equation["intercept"])
    for name, coefficient in equation["numeric"].items():
        values = frame[name].fillna(equation["numeric_missing_medians"][name]).to_numpy(float)
        result += coefficient * values
    if equation["genre_offsets"]:
        unknown = set(frame.primary_genre.dropna()) - set(equation["genre_offsets"])
        if unknown:
            raise ValueError("Unknown primary genre: " + repr(unknown))
        result += frame.primary_genre.map(equation["genre_offsets"]).fillna(0).to_numpy(float)
    return result


def prediction_metrics(predictions):
    """Independent metric calculation directly from every saved held-out row."""
    y, p, w = (predictions[name].to_numpy(float) for name in ("actual", "predicted", "weight"))
    if not np.isfinite(np.column_stack([y, p, w])).all() or not (w > 0).all():
        raise ValueError("Non-finite predictions/outcomes or invalid weights")
    mse = np.sum(w * (y - p) ** 2) / np.sum(w)
    average = np.sum(w * y) / np.sum(w)
    variance = np.sum(w * (y - average) ** 2) / np.sum(w)
    return dict(r2=float(1 - mse / variance),
                mae=float(np.sum(w * abs(y - p)) / np.sum(w)), rmse=float(np.sqrt(mse)))


def check_metrics(computed, expected):
    for name in ("r2", "mae", "rmse"):
        if not np.isclose(computed[name], float(expected[name]), atol=TOLERANCE, rtol=0):
            raise ValueError("Published metric not reproduced: " + name)


def load_verified():
    source = ROOT / spec.FILES["songs"]
    source_hash = sha(source)
    # Use the original reader, including its original float parsing and row order.
    raw = spec.original.read_table(spec.FILES["songs"])
    if raw.song_id.duplicated().any():
        raise ValueError("Duplicate exact song identity")
    train_mask, test_mask = core.partition(raw, "2018-01-01", None)
    observed = raw[TARGET].notna()
    expected_train = raw.index[train_mask & observed].to_numpy()
    expected_test = raw.index[test_mask & observed].to_numpy()
    results, source_hashes = [], {str(source.relative_to(ROOT)): source_hash}
    for definition in DEFINITIONS:
        manifest_path = ROOT / definition["manifest"]
        matches = [m for m in read_json(manifest_path)["models"]
                   if m["task_id"] == "songs:" + TARGET and
                   (definition["view"] is None or m["view"] == definition["view"])]
        if len(matches) != 1:
            raise ValueError("Ambiguous saved model")
        entry = matches[0]
        if entry["predictors"] != definition["predictors"]:
            raise ValueError("Requested model differs from published selection")
        model_path = ROOT / entry["model_path"]
        artifacts = entry.get("artifacts", entry.get("final_artifacts_sha256"))
        for name, digest in artifacts.items():
            path = model_path.parent / name
            source_hashes[str(path.relative_to(ROOT))] = checked_hash(path, digest)
        source_hashes[definition["manifest"]] = sha(manifest_path)
        model = read_json(model_path)
        if model["task"]["target"] != TARGET or model["predictors"] != definition["predictors"]:
            raise ValueError("Wrong saved model specification")
        data_hash = model.get("data_sha256", model.get("identity", {}).get("data_sha256"))
        if data_hash != source_hash:
            raise ValueError("Public source differs from fitted-model source")
        for name, digest in model["provenance"]["code_sha256"].items():
            source_hashes[name] = checked_hash(ROOT / name, digest)
        predictions = pd.read_csv(model_path.parent / definition["prediction_file"], float_precision="round_trip")
        split = pd.read_csv(model_path.parent / definition["split_file"])
        saved_metrics = read_json(model_path.parent / definition["metrics_file"])
        if predictions.source_row.duplicated().any() or predictions.song_id.duplicated().any():
            raise ValueError("Duplicate evaluated song/row")
        np.testing.assert_array_equal(predictions.source_row, expected_test)
        np.testing.assert_array_equal(split.loc[split.partition.eq("test"), "source_row"], expected_test)
        np.testing.assert_array_equal(split.loc[split.partition.eq("refit"), "source_row"], expected_train)
        if len(split) != len(expected_test) + len(expected_train):
            raise ValueError("Unexpected split rows")
        np.testing.assert_array_equal(raw.loc[split.source_row, "song_id"], split.song_id)
        held_out = raw.loc[predictions.source_row]
        np.testing.assert_array_equal(held_out.song_id, predictions.song_id)
        np.testing.assert_allclose(held_out[TARGET], predictions.actual, atol=TOLERANCE, rtol=0)
        np.testing.assert_array_equal(predictions.weight, np.ones(len(predictions)))
        if any(int(saved_metrics[k]) != len(predictions) for k in ("n_test", "test_songs")):
            raise ValueError("Published test sample size differs")
        if int(saved_metrics["n_refit"]) != len(expected_train):
            raise ValueError("Published refit sample size differs")
        # Only transformation with the saved encoder. No Encoder.fit or OLS fit calls.
        encoder = core.Encoder({p: model["encoder"][p] for p in model["predictors"]})
        replay = encoder.transform(held_out) @ np.asarray(model["coefficients"]) + model["target_center"]
        equation = original_equation(model)
        unscaled = equation_predictions(equation, held_out)
        np.testing.assert_allclose(replay, predictions.predicted, atol=TOLERANCE, rtol=0)
        np.testing.assert_allclose(unscaled, predictions.predicted, atol=TOLERANCE, rtol=0)
        computed = prediction_metrics(predictions)
        check_metrics(computed, saved_metrics)
        leaderboard_path = ROOT / definition["leaderboard"]
        leaderboard = pd.read_csv(leaderboard_path, float_precision="round_trip")
        row = leaderboard.loc[leaderboard.task_id.eq("songs:" + TARGET)].squeeze()
        if json.loads(row.predictors) != definition["predictors"]:
            raise ValueError("Leaderboard predictor mismatch")
        prefix = "test_" if definition["label"] == "B" else ""
        check_metrics(computed, {k: row[prefix + k] for k in computed})
        if int(row.test_songs) != len(predictions) or int(row.n_test) != len(predictions):
            raise ValueError("Leaderboard sample size mismatch")
        source_hashes[definition["leaderboard"]] = sha(leaderboard_path)
        results.append(dict(definition=definition, model=model, entry=entry, equation=equation,
                            predictions=predictions, metrics=computed,
                            n_songs=int(predictions.song_id.nunique()), n_refit=len(expected_train),
                            chart_debut_min=str(held_out.first_chart_date.min()),
                            chart_debut_max=str(held_out.first_chart_date.max()),
                            replay_max_absolute_error=float(np.max(abs(replay - predictions.predicted))),
                            equation_max_absolute_error=float(np.max(abs(unscaled - predictions.predicted))),
                            missing_inputs=held_out[definition["predictors"]].isna().sum().to_dict()))
    np.testing.assert_array_equal(results[0]["predictions"].song_id, results[1]["predictions"].song_id)
    np.testing.assert_array_equal(results[0]["predictions"].actual, results[1]["predictions"].actual)
    return results, source_hashes


INK, MUTED, PAPER = "#172B42", "#455B70", "#F4F7FA"
COLORS = ("#087E8B", "#B65029")


def make_figure(results):
    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                         "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})
    fig = plt.figure(figsize=(24, 13.5), dpi=200, facecolor=PAPER)
    fig.text(.04, .965, "Predicting Detoxify toxicity scores", fontsize=33, weight="bold", va="top")
    count = results[0]["n_songs"]
    fig.text(.04, .918,
             f"Target: detox_toxicity  |  Same {count:,} held-out songs  |  Chart debuts 2018–2026",
             fontsize=21, color=MUTED, va="top")
    for index, result in enumerate(results):
        left = .04 + index * .48
        color = COLORS[index]
        definition, equation = result["definition"], result["equation"]
        fig.add_artist(FancyBboxPatch((left - .012, .238), .458, .642,
                                     boxstyle="round,pad=0.006,rounding_size=0.008",
                                     facecolor="white", edgecolor="#D8E2EB", linewidth=1,
                                     transform=fig.transFigure, zorder=-1))
        fig.text(left, .864, f"MODEL {definition['label']}  ·  {definition['name']}",
                 fontsize=27, color=color, weight="bold", va="top")
        fig.text(left, .826, definition["kind"], fontsize=20, color=MUTED, va="top")
        items = list(equation["numeric"].items())
        lines = [f"ŷ = {equation['intercept']:.6f} + {items[0][1]:.6f} × {items[0][0]}"]
        for name, coefficient in items[1:]:
            sign = "+" if coefficient >= 0 else "−"
            lines.append(f"    {sign} {abs(coefficient):.6f} × {name}")
        if equation["genre_offsets"]:
            lines.append("    + G(primary_genre)  [offsets below]")
        for j, line in enumerate(lines):
            fig.text(left, .785 - j * .032, line, fontsize=21, va="top")
        metric_items = [("Held-out R²", f"{result['metrics']['r2']:.4f}"),
                        ("MAE", f"{result['metrics']['mae']:.4f}"),
                        ("RMSE", f"{result['metrics']['rmse']:.4f}"),
                        ("Evaluated songs", f"{result['n_songs']:,}")]
        for j, (label, value) in enumerate(metric_items):
            x = left + j * .111
            fig.text(x, .671, label, fontsize=17, color=MUTED, va="top")
            fig.text(x, .644, value, fontsize=28, weight="bold", color=color, va="top")
        ax = fig.add_axes([left + .035, .332, .377, .265])
        predictions = result["predictions"]
        ax.scatter(predictions.actual, predictions.predicted, s=9, alpha=.40,
                   color=color, edgecolors="none", rasterized=True)
        ax.plot([0, 1], [0, 1], color=INK, linestyle="--", linewidth=1.7,
                label="y = x  (perfect prediction)")
        # Common axes contain every saved prediction, including OLS values above 1.
        maximum = max(float(r["predictions"].predicted.max()) for r in results)
        minimum = min(float(r["predictions"].predicted.min()) for r in results)
        ax.set(xlim=(-.025, 1.025), ylim=(min(0., minimum) - .03, max(1., maximum) + .06),
               xlabel="Actual Detoxify toxicity score", ylabel="Predicted score")
        ax.set_xticks(np.arange(0, 1.01, .2))
        ax.set_yticks(np.arange(0, 1.41, .2))
        ax.tick_params(labelsize=17, length=3)
        ax.xaxis.label.set_size(19)
        ax.yaxis.label.set_size(19)
        ax.grid(color="#E2E8EE", linewidth=.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#ADBCC9")
        ax.legend(loc="upper left", fontsize=16, frameon=False)
        ax.text(.98, .96, "All songs shown; no clipping", transform=ax.transAxes,
                ha="right", va="top", fontsize=15, color=MUTED)
        text = ("Emotion scores + genre explain about 55% of test-score variation.\n"
                "Substantial differences remain between predictions and scores." if index == 0 else
                "Other Detoxify outputs explain about 91% of test-score variation.\n"
                "This reflects shared classifier information, not independent validation.")
        fig.text(left, .278, text, fontsize=18, linespacing=1.45, va="top")
    fig.text(.04, .209,
             "MODEL A · Genre offset G: one-hot indicators; Pop is the reference. Add the offset for primary_genre.",
             fontsize=19, weight="bold", va="top")
    for i, (genre, coefficient) in enumerate(results[0]["equation"]["genre_offsets"].items()):
        col, row = divmod(i, 4)
        x, y = .04 + col * .24, .173 - row * .032
        fig.text(x, y, genre, fontsize=17, color=INK, va="top")
        fig.text(x + .209, y, "0 (ref.)" if genre == "Pop" else f"{coefficient:+.6f}",
                 fontsize=17, ha="right", color=COLORS[0], va="top", family="DejaVu Sans Mono")
    fig.text(.04, .027,
             "Exploratory, previously inspected held-out results · Classifier scores, not human-verified toxicity · Coefficients rounded; exact equations in companion note",
             fontsize=16, color=MUTED, va="top")
    return fig


def validate_figure(fig, results):
    """Check what is actually drawn, not just the data provided to the renderer."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for artist in fig.texts:
        bounds = artist.get_window_extent(renderer)
        if bounds.x0 < 0 or bounds.y0 < 0 or bounds.x1 > fig.bbox.width or bounds.y1 > fig.bbox.height:
            raise ValueError("Text outside canvas: " + artist.get_text())
    for ax, result in zip(fig.axes, results):
        expected = result["predictions"][["actual", "predicted"]].to_numpy()
        np.testing.assert_array_equal(ax.collections[0].get_offsets(), expected)
        for values, bounds in zip(expected.T, [ax.get_xlim(), ax.get_ylim()]):
            if values.min() < bounds[0] or values.max() > bounds[1]:
                raise ValueError("A plotted prediction is clipped")
        np.testing.assert_array_equal(ax.lines[0].get_xdata(), ax.lines[0].get_ydata())
    if fig.axes[0].get_xlim() != fig.axes[1].get_xlim() or fig.axes[0].get_ylim() != fig.axes[1].get_ylim():
        raise ValueError("Models must share axis limits")


def markdown(results):
    a, b = results
    lines = ["# Two saved toxicity regressions", "",
             f"![Comparison of two saved toxicity regressions]({STEM}.png)", "",
             "The 4800 × 2700 PNG compares predictions of the **Detoxify toxicity classifier score**, "
             "not human-verified toxicity. Each scatterplot contains all 2,729 evaluated songs, "
             "with identical axes and a y=x reference. OLS predictions are not clipped to [0, 1].", "",
             "These are **exploratory, previously inspected held-out results**. Model A is the "
             "previous post-hoc cross-domain selection; Model B is the original unrestricted "
             "validation winner. Their existing selections, fitted parameters, predictions and "
             "evaluations were reused unchanged. No model was fitted or reselected for this figure.", "",
             "| Model | Original predictors | Held-out R² | MAE | RMSE | Evaluated songs |",
             "|---|---|---:|---:|---:|---:|"]
    for r in results:
        m = r["metrics"]
        lines.append(f"| {r['definition']['label']} — {r['definition']['name']} | " +
                     ", ".join(f"`{p}`" for p in r["definition"]["predictors"]) +
                     f" | {m['r2']:.16g} | {m['mae']:.16g} | {m['rmse']:.16g} | {r['n_songs']:,} |")
    lines += ["", "## Exact equations in original score units", "",
              "Let `y_hat` be predicted `detox_toxicity`. The following coefficients retain "
              "17 significant digits. The figure rounds to six decimal places for readability; "
              "plots and metrics always use the original saved predictions.", ""]
    for r in results:
        e = r["equation"]
        lines += [f"**Model {r['definition']['label']}**", "", "```text", f"y_hat = {e['intercept']:.17g}"]
        for name, coefficient in e["numeric"].items():
            sign = "+" if coefficient >= 0 else "-"
            lines.append(f"        {sign} {abs(coefficient):.17g} * {name}")
        if e["genre_offsets"]:
            lines.append("        + G(primary_genre)")
        lines += ["```", ""]
    lines += ["Model A uses the original fixed 16-category taxonomy: **Pop is the reference** "
              "and its offset is zero. Fifteen one-hot indicators represent the other genres. "
              "Equivalently, `G = sum(coefficient[g] * I(primary_genre == g))` over non-Pop "
              "genres. It is one original predictor with 15 encoded columns, not a numeric genre rank.", "",
              "| primary_genre | Offset relative to Pop |", "|---|---:|"]
    lines.extend(f"| {name} | {coefficient:.17g} |" for name, coefficient in a["equation"]["genre_offsets"].items())
    lines += ["", "The saved models center the target and standardize each retained input column. "
              "The equations above undo this exactly algebraically: `b_j = beta_j / std_j`; "
              "`intercept = target_center + beta_0 - sum(b_j * mean_j)`. Original stored "
              "coefficients, centers and encoders are also preserved in `verification.json`.", "",
              "No evaluated predictor values are missing. The original encoder would replace "
              "a missing numerical score with its training median (recorded in `verification.json`). "
              "Missingness indicators were constant zero during training and dropped. The "
              "genre-missing indicator was also dropped; missing genre therefore contributes "
              "zero offset. All 15 non-reference genre indicators were retained.", "",
              "## Interpretation and evaluation", "",
              "**A: cross-classifier prediction plus genre.** Emotion anger/annoyance scores and "
              "genre account for about 55% of held-out Detoxify-score variance. Substantial "
              "errors remain. Genre offsets are conditional associations relative to Pop, "
              "holding the emotion scores fixed; they are not causal effects or judgments about genres.", "",
              "**B: same-classifier redundancy.** Three other Detoxify outputs account for about "
              "91% of held-out Detoxify-score variance. The stronger fit reflects overlapping "
              "outputs from the same classifier, not independent validation of toxicity. The "
              "negative severe-toxicity coefficient is a conditional multivariable coefficient; "
              "it does not imply that severe language reduces toxicity.", "",
              f"Both saved models used {a['n_refit']:,} observed-target songs whose first and last "
              "chart dates precede 2018-01-01 for the final fit. The same 2,729 observed-target "
              f"test songs debuted from {a['chart_debut_min']} to {a['chart_debut_max']}. "
              "Songs crossing the training boundary were purged under the original protocol. "
              "Each evaluated song has weight 1. Chart debuts are not release dates. This is "
              "retrospective cohort transfer, not an as-of forecast or a new COVID analysis.", "",
              "Verification checks source/model/prediction/split hashes, exact song IDs and row "
              "membership, original saved preprocessing, all predictions, and R²/MAE/RMSE "
              "against both saved metric files and published leaderboards (absolute tolerance "
              "1e-12). No artifacts were unavailable; no deterministic refit or recovery was needed.", "",
              "| Model | Maximum prediction replay error | Maximum original-unit equation error |",
              "|---|---:|---:|"]
    lines.extend(f"| {r['definition']['label']} | {r['replay_max_absolute_error']:.3g} | "
                 f"{r['equation_max_absolute_error']:.3g} |" for r in results)
    lines += ["", "## Saved sources and reproduction", ""]
    for r in results:
        lines += [f"- Model {r['definition']['label']}: `{r['entry']['model_path']}`; "
                  f"`{r['definition']['prediction_file']}` and `{r['definition']['metrics_file']}` "
                  "in the same directory.",
                  f"- Published evaluation {r['definition']['label']}: `{r['definition']['leaderboard']}`."]
    lines += ["", "The local model/prediction files remain ignored by Git; this figure requires "
              "those retained artifacts to reproduce. Public input is `data/public/songs.csv`. "
              "SHA-256 provenance, full precision equations, runtime versions and image hash "
              "are in [verification.json](verification.json).", "", "```bash",
              "python3 analysis/regression_search/presentation/render.py --verify-only",
              "python3 analysis/regression_search/presentation/render.py",
              "python3 -m unittest discover -s tests -p test_toxicity_presentation.py -v", "```", "",
              "Rendering writes this presentation directory and registers its PNG hash in "
              "`analysis/figure_manifest.json`. That catalog is also pinned by the historical "
              "publication, so its `preservation_manifest.json` records the original/current "
              "catalog hashes and the single added figure; its `artifact_manifest.json` pins "
              "the revised preservation metadata. The renderer verifies that every pre-existing "
              "catalog entry and hash is unchanged against the recorded Git baseline. Existing "
              "data, model artifacts, numerical analysis results and figures are unchanged.", ""]
    return "\n".join(lines)


def verification_record(results, source_hashes, image_path):
    models = []
    for r in results:
        models.append({**{k: r[k] for k in ["definition", "equation", "metrics", "n_songs", "n_refit",
                                          "chart_debut_min", "chart_debut_max", "replay_max_absolute_error",
                                          "equation_max_absolute_error", "missing_inputs"]},
                       "model_path": r["entry"]["model_path"], "candidate_id": r["entry"]["candidate_id"],
                       "saved_parameterization": {k: r["model"][k] for k in
                                                  ["coefficients", "target_center", "encoder", "predictors"]},
                       "predictions_above_one": int((r["predictions"].predicted > 1).sum()),
                       "predictions_below_zero": int((r["predictions"].predicted < 0).sum())})
    return dict(status="PASS", target=TARGET, evaluated_population_identical=True,
                all_evaluated_songs_plotted=True, fit_or_selection_performed=False,
                artifact_recovery_needed=False, evaluation="Exploratory, previously inspected held-out results",
                metric_absolute_tolerance=TOLERANCE, models=models, source_sha256=source_hashes,
                renderer_sha256=sha(__file__), image_sha256=sha(image_path), image_pixels=[4800, 2700],
                runtime=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                             matplotlib=matplotlib.__version__))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Read-only replay and published-image integrity check")
    args = parser.parse_args()
    results, hashes = load_verified()
    if args.verify_only:
        record = read_json(OUT / "verification.json")
        checked_hash(OUT / f"{STEM}.png", record["image_sha256"])
        if record["source_sha256"] != hashes:
            raise ValueError("Presentation source provenance changed")
        if record["renderer_sha256"] != sha(__file__):
            raise ValueError("Renderer differs from published figure")
        for saved, current in zip(record["models"], results):
            check_metrics(current["metrics"], saved["metrics"])
            if saved["equation"] != current["equation"]:
                raise ValueError("Published equation changed")
        if (OUT / f"{STEM}.md").read_text() != markdown(results):
            raise ValueError("Companion explanation differs from verified equations")
    else:
        with tempfile.TemporaryDirectory(prefix="toxicity-presentation-") as temporary:
            stage = Path(temporary)
            fig = make_figure(results)
            validate_figure(fig, results)
            png = stage / f"{STEM}.png"
            fig.savefig(png, dpi=200, facecolor=PAPER, metadata={"Description":
                        "Two frozen OLS models predicting Detoxify scores; exploratory held-out evaluation."})
            plt.close(fig)
            with Image.open(png) as im:
                if im.size != (4800, 2700):
                    raise ValueError("Unexpected output dimensions")
                im.verify()
            (stage / f"{STEM}.md").write_text(markdown(results))
            record = verification_record(results, hashes, png)
            (stage / "verification.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            # Guard all numerical/model sources again before publishing anything.
            for name, digest in hashes.items():
                checked_hash(ROOT / name, digest)
            registrations = catalog_registration(str((OUT / png.name).relative_to(ROOT)), sha(png))
            for path in sorted(stage.iterdir()):
                # Stage beside each destination so publication uses an atomic rename.
                target = OUT / path.name
                temp = target.with_suffix(target.suffix + ".tmp")
                temp.write_bytes(path.read_bytes())
                os.replace(temp, target)
            for name, content in registrations.items():
                target = ROOT / name
                temp = target.with_suffix(".json.tmp")
                temp.write_bytes(content)
                os.replace(temp, target)
    print(json.dumps({"status": "PASS", "refitted": False,
                      "models": [{"model": r["definition"]["label"], "n": r["n_songs"],
                                  **r["metrics"]} for r in results]}, indent=2))


if __name__ == "__main__":
    main()
