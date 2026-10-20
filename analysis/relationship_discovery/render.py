"""Render only the measured pilot, transparent rankings, estimates and figures."""
from collections import Counter,defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import relationship_discovery as engine
import relationship_discovery_spec as spec

PUBLIC=spec.PUBLIC
INFERENTIAL={'pairwise','nonlinear','genre_interaction','numeric_interaction','threshold_interaction'}
PREDICTIVE=INFERENTIAL-{'pairwise'}


def table(headers,rows):
    def cell(x):return str(x).replace('|','\\|').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(cell(v) for v in r)+' |' for r in rows])


def number(x,digits=4):return '—' if x is None else f'{x:.{digits}f}'


def read_results():
    plain=PUBLIC/'pilot_results/results.json'
    if plain.exists():return engine.read_json(plain)
    return json.loads(gzip.decompress((PUBLIC/'pilot_results/results.json.gz').read_bytes()))


def flat(row):
    keep=['candidate_id','family','target','predictors','conditioner','category','circular_rules','pure_cross_domain',
          'status','n','n_missing','effect','effect_name','ci_low','ci_high','r2','mae','rmse','baseline_rmse','baseline_mae',
          'skill','relative_mse_improvement','mean_period_relative_improvement','worst_period_relative_improvement',
          'stability_fraction','evaluated_periods','blocks','p_value','q_by_global','q_by_family','multiple_testing_status',
          'pearson','spearman','mutual_information_nats','distance_correlation','distance_correlation_n',
          'knn_mutual_information_nats','knn_mutual_information_n','minimum_group_n','group_coverage_warning',
          'primary_test','primary_statistic_name','primary_statistic','p_resolution','comparison',
          'family_tags','leakage_warning','inference_warning','uncertainty_warning','independent_confirmation',
          'evaluation_label','fit_count','wall_seconds','peak_rss_bytes','method','k','quantile','stability_metric']
    result={k:row.get(k) for k in keep}
    name=row['target']
    result['target_units']='months since 1970-01' if name in {'first_snapshot_month','last_snapshot_month'} else 'days since 1970-01-01' if name in spec.old.original.DATES else 'calendar year' if name=='mb_release_year' else 'classifier score' if name in spec.old.original.SCORES else 'seconds' if name in spec.old.original.DURATIONS else 'named count/rank/category or panel'
    if row.get('effect_interval',{}).get('interval'):
        result['ci_low'],result['ci_high']=row['effect_interval']['interval']
    return result


def stat_key(row):
    return (row.get('q_by_global') if row.get('q_by_global') is not None else 2.,
            -(row.get('stability_fraction') or 0),row['candidate_id'])


def improvement_key(row):
    return (-(row.get('ci_low') if row.get('ci_low') is not None else -float('inf')),
            -(row.get('effect') if row.get('effect') is not None else -float('inf')),row['candidate_id'])


def result_table(rows):
    return table(['Target','Predictor(s); condition','Category','Effect','95% block interval','Outer R²','Global BY q','Positive periods'],
        [[r['target'],' + '.join(r['predictors'])+('; '+r['conditioner'] if r['conditioner'] else ''),r['category'][0],
          number(r.get('effect')),f"[{number(r.get('ci_low'))}, {number(r.get('ci_high'))}]",number(r.get('r2')),
          number(r.get('q_by_global')),number(r.get('stability_fraction'),2)] for r in rows])


