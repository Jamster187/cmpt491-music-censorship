"""V3 variable-block encoder and unchanged validated cached OLS kernel."""
import numpy as np
import regression_expanded_core as v2core
import regression_cross_domain_spec as spec


class Encoder(v2core.BlockEncoder):
    def fit(self,frame,names):
        self.state=dict(names=list(names),variables={})
        for name in names:
            definition=spec.REGISTRY[name];kind=definition['kind'];fields=definition['source_columns'];r=dict(kind=kind,source_columns=fields)
            if kind in ['numeric','numeric_block']:
                x=frame[fields].to_numpy(float)
                if np.isinf(x).any():raise ValueError('Infinite training predictor '+name)
                r['median']=[float(np.median(x[np.isfinite(x[:,i]),i])) if np.isfinite(x[:,i]).any() else 0. for i in range(x.shape[1])]
            elif kind=='categorical':r['levels']=sorted(set(frame[fields[0]].map(v2core.category).dropna()))
            elif kind=='multilabel':r['levels']=sorted({c for v in frame[fields[0]].map(v2core.labels) for c in v})
            else:raise ValueError('Unsupported encoding')
            raw=self.raw(frame,name,r);keep=np.flatnonzero(np.ptp(raw,axis=0)>0)
            r.update(keep=keep.tolist(),mean=raw[:,keep].mean(axis=0).tolist(),std=raw[:,keep].std(axis=0).tolist(),dropped=np.flatnonzero(np.ptp(raw,axis=0)==0).tolist(),raw_width=raw.shape[1])
            self.state['variables'][name]=r
        return self


def prepare(target,start,end):
    train,valid=spec.partition(target,start,end)
    names=[n for n in spec.NAMES if spec.pair(target,n)[0]>1]
    encoder=Encoder().fit(train,names);x=encoder.transform(train);v=encoder.transform(valid)
    fold=v2core.original_core.Fold(x,v,train.outcome.to_numpy(float),valid.outcome.to_numpy(float),np.ones(len(train)),np.ones(len(valid)),encoder.groups,encoder,train,valid,
        dict(start=start,end=end or spec.v2.end_date(),target=target,train_ids_sha256=spec.digest(train.song_id.tolist()),validation_ids_sha256=spec.digest(valid.song_id.tolist()),validation_variance=float(np.var(valid.outcome)),training_variance=float(np.var(train.outcome))))
    return fold


def export_model(fold,combo,selection_hash):
    model=v2core.export_model(fold,combo,dict(target=fold.metadata['target']),selection_hash)
    model['version']=spec.CONFIG['version'];return model


predict_model=v2core.predict_model
metrics=v2core.metrics
training_r2=v2core.training_r2


def evaluate(fold,combos):
    """Exact residual metrics using sparse coefficients and cached contiguous columns.

    Every row and every encoded categorical coefficient contributes. This avoids
    multiplying the many zero coefficients of each 1/2/3-variable model.
    """
    import time
    from scipy import sparse
    start=time.perf_counter();beta,ranks,fallback=fold.fit_batch(combos);fit_seconds=time.perf_counter()-start;start=time.perf_counter()
    if not hasattr(fold,'VT'):fold.VT=np.ascontiguousarray(fold.V.T)
    coefficients=sparse.csr_matrix(beta.T);residual=fold.centered_z[None,:]-(coefficients@fold.VT)
    mse=(residual*residual)@fold.u/fold.u.sum();mae=np.abs(residual)@fold.u/fold.u.sum()
    variance=float(np.average((fold.z-np.average(fold.z,weights=fold.u))**2,weights=fold.u));baseline=fold.baseline['mse']
    result=dict(mse=mse,mae=mae,r2=1-mse/variance if variance>0 else np.full(len(combos),np.nan),skill=1-mse/baseline if baseline>0 else np.full(len(combos),np.nan),rank=ranks,fallback=fallback)
    return result,dict(fit_seconds=fit_seconds,metrics_seconds=time.perf_counter()-start,fits=len(combos),qr_svd_fallbacks=int(fallback.sum()))
