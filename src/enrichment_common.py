"""Isolated, auditable artifacts for music enrichment v2 and external history v1."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from urllib.parse import urlencode

from feature_expansion_common import sha, write_csv, write_json, atomic_bytes

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / 'data/experiments/music_enrichment_v2'
MUSIC = ROOT / 'analysis/music_enrichment_v2'
DATA = ROOT / 'data/public/music_enrichment_v2'
HISTORY = ROOT / 'analysis/external_historical'
HISTORY_DATA = ROOT / 'data/public/external_historical_v1'
EXTERNAL = ROOT / 'data/external_historical'
UA = 'CMPT491-Research/2.0 (https://github.com/Jamster187/cmpt491-music-censorship)'


def preservation(initialize=False):
    path = LOCAL / 'preservation.json'
    if not path.exists():
        if not initialize:
            raise ValueError('Initialize preservation baseline before modifying artifacts')
        excluded = [LOCAL, MUSIC, DATA, HISTORY, HISTORY_DATA, EXTERNAL]
        files = {}
        for base in [ROOT/'data', ROOT/'analysis']:
            for p in sorted(base.rglob('*')):
                if not p.is_file() or '__pycache__' in p.parts or any(x == p or x in p.parents for x in excluded):
                    continue
                files[str(p.relative_to(ROOT))] = {'size': p.stat().st_size, 'sha256': sha(p)}
        write_json(path, {'commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(), 'files': files})
    record = json.loads(path.read_text())
    if not initialize:
        for name, expected in record['files'].items():
            p = ROOT/name
            if not p.is_file() or p.stat().st_size != expected['size'] or sha(p) != expected['sha256']:
                raise ValueError('Protected artifact changed: '+name)
    return {'files': len(record['files']), 'bytes': sum(v['size'] for v in record['files'].values()), 'baseline_commit': record['commit'], 'status': 'BASELINE' if initialize else 'PASS'}


def fetch(url, path, *, limit=20_000_000, timeout=40):
    """Immutable cached GET with bounded size and explicit provenance; no refresh."""
    path = Path(path)
    meta = path.with_name(path.name+'.provenance.json')
    if path.exists():
        if not meta.exists():
            raise ValueError('Unprovenanced existing download: '+str(path))
        record = json.loads(meta.read_text())
        if record['url'] != url or record['sha256'] != sha(path):
            raise ValueError('Download identity/hash mismatch')
        return record
    start = time.monotonic()
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=timeout) as response:
        raw = response.read(limit+1)
        if len(raw) > limit:
            raise ValueError('Download exceeds explicit byte budget')
        record = {'url': url, 'resolved_url': response.url, 'retrieval_date': dt.datetime.now(dt.timezone.utc).isoformat(),
                  'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'content_type': response.headers.get('Content-Type'),
                  'last_modified': response.headers.get('Last-Modified'), 'seconds': time.monotonic()-start}
    atomic_bytes(path, raw)
    write_json(meta, record)
    return record


def fetch_post(url, payload, path, *, limit=20_000_000, timeout=40):
    """Read-only data API POST; payload and response hashes are both recorded."""
    path=Path(path);meta=path.with_name(path.name+'.provenance.json')
    body=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    bodyhash=hashlib.sha256(body).hexdigest()
    if path.exists():
        record=json.loads(meta.read_text())
        if record['url']!=url or record['request_sha256']!=bodyhash or record['sha256']!=sha(path):raise ValueError('POST cache identity/hash mismatch')
        return record
    request=urllib.request.Request(url,data=body,headers={'User-Agent':UA,'Content-Type':'application/json'},method='POST')
    start=time.monotonic()
    with urllib.request.urlopen(request,timeout=timeout) as response:
        raw=response.read(limit+1)
        if len(raw)>limit:raise ValueError('POST download byte budget exceeded')
    record={'url':url,'method':'POST','request':payload,'request_sha256':bodyhash,'retrieval_date':dt.datetime.now(dt.timezone.utc).isoformat(),
            'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'seconds':time.monotonic()-start}
    atomic_bytes(path,raw);write_json(meta,record);return record


def fetch_form(url, payload, path, *, limit=5_000_000):
    """Read-only download form; never submit an account, purchase, or agreement."""
    path=Path(path);meta=path.with_name(path.name+'.provenance.json')
    body=urlencode(sorted(payload.items())).encode();bodyhash=hashlib.sha256(body).hexdigest()
    if path.exists():
        record=json.loads(meta.read_text())
        if record['url']!=url or record['request_sha256']!=bodyhash or record['sha256']!=sha(path):raise ValueError('Form cache differs')
        return record
    request=urllib.request.Request(url,data=body,headers={'User-Agent':UA,'Content-Type':'application/x-www-form-urlencoded'},method='POST')
    with urllib.request.urlopen(request,timeout=40) as response:
        raw=response.read(limit+1)
        if len(raw)>limit:raise ValueError('Form download byte budget exceeded')
        content_type=response.headers.get('Content-Type')
    record={'url':url,'method':'POST','request':payload,'request_sha256':bodyhash,'retrieval_date':dt.datetime.now(dt.timezone.utc).isoformat(),
        'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'content_type':content_type}
    atomic_bytes(path,raw);write_json(meta,record);return record


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','verify']);args=parser.parse_args()
    print(json.dumps(preservation(args.action=='prepare'), indent=2), flush=True)
