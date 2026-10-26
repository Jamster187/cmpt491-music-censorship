"""Compact float64 hierarchy with durable checksummed chunk checkpointing."""
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import numpy as np
import regression_cross_domain_spec as spec


def save_array(path,array):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
    with tmp.open('wb') as f:np.save(f,array,allow_pickle=False);f.flush();os.fsync(f.fileno())
    tmp.replace(path)


def checked_array(path,expected):
    if path.exists():
        actual=np.load(path,allow_pickle=False)
        if actual.dtype!=expected.dtype or not np.array_equal(actual,expected):raise ValueError('Changed catalog: '+str(path))
    else:save_array(path,expected)


def global_catalog():
    spec.LOCAL.mkdir(parents=True,exist_ok=True);p=spec.LOCAL/'candidate_catalog.npy'
    checked_array(p,spec.catalog());return spec.sha(p)


class Store:
    def __init__(self,target,provenance=None,base=None,sample_ids=None):
        self.target=target;self.path=Path(base) if base is not None else spec.LOCAL/'targets'/target
        self.path.mkdir(parents=True,exist_ok=True);catalog_hash=global_catalog()
        categories,reasons=spec.relations(target);ids=np.flatnonzero(categories>1).astype(np.uint32)
        if sample_ids is not None:
            selected=np.asarray(sorted(sample_ids),np.uint32)
            if not set(selected)<=set(ids):raise ValueError('Benchmark included invalid candidates')
            ids=selected
        self.n=len(ids);self.ids=ids;self.categories=categories[ids]
        identity=dict(target=target,provenance=provenance or spec.provenance(),catalog_sha256=catalog_hash,valid_ids_sha256=hashlib.sha256(ids.tobytes()).hexdigest(),rows=self.n)
        p=self.path/'identity.json'
        if p.exists() and spec.read_json(p)!=spec.clean(identity):raise ValueError('Checkpoint identity mismatch')
        if not p.exists():spec.write_json(p,identity)
        for name,value in [('categories.npy',categories),('exclusion_rules.npy',reasons),('valid_ids.npy',ids)]:checked_array(self.path/name,value)
        self.db=sqlite3.connect(self.path/'checkpoint.sqlite');self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE IF NOT EXISTS chunks(fold INTEGER CHECK(fold BETWEEN 0 AND 3),start INTEGER,stop INTEGER,sha256 TEXT,PRIMARY KEY(fold,start));')
        if self.db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Checkpoint SQL integrity failed')
        shapes={'metrics.npy':((4,self.n,2),np.dtype('<f8'),np.nan),'status.npy':((4,self.n),np.dtype('<u2'),0)}
        for name,(shape,dtype,fill) in shapes.items():
            p=self.path/name
            if not p.exists():
                if self.db.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]:raise ValueError('Committed data file missing')
                tmp=p.with_name(p.name+'.tmp');a=np.lib.format.open_memmap(tmp,mode='w+',dtype=dtype,shape=shape);a[:]=fill;a.flush();del a;tmp.replace(p)
            a=np.load(p,mmap_mode='r+',allow_pickle=False)
            if a.shape!=shape or a.dtype!=dtype:raise ValueError('Unsupported data array schema')
            if name=='metrics.npy':self.metrics=a
            else:self.status=a
        self.verify_chunks()

    def get(self,key):
        r=self.db.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        return json.loads(r[0]) if r else None
    def put(self,key,value):self.db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',(key,json.dumps(spec.clean(value),sort_keys=True,allow_nan=False)))
    def checksum(self,fold,start,stop):
        h=hashlib.sha256(self.metrics[fold,start:stop].tobytes());h.update(self.status[fold,start:stop].tobytes());return h.hexdigest()
    def verify_chunks(self):
        size=spec.CONFIG['checkpoint_rows']
        for r in self.db.execute('SELECT * FROM chunks ORDER BY fold,start'):
            if r['start']%size or r['stop']!=min(r['start']+size,self.n) or r['start']>=self.n or r['sha256']!=self.checksum(r['fold'],r['start'],r['stop']):raise ValueError('Committed chunk is corrupt or misaligned')
    def completed(self,fold):return {r[0] for r in self.db.execute('SELECT start FROM chunks WHERE fold=?',(fold,))}
    def complete(self,folds=range(3)):
        expected=set(range(0,self.n,spec.CONFIG['checkpoint_rows']))
        return all(self.completed(f)==expected for f in folds)
    def save(self,fold,start,values,status,metadata,timing):
        stop=start+len(values)
        if start%spec.CONFIG['checkpoint_rows'] or stop!=min(start+spec.CONFIG['checkpoint_rows'],self.n):raise ValueError('Invalid chunk boundaries')
        if not np.isfinite(values).all() or (values<0).any():raise ValueError('Invalid squared/absolute errors')
        self.metrics[fold,start:stop]=values;self.status[fold,start:stop]=status
        self.metrics.flush();self.status.flush()
        for name in ['metrics.npy','status.npy']:
            with (self.path/name).open('rb') as f:os.fsync(f.fileno())
        checksum=self.checksum(fold,start,stop)
        with self.db:
            self.db.execute('INSERT INTO chunks VALUES (?,?,?,?)',(fold,start,stop,checksum));self.put('fold_'+str(fold),metadata)
            total=self.get('timing') or {}
            for key,value in timing.items():total[key]=total.get(key,0)+value
            self.put('timing',total)
    def scores(self,evaluation=False):
        if not self.complete(range(4) if evaluation else range(3)):raise ValueError('Incomplete hierarchy')
        meta=[self.get('fold_'+str(i)) for i in range(4 if evaluation else 3)]
        mse=np.asarray(self.metrics[:3,:,0]);mae=np.asarray(self.metrics[:3,:,1]);variance=np.asarray([m['validation_variance'] for m in meta[:3]])[:,None];base=np.asarray([m['baseline']['mse'] for m in meta[:3]])[:,None]
        period_r2=1-mse/variance;period_skill=1-mse/base
        result=dict(validation_r2=period_r2.mean(axis=0),validation_mae=mae.mean(axis=0),validation_rmse=np.sqrt(mse.mean(axis=0)),validation_skill=period_skill.mean(axis=0),worst_period_r2=period_r2.min(axis=0),period_r2_range=np.ptp(period_r2,axis=0),worst_period_skill=period_skill.min(axis=0),period_r2=period_r2,period_skill=period_skill)
        if evaluation:
            v=meta[3]['validation_variance'];base=meta[3]['baseline']['mse'];mse=np.asarray(self.metrics[3,:,0])
            result.update(evaluation_r2=1-mse/v if v>0 else np.full(self.n,np.nan),evaluation_mae=np.asarray(self.metrics[3,:,1]),evaluation_rmse=np.sqrt(mse),evaluation_skill=1-mse/base if base>0 else np.full(self.n,np.nan))
        return result
    def order(self):
        scores=self.scores();order=np.lexsort((self.ids,-scores['validation_r2'])).astype(np.uint32)
        p=self.path/'validation_order.npy';checked_array(p,order);return order
    def subset(self,view,configuration='combined',k=None):
        mask=self.categories>=spec.VIEWS[view]
        mask&=spec.configuration_filter(configuration)[self.ids]
        if k is not None:mask&=(spec.catalog()[self.ids]!=255).sum(axis=1)==k
        return mask
    def close(self):
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');self.db.close();del self.metrics;del self.status
