"""Independent Apriori, FP-growth and vertical ECLAT; bounded association campaign."""
from __future__ import annotations
from collections import Counter, defaultdict
import itertools
import math
import time

import numpy as np
import pandas as pd
from scipy import stats
from threadpoolctl import threadpool_limits

import course_common as c


def count(bits):
    # CPython 3.9 is the frozen numerical environment; bit_count arrived in 3.10.
    return bits.bit_count() if hasattr(bits,"bit_count") else bin(bits).count("1")


def variable(item):return item.split("=",1)[0]


def compatible(items):return len({variable(x) for x in items})==len(items)


def vertical(transactions):
    result=defaultdict(int)
    for row,items in enumerate(transactions):
        for item in set(items):result[item] |= 1<<row
    return dict(sorted(result.items()))


def intersection(items,index,full):
    result=full
    for item in items:result &= index.get(item,0)
    return result


def apriori(transactions,minimum,max_size=4):
    index=vertical(transactions);full=(1<<len(transactions))-1
    previous={(i,):count(v) for i,v in index.items() if count(v)>=minimum};result=dict(previous)
    for size in range(2,max_size+1):
        groups=defaultdict(list)
        for itemset in sorted(previous):groups[itemset[:-1]].append(itemset)
        current={}
        for group in groups.values():
            for left,right in itertools.combinations(group,2):
                candidate=left+(right[-1],)
                if not compatible(candidate) or any(sub not in previous for sub in itertools.combinations(candidate,size-1)):continue
                n=count(intersection(candidate,index,full))
                if n>=minimum:current[candidate]=n
        result.update(current);previous=current
        if not previous:break
    return result


def eclat(transactions,minimum,max_size=4):
    index=vertical(transactions);result={}
    def visit(prefix,suffix):
        for pos,(item,bits) in enumerate(suffix):
            candidate=prefix+(item,);result[candidate]=count(bits)
            if len(candidate)>=max_size:continue
            follow=[]
            for other,tids in suffix[pos+1:]:
                if variable(other) in {variable(x) for x in candidate}:continue
                common=bits&tids
                if count(common)>=minimum:follow.append((other,common))
            visit(candidate,follow)
    visit((),[(i,v) for i,v in index.items() if count(v)>=minimum])
    return result


class Node:
    __slots__=("item","count","parent","children")
    def __init__(self,item=None,parent=None):
        self.item=item;self.count=0;self.parent=parent;self.children={}


def fpgrowth(transactions,minimum,max_size=4):
    result={}
    def build(paths):
        frequencies=Counter()
        for items,n in paths:
            for item in items:frequencies[item]+=n
        frequencies={i:n for i,n in frequencies.items() if n>=minimum}
        root=Node();headers=defaultdict(list)
        for items,n in paths:
            node=root
            for item in sorted((x for x in items if x in frequencies),key=lambda x:(-frequencies[x],x)):
                if item not in node.children:
                    node.children[item]=Node(item,node);headers[item].append(node.children[item])
                node=node.children[item];node.count+=n
        return frequencies,headers
    def grow(paths,prefix):
        frequencies,headers=build(paths)
        for item in sorted(frequencies,key=lambda x:(frequencies[x],x)):
            candidate=tuple(sorted(prefix+(item,)))
            if not compatible(candidate):continue
            result[candidate]=frequencies[item]
            if len(candidate)>=max_size:continue
            conditional=[]
            for node in headers[item]:
                path=[];parent=node.parent
                while parent and parent.item is not None:
                    path.append(parent.item);parent=parent.parent
                if path:conditional.append((path,node.count))
            if conditional:grow(conditional,prefix+(item,))
    grow([(sorted(set(t)),1) for t in transactions],())
    return result


def closed_maximal(patterns,transactions,minimum):
    """Exact global closure/maximality, including extensions beyond size four."""
    index=vertical(transactions);full=(1<<len(transactions))-1;rows=[]
    singles=[(i,v) for i,v in index.items() if count(v)>=minimum]
    for items,n in sorted(patterns.items()):
        bits=intersection(items,index,full);closed=True;maximal=True;variables={variable(i) for i in items}
        for item,tids in singles:
            if variable(item) in variables:continue
            extension=count(bits&tids)
            if extension==n:closed=False
            if extension>=minimum:maximal=False
            if not closed:break
        rows.append(dict(items=list(items),size=len(items),count=n,support=n/len(transactions),closed=closed,maximal=maximal))
    return rows


def fit_bins(train):
    fields=c.SCORES+["mb_duration_median_seconds","mb_recording_count","mb_release_count"]
    return {name:train[name].dropna().quantile([.25,.75]).tolist() for name in fields}


