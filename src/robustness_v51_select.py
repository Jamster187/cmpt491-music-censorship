"""Selection from complete saved V5 rankings, frozen before new diagnostics."""
from __future__ import annotations
import collections
import json
import numpy as np
import pandas as pd
import pairwise_v5_common as v5
import pairwise_v5_report as report
import robustness_v51_common as c

EXCLUDED_ROLES={'sample_size','quality_diagnostic','provenance_or_quality'}


def base_name(name):
    return name.removeprefix('fixed_composition__').removeprefix('matched_composition__')


def domain(value):
    if value in ['political','social']: return 'political_social'
    return value


def prepare(record, results):
    record=dict(record)
    external=results.external[record['external_variable']]
    dependencies=external.get('dependencies',[])
    record['external_root']='|'.join(sorted(dependencies)) if dependencies else record['external_variable'].removesuffix('__month_end')
    record['base_music_variable']=base_name(record['music_variable'])
    record['superdomain']=domain(record['external_domain'])
    record['original_q_min']=min(record['global_BY_q'] or 1.,record['global_rank_BY_q'] or 1.)
    # Preserve an exact zero q, if it occurs.
    record['original_q_min']=min(1. if record[k] is None else record[k] for k in ['global_BY_q','global_rank_BY_q'])
    record['selection_effect']=max(abs(record['pearson_r'] or 0),abs(record['spearman_rho'] or 0))
    a=record.get('exposure_effective_blocks'); b=record.get('score_effective_blocks')
    record['selection_broad_variation']=bool(a is not None and b is not None and np.isfinite(a) and np.isfinite(b) and min(a,b)>=6)
    record['coverage_months']=(pd.Period(record['last_month'],'M')-pd.Period(record['first_month'],'M')).n+1
    return record


def rank_key(r):
    return (-int(r['selection_broad_variation']),-r['positive_same_direction_folds'],-r['selection_effect'],
        r['original_q_min'],-r['coverage_months'],-r['native_n'],r['row_id'])


def eligible(r):
    return r['status']=='ok' and r['method'].startswith('Pearson') and r['native_n']>=v5.CONFIG['minimum_native'][r['native_frequency']] and r['external_source'] not in ['', '[]']


def choose(records, count, diverse_domains=False):
    ordered=sorted(records,key=rank_key); selected=[]; keys=set(); caps=collections.Counter()
    def take(r):
        key=(r['base_music_variable'],r['view'],r['external_root'],r['track'])
        cap=(r['base_music_variable'],r['view'],r['track'])
        if key in keys or caps[cap]>=2: return False
        selected.append(r); keys.add(key); caps[cap]+=1;return True
    if diverse_domains:
        for d in sorted({r['superdomain'] for r in records}):
            for r in ordered:
                if r['superdomain']==d and take(r): break
            if len(selected)>=count: return selected[:count]
    for r in ordered:
        if len(selected)>=count:break
        take(r)
    return selected


