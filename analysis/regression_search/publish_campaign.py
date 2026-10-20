"""Publish compact final evidence from the completed, audited frozen campaign."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import campaign_report as audit
from campaign_report import CAMPAIGN, FROZEN, PUBLIC, ROOT, run, spec, write_json
import render_report
from render_report import table


def load(path):
    return json.loads(Path(path).read_text())


def target_unit(target):
    if target in spec.original.SCORES:
        return "frozen classifier score (0–1)"
    if target.endswith("seconds"):
        return "seconds"
    if target in ("first_snapshot_month","last_snapshot_month"):
        return "months since 1970-01"
    if target in spec.original.DATES:
        return "days since 1970-01-01"
    if target=="mb_release_year":
        return "calendar year"
    return "observed count / chart points as named"


def publish():
    verified = load(PUBLIC/"coverage_after_test.json")
    if verified["status"]!="PASS" or verified["target_count"]!=59:
        raise ValueError("Publication requires the full final audit")
    audit.verify_frozen()
    hierarchy = load(PUBLIC/"hierarchy_manifest.json")
    if hierarchy["total_rows"]!=1998901:
        raise ValueError("All complete hierarchy exports are required")
    results = load(CAMPAIGN/"target_leaderboard.json")
    resumed = load(CAMPAIGN/"search_complete.json")["tasks"]
    if len(resumed)!=59 or not all(t.get("already_complete") for t in resumed):
        raise ValueError("The completed-target resume verification is required")
    flat, best, stability, models, samples, cohorts = [],[],[],[],[],[]
    tasks = {t["task_id"]:t for t in spec.specs()}
    for result in results:
        task = tasks[result["task_id"]]
        dest = run.task_path(CAMPAIGN,task)
        selection = load(dest/"selection.json")
        if spec.original.sha(dest/"selection.json")!=verified["selection_sha256"][task["task_id"]]:
            raise ValueError("Selection changed after audit")
        winner = selection["winner"]
        row = dict(target_rank=result["target_rank"], task_id=result["task_id"], target=result["target"],
            units=target_unit(result["target"]), predictors=result["predictors"], k=result["k"],
            candidate_id=winner["id"], candidates=selection["candidate_count"],
            validation_r2=winner["validation_r2"],validation_mae=winner["validation_mae"],
            validation_rmse=winner["validation_rmse"],validation_skill=winner["validation_skill"],
            validation_baseline_r2=winner["baseline_r2"],validation_baseline_mae=winner["baseline_mae"],
            validation_baseline_rmse=winner["baseline_rmse"],n_validation=winner["n_validation"],
            validation_songs=winner["validation_songs"],n_train_by_period=winner["n_train_by_period"],
            n_refit=result["n_refit"],n_test=result["n_test"],test_songs=result["test_songs"],
            test_r2=result["r2"],test_mae=result["mae"],test_rmse=result["rmse"],
            test_baseline_r2=result["baseline_r2"],test_baseline_mae=result["baseline_mae"],
            test_baseline_rmse=result["baseline_rmse"],test_mse_skill=result["skill"],test_mae_skill=result["mae_skill"],
            test_minus_validation_r2=result["test_minus_validation_r2"],
            test_minus_validation_skill=result["test_minus_validation_skill"],
            test_minus_validation_mae=result["mae"]-winner["validation_mae"],
            test_minus_validation_rmse=result["rmse"]-winner["validation_rmse"],
            validation_worst_period_skill=winner["worst_period_skill"],
            validation_period_skill_range=winner["period_skill_range"],
            selected_period_ranks=[s["selected_period_rank"] for s in selection["historical_stability"]],
            test_r2_ci95_low=result["ci95"]["r2"][0],test_r2_ci95_high=result["ci95"]["r2"][1],
            song_cluster_ci95=result["ci95"],calendar_block_ci95=result["calendar_block_ci95"],
            unsupported_genre_rows=result["unsupported_genre_rows"],interpretation=result["interpretation"])
        flat.append(row)
        best.extend(dict(task_id=task["task_id"],**b) for b in selection["best_by_k"])
        stability.extend(dict(task_id=task["task_id"],start=spec.FOLDS[s["fold"]][0],
            end_exclusive=spec.FOLDS[s["fold"]][1],**s) for s in selection["historical_stability"])
        cohorts.extend(dict(task_id=task["task_id"],**c) for c in result["test_cohorts"])
        hashes=load(dest/"final_artifacts.json")
        models.append(dict(task_id=task["task_id"],predictors=result["predictors"],
            candidate_id=winner["id"],k=result["k"],encoded_rank=result["rank"],
            specification_path=str((dest/"specification.json").relative_to(ROOT)),
            specification_sha256=spec.original.sha(dest/"specification.json"),
            selection_sha256=verified["selection_sha256"][task["task_id"]],
            model_path=str((dest/"selected_model.json").relative_to(ROOT)),
            final_artifacts_sha256=hashes,identity_sha256=selection["identity_sha256"]))
        candidates=list(enumerate(spec.combinations(task)))
        with audit.Store(dest/"results.sqlite",run.identity(task,candidates,spec.configuration()),candidates,task["predictors"]) as store:
            samples.extend(dict(task_id=task["task_id"],**r) for r in store.rows(limit=10))
    write_json(PUBLIC/"target_leaderboard.json",results)
    run.write_csv(PUBLIC/"target_leaderboard.csv",flat)
    run.write_csv(PUBLIC/"best_by_predictor_count.csv",best)
    run.write_csv(PUBLIC/"historical_stability.csv",stability)
    run.write_csv(PUBLIC/"hierarchy_top10_per_target.csv",samples)
    run.write_csv(PUBLIC/"test_cohorts.csv",cohorts)
    write_json(PUBLIC/"selected_models.json",dict(implementation_commit=FROZEN,
        configuration=spec.configuration(),models=models))
    measurements=[load(p) for p in sorted((CAMPAIGN/"execution").glob("*.json")) if p.name!="protected_before.json"]
    phases={name:[m for m in measurements if m["phase"]==name] for name in ("search","finalize","resume_probe")}
    if any(m["status"]!="complete" for m in measurements):
        raise ValueError("Execution record includes an unsuccessful attempt; document before publication")
    disk=Counter()
    for p in CAMPAIGN.rglob("*"):
        if p.is_file():
            key="hierarchy_exports" if p.parent.name=="hierarchies" else "sqlite" if p.suffix==".sqlite" else "other_checkpoints_models_splits_predictions_logs"
            disk[key]+=p.stat().st_size
    disk["total"]=sum(disk.values())
    validation = load(PUBLIC/"validation.json") if (PUBLIC/"validation.json").exists() else {"status":"tests pending"}
    summary=dict(status="complete",full_campaign_run=True,numerical_targets=59,successful_models=len(results),
        combinations=verified["combinations"],validation_fits=verified["validation_fits"],by_k=verified["by_k"],
        implementation_commit=FROZEN,categorical_ordinal_tasks_run=0,resume_reused_targets=len(resumed),
        phase_elapsed_seconds={k:sum(m["elapsed_seconds"] for m in v) for k,v in phases.items()},
        search_plus_finalization_seconds=sum(m["elapsed_seconds"] for m in measurements if m["phase"] in ("search","finalize")),
        peak_search_or_finalize_rss_bytes=max(m["child_peak_rss_bytes"] for m in measurements if m["phase"] in ("search","finalize")),
        audit_seconds=sum(load(PUBLIC/p)["elapsed_seconds"] for p in ["coverage_before_test.json","coverage_after_test.json"]),
        hierarchy_export_seconds=hierarchy["elapsed_seconds"],
        peak_hierarchy_export_rss_bytes=hierarchy["peak_rss_bytes"],
        disk_bytes=dict(disk),measurements=measurements,
        mse_baseline_failures=[r["task_id"] for r in results if r["skill"]<=0],
        mae_baseline_failures=[r["task_id"] for r in results if r["mae_skill"]<=0],
        negative_test_r2=[r["task_id"] for r in results if r["r2"]<0],
        r2_drop_over_point_one=[r["task_id"] for r in results if r["test_minus_validation_r2"]<-.1],
        winners_including_genre=[r["task_id"] for r in results if set(r["predictors"]) & set(spec.original.GENRES)],
        winners_including_time=[r["task_id"] for r in results if set(r["predictors"]) & (set(spec.original.DATES)|{"mb_release_year","chart_date","snapshot_chart_date"})],
        selected_k=dict(Counter(str(r["k"]) for r in results)),
        final_test_selection_revisions=0,validation=validation)
    write_json(PUBLIC/"run_summary.json",summary)
    write_report(flat,summary,verified)
    render_report.main()
    refresh_manifest()
    return summary


def refresh_manifest():
    path=run.PUBLIC/"artifact_manifest.json"
    artifacts=set(load(path)["artifacts_sha256"])
    artifacts.update(str(p.relative_to(ROOT)) for p in run.PUBLIC.rglob("*")
        if p.is_file() and p.suffix in (".json",".csv",".md",".py") and p!=path)
    artifacts.update(["README.md","docs/regression_search_results.md","tests/test_regression_campaign_report.py"])
    write_json(path,dict(scope="Frozen three-predictor OLS implementation, historical bounded pilot, and completed authorized numerical campaign",
        artifacts_sha256={name:spec.original.sha(ROOT/name) for name in sorted(artifacts)}))


def write_report(rows,summary,verified):
    def name(task):return task.removeprefix("songs:")
    def preds(row):return " + ".join(row["predictors"])
    def leaderboard(items):
        return table(["Rank","Target","Selected predictors","Validation R²","Test R²","Test MAE","Test RMSE","Test songs"],
            [[r["target_rank"],name(r["task_id"]),preds(r),f'{r["validation_r2"]:.4f}',f'{r["test_r2"]:.4f}',
              f'{r["test_mae"]:.5g}',f'{r["test_rmse"]:.5g}',f'{r["test_songs"]:,}'] for r in items])
    def names(key):return ", ".join(name(t) for t in summary[key]) or "None"
    text=f'''# Full exhaustive numerical OLS results

Completed on 2026-10-20 with the exact search implementation from `{FROZEN}`.
All **59 targets**, **1,998,901 unique combinations**, and **5,996,703 historical
validation fits** completed. There were 3,466 one-variable, 100,118 two-variable
and 1,895,317 three-variable combinations. The final 2018-onward test was scored
only after every validation winner was selected and the full coverage audit passed.
No winner was revised using test performance. Categorical/ordinal tasks were not run.

## Results and interpretation

The following rankings compare held-out R², which adjusts squared error for each
target's test-population variance. MAE and RMSE remain in the named target's units;
they should not be compared across different units. Selection within each target
used equal-period mean MSE skill relative to the historical training-mean baseline,
with the approved fewer-predictors/lexicographic tie rule. Thus final target ranking
and validation candidate ranking have different purposes.
Each target uses its observed-outcome population, so sample sizes and missingness
patterns differ across targets. Rankings describe that population and need not
transfer to missing or unenriched songs. Small rank differences with overlapping
uncertainty intervals should not be treated as resolved performance differences.

### Ten most predictable targets

{leaderboard(rows[:10])}

### Ten least predictable targets

{leaderboard(rows[-10:])}

### Strongest lyric-score relationships

{leaderboard([r for r in rows if r['target'] in spec.original.SCORES][:5])}

Low R² describes the limitations of these additive models, candidate variables and
historical transfer setting. It does not establish objective randomness. The many
classifier outputs are frozen model scores, so strong score-to-score relationships
measure model agreement and overlapping content, not independent ground-truth validity.
OLS predictions are unbounded and were not clipped to score or count ranges.

Duration summaries, near-identity chart counts and related chart-date coordinates
can reconstruct one another very accurately. These retained correlations are part
of the approved universe; their high R² is not evidence of causal discovery or a
useful advance forecast. In particular, chart weeks and weekly observation count
are almost identical in the source data. Chart-date coordinates use days since
1970-01-01; first/last snapshot-month coordinates use months since 1970-01.
Release year remains a calendar year. These are the unchanged frozen conversions.

Genre appears in {len(summary['winners_including_genre'])} selected models:
{names('winners_including_genre')}. Historical date/year predictors appear in
{len(summary['winners_including_time'])} selected models: {names('winners_including_time')}.
Genre and time may encode cohort composition, measurement practices and changing
music populations. None of these observational relationships identify causal effects.

### Generalization and baselines

Targets that did not beat the refit-training mean under test squared error:
**{names('mse_baseline_failures')}**.

Targets that did not beat the refit-training median under test absolute error:
**{names('mae_baseline_failures')}**.

Negative final R²: **{names('negative_test_r2')}**. A negative R² compares with the
test-set mean; baseline skill compares with the training mean. These comparisons
can disagree under historical shift. R² drops larger than 0.10 from aggregate
validation: **{names('r2_drop_over_point_one')}**. These are descriptive flags,
not significance tests or a revised selection criterion.

{table(['Target','Validation R²','Test R²','Test − validation R²','Test MSE skill'],
       [[name(r['task_id']),f"{r['validation_r2']:.4f}",f"{r['test_r2']:.4f}",
         f"{r['test_minus_validation_r2']:.4f}",f"{r['test_mse_skill']:.4f}"]
        for r in sorted(rows,key=lambda r:r['test_minus_validation_r2']) if r['test_minus_validation_r2']<-.1])}

All {summary['successful_models']} models fitted successfully; successful fitting
does not imply useful generalization. {len(summary['mse_baseline_failures'])} models
failed the squared-error baseline and {len(summary['mae_baseline_failures'])} failed
the median absolute-error baseline. OLS selection optimizes squared-error skill,
so absolute-error improvements are not guaranteed. All 59 overall winners use
three original predictors; the best smaller models remain available separately.

The [full leaderboard](../analysis/regression_search/campaign/target_leaderboard.csv)
includes validation/test R², MAE, RMSE, both baselines, sample sizes, R²/skill/error
gaps, worst-period skill and all uncertainty intervals. Validation R²/MAE are means
over the three periods; validation RMSE is the square root of their mean MSE.
The [historical stability table](../analysis/regression_search/campaign/historical_stability.csv)
retains the chosen model's rank and skill in 1990–1999, 2000–2009 and 2010–2017,
alongside each period's own winner. The [cohort table](../analysis/regression_search/campaign/test_cohorts.csv)
shows final performance in successive two-year debut cohorts.

Uncertainty uses the implemented 500 song-cluster resamples of fixed predictions,
plus exploratory two-year debut-block intervals when at least three blocks exist.
These intervals condition on the selected fitted model: they do not include search
selection or refit uncertainty, and the many targets are not independent tests.
Recent chart histories are censored at the frozen 2026-09-19 snapshot. Follow-up
length differs by cohort, so observed career counts are not lifetime outcomes.

## Full target leaderboard

{leaderboard(rows)}

## Integrity and measured resources

Independent enumeration verified every candidate identity and all three scores,
without missing or duplicate combinations. SQLite integrity checks passed for all
59 stores; repeated ranking queries and independent metric averaging agreed.
An actual no-op resume reused every completed target; validation score/ranking and
selection hashes were unchanged at the post-test audit. All 59 final encoders were
reconstructed from training rows only, predictions replayed, metrics recomputed,
and predictions checked against direct original-row LAPACK SVD. The maximum scaled
prediction discrepancy was {max(t['final']['max_direct_prediction_scaled_error'] for t in verified['targets']):.3g}.

Whole-song temporal membership and source-row membership were checked for every
validation and final split. All six frozen implementation files and eight approved
input hashes match the launch specification. Every tracked public/preprocessing data
file and protected existing analytical output remains byte-identical. These checks
establish the approved leakage boundaries; the metadata's enrichment times are not
historically certified, so results describe retrospective cohort transfer.

| Measurement | Actual |
|---|---:|
| Full search including checkpoint/ranking work | {summary['phase_elapsed_seconds']['search']/60:.2f} min |
| Final refits, test scoring and intervals | {summary['phase_elapsed_seconds']['finalize']/60:.2f} min |
| Search + final evaluation | {summary['search_plus_finalization_seconds']/60:.2f} min |
| No-op resume verification | {summary['phase_elapsed_seconds']['resume_probe']:.2f} s |
| Independent pre-/post-test audits | {summary['audit_seconds']/60:.2f} min |
| Complete hierarchy export and verification | {summary['hierarchy_export_seconds']/60:.2f} min |
| Peak child-process RAM during search/finalization | {summary['peak_search_or_finalize_rss_bytes']/1024**3:.2f} GiB |
| Peak hierarchy export RAM | {summary['peak_hierarchy_export_rss_bytes']/1024**3:.2f} GiB |
| SQLite result stores | {summary['disk_bytes']['sqlite']/1024**3:.2f} GiB |
| Complete compressed hierarchy exports | {summary['disk_bytes']['hierarchy_exports']/1024**3:.2f} GiB |
| Total retained campaign files, logical bytes | {summary['disk_bytes']['total']/1024**3:.2f} GiB |

Measurements use one target worker and one BLAS thread on the same Apple M2 Pro
machine as the pilot. Search/evaluation times exclude independent audits, hierarchy
export and documentation. Detailed phase timestamps, CPU/RAM, hashes and validation
evidence are in [run_summary.json](../analysis/regression_search/campaign/run_summary.json).
Test status: {summary['validation']['status']}.

## Access and reproduction

The [experiment README](../analysis/regression_search/README.md) gives the exact
commands. The complete local hierarchy consists of 59 compressed CSVs under
`data/experiments/regression_search/campaign/hierarchies/`, containing all 1,998,901
rows, not only winners. The [hierarchy manifest](../analysis/regression_search/campaign/hierarchy_manifest.json)
records every path, row count and SHA-256. SQLite `hierarchy` views provide the same
complete rankings. The [top-ten-per-target extract](../analysis/regression_search/campaign/hierarchy_top10_per_target.csv)
is a small convenience extract, not the complete hierarchy.

The [best-by-count file](../analysis/regression_search/campaign/best_by_predictor_count.csv)
retains all 177 best one-, two- and three-variable models and their validation metrics.
Only the overall validation winner per target was evaluated on the final test.
The [selected-model manifest](../analysis/regression_search/campaign/selected_models.json)
records final specifications and hashes. Each local target directory contains its
exact encoder, coefficients, training baselines, splits, predictions and integrity
hashes. Large databases, row-level predictions and exports remain ignored by Git.
Small summaries, model specifications and audit evidence are versioned.
'''
    (ROOT/"docs/regression_search_results.md").write_text(text)


if __name__=="__main__":
    publish()
