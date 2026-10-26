"""Render measured findings and standalone SVG figures from saved campaign tables."""
from __future__ import annotations
from pathlib import Path
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from feature_expansion_common import ROOT,PUBLIC,DATA,LOCAL,CONFIG,sha,read_json,write_json,write_csv,atomic_bytes

LABELS={'top10':'Top 10','long_chart':'13+ chart weeks','best_rank':'Best rank','chart_weeks':'Chart weeks','chart_points':'Chart points'}
COLORS={'baseline':'#59768e','new_only':'#db9143','combined':'#257b68'}


def markdown(frame,formats=None):
    formats=formats or {};rows=[]
    for row in frame.itertuples(index=False,name=None):
        cells=[]
        for col,v in zip(frame.columns,row):
            if pd.isna(v):s='—'
            elif col in formats:s=formats[col].format(v)
            elif isinstance(v,(float,np.floating)):s=f'{v:.4f}'
            else:s=str(v)
            cells.append(s.replace('|','/').replace('\n',' '))
        rows.append('| '+' | '.join(cells)+' |')
    return '\n'.join(['| '+' | '.join(frame.columns)+' |','|'+'|'.join(['---']*len(frame.columns))+'|']+rows)


def save_text(path,text):atomic_bytes(path,(textwrap.dedent(text).strip()+'\n').encode())


def save_figure(fig,name):
    path=PUBLIC/'figures'/name;path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format='svg',bbox_inches='tight',metadata={'Date':None})
    # Matplotlib leaves spaces before path-data newlines. Normalize serialization
    # without changing SVG coordinates or the rendered figure.
    atomic_bytes(path,('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n').encode())
    previews=LOCAL/'figure_previews';previews.mkdir(parents=True,exist_ok=True)
    fig.savefig(previews/(Path(name).stem+'.png'),dpi=130,bbox_inches='tight');plt.close(fig)


