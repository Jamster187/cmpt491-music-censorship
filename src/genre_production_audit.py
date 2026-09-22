"""Read-only aggregate checkpoint and deterministic post-run review selection."""
import csv
from contextlib import closing
import json
import re
import sqlite3

from genre_evidence import ro
import genre_production as g

REPORT=g.ROOT/'reports/genre_production_checkpoint.md'


def review_sample(rows):
    """Bounded, deterministic coverage of labels, confidence and periods."""
    ordered=sorted(rows,key=lambda r:g.digest(('genre-post-run-review-v1'+r['song_id']).encode()))
    chosen={}
    # At most 32 + 45 + 35 selections before filling to 160.
    for field,values,n in [('primary_genre',g.TAXONOMY,2),
                           ('confidence',('high','medium','low'),15),
                           ('period',sorted({r['period'] for r in rows}),5)]:
        for value in values:
            for row in [r for r in ordered if r[field]==value][:n]:chosen[row['song_id']]=row
    for row in ordered:
        if len(chosen)>=160:break
        chosen[row['song_id']]=row
    return sorted(chosen.values(),key=lambda r:r['song_id'])


def main():
    with closing(ro(g.DB)) as c:
        c.row_factory=sqlite3.Row
        c.execute('BEGIN')
        g.verify(c)
        s=g.stats(c)
        n=s['status_counts'].get('completed',0)
        complete=n==28041
        attempts=[dict(r) for r in c.execute('SELECT status,seconds,started_at,finished_at FROM attempts ORDER BY attempt_id')]
        launch=json.loads((g.LOCAL/'launch.json').read_text()) if (g.LOCAL/'launch.json').exists() else {}
        lines=['# Genre production checkpoint','',f"As of {s['as_of']}. **{'Inference complete; qualitative review pending' if complete else 'INCOMPLETE: production checkpoint, not final results'}.**",'',
               f"Target: 28,041. Completed: {n:,} (includes 300 reused approved pilot labels). Errors: {s['status_counts'].get('error',0)}. Remaining: {28041-n:,}.",
               '', 'Execution: ChatGPT-authenticated Codex CLI 0.155.1, GPT-5.5, medium reasoning. No separately billed API fallback.',
               f"Frozen pilot: `{g.PILOT_COMMIT}`. Runner launch commit: `{launch.get('commit','not launched')}`.",
               '',f"New request attempts: {len(attempts):,}; recorded request time: {s['request_seconds']/3600:.3f} hours. This excludes pilot inference and time between requests.",
               f"Recorded failed attempts: {sum(a['status']=='error' for a in attempts)}. Failures remain in the audit trail even when an identical-request retry fills the missing result.",
               f"Results database: {g.DB.stat().st_size:,} bytes, excluding active WAL. Final predictions export: {'available locally' if complete else 'pending completion'}.",
               '', '## Confidence','', '| Confidence | Count | % completed |','|---|---:|---:|']
        for k in ('high','medium','low'):
            count=s['confidence'].get(k,0);lines.append(f'| {k} | {count} | {100*count/n if n else 0:.2f}% |')
        lines+=['','## Genres','', 'Percentages use completed predictions only; these are not final population estimates. Confidence columns are counts.','',
                '| Genre | Count | % completed | High | Medium | Low |','|---|---:|---:|---:|---:|---:|']
        for genre,d in s['genres'].items():
            cf=d['confidence'];lines.append(f"| {genre} | {d['count']} | {100*d['count']/n if n else 0:.2f}% | {cf.get('high',0)} | {cf.get('medium',0)} | {cf.get('low',0)} |")
        lines+=['','## Period counts','', 'Data-quality counts only; no historical interpretation.','', '| Period | Genre | Completed |','|---|---|---:|']
        for r in s['period_genres']:lines.append(f"| {r['period']} | {r['primary_genre']} | {r['n']} |")
        testlog=g.LOCAL/'tests.log'
        testtext=testlog.read_text() if testlog.exists() else ''
        tests=re.search(r'Ran (\d+) tests',testtext)
        protected=g.LOCAL/'protected_validation.json'
        integrity=json.loads(protected.read_text()) if protected.exists() else {}
        validation=f"Latest stored test log: {tests.group(1) if tests else 'unknown'} tests; final OK marker: {testtext.rstrip().endswith('OK')}. Protected-file check: {integrity.get('protected_files','unknown')} files; unchanged: {integrity.get('protected_unchanged','unknown')}. These are launch/checkpoint checks, not the final post-run audit."
        lines+=['','## Validation and remaining work','',validation,'',
                'Population IDs, input/request hashes, frozen configuration and completed structured outputs pass the production validator. Public datasets are not rebuilt by this runner.',
                '', 'Post-run protected-file validation, complete test suite and qualitative audit remain required. No post-run plausible/questionable/wrong counts are claimed before that review.',
                '', 'Rebuild this checkpoint with `python3 src/genre_production_audit.py`. Run/resume instructions are in [production.md](../docs/genre/production.md).','']
        REPORT.write_text('\n'.join(lines))
        if complete:
            rows=[dict(r) for r in c.execute("SELECT song_id,title,artist,period,primary_genre,secondary_genres,confidence,reason FROM songs WHERE status='completed'")]
            selected=review_sample(rows)
            dest=g.LOCAL/'post_run_review_template.csv'
            if not dest.exists():
                with dest.open('w',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=list(selected[0])+['judgment','review_note']);writer.writeheader();writer.writerows(selected)
        print(json.dumps({'completed':n,'errors':s['status_counts'].get('error',0),'report':str(REPORT),'review_pending':True}))

if __name__=='__main__':main()
