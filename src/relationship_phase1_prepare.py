"""Initialize scientific-artifact preservation without freezing volatile interpreter caches."""
from pathlib import Path
import json
import relationship_discovery as engine
import relationship_phase1 as phase


def prepare_preservation():
    path=phase.LOCAL/'preservation.json'
    if not path.exists():
        files={str(p.relative_to(phase.spec.ROOT)):engine.old.original.sha(p)
            for p in phase.spec.PUBLIC.rglob('*') if p.is_file() and phase.PUBLIC not in p.parents
            and p.name!='full_phase1_findings.md' and '__pycache__' not in p.parts}
        engine.write_json(path,dict(sha256=files))
        return dict(status='PASS',initialized=True,excluded_runtime_caches=[],protected_files=len(files))
    snapshot=engine.read_json(path);before=engine.old.original.sha(path);excluded=[]
    for name,digest in snapshot['sha256'].items():
        file=phase.spec.ROOT/name
        if file.parent.name=='__pycache__' and file.suffix=='.pyc' and '.cpython-' in file.name:
            source=file.parent.parent/(file.name.split('.cpython-',1)[0]+'.py')
            source_name=str(source.relative_to(phase.spec.ROOT))
            if source_name not in snapshot['sha256'] or engine.old.original.sha(source)!=snapshot['sha256'][source_name]:
                raise ValueError('Cannot exclude cache without verifying its original source: '+name)
            excluded.append(dict(path=name,recorded_cache_sha256=digest,
                current_cache_sha256=engine.old.original.sha(file) if file.exists() else None,
                unchanged_source=source_name,source_sha256=snapshot['sha256'][source_name]))
        elif not file.exists() or engine.old.original.sha(file)!=digest:
            raise ValueError('Scientific/source artifact changed; cache exclusion cannot bypass it: '+name)
    if excluded:
        backup=phase.LOCAL/'preservation_with_runtime_caches.json'
        if backup.exists():raise ValueError('Existing cache-exclusion backup needs explicit review')
        backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(path.read_bytes())
        names={r['path'] for r in excluded}
        engine.write_json(path,dict(sha256={n:h for n,h in snapshot['sha256'].items() if n not in names}))
    result=dict(status='PASS',initialized=False,original_snapshot_sha256=before,
        current_snapshot_sha256=engine.old.original.sha(path),excluded_runtime_caches=excluded,
        protected_files=len(snapshot['sha256'])-len(excluded),
        explanation='Only verified CPython bytecode caches are excluded. Their source hashes and every other protected artifact must match; no statistical code, inputs, results or checkpoint identity changes.')
    if excluded:engine.write_json(phase.LOCAL/'preservation_cache_exclusion_audit.json',result)
    return result


def prepare():
    original=engine.preserve(initialize=True)
    snapshot=prepare_preservation()
    return {'protocol_sha256':phase.freeze(),'status':'PASS','model_fits':0,'original_preservation':original,'phase1_preservation':snapshot}


if __name__=='__main__':print(json.dumps(prepare(),indent=2))
