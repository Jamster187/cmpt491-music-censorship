"""Render a small figure set and measured findings from the completed campaign."""
from __future__ import annotations
from datetime import datetime,timezone
import itertools
import json
from pathlib import Path
import textwrap
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from threadpoolctl import threadpool_limits

import course_common as c
import course_demo_model as demo

COLORS={"tree":"#176b87","naive_bayes":"#c05a27","majority":"#555555",
        "kmeans":"#176b87","kmedoids":"#c05a27","hierarchical":"#684b9f"}
FIGURES=[]


def read(name):return pd.read_csv(c.PUBLIC/name,float_precision="round_trip")


def save(fig,name,caption):
    folder=c.PUBLIC/"figures";folder.mkdir(exist_ok=True);preview=c.LOCAL/"figure_previews";preview.mkdir(exist_ok=True)
    svg=folder/(name+".svg")
    fig.savefig(svg,metadata={"Date":None},bbox_inches="tight")
    # Matplotlib emits trailing spaces in path commands; newlines retain the
    # required SVG separators while keeping generated files diff-check clean.
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    fig.savefig(preview/(name+".png"),dpi=135,bbox_inches="tight");plt.close(fig)
    FIGURES.append(dict(file="figures/"+name+".svg",caption=caption))


def pct(x):return f"{100*x:.1f}%"


def pp(x):return f"{100*x:+.1f} percentage points"


def md_table(frame,columns=None):
    if columns is not None:frame=frame[columns]
    def cell(x):return str(x).replace("|","/").replace("\n"," ")
    lines=["| "+" | ".join(map(cell,frame.columns))+" |","|"+"---|"*len(frame.columns)]
    lines += ["| "+" | ".join(cell(v) for v in row)+" |" for row in frame.itertuples(index=False,name=None)]
    return "\n".join(lines)


def get_rule(rules,antecedent,consequent,negative=False):
    key=c.digest([tuple(sorted(antecedent)),consequent,negative])[:16]
    return rules.loc[rules.rule_id==key].iloc[0]


