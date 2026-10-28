"""Independent OLS, exhaustive accounting, temporal isolation and audit regressions."""
import itertools
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy.stats import hypergeom

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import cross_domain_v4_audit as parent_audit
import hierarchical_v4_common as c
import hierarchical_v4_engine as engine
import hierarchical_v4_screen as screen
import hierarchical_v4_sampling as sampling
import hierarchical_v4_run as runner
import hierarchical_v4_benchmark_report as benchmark


def task_fixture(n=10, domains=3):
    names = [f'x{i:02}' for i in range(n)]
    registry = {name: {'domain': f'd{i % domains}'} for i, name in enumerate(names)}
    task = dict(task_id=7, population='song', track='raw', scope='pooled', target='y',
                predictors=names, edges=[], triples=[], counts=parent_audit.count_combinations(names))
    return task, registry


class LossTests(unittest.TestCase):
    def design(self):
        rng = np.random.default_rng(49141)
        x = rng.normal(size=(220, 17)); v = rng.normal(size=(90, 17))
        coefficients = rng.normal(size=(17, 3))
        y = x@coefficients+rng.normal(size=(220, 3))
        z = v@coefficients+rng.normal(size=(90, 3))
        groups = [[0], [1, 2], [3, 4, 5], list(range(6, 17))]
        return engine.Design.from_arrays(x, v, y, z, rng.uniform(.2, 2, 220), rng.uniform(.2, 2, 90),
                                         ['a', 'b', 'c', 'd'], groups)

    def test_all_small_combinations_match_full_weighted_svd(self):
        design = self.design()
        for k in [1, 2, 3]:
            for combo in itertools.combinations(range(4), k):
                for target in range(3):
                    self.assertLess(design.reference(combo, target)['scaled_mse_error'], 1e-10)

    def test_target_batch_and_order_do_not_change_losses(self):
        design = self.design()
        combos = [(0, 1), (1, 3), (2, 3)]
        all_scores, status = design.score(combos)
        batched, other = design.score(combos, [2, 0])
        np.testing.assert_array_equal(status, other)
        np.testing.assert_allclose(batched, all_scores[:, [2, 0]], rtol=1e-12)

    def test_complete_lower_order_iterator_has_exact_coverage(self):
        design = self.design()
        ids, scores, status = engine.score_lower(design)
        expected = {(i, -1) for i in range(4)} | set(itertools.combinations(range(4), 2))
        self.assertEqual(set(map(tuple, ids)), expected)
        self.assertEqual(len(ids), len(expected))
        for row, identifier in enumerate(ids):
            combo = tuple(i for i in identifier if i >= 0)
            direct, _ = design.score([combo])
            np.testing.assert_allclose(scores[row], direct[0], rtol=1e-12)
        self.assertTrue((status == engine.OK).all())

    def test_validation_values_cannot_change_training_basis(self):
        rng = np.random.default_rng(23)
        x, v = rng.normal(size=(80, 3)), rng.normal(size=(20, 3))
        y, z = rng.normal(size=80), rng.normal(size=20)
        first = engine.Design.from_arrays(x, v, y, z, np.ones(80), np.ones(20), ['a', 'b', 'c'], [[0], [1], [2]])
        second = engine.Design.from_arrays(x, v*1e6, y, z*1e6, np.ones(80), np.ones(20), ['a', 'b', 'c'], [[0], [1], [2]])
        for name in ['X', 'Y', 'G', 'H', 'train_mean']:
            np.testing.assert_array_equal(getattr(first, name), getattr(second, name))

    def test_collinearity_and_insufficient_df_are_explicit_attempts(self):
        rng = np.random.default_rng(24)
        x, v = rng.normal(size=(30, 35)), rng.normal(size=(15, 35))
        x[:, 1], v[:, 1] = x[:, 0], v[:, 0]
        d = engine.Design.from_arrays(x, v, x[:, 2], v[:, 2], np.ones(30), np.ones(15),
                                     ['a', 'duplicate', 'large'], [[0], [1], list(range(2, 35))])
        scores, status = d.score([(0, 1), (0, 2)])
        np.testing.assert_array_equal(status, [engine.CONDITION, engine.RESIDUAL_DF])
        self.assertTrue(np.isinf(scores).all())

    def test_coefficients_reproduce_prediction_in_original_group_coordinates(self):
        design = self.design()
        combo = (0, 2, 3)
        coefficients = design.coefficients(combo, 1)
        for item in combo:
            self.assertEqual(len(coefficients[design.names[item]]), len(design.groups[item]))
        self.assertLess(design.reference(combo, 1)['scaled_mse_error'], 1e-10)


