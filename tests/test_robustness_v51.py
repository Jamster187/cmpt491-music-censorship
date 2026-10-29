"""Independent reference checks for the selected-candidate historical audit."""
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_hac
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import robustness_v51_common as c
import robustness_v51_stats as s
import robustness_v51_select as selection
import robustness_v51_runner as runner
import robustness_v51_report as report
import robustness_v51_data as data


class StatisticsTests(unittest.TestCase):
    def fixture(self,n=450):
        rng=np.random.default_rng(5151);x=rng.normal(size=n);z=rng.normal(size=n)
        controls=np.column_stack([np.ones(n),z,2*z,np.zeros(n)])
        y=1.7*x+2*z+rng.normal(size=n)
        return s.Series(x,y,controls,np.arange(n)+1,np.arange(n),np.arange(n),'M',6)

    def test_ols_and_hac_match_independent_statsmodels(self):
        d=self.fixture();value,_=s.fit(d,bandwidth=12)
        reference=sm.OLS(d.y,np.column_stack([d.controls[:,:2],d.x])).fit()
        self.assertAlmostEqual(value['slope'],reference.params[-1],places=12)
        self.assertAlmostEqual(value['se'],np.sqrt(cov_hac(reference,nlags=12,use_correction=True)[-1,-1]),places=12)

    def test_weighted_hac_matches_explicit_score_reference(self):
        d=self.fixture();value,_=s.fit(d,weighted=True,bandwidth=12)
        X=np.column_stack([d.controls[:,:2],d.x]);w=d.weights
        reference=sm.WLS(d.y,X,weights=w).fit();bread=np.linalg.inv(X.T@(w[:,None]*X))
        scores=w[:,None]*X*reference.resid[:,None];meat=scores.T@scores
        for lag in range(1,13):
            cross=scores[lag:].T@scores[:-lag];meat+=(1-lag/13)*(cross+cross.T)
        covariance=bread@meat@bread*len(X)/(len(X)-X.shape[1])
        np.testing.assert_allclose(value['slope'],reference.params[-1],rtol=1e-12)
        np.testing.assert_allclose(value['se'],np.sqrt(covariance[-1,-1]),rtol=1e-12)

    def test_analytic_influence_matches_direct_deletion(self):
        d=self.fixture();full,info=s.fit(d)
        for i in [0,32,217,449]:
            mask=np.arange(len(d.x))!=i;deleted,_=s.fit(d,subset=mask)
            self.assertAlmostEqual(full['slope']-info['deletion_delta'][i],deleted['slope'],places=12)

    def test_collinear_exposure_is_not_evidence(self):
        d=self.fixture();d.x=d.controls[:,1]
        value,info=s.fit(d);self.assertEqual(value['status'],'unidentified_effect');self.assertIsNone(info)
        self.assertEqual(value['p_for_family'],1.)

    def test_rank_regression_matches_independent_reference(self):
        d=self.fixture();value,_=s.fit(d,ranked=True)
        reference=sm.OLS(stats.rankdata(d.y),np.column_stack([d.controls[:,:2],stats.rankdata(d.x)])).fit()
        self.assertAlmostEqual(value['slope'],reference.params[-1],places=12)

    def test_missing_months_are_not_compressed_for_hac(self):
        d=self.fixture();d.y[30:100]=np.nan;value,info=s.fit(d,bandwidth=12)
        score=info['score'];grid=np.zeros(len(d.x));grid[info['positions']]=score
        variance=grid@grid
        for lag in range(1,13):variance+=2*(1-lag/13)*(grid[lag:]@grid[:-lag])
        variance*=value['n']/value['residual_df']
        self.assertAlmostEqual(value['se'],np.sqrt(variance),places=12)

    def test_moving_bootstrap_refits_full_nuisance_design(self):
        d=self.fixture();summary,draws=s.bootstrap(d,'moving_pairs',40,991)
        rng=np.random.default_rng(991);indices=s.block_draws(len(d.x),49,rng)
        reference=sm.OLS(d.y[indices],np.column_stack([d.controls[indices,:2],d.x[indices]])).fit()
        self.assertAlmostEqual(draws[0]['slope'],reference.params[-1],places=11)
        self.assertEqual(summary['successful'],40)
        self.assertGreater(summary['ci_low'],1.)

    def test_bootstrap_preserves_missing_calendar_slots(self):
        d=self.fixture();d.y[20:80]=np.nan
        _,draws=s.bootstrap(d,'moving_pairs',20,44)
        rng=np.random.default_rng(44);indices=s.block_draws(len(d.x),49,rng)
        self.assertEqual(draws[0]['sample_n'],int(np.isfinite(d.y[indices]).sum()))

    def test_bootstrap_deterministic_without_mutating_input(self):
        d=self.fixture();before=d.x.copy();a=s.bootstrap(d,'calendar_year_pairs',25,22);b=s.bootstrap(d,'calendar_year_pairs',25,22)
        self.assertEqual(c.digest(a),c.digest(b));np.testing.assert_array_equal(before,d.x)

    def test_annual_year_bootstrap_uses_five_year_blocks(self):
        d=self.fixture(65);d.frequency='A';d.first_month=np.arange(65)*12;d.last_month=d.first_month+11
        result,_=s.bootstrap(d,'calendar_year_pairs',30,77)
        self.assertEqual(result['block_definition'],'five calendar years')

    def test_shift_sign_no_wrap_and_missingness(self):
        x=np.arange(8,dtype=float);past=s.shifted(x,2);future=s.shifted(x,-2)
        np.testing.assert_array_equal(past[2:],x[:-2]);self.assertTrue(np.isnan(past[:2]).all())
        np.testing.assert_array_equal(future[:-2],x[2:]);self.assertTrue(np.isnan(future[-2:]).all())

    def test_period_deletion_includes_lagged_exposure(self):
        d=self.fixture(100);d.first_month=np.arange(100);d.last_month=d.first_month.copy();d.lag=6
        direct=s.period_mask(d,'1959-01','1960-01');combined=s.period_mask(d,'1959-01','1960-01',True)
        self.assertEqual(direct.sum(),12);self.assertEqual(combined.sum(),18)

    def test_rolling_is_trailing_and_does_not_fill_gaps(self):
        d=self.fixture();d.x[100]=np.nan;r=s.rolling(d)
        self.assertTrue(np.isnan(r.x[100:103]).all());self.assertAlmostEqual(r.x[50],d.x[48:51].mean())
        self.assertEqual(r.first_month[50],48)

    def test_concentration_does_not_equate_nominal_n_to_information(self):
        d=self.fixture();d.x[:]=.01;d.x[250]=100
        _,info=s.fit(d);energy=info['energy'];self.assertLess(s.kish(energy),1.2)
        self.assertEqual(len(info['positions']),450)

    def test_block_origin_sensitivity_retains_all_declared_offsets(self):
        d=self.fixture();_,info=s.fit(d);rows=runner.fixed_concentration(d,info)
        self.assertEqual(len(rows),12+24+49+60)
        self.assertEqual({r['origin_offset'] for r in rows if r['width_native_periods']==49},set(range(49)))

    def test_fixed_break_has_known_direction(self):
        d=self.fixture(818);year=2000;post=d.first_month>=s.month_number(f'{year}-01')
        d.y=d.y+3*d.x*post
        result=s.break_fit(d,year);self.assertGreater(result['slope'],2.5);self.assertLess(result['ci_low'],3.5)

    def test_permutation_diagnostic_detects_known_signal(self):
        d=self.fixture();result,draws=s.block_permutation(d,39,51)
        self.assertEqual(len(draws),39);self.assertLessEqual(result['exceedance_probability'],.05)

    def test_short_native_series_keeps_point_estimate_but_gates_inference(self):
        d=self.fixture(80);result,_=s.fit(d)
        self.assertEqual(result['status'],'ok');self.assertFalse(result['inferential_support']);self.assertEqual(result['p_for_family'],1.)


