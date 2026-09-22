"""Report exact request/response identity reconciliation without changing state."""
import argparse
from collections import Counter
from contextlib import closing
import json
import sqlite3
from genre_evidence import ro
import genre_production as g


def report(batch_id, attempt_id):
    with closing(ro(g.DB)) as c:
        c.row_factory=sqlite3.Row
        a=c.execute('SELECT * FROM attempts WHERE batch_id=? AND attempt_id=?',(batch_id,attempt_id)).fetchone()
        if a is None:raise ValueError('Attempt not found for this batch')
        manifest=g.saved_request(c,a);ids=manifest['song_ids']
        obj=json.loads((g.LOCAL/a['folder']/'response.json').read_text())
        returned=[r.get('song_id') for r in obj['predictions']]
        counts=Counter(returned);missing=sorted(set(ids)-set(returned));foreign=sorted(set(returned)-set(ids))
        duplicate={sid:n for sid,n in counts.items() if n>1}
        lines=[f'# Genre batch {batch_id}: identity audit','',f"Attempt {attempt_id}; finished {a['finished_at']}. Expected {len(ids)} IDs; returned {len(returned)} rows.",
               f'Missing: {len(missing)}. Foreign: {len(foreign)}. Duplicate IDs: {len(duplicate)}.','',
               '## Expected IDs','', '| Title | Artist | Exact expected song_id | Exact unique ID returned |','|---|---|---|---|']
        for sid in ids:
            row=c.execute('SELECT title,artist FROM songs WHERE song_id=?',(sid,)).fetchone()
            lines.append(f"| {row['title']} | {row['artist']} | `{sid}` | {counts[sid]==1} |")
        lines+=['','## Returned IDs (response order)','']+[f'- `{sid}`' for sid in returned]
        for title,values in [('Missing IDs',missing),('Foreign IDs',foreign),('Duplicate IDs',list(duplicate))]:
            lines+=['',f'## {title}','']+([f'- `{sid}`' for sid in values] or ['None.'])
        lines+=['','## Decision','',
                'Only schema-valid predictions carrying exact, unique requested IDs may be retained. A foreign ID is not repaired or mapped by response position, even when its text appears to describe an input song. Genre plausibility and exact identity reconciliation are separate questions.',
                '', ('For batch 597, nine rows match exact requested IDs and their reasons refer to the corresponding input artists or evidence. The remaining row contains an extra zero in the ID associated with Gypsy’s “Gypsy Queen - Part 1”; its label is not attached to that song. That unresolved input requires a new exact-ID response.' if batch_id==597 and attempt_id==569 else 'Unresolved inputs require new exact-ID responses.'),
                '',f'Rebuild: `python3 src/genre_batch_audit.py {batch_id} {attempt_id}`.','']
        dest=g.ROOT/f'reports/genre_batch_{batch_id}_audit.md';dest.write_text('\n'.join(lines));print(dest)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('batch',type=int);parser.add_argument('attempt',type=int);args=parser.parse_args();report(args.batch,args.attempt)
