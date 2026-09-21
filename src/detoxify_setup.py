"""Fetch pinned official artifacts into ignored storage; never fetch lyrics."""
import json
import os
from pathlib import Path
import subprocess
import urllib.request
from detoxify_evaluation import ROOT, REPORTS, WORK, sha

def fetch(url,path,expected):
    if path.exists():
        if sha(path)!=expected:raise ValueError('Existing artifact differs: '+path.name)
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.download')
    with urllib.request.urlopen(url,timeout=120) as response, temporary.open('wb') as out:
        while True:
            chunk=response.read(1024*1024)
            if not chunk:break
            out.write(chunk)
    if sha(temporary)!=expected:
        temporary.unlink();raise ValueError('Download checksum mismatch')
    temporary.replace(path)

def main():
    import certifi
    os.environ['SSL_CERT_FILE']=certifi.where()
    probe=WORK/'source/LICENSE'
    subprocess.run(['git','check-ignore','--quiet',str(probe.relative_to(ROOT))],cwd=ROOT,check=True)
    pins=json.loads((REPORTS/'detoxify_artifacts.json').read_text())
    revision=pins['detoxify_commit']
    for name,h in pins['source'].items():
        if name=='revision.txt':
            path=WORK/'source'/name;path.parent.mkdir(parents=True,exist_ok=True)
            if not path.exists():path.write_text(revision+'\n')
            if sha(path)!=h:raise ValueError('Revision mismatch')
        else:fetch(f'https://raw.githubusercontent.com/unitaryai/detoxify/{revision}/{name}',WORK/'source'/name,h)
    for name,h in pins['tokenizer'].items():
        fetch(f"https://huggingface.co/{pins['tokenizer_repository']}/resolve/{pins['tokenizer_revision']}/{name}",WORK/'tokenizer'/name,h)
    fetch(pins['checkpoint_url'],WORK/'toxic_debiased-c7548aa0.ckpt',pins['checkpoint_sha256'])
    (WORK/'artifacts.json').write_text(json.dumps(pins,indent=2)+'\n')
    print('Pinned source, tokenizer, checkpoint verified in ignored local storage.')

if __name__=='__main__':main()
