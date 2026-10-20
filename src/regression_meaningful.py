"""Complete validation-only filtering of the preserved exhaustive campaign."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import numpy as np

import regression_relationships as rel
import regression_search as original
import regression_spec as spec
from regression_store import clean, write_json

ROOT=spec.ROOT
SOURCE=original.LOCAL/"campaign"
LOCAL=original.LOCAL/"meaningful_v1"
PUBLIC=original.PUBLIC/"meaningful"
SOURCE_COMMIT="6d8da5fab45b3fd3326355282e4b6f95175dd9fc"
sys.path.insert(0,str(original.PUBLIC))
from campaign_report import catalog_and_scores, metadata


def read_json(path):
    return json.loads(Path(path).read_text())


@contextmanager
def readonly(path):
    if not Path(path).is_file():
        raise FileNotFoundError("Complete local hierarchy required: "+str(path))
    db=sqlite3.connect("file:"+str(Path(path).resolve())+"?mode=ro&immutable=1",uri=True)
    db.row_factory=sqlite3.Row
    try:yield db
    finally:db.close()


def tasks():
    return [t for t in spec.specs() if t["model_family"]=="regression"]


def target_task(task_id):
    return next(t for t in tasks() if t["task_id"]==task_id)


def original_path(task):
    return original.task_path(SOURCE,task)


def index_path(task):
    return original.task_path(LOCAL/"hierarchies",task).with_suffix(".sqlite")


def preserve_originals(initialize=False):
    path=LOCAL/"original_artifacts_before.json"
    if not path.exists():
        if not initialize:raise ValueError("Original-artifact baseline is missing")
        tracked=subprocess.check_output(["git","ls-tree","-r","--name-only",SOURCE_COMMIT,
            "data","analysis","docs/regression_search_plan.md","docs/regression_search_results.md",
            "docs/regression_search_four_predictor_feasibility.md","docs/assets/regression_search_professor_demo.png",*original.CODE],cwd=ROOT,text=True).splitlines()
        files={p:spec.original.sha(ROOT/p) for p in tracked if (ROOT/p).is_file()}
        files.update({str(p.relative_to(ROOT)):spec.original.sha(p) for p in SOURCE.rglob("*") if p.is_file()})
        write_json(path,dict(source_commit=SOURCE_COMMIT,files=files))
    saved=read_json(path)
    for name,expected in saved["files"].items():
        if not (ROOT/name).is_file() or spec.original.sha(ROOT/name)!=expected:
            raise ValueError("Preserved original changed: "+name)
    for name,expected in read_json(original.PUBLIC/"artifact_manifest.json")["artifacts_sha256"].items():
        if spec.original.sha(ROOT/name)!=expected:raise ValueError("Original published artifact changed: "+name)
    return dict(files=len(saved["files"]),snapshot_sha256=spec.original.sha(path),status="PASS")


def lock_policy():
    proposed=dict(policy=rel.policy(),classification_code_sha256=spec.original.sha(ROOT/"src/regression_relationships.py"),source_commit=SOURCE_COMMIT)
    dest=PUBLIC/"relationship_policy.json"
    if dest.exists():
        saved=read_json(dest)
        if {k:saved[k] for k in proposed}!=clean(proposed):
            raise ValueError("Frozen relationship policy changed; do not retune using exploratory test results")
    else:
        if any((LOCAL/"models").glob("*/*/metrics.json")):
            raise ValueError("Cannot define a policy after new model evaluations")
        saved=dict(proposed,locked_utc=datetime.now(timezone.utc).isoformat(),new_test_evaluations_at_lock=0)
        write_json(dest,saved)
    return spec.digest(saved)


def decorate(db,task,row):
    r=dict(row)
    r["predictors"]=[task["predictors"][r.pop(key)] for key in ("i1","i2","i3") if r[key] is not None]
    r.pop("i2",None);r.pop("i3",None)
    folds=[metadata(db,"fold_"+str(f)) for f in range(3)]
    r.update(validation_rmse=r["validation_mse"]**.5,
        baseline_r2=np.mean([f["baseline"]["r2"] for f in folds]),
        baseline_mae=np.mean([f["baseline"]["baseline_mae"] for f in folds]),
        baseline_rmse=np.mean([f["baseline"]["mse"] for f in folds])**.5,
        n_validation=sum(f["n_validation"] for f in folds),
        validation_songs=sum(f["validation_songs"] for f in folds),n_train_by_period=[f["n_train"] for f in folds],
        period_metrics=[dict(s) for s in db.execute("SELECT fold,r2,mae,mse,skill,rank FROM scores WHERE id=? ORDER BY fold",(r["id"],))])
    return clean(r)


def build():
    started=time.perf_counter()
    preserved=preserve_originals(True)
    policy_sha=lock_policy()
    approved=read_json(original.PUBLIC/"campaign/coverage_after_test.json")
    proof={t["task_id"]:t for t in approved["targets"]}
    selected=[];summaries=[];pairs=[]
    for task in tasks():
        dest=original_path(task)
        with readonly(dest/"results.sqlite") as db:
            candidates,ranked,coverage=catalog_and_scores(db,task)
            for key in ("ranking_sha256","score_rows_sha256"):
                if coverage[key]!=proof[task["task_id"]][key]:
                    raise ValueError("Original validation hierarchy changed: "+task["task_id"])
            # Independently compare the decorated original winner with its saved selection.
            if decorate(db,task,ranked[0])!=read_json(dest/"selection.json")["winner"]:
                raise ValueError("Saved metric decoration does not reproduce the original hierarchy")
            indexed=[];counts=Counter();rules=Counter();f_rank=0;c_rank=0;fk=Counter();ck=Counter()
            winners={"filtered":None,"cross_domain":None};best={"filtered":{},"cross_domain":{}}
            for row in ranked:
                combo=candidates[row["id"]][1]
                classification=rel.classify(task["target"],combo)
                category=classification["category"]
                counts[category]+=1;rules.update(classification["circular_rules"])
                k=row["k"];fr=None;cr=None;fkr=None;ckr=None
                if category!=rel.A:
                    f_rank+=1;fk[k]+=1;fr=f_rank;fkr=fk[k]
                    if winners["filtered"] is None or k not in best["filtered"]:
                        full=dict(decorate(db,task,row),**classification,filtered_rank=fr,filtered_rank_within_k=fkr)
                        if winners["filtered"] is None:winners["filtered"]=full
                        best["filtered"].setdefault(k,full)
                if category==rel.C:
                    c_rank+=1;ck[k]+=1;cr=c_rank;ckr=ck[k]
                    if winners["cross_domain"] is None or k not in best["cross_domain"]:
                        full=dict(decorate(db,task,row),**classification,cross_domain_rank=cr,cross_domain_rank_within_k=ckr)
                        if winners["cross_domain"] is None:winners["cross_domain"]=full
                        best["cross_domain"].setdefault(k,full)
                indexed.append((row["id"],k,category,row["validation_rank"],fr,fkr,cr,ckr,json.dumps(classification["circular_rules"])))
            path=index_path(task);path.parent.mkdir(parents=True,exist_ok=True)
            index_identity=dict(policy_sha256=policy_sha,original_validation_ranking_sha256=coverage["ranking_sha256"],
                original_score_rows_sha256=coverage["score_rows_sha256"],task_id=task["task_id"],candidate_count=len(candidates))
            if path.exists():
                with readonly(path) as existing:
                    if metadata(existing,"identity")!=index_identity or [tuple(r) for r in existing.execute("SELECT * FROM ranking ORDER BY original_rank")]!=indexed:
                        raise ValueError("Existing filtered index differs; refusing replacement")
            else:
                temp=path.with_suffix(".sqlite.tmp")
                if temp.exists():temp.unlink()
                with sqlite3.connect(temp) as out:
                    out.executescript("CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT); CREATE TABLE ranking (id INTEGER PRIMARY KEY,k INTEGER,category TEXT,original_rank INTEGER UNIQUE,filtered_rank INTEGER UNIQUE,filtered_rank_k INTEGER,cross_rank INTEGER UNIQUE,cross_rank_k INTEGER,reasons TEXT);")
                    out.execute("INSERT INTO metadata VALUES (?,?)",("identity",json.dumps(index_identity,sort_keys=True)))
                    out.executemany("INSERT INTO ranking VALUES (?,?,?,?,?,?,?,?,?)",indexed)
                temp.replace(path)
            selected.append(dict(task_id=task["task_id"],target=task["target"],winners=winners,
                best_by_k={mode:[items[k] for k in sorted(items)] for mode,items in best.items()},
                original_candidates=len(candidates),eligible_candidates=f_rank,cross_domain_candidates=c_rank))
            summaries.append(dict(task_id=task["task_id"],original=len(candidates),excluded=counts[rel.A],eligible=f_rank,
                cross_domain=c_rank,by_category=dict(counts),circular_rule_counts=dict(rules),
                source_coverage=coverage,index_path=str(path.relative_to(ROOT)),index_sha256=spec.original.sha(path)))
            for p in task["predictors"]:
                pairs.append(dict(task_id=task["task_id"],predictor=p,**rel.classify(task["target"],[p])))
        print("Filtered",task["task_id"],f_rank,"eligible,",c_rank,"cross-domain",flush=True)
    bundle=dict(policy_sha256=policy_sha,evaluation_label="POST-HOC EXPLORATORY",selection_uses_test=False,
        selected_from_complete_saved_validation=True,targets=selected)
    lock=PUBLIC/"selected_candidates.json"
    if lock.exists() and read_json(lock)!=clean(bundle):raise ValueError("Frozen selections changed")
    write_json(lock,bundle)
    totals=dict(status="PASS",source_combinations=sum(r["original"] for r in summaries),
        excluded_combinations=sum(r["excluded"] for r in summaries),eligible_combinations=sum(r["eligible"] for r in summaries),
        cross_domain_combinations=sum(r["cross_domain"] for r in summaries),
        circular_directed_relationships=sum(r["category"]==rel.A for r in pairs),
        targets_with_filtered_winners=sum(t["winners"]["filtered"] is not None for t in selected),
        targets_with_cross_domain_winners=sum(t["winners"]["cross_domain"] is not None for t in selected),
        policy_sha256=policy_sha,selection_sha256=spec.original.sha(lock),elapsed_seconds=time.perf_counter()-started,
        preservation=preserved,targets=summaries,full_search_rerun=False)
    if totals["source_combinations"]!=1998901 or len(selected)!=59:raise ValueError("Incomplete source universe")
    write_json(PUBLIC/"filter_audit.json",totals)
    original.write_csv(PUBLIC/"relationship_pairs.csv",pairs)
    write_best_by_count(bundle)
    preserve_originals()
    return totals


def write_best_by_count(bundle):
    original.write_csv(PUBLIC/"best_by_predictor_count.csv",(dict(
        task_id=t["task_id"],view=mode,filtered_rank=r.get("filtered_rank"),
        filtered_rank_within_k=r.get("filtered_rank_within_k"),cross_domain_rank=r.get("cross_domain_rank"),
        cross_domain_rank_within_k=r.get("cross_domain_rank_within_k"),
        **{k:v for k,v in r.items() if k not in {"filtered_rank","filtered_rank_within_k","cross_domain_rank","cross_domain_rank_within_k"}})
        for t in bundle["targets"] for mode,rows in t["best_by_k"].items() for r in rows))


def hierarchy(task_id,view="filtered",k=None,category=None):
    """All candidates and original metrics; filters never silently truncate coverage."""
    task=target_task(task_id)
    with readonly(index_path(task)) as index,readonly(original_path(task)/"results.sqlite") as source:
        if metadata(index,"identity")["policy_sha256"]!=spec.digest(read_json(PUBLIC/"relationship_policy.json")):
            raise ValueError("Filtered hierarchy policy mismatch")
        ranked={r["id"]:dict(r) for r in source.execute("SELECT * FROM hierarchy")}
        rank_column={"unrestricted":"original_rank","filtered":"filtered_rank","cross_domain":"cross_rank"}[view]
        query="SELECT * FROM ranking WHERE "+rank_column+" IS NOT NULL"
        params=[]
        if k is not None:query+=" AND k=?";params.append(k)
        if category is not None:query+=" AND category=?";params.append(category)
        query+=" ORDER BY "+rank_column
        folds=[metadata(source,"fold_"+str(f)) for f in range(3)]
        for ix in index.execute(query,params):
            r=ranked[ix["id"]]
            p=[task["predictors"][r[x]] for x in ("i1","i2","i3") if r[x] is not None]
            yield dict(task_id=task_id,id=r["id"],rank=ix[rank_column],original_rank=ix["original_rank"],k=r["k"],
                predictors=p,validation_r2=r["validation_r2"],validation_mae=r["validation_mae"],
                validation_rmse=r["validation_mse"]**.5,validation_skill=r["validation_skill"],
                baseline_r2=float(np.mean([f["baseline"]["r2"] for f in folds])),
                baseline_mae=float(np.mean([f["baseline"]["baseline_mae"] for f in folds])),
                baseline_rmse=float(np.mean([f["baseline"]["mse"] for f in folds])**.5),
                n_validation=sum(f["n_validation"] for f in folds),validation_songs=sum(f["validation_songs"] for f in folds),
                **rel.classify(task["target"],p))


def candidate(task_id,candidate_id):
    task=target_task(task_id)
    with readonly(original_path(task)/"results.sqlite") as db:
        r=db.execute("SELECT * FROM hierarchy WHERE id=?",(int(candidate_id),)).fetchone()
        if r is None:raise ValueError("Candidate is not in the complete original validation hierarchy")
        full=decorate(db,task,r)
        return dict(task_id=task_id,**full,**rel.classify(task["target"],full["predictors"]))


def evaluate():
    from regression_demo_model import fit_candidate
    started=time.perf_counter()
    lock_policy();preserve_originals()
    selections=read_json(PUBLIC/"selected_candidates.json")
    audit=read_json(PUBLIC/"filter_audit.json")
    if spec.original.sha(PUBLIC/"selected_candidates.json")!=audit["selection_sha256"]:raise ValueError("Selection lock changed")
    rows={"filtered":[],"cross_domain":[]}
    unique=set()
    for task in selections["targets"]:
        for mode,winner in task["winners"].items():
            if winner is None:continue
            model,result,_=fit_candidate(task["task_id"],winner["id"])
            unique.add((task["task_id"],winner["id"]))
            rows[mode].append(dict(result,view=mode))
        print("Evaluated",task["task_id"],flush=True)
    for mode,results in rows.items():
        results.sort(key=lambda r:(-r["r2"],r["task_id"]))
        for rank,r in enumerate(results,1):r["target_rank"]=rank
        write_json(PUBLIC/(mode+"_leaderboard.json"),results)
        original.write_csv(PUBLIC/(mode+"_leaderboard.csv"),results)
    write_json(PUBLIC/"evaluation_audit.json",dict(status="PASS",elapsed_seconds=time.perf_counter()-started,
        unique_selected_models=len(unique),filtered_models=len(rows["filtered"]),cross_domain_models=len(rows["cross_domain"]),
        policy_sha256=selections["policy_sha256"],selection_sha256=audit["selection_sha256"],
        original_preservation=preserve_originals(),evaluation_label="POST-HOC EXPLORATORY",test_based_reselection=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("build");sub.add_parser("evaluate");sub.add_parser("verify-originals")
    p=sub.add_parser("export");p.add_argument("--task",required=True);p.add_argument("--view",choices=["unrestricted","filtered","cross_domain"],default="filtered");p.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.command=="build":build()
    elif args.command=="evaluate":evaluate()
    elif args.command=="verify-originals":print(json.dumps(preserve_originals(),indent=2))
    else:original.write_csv(args.output,hierarchy(args.task,args.view))


if __name__=="__main__":main()
