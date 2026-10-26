"""Public-output replay, selected refits, checkpoint validation and preservation audit."""
from __future__ import annotations
import argparse
import itertools
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import silhouette_score
from threadpoolctl import threadpool_limits

import course_common as c
import course_patterns as patterns
import course_classification as classification
import course_clustering as clustering
import course_demo_model as demo

OPERATIONAL_ARTIFACTS={"analysis/course_methods/"+name for name in (
    "preparation.json","report_execution.json","validation.json","replay_validation.json","test_results.json",
    "frequent_patterns/execution.json","classification/execution.json","clustering/execution.json")}


def read_csv(name):return pd.read_csv(c.PUBLIC/name,float_precision="round_trip")


def close(actual,expected,name):
    if expected is None or pd.isna(expected):
        if actual is not None and not pd.isna(actual):raise AssertionError(name)
    else:np.testing.assert_allclose(actual,expected,rtol=3e-12,atol=1e-13,err_msg=name)


def verify_patterns(train,validation,test):
    schema=c.read_json(c.PUBLIC/"frequent_patterns/transaction_schema.json")
    assert schema["bins"]==patterns.fit_bins(train)
    assert schema["longevity_threshold"]==float(train.chart_weeks.quantile(.75))
    frames=dict(train=train,validation=validation,test=test)
    tx={name:patterns.transactions(f,schema["bins"],schema["longevity_threshold"]) for name,f in frames.items()}
    assert {name:c.digest(rows) for name,rows in tx.items()}==schema["transaction_hashes"]
    index={name:patterns.vertical(rows) for name,rows in tx.items()};full={name:(1<<len(f))-1 for name,f in frames.items()}
    benchmarks=read_csv("frequent_patterns/algorithm_comparison.csv")
    assert len(benchmarks)==9 and benchmarks.equivalent.all()
    checked=0
    for support in c.CONFIG["frequent_supports"]:
        saved=read_csv(f"frequent_patterns/itemsets_support_{support:.2f}.csv.gz");actual={}
        for row in saved.itertuples():
            items=tuple(json.loads(row.items));assert patterns.compatible(items) and 1<=len(items)<=4
            n=patterns.count(patterns.intersection(items,index["train"],full["train"]))
            assert n==row.count and n>=np.ceil(support*len(train));close(n/len(train),row.support,"itemset support")
            actual[items]=n;checked+=1
        hashes=benchmarks[benchmarks.support_threshold==support].result_sha256
        assert hashes.nunique()==1 and hashes.iloc[0]==c.digest([[list(k),v] for k,v in sorted(actual.items())])
        # Enumeration independent of the published Apriori/FP trees, all support counts.
        assert patterns.eclat(tx["train"],int(np.ceil(support*len(train))),4)==actual
        # Full extension checks on an outcome-blind deterministic sample of each size.
        sample=saved.assign(order=saved["items"].map(lambda x:c.digest(x))).sort_values("order").groupby("size",group_keys=False).head(12)
        for row in sample.itertuples():
            items=tuple(json.loads(row.items));bits=patterns.intersection(items,index["train"],full["train"])
            extensions=[patterns.count(bits&v) for i,v in index["train"].items() if patterns.variable(i) not in {patterns.variable(x) for x in items}]
            assert bool(row.closed)==(row.count not in extensions)
            assert bool(row.maximal)==(max(extensions,default=0)<np.ceil(support*len(train)))
    rules=read_csv("association_rules/all_rules.csv.gz")
    assert rules.rule_id.is_unique and len(rules)>10000
    np.testing.assert_allclose(stats.false_discovery_control(rules.p_value.to_numpy(),method="by"),rules.q_by_global,rtol=5e-12,atol=1e-14)
    cache={};year_masks=[patterns.bitmask(test.year.to_numpy()==year) for year in sorted(test.year.unique())]
    rule_checks=0
    for row in rules.to_dict("records"):
        ant=tuple(json.loads(row["antecedent"]));con=row["consequent"];negative=bool(row["negative_consequent"])
        assert 1<=len(ant)<=3 and patterns.compatible([*ant,con])
        assert row["rule_id"]==c.digest([ant,con,negative])[:16]
        assert row["strict_cross_domain"]==all(patterns.domain(a)!=patterns.domain(con) for a in ant)
        for name in frames:
            key=(name,con,negative)
            if key not in cache:cache[key]=patterns.outcome_bits(con,negative,index[name],full[name],frames[name])
            b,universe=cache[key];a=patterns.intersection(ant,index[name],universe)
            n=patterns.count(universe);na=patterns.count(a);nb=patterns.count(b);joint=patterns.count(a&b)
            assert row[name+"_n"]==n and row[name+"_antecedent_n"]==na and row[name+"_consequent_n"]==nb and row[name+"_joint_n"]==joint
            close(joint/n,row[name+"_support"],"rule support")
            confidence=joint/na if na else None;close(confidence,row[name+"_confidence"],"rule confidence")
            close(confidence/(nb/n) if na and nb else None,row[name+"_lift"],"rule lift")
            close(joint/n-na*nb/n**2,row[name+"_leverage"],"rule leverage")
            if name=="test":
                # Recompute stratified 2x2 expected counts directly, not through cmh_p.
                tables=[]
                for year_mask in year_masks:
                    m=year_mask&universe;aa=patterns.count(a&m);bb=patterns.count(b&m);ab=patterns.count(a&b&m);total=patterns.count(m)
                    tables.append([ab,aa-ab,bb-ab,total-aa-bb+ab])
                observed=np.array(tables,float).reshape(-1,2,2)
                total=observed.sum(axis=(1,2));r=observed.sum(axis=2)[:,0];s=observed.sum(axis=1)[:,0]
                valid=total>1;total=total[valid];r=r[valid];s=s[valid]
                difference=np.sum(observed[valid,0,0]-r*s/total)
                variance=np.sum(r*s*(total-r)*(total-s)/(total**2*(total-1)))
                expected=float(stats.chi2.sf(difference**2/variance,1)) if row["test_supported"] and variance>0 else 1.
                close(expected,row["p_value"],"year-stratified CMH p")
            rule_checks+=1
    return dict(itemsets_counted=checked,rules=len(rules),rule_split_metrics_replayed=rule_checks,
        global_by_hypotheses=len(rules),algorithm_equivalence=True,closure_checked_beyond_size_cap=True)


