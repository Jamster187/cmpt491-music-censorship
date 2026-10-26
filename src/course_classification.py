"""Chronological tree, Gaussian Bayes and exactly equivalent IF–THEN classifiers."""
from __future__ import annotations
from collections import Counter
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from threadpoolctl import threadpool_limits

import course_common as c

TARGETS=["top10","long_chart","broad_genre"]


def target(frame,name,threshold):
    if name=="top10":return np.where(frame.best_chart_rank<=10,"yes","no")
    if name=="long_chart":return np.where(frame.chart_weeks>threshold,"yes","no")
    if name=="broad_genre":return frame.broad_genre.to_numpy(str)
    raise ValueError(name)


def labels(name):return sorted(c.GENRES+["Other broad genre"]) if name=="broad_genre" else ["no","yes"]


def confusion(y,pred,classes,weights=None):
    lookup={label:i for i,label in enumerate(classes)}
    a=np.array([lookup[v] for v in y]);b=np.array([lookup[v] for v in pred]);k=len(classes)
    return np.bincount(a*k+b,weights=weights,minlength=k*k).reshape(k,k)


def from_confusion(matrix):
    matrix=np.asarray(matrix,float);actual=matrix.sum(axis=1);predicted=matrix.sum(axis=0);tp=np.diag(matrix);n=actual.sum()
    precision=np.divide(tp,predicted,out=np.zeros_like(tp),where=predicted>0)
    recall=np.divide(tp,actual,out=np.zeros_like(tp),where=actual>0)
    f1=np.divide(2*precision*recall,precision+recall,out=np.zeros_like(tp),where=(precision+recall)>0)
    return dict(n=int(n),accuracy=float(tp.sum()/n) if n else None,
        balanced_accuracy=float(recall[actual>0].mean()) if n else None,
        precision_macro=float(precision.mean()),recall_macro=float(recall.mean()),f1_macro=float(f1.mean()),
        precision_weighted=float(precision@actual/n) if n else None,recall_weighted=float(recall@actual/n) if n else None,
        f1_weighted=float(f1@actual/n) if n else None,
        precision_positive=float(precision[-1]) if len(tp)==2 else None,
        recall_positive=float(recall[-1]) if len(tp)==2 else None,
        per_class=[dict(precision=p,recall=r,f1=f,support=int(s)) for p,r,f,s in zip(precision,recall,f1,actual)])


def metrics(y,pred,classes):return from_confusion(confusion(y,pred,classes))


def export_tree(model,train_x,train_y):
    tree=model.tree_;leaves=model.apply(train_x);rules=[]
    def walk(node,conditions):
        if tree.children_left[node]<0:
            observed=train_y[leaves==node];counts=Counter(observed)
            probabilities=np.asarray(tree.value[node,0],float);probabilities=probabilities/probabilities.sum()
            rules.append(dict(leaf_id=int(node),conditions=conditions,prediction=str(model.classes_[np.argmax(probabilities)]),
                training_n=int((leaves==node).sum()),training_class_counts={str(k):int(v) for k,v in sorted(counts.items())},
                model_probabilities=probabilities.tolist()))
        else:
            name=c.SCORES[tree.feature[node]];threshold=float(tree.threshold[node])
            walk(tree.children_left[node],conditions+[dict(feature=name,operator="<=",threshold=threshold)])
            walk(tree.children_right[node],conditions+[dict(feature=name,operator=">",threshold=threshold)])
    walk(0,[])
    return dict(kind="decision_tree",features=c.SCORES,classes=model.classes_.tolist(),
        children_left=tree.children_left.tolist(),children_right=tree.children_right.tolist(),
        feature=tree.feature.tolist(),threshold=tree.threshold.tolist(),values=tree.value[:,0,:].tolist(),rules=rules,
        feature_importance=model.feature_importances_.tolist(),input_precision="float32, as scikit-learn tree prediction")


def export_bayes(model,scaler):
    return dict(kind="gaussian_nb",features=c.SCORES,classes=model.classes_.tolist(),mean=scaler.mean_.tolist(),
        scale=scaler.scale_.tolist(),theta=model.theta_.tolist(),variance=model.var_.tolist(),
        class_prior=model.class_prior_.tolist(),epsilon=float(model.epsilon_),
        probability_note="Model probabilities are uncalibrated; correlated features violate conditional independence")


