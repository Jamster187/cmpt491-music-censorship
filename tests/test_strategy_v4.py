"""Search accounting, hidden signals, estimators, temporal isolation and recovery."""
import collections
import itertools
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy import linalg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import strategy_v4_common as c
import strategy_v4_data as data
import strategy_v4_engine as engine
import strategy_v4_search as search
import strategy_v4_report as report
import cross_domain_v4_audit as old


def fixture(p=12, n=480):
    rng = np.random.default_rng(49154)
    names = [f'x{i:02}' for i in range(p)]
    reg = {name: dict(domain=f'd{i%3}', family=f'f{i%6}', source=[f's{i%4}'], origin='music',
                      kind='numeric', frequency='song', base=name, lag=0, source_columns=[name]) for i, name in enumerate(names)}
    reg['y'] = dict(domain='d0', family='target', source=['s0'], origin='music', kind='numeric', frequency='song', base='y', lag=0, source_columns=['y'])
    x = rng.normal(size=(n, p)); y = x[:, 0]+rng.normal(size=n)*.1
    frame = pd.DataFrame(x, columns=names)
    frame['y'] = y; frame['month'] = pd.period_range('1960-01', periods=n, freq='M').astype(str)
    frame['row_id'] = [f'id{i}' for i in range(n)]; frame['artist'] = [f'artist{i%30}' for i in range(n)]
    frame['primary_genre'] = [f'g{i%3}' for i in range(n)]
    task = dict(task_id=1, population='song', track='raw', scope='pooled', target='y', predictors=names,
                edges=[], triples=[], counts=old.count_combinations(names),
                bounds=['1980-01', '1985-01', '1990-01', '1995-01', '2000-01'])
    return engine.ObservedCase('opaque', task, frame, y, reg)


class AccountingTests(unittest.TestCase):
    def test_exact_stratification_matches_brute_force_for_every_k(self):
        case = fixture(); task = case.task
        task['edges'] = [['x00', 'x01'], ['x02', 'x03']]
        task['triples'] = [['x04', 'x05', 'x06']]
        task['counts'] = old.count_combinations(task['predictors'], task['edges'], task['triples'])
        pool = search.StratifiedPool(task, case.registry)
        expected = collections.Counter(pool.stratum(combo) for combo in old.enumerate_combinations(task['predictors'], task['edges'], task['triples']))
        self.assertEqual(dict(expected), pool.sizes)
        self.assertEqual(sum(expected.values()), sum(task['counts'].values()))

    def test_stratified_census_has_no_duplicates_and_exact_conditional_probability(self):
        case = fixture(7); pool = search.StratifiedPool(case.task, case.registry)
        rng = np.random.default_rng(49155); seen = set()
        for k in [1, 2, 3]:
            for _ in range(case.task['counts'][k]):
                combo, record = pool.draw(rng, k, seen)
                self.assertNotIn(combo, seen); self.assertTrue(c.eligible(case.task, combo))
                key = record['stratum']; used = sum(pool.stratum(old_combo) == key for old_combo in seen)
                self.assertAlmostEqual(record['conditional_candidate_probability'], 1/(pool.sizes[key]-used))
                self.assertAlmostEqual(record['proposal_probability'], record['conditional_candidate_probability']*record['stratum_probability'])
                seen.add(combo)
        self.assertEqual(len(seen), sum(case.task['counts'].values()))
        self.assertEqual(pool.draw(rng, 3, seen), (None, None))

    def test_sampling_seed_replays_without_outcome_information(self):
        case = fixture(); pool = search.StratifiedPool(case.task, case.registry)
        def draw():
            rng = np.random.default_rng(731); seen = set(); rows = []
            for i in range(30):
                combo, probability = pool.draw(rng, 1+i%3, seen); seen.add(combo); rows.append((combo, probability))
            return rows
        first = draw(); case.y *= -100
        self.assertEqual(first, draw())

    def test_provenance_separation_is_distinct_from_cross_domain(self):
        case = fixture()
        self.assertTrue(c.classification(case.task, ('x04',), case.registry)['cross_domain'])
        self.assertFalse(c.classification(case.task, ('x04',), case.registry)['target_provenance_separated'])
        self.assertTrue(c.classification(case.task, ('x01',), case.registry)['target_provenance_separated'])

    def test_explicit_identity_constraints_survive_every_policy_universe(self):
        case = fixture(); case.task['edges'] = [['x01', 'x02']]
        scores = {n: float(i) for i, n in enumerate(case.task['predictors'])}
        combos = search.screened_universe(case.task, case.registry, scores)
        self.assertTrue(all(c.eligible(case.task, row) for rows in combos.values() for row in rows))


