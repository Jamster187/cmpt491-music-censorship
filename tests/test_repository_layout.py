"""Structural regressions without recomputing or changing research results."""
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import repository_layout as r
import descriptive_analysis as d
import moving_average_analysis as m
import moving_average_all_genres as a


class RepositoryLayoutTests(unittest.TestCase):
    def test_entry_points_publish_to_current_analysis_paths(self):
        self.assertEqual(d.OUTPUT,r.ROOT/'analysis/milestone2')
        self.assertEqual(m.OUTPUT,r.ROOT/'analysis/moving_averages')
        self.assertEqual(a.REPORT,m.OUTPUT)
        self.assertEqual(a.OUTPUT,m.OUTPUT/'figures/all_genres')
        self.assertTrue((d.OUTPUT/'tables/summary_statistics.csv').is_file())

    def test_artifacts_links_frozen_implementation_and_ignore_rules(self):
        result=r.validate()
        self.assertGreaterEqual(result['immutable_artifacts_checked'],647)
        self.assertEqual(result['stale_active_paths'],0)
        self.assertEqual(result['private_tracked_files'],0)

    def test_manifest_covers_relocation_and_preserved_alias(self):
        manifest=json.loads(r.MANIFEST.read_text())
        self.assertGreater(len(manifest['moves']),600)
        for old,new in manifest['moves'].items():
            p=r.ROOT/new
            if new in r.OPTIONAL_PLAIN and not p.exists():continue
            self.assertTrue(p.is_file(),new)
        for alias,target in manifest['compatibility_aliases'].items():
            self.assertEqual((r.ROOT/alias).resolve(),(r.ROOT/target).resolve())


if __name__=='__main__':
    unittest.main()
