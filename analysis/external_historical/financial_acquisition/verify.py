"""Read-only publication, baseline preservation and public navigation verifier."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
REPORT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from artifact_integrity import sha


def verify(private=False):
    manifest=json.loads((REPORT/'publication_manifest.json').read_text())
    for name,digest in manifest['files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Publication file changed: '+name)
    baseline=json.loads((REPORT/'protected_baseline.json').read_text());checked=0;optional=[]
    for name,row in baseline['files'].items():
        if name=='data/processed/music.db' and not private and not (ROOT/name).exists():optional.append(name);continue
        if sha(ROOT/name)!=row['sha256']:raise ValueError('Existing data/analysis changed: '+name)
        checked+=1
    links=0
    for name in manifest['files']:
        if not name.endswith('.md'):continue
        path=ROOT/name
        for target in re.findall(r'\]\(([^)\s]+)\)',path.read_text()):
            if re.match(r'[a-z]+://|#|mailto:',target):continue
            if not (path.parent/target.split('#')[0]).exists():raise ValueError('Broken publication link: '+name+' -> '+target)
            links+=1
    base=ROOT/'data/external_historical/financial'
    source=json.loads((base/'manifests/acquisition_v1/sources.json').read_text())
    if len(source)!=32 or any(r['status']!='ok' for r in source.values()):raise ValueError('Source inventory changed')
    normalization=json.loads((base/'manifests/acquisition_v1/normalization.json').read_text())
    if normalization['source_manifest_sha256']!=sha(base/'manifests/acquisition_v1/sources.json'):raise ValueError('Normalization source manifest changed')
    if normalization['parser_sha256']!=sha(ROOT/'src/financial_acquisition_sources.py'):raise ValueError('Normalization parser changed')
    if normalization['research_metadata_sha256']!=sha(ROOT/'analysis/external_historical/financial_research/indicator_inventory.csv'):raise ValueError('Frozen research metadata changed')
    if normalization['failures'] or json.loads((REPORT/'normalization_failures.json').read_text()):raise ValueError('Unresolved normalization failures')
    tracked=subprocess.check_output(['git','ls-files','--','data/external_historical/financial'],cwd=ROOT,text=True).splitlines()
    forbidden=[p for p in tracked if '/raw/' in p or '_local.' in p or '/figures_local/' in p]
    if forbidden:raise ValueError('Restricted artifacts tracked: '+str(forbidden))
    for rel in ['raw/acquisition_v1/test.bin','processed/acquisition_v1/native_local.csv.xz','processed/acquisition_v1/figures_local/test.svg']:
        if subprocess.run(['git','check-ignore','--quiet',str(base/rel)],cwd=ROOT).returncode:raise ValueError('Local artifact not ignored: '+rel)
    if private:
        for r in source.values():
            if sha(ROOT/r['raw_path'])!=r['sha256']:raise ValueError('Source hash mismatch: '+r['source_key'])
    result=dict(status='PASS',publication_files=len(manifest['files']),protected_files=checked,optional_local_files_absent=optional,
                publication_links=links,pinned_sources=len(source),private=private)
    print(json.dumps(result,sort_keys=True,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private',action='store_true');a=p.parse_args();verify(a.private)
