"""Calendar, weighting, missingness and source-integrity regression checks."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import moving_average_analysis as m


def fixture(months=25):
    rows = []
    for month in pd.period_range('2000-01', periods=months, freq='M').astype(str):
        for i in range(6):
            rows.append(dict(month=month, song_id=f's{i}', primary_genre='Pop',
                monthly_rank=i+1, **{c: i/5 for c in m.FEATURES}))
    return pd.DataFrame(rows)


class MovingAverageTests(unittest.TestCase):
    def test_trailing_window_has_no_partial_values_and_known_mean(self):
        f = pd.DataFrame({'n': [5]*14, 'mean': np.arange(14)/20,
                          'rank_weighted_mean': np.arange(14)/20})
        r = m.rolling(f, 5)
        self.assertTrue(r.rolling_12m_mean.iloc[:11].isna().all())
        self.assertAlmostEqual(r.rolling_12m_mean.iloc[11], .275)
        self.assertAlmostEqual(r.rolling_12m_mean.iloc[12], .325)
        self.assertEqual(r.rolling_12m_n.iloc[11], 60)
        self.assertEqual(r.rolling_12m_min_monthly_n.iloc[11], 5)
        self.assertEqual(r.rolling_qualifying_months.iloc[0], 1)

    def test_low_count_month_breaks_window_and_requires_full_recovery(self):
        f = pd.DataFrame({'n': [5]*25, 'mean': [.2]*25, 'rank_weighted_mean': [.3]*25})
        f.loc[12, 'n'] = 4
        r = m.rolling(f, 5)
        self.assertEqual(r.loc[12, 'sample_size_flag'], 'below_minimum')
        self.assertAlmostEqual(r.loc[11, 'rolling_12m_mean'], .2)
        self.assertTrue(r.rolling_12m_mean.iloc[12:24].isna().all())
        self.assertAlmostEqual(r.loc[24, 'rolling_12m_mean'], .2)
        self.assertAlmostEqual(r.loc[24, 'rank_weighted_rolling_12m_mean'], .3)

    def test_missing_calendar_month_is_not_compressed(self):
        f = fixture()
        f = f[~f.month.eq('2001-01')]
        data, calendar, _ = m.prepare(f, expected=False)
        self.assertEqual(len(calendar), 25)
        g = m.aggregate(data, calendar, by_genre=True)
        g = g[g.classifier.eq(m.FEATURES[0])].reset_index(drop=True)
        self.assertEqual(g.loc[12, 'n'], 0)
        self.assertTrue(pd.isna(g.loc[12, 'mean']))
        self.assertEqual(g.loc[12, 'sample_size_flag'], 'no_scores')
        self.assertTrue(g.rolling_12m_mean.iloc[12:24].isna().all())
        self.assertAlmostEqual(g.loc[24, 'rolling_12m_mean'], .5)

    def test_missing_scores_are_not_zero_and_weights_renormalize(self):
        f = fixture(months=1).iloc[:3].copy()
        f.loc[:, 'monthly_rank'] = [1, 51, 100]
        for c in m.FEATURES:
            f.loc[:, c] = [0., 1., np.nan]
        data, calendar, _ = m.prepare(f, expected=False)
        result = m.aggregate(data, calendar).iloc[0]
        self.assertEqual(result.n, 2)
        self.assertEqual(result.n_songs_total, 3)
        self.assertEqual(result['mean'], .5)
        self.assertEqual(result['median'], .5)
        self.assertAlmostEqual(result['std'], np.sqrt(.5))
        self.assertAlmostEqual(result.rank_weighted_mean, 1/3)
        self.assertEqual(result.rank_weight_sum, 150)
        self.assertTrue(pd.isna(result.rolling_12m_mean))

    def test_song_repeats_across_months_but_duplicate_within_month_is_audited(self):
        f = fixture(months=2)
        duplicate = f.iloc[[0]].copy()
        duplicate.loc[:, 'monthly_rank'] = 51
        f = pd.concat([f, duplicate], ignore_index=True)
        before = f.copy(deep=True)
        data, calendar, audit = m.prepare(f, expected=False)
        self.assertEqual(len(data), 12)
        self.assertEqual(data.source_rows.sum(), 13)
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit.iloc[0].source_ranks, '1|51')
        self.assertEqual(audit.iloc[0].analysis_rank_weight, 75)
        self.assertEqual(data.song_id.nunique(), 6)
        pd.testing.assert_frame_equal(f, before)
        shuffled, cal2, a2 = m.prepare(f.sample(frac=1, random_state=24), expected=False)
        pd.testing.assert_frame_equal(data, shuffled)
        pd.testing.assert_frame_equal(audit, a2)
        self.assertEqual(list(calendar), list(cal2))

    def test_reject_classifier_or_genre_conflicts(self):
        f = fixture(months=2)
        f.loc[6, m.FEATURES[0]] = np.nan
        with self.assertRaisesRegex(ValueError, 'differs within'):
            m.prepare(f, expected=False)
        f = fixture(months=2)
        f.loc[6, 'primary_genre'] = 'Rock'
        with self.assertRaisesRegex(ValueError, 'differs within'):
            m.prepare(f, expected=False)

    def test_months_equally_weighted_not_pooled_by_n(self):
        # Eleven n=5 months with mean 0; one n=50 month with mean 1.
        f = pd.DataFrame({'n': [5]*11+[50], 'mean': [0.]*11+[1.],
                          'rank_weighted_mean': [0.]*11+[1.]})
        r = m.rolling(f, 5).iloc[-1]
        self.assertAlmostEqual(r.rolling_12m_mean, 1/12)
        self.assertNotAlmostEqual(r.rolling_12m_mean, 50/105)

    def test_export_determinism_flags_and_sparse_genres(self):
        f = fixture()
        sparse = f[f.song_id.eq('s0')].copy()
        sparse.loc[:, 'primary_genre'] = 'Sparse'
        sparse.loc[:, 'song_id'] = 'sparse_song'
        f = pd.concat([f, sparse], ignore_index=True)
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'
            tables = m.build(a, f, render=False, expected=False)
            m.build(b, f.sample(frac=1, random_state=17), render=False, expected=False)
            for path in (a/'data').iterdir():
                self.assertEqual(path.read_bytes(), (b/'data'/path.name).read_bytes(), path.name)
            cov = tables['coverage_summary']
            sparse_rows = cov[cov.primary_genre.eq('Sparse')]
            self.assertTrue(sparse_rows.months_below_minimum.eq(25).all())
            self.assertTrue(sparse_rows.valid_rolling_endpoints.eq(0).all())
            self.assertTrue((~sparse_rows.individual_plot_generated).all())
            pop = cov[cov.primary_genre.eq('Pop')]
            self.assertTrue(pop.individual_plot_generated.all())
            self.assertTrue(pop.valid_rolling_endpoints.eq(14).all())
            overall = tables['monthly_classifier_overall']
            genre = tables['monthly_classifier_by_genre']
            calendar = pd.period_range('2000-01', periods=25, freq='M').astype(str)
            bad = genre.copy()
            bad.iloc[1] = bad.iloc[0]
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                m.validate_outputs(overall, bad, calendar, ['Pop', 'Sparse'])
            bad = genre.copy()
            bad.loc[bad.primary_genre.eq('Sparse'), 'sample_size_flag'] = 'sufficient'
            with self.assertRaisesRegex(ValueError, 'flags inconsistent'):
                m.validate_outputs(overall, bad, calendar, ['Pop', 'Sparse'])


class PublicInputTests(unittest.TestCase):
    def test_real_calendar_duplicates_counts_and_integrity(self):
        before = m.descriptive.sha(m.INPUT)
        f = pd.read_csv(m.INPUT, keep_default_na=False, na_values=[''])
        scores_and_genres = f[['month','song_id','primary_genre']+m.FEATURES].copy(deep=True)
        data, calendar, audit = m.prepare(f)
        self.assertEqual(len(calendar), 818)
        self.assertEqual(len(data), 81794)
        self.assertEqual(data.source_rows.sum(), 81797)
        self.assertEqual(data.song_id.nunique(), 28041)
        self.assertEqual(len(audit), 3)
        overall = m.aggregate(data, calendar)
        genre = m.aggregate(data, calendar, by_genre=True)
        m.validate_outputs(overall, genre, calendar, sorted(data.primary_genre.unique()))
        self.assertEqual(len(overall), 34356)
        self.assertEqual(len(genre), 549696)
        self.assertEqual(genre.primary_genre.nunique(), 16)
        pd.testing.assert_frame_equal(scores_and_genres, f[scores_and_genres.columns])
        self.assertEqual(before, m.descriptive.sha(m.INPUT))
        # Cross-check an actual monthly mean against a direct unique-song calculation.
        sample = overall[(overall.month == '2020-01') & (overall.classifier == 'll_violence')].iloc[0]
        self.assertAlmostEqual(sample['mean'], data.loc[data.month.eq('2020-01'), 'll_violence'].mean())
        g = overall[overall.classifier.eq('ll_violence')].set_index('month')
        self.assertAlmostEqual(g.loc['2020-12', 'rolling_12m_mean'],
                              g.loc['2020-01':'2020-12', 'mean'].mean())


if __name__ == '__main__':
    unittest.main()
