"""Bounded 2–12 cluster comparison, with out-of-time assignment and resample stability."""
from __future__ import annotations
import time

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

import course_common as c


def sample_indices(n,size,seed):
    return np.sort(np.random.default_rng(seed).choice(n,min(n,size),replace=False))


def assign(x,centers):return cdist(x,np.asarray(centers)).argmin(axis=1)


def kmedoids(x,k,seed,max_iter=100):
    """Alternating exact within-cluster medoid updates; sampled, not full PAM."""
    distance=cdist(x,x);rng=np.random.default_rng(seed);medoids=[int(rng.integers(len(x)))]
    for _ in range(1,k):
        nearest=distance[:,medoids].min(axis=1)**2;nearest[medoids]=0
        candidate=int(rng.choice(len(x),p=nearest/nearest.sum())) if nearest.sum() else next(i for i in range(len(x)) if i not in medoids)
        medoids.append(candidate)
    medoids=np.array(medoids);trace=[]
    for _ in range(max_iter):
        labels=distance[:,medoids].argmin(axis=1);trace.append(float(distance[np.arange(len(x)),medoids[labels]].sum()))
        updated=medoids.copy()
        for group in range(k):
            members=np.flatnonzero(labels==group)
            if len(members):updated[group]=members[np.argmin(distance[np.ix_(members,members)].sum(axis=1))]
        if np.array_equal(updated,medoids):break
        medoids=updated
    labels=distance[:,medoids].argmin(axis=1);objective=float(distance[np.arange(len(x)),medoids[labels]].sum());trace.append(objective)
    if np.any(np.diff(trace)>1e-8):raise AssertionError("Medoid objective increased")
    return dict(centers=x[medoids].tolist(),native_labels=labels.tolist(),medoid_indices=medoids.tolist(),
                objective=objective,objective_trace=trace,iterations=len(trace)-1,converged=len(trace)-1<max_iter)


def representations(train):
    scaler=StandardScaler().fit(train[c.SCORES]);z=scaler.transform(train[c.SCORES])
    pca=PCA(n_components=.9,svd_solver="full").fit(z)
    weights=np.array([1/np.sqrt(len(c.FAMILIES[next(p for p in c.FAMILIES if name.startswith(p))])) for name in c.SCORES])
    definition=dict(features=c.SCORES,mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),
        pca_mean=pca.mean_.tolist(),pca_components=pca.components_.tolist(),pca_explained_variance_ratio=pca.explained_variance_ratio_.tolist(),
        family_weights=weights.tolist(),training_n=len(train),training_song_hash=c.digest(train.song_id.tolist()))
    return definition


def transform(frame,definition,representation):
    z=(frame[c.SCORES].to_numpy(float)-definition["mean"])/definition["scale"]
    if representation=="standardized42":return z
    if representation=="family_balanced":return z*np.array(definition["family_weights"])
    if representation=="pca90":return (z-definition["pca_mean"])@np.array(definition["pca_components"]).T
    raise ValueError(representation)


def fit(x,method,k,seed,subsample=False):
    size=int(.8*len(x)) if subsample and method=="kmeans" else len(x)
    if method!="kmeans":size=c.CONFIG["expensive_training_sample"]
    index=sample_indices(len(x),size,seed);sample=x[index]
    if method=="kmeans":
        model=KMeans(n_clusters=k,n_init=10,max_iter=300,random_state=seed,algorithm="lloyd").fit(sample)
        result=dict(centers=model.cluster_centers_.tolist(),native_labels=model.labels_.tolist(),
                    objective=float(model.inertia_),iterations=int(model.n_iter_),converged=model.n_iter_<300)
    elif method=="kmedoids":result=kmedoids(sample,k,seed)
    elif method=="hierarchical":
        model=AgglomerativeClustering(n_clusters=k,linkage="ward").fit(sample)
        centers=np.array([sample[model.labels_==i].mean(axis=0) for i in range(k)])
        result=dict(centers=centers.tolist(),native_labels=model.labels_.tolist(),
                    objective=None,iterations=None,converged=True,
                    out_of_sample="nearest Ward-cluster centroid; a transfer approximation, not native hierarchical prediction")
    else:raise ValueError(method)
    result["fit_indices"]=index.tolist();result["fit_n"]=len(index)
    if method=="kmedoids":result["medoid_train_indices"]=index[result["medoid_indices"]].tolist()
    return result


def silhouette(x,labels):
    labels=np.asarray(labels)
    if len(set(labels))<2 or len(set(labels))>=len(labels):return None
    return float(silhouette_score(x,labels,metric="euclidean"))


