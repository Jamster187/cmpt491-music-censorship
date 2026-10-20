"""Generate the exploratory findings and compact publication from saved results."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
import regression_meaningful as m
import regression_relationships as rel


def table(headers,rows):
    def cell(x):return str(x).replace('|','\\|').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(cell(v) for v in r)+' |' for r in rows])


def short(name):return name.removeprefix('songs:')


def results_table(rows):
    return table(['Target','Predictors','Category','Validation R²','Exploratory test R²','95% song-bootstrap R² interval'],
        [[short(r['task_id']),' + '.join(r['predictors']),r['category'][0],f"{r['validation_r2']:.4f}",f"{r['r2']:.4f}",
          f"[{r['ci95']['r2'][0]:.4f}, {r['ci95']['r2'][1]:.4f}]"] for r in rows])


def render():
    filtered=m.read_json(m.PUBLIC/'filtered_leaderboard.json')
    cross=m.read_json(m.PUBLIC/'cross_domain_leaderboard.json')
    original=m.read_json(m.original.PUBLIC/'campaign/target_leaderboard.json')
    old={r['task_id']:r for r in original}
    old_ids={r['task_id']:r['candidate_id'] for r in m.read_json(m.original.PUBLIC/'campaign/selected_models.json')['models']}
    audit=m.read_json(m.PUBLIC/'filter_audit.json');evaluation=m.read_json(m.PUBLIC/'evaluation_audit.json')
    changes=[dict(task_id=r['task_id'],original_predictors=old[r['task_id']]['predictors'],filtered_predictors=r['predictors'],
        original_r2=old[r['task_id']]['r2'],filtered_r2=r['r2'],test_r2_change=r['r2']-old[r['task_id']]['r2'],
        removed_original_rules=rel.circular_reasons(r['target'],old[r['task_id']]['predictors']),
        winner_changed=r['candidate_id']!=old_ids[r['task_id']]) for r in filtered]
    changes.sort(key=lambda r:r['test_r2_change'])
    m.original.write_csv(m.PUBLIC/'changes_from_unrestricted.csv',changes)
    annotated=[dict(r,candidate_id=old_ids[r['task_id']],**rel.classify(r['target'],r['predictors']),
        evaluation_label='Original unrestricted evaluation; preserved and already inspected') for r in original]
    m.original.write_csv(m.PUBLIC/'original_annotated_leaderboard.csv',annotated)
    selections=m.read_json(m.PUBLIC/'selected_candidates.json')
    selected_models=[]
    for t in selections['targets']:
        for view,row in t['winners'].items():
            path=m.LOCAL/'models'/t['task_id'].replace(':','__')/str(row['id'])
            selected_models.append(dict(task_id=t['task_id'],view=view,candidate_id=row['id'],predictors=row['predictors'],
                model_path=str((path/'model.json').relative_to(ROOT)),model_sha256=m.spec.original.sha(path/'model.json'),
                artifacts=m.read_json(path/'artifacts.json')))
    m.write_json(m.PUBLIC/'model_manifest.json',dict(evaluation_label='POST-HOC EXPLORATORY',models=selected_models))
    f={r['target']:r for r in filtered};c={r['target']:r for r in cross}
    chart=[r for r in cross if r['target'] in m.spec.original.HISTORY_COUNTS or r['task_id'].startswith(('monthly:','weekly:'))]
    genre=[r for r in cross if set(r['predictors']) & set(m.spec.original.GENRES)]
    dates=[r for r in cross if set(r['predictors']) & (rel.DATES|{'chart_date','snapshot_chart_date','mb_release_year'})]
    changed=[r for r in changes if r['winner_changed']]
    tests=m.read_json(m.PUBLIC/'test_results.json') if (m.PUBLIC/'test_results.json').exists() else {'status':'pending'}
    disk=sum(p.stat().st_size for p in m.LOCAL.rglob('*') if p.is_file())
    summary=dict(source_combinations=audit['source_combinations'],excluded_combinations=audit['excluded_combinations'],
        eligible_combinations=audit['eligible_combinations'],cross_domain_combinations=audit['cross_domain_combinations'],
        circular_directed_relationships=audit['circular_directed_relationships'],filtered_winners=len(filtered),cross_domain_winners=len(cross),
        changed_winners=len(changed),unique_selected_refits=evaluation['unique_selected_models'],
        filter_seconds=audit['elapsed_seconds'],evaluation_seconds=evaluation['elapsed_seconds'],local_logical_bytes=disk,
        filtered_negative_r2=sum(r['r2']<0 for r in filtered),cross_domain_negative_r2=sum(r['r2']<0 for r in cross),
        filtered_mean_baseline_failures=[r['task_id'] for r in filtered if r['skill']<=0],
        cross_domain_mean_baseline_failures=[r['task_id'] for r in cross if r['skill']<=0],
        test_results=tests,full_search_rerun=False,evaluation_label='POST-HOC EXPLORATORY')
    m.write_json(m.PUBLIC/'run_summary.json',summary)
    report=f'''# Meaningful regression findings

**POST-HOC EXPLORATORY — the original 2018-onward final test had already been inspected.**
This report filters the complete campaign from commit `{m.SOURCE_COMMIT}`. No new
untouched holdout is claimed. The policy and all winners were frozen before these
new refits; no test result changed a rule or selected a replacement winner.
The original hierarchies, models, metrics and public datasets remain byte-identical.

## Scope and interpretation policy

All {audit['source_combinations']:,} original combinations were recovered locally and
verified against the completed campaign's exact candidate and score hashes. We
excluded **{audit['excluded_combinations']:,} combinations**, leaving **{audit['eligible_combinations']:,}**;
**{audit['cross_domain_combinations']:,}** satisfy the strict cross-domain definition.
All 59 targets have filtered and cross-domain winners. The 20 directed pairwise
reconstruction relationships are supplemented by a two-endpoint exposure rule.
Rule counts overlap; exclusions count each combination only once.

The [frozen policy](meaningful/relationship_policy.json) and
[complete pair registry](meaningful/relationship_pairs.csv) record definitions,
domains, reasons and source references. Rules use the public schema and production
derivations, never a correlation threshold. See [the public definitions](../../data/public/README.md).

| Category | Operational meaning | Treatment |
|---|---|---|
| A: circular / reconstruction | Weekly rows versus distinct weekly dates; alternative calendar coordinates of the same chart career; min/median/max of the same recording-length set; both episode endpoints predicting its exposure count | Excluded |
| B: redundant / same-family | Shared information domain, including related classifier constructs, MusicBrainz counts, and chart-performance aggregates | Retained and labelled |
| C: cross-domain | Every predictor belongs to a different information domain from the target, with no A rule | Separate strict view |

There are six documented domains: lyrical content (LyricLens/Detoxify), lyrical
affect (GoEmotions/sentiment), genre, historical calendar, MusicBrainz metadata,
and chart performance. Mixed B/C combinations are B with cross-domain tags.
Domain boundaries are interpretive choices, not discovered natural categories.
C can share the same lyrics or chart source with its target; it does not establish
independent measurement. A also includes explicitly documented reconstruction
scope restrictions beyond exact algebraic identity: endpoints can differ because
of gaps, month sampling, and recording versions. These are not claims of equality.

Monthly versus weekly exposure counts, points versus count/best rank, and related
MusicBrainz counts remain B. They are not exactly interchangeable under the stated
definitions. Thus a filtered leaderboard can still be dominated by redundancy;
its label means eligible under this policy, not inherently novel science.

## Most predictable filtered targets

{results_table(filtered[:10])}

All of these leading combinations are B. Chart exposure summaries and metadata
counts retain substantial shared structure. The strongest lyric-score example is
toxicity from insult, obscenity and severe toxicity, R² {f['detox_toxicity']['r2']:.3f}.
It measures agreement among frozen model outputs rather than human-validated accuracy.

## Least predictable filtered targets

{results_table(filtered[-10:])}

Large negative calendar R² values are retained without clipping. The recent test
cohort has a much narrower date range than historical training, and these models
poorly extrapolate its calendar location after the same-career date predictors are
removed. The training-mean baseline is often worse still, so positive baseline
skill can coexist with very negative R². This does not make the model useful.
Date errors are in days, snapshot-month errors in months, and release-year errors
in years. Weak prediction in this setting is not evidence of objective randomness.

## Strongest cross-domain relationships

{results_table(cross[:10])}

Content–affect links often share the same lyrics despite using different model
families. Genre adds population structure but is itself a frozen inferred label.
These results describe associations and cohort transfer, not causal effects or
independent validation of the classifier panel.

## Chart-success prediction

{results_table(chart)}

The cross-domain model for total chart points has R² {c['total_chart_points']['r2']:.4f}
and its fixed-model song-bootstrap interval includes zero. Monthly reported weeks
also has almost no explained variance. Whole-history exposure counts have negative
cross-domain test R². The weekly reported-weeks model uses current and first chart
dates plus genre; it is partly an elapsed-time proxy within chart history, not a
demonstration that lyrical characteristics forecast success. Gaps/re-entries and the
separately reported counter prevent an exact identity, but this shared provenance
limits its interpretation. No general lyric-to-chart-success claim is supported.

## Genre and historical period

Genre occurs in {len(genre)} cross-domain winners; calendar/date/year variables occur
in {len(dates)}. Examples worth explaining are obscenity from anger, debut date and
genre (R² {c['detox_obscene']['r2']:.3f}); explicit language from annoyance and the two
genre fields (R² {c['ll_explicit_language']['r2']:.3f}); and substance-use score from
neutral affect, first snapshot month and primary genre (R² {c['ll_substance_use']['r2']:.3f}).
These combinations do not isolate a marginal genre or period effect. They cannot
support a COVID breakpoint claim, and no such analysis was performed.

## Biggest changes and historical transfer failures

Only {len(changed)} filtered winners differ from the original unrestricted winners.
The following comparison is descriptive; test changes did not select these models.

{table(['Target','Original test R²','Filtered test R²','Change','Excluded original rule'],
       [[short(r['task_id']),f"{r['original_r2']:.4f}",f"{r['filtered_r2']:.4f}",f"{r['test_r2_change']:.4f}",', '.join(r['removed_original_rules'])] for r in changed])}

There are {summary['filtered_negative_r2']} negative-R² filtered targets and
{summary['cross_domain_negative_r2']} negative-R² cross-domain targets. Against the
training-mean squared-error baseline, {len(summary['filtered_mean_baseline_failures'])}
filtered models and {len(summary['cross_domain_mean_baseline_failures'])} cross-domain
models fail. The full files also report training-median MAE baselines, validation
MAE/RMSE, all gaps, sample sizes and each historical validation period.

## Eight presentation findings

1. **High accuracy can be reconstruction.** Removing 32,619 definition-based
   candidates changes nine winners and sharply reduces calendar/duration performance.
2. **Redundancy remains informative but must be named.** Toxicity R² is
   {f['detox_toxicity']['r2']:.3f} within related content outputs versus
   {c['detox_toxicity']['r2']:.3f} for the selected cross-domain model.
3. **The strongest cross-domain result is moderate, not near-perfect.** Insult
   from anger, annoyance and genre reaches R² {c['detox_insult']['r2']:.3f}.
4. **Genre and affect jointly relate to explicitness.** The strict cross-domain
   explicit-language model reaches R² {c['ll_explicit_language']['r2']:.3f}; do not
   interpret this as a causal genre effect.
5. **Moderation scores have different predictability.** Violence reaches
   cross-domain R² {c['ll_violence']['r2']:.3f}, sexual content
   {c['ll_sexual_content']['r2']:.3f}, and substance use
   {c['ll_substance_use']['r2']:.3f}. These are limited explanatory fractions.
6. **Chart success does not transfer well from the other domains.** Total points
   has cross-domain R² {c['total_chart_points']['r2']:.4f}, with uncertainty spanning
   zero; longevity counts perform below the test-mean reference.
7. **Historical transfer matters.** Show the extreme calendar failures and the
   validation-to-test gaps instead of presenting only attractive fitted examples.
8. **A real interactive prediction can be wrong.** Use the local demo to compare
   actual values, predictions and residuals, then change inputs and discuss
   availability, missingness and extrapolation. Never replace a poor held-out row
   with a fabricated example or claim that a single good prediction proves accuracy.

## Limitations and reproducibility

All new results are post-hoc exploratory. The policy was informed by known variable
definitions and the already inspected unrestricted study. The same final population
cannot provide fresh confirmatory evidence. A new future cohort would be needed for
confirmation; none was acquired. The exhaustive original search creates selection
optimism; fixed-model bootstrap intervals do not include selection/refit uncertainty
or multiple-comparison adjustment. Two-year debut-block intervals are exploratory.

OLS is additive with at most three original predictors; genre variables expand to
multiple columns. Predictions are not clipped. Outcomes are frozen classifier scores
or retrospective metadata, with enrichment timing not certified at historical dates.
Missing-target populations differ. Chart histories are censored at 2026-09-19,
and whole-song temporal purging changes cohort composition. These limitations matter
especially for calendar extrapolation and apparent chart-success prediction.

Complete original hierarchies are accessed read-only. Complete filtered SQLite
indices retain every original candidate ID and its filtered/category rank; no sampled
candidate set was substituted. Validation ranks retain the original mean-period
baseline-relative MSE skill and tie rules. All 59 filtered winners and 59 strict
cross-domain winners were frozen together; {evaluation['unique_selected_models']}
distinct refits sufficed. Filtering/integrity checks took {audit['elapsed_seconds']:.1f}s;
selected-model refits and uncertainty took {evaluation['elapsed_seconds']:.1f}s.
The original two-million-combination campaign was not rerun.

See the [launch and reproduction guide](meaningful/README.md),
[filtered leaderboard](meaningful/filtered_leaderboard.csv),
[cross-domain leaderboard](meaningful/cross_domain_leaderboard.csv),
[all best-by-size models](meaningful/best_by_predictor_count.csv),
[verification evidence](meaningful/validation.json), and
[selected-model manifest](meaningful/model_manifest.json).
Large indices, fitted models, predictions and splits remain local and ignored.
Current test status: {tests['status']}.
'''
    (m.original.PUBLIC/'meaningful_findings.md').write_text(report)
    refresh_manifest()


def refresh_manifest():
    files=[p for p in m.PUBLIC.rglob('*') if p.is_file() and p.suffix in {'.json','.csv','.py','.md'} and p.name!='artifact_manifest.json']
    files += [ROOT/p for p in ['src/regression_relationships.py','src/regression_meaningful.py','src/regression_demo_model.py',
        'src/regression_demo.py','requirements-demo.txt','tests/test_regression_meaningful.py','tests/test_regression_demo_app.py',
        'analysis/regression_search/meaningful_findings.md']]
    m.write_json(m.PUBLIC/'artifact_manifest.json',dict(scope='Separate post-hoc exploratory meaningful analysis; original campaign preserved',
        sha256={str(p.relative_to(ROOT)):m.spec.original.sha(p) for p in sorted(files)}))


if __name__=='__main__':render()
