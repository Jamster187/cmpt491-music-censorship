"""Frozen three-variable OLS specification; the original audit remains historical."""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.planning.regression_search import audit as original

VERSION = "ols-three-v1"
MAX_PREDICTORS = 3
SEED = 491
FILES = dict(songs=original.FILES[0], monthly=original.FILES[1], weekly=original.FILES[2])
FOLDS = [("1990-01-01", "2000-01-01"), ("2000-01-01", "2010-01-01"),
         ("2010-01-01", "2018-01-01")]
PILOT_FOLDS = FOLDS[:2] + [("2010-01-01", "2014-01-01")]
PILOT_TASKS = ["songs:" + c for c in ["detox_toxicity", "ll_violence", "emotion_joy",
    "sentiment_positive", "mb_duration_median_seconds", "mb_release_year", "chart_weeks"]] + [
    "monthly:reported_weeks_on_chart", "weekly:reported_weeks_on_chart"]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def specs():
    result = original.target_specs()
    for s in result:
        s["all_subsets_rule"] = "Every allowed unordered subset of 1, 2 or 3 original variables."
        s["campaign_status"] = "OLS" if s["model_family"] == "regression" else "deferred_separate_family"
    return result


def combinations(spec):
    for k in range(1, MAX_PREDICTORS + 1):
        for combo in itertools.combinations(spec["predictors"], k):
            if original.allowed(combo, spec["forbidden_subsets"]):
                yield combo


def count(spec, k):
    return original.count_combinations(spec["predictors"], spec["forbidden_subsets"], k)


def stratum(combo):
    return "both" if set(original.GENRES) <= set(combo) else (
        "primary" if "primary_genre" in combo else "secondary" if "secondary_genres" in combo else "numeric")


def sample(spec, per_stratum=16):
    """Bounded hash sample, balanced by k and encoding width; no outcome screening."""
    buckets = {}
    for index, combo in enumerate(combinations(spec)):
        buckets.setdefault((len(combo), stratum(combo)), []).append((digest([SEED, combo]), index, combo))
    chosen = [item[1:] for bucket in buckets.values() for item in sorted(bucket)[:per_stratum]]
    return sorted(chosen)


def configuration(pilot=False):
    return dict(version=VERSION, estimator="OLS", intercept=True, interactions=False,
        max_original_predictors=3, folds=PILOT_FOLDS if pilot else FOLDS,
        test_start="2014-01-01" if pilot else "2018-01-01",
        test_end="2018-01-01" if pilot else None, seed=SEED,
        selection="mean equal-fold baseline-relative MSE skill; then fewer variables; then lexicographic predictors",
        weights="inverse rows per song within target-observed partition, normalized to mean 1",
        preprocessing="train median + missing flag, fixed 16 genres, unweighted train standardization, remove constant columns",
        rank_tolerance="float64 eps * max(original training rows, selected columns) * largest singular value",
        uncertainty="500 song-cluster resamples of fixed final predictions; additional two-year debut-block intervals when at least three blocks exist; no selection/refit inside bootstrap",
        test_isolation="pilot uses only pre-2018 songs; campaign final test reserved until all winners frozen",
        scope="retrospective frozen-release cohort generalization, not an as-of forecast")
