"""Verify the published baseline and initialize only the ignored local cache guard."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import historical_decomposition as hd


def prepare():
    record=json.loads((hd.PUBLIC/'preservation_manifest.json').read_text())
    for name,expected in record['sha256'].items():
        if hd.descriptive.sha(ROOT/name)!=expected:
            raise ValueError('Protected baseline differs: '+name)
    for name,revision in record.get('approved_verification_revisions',{}).items():
        if hd.descriptive.sha(ROOT/name)!=revision['current_sha256']:
            raise ValueError('Authorized verification revision differs: '+name)
    expected=json.loads((hd.PUBLIC/'protocol.json').read_text())['identity']
    actual=json.loads(json.dumps(hd.source_identity()))
    if actual!=expected:
        different=[key for key in expected if actual.get(key)!=expected[key]]
        raise ValueError('Frozen reproduction fingerprint differs: '+', '.join(different))
    hd.LOCAL.mkdir(parents=True,exist_ok=True)
    destination=hd.LOCAL/'preservation.json'
    if destination.exists() and json.loads(destination.read_text())!=record:
        raise ValueError('Existing local preservation guard differs')
    if not destination.exists():hd.write_json(destination,record)
    return dict(status='PASS',protected_files=len(record['sha256']),bootstrap_fits=0)


if __name__=='__main__':print(json.dumps(prepare(),indent=2))
