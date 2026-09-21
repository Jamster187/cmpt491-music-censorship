"""Fetch only the pinned artifacts needed for the isolated LyricLens pilot.

Run with the dedicated environment after installing docs/lyriclens_requirements.lock.
Source is CC BY 4.0 by Kai Yu Lu, Malhar Sham Ghogare, Zihan Su, Shanu Sushmita.
Artifacts remain under ignored data/experiments/lyriclens; no training-state pickle
or optimizer files are fetched or loaded. Downloads must match reviewed hashes.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
from lyriclens_evaluation import ROOT,WORK,REVISION,sha


def main():
    import certifi
    import gdown
    import nltk
    os.environ['SSL_CERT_FILE']=certifi.where()
    pins=json.loads((ROOT/'reports/lyriclens_artifacts.json').read_text())
    if pins['revision']!=REVISION:raise ValueError('Wrong source revision')
    for group in ('source','model'):
        (WORK/group).mkdir(parents=True,exist_ok=True)
        for name,checksum in pins[group].items():
            if Path(name).name!=name:raise ValueError('Artifact name must not contain a directory')
            dest=WORK/group/name
            if dest.exists():
                if sha(dest)!=checksum:raise ValueError('Existing artifact differs; preserve it for investigation')
                continue
            stage=Path(str(dest)+'.tmp')
            if group=='source':
                url=f'https://raw.githubusercontent.com/su1zihan/LyricLens/{REVISION}/{name}'
                with urllib.request.urlopen(url,timeout=60) as response,stage.open('wb') as f:
                    shutil.copyfileobj(response,f)
            else:
                item=next(x for x in pins['drive_files'] if x['name']==name)
                gdown.download(id=item['id'],output=str(stage),quiet=False)
                if stage.stat().st_size!=item['bytes']:raise ValueError('Artifact size changed')
            if sha(stage)!=checksum:raise ValueError('Artifact hash changed; do not publish/download blindly')
            stage.replace(dest)
    for name in ('punkt','stopwords','wordnet','averaged_perceptron_tagger','omw-1.4'):
        nltk.download(name,download_dir=str(WORK/'nltk_data'),quiet=True,raise_on_error=True)
    for name,checksum in pins['nltk'].items():
        if sha(WORK/'nltk_data'/name)!=checksum:raise ValueError('NLTK resource version changed')
    (WORK/'setup_provenance.json').write_text(json.dumps(pins,indent=2)+'\n')
    (WORK/'requirements-resolved.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze']).decode())
    print('Pinned local artifacts verified; no inference performed.')


if __name__=='__main__':main()
