"""Immutable source snapshots and atomic outputs for financial acquisition v1."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/external_historical/financial'
RAW = BASE / 'raw/acquisition_v1'
PROCESSED = BASE / 'processed/acquisition_v1'
MANIFESTS = BASE / 'manifests/acquisition_v1'
REPORT = ROOT / 'analysis/external_historical/financial_acquisition'
SOURCE_MANIFEST = MANIFESTS / 'sources.json'
UA = 'CMPT491-Financial-Acquisition/1.0 (https://github.com/Jamster187/cmpt491-music-censorship)'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def atomic(path, content):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(content);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def write_json(path,obj):atomic(path,(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())


def write_csv(path, data):
    import lzma
    frame=data if isinstance(data,pd.DataFrame) else pd.DataFrame(data)
    content=frame.to_csv(index=False,lineterminator='\n',float_format='%.17g',na_rep='').encode()
    if str(path).endswith('.xz'):content=lzma.compress(content,preset=6)
    atomic(path,content)


def snapshots():return json.loads(SOURCE_MANIFEST.read_text()) if SOURCE_MANIFEST.exists() else {}


def source_path(key):
    row=snapshots()[key]
    if row['status']!='ok':raise ValueError('Source unavailable: '+key)
    path=ROOT/row['raw_path']
    if sha(path)!=row['sha256']:raise ValueError('Raw hash mismatch: '+key)
    return path


def snapshot(key,url,*,reuse=None,extension='.bin',post=None,form=None,max_bytes=30_000_000):
    """One immutable content-addressed snapshot; bounded retries; never refresh v1."""
    catalog=snapshots()
    if key in catalog and catalog[key]['status']=='ok':
        old=catalog[key]
        if old['url']!=url or old.get('request_json')!=post or old.get('request_form')!=form:raise ValueError('Request identity changed: '+key)
        source_path(key)
        return old
    entry={'source_key':key,'url':url,'request_json':post,'request_form':form,'status':'failed','retrieved_at':'',
           'raw_path':'','sha256':'','bytes':0,'resolved_url':'','http_last_modified':'',
           'reused_from':'','attempts':0,'error':''}
    try:
        if reuse:
            oldpath=ROOT/reuse;side=oldpath.with_name(oldpath.name+'.provenance.json')
            meta=json.loads(side.read_text())
            if meta['url']!=url or sha(oldpath)!=meta['sha256']:raise ValueError('Unverified reusable source: '+reuse)
            body=oldpath.read_bytes()
            entry.update(retrieved_at=meta['retrieval_date'],resolved_url=meta.get('resolved_url',url),
                         http_last_modified=meta.get('last_modified',''),reused_from=reuse)
        else:
            for attempt in range(1,4):
                entry['attempts']=attempt
                time.sleep(1.1)
                try:
                    with requests.request('POST' if post is not None or form is not None else 'GET',url,json=post,data=form,
                            headers={'User-Agent':UA},timeout=(15,45),stream=True) as response:
                        if response.status_code in {429,500,502,503,504} and attempt<3:
                            time.sleep(min(8,2**attempt));continue
                        response.raise_for_status();chunks=[];size=0
                        for block in response.iter_content(65536):
                            size+=len(block)
                            if size>max_bytes:raise ValueError('Source exceeds byte budget')
                            chunks.append(block)
                        body=b''.join(chunks)
                        entry.update(retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                                     resolved_url=response.url,http_last_modified=response.headers.get('Last-Modified',''))
                    break
                except (requests.Timeout,requests.ConnectionError):
                    if attempt==3:raise
            else:raise ValueError('Retry budget exhausted')
        if not body or len(body)>max_bytes:raise ValueError('Empty/oversized source')
        digest=hashlib.sha256(body).hexdigest();path=RAW/(digest+extension)
        if path.exists():
            if sha(path)!=digest:raise ValueError('Content-address collision')
        else:atomic(path,body)
        entry.update(status='ok',raw_path=str(path.relative_to(ROOT)),sha256=digest,bytes=len(body))
    except Exception as error:
        entry['error']=type(error).__name__+': '+str(error)
    catalog[key]=entry;write_json(SOURCE_MANIFEST,catalog)
    print(key,entry['status'],entry['bytes'],flush=True)
    return entry


def restore_snapshots():
    """Recover missing pinned bytes only; newer provider revisions cannot replace v1."""
    result=[]
    for key,row in snapshots().items():
        if row['status']!='ok':continue
        path=ROOT/row['raw_path']
        if path.exists():
            source_path(key);result.append(dict(source_key=key,status='already_verified'));continue
        outcome=dict(source_key=key,status='failed',error='')
        try:
            time.sleep(1.1)
            with requests.request('POST' if row.get('request_json') is not None or row.get('request_form') is not None else 'GET',
                    row['url'],json=row.get('request_json'),data=row.get('request_form'),headers={'User-Agent':UA},
                    timeout=(15,45),stream=True) as response:
                response.raise_for_status();pieces=[];size=0
                for block in response.iter_content(65536):
                    size+=len(block)
                    if size>30_000_000:raise ValueError('Source exceeds restoration byte budget')
                    pieces.append(block)
                content=b''.join(pieces)
            if hashlib.sha256(content).hexdigest()!=row['sha256']:raise ValueError('Provider bytes changed; original v1 snapshot unavailable; no overwrite')
            atomic(path,content);outcome['status']='restored_exact_bytes'
        except Exception as e:outcome['error']=type(e).__name__+': '+str(e)
        result.append(outcome)
    write_json(PROCESSED/'restoration_local.json',result)
    print(json.dumps(result,indent=2))
    return result