def benchmarks(rows,space):
    counts={name:space[name]['candidates'] for name in ['pairwise','nonlinear','genre_interaction','numeric_interaction','threshold_interaction']}
    counts['temporal']=space['temporal']['pairs'];counts['structure']=None
    records=[];timings=defaultdict(list)
    for row in rows:
        for t in row.get('timings',[]):timings[t['method']].append(t)
    method_rows=[dict(method=name,fit_calls=len(ts),total_fit_seconds=sum(t['seconds'] for t in ts),
        fits_per_second=len(ts)/sum(t['seconds'] for t in ts),median_seconds=float(np.median([t['seconds'] for t in ts])),
        mean_training_n=float(np.mean([t['n_train'] for t in ts]))) for name,ts in sorted(timings.items())]
    for family in sorted(counts):
        selected=[r for r in rows if r['family']==family]
        elapsed=sum(r['wall_seconds'] for r in selected);n=len(selected)
        full=counts[family]
        factor=(full/n) if full else 360/sum(r['fit_count'] for r in selected)
        if family=='structure':factor*=1.25 # Larger k/rank grid; explicitly a rough allowance.
        sizes=[len(json.dumps(r,separators=(',',':')).encode()) for r in selected]
        records.append(dict(family=family,pilot_candidates=n,pilot_seconds=elapsed,candidates_per_second=n/elapsed,
            pilot_fit_calls=sum(r.get('fit_count',0) for r in selected),proposed_candidates=full,
            estimated_serial_seconds=elapsed*factor,conservative_budget_seconds=elapsed*factor*2,
            detailed_uncompressed_bytes_estimate=int(sum(sizes)*factor),
            extrapolation='mean measured cost per candidate, same resampling counts; factor-two planning margin, not a confidence interval' if full else '360 proposed model/stability fits, scaled from pilot, plus 25% allowance for larger k'))
    engine.write_csv(PUBLIC/'benchmark_results/family_throughput.csv',records)
    engine.write_csv(PUBLIC/'benchmark_results/method_throughput.csv',method_rows)
    total=sum(r['estimated_serial_seconds'] for r in records)
    summary=dict(families=records,total_estimated_serial_seconds=total,conservative_budget_seconds=2*total,
        proposed_predictive_fit_upper_bound=space['total_proposed_predictive_model_fits_upper_bound'],
        proposed_structure_fits=360,total_proposed_fit_upper_bound=space['total_proposed_predictive_model_fits_upper_bound']+360,
        detailed_uncompressed_bytes_estimate=sum(r['detailed_uncompressed_bytes_estimate'] for r in records),
        peak_single_process_rss_bytes=max(r['peak_rss_bytes'] for r in rows),
        inference_precision_warning='Estimates retain pilot resampling counts. Adequate full-search Monte Carlo precision and null calibration can cost substantially more; these are not guaranteed full-inference runtimes.',
        parallel=engine.read_json(PUBLIC/'benchmark_results/parallel.json') if (PUBLIC/'benchmark_results/parallel.json').exists() else None)
    engine.write_json(PUBLIC/'benchmark_results/summary.json',summary)
    return summary


