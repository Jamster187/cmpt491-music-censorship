"""Shared-cohort OLS with bounded memory and Schur-complement loss evaluation."""
from __future__ import annotations

import os
for variable in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']:
    os.environ[variable] = '1'

import hashlib
import itertools
import time
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import linalg

import cross_domain_v4_common as parent
import cross_domain_v4_audit as old_audit
import cross_domain_v4_pilot as old_pilot
import hierarchical_v4_common as c

OK, EMPTY, CONDITION, RESIDUAL_DF, NUMERICAL = range(5)
STATUS_NAMES = ['ok', 'empty_or_constant', 'numerically_ill_conditioned', 'insufficient_residual_df', 'numerical_loss_error']


@lru_cache(maxsize=1)
def materialized(population, track):
    source = parent.load_frame(population+'.pkl')
    reg = c.registry(population)
    months = pd.PeriodIndex(source.month, freq='M')
    ext = old_pilot.external(track)
    ends = old_pilot.period_end()
    columns = {}
    for name, definition in reg.items():
        if definition['origin'] != 'external':
            if definition['kind'] != 'block' and definition['source_columns'][0] != name:
                columns[name] = source[definition['source_columns'][0]].to_numpy()
            continue
        keys = months-definition['lag']
        values = ext[definition['base']].reindex(keys).to_numpy()
        if definition['lag']:
            dates = pd.to_datetime(ends[definition['base']].reindex(keys).to_numpy(), errors='coerce')
            values = np.where(dates < months.start_time, values, np.nan)
        columns[name] = values
    return pd.concat([source, pd.DataFrame(columns, index=source.index)], axis=1)


def masks(frame, target, bounds, number):
    month = pd.PeriodIndex(frame.month, freq='M').asi8
    start, end = pd.Period(bounds[number], 'M'), pd.Period(bounds[number+1], 'M')
    cutoff = start-parent.CONFIG['embargo_months']
    observed = np.isfinite(target)
    train = observed & (month < cutoff.ordinal)
    valid = observed & (month >= start.ordinal) & (month < end.ordinal)
    if 'label_available_date' in frame:
        dates = pd.to_datetime(frame.label_available_date).to_numpy(dtype='datetime64[D]')
        train &= dates < np.datetime64(str(cutoff)+'-01')
        valid &= dates < np.datetime64(str(end)+'-01')
    return train, valid


def mask_hash(train, valid):
    return hashlib.sha256(np.packbits(train).tobytes()+np.packbits(valid).tobytes()).hexdigest()


def catalog(tasks):
    rows = []
    for pop in old_audit.POPULATIONS:
        frame = parent.load_frame(pop+'.pkl')
        reg = c.registry(pop)
        month = pd.PeriodIndex(frame.month, freq='M').asi8
        dates = pd.to_datetime(frame.label_available_date).to_numpy(dtype='datetime64[D]') if 'label_available_date' in frame else None
        for track in ['raw', 'adjusted']:
            values = old_audit.numeric_view(frame, reg, track)
            for task in (t for t in tasks if t['population'] == pop and t['track'] == track):
                scope = np.ones(len(frame), bool) if task['scope'] == 'pooled' else frame.primary_genre.eq(task['scope']).to_numpy()
                observed = np.isfinite(values[task['target']].to_numpy()) & scope
                keys = []
                for number in range(4):
                    start, end = pd.Period(task['bounds'][number], 'M'), pd.Period(task['bounds'][number+1], 'M')
                    cutoff = start-parent.CONFIG['embargo_months']
                    tr = observed & (month < cutoff.ordinal)
                    va = observed & (month >= start.ordinal) & (month < end.ordinal)
                    if dates is not None:
                        tr &= dates < np.datetime64(str(cutoff)+'-01')
                        va &= dates < np.datetime64(str(end)+'-01')
                    keys.append(mask_hash(tr, va))
                profile = 'share_target' if task['target'].startswith('genre_share__') else 'other_target'
                key = c.digest([pop, track, task['scope'], profile, keys])
                rows.append(dict(task_id=task['task_id'], population=pop, track=track,
                                 scope=task['scope'], cohort=key, fold_keys=keys))
        print('Cohort audit: '+pop, flush=True)
    return rows


