"""V5 native-time, rank-preserving inference and restart regression tests."""
import collections
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.sandwich_covariance import cov_hac
import pairwise_v5_common as c
import pairwise_v5_data as data
import pairwise_v5_stats as s
import pairwise_v5_runner as runner
import pairwise_v5_diagnostics as diagnostics
import pairwise_v5_report as report


class EstimatorTests(unittest.TestCase):
    def fixture(self):
        rng=np.random.default_rng(719); n=400; x=rng.normal(size=n); z=rng.normal(size=n)
        controls=np.column_stack([np.ones(n),z,z*2,np.zeros(n)])
        y=(1.7*x+3*z+rng.normal(size=n))[:,None]
        return x,y,controls

    def test_redundant_control_span_matches_full_svd(self):
        x,y,controls=self.fixture(); fit=s.numeric_fit(x,y,controls,np.arange(len(x)),len(x),8)
        reference=np.linalg.lstsq(np.column_stack([controls,x]),y,rcond=1e-10)[0]
        self.assertEqual(fit['rank'],2)
        np.testing.assert_allclose(fit['beta'],reference[-1],rtol=1e-12,atol=1e-12)

    def test_hac_matches_independent_statsmodels(self):
        x,y,controls=self.fixture(); n=len(x)
        fit=s.numeric_fit(x,y,controls,np.arange(n),n,8)
        reference=sm.OLS(y[:,0],np.column_stack([controls[:,:2],x])).fit()
        np.testing.assert_allclose(fit['se'],np.sqrt(cov_hac(reference,nlags=8,use_correction=True)[-1,-1]),rtol=1e-11)

    def test_calendar_gap_hac_does_not_compress_rows(self):
        score=np.array([1.,2.,3.]); positions=np.array([0,1,4]); actual=s.hac_variance(score,positions,5,2)[0]
        self.assertAlmostEqual(actual,14+2*(1-1/3)*2)
        self.assertNotAlmostEqual(actual,s.hac_variance(score,np.arange(3),3,2)[0])

    def test_control_basis_uses_training_only_and_rejects_new_span(self):
        controls=np.column_stack([np.ones(30),np.arange(30.),np.zeros(30)])
        basis=s.control_basis(controls); before=basis.transform.copy()
        future=np.array([[1.,40.,1.],[1.,41.,0.]])
        _,supported=basis.apply(future)
        np.testing.assert_array_equal(supported,[False,True]); np.testing.assert_array_equal(before,basis.transform)

    def test_collinear_external_has_no_identifiable_effect(self):
        _,y,controls=self.fixture()
        fit=s.numeric_fit(controls[:,1],y,controls,np.arange(len(y)),len(y),8)
        self.assertIsNone(fit)

    def test_categorical_omnibus_invariant_to_relabeling(self):
        rng=np.random.default_rng(91); n=360; x=np.resize(['alpha','beta','gamma'],n)
        y=(np.where(x=='alpha',-1.,np.where(x=='beta',1.,0.))+rng.normal(size=n))[:,None]
        controls=np.ones((n,1)); a,_=s.categorical_fit(x,y,controls,np.arange(n),n,8)
        renamed=np.array([{'alpha':'z','beta':'b','gamma':'a'}[v] for v in x])
        b,_=s.categorical_fit(renamed,y,controls,np.arange(n),n,8)
        np.testing.assert_allclose(a['p'],b['p'],rtol=1e-10)
        np.testing.assert_allclose(a['eta'],b['eta'],rtol=1e-12)

    def test_weighted_point_matches_weighted_least_squares(self):
        x,y,controls=self.fixture(); weights=np.arange(len(x))+1
        beta,_=s.weighted_point(x,y,controls,weights)
        ref=sm.WLS(y[:,0],np.column_stack([controls[:,:2],x]),weights=weights).fit()
        np.testing.assert_allclose(beta,ref.params[-1],rtol=1e-12)

    def test_transfer_has_explicit_baseline_and_no_training_leak(self):
        rng=np.random.default_rng(12); n=400; x=rng.normal(size=n); y=(2*x+rng.normal(size=n)*.1)[:,None]
        controls=np.ones((n,1)); train=np.arange(n)<250; valid=np.arange(n)>=300
        value=s.forecast(x,y,controls,train,valid,'M')
        self.assertEqual(value['status'],0); self.assertGreater(value['skill'][0],.98)
        changed=y.copy(); changed[250:300]=1e90
        second=s.forecast(x,changed,controls,train,valid,'M')
        np.testing.assert_array_equal(value['skill'],second['skill'])

    def test_by_matches_reference_including_invalid_slots(self):
        p=np.array([1e-8,.002,.04,.8,1.,1.,1.]); q=s.by_adjust(p)
        np.testing.assert_allclose(q,multipletests(p,method='fdr_by')[1],rtol=1e-14)
        self.assertGreater(q[0],s.by_adjust(p[:4])[0])
        with self.assertRaises(ValueError): s.by_adjust([np.nan])

    def test_missingness_masks_keep_pair_specific_sample_sizes(self):
        rng=np.random.default_rng(18); n=600; x=rng.normal(size=n); y=rng.normal(size=(n,2)); y[:50,1]=np.nan
        controls=np.ones((n,1)); a=s.Aligned(y,x,controls,controls,np.ones(n),np.isfinite(y).astype(int),
            np.arange(n),np.arange(n),np.arange(n),['a','b'],['time','time'],'M')
        result,_=s.evaluate(a,{'external_kind':'numeric','track':'raw'},[.001,.001],.001)
        np.testing.assert_array_equal(result['n'],[600,550]); self.assertTrue(np.all(result['status']==0))
        self.assertTrue(np.all(result['inferential']==1))

    def test_failed_stationarity_keeps_estimate_but_blocks_inference(self):
        rng=np.random.default_rng(19); n=600; x=rng.normal(size=n); y=(x+rng.normal(size=n)*.2)[:,None]
        controls=np.ones((n,1)); a=s.Aligned(y,x,controls,controls,np.ones(n),np.ones((n,1),int),
            np.arange(n),np.arange(n),np.arange(n),['a'],['time'],'M')
        result,_=s.evaluate(a,{'external_kind':'numeric','track':'raw'},[.7],.001)
        self.assertEqual(result['status'][0],0); self.assertEqual(result['inferential'][0],0)
        self.assertGreater(result['r'][0],.9)

    def test_sparse_genre_series_does_not_pass_block_support(self):
        rng=np.random.default_rng(20); n=200; x=rng.normal(size=n); y=rng.normal(size=(n,1)); controls=np.ones((n,1))
        a=s.Aligned(y,x,controls,controls,np.ones(n),np.ones((n,1),int),np.arange(n),np.arange(n),np.arange(n),['a'],['time'],'M')
        result,_=s.evaluate(a,{'external_kind':'numeric','track':'raw'},[.001],.001)
        self.assertEqual(s.STATUS[int(result['status'][0])],'insufficient_time_blocks'); self.assertEqual(result['inferential'][0],0)


