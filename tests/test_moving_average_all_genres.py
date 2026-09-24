"""Overlay regressions: frozen values, NaN gaps, coverage and fixed styling."""
from pathlib import Path
import sys
import tempfile
import unittest

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import moving_average_all_genres as a


def fixture(classifier='ll_explicit_language'):
    months=pd.period_range('2000-01',periods=121,freq='M').astype(str)
    rows=[]
    for genre in a.STYLES:
        for i,month in enumerate(months):
            value = (i/150 if i != 60 else np.nan) if genre == 'Pop' else (.3 if i in [0,120] else np.nan) if genre == 'Latin' else np.nan
            rows.append(dict(month=month,primary_genre=genre,classifier=classifier,rolling_12m_mean=value))
    return pd.DataFrame(rows)


class OverlayTests(unittest.TestCase):
    def test_exact_arrays_keep_gap_and_isolated_endpoints(self):
        frame=fixture()
        before=frame.copy(deep=True)
        fig,records=a.plot(frame,'ll_explicit_language')
        try:
            self.assertEqual([r['primary_genre'] for r in records],['Pop','Latin'])
            self.assertEqual([r['valid_endpoints'] for r in records],[120,2])
            ax=fig.axes[0]
            self.assertEqual(len(fig.axes),1)
            self.assertEqual(ax.get_ylim(),(0.,1.))
            for line,r in zip(ax.lines,records):
                g=frame[frame.primary_genre.eq(r['primary_genre'])]
                np.testing.assert_array_equal(line.get_ydata(),g.rolling_12m_mean.to_numpy())
                self.assertEqual(line.get_color(),a.STYLES[r['primary_genre']][0])
            self.assertTrue(np.isnan(ax.lines[0].get_ydata()[60]))
            self.assertEqual(ax.lines[1].get_marker(),'.')
            # NaNs form separate finite subpaths; no dropna/interpolation bridge.
            self.assertEqual(sum(code == 1 for _,code in ax.lines[0].get_path().iter_segments()),2)
            self.assertEqual(sum(code == 1 for _,code in ax.lines[1].get_path().iter_segments()),2)
            pd.testing.assert_frame_equal(before,frame)
        finally:
            plt.close(fig)

    def test_major_coverage_threshold_is_inclusive_and_not_named_genre_selection(self):
        frame=fixture()
        frame.loc[frame.primary_genre.eq('Latin'),'rolling_12m_mean']=frame.loc[frame.primary_genre.eq('Pop'),'rolling_12m_mean'].to_numpy()
        frame.loc[frame.primary_genre.eq('Pop'),'rolling_12m_mean']=np.nan
        fig,records=a.plot(frame,'ll_explicit_language',major=True)
        try:
            self.assertEqual([r['primary_genre'] for r in records],['Latin'])
            self.assertEqual(records[0]['valid_endpoints'],120)
        finally:
            plt.close(fig)
        frame.loc[frame.primary_genre.eq('Latin') & frame.month.eq('2000-01'),'rolling_12m_mean']=np.nan
        fig,records=a.plot(frame,'ll_explicit_language',major=True)
        plt.close(fig)
        self.assertEqual(records,[])

    def test_style_mapping_is_identical_across_classifiers_and_variants(self):
        self.assertEqual(len(a.STYLES),16)
        self.assertEqual(len(set(c for c,_ in a.STYLES.values())),16)
        for c in ['ll_explicit_language','emotion_joy']:
            for major in [False,True]:
                fig,records=a.plot(fixture(c),c,major)
                plt.close(fig)
                for r in records:
                    self.assertEqual((r['color'],r['line_style']),a.STYLES[r['primary_genre']])

    def test_figure_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            files=[]
            for i in range(2):
                fig,_=a.plot(fixture(),'ll_explicit_language')
                path=Path(tmp)/f'{i}.png'
                fig.savefig(path,dpi=75,metadata={'Software':a.VERSION})
                plt.close(fig)
                files.append(path.read_bytes())
            self.assertEqual(*files)

    def test_frozen_source_coverage_masks_and_prior_integrity(self):
        frame,coverage,prefix,protected=a.load_frozen()
        self.assertEqual(len(frame),549696)
        self.assertEqual(frame.month.nunique(),818)
        self.assertEqual(frame.classifier.nunique(),42)
        self.assertEqual(frame.primary_genre.nunique(),16)
        self.assertNotIn(a.MARKER,prefix)
        self.assertIn(a.ma.INPUT,protected)
        for c in a.ma.FEATURES:
            count=frame[frame.classifier.eq(c)].groupby('primary_genre').rolling_12m_mean.count()
            self.assertEqual(int(count.gt(0).sum()),8)
            self.assertEqual(int(count.ge(a.MAJOR_ENDPOINTS).sum()),5)
        broken=frame.copy()
        valid_index=broken.rolling_12m_mean.first_valid_index()
        broken.loc[valid_index,'rolling_12m_mean']=np.nan
        with self.assertRaisesRegex(ValueError,'validity mask'):
            a.validate(broken,coverage)
        broken=coverage.copy()
        mask=(broken.primary_genre == 'Pop') & (broken.classifier == 'll_violence')
        broken.loc[mask,'valid_rolling_endpoints']-=1
        with self.assertRaisesRegex(ValueError,'Coverage count'):
            a.validate(frame,broken)


if __name__ == '__main__':
    unittest.main()
