"""Bounded deterministic timing experiment, never an exhaustive search.

At most 64 predictor sets per representative table, OLS + one fixed Ridge alpha,
three timing repeats. Test rows are excluded before any feature fitting/scoring.
"""
from __future__ import annotations

import gc
import json
import platform
import random
import resource
import subprocess
import time

import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.linear_model import LinearRegression, Ridge
from threadpoolctl import threadpool_info, threadpool_limits

import audit as a

SEED = 491
PER_K = 16
REPEATS = 3
MAX_SETS = 3 * 4 * PER_K


def sample_sets(spec):
    rng = random.Random(SEED)
    chosen = []
    # Deliberately include both wide genre encodings in the bounded benchmark,
    # alongside numeric-only sets; not a policy for the exhaustive campaign.
    for k in range(1, 5):
        seen = set()
        for genre_group in [[], ["primary_genre"], ["secondary_genres"],
                            ["primary_genre", "secondary_genres"]]:
            if len(genre_group) > k or not set(genre_group) <= set(spec["predictors"]):
                continue
            others = [p for p in spec["predictors"] if p not in a.GENRES]
            combo = tuple(sorted(genre_group + rng.sample(others, k-len(genre_group))))
            if a.allowed(combo, spec["forbidden_subsets"]):
                seen.add(combo)
        while len(seen) < PER_K:
            combo = tuple(sorted(rng.sample(spec["predictors"], k)))
            if a.allowed(combo, spec["forbidden_subsets"]):
                seen.add(combo)
        chosen.extend(sorted(seen))
    assert len(chosen) == PER_K * 4
    return chosen


def encode(train, validation, predictors):
    """Train-fitted imputation/scaling. Fixed taxonomy has no learned test levels."""
    tr_columns, va_columns, groups = [], [], {}
    for c in predictors:
        if c == "primary_genre":
            tr = np.column_stack([train[c].eq(v).to_numpy(float) for v in a.GENRE_TAXONOMY[1:]]
                                 + [train[c].isna().to_numpy(float)])
            va = np.column_stack([validation[c].eq(v).to_numpy(float) for v in a.GENRE_TAXONOMY[1:]]
                                 + [validation[c].isna().to_numpy(float)])
        elif c == "secondary_genres":
            def multi(series):
                parsed = [set(json.loads(v)) if pd.notna(v) else None for v in series]
                return np.array([[float(g in v) if v is not None else 0.
                                  for g in a.GENRE_TAXONOMY] + [float(v is None)]
                                 for v in parsed], dtype=float)
            tr, va = multi(train[c]), multi(validation[c])
        else:
            x, z = train[c].to_numpy(float), validation[c].to_numpy(float)
            median = float(np.nanmedian(x)) if np.isfinite(x).any() else 0.
            tr = np.column_stack([np.where(np.isnan(x), median, x), np.isnan(x).astype(float)])
            va = np.column_stack([np.where(np.isnan(z), median, z), np.isnan(z).astype(float)])
        # Remove only constant encoded columns; retain the original candidate set.
        keep = np.ptp(tr, axis=0) > 0
        tr, va = tr[:, keep], va[:, keep]
        mean, std = tr.mean(axis=0), tr.std(axis=0)
        tr, va = (tr-mean)/std, (va-mean)/std
        start = len(tr_columns)
        tr_columns.extend(tr.T)
        va_columns.extend(va.T)
        groups[c] = list(range(start, len(tr_columns)))
    return np.column_stack(tr_columns), np.column_stack(va_columns), groups


def weights(frame):
    n = frame.song_id.map(frame.song_id.value_counts()).to_numpy(float)
    w = 1/n
    return w/w.mean()


def gram_fit(G, h, alpha, X=None, y=None, w=None):
    penalty = np.eye(len(h)) * alpha
    penalty[0, 0] = 0.
    # Normal equations amplify condition number. Never silently drop a candidate.
    condition = float(np.linalg.cond(G + penalty))
    fallback = alpha == 0 and (not np.isfinite(condition) or condition > 1e10)
    if fallback:
        if X is None:
            raise ValueError("Ill-conditioned OLS requires direct SVD inputs")
        root = np.sqrt(w)
        beta = np.linalg.lstsq(X*root[:, None], y*root, rcond=None)[0]
    else:
        beta = np.linalg.solve(G+penalty, h)
    return beta, fallback, condition


