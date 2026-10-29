"""Common training-only encoding, additive/polynomial fits and clustered diagnostics."""
from __future__ import annotations
import itertools
import time
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy import linalg, stats

import strategy_v4_common as c
import cross_domain_v4_pilot as old
import hierarchical_v4_engine as previous


@dataclass
class ObservedCase:
    key: str
    task: dict
    frame: pd.DataFrame
    y: np.ndarray
    registry: dict
    # No signal labels, locations, scenario family or oracle model live here.


@dataclass
class SearchContext:
    key: str
    task: dict
    registry: dict


@dataclass
class Prepared:
    X: np.ndarray
    V: np.ndarray
    y: np.ndarray
    z: np.ndarray
    w: np.ndarray
    u: np.ndarray
    a: np.ndarray
    b: np.ndarray
    groups: dict
    primary: dict
    train: pd.DataFrame
    valid: pd.DataFrame
    baseline_prediction: np.ndarray
    baseline_mse: float
    baseline_mae: float
    train_residual: np.ndarray
    support: dict


def real_case(task):
    frame = previous.materialized(task['population'], task['track'])
    if task['scope'] != 'pooled':
        frame = frame.loc[frame.primary_genre.eq(task['scope'])].reset_index(drop=True)
    return ObservedCase(c.digest(['real', task['task_id']])[:20], task, frame,
                        frame[task['target']].to_numpy(float), c.registry(task['population']))


def prepare(case, number):
    task, frame = case.task, case.frame
    tr, va = previous.masks(frame, case.y, task['bounds'], number)
    train, valid = frame.loc[tr].copy(), frame.loc[va].copy()
    if len(train) < 30 or len(valid) < 12:
        raise ValueError('Benchmark case violates original chronological row support')
    if set(train.row_id) & set(valid.row_id):
        raise ValueError('Whole-song/row split contamination')
    encoder = old.Encoder(case.registry).fit(train, task['predictors'])
    x, v = encoder.transform(train)[:, 1:], encoder.transform(valid)[:, 1:]
    groups = {name: [i-1 for i in indexes] for name, indexes in encoder.groups.items()}
    primary = {name: groups[name][encoder.state[name]['keep'].index(0)]
               for name in task['predictors'] if case.registry[name]['kind'] == 'numeric'
               and 0 in encoder.state[name]['keep']}
    y, z = case.y[tr].copy(), case.y[va].copy()
    w, u = np.ones(len(train)), np.ones(len(valid))
    if task['population'] == 'genre_month':
        w = 1/train.month.map(train.month.value_counts()).to_numpy(float)
        u = 1/valid.month.map(valid.month.value_counts()).to_numpy(float)
    if task['track'] == 'adjusted':
        a, b = old.nuisance(train, valid, task['population'], task['target'])
    else:
        a, b = np.ones((len(train), 1)), np.ones((len(valid), 1))
    coefficient = linalg.lstsq(a*np.sqrt(w)[:, None], y*np.sqrt(w), lapack_driver='gelsy')[0]
    pred = b@coefficient
    baseline = float(np.average((z-pred)**2, weights=u))
    native = case.registry[task['target']].get('frequency', 'M')
    freq = 'Y' if native in ['A', 'Y', 'annual'] else ('Q' if native in ['Q', 'quarterly'] else 'M')
    support = dict(train_rows=len(train), test_rows=len(valid), train_months=train.month.nunique(), test_months=valid.month.nunique(),
                   train_periods=pd.PeriodIndex(train.month, freq='M').asfreq(freq).nunique(),
                   test_periods=pd.PeriodIndex(valid.month, freq='M').asfreq(freq).nunique(),
                   train_ids=c.digest(train.row_id.tolist()), test_ids=c.digest(valid.row_id.tolist()))
    support['enough'] = (support['train_months'] >= c.CONFIG['minimum_train_months']
                         and support['test_months'] >= c.CONFIG['minimum_test_months']
                         and support['train_periods'] >= c.CONFIG['minimum_native_train_periods']
                         and support['test_periods'] >= c.CONFIG['minimum_native_test_periods'])
    return Prepared(x, v, y, z, w, u, a, b, groups, primary, train, valid, pred, baseline,
                    float(np.average(abs(z-pred), weights=u)), y-a@coefficient, support)