class ScreeningTests(unittest.TestCase):
    def test_domain_counts_equal_brute_force_with_constraints(self):
        rng = np.random.default_rng(49142)
        for n in range(4, 13):
            for _ in range(4):
                task, reg = task_fixture(n)
                task['edges'] = [list(pair) for pair in itertools.combinations(task['predictors'], 2) if rng.random() < .1]
                task['triples'] = [list(t) for t in itertools.combinations(task['predictors'], 3) if rng.random() < .1]
                task['counts'] = parent_audit.count_combinations(task['predictors'], task['edges'], task['triples'])
                patterns = list(itertools.combinations_with_replacement(['d0', 'd1', 'd2'], 3))
                counts = screen.domain_counts(task, reg, patterns)
                expected = {pattern: 0 for pattern in patterns}
                for combo in parent_audit.enumerate_combinations(task['predictors'], task['edges'], task['triples']):
                    if len(combo) == 3:
                        expected[tuple(sorted(reg[name]['domain'] for name in combo))] += 1
                self.assertEqual(counts.tolist(), [expected[p] for p in patterns])

    def lower(self):
        task, reg = task_fixture(15)
        ids = engine.lower_order_ids(task['predictors'])
        losses = np.linspace(.1, 2., len(ids))
        # The weakest domain remains eligible for an equal per-domain quota.
        losses[[i for i, row in enumerate(ids) if reg[task['predictors'][row[0]]]['domain'] == 'd2']] += 10
        with patch.dict(c.CONFIG, single_global_quota=2, single_per_domain_quota=1,
                        pair_global_quota=2, pair_per_domain_multiset_quota=1):
            result = screen.screen_lower(task, task['predictors'], ids, [losses, losses*1.1],
                                         [np.zeros(len(ids), int)]*2, [1., 1.], reg)
        return task, reg, result

    def test_weaker_domains_keep_equal_quota_without_variable_favorites(self):
        _, _, lower = self.lower()
        singles = [r for r in lower['domain_coverage'] if r['k'] == 1]
        self.assertEqual({r['domains'][0] for r in singles}, {'d0', 'd1', 'd2'})
        self.assertTrue(all(r['quota_selected'] == 1 for r in singles))

    def test_triples_are_bounded_deterministic_and_constraint_safe(self):
        task, reg, lower = self.lower()
        with patch.dict(c.CONFIG, triple_cap_per_target=20, triple_per_domain_multiset_quota=1):
            first = screen.triples(task, lower, reg)
            reversed_lower = dict(lower, retained=list(reversed(lower['retained'])))
            second = screen.triples(task, reversed_lower, reg)
        self.assertEqual(first, second)
        self.assertLessEqual(len(first['candidates']), 20)
        self.assertEqual(len(first['candidates']), len(set(first['candidates'])))
        self.assertTrue(all(len(set(t)) == 3 for t in first['candidates']))
        actual = {tuple(sorted(reg[name]['domain'] for name in combo)) for combo in first['candidates']}
        self.assertEqual(len(actual), first['domain_patterns'])

    def test_coverage_check_rejects_missing_pair(self):
        task, _ = task_fixture()
        ids = engine.lower_order_ids(task['predictors'])
        with self.assertRaises(ValueError):
            screen.allowed_mask(task, task['predictors'], ids[:-1])


class RandomAuditTests(unittest.TestCase):
    def test_sampling_is_reproducible_independent_and_without_replacement(self):
        task, reg = task_fixture(9)
        selected = {7: [('x00', 'x01', 'x02')]}
        strata, samples = sampling.sample([task], selected, {'song': reg}, total=30, minimum=1)
        again = sampling.sample([dict(task, predictors=list(reversed(task['predictors'])))], selected,
                                {'song': reg}, total=30, minimum=1)
        self.assertEqual((strata, samples), again)
        self.assertEqual(len(samples), 30)
        self.assertEqual(len({tuple(s['predictors']) for s in samples}), 30)
        self.assertNotIn(selected[7][0], {tuple(s['predictors']) for s in samples})
        self.assertEqual(sum(s['population_size'] for s in strata), task['counts'][3]-1)
        self.assertTrue(all(s['sample_size'] >= 1 for s in strata))

    def test_census_audit_visits_every_rejected_eligible_triple(self):
        task, reg = task_fixture(7, 1)
        task['edges'] = [['x00', 'x01']]
        task['counts'] = parent_audit.count_combinations(task['predictors'], task['edges'])
        selected = {7: [('x00', 'x02', 'x03')]}
        _, sample = sampling.sample([task], selected, {'song': reg}, 10000, 1)
        expected = {combo for combo in parent_audit.enumerate_combinations(task['predictors'], task['edges'])
                    if len(combo) == 3 and combo not in selected[7]}
        self.assertEqual({tuple(s['predictors']) for s in sample}, expected)

    def test_allocation_honors_total_small_strata_and_minimum(self):
        a = sampling.allocation([2, 100, 200, 0], 40, 5)
        self.assertEqual(a.sum(), 40)
        self.assertEqual(a[0], 2)
        self.assertEqual(a[-1], 0)
        self.assertTrue((a[1:3] >= 5).all())
        with self.assertRaises(ValueError):
            sampling.allocation([100]*4, 10, 4)

    def test_hypergeometric_interval_has_nominal_small_population_coverage(self):
        M, n = 30, 6
        intervals = [sampling.hypergeom_interval(M, n, x) for x in range(n+1)]
        for good in range(M+1):
            coverage = sum(hypergeom.pmf(x, M, good, n) for x, (lo, hi) in enumerate(intervals) if lo <= good <= hi)
            self.assertGreaterEqual(coverage, .95-1e-12)

    def test_no_hits_do_not_imply_no_false_negatives(self):
        strata = [dict(population_size=1000000, sample_size=100)]
        result = sampling.estimate(strata, {0: 0}, retained_qualifying=100)
        self.assertEqual(result['false_negative_fraction_estimate'], 0.)
        self.assertGreater(result['false_negative_fraction_simultaneous_interval'][1], 0.)
        self.assertEqual(sampling.hypergeom_interval(10, 10, 3), (3, 3))

    def test_audit_finds_suppressed_triples_in_controlled_census(self):
        task, reg = task_fixture(8, 1)
        selected = {7: [('x00', 'x01', 'x02')]}
        strata, samples = sampling.sample([task], selected, {'song': reg}, 10000, 1)
        # A fixed quality label invisible to screening; audit never feeds it back.
        hidden = {('x03', 'x04', 'x05'), ('x04', 'x06', 'x07')}
        hits = {0: sum(tuple(s['predictors']) in hidden for s in samples)}
        estimate = sampling.estimate(strata, hits, retained_qualifying=1)
        self.assertEqual(estimate['missed_qualifying_estimate'], 2.)
        self.assertEqual(estimate['false_negative_fraction_estimate'], 2/3)


