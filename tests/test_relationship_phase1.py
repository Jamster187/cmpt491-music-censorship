"""Approval boundary, exhaustive coverage and restart integrity for Phase 1."""
import copy
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scipy import stats
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import relationship_phase1 as phase
import relationship_discovery_stats as inference


class PhaseOneTests(unittest.TestCase):
    def test_full_universe_is_exact_unique_and_deterministic(self):
        rows=phase.candidates();again=phase.candidates()
        self.assertEqual(rows,again)
        self.assertEqual(len(rows),9159)
        self.assertEqual(len({r['candidate_id'] for r in rows}),9159)
        self.assertEqual(set(r['family'] for r in rows),set(phase.FAMILIES))
        self.assertEqual([r['candidate_id'] for r in rows],sorted(r['candidate_id'] for r in rows))
        self.assertTrue(any(r['category'].startswith('A') for r in rows))
    def test_checkpoints_reject_corruption_and_changed_protocol(self):
        row=dict(phase.candidates()[0],status='ok',effect=.2,p_value=.03,evaluation_label=phase.LABEL)
        with tempfile.TemporaryDirectory() as directory,patch.object(phase,'LOCAL',Path(directory)):
            phase.save_checkpoint(row,'version1')
            self.assertEqual(phase.read_checkpoint(phase.candidates()[0],'version1'),row)
            with self.assertRaisesRegex(ValueError,'integrity'):
                phase.read_checkpoint(phase.candidates()[0],'version2')
            path=phase.checkpoint_path(row)
            data=json.loads(gzip.decompress(path.read_bytes()));data['result']['effect']=.8
            path.write_bytes(gzip.compress(json.dumps(data).encode()))
            with self.assertRaisesRegex(ValueError,'integrity'):
                phase.read_checkpoint(phase.candidates()[0],'version1')
    def test_global_by_denominator_includes_every_failed_candidate(self):
        rows=[dict(r,p_value=.000030517578125 if i<20 else None,status='ok' if i<20 else 'failed') for i,r in enumerate(phase.candidates())]
        inference.adjust_multiple_testing(rows)
        expected=stats.false_discovery_control([.000030517578125]*20+[1.]*9139,method='by')
        np.testing.assert_array_equal(expected,[r['q_by_global'] for r in rows])
        self.assertTrue(all(r['q_by_global']==1 for r in rows[20:]))
        self.assertTrue(all(not r['independent_confirmation'] for r in rows))
    def test_expected_numerical_failure_is_retained(self):
        candidate=phase.candidates()[0]
        with patch.object(phase.engine,'execute',side_effect=ValueError('bad numeric example')):
            row=phase.execute(candidate)
        self.assertEqual(row['candidate_id'],candidate['candidate_id'])
        self.assertEqual(row['status'],'failed');self.assertIsNone(row['p_value'])
        self.assertTrue(row['fit_count_unknown'])
        self.assertIn('bad numeric example',row['error'])
    def test_unexpected_programming_error_is_not_silently_swallowed(self):
        with patch.object(phase.engine,'execute',side_effect=KeyError('bug')):
            with self.assertRaises(KeyError):phase.execute(phase.candidates()[0])
    def test_prior_protocol_source_bytes_remain_frozen(self):
        lock=json.loads((ROOT/'analysis/relationship_discovery/pilot_protocol.json').read_text())
        for name,digest in lock['identity']['code_sha256'].items():
            self.assertEqual(phase.engine.old.original.sha(ROOT/name),digest,name)