def select(results=None):
    results=report.Results() if results is None else results
    corrected=pd.read_csv(v5.PUBLIC/'corrected_relationships_complete.csv').to_dict('records')
    corrected=[prepare(r,results) for r in corrected if eligible(r)]
    selected={}; selection=c.CONFIG['selection']
    def add(rows,stratum):
        for r in rows:
            row_id=r['row_id']
            if row_id not in selected: selected[row_id]=dict(r,selection_strata=[])
            selected[row_id]['selection_strata'].append(stratum)
    lyric=lambda r:r['music_domain'].startswith('lyric') and r['music_role'] not in EXCLUDED_ROLES
    add(choose([r for r in corrected if r['track']=='adjusted' and lyric(r)],selection['corrected_adjusted_lyrical']),'corrected_adjusted_lyrical')
    add(choose([r for r in corrected if r['track']=='adjusted' and not lyric(r)],selection['corrected_adjusted_other']),'corrected_adjusted_other')
    add(choose([r for r in corrected if r['track']=='raw'],selection['corrected_raw'],True),'corrected_raw')
    # Complete domain index arrays, not their 200-row public excerpts.
    for d in selection['failed_domains']:
        ranking='adjusted' if d=='cultural' else 'political_social' if d=='political_social' else d
        indexes=np.load(v5.LOCAL/'rankings'/f'{ranking}.npy',mmap_mode='r')
        best=[]
        for index in indexes:
            task,name=results.locate(int(index)); row=results.rows[index]
            if task['track']!='adjusted' or task['external_kind']=='categorical' or row['status'] or domain(task['external_domain'])!=d:continue
            if row['q']<=.05 or row['q_rank']<=.05:continue
            meta=results.views[task['view_id']]['metadata'][name]
            if not meta['domain'].startswith('lyric') or results.role(name,meta) in EXCLUDED_ROLES:continue
            r=prepare(results.record(int(index)),results)
            if eligible(r):best=[r];break
        add(best,'strong_failed_'+d)
    indexes=np.load(v5.LOCAL/'rankings/raw.npy',mmap_mode='r')
    raw=[]
    for index in indexes:
        task,name=results.locate(int(index));row=results.rows[index]
        if row['status'] or task['external_kind']=='categorical':continue
        r=prepare(results.record(int(index)),results)
        if not eligible(r):continue
        if max(abs(r['time_correlation_external'] or 0),abs(r['time_correlation_music'] or 0))<.9:continue
        if any((q['base_music_variable'],q['view'],q['external_root'])==(r['base_music_variable'],r['view'],r['external_root']) for q in raw):continue
        raw.append(r)
        if len(raw)==selection['raw_trend_controls']:break
    add(raw,'raw_secular_trend_control')
    mandatory=[r for r in corrected if all(r[k]==v for k,v in selection['mandatory'].items())]
    if len(mandatory)!=1:raise ValueError('Mandatory caring/unemployment case not uniquely identified')
    add(mandatory,'mandatory_diagnostic')
    final=[]
    for i,(_,r) in enumerate(sorted(selected.items()),1):
        r=dict(r);r['candidate_id']=f'C{i:02d}';r['selection_strata']=';'.join(r['selection_strata']);final.append(r)
    return final


def freeze():
    with c.Budget('selection_and_preservation') as budget:
        c.snapshot(); budget.check()
        records=select();frame=pd.DataFrame(records)
        body=frame.to_csv(index=False,float_format='%.17g').encode()
        path=c.PUBLIC/'candidate_selection.csv'
        if path.exists() and path.read_bytes()!=body:raise ValueError('Selection changed; no hidden reselection permitted')
        if not path.exists():c.atomic(path,body)
        inputs=[v5.PUBLIC/'corrected_relationships_complete.csv',v5.PUBLIC/'corrected_influence_diagnostics.csv',
            v5.PUBLIC/'publication_manifest.json',v5.LOCAL/'results.npy',v5.LOCAL/'plan.pkl',v5.LOCAL/'views.pkl',v5.LOCAL/'external.pkl']
        inputs+=sorted((v5.LOCAL/'rankings').glob('*.npy'))
        value=dict(config=c.CONFIG,candidate_sha256=c.sha(path),candidate_count=len(records),
            input_hashes={str(p.relative_to(c.ROOT)):c.sha(p) for p in inputs},selection_code_sha256=c.sha(__file__),
            prior_results_only=True,new_robustness_fits_at_freeze=0)
        target=c.PUBLIC/'selection_freeze.json'
        if target.exists() and c.read_json(target)!=v5.clean(value):raise ValueError('Selection freeze metadata changed')
        if not target.exists():c.write_json(target,value)
        print(frame[['candidate_id','selection_strata','music_variable','view','external_variable','track','lag_months','pearson_r','original_q_min']].to_string(index=False),flush=True)


if __name__=='__main__':freeze()