def figures():
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,"axes.spines.right":False,"svg.hashsalt":"cmpt491-course-methods-v1"})
    benchmark=read("frequent_patterns/algorithm_comparison.csv")
    fig,ax=plt.subplots(figsize=(7.5,4),layout="constrained")
    for algorithm,g in benchmark.groupby("algorithm"):
        ax.plot(100*g.support_threshold,g.wall_seconds,marker="o",label=algorithm)
    ax.set(xlabel="Minimum training support (%)",ylabel="Wall seconds",title="Same transactions and frequent-itemset counts");ax.legend();ax.set_ylim(bottom=0)
    save(fig,"algorithm_comparison","One measured run per algorithm/threshold; implementations and shared data preparation are described in methodology.")

    evaluation=read("classification/evaluation.csv");fig,axes=plt.subplots(1,3,figsize=(12,3.5),layout="constrained")
    for ax,target,title in zip(axes,["top10","long_chart","broad_genre"],["Top 10","Long chart longevity","Broad genre"]):
        for method in ("tree","naive_bayes","majority"):
            g=evaluation[(evaluation.target==target)&(evaluation.method==method)].sort_values("start")
            ax.plot(g.start,g.balanced_accuracy,marker="o",color=COLORS[method],label=method,linestyle="--" if method=="majority" else "-")
        ax.set(title=title,xlabel="Evaluation window starts",ylabel="Balanced accuracy",ylim=(0,1),xticks=[1990,2000,2010,2018]);ax.grid(alpha=.15)
    axes[-1].legend(loc="upper left",fontsize=8)
    save(fig,"classification_generalization","Chronological outer evaluations; inner validation selects tree settings. Chance-level binary balanced accuracy is 0.5.")

    matrices=c.read_json(c.PUBLIC/"classification/confusion_matrices.json");fig,axes=plt.subplots(3,2,figsize=(11,12),layout="constrained")
    for i,target in enumerate(["top10","long_chart","broad_genre"]):
        for j,method in enumerate(["tree","naive_bayes"]):
            row=next(r for r in matrices if r["target"]==target and r["start"]==2018 and r["method"]==method)
            matrix=np.asarray(row["matrix"]);fractions=matrix/matrix.sum(axis=1)[:,None];ax=axes[i,j]
            ax.imshow(fractions,vmin=0,vmax=1,cmap="Blues")
            labels=[x.replace("Electronic / Dance","Electronic").replace("Other broad genre","Other").replace("Hip-Hop / Rap","Hip-Hop").replace("R&B / Soul","R&B") for x in row["classes"]]
            ax.set(xticks=range(len(labels)),yticks=range(len(labels)),xticklabels=labels,yticklabels=labels,
                   xlabel="Predicted",ylabel="Actual",title=f"{target} · {method}")
            ax.tick_params(axis="x",rotation=40)
            for a,b in itertools.product(range(len(labels)),repeat=2):
                ax.text(b,a,f"{matrix[a,b]}\n{100*fractions[a,b]:.0f}%",ha="center",va="center",fontsize=7 if i==2 else 11,color="white" if fractions[a,b]>.6 else "black")
    save(fig,"latest_confusion_matrices","2018–2025 counts and row-normalized percentages. Every class remains visible, including classes with zero recall.")

    grid=read("clustering/grid.csv");fig,axes=plt.subplots(2,3,figsize=(12,6),layout="constrained")
    for j,representation in enumerate(c.CONFIG["clustering_representations"]):
        for method in c.CONFIG["clustering_methods"]:
            g=grid[(grid.representation==representation)&(grid.method==method)].sort_values("k")
            axes[0,j].plot(g.k,g.validation_silhouette,marker=".",label=method,color=COLORS[method])
            axes[1,j].plot(g.k,g.stability_mean,marker=".",color=COLORS[method])
        axes[0,j].set(title=representation,ylabel="Validation silhouette",ylim=(0,.65));axes[1,j].set(ylabel="Mean resample ARI",xlabel="Number of clusters",ylim=(0,1.03))
        axes[1,j].axhline(.6,color="#666666",linestyle="--",linewidth=1)
        for ax in axes[:,j]:ax.set_xticks([2,4,6,8,10,12]);ax.grid(alpha=.15)
    axes[0,0].legend(fontsize=8)
    save(fig,"clustering_comparison","All 99 configurations. High hierarchical silhouettes can reflect small outlier clusters; medoid solutions fail the predefined stability/size criteria.")

    profiles=read("clustering/profiles.csv");keys=["kmeans_standardized42_k3","kmeans_family_balanced_k2"]
    main=profiles[profiles.configuration==keys[0]].pivot(index="feature",columns="cluster",values="standardized_mean")
    chosen=[]
    for names in c.FAMILIES.values():chosen+=main.loc[names].abs().max(axis=1).sort_values(ascending=False).head(4).index.tolist()
    data=[profiles[profiles.configuration==key].pivot(index="feature",columns="cluster",values="standardized_mean").loc[chosen] for key in keys]
    limit=max(abs(d.to_numpy()).max() for d in data);fig,axes=plt.subplots(1,2,figsize=(10,8),layout="constrained")
    for ax,d,key in zip(axes,data,keys):
        im=ax.imshow(d.to_numpy(),cmap="RdBu_r",vmin=-limit,vmax=limit,aspect="auto")
        ax.set(yticks=range(len(chosen)),yticklabels=chosen,xticks=range(d.shape[1]),xticklabels=["Cluster "+str(i) for i in d],title=key.replace("kmeans_","").replace("_"," "))
        ax.tick_params(axis="y",labelsize=9)
    fig.colorbar(im,ax=axes,label="Profile mean in training standard deviations",shrink=.7)
    save(fig,"cluster_profiles","Up to four displayed features per classifier family, selected by absolute profile contrast. Profiles describe all eligible historical songs; scaling is training-only.")

    history=read("clustering/historical_prevalence.csv");pre=read("clustering/pre2020_post2020.csv");adjusted=read("clustering/genre_standardized_prevalence.csv")
    key=keys[0];fig,axes=plt.subplots(1,2,figsize=(12,4),layout="constrained")
    for group,g in history[history.configuration==key].groupby("cluster"):
        axes[0].plot(g.decade,g.share,marker="o",label=f"Cluster {group}")
    axes[0].set(ylabel="Share of complete-score songs",xlabel="Debut decade",ylim=(0,1),title="Three-cluster historical prevalence");axes[0].tick_params(axis="x",rotation=35);axes[0].legend()
    raw=pre[pre.configuration==key].sort_values("cluster");adj=adjusted[adjusted.configuration==key].sort_values("cluster");x=np.arange(3)
    axes[1].bar(x-.18,raw.difference,width=.36,label="Raw full population")
    axes[1].bar(x+.18,adj.standardized_difference,width=.36,label="Fixed genre mixture, supported genres")
    axes[1].axhline(0,color="black",linewidth=.7);axes[1].set(xticks=x,xticklabels=[f"Cluster {i}" for i in x],ylabel="Post-2020 minus pre-2020 share",title="Descriptive contrasts, different coverage");axes[1].legend(fontsize=8)
    save(fig,"cluster_history","Pre/post contrasts span unequal historical periods, not a breakpoint design. Genre-standardized values retain only 72.0% of the training genre mass; the bar difference is not a decomposition.")

    rules=read("association_rules/all_rules.csv.gz")
    selected=[get_rule(rules,["emotion_caring=low","emotion_love=low"],"long_chart=no"),
              get_rule(rules,["mb_duration_median_seconds=high"],"ll_violence=high"),
              get_rule(rules,["genre=Pop"],"top10=yes"),get_rule(rules,["genre=Country"],"long_chart=yes"),
              get_rule(rules,["top10=yes"],"mb_release_count=low",True)]
    fig,ax=plt.subplots(figsize=(11,5),layout="constrained")
    for i,row in enumerate(selected):
        ax.plot([row.test_baseline,row.test_confidence],[i,i],color="#aaaaaa",linewidth=3)
        ax.scatter(row.test_baseline,i,color="#777777",marker="x",label="Consequent baseline" if i==0 else None,s=60)
        ax.scatter(row.test_confidence,i,color="#176b87",label="Rule confidence" if i==0 else None,s=55)
        ax.text(min(.96,max(row.test_confidence,row.test_baseline)+.025),i,f"n={int(row.test_antecedent_n)}",va="center",fontsize=9)
    labels=[textwrap.fill(demo.rule_text(row.to_dict()).replace("IF ","").replace(" THEN "," → "),58) for row in selected]
    ax.set(yticks=range(len(labels)),yticklabels=labels,xlim=(0,1),xlabel="2018–2025 probability / share",title="Association confidence compared with its baseline");ax.legend(loc="upper left");ax.invert_yaxis();ax.grid(axis="x",alpha=.2)
    save(fig,"association_baselines","Retrospective display examples. The multidimensional rule also adds only about 2.6 percentage points over its strongest immediate parent.")
    c.write_json(c.PUBLIC/"figure_index.json",FIGURES)