class ArtistSensitivityTests(unittest.TestCase):
    def test_weighted_numeric_and_nominal_estimators_match_expanded_rows(self):
        import relationship_phase1_analysis as analysis
        x=np.array([1.,2.,4.,8.]);y=np.array([9.,3.,5.,1.]);g=np.array([0,0,1,1]);h=np.array([0,1,1,0]);w=np.array([3,1,4,2])
        ix=np.repeat(np.arange(4),w)
        self.assertAlmostEqual(analysis.weighted_correlation(x,y,w),np.corrcoef(x[ix],y[ix])[0,1])
        self.assertAlmostEqual(analysis.weighted_eta(g,y,w),inference.eta_squared(g[ix],y[ix]))
        self.assertAlmostEqual(analysis.weighted_v(g,h,w),inference.cramers_v(g[ix],h[ix]))
    def test_artist_resampling_preserves_equal_block_effect(self):
        import pandas as pd
        import relationship_phase1_analysis as analysis
        frame=pd.DataFrame({'artist':['a','b','a','c','c','c'],'debut_year':[2000,2000,2002,2002,2002,2002],
            'normalized_loss_gain':[2.,0.,1.,3.,5.,7.],'seen_artist_in_training':[True,False,True,False,False,False]})
        result=analysis.artist_prediction_interval(frame,'fixture',repeats=99)
        self.assertEqual(result['effect'],2.5) # block means 1 and 4, equal block weights
        self.assertEqual(result['artist_credits'],3)
        self.assertEqual(result['largest_credit_song_share'],.5)
        self.assertEqual(result,analysis.artist_prediction_interval(frame,'fixture',repeats=99))
    def test_shared_lyric_scores_stay_cross_category_but_not_cross_source_priority(self):
        import relationship_phase1_analysis as analysis
        row=phase.spec.candidate('nonlinear','detox_insult',['emotion_anger'])
        self.assertTrue(row['category'].startswith('C'))
        self.assertFalse(analysis.priority_cross(row))
        row=phase.spec.candidate('nonlinear','chart_weeks',['emotion_anger'])
        self.assertTrue(analysis.priority_cross(row))
    def test_large_relative_gain_with_negative_r2_is_not_positive_utility(self):
        import relationship_phase1_analysis as analysis
        row=dict(evaluated_periods=4,r2=-3,skill=.9,stability_fraction=1,ci_low=.5)
        self.assertFalse(analysis.utility_tier(row))
        row['r2']=.1
        self.assertTrue(analysis.utility_tier(row))
    def test_period_sign_changes_require_substantial_opposed_signs_and_coverage(self):
        import relationship_phase1_analysis as analysis
        row=phase.spec.candidate('genre_interaction','chart_weeks',['emotion_anger'],'primary_genre')
        row['diagnostics']=[dict(period=[1990,2000],conditional_correlations=dict(marginal_spearman=-.2,n_complete=250)),
            dict(period=[2018,2026],conditional_correlations=dict(marginal_spearman=.3,n_complete=250))]
        result=analysis.period_sign_records([row])[0]
        self.assertTrue(result['period_sign_reversal']);self.assertTrue(result['descriptive_only'])
        row['diagnostics'][1]['conditional_correlations']['n_complete']=199
        self.assertFalse(analysis.period_sign_records([row])[0]['period_sign_reversal'])
        row['diagnostics'][1]['conditional_correlations'].update(n_complete=250,marginal_spearman=.02)
        self.assertFalse(analysis.period_sign_records([row])[0]['period_sign_reversal'])
    def test_reversal_flags_do_not_promote_inadequate_genre_cells(self):
        import relationship_phase1_analysis as analysis
        row=phase.spec.candidate('genre_interaction','chart_weeks',['emotion_anger'],'primary_genre')
        row.update(q_by_global=1.,diagnostics=[dict(period=[1990,2000],conditional_correlations=dict(n_complete=500,
            marginal_spearman=.2,partial_spearman=.15,subgroups=[dict(group='Pop',adequate=True,n=490,spearman=.2),
                dict(group='Rock',adequate=False,n=10,spearman=-.8)]))])
        result=analysis.reversal_records([row])[0]
        self.assertFalse(result['opposed_genre_signs']);self.assertTrue(result['descriptive_only'])
    def test_failed_numeric_pair_keeps_its_variable_type(self):
        import relationship_phase1_analysis as analysis
        row=phase.spec.candidate('pairwise','mb_release_count',['chart_weeks'])
        row.update(status='failed',n=0,p_value=None,q_by_global=1.)
        views=analysis.rank_views([row])
        self.assertEqual([r['candidate_id'] for r in views['cross_numeric']],[row['candidate_id']])
        self.assertEqual(views['cross_categorical'],[])


class PreservationCacheTests(unittest.TestCase):
    def fixture(self,root):
        source=root/'analysis/pilot/render.py';cache=source.parent/'__pycache__/render.cpython-39.pyc';data=root/'data.csv'
        cache.parent.mkdir(parents=True);source.write_text('pass\n');cache.write_bytes(b'old compiled cache');data.write_bytes(b'unchanged data')
        snapshot=root/'local/preservation.json'
        phase.engine.write_json(snapshot,dict(sha256={str(p.relative_to(root)):phase.engine.old.original.sha(p) for p in [source,cache,data]}))
        cache.write_bytes(b'regenerated compiled cache')
        return source,cache,data,snapshot
    def test_only_cache_is_excluded_after_source_and_data_verification(self):
        import relationship_phase1_prepare as prepare
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,cache,data,snapshot=self.fixture(root);original=snapshot.read_bytes()
            with patch.object(phase,'LOCAL',root/'local'),patch.object(phase.spec,'ROOT',root):result=prepare.prepare_preservation()
            self.assertEqual(len(result['excluded_runtime_caches']),1)
            self.assertEqual(result['protected_files'],2)
            self.assertEqual((root/'local/preservation_with_runtime_caches.json').read_bytes(),original)
            self.assertEqual(source.read_text(),'pass\n');self.assertEqual(data.read_bytes(),b'unchanged data')
            self.assertIn('analysis/pilot/render.py',json.loads(snapshot.read_text())['sha256'])
    def test_changed_source_or_data_cannot_be_hidden_by_cache_exclusion(self):
        import relationship_phase1_prepare as prepare
        for change in ('source','data'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);source,cache,data,snapshot=self.fixture(root);original=snapshot.read_bytes()
                (source if change=='source' else data).write_text('unexpected change')
                with patch.object(phase,'LOCAL',root/'local'),patch.object(phase.spec,'ROOT',root):
                    with self.assertRaises(ValueError):prepare.prepare_preservation()
                self.assertEqual(snapshot.read_bytes(),original)


if __name__=='__main__':unittest.main()
