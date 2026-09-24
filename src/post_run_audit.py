"""Read-only, local post-acquisition audit; emits aggregates, never lyric text."""
import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
import statistics
import subprocess

import lyrics_production as lyrics
import populations
import research
import research_report

ROOT = Path(__file__).resolve().parents[1]
PERIODS = [(1958,1969,'1958–1969'),(1970,1979,'1970s'),(1980,1989,'1980s'),
           (1990,1999,'1990s'),(2000,2009,'2000s'),(2010,2019,'2010–2019'),
           (2020,2026,'2020–2026'),(2015,2019,'2015–2019')]


def pct(n, d):
    return f'{100*n/d:.2f}%' if d else '—'


def table(lines, header, rows):
    lines.extend(['', '| ' + ' | '.join(header) + ' |', '|' + '|'.join(['---']*len(header))+'|'])
    lines.extend('| '+' | '.join(map(str,row))+' |' for row in rows)


def validate_snapshot(identities, assets):
    """Require the frozen sidecar to retain the entire exact study identity set."""
    if set(identities) != set(assets):
        raise ValueError('Population set differs')
    for sid, identity in identities.items():
        a = assets[sid]
        if identity != (a['song_id'], a['title'], a['artist'], a['first_chart_date']):
            raise ValueError('Frozen lyrics identity differs from research population')