def transactions(frame,bins,longevity):
    rows=[[] for _ in range(len(frame))]
    for name,(low,high) in bins.items():
        for i,value in enumerate(frame[name]):
            if pd.isna(value):continue
            if value<=low:rows[i].append(name+"=low")
            elif value>high:rows[i].append(name+"=high")
    for i,row in enumerate(frame.itertuples()):
        rows[i].extend(["genre="+row.primary_genre,"decade="+row.decade,
                       "top10="+("yes" if row.best_chart_rank<=10 else "no"),
                       "long_chart="+("yes" if row.chart_weeks>longevity else "no")])
    if any(not compatible(row) for row in rows):raise AssertionError("Contradictory transaction")
    # Canonical set order survives sorted-key JSON schema round trips.
    return [sorted(row) for row in rows]


def domain(item):
    name=variable(item)
    if name.startswith(("ll_","detox_","emotion_","sentiment_")):return "lyrics"
    if name.startswith("mb_"):return "metadata"
    if name=="genre":return "genre"
    if name=="decade":return "history"
    return "chart"


def category(antecedent,consequent):
    domains={domain(x) for x in [*antecedent,consequent]}
    strict=all(domain(a)!=domain(consequent) for a in antecedent)
    return dict(category="C: cross-domain" if strict else "B: same-family measurement overlap",
                multidimensional=len(antecedent)>1,historical="history" in domains,
                cross_domain=len(domains)>1,strict_cross_domain=strict,domains=sorted(domains),circular=False)


def outcome_bits(consequent,negative,index,full,frame):
    """A negative numerical item means observed outside that bin, never missing."""
    universe=full;name=variable(consequent)
    if negative and name in frame.columns:universe=bitmask(frame[name].notna().to_numpy())
    bits=index.get(consequent,0)
    return ((universe^bits)&universe if negative else bits),universe


def rule_metrics(a,b,n):
    na=count(a);nb=count(b);joint=count(a&b)
    support=joint/n if n else None;confidence=joint/na if na else None;base=nb/n if n else None
    return dict(n=n,antecedent_n=na,consequent_n=nb,joint_n=joint,support=support,confidence=confidence,
        baseline=base,lift=confidence/base if na and nb else None,leverage=support-na*nb/n**2 if n else None,
        risk_difference=confidence-base if na else None)


def cmh_p(a,b,year_masks):
    """Two-sided asymptotic CMH for independence conditional on debut year."""
    difference=0.;variance=0.
    for mask in year_masks:
        n=count(mask)
        if n<2:continue
        na=count(a&mask);nb=count(b&mask);joint=count(a&b&mask)
        difference+=joint-na*nb/n
        variance+=na*(n-na)*nb*(n-nb)/(n*n*(n-1))
    return float(stats.chi2.sf(difference*difference/variance,1)) if variance>0 else 1.


def bitmask(values):
    return sum(1<<int(i) for i in np.flatnonzero(values))


def benchmark(train_transactions):
    rows=[];patterns={}
    for support in c.CONFIG["frequent_supports"]:
        minimum=math.ceil(support*len(train_transactions));reference=None
        for name,method in [("apriori",apriori),("fpgrowth",fpgrowth),("eclat",eclat)]:
            def run():
                started=time.perf_counter();found=method(train_transactions,minimum,4)
                return dict(patterns=[[list(k),v] for k,v in sorted(found.items())],**c.usage(started))
            result,reused=c.checkpoint(f"patterns/{support}/{name}",run,["src/course_patterns.py"])
            found={tuple(k):v for k,v in result["patterns"]}
            if reference is not None and reference!=found:raise AssertionError("Algorithms disagree")
            reference=found
            rows.append(dict(algorithm=name,support_threshold=support,min_count=minimum,n=len(train_transactions),
                itemsets=len(found),equivalent=True,result_sha256=c.digest(result["patterns"]),
                wall_seconds=result["wall_seconds"],peak_rss_bytes=result["peak_rss_bytes"]))
            print(f"{name} support={support}: {len(found)} itemsets ({result['wall_seconds']:.2f}s), reused={reused}",flush=True)
        patterns[support]=reference
        records=closed_maximal(reference,train_transactions,minimum)
        c.write_csv(c.PUBLIC/f"frequent_patterns/itemsets_support_{support:.2f}.csv.gz",records)
    c.write_csv(c.PUBLIC/"frequent_patterns/algorithm_comparison.csv",rows)
    return patterns


