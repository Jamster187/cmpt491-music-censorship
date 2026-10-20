"""Hard-bounded actual-data rehearsal, throughput extrapolation and professor demo."""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
import platform
import resource
import sqlite3
import time

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_info, threadpool_limits

import regression_core as core
import regression_search as run
import regression_spec as spec
from regression_store import Store, write_json, clean

MAX_UNIQUE_COMBINATIONS = 9 * 131


def peak_bytes():
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if platform.system() == "Darwin" else peak * 1024)


def estimate(summaries, folder):
    counts = pd.read_csv(run.PUBLIC/"specification/search_counts.csv").set_index("task_id")
    support = pd.read_csv(run.PUBLIC/"specification/split_support.csv").set_index(["task_id", "fold"])
    measured = {s["task_id"]: s for s in summaries}
    details = []
    regression_tasks = [t for t in spec.specs() if t["model_family"] == "regression"]
    total_seconds = 0.
    for task in regression_tasks:
        name = task["target"]
        if task["table"] != "songs":
            proxy = task["task_id"]
        elif name in spec.original.SCORES:
            proxy = "songs:" + ("ll_violence" if name.startswith("ll_") else "emotion_joy" if name.startswith("emotion_")
                               else "sentiment_positive" if name.startswith("sentiment_") else "detox_toxicity")
        elif name in spec.original.MB_FIELDS:
            proxy = "songs:mb_release_year" if name == "mb_release_year" else "songs:mb_duration_median_seconds"
        else:
            proxy = "songs:chart_weeks"
        source = measured[proxy]
        strata = Counter((len(c), spec.stratum(c)) for c in spec.combinations(task))
        target_seconds = 0.
        for row in source["strata"]:
            number = strata[(row["k"], row["stratum"])]
            scale = support.loc[(task["task_id"], row["fold"]), "n_validation"]/row["n_validation"]
            nonmetric_seconds = row["loop_seconds_including_checkpoint"]-row["metrics_seconds"]
            seconds = number/row["fits"]*(nonmetric_seconds + row["metrics_seconds"]*scale)
            target_seconds += seconds
            details.append(dict(task_id=task["task_id"], proxy=proxy, fold=row["fold"],
                k=row["k"], stratum=row["stratum"], combinations=number,
                metric_rows_ratio=scale, estimated_seconds=seconds))
        # Candidate catalog insertion and ranking grow with the candidate count.
        # Scale their measured cost conservatively; preprocessing/QR are once per
        # target/fold. Checkpoint writes are already inside every stratum timing.
        scaled_cost = source["initialization_seconds"]+source["ranking_seconds"]
        target_seconds += scaled_cost*int(counts.loc[task["task_id"], "total"])/source["completed_combinations"]
        measured_loop = sum(r["loop_seconds_including_checkpoint"] for r in source["strata"])
        target_seconds += max(0., source["elapsed_seconds"]-measured_loop-scaled_cost)
        total_seconds += target_seconds
    actual_combos = sum(s["completed_combinations"] for s in summaries)
    db_bytes = sum((run.task_path(folder, t)/"results.sqlite").stat().st_size for t in regression_tasks
                   if (run.task_path(folder, t)/"results.sqlite").exists())
    total_combos = int(counts.loc[[t["task_id"] for t in regression_tasks], "total"].sum())
    # SQLite pilot pages overestimate per-row overhead at campaign scale;
    # preserve that conservative observation instead of assuming compression.
    result_bytes = db_bytes/actual_combos*total_combos
    other_bytes = sum(p.stat().st_size for p in Path(folder).rglob("*") if p.is_file() and p.suffix != ".sqlite")
    # Split membership has target-dependent repetition but does not grow with
    # candidate count. Include it conservatively in retained storage.
    retained = result_bytes + other_bytes/len(summaries)*len(regression_tasks)
    kernels = sum(s["fitting"]["fit_seconds"]+s["fitting"]["metrics_seconds"] for s in summaries)
    elapsed = sum(s["elapsed_seconds"] for s in summaries)
    result = dict(total_combinations=total_combos, validation_fits=3*total_combos,
        single_worker_hours=total_seconds/3600,
        planning_range_hours=[total_seconds/3600*.5, total_seconds/3600*3],
        uncertainty="Scenario range, not a confidence interval; tiny genre strata, SVD mix, thermal/storage effects and worker contention vary.",
        timing_basis="Measured full-population three-period OLS pilot; k/genre/target strata include checkpoint writes; catalog/ranking costs scale by candidate count; exact MAE for every candidate",
        measured_combinations=actual_combos, measured_validation_fits=actual_combos*3,
        validation_fits_per_kernel_second=actual_combos*3/kernels,
        completed_combinations_per_end_to_end_second=actual_combos/elapsed,
        estimated_results_bytes=int(result_bytes), estimated_retained_bytes=int(retained),
        recommended_free_disk_bytes=max(int(retained*3), 2*1024**3),
        peak_rss_bytes=peak_bytes(), measured_workers=1, blas_threads=1,
        parallelism="Optional 2-3 independent target workers with one BLAS thread each; no unmeasured speedup assumed",
        numerical_campaign_ready=total_seconds/3600 <= 6,
        final_refits_and_bootstrap="59 small selected-model refits and 500-resample fixed-prediction cluster intervals; allow an additional 5-15 minutes",
        bottleneck="Exact held-out absolute errors require all predictions; caching avoids per-combination full-row fitting.")
    run.write_csv(run.PUBLIC/"pilot/runtime_strata.csv", details)
    write_json(run.PUBLIC/"pilot/runtime_estimate.json", result)
    return result


