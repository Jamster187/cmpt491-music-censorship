"""Non-lyrical population, enrichment, and source-access coverage reports."""
import csv
import json
from collections import Counter

from lyrics_plan import PERIODS
from musicbrainz import write_json
from research import ROOT, connect


def group_summary(rows):
    total=len(rows)
    metadata=Counter(r['metadata_status'] or 'pending' for r in rows)
    lyrics=Counter(r['lyrics_status'] for r in rows)
    attempted=sum(n for status,n in lyrics.items() if status not in ('not_attempted','blocked_source_access'))
    m_attempted=total-metadata['pending']
    return {'population':total,'metadata':dict(metadata),'metadata_attempted':m_attempted,
            'metadata_high_confidence_percent_of_population':round(100*metadata['high_confidence']/total,2) if total else 0,
            'metadata_high_confidence_percent_of_attempted':round(100*metadata['high_confidence']/m_attempted,2) if m_attempted else 0,
            'lyrics':dict(lyrics),'lyrics_attempted':attempted,
            'lyrics_success_percent_of_population':round(100*lyrics['success']/total,2) if total else 0}


def collect(conn):
    names=('song_id','year','metadata_status','lyrics_status')
    rows=[dict(zip(names,r)) for r in conn.execute("SELECT p.song_id,CAST(substr(s.first_chart_date,1,4) AS INTEGER),m.match_status,l.lyrics_status FROM study_population p JOIN songs s USING(song_id) LEFT JOIN metadata_matches m USING(song_id) JOIN lyrics_manifest l USING(song_id)")]
    summary=group_summary(rows)
    summary['database_path']='data/processed/research.db'
    summary['counts']={table:conn.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in
                       ('songs','chart_observations','monthly_top100','study_population','metadata_matches','external_entities','song_external_links','lyrics_manifest','lyrics_pilot')}
    summary['by_period']=[dict(period=label,**group_summary([r for r in rows if start<=r['year']<=end])) for start,end,label,_ in PERIODS]
    summary['by_year']=[dict(year=year,**group_summary([r for r in rows if r['year']==year])) for year in sorted({r['year'] for r in rows})]
    summary['focus_periods']=[dict(period=label,**group_summary([r for r in rows if start<=r['year']<=end])) for start,end,label in [(2015,2019,'2015–2019'),(2020,2026,'2020–2026')]]
    summary['metadata_reasons']=dict(conn.execute('SELECT reason,count(*) FROM metadata_matches GROUP BY reason'))
    flags=Counter()
    for row in conn.execute('SELECT evidence_json FROM metadata_matches'):
        flags.update(json.loads(row[0]).get('review_flags') or [])
    summary['metadata_review_flags']=dict(flags)
    summary['metadata_field_coverage']={}
    fields=[('recording','id'),('artist','id'),('release-group','id'),
            ('recording','tags'),('recording','genres'),('recording','length'),('recording','isrcs'),
            ('release','date'),('release','title'),('release-group','genres'),('artist','genres')]
    for scope,field in fields:
        sql="""SELECT count(DISTINCT l.song_id) FROM song_external_links l
          JOIN external_entities e USING(provider,entity_type,entity_id)
          JOIN metadata_matches m USING(song_id)
          WHERE m.match_status='high_confidence' AND e.entity_type=? AND EXISTS
          (SELECT 1 FROM json_each(e.metadata_json) v WHERE
           CASE json_type(v.value,?) WHEN 'array' THEN json_array_length(json_extract(v.value,?))>0
           WHEN 'text' THEN length(json_extract(v.value,?))>0
           WHEN 'integer' THEN json_extract(v.value,?)>0 ELSE 0 END)"""
        summary['metadata_field_coverage'][scope+'.'+field]=conn.execute(sql,(scope,*(['$.'+field]*4))).fetchone()[0]
    summary['lyrics_pilot_attempted']=conn.execute("SELECT count(*) FROM lyrics_pilot p JOIN lyrics_manifest l USING(song_id) WHERE l.lyrics_status NOT IN ('not_attempted','blocked_source_access')").fetchone()[0]
    summary['source_selected']=[r[0] for r in conn.execute('SELECT DISTINCT lyrics_source FROM lyrics_manifest WHERE lyrics_source IS NOT NULL ORDER BY lyrics_source')]
    summary['lyrics_stage']='dispositioned' if summary['lyrics_attempted']==summary['population'] else 'partial_or_unattempted'
    summary['runs']=[dict(zip(('run_id','provider','started_at','finished_at','status','parameters','summary'),r)) for r in conn.execute('SELECT * FROM acquisition_runs ORDER BY started_at,run_id')]
    for run in summary['runs']:
        run['parameters']=json.loads(run['parameters']);run['summary']=json.loads(run['summary'])
    return summary


