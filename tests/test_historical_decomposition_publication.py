"""Verify published historical evidence without private caches or new inference."""
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'analysis/historical_decomposition'


class PublishedHistoricalTests(unittest.TestCase):
    def test_publication_hashes_accounting_and_previous_monthly_values(self):
        spec=importlib.util.spec_from_file_location('historical_public_verify',PUBLIC/'verify.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        result=module.verify()
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['previous_monthly_score_cells_checked'],66*12*42)

    def test_missingness_bounds_and_sparse_cells_are_explicit(self):
        h=pd.read_csv(PUBLIC/'historical_comparisons.csv')
        s=pd.read_csv(PUBLIC/'sensitivity_results.csv')
        bounds=s[s.scenario=='unrestricted_0_1_bounds'].set_index(['comparison','classifier'])
        primary=h[h.weighting=='song_month'].set_index(['comparison','classifier']).loc[bounds.index]
        low=primary.coverage1*primary.mean1-(primary.coverage0*primary.mean0+1-primary.coverage0)
        high=primary.coverage1*primary.mean1+1-primary.coverage1-primary.coverage0*primary.mean0
        np.testing.assert_allclose(bounds.delta_low,low,atol=1e-12)
        np.testing.assert_allclose(bounds.delta_high,high,atol=1e-12)
        d=pd.read_csv(PUBLIC/'decomposition_results.csv')
        self.assertEqual(d.groupby(['comparison','weighting','classifier']).genre.nunique().min(),16)
        self.assertTrue(d['sparse'].any())
        absent=d.mean0.isna()|d.mean1.isna()
        self.assertTrue((d.loc[absent,'within']==0).all())

    def test_fixed_design_and_provenance_remain_visible(self):
        t=pd.read_csv(PUBLIC/'primary_tests.csv')
        self.assertEqual(t.groupby('family').size().to_dict(),{'breakpoint':484,'decomposition':231})
        old=pd.read_csv(PUBLIC/'precision_999_primary_tests.csv')
        self.assertEqual(set(old.test_id),set(t.test_id))
        claims=pd.read_csv(PUBLIC/'preliminary_claims_audit.csv')
        self.assertFalse(claims.original_code_available.any())
        self.assertFalse(claims.original_weighting_verified.any())
        figures=json.loads((PUBLIC/'figure_index.json').read_text())
        self.assertEqual(len(figures),8)
        for f in figures:
            self.assertTrue((PUBLIC/f['svg']).is_file())


if __name__=='__main__':unittest.main()
