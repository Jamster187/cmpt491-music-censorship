"""Offline candidate only: last available weekly chart per calendar month.

Never migrates databases, publishes public CSVs, or performs acquisition/inference.
"""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from billboard import song_id
from public_dataset import (ROOT, SONG_COLUMNS, CLASSIFIER_COLUMNS, metadata_summaries,
                            sha, write_csv, reconcile_csv)
from public_classifier_features import load_features

OUT = ROOT/'data/experiments/month_end_snapshots'
REPORT = ROOT/'reports/month_end_population_comparison'
SNAPSHOT_COLUMNS = ('month','snapshot_chart_date','monthly_rank','song_id',
                    'snapshot_last_week_rank','snapshot_reported_peak_position',
                    'snapshot_reported_weeks_on_chart')
SONG_FIELDS = tuple({'first_selected_month':'first_snapshot_month',
                    'last_selected_month':'last_snapshot_month',
                    'months_selected':'snapshot_months_selected'}.get(k,k) for k in SONG_COLUMNS)
MASTER_COLUMNS = SNAPSHOT_COLUMNS + SONG_FIELDS[1:] + CLASSIFIER_COLUMNS
SOURCE_COLUMNS = SNAPSHOT_COLUMNS + ('source_chart_index','source_row_index')
KNOWN_GAPS = {'1976-12-25':[100],'1977-01-29':[100],'1977-02-26':[100]}


def select_snapshots(charts):
    """Physical charts, not song aggregates; retain every selected source row."""
    selected = {}
    dates = set()
    for index, chart in enumerate(charts):
        dt = chart['date']
        if dt in dates:
            raise ValueError('Multiple physical charts on one date')
        dates.add(dt)
        month = dt[:7]
        if month not in selected or dt > selected[month][1]['date']:
            selected[month] = (index,chart)
    rows=[]; gaps={}
    for month,(index,chart) in sorted(selected.items()):
        ranks=[r['this_week'] for r in chart['data']]
        if len(set(ranks)) != len(ranks) or any(type(r) is not int or not 1<=r<=100 for r in ranks):
            raise ValueError('Duplicate or invalid month/rank')
        missing=sorted(set(range(1,101))-set(ranks))
        if missing:gaps[chart['date']]=missing
        for ri,row in enumerate(chart['data']):
            rows.append((month,chart['date'],row['this_week'],song_id(row['song'],row['artist']),
                         row['last_week'],row['peak_position'],row['weeks_on_chart'],index,ri))
    return sorted(rows,key=lambda r:(r[0],r[2])),gaps


def project_songs(history, monthly, metadata, statuses, lyrics):
    membership=defaultdict(set)
    for r in monthly:membership[r[3]].add(r[0])
    output={}
    for sid,months in sorted(membership.items()):
        if sid not in history:raise ValueError('Snapshot orphan')
        row=history[sid]
        if sid!=song_id(row[1],row[2]):raise ValueError('Identity changed')
        status=lyrics.get(sid,'not_attempted')
        output[sid]=row+(min(months),max(months),len(months),statuses.get(sid,'not_attempted'))+metadata.get(sid,('',)*9)+(status,int(status=='success'))
    return output


def master_rows(monthly,songs,features):
    for row in monthly:
        sid=row[3]
        if sid not in songs:raise ValueError('Snapshot orphan')
        values=features.get(sid,(None,)*len(CLASSIFIER_COLUMNS))
        if bool(songs[sid][-1]) != (sid in features):raise ValueError('Lyrics/classifier availability conflict')
        yield row[:7]+songs[sid][1:]+values


def protected_hashes():
    files=[ROOT/'data/raw/billboard-hot-100.json']
    files += [ROOT/'data/processed'/n for n in ('music.db','research.db','lyrics.db','classifier_results.db')]
    files += sorted((ROOT/'data/public').glob('*'))
    return {str(p.relative_to(ROOT)):sha(p) for p in files if p.is_file()}