class AlignmentTests(unittest.TestCase):
    def workspace(self,frequency='M'):
        w=s.Workspace.__new__(s.Workspace); w.months=pd.period_range('2000-01','2002-12',freq='M')
        n=len(w.months); periods=w.months.asfreq('Q-DEC' if frequency=='Q' else 'Y-DEC') if frequency in ['Q','A'] else w.months
        values=np.asarray(periods.asi8-periods.asi8[0],float)
        f=pd.DataFrame({'x':values},index=w.months)
        w.external=dict(raw=f,adjusted=f,ends=pd.DataFrame({'x':periods.end_time.strftime('%Y-%m-%d')},index=w.months),
            metadata={'x':dict(analysis_frequency=frequency,kind='numeric')})
        w.views=[dict(id=0,name='overall',scope='overall',values=pd.DataFrame({'music':np.arange(n,dtype=float)},index=w.months),
            counts=np.ones(n)*20,metadata={'music':dict(profile='time')})]
        w.shares=np.ones((n,1)); w.cache=collections.OrderedDict(); w.stationarity={}
        return w

    def task(self,lag=0,track='raw'): return dict(view_id=0,external='x',lag=lag,track=track,external_kind='numeric')

    def test_quarterly_data_has_one_row_per_native_quarter(self):
        a=self.workspace('Q').aligned(self.task())
        self.assertEqual(len(a.x),12); np.testing.assert_allclose(a.y[:2,0],[1,4]); np.testing.assert_allclose(a.x[:2],[0,1])
        self.assertTrue(np.all(a.months_count[:,0]==3))

    def test_annual_data_not_twelve_independent_observations(self):
        a=self.workspace('A').aligned(self.task()); self.assertEqual(len(a.x),3)
        np.testing.assert_allclose(a.y[:,0],[5.5,17.5,29.5])

    def test_positive_month_lag_uses_past_values(self):
        a=self.workspace().aligned(self.task(3))
        self.assertTrue(np.isnan(a.x[:3]).all()); self.assertEqual(a.x[3],0); self.assertEqual(a.x[-1],32)

    def test_quarter_lag_one_waits_for_complete_source_quarter(self):
        a=self.workspace('Q').aligned(self.task(1))
        ok=np.isfinite(a.x)&np.isfinite(a.y[:,0]); np.testing.assert_allclose(a.y[ok,0],np.arange(3,36,3))
        np.testing.assert_allclose(a.x[ok],np.arange(11))

    def test_missing_native_period_not_interpolated_or_differenced_across(self):
        w=self.workspace(); w.views[0]['values'].iloc[10,0]=np.nan
        a=w.aligned(self.task(track='adjusted'))
        self.assertTrue(np.isnan(a.y[10:12,0]).all()); self.assertEqual(a.y[12,0],1.)
        values=pd.Series([100.,np.nan,121.]); self.assertTrue(data.native_change(values,'log_growth_positive_endpoints').isna().all())

    def test_native_transformation_formulas_and_event_identity(self):
        values=pd.Series([100.,110.,121.]); np.testing.assert_allclose(data.native_change(values,'log_growth_positive_endpoints').iloc[1:],100*np.log(1.1))
        np.testing.assert_allclose(data.native_change(values,'first_difference_native_period').iloc[1:],[10,11])
        np.testing.assert_array_equal(data.native_change(values,'identity_rate_change_or_event'),values)

    def test_inconsistent_copied_native_values_fail(self):
        w=self.workspace('Q'); w.external['raw'].iloc[1,0]=999.
        with self.assertRaisesRegex(ValueError,'disagree'): w.aligned(self.task())

    def test_stationarity_uses_longest_contiguous_segment(self):
        rng=np.random.default_rng(12); values=rng.normal(size=80); values[30:40]=np.nan
        diagnostic=diagnostics.stationarity(values,'M')
        self.assertEqual(diagnostic['longest_run'],40); self.assertEqual(diagnostic['n_observed'],70)


