"""Stable cached OLS and exact weighted held-out metrics. No feature screening."""
from __future__ import annotations

from dataclasses import dataclass
import json
import time

import numpy as np
import pandas as pd
from scipy import linalg

import regression_spec as spec


def weights(frame):
    w = 1 / frame.song_id.map(frame.song_id.value_counts()).to_numpy(float)
    return w / w.mean()


def weighted_median(y, w):
    order = np.argsort(y, kind="stable")
    return float(y[order[np.searchsorted(np.cumsum(w[order]), w.sum()/2)]])


def raw_columns(frame, name, median=0.):
    if name == "primary_genre":
        unknown = set(frame[name].dropna()) - set(spec.original.GENRE_TAXONOMY)
        if unknown:
            raise ValueError("Unknown genre: " + repr(unknown))
        return np.column_stack([frame[name].eq(g).to_numpy(float) for g in spec.original.GENRE_TAXONOMY[1:]]
                               + [frame[name].isna().to_numpy(float)])
    if name == "secondary_genres":
        parsed = [json.loads(v) if pd.notna(v) else None for v in frame[name]]
        for v in parsed:
            if v is not None and (not isinstance(v, list) or set(v)-set(spec.original.GENRE_TAXONOMY)):
                raise ValueError("Invalid secondary genre list")
        return np.array([[float(g in v) if v is not None else 0. for g in spec.original.GENRE_TAXONOMY]
                         + [float(v is None)] for v in parsed])
    x = frame[name].to_numpy(float)
    if np.isinf(x).any():
        raise ValueError("Infinite predictor: " + name)
    return np.column_stack([np.where(np.isnan(x), median, x), np.isnan(x).astype(float)])


class Encoder:
    def __init__(self, state=None):
        self.state = state or {}
        self.groups = {}

    def fit(self, frame, predictors):
        self.state = {}
        for name in predictors:
            median = 0.
            if name not in spec.original.GENRES:
                x = frame[name].to_numpy(float)
                median = float(np.nanmedian(x)) if np.isfinite(x).any() else 0.
            raw = raw_columns(frame, name, median)
            keep = np.flatnonzero(np.ptp(raw, axis=0) > 0)
            kept = raw[:, keep]
            self.state[name] = dict(median=median, keep=keep.tolist(),
                mean=kept.mean(axis=0).tolist(), std=kept.std(axis=0).tolist(),
                train_absent_columns=np.flatnonzero(np.ptp(raw, axis=0) == 0).tolist(),
                constant_values=raw[0, np.ptp(raw, axis=0) == 0].tolist())
        return self

    def transform(self, frame):
        cols = [np.ones((len(frame), 1))]
        position = 1
        self.groups = {}
        for name, params in self.state.items():
            raw = raw_columns(frame, name, params["median"])
            x = (raw[:, params["keep"]] - params["mean"]) / params["std"]
            self.groups[name] = list(range(position, position+x.shape[1]))
            cols.append(x)
            position += x.shape[1]
        return np.ascontiguousarray(np.column_stack(cols))

    def unsupported(self, frame):
        return {name: int(np.any(raw_columns(frame, name, p["median"])[:, p["train_absent_columns"]] != p["constant_values"],
                                axis=1).sum()) for name, p in self.state.items()
                if name in spec.original.GENRES}


def partition(raw, start, end):
    # Strings are ISO dates in the immutable public schema. Entire label windows
    # must fit a partition, even for targets that do not themselves use history.
    first, last = raw.first_chart_date, raw.last_chart_date
    tr = (first < start) & (last < start)
    va = first.ge(start)
    if end is not None:
        va &= last.lt(end)
    if set(raw.loc[tr, "song_id"]) & set(raw.loc[va, "song_id"]):
        raise ValueError("Song crosses partitions")
    if raw.groupby("song_id").first_chart_date.nunique().max() > 1 or raw.groupby("song_id").last_chart_date.nunique().max() > 1:
        raise ValueError("Inconsistent song-level chart boundaries")
    return tr, va