def prepare():
    charts=json.loads((ROOT/'data/raw/billboard-hot-100.json').read_text())
    monthly,gaps=select_snapshots(charts)
    if gaps!=KNOWN_GAPS:raise ValueError('Unreviewed source rank gaps')
    if (len(charts),sum(len(c['data']) for c in charts),len(monthly),len({r[0] for r in monthly}))!=(3555,355487,81797,818):
        raise ValueError('Frozen source counts changed')
    with closing(sqlite3.connect('file:'+str(ROOT/'data/processed/music.db')+'?mode=ro',uri=True)) as c:
        weekly=c.execute('''WITH dates AS (SELECT substr(chart_date,1,7) month,max(chart_date) dt
          FROM chart_observations GROUP BY 1)
          SELECT dates.month,o.chart_date,o.rank,o.song_id,o.last_week,o.peak_position,
          o.weeks_on_chart,o.source_chart_index,o.source_row_index
          FROM dates JOIN chart_observations o ON o.chart_date=dates.dt ORDER BY 1,3''').fetchall()
        if weekly!=monthly:raise ValueError('Raw source and weekly foundation disagree')
    with closing(sqlite3.connect('file:'+str(ROOT/'data/processed/research.db')+'?mode=ro',uri=True)) as c:
        history={r[0]:r for r in c.execute('''SELECT song_id,title,artist,first_chart_date,last_chart_date,
          best_chart_rank,chart_observation_count,distinct_chart_dates,total_chart_points FROM songs''')}
        old={r[0] for r in c.execute('SELECT song_id FROM study_population')}
        metadata=metadata_summaries(c)
        statuses=dict(c.execute('SELECT song_id,match_status FROM metadata_matches'))
        lyrics=dict(c.execute('SELECT song_id,lyrics_status FROM lyrics_manifest'))
        features,provenance=load_features(c)
        old_rows=c.execute('SELECT count(*) FROM monthly_top100').fetchone()[0]
    songs=project_songs(history,monthly,metadata,statuses,lyrics)
    new=set(songs);added=new-old;removed=old-new
    # Early reviewed pilot evidence is inventoried, not silently promoted/imported.
    pilot={};pilot_hashes={}
    for sid in sorted(added):
        path=ROOT/'data/experiments/phase2ar/results'/f'{sid}.json'
        if path.exists():
            d=json.loads(path.read_text())
            if d['song']['song_id']!=sid:raise ValueError('Pilot identity mismatch')
            pilot[sid]=d['asset_match_status']
            pilot_hashes[sid]=sha(path)
    with closing(sqlite3.connect('file:'+str(ROOT/'data/processed/lyrics.db')+'?mode=ro',uri=True)) as c:
        evidence={t:len(added&{r[0] for r in c.execute('SELECT song_id FROM '+t)}) for t in ('results','production_results','production_assets')}
    evidence['canonical_files']=sum((ROOT/'data/lyrics'/f'{sid}.txt').exists() for sid in added)
    evidence['production_metadata_result_files']=sum(p.name[:69] in added for p in (ROOT/'data/processed/metadata_results').glob('*.json'))
    summary={
      'version':'month-end-candidate-v1','old_observations':old_rows,'old_songs':len(old),
      'months':len({r[0] for r in monthly}),'observations':len(monthly),'songs':len(new),
      'both':len(old&new),'removed':len(removed),'added':len(added),'columns':list(MASTER_COLUMNS),
      'source_rank_gaps':gaps,'rows_per_month':dict(sorted(Counter(Counter(r[0] for r in monthly).values()).items())),
      'last_available_chart_date':max(r[1] for r in monthly),
      'added_production_metadata':sum(statuses.get(s)=='high_confidence' for s in added),
      'added_metadata_attempted':sum(s in statuses for s in added),
      'added_usable_lyrics':sum(lyrics.get(s)=='success' for s in added),
      'added_all_classifier_features':sum(s in features and all(v is not None for v in features[s]) for s in added),
      'added_pilot_metadata_statuses':dict(sorted(Counter(pilot.values()).items())),
      'added_other_evidence':evidence,'archived_pilot_sha256':pilot_hashes,
      'candidate_metadata_accepted':sum(statuses.get(s)=='high_confidence' for s in new),
      'candidate_usable_lyrics':sum(lyrics.get(s)=='success' for s in new),
      'candidate_all_features':sum(s in features and all(v is not None for v in features[s]) for s in new),
      'candidate_observations_with_features':sum(r[3] in features for r in monthly),
      'classifier_configuration_sha256':provenance.get('configuration_sha256'),
    }
    if (old_rows,len(old),len(new),len(old&new),len(removed),len(added))!=(81800,25363,28041,24387,976,3654):
        raise ValueError('Reviewed population census changed')
    if Counter(pilot.values())!=Counter(high_confidence=15,ambiguous=3,not_found=1) or any(evidence.values()):
        raise ValueError('Added-song evidence changed; refresh the catch-up assessment')
    if any(s in statuses or s in lyrics or s in features for s in added):
        raise ValueError('Production coverage changed; refresh the catch-up assessment')
    changes=[(kind,sid,history[sid][1],history[sid][2],pilot.get(sid,''))
             for kind,ids in [('added',added),('removed',removed)] for sid in sorted(ids)]
    return monthly,songs,features,summary,changes


