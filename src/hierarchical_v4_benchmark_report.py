"""Measured hierarchical resource projections; contains no selection or fitting rules."""
from __future__ import annotations
import shutil
import math
import hierarchical_v4_common as c


def preparation_seconds(measurements, rows, variables, targets):
    """Measured latency envelope with scaling only beyond observed row support.

    Fixed materialization/encoding overhead must not be multiplied by the ratio
    of a large cohort to a tiny cohort. Keep the maximum observed latency, then
    scale beyond measured row support and conservatively for feature/target width.
    Each timing covers two folds; the full campaign has two such stages.
    """
    return (2*max(r['seconds'] for r in measurements)
            * max(1., rows/max(r['n_train_max'] for r in measurements))
            * max(1., variables/min(r['variables'] for r in measurements))**2
            * (1.+targets/variables))


def projection(tasks, rows, pilot, timings, budget_elapsed):
    from hierarchical_v4_run import grouped
    groups = grouped(tasks, rows)
    compute = dict(prepare=0., screen=0., stability=0.)
    details = []
    # Cohort caching is counted once; target-specific scans remain exhaustive.
    for cohort, group in groups:
        pop, track = group[0]['population'], group[0]['track']
        union = len({name for task in group for name in task['predictors']})
        training = max(fold['n_train'] for task in group for fold in task['folds'])
        prep = [row for row in timings if row.get('population') == pop and row.get('track') == track and row['stage'] in ['prepare_screen', 'prepare_stability']]
        if not prep:
            raise ValueError('Unbenchmarked preparation stratum')
        prep_seconds = preparation_seconds(prep, training, union, len(group))
        compute['prepare'] += prep_seconds
        scans = [row for row in timings if row['stage'] == 'screen' and row.get('population') == pop and row.get('track') == track]
        # A factorization batch scores up to eight targets together. Charge the
        # maximum observed union-candidate fit rate for every actual batch;
        # selection/digests still cost per target/model relationship.
        widths = {row['cohort']: row['variables'] for row in prep}
        fit_rates = [row['fit_seconds']/(widths[row['cohort']]*(widths[row['cohort']]+1)/2) for row in scans]
        selection_rates = [row['screen_seconds']/row['attempted_models'] for row in scans]
        batches = math.ceil(len(group)/c.CONFIG['target_batch_size'])
        fit_seconds = max(fit_rates)*(union*(union+1)/2)*batches
        selection_seconds = max(selection_rates)*sum(task['counts'][1]+task['counts'][2] for task in group)
        screen_seconds = fit_seconds+selection_seconds
        compute['screen'] += screen_seconds
        stable = [row for row in timings if row['stage'] == 'stability' and row.get('population') == pop and row.get('track') == track]
        stable_rate = max(row['seconds']/max(1, row['attempted_models']) for row in stable)
        lower_cap = c.read_json(c.PUBLIC/'search_design.json')['lower_retained_per_target_cap']
        stability_attempts = len(group)*2*(4*c.CONFIG['triple_cap_per_target']+lower_cap)
        stability_seconds = stable_rate*stability_attempts
        compute['stability'] += stability_seconds
        details.append(dict(cohort=cohort, population=pop, track=track, tasks=len(group),
                            target_batches=batches, prepare_seconds=prep_seconds, screen_seconds=screen_seconds,
                            screening_fit_seconds=fit_seconds, screening_selection_seconds=selection_seconds,
                            stability_seconds=stability_seconds))
    audit_rate = max(row['seconds']/max(1, row['attempted_models']) for row in timings if row['stage'] == 'stability')
    compute['stability'] += audit_rate*8*c.CONFIG['audit_samples_full']
    projected = sum(compute.values())
    # The uncertainty allowance includes sampling, hashes, confidence bounds,
    # reporting, writes and checkpoint reopening. No ideal CPU speedup assumed.
    conservative = projected*1.5+900+budget_elapsed
    design = c.read_json(c.PUBLIC/'search_design.json')
    storage = int(design['triple_payload_byte_cap']*1.5+len(tasks)*180000+1_000_000_000)
    free = shutil.disk_usage(c.ROOT).free
    allowed = (conservative <= c.CONFIG['runtime_limit_seconds'] and storage <= c.CONFIG['temporary_disk_limit_bytes']
               and storage+c.CONFIG['disk_headroom_bytes'] <= free)
    output = dict(status='WITHIN_BUDGET' if allowed else 'BUDGET_NOT_MET', full_campaign_started=False,
                  estimated_component_seconds=compute, projected_seconds=projected,
                  conservative_total_seconds=conservative, projected_temporary_storage_bytes=storage,
                  free_disk_bytes=free, benchmark_seconds=budget_elapsed,
                  limits={key: c.CONFIG[key] for key in ['runtime_limit_seconds', 'temporary_disk_limit_bytes', 'disk_headroom_bytes']},
                  projection='Maximum matching population/track latency and rates; preparation once per cohort, row scaling only beyond maximum measured support, conservative variable/target-width scaling; actual batches of at most eight targets for fitting and per-model selection; 1.5x compute plus 900 seconds and pilot wall time; no unmeasured parallel speedup',
                  protocol_sha256=c.freeze(), projection_code_sha256=c.sha(__file__))
    c.write_csv(c.PUBLIC/'resource_projection_by_cohort.csv', details)
    c.write_json(c.PUBLIC/'benchmark_gate.json', output)
    return output
