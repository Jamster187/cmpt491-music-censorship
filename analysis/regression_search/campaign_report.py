"""Read-only campaign coverage audit and publication; never selects new models."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import resource
import sqlite3
import sys
import time

import numpy as np
import pandas as pd
from scipy import linalg
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))
import regression_core as core
import regression_search as run
import regression_spec as spec
from regression_store import Store, clean, write_json
from measure_campaign import CAMPAIGN, FROZEN, protected_files, verify_frozen

PUBLIC = run.PUBLIC/"campaign"


def peak_rss_bytes():
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if platform.system()=="Darwin" else value*1024)


@contextmanager
def database(path):
    connection = sqlite3.connect("file:"+str(Path(path).resolve())+"?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def metadata(db, key):
    row = db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
    if row is None:
        raise ValueError("Missing checkpoint metadata: "+key)
    return json.loads(row[0])


def catalog_and_scores(db, task):
    """Independent exact enumeration, finite metrics, all three folds and ranks."""
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Checkpoint integrity failure")
    candidates = list(enumerate(spec.combinations(task)))
    index = {name:i for i,name in enumerate(task["predictors"])}
    expected = [(i, len(c), *([index[p] for p in c]+[None]*(3-len(c)))) for i,c in candidates]
    actual = [tuple(r) for r in db.execute("SELECT * FROM candidates ORDER BY id")]
    if actual != expected:
        raise ValueError("Missing, duplicate or incorrect eligible combinations")
    scores = np.array([tuple(r) for r in db.execute("SELECT id,fold,r2,mae,mse,skill,rank,fallback FROM scores ORDER BY id,fold")], float)
    n = len(candidates)
    if scores.shape != (3*n, 8):
        raise ValueError("Incomplete validation fits")
    if not np.array_equal(scores[:,0], np.repeat(np.arange(n),3)) or not np.array_equal(scores[:,1], np.tile(np.arange(3),n)):
        raise ValueError("Missing or duplicate target/combination/period records")
    if not np.isfinite(scores).all() or np.any(scores[:,[3,4]] < 0):
        raise ValueError("Nonfinite or invalid validation metrics")
    ranked = [dict(r) for r in db.execute("SELECT * FROM hierarchy ORDER BY validation_rank")]
    if len(ranked) != n or [r["validation_rank"] for r in ranked] != list(range(1,n+1)):
        raise ValueError("Incomplete hierarchy")
    if [r["id"] for r in ranked] != [r["id"] for r in sorted(ranked,key=lambda r:(-r["validation_skill"],r["k"],r["id"]))]:
        raise ValueError("Hierarchy violates frozen tie/selection rule")
    by_id = sorted(ranked, key=lambda r:r["id"])
    means = scores[:,2:6].reshape(n,3,4).sum(axis=1)/3
    observed = np.array([[r[k] for k in ["validation_r2","validation_mae","validation_mse","validation_skill"]] for r in by_id])
    np.testing.assert_allclose(observed, means, rtol=1e-12, atol=1e-12)
    for k in (1,2,3):
        ranks = [r["rank_within_k"] for r in ranked if r["k"] == k]
        if ranks != list(range(1,len(ranks)+1)):
            raise ValueError("Predictor-count ranks are incomplete")
    rank_hash = spec.digest(ranked)
    repeated = [dict(r) for r in db.execute("SELECT * FROM hierarchy ORDER BY validation_rank")]
    if spec.digest(repeated) != rank_hash:
        raise ValueError("Nondeterministic ranking")
    return candidates, ranked, dict(combinations=n, validation_fits=3*n,
        by_k={str(k):sum(len(c)==k for _,c in candidates) for k in (1,2,3)},
        ranking_sha256=rank_hash, score_rows_sha256=hashlib.sha256(scores.tobytes()).hexdigest(),
        qr_svd_fits=int(scores[:,7].sum()), minimum_encoded_rank=int(scores[:,6].min()))


def verify_splits(dest, task, raw, db):
    observed = raw["mb_earliest_release_date" if task["target"]=="mb_release_year" else task["target"]].notna()
    periods = []
    for fold, (start,end) in enumerate(spec.FOLDS):
        tr, va = core.partition(raw,start,end)
        expected = {"train":raw.loc[tr & observed], "validation":raw.loc[va & observed]}
        members = pd.read_csv(dest/f"split_{fold}.csv.gz", dtype={"song_id":str})
        if members.source_row.duplicated().any() or set(members.partition) != {"train","validation"}:
            raise ValueError("Duplicate source rows or invalid split partition")
        for partition, frame in expected.items():
            actual = members.loc[members.partition.eq(partition)]
            if actual.source_row.tolist() != frame.index.tolist() or actual.song_id.tolist() != frame.song_id.tolist():
                raise ValueError("Saved split membership differs from frozen whole-song temporal rule")
        if set(expected["train"].song_id) & set(expected["validation"].song_id):
            raise ValueError("Repeated-song leakage")
        meta = metadata(db,"fold_"+str(fold))
        if meta["n_train"] != len(expected["train"]) or meta["n_validation"] != len(expected["validation"]):
            raise ValueError("Inconsistent evaluation population")
        periods.append(dict(fold=fold,start=start,end=end,n_train=meta["n_train"],n_validation=meta["n_validation"],
            train_songs=meta["train_songs"],validation_songs=meta["validation_songs"]))
    return periods


def verify_final(dest, task, raw, converted):
    selection = json.loads((dest/"selection.json").read_text())
    model = json.loads((dest/"selected_model.json").read_text())
    result = json.loads((dest/"test_metrics.json").read_text())
    hashes = json.loads((dest/"final_artifacts.json").read_text())
    if any(spec.original.sha(dest/p) != value for p,value in hashes.items()):
        raise ValueError("Final model/prediction artifact changed")
    if model["selection_sha256"] != spec.digest(selection) or model["predictors"] != selection["winner"]["predictors"]:
        raise ValueError("Final model differs from validation selection")
    tr, te = core.partition(raw,"2018-01-01",None)
    observed = converted[task["target"]].notna()
    train, test = converted.loc[tr & observed], converted.loc[te & observed]
    members = pd.read_csv(dest/"refit_split.csv.gz",dtype={"song_id":str})
    if members.source_row.duplicated().any():
        raise ValueError("Refit/test source-row overlap")
    for name, frame in [("refit",train),("test",test)]:
        part = members.loc[members.partition.eq(name)]
        if part.source_row.tolist()!=frame.index.tolist() or part.song_id.tolist()!=frame.song_id.tolist():
            raise ValueError("Final membership violates approved chronology")
    if set(train.song_id) & set(test.song_id):
        raise ValueError("Final song overlap")
    predictions = pd.read_csv(dest/"test_predictions.csv.gz",float_precision="round_trip",dtype={"song_id":str})
    if predictions.source_row.tolist()!=test.index.tolist() or predictions.song_id.tolist()!=test.song_id.tolist():
        raise ValueError("Incorrect final prediction population")
    # Check every final encoder was fitted on refit rows alone, and independently
    # check final predictions using direct original-row LAPACK SVD.
    encoder = core.Encoder().fit(train,model["predictors"])
    if encoder.state != model["encoder"]:
        raise ValueError("Final preprocessing differs from train-only fit")
    X, V = encoder.transform(train), encoder.transform(test)
    y, z = train[task["target"]].to_numpy(float),test[task["target"]].to_numpy(float)
    w, u = core.weights(train),core.weights(test)
    mean, median = float(np.average(y,weights=w)),core.weighted_median(y,w)
    if mean!=model["target_center"] or mean!=model["training_mean_baseline"] or median!=model["training_median_baseline"]:
        raise ValueError("Final baseline/centering differs from training data")
    replay = V@np.array(model["coefficients"])+mean
    direct = linalg.lstsq(X*np.sqrt(w)[:,None],(y-mean)*np.sqrt(w),
        cond=np.finfo(float).eps*max(X.shape),lapack_driver="gelsd")[0]
    reference = V@direct+mean
    error = float(np.max(abs(replay-reference)))
    scale = max(1.,float(np.max(abs(reference))))
    if error > 2e-7*scale:
        raise ValueError("Final optimized model disagrees with direct SVD")
    np.testing.assert_allclose(replay,predictions.predicted,atol=1e-10,rtol=1e-10)
    np.testing.assert_array_equal(z,predictions.actual)
    np.testing.assert_allclose(u,predictions.weight,atol=1e-12,rtol=1e-12)
    metrics = core.metrics(z,replay,u,mean,median)
    for key,value in metrics.items():
        if value is None:
            if result[key] is not None:raise ValueError("Undefined final metric")
        else:
            np.testing.assert_allclose(value,result[key],rtol=1e-10,atol=1e-10)
    if result["n_test"]!=len(test) or result["test_songs"]!=test.song_id.nunique() or result["n_refit"]!=len(train):
        raise ValueError("Final sample-size mismatch")
    return dict(test_rows=len(test),test_songs=int(test.song_id.nunique()),refit_rows=len(train),
        max_direct_prediction_absolute_error=error,max_direct_prediction_scaled_error=error/scale,
        encoder_train_only=True,predictions_replayed=True,metrics_recomputed=True)


def audit(stage):
    started = time.perf_counter()
    frozen = verify_frozen()
    baseline = json.loads((CAMPAIGN/"execution/protected_before.json").read_text())
    if protected_files()!=baseline:
        raise ValueError("Protected datasets or existing analyses changed")
    tasks = [t for t in spec.specs() if t["model_family"]=="regression"]
    expected = {t["task_id"].replace(":","__") for t in tasks}
    if {p.parent.name for p in CAMPAIGN.glob("*/results.sqlite")} != expected:
        raise ValueError("Missing or unexpected campaign target databases")
    if stage=="before-test" and any(CAMPAIGN.glob("*/test_metrics.json")):
        raise ValueError("Final evaluation occurred before this pre-test audit")
    saved_before = json.loads((PUBLIC/"coverage_before_test.json").read_text()) if stage=="after-test" else None
    rows, selection_hashes = [], {}
    raw, converted, table = None,None,None
    with threadpool_limits(limits=1):
        for task in tasks:
            if task["table"] != table:
                table = task["table"]
                raw = run.read_table(table)
                converted = spec.original.convert(raw) if stage=="after-test" else None
            dest = run.task_path(CAMPAIGN,task)
            with database(dest/"results.sqlite") as db:
                candidates, ranked, row = catalog_and_scores(db,task)
                if metadata(db,"identity") != clean(run.identity(task,candidates,spec.configuration())):
                    raise ValueError("Checkpoint specification/data/code identity mismatch")
                selected = json.loads((dest/"selection.json").read_text())
                if selected["identity_sha256"] != spec.digest(metadata(db,"identity")):
                    raise ValueError("Selection identity mismatch")
                if selected["candidate_count"]!=len(candidates) or selected["winner"]["id"]!=ranked[0]["id"]:
                    raise ValueError("Selected model is not the validation winner")
                if selected["winner"]["predictors"]!=list(candidates[ranked[0]["id"]][1]):
                    raise ValueError("Selected predictors differ from ranked candidate")
                for k in (1,2,3):
                    retained = next(r for r in selected["best_by_k"] if r["k"]==k)
                    if retained["id"]!=next(r["id"] for r in ranked if r["k"]==k):
                        raise ValueError("Best-by-count retention mismatch")
                row.update(task_id=task["task_id"],periods=verify_splits(dest,task,raw,db))
            selection_hashes[task["task_id"]] = spec.original.sha(dest/"selection.json")
            if stage=="after-test":
                row["final"] = verify_final(dest,task,raw,converted)
            rows.append(row)
            print(stage,task["task_id"],"verified",flush=True)
    if sum(r["combinations"] for r in rows)!=1998901 or len(rows)!=59:
        raise ValueError("Campaign totals do not match approval")
    if saved_before:
        if saved_before["selection_sha256"]!=selection_hashes:
            raise ValueError("Validation winners changed after test access")
        previous = {r["task_id"]:r for r in saved_before["targets"]}
        for row in rows:
            for key in ("ranking_sha256","score_rows_sha256"):
                if row[key]!=previous[row["task_id"]][key]:
                    raise ValueError("Validation scores/rankings changed after test access")
        lock = json.loads((CAMPAIGN/"frozen_selections.json").read_text())
        if len(lock)!=59 or any(spec.digest(s)!=spec.digest(json.loads((run.task_path(CAMPAIGN,
            next(t for t in tasks if t["task_id"]==s["task_id"]))/"selection.json").read_text())) for s in lock):
            raise ValueError("Final selection lock mismatch")
    report = dict(status="PASS",stage=stage,checked_utc=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=time.perf_counter()-started,targets=rows,target_count=59,
        peak_rss_bytes=peak_rss_bytes(),
        combinations=1998901,validation_fits=5996703,
        by_k={str(k):sum(r["by_k"][str(k)] for r in rows) for k in (1,2,3)},
        all_candidates_unique_and_present=True,all_three_periods_present=True,
        deterministic_rankings=True,selection_sha256=selection_hashes,
        public_data_unchanged=True,existing_analyses_unchanged=True,frozen=frozen,
        final_test_evaluated=stage=="after-test",categorical_ordinal_tasks_run=0)
    write_json(PUBLIC/("coverage_before_test.json" if stage=="before-test" else "coverage_after_test.json"),report)
    return report


def export_hierarchies():
    started=time.perf_counter()
    tasks = [t for t in spec.specs() if t["model_family"]=="regression"]
    manifest = []
    for task in tasks:
        dest = run.task_path(CAMPAIGN,task)
        output = CAMPAIGN/"hierarchies"/(task["task_id"].replace(":","__")+".csv.gz")
        candidates = list(enumerate(spec.combinations(task)))
        with Store(dest/"results.sqlite",run.identity(task,candidates,spec.configuration()),candidates,task["predictors"]) as store:
            if not store.complete():raise ValueError("Cannot export incomplete hierarchy")
            run.write_csv(output,(dict(task_id=task["task_id"],**r) for r in store.rows()))
        # Count every exported record, verify predictor-count coverage and rank
        # order independently of the database before advertising the artifact.
        exported = pd.read_csv(output,usecols=["task_id","id","k","validation_rank","rank_within_k"])
        if len(exported)!=len(candidates) or exported.id.nunique()!=len(candidates) or exported.validation_rank.tolist()!=list(range(1,len(candidates)+1)):
            raise ValueError("Incomplete or duplicate hierarchy export")
        for k in (1,2,3):
            if exported.k.eq(k).sum()!=spec.count(task,k):raise ValueError("Export count differs by k")
        manifest.append(dict(task_id=task["task_id"],rows=len(candidates),
            path=str(output.relative_to(ROOT)),bytes=output.stat().st_size,sha256=spec.original.sha(output)))
        print("Exported",task["task_id"],len(candidates),flush=True)
    write_json(PUBLIC/"hierarchy_manifest.json",dict(total_rows=sum(r["rows"] for r in manifest),
        elapsed_seconds=time.perf_counter()-started,peak_rss_bytes=peak_rss_bytes(),
        files=manifest,storage="Local ignored outputs; reproduce with the frozen hierarchy command"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["before-test","after-test","export"])
    args = parser.parse_args()
    if args.command=="export":
        export_hierarchies()
    else:
        audit(args.command)


if __name__=="__main__":
    main()