def expanded(fold, combo, family):
    indexes = [i for name in combo for i in fold.groups[name]]
    if not indexes:
        return None
    x, v = fold.X[:, indexes], fold.V[:, indexes]
    if family == 'polynomial':
        # Full categorical/embedding main effects stay present. A polynomial
        # candidate too wide for this bounded estimator is recorded unsupported.
        if len(indexes) > c.CONFIG['polynomial_max_columns']:
            return None
        numbers = [fold.primary[name] for name in combo if name in fold.primary]
        extra_x, extra_v = [], []
        for i in numbers:
            extra_x.append(fold.X[:, i]**2); extra_v.append(fold.V[:, i]**2)
        for degree in [2, 3]:
            for term in itertools.combinations(numbers, degree):
                extra_x.append(np.prod(fold.X[:, term], axis=1)); extra_v.append(np.prod(fold.V[:, term], axis=1))
        if extra_x:
            x, v = np.column_stack([x, *extra_x]), np.column_stack([v, *extra_v])
    return x, v


def fit(fold, combo, family, predictions=False):
    arrays = expanded(fold, combo, family)
    if arrays is None:
        return dict(status='unsupported_encoding', skill=None, mse=None, mae=None)
    x, v = arrays
    # Standardize engineered terms using training rows only, preserving their span.
    mean, scale = np.average(x, axis=0, weights=fold.w), np.sqrt(np.average((x-np.average(x, axis=0, weights=fold.w))**2, axis=0, weights=fold.w))
    good = scale > 1e-10
    if not good.any():
        return dict(status='constant', skill=None, mse=None, mae=None)
    x, v = (x[:, good]-mean[good])/scale[good], (v[:, good]-mean[good])/scale[good]
    a, b = np.column_stack([fold.a, x]), np.column_stack([fold.b, v])
    if len(a)-a.shape[1] < c.CONFIG['minimum_residual_df']:
        return dict(status='insufficient_df', skill=None, mse=None, mae=None)
    beta, _, rank, _ = linalg.lstsq(a*np.sqrt(fold.w)[:, None], fold.y*np.sqrt(fold.w), cond=1e-8, lapack_driver='gelsy')
    # Nuisance/control overlap is harmless to predictions but is always labelled.
    prediction = b@beta
    loss = (fold.z-prediction)**2
    mse = float(np.average(loss, weights=fold.u))
    if not np.isfinite(mse) or fold.baseline_mse <= 1e-15:
        return dict(status='invalid_loss', skill=None, mse=None, mae=None)
    result = dict(status='ok' if rank == a.shape[1] else 'rank_deficient', skill=1-mse/fold.baseline_mse,
                  mse=mse, mae=float(np.average(abs(fold.z-prediction), weights=fold.u)), rank=int(rank), columns=a.shape[1],
                  support_sufficient=fold.support['enough'])
    if predictions:
        result['loss'] = loss; result['prediction'] = prediction
    return result


def weighted_corr(x, y, w):
    x = x-np.average(x, axis=0, weights=w); y = y-np.average(y, weights=w)
    denominator = np.sqrt(np.sum(w[:, None]*x*x, axis=0)*np.sum(w*y*y))
    return np.divide(x.T@(w*y), denominator, out=np.zeros(x.shape[1]), where=denominator > 1e-15)


