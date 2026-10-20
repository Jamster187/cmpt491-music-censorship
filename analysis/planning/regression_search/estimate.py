"""Extrapolate bounded timings; arithmetic only, no model fitting."""
from __future__ import annotations

import itertools
import json

import pandas as pd

import audit as a


def stratum_count(spec, k, genres):
    """Exact number of size-k sets with exactly these genre variables."""
    mandatory = set(genres)
    pool = [p for p in spec["predictors"] if p not in a.GENRES]
    if not mandatory <= set(spec["predictors"]) or k < len(mandatory):
        return 0
    # Current forbidden subsets are sentiment-only, disjoint from genre groups.
    assert not any(set(x)&mandatory for x in spec["forbidden_subsets"])
    return a.count_combinations(pool, spec["forbidden_subsets"], k-len(mandatory))


def main():
    specs = json.loads((a.OUT/"predictor_sets.json").read_text())
    bench = json.loads((a.OUT/"benchmark_results.json").read_text())
    samples = pd.read_csv(a.OUT/"benchmark_samples.csv")
    timing = pd.read_csv(a.OUT/"benchmark_timings.csv")
    counts = pd.read_csv(a.OUT/"search_counts.csv").set_index("task_id")
    splits = pd.read_csv(a.OUT/"split_summary.csv").set_index(["task_id","split"])
    samples["genre_stratum"] = samples.predictors.map(
        lambda x: "|".join(sorted(set(json.loads(x)) & set(a.GENRES))))
    timing = timing.merge(samples[["task_id","sample_number","genre_stratum"]],on=["task_id","sample_number"])
    # Mean across stratified sampled sets, each itself a median of three repeats.
    cells = timing.groupby(["task_id","k","genre_stratum","estimator"])[[
        "direct_fit_predict_metrics_seconds", "cached_fit_sse_seconds",
        "additional_exact_mae_seconds"]].mean()
    summaries = {x["task_id"]:x for x in bench["summaries"]}
    rows = []
    for spec in specs:
        if spec["model_family"] not in ["regression","ordinal_rank"]:
            continue
        task = spec["task_id"]
        proxy = ("songs:detox_toxicity" if spec["table"]=="songs"
                 else "monthly:monthly_rank" if spec["table"]=="monthly" else "weekly:weekly_rank")
        # Row-linear approximation for direct fit and validation projection;
        # small-matrix cached solves are independent of sample size except SVD fallback.
        sample = summaries[proxy]
        tr = int(splits.loc[(task,"train"),"observed_target_rows"])
        va = int(splits.loc[(task,"validation"),"observed_target_rows"])
        train_ratio, val_ratio = tr/sample["n_train"], va/sample["n_validation"]
        total_ratio = (tr+va)/(sample["n_train"]+sample["n_validation"])
        for estimator in ["OLS","Ridge"]:
            direct, cached, mae, batch, enumerator = 0.,0.,0.,0.,0.
            counted = 0
            for k in range(1,5):
                for ng in range(3):
                    for genre_group in itertools.combinations(a.GENRES,ng):
                        n = stratum_count(spec,k,genre_group)
                        if not n:
                            continue
                        key = "|".join(sorted(genre_group))
                        cell = cells.loc[(proxy,k,key,estimator)]
                        counted += n
                        direct += n*cell.direct_fit_predict_metrics_seconds*total_ratio
                        # Scale fallback cost conservatively with training rows.
                        cached += n*cell.cached_fit_sse_seconds*max(1.,train_ratio)
                        mae += n*cell.additional_exact_mae_seconds*val_ratio
                        batch += n*sample["batch_mae_seconds_per_estimator_fit"]*val_ratio
                        enumerator += n*sample["membership_check_seconds_per_set"]
            assert counted == int(counts.loc[task,"total"]),task
            rows.append(dict(
                task_id=task, family=spec["model_family"], estimator=estimator,
                target_predictor_sets=counted, timing_proxy=proxy,
                naive_direct_one_fold_seconds=direct+enumerator,
                cached_sse_only_one_fold_seconds=cached+enumerator,
                cached_all_metrics_one_fold_seconds=cached+mae+enumerator,
                cached_batch_mae_one_fold_seconds=cached+batch+enumerator,
                preprocessing_and_crossproducts_proxy_seconds=sample["preprocessing_and_read_seconds"]+sample["full_crossproducts_seconds"],
                forecast="Extrapolation, not a campaign measurement; sample-dependent rank-deficiency cost; 0.5x–5x planning range",
            ))
    a.write_csv("runtime_estimates.csv",rows)
    d=pd.DataFrame(rows)
    scenarios={}
    for family in ["regression","ordinal_rank"]:
        part=d[d.family.eq(family)]
        scenarios[family]={}
        for metric in ["naive_direct_one_fold_seconds","cached_sse_only_one_fold_seconds",
                       "cached_all_metrics_one_fold_seconds","cached_batch_mae_one_fold_seconds"]:
            ols=float(part.loc[part.estimator.eq("OLS"),metric].sum())
            ridge=float(part.loc[part.estimator.eq("Ridge"),metric].sum())
            scenarios[family][metric]=dict(
                ols_one_fold_hours=ols/3600,
                ridge_one_alpha_one_fold_hours=ridge/3600,
                ols_plus_four_ridge_alphas_three_folds_hours=3*(ols+4*ridge)/3600,
                note="Uses largest fold timing for all 3 folds; excludes categorical/ordinal likelihood fits and final refit."
            )
    regression_sets=int(counts[counts.model_family.eq("regression")].total.sum())
    all_sets=int(counts.total.sum())
    a.write_json("feasibility_estimates.json",dict(
        scenarios=scenarios,
        multiplicity=dict(
            regression_sets=regression_sets, all_sets=all_sets,
            three_folds_one_ols_four_ridge_regression_fit_count=regression_sets*15,
            final_test_refits="One selected estimator/set per target; final test never evaluated for every candidate."
        ),
        storage_bytes=dict(
            all_specifications_one_aggregate_result_128_bytes=all_sets*128,
            regression_15_fit_records_at_128_bytes=regression_sets*15*128,
            regression_five_estimator_aggregates_at_128_bytes=regression_sets*5*128,
            regression_15_fit_coefficients_max_38_float64=regression_sets*15*38*8,
        ),
        planning_uncertainty_multiplier=[0.5,5.0],
        caveats=[
            "No native ordinal/logistic/multilabel model timings; their runtime remains unmeasured.",
            "MAE requires row-level predictions; cross-products alone yield squared-error metrics, not exact MAE.",
            "Batch MAE timing uses all sampled coefficient vectors including wide groups; real production batch sizes and memory bandwidth need a bounded pilot.",
            "No measured parallel speedup; use 2–4 workers initially, one BLAS thread each; validate peak RSS before increasing.",
            "Timing extrapolates by exact k and genre stratum, target sample size and data resolution, not an unweighted average of handpicked combinations.",
        ],
    ))


if __name__=="__main__":
    main()