class PipelineTests(unittest.TestCase):
    def test_preparation_projection_does_not_scale_fixed_small_sample_latency(self):
        measurements = [dict(seconds=7., n_train_max=30, variables=1000),
                        dict(seconds=30., n_train_max=20000, variables=1200)]
        self.assertAlmostEqual(benchmark.preparation_seconds(measurements, 20000, 1000, 8), 60*1.008)
        self.assertAlmostEqual(benchmark.preparation_seconds(measurements, 40000, 1000, 8), 120*1.008)

    def test_calendar_embargo_and_whole_song_label_availability(self):
        frame = pd.DataFrame({'month': ['2010-12', '2010-12', '2011-01', '2018-01', '2018-12', '2019-01'],
                              'label_available_date': ['2010-12-31', '2011-01-01', '2011-01-02',
                                                       '2018-12-31', '2019-01-01', '2019-02-01']})
        train, valid = engine.masks(frame, np.ones(6), ['2018-01', '2019-01'], 0)
        np.testing.assert_array_equal(train, [True, False, False, False, False, False])
        np.testing.assert_array_equal(valid, [False, False, False, True, False, False])

    def test_checkpoint_identity_corruption_and_resume_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.sqlite'
            store = runner.Store(path, 'frozen')
            store.put('screen', 3, {'value': np.arange(4)})
            store.put('screen', 3, {'value': np.arange(4)})
            segment = store.start_segment(100.)
            store.finish_segment(segment, 25.)
            store.close()
            store = runner.Store(path, 'frozen')
            np.testing.assert_array_equal(store.get('screen', 3)['value'], np.arange(4))
            self.assertEqual(store.previous_runtime(), 25.)
            with self.assertRaises(ValueError):
                store.put('screen', 3, {'value': np.arange(5)})
            store.db.execute("UPDATE records SET payload=X'00' WHERE kind='screen'")
            store.db.commit(); store.close()
            with self.assertRaises(ValueError):
                runner.Store(path, 'frozen')
            with self.assertRaises(ValueError):
                runner.Store(path, 'changed')

    def test_stability_is_locked_until_all_lower_screens_are_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            store = runner.Store(Path(directory)/'test.sqlite', 'frozen')
            task, _ = task_fixture()
            with self.assertRaises(ValueError):
                runner.freeze_candidates([task], store, 'pilot', None)
            store.close()

    def test_stability_rule_requires_both_periods_and_incremental_value(self):
        skill = np.array([[.1, .2], [.1, -.01], [.1, .2], [.1, .2]])
        gain = np.array([[.01, .02], [.01, .02], [.04, -.01], [.001, .002]])
        status = np.zeros((4, 2), dtype=np.uint8)
        support = [{'support_sufficient': True}]*2
        np.testing.assert_array_equal(runner.qualify(skill, gain, status, support), [True, False, False, False])
        self.assertFalse(runner.qualify(skill, gain, status, [{'support_sufficient': False}]).any())

    def test_storage_format_has_explicit_fixed_upper_bound(self):
        self.assertEqual(runner.RESULT_DTYPE.itemsize, 42)
        records = 10097*c.CONFIG['triple_cap_per_target']+c.CONFIG['audit_samples_full']
        self.assertLess(records*runner.RESULT_DTYPE.itemsize, c.CONFIG['temporary_disk_limit_bytes'])


if __name__ == '__main__':
    unittest.main()