def pairwise(folds, names):
    """All eligible target/predictor pairs; ranks and bin edges are training-only."""
    started = time.perf_counter(); by_fold = []; diagnostics = []
    for fold in folds:
        # Work in chunks: all original variables are visited, including blocks.
        score = {}; details = []
        for start in range(0, len(names), 48):
            chunk = names[start:start+48]
            columns = [i for name in chunk for i in fold.groups[name]]
            if not columns:
                for name in chunk:
                    score[name] = 0.
                continue
            x = fold.X[:, columns]
            coefficient = linalg.lstsq(fold.a*np.sqrt(fold.w)[:, None], x*np.sqrt(fold.w)[:, None], lapack_driver='gelsy')[0]
            x = x-fold.a@coefficient
            pearson = weighted_corr(x, fold.train_residual, fold.w)
            ranks = stats.rankdata(x, axis=0, method='average')
            spearman = weighted_corr(ranks, stats.rankdata(fold.train_residual), fold.w)
            # Five empirical-quantile bins: eta squared is a nonlinear dependence
            # diagnostic, not a p-value. Wide blocks use the maximum column score.
            labels = np.minimum((ranks/len(x)*5).astype(int), 4)
            labels += np.arange(x.shape[1])[None, :]*5
            denominator = np.bincount(labels.ravel(), weights=np.repeat(fold.w, x.shape[1]), minlength=x.shape[1]*5)
            numerator = np.bincount(labels.ravel(), weights=np.repeat(fold.w*fold.train_residual, x.shape[1]), minlength=x.shape[1]*5)
            ybar = np.average(fold.train_residual, weights=fold.w)
            means = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)
            eta = (denominator*(means-ybar)**2).reshape(-1, 5).sum(axis=1)/max(np.sum(fold.w*(fold.train_residual-ybar)**2), 1e-15)
            position = 0
            for name in chunk:
                width = len(fold.groups[name]); sl = slice(position, position+width); position += width
                values = dict(predictor=name, pearson=float(np.max(abs(pearson[sl]))) if width else 0.,
                              spearman=float(np.max(abs(spearman[sl]))) if width else 0.,
                              eta_squared=float(np.max(eta[sl])) if width else 0., encoded_columns=width)
                score[name] = max(values['pearson'], values['spearman'], np.sqrt(max(0., values['eta_squared'])))
                details.append(values)
        by_fold.append(score); diagnostics.append(details)
    merged = {name: float(np.mean([row.get(name, 0.) for row in by_fold])+.5*min(row.get(name, 0.) for row in by_fold)) for name in names}
    return merged, dict(seconds=time.perf_counter()-started, original_pairs=len(names), fold_pairs=len(names)*len(folds),
                        numeric_and_group_diagnostics=diagnostics)


def rank(results):
    values = [row['skill'] for row in results]
    if any(v is None or not np.isfinite(v) for v in values) or any(r['status'] != 'ok' for r in results):
        return -np.inf
    return float(np.mean(values)+.5*min(values))


def assessment_stat(results):
    if any(r['status'] != 'ok' or r['skill'] is None or not r.get('support_sufficient') for r in results):
        return -np.inf
    return min(r['skill'] for r in results)


def clustered_interval(folds, results, population, seed):
    """Two-way pigeonhole weights for time blocks and credit/genre clusters.

    These are descriptive uncertainty intervals conditional on the frozen model;
    they are neither independent confirmation nor post-selection confidence sets.
    """
    if any('loss' not in r for r in results):
        return dict(status='unavailable')
    baseline, loss, weights, month, second = [], [], [], [], []
    for fold, result in zip(folds, results):
        baseline.extend((fold.z-fold.baseline_prediction)**2); loss.extend(result['loss']); weights.extend(fold.u)
        month.extend(pd.PeriodIndex(fold.valid.month, freq='M').asi8)
        if population == 'song':
            second.extend(fold.valid.artist.astype(str).tolist())
        elif population == 'genre_month':
            second.extend(fold.valid.primary_genre.astype(str).tolist())
        else:
            second.extend(['monthly']*len(fold.valid))
    block = np.asarray(month)//c.CONFIG['block_months']
    block_ids, unique = pd.factorize(block); cluster_ids, clusters = pd.factorize(np.asarray(second))
    if len(unique) < c.CONFIG['minimum_uncertainty_blocks']:
        return dict(status='insufficient_time_blocks', time_blocks=len(unique), second_clusters=len(clusters))
    w, b, e = np.asarray(weights), np.asarray(baseline), np.asarray(loss)
    rng = np.random.default_rng(seed); values = []
    for _ in range(c.CONFIG['bootstrap_replicates']):
        wb = rng.multinomial(len(unique), np.full(len(unique), 1/len(unique)))[block_ids]
        wc = rng.multinomial(len(clusters), np.full(len(clusters), 1/len(clusters)))[cluster_ids] if len(clusters) > 1 else 1.
        a = w*wb*wc
        if a.sum() and np.sum(a*b) > 1e-15:
            values.append(1-np.sum(a*e)/np.sum(a*b))
    return dict(status='ok', low=float(np.quantile(values, .025)), high=float(np.quantile(values, .975)),
                time_blocks=len(unique), second_clusters=len(clusters), resamples=len(values),
                cluster_type='exact_artist_credit' if population == 'song' else ('genre' if population == 'genre_month' else 'calendar_block'))
