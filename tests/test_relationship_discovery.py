"""Statistical calculations, temporal isolation and bounded discovery behavior."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from scipy import stats

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import relationship_discovery_spec as spec
import relationship_discovery_stats as inf
import relationship_discovery_models as models
import relationship_discovery as engine


class StatisticalTests(unittest.TestCase):
    def test_correlations_match_reference_with_ties(self):
        x=np.array([1,1,2,3,4,5]);y=np.array([3,2,2,4,8,7])
        self.assertAlmostEqual(inf.correlation(x,y),stats.pearsonr(x,y).statistic)
        self.assertAlmostEqual(inf.correlation(stats.rankdata(x),stats.rankdata(y)),stats.spearmanr(x,y).statistic)
    def test_nominal_labels_do_not_imply_numeric_distance(self):
        a=np.array([0,0,1,1,2,2]*10);b=np.array([0,0,1,2,1,2]*10);v=np.arange(len(a))%7
        self.assertAlmostEqual(inf.cramers_v(a,b),inf.cramers_v(np.array([2,0,1])[a],np.array([1,2,0])[b]))
        self.assertAlmostEqual(inf.eta_squared(a,v),inf.eta_squared(np.array([2,0,1])[a],v))
    def test_eta_squared_matches_anova_identity(self):
        g=np.repeat([0,1],4);v=np.array([0,1,2,3,10,11,12,13])
        expected=np.sum([4*(v[g==i].mean()-v.mean())**2 for i in [0,1]])/np.sum((v-v.mean())**2)
        self.assertAlmostEqual(inf.eta_squared(g,v),expected)
    def test_distance_correlation_finds_u_shape(self):
        x=np.linspace(-1,1,400);y=x*x
        self.assertLess(abs(inf.correlation(x,y)),1e-12)
        self.assertGreater(inf.distance_correlation(x,y),.4)
    def test_permutation_add_one_and_year_conditioning(self):
        years=np.repeat(np.arange(10),10);x=years.astype(float);y=x.copy()
        # All apparent dependence is shared year: conditional shuffling cannot break it.
        self.assertEqual(inf.permutation_p(x,y,years,False,False,'null',repeats=99),1.)
    def test_by_adjustment_includes_failed_attempts(self):
        rows=[dict(family='nonlinear',p_value=p) for p in [.001,.01,None]]
        inf.adjust_multiple_testing(rows)
        np.testing.assert_allclose([r['q_by_global'] for r in rows],[.0055,.0275,1.])
        self.assertFalse(rows[0]['independent_confirmation'])
    def test_zero_loss_gain_has_no_significance(self):
        years=np.repeat(np.arange(1990,2026),10)
        result=inf.paired_evidence(np.zeros(len(years)),years,'zero')
        self.assertEqual(result['p_value'],1.)
        self.assertEqual(result['ci_low'],0.)
    def test_constant_annual_variables_are_not_reported_as_zero_correlation(self):
        f=pd.DataFrame({'debut_year':np.repeat([2000,2001],50),'x':np.ones(100),'y':np.arange(100)})
        self.assertEqual(models.annual_correlations(f,'x','y'),[])
    def test_too_few_blocks_withholds_p_value(self):
        result=inf.paired_evidence(np.ones(100),np.repeat([2020,2021],50),'few')
        self.assertIsNone(result['p_value'])


class ModelTests(unittest.TestCase):
    def test_quadratic_fit_recovers_u_shape_on_new_inputs(self):
        x=np.linspace(-3,3,1000);train=pd.DataFrame({'x':x,'y':2*x*x+3})
        test=pd.DataFrame({'x':np.linspace(-2.9,2.9,300)})
        m=models.Univariate('x','quadratic').fit(train,'y')
        np.testing.assert_allclose(m.predict(test),2*test.x**2+3,atol=1e-10)
        baseline=models.Univariate('x','linear').fit(train,'y').predict(test)
        self.assertGreater(np.mean((baseline-(2*test.x**2+3))**2),10)
    def test_imputation_and_spline_knots_are_training_only(self):
        train=pd.DataFrame({'x':np.arange(1000,dtype=float),'y':np.arange(1000,dtype=float)})
        m=models.Univariate('x','spline4').fit(train,'y');median=m.median
        m.predict(pd.DataFrame({'x':[np.nan,1e8]}))
        self.assertEqual(m.median,median);self.assertEqual(median,499.5)
    def test_hinge_uses_training_quantile(self):
        train=pd.DataFrame({'x':np.arange(1000,dtype=float),'y':np.arange(1000,dtype=float)})
        m=models.Univariate('x','hinge75').fit(train,'y')
        self.assertAlmostEqual(m.knot*m.scale+m.mean,749.25)
    def test_genre_interaction_can_recover_sign_reversal(self):
        x=np.tile(np.linspace(-2,2,500),2);g=np.repeat(['Pop','Rock'],500)
        f=pd.DataFrame({'x':x,'primary_genre':g,'debut_year':np.tile(np.arange(1960,1980),50)})
        f['y']=np.where(g=='Pop',3*x,-3*x)
        row={'family':'genre_interaction','predictors':['x'],'conditioner':'primary_genre'}
        m=models.Interaction(row,True).fit(f,'y');base=models.Interaction(row,False).fit(f,'y')
        self.assertLess(np.mean((m.predict(f)-f.y)**2),1e-20)
        self.assertGreater(np.mean((base.predict(f)-f.y)**2),5)
    def test_threshold_main_effect_is_in_baseline(self):
        rng=np.random.default_rng(491);x=rng.normal(size=2000);z=np.linspace(-2,2,2000)
        f=pd.DataFrame({'x':x,'z':z,'y':x+z+10*(z>0)})
        row={'family':'threshold_interaction','predictors':['x'],'conditioner':'z','quantile':.5}
        base=models.Interaction(row,False).fit(f,'y')
        np.testing.assert_allclose(base.predict(f),f.y,atol=1e-10)
    def test_whole_song_label_window_is_purged(self):
        f=pd.DataFrame({'song_id':['a','b','c'],'first_iso':['1980-01-01','1989-01-01','1991-01-01'],
                        'last_iso':['1981-01-01','1991-01-01','1992-01-01']})
        tr,va=models.make_splits(f)[(1990,2000)]
        np.testing.assert_array_equal(tr,[True,False,False]);np.testing.assert_array_equal(va,[False,False,True])
    def test_outer_outcomes_do_not_choose_nonlinear_method(self):
        rng=np.random.default_rng(491);years=np.repeat(np.arange(1960,2000),50);x=rng.normal(size=len(years))
        f=pd.DataFrame({'song_id':[str(i) for i in range(len(years))],
            'first_iso':[str(y)+'-01-01' for y in years],'last_iso':[str(y)+'-06-01' for y in years],
            'debut_year':years,'primary_genre':'Pop','detox_toxicity':x,'ll_violence':x*x})
        row=spec.candidate('nonlinear','ll_violence',['detox_toxicity'])
        with patch.object(spec,'OUTER',[(1990,2000)]):
            masks=models.make_splits(f);one=models.predictive_analysis(f,masks,row)
            altered=f.copy();altered.loc[years>=1990,'ll_violence']=1000+rng.normal(size=np.sum(years>=1990))
            two=models.predictive_analysis(altered,masks,row)
        self.assertEqual(one['folds'][0]['inner_models'],two['folds'][0]['inner_models'])
        self.assertEqual(one['folds'][0]['selected_method'],two['folds'][0]['selected_method'])
        self.assertNotEqual(one['r2'],two['r2'])
    def test_subgroup_results_withhold_small_samples(self):
        f=pd.DataFrame({'primary_genre':['Pop']*50,'debut_year':np.repeat(np.arange(2000,2005),10),'x':np.arange(50),'y':np.arange(50)})
        r=models.coverage(f,{'target':'y','predictors':['x']},np.zeros(50),np.zeros(50),(2000,2010))
        self.assertFalse(next(g for g in r if g['genre']=='Pop')['adequate'])


class SpecificationTests(unittest.TestCase):
    def test_variable_types_and_original_categories(self):
        self.assertEqual(spec.kind('best_chart_rank'),'ordinal')
        self.assertNotIn('best_chart_rank',spec.NUMERIC)
        self.assertEqual(len(spec.NUMERIC),57);self.assertEqual(len(spec.CATEGORICAL),17)
        self.assertEqual(spec.classify('chart_weeks',['weekly_observation_count'])['category'][0],'A')
        self.assertEqual(spec.classify('detox_insult',['emotion_anger'])['category'][0],'C')
    def test_candidate_identity_does_not_depend_on_values(self):
        a=spec.candidate('nonlinear','ll_violence',['emotion_joy'])
        self.assertEqual(a,spec.candidate('nonlinear','ll_violence',['emotion_joy']))
        self.assertNotEqual(a['candidate_id'],spec.candidate('nonlinear','emotion_joy',['ll_violence'])['candidate_id'])
    def test_exact_pair_and_model_candidate_counts(self):
        self.assertEqual(sum(1 for _ in spec.pair_candidates()),2775)
        self.assertEqual(sum(1 for _ in spec.nonlinear_candidates()),3192)
    def test_hash_sampling_is_order_independent(self):
        rows=list(spec.nonlinear_candidates())[:100]
        f=lambda r:r['category']
        self.assertEqual(spec.hash_sample(rows,3,f),spec.hash_sample(reversed(rows),3,f))
    def test_logical_fingerprint_ignores_only_runtime_metadata(self):
        a={'effect':.5,'wall_seconds':1,'timings':[1]};b={'effect':.5,'wall_seconds':2,'timings':[2]}
        self.assertEqual(engine.logical(a),engine.logical(b))
        b['effect']=.6;self.assertNotEqual(engine.logical(a),engine.logical(b))



class PublishedDiscoveryTests(unittest.TestCase):
    def test_published_hypothesis_universe_and_global_correction(self):
        import gzip,json
        folder=ROOT/'analysis/relationship_discovery'
        results=json.loads(gzip.decompress((folder/'pilot_results/results.json.gz').read_bytes()))
        protocol=json.loads((folder/'pilot_protocol.json').read_text())
        self.assertEqual({r['candidate_id'] for r in results},{r['candidate_id'] for r in protocol['identity']['pilot_candidates']})
        primary=[r for r in results if 'q_by_global' in r]
        expected=stats.false_discovery_control([r['p_value'] if r['p_value'] is not None else 1. for r in primary],method='by')
        np.testing.assert_allclose(expected,[r['q_by_global'] for r in primary],atol=0,rtol=0)
        self.assertTrue(all(not r['independent_confirmation'] for r in results))
        temporal=[r for r in results if r['family']=='temporal']
        expanded=json.loads((folder/'expanded_workload.json').read_text())
        self.assertEqual(sum(len(r['conditional_correlations']) for r in temporal),len(temporal)*17*7)
        self.assertEqual(expanded['crossed_genre_period_cells'],1653*17*7)


if __name__=='__main__':unittest.main()