@dataclass
class Design:
    X: np.ndarray
    V: np.ndarray
    Y: np.ndarray
    Z: np.ndarray
    w: np.ndarray
    u: np.ndarray
    names: list
    groups: list
    group_status: np.ndarray
    nuisance_rank: int = 0

    def __post_init__(self):
        self.G = self.X.T @ (self.w[:, None]*self.X)
        self.H = self.X.T @ (self.w[:, None]*self.Y)
        self.VG = self.V.T @ (self.u[:, None]*self.V)
        self.VH = self.V.T @ (self.u[:, None]*self.Z)
        self.ZZ = np.sum(self.u[:, None]*self.Z*self.Z, axis=0)
        self.weight_sum = self.u.sum()
        self.baseline = self.ZZ/self.weight_sum
        self.width = np.array([len(ix) for ix in self.groups], dtype=int)
        self._anchor_id = None
        self._anchor = None
        self._large_anchor_factors = {}

    @classmethod
    def from_arrays(cls, X, V, Y, Z, w, u, names, groups, nuisance_rank=0):
        """Training-only centering and within-variable whitening preserve OLS spans."""
        if Y.ndim == 1:
            Y, Z = Y[:, None], Z[:, None]
        xm = np.average(X, axis=0, weights=w)
        ym = np.average(Y, axis=0, weights=w)
        X, V = X-xm, V-xm
        Y, Z = Y-ym, Z-ym
        xx, vv, indexes, status, position = [], [], [], [], 0
        transforms = []
        for ix in groups:
            if not ix:
                indexes.append([]); status.append(EMPTY); transforms.append(None); continue
            if len(X)-max(1, nuisance_rank)-len(ix) < c.CONFIG['minimum_residual_degrees_of_freedom']:
                indexes.append([]); status.append(RESIDUAL_DF); transforms.append(None); continue
            a, b = X[:, ix], V[:, ix]
            gram = a.T @ (w[:, None]*a)
            eig = np.linalg.eigvalsh(gram)
            if eig[-1] <= 0 or eig[0] <= eig[-1]/c.CONFIG['maximum_within_group_gram_condition']:
                indexes.append([]); status.append(CONDITION); transforms.append(None); continue
            lower = linalg.cholesky(gram, lower=True, check_finite=False)
            transform = linalg.solve_triangular(lower, np.eye(len(ix)), lower=True, check_finite=False).T
            xx.append(a@transform); vv.append(b@transform)
            indexes.append(list(range(position, position+len(ix))))
            status.append(OK); position += len(ix)
            transforms.append(transform)
        x = np.column_stack(xx) if xx else np.empty((len(X), 0))
        v = np.column_stack(vv) if vv else np.empty((len(V), 0))
        result = cls(x, v, Y, Z, w, u, names, indexes, np.asarray(status, dtype=np.uint8), nuisance_rank)
        result.train_mean = ym
        result.transforms = transforms
        return result

    def anchor(self, index, targets):
        key = (index, tuple(targets))
        if self._anchor_id == key:
            return self._anchor
        a = self.groups[index]
        if index in self._large_anchor_factors:
            C, E, VA, F = self._large_anchor_factors[index]
        else:
            C = self.G[a, :]
            E = self.VG[a, :]
            VA = self.VG[np.ix_(a, a)]
            F = VA@C
            if len(a) > 16 and len(self._large_anchor_factors) < 8:
                self._large_anchor_factors[index] = (C, E, VA, F)
        HA = self.H[np.ix_(a, targets)]
        # The anchor is internally whitened: training Gram equals identity.
        loss = self.ZZ[targets]-2*np.sum(HA*self.VH[np.ix_(a, targets)], axis=0)+np.sum(HA*(VA@HA), axis=0)
        residual_h = self.H[:, targets]-C.T@HA
        residual_vh = self.VH[:, targets]-C.T@self.VH[np.ix_(a, targets)]-self.VG[:, a]@HA+C.T@(VA@HA)
        self._anchor_id = key
        self._anchor = (C, E, F, loss, residual_h, residual_vh)
        return self._anchor

    def score(self, combos, target_columns=None):
        """Score original-variable combinations; invalid attempts retain explicit status."""
        targets = np.arange(self.Y.shape[1]) if target_columns is None else np.asarray(target_columns)
        score = np.full((len(combos), len(targets)), np.inf)
        status = np.zeros(len(combos), dtype=np.uint8)
        batches = {}
        # Calls use one original-variable count; vectorize validity before the
        # small remaining index-assembly loop. No candidate values are screened.
        matrix = np.asarray(combos, dtype=int)
        if not len(matrix):
            return score, status
        status[:] = self.group_status[matrix].max(axis=1)
        widths = self.width[matrix]
        full_width = widths.sum(axis=1)
        too_wide = len(self.X)-max(1, self.nuisance_rank)-full_width < c.CONFIG['minimum_residual_degrees_of_freedom']
        status[(status == OK) & too_wide] = RESIDUAL_DF
        anchors = matrix[np.arange(len(matrix)), np.argmax(widths, axis=1)]
        for position in np.flatnonzero(status == OK):
            anchor = int(anchors[position])
            other = [column for item in matrix[position] if item != anchor for column in self.groups[item]]
            batches.setdefault((anchor, len(other)), []).append((position, other))
        for (anchor, width), rows in batches.items():
            C, E, F, loss, H, VH = self.anchor(anchor, targets)
            if not width:
                if np.any(loss < -1e-8*np.maximum(self.ZZ[targets], 1.)):
                    raise ArithmeticError('Univariate loss has catastrophic cancellation')
                score[[row[0] for row in rows]] = np.maximum(loss, 0.)/self.weight_sum
                continue
            for offset in range(0, len(rows), c.CONFIG['candidate_chunk_size']):
                part = rows[offset:offset+c.CONFIG['candidate_chunk_size']]
                positions = np.array([row[0] for row in part])
                ix = np.array([row[1] for row in part])
                ca = C[:, ix].transpose(1, 0, 2)
                ea = E[:, ix].transpose(1, 0, 2)
                fa = F[:, ix].transpose(1, 0, 2)
                schur = self.G[ix[:, :, None], ix[:, None, :]]-np.einsum('bai,baj->bij', ca, ca)
                eigen, vectors = np.linalg.eigh(schur)
                safe = (eigen[:, 0] > c.CONFIG['minimum_schur_eigenvalue']) & (eigen[:, 0] > eigen[:, -1]/c.CONFIG['maximum_within_group_gram_condition'])
                status[positions[~safe]] = CONDITION
                if not safe.any():
                    continue
                ca, ea, fa, chosen = ca[safe], ea[safe], fa[safe], ix[safe]
                rhs = H[chosen]
                eigvec = vectors[safe]
                projected = np.einsum('bij,bit->bjt', eigvec, rhs)
                coef = np.einsum('bij,bjt->bit', eigvec, projected/eigen[safe, :, None])
                cross = np.einsum('bai,baj->bij', ca, ea)
                valgram = self.VG[chosen[:, :, None], chosen[:, None, :]]-cross-cross.transpose(0, 2, 1)+np.einsum('bai,baj->bij', ca, fa)
                losses = loss[None, :]-2*np.sum(coef*VH[chosen], axis=1)+np.einsum('bit,bij,bjt->bt', coef, valgram, coef)
                tolerance = 1e-8*np.maximum(self.ZZ[targets], 1.)
                bad = np.any(~np.isfinite(losses) | (losses < -tolerance), axis=1)
                if bad.any():
                    raise ArithmeticError('Schur validation loss failed numerical integrity')
                score[positions[safe]] = np.maximum(losses, 0.)/self.weight_sum
        return score, status

    def reference(self, combo, target_column=0):
        columns = [j for i in combo for j in self.groups[i]]
        x = np.column_stack([np.ones(len(self.X)), self.X[:, columns]])
        v = np.column_stack([np.ones(len(self.V)), self.V[:, columns]])
        beta, _, rank, _ = linalg.lstsq(x*np.sqrt(self.w)[:, None], self.Y[:, target_column]*np.sqrt(self.w), lapack_driver='gelsd')
        prediction = v@beta
        direct = np.average((self.Z[:, target_column]-prediction)**2, weights=self.u)
        score, status = self.score([combo], [target_column])
        error = abs(score[0, 0]-direct)/max(self.baseline[target_column], 1e-15)
        if status[0] != OK or error > 2e-7:
            raise AssertionError('Schur OLS differs from direct full-row SVD')
        return dict(rank=int(rank), scaled_mse_error=float(error))

    def coefficients(self, combo, target_column=0):
        score, status = self.score([combo], [target_column])
        if status[0] != OK:
            return None
        anchor = min(combo, key=lambda item: (-self.width[item], item))
        a = self.groups[anchor]
        other = [column for item in combo if item != anchor for column in self.groups[item]]
        C, _, _, _, H, _ = self.anchor(anchor, [target_column])
        beta = np.zeros(self.X.shape[1])
        if other:
            cross = C[:, other]
            schur = self.G[np.ix_(other, other)]-cross.T@cross
            beta[other] = np.linalg.solve(schur, H[other, 0])
            beta[a] = self.H[a, target_column]-cross@beta[other]
        else:
            beta[a] = self.H[a, target_column]
        return {self.names[i]: self.transforms[i]@beta[self.groups[i]] for i in combo}


