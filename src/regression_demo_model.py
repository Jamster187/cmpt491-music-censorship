"""Bounded real-model refits and the exact prediction interface for the local demo."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from scipy import linalg
from threadpoolctl import threadpool_limits

import regression_core as core
import regression_meaningful as meaningful
import regression_relationships as rel
import regression_search as run
import regression_spec as spec
from regression_store import clean,write_json


def convert_inputs(frame,predictors):
    """Only supplied predictors are converted; never consult an outcome column."""
    data=frame.loc[:,predictors].copy()
    for name in predictors:
        if name in spec.original.GENRES:continue
        if name in rel.DATES or name in ("chart_date","snapshot_chart_date"):
            if "snapshot_month" in name:
                dt=pd.to_datetime(data[name],format="%Y-%m")
                data[name]=((dt.dt.year-1970)*12+dt.dt.month-1).astype(float)
            else:
                data[name]=(pd.to_datetime(data[name])-pd.Timestamp("1970-01-01")).dt.days.astype(float)
        else:data[name]=pd.to_numeric(data[name],errors="raise").astype(float)
        if np.isinf(data[name]).any():raise ValueError("Infinite input: "+name)
    return data


def input_rows(raw,predictors):
    data=raw.copy()
    if "mb_release_year" in predictors:
        data["mb_release_year"]=pd.to_numeric(data.mb_earliest_release_date.astype("string").str[:4],errors="raise").astype(float)
    return data.loc[:,predictors]


def encoder(model):
    # Explicit coefficient order survives sorted JSON serialization.
    return core.Encoder({p:model["encoder"][p] for p in model["predictors"]})


def predict_frame(model,raw_inputs):
    data=convert_inputs(raw_inputs,model["predictors"])
    return encoder(model).transform(data)@np.array(model["coefficients"])+model["target_center"]


def predict_values(model,values):
    if set(values)!=set(model["predictors"]):raise ValueError("Provide exactly the selected predictor variables")
    return float(predict_frame(model,pd.DataFrame([values]))[0])


def units(name):
    if name in {"first_snapshot_month","last_snapshot_month"}:return "months since 1970-01"
    if name in rel.DATES or name in {"chart_date","snapshot_chart_date"}:return "days since 1970-01-01"
    if name in spec.original.SCORES:return "classifier score"
    if name in rel.DURATIONS:return "seconds"
    if name=="mb_release_year":return "calendar year"
    return "count / rank / chart points as named"


def availability_warnings(predictors,scenario):
    if scenario=="Retrospective frozen-release analysis":return []
    warnings=["This model has only retrospective evaluation; changing the input scenario does not establish forecasting accuracy."]
    for p in predictors:
        if p in spec.original.FINAL_HISTORY or p in rel.LAST or p=="first_snapshot_month":
            warnings.append(p+": uses later or completed chart history and is unavailable at first chart appearance.")
        elif p in spec.original.SCORES or p in spec.original.GENRES or p.startswith("mb_"):
            warnings.append(p+": enrichment or classifier availability at the historical prediction date is unverified.")
        elif p!="first_chart_date":
            warnings.append(p+": current chart/snapshot value; availability at the first appearance must be established separately.")
    return warnings


def input_warnings(model,values):
    data=convert_inputs(pd.DataFrame([values]),model["predictors"])
    warnings=[]
    for p,bounds in model["input_ranges"].items():
        if p in spec.original.GENRES:continue
        value=data[p].iloc[0]
        if pd.notna(value) and bounds["min"] is not None and not bounds["min"]<=value<=bounds["max"]:
            warnings.append(p+": outside the observed refit-training range; this is extrapolation.")
    for p,n in encoder(model).unsupported(data).items():
        if n:warnings.append(p+": selected category was absent or constant during training.")
    return warnings


def model_directory(task_id,candidate_id):
    return meaningful.LOCAL/"models"/task_id.replace(":","__")/str(int(candidate_id))


def identity(task,candidate):
    return dict(task_id=task["task_id"],candidate_id=candidate["id"],predictors=candidate["predictors"],
        data_sha256=spec.original.sha(spec.ROOT/spec.FILES[task["table"]]),configuration=spec.configuration(),
        policy_sha256=spec.digest(meaningful.read_json(meaningful.PUBLIC/"relationship_policy.json")),
        code_sha256={p:spec.original.sha(spec.ROOT/p) for p in [*run.CODE,"src/regression_demo_model.py"]})


def fit_candidate(task_id,candidate_id):
    """One explicitly selected candidate; never searches or reselects by test metrics."""
    task=meaningful.target_task(task_id)
    chosen=meaningful.candidate(task_id,candidate_id)
    ident=clean(identity(task,chosen))
    dest=model_directory(task_id,candidate_id)
    if (dest/"artifacts.json").exists():
        hashes=meaningful.read_json(dest/"artifacts.json")
        for name,h in hashes.items():
            if spec.original.sha(dest/name)!=h:raise ValueError("Cached model integrity failure: "+str(dest/name))
        model=meaningful.read_json(dest/"model.json")
        if model["identity"]!=ident:raise ValueError("Cached model identity mismatch; preserve results and use a new version")
        return model,meaningful.read_json(dest/"metrics.json"),dest
    started=time.perf_counter()
    raw=run.read_table(task["table"])
    with threadpool_limits(limits=1):
        fold=core.prepare(raw,dict(task,predictors=chosen["predictors"]),"2018-01-01",None)
        beta,ranks,_=fold.fit_batch([chosen["predictors"]])
        predicted=fold.V@beta[:,0]+fold.mean
        reference=linalg.lstsq(fold.X*np.sqrt(fold.w)[:,None],(fold.y-fold.mean)*np.sqrt(fold.w),
            cond=np.finfo(float).eps*max(fold.X.shape),lapack_driver="gelsd")[0]
        reference_prediction=fold.V@reference+fold.mean
        error=float(np.max(abs(predicted-reference_prediction)))
        scaled=error/max(1.,float(np.max(abs(reference_prediction))))
        if scaled>2e-7:raise ValueError("Refit differs from independent original-row SVD")
        result=core.metrics(fold.z,predicted,fold.u,fold.mean,fold.median)
        ci=run.bootstrap(fold,predicted);block_ci=run.bootstrap(fold,predicted,calendar_blocks=True)
        ranges={p:dict(min=None if p in spec.original.GENRES or fold.train[p].notna().sum()==0 else float(fold.train[p].min()),
                       max=None if p in spec.original.GENRES or fold.train[p].notna().sum()==0 else float(fold.train[p].max())) for p in chosen["predictors"]}
        model=clean(dict(identity=ident,task=task,predictors=chosen["predictors"],encoder=fold.encoder.state,
            coefficients=beta[:,0],target_center=fold.mean,training_mean_baseline=fold.mean,
            training_median_baseline=fold.median,input_ranges=ranges,rank=int(ranks[0]),
            evaluation_label="POST-HOC EXPLORATORY",test_previously_inspected=True,
            selected_using_saved_validation_only=True,provenance=run.provenance()))
        supplied=input_rows(raw.loc[fold.validation.index],chosen["predictors"])
        replay=predict_frame(model,supplied)
        np.testing.assert_allclose(replay,predicted,atol=1e-10,rtol=1e-10)
        result.update(task_id=task_id,target=task["target"],candidate_id=chosen["id"],predictors=chosen["predictors"],k=chosen["k"],
            category=chosen["category"],same_family_predictors=chosen["same_family_predictors"],cross_domain_predictors=chosen["cross_domain_predictors"],
            units=units(task["target"]),evaluation_label="POST-HOC EXPLORATORY",test_previously_inspected=True,
            n_refit=len(fold.y),n_test=len(fold.z),test_songs=int(fold.validation.song_id.nunique()),
            validation_r2=chosen["validation_r2"],validation_mae=chosen["validation_mae"],validation_rmse=chosen["validation_rmse"],
            validation_skill=chosen["validation_skill"],validation_baseline_r2=chosen["baseline_r2"],
            validation_baseline_mae=chosen["baseline_mae"],validation_baseline_rmse=chosen["baseline_rmse"],
            n_validation=chosen["n_validation"],validation_songs=chosen["validation_songs"],
            historical_validation_metrics=chosen["period_metrics"],
            test_minus_validation_r2=result["r2"]-chosen["validation_r2"],
            test_minus_validation_mae=result["mae"]-chosen["validation_mae"],
            test_minus_validation_rmse=result["rmse"]-chosen["validation_rmse"],
            test_minus_validation_skill=result["skill"]-chosen["validation_skill"],
            ci95=ci,calendar_block_ci95=block_ci,unsupported_genre_rows=fold.encoder.unsupported(fold.validation),
            direct_prediction_max_absolute_error=error,direct_prediction_max_scaled_error=scaled,
            prediction_interface_max_absolute_error=float(np.max(abs(replay-predicted))),
            elapsed_seconds=time.perf_counter()-started)
        original_selected=meaningful.read_json(meaningful.original_path(task)/"selection.json")
        if chosen["id"]==original_selected["winner"]["id"]:
            old=meaningful.read_json(meaningful.original_path(task)/"test_metrics.json")
            for key in ("r2","mae","rmse","baseline_r2","baseline_mae","baseline_rmse"):
                np.testing.assert_allclose(result[key],old[key],atol=1e-9,rtol=1e-9)
            result["matches_original_selected_model"]=True
        write_json(dest/"model.json",model);write_json(dest/"metrics.json",result)
        run.write_csv(dest/"predictions.csv.gz",(dict(source_row=int(i),song_id=s,actual=float(y),predicted=float(p),weight=float(w))
            for i,s,y,p,w in zip(fold.validation.index,fold.validation.song_id,fold.z,predicted,fold.u)))
        run.write_csv(dest/"split.csv.gz",(dict(source_row=int(i),song_id=s,partition=part)
            for part,frame in [("refit",fold.train),("test",fold.validation)] for i,s in frame.song_id.items()))
        write_json(dest/"artifacts.json",{n:spec.original.sha(dest/n) for n in ["model.json","metrics.json","predictions.csv.gz","split.csv.gz"]})
    return model,clean(result),dest
