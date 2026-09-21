"""Rebuild numerical diagnostics/report twice in temporary output directories."""
import shutil
import tempfile
from pathlib import Path
import classifier_panel_diagnostics as diagnostics
import classifier_panel_report as report
from classifier_panel import OUT,ROOT,REPORTS
from lyriclens_evaluation import sha

def main():
    generated=('distributions.csv','aggregation_sensitivity.csv','agreement.csv','agreement_cases.csv','extremes.csv','diagnostic_counts.json')
    original=(diagnostics.OUT,diagnostics.ROOT,report.OUT,report.ROOT,report.REPORTS)
    with tempfile.TemporaryDirectory() as name:
        root=Path(name);out=root/'reports/classifier_panel';out.mkdir(parents=True);(root/'docs').mkdir()
        for p in OUT.iterdir():
            if p.name not in generated:shutil.copyfile(p,out/p.name)
        shutil.copyfile(ROOT/'docs/classifier_panel_findings.md',root/'docs/classifier_panel_findings.md')
        try:
            diagnostics.OUT=out;diagnostics.ROOT=root;report.OUT=out;report.ROOT=root;report.REPORTS=root/'reports'
            for _ in range(2):
                diagnostics.main();report.main()
                for p in generated:
                    if sha(out/p)!=sha(OUT/p):raise ValueError('Nondeterministic diagnostics: '+p)
                if sha(root/'docs/classifier_panel_concepts.json')!=sha(ROOT/'docs/classifier_panel_concepts.json'):raise ValueError('Concept mapping changed')
                if sha(root/'reports/classifier_panel_design.md')!=sha(REPORTS/'classifier_panel_design.md'):raise ValueError('Report changed')
        finally:diagnostics.OUT,diagnostics.ROOT,report.OUT,report.ROOT,report.REPORTS=original
    print('Two independent temporary rebuilds match every diagnostic, concept mapping and panel report byte-for-byte.')

if __name__=='__main__':main()