class EstimatorTests(unittest.TestCase):
    def test_additive_matches_independent_full_row_svd(self):
        case = fixture(); fold = engine.prepare(case, 0)
        combo = ('x00', 'x01'); result = engine.fit(fold, combo, 'additive', predictions=True)
        indexes = [i for n in combo for i in fold.groups[n]]
        x, v = np.c_[np.ones(len(fold.y)), fold.X[:, indexes]], np.c_[np.ones(len(fold.z)), fold.V[:, indexes]]
        beta = linalg.lstsq(x, fold.y, lapack_driver='gelsd')[0]
        np.testing.assert_allclose(result['prediction'], v@beta, rtol=1e-10, atol=1e-10)

    def test_adjusted_polynomial_matches_independent_joint_control_svd(self):
        case = fixture(); case.task['track'] = 'adjusted'
        case.y = case.frame.x00.to_numpy()*case.frame.x01.to_numpy()+.4*case.frame.x00.to_numpy()**2
        fold = engine.prepare(case,0)
        result = engine.fit(fold,('x00','x01'),'polynomial',predictions=True)
        a,b = fold.primary['x00'],fold.primary['x01']
        x = np.c_[fold.a,fold.X[:,a],fold.X[:,b],fold.X[:,a]**2,fold.X[:,b]**2,fold.X[:,a]*fold.X[:,b]]
        v = np.c_[fold.b,fold.V[:,a],fold.V[:,b],fold.V[:,a]**2,fold.V[:,b]**2,fold.V[:,a]*fold.V[:,b]]
        beta = linalg.lstsq(x*np.sqrt(fold.w)[:,None],fold.y*np.sqrt(fold.w),lapack_driver='gelsd')[0]
        np.testing.assert_allclose(result['prediction'],v@beta,rtol=1e-9,atol=1e-9)

    def test_redundant_nuisance_control_is_an_explicit_failed_gate(self):
        case = fixture(); fold = engine.prepare(case,0)
        fold.a = np.column_stack([fold.a,np.zeros(len(fold.y))])
        fold.b = np.column_stack([fold.b,np.zeros(len(fold.z))])
        result = engine.fit(fold,('x00',),'additive',predictions=True)
        self.assertEqual(result['status'],'rank_deficient')
        self.assertTrue(np.isfinite(result['prediction']).all())
        self.assertLess(result['rank'],result['columns'])
        self.assertEqual(engine.rank([result,result]),-np.inf)
        self.assertEqual(engine.assessment_stat([result,result]),-np.inf)

    def test_polynomial_represents_pure_pair_interactions_that_additive_misses(self):
        case = fixture(n=2400); case.y = case.frame.x00.to_numpy()*case.frame.x01.to_numpy()
        case.task['bounds'] = ['2050-01', '2070-01', '2090-01', '2110-01', '2160-01']
        fold = engine.prepare(case, 0)
        additive = engine.fit(fold, ('x00', 'x01'), 'additive')
        poly = engine.fit(fold, ('x00', 'x01'), 'polynomial')
        self.assertLess(additive['skill'], .1); self.assertGreater(poly['skill'], .99999)

    def test_polynomial_represents_triple_products(self):
        case = fixture(n=2400)
        case.y = case.frame.x00.to_numpy()*case.frame.x01.to_numpy()*case.frame.x02.to_numpy()
        case.task['bounds'] = ['2050-01', '2070-01', '2090-01', '2110-01', '2160-01']
        fold = engine.prepare(case, 0)
        self.assertGreater(engine.fit(fold, ('x00', 'x01', 'x02'), 'polynomial')['skill'], .99999)

    def test_future_values_do_not_change_training_preprocessing(self):
        case = fixture(); first = engine.prepare(case, 0)
        late = case.frame.month.ge(case.task['bounds'][0])
        case.frame.loc[late, case.task['predictors']] *= 1e6; case.y[late] *= -1e7
        second = engine.prepare(case, 0)
        np.testing.assert_array_equal(first.X, second.X)
        np.testing.assert_array_equal(first.y, second.y)
        np.testing.assert_array_equal(first.train_residual, second.train_residual)

    def test_whole_song_or_row_overlap_is_rejected(self):
        case = fixture(); case.frame.loc[250, 'row_id'] = case.frame.loc[0, 'row_id']
        with self.assertRaises(ValueError):
            engine.prepare(case, 0)

    def test_pairwise_measures_are_exhaustive_and_detect_quadratic_dependence(self):
        case = fixture(); case.y = case.frame.x00.to_numpy()**2
        folds = [engine.prepare(case, i) for i in [0, 1]]
        scores, record = engine.pairwise(folds, case.task['predictors'])
        self.assertEqual(set(scores), set(case.task['predictors']))
        self.assertEqual(record['original_pairs'], len(case.task['predictors']))
        self.assertEqual(max(scores, key=scores.get), 'x00')
        for rows in record['numeric_and_group_diagnostics']:
            row = next(r for r in rows if r['predictor'] == 'x00')
            self.assertGreater(row['eta_squared'], row['pearson']**2)

    def test_24_month_cluster_interval_is_not_narrowed_by_row_replication(self):
        case = fixture(); folds = [engine.prepare(case, i) for i in [2, 3]]
        results = [engine.fit(f, ('x00',), 'additive', predictions=True) for f in folds]
        with patch.dict(c.CONFIG, minimum_uncertainty_blocks=3):
            original = engine.clustered_interval(folds, results, 'song', 12)
            import copy
            repeated_folds = [copy.copy(f) for f in folds]; repeated_results = []
            for f, result in zip(repeated_folds, results):
                f.z = np.tile(f.z, 3); f.baseline_prediction = np.tile(f.baseline_prediction, 3)
                f.u = np.tile(f.u, 3); f.valid = pd.concat([f.valid]*3, ignore_index=True)
                repeated_results.append(dict(result, loss=np.tile(result['loss'], 3)))
            repeated = engine.clustered_interval(repeated_folds, repeated_results, 'song', 12)
        self.assertAlmostEqual(original['low'], repeated['low'], places=12)
        self.assertAlmostEqual(original['high'], repeated['high'], places=12)


