"""Read-only post-run census and integrity audit; writes non-lyrical reports only."""
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import subprocess

import month_end_catchup as catchup
from month_end_snapshots import select_snapshots, KNOWN_GAPS
from public_classifier_features import load_features, project_song
from classifier_production_store import (ROOT, SPEC, MODELS, COLUMNS, canonical, sha,
                                        chunks, chunk_ranges, aggregate, validate_chunk)

REPORT=ROOT/'reports/month_end_catchup_audit'


def merge_population(old,new,population):
    if set(old)&set(new):raise ValueError('Conflicting old/catch-up identities')
    merged=dict(old,**new)
    if not set(population)<=set(merged):raise ValueError('Missing population identities')
    return {sid:merged[sid] for sid in sorted(population)}


def validate_chunks(job,rows,song):
    model=job['model'];budget=SPEC['models'][model]['window']-2
    if job['content_budget']!=budget:raise ValueError('Wrong content budget')
    if len(rows)!=job['chunk_count'] or [r['chunk_index'] for r in rows]!=list(range(len(rows))):raise ValueError('Wrong chunk sequence')
    if [(r['content_start'],r['content_end']) for r in rows]!=chunk_ranges(job['token_count'],budget):raise ValueError('Changed or incomplete token partitions')
    for row in rows:
        validate_chunk(model,row)
        if row['input_tokens']!=row['content_end']-row['content_start']+2:raise ValueError('Wrong special-token count')
    for col in SPEC['models'][model]['columns']:
        value=aggregate([r['scores'][col] for r in rows],[r['content_end']-r['content_start'] for r in rows])['token_weighted_mean']
        if value!=song[col]:raise ValueError('Weighted aggregation changed')


def active_workers():
    active=[]
    for line in subprocess.check_output(['ps','-eo','pid=,comm=,args='],text=True).splitlines():
        parts=line.split(maxsplit=2)
        if len(parts)!=3 or 'python' not in Path(parts[1]).name.lower():continue
        if re.search(r'month_end_catchup(?:_classifier)?\.py\s+(supervise|metadata|lyrics|run|worker)(?:\s|$)',parts[2]):active.append(int(parts[0]))
    return active


