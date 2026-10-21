"""Publish complete approved Phase 1 results and compact, measured presentation views."""
from __future__ import annotations
from collections import Counter,defaultdict
import csv
import gzip
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
import relationship_phase1 as phase
import relationship_phase1_analysis as interpret
import relationship_discovery as engine
import relationship_discovery_spec as spec

PUBLIC=phase.PUBLIC
_loader=importlib.util.spec_from_file_location('preserved_pilot_renderer',spec.PUBLIC/'render.py')
pilot=importlib.util.module_from_spec(_loader);_loader.loader.exec_module(pilot)


def write_gzip(path,value):
    raw=json.dumps(engine.clean(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    path=Path(path);temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_bytes(gzip.compress(raw,mtime=0));os.replace(temp,path)


def write_csv(path,rows):
    rows=list(rows)
    if not rows:raise ValueError('No empty placeholder output: '+str(path))
    fields=sorted(set().union(*(r.keys() for r in rows)))
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator='\n');writer.writeheader()
    for row in rows:
        row=engine.clean(row)
        writer.writerow({k:json.dumps(v,separators=(',',':'),sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    raw=out.getvalue().encode();path=Path(path)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_bytes(gzip.compress(raw,mtime=0) if path.suffix=='.gz' else raw);os.replace(temp,path)


def flatten(row):
    result=pilot.flat(row)
    result.update(target_domain=spec.domain(row['target']),predictor_domain=spec.domain(row['predictors'][0]),
        priority_cross_domain=interpret.priority_cross(row),positive_stable_performance_tier=interpret.utility_tier(row),
        shared_lyric_measurement=interpret.source_domain(row['target'])==interpret.source_domain(row['predictors'][0])=='lyrics',
        comparison_r2=row.get('comparison_metrics',{}).get('r2'),comparison_rmse=row.get('comparison_metrics',{}).get('rmse'),
        comparison_mae=row.get('comparison_metrics',{}).get('mae'),
        error=row.get('error'),fit_count_unknown=row.get('fit_count_unknown',False),
        global_by_hypotheses=9159,family_by_hypotheses=phase.FAMILIES[row['family']])
    if row['family']!='pairwise':result['p_resolution']=1/(spec.SIGN_FLIPS+1)
    for fold in row.get('folds',[]):
        prefix='period_'+str(fold['period'][0])+'_'
        result.update({prefix+k:v for k,v in dict(status=fold['status'],n_train=fold['n_train'],n_test=fold['n_test'],
            n_test_predictor_complete=fold['n_test_predictor_complete'],r2=fold.get('metrics',{}).get('r2'),
            comparison_r2=fold.get('comparison_metrics',{}).get('r2'),relative_mse_improvement=fold.get('relative_mse_improvement'),
            selected_method=fold.get('selected_method')).items()})
    return result


def demo_record(row):
    # Complete published aggregates; method-by-method timings remain in local checkpoints.
    excluded={'timings','traceback'}
    result={k:v for k,v in row.items() if k not in excluded}
    result['priority_cross_domain']=interpret.priority_cross(row)
    result['positive_stable_performance_tier']=interpret.utility_tier(row)
    if 'folds' in result:
        result['folds']=[{k:v for k,v in fold.items() if k!='inner_models'} for fold in row['folds']]
    if row['family']=='nonlinear':
        result.pop('subgroup_results',None) # All complete coverage remains in local checkpoints; no UI uses these repeated cells.
        diags=[]
        for detail in row.get('diagnostics',[]):
            indices=np.unique(np.round(np.linspace(0,len(detail['x'])-1,25)).astype(int))
            d={k:v for k,v in detail.items() if k not in {'x','linear','nonlinear'}}
            for key in ('x','linear','nonlinear'):d[key]=[detail[key][int(i)] for i in indices]
            d['plot_grid_note']='25 retained points of the 100 saved fitted-curve points; line segments are a display approximation'
            diags.append(d)
        result['diagnostics']=diags
    return result


def publish_demo(rows):
    index=[];groups=defaultdict(list);mapping={}
    for row in rows:
        item={k:v for k,v in row.items() if k not in {'timings','traceback','folds','diagnostics','subgroup_results','annual_effects'}}
        item['priority_cross_domain']=interpret.priority_cross(row)
        item['positive_stable_performance_tier']=interpret.utility_tier(row)
        index.append(item);groups[(row['family'],row['target'])].append(row)
    for (family,target),group in sorted(groups.items()):
        name='demo_details/'+family+'/'+engine.old.digest(target)[:16]+'.json.gz'
        path=PUBLIC/name;path.parent.mkdir(parents=True,exist_ok=True)
        write_gzip(path,[demo_record(r) for r in group])
        mapping.setdefault(family,{})[target]=name
    engine.write_json(PUBLIC/'demo_detail_files.json',mapping)
    # The index is the app's readiness marker: publish it only after all details.
    write_gzip(PUBLIC/'demo_results.json.gz',index)


def digest_manifest():
    paths=[p for p in PUBLIC.rglob('*') if p.is_file() and p.name!='artifact_manifest.json' and '__pycache__' not in p.parts]
    paths.append(spec.PUBLIC/'full_phase1_findings.md')
    sources=[Path(__file__).resolve(),ROOT/'src/relationship_phase1.py',ROOT/'src/relationship_phase1_analysis.py',ROOT/'src/relationship_phase1_prepare.py',ROOT/'src/relationship_demo.py',
        ROOT/'tests/test_relationship_phase1.py',ROOT/'tests/test_relationship_phase1_demo.py',ROOT/'tests/test_relationship_phase1_publication.py',ROOT/'tests/test_relationship_demo.py']
    prior=engine.read_json(spec.PUBLIC/'artifact_manifest.json')['sha256']
    engine.write_json(PUBLIC/'artifact_manifest.json',dict(sha256={str(p.relative_to(ROOT)):engine.old.original.sha(p) for p in paths},
        protocol_sha256=engine.old.digest(engine.read_json(PUBLIC/'protocol.json')['identity']),
        sources_sha256={str(p.relative_to(ROOT)):engine.old.original.sha(p) for p in sources},
        approved_ui_revisions=dict(source_commit='5e77ab93f6c951aed8c1ea625264c94d08118fab',
            preserved_historical_sha256={p:prior[p] for p in ['src/relationship_demo.py','tests/test_relationship_demo.py']},
            reason='User explicitly requested extending the discovery classroom demo; previous UI/tests remain retrievable from the source commit; all pilot results and statistical code are unchanged'),
        large_local_checkpoints_committed=False))


def summaries(rows):
    output=[]
    for family in phase.FAMILIES:
        group=[r for r in rows if r['family']==family];elapsed=sum(r['wall_seconds'] for r in group)
        output.append(dict(family=family,candidates=len(group),status_counts=dict(Counter(r['status'] for r in group)),
            global_by_pass=sum(r['q_by_global']<=.05 for r in group),nontrivial_by_pass=sum(r['q_by_global']<=.05 and not r['category'].startswith('A') for r in group),
            cross_source_by_pass=sum(r['q_by_global']<=.05 and interpret.priority_cross(r) for r in group),
            positive_stable_performance=sum(interpret.utility_tier(r) and not r['category'].startswith('A') for r in group),
            negative_r2=sum(r.get('r2') is not None and r['r2']<0 for r in group),
            fit_calls=sum(r.get('fit_count',0) for r in group),candidate_seconds=elapsed,
            candidates_per_second=len(group)/elapsed,maximum_process_rss_bytes=max(r['peak_rss_bytes'] for r in group)))
    return output


def null_summaries(rows):
    result=[]
    for family in ('nonlinear','genre_interaction'):
        for target in spec.NUMERIC:
            if spec.domain(target)!='chart_performance':continue
            group=[r for r in rows if r['family']==family and r['target']==target and interpret.source_domain(r['predictors'][0])=='lyrics']
            if not group:continue
            result.append(dict(family=family,target=target,lyric_predictors=len(group),
                global_by_pass=sum(r['q_by_global']<=.05 for r in group),positive_r2=sum((r.get('r2') or 0)>0 for r in group),
                positive_stable_performance=sum(interpret.utility_tier(r) for r in group),
                best_r2=max((r.get('r2') for r in group if r.get('r2') is not None),default=None),
                median_r2=float(np.median([r['r2'] for r in group if r.get('r2') is not None])),
                median_relative_mse_improvement=float(np.median([r['relative_mse_improvement'] for r in group if r.get('relative_mse_improvement') is not None]))))
    return result


def table_results(rows):
    table=[]
    for row in rows:
        ci=row.get('effect_interval',{}).get('interval') if row['family']=='pairwise' else [row.get('ci_low'),row.get('ci_high')]
        table.append([row['candidate_id'],row['target'],row['predictors'][0],row['family'],row['category'][0],row['n'],
            pilot.number(row.get('effect')),('['+', '.join(pilot.number(x) for x in ci)+']') if ci else 'unavailable',
            pilot.number(row.get('r2')),pilot.number(row.get('comparison_metrics',{}).get('r2')),
            pilot.number(100*row['relative_mse_improvement'],2) if row.get('relative_mse_improvement') is not None else 'n/a',
            pilot.number(row['q_by_global'],5),pilot.number(row.get('stability_fraction'),2)])
    return pilot.table(['ID','Target','Predictor','Family','Category','N','Effect','95% temporal block interval','Outer R²','Comparison R²','MSE gain %','Global BY q','Positive-period/annual-sign fraction'],table)


def axis_label(name):
    unit='months since 1970-01' if name in {'first_snapshot_month','last_snapshot_month'} else 'days since 1970-01-01' if name in spec.old.original.DATES else 'calendar year' if name=='mb_release_year' else 'classifier score' if name in spec.old.original.SCORES else 'seconds' if name in spec.old.original.DURATIONS else None
    return name.replace('_',' ')+(f' ({unit})' if unit else '')


def substantive_examples(views):
    # Post-hoc filters preserve the existing rank key and the complete rankings.
    genre=next(r for r in views['genre_interaction'] if interpret.priority_cross(r))
    chart=next(r for r in views['nonlinear'] if spec.domain(r['target'])=='chart_performance'
        and r['predictors'][0].startswith('mb_'))
    return genre,chart


def render_figures(views,rows,plots,reversals):
    folder=PUBLIC/'figures';folder.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'svg.hashsalt':'cmpt491-phase1-v1'})
    index=[]
    def save(fig,name,row,description):
        if name=='aggregate_within_genre':footer='Exploratory descriptive associations; no subgroup p-values or q-values'
        elif name=='improvement_vs_performance':footer='Exploratory; per-model uncertainty, q-values and sample sizes are in the numbered table'
        else:footer=f"Exploratory · overall improvement global BY q={row['q_by_global']:.4g} · all-evaluation N={row['n']:,} · pooled R²={row['r2']:.3f}"
        fig.supxlabel(footer,fontsize=8)
        path=folder/(name+'.svg');fig.savefig(path,metadata={'Date':None})
        fig.savefig(Path('/tmp')/('cmpt491-phase1-'+name+'.png'),dpi=150)
        plt.close(fig)
        path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
        index.append(dict(file=str(path.relative_to(PUBLIC)),candidate_id=row['candidate_id'],description=description))
    row=views['nonlinear'][0];detail=row['diagnostics'][-1]
    fig,ax=plt.subplots(figsize=(8.5,4.5),layout='constrained')
    ax.plot(detail['x'],detail['linear'],color='#777777',label='OLS baseline')
    ax.plot(detail['x'],detail['nonlinear'],color='#2166ac',label=detail['selected_method'],linewidth=2)
    ax.set(xlabel=axis_label(row['predictors'][0]),ylabel=axis_label(row['target']),title='Training-fitted nonlinear curve · 2018–2025 evaluation')
    ax.legend();save(fig,'nonlinear_curve',row,'Highest presentation-ranked non-reconstruction nonlinear relationship; last outer fold; 100 saved curve points')
    row,_=substantive_examples(views)
    data=[d for d in plots[row['candidate_id']]['artist_slopes'] if d['period']==[2018,2026] and d['train_supported'] and d['evaluation_adequate']]
    data.sort(key=lambda d:d['slope'])
    fig,ax=plt.subplots(figsize=(8.5,4.5),layout='constrained')
    ax.barh([d['genre'] for d in data],[d['slope'] for d in data],color='#2166ac')
    if data:ax.axvline(data[0]['additive_slope'],color='#b35806',linestyle='--',label='Additive common slope')
    ax.axvline(0,color='#777777',linewidth=.7);ax.set(xlabel=f"Change in {axis_label(row['target'])}\nper unit {axis_label(row['predictors'][0])}",title='Fitted genre-specific slopes · 2018–2025 evaluation')
    ax.legend();save(fig,'genre_slopes',row,'Training-fitted slopes; only training-supported, adequately evaluated genres displayed; no slope confidence claims')
    row=views['cross_predictive'][0]
    fig,ax=plt.subplots(figsize=(8.5,4.5),layout='constrained');valid=[f for f in row['folds'] if f['status']=='ok']
    names=[f"{f['period'][0]}–{f['period'][1]-1}" for f in valid];x=np.arange(len(names))
    ax.bar(x-.18,[f['comparison_metrics']['r2'] for f in valid],.36,label='Comparison',color='#999999')
    ax.bar(x+.18,[f['metrics']['r2'] for f in valid],.36,label=row['family'],color='#2166ac')
    ax.set(xticks=x,xticklabels=names,ylabel='Out-of-period R²',title=f"{row['target']} ← {row['predictors'][0]}")
    ax.axhline(0,color='#555555',linewidth=.7);ax.legend();save(fig,'historical_stability',row,'All four approved outer periods; no breakpoint search')
    _,row=substantive_examples(views)
    values=plots[row['candidate_id']]['actual_predicted'];actual=np.array([p['actual'] for p in values]);pred=np.array([p['predicted'] for p in values])
    fig,ax=plt.subplots(figsize=(6.5,5),layout='constrained');ax.scatter(actual,pred,s=9,alpha=.25,color='#2166ac')
    lower=float(min(actual.min(),pred.min()));upper=float(max(actual.max(),pred.max()));ax.plot([lower,upper],[lower,upper],color='#b35806',linestyle='--')
    ax.set(xlabel='Observed '+axis_label(row['target']),ylabel='Predicted '+axis_label(row['target']),title='Actual versus predicted · fixed hash sample of outer songs')
    save(fig,'actual_predicted',row,'Up to 1,200 actual outer-evaluation songs; published metrics use all eligible songs')
    flagged=[r for r in reversals if r['priority_cross_domain'] and (r['sign_reversal'] or r['attenuation'] or r['opposed_genre_signs'])]
    flagged.sort(key=lambda r:(not r['sign_reversal'],not r['attenuation'],-abs(r['pooled_rho']-r['genre_adjusted_rho']),r['candidate_id'],r['period']))
    if flagged:
        found=flagged[0];row=next(r for r in rows if r['candidate_id']==found['candidate_id'])
        d=next(d['conditional_correlations'] for d in row['diagnostics'] if d['period']==found['period'])
        groups=[g for g in d['subgroups'] if g['adequate']]
        labels=['Pooled','Genre adjusted']+[g['group'] for g in groups]
        vals=[d['marginal_spearman'],d['partial_spearman']]+[g['spearman'] for g in groups]
        fig,ax=plt.subplots(figsize=(8.5,5),layout='constrained');ax.barh(labels,vals,color=['#b35806','#666666']+['#2166ac']*len(groups));ax.axvline(0,color='#555555',linewidth=.7)
        ax.set(xlabel='Descriptive Spearman / partial-rank association',xlim=(-1,1),title=f"{found['target']} ↔ {found['predictor']}\nAggregate and genre associations · {found['period'][0]}–{found['period'][1]-1}")
        save(fig,'aggregate_within_genre',row,'Post-hoc descriptive sign/attenuation candidate; adequate genre cells retained; no subgroup significance claim')
    # Directly contrast absolute predictive utility with relative improvement.
    values=views['nonlinear'][:10]
    fig,ax=plt.subplots(figsize=(8.5,5),layout='constrained')
    ax.scatter([100*r['relative_mse_improvement'] for r in values],[r['r2'] for r in values],s=45,color='#2166ac')
    offsets={2:(-22,-20),3:(8,20),4:(-22,13),5:(14,-16),8:(-20,-15),9:(7,8)}
    for i,r in enumerate(values):ax.annotate(str(i+1),(100*r['relative_mse_improvement'],r['r2']),xytext=offsets.get(i,(4,4)),textcoords='offset points',arrowprops=dict(arrowstyle='-',color='#888888',lw=.5))
    ax.axhline(0,color='#555555',linewidth=.7);ax.axvline(0,color='#777777',linewidth=.7)
    ax.set(xlabel='MSE improvement over OLS (%)',ylabel='Absolute outer R²',title='Top ten nonlinear presentation rows · numbers match table order')
    save(fig,'improvement_vs_performance',values[0],'No arbitrary combined score; shows two distinct measured quantities')
    engine.write_json(PUBLIC/'figure_index.json',index)


def findings(rows,views,family_summary,reversals,period_signs,nulls,artist,execution):
    total_by=sum(r['q_by_global']<=.05 for r in rows)
    nonlinear=views['nonlinear'][:10];genre=views['genre_interaction'][:10];cross=views['cross_shortlist']
    flagged=[r for r in reversals if r['priority_cross_domain'] and (r['sign_reversal'] or r['attenuation'] or r['opposed_genre_signs'])]
    flagged.sort(key=lambda r:(not r['sign_reversal'],not r['attenuation'],-abs(r['pooled_rho']-r['genre_adjusted_rho']),r['candidate_id'],r['period']))
    # Reciprocal x/y fits report the same diagnostic association: show unique pair-periods.
    unique=[];seen=set()
    for row in flagged:
        key=(tuple(sorted([row['target'],row['predictor']])),tuple(row['period']))
        if key not in seen:unique.append(row);seen.add(key)
    period_flags=[r for r in period_signs if r['priority_cross_domain'] and r['period_sign_reversal']]
    period_flags.sort(key=lambda r:(-min(abs(r['minimum_rho']),abs(r['maximum_rho'])),r['candidate_id']))
    period_examples=[];seen=set()
    for row in period_flags:
        key=tuple(sorted([row['target'],row['predictor']]))
        if key not in seen:period_examples.append(row);seen.add(key)
    failures=[r for r in rows if r['family']!='pairwise' and not r['category'].startswith('A') and
        (r.get('r2') or 0)>0 and (r.get('relative_mse_improvement') or 0)>0 and
        (r.get('worst_period_relative_improvement') or 0)<-.05]
    failures.sort(key=lambda r:(not interpret.priority_cross(r),r['worst_period_relative_improvement'],r['candidate_id']))
    artist_map={r['candidate_id']:r for r in artist}
    best=views['cross_predictive'][0];non=nonlinear[0];gen=genre[0]
    substantive_genre,metadata_chart=substantive_examples(views)
    text=f'''# Full Phase 1 relationship-discovery findings

**Exploratory full search, not independent confirmation or causation.** All
9,159 approved candidates were attempted: 2,775 pairwise, 3,192 nonlinear and
3,192 genre interactions. Previous analyses and datasets remain unchanged.
No additional discovery family was launched.

## Execution and evidence

The run performed {execution['fit_count']:,} fitting calls and evaluated 9,159
primary candidate hypotheses in {execution['session_seconds']/60:.2f} minutes
of execution-session wall time ({execution['candidate_seconds']/60:.2f} minutes
inside candidate calculations). Peak process RSS was
{execution['maximum_process_rss_bytes']/1024**2:.1f} MiB. All candidate checkpoints
were retained. See [execution accounting](full_phase1/execution.json) and
[validation](full_phase1/validation.json). Replay and artist-sensitivity refits
are additional validation/interpretation work, recorded separately.

{pilot.table(['Family','Candidates','Fits','Global BY ≤0.05','Non-reconstruction BY','Priority cross-domain BY','Positive/stable performance tier','Negative outer R²'],[[r['family'],r['candidates'],r['fit_calls'],r['global_by_pass'],r['nontrivial_by_pass'],r['cross_source_by_pass'],r['positive_stable_performance'],r['negative_r2']] for r in family_summary])}

Global Benjamini–Yekutieli adjustment used all **9,159** candidates, including
reconstruction controls and unavailable tests at p=1. **{total_by:,}** candidates
meet the exploratory global q≤0.05 threshold. This is the denominator for this
approved campaign, not an omnibus correction over every previous project
analysis. No hypothesis is independently confirmed. The fixed permutation
resolution, artist dependence, overlapping training histories and selection
uncertainty remain limitations; a low q-value is not proof of scientific novelty.

Raw p-values, global and family q-values, uncertainty and failed/null rows are in
the three [complete result tables](full_phase1/README.md). All secondary measures,
subgroup comparisons and signs are descriptive. Exact frozen support rules and
[methodology](full_phase1/methodology.md) are unchanged.

## What the rankings mean

Statistical evidence, predictive usefulness and scientific interest are different.
Predictive presentation rows first require positive pooled absolute R² and mean-baseline
skill, improvement in all four periods, and a positive temporal interval lower
bound. Within that tier, worst-period relative improvement precedes the lower
interval bound. Rows outside the tier remain in the complete rankings. This
presentation order does not choose/refit models using outer outcomes.
The positive/stable tier is a presentation screen, not a practical-usefulness
threshold. Tiny positive R² or error reductions can still be of little use.
It does not require positive R² within every period. For the leading calendar-to-
duration example, all four period-specific R² values are negative despite pooled
R² {best['r2']:.4f}; pooling includes between-period variation. Its large gain over
an extrapolating linear baseline does not establish useful within-period prediction.

Pairwise effects are ranked within their own effect type. The cross-domain table
below is a fixed coverage shortlist: five numerical associations, two categorical
associations, three predictive relationships. These blocks do not have a common
magnitude scale. Affect–content classifier comparisons remain in the original
C category but are excluded from this **priority cross-domain shortlist**.
All charts and ranks are descriptive post-hoc selections from the complete run.

For numerical pairwise rows, effect is pooled Spearman rho and the interval is a
two-year block interval. Categorical rows use eta-squared or corrected Cramér's V.
Their primary permutation statistic conditions on debut year and can differ from
the displayed pooled effect. Predictive effect is the equal-two-year-block mean
loss reduction divided by training target variance; it is **not** the MSE-gain
percentage. R², comparison R² and MSE gain use equal-song outer losses.

## Ten cross-domain presentation relationships

{table_results(cross)}

## Ten nonlinear presentation relationships

{table_results(nonlinear)}

Category B rows are related measurements, often classifier overlap; they are useful
model-behavior demonstrations, not major independent musical discoveries.
Some original-category C content–affect pairs also share the same lyrics and
classification pipeline. The complete tables explicitly flag shared lyrical
measurement; C alone is not evidence of independent measurement or novelty.

## Ten genre-interaction presentation relationships

{table_results(genre)}

Genre models compare genre-specific slopes against the same predictor plus genre
main effects. Adequate support is determined from training only. A positive gain
can coexist with poor absolute prediction. Complete held-out genre coverage and
four-period metrics are available through the classroom demo.

## Substantive examples beyond shared measurements

The top raw rankings above deliberately retain related classifiers and metadata
counts. The following examples use the same existing order, restricted to
(1) broader-domain genre interactions and (2) metadata predicting chart outcomes.
These are disclosed post-hoc presentation choices, with no additional hypotheses.

{table_results([substantive_genre,metadata_chart])}

The metadata-to-chart example has only modest absolute performance despite its
strong pooled pairwise association: nonlinear R² {metadata_chart['r2']:.4f},
MSE gain {100*metadata_chart['relative_mse_improvement']:.2f}%, with all four periods
improving on OLS. Catalog release counts can accumulate after a song succeeds;
this is retrospective prediction, not a deployable debut-time popularity forecast.
The broader-domain genre interaction improves MSE by
{100*substantive_genre['relative_mse_improvement']:.2f}% over the additive model,
with worst-period gain {100*substantive_genre['worst_period_relative_improvement']:.2f}%.
Its absolute R² includes genre main effects. It does not establish that catalog
counts cause lyrical content. Both examples have separate artist-credit checks.

## Sign reversals, attenuation and historical consistency

The following are descriptive candidates, with no new subgroup significance claim.
Opposed genre signs require adequate genres with rho ≤−0.10 and ≥+0.10. A pooled
to adjusted reversal requires |pooled rho|≥0.10 and |adjusted rho|≥0.05. Attenuation
means |adjusted rho|≤25% of |pooled rho| with |pooled rho|≥0.10. These are disclosed
presentation cutoffs, not evidence of a causal Simpson's paradox.
Chart weeks and weekly-observation counts are aliases here; their repeated rows
represent the same substantive pattern, not independent discoveries.

{pilot.table(['Target','Predictor','Period','Pooled rho','Genre-adjusted rho','Reversal','Attenuation','Most negative adequate genre','Most positive adequate genre'],[[r['target'],r['predictor'],str(r['period']),pilot.number(r['pooled_rho']),pilot.number(r['genre_adjusted_rho']),r['sign_reversal'],r['attenuation'],f"{r['minimum_genre']} {pilot.number(r['minimum_genre_rho'])} (N={r['minimum_genre_n']})",f"{r['maximum_genre']} {pilot.number(r['maximum_genre_rho'])} (N={r['maximum_genre_n']})"] for r in unique[:10]])}

All four historical windows are shown for every predictive candidate. They are
reused observations, not four independent confirmation studies. A stable sign
alone does not guarantee useful predictions. No breakpoint or 2020 effect was
newly tested in Phase 1.

Substantial sign changes across the same four approved windows are shown below.
Each displayed window has at least 200 complete pairs; both signs must reach
absolute rho 0.10. Changing genre composition and coverage can contribute.

{pilot.table(['Target','Predictor','Negative period','Negative rho','Positive period','Positive rho'],[[r['target'],r['predictor'],str(r['minimum_period']),pilot.number(r['minimum_rho']),str(r['maximum_period']),pilot.number(r['maximum_rho'])] for r in period_examples[:5]])}

## Null and generalization results

The following summary retains all 42 lyric predictors for every eligible chart
outcome, including weak and adverse results. “No BY evidence” means this analysis
did not establish the specified improvement; it does not establish no association.
Genre-interaction R² includes genre main effects as well as the lyric predictor;
it cannot be attributed to lyrics alone. Its improvement compares with the same
lyric predictor plus genre main effects, isolating the additional genre slopes.

{pilot.table(['Family','Chart target','Lyric predictors','Global BY passes','Positive R²','Positive/stable performance tier','Best R²','Median R²','Median MSE gain %'],[[r['family'],r['target'],r['lyric_predictors'],r['global_by_pass'],r['positive_r2'],r['positive_stable_performance'],pilot.number(r['best_r2']),pilot.number(r['median_r2']),pilot.number(100*r['median_relative_mse_improvement'],2)] for r in nulls])}

{sum(r.get('r2') is not None and r['r2']<0 for r in rows):,} predictive candidates have
negative pooled outer R². Their values and period failures remain visible.
Calendar targets and extreme extrapolations can produce large relative gains from
an even worse linear comparator. They must not be described as successful prediction.

These models have positive pooled R² and positive pooled improvement, yet worsen
comparison MSE by more than 5% in at least one outer period. Pooled success alone
therefore does not establish historical consistency.

{pilot.table(['Target','Predictor','Family','Pooled R²','Pooled MSE gain %','Worst-period gain %','Global BY q'],[[r['target'],r['predictors'][0],r['family'],pilot.number(r['r2']),pilot.number(100*r['relative_mse_improvement'],2),pilot.number(100*r['worst_period_relative_improvement'],2),pilot.number(r['q_by_global'],5)] for r in failures[:5]])}

## Artist-credit sensitivity

{len(artist)} selected leading relationships were checked with 499 exact-artist-credit
cluster bootstrap replicates, retaining fitted models and the original effect
weighting. Selection was post-hoc; these checks have no new p-values or q-values.
See [all artist checks](full_phase1/artist_sensitivity.csv). The temporal interval
and artist interval are separate sensitivities, not a joint dependence correction.

{pilot.table(['Candidate','Family','Exact credits','Largest credit share','Artist interval','Training-seen artist share'],[[r['candidate_id'],r['family'],r['artist_credits'],pilot.number(r['largest_credit_song_share'],3),'['+', '.join(pilot.number(v) for v in r['interval'])+']',pilot.number(r.get('evaluation_songs_seen_artist_fraction'),3)] for r in artist[:12]])}

Exact credit strings preserve the dataset's identity convention. Collaborations
and spelling variants can split the same person across clusters. These checks do
not solve all artist dependence, refit uncertainty, temporal dependence or prior
data inspection.

## Eight presentation recommendations

1. Show the numerical pairwise cross-domain example in the first table row, its
   calendar-conditioned null, and its artist sensitivity. Explain why association
   with accumulated metadata is not a debut-time forecast.
2. Show the two categorical cross-domain examples to demonstrate appropriate
   genre/category comparisons without arbitrary integer distances.
3. Compare **{metadata_chart['target']} ← {metadata_chart['predictors'][0]}** against
   its stronger-looking pooled association: outer R² {metadata_chart['r2']:.4f},
   MSE gain {100*metadata_chart['relative_mse_improvement']:.2f}%. Discuss retrospective accumulation.
4. Show **{substantive_genre['target']} ← {substantive_genre['predictors'][0]} × genre**:
   outer R² {substantive_genre['r2']:.4f}, additive R² {substantive_genre['comparison_metrics']['r2']:.4f}.
   Display supported genre slopes, the modest extra gain and all four periods.
5. Show **{best['target']} ← {best['predictors'][0]}** as an example of a large
   baseline improvement with weak absolute performance. Its pooled R² is
   {best['r2']:.4f}, but each individual period has negative R².
6. Use one aggregate/genre-adjusted example above to explain aggregation effects;
   call it a descriptive candidate, not a proven paradox or causal effect.
7. Use the lyric-to-chart null table to explain why extensive search and nonlinear
   flexibility need not produce a useful measure of commercial success.
8. Show the descriptive release-count/love-score sign change between 1990–1999
   and 2018–2025. Discuss coverage and composition; no COVID breakpoint was tested.

The strongest classifier-to-classifier nonlinear curve is a supporting method
demonstration only. Its predictive performance is not an independent musical discovery.

The {len(engine.read_json(PUBLIC/'figure_index.json'))} [selected figures](full_phase1/figure_index.json) are generated from saved
curves, replayed fitted predictions and recorded subgroup statistics. The
[classroom demo](full_phase1/README.md) exposes complete results, cross-domain
filters, actual effect sizes, uncertainty and warnings.

## Limitations and next work

The sample is Billboard-charting songs, not all music. Missing lyrics/enrichment,
linked-metadata coverage, changing genre composition and classifier measurement
error can all shape associations. Counts and whole-career outcomes can encode
exposure and retrospective accumulation. Whole-window purging removes boundary-
crossing and ongoing chart runs, changing cohort composition and potentially
underrepresenting recent long-running hits. Broadly different domains can still
share metadata, artists or classification inputs. No reclassification or dataset changes
were made. Confidence intervals hold selected models fixed and do not include
full model-selection uncertainty. The existing data have been inspected repeatedly.

Prioritize a bounded, explicitly approved follow-up on stable priority cross-domain and
aggregation candidates with stronger artist/time dependence handling and a frozen
replication plan. Historical stratification is a more directly motivated next
step than the very large numeric/threshold interaction universes; choose its
scope and correction family before running. Numeric interactions should require
a separate runtime/statistical design decision. **Neither follow-up was launched.**
'''
    (spec.PUBLIC/'full_phase1_findings.md').write_text(text)


def render():
    started=time.perf_counter();rows=phase.complete_results();views=interpret.rank_views(rows)
    execution=engine.read_json(PUBLIC/'execution.json');summary=summaries(rows);reversals=interpret.reversal_records(rows);period_signs=interpret.period_sign_records(rows);nulls=null_summaries(rows)
    for family in phase.FAMILIES:write_csv(PUBLIC/(family+'_results.csv.gz'),[flatten(r) for r in rows if r['family']==family])
    for name,group in views.items():write_csv(PUBLIC/(name+'_leaderboard.csv.gz'),[dict(rank=i+1,**flatten(r)) for i,r in enumerate(group)])
    write_csv(PUBLIC/'sign_reversals_and_attenuation.csv.gz',reversals)
    write_csv(PUBLIC/'period_sign_changes.csv.gz',period_signs)
    write_csv(PUBLIC/'lyric_chart_null_summary.csv',nulls)
    engine.write_json(PUBLIC/'family_summary.json',summary)
    timings=defaultdict(list)
    for row in rows:
        for item in row.get('timings',[]):timings[(item['method'],item['phase'])].append(item)
    write_csv(PUBLIC/'method_throughput.csv',[dict(method=method,phase=stage,fit_calls=len(items),
        total_fit_seconds=sum(t['seconds'] for t in items),median_fit_seconds=float(np.median([t['seconds'] for t in items])))
        for (method,stage),items in sorted(timings.items())])
    engine.write_json(PUBLIC/'selected_method_counts.json',dict(Counter(f['selected_method'] for r in rows if r['family']=='nonlinear' for f in r['folds'] if f['status']=='ok')))
    shortlist={r['candidate_id']:r for r in [*views['cross_shortlist'],*views['nonlinear'][:10],*views['genre_interaction'][:10]]}
    # These are bounded diagnostic replays of already tested candidates, not a new search.
    cache=phase.LOCAL/'presentation_sensitivity.json.gz'
    identity=engine.old.digest([engine.old.original.sha(ROOT/'src/relationship_phase1_analysis.py'),
        sorted(shortlist),engine.old.digest(engine.read_json(PUBLIC/'protocol.json')['identity'])])
    if cache.exists():
        saved=json.loads(gzip.decompress(cache.read_bytes()))
        if saved['identity']!=identity:raise ValueError('Artist sensitivity selection/source changed; use an explicit new cache version')
    else:
        t=time.perf_counter();frame=engine.data();masks=engine.models.make_splits(frame)
        artist,plots,fit_calls=interpret.artist_sensitivity(list(shortlist.values()),frame,masks)
        saved=dict(identity=identity,artist=artist,plots=plots,fit_calls=fit_calls,seconds=time.perf_counter()-t)
        write_gzip(cache,saved)
    # Bounded diagnostic replays: no search or model selection is repeated.
    extra=list(substantive_examples(views));extra_cache=phase.LOCAL/'substantive_sensitivity_v1.json.gz'
    extra_identity=engine.old.digest([engine.old.original.sha(ROOT/'src/relationship_phase1_analysis.py'),
        [r['candidate_id'] for r in extra],engine.old.digest(engine.read_json(PUBLIC/'protocol.json')['identity'])])
    if extra_cache.exists():
        extra_saved=json.loads(gzip.decompress(extra_cache.read_bytes()))
        if extra_saved['identity']!=extra_identity:raise ValueError('Substantive sensitivity identity changed')
    else:
        t=time.perf_counter();frame=engine.data();masks=engine.models.make_splits(frame)
        extra_artist,extra_plots,extra_fits=interpret.artist_sensitivity(extra,frame,masks)
        extra_saved=dict(identity=extra_identity,artist=extra_artist,plots=extra_plots,fit_calls=extra_fits,seconds=time.perf_counter()-t)
        write_gzip(extra_cache,extra_saved)
    artist=saved['artist']+extra_saved['artist'];plots={**saved['plots'],**extra_saved['plots']};write_csv(PUBLIC/'artist_sensitivity.csv',artist)
    engine.write_json(PUBLIC/'sensitivity_accounting.json',dict(selected_candidates=len(artist),fit_calls=saved['fit_calls']+extra_saved['fit_calls'],seconds=saved['seconds']+extra_saved['seconds'],identity=identity,substantive_identity=extra_identity,substantive_candidates=[r['candidate_id'] for r in extra]))
    write_gzip(PUBLIC/'selected_plot_data.json.gz',plots)
    # Compact aggregate detail for every result. No lyrics, IDs, caches or fitted databases.
    publish_demo(rows)
    render_figures(views,rows,plots,reversals)
    findings(rows,views,summary,reversals,period_signs,nulls,artist,execution)
    engine.write_json(PUBLIC/'render_accounting.json',dict(status='PASS',candidates=len(rows),render_seconds=time.perf_counter()-started,
        public_result_bytes=sum(p.stat().st_size for p in PUBLIC.rglob('*.gz')),peak_rss_bytes=engine.peak_rss_bytes(),
        source_commit=engine.read_json(PUBLIC/'protocol.json')['identity']['source_commit']))
    digest_manifest()
    print(json.dumps(dict(candidates=len(rows),summary=summary,artist_checks=len(artist),seconds=time.perf_counter()-started),indent=2))


if __name__=='__main__':render()
