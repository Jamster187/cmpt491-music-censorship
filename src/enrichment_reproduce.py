"""Replay the existing offline pipeline and compare every numerical release artifact."""
from __future__ import annotations
import json
import subprocess
import sys
import time
from enrichment_common import ROOT,LOCAL,MUSIC,DATA,HISTORY,HISTORY_DATA,EXTERNAL,sha,write_json


def artifact_paths():
    paths=[]
    for directory in [MUSIC,DATA,HISTORY,HISTORY_DATA]:
        paths.extend(p for p in directory.iterdir() if p.is_file() and (p.name.endswith('.csv') or p.name.endswith('.csv.xz')))
        paths.extend((directory/'figures').glob('*.svg'))
    paths.extend(EXTERNAL.glob('*/observations.csv.xz'))
    paths.extend((EXTERNAL/'derived').glob('*.csv.xz'))
    return sorted(set(paths))


def replay():
    start=time.monotonic();before={str(p.relative_to(ROOT)):sha(p) for p in artifact_paths()}
    commands=[['music_enrichment_views.py','chart'],['music_enrichment_views.py','build'],
              ['external_historical_sources.py','normalize'],['external_historical_features.py'],
              ['external_historical_joins.py','build'],['enrichment_reports.py']]
    directory=LOCAL/'reproduction';directory.mkdir(exist_ok=True)
    write_json(directory/'before.json',before)
    for i,command in enumerate(commands):
        print('Offline replay:', ' '.join(command),flush=True)
        with (directory/f'{i:02d}.log').open('w') as log:
            subprocess.run([sys.executable,str(ROOT/'src'/command[0])]+command[1:],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    after={str(p.relative_to(ROOT)):sha(p) for p in artifact_paths()}
    changed=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
    report={'status':'FAIL' if changed else 'PASS','artifacts_compared':len(before),'changed_artifacts':changed,
            'seconds':time.monotonic()-start,'replay_code_sha256':sha(__file__),
            'scope':'Offline original-snapshot parsers, chart/song/month views, native-frequency joins, CSV inventories and SVG coverage figures; no network or model training'}
    write_json(MUSIC/'deterministic_replay.json',report);print(json.dumps(report,indent=2))
    if changed:raise ValueError('Offline replay changed artifacts')

if __name__=='__main__':replay()