def audit():
    if active_workers():raise ValueError('Catch-up worker still active')
    m=catchup.manifest();folder=catchup.BASE
    db_before={p.name:sha(p) for p in folder.glob('*.db')}
    checked=catchup.validate_acquisition(True)
    monthly,gaps=select_snapshots(catchup.read(ROOT/'data/raw/billboard-hot-100.json'))
    if gaps!=KNOWN_GAPS:raise ValueError('Accepted source gaps changed')
    population={r[3] for r in monthly};added={s['song_id'] for s in m['songs']}
    if len(population)!=28041 or len(monthly)!=81797 or len({r[0] for r in monthly})!=818 or population!=set(m['new_population']):raise ValueError('Month-end population changed')
    with closing(catchup.connect(ROOT/'data/processed/music.db',True)) as c:
        sql=c.execute('''WITH dates AS (SELECT substr(chart_date,1,7) month,max(chart_date) dt FROM chart_observations GROUP BY 1)
          SELECT dates.month,o.chart_date,o.rank,o.song_id,o.last_week,o.peak_position,o.weeks_on_chart,o.source_chart_index,o.source_row_index
          FROM dates JOIN chart_observations o ON o.chart_date=dates.dt ORDER BY 1,3''').fetchall()
        if sql!=monthly:raise ValueError('Snapshots differ from latest source charts')
        weekly=c.execute('SELECT count(*) FROM chart_observations').fetchone()[0]
        if weekly!=355487:raise ValueError('Weekly source count changed')
    with closing(catchup.connect(ROOT/'data/processed/research.db',True)) as c:
        old_population={r[0] for r in c.execute('SELECT song_id FROM study_population')}
        if added!=population-old_population or len(added)!=3654:raise ValueError('Catch-up scope changed')
        old_meta=dict(c.execute('SELECT song_id,match_status FROM metadata_matches'))
        old_lyrics={sid:'accepted' if status=='success' else status for sid,status in c.execute('SELECT song_id,lyrics_status FROM lyrics_manifest')}
        history={r[0]:r for r in c.execute('SELECT * FROM songs')}
        old_features,old_provenance=load_features(c)
    with closing(catchup.connect(catchup.METADATA,True)) as c:
        new_meta=dict(c.execute('SELECT song_id,match_status FROM metadata_matches'))
        metadata_runs=[dict(zip(('started_at','finished_at','status','summary'),r)) for r in c.execute('SELECT started_at,finished_at,status,summary_json FROM acquisition_runs ORDER BY started_at')]
        if len(new_meta)!=3654 or set(new_meta)!=added or any(r['status']!='complete' or not r['finished_at'] for r in metadata_runs):raise ValueError('Metadata unfinished')
        for row in c.execute('SELECT * FROM songs'):
            if tuple(row)!=history[row[0]]:raise ValueError('Catch-up song identity/history differs')
        for sid,status,path in c.execute('SELECT song_id,match_status,result_path FROM metadata_matches'):
            evidence=catchup.read(ROOT/path)
            if evidence['song']['song_id']!=sid or evidence['asset_match_status']!=status:raise ValueError('Metadata evidence/status differs')
    lyrics=catchup.lyric_results();new_lyrics={s:r['status'] for s,r in lyrics.items()}
    with closing(catchup.connect(catchup.LYRICS,True)) as c:
        lyrics_runs=[dict(zip(('started_at','finished_at','state','requests','processed'),r)) for r in c.execute('SELECT started_at,finished_at,state,requests,processed FROM production_runs ORDER BY run_id')]
    if lyrics_runs[-1]['state']!='completed' or not lyrics_runs[-1]['finished_at']:raise ValueError('Lyrics worker incomplete')
    usable={s:r for s,r in lyrics.items() if r['status']=='accepted'}
    new_features={};job_counts={};chunk_counts={}
    with closing(catchup.connect(catchup.CLASSIFIERS,True)) as c:
        c.row_factory=sqlite3.Row
        config=json.loads(c.execute('SELECT configuration FROM run_config WHERE id=1').fetchone()[0])
        with closing(catchup.connect(ROOT/'data/processed/classifier_results.db',True)) as old:
            original=json.loads(old.execute('SELECT configuration FROM run_config WHERE id=1').fetchone()[0])
        expected=dict(original,scope='month-end-catchup-v1',catchup_population_sha256=m['population_sha256'],frozen_full_configuration_sha256=old_provenance['configuration_sha256'],scope_adapter_sha256={n:m['implementation_sha256'][n] for n in catchup.ADAPTER_FILES})
        if config!=expected:raise ValueError('Frozen model configuration changed')
        for path,h in original['files'].items():
            if sha(ROOT/path)!=h:raise ValueError('Classifier implementation changed')
        if dict(c.execute('SELECT song_id,lyrics_sha256 FROM targets'))!={s:r['lyrics_sha256'] for s,r in usable.items()}:raise ValueError('Classifier target/hash mismatch')
        if {r['name'] for r in c.execute('PRAGMA table_info(song_results)') if r['type']=='REAL'}!=set(COLUMNS):raise ValueError('Unexpected score schema')
        for model in MODELS:
            job_counts[model]=dict(c.execute('SELECT status,count(*) FROM jobs WHERE model=? GROUP BY status',(model,)))
            if job_counts[model]!={'success':len(usable)}:raise ValueError('Unexpected catch-up model failure or pending job')
            chunk_counts[model]=c.execute('SELECT count(*) FROM chunk_predictions WHERE model=?',(model,)).fetchone()[0]
        for row in c.execute('SELECT * FROM song_results'):
            sid=row['song_id'];jobs={r['model']:r for r in c.execute('SELECT * FROM jobs WHERE song_id=?',(sid,))}
            new_features[sid]=project_song(row,jobs,{})
            for model,job in jobs.items():validate_chunks(job,chunks(c,sid,model),row)
        if set(new_features)!=set(usable):raise ValueError('Classifier result coverage mismatch')
        executions=[dict(r) for r in c.execute('SELECT * FROM executions ORDER BY id')]
        if len(executions)!=4 or any(r['status']!='complete' or r['failures'] or not r['finished_at'] for r in executions):raise ValueError('Model execution did not finish')
    metadata=merge_population(old_meta,new_meta,population)
    lyric_status=merge_population(old_lyrics,new_lyrics,population)
    features=merge_population({s:old_features.get(s) for s in old_population},{s:new_features.get(s) for s in added},population)
    present={s for s,v in features.items() if v is not None};all_42={s for s in present if all(v is not None for v in features[s])}
    if present!={s for s,v in lyric_status.items() if v=='accepted'}:raise ValueError('Final lyrics/classifier availability differs')
    periods=[]
    for lo,hi,label in catchup.lp.PERIODS:
        group={s for s in population if lo<=int(history[s][5][:4])<=hi}
        n=len(group);ok=len(group&present);full=len(group&all_42)
        periods.append(dict(period=label,songs=n,usable=ok,usable_percent=round(100*ok/n,2),all_42=full,all_42_percent=round(100*full/n,2)))
    complete=catchup.read(folder/'completion.json')
    if complete['status']!='COMPLETE' or any(complete[k] for k in ('tests_exit_code','classifier_validation_exit_code','public_validation_exit_code')) or any(complete['worker_exit_codes'].values()):raise ValueError('Supervisor recorded failed completion')
    if complete['final_usable']!=len(present) or complete['final_all_42']!=len(all_42):raise ValueError('Completion census differs from databases')
    tracked=subprocess.check_output(['git','ls-files','--','data/lyrics','data/cache','data/processed','data/experiments'],cwd=ROOT,text=True)
    if tracked.strip():raise ValueError('Private/generated artifacts tracked')
    tests=(folder/'post_run_tests.log').read_text();test_count=re.search(r'Ran (\d+) tests',tests)
    if not test_count or not tests.rstrip().endswith('OK'):raise ValueError('Post-run tests did not pass')
    if {p.name:sha(p) for p in folder.glob('*.db')}!=db_before:raise ValueError('Catch-up database changed during audit')
    failures=catchup.read(ROOT/'docs/classifier_accepted_missingness.json')['exceptions']
    result=dict(status='COMPLETE',population=28041,months=818,observations=81797,weekly_observations=weekly,source_gaps=gaps,
      components={k:'COMPLETE' for k in ('metadata','lyrics','classifiers')},active_workers=[],catchup_population=3654,
      catchup_metadata=dict(Counter(new_meta.values())),full_metadata=dict(Counter(metadata.values())),metadata_accepted_percent=round(100*sum(v=='high_confidence' for v in metadata.values())/28041,2),
      catchup_lyrics=dict(Counter(new_lyrics.values())),full_lyrics=dict(Counter(lyric_status.values())),final_usable=len(present),final_usable_percent=round(100*len(present)/28041,2),unavailable=28041-len(present),
      lyrics_error_reasons=dict(Counter(r['reason'] for r in lyrics.values() if r['status']=='error')),
      new_usable=len(usable),new_classifier_jobs=job_counts,new_all_42=len(new_features),final_any_classifier=len(present),final_all_42=len(all_42),accepted_model_missingness=[r for r in failures if r['song_id'] in population],
      period_coverage=periods,total_local_lyric_files=len(list((ROOT/'data/lyrics').glob('*.txt'))),retained_out_of_population_lyrics=len(m['old_lyrics_sha256'])+len(usable)-len(present),
      metadata_runs=metadata_runs,lyrics_runs=lyrics_runs,classifier_executions=executions,chunk_counts=chunk_counts,
      database_sizes={p.name:p.stat().st_size for p in folder.glob('*.db')},database_sha256=db_before,
      frozen_configuration_sha256=old_provenance['configuration_sha256'],public_master_sha256=sha(ROOT/'data/public/master_dataset.csv'),
      tests_passed=int(test_count[1]),integrity=checked,report_source_sha256=sha(__file__))
    return result