def metrics(y, prediction, w, mean, median):
    mse = float(np.average((y-prediction)**2, weights=w))
    mae = float(np.average(abs(y-prediction), weights=w))
    variance = float(np.average((y-np.average(y, weights=w))**2, weights=w))
    baseline_mse = float(np.average((y-mean)**2, weights=w))
    baseline_mae = float(np.average(abs(y-median), weights=w))
    return dict(r2=1-mse/variance if variance > 0 else None, mae=mae, rmse=mse**.5,
        mse=mse, skill=1-mse/baseline_mse if baseline_mse > 0 else None,
        baseline_r2=1-baseline_mse/variance if variance > 0 else None,
        baseline_mae=baseline_mae, baseline_rmse=baseline_mse**.5,
        mae_skill=1-mae/baseline_mae if baseline_mae > 0 else None)


@dataclass
class Fold:
    X: np.ndarray
    V: np.ndarray
    y: np.ndarray
    z: np.ndarray
    w: np.ndarray
    u: np.ndarray
    groups: dict
    encoder: Encoder
    train: pd.DataFrame
    validation: pd.DataFrame
    metadata: dict

    def __post_init__(self):
        t = time.perf_counter()
        self.mean = float(np.average(self.y, weights=self.w))
        self.median = weighted_median(self.y, self.w)
        self.centered_y = self.y - self.mean
        self.centered_z = self.z - self.mean
        self.G = self.X.T @ (self.w[:, None] * self.X)
        self.h = self.X.T @ (self.w * self.centered_y)
        # QR of augmented data once. R preserves singular values of every
        # selected submatrix; its last column provides Q' y without storing Q.
        augmented = np.column_stack([self.X, self.centered_y]) * np.sqrt(self.w)[:, None]
        qr = linalg.qr(augmented, mode="r", overwrite_a=True, check_finite=False)[0]
        p = self.X.shape[1]
        self.R = qr[:min(len(self.y), p), :p].copy()
        self.qy = qr[:min(len(self.y), p), p].copy()
        self.baseline = metrics(self.z, np.full(len(self.z), self.mean), self.u, self.mean, self.median)
        self.metadata.update(n_train=len(self.y), n_validation=len(self.z),
            train_songs=int(self.train.song_id.nunique()), validation_songs=int(self.validation.song_id.nunique()),
            baseline=self.baseline, train_mean=self.mean, train_median=self.median,
            encoded_columns=p, cache_seconds=time.perf_counter()-t,
            unsupported_genre_rows=self.encoder.unsupported(self.validation))

    def indices(self, combo):
        return [0] + [i for c in combo for i in self.groups[c]]

    def fit_batch(self, combos):
        """Batched normal equations when safe; cached QR/SVD otherwise.

        Group by encoded width so no padding can alter rank. Exact duplicates,
        empty feature groups, and near singular fits are all evaluated.
        """
        indices = [self.indices(c) for c in combos]
        B = np.zeros((self.X.shape[1], len(combos)))
        ranks = np.empty(len(combos), int)
        fallbacks = np.zeros(len(combos), bool)
        for width in sorted(set(map(len, indices))):
            positions = [i for i, ix in enumerate(indices) if len(ix) == width]
            ix = np.array([indices[i] for i in positions])
            gram = self.G[ix[:, :, None], ix[:, None, :]]
            values, vectors = np.linalg.eigh(gram)
            safe = values[:, 0] > values[:, -1] * 1e-8
            beta = np.zeros((len(positions), width))
            if safe.any():
                v = vectors[safe]
                projected = np.einsum("bij,bi->bj", v, self.h[ix[safe]])
                beta[safe] = np.einsum("bij,bj->bi", v, projected / values[safe])
            ranks[positions] = width
            if (~safe).any():
                A = self.R[:, ix[~safe]].transpose(1, 0, 2)
                u, s, vh = np.linalg.svd(A, full_matrices=False)
                keep = s > np.finfo(float).eps * max(len(self.y), width) * s[:, :1]
                inv = np.divide(1., s, out=np.zeros_like(s), where=keep)
                beta[~safe] = np.einsum("bji,bj->bi", vh,
                    np.einsum("brj,r->bj", u, self.qy) * inv)
                ranks[np.array(positions)[~safe]] = keep.sum(axis=1)
                fallbacks[np.array(positions)[~safe]] = True
            for pos, columns, coef in zip(positions, ix, beta):
                B[columns, pos] = coef
        return B, ranks, fallbacks

    def evaluate(self, combos, row_batch=4096):
        t = time.perf_counter()
        B, ranks, fallbacks = self.fit_batch(combos)
        fitting = time.perf_counter()-t
        t = time.perf_counter()
        sae, sse = np.zeros(len(combos)), np.zeros(len(combos))
        for start in range(0, len(self.z), row_batch):
            stop = start + row_batch
            residual = self.centered_z[start:stop, None] - self.V[start:stop] @ B
            sae += self.u[start:stop] @ abs(residual)
            sse += self.u[start:stop] @ (residual*residual)
        mse, mae = sse / self.u.sum(), sae / self.u.sum()
        variance = np.average((self.z-np.average(self.z, weights=self.u))**2, weights=self.u)
        r2 = 1-mse/variance if variance > 0 else np.full(len(combos), np.nan)
        base = self.baseline["mse"]
        skill = 1-mse/base if base > 0 else np.full(len(combos), np.nan)
        return dict(r2=r2, mae=mae, mse=mse, skill=skill, rank=ranks, fallback=fallbacks), dict(
            fit_seconds=fitting, metrics_seconds=time.perf_counter()-t, fits=len(combos),
            qr_svd_fallbacks=int(fallbacks.sum()))

    def reference_check(self, combo):
        ix = self.indices(combo)
        root = np.sqrt(self.w)
        reference, _, rank, _ = linalg.lstsq(self.X[:, ix]*root[:, None],
            self.centered_y*root, cond=np.finfo(float).eps*max(len(self.y), len(ix)),
            lapack_driver="gelsd")
        B, ranks, _ = self.fit_batch([combo])
        expected, actual = self.V[:, ix] @ reference, self.V @ B[:, 0]
        scale = max(1., float(np.max(abs(expected))))
        error = float(np.max(abs(expected-actual)))
        if error > 2e-7*scale or rank != ranks[0]:
            raise AssertionError("OLS disagrees with direct SciPy SVD: " + repr((combo, error, scale, rank, ranks[0])))
        a = metrics(self.z, actual+self.mean, self.u, self.mean, self.median)
        e = metrics(self.z, expected+self.mean, self.u, self.mean, self.median)
        return dict(predictors=list(combo), max_prediction_abs_error=error,
            max_prediction_scaled_error=error/scale, rank=int(rank),
            max_metric_abs_error=max(abs(a[k]-e[k]) for k in ("mae", "rmse", "mse")))


def prepare(raw, task, start, end):
    tr, va = partition(raw, start, end)
    # No held-out values enter feature fitting; target-specific population is
    # fixed once for every candidate. Dates/year transform without fitting.
    converted = spec.original.convert(raw.loc[tr | va])
    observed = converted[task["target"]].notna()
    train = converted.loc[tr.loc[converted.index] & observed]
    val = converted.loc[va.loc[converted.index] & observed]
    if len(train) < 2 or len(val) < 2:
        raise ValueError("Insufficient observed target support")
    encoder = Encoder().fit(train, task["predictors"])
    X, V = encoder.transform(train), encoder.transform(val)
    y, z = train[task["target"]].to_numpy(float), val[task["target"]].to_numpy(float)
    if not np.isfinite(y).all() or not np.isfinite(z).all():
        raise ValueError("Nonfinite outcome")
    return Fold(X, V, y, z, weights(train), weights(val), encoder.groups, encoder, train, val,
                dict(validation_start=start, validation_end=end))