def configuration(train,validation,definition,representation,method,k):
    x=transform(train,definition,representation);v=transform(validation,definition,representation)
    vz=transform(validation,definition,"standardized42");vi=sample_indices(len(v),c.CONFIG["silhouette_sample"],c.SEED+10)
    ti=sample_indices(len(x),c.CONFIG["silhouette_sample"],c.SEED+20)
    started=time.perf_counter();base=fit(x,method,k,c.SEED);train_labels=assign(x,base["centers"]);val_labels=assign(v,base["centers"])
    stability=[]
    for seed in c.CONFIG["clustering_seeds"][1:]:
        other=fit(x,method,k,seed,True);other_labels=assign(v,other["centers"])
        stability.append(dict(seed=seed,adjusted_rand=float(adjusted_rand_score(val_labels,other_labels)),fit_n=other["fit_n"]))
    sizes=np.bincount(train_labels,minlength=k)
    return dict(representation=representation,method=method,k=k,dimension=x.shape[1],
        train_n=len(x),validation_n=len(v),fit_n=base["fit_n"],training_cluster_sizes=sizes.tolist(),
        minimum_cluster_share=float(sizes.min()/len(x)),native_sample_cluster_sizes=np.bincount(base["native_labels"],minlength=k).tolist(),
        train_silhouette=silhouette(x[ti],train_labels[ti]),validation_silhouette=silhouette(v[vi],val_labels[vi]),
        validation_silhouette_original42=silhouette(vz[vi],val_labels[vi]),silhouette_n=len(vi),
        stability_mean=float(np.mean([r["adjusted_rand"] for r in stability])),stability=stability,
        fit=base,**c.usage(started))


def prevalence_intervals(frame,cluster_labels,k):
    """Descriptive post-selection exact-credit cluster bootstrap, shared periods."""
    artists=sorted(frame.artist.unique());lookup={a:i for i,a in enumerate(artists)}
    a=np.array([lookup[v] for v in frame.artist]);period=(frame.year.to_numpy()>=2020).astype(int)
    counts=np.bincount(a*2*k+period*k+cluster_labels,minlength=len(artists)*2*k).reshape(len(artists),2,k)
    rng=np.random.default_rng(c.SEED);values=[]
    for _ in range(c.CONFIG["bootstrap_repeats"]):
        weights=rng.multinomial(len(artists),np.repeat(1/len(artists),len(artists)))
        summed=np.tensordot(weights,counts,axes=(0,0));share=summed/summed.sum(axis=1)[:,None]
        values.append(share[1]-share[0])
    q=np.quantile(values,[.025,.975],axis=0);totals=counts.sum(axis=0);shares=totals/totals.sum(axis=1)[:,None]
    return [dict(cluster=i,pre2020_n=int(totals[0,i]),post2020_n=int(totals[1,i]),pre2020_share=shares[0,i],post2020_share=shares[1,i],
        difference=shares[1,i]-shares[0,i],artist_ci_low=q[0,i],artist_ci_high=q[1,i],artist_credits=len(artists)) for i in range(k)]


