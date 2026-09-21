"""Reconcile artifacts, review notes and deterministic public pilot diagnostics."""
import json
import shutil
import tempfile
from pathlib import Path
from collections import Counter
import detoxify_diagnostics as diagnostics
import detoxify_report as report
from detoxify_evaluation import WORK, REPORTS, ROOT, LABELS, validate, sha
from lyriclens_evaluation import read_csv
from public_dataset import public_cell


def main():
    validate()
    pins=json.loads((REPORTS/'detoxify_artifacts.json').read_text())
    if sha(WORK/'toxic_debiased-c7548aa0.ckpt')!=pins['checkpoint_sha256']:raise ValueError('Checkpoint changed')
    for group in ('source','tokenizer'):
        for name,h in pins[group].items():
            if sha(WORK/group/name)!=h:raise ValueError('Artifact changed: '+name)
    review=read_csv(REPORTS/'detoxify_review.csv')
    notes=json.loads((ROOT/'docs/detoxify_review_notes.json').read_text())['annotations']
    selected=diagnostics.select_review(diagnostics.joined())
    if len(review)!=50 or {r['song_id'] for r in review}!=set(notes):raise ValueError('Review identities changed')
    for row,expected in zip(review,selected):
        if row!=dict(expected,**notes[expected['song_id']]):raise ValueError('Review differs from selection/notes')
        for key in ('lyriclens_judgment','detoxify_judgment'):
            if row[key] not in ('plausible','questionable','clearly_wrong'):raise ValueError('Unknown judgment')
    preds={r['song_id']:r for r in read_csv(REPORTS/'detoxify_predictions.csv')}
    probes=read_csv(REPORTS/'detoxify_sensitivity.csv')
    if len(probes)!=24 or Counter(r['variant'] for r in probes)!={'original_replay':8,'unique_lines':8,'tail_510_tokens':8}:raise ValueError('Sensitivity rows changed')
    from detoxify_sensitivity import TITLES
    if {r['title'] for r in probes}!=set(TITLES):raise ValueError('Sensitivity set changed')
    if len({(r['song_id'],r['variant']) for r in probes})!=24:raise ValueError('Repeated sensitivity rows')
    for r in probes:
        p=preds[r['song_id']]
        if r['title']!=p['title'] or r['artist']!=p['artist']:raise ValueError('Sensitivity identity changed')
        if not 2<=int(r['input_tokens'])<=512:raise ValueError('Invalid input length')
        for k in LABELS:
            if not 0<=float(r[k])<=1:raise ValueError('Invalid probe score')
            if r['variant']=='original_replay' and abs(float(r[k])-float(p[k]))>1e-6:raise ValueError('Replay mismatch')
    for name in ('detoxify_predictions.csv','detoxify_review.csv','detoxify_sensitivity.csv','detoxify_extremes.csv'):
        for r in read_csv(REPORTS/name):
            for value in r.values():public_cell(value)
    generated=['detoxify_diagnostics.json','detoxify_review.csv','detoxify_evaluation.md','detoxify_extremes.csv']
    original=diagnostics.REPORTS,report.REPORTS
    with tempfile.TemporaryDirectory() as temp:
        target=Path(temp)
        for name in ('lyriclens_predictions.csv','detoxify_predictions.csv','detoxify_raw_outputs.jsonl','detoxify_run.json'):
            shutil.copyfile(REPORTS/name,target/name)
        try:
            diagnostics.REPORTS=target;report.REPORTS=target
            for _ in range(2):
                diagnostics.main();report.main()
                for name in generated:
                    if sha(target/name)!=sha(REPORTS/name):raise ValueError('Nondeterministic report: '+name)
        finally:diagnostics.REPORTS,report.REPORTS=original
    print('Validated pinned artifacts, 50 exact review rows, 24 sensitivity rows, public cell safety and two deterministic report rebuilds.')

if __name__=='__main__':main()