def pilot(folder, benchmark_only=False):
    tasks = [t for t in spec.specs() if t["task_id"] in spec.PILOT_TASKS]
    samples = {t["task_id"]: spec.sample(t) for t in tasks}
    n = sum(map(len, samples.values()))
    if len(tasks) != 9 or n > MAX_UNIQUE_COMBINATIONS:
        raise ValueError("Pilot hard bound exceeded")
    before = {rel: spec.original.sha(spec.ROOT/rel) for rel in spec.original.FILES}
    started = time.perf_counter()
    public = run.PUBLIC/"pilot"
    resume = {}
    with threadpool_limits(limits=1):
        if not benchmark_only:
            # A real-data interruption after two committed batches; run_task
            # resumes this exact specification in the normal pilot loop.
            first = tasks[0]
            first_path = run.task_path(folder, first)
            if not (first_path/"results.sqlite").exists():
                interrupted = run.run_task(first, folder, spec.configuration(True), samples[first["task_id"]], stop_batches=2)
                resume["interrupted"] = interrupted
            summaries = [run.run_task(t, folder, spec.configuration(True), samples[t["task_id"]], check=True) for t in tasks]
            # Independent uninterrupted execution verifies all persisted scores,
            # ranks and the winner against the interrupted actual-data search.
            reference_folder = Path(folder)/"resume_reference"
            run.run_task(first, reference_folder, spec.configuration(True), samples[first["task_id"]])
            def persisted(path):
                with sqlite3.connect(path/"results.sqlite") as db:
                    return db.execute("SELECT * FROM scores ORDER BY id,fold").fetchall()
            if persisted(first_path) != persisted(run.task_path(reference_folder, first)):
                raise AssertionError("Resumed scores differ from uninterrupted execution")
            resume.update(actual_data_scores_identical=True,
                no_op_resume=run.run_task(first, folder, spec.configuration(True), samples[first["task_id"]]))
            leaderboard = run.finalize(folder, pilot=True)
            write_json(public/"target_leaderboard.json", dict(status="bounded rehearsal; not exhaustive winners; 2018+ test untouched",
                       results=leaderboard))
            run.write_csv(public/"target_leaderboard.csv", leaderboard)
            hierarchy_rows = []
            stability = []
            for task in tasks:
                candidates = samples[task["task_id"]]
                ident = run.identity(task, candidates, spec.configuration(True))
                with Store(run.task_path(folder, task)/"results.sqlite", ident, candidates, task["predictors"]) as store:
                    # All sampled candidates, including poor results, are small
                    # enough to commit; full-campaign databases remain ignored.
                    hierarchy_rows.extend(dict(task_id=task["task_id"], **r) for r in store.rows())
                    winner = next(store.rows(limit=1))
                    stability.extend(dict(task_id=task["task_id"], **r) for r in store.stability(winner["id"]))
            run.write_csv(public/"predictor_hierarchy.csv", hierarchy_rows)
            run.write_csv(public/"best_by_predictor_count.csv", [r for r in hierarchy_rows if r["rank_within_k"] == 1])
            run.write_csv(public/"historical_stability.csv", stability)
            write_json(public/"resume_validation.json", resume)
            demo(folder)
        # Timing uses the ACTUAL campaign validation periods/populations. It
        # never evaluates the 2018+ test and cannot trigger a full search.
        bench_folder = Path(folder)/"benchmark"
        config = dict(spec.configuration(), purpose="bounded full-population timing only")
        summaries = []
        for task in tasks:
            summary = run.run_task(task, bench_folder, config, samples[task["task_id"]], check=True)
            if summary.get("already_complete"):
                summary = json.loads((run.task_path(bench_folder, task)/"run_summary.json").read_text())
            summaries.append(summary)
        runtime = estimate(summaries, bench_folder)
    checks = [c for s in summaries for c in s["checks"]]
    report = dict(full_campaign_run=False, actual_final_test_rows_used=0,
        bounded_unique_predictor_sets=n, validation_fits_per_rehearsal=3*n,
        benchmark_validation_fits=3*n, resume_reference_combinations=len(samples[tasks[0]["task_id"]]),
        elapsed_seconds=time.perf_counter()-started, peak_rss_bytes=peak_bytes(),
        provenance=run.provenance(), hardware=dict(system=platform.platform(), processor=platform.processor(),
            threadpools=threadpool_info()), data_sha256=before,
        correctness_reference="SciPy LAPACK gelsd direct weighted SVD on original training rows with explicit rank cutoff",
        direct_reference_checks=len(checks),
        maximum_prediction_absolute_error=max(c["max_prediction_abs_error"] for c in checks),
        maximum_prediction_scaled_error=max(c["max_prediction_scaled_error"] for c in checks),
        correctness_checks=checks, timing_summaries=summaries, runtime_estimate=runtime)
    if before != {rel: spec.original.sha(spec.ROOT/rel) for rel in before}:
        raise AssertionError("Pilot changed protected input bytes")
    write_json(public/"benchmark.json", report)
    print(json.dumps(clean({k: report[k] for k in ["bounded_unique_predictor_sets", "benchmark_validation_fits",
        "direct_reference_checks", "maximum_prediction_absolute_error", "peak_rss_bytes", "runtime_estimate"]}), indent=2), flush=True)


