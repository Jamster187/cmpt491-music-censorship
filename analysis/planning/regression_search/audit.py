"""Read-only feasibility audit. This module has no exhaustive model-fit command.

Run from any directory: python3 analysis/planning/regression_search/audit.py
Writes only small planning inventories beside this script; never changes inputs.
The benchmark is a separate, explicitly bounded script.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import subprocess

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FILES = [
    "data/public/songs.csv",
    "data/public/master_monthly.csv",
    "data/public/master_weekly.csv.xz",
    "data/preprocessing/monthly.csv",
    "data/preprocessing/monthly_no_duplicates.csv",
    "data/preprocessing/monthly_lyrics_available.csv",
    "data/preprocessing/weekly.csv.xz",
    "data/preprocessing/weekly_no_duplicates.csv",
]
SCORES = (
    ["ll_" + x for x in ("sexual_content", "violence", "explicit_language", "substance_use")]
    + ["detox_" + x for x in ("toxicity", "severe_toxicity", "obscene", "threat",
                              "insult", "identity_attack", "sexual_explicit")]
    + ["emotion_" + x for x in (
        "admiration amusement anger annoyance approval caring confusion curiosity desire "
        "disappointment disapproval disgust embarrassment excitement fear gratitude grief "
        "joy love nervousness optimism pride realization relief remorse sadness surprise neutral"
    ).split()]
    + ["sentiment_negative", "sentiment_neutral", "sentiment_positive"]
)
SENTIMENT = SCORES[-3:]
DURATIONS = ["mb_duration_" + x + "_seconds" for x in ("median", "min", "max")]
MB_COUNTS = ["mb_recording_count", "mb_release_count", "mb_distinct_duration_count"]
HISTORY_COUNTS = ["weekly_observation_count", "chart_weeks", "total_chart_points",
                  "snapshot_months_selected"]
DATES = ["first_chart_date", "last_chart_date", "first_snapshot_month", "last_snapshot_month"]
GENRES = ["primary_genre", "secondary_genres"]
DIAGNOSTIC = ["musicbrainz_match_status", "mb_release_date_precision",
              "lyrics_status", "lyrics_available", "genre_confidence"]
NUMERIC = SCORES + DURATIONS + MB_COUNTS + HISTORY_COUNTS + DATES + [
    "mb_release_year", "best_chart_rank"
]
SONG_POOL = NUMERIC + GENRES
FINAL_HISTORY = HISTORY_COUNTS + [
    "best_chart_rank", "last_chart_date", "first_snapshot_month", "last_snapshot_month"
]
MB_FIELDS = DURATIONS + MB_COUNTS + ["mb_release_year"]
GENRE_TAXONOMY = [
    "Pop", "Rock", "Hip-Hop / Rap", "R&B / Soul", "Country", "Latin",
    "Electronic / Dance", "Alternative / Indie", "Metal", "Folk / Singer-Songwriter",
    "Jazz / Blues", "Reggae / Dancehall", "Gospel / Christian", "K-Pop",
    "Afrobeats / African Pop", "Other",
]
GLOBAL_EXCLUSIONS = {
    "song_id": "Exact identity/group key; no numerical or categorical model input.",
    "title": "High-cardinality identity text; no validated content encoding in this scalar search.",
    "artist": "High-cardinality exact artist-credit identity; not an arbitrary numeric code. New-artist analysis requires a separately approved representation.",
    "mb_release_title": "High-cardinality linked-release identity; not an album measurement.",
    "source_chart_index": "Source coordinate; arbitrary order and row leakage.",
    "source_row_index": "Source coordinate; effectively exposes chart ordering/rank.",
    "month": "Monthly date alias; use snapshot_chart_date once, not both encodings.",
    "mb_earliest_release_date": "Partial dates represented once as mb_release_year; never invent month/day.",
    "in_final_study_population": "Bookkeeping/selection indicator; constant in songs/monthly, structural enrichment scope in weekly.",
    "musicbrainz_match_status": "Acquisition bookkeeping; diagnostic target only, never substantive predictor.",
    "mb_release_date_precision": "Acquisition precision bookkeeping; diagnostic target only.",
    "lyrics_status": "Acquisition bookkeeping and direct proxy for score availability; diagnostic target only.",
    "lyrics_available": "Acquisition bookkeeping and deterministic proxy for missing scores; diagnostic target only.",
    "genre_confidence": "Qualitative annotation confidence, not musical content; diagnostic target only.",
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_csv(name, rows):
    if not rows:
        raise ValueError("Empty inventory: " + name)
    with (OUT / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_table(rel):
    # Literal 'NA' in an exact title/artist must survive. readr's NA token applies
    # to other preprocessing fields; public release uses blank only.
    d = pd.read_csv(ROOT / rel, keep_default_na=False, na_values=[""], low_memory=False)
    if rel.startswith("data/preprocessing/"):
        cols = [c for c in d if c not in ("title", "artist")]
        d[cols] = d[cols].replace("NA", np.nan)
        for c in set(cols) & set(SCORES + HISTORY_COUNTS + ["reported_peak_position",
                 "reported_weeks_on_chart", "best_chart_rank", "lyrics_available",
                 "mb_earliest_release_date", "in_final_study_population"]):
            d[c] = pd.to_numeric(d[c], errors="raise")
    return d


def family(c, pre=False):
    if c in SCORES:
        return "binary" if pre and c.startswith("ll_") else "continuous"
    if c in DURATIONS:
        return "continuous"
    if c in MB_COUNTS:
        return "bookkeeping_count"
    if c in HISTORY_COUNTS or c == "reported_weeks_on_chart":
        return "derived_outcome_count" if c in HISTORY_COUNTS else "count"
    if c in ["best_chart_rank", "weekly_rank", "monthly_rank",
             "reported_last_week_rank", "reported_peak_position"]:
        return "ordinal"
    if c in ["song_id", "title", "artist", "mb_release_title", "source_chart_index", "source_row_index"]:
        return "identifier"
    if c in DATES:
        return "derived_outcome_temporal"
    if c in ["chart_date", "snapshot_chart_date", "month"]:
        return "bookkeeping_temporal"
    if c in ["lyrics_available", "in_final_study_population"]:
        return "binary_bookkeeping"
    if c == "genre_confidence":
        return "ordinal_bookkeeping"
    if c == "secondary_genres":
        return "categorical_multilabel"
    if c in GENRES:
        return "categorical"
    if c in DIAGNOSTIC:
        return "categorical_bookkeeping"
    if c == "mb_earliest_release_date":
        return "temporal_metadata"
    raise ValueError("Unclassified new column " + c)


def provenance(c):
    if c in SCORES:
        group = ("lyriclens" if c.startswith("ll_") else "detoxify" if c.startswith("detox_")
                 else "goemotions" if c.startswith("emotion_") else "cardiff")
        return "Frozen " + group + "; docs/classifier_production_schema.json; src/public_classifier_features.py"
    if c.startswith("mb_") or c == "musicbrainz_match_status":
        return "Accepted MusicBrainz links; src/public_dataset.py:metadata_summaries"
    if c in GENRES + ["genre_confidence"]:
        return "Frozen genre model; src/genre_production.py; docs/genre/production.md (not the older rule-based pilot)"
    if c.startswith("lyrics_"):
        return "Private acquisition disposition exported by src/final_dataset.py"
    return "Reported Billboard snapshot; src/final_dataset.py; data/public/manifest.json"


def availability(c):
    if c in SCORES:
        return "After usable lyrics and frozen inference; historical as-of availability not recorded in public tables."
    if c in GENRES + ["genre_confidence"]:
        return "After frozen genre assignment; historical as-of availability not established."
    if c.startswith("mb_") or c == "musicbrainz_match_status":
        return "After metadata lookup/acceptance; later recordings/releases/reissues may be included; no historical as-of guarantee."
    if c.startswith("lyrics_"):
        return "After acquisition attempt, not a release-time song attribute."
    if c in FINAL_HISTORY:
        return "After the observed career/snapshot history through 2026-09-19; unavailable at earlier prediction origins."
    if c == "first_chart_date":
        return "At first chart appearance; history is left-truncated at 1958-08-04."
    if c == "reported_last_week_rank":
        return "Refers to prior chart, exported on current chart; missing on debut/re-entry, verify source chronology before forecasting."
    if c in ("weekly_rank", "monthly_rank", "reported_peak_position", "reported_weeks_on_chart"):
        return "Current chart publication; peak/weeks include current observation, not a prior-origin measurement."
    return "Identity or sampling/bookkeeping coordinate; not a substantive forecasting feature."


def convert(frame):
    d = frame.copy()
    d["mb_release_year"] = pd.to_numeric(
        d.mb_earliest_release_date.astype("string").str[:4], errors="raise"
    ).astype(float)
    for c in DATES + [x for x in ("chart_date", "snapshot_chart_date") if x in d]:
        if "snapshot_month" in c:
            dt = pd.to_datetime(d[c], format="%Y-%m")
            d[c] = (dt.dt.year - 1970) * 12 + dt.dt.month - 1
        else:
            d[c] = (pd.to_datetime(d[c]) - pd.Timestamp("1970-01-01")).dt.days.astype(float)
    return d


def split_labels(frame, train_end="2010-01-01", test_start="2018-01-01"):
    # Entire songs, including lifetime label windows, must fit in a block.
    first, last = frame.first_chart_date, frame.last_chart_date
    return pd.Series(np.select(
        [(first < train_end) & (last < train_end),
         (first >= train_end) & (last < test_start),
         first >= test_start],
        ["train", "validation", "test"], default="purged_boundary_song"
    ), index=frame.index)


def forbidden_sets(target, predictors):
    present = set(predictors)
    if target in SENTIMENT:
        other = set(SENTIMENT) - {target}
        return [sorted(other)] if other <= present else []
    return [list(SENTIMENT)] if set(SENTIMENT) <= present else []


def allowed(combo, forbidden):
    return not any(set(b) <= set(combo) for b in forbidden)


def count_combinations(predictors, forbidden, k):
    """Inclusion-exclusion, not a heuristic and not enumeration of fitted models."""
    n = len(predictors)
    value = math.comb(n, k) if k <= n else 0
    for r in range(1, len(forbidden) + 1):
        for groups in itertools.combinations(forbidden, r):
            union = set().union(*map(set, groups))
            u = len(union)
            if u <= k:
                value += (-1) ** r * math.comb(n - u, k - u)
    return value


def target_family(c):
    if c in ["primary_genre", "musicbrainz_match_status", "mb_release_date_precision", "lyrics_status"]:
        return "multiclass"
    if c == "secondary_genres":
        return "multilabel"
    if c == "lyrics_available":
        return "binary"
    if c == "genre_confidence":
        return "ordinal_diagnostic"
    if c in ["best_chart_rank", "weekly_rank", "monthly_rank",
             "reported_last_week_rank", "reported_peak_position"]:
        return "ordinal_rank"
    return "regression"


def candidate_plan(table, target):
    pool = list(SONG_POOL)
    excluded = dict(GLOBAL_EXCLUSIONS)
    if table != "songs":
        current = "monthly_rank" if table == "monthly" else "weekly_rank"
        date = "snapshot_chart_date" if table == "monthly" else "chart_date"
        pool += [current, date, "reported_last_week_rank", "reported_peak_position",
                 "reported_weeks_on_chart"]
        for c in FINAL_HISTORY:
            excluded[c] = "Whole-history or month-end membership information includes events after this chart target."
        if target == "reported_last_week_rank":
            for c in [current, "reported_peak_position", "reported_weeks_on_chart", "first_chart_date"]:
                excluded[c] = "Current-chart information is later than the previous-week target; even debut identity timing may be later."
        elif target == current:
            excluded["reported_peak_position"] = "Current reported peak can incorporate the target rank; target-derived information."
        # Current rank is a legitimate input to current cumulative peak/weeks in
        # retrospective chart-state explanation; it is not called a forecast.
    if target in ["lyrics_status", "lyrics_available"]:
        for c in SCORES:
            excluded[c] = "Scores and their missingness are generated conditional on successful acquisition; reveal this diagnostic target."
    if target in ["musicbrainz_match_status", "mb_release_date_precision"]:
        for c in MB_FIELDS:
            excluded[c] = "Accepted-link metadata values/missingness arise from the match/precision process being predicted."
    if target == "first_chart_date":
        for c in GENRES:
            excluded[c] = "Genre production explicitly receives first_chart_date as input; downstream annotation leaks the date target."
        for c in MB_FIELDS:
            excluded[c] = "MusicBrainz acceptance uses first_chart_date for temporal anchoring; selected metadata and missingness are conditioned on the date target."
    if target in GENRES:
        other = next(x for x in GENRES if x != target)
        excluded[other] = "Secondary label construction explicitly excludes the primary label; structural target information, not ordinary correlation."
    excluded[target] = "Target itself."
    predictors = sorted(c for c in pool if c not in excluded)
    assert len(predictors) == len(set(predictors))
    forbidden = forbidden_sets(target, predictors)
    for c in set(SONG_POOL + DIAGNOSTIC) - set(pool):
        excluded.setdefault(c, "Not a field at this analysis unit.")
    return dict(
        task_id=table + ":" + target, table=table, target=target,
        model_family=target_family(target), scope="retrospective_frozen_release",
        predictors=predictors, excluded_predictors=excluded,
        forbidden_subsets=forbidden,
        forbidden_reason="Sentiment softmax composition: other two reconstruct a sentiment target; all three are affine redundant with an intercept.",
        all_subsets_rule="Every unordered subset of predictors of size 1..4 that contains no forbidden_subset; no correlation or univariate screening.",
        forecast_status="Not historically as-of certified. Requires new availability audit and a separately frozen forecast specification.",
        same_model_predictors_retained=True,
    )


def target_specs():
    specs = [candidate_plan("songs", c) for c in SONG_POOL + DIAGNOSTIC]
    for table, rank in [("monthly", "monthly_rank"), ("weekly", "weekly_rank")]:
        specs += [candidate_plan(table, c) for c in [
            rank, "reported_last_week_rank", "reported_peak_position", "reported_weeks_on_chart"
        ]]
    return specs


def encoded_width(c):
    # Fixed-schema upper bound: numeric value + missing indicator.
    return 16 if c == "primary_genre" else 17 if c == "secondary_genres" else 2


def schema_inventory(rel, d):
    rows, categories = [], []
    pre = rel.startswith("data/preprocessing/")
    for c in d:
        s = d[c]
        nonnull = s.dropna()
        numeric = pd.api.types.is_numeric_dtype(s)
        typ = family(c, pre)
        rows.append(dict(
            table=rel, field=c, storage_dtype=str(s.dtype), semantic_class=typ,
            n_rows=len(d), non_missing_n=len(nonnull), missing_n=int(s.isna().sum()),
            missing_pct=float(100 * s.isna().mean()), unique_nonmissing=int(s.nunique()),
            minimum=str(nonnull.min()) if len(nonnull) else "",
            maximum=str(nonnull.max()) if len(nonnull) else "",
            variance=float(nonnull.var()) if numeric and len(nonnull) > 1 else "",
            availability_timing=availability(c),
            provenance=provenance(c) + ("; transformed by data/preprocessing/preprocessing.Rmd" if pre else ""),
            preprocessing_change=(
                "Threshold > 0.5; information lost" if pre and c.startswith("ll_")
                else "Year only" if pre and c == "mb_earliest_release_date"
                else "Afrobeats -> Other; low-confidence rows removed (monthly) or labels masked (weekly)"
                if pre and c in GENRES else ""
            ),
            candidate_disposition=GLOBAL_EXCLUSIONS.get(c, "Considered with target-specific restrictions"),
        ))
        if typ.startswith(("categorical", "binary", "ordinal_bookkeeping")) or c == "mb_release_date_precision":
            for value, n in s.fillna("<MISSING>").value_counts(dropna=False).items():
                categories.append(dict(table=rel, field=c, value=str(value), n=int(n)))
    return rows, categories


def main():
    initial = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    protected = {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / "data").rglob("*"))
                 if p.is_file() and ".git" not in p.parts}
    data, schema, categories, tables = {}, [], [], []
    for rel in FILES:
        d = read_table(rel)
        rows, cats = schema_inventory(rel, d)
        schema.extend(rows)
        categories.extend(cats)
        n_songs = d.song_id.nunique() if "song_id" in d else d[["title", "artist"]].drop_duplicates().shape[0]
        tables.append(dict(path=rel, rows=len(d), columns=len(d.columns),
            unique_exact_identities=int(n_songs), has_song_id="song_id" in d,
            duplicate_identity_rows=len(d)-int(n_songs), bytes=(ROOT/rel).stat().st_size,
            sha256=sha(ROOT/rel), deep_frame_bytes=int(d.memory_usage(deep=True).sum())))
        if rel.startswith("data/public/"):
            key = "songs" if rel.endswith("songs.csv") else "monthly" if "monthly" in rel else "weekly"
            data[key] = d
        print("Inventoried", rel, d.shape, flush=True)
    # All public identity repetitions must be truly invariant before pooling.
    s = data["songs"].set_index("song_id")
    for name in ("monthly", "weekly"):
        d = data[name]
        shared = d[d.song_id.isin(s.index)]
        for c in s:
            original, repeated = s[c].reindex(shared.song_id), shared[c]
            equal = (original.fillna("<MISSING>").to_numpy() == repeated.fillna("<MISSING>").to_numpy())
            if not equal.all():
                raise ValueError("Non-invariant public song attribute: " + name + ":" + c)

    converted = {name: convert(d) for name, d in data.items()}
    splits = {name: split_labels(d) for name, d in data.items()}
    specs = target_specs()
    targets, counts, split_rows, split_categories = [], [], [], []
    for spec in specs:
        name, target = spec["table"], spec["target"]
        d, raw, labels = converted[name], data[name], splits[name]
        observed = d[target].notna()
        pred = spec["predictors"]
        complete = observed & d[pred].notna().all(axis=1)
        series = d.loc[observed, target]
        targets.append(dict(
            task_id=spec["task_id"], table=name, target=target,
            source_field="mb_earliest_release_date" if target == "mb_release_year" else target,
            model_family=spec["model_family"], eligible=True,
            role="acquisition_diagnostic" if target in DIAGNOSTIC + MB_COUNTS else "measurement",
            n_rows=len(d), observed_target_rows=int(observed.sum()),
            observed_target_songs=int(raw.loc[observed, "song_id"].nunique()),
            missing_target_pct=float(100*(~observed).mean()),
            distinct_observed_values=int(series.nunique()),
            modal_value_share=float(series.value_counts().iloc[0]/len(series)),
            standard_deviation=float(series.std()) if pd.api.types.is_numeric_dtype(series) else "",
            smallest_observed_class_n=int(series.value_counts().min()) if spec["model_family"] != "regression" else "",
            severe_missingness_gt_50pct=bool((~observed).mean() > .5),
            insufficient_global_variation=bool(series.nunique() < 2),
            full_universe_complete_rows=int(complete.sum()),
            full_universe_complete_songs=int(raw.loc[complete, "song_id"].nunique()),
            target_encoding=("calendar year only; not true original release year" if target == "mb_release_year"
                             else "month index since 1970-01" if target in ["first_snapshot_month", "last_snapshot_month"]
                             else "days since 1970-01-01" if target in DATES
                             else "JSON multilabel set" if target == "secondary_genres" else "original values"),
        ))
        count = dict(task_id=spec["task_id"], model_family=spec["model_family"],
                     conceptual_predictors=len(pred))
        for k in range(1, 5):
            count["k" + str(k)] = count_combinations(pred, spec["forbidden_subsets"], k)
        count["total"] = sum(count["k"+str(k)] for k in range(1, 5))
        widths = sorted(map(encoded_width, pred), reverse=True)
        count["max_encoded_coefficients_including_intercept"] = 1 + sum(widths[:4])
        count["full_cached_matrix_columns_including_intercept"] = 1 + sum(widths)
        count["full_cached_matrix_float64_bytes_observed_target"] = int(observed.sum()) * 8 * (1 + sum(widths))
        counts.append(count)
        for block in ["train", "validation", "test", "purged_boundary_song"]:
            mask = observed & labels.eq(block)
            w = raw.loc[mask, "song_id"].value_counts()
            split_rows.append(dict(
                task_id=spec["task_id"], split=block, observed_target_rows=int(mask.sum()),
                unique_songs=int(len(w)), complete_universe_rows=int((complete & mask).sum()),
                observed_target_unique_values=int(d.loc[mask, target].nunique()),
                full_dependence_cluster_ess=float(w.sum()**2/(w*w).sum()) if len(w) else 0.0,
                first_chart_min=str(raw.loc[mask, "first_chart_date"].min()) if mask.any() else "",
                last_chart_max=str(raw.loc[mask, "last_chart_date"].max()) if mask.any() else "",
            ))
            if spec["model_family"] in ("binary", "multiclass", "multilabel", "ordinal_diagnostic"):
                if target == "secondary_genres":
                    parsed = d.loc[mask, target].map(lambda x: set(json.loads(x)))
                    values = {c:int(parsed.map(lambda x: c in x).sum()) for c in GENRE_TAXONOMY}
                else:
                    values = {str(c):int(d.loc[mask, target].eq(c).sum()) for c in sorted(series.unique(), key=str)}
                split_categories.extend(dict(task_id=spec["task_id"], split=block,
                    category=c, positive_rows=n, denominator=int(mask.sum()),
                    fewer_than_30=bool(n<30)) for c,n in values.items())
    song = data["songs"]
    weekly = data["weekly"]
    monthly = data["monthly"]
    sentiment_error = (song[SENTIMENT].sum(axis=1, min_count=3)-1).abs()
    findings = {
        "monthly_preprocessing_three_files_byte_identical": len({
            sha(ROOT / f"data/preprocessing/{x}.csv")
            for x in ["monthly", "monthly_no_duplicates", "monthly_lyrics_available"]
        }) == 1,
        "monthly_preprocessing_rows_without_lyrics": int((read_table(FILES[3]).lyrics_available == 0).sum()),
        "monthly_preprocessing_expected_deduplicated_songs": int(song.genre_confidence.ne("low").sum()),
        "monthly_preprocessing_expected_deduplicated_with_lyrics": int(
            (song.genre_confidence.ne("low") & song.lyrics_available.eq(1)).sum()),
        "song_week_count_vs_row_count_different_songs": int((song.weekly_observation_count != song.chart_weeks).sum()),
        "weekly_duplicate_song_dates_extra_rows": int(weekly.duplicated(["song_id","chart_date"]).sum()),
        "monthly_duplicate_song_dates_extra_rows": int(monthly.duplicated(["song_id","snapshot_chart_date"]).sum()),
        "sentiment_sum_max_abs_error": float(sentiment_error.max()),
        "goemotion_sum_min_max": [float(x) for x in (
            song[[c for c in SCORES if c.startswith("emotion_")]].sum(axis=1, min_count=28).min(),
            song[[c for c in SCORES if c.startswith("emotion_")]].sum(axis=1, min_count=28).max())],
        "duration_min_median_max_all_equal_songs": int(
            (song[DURATIONS].nunique(axis=1) == 1).sum()),
        "mb_duration_max_over_one_hour_songs": int((song.mb_duration_max_seconds > 3600).sum()),
        "release_year_after_first_chart_year_songs": int((
            converted["songs"].mb_release_year > song.first_chart_date.str[:4].astype(int)).sum()),
        "weekly_outside_final_population_rows": int(weekly.in_final_study_population.eq(0).sum()),
        "weekly_outside_final_population_songs": int(weekly.loc[weekly.in_final_study_population.eq(0),"song_id"].nunique()),
        "all_42_available_songs": int(song[SCORES].notna().all(axis=1).sum()),
        "primary_genre_counts": {str(k):int(v) for k,v in song.primary_genre.value_counts().items()},
        "split_row_counts": {name: {str(k): int(v) for k,v in labels.value_counts().items()} for name,labels in splits.items()},
        "split_unique_song_counts": {
            name:{block:int(data[name].loc[labels.eq(block),"song_id"].nunique())
                  for block in sorted(labels.unique())} for name,labels in splits.items()
        },
        "test_use": "Schema/coverage audit only; no benchmark fitting, prediction, scoring, or selection on test rows.",
    }
    catalog = {
        "version": "proposal-v1-unapproved",
        "song_candidate_pool": SONG_POOL,
        "raw_fields_excluded_globally": GLOBAL_EXCLUSIONS,
        "non_target_coordinates": {
            c: "Sampling/observation coordinate, not a song response; chart dates can be predictors at that resolution."
            for c in ["chart_date", "snapshot_chart_date", "month", "source_chart_index", "source_row_index"]
        },
        "non_target_identifiers": {c: GLOBAL_EXCLUSIONS[c] for c in ["song_id","title","artist","mb_release_title"]},
        "non_target_population_flag": GLOBAL_EXCLUSIONS["in_final_study_population"],
        "date_representations": {
            **{c: "day offset from 1970-01-01" for c in ["first_chart_date","last_chart_date","chart_date","snapshot_chart_date"]},
            **{c: "month offset from 1970-01" for c in ["first_snapshot_month","last_snapshot_month"]},
            "mb_earliest_release_date": "mb_release_year: first four characters; no invented day/month",
        },
        "numeric_encoding": "Float64 value, train median imputation and one fixed missing indicator per original variable; train-only scaling; constant encoded columns removed per fold.",
        "primary_genre_encoding": "16 fixed taxonomy levels; 15 contrasts with Pop reference plus missing indicator; train-absent columns have zero coefficient; no merging labels.",
        "secondary_genres_encoding": "16 multi-hot indicators plus missing indicator; [] is an observed empty set, never missing; one conceptual variable.",
        "genre_taxonomy": GENRE_TAXONOMY,
        "max_conceptual_predictors": 4,
        "estimator_instances": "Counts describe distinct target/predictor specifications, not folds, OLS/Ridge duplication, alpha grids or multilabel output heads.",
    }
    totals = {
        "all_tasks": len(counts),
        "all_target_predictor_specifications": sum(c["total"] for c in counts),
        "by_k": {str(k):sum(c["k"+str(k)] for c in counts) for k in range(1,5)},
        "by_family": {},
    }
    for f in sorted({c["model_family"] for c in counts}):
        rows = [c for c in counts if c["model_family"] == f]
        totals["by_family"][f] = dict(
            tasks=len(rows), total=sum(c["total"] for c in rows),
            **{"k"+str(k):sum(c["k"+str(k)] for c in rows) for k in range(1,5)}
        )
    assert protected == {rel:sha(ROOT/rel) for rel in protected}, "Input modified during audit"
    write_json("dataset_inventory.json", tables)
    write_csv("schema_inventory.csv", schema)
    write_csv("category_counts.csv", categories)
    write_json("variable_catalog.json", catalog)
    write_json("predictor_sets.json", specs)
    write_csv("target_inventory.csv", targets)
    write_csv("search_counts.csv", counts)
    write_csv("split_summary.csv", split_rows)
    write_csv("target_category_split_counts.csv", split_categories)
    write_json("data_findings.json", findings)
    write_json("search_totals.json", totals)
    manifest = {
        "audited_head": initial,
        "origin_main_at_audit": subprocess.check_output(["git","rev-parse","origin/main"],cwd=ROOT,text=True).strip(),
        "repository": "https://github.com/Jamster187/cmpt491-music-censorship",
        "sync": "No checkout initially; fresh clone followed by git fetch origin; clean main; 0/0 ahead/behind; merge --ff-only already up to date.",
        "recent_commits": subprocess.check_output(["git","log","-8","--format=%H %aI %an %s"],cwd=ROOT,text=True).splitlines(),
        "runtime": dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
        "input_hashes": protected,
        "audit_script_sha256": sha(Path(__file__)),
        "full_campaign_run": False,
    }
    write_json("audit_manifest.json", manifest)
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
