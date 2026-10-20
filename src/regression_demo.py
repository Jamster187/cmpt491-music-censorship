"""Local professor demonstration. Launch with Streamlit; never starts a search."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

import regression_meaningful as m
import regression_demo_model as models
import regression_relationships as rel


@st.cache_data(max_entries=6,show_spinner=False)
def hierarchy_frame(task_id,view,k,category,policy_sha):
    return pd.DataFrame(m.hierarchy(task_id,view,k,category))


@st.cache_data(max_entries=6,show_spinner=False)
def fitted(task_id,candidate_id):
    model,metrics,dest=models.fit_candidate(task_id,candidate_id)
    predictions=pd.read_csv(dest/"predictions.csv.gz",float_precision="round_trip",dtype={"song_id":str})
    raw=m.original.read_table(m.target_task(task_id)["table"])
    examples=raw.loc[predictions.source_row].reset_index(drop=True)
    return model,metrics,predictions,examples


def leaderboards(view):
    if view=="Original unrestricted":
        rows=m.read_json(m.original.PUBLIC/"campaign/target_leaderboard.json")
        ids={r["task_id"]:r["candidate_id"] for r in m.read_json(m.original.PUBLIC/"campaign/selected_models.json")["models"]}
        return [dict(r,candidate_id=ids[r["task_id"]],category=rel.classify(r["target"],r["predictors"])["category"],
            evaluation_label="Original unrestricted evaluation; already inspected") for r in rows]
    name="cross_domain" if view=="Cross-domain" else "filtered"
    return m.read_json(m.PUBLIC/(name+"_leaderboard.json"))


def show_leaderboard(rows):
    frame=pd.DataFrame(rows)
    if frame.empty:st.info("No eligible models.");return
    order=st.selectbox("Sort targets",["Test R²: highest first","Test R²: lowest first"],key="leaderboard_sort")
    frame=frame.sort_values(["r2","task_id"],ascending=[order.endswith("lowest first"),True])
    cols=["task_id","predictors","r2","mae","rmse","baseline_r2","baseline_rmse","baseline_mae",
          "skill","category","n_test","test_songs","test_minus_validation_r2"]
    shown=frame[cols].copy();shown["predictors"]=shown.predictors.map(" + ".join)
    st.dataframe(shown,hide_index=True,width="stretch")
    st.caption("R² compares target-relative variance. MAE/RMSE have different units across targets. Baseline MSE skill compares with the training mean; baseline MAE uses the training median.")


def diagnostics(predictions,metrics):
    sample=predictions.iloc[np.linspace(0,len(predictions)-1,min(2000,len(predictions)),dtype=int)]
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout="constrained")
    axes[0].scatter(sample.actual,sample.predicted,s=9,alpha=.35,color="#2166ac")
    low=min(sample.actual.min(),sample.predicted.min());high=max(sample.actual.max(),sample.predicted.max())
    axes[0].plot([low,high],[low,high],color="#ad343e",linewidth=1)
    axes[0].set(xlabel="Actual",ylabel="Predicted",title="Actual versus predicted")
    axes[1].scatter(sample.predicted,sample.actual-sample.predicted,s=9,alpha=.35,color="#2c7f70")
    axes[1].axhline(0,color="#ad343e",linewidth=1)
    axes[1].set(xlabel="Predicted",ylabel="Actual − predicted",title="Residuals")
    st.pyplot(fig);plt.close(fig)
    st.caption(f"Plots show {len(sample):,} deterministic held-out rows. Metrics use all {metrics['n_test']:,} rows with equal total weight per song. Units: {metrics['units']}.")


def manual_field(name,value,key):
    missing=bool(pd.isna(value))
    unknown=st.checkbox(name+": missing / unavailable",value=missing,key=key+":missing")
    if name=="primary_genre":
        choices=m.spec.original.GENRE_TAXONOMY
        answer=st.selectbox(name,choices,index=choices.index(value) if not missing else 0,key=key)
    elif name=="secondary_genres":
        chosen=[] if missing else json.loads(value)
        answer=json.dumps(st.multiselect(name,m.spec.original.GENRE_TAXONOMY,default=chosen,key=key))
        st.caption("An empty list means no secondary genre; missing uses the fitted missingness encoding.")
    elif name in rel.DATES or name in ("chart_date","snapshot_chart_date"):
        fmt="YYYY-MM" if "snapshot_month" in name else "YYYY-MM-DD"
        answer=st.text_input(name+" ("+fmt+")",value="1970-01" if missing and "snapshot_month" in name else "1970-01-01" if missing else str(value),key=key)
    else:
        answer=st.number_input(name,value=0. if missing else float(value),step=.01 if name in m.spec.original.SCORES else 1.,format="%.6f",key=key)
    return None if unknown else answer


def prediction_panel(task_id,candidate_id):
    key=task_id+":"+str(candidate_id)
    path=models.model_directory(task_id,candidate_id)
    if not (path/"artifacts.json").exists() and st.session_state.get("loaded_model")!=key:
        st.info("This candidate has saved validation scores. Load it to refit one model with the frozen protocol and calculate exploratory held-out metrics; usually a few seconds. This never runs the exhaustive search.")
        if st.button("Load/refit this model",key="load_model"):st.session_state["loaded_model"]=key
        else:return
    with st.spinner("Loading or refitting this selected model…"):
        model,metrics,predictions,examples=fitted(task_id,candidate_id)
    st.subheader("Use the fitted model")
    st.warning("POST-HOC EXPLORATORY. The 2018-onward test population was already inspected. This is retrospective prediction, with no causal or as-of forecasting claim.")
    st.write("Predictors: "+" + ".join(model["predictors"]))
    columns=st.columns(4)
    for col,name,label in zip(columns,["r2","mae","rmse","skill"],["Test R²","Test MAE","Test RMSE","MSE skill vs mean"]):col.metric(label,f"{metrics[name]:.4f}")
    st.write(f"Training-mean baseline: R² {metrics['baseline_r2']:.4f}, RMSE {metrics['baseline_rmse']:.4f}. Training-median baseline MAE: {metrics['baseline_mae']:.4f}.")
    st.write(f"Validation R² {metrics['validation_r2']:.4f}; MAE {metrics['validation_mae']:.4f}; RMSE {metrics['validation_rmse']:.4f}. Test − validation R²: {metrics['test_minus_validation_r2']:+.4f}.")
    st.caption(f"Test: {metrics['n_test']:,} rows / {metrics['test_songs']:,} songs. Refit: {metrics['n_refit']:,} rows. 95% fixed-model song-bootstrap R² interval: {metrics['ci95']['r2'][0]:.4f} to {metrics['ci95']['r2'][1]:.4f}; excludes model-selection/refit uncertainty.")
    scenario=st.selectbox("Prediction scenario",["Retrospective frozen-release analysis","At first chart appearance (availability check)"],key="scenario")
    warnings=models.availability_warnings(model["predictors"],scenario)
    for warning in warnings:st.warning(warning)
    mode=st.radio("Predict using",["Held-out example","Enter values"],horizontal=True,key="input_mode")
    if mode=="Held-out example":
        idx=int(st.number_input("Held-out row (0-based)",min_value=0,max_value=len(examples)-1,value=0,step=1,key="example_index"))
        example=examples.iloc[idx]
        st.write(f"{example['title']} — {example['artist']}")
        values=models.input_rows(examples.iloc[[idx]],model["predictors"]).iloc[0].to_dict()
        st.dataframe(pd.DataFrame({"Predictor":list(values),"Observed value":[str(v) for v in values.values()]}),hide_index=True,width="stretch")
        prediction=models.predict_values(model,values)
        if not np.isclose(prediction,predictions.predicted.iloc[idx],atol=1e-9,rtol=1e-9):raise ValueError("Prediction interface replay mismatch")
        a,b,c=st.columns(3)
        a.metric("Actual",f"{predictions.actual.iloc[idx]:.6f}")
        b.metric("Prediction",f"{prediction:.6f}")
        c.metric("Residual",f"{predictions.actual.iloc[idx]-prediction:.6f}")
        st.session_state["last_prediction"]=prediction
        st.session_state["last_actual"]=float(predictions.actual.iloc[idx])
    else:
        defaults=models.input_rows(examples.iloc[[0]],model["predictors"]).iloc[0].to_dict()
        acknowledge=not warnings or st.checkbox("I understand these inputs may be unavailable at that historical time",key="acknowledge")
        st.caption("A checked missing/unavailable box overrides the entered value and uses the saved missingness/imputation rules.")
        with st.form("manual_prediction"):
            values={p:manual_field(p,defaults[p],key+":"+p) for p in model["predictors"]}
            submit=st.form_submit_button("Generate prediction",disabled=not acknowledge)
        if submit:
            try:
                extra=models.input_warnings(model,values)
                for warning in extra:st.warning(warning)
                prediction=models.predict_values(model,values)
                st.metric("Prediction",f"{prediction:.6f}")
                st.caption("No actual outcome is supplied for manually entered values. OLS outputs are not clipped.")
                st.session_state["last_prediction"]=prediction
                st.session_state["last_actual"]=None
            except (ValueError,TypeError,KeyError) as error:st.error(str(error))
    diagnostics(predictions,metrics)
    with st.expander("Relationship, availability and uncertainty details"):
        st.json(rel.classify(model["task"]["target"],model["predictors"]))
        st.json({p:m.spec.original.availability(p) for p in model["predictors"]})
        st.json(metrics["calendar_block_ci95"])


def main():
    st.set_page_config(page_title="Music regression lab",layout="wide")
    st.title("Music regression lab")
    st.caption("Explore the completed 1–3 predictor OLS campaign. Original results are preserved; meaningful and cross-domain views are post-hoc exploratory.")
    if not (m.PUBLIC/"relationship_policy.json").exists():
        st.error("Meaningful results are not prepared. See analysis/regression_search/meaningful/README.md.");return
    view=st.sidebar.radio("View",["A · Predictor hierarchy","B · Target predictability","C · Cross-domain"],key="view")
    task_ids=[t["task_id"] for t in m.tasks()]
    task_id=st.sidebar.selectbox("Target variable",task_ids,index=task_ids.index("songs:ll_violence"),key="target")
    policy_sha=m.spec.digest(m.read_json(m.PUBLIC/"relationship_policy.json"))
    candidate_id=None
    try:
        if view.startswith("A"):
            mode=st.radio("Hierarchy",["Filtered (A excluded)","Unrestricted"],horizontal=True,key="hierarchy_mode")
            k=st.selectbox("Predictor count",["All",1,2,3],key="predictor_count")
            category=st.selectbox("Relationship filter",["All",rel.B,rel.C]+([rel.A] if mode=="Unrestricted" else []),key="relationship_filter")
            df=hierarchy_frame(task_id,"unrestricted" if mode=="Unrestricted" else "filtered",None if k=="All" else k,None if category=="All" else category,policy_sha)
            search=st.text_input("Find predictor name",key="find_predictor")
            if search:df=df[df.predictors.map(lambda p:search.lower() in " ".join(p).lower())]
            st.write(f"{len(df):,} matching combinations. Ranked by the original validation MSE skill; no test scores enter this ranking.")
            if df.empty:st.info("No combinations match these filters.");return
            pages=math.ceil(len(df)/50)
            page=int(st.number_input("Page",min_value=1,max_value=pages,value=1,step=1,key="hierarchy_page"))
            shown=df.iloc[(page-1)*50:page*50].copy()
            shown["predictors"]=shown.predictors.map(" + ".join)
            st.dataframe(shown[["rank","original_rank","id","predictors","k","validation_r2","validation_mae","validation_rmse","validation_skill","n_validation","category"]],hide_index=True,width="stretch")
            options=shown.id.astype(int).tolist()
            labels={int(r.id):f"{r.id}: {r.predictors}" for r in shown.itertuples()}
            candidate_id=st.selectbox("Model on this page",options,format_func=lambda x:labels[x],key="candidate_select")
            st.download_button("Download all matching validation rows",df.to_csv(index=False).encode(),file_name=task_id.replace(":","__")+"_hierarchy.csv",mime="text/csv")
        else:
            variant="Cross-domain" if view.startswith("C") else st.radio("Leaderboard",["Filtered meaningful","Original unrestricted"],horizontal=True,key="leaderboard_variant")
            rows=leaderboards(variant)
            st.info("Original unrestricted evaluation" if variant=="Original unrestricted" else "POST-HOC EXPLORATORY: winners were chosen from saved validation results; the final test had previously been inspected.")
            show_leaderboard(rows)
            chosen=next((r for r in rows if r["task_id"]==task_id),None)
            if chosen is None:st.info("No eligible winner for this target.");return
            candidate_id=chosen["candidate_id"]
        relationship=rel.classify(m.target_task(task_id)["target"],m.candidate(task_id,candidate_id)["predictors"])
        if relationship["category"]==rel.A:st.warning("This unrestricted candidate is reconstruction and is excluded from the meaningful leaderboard.")
        st.caption(relationship["category"]+(" · includes both same-family and cross-domain predictors" if relationship["mixed_domains"] else ""))
        prediction_panel(task_id,int(candidate_id))
    except (FileNotFoundError,ValueError) as error:
        st.error(str(error))
        st.info("Complete local original hierarchies are required for arbitrary model selection. No sampled or truncated hierarchy is substituted. See the demo README for recovery and setup.")


if __name__=="__main__":main()