def verify_classification(frame):
    models=c.read_json(c.PUBLIC/"classification/models.json.gz");predictions=read_csv("classification/predictions.csv.gz")
    evaluation=read_csv("classification/evaluation.csv");grid=read_csv("classification/validation_grid.csv")
    matrices=c.read_json(c.PUBLIC/"classification/confusion_matrices.json");folds=0;rows_checked=0
    for key,record in models.items():
        start,end=record["period"];name=record["target"];train,test=c.partitions(frame,start,end);inner,val=c.partitions(frame,start-5,start)
        assert record["threshold"]==float(inner.chart_weeks.quantile(.75))
        assert record["split_hashes"]=={n:c.digest(f.song_id.tolist()) for n,f in [("inner_train",inner),("validation",val),("train",train),("test",test)]}
        saved=predictions[(predictions.target==name)&(predictions.start==start)].set_index("song_id").loc[test.song_id]
        y=classification.target(test,name,record["threshold"]);classes=classification.labels(name)
        np.testing.assert_array_equal(y,saved.truth)
        x=test[c.SCORES].to_numpy(float)
        candidates=grid[(grid.target==name)&(grid.start==start)].to_dict("records")
        assert len(candidates)==8
        candidates.sort(key=lambda r:(-r["balanced_accuracy"],-r["f1_macro"],r["depth"],not pd.isna(r["class_weight"])))
        assert candidates[0]["depth"]==record["selection"]["depth"]
        chosen_weight=None if pd.isna(candidates[0]["class_weight"]) else candidates[0]["class_weight"]
        assert chosen_weight==record["selection"]["class_weight"]
        bayes=record["models"]["naive_bayes"]
        np.testing.assert_allclose(bayes["mean"],train[c.SCORES].to_numpy().mean(axis=0),atol=1e-13)
        np.testing.assert_allclose(bayes["scale"],train[c.SCORES].to_numpy().std(axis=0),atol=1e-13)
        for method in ("tree","naive_bayes"):
            pred,prob,_=demo.predict(record["models"][method],x)
            np.testing.assert_array_equal(pred,saved[method]);np.testing.assert_allclose(prob.sum(axis=1),1,atol=1e-13)
            if method=="tree":
                rule_pred=classification.predict_rules(record["models"][method]["rules"],c.SCORES,x)
                np.testing.assert_array_equal(pred,rule_pred);np.testing.assert_array_equal(pred,saved.rules)
        for method in ("tree","naive_bayes","rules","majority","stratified"):
            measured=classification.metrics(y,saved[method].to_numpy(),classes)
            expected=evaluation[(evaluation.target==name)&(evaluation.start==start)&(evaluation.method==method)].iloc[0]
            for metric,value in measured.items():
                if metric!="per_class":close(value,expected[metric],"classification "+metric)
            matrix=next(r for r in matrices if r["target"]==name and r["start"]==start and r["method"]==method)
            np.testing.assert_array_equal(classification.confusion(y,saved[method].to_numpy(),classes),matrix["matrix"])
            rows_checked+=len(test)
        folds+=1
    assert folds==12
    return dict(folds=folds,predictions_checked=rows_checked,independent_demo_inference=True,tree_rules_equal=True,training_only_scalers=True)