class AuditTests(unittest.TestCase):
    def test_recession_catalog_includes_available_lag_prefix(self):
        import pandas as pd
        months=pd.period_range('1957-01','1962-12',freq='M');values=np.zeros(len(months))
        values[months<pd.Period('1958-01','M')]=np.nan
        values[(months>=pd.Period('1958-01','M'))&(months<=pd.Period('1958-04','M'))]=1.
        workspace=SimpleNamespace(months=pd.period_range('1958-08','1962-12',freq='M'),external={'raw':pd.DataFrame({'US_NBER_DATED_RECESSION':values},index=months)})
        episodes=data.recession_episodes(workspace)
        self.assertEqual(len(episodes),1);self.assertEqual(episodes[0]['start'],'1958-01');self.assertEqual(episodes[0]['end'],'1958-05')
        self.assertTrue(episodes[0]['left_censored_observed_fragment']);self.assertTrue(episodes[0]['before_first_music_month'])

    def test_empty_provider_overlap_is_not_reproduction(self):
        import pandas as pd
        a=pd.DataFrame({'series_id':['a'],'date':['2000-01-01'],'value':[1.]})
        b=pd.DataFrame({'series_id':['b'],'observation_date':['2001-01-01'],'value':[1.]})
        w=SimpleNamespace(external={'metadata':{'x':{'source_records':['platform:a','finance:b']}}})
        with patch.object(data.pd,'read_csv',side_effect=[a,b]):
            result=data.overlap_reproduction(w,pd.DataFrame({'external_variable':['x']}))
        self.assertEqual(result[0]['status'],'no_common_native_observations');self.assertEqual(result[0]['common_native_observations'],0)

    def test_replay_tolerance_allows_only_roundoff(self):
        value=report.compare_numerical_payloads({'r':.2,'status':'ok'},{'r':.2+1e-16,'status':'ok'})
        self.assertEqual(value['float_values_compared'],1)
        with self.assertRaises(ValueError):report.compare_numerical_payloads({'r':.2},{'r':.2001})
        with self.assertRaises(ValueError):report.compare_numerical_payloads({'status':'ok'},{'status':'unsupported'})

    def test_checkpoint_detects_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'checkpoint.json';runner.write_checkpoint(p,{'r':.2},'abc')
            self.assertEqual(runner.read_checkpoint(p,'abc'),{'r':.2})
            value=c.read_json(p);value['payload']['r']=.9;c.write_json(p,value)
            with self.assertRaises(ValueError):runner.read_checkpoint(p,'abc')

    def test_native_block_draws_are_contiguous_within_blocks(self):
        indices=s.block_draws(100,13,np.random.default_rng(42))
        self.assertEqual(len(indices),100)
        for start in range(0,91,13):np.testing.assert_array_equal(np.diff(indices[start:start+13]),np.ones(12))

    def test_substantive_role_excludes_quality_fields(self):
        self.assertIn('provenance_or_quality',selection.EXCLUDED_ROLES)
        self.assertIn('sample_size',selection.EXCLUDED_ROLES)

    @unittest.skipUnless((c.PUBLIC/'selection_freeze.json').exists(),'No frozen V5.1 selection')
    def test_public_selection_remains_frozen_and_mandatory_unprivileged(self):
        import pandas as pd
        value=c.read_json(c.PUBLIC/'selection_freeze.json');self.assertEqual(c.sha(c.PUBLIC/'candidate_selection.csv'),value['candidate_sha256'])
        d=pd.read_csv(c.PUBLIC/'candidate_selection.csv');mandatory=d[d.selection_strata.str.contains('mandatory_diagnostic')]
        self.assertEqual(len(mandatory),1);self.assertEqual(mandatory.iloc[0].music_variable,'emotion_caring')
        self.assertEqual(mandatory.iloc[0].lag_months,6);self.assertEqual(len(d),value['candidate_count'])

    @unittest.skipUnless((c.PUBLIC/'primary.csv').exists(),'No completed V5.1 audit')
    def test_mandatory_candidate_gets_no_special_outcome_rule(self):
        import pandas as pd
        candidates=pd.read_csv(c.PUBLIC/'candidate_selection.csv')
        row=candidates.loc[candidates.selection_strata.str.contains('mandatory_diagnostic')].iloc[0].to_dict()
        names=['primary','influence_diagnostics','temporal_sensitivity','weighting_sensitivity','negative_controls','bootstrap_intervals']
        frames={name:pd.read_csv(c.PUBLIC/(name+'.csv')) for name in names}
        original=report.classify(row,frames);other=dict(row,candidate_id='renamed_diagnostic',selection_strata='corrected_adjusted_lyrical')
        replaced={name:frame.assign(candidate_id=frame.candidate_id.replace({row['candidate_id']:other['candidate_id']})) for name,frame in frames.items()}
        second=report.classify(other,replaced)
        self.assertEqual(original['outcome'],second['outcome']);self.assertEqual(original['failed_gates'],second['failed_gates'])

    @unittest.skipUnless((c.PUBLIC/'multiple_testing.csv').exists(),'No completed V5.1 audit')
    def test_failed_and_interval_slots_remain_in_diagnostic_family(self):
        import pandas as pd
        family=pd.read_csv(c.PUBLIC/'multiple_testing.csv');candidates=pd.read_csv(c.PUBLIC/'candidate_selection.csv')
        intervals=family[family.table=='bootstrap_intervals']
        self.assertEqual(len(intervals),2*len(candidates));self.assertTrue((intervals.p==1).all())
        invalid=family[family.status.isin(['insufficient_observations','unidentified_effect','unavailable','not_applicable'])]
        self.assertGreater(len(invalid),0);self.assertTrue((invalid.p==1).all())
        self.assertEqual(family.test_id.nunique(),len(family))

    def test_fixed_break_without_stationarity_screen_is_formally_unsupported(self):
        payload={key:[] for key in report.TABLES}
        payload['temporal_sensitivity']=[dict(candidate_id='x',group='temporal_sensitivity',specification='fixed_break_2000',method='slope_change',
            status='ok',inferential_support=True,p_for_family=1e-10,nominal_p=1e-10)]
        # Supply one ordinary comparison in every otherwise empty test table.
        for name in report.TEST_TABLES:
            if not payload[name]:payload[name]=[dict(candidate_id='x',group=name,specification='reference',method='pearson',status='ok',p_for_family=.5)]
        frames=report.tables([payload]);value=frames['temporal_sensitivity'].iloc[0]
        self.assertFalse(value.inferential_support);self.assertEqual(value.p_for_family,1.);self.assertEqual(value.nominal_p,1e-10)


if __name__=='__main__':unittest.main()