def render():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'feature-expansion-v1'})
    selected=pd.read_csv(PUBLIC/'selected_models.csv');all_metrics=pd.read_csv(PUBLIC/'model_comparison.csv')
    results=all_metrics.merge(selected[['track','target','configuration','method']],on=['track','target','configuration','method'],validate='many_to_one')
    test=results[results.partition.eq('test')];audit=read_json(PUBLIC/'feature_build_audit.json');importance=pd.read_csv(PUBLIC/'permutation_importance.csv');ablation=pd.read_csv(PUBLIC/'feature_ablation.csv')
    uncertainty=pd.read_csv(PUBLIC/'uncertainty.csv');coverage=pd.read_csv(PUBLIC/'coverage_report.csv');history=pd.read_csv(PUBLIC/'historical_sensitivity.csv');periods=pd.read_csv(PUBLIC/'test_period_metrics.csv')
    generalization=[]
    for keys,g in all_metrics.groupby(['track','target','configuration','method'],sort=True):
        metric='balanced_accuracy' if keys[1] in ['top10','long_chart'] else 'r2';v=g.set_index('partition')[metric]
        generalization.append(dict(zip(['track','target','configuration','method'],keys),metric=metric,train=v['train'],validation=v['validation'],test=v['test'],test_minus_train=v['test']-v['train'],test_minus_validation=v['test']-v['validation']))
    write_csv(PUBLIC/'generalization_gaps.csv',generalization)
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for i,track in enumerate(['strict','retrospective']):
        for j,target in enumerate(['top10','long_chart']):
            ax=axes[i,j];s=test[(test.track==track)&(test.target==target)].set_index('configuration').loc[CONFIG['configurations']]
            bars=ax.bar(['Baseline','New only','Combined'],s.balanced_accuracy,color=[COLORS[c] for c in s.index]);ax.axhline(.5,color='#555',ls='--',lw=1)
            ax.bar_label(bars,fmt='%.3f',padding=3);ax.set(ylim=(0,1),ylabel='Balanced accuracy',title=f'{track.title()} · {LABELS[target]} · n={int(s.n.iloc[0]):,}')
    fig.suptitle('Exploratory 2018-onward evaluation · 26-week outcomes',fontsize=14);save_figure(fig,'classification_comparison.svg')
    fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
    for i,track in enumerate(['strict','retrospective']):
        for j,target in enumerate(['best_rank','chart_weeks','chart_points']):
            ax=axes[i,j];s=test[(test.track==track)&(test.target==target)].set_index('configuration').loc[CONFIG['configurations']];ratios=s.mae/s.loc['baseline','mae']
            bars=ax.bar(['Baseline','New only','Combined'],ratios,color=[COLORS[c] for c in s.index]);ax.axhline(1,color='#555',ls='--',lw=1)
            ax.bar_label(bars,labels=[f'MAE {v:.2f}' for v in s.mae],padding=3,fontsize=9);ax.set(ylim=(0,max(1.2,ratios.max()+.2)),ylabel='MAE / eligible baseline MAE',title=f'{track.title()} · {LABELS[target]}')
    fig.suptitle('Numerical prediction error · lower is better',fontsize=14);save_figure(fig,'regression_comparison.svg')
    fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained')
    for ax,track in zip(axes,['strict','retrospective']):
        s=importance[(importance.track==track)&importance.target.eq('top10')&~importance.group.isin(['existing_scores','debut_rank','primary_genre','duration_seconds'])].nlargest(10,'mean_drop').sort_values('mean_drop')
        ax.barh(s.feature.str.replace('_',' '),100*s.mean_drop,color=COLORS['combined']);ax.axvline(0,color='#555',lw=1);ax.set(title=track.title(),xlabel='Balanced-accuracy loss (percentage points)')
    fig.suptitle('New features ranked by validation permutation importance · Top 10',fontsize=14);save_figure(fig,'top10_new_feature_importance.svg')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for ax,target in zip(axes,['top10','long_chart']):
        for config in CONFIG['configurations']:
            s=periods[(periods.track=='strict')&periods.target.eq(target)&periods.configuration.eq(config)].sort_values('period')
            ax.plot(s.period,s.balanced_accuracy,marker='o',label=config.replace('_',' '),color=COLORS[config])
        ax.axhline(.5,color='#555',ls='--',lw=1);ax.set(ylim=(.35,1),ylabel='Balanced accuracy',title=LABELS[target]);ax.legend(frameon=False)
    fig.suptitle('Same fitted strict models across evaluation periods · partial 2026',fontsize=13);save_figure(fig,'evaluation_period_stability.svg')
    calibration=pd.read_csv(PUBLIC/'calibration.csv');fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained')
    for ax,target in zip(axes,['top10','long_chart']):
        for config in CONFIG['configurations']:
            s=calibration[(calibration.track=='strict')&calibration.target.eq(target)&calibration.configuration.eq(config)&calibration.partition.eq('test')]
            ax.plot(s.mean_probability,s.observed_rate,marker='o',label=config.replace('_',' '),color=COLORS[config])
        ax.plot([0,1],[0,1],color='#777',ls='--');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Mean predicted probability',ylabel='Observed event fraction',title=LABELS[target]);ax.legend(frameon=False)
    fig.suptitle('Raw probability calibration · strict evaluation population',fontsize=13);save_figure(fig,'calibration.svg')
    predictions=pd.read_csv(PUBLIC/'selected_predictions.csv.gz');fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for ax,target in zip(axes,['best_rank','chart_weeks','chart_points']):
        s=predictions[predictions.track.eq('strict')&predictions.target.eq(target)&predictions.configuration.eq('combined')&predictions.partition.eq('test')]
        if len(s)>1500:s=s.iloc[np.linspace(0,len(s)-1,1500,dtype=int)]
        ax.scatter(s.actual,s.prediction,s=7,alpha=.25,color=COLORS['combined']);lo=min(s.actual.min(),s.prediction.min());hi=max(s.actual.max(),s.prediction.max());ax.plot([lo,hi],[lo,hi],color='#777',ls='--')
        ax.set(xlabel='Actual (26 weeks)',ylabel='Predicted',title=LABELS[target])
    fig.suptitle('Strict combined models · deterministic evaluation sample · unmodified predictions',fontsize=12);save_figure(fig,'regression_diagnostics.svg')
    write_json(PUBLIC/'figures/manifest.json',dict(renderer_sha256=sha(Path(__file__)),figures={p.name:sha(p) for p in sorted((PUBLIC/'figures').glob('*.svg'))}))
    tables=[]
    for track in ['strict','retrospective']:
        s=test[test.track.eq(track)].copy();s['target']=s.target.map(LABELS)
        tables.append('## '+track.title()+' comparison\n\n'+markdown(s[['target','configuration','method','n','balanced_accuracy','roc_auc','pr_auc','brier','r2','mae','rmse']]))
    improvements=[]
    for track,target in [(a,b) for a in ['strict','retrospective'] for b in LABELS]:
        s=test[(test.track==track)&test.target.eq(target)].set_index('configuration');cls=target in ['top10','long_chart'];metric='balanced_accuracy' if cls else 'mae'
        improvement=s.loc['combined',metric]-s.loc['baseline',metric] if cls else s.loc['baseline',metric]-s.loc['combined',metric]
        improvements.append(dict(track=track,target=target,metric=metric,baseline=s.loc['baseline',metric],new_only=s.loc['new_only',metric],combined=s.loc['combined',metric],improvement=improvement,
            relative_mae_reduction_percent=100*improvement/s.loc['baseline',metric] if not cls else np.nan))
    write_csv(PUBLIC/'incremental_improvements.csv',improvements)
    top=importance[(importance.track=='strict')&importance.target.eq('top10')&~importance.feature.eq('debut_rank')].nlargest(10,'mean_drop')[['feature','group','mean_drop','std_drop']]
    relevant=ablation[ablation.partition.eq('test')].copy()
    limits='''## Interpretation and limits

This is an exploratory evaluation on a previously inspected test population. No model or feature was selected by its final-test result; nevertheless, the campaign is not fresh independent confirmation. Confidence intervals condition on fitted models and omit selection and refit uncertainty. Artist-credit clusters are exact strings, so the same person may occur in several clusters; the year-cluster interval has only nine clusters.

Only the strict track uses historically available predictors. Retrospective comparisons use modern lyric/genre/metadata measurements, and membership in the enriched monthly population is itself determined using later history. Strict and retrospective tracks have different populations and must not be compared as a causal estimate of the value of lyrics. Within each track, A/B/C share exactly the same songs.

Debut rank is already known at the prediction moment. Numerical outcomes include that first chart contribution, which makes part of the target predictable by construction. Top-10 debut songs are excluded from Top-10 classification. Chart points are 101 minus rank summed over source rows, not sales, streams, revenue, or market share. No inference applies to uncharted releases.

The 26-week target handles endpoint censoring but is not complete eventual career success. Long returns and seasonal reentries can occur later. Observed careers before 1958 are unavailable; the 1960 burn-in does not reconstruct them. The final 2026 period is partial. Exact-credit history intentionally splits collaborations and spelling differences. Entity-credit features use unanimous modern recording credits but are still retrospective; first-listed does not prove lead/featured performance roles.

Lyrics retain provider/version/format and language effects. MATTR is missing below 50 tokens. English lexical lists are literal counts, not language detection or psychological labels. A title-equal opening line remains a lyric; only recognized standalone section markers are omitted. Symbolic repeat instructions are not expanded. Missing values are median-imputed from training data; this can still reveal missingness patterns even without explicit indicators. Genre and 42 existing scores are model measurements, not ground truth.

Permutation importance is marginal and can understate correlated predictors. Coefficients, impurity importance and fixed-hyperparameter ablations provide complementary checks; none establish causation. Ablations reselect only the decision threshold on validation data. Raw probabilities are not recalibrated and may be poorly calibrated after historical drift. Negative ablation degradation means removing a group improved that evaluation metric; it is not a new feature-selection instruction.

The historical folds use a prespecified HGB model with its own earlier validation interval. The primary comparison selects among three model families, so historical-fold and primary scores also differ in model-selection procedure. The 12-week sensitivity changes the target (including longevity to at least six weeks), not merely sample size. No COVID breakpoint or causal analysis was performed.
'''
    strict=test[test.track.eq('strict')].set_index(['target','configuration']);retro=test[test.track.eq('retrospective')].set_index(['target','configuration'])
    top_model=strict.loc[('top10','combined')];top_base=strict.loc[('top10','baseline')];rank_model=strict.loc[('best_rank','combined')]
    top_ci=uncertainty[uncertainty.track.eq('strict')&uncertainty.target.eq('top10')&uncertainty.cluster.eq('artist_credit')&uncertainty.quantity.eq('combined_minus_baseline_improvement')].iloc[0]
    narrative=f'''## What improved, and what did not

New information improves **Top-10 discrimination and strict best-rank prediction**, but does not produce reliable forecasting of every chart outcome. The strict combined Top-10 model is regularized logistic regression (C=0.1, validation threshold 0.10): balanced accuracy rises from {top_base.balanced_accuracy:.3f} to {top_model.balanced_accuracy:.3f}, ROC-AUC from {top_base.roc_auc:.3f} to {top_model.roc_auc:.3f}. The paired artist-credit interval for the balanced-accuracy improvement is {100*top_ci.lower:.1f} to {100*top_ci.upper:.1f} percentage points.

This ranking improvement is **not reliable probability calibration**. Only {100*top_model.positive_rate:.2f}% of eligible evaluation songs climb into the Top 10, versus 17.85% in training and 8.90% in validation. Combined precision is {100*top_model.precision:.2f}% at {100*top_model.recall:.1f}% recall. Its Brier score is {top_model.brier:.3f}, worse than the training-prevalence baseline's 0.050. The saved probabilities should be presented as raw model estimates, not dependable hit probabilities.

Strict combined HGB models reduce best-rank MAE from {strict.loc[('best_rank','baseline'),'mae']:.2f} to {rank_model.mae:.2f} (R² {rank_model.r2:.3f}) and chart-week MAE from {strict.loc[('chart_weeks','baseline'),'mae']:.2f} to {strict.loc[('chart_weeks','combined'),'mae']:.2f} (R² {strict.loc[('chart_weeks','combined'),'r2']:.3f}). Chart-point MAE improves versus the rank-only model, but the combined model's {strict.loc[('chart_points','combined'),'mae']:.2f} is worse than the training-median baseline's 411.16. New-only HGB has lower point MAE ({strict.loc[('chart_points','new_only'),'mae']:.2f}) and essentially zero R²; even it does not beat that median baseline on MAE. These are limited improvements, not strong overall commercial-performance prediction.

For **26-week longevity**, adding features hurts the strict comparison: combined HGB balanced accuracy is {strict.loc[('long_chart','combined'),'balanced_accuracy']:.3f} versus {strict.loc[('long_chart','baseline'),'balanced_accuracy']:.3f} for the rank-only logistic model. The new-only logistic model was strongest on validation among the three configurations, but falls to {strict.loc[('long_chart','new_only'),'balanced_accuracy']:.3f} in evaluation. That is substantial historical generalization failure, despite its evaluation ROC-AUC of {strict.loc[('long_chart','new_only'),'roc_auc']:.3f}; its saved validation threshold transfers poorly.

On the common retrospective cohort, combined logistic models improve Top-10 balanced accuracy from {retro.loc[('top10','baseline'),'balanced_accuracy']:.3f} to {retro.loc[('top10','combined'),'balanced_accuracy']:.3f} and longevity from {retro.loc[('long_chart','baseline'),'balanced_accuracy']:.3f} to {retro.loc[('long_chart','combined'),'balanced_accuracy']:.3f}. The Top-10 improvement's artist-credit interval includes zero, and probability calibration worsens. Combined best-rank MAE is worse than baseline ({retro.loc[('best_rank','combined'),'mae']:.2f} versus {retro.loc[('best_rank','baseline'),'mae']:.2f}). Retrospective combined chart-week and chart-point models have negative R² and do not beat the simple training-median MAE baseline. These F-track results cannot be described as historical forecasts.

## Where the information comes from

Chart competition is the strongest source group for the strict Top-10 gain: removing it costs 8.24 balanced-accuracy points, versus 1.59 points for removing artist history. It also accounts for much of the strict numerical error reduction. The highest-ranked new validation feature is the count of **other same-credit songs debuting together**. Its logistic coefficient is negative, as are the coefficients for the number of other new entrants and prior-chart incumbent age. These are conditional model associations; simultaneous debuts are not verified album membership.

Prior attained Top-10 count has a positive coefficient, while prior song count and accumulated weeks have negative conditional coefficients alongside other history measures. Thus, more observed output is not uniformly associated with higher success after controlling for prior hits and chart context. Collinearity makes individual coefficient interpretation fragile; the group ablation is more informative.

The 16 lyric-structure features add little consistent incremental value. Removing the whole group slightly improves retrospective Top-10 balanced accuracy, while its longevity contribution is only 0.74 percentage points. Removing existing 42 lyrical scores costs 1.09 Top-10 points and 0.12 longevity points on that retrospective cohort. Calendar/title features have little stable group benefit; chart weekday is nearly uninformative. Genre and entity-credit history help some retrospective comparisons, but retain modern-measurement and coverage limitations.

## Historical generalization

Strict combined Top-10 balanced accuracy is stable at 0.660, 0.669 and 0.665 across the three evaluation periods. Fixed-HGB earlier folds also improve on their own rank-only baselines (0.603 versus 0.526 in 2000–2009; 0.603 versus 0.576 in 2010–2017). This supports a recurring predictive signal, within the exploratory limitations. Longevity gains are inconsistent across eras. The 12-week strict combined classifier performs better (0.620 versus 0.497 baseline), showing that the chosen longevity window materially changes the task. No favorable horizon replaces the prespecified 26-week primary outcome.

'''
    finding_text='''# Local feature expansion v1 — measured findings

The tables report the final validation-selected models. Higher classification balanced accuracy and lower regression MAE indicate improvement. Positive values in the incremental-improvement table favor the combined model. Use the paired intervals and group ablations to assess how stable those improvements are.

'''+ narrative+'\n\n'.join(tables)+'\n\n## Incremental improvement\n\n'+markdown(pd.DataFrame(improvements))+\
        '\n\n## Paired uncertainty\n\n'+markdown(uncertainty[uncertainty.quantity.eq('combined_minus_baseline_improvement')][['track','target','cluster','estimate','lower','upper']])+\
        '\n\n## Ten highest-ranked new debut-time features for Top-10 classification\n\nRanked on validation data; a near-zero or negative value is weak evidence of usefulness. Values are balanced-accuracy loss after shuffling.\n\n'+markdown(top)+\
        '\n\n## Group ablations\n\nPositive degradation means removing the group hurt the test result. Classification units are balanced accuracy; regression units are target MAE. Method and structural hyperparameters stay fixed.\n\n'+markdown(relevant[['track','target','removed_group','degradation']])+\
        '\n\n## Historical stability and 12-week sensitivity\n\n'+markdown(history[history.partition.eq('test')][['experiment','track','target','configuration','n','balanced_accuracy','r2','mae']])+\
        '\n\n'+limits
    save_text(PUBLIC/'findings.md',finding_text)
    save_text(PUBLIC/'README.md',f'''# Local feature expansion v1

Completed local engineering and exploratory prediction campaign for songs already on the Billboard Hot 100. Read [findings](findings.md) with the [methodology](methodology.md). The prior 2018-onward test population was already inspected. No external acquisition, new content-classifier inference, or COVID analysis was performed.

The [navigation and command note](../../docs/feature_expansion_v1.md) explains why the hash-pinned original root navigation files remain unchanged. All new reproduction instructions live with this campaign and its separate dataset.

The separate [versioned dataset](../../data/public/feature_expansion_v1/README.md) contains {audit['song_count']:,} exact weekly identities, {audit['new_columns']} new columns representing {audit['new_constructs']} constructs, and separate outcomes. It preserves the existing {audit['study_count']:,}-song release. Of 59 researched local candidates, {audit['local_candidates_implemented']} are implemented; [dispositions](candidate_dispositions.csv) explain the rest.

| Artifact | Purpose |
|---|---|
| [Frozen protocol](protocol.json) | Prediction moment, windows, cohorts, tuning and seeds |
| [Feature dictionary](feature_dictionary.csv) | Definitions, sources, availability, missingness and risks |
| [Coverage](coverage_report.csv) | All-weekly and final-study denominators |
| [Model comparison](model_comparison.csv) | All three methods, A/B/C, five outcomes, train/validation/test |
| [Selected models](selected_models.csv) | Choices made on validation only |
| [Incremental improvements](incremental_improvements.csv) | Matched-cohort baseline/new/combined effects |
| [Simple baselines](simple_baselines.csv) | Majority, prevalence, historical credit, mean and median |
| [Predictions](selected_predictions.csv.gz) | Selected models, validation and test; no raw lyrics |
| [Permutation importance](permutation_importance.csv) | Validation-only ranking, three repeats |
| [Coefficients/tree importance](coefficient_tree_importance.csv) | All validation-tuned linear/tree configurations |
| [Ablations](feature_ablation.csv) | Remove each predefined feature group |
| [Uncertainty](uncertainty.csv) | 199 paired artist-credit/year cluster resamples |
| [Historical and horizon checks](historical_sensitivity.csv) | Earlier folds and 12-week sensitivity |
| [Generalization gaps](generalization_gaps.csv) | Every model's training/validation/test gap |
| [Calibration](calibration.csv) | Reliability bins; full metrics include Brier/log loss/ECE |
| [Validation audit](validation_audit.json) | Independent as-of checks, splits and preservation |
| [Replay audit](model_replay_audit.csv) | Every selected model on all three partitions |
| [Repeat-fit audit](determinism_audit.csv) | Bitwise repeats of the three strict Top-10 model families |

Standalone figures: [classification](figures/classification_comparison.svg), [regression](figures/regression_comparison.svg), [new-feature importance](figures/top10_new_feature_importance.svg), [period stability](figures/evaluation_period_stability.svg), [calibration](figures/calibration.svg), [regression diagnostics](figures/regression_diagnostics.svg). SVG files have their own [manifest](figures/manifest.json); previous PNG catalogs are unchanged.

## Reproduction

Run from the canonical repository root with the versions recorded in [protocol.json](protocol.json) and the campaign-specific [requirements](requirements.txt). These differ from the repository's historical requirements; do not replace the original file. Model fitting uses NumPy, pandas, SciPy, scikit-learn, joblib and threadpoolctl. The existing local environment has these packages; no new installation is needed here. The protocol guard includes the recorded platform/environment; portable saved-model replay does not require that fitting environment.

```bash
python3 src/feature_expansion_common.py prepare
python3 src/feature_expansion_features.py
python3 src/feature_expansion_models.py all
python3 src/feature_expansion_validate.py --prefix --preservation
python3 src/feature_expansion_report.py
python3 -m unittest discover -s tests -v
```

Feature rebuilding requires the retained private lyric/metadata stores and approved lyric text. These are read-only and never distributed. The published feature/outcome tables are sufficient for model fitting in the frozen environment. Models are checkpointed by data/protocol/code hashes under ignored `data/experiments/feature_expansion_v1/`; changed code requires a new matching checkpoint. The environment/protocol guard fails rather than silently accepting a changed experiment. A preservation baseline is local; fresh clones can use the public dataset and replay the portable models without private inputs.

Individual bounded stages are `train`, `baselines`, `interpret`, `backtests`, and `determinism` on `feature_expansion_models.py`. `all` runs them sequentially. No exhaustive combination search is invoked. Publication includes compact NumPy-replay model specifications; fitted sklearn objects and intermediate checkpoints remain private/local.

## Professor demonstration

```bash
.venv-regression-demo/bin/streamlit run src/feature_expansion_demo.py --server.address 127.0.0.1 --server.port 8503 --browser.gatherUsageStats false
.venv-regression-demo/bin/python -m unittest discover -s tests -p test_feature_expansion_demo.py -v
```

The existing Streamlit environment is reused. The page shows the known debut information, strict earlier credit history, real saved Top-10/long-chart/numerical predictions, actual 26-week outcomes, observed full-history context, baseline comparisons, confusion matrices, calibration and validation importance. Every displayed prediction is checked against its saved value. It performs no model fitting or network acquisition. The earlier demos remain at their existing entry points.
''')
    save_text(DATA/'README.md',f'''# Billboard debut features — version 1

This separate derived release contains {len(pd.read_csv(DATA/'song_features.csv.xz')):,} exact weekly song identities. It does not overwrite or redefine the existing final monthly study population of 28,041 identities. Join by `song_id`; title and full artist credit are unchanged.

| File | Unit and contents |
|---|---|
| [song_features.csv.xz](song_features.csv.xz) | One row per exact weekly identity; ID/title/artist/debut date/rank, 58 new columns, existing primary genre/42 scores/consistent duration |
| [song_outcomes.csv.xz](song_outcomes.csv.xz) | Separate 12/26-week targets, window ends, eligibility and descriptive observed lifetime fields; never predictors |
| [manifest.json](manifest.json) | File, source and pipeline hashes, coverage and input provenance references |

Use the [feature dictionary](../../../analysis/feature_expansion_v1/feature_dictionary.csv), [coverage](../../../analysis/feature_expansion_v1/coverage_report.csv), [protocol](../../../analysis/feature_expansion_v1/protocol.json), and [methodology](../../../analysis/feature_expansion_v1/methodology.md). CSV blanks are missing, not zero. Numeric engineered columns are stored as numbers; categorical `primary_genre` is the existing model label. `first_chart_date` and window ends are ISO dates. `eligible_12`/`eligible_26` are booleans. Identity is never inferred from normalized strings.

33 new columns are available at chart publication (category C). The other 25 are retrospective measurements (F), even where their intrinsic content existed earlier. Baseline `debut_rank` is known at publication; existing lyrics, genre and matched duration are retrospective. The strict forecast uses only debut rank and the 33 C columns. The retrospective track requires complete existing scores and usable lyrics, and includes modern metadata proxies. It is not a verified historical forecast.

`top10_H` means minimum rank <=10 within H weeks, `long_chart_H` means at least ceil(H/2) distinct chart dates, `best_rank_H` is the minimum rank, `chart_weeks_H` counts distinct dates, and `chart_points_H` sums 101-rank over every source row. Windows are [debut, debut + 7H days). `eligible_H` requires the source endpoint to reach that exclusive end. Top-10 classification further excludes debut ranks <=10. Descriptive observed lifetime totals may include later returns and remain right-censored.

Source: the project's supplied Billboard snapshot, reported upstream as [mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100). This records reported provenance, not independent verification. Private lyrics and acquisition databases are excluded. Original source observations, including 13 repeated song/date rows, remain unchanged; points preserve source rows while weeks count distinct dates.

Rebuilding requires the already-retained private inputs; viewing this release and replaying models do not. See the [campaign reproduction guide](../../../analysis/feature_expansion_v1/README.md).
''')
    write_json(PUBLIC/'publication_manifest.json',dict(inputs={p.name:sha(p) for p in [DATA/'song_features.csv.xz',DATA/'song_outcomes.csv.xz']},
        code={p.name:sha(p) for p in sorted((ROOT/'src').glob('feature_expansion_*.py'))},
        artifacts={str(p.relative_to(PUBLIC)):sha(p) for p in sorted(PUBLIC.rglob('*')) if p.is_file() and p.name not in ['publication_manifest.json','execution_report.json']},
        fitted_campaign=read_json(LOCAL/'active_campaign.json')['key']))
    print('Rendered findings and six standalone SVG figures',flush=True)


if __name__=='__main__':render()