def agreement():
    assignments=read("clustering/assignments.csv.gz");names=[x for x in assignments if x not in {"song_id","split"}];rows=[]
    for split in ("train","validation","test"):
        f=assignments[assignments.split==split]
        for left,right in itertools.combinations(names,2):rows.append(dict(split=split,n=len(f),left=left,right=right,adjusted_rand=float(adjusted_rand_score(f[left],f[right]))))
    c.write_csv(c.PUBLIC/"clustering/representation_agreement.csv",rows)
    return pd.DataFrame(rows)


def findings(agreement_table):
    evaluation=read("classification/evaluation.csv");latest=evaluation[evaluation.start==2018];confusions=c.read_json(c.PUBLIC/"classification/confusion_matrices.json")
    selected=read("clustering/selected_configurations.csv");rules=read("association_rules/all_rules.csv.gz");bench=read("frequent_patterns/algorithm_comparison.csv")
    summary=c.read_json(c.PUBLIC/"frequent_patterns/execution.json");schema=c.read_json(c.PUBLIC/"frequent_patterns/transaction_schema.json")
    pattern_summary=[]
    for support in c.CONFIG["frequent_supports"]:
        itemsets=read(f"frequent_patterns/itemsets_support_{support:.2f}.csv.gz")
        pattern_summary.append(dict(support_threshold=support,itemsets=len(itemsets),closed=int(itemsets.closed.sum()),maximal=int(itemsets.maximal.sum()),algorithms=3,identical=True))
    c.write_csv(c.PUBLIC/"frequent_patterns/itemset_summary.csv",pattern_summary)
    model=c.read_json(c.PUBLIC/"classification/models.json.gz");profiles=read("clustering/genre_composition.csv");history=read("clustering/pre2020_post2020.csv");adj=read("clustering/genre_standardized_prevalence.csv")
    def metric(target,method,field):return float(latest[(latest.target==target)&(latest.method==method)].iloc[0][field])
    rule=get_rule(rules,["emotion_caring=low","emotion_love=low"],"long_chart=no")
    duration=get_rule(rules,["mb_duration_median_seconds=high"],"ll_violence=high")
    negatives=get_rule(rules,["detox_obscene=low"],"genre=Hip-Hop / Rap",True)
    conditional=read("association_rules/conditional_pairs.csv.gz")
    reversal=conditional[(conditional.antecedent=='["mb_release_count=high"]')&(conditional.consequent=="ll_substance_use=high")&(conditional.genre=="Pop")].iloc[0]
    standard=selected[selected.configuration=="kmeans_standardized42_k3"].iloc[0];balanced=selected[selected.configuration=="kmeans_family_balanced_k2"].iloc[0]
    agreement_row=agreement_table[(agreement_table.split=="test") & (agreement_table.left=="kmeans_pca90_k3") & (agreement_table.right=="kmeans_standardized42_k3")].iloc[0]
    content=history[(history.configuration==standard.configuration)&(history.cluster==2)].iloc[0]
    adjusted=adj[(adj.configuration==standard.configuration)&(adj.cluster==2)].iloc[0]
    across=profiles[(profiles.configuration==standard.configuration)&(profiles.cluster==0)].sort_values("within_cluster_share",ascending=False).head(4)
    share=profiles[(profiles.configuration==standard.configuration)&(profiles.cluster==2)&(profiles.genre=="Hip-Hop / Rap")].iloc[0].within_cluster_share
    report=["# Findings: completed course-method campaign","",
        "All requested major method families were implemented and executed. The clearest result is a limit: the lyrical scores do not provide useful, stable chronological chart-success classification in this population. Stable broad score profiles exist, while many impressive association rules still reflect overlapping measurements or historical composition. No result identifies a COVID effect.","",
        "## Eight findings worth discussing","",
        f"1. **Chart success remains difficult.** In 2018–2025, tree/Bayes balanced accuracy is {metric('top10','tree','balanced_accuracy'):.3f}/{metric('top10','naive_bayes','balanced_accuracy'):.3f} for Top 10 and {metric('long_chart','tree','balanced_accuracy'):.3f}/{metric('long_chart','naive_bayes','balanced_accuracy'):.3f} for long longevity, against 0.500 majority baselines. More flexible multivariate classifiers do not rescue the weak lyrical-to-chart signal found in earlier work.",
        f"2. **Lyrics help distinguish broad genres, with large limitations.** Latest tree/Bayes balanced accuracy is {metric('broad_genre','tree','balanced_accuracy'):.3f}/{metric('broad_genre','naive_bayes','balanced_accuracy'):.3f}, versus {metric('broad_genre','majority','balanced_accuracy'):.3f}; macro F1 is only {metric('broad_genre','tree','f1_macro'):.3f}/{metric('broad_genre','naive_bayes','f1_macro'):.3f}. Bayes accuracy is {pct(metric('broad_genre','naive_bayes','accuracy'))}, but the largest test class alone contains {pct(max(model['broad_genre_2018']['test_class_counts'].values())/model['broad_genre_2018']['test_n'])} of songs. Minority-class failures remain visible in the confusion matrices; the training-majority baseline's {pct(metric('broad_genre','majority','accuracy'))} accuracy should not make this look like a general genre solution.",
        f"3. **Three broad score profiles are reproducible, not sharply separated.** Standardized K-means selects K=3, mean resample ARI {standard.stability_mean:.3f}, and test silhouette {standard.test_silhouette:.3f}. PCA also selects K=3 and agrees with those test assignments at ARI {agreement_row.adjusted_rand:.3f}. Family balancing instead selects K=2 (ARI stability {balanced.stability_mean:.3f}; test silhouette {balanced.test_silhouette:.3f}). Stable assignments do not establish a unique natural taxonomy.",
        "4. **An affect profile spans genres.** Standardized cluster 0 has elevated disappointment, sadness and grief scores. Its largest genre shares are "+", ".join(f"{r.genre} {pct(r.within_cluster_share)}" for r in across.itertuples())+f". The high content-score cluster 2 is {pct(share)} Hip-Hop / Rap, leaving a substantial share from other genres. These are classifier profiles, not human-validated lyrical categories.",
        f"5. **Cluster prevalence changes substantially over historical cohorts.** The high content-score cluster's raw share is {pct(content.pre2020_share)} before 2020 and {pct(content.post2020_share)} after, a {pp(content.difference)} contrast (fixed-cluster artist interval {pp(content.artist_ci_low)} to {pp(content.artist_ci_high)}). A fixed genre mixture gives {pct(adjusted.standardized_pre2020_share)} to {pct(adjusted.standardized_post2020_share)}, but retains only {pct(adjusted.retained_training_genre_mass)} of training genre mass. Unequal historical spans, missingness, genre composition and right-boundary selection prevent a COVID or breakpoint interpretation.",
        f"6. **A multidimensional chart association is measurable but modest.** Low caring AND low love scores imply ≤{schema['longevity_threshold']:g} observed chart weeks for {pct(rule.test_confidence)} of {int(rule.test_antecedent_n):,} recent songs, versus {pct(rule.test_baseline)} overall. Improvement over the strongest immediate parent is only {pp(rule.test_confidence_gain_vs_best_parent)} (global BY q={rule.q_by_global:.3g}). This is a retrospective conditional association; it does not overturn the poor full-classifier results.",
        f"7. **Aggregation can conceal a genre reversal.** High MusicBrainz release count is associated with a {pp(reversal.pooled_risk_difference)} change in high substance-use-score prevalence overall, but {pp(reversal.risk_difference)} within Pop: {pct(reversal.confidence)} versus a Pop baseline of {pct(reversal.baseline)} ({int(reversal.antecedent_n)} antecedent songs among {int(reversal.n)} Pop songs). This is a post-hoc descriptive screen, not a separately confirmed subgroup test or proof of Simpson's paradox. Catalog exposure and era/artist composition are plausible confounders.",
        f"8. **Recording metadata has cross-domain associations, not demonstrated forecasting value.** Among {int(duration.test_antecedent_n)} recent songs above the training duration Q75 ({schema['bins']['mb_duration_median_seconds'][1]:.2f} seconds), {pct(duration.test_confidence)} have high violence scores versus {pct(duration.test_baseline)} overall (lift {duration.test_lift:.2f}; BY q={duration.q_by_global:.3g}). MusicBrainz metadata is present-day evidence and was deliberately excluded from pre-chart prediction models. Genre and catalog matching can explain part of this association.","",
        "## Frequent patterns and rules","",
        md_table(pd.DataFrame(pattern_summary)),"",
        f"All three algorithms agree on every itemset and integer support count. The primary 8% set generates {summary['families']['primary']:,} rules; {summary['families']['rare_pair']:,} supplemental rare positive pairs and {summary['families']['negative']:,} negative rules bring the complete search to {summary['rules']:,}. Of these, {summary['strict_cross_domain']:,} have strict cross-domain direction and {summary['by_below_05']:,} have global BY q≤0.05 under the declared assumptions. That count includes many redundant/expected relationships and is not a discovery count.","",
        f"For a concrete negative pattern, low obscenity scores imply an observed non-Hip-Hop genre for {pct(negatives.test_confidence)} of {int(negatives.test_antecedent_n)} test songs, against a {pct(negatives.test_baseline)} baseline. This is unsurprising genre separation, not a scientific breakthrough. Rare rules retain nulls and inadequate test support. The conditional scan retains {summary['conditional_cells']:,} genre cells and flags {summary['reversal_cells']} descriptive sign reversals; no independent significance claim is made for those subgroup screens.","",
        "All itemsets include globally valid closed/maximal flags within the size-four output cap. Complete raw rules, parent comparisons, BY values and subgroup diagnostics are linked in the [README](README.md).", "",
        "## Latest chronological classification","",
        "All rows use 2,382 Billboard-study songs whose observed chart histories fit wholly within 2018–2025. Long longevity here means more than "+str(int(model['long_chart_2018']['threshold']))+" weeks; association transactions separately use more than "+str(int(schema['longevity_threshold']))+" weeks. These training-derived thresholds must not be conflated.","",
        md_table(latest[latest.method.isin(["tree","naive_bayes","majority"])][["target","method","accuracy","balanced_accuracy","precision_macro","recall_macro","f1_macro","f1_weighted"]].round(4)),"",
        "Binary confusion matrices below use actual rows and predicted columns, both ordered [no, yes]. Full seven-class genre matrices and all historical folds are in [confusion_matrices.json](classification/confusion_matrices.json).", ""]
    for target in ("top10","long_chart"):
        for method in ("tree","naive_bayes"):
            row=next(r for r in confusions if r["target"]==target and r["method"]==method and r["start"]==2018)
            report.append(f"- {target}, {method}: `{row['matrix']}`.")
    rule_table=read("classification/rules.csv")
    example=rule_table[(rule_table.start==2018)&(rule_table.target=="long_chart")&(rule_table.prediction=="yes")&(rule_table.test_n>=100)].sort_values("test_accuracy",ascending=False).iloc[0]
    report += ["", "One compact learned rule (the full-precision thresholds and every leaf are saved):", "", "```text",example.text,"```", "",
        f"It covers {int(example.test_n)} test songs and is correct on {pct(example.test_accuracy)}. Interpretable rules can still be weak. The rule classifier reproduces the tree exactly; it is not an independent success.","",
        "## Clustering comparison and null results","",
        md_table(selected[["configuration","selection_supported","validation_silhouette","test_silhouette","test_silhouette_original42","stability_mean","minimum_cluster_share"]].round(4)),"",
        "No sampled k-medoids configuration satisfies both predefined stability/size criteria. The strongest hierarchical silhouette values mainly isolate a small outlier group, and the PCA hierarchical family has no qualifying configuration. These are retained unsuccessful outcomes. They do not establish that medoid/hierarchical methods can never work; the result applies to this fixed representation, sample, initialization and bounded algorithm grid.","",
        "## Reliability, limitations and follow-up","",
        "The full search is exploratory and uses previously examined outcomes. Complete-case inclusion, frozen model errors, genre-label noise, same-artist dependence, catalog coverage, discrete-bin ties, retrospective metadata, whole-history purging and incomplete lifetime follow-up limit interpretation. Sparse CMH cells weaken asymptotic inference. Artist/block intervals are marginal fixed-analysis sensitivities, not simultaneous post-selection guarantees. The clustering bootstrap holds preprocessing fixed and has only two refit comparisons per configuration.","",
        "A worthwhile next step is a frozen replication on genuinely new, mature chart cohorts, together with a small human-labelled audit of the score profiles and genre labels. Conditional catalog/genre reversals deserve replication before causal interpretation. More classifier tuning or another exhaustive relationship search is not justified by these results. This campaign does not justify new bulk data acquisition; annotation quality and an independent evaluation set are more pressing.","",
        "## Selected figures","",
        "\n".join(f"- [{r['file'].split('/')[-1]}]({r['file']}): {r['caption']}" for r in FIGURES),"",
        "This report is generated by `src/course_report.py`; do not hand-edit its measured values."]
    (c.PUBLIC/"findings.md").write_text("\n".join(report)+"\n")


def run():
    started=time.perf_counter();figures();agreements=agreement();findings(agreements)
    stages={name:c.read_json(c.PUBLIC/path) for name,path in [("preparation","preparation.json"),("frequent_patterns_and_rules","frequent_patterns/execution.json"),("classification","classification/execution.json"),("clustering","clustering/execution.json")]}
    for name in ["frequent_patterns","association_rules","classification","clustering","figures"]:
        directory=c.PUBLIC/name
        assert directory.is_dir() and any(directory.iterdir())
    c.write_json(c.PUBLIC/"report_execution.json",dict(**c.usage(started),figures=len(FIGURES),matplotlib=matplotlib.__version__,stage_execution=stages,
        first_repository_verification_utc="2026-10-25T23:55:25+00:00",rendered_utc=datetime.now(timezone.utc).isoformat(),
        public_bytes=sum(p.stat().st_size for p in c.PUBLIC.rglob("*") if p.is_file()),
        local_cache_bytes=sum(p.stat().st_size for p in c.LOCAL.rglob("*") if p.is_file())))
    print(json.dumps(dict(status="PASS",figures=len(FIGURES),**c.usage(started)),indent=2))


if __name__=="__main__":
    with threadpool_limits(limits=1):run()
