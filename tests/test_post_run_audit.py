"""Synthetic exact-identity regressions for the read-only cross-store audit."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from post_run_audit import validate_snapshot


class AuditSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.identities = {'s': ('s', 'Example!', 'Artist Featuring Guest', '2000-01-01')}
        self.assets = {'s': dict(zip(('song_id','title','artist','first_chart_date'),self.identities['s']))}

    def test_exact_snapshot_matches(self):
        validate_snapshot(self.identities,self.assets)

    def test_credit_punctuation_date_and_payload_id_cannot_drift(self):
        for key,value in [('artist','Artist'),('title','Example'),('first_chart_date','2001-01-01'),('song_id','other')]:
            with self.subTest(key=key):
                altered={'s':dict(self.assets['s'],**{key:value})}
                with self.assertRaises(ValueError): validate_snapshot(self.identities,altered)

    def test_missing_and_extra_members_refused(self):
        for altered in ({},dict(self.assets,extra=self.assets['s'])):
            with self.assertRaises(ValueError): validate_snapshot(self.identities,altered)