def main(output="archive/intermediate_reports/post_run_audit.md", decisions="../docs/post_run_audit.md"):
    c = research.connect(readonly=True)
    before = {p: research.sha(ROOT/p) for p in ('data/processed/research.db','data/processed/lyrics.db')}
    foundation = research.validate(c, check_files=False)
    evidence = 0
    for path, checksum in c.execute('SELECT result_path,result_sha256 FROM metadata_matches'):
        target = (ROOT/path).resolve()
        if ROOT/'data/processed' not in target.parents or research.sha(target) != checksum:
            raise ValueError('Metadata evidence integrity failure')
        evidence += 1
    p = sqlite3.connect((ROOT/'data/processed/populations/populations.db').as_uri()+'?mode=ro',uri=True)
    populations.attach_weekly(p)
    populations.validate(p)
    p.close()
    l = lyrics.connect(readonly=True)
    if l.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or l.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Lyrics database integrity failure')
    local_files = lyrics.validate(l)
    assets = {sid:json.loads(payload) for sid,payload in l.execute('SELECT * FROM production_assets')}
    results = {sid:json.loads(payload) for sid,payload in l.execute('SELECT * FROM production_results')}
    identities = {r[0]: tuple(r) for r in c.execute('SELECT s.song_id,s.title,s.artist,s.first_chart_date FROM songs s JOIN study_population p USING(song_id)')}
    validate_snapshot(identities, assets)
    rows = []
    for r in c.execute('''SELECT s.song_id,s.title,s.artist,s.first_chart_date,s.best_chart_rank,
      s.chart_observation_count,s.total_chart_points,p.months_selected,m.match_status
      FROM study_population p JOIN songs s USING(song_id) LEFT JOIN metadata_matches m USING(song_id)'''):
        sid,title,artist,date,rank,weeks,points,months,meta = r
        rows.append(dict(sid=sid,year=int(date[:4]),rank=rank,weeks=weeks,points=points,months=months,
                         complex=bool(re.search(r'\b(featuring|feat\.?|with|and)\b|[&/,]',artist,re.I)),
                         meta=meta or 'unprocessed',status=results.get(sid,{}).get('status','unprocessed')))
    files = list((ROOT/'data/lyrics').rglob('*.txt'))
    if len(files)!=local_files or any(p.stem not in assets for p in files): raise ValueError('Invalid file identities/layout')
    accepted = {r['sid'] for r in rows if r['status']=='accepted'}
    # Preserve pilot successes and prohibit conflicting canonical paths/hashes.
    for sid,payload in l.execute('SELECT * FROM results'):
        old=json.loads(payload)
        if old['status']=='success' and (sid not in accepted or old['lyrics_sha256']!=results[sid]['lyrics_sha256']):
            raise ValueError('Original pilot success changed')
    successful = [results[sid] for sid in accepted]
    if len({r['lyrics_path'] for r in successful}) != len(successful): raise ValueError('Duplicate successful paths')
    # All cache envelopes: verify body and URL hashes without emitting their content.
    cache_counts={}
    http_counts={}
    for provider,directory in [('MusicBrainz','musicbrainz_production/requests'),('LRCLIB','lrclib')]:
        checked=0;statuses=Counter()
        for path in sorted((ROOT/'data/cache'/directory).glob('*.json')):
            obj=json.loads(path.read_text())
            if 'url' not in obj: continue
            key=hashlib.sha256(obj['url'].encode()).hexdigest()
            if path.stem.split('-attempt-')[0] != key: raise ValueError('Cache URL hash mismatch')
            if provider=='MusicBrainz':
                if obj['cache_key'] != key: raise ValueError('MusicBrainz cache key mismatch')
                for attempt in obj['attempts']:
                    if attempt.get('body') is not None and hashlib.sha256(attempt['body'].encode()).hexdigest()!=attempt['body_sha256']:
                        raise ValueError('MusicBrainz cache body mismatch')
                statuses[str(obj['attempts'][-1]['status'])]+=1
            else:
                if hashlib.sha256(obj['body'].encode()).hexdigest()!=obj['sha256']: raise ValueError('LRCLIB cache body mismatch')
                statuses[str(obj['status'])]+=1
            checked+=1
        cache_counts[provider]=checked;http_counts[provider]=dict(statuses)
    fingerprint_matches = l.execute("SELECT value FROM production_settings WHERE key IN ('current_pipeline_sha256','pipeline_sha256') ORDER BY key LIMIT 1").fetchone()[0] == lyrics.fingerprint()
    summary=research_report.collect(c)
    counts=Counter(r['status'] for r in rows)
    meta=Counter(r['meta'] for r in rows)
    attempted=len(results)
    lines=['# Post-run acquisition audit', '', f'Generated by `python3 src/post_run_audit.py` from read-only local databases, evidence files, and caches. No requests or acquisition writes. See [audit decisions](../../reports/{decisions}) for validation and next steps.',
           '', 'Periods and years use first Billboard chart appearance, not release year. 2015–2019 overlaps the 2010–2019 row. Unprocessed assets are separate from attempted failures.',
           '', '## Foundation', '', f'Validated counts: `{json.dumps(foundation,sort_keys=True)}`.',
           f"Weekly charts: {c.execute('SELECT count(DISTINCT chart_date) FROM chart_observations').fetchone()[0]}; monthly baskets: {c.execute('SELECT count(DISTINCT month) FROM monthly_top100').fetchone()[0]}.",
           '', '## Metadata', '', f'Processed {len(rows)-meta["unprocessed"]:,}/{len(rows):,}; accepted {meta["high_confidence"]:,}; ambiguous {meta["ambiguous"]:,}; not found {meta["not_found"]:,}; errors {meta["error"]}; unprocessed {meta["unprocessed"]}. Accepted/processed {pct(meta["high_confidence"],len(rows)-meta["unprocessed"])}; accepted/population {pct(meta["high_confidence"],len(rows))}.']
    table(lines,['Period','Target','Processed','Accepted','Ambiguous','Not found','Error','Unprocessed','Accepted/processed','Accepted/target'],
          [[label,len(g),len(g)-m['unprocessed'],m['high_confidence'],m['ambiguous'],m['not_found'],m['error'],m['unprocessed'],pct(m['high_confidence'],len(g)-m['unprocessed']),pct(m['high_confidence'],len(g))]
           for lo,hi,label in PERIODS for g in [[r for r in rows if lo<=r['year']<=hi]] for m in [Counter(r['meta'] for r in g)]])
    table(lines,['Accepted asset field','Assets','Coverage among accepted'],[[k,v,pct(v,meta['high_confidence'])] for k,v in summary['metadata_field_coverage'].items()])
    lines += ['', 'Date means at least one linked release date (possibly partial or a reissue); duration means at least one positive linked recording length. Release title is release information, not proof of an original album. Multiple manifestations remain linked evidence. Artist tags are not song genres. Metadata is optional enrichment for future content work.', '', '## Lyrics', '', f'Target {len(rows):,}; attempted {attempted:,} (includes all 200 reviewed pilot outcomes); candidate found {sum(r["candidate_found"] for r in results.values()):,}; usable {len(accepted):,}; local files {local_files:,}. Overall coverage {pct(len(accepted),len(rows))}; acceptance among attempted {pct(len(accepted),attempted)}.']
    table(lines,['Disposition','Assets'],[(status,counts[status]) for status in (*lyrics.STATUSES,'unprocessed')])
    def coverage(lo,hi,label):
        g=[r for r in rows if lo<=r['year']<=hi];n=len(g);a=sum(r['status']!='unprocessed' for r in g);ok=sum(r['status']=='accepted' for r in g)
        return [label,n,a,ok,n-a,pct(ok,n),pct(ok,a)]
    table(lines,['Period','Target','Attempted','Usable','Unprocessed','Usable/target','Usable/attempted'],[coverage(lo,hi,label) for lo,hi,label in PERIODS])
    table(lines,['Year','Target','Attempted','Usable','Unprocessed','Usable/target','Usable/attempted'],[coverage(y,y,y) for y in range(1958,2027)])
    lines += ['', '## Descriptive missingness', '', ('Every study asset now has a disposition, so target and attempted coverage denominators coincide. Coverage does not prove representativeness.' if counts['unprocessed']==0 else 'Current usable/target includes the unfinished acquisition queue. Usable/attempted isolates observed selection losses; neither proves representativeness.')+' No COVID test or content scoring is performed. Rank cutoffs below are descriptive bins only.']
    table(lines,['Outcome','Assets','Mean weekly peak rank','Mean weekly rows','Mean total weekly points','Mean selected months','Median selected months'],
          [[label,len(g),*[round(statistics.mean(r[k] for r in g),2) for k in ('rank','weeks','points','months')],statistics.median(r['months'] for r in g)]
           for label in ('accepted','attempted unsuccessful','unprocessed')
           for g in [[r for r in rows if (r['status']=='accepted' if label=='accepted' else r['status']=='unprocessed' if label=='unprocessed' else r['status'] not in ('accepted','unprocessed'))]] if g])
    bins=[('Weekly peak 1–10',lambda r:r['rank']<=10),('Weekly peak 11–40',lambda r:10<r['rank']<=40),('Weekly peak 41–100',lambda r:r['rank']>40),
          ('Selected 1 month',lambda r:r['months']==1),('Selected 2–3 months',lambda r:2<=r['months']<=3),('Selected 4–6 months',lambda r:4<=r['months']<=6),('Selected 7+ months',lambda r:r['months']>=7),
          ('Credit separator present',lambda r:r['complex']),('No credit separator',lambda r:not r['complex'])]
    table(lines,['Group','Target','Attempted','Usable','Usable/target','Usable/attempted'],
          [[label,len(g),a,ok,pct(ok,len(g)),pct(ok,a)] for label,pred in bins for g in [[r for r in rows if pred(r)]] for a in [sum(r['status']!='unprocessed' for r in g)] for ok in [sum(r['status']=='accepted' for r in g)]])
    lines += ['', 'Credit complexity is only a separator/word heuristic; band names can contain these tokens. It is not an entity count or inferred collaboration taxonomy.']
    monthly=[(sid,rank,points,int(month[:4])) for sid,rank,points,month in c.execute('SELECT song_id,monthly_rank,monthly_points,month FROM monthly_top100')]
    table(lines,['Monthly rank (observation weighted)','Rows','Attempted rows','Usable rows','Usable/all rows','Usable/attempted rows'],
          [[f'{lo}–{hi}',len(g),a,ok,pct(ok,len(g)),pct(ok,a)] for lo,hi in [(1,10),(11,25),(26,50),(51,100)] for g in [[r for r in monthly if lo<=r[1]<=hi]] for a in [sum(r[0] in results for r in g)] for ok in [sum(r[0] in accepted for r in g)]])
    table(lines,['Calendar basket period','Monthly rows','Usable rows','Usable row coverage','Usable monthly point share'],
          [[label,len(g),sum(r[0] in accepted for r in g),pct(sum(r[0] in accepted for r in g),len(g)),pct(sum(r[2] for r in g if r[0] in accepted),sum(r[2] for r in g))]
           for lo,hi,label in [(1958,2026,'All'),(2015,2019,'2015–2019'),(2020,2026,'2020–2026')] for g in [[r for r in monthly if lo<=r[3]<=hi]]])
    lines += ['', 'Calendar basket periods above include older songs appearing in those months; they differ from first-chart cohorts. These are availability diagnostics, not historical content indices.', '', '## Integrity and provenance', '',
              f'- Immutable input hashes match the research build; source SHA-256: `{research.sha(ROOT/"data/raw/billboard-hot-100.json")}`.',
              '- Research/source rows reconciled in both directions. Independent monthly ranking reconstruction passed. Both SQLite integrity checks and foreign-key checks passed.',
              f'- All {evidence:,} metadata evidence checksums passed; all {local_files:,} lyric file hashes and exact identities passed; zero orphan files, conflicting pilot successes, or duplicate canonical paths.',
              f'- Cache envelopes checked: `{json.dumps(cache_counts,sort_keys=True)}`. Final-envelope HTTP states (LRCLIB includes attempt copies): `{json.dumps(http_counts,sort_keys=True)}`.',
              '- Identical text across different Billboard identities is not automatically an error; successful-record uniqueness is checked per exact asset and canonical path.',
              f'- Unified manifest statuses: `{dict(c.execute("SELECT lyrics_status,count(*) FROM lyrics_manifest GROUP BY lyrics_status"))}`. Production sidecar retains detailed decision evidence; synchronized manifest rows reference it.',
              f'- Production code fingerprint matches frozen run: {fingerprint_matches}.', '', '## Persisted runs']
    table(lines,['Provider','Started UTC','Finished UTC','State','New decisions','Requests'],
          [['MusicBrainz',r['started_at'],r['finished_at'],r['status'],r['summary'].get('processed_this_run','—'),r['summary'].get('network_requests','—')] for r in summary['runs']] +
          [['LRCLIB',start,finish,state,processed,requests] for _,start,finish,state,requests,processed in l.execute('SELECT * FROM production_runs ORDER BY started_at')])
    tracked=subprocess.check_output(['git','ls-files','data/lyrics','data/cache','data/processed','.env'],cwd=ROOT,text=True).strip()
    if tracked: raise ValueError('Private generated paths tracked')
    lines += ['', '- No generated databases, lyrics, or lyric-containing caches are tracked in Git.']
    c.close();l.close()
    if any(research.sha(ROOT/p)!=h for p,h in before.items()): raise ValueError('Databases changed during read-only audit')
    lines += ['- Both working database file hashes unchanged across this audit.', '']
    target=ROOT/output
    temp=target.with_suffix('.md.tmp');temp.write_text('\n'.join(lines));temp.replace(target)
    print(json.dumps({'metadata':dict(meta),'lyrics':dict(counts),'files':local_files,'report':str(target)},sort_keys=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='archive/intermediate_reports/post_run_audit.md')
    parser.add_argument('--decisions',default='../docs/post_run_audit.md')
    args=parser.parse_args()
    main(args.output,args.decisions)
