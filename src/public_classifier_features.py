"""Read-only, allowlisted classifier export with explicitly accepted missingness.

No model loading, inference, lyrics-file access or database mutation.
"""
import json
import math
import sqlite3
from contextlib import closing
from classifier_production_store import (
    ROOT, SPEC, MODELS, COLUMNS, sha, canonical, digest, chunks,
    validate_chunk, chunk_ranges, aggregate,
)

DATABASE=ROOT/'data/processed/classifier_results.db'
POLICY_PATH=ROOT/'docs/classifier_accepted_missingness.json'
POLICY=json.loads(POLICY_PATH.read_text())
EXCEPTIONS={(x['song_id'],x['model']):x for x in POLICY['exceptions']}


def project_song(row,jobs,exceptions=EXCEPTIONS):
    """Only successful numerical features or the named, documented nulls may leave."""
    sid=row['song_id'];values={}
    if set(jobs)!=set(MODELS):raise ValueError('Missing/extra model jobs')
    for model in MODELS:
        spec=SPEC['models'][model];job=jobs[model];exception=exceptions.get((sid,model))
        artifact=spec['artifact']
        if row[model+'_model_revision']!=artifact['revision'] or row[model+'_checkpoint_sha256']!=artifact['sha256'][artifact['weight_file']]:
            raise ValueError('Wrong model/checkpoint version')
        if row[model+'_status']!=job['status']:raise ValueError('Job/result status mismatch')
        if exception:
            if job['status']!='error' or job['error_type']!=exception['error_type'] or job['token_count'] is not None or job['chunk_count'] is not None:
                raise ValueError('Accepted exception evidence changed')
            if any(row[col] is not None for col in spec['columns']):raise ValueError('Accepted missing scores must remain NULL')
        elif job['status']!='success':raise ValueError('Undocumented classifier failure or unfinished job')
        for col in spec['columns']:
            value=row[col]
            if not exception and (type(value) not in (float,int) or not math.isfinite(value) or not 0<=value<=1):
                raise ValueError('Invalid classifier score')
            values[col]=value
        if not exception and model=='cardiff' and abs(sum(values[col] for col in spec['columns'])-1)>3e-7:
            raise ValueError('Sentiment scores do not sum to one')
    return tuple(values[col] for col in COLUMNS)


def load_features(research,database=DATABASE):
    """Validate the complete accepted release, without rewriting historical errors."""
    approved=dict(research.execute("SELECT song_id,lyrics_sha256 FROM lyrics_manifest JOIN study_population USING(song_id) WHERE lyrics_status='success' AND match_status='high_confidence'"))
    if len(approved)!=19372:raise ValueError('Approved lyric population changed')
    before=sha(database)
    with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)) as c:
        c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Classifier database integrity failed')
        config=c.execute('SELECT configuration FROM run_config WHERE id=1').fetchone()[0]
        if digest(config)!=POLICY['configuration_sha256']:raise ValueError('Not the accepted frozen production configuration')
        targets=dict(c.execute('SELECT song_id,lyrics_sha256 FROM targets'))
        if targets!=approved:raise ValueError('Classifier targets differ from approved lyrics')
        all_jobs={}
        for j in c.execute('SELECT * FROM jobs'):
            key=(j['song_id'],j['model'])
            if key in all_jobs or j['song_id'] not in approved or j['model'] not in MODELS:raise ValueError('Duplicate/unknown classifier job')
            all_jobs[key]=dict(j)
        if len(all_jobs)!=19372*4:raise ValueError('Wrong model-job count')
        if {k for k,j in all_jobs.items() if j['status']!='success'}!=set(EXCEPTIONS):raise ValueError('Unaccepted model missingness')
        result={};chunk_count=0
        for row in c.execute('SELECT * FROM song_results ORDER BY song_id').fetchall():
            sid=row['song_id']
            if sid in result or sid not in approved or row['lyrics_sha256']!=approved[sid]:raise ValueError('Duplicate/unknown/changed classifier input')
            jobs={m:all_jobs[sid,m] for m in MODELS}
            values=project_song(row,jobs)
            for model,job in jobs.items():
                raw=chunks(c,sid,model);chunk_count+=len(raw)
                if (sid,model) in EXCEPTIONS:
                    if raw:raise ValueError('Preprocessing exception has unexpected predictions')
                    continue
                if job['content_budget']!=SPEC['models'][model]['window']-2:raise ValueError('Changed chunk budget')
                if len(raw)!=job['chunk_count'] or [r['chunk_index'] for r in raw]!=list(range(len(raw))):raise ValueError('Incomplete/duplicate chunk sequence')
                if [(r['content_start'],r['content_end']) for r in raw]!=chunk_ranges(job['token_count'],job['content_budget']):raise ValueError('Changed/incomplete token partitions')
                for r in raw:
                    validate_chunk(model,r)
                    if r['input_tokens']!=r['content_end']-r['content_start']+2:raise ValueError('Incorrect special-token count')
                for col in SPEC['models'][model]['columns']:
                    expected=aggregate([r['scores'][col] for r in raw],[r['content_end']-r['content_start'] for r in raw])['token_weighted_mean']
                    if row[col]!=expected:raise ValueError('Changed aggregation or score')
            result[sid]=values
        if set(result)!=set(approved):raise ValueError('Missing classifier song result')
        if chunk_count!=c.execute('SELECT count(*) FROM chunk_predictions').fetchone()[0]:raise ValueError('Unexpected chunk records')
    if sha(database)!=before:raise ValueError('Classifier database changed during validation')
    provenance=dict(database_sha256=before,configuration_sha256=digest(config),production_commit=POLICY['production_commit'],
                    schema_sha256=sha(ROOT/'docs/classifier_production_schema.json'),accepted_missingness_sha256=sha(POLICY_PATH),
                    projection_sha256=sha(__file__),target_songs=len(result),all_models_available=len(result)-len(EXCEPTIONS),
                    numerical_features=len(COLUMNS),chunks=chunk_count,accepted_missingness=POLICY['exceptions'])
    return result,provenance
