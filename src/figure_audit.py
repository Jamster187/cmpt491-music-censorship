"""Audit and rebuild presentation from saved results; never write numerical outputs."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import descriptive_analysis as d
import moving_average_analysis as m
import moving_average_all_genres as overlays
import figure_style as style

ROOT=Path(__file__).resolve().parents[1]
ANALYSIS=ROOT/'analysis'
BASELINE=ANALYSIS/'figure_inventory_before.csv'
MANIFEST=ANALYSIS/'figure_manifest.json'
CODE=['src/figure_audit.py','src/figure_style.py','src/moving_average_figures.py',
      'src/descriptive_figures.py','src/moving_average_analysis.py',
      'src/descriptive_analysis.py','src/moving_average_all_genres.py']


def numerical_hashes():
    paths=set()
    for directory in ['data/public','analysis/milestone2/tables','analysis/moving_averages/data']:
        paths.update(p for p in (ROOT/directory).rglob('*') if p.is_file())
    return {str(p.relative_to(ROOT)):d.sha(p) for p in sorted(paths)}


def read_inputs():
    overall=pd.read_csv(m.OUTPUT/'data/monthly_classifier_overall.csv.xz',float_precision='round_trip')
    genres=pd.read_csv(m.OUTPUT/'data/monthly_classifier_by_genre.csv.xz',float_precision='round_trip')
    coverage=pd.read_csv(m.OUTPUT/'data/coverage_summary.csv')
    overlays.validate(genres,coverage)
    frame=pd.read_csv(d.INPUT,keep_default_na=False,na_values=[''])
    songs=d.validate(frame)
    return overall,genres,coverage,frame,songs


def overlay_records(genres):
    manifest=json.loads((overlays.OUTPUT/'manifest.json').read_text())
    rows=[]
    for name in sorted(manifest['figures']):
        records=[r for r in manifest['plotted_series'] if r['filename']==name]
        r=records[0]
        values=genres[genres.classifier.eq(r['classifier']) & genres.primary_genre.isin([x['primary_genre'] for x in records])].rolling_12m_mean
        style.assert_contained(values,r['y_limits'])
        ref=name[:-4]+'_full_scale.png' if not name.endswith('_full_scale.png') else ''
        rows.append(dict(figure_path=str(overlays.OUTPUT/name),
            figure_family='moving_average_'+('major_coverage' if 'major_coverage' in name else 'all_genres'),
            primary_series='equal-weight 12-month means of qualifying genres',axis_dimension='y',
            **style.metrics(values,r['y_limits']), panels_json=json.dumps([style.metrics(values,r['y_limits'])],sort_keys=True),
            issue_detected='',action_taken='Retain previously validated independently scaled overlay' if ref else 'Retain full-domain reference',
            full_scale_reference_available=bool(ref),full_scale_reference=str(overlays.OUTPUT/ref) if ref else '',
            context_points_clipped=0,context_note='Scores range 0–1; observed-range axes disclosed on figure',labels_inside_canvas=True))
    return rows


def enrich(records, baseline, stage):
    old=baseline.set_index('figure_path')
    rows=[]
    for source in records:
        r=dict(source)
        for key in ['figure_path','full_scale_reference']:
            if not r.get(key): continue
            path=Path(r[key])
            r[key]=str(path.relative_to(stage)) if stage in path.parents else str(path.relative_to(ROOT))
        r['generating_script']=('src/moving_average_all_genres.py' if '/all_genres/' in r['figure_path'] else
            'src/moving_average_figures.py' if 'moving_average' in r['figure_family'] else 'src/descriptive_figures.py')
        reference=r['figure_path'].endswith('_full_scale.png')
        r['is_reference']=reference
        r['original_axis_rule']='New companion reference'
        if r['figure_path'] in old.index:
            b=old.loc[r['figure_path']]
            r['original_axis_rule']=b.original_axis_rule
            for key in ['primary_min','primary_max','axis_min','axis_max','utilization_ratio']:
                r['old_'+key]=b['old_'+key]
            ratio=b.old_utilization_ratio
            # Triage, not an effect-size claim: only nonconstant analytical trajectories.
            if 'moving_average' in r['figure_family'] and not reference and b.old_primary_span>1e-6 and ratio<.25:
                r['issue_detected']='Primary rolling range uses under 25% of old Y-axis; raw/global/domain scale dominates'
            elif 'moving_average' in r['figure_family'] and not reference and ratio<.5:
                r['issue_detected']='Primary rolling range uses 25–50% of old Y-axis; reviewed against raw/global scale'
        r['remaining_issue']=''
        if not reference and 'moving_average' in r['figure_family'] and r['primary_span'] is not None and r['primary_span']>1e-6 and r['utilization_ratio']<.25:
            r['remaining_issue']='Low primary utilization requires review'
        r['review_status']='intentional full-scale reference' if reference else 'reviewed by family; no unresolved presentation issue' if not r['remaining_issue'] else 'needs review'
        rows.append(r)
    result=pd.DataFrame(rows).sort_values('figure_path').reset_index(drop=True)
    if result.figure_path.duplicated().any(): raise ValueError('Duplicate audit figure')
    if not set(baseline.figure_path)<=set(result.figure_path): raise ValueError('Original analytical figure omitted')
    return result


def report(audit, baseline):
    flagged=audit[~audit.is_reference & audit.issue_detected.ne('')]
    lines=['# Repository-wide analytical figure audit','',
        f'Inventoried **{len(baseline)} original analytical PNGs** in 13 families before changes. '
        'A repository image search found none in reports, figures or archive; no decorative images were modified.',
        f'The current catalog contains **{len(audit)} figures**, including useful full-scale companions. '
        f'**{len(flagged)} default figures** were flagged for scale/distribution readability; '
        f'**{int(audit.remaining_issue.ne("").sum())} unresolved flags** remain.', '',
        '## Inventory and audit rules','',
        '`figure_inventory_before.csv` preserves the original inventory, renderer, intended series, axis rule and measured ranges. '
        '`figure_audit.csv` records every current image, the primary range, axis range, utilization, old limits, issue, action and reference availability. '
        'For multi-panel figures, headline metrics describe the least-utilized primary panel; `panels_json` retains every primary panel. '
        'Histogram metrics refer to the linear density panel, boxplot metrics to the X-axis, correlation metrics to the colour axis, '
        'and scatter metrics to the Y-axis. Nonlinear-axis utilization is left blank; a vertical utilization ratio alone is not a distribution-quality measure.', '',
        '- Nonconstant rolling trajectories occupying <25% of the old axis are high-priority flags. 25–50% receives contextual review. '
        'Neither threshold is an effect-size criterion. Constant/ranges ≤0.000001, full-scale references, percentage axes and signed correlation colour axes are reviewed separately, not blindly zoomed.',
        '- Histograms with a >100:1 ratio among positive bin densities get a log-density companion panel using the same bins and complete support. '
        'Zero-density bins remain visible on the linear panel. Legitimate tails are not dropped.',
        '- Shared score boxplots compress near-zero emotion boxes. Defaults show separate central 1.5-IQR whisker views with per-panel outside counts; '
        'a complete 0–1 companion retains all outliers. Genre comparisons and scatterplots retain their complete distributions.', '',
        '## Deterministic presentation rules','',
        '- Older moving-average defaults use only finite **displayed** rolling series: equal weight plus rank sensitivity when present. '
        'Pad observed extrema by 8% of their range; use only a 0.000001 score-unit guard for constant/numerically tiny ranges. '
        'Clamp to [0,1] and round bounds outward at the power-of-ten step `10**floor(log10(padded_span)-1)`. '
        'Zero is not forced. Numeric tick precision follows the actual tick interval, without offsets or scientific notation.',
        '- Raw monthly lines stay faint. Out-of-view raw points are explicitly counted on the chart; whenever any are clipped, '
        'a `_full_scale.png` companion displays every qualifying monthly value on 0–1. Primary rolling values are never clipped. '
        'Sample-size panels, thresholds, date gaps, genre eligibility and rank weighting are unchanged.',
        '- Newer all-genres overlays and their full-scale references retain their previously validated scale rule and image bytes. '
        'Annual plots scale all displayed means AND medians, never discard a subordinate but analytical series.',
        '- Readable 10–13 point text, exterior legends for trajectories, light grids, stable major-genre colours and 300 dpi. '
        'Historical time plots identify 2020 as a neutral reference. Independent classifier axes disclose the theoretical 0–1 domain; '
        'line separation alone does not establish effect magnitude.', '',
        '## Families','', '| Family | Current figures | Flagged defaults |', '|---|---:|---:|']
    for family,g in audit.groupby('figure_family',sort=True):
        lines.append(f'| {family} | {len(g)} | {int((~g.is_reference & g.issue_detected.ne("")).sum())} |')
    country=audit[audit.figure_path.eq('analysis/moving_averages/figures/detox_identity_attack/country.png')].iloc[0]
    lines += ['', '## Regression example: Country / Detoxify identity attack','',
        f'- Old Y-axis: {country.old_axis_min:.8g}–{country.old_axis_max:.8g}. '
        f'New Y-axis: {country.axis_min:.8g}–{country.axis_max:.8g}.',
        f'- Displayed equal/rank-weighted rolling range: {country.primary_min:.8g}–{country.primary_max:.8g}. '
        f'Utilization: {country.old_utilization_ratio:.1%} → {country.utilization_ratio:.1%}.',
        f'- {country.context_points_clipped} qualifying raw monthly points outside the default range; '
        'their faint line is visually clipped and the full-scale companion preserves the complete range. The scored-song panel remains unzoomed.', '',
        '## Validation and visual review','',
        'The renderer checks every primary rolling/annual value against its limits, every visible axis label against the canvas, '
        'source and numerical-artifact hashes, original figure coverage and complete current image catalog. '
        'The manifest stores all current PNG hashes and all protected numerical-file hashes. '
        'Run the presentation rebuild twice and compare the manifest, audit and image hashes; numerical exports are never rewritten.', '',
        'Manual review samples are recorded in [figure_visual_review.md](figure_visual_review.md). '
        'Tests and deterministic rebuild results are reported in the completion sitrep.', '',
        'Rebuild presentation only: `python3 src/figure_audit.py`. Validate published images/data: `python3 src/figure_audit.py --validate`.','']
    return '\n'.join(lines)


def validate():
    manifest=json.loads(MANIFEST.read_text())
    for category in ['numerical_sha256','code_sha256','figure_sha256','audit_sha256']:
        for name,digest in manifest[category].items():
            if d.sha(ROOT/name)!=digest: raise ValueError(category+' changed: '+name)
    actual={str(p.relative_to(ROOT)) for p in ANALYSIS.rglob('*.png')}
    if actual!=set(manifest['figure_sha256']): raise ValueError('Stale or missing generated analytical figures')
    print(f'Validated {len(actual)} figures; {len(manifest["numerical_sha256"])} unchanged numerical/input files',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--validate',action='store_true')
    if parser.parse_args().validate: return validate()
    before=numerical_hashes()
    code={name:d.sha(ROOT/name) for name in CODE}
    baseline=pd.read_csv(BASELINE).fillna('')
    overall,genres,coverage,frame,songs=read_inputs()
    style.RECORDS.clear()
    with tempfile.TemporaryDirectory(prefix='figure-audit-') as tmp:
        stage=Path(tmp)
        ma_stage=stage/'analysis/moving_averages';ma_stage.mkdir(parents=True)
        m.figures(ma_stage,overall,genres,coverage)
        ds_stage=stage/'analysis/milestone2';ds_stage.mkdir(parents=True)
        tables={p.stem:pd.read_csv(p,float_precision='round_trip') for p in (d.OUTPUT/'tables').glob('*.csv')}
        d.figures(ds_stage,frame,songs,tables['genre_summary'],tables['yearly_summary'],tables['availability_by_group'])
        audit=enrich(style.RECORDS+overlay_records(genres),baseline,stage)
        if audit.remaining_issue.ne('').any():
            print(audit.loc[audit.remaining_issue.ne(''),['figure_path','remaining_issue']].to_string(index=False),flush=True)
        audit.to_csv(stage/'analysis/figure_audit.csv',index=False,float_format='%.12g',lineterminator='\n')
        (stage/'analysis/figure_audit.md').write_text(report(audit,baseline))
        # Refresh generated narrative via its generator, leaving every numerical export intact.
        checks=pd.read_csv(m.OUTPUT/'data/trajectory_summary.csv',float_precision='round_trip')
        sensitivity=pd.read_csv(m.OUTPUT/'data/rank_weighting_sensitivity.csv',float_precision='round_trip')
        duplicates=pd.read_csv(m.OUTPUT/'data/duplicate_song_months.csv')
        inventory=pd.read_csv(m.OUTPUT/'data/figure_inventory.csv')
        m.findings(ma_stage,overall,genres,checks,coverage,sensitivity,duplicates,inventory)
        prefix=(ma_stage/'moving_average_findings.md').read_text()
        (ma_stage/'moving_average_findings.md').write_text(prefix+overlays.appendix(genres))
        if before!=numerical_hashes(): raise ValueError('Numerical artifact changed during rendering')
        if code!={name:d.sha(ROOT/name) for name in CODE}: raise ValueError('Code changed during rendering')
        # Update existing provenance instead of replacing numerical manifests with a new analysis.
        for folder in [m.OUTPUT,d.OUTPUT]:
            manifest=json.loads((folder/'manifest.json').read_text())
            if folder==m.OUTPUT:
                manifest['pipeline_sha256']={name:code[name] for name in CODE if name!='src/moving_average_all_genres.py'}
            else:
                manifest['pipeline_sha256']=code['src/descriptive_analysis.py']
                manifest['presentation_pipeline_sha256']=code
            dest=stage/folder.relative_to(ROOT)
            for path in dest.rglob('*.png'):
                manifest['artifacts'][str(path.relative_to(dest))]=d.sha(path)
            if folder==m.OUTPUT:
                import hashlib
                manifest['artifacts']['moving_average_findings.md']=hashlib.sha256(prefix.encode()).hexdigest()
            (dest/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        overlay=json.loads((overlays.OUTPUT/'manifest.json').read_text())
        overlay['code_sha256']={name:code[name] for name in overlay['code_sha256']}
        import hashlib
        overlay['original_findings_prefix_sha256']=hashlib.sha256(prefix.encode()).hexdigest()
        overlay['extended_findings_sha256']=d.sha(ma_stage/'moving_average_findings.md')
        overlay_dest=stage/overlays.OUTPUT.relative_to(ROOT);overlay_dest.mkdir(parents=True,exist_ok=True)
        (overlay_dest/'manifest.json').write_text(json.dumps(overlay,sort_keys=True,indent=2)+'\n')
        hashes={}
        for name in audit.figure_path:
            path=stage/name if (stage/name).exists() else ROOT/name
            hashes[name]=d.sha(path)
        manifest=dict(version=style.VERSION,numerical_sha256=before,code_sha256=code,figure_sha256=hashes,
            audit_sha256={name:d.sha(stage/name) if (stage/name).exists() else d.sha(ROOT/name) for name in
                ['analysis/figure_inventory_before.csv','analysis/figure_audit.csv','analysis/figure_audit.md']},
            regenerated_figures=len(style.RECORDS),retained_overlay_figures=len(overlay['figures']))
        (stage/'analysis/figure_manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        expected=set(audit.figure_path)
        obsolete={str(p.relative_to(ROOT)) for p in ANALYSIS.rglob('*.png')}-expected
        if obsolete: raise ValueError('Unexpected previous figures require explicit review: '+repr(obsolete))
        for p in sorted(stage.rglob('*')):
            if p.is_file():
                target=ROOT/p.relative_to(stage);target.parent.mkdir(parents=True,exist_ok=True);os.replace(p,target)
    validate()
    print(f'Regenerated {len(style.RECORDS)} figures; retained {len(overlay["figures"])} overlays; numerical bytes unchanged.',flush=True)


if __name__=='__main__':main()
