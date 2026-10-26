"""Functional classroom explorer of the completed, saved course-method campaign."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import streamlit as st

import course_demo_model as api

st.set_page_config(page_title="CMPT 491 · Data-mining methods",layout="wide")


@st.cache_data
def table(name):return pd.read_csv(api.PUBLIC/name)


@st.cache_data
def document(name):return api.read_json(api.PUBLIC/name)


@st.cache_data
def songs():
    features=document("clustering/models.json.gz")["preprocessing"]["features"]
    frame=pd.read_csv(api.ROOT/"data/public/songs.csv",keep_default_na=False,na_values=[""]).dropna(subset=features)
    frame=frame.loc[frame.last_chart_date.lt("2026-01-01")].sort_values(["title","artist","song_id"]).set_index("song_id",drop=False)
    return frame


def song_choice(frame,key):
    return st.selectbox("Example song",frame.index.tolist(),format_func=lambda i:f"{frame.loc[i,'title']} — {frame.loc[i,'artist']}",key=key)


def classification():
    st.subheader("Predict from the 42 lyrical scores")
    models=document("classification/models.json.gz")
    target=st.selectbox("Target",["top10","long_chart","broad_genre"],format_func=lambda x:{"top10":"Reached the Billboard Top 10","long_chart":"Long chart longevity","broad_genre":"Broad primary genre"}[x],key="target")
    year=st.selectbox("Historical evaluation begins",[2018,2010,2000,1990],key="evaluation_year")
    result=models[f"{target}_{year}"];algorithm=st.radio("Classifier",["Decision tree","Naïve Bayes","IF–THEN rules"],horizontal=True,key="classifier")
    method="naive_bayes" if algorithm=="Naïve Bayes" else "tree";model=result["models"][method]
    st.caption(result["prediction_scenario"]+". Evaluation uses whole song histories within the displayed years; no final chart variables enter the model.")
    if target=="long_chart":st.write(f"Long longevity means more than {result['threshold']:g} observed chart weeks in this historical fold.")
    scores=table("classification/evaluation.csv");scores=scores[(scores.target==target)&(scores.start==year)]
    view=scores[scores.method.isin(["tree","naive_bayes","majority","stratified"])][["method","n","accuracy","balanced_accuracy","precision_macro","recall_macro","f1_macro","f1_weighted"]]
    st.dataframe(view,hide_index=True,width="stretch")
    st.caption("Majority and stratified baselines use training class frequencies. Balanced accuracy is mean recall over represented classes. Classifier scores and model probabilities are not ground truth or calibrated probabilities.")
    frame=songs();start,end=result["period"];examples=frame[(frame.first_chart_date>=f"{start}-01-01")&(frame.last_chart_date<f"{end}-01-01")]
    sid=song_choice(examples,"classification_song");values=examples.loc[sid,model["features"]].to_numpy(float).copy()
    manual=st.checkbox("Adjust one lyrical score",key="manual_input")
    if manual:
        feature=st.selectbox("Score to adjust",model["features"],key="manual_feature")
        value=st.number_input("Score value",min_value=0.,max_value=1.,value=float(values[model["features"].index(feature)]),step=.01,format="%.5f",key="manual_value")
        values[model["features"].index(feature)]=value
        st.caption("The other 41 scores retain the example song's values. This changes the example prediction, not the saved evaluation.")
    prediction,prob,leaf=api.predict(model,values)
    st.metric("Model prediction",str(prediction[0]));st.session_state["last_prediction"]=str(prediction[0]);st.session_state["input_song_id"]=sid
    if not manual:
        observed=examples.loc[sid,"broad_genre"] if "broad_genre" in examples else None
        if target=="top10":observed="yes" if examples.loc[sid,"best_chart_rank"]<=10 else "no"
        elif target=="long_chart":observed="yes" if examples.loc[sid,"chart_weeks"]>result["threshold"] else "no"
        else:
            genre=examples.loc[sid,"primary_genre"];observed=genre if genre in model["classes"] else "Other broad genre"
        st.write("Observed target:",observed)
    st.dataframe(pd.DataFrame({"class":model["classes"],"uncalibrated_model_probability":prob[0]}),hide_index=True)
    if method=="tree":
        rule=next(r for r in model["rules"] if r["leaf_id"]==leaf[0])
        st.code(api.rule_text(rule),language=None)
        st.caption(f"This leaf contains {rule['training_n']:,} training songs. The complete rule classifier exactly reproduces tree predictions.")
        with st.expander("All IF–THEN rules"):
            st.dataframe(pd.DataFrame([{k:v for k,v in r.items() if k in {"leaf_id","training_n","prediction"}}|{"rule":api.rule_text(r)} for r in model["rules"]]),hide_index=True,width="stretch")
    matrices=document("classification/confusion_matrices.json");matrix=next(x for x in matrices if x["target"]==target and x["start"]==year and x["method"]==method)
    st.write("Confusion matrix: actual rows × predicted columns")
    st.dataframe(pd.DataFrame(matrix["matrix"],index=matrix["classes"],columns=matrix["classes"]),width="stretch")
    historical=table("classification/evaluation.csv");historical=historical[(historical.target==target)&historical.method.isin(["tree","naive_bayes","majority"])]
    st.line_chart(historical.pivot(index="start",columns="method",values="balanced_accuracy"))
    with st.expander("Class imbalance, uncertainty and exact-artist-credit checks"):
        st.write("Training class counts",result["train_class_counts"]);st.write("Evaluation class counts",result["test_class_counts"])
        for name in ("uncertainty.csv","subgroup_metrics.csv"):
            detail=table("classification/"+name);st.dataframe(detail[(detail.target==target)&(detail.start==year)],hide_index=True,width="stretch")


def frequent_patterns():
    st.subheader("Equivalent frequent itemsets from three algorithms")
    st.dataframe(table("frequent_patterns/algorithm_comparison.csv"),hide_index=True,width="stretch")
    support=st.selectbox("Minimum training support",[.08,.05,.12],key="support")
    rows=table(f"frequent_patterns/itemsets_support_{support:.2f}.csv.gz")
    kind=st.radio("Itemset collection",["All frequent","Closed","Maximal"],horizontal=True,key="itemset_kind")
    if kind!="All frequent":rows=rows[rows[kind.lower()]]
    query=st.text_input("Contains text",key="itemset_query")
    if query:rows=rows[rows["items"].str.contains(query,case=False,regex=False)]
    st.metric("Matching itemsets",len(rows));st.dataframe(rows.sort_values(["size","support"],ascending=[False,False]).head(500),hide_index=True,width="stretch")
    st.caption("Shows at most 500 rows. Exact global closure/maximality checks include possible extensions beyond the size-four publication cap. Low/high bins come only from pre-2010 training quartiles; middle values emit no tail item.")


def association_rules():
    st.subheader("Historical associations and conditional rules")
    collection=st.radio("Rule collection",["Presentation shortlist","All searched rules"],horizontal=True,key="rule_collection")
    name="presentation_shortlist.csv" if collection=="Presentation shortlist" else "all_rules.csv.gz"
    rows=table("association_rules/"+name)
    query=st.text_input("Rule contains text",key="rule_query")
    if query:rows=rows[rows.antecedent.str.contains(query,case=False,regex=False)|rows.consequent.str.contains(query,case=False,regex=False)]
    st.write(f"{len(rows):,} rules match. The complete compressed table retains every searched rule, including null and overlapping measurements.")
    if rows.empty:return
    rows=rows.sort_values(["stable_positive","test_antecedent_n","rule_id"],ascending=[False,False,True])
    lookup=rows.set_index("rule_id");rid=st.selectbox("Rule",lookup.index.tolist(),format_func=lambda x:api.rule_text(lookup.loc[x].to_dict()),key="association_rule")
    row=lookup.loc[rid].to_dict();st.code(api.rule_text(row),language=None);st.session_state["selected_rule"]=rid
    performance=[]
    for split in ("train","validation","test"):
        performance.append(dict(split=split,**{name:row[split+"_"+name] for name in ["n","antecedent_n","joint_n","support","confidence","baseline","lift","leverage","confidence_gain_vs_best_parent"]}))
    st.dataframe(pd.DataFrame(performance),hide_index=True,width="stretch")
    st.write("Relationship:",row["category"],"· Global BY q:",row["q_by_global"])
    st.caption("These are retrospective associations. Confidence must be compared with the consequent's baseline and simpler parent rules. Negative numerical items require an observed value outside the named bin. BY correction covers all searched rules under the debut-year-stratified test assumptions; repeated artists and prior inspection limit inference.")
    history=table("association_rules/historical_and_genre_stability.csv");history=history[history.rule_id==rid]
    if len(history):st.dataframe(history,hide_index=True,width="stretch")
    else:st.caption("Detailed subgroup display is limited to the declared presentation shortlist; training/validation/test results above cover this rule.")


def clustering():
    st.subheader("Lyrical-score clusters")
    exported=document("clustering/models.json.gz");options=list(exported["models"])
    default=options.index("kmeans_standardized42_k3") if "kmeans_standardized42_k3" in options else 0
    key=st.selectbox("Configuration",options,index=default,key="cluster_configuration");model=exported["models"][key]
    selection=table("clustering/selected_configurations.csv");st.dataframe(selection[selection.configuration==key],hide_index=True,width="stretch")
    if not model["selection_supported"]:st.warning("No configuration for this method/representation passed both the size and resample-stability criteria. This is the best silhouette fallback, not an endorsed cluster solution.")
    if model["method"]=="hierarchical":st.caption("Ward clustering was fit to a seeded 1,200-song training sample. Other songs are assigned to its nearest cluster centroid; this is a transfer approximation.")
    elif model["method"]=="kmedoids":st.caption("Alternating k-medoids was fit to a seeded 1,200-song sample. The medoids are actual training songs.")
    frame=songs();sid=song_choice(frame,"cluster_song");features=exported["preprocessing"]["features"]
    group=int(api.cluster_predict(model,exported["preprocessing"],frame.loc[sid,features].to_numpy(float))[0]);st.metric("Assigned cluster",group);st.session_state["last_cluster"]=group
    profiles=table("clustering/profiles.csv");profiles=profiles[(profiles.configuration==key)&(profiles.cluster==group)]
    profiles=profiles.assign(magnitude=profiles.standardized_mean.abs()).sort_values("magnitude",ascending=False)
    st.bar_chart(profiles.head(12).set_index("feature")[["standardized_mean"]]);st.caption("Profile means are in pre-2010 training standard deviations. Cluster numbers are arbitrary labels; these are classifier-score profiles, not validated musical categories.")
    genres=table("clustering/genre_composition.csv");st.dataframe(genres[(genres.configuration==key)&(genres.cluster==group)],hide_index=True,width="stretch")
    history=table("clustering/historical_prevalence.csv");history=history[history.configuration==key]
    st.line_chart(history.pivot(index="decade",columns="cluster",values="share"))
    st.caption("One song per exact identity; complete scores and histories ending before 2026. Historical prevalence is descriptive and does not identify a COVID effect.")
    chart=table("clustering/chart_distributions.csv");st.dataframe(chart[chart.configuration==key],hide_index=True,width="stretch")
    with st.expander("All 99 configurations and stability"):
        st.dataframe(table("clustering/grid.csv"),hide_index=True,width="stretch")


st.title("CMPT 491 · Data-mining methods")
st.caption("Saved models and measured results · public song data · no searches or model fitting in the demonstration")
view=st.sidebar.radio("View",["Classification","Frequent patterns","Association rules","Clustering"],key="view")
{"Classification":classification,"Frequent patterns":frequent_patterns,"Association rules":association_rules,"Clustering":clustering}[view]()