class SyntheticTests(unittest.TestCase):
    def make(self, family, replicate=0, phase='development'):
        case = fixture(); case.frame.loc[::7, 'x00'] = np.nan
        with patch.object(data, 'real_case', return_value=case):
            return data.world(case.task, family, replicate, phase, [case.task, case.task]), case

    def test_injection_preserves_original_bytes_and_missingness(self):
        case = fixture(); snapshot = case.frame.copy(deep=True); y = case.y.copy()
        with patch.object(data, 'real_case', return_value=case):
            observed, truth = data.world(case.task, 'linear', 0, 'development', [case.task, case.task])
        pd.testing.assert_frame_equal(case.frame, snapshot); np.testing.assert_array_equal(case.y, y)
        self.assertTrue(truth['missingness_preserved']); self.assertFalse(np.array_equal(observed.y, y))
        self.assertFalse(hasattr(observed, 'truth')); self.assertFalse(hasattr(observed, 'family'))

    def test_tuning_and_final_worlds_are_disjoint_and_reproducible(self):
        (first, truth1), _ = self.make('interaction')
        (second, truth2), _ = self.make('interaction')
        (final, truth3), _ = self.make('interaction', phase='final')
        np.testing.assert_array_equal(first.y, second.y)
        self.assertEqual(truth1, truth2); self.assertNotEqual(truth1['generator_seed'], truth3['generator_seed'])
        self.assertFalse(np.array_equal(first.y, final.y))

    def test_all_requested_signal_classes_construct_valid_hidden_truth(self):
        for family in c.CONFIG['signal_types']:
            for replicate in [0, 1]:
                with self.subTest(family=family, replicate=replicate):
                    (_, truth), case = self.make(family, replicate)
                    if truth['active_predictors']:
                        self.assertTrue(c.eligible(case.task, truth['active_predictors']))
                    self.assertEqual(truth['null_or_spurious'], family in ['null', 'spurious_trend'])

    def test_null_has_no_injected_cross_domain_signal(self):
        (_, truth), _ = self.make('null')
        self.assertEqual(truth['active_predictors'], []); self.assertEqual(truth['active_families'], [])

    def test_recovery_requires_complete_support_and_handles_redundant_families(self):
        case = fixture(); truth = dict(active_predictors=['x00', 'x01'], active_families=[('d0', 'f0'), ('d1', 'f1')])
        self.assertFalse(data.signal_hit(('x00',), truth, case.registry))
        self.assertTrue(data.signal_hit(('x00', 'x01', 'x02'), truth, case.registry))
        self.assertTrue(data.signal_hit(('x06', 'x07'), truth, case.registry, tolerant=True))


