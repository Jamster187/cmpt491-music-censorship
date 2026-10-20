"""CLI for audit, bounded pilot, resumable exhaustive OLS, rankings and final refits."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import csv
from functools import lru_cache
import gc
import gzip
import itertools
import json
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import time

import numpy as np
import pandas as pd
import scipy
from threadpoolctl import threadpool_limits

import regression_core as core
import regression_spec as spec
from regression_store import Store, clean, write_json

PUBLIC = spec.ROOT / "analysis/regression_search"
LOCAL = spec.ROOT / "data/experiments/regression_search"
CODE = ["src/regression_spec.py", "src/regression_core.py", "src/regression_store.py",
        "src/regression_search.py", "src/regression_pilot.py", "analysis/planning/regression_search/audit.py"]


def provenance():
    return dict(code_sha256={p: spec.original.sha(spec.ROOT/p) for p in CODE},
        python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
        scipy=scipy.__version__, sqlite=sqlite3.sqlite_version,
        git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=spec.ROOT, text=True).strip())


@lru_cache(maxsize=1)
def read_table(table):
    raw = spec.original.read_table(spec.FILES[table])
    if table == "songs" and raw.song_id.duplicated().any():
        raise ValueError("Duplicate song identity in song table")
    return raw


def task_path(folder, task):
    return Path(folder)/task["task_id"].replace(":", "__")


def identity(task, candidates, config):
    version = provenance()
    version.pop("git_head")  # An unchanged code tree can resume after its commit.
    return dict(task=task, config=config, versions=version,
        data_sha256=spec.original.sha(spec.ROOT/spec.FILES[task["table"]]),
        candidate_sha256=spec.digest(candidates), candidate_count=len(candidates))


def write_csv(path, rows):
    rows = iter(rows)
    first = next(rows, None)
    if first is None:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(first), lineterminator="\n")
        writer.writeheader()
        for row in itertools.chain([first], rows):
            writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                             for k, v in clean(row).items()})


def audit():
    """Recount from current data, independently of the historical saved totals."""
    dest = PUBLIC/"specification"
    before = {p: spec.original.sha(spec.ROOT/p) for p in spec.original.FILES}
    datasets, targets, counts, splits = [], [], [], []
    plans = spec.specs()
    for table, rel in spec.FILES.items():
        raw = read_table(table)
        # Fail on new unclassified fields rather than silently excluding them.
        for c in raw:
            spec.original.family(c)
        converted = spec.original.convert(raw)
        datasets.append(dict(table=table, path=rel, rows=len(raw), columns=len(raw.columns),
            songs=int(raw.song_id.nunique()), sha256=before[rel],
            fields={c: dict(dtype=str(raw[c].dtype), missing=int(raw[c].isna().sum())) for c in raw}))
        for task in [s for s in plans if s["table"] == table]:
            y = converted[task["target"]]
            targets.append(dict(task_id=task["task_id"], target=task["target"], table=table,
                family=task["model_family"], status=task["campaign_status"],
                observed_rows=int(y.notna().sum()), missing_rows=int(y.isna().sum()),
                unique_values=int(y.nunique()), predictors=len(task["predictors"])))
            row = dict(task_id=task["task_id"], family=task["model_family"],
                predictors=len(task["predictors"]), **{"k"+str(k): spec.count(task, k) for k in (1, 2, 3)})
            row["total"] = sum(row["k"+str(k)] for k in (1, 2, 3))
            row["previous_k4"] = spec.count(task, 4)  # Arithmetic only, never four-variable fits.
            counts.append(row)
            for index, (start, end) in enumerate(spec.FOLDS + [("2018-01-01", None)]):
                tr, va = core.partition(raw, start, end)
                observed = y.notna()
                splits.append(dict(task_id=task["task_id"], fold=index, start=start, end=end,
                    n_train=int((tr & observed).sum()), n_validation=int((va & observed).sum()),
                    train_songs=int(raw.loc[tr & observed, "song_id"].nunique()),
                    validation_songs=int(raw.loc[va & observed, "song_id"].nunique())))
    families = {}
    for family in sorted({r["family"] for r in counts}):
        members = [r for r in counts if r["family"] == family]
        families[family] = dict(targets=len(members), **{k: sum(r[k] for r in members)
            for k in ("k1", "k2", "k3", "total", "previous_k4")})
    regression = families["regression"]
    regression["previous_total"] = regression["total"] + regression["previous_k4"]
    regression["reduction_pct"] = 100*regression["previous_k4"]/regression["previous_total"]
    totals = dict(numerical_targets=regression["targets"],
        separate_categorical_ordinal_targets=len(targets)-regression["targets"], by_family=families,
        full_campaign_run=False, current_data_hashes=before, provenance=provenance())
    songs = read_table("songs")
    censoring = []
    cutoff = pd.Timestamp("2026-09-19")
    for decade, group in songs.groupby(songs.first_chart_date.str[:3]+"0s"):
        followup = (cutoff-pd.to_datetime(group.first_chart_date)).dt.days
        censoring.append(dict(debut_decade=decade, songs=len(group),
            median_possible_followup_days=float(followup.median()),
            under_two_years_followup=int(followup.lt(731).sum()),
            last_seen_within_90_days=int(pd.to_datetime(group.last_chart_date).ge(cutoff-pd.Timedelta(days=90)).sum())))
    assert before == {p: spec.original.sha(spec.ROOT/p) for p in before}
    write_json(dest/"datasets.json", datasets)
    write_json(dest/"predictor_eligibility.json", plans)
    write_json(dest/"model_specification.json", spec.configuration())
    write_json(dest/"search_totals.json", totals)
    write_json(dest/"censoring_audit.json", dict(cutoff=str(cutoff.date()), cohorts=censoring,
        interpretation="Observed-through-snapshot histories, not uncensored lifetime outcomes; purging also selects against recurrent songs."))
    write_csv(dest/"target_inventory.csv", targets)
    write_csv(dest/"search_counts.csv", counts)
    write_csv(dest/"split_support.csv", splits)
    # Native families have no approved estimator, so show explicit status, never
    # invent classification metrics or quietly run OLS on category/rank codes.
    write_csv(dest/"categorical_ordinal_tasks.csv", [dict(task_id=t["task_id"], family=t["model_family"],
        status="not_run_requires_native_model_specification", appropriate_metrics=(
            "ranked probability score; ordinal log loss; rank MAE" if t["model_family"].startswith("ordinal") else
            "macro/micro F1; per-label PR-AUC; log loss" if t["model_family"] == "multilabel" else
            "log loss; balanced accuracy; macro F1; Brier/PR-AUC for binary"))
        for t in plans if t["model_family"] != "regression"])
    print(json.dumps(regression, indent=2), flush=True)
    return totals


def run_task(task, folder, config, candidates=None, batch_size=256, check=False, stop_batches=None):
    if task["model_family"] != "regression":
        raise ValueError("This engine accepts numerical OLS tasks only")
    candidates = candidates if candidates is not None else list(enumerate(spec.combinations(task)))
    if any(not 1 <= len(c) <= 3 or not set(c) <= set(task["predictors"]) or
           not spec.original.allowed(c, task["forbidden_subsets"]) for _, c in candidates):
        raise ValueError("Invalid candidate specification")
    ident = identity(task, candidates, config)
    dest = task_path(folder, task)
    raw = read_table(task["table"])
    # Final test data never reach any selection/preprocessing operation.
    selection_raw = raw.loc[raw.last_chart_date.lt(config["test_start"]) & raw.first_chart_date.lt(config["test_start"])]
    started = time.perf_counter()
    batches = 0
    checks = []
    init_start = time.perf_counter()
    with Store(dest/"results.sqlite", ident, candidates, task["predictors"]) as store:
        initialization_seconds = time.perf_counter()-init_start
        write_json(dest/"specification.json", dict(identity=ident, provenance=provenance()))
        if store.complete():
            return dict(task_id=task["task_id"], already_complete=True, completed_combinations=len(candidates))
        for f, (start, end) in enumerate(config["folds"]):
            completed = store.completed(f)
            pending = [(i, c) for i, c in candidates if i not in completed]
            if not pending:
                continue
            prep = time.perf_counter()
            fold = core.prepare(selection_raw, task, start, end)
            fold.metadata["preprocessing_seconds_including_cache"] = time.perf_counter()-prep
            # Save exact song/row membership, independent of CSV parsing order.
            write_csv(dest/("split_"+str(f)+".csv.gz"), itertools.chain(
                (dict(source_row=int(i), song_id=s, partition="train") for i, s in fold.train.song_id.items()),
                (dict(source_row=int(i), song_id=s, partition="validation") for i, s in fold.validation.song_id.items())))
            if check:
                for k in (1, 2, 3):
                    for group in ("numeric", "primary", "secondary", "both"):
                        chosen = [c for _, c in candidates if len(c) == k and spec.stratum(c) == group]
                        if chosen:
                            checks.append(dict(task_id=task["task_id"], fold=f, **fold.reference_check(chosen[0])))
            grouped = defaultdict(list)
            for item in pending:
                grouped[(len(item[1]), spec.stratum(item[1]))].append(item)
            for (k, group), items in sorted(grouped.items()):
                loop_seconds = 0.
                for start_index in range(0, len(items), batch_size):
                    loop_start = time.perf_counter()
                    batch = items[start_index:start_index+batch_size]
                    result, timing = fold.evaluate([c for _, c in batch])
                    key = "stratum_"+str(f)+"_"+str(k)+"_"+group
                    store.save(f, batch, result, fold.metadata, timing, key,
                        dict(fold=f, k=k, stratum=group, n_validation=fold.metadata["n_validation"]))
                    loop_seconds += time.perf_counter()-loop_start
                    batches += 1
                    if stop_batches is not None and batches >= stop_batches:
                        return dict(task_id=task["task_id"], interrupted_after_batches=batches)
                with store.db:
                    timed = store.get(key)
                    timed["loop_seconds_including_checkpoint"] = timed.get("loop_seconds_including_checkpoint", 0.) + loop_seconds
                    store.put(key, timed)
            del fold
            gc.collect()
            print(task["task_id"], "validation period", f+1, "complete", flush=True)
        if not store.complete():
            raise AssertionError("Incomplete exhaustive coverage")
        ranking_start = time.perf_counter()
        winner = next(store.rows(limit=1))
        if winner["validation_skill"] is None:
            raise ValueError("No defined aggregate validation skill; inspect zero-variance/support diagnostics")
        best = [next(store.rows(k=k, limit=1)) for k in (1, 2, 3)]
        write_json(dest/"selection.json", dict(task_id=task["task_id"], identity_sha256=spec.digest(ident),
            candidate_count=len(candidates), winner=winner, best_by_k=best,
            historical_stability=store.stability(winner["id"]),
            selection_rule=config["selection"], final_test_used=False))
        elapsed = time.perf_counter()-started
        report = dict(task_id=task["task_id"], completed_combinations=len(candidates),
            elapsed_seconds=elapsed, fitting=store.get("timing"), checks=checks,
            initialization_seconds=initialization_seconds,
            ranking_seconds=time.perf_counter()-ranking_start,
            strata=[json.loads(r[0]) for r in store.db.execute("SELECT value FROM metadata WHERE key LIKE 'stratum_%' ORDER BY key")],
            folds=[store.get("fold_"+str(i)) for i in range(3)])
        write_json(dest/"run_summary.json", report)
    if spec.original.sha(spec.ROOT/spec.FILES[task["table"]]) != ident["data_sha256"]:
        raise ValueError("Dataset changed while searching")
    return report


def bootstrap(fold, prediction, repeats=500, calendar_blocks=False):
    """Cluster bootstrap of fixed predictions, preserving equal total song weight."""
    _, first, index = np.unique(fold.validation.song_id.to_numpy(), return_index=True, return_inverse=True)
    n = np.bincount(index)
    aggregate = lambda values: np.bincount(index, weights=values)/n
    y = fold.z
    summaries = np.column_stack([aggregate(y), aggregate(y*y), aggregate((y-prediction)**2),
        aggregate(abs(y-prediction)), aggregate((y-fold.mean)**2), aggregate(abs(y-fold.median))])
    sizes = np.ones(len(summaries))
    if calendar_blocks:
        years = pd.to_datetime(fold.validation.first_chart_date, unit="D", origin="1970-01-01").dt.year.to_numpy()[first]
        _, blocks = np.unique(years//2, return_inverse=True)
        sizes = np.bincount(blocks).astype(float)
        if len(sizes) < 3:
            return dict(blocks=len(sizes), intervals=None, limitation="Fewer than three two-year debut blocks; no credible block interval")
        summaries = np.column_stack([np.bincount(blocks, weights=column) for column in summaries.T])
    rng = np.random.default_rng(spec.SEED)
    values = []
    for _ in range(repeats):
        picked = rng.integers(len(sizes), size=len(sizes))
        avg = summaries[picked].sum(axis=0)/sizes[picked].sum()
        variance = avg[1]-avg[0]**2
        values.append([1-avg[2]/variance if variance > 0 else np.nan, avg[3], avg[2]**.5,
                       1-avg[2]/avg[4] if avg[4] > 0 else np.nan])
    intervals = {name: clean(np.nanquantile(np.array(values)[:, i], [.025, .975]))
                 for i, name in enumerate(["r2", "mae", "rmse", "skill"])}
    return dict(blocks=len(sizes), intervals=intervals,
                limitation="Few calendar blocks; exploratory fixed-model interval") if calendar_blocks else intervals


def evaluate_selected(task, folder, config):
    dest = task_path(folder, task)
    selection = json.loads((dest/"selection.json").read_text())
    selected = selection["winner"]["predictors"]
    raw = read_table(task["table"])
    if config["test_end"]:
        raw = raw.loc[raw.last_chart_date.lt(config["test_end"])]
    fold = core.prepare(raw, dict(task, predictors=selected), config["test_start"], config["test_end"])
    beta, ranks, fallbacks = fold.fit_batch([selected])
    prediction = fold.V @ beta[:, 0] + fold.mean
    result = core.metrics(fold.z, prediction, fold.u, fold.mean, fold.median)
    result.update(task_id=task["task_id"], target=task["target"], predictors=selected, k=len(selected),
        n_test=len(fold.z), test_songs=int(fold.validation.song_id.nunique()), n_refit=len(fold.y),
        validation_r2=selection["winner"]["validation_r2"],
        test_minus_validation_r2=(result["r2"]-selection["winner"]["validation_r2"]) if result["r2"] is not None else None,
        validation_skill=selection["winner"]["validation_skill"],
        test_minus_validation_skill=(result["skill"]-selection["winner"]["validation_skill"]) if result["skill"] is not None else None,
        ci95=bootstrap(fold, prediction), calendar_block_ci95=bootstrap(fold, prediction, calendar_blocks=True), rank=int(ranks[0]),
        test_start=config["test_start"], test_end=config["test_end"],
        unsupported_genre_rows=fold.encoder.unsupported(fold.validation),
        interpretation=("Observed history; near-identity chart counts retained" if task["target"] in spec.original.HISTORY_COUNTS else
                        "Agreement among frozen models; not causal or independently measured labels" if task["target"] in spec.original.SCORES else
                        "Retrospective metadata or timing reconstruction; not a causal forecast"))
    cohorts = []
    # Use source ISO years for exact calendar cohort membership.
    years = raw.loc[fold.validation.index, "first_chart_date"].str[:4].astype(int)
    for start in range(int(years.min())//2*2, int(years.max())+1, 2):
        mask = years.between(start, start+1).to_numpy()
        if mask.any():
            cohorts.append(dict(debut_period=f"{start}-{start+1}", rows=int(mask.sum()),
                songs=int(fold.validation.loc[mask, "song_id"].nunique()),
                **core.metrics(fold.z[mask], prediction[mask], fold.u[mask], fold.mean, fold.median)))
    result["test_cohorts"] = cohorts
    model = dict(task=task, predictors=selected, encoder=fold.encoder.state,
        coefficients=beta[:, 0].tolist(), target_center=fold.mean,
        training_mean_baseline=fold.mean, training_median_baseline=fold.median,
        rank=int(ranks[0]), selected_before_test=True, selection_sha256=spec.digest(selection),
        provenance=provenance(), data_sha256=spec.original.sha(spec.ROOT/spec.FILES[task["table"]]))
    write_json(dest/"selected_model.json", model)
    write_json(dest/"test_metrics.json", result)
    write_csv(dest/"test_predictions.csv.gz", (dict(source_row=int(i), song_id=song, actual=float(y),
        predicted=float(p), weight=float(w)) for i, song, y, p, w in zip(
            fold.validation.index, fold.validation.song_id, fold.z, prediction, fold.u)))
    write_csv(dest/"refit_split.csv.gz", itertools.chain(
        (dict(source_row=int(i), song_id=s, partition="refit") for i, s in fold.train.song_id.items()),
        (dict(source_row=int(i), song_id=s, partition="test") for i, s in fold.validation.song_id.items())))
    write_json(dest/"final_artifacts.json", {p: spec.original.sha(dest/p) for p in
        ["selected_model.json", "test_metrics.json", "test_predictions.csv.gz", "refit_split.csv.gz"]})
    return clean(result)


def worker(args):
    with threadpool_limits(limits=1):
        return run_task(*args)


def campaign(folder, workers):
    if not 1 <= workers <= 3:
        raise ValueError("Use one to three memory-bounded workers")
    tasks = [t for t in spec.specs() if t["model_family"] == "regression"]
    args = [(task, folder, spec.configuration()) for task in tasks]
    if workers == 1:
        summaries = [worker(arg) for arg in args]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            summaries = list(pool.map(worker, args))
    write_json(Path(folder)/"search_complete.json", dict(tasks=summaries, final_test_used=False))
    print("All validation searches complete. Final evaluation requires the finalize command.")


def finalize(folder, pilot=False):
    config = spec.configuration(pilot)
    tasks = [t for t in spec.specs() if t["task_id"] in spec.PILOT_TASKS] if pilot else [
        t for t in spec.specs() if t["model_family"] == "regression"]
    selections = []
    # Validate ALL completed identities and freeze ALL winners before reading
    # any final outcomes for evaluation. Ranking final results cannot reselect.
    for task in tasks:
        candidates = spec.sample(task) if pilot else list(enumerate(spec.combinations(task)))
        ident = identity(task, candidates, config)
        dest = task_path(folder, task)
        with Store(dest/"results.sqlite", ident, candidates, task["predictors"]) as store:
            if not store.complete():
                raise ValueError("Every target search must finish before final evaluation")
            selected = json.loads((dest/"selection.json").read_text())
            if selected["identity_sha256"] != spec.digest(ident) or selected["winner"] != next(store.rows(limit=1)):
                raise ValueError("Selection lock does not match validation ranking")
            selections.append(selected)
    lock_path = Path(folder)/"frozen_selections.json"
    if lock_path.exists() and json.loads(lock_path.read_text()) != selections:
        raise ValueError("Frozen selections changed; final results cannot be retuned")
    write_json(lock_path, selections)
    leaderboard = []
    with threadpool_limits(limits=1):
        for task in tasks:
            dest = task_path(folder, task)
            if (dest/"final_artifacts.json").exists():
                hashes = json.loads((dest/"final_artifacts.json").read_text())
                if any(not (dest/p).exists() or spec.original.sha(dest/p) != h for p, h in hashes.items()):
                    raise ValueError("Final artifact integrity failure")
                result = json.loads((dest/"test_metrics.json").read_text())
            else:
                result = evaluate_selected(task, folder, config)
            leaderboard.append(result)
    leaderboard.sort(key=lambda r: (r["r2"] is None, -(r["r2"] or 0.), r["task_id"]))
    for rank, row in enumerate(leaderboard, 1):
        row["target_rank"] = rank
    write_json(Path(folder)/"target_leaderboard.json", leaderboard)
    write_csv(Path(folder)/"target_leaderboard.csv", leaderboard)
    return leaderboard


def hierarchy(folder, task_id, output, k=None, limit=None):
    task = next(t for t in spec.specs() if t["task_id"] == task_id)
    dest = task_path(folder, task)
    saved = json.loads((dest/"specification.json").read_text())["identity"]
    candidates = spec.sample(task) if saved["config"]["test_start"] == "2014-01-01" else list(enumerate(spec.combinations(task)))
    with Store(dest/"results.sqlite", identity(task, candidates, saved["config"]), candidates, task["predictors"]) as store:
        if not store.complete():
            raise ValueError("Hierarchy requires all three validation periods")
        write_csv(output, (dict(task_id=task_id, **r) for r in store.rows(k=k, limit=limit)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("audit")
    p = sub.add_parser("pilot")
    p.add_argument("--folder", type=Path, default=LOCAL/"pilot")
    p.add_argument("--benchmark-only", action="store_true")
    p = sub.add_parser("campaign")
    p.add_argument("--folder", type=Path, default=LOCAL/"campaign")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--execute-full", action="store_true", help="Explicit launch gate; obtain user approval first")
    p = sub.add_parser("finalize")
    p.add_argument("--folder", type=Path, default=LOCAL/"campaign")
    p.add_argument("--evaluate-final-test", action="store_true")
    p = sub.add_parser("hierarchy")
    p.add_argument("--folder", type=Path, default=LOCAL/"campaign")
    p.add_argument("--task", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--k", type=int, choices=[1, 2, 3])
    p.add_argument("--limit", type=int)
    p = sub.add_parser("demo")
    p.add_argument("--folder", type=Path, default=LOCAL/"pilot")
    args = parser.parse_args()
    if args.command == "audit":
        audit()
    elif args.command == "pilot":
        from regression_pilot import pilot
        pilot(args.folder, args.benchmark_only)
    elif args.command == "campaign":
        if not args.execute_full:
            parser.error("Full campaign is gated; --execute-full is required after user approval")
        campaign(args.folder, args.workers)
    elif args.command == "finalize":
        if not args.evaluate_final_test:
            parser.error("Final test evaluation requires --evaluate-final-test after validation winners are frozen")
        finalize(args.folder)
    elif args.command == "hierarchy":
        hierarchy(args.folder, args.task, args.output, args.k, args.limit)
    elif args.command == "demo":
        from regression_pilot import demo
        demo(args.folder)


if __name__ == "__main__":
    main()