def predict_export(model,values):
    x=np.asarray(values,float);classes=np.array(model["classes"])
    if model["kind"]=="decision_tree":
        x=x.astype(np.float32);probs=[];leaves=[]
        for row in x:
            node=0
            while model["children_left"][node]>=0:
                node=model["children_left"][node] if row[model["feature"][node]]<=model["threshold"][node] else model["children_right"][node]
            prob=np.array(model["values"][node]);probs.append(prob/prob.sum());leaves.append(node)
        probabilities=np.array(probs)
        return classes[probabilities.argmax(axis=1)],probabilities,np.array(leaves)
    if model["kind"]!="gaussian_nb":raise ValueError("Unknown model")
    z=(x-np.array(model["mean"]))/np.array(model["scale"]);theta=np.array(model["theta"]);var=np.array(model["variance"])
    joint=np.log(model["class_prior"])[None,:]-.5*np.log(2*np.pi*var).sum(axis=1)[None,:]-.5*((z[:,None,:]-theta[None,:,:])**2/var[None,:,:]).sum(axis=2)
    joint-=joint.max(axis=1)[:,None];probabilities=np.exp(joint);probabilities/=probabilities.sum(axis=1)[:,None]
    return classes[probabilities.argmax(axis=1)],probabilities,None


def predict_rules(rules,features,values):
    """Rule-based classifier evaluated without traversing the original tree."""
    x=np.asarray(values,np.float32);out=np.full(len(x),"",dtype=object);matched=np.zeros(len(x),int)
    indexes={name:i for i,name in enumerate(features)}
    for rule in rules:
        mask=np.ones(len(x),bool)
        for cond in rule["conditions"]:
            v=x[:,indexes[cond["feature"]]].astype(float)
            mask &= v<=cond["threshold"] if cond["operator"]=="<=" else v>cond["threshold"]
        out[mask]=rule["prediction"];matched[mask]+=1
    if not np.all(matched==1):raise AssertionError("Rules must cover every row exactly once")
    return out.astype(str)


def bootstrap_difference(y,pred,base,classes,group_ids,seed):
    """Fixed-model cluster intervals; avoids refits and preserves within-cluster songs."""
    unique=sorted(set(group_ids));blocks=[]
    for group in unique:
        mask=group_ids==group
        blocks.append((confusion(y[mask],pred[mask],classes),confusion(y[mask],base[mask],classes)))
    first=np.array([x[0] for x in blocks]);second=np.array([x[1] for x in blocks]);rng=np.random.default_rng(seed)
    values=[]
    for _ in range(c.CONFIG["bootstrap_repeats"]):
        index=rng.integers(0,len(blocks),len(blocks));a=from_confusion(first[index].sum(axis=0));b=from_confusion(second[index].sum(axis=0))
        values.append([a["balanced_accuracy"]-b["balanced_accuracy"],a["f1_macro"]-b["f1_macro"]])
    q=np.quantile(values,[.025,.975],axis=0)
    return dict(groups=len(blocks),balanced_accuracy_gain_low=q[0,0],balanced_accuracy_gain_high=q[1,0],
                macro_f1_gain_low=q[0,1],macro_f1_gain_high=q[1,1],repeats=len(values))


