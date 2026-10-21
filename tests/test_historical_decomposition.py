"""Independent accounting and dependence checks for the bounded historical study."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import historical_decomposition as hd


class AccountingTests(unittest.TestCase):
    def test_two_reference_paths_reconcile_and_reverse(self):
        p0=np.array([[.8],[.2]]);p1=np.array([[.3],[.7]])
        m0=np.array([[.1],[.6]]);m1=np.array([[.2],[.8]])
        got=hd.kitagawa(p0,m0,p1,m1)
        # Means .20 -> .62; average-path within .145, composition .275.
        np.testing.assert_allclose(got['mean0'],.20)
        np.testing.assert_allclose(got['mean1'],.62)
        np.testing.assert_allclose(got['within'].sum(),.145)
        np.testing.assert_allclose(got['composition'].sum(),.275)
        reverse=hd.kitagawa(p1,m1,p0,m0)
        np.testing.assert_allclose(reverse['within'],-got['within'])
        np.testing.assert_allclose(reverse['composition'],-got['composition'])
    def test_pure_composition_and_pure_within_changes(self):
        p0=np.array([[.4],[.6]]);p1=np.array([[.8],[.2]])
        m=np.array([[.1],[.9]])
        composition=hd.kitagawa(p0,m,p1,m)
        np.testing.assert_allclose(composition['within'],0)
        within=hd.kitagawa(p0,m,p0,m+.05)
        np.testing.assert_allclose(within['composition'],0)
        np.testing.assert_allclose(within['within'].sum(),.05)
    def test_entry_exit_is_explicit_and_bounds_contain_other_allocations(self):
        p0=np.array([[1.],[0.],[0.]]);p1=np.array([[.5],[.5],[0.]])
        m0=np.array([[.2],[np.nan],[np.nan]]);m1=np.array([[.3],[.8],[np.nan]])
        got=hd.kitagawa(p0,m0,p1,m1)
        self.assertEqual(got['within'][1,0],0)
        self.assertTrue(got['entry_exit'][1,0]);self.assertFalse(got['entry_exit'][2,0])
        np.testing.assert_allclose(got['delta'],.35)
        self.assertTrue(np.isnan(m0[1,0]))
        for missing_mean in [0,.5,1]:
            filled=m0.copy();filled[1,0]=missing_mean
            alternative=hd.kitagawa(p0,filled,p1,m1) # entry convention is always explicit
            np.testing.assert_allclose(alternative['delta'],got['delta'])
            allocation=.75*.1+.25*(.8-missing_mean)
            self.assertLessEqual(got['within_allocation_low'][0],allocation+1e-12)
            self.assertGreaterEqual(got['within_allocation_high'][0],allocation-1e-12)
    def test_positive_share_missing_mean_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'positive-share'):
            hd.kitagawa([[1]],[[np.nan]],[[1]],[[.4]])
    def test_missing_values_do_not_enter_observed_denominator(self):
        frame=pd.DataFrame(dict(primary_genre=['A','A','B'],song_id=['1','2','3'],
            artist=['X','X','Y'],month=['2000-01']*3,weight=[1.,3.,2.],score=[0.,np.nan,1.]))
        got=hd.cell_summary(frame,['score'],['A','B','absent'])
        np.testing.assert_allclose(got['observed_mean'],2/3)
        np.testing.assert_allclose(got['share'][:,0],[1/3,2/3,0])
        self.assertEqual(got['mean'][0,0],0);self.assertTrue(np.isnan(got['mean'][2,0]))
        self.assertEqual(got['coverage'][0],.5)
    def test_mar_scenario_changes_population_without_zero_imputation(self):
        frame=pd.DataFrame(dict(primary_genre=['A','A','B'],song_id=['1','2','3'],
            artist=['X','X','Y'],month=['2000-01']*3,weight=[1.,3.,2.],score=[.2,np.nan,.8]))
        got=hd.cell_summary(frame,['score'],['A','B'])
        share,mean,fallback=hd.missing_scenario(got,0)
        np.testing.assert_allclose((share*mean).sum(),.4)
        np.testing.assert_allclose(mean[:,0],[.2,.8]);np.testing.assert_allclose(fallback,0)
        self.assertTrue(np.isnan(frame.score.iloc[1]))
    def test_unique_song_weighting_preserves_cross_period_membership(self):
        frame=pd.DataFrame(dict(song_id=['a','a','a','b'],year=[1998,1999,2000,2001],rank_weight=[2,1,3,4]))
        left=hd.period_frame(frame,'1990s','unique_song');right=hd.period_frame(frame,'2000s','unique_song')
        self.assertEqual(left.song_id.tolist(),['a']);self.assertEqual(right.song_id.tolist(),['a','b'])
        self.assertEqual(left.weight.sum(),1);self.assertEqual(right.weight.sum(),2)


class DependenceTests(unittest.TestCase):
    def test_frozen_identity_survives_saved_json_round_trip(self):
        identity=hd.source_identity()
        self.assertEqual(identity,json.loads(json.dumps(identity)))
    def test_cluster_weights_are_shared_positive_and_deterministic(self):
        artists=['same','same','other'];months=[24000,24000,24001]
        a=np.concatenate(list(hd.multiplier_batches(artists,months,100,'fixture')))
        b=np.concatenate(list(hd.multiplier_batches(artists,months,100,'fixture')))
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(a[:,0],a[:,1])
        self.assertTrue((a>0).all());self.assertFalse(np.array_equal(a[:,0],a[:,2]))
    def test_calendar_correlation_falls_with_distance(self):
        values=np.concatenate(list(hd.multiplier_batches(['a']*3,[24000,24001,24100],4000,'calendar',mode='calendar_only')))
        covariance=np.corrcoef(values.T)
        self.assertGreater(covariance[0,1],.85);self.assertLess(abs(covariance[0,2]),.1)
    def test_no_month_independence_in_artist_only_resampling(self):
        w=np.concatenate(list(hd.multiplier_batches(['a','a','b'],[1,100,100],30,'artist',mode='artist_only')))
        np.testing.assert_array_equal(w[:,0],w[:,1]);self.assertFalse(np.array_equal(w[:,1],w[:,2]))
    def test_centered_bootstrap_resolution_and_zero_effect(self):
        values=np.linspace(-1,1,999)[:,None]
        u=hd.uncertainty(np.array([0.]),values)
        self.assertEqual(u['p'][0],1.)
        u=hd.uncertainty(np.array([10.]),values+10)
        self.assertEqual(u['p'][0],.001)
    def test_complete_primary_family_is_fixed_before_outcomes(self):
        self.assertEqual(len(hd.COMPARISONS),7);self.assertEqual(len(hd.PRIMARY),11)
        self.assertEqual(hd.BREAKS,list(range(1970,2021,5)))
        self.assertEqual(hd.HYPOTHESES,715);self.assertEqual(len(hd.FEATURES),42)


class SegmentedTests(unittest.TestCase):
    def frame(self):
        months=np.arange(2014*12,2026*12)
        return pd.DataFrame(dict(month_index=months,month=[str(x//12)+'-'+str(x%12+1).zfill(2) for x in months],
            primary_genre=['A']*144,song_id=[str(i) for i in range(144)],artist=[str(i//3) for i in range(144)],rank_weight=np.ones(144)))
    def test_known_level_and_slope_recovered_on_fixed_calendar(self):
        frame=self.frame();x,_=hd.design(frame,2020*12)
        beta=np.zeros((x.shape[1],1));beta[:4,0]=[.3,.01,.08,-.02]
        frame['score']=(x@beta)[:,0]
        result=hd.breakpoint_group(frame,['score'],2020,repeats=4)
        np.testing.assert_allclose(result['beta'],[[.08,-.02]],atol=1e-12)
        np.testing.assert_allclose(result['draws'],np.tile([[[.08,-.02]]],(4,1,1)),atol=1e-10)
    def test_point_weights_equal_monthly_mean_regression(self):
        frame=self.frame();frame['score']=.2+.001*np.arange(144)+.03*np.sin(np.arange(144))
        doubled=pd.concat([frame,frame.iloc[:30].assign(score=.5,song_id='extra')],ignore_index=True)
        result=hd.breakpoint_group(doubled,['score'],2020,do_bootstrap=False)
        x,_=hd.design(frame,2020*12)
        means=doubled.groupby('month_index').score.mean().to_numpy()
        ref=np.linalg.lstsq(x,means,rcond=None)[0]
        np.testing.assert_allclose(result['beta'][0],ref[[2,3]],atol=1e-12)
    @unittest.skipUnless(importlib.util.find_spec('statsmodels'),'Optional independent HAC reference')
    def test_hac_matches_independent_statsmodels_monthly_calculation(self):
        import statsmodels.api as sm
        from statsmodels.stats.sandwich_covariance import cov_hac
        frame=self.frame();x,_=hd.design(frame,2020*12)
        rng=np.random.default_rng(81);y=.3+.01*x[:,1]+rng.normal(0,.02,len(frame))
        beta=hd.weighted_fit(x,y[:,None],np.ones(len(frame)))
        ours=hd.hac_intervals(x,y[:,None],np.ones(len(frame)),beta,frame.month_index.to_numpy())
        ref=cov_hac(sm.OLS(y,x).fit(),nlags=24,use_correction=True)
        np.testing.assert_allclose(ours['se'][:,0],np.sqrt(np.diag(ref))[[2,3]],rtol=1e-10,atol=1e-12)


if __name__=='__main__':unittest.main()
