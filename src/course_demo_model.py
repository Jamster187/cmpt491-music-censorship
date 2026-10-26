"""Read-only, NumPy-only inference for the professor demonstration.

Independent replay of the public numeric model exports; no pickle or fitting.
The existing Python 3.11 Streamlit environment needs no added ML dependency.
"""
from pathlib import Path
import gzip
import json

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"analysis/course_methods"


def read_json(path):
    path=Path(path);raw=path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix==".gz" else raw)


def predict(model,values):
    x=np.atleast_2d(np.asarray(values,float));classes=np.array(model["classes"])
    if model["kind"]=="decision_tree":
        x=x.astype(np.float32);probabilities=[];leaf=[]
        for row in x:
            node=0
            while model["children_left"][node]!=-1:
                f=model["feature"][node];left=float(row[f])<=model["threshold"][node]
                node=model["children_left" if left else "children_right"][node]
            values=np.asarray(model["values"][node],float);probabilities.append(values/values.sum());leaf.append(node)
        probabilities=np.array(probabilities)
        return classes[probabilities.argmax(axis=1)],probabilities,leaf
    if model["kind"]!="gaussian_nb":raise ValueError("Unsupported public model")
    z=(x-np.asarray(model["mean"]))/np.asarray(model["scale"]);joint=[]
    for prior,mean,var in zip(model["class_prior"],model["theta"],model["variance"]):
        variance=np.asarray(var)
        joint.append(np.log(prior)-.5*(np.log(2*np.pi*variance)+(z-mean)**2/variance).sum(axis=1))
    joint=np.array(joint).T;weights=np.exp(joint-joint.max(axis=1,keepdims=True));prob=weights/weights.sum(axis=1,keepdims=True)
    return classes[prob.argmax(axis=1)],prob,None


def cluster_transform(values,preprocessing,representation):
    x=np.atleast_2d(np.asarray(values,float));z=(x-np.asarray(preprocessing["mean"]))/np.asarray(preprocessing["scale"])
    if representation=="standardized42":return z
    if representation=="family_balanced":return z*np.asarray(preprocessing["family_weights"])
    if representation=="pca90":return (z-np.asarray(preprocessing["pca_mean"]))@np.asarray(preprocessing["pca_components"]).T
    raise ValueError("Unknown feature representation")


def cluster_predict(model,preprocessing,values):
    transformed=cluster_transform(values,preprocessing,model["representation"]);centers=np.asarray(model["centers"])
    # Centers are small (at most 12); no quadratic song-by-song matrix.
    distances=np.column_stack([np.sum((transformed-center)**2,axis=1) for center in centers])
    return distances.argmin(axis=1)


def rule_text(rule):
    conditions=rule.get("conditions")
    if conditions is not None:
        left=" AND ".join(f"{v['feature']} {v['operator']} {v['threshold']:.6g}" for v in conditions)
        return "IF "+left+" THEN "+rule["prediction"]
    ant=rule["antecedent"]
    if isinstance(ant,str):ant=json.loads(ant)
    right=("observed NOT " if rule.get("negative_consequent") else "")+rule["consequent"]
    return "IF "+" AND ".join(ant)+" THEN "+right