def render(s):
    m=s['metadata'];l=s['lyrics'];c=s['counts']
    lines=['# Research database construction status','',
      'Generated with `python3 src/research_report.py`. Counts describe persisted decisions at report generation; rerun after resuming acquisition. Historical periods use first Billboard appearance, not release year or first monthly entry.','',
      f"Database: `data/processed/research.db`. **{c['songs']:,} assets, {c['chart_observations']:,} weekly observations, {c['monthly_top100']:,} monthly observations, {c['study_population']:,} study members.**",
      'The canonical Phase 1 database and raw JSON are unchanged. All weekly and monthly rows were reconciled field-for-field. Study membership does not depend on metadata/lyrics availability. See [schema and build instructions](../../docs/research_database.md).','',
      '## Metadata','',
      f"Attempted: **{s['metadata_attempted']:,}**. High confidence: **{m.get('high_confidence',0):,}**; ambiguous: **{m.get('ambiguous',0):,}**; not found: **{m.get('not_found',0):,}**; errors: **{m.get('error',0):,}**; pending: **{m.get('pending',0):,}**.",
      f"Accepted coverage is **{s['metadata_high_confidence_percent_of_population']}% of the study population**, or **{s['metadata_high_confidence_percent_of_attempted']}% of attempted assets**. Attempted and population denominators coincide only when every study asset has a disposition.",
      'The approved Phase 2A-R matcher is unchanged. The initial cache import reproduced all 160 pilot assets that belong to the study population: 137 accepted, 12 ambiguous, 11 not found, zero new requests. Other pilot songs were not imported. Live acquisition uses bounded original search queries; extra detailed lookups and difficult-tail rescue are deferred.','',
      '| First-chart period | Population | Attempted | Accepted | Ambiguous | Not found | Error | Accepted / population |',
      '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in s['by_period']:
        q=p['metadata']
        lines.append(f"| {p['period']} | {p['population']:,} | {p['metadata_attempted']} | {q.get('high_confidence',0)} | {q.get('ambiguous',0)} | {q.get('not_found',0)} | {q.get('error',0)} | {p['metadata_high_confidence_percent_of_population']}% |")
    lines+=['','Reasons: `'+json.dumps(s['metadata_reasons'],sort_keys=True)+'`.',
            'Review flags: `'+json.dumps(s['metadata_review_flags'],sort_keys=True)+'`.','',
            'Returned metadata among accepted assets (presence, not validation of one canonical value):','',
            '| Entity and field | Assets | Percent of accepted |','|---|---:|---:|']
    for field,count in sorted(s['metadata_field_coverage'].items()):
        denominator=m.get('high_confidence',0)
        lines.append(f"| {field} | {count:,} | {100*count/denominator if denominator else 0:.2f}% |")
    lines+=['',
            'All returned raw tag/genre values remain scoped to recordings, release groups, or artists. Missing new detailed genre lookups are unmeasured. Multiple recordings and conflicting dates/durations are retained; the database does not select a canonical recording or assign artist genres to songs. No final genre taxonomy is constructed.','',
            'Matching limitations remain visible in the decision files: missing candidates, incompatible full artist credits, conflicting artist identities, unsupported versions, and inadequate temporal anchors can leave an asset unresolved. Accepted later/undated manifestations inherit asset support from a compatible dated candidate; their own dates and durations should not be treated as the original release. Raw tags can include non-genre labels, and their presence is not a validated genre assignment. Production decisions have not received exhaustive manual review.','',
            '## Lyrics','',
            f"Manifest sources: **{', '.join(s['source_selected']) or 'none recorded'}**. Status: **{s['lyrics_stage']}**. Production details and local storage are described in [lyrics instructions](../../docs/lyrics_production.md).",
            f"Pilot: **{c['lyrics_pilot']} study-member identities, {s['lyrics_pilot_attempted']} attempted**. Total attempted: **{s['lyrics_attempted']}**; successful: **{l.get('success',0)}**. Overall acquired coverage: **{s['lyrics_success_percent_of_population']}%**.",
            'Manifest dispositions: `'+json.dumps(l,sort_keys=True)+'`. Unattempted/blocked rows are not provider misses; wrong identity, bad/missing text, quarantine and API errors remain distinct. Only successful paths supply the corpus. No lyric text is copied into this report.','',
            '| First-chart period | Population | Lyrics attempted | Retrieved | Acquired coverage |',
            '|---|---:|---:|---:|---:|']
    for p in s['by_period']:
        lines.append(f"| {p['period']} | {p['population']:,} | {p['lyrics_attempted']} | {p['lyrics'].get('success',0)} | {p['lyrics_success_percent_of_population']}% |")
    lines+=['','### Important recent periods','']
    for p in s['focus_periods']:
        lines.append(f"- {p['period']}: {p['population']:,} study assets; metadata accepted {p['metadata'].get('high_confidence',0)}/{p['metadata_attempted']} attempted; lyrics {p['lyrics'].get('success',0)}/{p['population']:,} ({p['lyrics_success_percent_of_population']}%).")
    lines+=['','### Every first-chart year','',
            '| Year | Study assets | Metadata attempted | Metadata accepted | Lyrics attempted | Lyrics retrieved | Lyrics coverage |',
            '|---|---:|---:|---:|---:|---:|---:|']
    for p in s['by_year']:
        lines.append(f"| {p['year']} | {p['population']} | {p['metadata_attempted']} | {p['metadata'].get('high_confidence',0)} | {p['lyrics_attempted']} | {p['lyrics'].get('success',0)} | {p['lyrics_success_percent_of_population']}% |")
    lines+=['','## Remaining work','',
            f"Metadata pending: **{m.get('pending',0):,}**; recorded errors: **{m.get('error',0)}**. Metadata is optional enrichment, not a classifier prerequisite.",
            f"Lyrics without a disposition in this manifest: **{s['population']-s['lyrics_attempted']:,}**. Do not restart a complete pass merely to improve acceptance. Unresolved outcomes remain explicit; no manual rescue or classifier is run by these commands.",
            '```bash','python3 src/research.py validate','python3 src/lyrics_production.py validate',
            'python3 -m unittest discover -s tests -v','```','',
            'Lyrics, caches and generated databases remain local and Git-ignored. See [completion record](../../docs/lyrics_completion.md) for acquisition, synchronization, validation and remaining limitations.','']
    return '\n'.join(lines)


def main():
    with connect(readonly=True) as conn:
        conn.execute('BEGIN')
        summary=collect(conn)
        conn.rollback()
    write_json(ROOT/'data/processed/research_status.json',summary)
    target=ROOT/'archive/intermediate_reports/research_dataset_status.md'
    tmp=target.with_suffix('.md.tmp');tmp.write_text(render(summary),encoding='utf-8');tmp.replace(target)
    fields=('year','population','metadata_attempted','metadata_accepted','lyrics_attempted','lyrics_success','lyrics_coverage_percent')
    with (ROOT/'data/processed/research_coverage_by_year.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(fields)
        for p in summary['by_year']:
            writer.writerow((p['year'],p['population'],p['metadata_attempted'],p['metadata'].get('high_confidence',0),p['lyrics_attempted'],p['lyrics'].get('success',0),p['lyrics_success_percent_of_population']))
    print(json.dumps({k:v for k,v in summary.items() if k not in ('by_year','by_period','runs')},indent=2))


if __name__=='__main__':
    main()