def figures(rows,nonlinear,conditional,temporal):
    folder=PUBLIC/'pilot_results/figures';folder.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'svg.hashsalt':'cmpt491-discovery-pilot-v2'})
    # Examples follow published ranking rules; all underlying candidates remain available.
    choices=[r for r in nonlinear if (r.get('r2') or 0)>0]
    selected=choices[0] if choices else nonlinear[0]
    detail=next(r for r in rows if r['candidate_id']==selected['candidate_id'])
    diag=detail['diagnostics'][-1]
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    ax.plot(diag['x'],diag['linear'],label='OLS',color='#777777')
    ax.plot(diag['x'],diag['nonlinear'],label=diag['selected_method'],color='#2166ac')
    ax.set(xlabel=selected['predictors'][0],ylabel=selected['target'],title=f"Training-fitted curves for {diag['period'][0]}–{diag['period'][1]-1} evaluation")
    ax.legend();fig.savefig(folder/'nonlinear.svg',metadata={'Date':None});plt.close(fig)
    selected=conditional[0];detail=next(r for r in rows if r['candidate_id']==selected['candidate_id'])
    folds=[f for f in detail['folds'] if f['status']=='ok']
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained');ax.axhline(0,color='#888888',linewidth=1)
    ax.bar([f"{f['period'][0]}–{f['period'][1]-1}" for f in folds],[100*f['relative_mse_improvement'] for f in folds],color='#2c7f70')
    ax.set(ylabel='MSE reduction versus additive model (%)',title=selected['target']+' | '+selected['family'])
    fig.savefig(folder/'conditional.svg',metadata={'Date':None});plt.close(fig)
    global2020=[r for r in temporal if r['genre']=='All genres' and r['breakpoint']==2020 and r['category'][0]=='C']
    selected=global2020[0] if global2020 else temporal[0]
    detail=next(r for r in rows if r['candidate_id']==selected['parent_candidate_id'])
    ann=[r for r in detail['annual'] if r['genre']=='All genres']
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained');ax.plot([r['year'] for r in ann],[r['rho'] for r in ann],color='#2166ac')
    for point in spec.BREAKPOINTS:ax.axvline(point,color='#b44b4b' if point==2020 else '#bbbbbb',linestyle='--',linewidth=1)
    ax.set(xlabel='Debut year',ylabel='Within-year Spearman rho',title=detail['target']+' versus '+detail['predictors'][0]);ax.axhline(0,color='#777777',linewidth=.7)
    fig.savefig(folder/'historical.svg',metadata={'Date':None});plt.close(fig)
    structure=next(r for r in rows if r['family']=='structure' and r['target']=='all_lyrics' and r['method']=='pca' and r['k']==5)
    last=structure['folds'][-1];load=np.array(last['loadings']);order=np.argsort(np.abs(load[0]))[-12:]
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained');ax.barh([structure['predictors'][i] for i in order],load[0,order],color='#6a51a3')
    ax.set(xlabel='Standardized-variable loading',title='First data-fitted component: all lyric scores, pre-2018 training')
    fig.savefig(folder/'pca_loadings.svg',metadata={'Date':None});plt.close(fig)
    # Matplotlib emits trailing whitespace inside SVG paths; normalize text only.
    for path in folder.glob('*.svg'):
        path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')


