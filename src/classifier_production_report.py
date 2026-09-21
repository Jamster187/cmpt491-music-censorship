"""Deterministic numerical-only readiness report from two bounded production pilots."""
import argparse
import csv
import json
import math
import sqlite3
import statistics
from pathlib import Path
from classifier_production_store import ROOT,SPEC,MODELS,COLUMNS,sha,canonical,digest
from classifier_production import validate,DEFAULT_PILOT
from lyriclens_diagnostics import summary,spearman
from detoxify_diagnostics import pearson

OUT=ROOT/'reports/classifier_production'
OLD={'lyriclens':'lyriclens','detoxify':'detoxify','goemotions':'emotion','cardiff':'sentiment'}
PAIRS=[('ll_sexual_content','detox_sexual_explicit'),('ll_explicit_language','detox_obscene'),('ll_violence','detox_threat'),('ll_violence','emotion_anger'),('ll_violence','emotion_disgust'),('detox_toxicity','emotion_anger'),('detox_toxicity','emotion_disgust'),('detox_insult','emotion_anger'),('detox_insult','emotion_disgust'),('sentiment_negative','emotion_sadness')]


def read(path):
    with path.open() as f:return list(csv.DictReader(f))
def write(path,rows):
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    temp.replace(path)
def open_db(path):
    c=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;return c