def main():
    plan = {s["task_id"]:s for s in json.loads((a.OUT/"predictor_sets.json").read_text())}
    before = {rel:a.sha(a.ROOT/rel) for rel in a.FILES[:3]}
    results, sample_rows, summaries = [], [], []
    cases = [
        ("songs:detox_toxicity", a.FILES[0]),
        ("monthly:monthly_rank", a.FILES[1]),
        ("weekly:weekly_rank", a.FILES[2]),
    ]
    started = time.perf_counter()
    for task, rel in cases:
        spec = plan[task]
        t = time.perf_counter()
        raw = a.read_table(rel)
        labels = a.split_labels(raw)
        # Deliberately do not pass test rows through learned preprocessing.
        eligible = labels.isin(["train", "validation"]) & raw[spec["target"]].notna()
        d = a.convert(raw.loc[eligible].copy())
        labels = labels.loc[eligible]
        train, val = d.loc[labels.eq("train")], d.loc[labels.eq("validation")]
        assert set(train.song_id).isdisjoint(set(val.song_id))
        X, V, groups = encode(train, val, spec["predictors"])
        y, z = train[spec["target"]].to_numpy(float), val[spec["target"]].to_numpy(float)
        w, u = weights(train), weights(val)
        X = np.column_stack([np.ones(len(X)), X])
        V = np.column_stack([np.ones(len(V)), V])
        groups = {c:[i+1 for i in idx] for c,idx in groups.items()}
        prep_seconds = time.perf_counter()-t
        t = time.perf_counter()
        G, h = X.T @ (w[:, None]*X), X.T @ (w*y)
        H, j, zz = V.T @ (u[:, None]*V), V.T @ (u*z), float(np.dot(u*z,z))
        cache_seconds = time.perf_counter()-t
        sets = sample_sets(spec)
        coefficients = []
        fallback_n, max_difference, max_sse_relative_error = 0, 0., 0.
        for number, combo in enumerate(sets):
            t = time.perf_counter()
            columns = [0] + sum([groups[c] for c in combo], [])
            gg, hh = G[np.ix_(columns,columns)], h[columns]
            vv, jj = H[np.ix_(columns,columns)], j[columns]
            crossproduct_gather_seconds = time.perf_counter()-t
            t = time.perf_counter()
            xt = X[:, columns]
            train_gather_seconds = time.perf_counter()-t
            t = time.perf_counter()
            vt = V[:, columns]
            validation_gather_seconds = time.perf_counter()-t
            sample_rows.append(dict(task_id=task, sample_number=number, k=len(combo),
                predictors=json.dumps(combo), n_train=len(y), n_validation=len(z),
                encoded_coefficients=len(columns),
                train_gather_seconds=train_gather_seconds,
                validation_gather_seconds=validation_gather_seconds,
                crossproduct_gather_seconds=crossproduct_gather_seconds,
                matrix_rank=int(np.linalg.matrix_rank(gg))))
            for estimator, alpha in [("OLS", 0.), ("Ridge", len(y)*.001)]:
                direct_times, cache_times, mae_times = [], [], []
                for repeat in range(REPEATS):
                    t = time.perf_counter()
                    if estimator == "OLS":
                        # Explicit rank-aware SVD tolerance. sklearn 1.5.2's
                        # default scipy cutoff can keep near-zero singular
                        # values from identical metadata missing indicators.
                        root = np.sqrt(w)
                        direct_beta = np.linalg.lstsq(
                            xt*root[:,None], y*root, rcond=None
                        )[0]
                        pred = vt@direct_beta
                    else:
                        model = Ridge(alpha=alpha, solver="cholesky")
                        model.fit(xt[:,1:], y, sample_weight=w)
                        pred = model.predict(vt[:,1:])
                    direct_sse = float(np.dot(u, (z-pred)**2))
                    _mae = float(np.dot(u, abs(z-pred))/u.sum())
                    direct_times.append(time.perf_counter()-t)
                    t = time.perf_counter()
                    beta, fallback, condition = gram_fit(gg, hh, alpha, xt, y, w)
                    sse = float(zz - 2*beta@jj + beta@vv@beta)
                    cache_times.append(time.perf_counter()-t)
                    t = time.perf_counter()
                    cpred = vt@beta
                    _mae = float(np.dot(u, abs(z-cpred))/u.sum())
                    mae_times.append(time.perf_counter()-t)
                    max_difference = max(max_difference, float(np.max(abs(pred-cpred))))
                    max_sse_relative_error = max(max_sse_relative_error,
                        abs(sse-direct_sse)/max(1., direct_sse))
                    if not np.allclose(pred, cpred, rtol=1e-5, atol=1e-6):
                        raise AssertionError("Direct/cached prediction mismatch: "+str((task,combo,estimator)))
                fallback_n += int(fallback)
                coefficients.append((columns,beta))
                results.append(dict(task_id=task, sample_number=number, k=len(combo),
                    estimator=estimator, ridge_alpha=alpha, encoded_coefficients=len(columns),
                    direct_fit_predict_metrics_seconds=float(np.median(direct_times))
                        + train_gather_seconds + validation_gather_seconds,
                    cached_fit_sse_seconds=float(np.median(cache_times))
                        + crossproduct_gather_seconds + (train_gather_seconds if fallback else 0.),
                    additional_exact_mae_seconds=float(np.median(mae_times))
                        + validation_gather_seconds,
                    condition_number=condition if np.isfinite(condition) else None,
                    svd_fallback=bool(fallback)))
        # Batch projection still evaluates EVERY sampled candidate's MAE.
        B = np.zeros((X.shape[1], len(coefficients)))
        for i,(cols,beta) in enumerate(coefficients):
            B[cols,i] = beta
        t = time.perf_counter()
        _batch_mae = np.sum(u[:,None]*abs(z[:,None]-V@B), axis=0)/u.sum()
        batch_seconds = time.perf_counter()-t
        t = time.perf_counter()
        for _ in range(1000):
            for combo in sets:
                if not a.allowed(combo,spec["forbidden_subsets"]):
                    raise AssertionError("Forbidden benchmark sample")
        enumeration_seconds = (time.perf_counter()-t)/(1000*len(sets))
        summaries.append(dict(task_id=task, sampled_sets=len(sets), estimators=2,
            timing_repeats=REPEATS, n_train=len(y), n_validation=len(z),
            train_songs=int(train.song_id.nunique()), validation_songs=int(val.song_id.nunique()),
            prepared_matrix_columns=X.shape[1], prepared_matrix_bytes=X.nbytes+V.nbytes,
            preprocessing_and_read_seconds=prep_seconds, full_crossproducts_seconds=cache_seconds,
            cached_crossproducts_bytes=G.nbytes+H.nbytes+h.nbytes+j.nbytes,
            batch_mae_seconds_per_estimator_fit=batch_seconds/len(coefficients),
            membership_check_seconds_per_set=enumeration_seconds,
            svd_fallback_fit_specifications=fallback_n,
            max_direct_cached_prediction_abs_difference=max_difference,
            max_direct_cached_sse_relative_difference=max_sse_relative_error))
        print("Benchmarked", task, summaries[-1], flush=True)
        del raw, d, train, val, X, V, G, H, B, xt, vt
        gc.collect()
    assert len(sample_rows) <= MAX_SETS
    assert before == {rel:a.sha(a.ROOT/rel) for rel in before}
    # Peak RSS is bytes on Darwin and KiB on Linux.
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = int(rss if platform.system()=="Darwin" else rss*1024)
    a.write_csv("benchmark_samples.csv", sample_rows)
    a.write_csv("benchmark_timings.csv", results)
    a.write_json("benchmark_results.json", dict(
        seed=SEED, max_sets=MAX_SETS, actual_sets=len(sample_rows),
        direct_fit_calls=len(results)*REPEATS,
        cached_fit_calls=len(results)*REPEATS,
        estimator_specifications=len(results),
        note="Direct and cached paths both execute each timing repeat; NumPy rank-aware OLS and sklearn Ridge only. Ordinal likelihoods and categorical classifiers not benchmarked.",
        ridge_objective="sum(weight * squared error) + alpha * squared coefficients; mean weight=1; alpha=n_train*0.001; intercept unpenalized",
        elapsed_seconds=time.perf_counter()-started, peak_process_rss_bytes=rss_bytes,
        peak_rss_includes="CSV parsing, DataFrames, copies, preprocessing and all three sequential cases; not solely linear algebra",
        hardware=subprocess.check_output(["sysctl","-n","machdep.cpu.brand_string","hw.memsize","hw.logicalcpu"],text=True).splitlines()
                 if platform.system()=="Darwin" else [platform.machine()],
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                      scipy=scipy.__version__, sklearn=sklearn.__version__),
        threadpools=threadpool_info(), blas_threads=1, summaries=summaries,
        input_hashes=before, benchmark_script_sha256=a.sha(__file__),
        full_campaign_run=False, test_rows_used=0,
    ))


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        main()