def demo(folder):
    task = next(t for t in spec.specs() if t["task_id"] == "songs:detox_toxicity")
    dest = run.task_path(folder, task)
    if not (dest/"test_metrics.json").exists():
        raise ValueError("Run the bounded pilot before the demo")
    result = json.loads((dest/"test_metrics.json").read_text())
    model = json.loads((dest/"selected_model.json").read_text())
    # Re-use the saved trained coefficients, independently reconstruct encoding,
    # and verify predictions against the persisted held-out values.
    raw = run.read_table("songs")
    predictions = pd.read_csv(dest/"test_predictions.csv.gz")
    frame = spec.original.convert(raw.loc[predictions.source_row])
    actual = core.Encoder(model["encoder"]).transform(frame) @ np.array(model["coefficients"]) + model["target_center"]
    np.testing.assert_allclose(actual, predictions.predicted, atol=1e-10, rtol=1e-10)
    public = run.PUBLIC/"pilot"
    public.mkdir(parents=True, exist_ok=True)
    ordered = predictions.assign(sample_order=predictions.song_id.map(lambda x: spec.digest([spec.SEED, x]))).sort_values("sample_order")
    run.write_csv(public/"professor_actual_vs_predicted.csv", ordered.head(40).drop(columns="sample_order").to_dict("records"))
    # This one small public-data demonstrator is reviewable; the remaining
    # selected models, row-level predictions and checkpoints stay local.
    write_json(public/"professor_model.json", model)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(predictions.actual, predictions.predicted, s=10, alpha=.35, color="#2166ac")
    lo = min(predictions.actual.min(), predictions.predicted.min())
    hi = max(predictions.actual.max(), predictions.predicted.max())
    ax.plot([lo, hi], [lo, hi], color="#666666", linewidth=1)
    ax.set(xlabel="Actual frozen Detoxify toxicity score", ylabel="OLS predicted score",
           title="Pilot rehearsal: held-out 2014–2017 songs")
    ax.text(.03, .97, f"R² = {result['r2']:.3f}\nMAE = {result['mae']:.3f}\nRMSE = {result['rmse']:.3f}\nN = {result['n_test']:,}",
            transform=ax.transAxes, va="top")
    fig.tight_layout()
    plot = spec.ROOT/"docs/assets/regression_search_professor_demo.png"
    plot.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(plot, dpi=140)
    plt.close(fig)
    text = (f"Target: {task['target']}\nPredictors ({len(result['predictors'])}): {', '.join(result['predictors'])}\n"
        f"Training rows: {result['n_refit']:,}; held-out rehearsal rows: {result['n_test']:,}\n"
        f"R² {result['r2']:.4f}; MAE {result['mae']:.4f}; RMSE {result['rmse']:.4f}\n"
        f"Training-mean baseline R² {result['baseline_r2']:.4f}; RMSE {result['baseline_rmse']:.4f}; "
        f"training-median baseline MAE {result['baseline_mae']:.4f}\n"
        f"95% song-bootstrap R² interval: {result['ci95']['r2']}\n"
        "Interpretation: this measures agreement among frozen model outputs on later songs. It does not establish "
        "causation or accuracy against human toxicity labels. The winner comes from a bounded deterministic sample, "
        "not the exhaustive campaign. OLS predictions are unbounded and are not clipped.\n"
        "The campaign's 2018-onward test remains untouched. Poor performance would mean difficult to predict "
        "with these variables and additive OLS, not objectively random.\n")
    (public/"professor_demo.txt").write_text(text)
    print(text, flush=True)
