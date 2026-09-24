"""Known-answer calculations plus read-only checks against the final public input."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import descriptive_analysis as d


class CalculationTests(unittest.TestCase):
    def test_summary_quantiles_sample_variance_missing_and_outliers(self):
        f = pd.DataFrame({'x': [0., 1., 2., 3., 100., np.nan]})
        r = d.summary(f, ['x'], 'song').iloc[0]
        self.assertEqual(r.non_missing_n, 5)
        self.assertEqual(r.missing_n, 1)
        self.assertAlmostEqual(r.missing_pct, 100/6)
        self.assertEqual(r['mean'], 21.2)
        self.assertEqual(r['median'], 2)
        self.assertEqual((r.q25, r.q75, r.iqr), (1, 3, 2))
        self.assertAlmostEqual(r.variance, 1941.7)
        self.assertAlmostEqual(r['std'], np.sqrt(1941.7))
        self.assertEqual((r.minimum, r.maximum), (0, 100))
        self.assertEqual((r.lower_outlier_fence, r.upper_outlier_fence), (-2, 6))
        self.assertEqual(r.potential_outlier_n, 1)
        self.assertEqual(r.potential_outlier_pct, 20)
        self.assertEqual(len(f), 6)  # No outliers or missing rows removed.

    def test_empty_singleton_and_zero_iqr(self):
        f = pd.DataFrame({'empty': [np.nan]*4, 'one': [1., np.nan, np.nan, np.nan],
                          'constant': [0., 0., 0., 0.]})
        s = d.summary(f, list(f), 'song').set_index('variable')
        self.assertTrue(pd.isna(s.loc['empty', 'mean']))
        self.assertTrue(pd.isna(s.loc['one', 'variance']))
        self.assertEqual(s.loc['constant', 'potential_outlier_n'], 0)
        self.assertEqual(s.loc['constant', 'missing_n'], 0)

    def test_pairwise_correlations_ties_missing_constants(self):
        f = pd.DataFrame({'x': [1., 2., 2., 4., 99.], 'y': [4., 3., 3., 1., np.nan],
                          'constant': [1.]*5, 'sparse': [1., np.nan, np.nan, 2., np.nan]})
        result = d.correlations(f, list(f), 'song')
        for method, table in result.items():
            self.assertEqual(len(table), 6)
            pair = table[(table.variable_x == 'x') & (table.variable_y == 'y')].iloc[0]
            self.assertEqual(pair.pairwise_n, 4)
            self.assertAlmostEqual(pair.correlation, -1.)
            self.assertTrue(table.loc[table.variable_y.isin(['constant', 'sparse']), 'correlation'].isna().all())
            self.assertTrue(table.weighting.eq('song').all())
        # Spearman must rerank within paired cases, not rank then drop missing rows.
        g = pd.DataFrame({'a': [1., 2., 3., 4.], 'b': [1., 4., np.nan, 2.]})
        self.assertAlmostEqual(d.correlations(g, list(g), 'song')['spearman'].iloc[0].correlation, .5)

    def test_dedup_invariance_order_and_weighting(self):
        f = pd.DataFrame({'song_id': ['b', 'a', 'a'], 'month': ['2000-01', '2000-01', '2000-02'],
                          'monthly_rank': [10, 20, 1], 'score': [0., 1., 1.]})
        songs = d.song_level(f)
        self.assertEqual(songs.song_id.tolist(), ['a', 'b'])
        self.assertNotIn('monthly_rank', songs)
        self.assertEqual(songs.score.mean(), .5)
        self.assertAlmostEqual(f.score.mean(), 2/3)
        pd.testing.assert_frame_equal(songs, d.song_level(f.iloc[::-1]))
        f.loc[2, 'score'] = np.nan
        with self.assertRaisesRegex(ValueError, 'Inconsistent song-level'):
            d.song_level(f)


class PublicDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = d.sha(d.INPUT)
        cls.frame = pd.read_csv(d.INPUT, keep_default_na=False, na_values=[''])
        cls.songs = d.validate(cls.frame)

    @classmethod
    def tearDownClass(cls):
        if d.sha(d.INPUT) != cls.before:
            raise AssertionError('Public source modified')

    def test_dimensions_required_columns_ranks_and_genres(self):
        self.assertEqual(self.frame.shape, (81797, 78))
        self.assertEqual(self.frame.month.nunique(), 818)
        self.assertEqual(len(self.songs), 28041)
        self.assertEqual(self.frame.primary_genre.nunique(), 16)
        self.assertEqual(len(d.FEATURES), 42)
        self.assertTrue(set(d.NUMERIC) <= set(self.frame))
        self.assertTrue(self.frame.monthly_rank.between(1, 100).all())
        self.assertEqual(self.songs.song_id.nunique(), len(self.songs))

    def test_invalid_input_fails_clearly(self):
        with self.assertRaisesRegex(ValueError, 'Missing required columns'):
            d.validate(self.frame.drop(columns='emotion_joy'))
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            d.validate(self.frame.iloc[:-1])
        bad = self.frame.head(3).copy()
        bad.loc[bad.index[0], 'monthly_rank'] = 101
        with self.assertRaisesRegex(ValueError, 'rank range'):
            d.validate(bad, expected=False)

    def test_group_totals_and_availability_denominators(self):
        genre = d.group_counts(self.frame, 'primary_genre')
        self.assertEqual(genre.observation_count.sum(), len(self.frame))
        self.assertEqual(genre.unique_songs.sum(), len(self.songs))
        self.assertAlmostEqual(genre.observation_pct.sum(), 100)
        av = d.availability(self.frame)
        for dimension in ['decade', 'primary_genre', 'rank_band']:
            g = av[(av.group_dimension == dimension) & (av.measure == 'lyrics_available')]
            self.assertEqual(g.observation_count.sum(), len(self.frame))
            self.assertEqual(g.available_observations.sum(), self.frame.lyrics_available.sum())

    def test_generated_outputs_integrity_and_no_source_modification(self):
        # Exercise the real report builder in an isolated location, not tracked outputs.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            tables = d.build(out, self.frame, self.songs)
            self.assertEqual(len(tables['summary_statistics']), 52)
            self.assertEqual(len(tables['song_level_summary_statistics']), 48)
            self.assertEqual(len(tables['missingness']), 78)
            self.assertEqual(len(tables['genre_statistics']), 16)
            self.assertEqual(len(list((out/'figures').glob('*.png'))), 29)
            self.assertTrue((out/'descriptive_findings.md').is_file())
            for method in ['pearson', 'spearman']:
                t = tables[method+'_correlations']
                self.assertEqual(set(t.weighting), {'song', 'observation'})
                self.assertTrue(t.correlation.dropna().between(-1, 1).all())
                self.assertTrue((t.pairwise_n > 0).all())
                self.assertFalse(((t.weighting == 'song') &
                    (t.variable_x.eq('monthly_rank') | t.variable_y.eq('monthly_rank'))).any())
            self.assertEqual(d.sha(d.INPUT), self.before)


if __name__ == '__main__':
    unittest.main()