def fit_fold(frame,name,start,end):
    inner_train,validation=c.partitions(frame,start-5,start)
    train,test=c.partitions(frame,start,end)
    if min(len(inner_train),len(validation),len(test))<100:raise ValueError("Insufficient temporal coverage")
    threshold=float(inner_train.chart_weeks.quantile(.75));classes=labels(name)
    x_inner=inner_train[c.SCORES].to_numpy(float);x_val=validation[c.SCORES].to_numpy(float)
    x_train=train[c.SCORES].to_numpy(float);x_test=test[c.SCORES].to_numpy(float)
    y_inner=target(inner_train,name,threshold);y_val=target(validation,name,threshold)
    y_train=target(train,name,threshold);y_test=target(test,name,threshold)
    candidates=[]
    for depth in c.CONFIG["tree_depths"]:
        for weight in c.CONFIG["tree_class_weights"]:
            model=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=c.CONFIG["minimum_leaf"],class_weight=weight,random_state=c.SEED).fit(x_inner,y_inner)
            measured=metrics(y_val,model.predict(x_val),classes);measured.pop("per_class")
            candidates.append(dict(depth=depth,class_weight=weight,**measured))
    selected=sorted(candidates,key=lambda r:(-r["balanced_accuracy"],-r["f1_macro"],r["depth"],r["class_weight"] is not None))[0]
    tree=DecisionTreeClassifier(max_depth=selected["depth"],min_samples_leaf=c.CONFIG["minimum_leaf"],class_weight=selected["class_weight"],random_state=c.SEED).fit(x_train,y_train)
    scaler=StandardScaler().fit(x_train);bayes=GaussianNB(var_smoothing=1e-9).fit(scaler.transform(x_train),y_train)
    exports=dict(tree=export_tree(tree,x_train,y_train),naive_bayes=export_bayes(bayes,scaler))
    counts=Counter(y_train);majority=sorted(counts,key=lambda x:(-counts[x],x))[0]
    rng=np.random.default_rng(c.SEED);prob=np.array([counts[x] for x in classes],float);prob/=prob.sum()
    predictions=dict(tree=tree.predict(x_test),naive_bayes=bayes.predict(scaler.transform(x_test)),
        rules=predict_rules(exports["tree"]["rules"],c.SCORES,x_test),
        majority=np.repeat(majority,len(test)),stratified=rng.choice(classes,len(test),p=prob))
    for method in ("tree","naive_bayes"):
        replay,probabilities,_=predict_export(exports[method],x_test)
        np.testing.assert_array_equal(replay,predictions[method])
        native=tree.predict_proba(x_test) if method=="tree" else bayes.predict_proba(scaler.transform(x_test))
        np.testing.assert_allclose(probabilities,native,atol=1e-12,rtol=1e-10)
    np.testing.assert_array_equal(predictions["tree"],predictions["rules"])
    evaluations=[];uncertainty=[];subgroups=[]
    seen=test.artist.isin(train.artist).to_numpy()
    for method,pred in predictions.items():
        measured=metrics(y_test,pred,classes)
        evaluations.append(dict(method=method,**measured,confusion_matrix=confusion(y_test,pred,classes).tolist()))
        if method in ("tree","naive_bayes"):
            for group_name,groups in [("artist_credit",test.artist.to_numpy()),("two_year_block",(test.year//2).to_numpy())]:
                uncertainty.append(dict(method=method,resampling=group_name,**bootstrap_difference(y_test,pred,predictions["majority"],classes,groups,c.SEED)))
        masks=[("artist","unseen_exact_credit",~seen),("artist","seen_exact_credit",seen)]
        masks += [("genre",g,test.primary_genre.eq(g).to_numpy()) for g in sorted(test.primary_genre.unique())]
        masks += [("period",g,test.period.eq(g).to_numpy()) for g in sorted(test.period.unique())]
        for kind,group,mask in masks:
            if mask.sum()<100:
                subgroups.append(dict(method=method,group_type=kind,group=group,n=int(mask.sum()),adequate=False));continue
            mm=metrics(y_test[mask],pred[mask],classes);mm.pop("per_class")
            subgroups.append(dict(method=method,group_type=kind,group=group,adequate=True,**mm))
    rules=[];leaf_ids=tree.apply(x_test)
    for rule in exports["tree"]["rules"]:
        mask=leaf_ids==rule["leaf_id"]
        rules.append(dict(**rule,test_n=int(mask.sum()),test_accuracy=float((y_test[mask]==rule["prediction"]).mean()) if mask.any() else None,
            text="IF "+" AND ".join(f"{v['feature']} {v['operator']} {v['threshold']:.8g}" for v in rule["conditions"])+" THEN "+rule["prediction"]))
    return dict(target=name,period=[start,end],inner_train_n=len(inner_train),validation_n=len(validation),train_n=len(train),test_n=len(test),
        threshold=threshold,classes=classes,selection=selected,validation_candidates=candidates,
        train_class_counts=dict(counts),test_class_counts=dict(Counter(y_test)),
        input_features=c.SCORES,prediction_scenario=c.CONFIG["chart_prediction_scenario"] if name!="broad_genre" else "Broad primary genre inferred from lyrics; classified genre label is not ground truth",
        seen_artist_share=float(seen.mean()),evaluations=evaluations,uncertainty=uncertainty,subgroups=subgroups,
        models=exports,rules=rules,song_ids=test.song_id.tolist(),truth=y_test.tolist(),predictions={k:v.tolist() for k,v in predictions.items()},
        split_hashes={n:c.digest(f.song_id.tolist()) for n,f in [("inner_train",inner_train),("validation",validation),("train",train),("test",test)]},
        training_feature_summary=dict(median=np.median(x_train,axis=0).tolist(),minimum=x_train.min(axis=0).tolist(),maximum=x_train.max(axis=0).tolist()))


def run():
    started=time.perf_counter();c.freeze();frame=c.data();results=[];runtimes=[]
    for name in TARGETS:
        for start,end in c.OUTER:
            t=time.perf_counter()
            result,reused=c.checkpoint(f"classification/{name}_{start}",lambda:fit_fold(frame,name,start,end),["src/course_classification.py"])
            results.append(result);runtimes.append(dict(target=name,start=start,reused=reused,seconds=time.perf_counter()-t))
            print(name,start,"depth",result["selection"]["depth"],[(r["method"],round(r["balanced_accuracy"],3)) for r in result["evaluations"]],flush=True)
    evaluations=[];validation=[];rules=[];uncertainty=[];subgroups=[];confusions=[];class_metrics=[];models={};prediction_rows=[]
    for r in results:
        ident=dict(target=r["target"],start=r["period"][0],end=r["period"][1],threshold=r["threshold"])
        for v in r["evaluations"]:
            evaluations.append(dict(**ident,train_n=r["train_n"],test_n=r["test_n"],selected_depth=r["selection"]["depth"],selected_class_weight=r["selection"]["class_weight"],**{k:x for k,x in v.items() if k not in {"per_class","confusion_matrix"}}))
            confusions.append(dict(**ident,method=v["method"],classes=r["classes"],matrix=v["confusion_matrix"]))
            class_metrics += [dict(**ident,method=v["method"],label=label,**x) for label,x in zip(r["classes"],v["per_class"])]
        validation += [dict(**ident,**v) for v in r["validation_candidates"]]
        rules += [dict(**ident,**v) for v in r["rules"]]
        uncertainty += [dict(**ident,**v) for v in r["uncertainty"]]
        subgroups += [dict(**ident,**v) for v in r["subgroups"]]
        for i,song_id in enumerate(r["song_ids"]):
            prediction_rows.append(dict(**ident,song_id=song_id,truth=r["truth"][i],**{name:values[i] for name,values in r["predictions"].items()}))
        key=f"{r['target']}_{r['period'][0]}"
        models[key]={k:v for k,v in r.items() if k in {"models","target","period","threshold","selection","train_n","test_n","prediction_scenario","training_feature_summary","train_class_counts","test_class_counts","seen_artist_share","split_hashes","inner_train_n","validation_n"}}
    for filename,rows in [("evaluation.csv",evaluations),("validation_grid.csv",validation),("rules.csv",rules),
                          ("uncertainty.csv",uncertainty),("subgroup_metrics.csv",subgroups),("per_class_metrics.csv",class_metrics),
                          ("predictions.csv.gz",prediction_rows)]:c.write_csv(c.PUBLIC/"classification"/filename,rows)
    c.write_json(c.PUBLIC/"classification/models.json.gz",models)
    c.write_json(c.PUBLIC/"classification/confusion_matrices.json",confusions)
    c.write_json(c.PUBLIC/"classification/execution.json",dict(folds=len(results),tree_candidates=len(validation),
        native_and_exported_predictions_equal=True,tree_and_rules_equal=True,runtimes=runtimes,**c.usage(started)))


if __name__=="__main__":
    with threadpool_limits(limits=1):run()
