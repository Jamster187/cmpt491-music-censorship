"""Reconstruct pinned panel assets locally; no lyrics or arbitrary remote code."""
import os
import json
import subprocess
from classifier_panel import ROOT,OUT,WORK,MODELS,artifacts
from detoxify_setup import fetch

def main():
    import certifi
    os.environ['SSL_CERT_FILE']=certifi.where()
    subprocess.run(['git','check-ignore','--quiet','data/experiments/classifier_panel/model.bin'],cwd=ROOT,check=True)
    pins=json.loads((OUT/'artifacts.json').read_text())
    # Existing evaluated models use their own pinned setup commands. Never overwrite them.
    for m in ('lyriclens','detoxify'):artifacts(m)
    for m in ('emotion','sentiment','bart'):
        spec=pins[m]
        for name,h in spec['sha256'].items():
            fetch(f"https://huggingface.co/{spec['repository']}/resolve/{spec['revision']}/{name}",WORK/m/name,h)
        artifacts(m)
    print('Verified all five models; downloaded only missing pinned artifacts into ignored storage.')

if __name__=='__main__':main()