def verify_clustering(frame,train,validation,test):
    exported=c.read_json(c.PUBLIC/"clustering/models.json.gz");pre=exported["preprocessing"]
    definition=clustering.representations(train)
    for name in ("mean","scale","pca_components","pca_explained_variance_ratio","family_weights"):
        np.testing.assert_allclose(definition[name],pre[name],rtol=1e-11,atol=1e-12)
    grid=read_csv("clustering/grid.csv");selected=read_csv("clustering/selected_configurations.csv");assignments=read_csv("clustering/assignments.csv.gz")
    expected=set(itertools.product(c.CONFIG["clustering_representations"],c.CONFIG["clustering_methods"],range(2,13)))
    assert set(zip(grid.representation,grid.method,grid.k))==expected and len(grid)==99
    closed=frame.loc[frame.last_chart_date.lt("2026-01-01")];checked=0
    for key,model in exported["models"].items():
        r=selected[selected.configuration==key].iloc[0];candidates=grid[(grid.representation==model["representation"])&(grid.method==model["method"])]
        supported=candidates[(candidates.minimum_cluster_share>=.01)&(candidates.stability_mean>=.6)]
        chosen=(supported if len(supported) else candidates).sort_values(["validation_silhouette","k"],ascending=[False,True]).iloc[0]
        assert r.k==chosen.k and bool(r.selection_supported)==bool(len(supported))
        labels=demo.cluster_predict(model,pre,closed[c.SCORES]);saved=assignments.set_index("song_id").loc[closed.song_id]
        np.testing.assert_array_equal(labels,saved[key])
        for name,f,seed in [("validation",validation,c.SEED+10),("test",test,c.SEED+30)]:
            lab=demo.cluster_predict(model,pre,f[c.SCORES]);sample=clustering.sample_indices(len(f),1200,seed)
            for representation,suffix in [(model["representation"],""),("standardized42","_original42")]:
                x=demo.cluster_transform(f[c.SCORES],pre,representation)[sample]
                close(silhouette_score(x,lab[sample]),r[name+"_silhouette"+suffix],"cluster silhouette")
        if model["method"]=="kmedoids":
            medoids=train.set_index("song_id").loc[model["medoid_song_ids"]]
            np.testing.assert_allclose(demo.cluster_transform(medoids[c.SCORES],pre,model["representation"]),model["centers"],atol=1e-12)
        checked+=len(closed)
    assert len(exported["models"])==9
    return dict(configurations=99,selected_configurations=9,assignments_checked=checked,train_only_pca=True,medoids_are_training_songs=True)