def report(s):
    return f'''# Month-end population comparison (candidate only)

Generated by `python3 src/month_end_snapshots.py build`. No acquisition or inference.
The published CSVs and research databases remain unchanged.

Weekly means the actual Billboard chart; monthly selects the latest available chart
within each calendar month. Chart dates are not release dates. September 2026 ends
at the source's last available chart, September 19, and is not a complete month.

| Population | Observations | Unique songs |
|---|---:|---:|
| Published aggregated-month | {s['old_observations']:,} | {s['old_songs']:,} |
| Candidate month-end | {s['observations']:,} | {s['songs']:,} |

There are {s['months']} months, {s['both']:,} shared songs, {s['removed']:,} removed and
{s['added']:,} added. Exact identities are in the accompanying population-changes CSV.

## Source gaps, not transformation failures

815 selected charts contain ranks 1–100. Three contain ranks 1–99 only:
1976-12-25, 1977-01-29 and 1977-02-26. The raw JSON and immutable weekly database agree.
Thus **81,800 observations and 100 rows in every month are NOT supported** by this
source under the frozen definition. The candidate preserves all 81,797 existing
rows, with unique month/rank pairs. No padding, rank reassignment, substitution of
an earlier chart, or source repair is performed. All 818 dates are independently
checked against SQL maximum chart dates and physical charts in the raw JSON.

## Existing evidence and catch-up

New songs with production accepted MusicBrainz metadata: {s['added_production_metadata']}.
New songs with usable lyrics: {s['added_usable_lyrics']}.
New songs with all classifier features: {s['added_all_classifier_features']}.
Production metadata and lyrics have not been attempted for any added song.
The original MusicBrainz Phase 2A-R pilot already contains **15 high-confidence,
3 ambiguous and 1 not-found** dispositions for 19 added identities. These are
archived pilot evidence, not imported production records. Their status is retained
in the comparison ledger; candidate metadata stays `not_attempted` until a
provenance-preserving import/replay is approved. Raw cached candidates alone are
not treated as accepted asset metadata.

Catch-up: 3,654 production metadata dispositions and 3,654 lyrics attempts are
needed. Review/reuse the 19 cached pilot cases first (15 already high-confidence);
3,635 added songs have no pilot disposition. There are 3,639 without an existing
high-confidence MusicBrainz match, including the four unresolved pilot cases.
No external requests are necessarily required for the 19 cached cases. Successful
matches or lyrics cannot be guaranteed. All 3,654 added songs currently lack
classifier results; inference is needed only for those subsequently obtaining
approved usable lyrics (zero eligible now, at most 3,654 later).

Candidate coverage reuses {s['candidate_metadata_accepted']:,} accepted production
metadata records and {s['candidate_usable_lyrics']:,} usable lyric assets;
{s['candidate_all_features']:,} songs retain all 42 features.
{s['candidate_observations_with_features']:,} snapshot observations have at least
some classifier features. Existing model-specific missing values are preserved.
Removed songs, lyrics and results remain in the original databases.

## Candidate files and semantics

Ignored local output: `data/experiments/month_end_snapshots/`:
`songs.csv`, `monthly_snapshots.csv`, `master_dataset.csv`, `manifest.json`.
Master: **{s['observations']:,} rows, {len(MASTER_COLUMNS)} columns**.
The monthly table additionally retains original source chart/row coordinates.

Remove old `monthly_points`, `weeks_present`, `best_weekly_rank`,
`average_weekly_rank`, and `weekly_observations`. `monthly_rank` is the selected
weekly rank. Add `snapshot_chart_date`, `snapshot_last_week_rank`,
`snapshot_reported_peak_position`, and `snapshot_reported_weeks_on_chart`.
These last three preserve reported source values, including source inconsistencies.
Rename/recalculate song-level selection fields as `first_snapshot_month`,
`last_snapshot_month`, `snapshot_months_selected`. Whole-history Billboard summaries
remain whole-history measures. No monthly aggregation defines membership.
The 42 classifier columns are unchanged, joined by exact song_id. No lyrics,
provider payloads, local paths, new scores or combined scores are exported.

## Validation and recommendation

Build/validate reconciles every candidate CSV cell to its allowlisted source
projection, writes a second independent serialization and compares checksums,
validates the frozen classifier release, and hashes protected databases, raw
source and all existing public files before/after. Candidate files are staged
before replacement; the public exporter is untouched. No HTTP client is used.

**Do not replace the public dataset yet.** First approve preserving the three
source gaps (81,797 actual observations) and complete the separately authorized
catch-up for added identities to the previous attempted-acquisition standard.
This is not a claim that every song can obtain accepted lyrics or predictions.
No catch-up, genre work, inference or historical/COVID analysis was performed.
'''