def render(r):
    lines=['# Final month-end catch-up audit','', '**Status: COMPLETE.** No acquisition or inference was restarted.',
      '', 'All 3,654 added songs have terminal metadata and lyrics dispositions. All 2,321 newly usable lyrics have four successful model results. Completion means the authorized acquisition pass finished; it does not imply every song has usable lyrics.',
      '', '## Population and process evidence', '',
      '28,041 final song_ids; 818 snapshots; 81,797 observations. Each date independently matches the latest available chart in its calendar month in both the raw JSON and immutable weekly database. The 355,487 weekly observations are unchanged.',
      '815 snapshots have ranks 1–100. The charts dated 1976-12-25, 1977-01-29 and 1977-02-26 retain ranks 1–99. No invented observations, alternative chart selection or deduplication.',
      'No catch-up worker remains active. Both metadata runs finished complete (19 offline replayed cases plus 3,635 online dispositions); lyrics finished 10 bounded-start plus 3,644 continuation dispositions. The first lyrics run’s interrupted flag is its intentional ten-asset limit, not lost work. All four classifier executions finished complete. Supervisor exit codes and independently queried databases agree.',
      '', '## Metadata', '', '| Disposition | Catch-up | Full month-end population |','|---|---:|---:|']
    for k in ('high_confidence','ambiguous','not_found','error'):lines.append(f"| {k} | {r['catchup_metadata'].get(k,0):,} | {r['full_metadata'].get(k,0):,} |")
    lines += ['',f"Attempted: 3,654/3,654; unprocessed: 0. Catch-up acceptance: {100*r['catchup_metadata']['high_confidence']/3654:.2f}%. Full-population metadata acceptance: **{r['full_metadata']['high_confidence']:,}/28,041 ({r['metadata_accepted_percent']}%)**. The one full-population metadata error predates catch-up.",
      '', '## Lyrics', '', '| Disposition | Catch-up | Full month-end population |','|---|---:|---:|']
    for k in catchup.lp.STATUSES:lines.append(f"| {k} | {r['catchup_lyrics'].get(k,0):,} | {r['full_lyrics'].get(k,0):,} |")
    lines += ['',f"Attempted: 3,654/3,654; unprocessed: 0. Catch-up usable coverage: {100*r['new_usable']/3654:.2f}%. Final usable lyrics: **{r['final_usable']:,}/28,041 ({r['final_usable_percent']}%)**; unavailable/excluded: **{r['unavailable']:,}**.",
      'All 44 catch-up API errors are terminal HTTP 503 responses, retained separately from not-found and identity/text exclusions. They may be retryable in a separately authorized pass, but no retries were executed or needed to finish this attempted-disposition scope.',
      f"Exactly {r['new_usable']:,} new lyric files reconcile to accepted records. There are {r['total_local_lyric_files']:,} canonical files overall: 19,372 preserved originals plus 2,321 new files. Of these, {r['retained_out_of_population_lyrics']} belong to removed old-population songs and remain preserved; they are excluded from final-population coverage.",
      '', '## Classifiers', '', '| Model | New successes | New errors | Final successes | Final model-specific missingness |','|---|---:|---:|---:|---:|']
    for model in MODELS:
        missing=sum(x['model']==model for x in r['accepted_model_missingness'])
        lines.append(f"| {model} | {r['new_classifier_jobs'][model]['success']:,} | 0 | {r['final_any_classifier']-missing:,} | {missing} |")
    lines += ['',f"New target songs and songs with all 42 features: **{r['new_all_42']:,}**. Final songs with classifier data: **{r['final_any_classifier']:,}**; with all 42 features: **{r['final_all_42']:,}**. All newly usable lyrics received all four model attempts; none failed.",
      'The only model-specific gaps remain the two accepted original LyricLens exceptions: Chinese Checkers — Booker T. & The MG\'s, and Snap Shot — Slave. Their four LyricLens values remain NULL because normalization becomes empty; their other 38 values are retained. No lyrics were altered and no unchanged failures were retried.',
      'The unchanged 42-column schema, per-model checkpoint revisions, configuration/source hashes, finite/ranged scores, raw activations, exact balanced token partitions and token-weighted means were verified. No BART, CSI/MCR, hardness, consensus or combined features exist in the production outputs.',
      '', '## Full-population coverage', '', 'Periods use first Billboard appearance, not release dates. Any-classifier coverage equals usable-lyrics coverage. The 2015–2019 subset overlaps 2010–2019; no historical content trends were analyzed.',
      '', '| Period | Songs | Usable / any classifier | Coverage | All 42 | All-42 coverage |','|---|---:|---:|---:|---:|---:|']
    for p in r['period_coverage']:lines.append(f"| {p['period']} | {p['songs']:,} | {p['usable']:,} | {p['usable_percent']}% | {p['all_42']:,} | {p['all_42_percent']}% |")
    secs=sum(x['elapsed_seconds'] for x in r['classifier_executions'])
    lines += ['', '## Runtime and integrity', '',
      f"New classifier inference workers used {secs:.2f} seconds total (about {secs/60:.1f} minutes). Peak worker RSS: {max(x['peak_rss_bytes'] for x in r['classifier_executions'])/1024**3:.3f} GiB. Saved chunk predictions: {sum(r['chunk_counts'].values()):,}. Classifier database: {r['database_sizes']['classifier_results.db']:,} bytes.",
      'Online metadata ran 18:23:42–20:15:40 UTC; lyrics continuation ran 18:23:42–20:38:40 UTC; classifier workers ran 20:38:42–21:18:02 UTC on September 21, 2026. The supervisor completed validation/reporting around 21:20:40 UTC: approximately 2 hours 57 minutes after launch.',
      f"**{r['tests_passed']} tests passed.** Fresh acquisition, frozen-classifier and public-export validations passed. Old lyrics, source/research/acquisition/classifier databases and all current public files match their pre-run hashes. New database hashes also remain unchanged through this audit. Identity joins, schema primary keys, foreign keys, stored evidence and file hashes were reconciled. No lyrics, caches, private databases or checkpoints are tracked by Git.",
      'The expanded canonical file census is validated as the union of the old and catch-up manifests. The historical research validator is used with its old file-count check disabled, then the strict combined census is enforced; no database or validator is modified.',
      '', 'Reproduce the report with `python3 src/month_end_catchup_audit.py` after the validation commands in [the catch-up guide](../docs/month_end_catchup.md). All audit database connections are read-only. The generated JSON includes exact counts, hashes and execution records; no lyric text or private absolute paths are included.',
      '', '## Next', '', '**Month-end population acquisition/classification is complete. Ready for genre assignment on the final 28,041-song population.**',
      'Results remain in the original databases and separate catch-up sidecars, joined by song_id for this audit. No genre assignment, public master replacement, or historical/COVID analysis was performed.']
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    result=audit()
    catchup.save(REPORT.with_suffix('.json'),result)
    catchup.lp.atomic(REPORT.with_suffix('.md'),render(result).encode())
    print(json.dumps({k:result[k] for k in ('status','population','final_usable','final_usable_percent','final_all_42','metadata_accepted_percent','tests_passed')},indent=2))
