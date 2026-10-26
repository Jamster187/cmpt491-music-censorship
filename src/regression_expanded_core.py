"""Training-only variable blocks feeding the preserved optimized OLS kernel."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from scipy import linalg

import regression_core as original_core
import regression_expanded_spec as spec


def category(value):
    if pd.isna(value):return None
    if isinstance(value,(int,float,np.number)) and float(value).is_integer():return str(int(value))
    return str(value)


def labels(value):
    if pd.isna(value):return ()
    result=json.loads(value)
    if not isinstance(result,list) or any(not isinstance(x,str) for x in result):raise ValueError('Invalid secondary-genre list')
    return tuple(sorted(set(result)))


class BlockEncoder:
    def __init__(self,state=None):
        self.state=state or {};self.groups={}

    @staticmethod
    def raw(frame,name,record):
        fields=record['source_columns'];kind=record['kind']
        if kind in ['numeric','numeric_block']:
            x=frame[fields].to_numpy(float)
            if np.isinf(x).any():raise ValueError('Infinite predictor '+name)
            return np.where(np.isnan(x),record['median'],x)
        if kind=='categorical':
            values=frame[fields[0]].map(category).to_numpy()
            return np.column_stack([values==c for c in record['levels'][1:]]).astype(float) if len(record['levels'])>1 else np.zeros((len(frame),0))
        if kind=='multilabel':
            values=frame[fields[0]].map(labels)
            return np.array([[float(c in v) for c in record['levels']] for v in values],float).reshape(len(frame),len(record['levels']))
        raise ValueError('Unsupported variable encoding')

    def fit(self,frame,names):
        self.state=dict(names=list(names),variables={})
        for name in names:
            definition=spec.REGISTRY[name];kind=definition['kind'];fields=definition['source_columns']
            r=dict(kind=kind,source_columns=fields)
            if kind in ['numeric','numeric_block']:
                x=frame[fields].to_numpy(float)
                if np.isinf(x).any():raise ValueError('Infinite training predictor '+name)
                r['median']=[float(np.median(x[np.isfinite(x[:,i]),i])) if np.isfinite(x[:,i]).any() else 0. for i in range(x.shape[1])]
            elif kind=='categorical':r['levels']=sorted(set(frame[fields[0]].map(category).dropna()))
            elif kind=='multilabel':r['levels']=sorted({c for v in frame[fields[0]].map(labels) for c in v})
            else:raise ValueError('Unknown predictor kind')
            raw=self.raw(frame,name,r);keep=np.flatnonzero(np.ptp(raw,axis=0)>0)
            r.update(keep=keep.tolist(),mean=raw[:,keep].mean(axis=0).tolist(),std=raw[:,keep].std(axis=0).tolist(),
                dropped=np.flatnonzero(np.ptp(raw,axis=0)==0).tolist(),raw_width=raw.shape[1])
            self.state['variables'][name]=r
        return self

    def transform(self,frame):
        arrays=[np.ones((len(frame),1))];position=1;self.groups={}
        for name in self.state['names']:
            r=self.state['variables'][name];a=self.raw(frame,name,r)[:,r['keep']]
            a=(a-r['mean'])/r['std'];arrays.append(a);self.groups[name]=list(range(position,position+a.shape[1]));position+=a.shape[1]
        return np.ascontiguousarray(np.column_stack(arrays))

    def unsupported(self,frame):
        result={}
        for name in self.state['names']:
            r=self.state['variables'][name]
            if r['kind']=='categorical':result[name]=int(frame[r['source_columns'][0]].map(category).map(lambda v:v is not None and v not in r['levels']).sum())
            elif r['kind']=='multilabel':result[name]=int(frame[r['source_columns'][0]].map(labels).map(lambda v:bool(set(v)-set(r['levels']))).sum())
        return result


def prepare(task,start,end):
    train,validation=spec.partition(task['track'],task['horizon'],task['target'],start,end)
    encoder=BlockEncoder().fit(train,spec.predictors(task['track']));x=encoder.transform(train);v=encoder.transform(validation)
    fold=original_core.Fold(x,v,train.outcome.to_numpy(float),validation.outcome.to_numpy(float),np.ones(len(train)),np.ones(len(validation)),
        encoder.groups,encoder,train,validation,dict(start=start,end=end or spec.end_date(),track=task['track'],horizon=task['horizon'],target=task['target'],
            train_ids_sha256=spec.digest(train.song_id.tolist()),validation_ids_sha256=spec.digest(validation.song_id.tolist())))
    return fold


def training_r2(fold,beta):
    sse=np.sum(fold.w*fold.centered_y**2)-2*(fold.h@beta)+np.einsum('ij,ij->j',beta,fold.G@beta)
    sse=np.maximum(sse,0);variance=np.average(fold.centered_y**2,weights=fold.w)
    return 1-sse/(fold.w.sum()*variance) if variance>0 else np.full(beta.shape[1],np.nan)


def export_model(fold,combo,task,selection_hash):
    beta,rank,fallback=fold.fit_batch([combo]);indices=fold.indices(combo)
    state=dict(names=list(combo),variables={n:fold.encoder.state['variables'][n] for n in combo})
    return spec.clean(dict(version=spec.CONFIG['version'],task=task,predictors=list(combo),encoder=state,coefficients=beta[indices,0],target_center=fold.mean,
        training_mean=fold.mean,training_median=fold.median,n_train=len(fold.y),rank=int(rank[0]),fallback=bool(fallback[0]),selection_sha256=selection_hash,
        training_ids_sha256=spec.digest(fold.train.song_id.tolist()),training_cutoff=fold.metadata['start']))


def predict_model(model,frame):return BlockEncoder(model['encoder']).transform(frame)@np.asarray(model['coefficients'])+model['target_center']


def independent_reference(fold,combo):
    """Direct full-row SciPy SVD check, independent of cached cross-products/QR."""
    return fold.reference_check(combo)


metrics=original_core.metrics