def verify_checkpoints():
    checked=0
    for base,code in [("patterns","src/course_patterns.py"),("classification","src/course_classification.py"),("clustering","src/course_clustering.py")]:
        files=sorted((c.LOCAL/base).rglob("*.json.gz"))
        if not files:continue
        for path in files:
            record=c.read_json(path)
            assert record["identity"]==dict(protocol=c.freeze(),code={p:c.sha(c.ROOT/p) for p in ["src/course_common.py",code]})
            assert record["result_sha256"]==c.digest(record["result"])
            checked+=1
    return dict(verified=checked,expected_if_local_cache_present=120)


def refit_replay(frame,train,validation):
    classification_count=0;cluster_count=0
    for name in classification.TARGETS:
        for start,end in c.OUTER:
            path=c.LOCAL/f"classification/{name}_{start}.json.gz"
            if not path.exists():raise ValueError("Refit comparison needs local completed checkpoints")
            expected=c.read_json(path)["result"];actual=c.clean(classification.fit_fold(frame,name,start,end))
            assert c.digest(actual)==c.digest(expected),(name,start)
            classification_count+=1
    definition=clustering.representations(train)
    for rep in c.CONFIG["clustering_representations"]:
        for method in c.CONFIG["clustering_methods"]:
            for k in (2,7,12):
                expected=c.read_json(c.LOCAL/f"clustering/{rep}/{method}_{k}.json.gz")["result"]
                actual=c.clean(clustering.configuration(train,validation,definition,rep,method,k))
                # Operational timings/high-water RSS are deliberately non-deterministic.
                for d in (actual,expected):
                    for key in ("wall_seconds","peak_rss_bytes"):d.pop(key,None)
                assert c.digest(actual)==c.digest(expected),(rep,method,k)
                cluster_count+=1
    return dict(classification_folds_refit=classification_count,cluster_configurations_refit=cluster_count,cluster_fits=cluster_count*3,exact_logical_replay=True)


def manifest():
    artifacts={str(p.relative_to(c.ROOT)):c.sha(p) for p in sorted(c.PUBLIC.rglob("*")) if p.is_file() and p.name!="artifact_manifest.json" and p.suffix!=".tmp"}
    code=[*sorted((c.ROOT/"src").glob("course_*.py")),*sorted((c.ROOT/"tests").glob("test_course_*.py")),c.ROOT/"requirements-course-methods.txt"]
    c.write_json(c.PUBLIC/"artifact_manifest.json",dict(sha256=artifacts,sources_sha256={str(p.relative_to(c.ROOT)):c.sha(p) for p in code if p.exists()}))


def check_manifest(previous,allow_operational_changes=False):
    changed=[]
    for category in ("sha256","sources_sha256"):
        for name,sha in previous[category].items():
            if c.sha(c.ROOT/name)==sha:continue
            if allow_operational_changes and category=="sha256" and name in OPERATIONAL_ARTIFACTS:
                changed.append(name)
            else:raise ValueError("Publication changed: "+name)
    return sorted(changed)


def verify(replay=False,preserve=False,record=False):
    started=time.perf_counter();c.freeze();path=c.PUBLIC/"artifact_manifest.json"
    operational_changes=[]
    if path.exists():
        operational_changes=check_manifest(c.read_json(path),allow_operational_changes=record)
    frame=c.data();train,validation,test=c.primary_split(frame)
    result=dict(status="PASS",patterns=verify_patterns(train,validation,test),classification=verify_classification(frame),
                clustering=verify_clustering(frame,train,validation,test),checkpoints=verify_checkpoints())
    if replay:result["refit_replay"]=refit_replay(frame,train,validation)
    if preserve:result["preservation"]=c.preservation()
    result.update(c.usage(started));result["operational_records_refreshed"]=operational_changes
    result["verification_source_sha256"]=c.sha(Path(__file__))
    if record:
        c.write_json(c.PUBLIC/("replay_validation.json" if replay else "validation.json"),result);manifest()
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--replay",action="store_true");parser.add_argument("--preservation",action="store_true");parser.add_argument("--record",action="store_true");args=parser.parse_args()
    with threadpool_limits(limits=1):print(json.dumps(verify(args.replay,args.preservation,args.record),indent=2))
