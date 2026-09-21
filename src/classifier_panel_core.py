"""Pure deterministic chunk/summary utilities; no model or corpus side effects."""
import math
import statistics
from lyriclens_diagnostics import quantile

VERSION='classifier-panel-v1'
AGGREGATIONS=('mean','token_weighted_mean','max','q90')

def chunk_ranges(token_count, budget):
    """Balanced contiguous partitions: every content token exactly once, no tiny tail."""
    if token_count<=0 or budget<=0:raise ValueError('Empty input or nonpositive budget')
    n=(token_count+budget-1)//budget
    width,remainder=divmod(token_count,n)
    start=0;result=[]
    for i in range(n):
        end=start+width+(i<remainder)
        result.append((start,end));start=end
    validate_ranges(result,token_count,budget)
    return result

def validate_ranges(ranges,token_count,budget):
    cursor=0
    for start,end in ranges:
        if start!=cursor or not start<end<=token_count or end-start>budget:
            raise ValueError('Missing, repeated or oversized content span')
        cursor=end
    if cursor!=token_count or not ranges:raise ValueError('Uncovered input')

def aggregate(values,weights):
    if not values or len(values)!=len(weights):raise ValueError('Missing chunk scores/weights')
    if any(not math.isfinite(v) or not 0<=v<=1 for v in values):raise ValueError('Invalid chunk score')
    if any(w<=0 or not math.isfinite(w) for w in weights):raise ValueError('Invalid token weights')
    if len(values)==1:return {k:values[0] for k in AGGREGATIONS}
    return dict(mean=statistics.mean(values),token_weighted_mean=sum(v*w for v,w in zip(values,weights))/sum(weights),
                max=max(values),q90=quantile(values,.9))

def softmax(logits):
    if not logits or any(not math.isfinite(x) for x in logits):raise ValueError('Invalid logits')
    exps=[math.exp(x-max(logits)) for x in logits];total=sum(exps)
    return [x/total for x in exps]

def sigmoid(x):
    if not math.isfinite(x):raise ValueError('Invalid logit')
    return 1/(1+math.exp(-x)) if x>=0 else math.exp(x)/(1+math.exp(x))

def bart_score(logits,contradiction=0,entailment=2):
    """HF multi_label=True semantics: neutral retained separately, not in this ratio."""
    if len(logits)!=3:raise ValueError('Expected three NLI logits')
    return softmax([logits[contradiction],logits[entailment]])[1]