def build(db,replay):
    c=open_db(db);r=open_db(replay)
    checks=validate(c,'pilot');validate(r,'pilot')
    noop=json.loads((db.parent/'noop_validation.json').read_text())
    if not noop['all_persisted_tables_unchanged'] or noop['new_jobs'] or noop['new_executions']:raise ValueError('No-op resume failed')
    for table,h in noop['table_digests'].items():
        if table not in ('targets','jobs','chunk_predictions','song_results','executions','run_config'):raise ValueError('Unexpected proof table')
        if digest(canonical([tuple(x) for x in c.execute('SELECT * FROM '+table+' ORDER BY 1,2')]))!=h:raise ValueError('No-op proof does not match current database')
    conf=json.loads(c.execute('SELECT configuration FROM run_config').fetchone()[0])
    if conf!=json.loads(r.execute('SELECT configuration FROM run_config').fetchone()[0]):raise ValueError('Replay configuration differs')
    songs=[dict(x) for x in c.execute('SELECT * FROM song_results ORDER BY song_id')]
    again=[dict(x) for x in r.execute('SELECT * FROM song_results ORDER BY song_id')]
    if songs!=again:raise ValueError('Fresh-run song results are not exactly reproducible')
    interruption=None
    proof_path=replay.parent/'interrupt_before.json'
    if proof_path.exists():
        proof=json.loads(proof_path.read_text())
        for table,key,fields in [('jobs','completed_jobs',('song_id','model')),('chunk_predictions','persisted_chunks',('song_id','model','chunk_index'))]:
            after={'/'.join(str(row[f]) for f in fields):digest(canonical(dict(row))) for row in r.execute('SELECT * FROM '+table)}
            if any(after.get(k)!=h for k,h in proof[key].items()):raise ValueError('Interrupt/resume changed completed work')
        interruption=dict(completed_jobs_preserved=len(proof['completed_jobs']),persisted_chunks_preserved=len(proof['persisted_chunks']),all_preserved_exactly=True,pre_resume_statuses=proof['interrupted_statuses'],proof_sha256=sha(proof_path))
    chunkcols='song_id,model,chunk_index,content_start,content_end,input_tokens,input_sha256,logits,activated,scores'
    raw=[dict(x) for x in c.execute('SELECT '+chunkcols+' FROM chunk_predictions ORDER BY song_id,model,chunk_index')]
    raw_again=[dict(x) for x in r.execute('SELECT '+chunkcols+' FROM chunk_predictions ORDER BY song_id,model,chunk_index')]
    if raw!=raw_again:raise ValueError('Fresh-run raw chunk results differ')
    sample={x['song_id']:x for x in read(ROOT/'reports/lyriclens_sample.csv')}
    old_max=0
    for model,oldname in OLD.items():
        with (ROOT/'reports/classifier_panel'/(oldname+'_chunks.jsonl')).open() as f:old={(x['song_id'],x['chunk_index']):x for x in map(json.loads,f)}
        subset=[x for x in raw if x['model']==model]
        if len(subset)!=len(old):raise ValueError('Prior chunk count differs')
        for x in subset:
            prev=old[x['song_id'],x['chunk_index']]
            if (x['content_start'],x['content_end'],x['input_tokens'],x['input_sha256'])!=(prev['content_start'],prev['content_end'],prev['input_tokens'],prev['input_ids_sha256']):raise ValueError('Prior token coverage differs')
            diff=max(abs(a-b) for a,b in zip(json.loads(x['logits']),prev['logits']));old_max=max(old_max,diff)
    if old_max>1e-6:raise ValueError('Prior whole-song inference differs beyond tolerance')
    OUT.mkdir(parents=True,exist_ok=True)
    write(OUT/'pilot_song_results.csv',songs)
    rawpath=OUT/'pilot_chunks.jsonl';temp=rawpath.with_suffix('.tmp')
    temp.write_text(''.join(canonical(dict(x,logits=json.loads(x['logits']),activated=json.loads(x['activated']),scores=json.loads(x['scores'])))+'\n' for x in raw));temp.replace(rawpath)
    distributions=[dict(column=col,**summary([s[col] for s in songs])) for col in COLUMNS];write(OUT/'distributions.csv',distributions)
    correlations=[]
    for subset in ('all_200','stratified_core_180'):
        selected=[s for s in songs if subset=='all_200' or sample[s['song_id']]['sample_component']=='stratified_core']
        for x,y in PAIRS:
            correlations.append(dict(subset=subset,x=x,y=y,n=len(selected),pearson=pearson([s[x] for s in selected],[s[y] for s in selected]),spearman=spearman([s[x] for s in selected],[s[y] for s in selected])))
    write(OUT/'correlations.csv',correlations)
    prefix=[]
    for model,file in [('lyriclens','lyriclens_predictions.csv'),('detoxify','detoxify_predictions.csv')]:
        old={x['song_id']:x for x in read(ROOT/'reports'/file)}
        for label,col in zip(SPEC['models'][model]['labels'],SPEC['models'][model]['columns']):
            oldcol=label+'_score' if model=='lyriclens' else label
            changes=[(abs(s[col]-float(old[s['song_id']][oldcol])),s) for s in songs]
            largest,song=max(changes,key=lambda x:x[0]);sid=song['song_id']
            prefix.append(dict(column=col,mean_absolute_change=statistics.mean(x[0] for x in changes),maximum_absolute_change=largest,changed_above_01=sum(x[0]>.01 for x in changes),changed_above_10=sum(x[0]>.1 for x in changes),largest_song_id=sid,largest_title=sample[sid]['title'],largest_artist=sample[sid]['artist'],prefix_score=float(old[sid][oldcol]),whole_song_score=song[col]))
    write(OUT/'prefix_comparison.csv',prefix)
    performance=[]
    for model in MODELS:
        executions=[dict(x) for x in c.execute('SELECT * FROM executions WHERE model=?',(model,))]
        if len(executions)!=1 or executions[0]['status']!='complete' or executions[0]['new_successes']!=200:raise ValueError('Benchmark must be a fresh complete pilot')
        e=executions[0];work=e['elapsed_seconds']-e['load_seconds']
        performance.append(dict(model=model,songs=200,chunks=sum(s[model+'_chunk_count'] for s in songs),multi_chunk_songs=sum(s[model+'_chunk_count']>1 for s in songs),max_chunks=max(s[model+'_chunk_count'] for s in songs),load_seconds=e['load_seconds'],processing_seconds=work,total_seconds=e['elapsed_seconds'],seconds_per_song=work/200,estimated_full_hours=(work*19372/200+e['load_seconds'])/3600,peak_rss_bytes=e['peak_rss_bytes']))
    write(OUT/'performance.csv',performance)
    totals=dict(total_seconds=sum(x['total_seconds'] for x in performance),estimated_full_hours=sum(x['estimated_full_hours'] for x in performance),peak_worker_rss_bytes=max(x['peak_rss_bytes'] for x in performance),pilot_database_bytes=db.stat().st_size,estimated_full_database_bytes=round(db.stat().st_size*19372/200),pilot_song_csv_bytes=(OUT/'pilot_song_results.csv').stat().st_size,pilot_chunks_jsonl_bytes=rawpath.stat().st_size)
    for kind in ('song_csv','chunks_jsonl'):totals['estimated_full_'+kind+'_bytes']=round(totals['pilot_'+kind+'_bytes']*19372/200)
    info=dict(configuration=conf,validation=checks,noop_resume=noop,real_interrupt_resume=interruption,exact_fresh_replay=True,raw_chunk_count=len(raw),prior_whole_song_max_logit_difference=old_max,performance=totals,
              files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.iterdir()) if p.suffix in ('.csv','.jsonl')})
    (OUT/'validation.json').write_text(json.dumps(info,indent=2,sort_keys=True)+'\n')
    floors=[d for d in distributions if d['below_01']>=180]
    ceilings=[d for d in distributions if d['above_99']>0]
    sentiment_winners={label:sum(max(SPEC['models']['cardiff']['columns'],key=lambda col:song[col])=='sentiment_'+label for song in songs) for label in ('negative','neutral','positive')}
    lines=['# Four-model production readiness','', '**READY for a separately authorized full-corpus run. Only the frozen 200-song sample has been classified by this production runner.**','',
           'BART is excluded from the production schema, executable model choices, replays and performance estimates. Earlier five-model experiments remain archived. The production panel preserves 42 separate content, emotion and sentiment features; it does not calculate CSI, MCR, hardness or consensus.','',
           '## Frozen panel and schema','',
           'The machine-readable [schema](../docs/classifier_production_schema.json) fixes labels, raw-head indices, artifact hashes, checkpoint revisions, windows and aggregation. The [operating guide](../docs/classifier_production.md) describes the local results database and resume commands. Model cards, licenses and training-domain limitations are retained in the [model specification](../docs/classifier_panel_specification.md); only its four retained models apply here.','',
           '| Model | Outputs | Context including special tokens | Aggregation |','|---|---:|---:|---|']
    for m in MODELS:lines.append(f"| {m} | {len(SPEC['models'][m]['columns'])} | {SPEC['models'][m]['window']} | Content-token-weighted chunk mean |")
    lines+=['','All four models use their own pinned tokenizer. Balanced, contiguous, non-overlapping partitions cover every normalized token exactly once. No truncation is enabled. Limits reserve two special tokens: 1,022 content tokens for LyricLens; 510 for the other models. LyricLens retains its upstream lossy English normalization; complete coverage refers to **normalized tokens**, not preservation of all original punctuation, inflections or non-English text. The original files are untouched. Cardiff retains its documented mention/URL substitution.','',
            'The weighted mean is the production summary for every output, including emotions and sentiment. It is an average of local classifier judgments, not a calibrated severity or whole-song occurrence probability. It avoids letting one noisy chunk determine the entire song. It can dilute a single extreme verse; the unmodified chunk logits and activated scores remain available for later, separately justified alternatives. Cardiff’s weighted mean preserves its three-class sum (float32 tolerance 3e-7).','',
            'The earlier pilot compared mean, weighted mean, maximum and q90. Maximum increased Detoxify toxicity by more than 0.10 in 17 songs and obscene in 12; with only two multi-chunk LyricLens songs it is not strong evidence for a category-specific maximum rule. Longer songs also have more opportunities for a high maximum. No cross-model averaging is performed.','',
            '## Exact 200-song validation','',
            f"All four models completed **200/200** songs: **800 successful song/model jobs**, **{len(raw):,} chunks**, zero failed jobs. The 180 stratified songs and 20 pre-existing sentinel songs are unchanged. Two fresh database runs reproduce all 42 song scores, processing metadata, chunk input hashes, raw logits and activated outputs **exactly** on this CPU configuration. Prior whole-song pilot maximum absolute logit difference: **{old_max:.3g}**. The coverage checks reconstruct every contiguous token range and verify the earlier independently persisted input hashes. No NaN/inf or out-of-range scores were accepted.",'',
            '| Model | Chunks | Songs needing >1 chunk | Maximum chunks/song |','|---|---:|---:|---:|']
    for x in performance:lines.append(f"| {x['model']} | {x['chunks']} | {x['multi_chunk_songs']} | {x['max_chunks']} |")
    lines+=['','All score distributions (min/max, mean/median/SD, quantiles and saturation counts) are in [distributions.csv](classifier_production/distributions.csv). Whole-song coverage does not repair domain mismatch or model saturation. Neither agreement nor numerical reproducibility establishes construct validity.','',
            'At least 90% of sample scores are below 0.01 for: '+', '.join(f"{d['column']} ({d['below_01']}/200)" for d in floors)+'. These can be sparse or domain-sensitive features; they are retained rather than silently dropped.', '',
            'Scores above 0.99 occur in: '+', '.join(f"{d['column']} ({d['above_99']}/200)" for d in ceilings)+'. Saturation is not cured by whole-song chunking.', '',
            'Cardiff largest-score classes: '+', '.join(f'{k} {v}/200' for k,v in sentiment_winners.items())+'. This neutral dominance is a domain diagnostic, not a historical finding.', '',
            '### Differences from prefix-only inference','', '| Feature | Mean absolute change | Maximum absolute change | Songs changing >0.10 | Largest-change identity | Prefix → whole |','|---|---:|---:|---:|---|---|']
    for x in prefix:lines.append(f"| {x['column']} | {x['mean_absolute_change']:.4f} | {x['maximum_absolute_change']:.4f} | {x['changed_above_10']} | {x['largest_title'].replace('|','/')} — {x['largest_artist'].replace('|','/')} | {x['prefix_score']:.4f} → {x['whole_song_score']:.4f} |")
    lines+=['','These are changes in input coverage and chunk context, not evidence that higher scores are more accurate. Song-level text, identities and scores have not been manually corrected.','',
            '## Cross-model judge map','',
            'Sexual content: LyricLens sexual content ↔ Detoxify sexual explicit. Explicit/obscene language: LyricLens explicit language ↔ Detoxify obscene. Violence, threats and anger/disgust are adjacent concepts, not synonyms: a violent narrative need not threaten a reader or express anger. LyricLens alone supplies substance use. Detoxify supplies comment-domain toxicity, severe toxicity, insult and identity attack. GoEmotions supplies all 28 emotion outputs, including neutral. Cardiff supplies negative/neutral/positive sentiment. No output is discarded as redundant merely because it correlates with another.','',
            '| Pair | Pearson (200) | Spearman (200) | Pearson (core 180) | Spearman (core 180) |','|---|---:|---:|---:|---:|']
    for x,y in PAIRS:
        a=next(z for z in correlations if z['subset']=='all_200' and z['x']==x and z['y']==y);b=next(z for z in correlations if z['subset']=='stratified_core_180' and z['x']==x and z['y']==y)
        lines.append(f"| {x} / {y} | {a['pearson']:.3f} | {a['spearman']:.3f} | {b['pearson']:.3f} | {b['spearman']:.3f} |")
    lines+=['','Correlations are diagnostic and sample-dependent; the sentinels affect the all-200 values. They do not establish a shared scale or independence of model errors. Weak violence/threat agreement is consistent with different constructs. Broad obscene/language agreement can coexist with disagreement over slang, narrative context and clean versions. Previous qualitative reviews still apply: comment toxicity is not lyrical content severity; emotion neutral is not a claim that lyrics are clean; tweet sentiment is not a measure of harmful content. No trend, COVID comparison or consensus outcome is estimated.','',
            '## Performance','', '| Model | Load (s) | Processing 200 (s) | Seconds/song | Projected 19,372 (hours) | Peak worker RSS (GiB) |','|---|---:|---:|---:|---:|---:|']
    for x in performance:lines.append(f"| {x['model']} | {x['load_seconds']:.2f} | {x['processing_seconds']:.2f} | {x['seconds_per_song']:.3f} | {x['estimated_full_hours']:.2f} | {x['peak_rss_bytes']/2**30:.2f} |")
    lines+=['',f"Sequential CPU float32 inference, four threads, batch size one: **{totals['total_seconds']/60:.2f} minutes** across the four workers including their model loads and durable per-chunk writes. Projected full run: **{totals['estimated_full_hours']:.2f} hours** plus parent preflight/hash validation and orchestration. Peak worker RSS: **{totals['peak_worker_rss_bytes']/2**30:.2f} GiB**; the lightweight parent is additional. Memory is bounded by sequential worker processes on the 16-GiB machine. No GPU benchmark or speedup is claimed.",'',
            f"Pilot database: {totals['pilot_database_bytes']:,} bytes; simple 96.86× projection: {totals['estimated_full_database_bytes']/2**20:.1f} MiB. Projected wide CSV: {totals['estimated_full_song_csv_bytes']/2**20:.1f} MiB; raw numerical chunk JSONL: {totals['estimated_full_chunks_jsonl_bytes']/2**20:.1f} MiB. Allow extra space for SQLite WAL and temporary exports; existing local model weights/environments are separate. Runtime and size estimates inherit this small sample’s lyric-length mix and are approximate.",'',
            '## Production safeguards and decision','',
            'The runner freezes an exact approved manifest, verifies all 19,372 source hashes and study membership, and opens research inputs read-only. It persists each completed chunk and finalizes each song/model independently in SQLite transactions. Pending/interrupted jobs resume; successful jobs skip; recorded errors require `--retry-errors`. Locks prevent concurrent writes by duplicate workers. Changed code, tokenizer/checkpoint, dependency versions, targets or lyric hashes fail closed rather than overwriting a prior run. Exception messages are not stored because they could contain input text.','',
            (f"The second fresh run was deliberately interrupted with SIGTERM and resumed: all {interruption['completed_jobs_preserved']} completed jobs and {interruption['persisted_chunks_preserved']} persisted chunks remained byte-for-byte equivalent as database row values. " if interruption else '')+'A no-op rerun and interruption/failure regression tests verify resume behavior. Full population and public-dataset integrity validation is recorded in the accompanying checkpoint validation note. The separate `song_results` table joins through stable `song_id`; the public 31-column master remains unchanged. The runner has not been invoked with full scope.','',
            '**READY for the authorized panel as reproducible exploratory features**, not validated calibrated severity measurements. The next action requires a separate decision to start the full run. No further BART work is needed.']
    (ROOT/'reports/classifier_production_readiness.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(info['performance'],indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,default=DEFAULT_PILOT);p.add_argument('--replay',type=Path,default=ROOT/'data/experiments/classifier_production/replay.db');a=p.parse_args();build(a.db,a.replay)