def run(action):
    before=protected_hashes()
    monthly,songs,features,summary,changes=prepare()
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUT,prefix='.candidate-') as td:
        temp=Path(td)
        projections={
          'songs.csv':(SONG_FIELDS,list(songs.values())),
          'monthly_snapshots.csv':(SOURCE_COLUMNS,monthly),
          'master_dataset.csv':(MASTER_COLUMNS,None)}
        manifest={}
        for name,(columns,rows) in projections.items():
            def values():return master_rows(monthly,songs,features) if rows is None else iter(rows)
            count=write_csv(temp/name,columns,values())
            reconcile_csv(temp/name,columns,values())
            write_csv(temp/('repeat-'+name),columns,values())
            if sha(temp/name)!=sha(temp/('repeat-'+name)):raise ValueError('Nondeterministic serialization')
            manifest[name]={'rows':count,'columns':len(columns),'bytes':(temp/name).stat().st_size,'sha256':sha(temp/name)}
        summary['files']=manifest
        summary['protected_sha256']=before
        summary['pipeline_sha256']={str(p.relative_to(ROOT)):sha(p) for p in
          (Path(__file__),ROOT/'src/public_dataset.py',ROOT/'src/public_classifier_features.py')}
        encoded=json.dumps(summary,indent=2,sort_keys=True)+'\n'
        (temp/'manifest.json').write_text(encoded)
        if protected_hashes()!=before:raise ValueError('Protected inputs changed')
        if action=='build':
            for name in (*projections,'manifest.json'):os.replace(temp/name,OUT/name)
            REPORT.with_suffix('.json').write_text(encoded)
            REPORT.with_suffix('.md').write_text(report(summary))
            write_csv(REPORT.with_name('month_end_population_changes.csv'),
                      ('change','song_id','title','artist','archived_musicbrainz_pilot_status'),changes)
        else:
            for name in (*projections,'manifest.json'):
                if sha(temp/name)!=sha(OUT/name):raise ValueError('Candidate differs from deterministic rebuild')
            reconcile_csv(REPORT.with_name('month_end_population_changes.csv'),
                          ('change','song_id','title','artist','archived_musicbrainz_pilot_status'),changes)
            if REPORT.with_suffix('.json').read_text()!=encoded or REPORT.with_suffix('.md').read_text()!=report(summary):raise ValueError('Stale comparison report')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('columns','protected_sha256','pipeline_sha256')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('build','validate'))
    run(parser.parse_args().action)