def prepare(tasks, number):
    started = time.perf_counter()
    task = tasks[0]
    for item in tasks:
        if any(item[key] != task[key] for key in ['population', 'track', 'scope']):
            raise ValueError('Cohort mixes analytical populations')
        if item['target'].startswith('genre_share__') != task['target'].startswith('genre_share__'):
            raise ValueError('Cohort mixes nuisance specifications')
    reg = c.registry(task['population'])
    frame = materialized(task['population'], task['track'])
    if task['scope'] != 'pooled':
        frame = frame.loc[frame.primary_genre.eq(task['scope'])].reset_index(drop=True)
    target_names = [item['target'] for item in tasks]
    values = frame[target_names].to_numpy(float)
    train, valid = masks(frame, values[:, 0], task['bounds'], number)
    for i, item in enumerate(tasks[1:], 1):
        tr, va = masks(frame, values[:, i], item['bounds'], number)
        if not np.array_equal(train, tr) or not np.array_equal(valid, va):
            raise ValueError('Cohort tasks do not have identical chronological rows')
    names = sorted({name for item in tasks for name in item['predictors']})
    tr, va = frame.loc[train].copy(), frame.loc[valid].copy()
    encoder = old_pilot.Encoder(reg).fit(tr, names)
    x = encoder.transform(tr)[:, 1:]
    v = encoder.transform(va)[:, 1:]
    groups = [[j-1 for j in encoder.groups[name]] for name in names]
    y, z = values[train].copy(), values[valid].copy()
    w, u = np.ones(len(tr)), np.ones(len(va))
    if task['population'] == 'genre_month':
        w = 1/tr.month.map(tr.month.value_counts()).to_numpy(float)
        u = 1/va.month.map(va.month.value_counts()).to_numpy(float)
    nuisance_rank = 0
    if task['track'] == 'adjusted':
        a, b = old_pilot.nuisance(tr, va, task['population'], task['target'])
        root = np.sqrt(w)
        coef, _, nuisance_rank, _ = linalg.lstsq(a*root[:, None], np.column_stack([x, y])*root[:, None], lapack_driver='gelsd')
        x -= a@coef[:, :x.shape[1]]; v -= b@coef[:, :v.shape[1]]
        y -= a@coef[:, x.shape[1]:]; z -= b@coef[:, x.shape[1]:]
    design = Design.from_arrays(x, v, y, z, w, u, names, groups, int(nuisance_rank))
    design.metadata = dict(population=task['population'], track=task['track'], scope=task['scope'], fold=number,
                           task_ids=[item['task_id'] for item in tasks], n_train=len(tr), n_validation=len(va),
                           train_months=tr.month.nunique(), validation_months=va.month.nunique(),
                           variables=len(names), encoded_columns=design.X.shape[1], seconds=time.perf_counter()-started,
                           mask_sha256=mask_hash(train, valid), unsupported_groups=int(np.count_nonzero(design.group_status)))
    design.train_months = tr.month.to_numpy()
    design.validation_months = va.month.to_numpy()
    return design


def lower_order_ids(names):
    p = len(names)
    i, j = np.triu_indices(p, 1)
    return np.column_stack([np.r_[np.arange(p), i], np.r_[np.full(p, -1), j]]).astype(np.int32)


def score_lower(design, target_columns=None, budget=None):
    ids = lower_order_ids(design.names)
    targets = list(range(design.Y.shape[1])) if target_columns is None else list(target_columns)
    scores = np.full((len(ids), len(targets)), np.inf)
    statuses = np.zeros(len(ids), dtype=np.uint8)
    p = len(design.names)
    scores[:p], statuses[:p] = design.score([(i,) for i in range(p)], targets)
    anchors = np.where(design.width[ids[p:, 0]] >= design.width[ids[p:, 1]], ids[p:, 0], ids[p:, 1])
    order = np.argsort(anchors, kind='stable')
    starts = np.searchsorted(anchors[order], np.arange(p+1))
    for anchor in range(p):
        if budget is not None and anchor % 32 == 0:
            budget.check()
        positions = p+order[starts[anchor]:starts[anchor+1]]
        if not len(positions):
            continue
        scores[positions], statuses[positions] = design.score(ids[positions], targets)
    return ids, scores, statuses
