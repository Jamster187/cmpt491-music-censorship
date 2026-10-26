"""Compact transactional exhaustive results; validation-only deterministic ranking."""
from pathlib import Path
import json
import sqlite3
import numpy as np
import pandas as pd
import regression_expanded_spec as spec


class Store:
    def __init__(self,path,identity,candidates,names):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path);self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON');self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        if self.db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Corrupt checkpoint')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS candidates(id INTEGER PRIMARY KEY,k INTEGER NOT NULL,i1 INTEGER NOT NULL,i2 INTEGER,i3 INTEGER,mask INTEGER NOT NULL,overlap TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS scores(id INTEGER REFERENCES candidates(id),fold INTEGER CHECK(fold BETWEEN 0 AND 3),r2 REAL NOT NULL,mae REAL NOT NULL,mse REAL NOT NULL,skill REAL NOT NULL,rank INTEGER NOT NULL,fallback INTEGER NOT NULL,train_r2 REAL,PRIMARY KEY(id,fold));
        CREATE VIEW IF NOT EXISTS averages AS SELECT c.*,AVG(s.r2) validation_r2,AVG(s.mae) validation_mae,AVG(s.mse) validation_mse,AVG(s.skill) validation_skill,MIN(s.skill) worst_period_skill,MAX(s.skill)-MIN(s.skill) period_skill_range,SUM(s.fallback) qr_svd_folds FROM candidates c JOIN scores s ON c.id=s.id WHERE s.fold<3 GROUP BY c.id HAVING COUNT(*)=3;
        ''')
        previous=self.get('identity');identity=spec.clean(identity)
        if previous is not None and previous!=identity:self.close();raise ValueError('Resume identity mismatch')
        lookup={n:i for i,n in enumerate(names)}
        rows=[(i,len(c),*([lookup[n] for n in c]+[None]*(3-len(c))),spec.configuration_mask(c),spec.overlap_flags(c)) for i,c in candidates]
        if previous is None:
            with self.db:
                self.put('identity',identity);self.put('predictors',names)
                self.db.executemany('INSERT INTO candidates VALUES (?,?,?,?,?,?,?)',rows)
        elif [tuple(r) for r in self.db.execute('SELECT * FROM candidates ORDER BY id')]!=rows:
            self.close();raise ValueError('Candidate catalog changed')

    def get(self,key):
        row=self.db.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self,key,value):self.db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',(key,json.dumps(spec.clean(value),sort_keys=True,allow_nan=False)))
    def completed(self,fold):return {r[0] for r in self.db.execute('SELECT id FROM scores WHERE fold=?',(fold,))}
    def complete(self,folds=range(3)):
        n=self.db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
        return all(len(self.completed(f))==n for f in folds)

    def save(self,fold,candidates,result,metadata,timing,train_r2=None):
        rows=[(i,fold,*[result[k][j] for k in ['r2','mae','mse','skill','rank','fallback']],None if train_r2 is None else train_r2[j]) for j,(i,_) in enumerate(candidates)]
        if any(not np.isfinite(result[k]).all() for k in ['r2','mae','mse','skill']):raise ValueError('Nonfinite model scores')
        with self.db:
            self.db.executemany('INSERT INTO scores VALUES (?,?,?,?,?,?,?,?,?)',spec.clean(rows));self.put('fold_'+str(fold),metadata)
            total=self.get('timing') or {}
            for k,v in timing.items():total[k]=total.get(k,0)+v
            self.put('timing',total)

    def rankings(self,evaluation=False):
        if not self.complete():raise ValueError('Incomplete validation cannot be ranked')
        query='SELECT a.*'+(',e.r2 evaluation_r2,e.mae evaluation_mae,e.mse evaluation_mse,e.skill evaluation_skill,e.rank evaluation_encoded_rank,e.fallback evaluation_svd,e.train_r2' if evaluation else '')+' FROM averages a'+(' JOIN scores e ON e.id=a.id AND e.fold=3' if evaluation else '')+' ORDER BY a.validation_skill DESC,a.k,a.id'
        f=pd.read_sql_query(query,self.db)
        if evaluation and not self.complete(range(4)):raise ValueError('Incomplete final evaluation')
        f['validation_rank']=np.arange(1,len(f)+1);f['rank_within_k']=f.groupby('k',sort=False).cumcount()+1
        for configuration,mask in [('original',1),('new',2)]:
            chosen=f['mask'].eq(mask);f[configuration+'_rank']=0;f.loc[chosen,configuration+'_rank']=np.arange(1,chosen.sum()+1)
            f[configuration+'_rank_within_k']=0;f.loc[chosen,configuration+'_rank_within_k']=f[chosen].groupby('k',sort=False).cumcount()+1
        return f

    def combo(self,row):
        names=self.get('predictors')
        return [names[int(row[k])] for k in ['i1','i2','i3'] if pd.notna(row[k])]

    def close(self):
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');self.db.close()
