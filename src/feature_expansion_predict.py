"""NumPy-only replay for exported fitted models (also used by the small demo)."""
from __future__ import annotations
import numpy as np
import pandas as pd


class Preprocessor:
    def __init__(self,columns):self.columns=list(columns)

    def fit(self,frame):
        self.numeric=[c for c in self.columns if c!='primary_genre'];self.categorical=[c for c in self.columns if c=='primary_genre']
        a=frame[self.numeric].to_numpy(float)
        self.median=np.array([np.median(a[np.isfinite(a[:,i]),i]) if np.isfinite(a[:,i]).any() else 0. for i in range(a.shape[1])])
        a=np.where(np.isfinite(a),a,self.median);self.mean=a.mean(axis=0);self.scale=a.std(axis=0);self.scale[self.scale==0]=1.
        self.categories={c:sorted(frame[c].fillna('__missing__').astype(str).unique()) for c in self.categorical}
        self.names=self.numeric+[c+'='+v for c in self.categorical for v in self.categories[c]]
        return self

    def transform(self,frame):
        a=frame[self.numeric].to_numpy(float);a=(np.where(np.isfinite(a),a,self.median)-self.mean)/self.scale
        extra=[frame[c].fillna('__missing__').astype(str).eq(v).to_numpy(float)[:,None] for c in self.categorical for v in self.categories[c]]
        return np.concatenate([a]+extra,axis=1) if extra else a

    def export(self):
        return {k:getattr(self,k) for k in ['columns','numeric','categorical','median','mean','scale','categories','names']}

    @classmethod
    def restore(cls,state):
        p=cls(state['columns'])
        for k,v in state.items():setattr(p,k,np.asarray(v,float) if k in ['median','mean','scale'] else v)
        return p


def export_estimator(estimator,classification):
    name=type(estimator).__name__
    if name.startswith(('Logistic','Ridge')):
        return dict(kind='linear',classification=classification,coef=estimator.coef_.reshape(-1),intercept=float(np.asarray(estimator.intercept_).reshape(-1)[0]))
    if name.startswith('DecisionTree'):
        t=estimator.tree_;value=t.value[:,0,:]
        if classification:value=value[:,1]/value.sum(axis=1)
        else:value=value[:,0]
        return dict(kind='tree',classification=classification,feature=t.feature,threshold=t.threshold,left=t.children_left,right=t.children_right,value=value)
    if name.startswith('HistGradient'):
        trees=[]
        for predictors in estimator._predictors:
            n=predictors[0].nodes
            if n['is_categorical'].any():raise ValueError('Categorical HGB export unsupported')
            trees.append(dict(feature=n['feature_idx'],threshold=n['num_threshold'],left=np.where(n['is_leaf'],-1,n['left']),right=np.where(n['is_leaf'],-1,n['right']),value=n['value']))
        return dict(kind='boosting',classification=classification,baseline=float(estimator._baseline_prediction.ravel()[0]),trees=trees)
    raise ValueError('Unsupported estimator '+name)


def tree_predict(tree,x):
    feature=np.asarray(tree['feature'],int);threshold=np.asarray(tree['threshold'],float);left=np.asarray(tree['left'],int);right=np.asarray(tree['right'],int);value=np.asarray(tree['value'],float)
    nodes=np.zeros(len(x),int)
    while True:
        active=np.flatnonzero(left[nodes]>=0)
        if not len(active):break
        n=nodes[active];nodes[active]=np.where(x[active,feature[n]]<=threshold[n],left[n],right[n])
    return value[nodes]


def predict_export(bundle,frame):
    p=Preprocessor.restore(bundle['preprocessing']);x=p.transform(frame);m=bundle['estimator']
    if m['kind']=='linear':result=x@np.asarray(m['coef'])+m['intercept']
    elif m['kind']=='tree':return tree_predict(m,x)
    elif m['kind']=='boosting':
        result=np.full(len(x),m['baseline'],float)
        for tree in m['trees']:result+=tree_predict(tree,x)
    else:raise ValueError('Unknown model type')
    return 1/(1+np.exp(-np.clip(result,-709,709))) if m['classification'] else result