def summarize_selected(selected,frame,train,validation,test,definition):
    summaries=[];assignments=[];profiles=[];composition=[];history=[];chart=[];prevalence=[];adjusted=[];models={};plot_rows=[]
    frame=frame.loc[frame.last_chart_date.lt("2026-01-01")].copy();z=transform(frame,definition,"standardized42")
    split=np.repeat("purged_boundary",len(frame)).astype(object)
    for name,f in [("train",train),("validation",validation),("test",test)]:split[frame.song_id.isin(f.song_id)]=name
    vi=sample_indices(len(test),c.CONFIG["silhouette_sample"],c.SEED+30)
    xy=transform(frame,definition,"pca90")[:,:2];plot_index=sample_indices(len(frame),1500,c.SEED+40)
    for r in selected:
        key=f"{r['method']}_{r['representation']}_k{r['k']}";centers=r["fit"]["centers"];k=r["k"];rep=r["representation"]
        x=transform(frame,definition,rep);label=assign(x,centers);test_label=assign(transform(test,definition,rep),centers)
        summary={k:v for k,v in r.items() if k not in {"fit","stability"}}
        summary.update(configuration=key,test_n=len(test),test_silhouette=silhouette(transform(test,definition,rep)[vi],test_label[vi]),
                       test_silhouette_original42=silhouette(transform(test,definition,"standardized42")[vi],test_label[vi]))
        summaries.append(summary);models[key]=dict(method=r["method"],representation=rep,k=k,centers=centers,selection_supported=r["selection_supported"])
        if r["method"]=="kmedoids":models[key]["medoid_song_ids"]=train.iloc[r["fit"]["medoid_train_indices"]].song_id.tolist()
        assignments += [dict(configuration=key,song_id=sid,split=part,cluster=int(group)) for sid,part,group in zip(frame.song_id,split,label)]
        for group in range(k):
            mask=label==group;g=frame.loc[mask]
            for j,name in enumerate(c.SCORES):profiles.append(dict(configuration=key,cluster=group,feature=name,n=len(g),mean=float(g[name].mean()),standardized_mean=float(z[mask,j].mean())))
            chart.append(dict(configuration=key,cluster=group,n=len(g),median_best_rank=float(g.best_chart_rank.median()),
                median_chart_weeks=float(g.chart_weeks.median()),chart_weeks_q25=float(g.chart_weeks.quantile(.25)),chart_weeks_q75=float(g.chart_weeks.quantile(.75)),
                top10_rate=float(g.best_chart_rank.le(10).mean())))
            for genre,n in g.primary_genre.value_counts().items():
                composition.append(dict(configuration=key,cluster=group,genre=genre,n=int(n),within_cluster_share=n/len(g),within_genre_share=n/frame.primary_genre.eq(genre).sum()))
        for decade in sorted(frame.decade.unique()):
            mask=frame.decade.eq(decade).to_numpy();counts=np.bincount(label[mask],minlength=k)
            for group,n in enumerate(counts):history.append(dict(configuration=key,decade=decade,cluster=group,n=int(n),decade_n=int(mask.sum()),share=n/mask.sum()))
        prevalence += [dict(configuration=key,**row) for row in prevalence_intervals(frame,label,k)]
        # Hold genre mixture fixed to training weights, only adequately observed broad genres.
        supported=[g for g in sorted(frame.broad_genre.unique()) if all(((frame.broad_genre==g)&(frame.period==p)).sum()>=100 for p in ("pre2020","post2020"))]
        weights=train.broad_genre.value_counts(normalize=True);mass=float(weights.reindex(supported).fillna(0).sum())
        for group in range(k):
            values={}
            for period in ("pre2020","post2020"):
                values[period]=sum(float(weights.get(g,0))/mass*float((label[(frame.broad_genre==g)&(frame.period==period)]==group).mean()) for g in supported)
            adjusted.append(dict(configuration=key,cluster=group,supported_genres=supported,retained_training_genre_mass=mass,
                standardized_pre2020_share=values["pre2020"],standardized_post2020_share=values["post2020"],
                standardized_difference=values["post2020"]-values["pre2020"],scope="descriptive fixed training genre mixture; no causal interpretation"))
        for i in plot_index:plot_rows.append(dict(configuration=key,song_id=frame.iloc[i].song_id,cluster=int(label[i]),pc1=xy[i,0],pc2=xy[i,1]))
    # Store each long public song identity once rather than repeating it nine times.
    assignment_matrix=pd.DataFrame(assignments).pivot(index=["song_id","split"],columns="configuration",values="cluster").reset_index()
    for filename,rows in [("selected_configurations.csv",summaries),("assignments.csv.gz",assignment_matrix),("profiles.csv",profiles),
        ("genre_composition.csv",composition),("historical_prevalence.csv",history),("chart_distributions.csv",chart),
        ("pre2020_post2020.csv",prevalence),("genre_standardized_prevalence.csv",adjusted),("plot_sample.csv.gz",plot_rows)]:
        c.write_csv(c.PUBLIC/"clustering"/filename,rows)
    c.write_json(c.PUBLIC/"clustering/models.json.gz",dict(preprocessing=definition,models=models))


def run():
    started=time.perf_counter();c.freeze();frame=c.data();train,validation,test=c.primary_split(frame);definition=representations(train)
    results=[];stability=[];sizes=[]
    c.write_json(c.PUBLIC/"clustering/preprocessing.json",definition)
    for representation in c.CONFIG["clustering_representations"]:
        for method in c.CONFIG["clustering_methods"]:
            for k in c.CONFIG["clustering_k"]:
                name=f"clustering/{representation}/{method}_{k}"
                result,reused=c.checkpoint(name,lambda:configuration(train,validation,definition,representation,method,k),["src/course_clustering.py"])
                results.append(result)
                ident=dict(representation=representation,method=method,k=k)
                stability += [dict(**ident,**v) for v in result["stability"]]
                sizes += [dict(**ident,cluster=i,n=n,share=n/len(train)) for i,n in enumerate(result["training_cluster_sizes"])]
                print(representation,method,k,"silhouette",round(result["validation_silhouette"],4),"ARI",round(result["stability_mean"],4),"reused",reused,flush=True)
    rows=[{k:v for k,v in r.items() if k not in {"fit","stability"}} for r in results]
    c.write_csv(c.PUBLIC/"clustering/grid.csv",rows);c.write_csv(c.PUBLIC/"clustering/stability.csv",stability);c.write_csv(c.PUBLIC/"clustering/cluster_sizes.csv",sizes)
    selected=[]
    for representation in c.CONFIG["clustering_representations"]:
        for method in c.CONFIG["clustering_methods"]:
            eligible=[r for r in results if r["representation"]==representation and r["method"]==method]
            supported=[r for r in eligible if r["minimum_cluster_share"]>=.01 and r["stability_mean"]>=.6]
            chosen=max(supported or eligible,key=lambda r:(r["validation_silhouette"],-r["k"]))
            selected.append(dict(**chosen,selection_supported=bool(supported)))
    summarize_selected(selected,frame,train,validation,test,definition)
    c.write_json(c.PUBLIC/"clustering/execution.json",dict(configurations=len(results),fits=len(results)*3,selected=len(selected),
        expensive_sample=c.CONFIG["expensive_training_sample"],maximum_distance_matrix_bytes=c.CONFIG["expensive_training_sample"]**2*8,
        pca_dimensions=len(definition["pca_components"]),pca_explained_variance=sum(definition["pca_explained_variance_ratio"]),**c.usage(started)))


if __name__=="__main__":
    with threadpool_limits(limits=1):run()