def render():
    rows=read_results();space=engine.read_json(PUBLIC/'search_space.json');inventory=[flat(r) for r in rows]
    expanded=dict(marginal_pair_group_cells=space['conditional_correlations']['pair_group_cells'],
        crossed_genre_period_cells=space['temporal']['pairs']*space['temporal']['strata']*len(spec.PERIODS),
        unadjusted_annual_cells=space['temporal']['annual_estimates'],
        additional_genre_adjusted_global_annual_cells=space['temporal']['pairs']*68,
        additional_genre_adjusted_global_breakpoint_cells=space['temporal']['pairs']*len(spec.BREAKPOINTS),
        continuous_pair_knn_mi_estimations=sum(1 for a,b in __import__('itertools').combinations(spec.VARIABLES,2) if spec.kind(a)==spec.kind(b)=='continuous'),
        note='Counts are bounds before coverage/variation exclusions; crossed and genre-adjusted diagnostics supplement the compact audit. No new candidates are fitted.')
    engine.write_json(PUBLIC/'expanded_workload.json',expanded)
    engine.write_csv(PUBLIC/'relationship_inventory.csv',inventory)
    eligible=[r for r in inventory if r['category'][0]!='A' and r['family'] in INFERENTIAL]
    statistical=sorted(eligible,key=stat_key);cross=sorted([r for r in eligible if r['category'][0]=='C'],key=stat_key)
    nonlinear=sorted([r for r in eligible if r['family']=='nonlinear'],key=improvement_key)
    conditional=sorted([r for r in eligible if r['family'] in PREDICTIVE-{'nonlinear'}],key=improvement_key)
    stable=sorted([r for r in eligible if r['family'] in PREDICTIVE and r['evaluated_periods']==4],
        key=lambda r:(-r['worst_period_relative_improvement'],-r['stability_fraction'],r['candidate_id']))
    for name,records in [('discovery',statistical),('cross_domain',cross),('nonlinear',nonlinear),('conditional',conditional),('stable',stable)]:
        engine.write_csv(PUBLIC/(name+'_leaderboard.csv'),[dict(rank=i+1,**r) for i,r in enumerate(records)])
    temporal=[]
    for r in rows:
        if r['family']!='temporal':continue
        for c in r['breakpoints']:
            peers=[v for v in r['breakpoints'] if v['genre']==c['genre'] and v['adequate']]
            item=dict(parent_candidate_id=r['candidate_id'],candidate_id=hashlib.sha256((r['candidate_id']+c['genre']+str(c['breakpoint'])).encode()).hexdigest()[:20],
                target=r['target'],predictors=r['predictors'],category=r['category'],**c,
                multiple_testing_status='descriptive only; no certified p or q',independent_confirmation=False)
            if c['adequate']:
                item['absolute_change_rank_among_available_placebos']=1+sum(abs(v['effect'])>abs(c['effect']) for v in peers)
                item['available_placebos']=len(peers)
            temporal.append(item)
    engine.write_csv(PUBLIC/'pilot_results/temporal_comparisons.csv',temporal)
    temporal_ranked=sorted([r for r in temporal if r['adequate'] and r['category'][0]!='A'],key=lambda r:(-abs(r['effect']),r['candidate_id']))
    engine.write_csv(PUBLIC/'temporal_leaderboard.csv',[dict(rank=i+1,**r) for i,r in enumerate(temporal_ranked)])
    benchmark=benchmarks(rows,space)
    figures(rows,nonlinear,conditional,temporal_ranked)
    engine.write_json(PUBLIC/'pilot_results/ranking_policy.json',dict(statistical='non-A inferential candidates: global BY q, then stability, then fixed ID; no cross-unit effect magnitude tie-break',
        cross_domain='same rule restricted to strict C',nonlinear_conditional='lower block improvement bound, then measured improvement, then ID',
        stable='four complete periods: worst-period relative MSE improvement, then positive-period fraction, then ID',
        temporal='non-A adequately covered prespecified comparisons: absolute annual Fisher-z contrast; descriptive only',weighted_novelty_score=False))
    fullrows=[]
    for family in ['pairwise','nonlinear','genre_interaction','numeric_interaction','threshold_interaction','temporal','structure']:
        if family=='temporal':full=space['temporal']['breakpoint_comparisons'];fits='337,212 rolling + 1,910,868 annual estimates'
        elif family=='structure':full='3 panels × (3 PCA ranks + 4 cluster counts)';fits='360 fits including stability refits'
        else:full=space[family]['candidates'];fits=space[family].get('fit_upper_bound',space[family].get('nested_fit_upper_bound','2,775 primary permutation tests'))
        fullrows.append([family,format(full,',') if isinstance(full,int) else full,format(fits,',') if isinstance(fits,int) else fits,space['pilot_counts'][family]])
    (PUBLIC/'search_space.md').write_text(f'''# Finite search space

Only the **137-candidate pilot** has run. Counts below are exhaustive proposed
universes, including reconstruction controls. The existing 59-target OLS campaign
is unchanged. This design has 57 cardinal song-level targets, 57 cardinal
predictors per pool (self removed per task), one ordinal measurement and 17 nominal
encodings: 75 variables. Observation-level extensions are explicitly deferred.

{table(['Family','Proposed candidates/comparisons','Maximum fits or estimates','Pilot candidates'],fullrows)}

Numeric pair counts: 1,596 cardinal–cardinal plus 57 ordinal–cardinal;
986 numerical/ordinal–categorical and 136 categorical–categorical pairs.
The pairwise methods total 8,799 statistics (1,596 Pearson, 1,653 Spearman,
2,775 MI, 1,653 capped distance correlations, 986 eta-squared and 136 Cramér V),
plus 990 continuous-variable kNN MI diagnostics on capped hash samples. There is one primary test
per pair, not an uncorrected claim for each method.

For p=57 cardinal variables, univariate directed pairs are p(p−1)=3,192.
Product interactions are p×choose(p−1,2)=87,780. Threshold interactions are
p(p−1)(p−2)×3=526,680 because the threshold conditioner is directional.
Genre conditioning adds 3,192 models. Four outer periods, two inner periods
and nine univariate methods give an upper bound of 80 fits per nonlinear
candidate; fixed conditional alternatives need at most eight fits per candidate.

The proposed predictive total is **5,196,576 fits**; adding the proposed 360
multivariate fit/stability calls gives **5,196,936**. There are **623,619 proposed
primary inferential hypotheses**, before any separately approved temporal tests.
A marginal descriptive subgroup scope contains 38,019 pair/group cells.
The implemented temporal family additionally crosses genre and period, giving
196,707 pair × genre × period cells in the full proposed grid (1,785 in this
pilot). Its 1,910,868 unadjusted annual estimates are supplemented by 112,404
global genre-adjusted annual estimates and 8,265 genre-adjusted breakpoint
contrasts. These diagnostics do not create certified additional p-values.
See [expanded_workload.json](expanded_workload.json) for these exact bounds. The optional
full numeric-threshold subgroup grid would add 1,053,360 cells and is counted
separately from model fits. Temporal comparisons span 1,653 numerical/ordinal
pairs × 17 strata × 5 breakpoints. Rolling windows overlap and are not independent
tests. PCA ranks share decompositions in the proposed efficient implementation.

The threshold-triple family is the main combinatorial bottleneck. No heuristic
screening is substituted for these counts. Approving only a predefined family
(e.g. univariate nonlinear plus genre interactions) is a transparent scope
choice; approving every threshold triple is a substantially larger campaign.

Runtime estimates retain pilot resampling settings. Full-search inference may
need much finer Monte Carlo resolution: an isolated rejection under global BY
at q=.05 across 623,619 hypotheses would require a p-value around
{.05/(623619*sum(1/i for i in range(1,623620))):.2g}. Pilot permutation/sign-flip
resolution cannot support that isolated-tail guarantee. Many simultaneous
rejections change the step-up threshold, but do not remove the need for a
predeclared precision and null-calibration plan. Approve inference design and
budget before launching a full search.
''')
    good_nonlin=[r for r in nonlinear if r.get('r2') is not None and r['r2']>0]
    genre=[r for r in conditional if r['family']=='genre_interaction']
    products=[r for r in conditional if r['family']=='numeric_interaction']
    thresholds=[r for r in conditional if r['family']=='threshold_interaction']
    historic=[r for r in temporal_ranked if r['genre']=='All genres' and r['breakpoint']==2020 and r['category'][0]=='C']
    historical_table=table(['Target','Predictor','2020 contrast','95% descriptive interval','Genre-adjusted contrast','Magnitude rank among placebos'],
        [[r['target'],' + '.join(r['predictors']),number(r['effect']),f"[{number(r['ci_low'])}, {number(r['ci_high'])}]",number(r.get('genre_adjusted_change')),str(r['absolute_change_rank_among_available_placebos'])+'/'+str(r['available_placebos'])] for r in historic[:5]])
    pair=[r for r in inventory if r['family']=='pairwise' and r['category'][0]!='A']
    structure=[r for r in rows if r['family']=='structure']
    inferential=[r for r in rows if r['family'] in INFERENTIAL]
    significant=[r for r in inferential if r.get('q_by_global',1)<=.05]
    summary=dict(status='EXPLORATORY PILOT',candidates=len(rows),primary_hypotheses=len(inferential),category_counts=dict(Counter(r['category'][0] for r in rows)),
        exploratory_global_by_passes=len(significant),non_A_global_by_passes=sum(r['category'][0]!='A' for r in significant),
        independently_confirmed=0,full_campaign_launched=False,pilot_fit_calls=sum(r.get('fit_count',0) for r in rows),
        adequate_temporal_comparisons=sum(r['adequate'] for r in temporal),all_temporal_comparisons=len(temporal),
        benchmark=benchmark,top_nonlinear_ids=[r['candidate_id'] for r in nonlinear[:5]],
        positive_r2_nonlinear_example_ids=[r['candidate_id'] for r in good_nonlin[:5]],top_conditional_ids=[r['candidate_id'] for r in conditional[:5]],
        top_cross_domain_ids=[r['candidate_id'] for r in cross[:5]])
    engine.write_json(PUBLIC/'pilot_results/summary.json',summary)
    (PUBLIC/'pilot_results/findings.md').write_text(f'''# Measured exploratory pilot findings

**No independent confirmation is claimed.** All {len(rows)} outcome-blind pilot
candidates were evaluated. There were {summary['pilot_fit_calls']:,} fits, including
inner selection and multivariate stability refits. The global BY family contains
{len(inferential)} attempted primary hypotheses; {len(significant)} have exploratory
q≤.05 ({summary['non_A_global_by_passes']} after omitting reconstruction controls).
This conditional-on-assumptions evidence is not a count of confirmed scientific
discoveries. Historical and latent-structure results are descriptive.

## Nonlinear improvements

Effects below are equal-calendar-block loss reductions divided by training target
variance. R² is pooled across held-out song rows. A positive improvement can
coexist with poor absolute prediction. The complete ranking retains those failures.

{result_table(nonlinear[:5])}

Examples with positive outer R², selected mechanically from that same ranking:

{result_table(good_nonlin[:5])}

The first table is deliberately retained: a nonlinear fit can beat a badly
extrapolating linear calendar model while remaining unusable. This is why the
leaderboards expose absolute performance, baseline improvement, interval, q and
period stability separately. A curve alone does not establish a useful prediction.

## Conditional and genre interactions

{result_table(conditional[:6])}

Genre-specific slope examples:

{result_table(genre[:4])}

Numeric-product examples:

{result_table(products[:3])}

Threshold-conditioned examples (all three training quantiles retained):

{result_table(thresholds[:3])}

These gains compare against additive models with the same inputs. Same-family B
relationships can still be informative about classifier agreement but are not
independent content measurements. Numeric product and threshold effects are also
retained when weak or negative. All prespecified subgroup coverage, partial rank
correlations and sign reversals are in the compressed complete results; an
individual subgroup sign flag has no separate corrected significance claim.

## Cross-domain evidence

This is ordered by global BY q and stability, not by a weighted novelty score.
Effect scales differ between pairwise and predictive families.

{result_table(cross[:8])}

C means different documented information domains. It does not guarantee different
source material, historical availability, causal direction or usefulness. In
particular, tiny improvements and negative R² remain visible even when a
block-based test yields a small exploratory q-value.

## Pairwise agreement and disagreement

{table(['Target','Predictor','Pearson','Spearman','Binned MI (nats)','Distance correlation (≤512 songs)','Year-conditioned BY q'],
 [[r['target'],' + '.join(r['predictors']),number(r.get('pearson')),number(r.get('spearman')),number(r.get('mutual_information_nats')),number(r.get('distance_correlation')),number(r.get('q_by_global'))] for r in sorted(pair,key=stat_key)[:8]])}

Metrics have different scales and different sensitivity to shape, ties and sample
size. A large pooled date association can disappear under the within-year
permutation null: it mostly encodes historical placement. Binned MI and capped
distance correlation are descriptive diagnostics, not extra uncorrected tests.

## Historical relationships and 2020 placebos

{historical_table}

Each row compares exactly five annual correlations on each side. Rank 1 means
largest magnitude among available prespecified breakpoints; it is **not a
p-value**. The other breakpoints are 1980, 1990, 2000 and 2010. All
{len(temporal):,} planned pair/genre/breakpoint cells remain recorded;
{summary['adequate_temporal_comparisons']:,} meet the sample/year requirements.
There are only five annual observations per side, so intervals are descriptive
and no breakpoint is called significant or causal. Genre adjustment removes
within-year group intercepts only; it does not remove every compositional change.

## Multivariate structure

{table(['Panel','Method','k','Mean held-out reconstruction/distortion fraction','Mean minimum block-refit stability','Stability metric'],
 [[r['target'],r['method'],r['k'],number(r.get('effect')),number(r.get('stability_fraction')),r['stability_metric']] for r in structure])}

PCA loadings and clustering profiles are fitted from real scores. Different k
values use different complexity and are not selected using these outer results.
The fixed panels include related outputs and sentiment closure; latent dimensions
are not new ground-truth musical qualities. Three stability resamples per fold
are useful diagnostics, not precise uncertainty estimates.

## Classroom figures

- [Linear versus nonlinear curves](figures/nonlinear.svg)
- [Conditional improvement by evaluation period](figures/conditional.svg)
- [Annual historical association and placebo dates](figures/historical.svg)
- [Actual PCA loadings](figures/pca_loadings.svg)

All figures are generated from saved measured results. The interactive demo adds
target/family selection, genre and period views, sample sizes and warnings. It
never launches a search when a plot is selected.
''')
    (PUBLIC/'benchmark_results/README.md').write_text(f'''# Measured performance and bounded extrapolation

{table(['Family','Pilot candidates','Measured seconds','Candidates/s','Estimated full serial minutes','Factor-two budget minutes','Detailed uncompressed GB'],
 [[r['family'],r['pilot_candidates'],number(r['pilot_seconds'],2),number(r['candidates_per_second'],2),number(r['estimated_serial_seconds']/60,1),number(r['conservative_budget_seconds']/60,1),number(r['detailed_uncompressed_bytes_estimate']/1e9,2)] for r in benchmark['families']])}

Combined point estimate: **{benchmark['total_estimated_serial_seconds']/3600:.2f} hours**;
factor-two planning allowance: **{benchmark['conservative_budget_seconds']/3600:.2f} hours**.
These are extrapolations from a small domain-stratified pilot, not measured full
campaign times. They retain pilot resampling precision; calibrated full-search
inference can require substantially more work. Sample size, knots, categories,
conditioning dimensions and BLAS implementation affect throughput.

Measured peak resident memory for the single-process pilot was
**{benchmark['peak_single_process_rss_bytes']/1024**2:.1f} MiB** (process-lifetime high
water mark, not incremental model memory). A two-worker run has separate data
copies; summing worker peaks is an upper-bound estimate rather than a measured
simultaneous aggregate peak. Read [parallel.json](parallel.json) for the actual
one-versus-two-worker microbenchmark, including startup. It is too small to
promise linear scaling. BLAS is capped at one thread per worker.

[Method throughput](method_throughput.csv) measures all nine univariate alternatives,
additive/interaction fits, PCA and k-means/refits. Candidate timings include the
associated statistics and resampling. Proposed detailed uncompressed diagnostics
would occupy approximately **{benchmark['detailed_uncompressed_bytes_estimate']/1e9:.2f} GB**
if retained at the pilot's density; compact summaries and compressed diagnostics
are much smaller. Model databases or row-level predictions are not committed.

A future full runner should batch pair statistics, reuse design/fold caches,
checkpoint atomic candidate records with input/code hashes, and avoid writing
repeated subgroup metadata. That engineering can improve performance without
screening away candidates. The current CLI deliberately cannot run the full grid.
''')
    # Lossless compact publication; keep all measured aggregate diagnostics, no song identities.
    compressed=gzip.compress(json.dumps(rows,sort_keys=True,separators=(',',':'),allow_nan=False).encode(),mtime=0)
    (PUBLIC/'pilot_results/results.json.gz').write_bytes(compressed)
    if (PUBLIC/'pilot_results/results.json').exists():(PUBLIC/'pilot_results/results.json').unlink()
    refresh_manifest()


def refresh_manifest():
    paths=[p for p in PUBLIC.rglob('*') if p.is_file() and p.name!='artifact_manifest.json' and '__pycache__' not in str(p)]
    paths += [ROOT/p for p in [*spec.CODE,'src/relationship_demo.py','requirements-discovery.txt','tests/test_relationship_discovery.py','tests/test_relationship_demo.py'] if (ROOT/p).exists()]
    engine.write_json(PUBLIC/'artifact_manifest.json',dict(scope='Bounded exploratory discovery pilot; no original analysis modified',
        sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}))


if __name__=='__main__':render()