def rules(patterns,tx,frames):
    indexes={name:vertical(rows) for name,rows in tx.items()};full={n:(1<<len(rows))-1 for n,rows in tx.items()}
    candidates={}
    for items in patterns:
        if len(items)<2:continue
        for consequent in items:
            ant=tuple(i for i in items if i!=consequent)
            candidates[(ant,consequent,False)]="primary"
    index=indexes["train"];n=len(tx["train"]);minimum=max(20,math.ceil(.005*n))
    single=[i for i in sorted(index) if count(index[i])>=20]
    # All cross-domain directed pairs with train-supported positive/complemented consequent.
    for a,b in itertools.permutations(single,2):
        if domain(a)==domain(b) or variable(a)==variable(b):continue
        for negative in (False,True):
            outcome,_=outcome_bits(b,negative,index,full["train"],frames["train"])
            if count(index[a]&outcome)>=minimum:
                candidates.setdefault(((a,),b,negative),"negative" if negative else "rare_pair")
    year_masks=[bitmask(frames["test"].year.to_numpy()==year) for year in sorted(frames["test"].year.unique())]
    rows=[]
    for (ant,con,negative),family in sorted(candidates.items()):
        row=dict(rule_id=c.digest([ant,con,negative])[:16],antecedent=list(ant),consequent=con,
                 negative_consequent=negative,family=family,**category(ant,con))
        for name in ("train","validation","test"):
            b,universe=outcome_bits(con,negative,indexes[name],full[name],frames[name])
            a=intersection(ant,indexes[name],universe)
            measured=rule_metrics(a,b,count(universe))
            row.update({name+"_"+k:v for k,v in measured.items()})
            parent_confidences=[]
            for i in range(len(ant)):
                parent=intersection(ant[:i]+ant[i+1:],indexes[name],universe)
                if count(parent)>=20:parent_confidences.append(count(parent&b)/count(parent))
            best_parent=max(parent_confidences) if parent_confidences else None
            row[name+"_best_parent_confidence"]=best_parent
            row[name+"_confidence_gain_vs_best_parent"]=(measured["confidence"]-best_parent) if measured["confidence"] is not None and best_parent is not None else None
            if name=="test":
                supported=min(measured["antecedent_n"],measured["consequent_n"],measured["n"]-measured["antecedent_n"],measured["n"]-measured["consequent_n"])>=20
                row["test_supported"]=supported;row["p_value"]=cmh_p(a,b,[mask&universe for mask in year_masks]) if supported else 1.
        row["stable_positive"]=all(row[n+"_lift"] is not None and row[n+"_lift"]>1 for n in ("train","validation","test"))
        rows.append(row)
    q=stats.false_discovery_control([r["p_value"] for r in rows],method="by")
    for row,value in zip(rows,q):row["q_by_global"]=float(value)
    c.write_csv(c.PUBLIC/"association_rules/all_rules.csv.gz",rows)
    eligible=[r for r in rows if r["strict_cross_domain"] and r["test_antecedent_n"]>=100 and r["test_joint_n"]>=20 and not r["historical"]]
    eligible.sort(key=lambda r:(not r["stable_positive"],r["q_by_global"]>.05,-abs(r["test_risk_difference"] or 0),r["rule_id"]))
    c.write_csv(c.PUBLIC/"association_rules/cross_domain_leaderboard.csv",eligible[:100])
    # Domain/direction quotas provide presentation coverage, not a novelty score.
    # Multi-condition rules compete separately and must add to their best parent.
    buckets=defaultdict(list)
    for row in eligible:
        if row["multidimensional"] and (row["test_confidence_gain_vs_best_parent"] or 0)<=.01:continue
        key=(tuple(sorted({domain(a) for a in row["antecedent"]})),domain(row["consequent"]),row["multidimensional"])
        buckets[key].append(row)
    chosen=[]
    for key,bucket in sorted(buckets.items()):
        used=set();selected=[]
        for row in bucket:
            # Keep one direction/value variant for each underlying variable combination.
            variables=tuple(sorted([variable(a) for a in row["antecedent"]]+[variable(row["consequent"])]))
            if variables in used:continue
            selected.append(row);used.add(variables)
            if len(selected)>=2:break
        chosen.extend(selected)
    chosen=sorted(chosen,key=lambda r:r["rule_id"])
    c.write_csv(c.PUBLIC/"association_rules/presentation_shortlist.csv",chosen)
    details=[];sensitivity=[]
    for row in chosen:
        for name,frame in frames.items():
            b,universe=outcome_bits(row["consequent"],row["negative_consequent"],indexes[name],full[name],frame)
            a=intersection(row["antecedent"],indexes[name],universe)
            groups=[("decade",g,frame.decade.eq(g).to_numpy()) for g in sorted(frame.decade.unique())]
            groups += [("genre",g,frame.primary_genre.eq(g).to_numpy()) for g in sorted(frame.primary_genre.unique())]
            groups += [("period",g,frame.period.eq(g).to_numpy()) for g in sorted(frame.period.unique())]
            for kind,group,values in groups:
                mask=bitmask(values)&universe;n_group=count(mask);metrics=rule_metrics(a&mask,b&mask,n_group)
                details.append(dict(rule_id=row["rule_id"],split=name,group_type=kind,group=group,
                                    adequate=n_group>=100 and metrics["antecedent_n"]>=20,**metrics))
        frame=frames["test"];b,universe=outcome_bits(row["consequent"],row["negative_consequent"],indexes["test"],full["test"],frame)
        a=intersection(row["antecedent"],indexes["test"],universe)
        av=np.array([bool(a&(1<<i)) for i in range(len(frame))]);bv=np.array([bool(b&(1<<i)) for i in range(len(frame))])
        observed=np.array([bool(universe&(1<<i)) for i in range(len(frame))]);artists=frame.artist.to_numpy()
        groups=[np.flatnonzero((artists==g)&observed) for g in sorted(set(artists[observed]))];rng=np.random.default_rng(c.SEED)
        values=[]
        for _ in range(c.CONFIG["bootstrap_repeats"]):
            sample=np.concatenate([groups[i] for i in rng.integers(0,len(groups),len(groups))]);aa=av[sample];bb=bv[sample]
            if aa.sum():values.append(float(bb[aa].mean()-bb.mean()))
        lo,hi=np.quantile(values,[.025,.975])
        sensitivity.append(dict(rule_id=row["rule_id"],artist_credits=len(groups),risk_difference_low=lo,risk_difference_high=hi,
                                bootstrap_repeats=len(values),scope="post-hoc fixed-rule exact-credit cluster bootstrap"))
    c.write_csv(c.PUBLIC/"association_rules/historical_and_genre_stability.csv",details)
    c.write_csv(c.PUBLIC/"association_rules/artist_sensitivity.csv",sensitivity)
    # Complete bounded pairwise conditional comparison, no new inferential claims.
    reversals=[];frame=frames["test"]
    genre_masks={g:bitmask(frame.primary_genre.eq(g).to_numpy()) for g in sorted(frame.primary_genre.unique())}
    for row in rows:
        if len(row["antecedent"])!=1 or row["negative_consequent"] or not row["cross_domain"] or "genre" in row["domains"]:continue
        a=intersection(row["antecedent"],indexes["test"],full["test"]);b=indexes["test"].get(row["consequent"],0)
        for genre,mask in genre_masks.items():
            metrics=rule_metrics(a&mask,b&mask,count(mask));adequate=metrics["n"]>=100 and metrics["antecedent_n"]>=20
            effect=metrics["risk_difference"];pooled=row["test_risk_difference"]
            reversals.append(dict(rule_id=row["rule_id"],antecedent=row["antecedent"],consequent=row["consequent"],genre=genre,
                adequate=adequate,pooled_risk_difference=pooled,reversal=bool(adequate and effect is not None and pooled is not None and effect*pooled<0 and abs(effect)>=.05 and abs(pooled)>=.05),**metrics))
    c.write_csv(c.PUBLIC/"association_rules/conditional_pairs.csv.gz",reversals)
    return dict(rules=len(rows),by_below_05=sum(r["q_by_global"]<=.05 for r in rows),
                families=dict(Counter(r["family"] for r in rows)),conditional_cells=len(reversals),reversal_cells=sum(r["reversal"] for r in reversals),
                presentation_shortlist=len(chosen),strict_cross_domain=sum(r["strict_cross_domain"] for r in rows))


def run():
    started=time.perf_counter();c.freeze();tr,va,te=c.primary_split(c.data());frames=dict(train=tr,validation=va,test=te)
    bins=fit_bins(tr);longevity=float(tr.chart_weeks.quantile(.75));tx={n:transactions(f,bins,longevity) for n,f in frames.items()}
    c.write_json(c.PUBLIC/"frequent_patterns/transaction_schema.json",dict(bins=bins,longevity_threshold=longevity,
        split_n={n:len(v) for n,v in tx.items()},transaction_hashes={n:c.digest(v) for n,v in tx.items()},
        missing_metadata="no item; not imputed",middle="no tail item; absence is not a low score"))
    patterns=benchmark(tx["train"])
    summary=rules(patterns[c.CONFIG["primary_support"]],tx,frames)
    c.write_json(c.PUBLIC/"frequent_patterns/execution.json",dict(**summary,**c.usage(started)))
    print(summary,flush=True)


if __name__=="__main__":
    with threadpool_limits(limits=1):run()