class CheckpointTests(unittest.TestCase):
    def test_reference_corpus_provenance_survives_composition_prefixes(self):
        result=report.Results.__new__(report.Results)
        name='lyric_semantic_prior_hit_reference_n'; result.source_roles={name:'provenance_or_quality'}
        for prefix in ['', 'fixed_composition__', 'matched_composition__']:
            self.assertEqual(result.role(prefix+name,{'role':'measurement'}),'provenance_or_quality')
        self.assertEqual(result.role(name+'__available_n',{'role':'sample_size'}),'sample_size')

    def test_restart_replays_exact_bytes_and_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'checkpoints.sqlite'; rows=s.blank(4); rows['status']=0
            store=runner.Store(path,'same'); store.put(0,rows,[],.01); store.close()
            store=runner.Store(path,'same'); self.assertEqual(runner.encode(rows),runner.encode(store.get(0)[0]))
            store.put(0,rows,[],.02); self.assertIsNone(store.get(1))
            changed=rows.copy(); changed['n']=20
            with self.assertRaisesRegex(ValueError,'change completed'): store.put(0,changed,[],.01)
            store.db.execute("UPDATE chunks SET body=x'00' WHERE id=0"); store.db.commit()
            with self.assertRaisesRegex(ValueError,'checksum'): store.get(0)
            store.close()
            with self.assertRaisesRegex(ValueError,'protocol mismatch'): runner.Store(path,'different')

    def test_resource_gate_refuses_oversized_campaign(self):
        with patch.object(c,'read_json',return_value={'status':'APPROVAL_REQUIRED'}):
            with self.assertRaises(c.ResourceLimit): runner.verify_gate()


if __name__=='__main__': unittest.main()