class PolicyTests(unittest.TestCase):
    def test_search_context_has_neither_future_labels_nor_hidden_truth(self):
        case = fixture(); context = engine.SearchContext(case.key, case.task, case.registry)
        self.assertEqual(set(vars(context)), {'key', 'task', 'registry'})
        for name in ['frame', 'y', 'truth', 'active_predictors', 'family']:
            self.assertFalse(hasattr(context, name))

    def test_native_memory_sampler_reports_bytes_and_stops_its_thread(self):
        with c.MemoryMeter() as meter:
            self.assertGreater(meter.peak, 1024*1024)
        self.assertFalse(meter.thread.is_alive())
        self.assertGreater(meter.result()['sampled_peak_rss_bytes'], 1024*1024)

    def test_every_policy_has_domain_floor_and_exact_checkpoint_recovery(self):
        case = fixture(); folds = [engine.prepare(case, i) for i in [0, 1]]
        pool = search.StratifiedPool(case.task, case.registry)
        class Budget:
            def check(self):
                pass
        with tempfile.TemporaryDirectory() as directory, patch.dict(c.CONFIG, combinations_per_cell=24, search_seconds_per_cell=100.):
            store = c.Store(Path(directory)/'test.sqlite', 'identity')
            for strategy in ['A', 'B', 'C']:
                first = search.run(case, folds, strategy, 491, pool, store, Budget())
                self.assertEqual(len(first['candidates']), 24)
                self.assertEqual(len({tuple(e['predictors']) for e in first['candidates']}), 24)
                covered = {case.registry[n]['domain'] for e in first['candidates'] for n in e['predictors']}
                self.assertEqual(covered, set(pool.domains))
                self.assertEqual(c.digest(first), c.digest(search.run(case, folds, strategy, 491, pool, store, Budget())))
                # Remove only the final wrapper in the test fixture. Prefix events
                # remain and must reconstruct the identical choices and scores.
                store.db.execute('DELETE FROM records WHERE kind=? AND key=?', ('search', first['key'])); store.db.commit()
                replay = search.run(case, folds, strategy, 491, pool, store, Budget())
                self.assertEqual(first['candidates'], replay['candidates']); self.assertEqual(first['selected'], replay['selected'])
            store.db.close()

    def test_adaptive_policy_keeps_exploration_after_initial_phase(self):
        case = fixture(); folds = [engine.prepare(case, i) for i in [0, 1]]
        pool = search.StratifiedPool(case.task, case.registry)
        class Budget:
            def check(self): pass
        with tempfile.TemporaryDirectory() as directory, patch.dict(c.CONFIG, combinations_per_cell=60, search_seconds_per_cell=100.):
            store = c.Store(Path(directory)/'test.sqlite', 'identity')
            result = search.run(case, folds, 'C', 12, pool, store, Budget())
            tail = result['candidates'][32:]
            self.assertGreaterEqual(sum(e['path'] == 'exploration' for e in tail), len(tail)//2)
            self.assertTrue(any(e['path'] == 'adaptive_exploitation' for e in tail)); store.db.close()

    def test_checksum_corruption_and_identity_change_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.sqlite'; store = c.Store(path, 'a'); store.put('event', 'x', {'a': 1}); store.db.close()
            with self.assertRaises(ValueError): c.Store(path, 'b')
            store = c.Store(path, 'a'); store.db.execute("UPDATE records SET payload=X'00'"); store.db.commit(); store.db.close()
            with self.assertRaises(ValueError): c.Store(path, 'a')

    def test_no_full_campaign_command_exists(self):
        body = (Path(__file__).resolve().parents[1]/'src/strategy_v4_run.py').read_text()
        self.assertIn("choices=['audit', 'development', 'benchmark']", body)
        self.assertFalse(c.CONFIG['full_campaign_authorized'])


class ReportingTests(unittest.TestCase):
    def test_acceptance_requires_worst_period_threshold_and_positive_cluster_bound(self):
        row = dict(min_skill=.2, uncertainty=dict(status='ok',low=.05))
        self.assertTrue(report.flagged(row,.1))
        self.assertFalse(report.flagged(row,.2))
        self.assertFalse(report.flagged(dict(row,uncertainty=dict(status='ok',low=0)),.1))
        self.assertFalse(report.flagged(dict(row,uncertainty=dict(status='insufficient_time_blocks')),.1))
        self.assertFalse(report.flagged(dict(row,min_skill=-np.inf),.1))

    def test_calibration_takes_maximum_over_all_seeds_and_estimators_per_world(self):
        truths = {str(i): dict(phase='calibration',population='monthly',track='raw') for i in range(24)}
        assessments = {}
        for i in range(24):
            for seed in range(3):
                assessments[f'{i}/{seed}'] = dict(case_key=str(i),strategy='A',results=[
                    dict(min_skill=(i+1)/100+seed/1000,uncertainty=dict(status='ok',low=.01)),
                    dict(min_skill=.9,uncertainty=dict(status='ok',low=-.01))])
        thresholds, rows = report.calibrate(assessments,truths)
        self.assertAlmostEqual(thresholds['A'],.242)
        self.assertEqual(len(rows),24)
        self.assertTrue(all(row['all_search_seeds_in_maximum'] for row in rows))
        self.assertTrue(np.isinf(thresholds['B']))

    def test_independent_selection_audit_uses_validation_and_family_diversity(self):
        case = fixture(); events = []
        for name,skills in [('x00',[.5,.1]),('x06',[.9,.9]),('x01',[.3,.3]),('x02',[.2,.2])]:
            fits = [dict(skill=v,status='ok') for v in skills]
            events.append(dict(predictors=(name,),models={f:fits for f in c.CONFIG['model_families']}))
        selected = [dict(predictors=(n,),family=f,search_score=score) for f in c.CONFIG['model_families']
                    for n,score in [('x06',1.35),('x01',.45),('x02',.3)]]
        # Decimal evaluation order is reproduced exactly in the audit input.
        for row in selected:
            event = next(e for e in events if e['predictors'] == row['predictors'])
            row['search_score'] = report.independent_rank(event['models'][row['family']])
        report.verify_selection(dict(candidates=events,selected=selected),case.registry)
        selected[0]['predictors'] = ('x00',)
        with self.assertRaises(ValueError):
            report.verify_selection(dict(candidates=events,selected=selected),case.registry)

    def test_worst_period_metric_rejects_unsupported_period_even_with_high_skill(self):
        valid = dict(status='ok',skill=.7,support_sufficient=True)
        invalid = dict(status='ok',skill=.9,support_sufficient=False)
        report.verify_assessment(dict(results=[dict(periods=[valid,invalid],min_skill=-np.inf)]))
        with self.assertRaises(ValueError):
            report.verify_assessment(dict(results=[dict(periods=[valid,invalid],min_skill=.7)]))

    def test_wilson_interval_does_not_treat_zero_observed_errors_as_zero_risk(self):
        low,high = report.wilson(0,6)
        self.assertAlmostEqual(low,0)
        self.assertGreater(high,.3)


if __name__ == '__main__':
    unittest.main()
