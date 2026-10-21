"""Explicitly approved exhaustive Phase 1; frozen pilot calculations, separate artifacts."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

import numpy as np
import scipy.stats

import relationship_discovery as engine
import relationship_discovery_spec as spec
import relationship_discovery_stats as stats
from regression_store import clean

PUBLIC=spec.PUBLIC/'full_phase1'
LOCAL=spec.ROOT/'data/experiments/relationship_discovery/full_phase1_v1'
FAMILIES={'pairwise':2775,'nonlinear':3192,'genre_interaction':3192}
LABEL='EXPLORATORY FULL PHASE 1; previously inspected population; no independent confirmation'
EXPECTED_SECONDS=68*60


def candidates():
    rows=[*spec.pair_candidates(),*spec.nonlinear_candidates(),*spec.genre_candidates()]
    rows.sort(key=lambda r:r['candidate_id'])
    ids=[r['candidate_id'] for r in rows]
    if len(ids)!=len(set(ids)) or dict(Counter(r['family'] for r in rows))!=FAMILIES:
        raise ValueError('Approved candidate universe changed')
    return rows


def identity():
    return dict(version='full-phase1-v1',source_commit='5e77ab93f6c951aed8c1ea625264c94d08118fab',
        pilot_identity=engine.identity(),runner_sha256=engine.old.original.sha(Path(__file__)),
        candidates_sha256=engine.old.digest(candidates()),candidate_counts=FAMILIES,
        primary_hypotheses=sum(FAMILIES.values()),global_correction='BY across all 9,159 attempted candidates, unavailable/failed p=1',
        inference=LABEL,precision='Frozen pilot resampling; no selective p-value refinement',
        execution_order='ascending candidate hash, all approved candidates; no screening',
        resource_guard=dict(projected_seconds=EXPECTED_SECONDS*1.5,check_after_new=200,maximum_rss_bytes=3*1024**3,minimum_free_bytes=2*1024**3),
        artist_sensitivity='Separate descriptive sensitivity on explicitly selected leading results; no new primary tests or q values')


def preservation(initialize=False):
    engine.preserve()
    path=LOCAL/'preservation.json'
    if not path.exists():
        if not initialize:raise ValueError('Phase 1 preservation snapshot missing')
        # The entire prior publication is immutable. The classroom UI may be extended.
        files={str(p.relative_to(spec.ROOT)):engine.old.original.sha(p)
               for p in spec.PUBLIC.rglob('*') if p.is_file() and PUBLIC not in p.parents
               and p.name!='full_phase1_findings.md'}
        engine.write_json(path,dict(sha256=files))
    record=engine.read_json(path)
    for name,digest in record['sha256'].items():
        if engine.old.original.sha(spec.ROOT/name)!=digest:raise ValueError('Prior pilot artifact changed: '+name)
    return dict(status='PASS',pilot_publication_files=len(record['sha256']),prior=engine.preserve())


def freeze():
    before=preservation(True)
    pilot=engine.read_json(spec.PUBLIC/'pilot_protocol.json')
    if pilot['identity']!=clean(engine.identity()):raise ValueError('Frozen pilot protocol changed')
    current=clean(identity());path=PUBLIC/'protocol.json'
    if path.exists():
        if engine.read_json(path)['identity']!=current:raise ValueError('Phase 1 protocol changed; refuse resume')
    else:
        engine.write_json(path,dict(locked_utc=datetime.now(timezone.utc).isoformat(),identity=current,
            approved_families=list(FAMILIES),prior_pilot_results_seen=True,initial_completed=0,preservation=before))
        engine.write_csv(PUBLIC/'candidates.csv',candidates())
    return engine.old.digest(current)


def checkpoint_path(row):return LOCAL/'checkpoints'/(row['candidate_id']+'.json.gz')


def save_checkpoint(row,fingerprint):
    path=checkpoint_path(row);path.parent.mkdir(parents=True,exist_ok=True)
    value=dict(protocol_sha256=fingerprint,logical_sha256=engine.old.digest(engine.logical(row)),result=row)
    raw=json.dumps(clean(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    temp=path.with_suffix('.tmp');temp.write_bytes(gzip.compress(raw,mtime=0));os.replace(temp,path)


def read_checkpoint(candidate,fingerprint):
    saved=json.loads(gzip.decompress(checkpoint_path(candidate).read_bytes()))
    row=saved['result']
    if saved['protocol_sha256']!=fingerprint or saved['logical_sha256']!=engine.old.digest(engine.logical(row)):
        raise ValueError('Checkpoint integrity failure: '+candidate['candidate_id'])
    for key in candidate:
        if row[key]!=candidate[key]:raise ValueError('Checkpoint candidate mismatch: '+candidate['candidate_id'])
    if row['evaluation_label']!=LABEL:raise ValueError('Exploratory evaluation label missing')
    return row


def complete_results():
    fingerprint=freeze();rows=[read_checkpoint(r,fingerprint) for r in candidates()]
    return stats.adjust_multiple_testing(rows)


def execute(row):
    started=time.perf_counter()
    try:
        result=engine.execute(row)
    except (ValueError,np.linalg.LinAlgError,FloatingPointError) as error:
        result=dict(row,status='failed',n=0,p_value=None,fit_count=0,fit_count_unknown=True,
            error=type(error).__name__+': '+str(error),traceback=traceback.format_exc(),
            wall_seconds=time.perf_counter()-started,peak_rss_bytes=engine.peak_rss_bytes())
    result['evaluation_label']=LABEL
    return clean(result)


def run(max_new=None):
    fingerprint=freeze();all_rows=candidates();summary=[];pending=[]
    for row in all_rows:
        if checkpoint_path(row).exists():summary.append(read_checkpoint(row,fingerprint))
        else:pending.append(row)
    reused=len(summary);started=time.perf_counter();last_print=started;new=0
    # Release detailed checkpoint rows after collecting the accounting fields.
    accounts=[{k:r.get(k) for k in ('family','status','fit_count','fit_count_unknown','wall_seconds','peak_rss_bytes')} for r in summary]
    del summary
    def progress(status):
        seconds=time.perf_counter()-started
        elapsed=sum(r['wall_seconds'] for r in accounts)
        counts=Counter(r['family'] for r in accounts)
        remaining={f:FAMILIES[f]-counts[f] for f in FAMILIES}
        family_seconds={f:sum(r['wall_seconds'] for r in accounts if r['family']==f) for f in FAMILIES}
        eta=sum(remaining[f]*family_seconds[f]/counts[f] if counts[f] else EXPECTED_SECONDS*remaining[f]/len(all_rows) for f in FAMILIES)
        result=dict(status=status,total=len(all_rows),completed=len(accounts),remaining=len(all_rows)-len(accounts),
            completed_by_family=dict(counts),remaining_by_family=remaining,status_counts=dict(Counter(r['status'] for r in accounts)),
            fit_count=sum(r['fit_count'] or 0 for r in accounts),unknown_failed_fit_counts=sum(bool(r['fit_count_unknown']) for r in accounts),
            resumed=reused,newly_computed=new,session_seconds=seconds,candidate_seconds=elapsed,
            candidates_per_second=len(accounts)/elapsed if elapsed else 0,estimated_remaining_seconds=eta,
            estimated_total_seconds=elapsed+eta,maximum_process_rss_bytes=max([r['peak_rss_bytes'] or 0 for r in accounts] or [0]),
            free_disk_bytes=shutil.disk_usage(LOCAL).free,protocol_sha256=fingerprint,
            updated_utc=datetime.now(timezone.utc).isoformat(),checkpoint_count=len(accounts))
        engine.write_json(LOCAL/'progress.json',result)
        print(json.dumps(result,sort_keys=True),flush=True)
        return result
    progress('running')
    for candidate in pending:
        if max_new is not None and new>=max_new:break
        result=execute(candidate);save_checkpoint(result,fingerprint)
        accounts.append({k:result.get(k) for k in ('family','status','fit_count','fit_count_unknown','wall_seconds','peak_rss_bytes')});new+=1
        now=time.perf_counter()
        if now-last_print>=25 or len(accounts)==len(all_rows):
            current=progress('running');last_print=now
            if current['maximum_process_rss_bytes']>3*1024**3 or current['free_disk_bytes']<2*1024**3 or (new>=200 and current['estimated_total_seconds']>1.5*EXPECTED_SECONDS):
                progress('paused_resource_guard');return 75
        if result['status']=='failed':print('RETAINED FAILED CANDIDATE '+candidate['candidate_id']+' '+result['error'],flush=True)
    status='complete' if len(accounts)==len(all_rows) else 'checkpointed'
    final=progress(status)
    if status=='complete':
        final['preservation']=preservation();engine.write_json(PUBLIC/'execution.json',final)
    return 0


def verify():
    started=time.perf_counter();rows=complete_results();ids=[r['candidate_id'] for r in rows]
    if len(ids)!=9159 or len(set(ids))!=9159:raise ValueError('Coverage failure')
    p=[r.get('p_value') if r.get('p_value') is not None else 1. for r in rows]
    q=scipy.stats.false_discovery_control(p,method='by')
    np.testing.assert_allclose(q,[r['q_by_global'] for r in rows],atol=0,rtol=0)
    frame=engine.data();splits=engine.models.make_splits(frame);proofs=[]
    for (a,b),(tr,va) in sorted(splits.items()):
        assert not set(frame.loc[tr,'song_id'])&set(frame.loc[va,'song_id'])
        assert frame.loc[tr,'last_iso'].lt(f'{a}-01-01').all()
        assert frame.loc[va,'last_iso'].lt(f'{b}-01-01').all()
        proofs.append(dict(period=[a,b],train=int(tr.sum()),evaluation=int(va.sum()),disjoint=True))
    for row in rows:
        for group in row.get('subgroup_results',[]):
            if group['adequate'] and (group['n']<spec.MIN_GROUP_EVALUATION or group['years']<5):raise ValueError('Invalid subgroup coverage')
    result=dict(status='PASS',candidate_counts=dict(Counter(r['family'] for r in rows)),candidates=len(ids),
        primary_hypotheses=len(p),unique_ids=True,checkpoints_verified=len(ids),global_by_recomputed=True,
        split_proofs=proofs,preservation=preservation(),logical_results_sha256=engine.old.digest(engine.logical(rows)),
        elapsed_seconds=time.perf_counter()-started)
    engine.write_json(PUBLIC/'validation.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['freeze','run','verify','verify-originals'])
    parser.add_argument('--max-new',type=int,help='Checkpoint after at most this many new candidates; never changes the candidate universe')
    args=parser.parse_args()
    if args.max_new is not None and args.max_new<1:parser.error('--max-new must be positive')
    if args.command=='run':raise SystemExit(run(args.max_new))
    print(json.dumps({'protocol_sha256':freeze()} if args.command=='freeze' else verify() if args.command=='verify' else preservation(),indent=2))


if __name__=='__main__':main()
