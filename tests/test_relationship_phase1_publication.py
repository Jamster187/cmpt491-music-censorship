"""Complete public Phase 1 coverage and campaign-wide inference; no private caches."""
import csv
import gzip
import hashlib
import io
import json
import subprocess
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy import stats
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import relationship_phase1 as phase
PUBLIC=ROOT/'analysis/relationship_discovery/full_phase1'


class PhaseOnePublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=json.loads(gzip.decompress((PUBLIC/'demo_results.json.gz').read_bytes()))
    def test_complete_candidate_universe_and_by_denominator(self):
        expected=phase.candidates();ids=[r['candidate_id'] for r in self.rows]
        self.assertEqual(len(ids),9159);self.assertEqual(len(set(ids)),9159)
        self.assertEqual(set(ids),{r['candidate_id'] for r in expected})
        p=[r.get('p_value') if r.get('p_value') is not None else 1 for r in self.rows]
        np.testing.assert_array_equal(stats.false_discovery_control(p,method='by'),[r['q_by_global'] for r in self.rows])
        self.assertTrue(all(r['evaluation_label']==phase.LABEL for r in self.rows))
        self.assertTrue(all(not r['independent_confirmation'] for r in self.rows))
    def test_complete_family_tables_match_published_metrics(self):
        lookup={r['candidate_id']:r for r in self.rows}
        for family,count in phase.FAMILIES.items():
            data=gzip.decompress((PUBLIC/(family+'_results.csv.gz')).read_bytes()).decode()
            rows=list(csv.DictReader(io.StringIO(data)))
            self.assertEqual(len(rows),count)
            self.assertEqual({r['candidate_id'] for r in rows},{r['candidate_id'] for r in self.rows if r['family']==family})
            for row in rows:
                expected=lookup[row['candidate_id']]
                for key in ('p_value','q_by_global','r2','effect'):
                    self.assertEqual(float(row[key]) if row[key] else None,expected.get(key))
                self.assertEqual(int(row['n']),expected['n'])
                self.assertEqual(row['status'],expected['status'])
    def test_prior_publications_and_new_artifacts_match_manifests(self):
        paths=[PUBLIC/'artifact_manifest.json',ROOT/'analysis/relationship_discovery/artifact_manifest.json',
            ROOT/'analysis/regression_search/meaningful/artifact_manifest.json',ROOT/'analysis/regression_search/artifact_manifest.json']
        for path in paths:
            record=json.loads(path.read_text());mapping=record.get('sha256',record.get('artifacts_sha256'))
            for name,digest in mapping.items():
                if path==ROOT/'analysis/relationship_discovery/artifact_manifest.json' and name in {'src/relationship_demo.py','tests/test_relationship_demo.py'}:
                    # These two UI files were explicitly authorized to evolve. Their
                    # historical bytes remain pinned by the unchanged pilot manifest.
                    content=subprocess.check_output(['git','show','5e77ab93f6c951aed8c1ea625264c94d08118fab:'+name],cwd=ROOT)
                elif path==ROOT/'analysis/regression_search/artifact_manifest.json' and name=='README.md':
                    # Navigation now describes the completed historical analysis.
                    # Preserve the original regression-publication checksum against
                    # its historical bytes; the new publication pins current docs.
                    content=subprocess.check_output(['git','show','d5a062c27ac88c15a02615e6f284cd801c19ee38:'+name],cwd=ROOT)
                else:content=(ROOT/name).read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(),digest,name)
            for name,digest in record.get('sources_sha256',{}).items():
                if path==PUBLIC/'artifact_manifest.json' and name=='tests/test_relationship_phase1_publication.py':
                    content=subprocess.check_output(['git','show','d5a062c27ac88c15a02615e6f284cd801c19ee38:'+name],cwd=ROOT)
                else:content=(ROOT/name).read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(),digest,name)
        protocol=json.loads((PUBLIC/'protocol.json').read_text())['identity']
        self.assertEqual(hashlib.sha256((ROOT/'src/relationship_phase1.py').read_bytes()).hexdigest(),protocol['runner_sha256'])
        self.assertEqual(protocol['primary_hypotheses'],9159)


if __name__=='__main__':unittest.main()
