"""Read-only validation of pilot scope, decisions, population and protected inputs."""
import csv
import json
from collections import Counter
from genre_evidence import ROOT,OUT,DATABASE,ro,sha
from genre_pilot import load_sample,collect,REPORTS
from genre_rules import assign,TAXONOMY
from month_end_snapshots import select_snapshots,KNOWN_GAPS


def validate():
    sample=load_sample();rows=list(csv.DictReader((REPORTS/'pilot.csv').open()))
    if len(rows)!=300 or {r['song_id'] for r in rows}!={r['song_id'] for r in sample}:raise ValueError('Pilot scope changed')
    c=ro(DATABASE);c.row_factory=__import__('sqlite3').Row
    for r in rows:
        expected=assign(collect(c,r['song_id']))
        for key,value in expected.items():
            actual=r[key]
            if isinstance(value,(bool,list)):actual=json.loads(actual)
            elif value is None:actual=actual or None
            if actual!=value:raise ValueError(f'Decision mismatch: {key}')
        if r['primary_genre'] and r['primary_genre'] not in TAXONOMY:raise ValueError('Unexpected category')
    if c.execute('SELECT count(*) FROM songs').fetchone()[0]!=28041:raise ValueError('Wrong evidence population')
    c.close()
    snapshots,gaps=select_snapshots(json.loads((ROOT/'data/raw/billboard-hot-100.json').read_text()))
    if gaps!=KNOWN_GAPS or len(snapshots)!=81797 or len({r[0] for r in snapshots})!=818 or len({r[3] for r in snapshots})!=28041:raise ValueError('Population changed')
    protected=json.loads((OUT/'protected.json').read_text())
    bad=[p for p,h in protected.items() if sha(ROOT/p)!=h]
    if bad:raise ValueError('Protected data changed: '+repr(bad))
    result=dict(pilot=300,population=28041,months=818,observations=81797,protected_files=len(protected),protected_lyrics=sum(p.startswith('data/lyrics/') for p in protected),protected_unchanged=True,dispositions=dict(Counter(r['disposition'] for r in rows)))
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':validate()
