"""Shared, public-data-only protocol for the authorized Chapters 5–8 campaign."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import scipy
import sklearn

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "analysis/course_methods"
LOCAL = ROOT / "data/experiments/course_methods_v1"
INPUT = ROOT / "data/public/songs.csv"
SEED = 491202610
SCORES = list(pd.read_csv(INPUT, nrows=0).filter(regex=r"^(ll_|detox_|emotion_|sentiment_)").columns)
FAMILIES = {p: [s for s in SCORES if s.startswith(p)] for p in ("ll_", "detox_", "emotion_", "sentiment_")}
GENRES = ["Pop", "R&B / Soul", "Rock", "Hip-Hop / Rap", "Country", "Electronic / Dance"]
OUTER = [(1990, 2000), (2000, 2010), (2010, 2018), (2018, 2026)]
CONFIG = dict(version="course-methods-v1", seed=SEED, unit="exact original title + artist song identity",
    score_features=SCORES, complete_case_scores=True, bins_training_end=2010,
    frequent_supports=[.05, .08, .12], primary_support=.08, maximum_itemset_size=4,
    transaction_bins="<=training Q25: low; >training Q75: high; middle interval emits no tail item",
    association_discovery="last chart before 2010; validation 2010–2017; test 2018–2025; whole-history purging",
    rare_pair_minimum_support=.005, rare_pair_minimum_count=20,
    primary_rule_max_antecedents=3, primary_rule_consequents=1,
    primary_inference="held-out debut-year-stratified CMH; global Benjamini–Yekutieli; exploratory",
    outer_periods=OUTER, classification_inner_validation_years=5, tree_depths=[3,4,5,6],
    tree_class_weights=[None,"balanced"], minimum_leaf=50,
    naive_bayes="GaussianNB; fixed var_smoothing=1e-9; all 42 eligible lyrical predictors",
    chart_prediction_scenario="lyrics measured before hypothetical first chart entry; conditional on eventual Billboard inclusion; retrospective frozen classifiers",
    longevity="strictly above inner-training chart_weeks 75th percentile; fixed within outer fold",
    broad_genres=GENRES, other_genres="Other broad genre", clustering_k=list(range(2,13)),
    clustering_representations=["standardized42","pca90","family_balanced"],
    clustering_methods=["kmeans","kmedoids","hierarchical"], expensive_training_sample=1200,
    silhouette_sample=1200, clustering_seeds=[SEED,SEED+1,SEED+2],
    cluster_selection="validation silhouette among min training cluster >=1% and mean resample ARI >=0.6; otherwise explicitly unsupported best silhouette",
    bootstrap_repeats=299, minimum_group=100, maximum_rss_gib=3,
    prior_outcomes_inspected=True, no_independent_confirmation=True, covid_causality=False)


def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def clean(value):
    if isinstance(value,dict): return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [clean(v) for v in value]
    if isinstance(value,np.ndarray): return clean(value.tolist())
    if isinstance(value,np.generic): return clean(value.item())
    if isinstance(value,float) and not np.isfinite(value): return None
    return value


def digest(value):
    return hashlib.sha256(json.dumps(clean(value),sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(clean(value),sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    if path.suffix==".gz":raw=gzip.compress(raw,mtime=0)
    tmp=path.with_name(path.name+".tmp");tmp.write_bytes(raw);os.replace(tmp,path)


def read_json(path):
    path=Path(path);raw=path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix==".gz" else raw)


def write_csv(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    frame=rows if isinstance(rows,pd.DataFrame) else pd.DataFrame(clean(rows))
    for col in frame:
        if frame[col].map(lambda x:isinstance(x,(list,dict,tuple))).any():
            frame[col]=frame[col].map(lambda x:json.dumps(clean(x),sort_keys=True) if isinstance(x,(list,dict,tuple)) else x)
    raw=frame.to_csv(index=False,lineterminator="\n",float_format="%.15g").encode()
    if path.suffix==".gz":raw=gzip.compress(raw,mtime=0)
    tmp=path.with_name(path.name+".tmp");tmp.write_bytes(raw);os.replace(tmp,path)


def data(complete=True):
    frame=pd.read_csv(INPUT,keep_default_na=False,na_values=[""]).sort_values("song_id").reset_index(drop=True)
    if len(frame)!=28041 or frame.song_id.duplicated().any() or len(SCORES)!=42:
        raise ValueError("Unexpected public schema/population")
    frame["year"]=pd.to_datetime(frame.first_chart_date).dt.year
    frame["decade"]=(frame.year//10*10).astype(str)+"s"
    frame["period"]=np.where(frame.year<2020,"pre2020","post2020")
    frame["broad_genre"]=frame.primary_genre.where(frame.primary_genre.isin(GENRES),"Other broad genre")
    if complete: frame=frame.dropna(subset=SCORES).copy()
    return frame.reset_index(drop=True)


def partitions(frame,start=2010,end=2018):
    train=frame.last_chart_date.lt(f"{start}-01-01")
    test=frame.first_chart_date.ge(f"{start}-01-01") & frame.last_chart_date.lt(f"{end}-01-01")
    assert not set(frame.loc[train,"song_id"]) & set(frame.loc[test,"song_id"])
    return frame.loc[train].copy(),frame.loc[test].copy()


def primary_split(frame):
    train,validation=partitions(frame,2010,2018)
    _,test=partitions(frame,2018,2026)
    return train,validation,test


def environment():
    return dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
                scipy=scipy.__version__,sklearn=sklearn.__version__,platform=platform.platform())


def freeze():
    PUBLIC.mkdir(parents=True,exist_ok=True);LOCAL.mkdir(parents=True,exist_ok=True)
    ident=dict(configuration=CONFIG,input_sha256=sha(INPUT),environment=environment())
    path=PUBLIC/"protocol.json"
    if path.exists():
        if read_json(path)!=clean(ident):raise ValueError("Protocol changed; refuse reuse")
    else:write_json(path,ident)
    return digest(ident)


def checkpoint(name,producer,code):
    identity=dict(protocol=freeze(),code={p:sha(ROOT/p) for p in ["src/course_common.py",*code]})
    path=LOCAL/(name+".json.gz")
    if path.exists():
        previous=read_json(path)
        if previous["identity"]!=identity:raise ValueError("Checkpoint identity differs: "+str(path))
        if digest(previous["result"])!=previous["result_sha256"]:raise ValueError("Corrupt checkpoint")
        return previous["result"],True
    started=time.perf_counter();result=clean(producer())
    write_json(path,dict(identity=identity,result=result,result_sha256=digest(result),seconds=time.perf_counter()-started))
    return result,False


def usage(start):
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform!="darwin":rss*=1024
    return dict(wall_seconds=time.perf_counter()-start,peak_rss_bytes=rss)


def preservation(initialize=False):
    """Hash pre-existing data and analysis, including ignored research artifacts."""
    LOCAL.mkdir(parents=True,exist_ok=True);path=LOCAL/"preservation.json"
    if not path.exists():
        if not initialize:raise ValueError("Preservation snapshot missing")
        files={}
        for base in (ROOT/"data",ROOT/"analysis"):
            for p in sorted(base.rglob("*")):
                if not p.is_file() or LOCAL in p.parents or PUBLIC in p.parents or "__pycache__" in p.parts:continue
                files[str(p.relative_to(ROOT))]=dict(sha256=sha(p),size=p.stat().st_size)
        write_json(path,dict(baseline_commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),files=files))
    record=read_json(path)
    for name,item in record["files"].items():
        p=ROOT/name
        if not p.exists() or p.stat().st_size!=item["size"] or sha(p)!=item["sha256"]:
            raise ValueError("Protected file changed: "+name)
    return dict(status="PASS",files=len(record["files"]),bytes=sum(x["size"] for x in record["files"].values()),baseline_commit=record["baseline_commit"])


def prepare():
    started=time.perf_counter();before=preservation(True);freeze();frame=data(False);tr,va,te=primary_split(data())
    coverage=[]
    for group,g in frame.groupby("decade"):
        coverage.append(dict(decade=group,n=len(g),complete_scores=int(g[SCORES].notna().all(axis=1).sum())))
    write_csv(PUBLIC/"coverage.csv",coverage)
    write_json(PUBLIC/"preparation.json",dict(preservation=before,rows=len(frame),complete_scores=len(data()),
        train=len(tr),validation=len(va),test=len(te),excluded_boundary_or_2026=len(data())-len(tr)-len(va)-len(te),
        split_song_hashes={n:digest(f.song_id.tolist()) for n,f in [("train",tr),("validation",va),("test",te)]},**usage(started)))
    print(json.dumps(read_json(PUBLIC/"preparation.json"),indent=2),flush=True)


if __name__=="__main__":prepare()
