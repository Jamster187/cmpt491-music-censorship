"""Catch-up target/configuration adapter; frozen inference and persistence unchanged."""
import argparse
from contextlib import contextmanager, closing
import json
import signal
import sqlite3
import subprocess
import sys
from pathlib import Path
import classifier_production as runner
import classifier_production_store as store
import month_end_catchup as catchup
from classifier_production_store import ROOT, MODELS, SPEC, COLUMNS, canonical, digest, sha


def targets():
    m=catchup.manifest();rows=catchup.lyric_results()
    if len(rows)!=3654:raise ValueError('Finish all catch-up lyric dispositions before freezing classifier targets')
    allowed={s['song_id'] for s in m['songs']}
    if set(rows)!=allowed:raise ValueError('Unexpected lyric population')
    result=[]
    for sid,r in sorted(rows.items()):
        if r['status']!='accepted':continue
        path=ROOT/'data/lyrics'/f'{sid}.txt'
        if r['identity_confidence']!='identity_high_confidence' or r['pipeline_sha256']!=m['lyrics_pipeline_sha256']:raise ValueError('Unapproved lyric')
        if r['lyrics_path']!=str(path.relative_to(ROOT)) or path.is_symlink() or sha(path)!=r['lyrics_sha256']:raise ValueError('Source lyric changed')
        result.append(dict(song_id=sid,lyrics_sha256=r['lyrics_sha256'],source_words=len(path.read_text().split())))
    with closing(catchup.connect(ROOT/'data/processed/classifier_results.db',True)) as c:
        existing={r[0] for r in c.execute('SELECT song_id FROM targets')}
    if existing&allowed:raise ValueError('Unexpected existing classifier overlap: inspect/reuse before inference')
    return result


@contextmanager
def scoped_runner():
    """Replace only target selection/config identity, never scoring or validation."""
    original_targets=runner.targets;original_configuration=runner.configuration
    frozen=original_configuration('full')
    with closing(catchup.connect(ROOT/'data/processed/classifier_results.db',True)) as c:
        old=c.execute('SELECT configuration FROM run_config WHERE id=1').fetchone()[0]
    if canonical(frozen)!=old:raise ValueError('Frozen model implementation/runtime differs from accepted full run')
    policy=catchup.read(ROOT/'docs/classifier_accepted_missingness.json')
    if digest(old)!=policy['configuration_sha256']:raise ValueError('Unexpected frozen production configuration')
    m=catchup.manifest()
    config=dict(frozen,scope='month-end-catchup-v1',catchup_population_sha256=m['population_sha256'],
                frozen_full_configuration_sha256=digest(old),
                scope_adapter_sha256={n:m['implementation_sha256'][n] for n in catchup.ADAPTER_FILES})
    def get_targets(scope):
        if scope!='month-end-catchup-v1':raise ValueError('Wrong catch-up scope')
        return targets()
    def get_config(scope):
        if scope!='month-end-catchup-v1':raise ValueError('Wrong catch-up scope')
        return config
    runner.targets=get_targets;runner.configuration=get_config
    try:yield config
    finally:runner.targets=original_targets;runner.configuration=original_configuration


def validate(c,config):
    if c.execute('SELECT configuration FROM run_config WHERE id=1').fetchone()[0]!=canonical(config):raise ValueError('Configuration changed')
    result=runner.validate(c,'month-end-catchup-v1',False)
    failures=[]
    if [dict(r) for r in c.execute('SELECT * FROM targets ORDER BY song_id')]!=targets():raise ValueError('Target change')
    score_names={r['name'] for r in c.execute('PRAGMA table_info(song_results)') if r['type']=='REAL'}
    if score_names!=set(COLUMNS):raise ValueError('Output schema changed')
    jobs=c.execute('SELECT * FROM jobs').fetchall()
    for j in jobs:
        row=c.execute('SELECT * FROM song_results WHERE song_id=?',(j['song_id'],)).fetchone()
        m=j['model'];spec=SPEC['models'][m];artifact=spec['artifact']
        if row[m+'_model_revision']!=artifact['revision'] or row[m+'_checkpoint_sha256']!=artifact['sha256'][artifact['weight_file']]:raise ValueError('Checkpoint version changed')
        if row[m+'_status']!=j['status']:raise ValueError('Job/result status mismatch')
        if j['status'] not in ('success','error'):raise ValueError('Unattempted/interrupted jobs remain')
        if j['status']=='error':
            if not j['error_type'] or j['attempts']<1 or any(row[col] is not None for col in spec['columns']):raise ValueError('Invalid model-specific missingness')
            # Exception text is deliberately not retained: it can contain lyrics.
            reason=('preprocessing/tokenization failure before chunk preparation' if j['token_count'] is None else 'model/chunk processing failure')
            failures.append(dict(song_id=j['song_id'],model=m,error_type=j['error_type'],reason=reason))
        elif any(not isinstance(row[col],(float,int)) or not 0<=row[col]<=1 for col in spec['columns']):raise ValueError('Invalid numerical output')
    if c.execute('SELECT count(*) FROM song_results').fetchone()[0]!=result['targets']:raise ValueError('Missing/extra song results')
    result['model_specific_failures']=failures
    catchup.save(catchup.BASE/'classifier_validation.json',result)
    return result


def main():
    def interrupted(signum,frame):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupted)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('run','worker','validate'))
    p.add_argument('--model',choices=MODELS);args=p.parse_args()
    with scoped_runner() as config:
        if args.command=='worker':
            if args.model is None:raise ValueError('Worker requires model')
            runner.worker(catchup.CLASSIFIERS,args.model,False,'month-end-catchup-v1');return
        if args.command=='validate':
            with closing(catchup.connect(catchup.CLASSIFIERS,True)) as c:
                c.row_factory=sqlite3.Row;print(json.dumps(validate(c,config),indent=2))
            return
        with runner.lock(Path(str(catchup.CLASSIFIERS)+'.run.lock')):
            with closing(store.connect(catchup.CLASSIFIERS)) as c:
                store.initialize(c,targets(),config)
                for model in MODELS:
                    if not store.worklist(c,model):continue
                    child=subprocess.Popen([sys.executable,'-u',str(Path(__file__)),'worker','--model',model],cwd=ROOT)
                    try:child.wait()
                    except BaseException:child.terminate();child.wait();raise
                    if child.returncode:print(model,'worker exited',child.returncode,flush=True)
                print(json.dumps(validate(c,config),indent=2))

if __name__=='__main__':main()
