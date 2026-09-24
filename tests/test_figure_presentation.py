"""Regressions for primary-series scaling, outlier disclosure and audit coverage."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import figure_style as s
import figure_audit as a
import moving_average_figures as mf


class PresentationTests(unittest.TestCase):
    def test_score_bounds_contain_primary_without_forcing_zero_or_large_floor(self):
        for values in [[.31,.67],[.00002,.00015],[0,0],[1,1],[.5,.5],[.05,.95]]:
            low,high=s.score_limits(values)
            self.assertGreaterEqual(low,0);self.assertLessEqual(high,1)
            self.assertLess(low,high)
            s.assert_contained(values,(low,high))
        self.assertGreater(s.score_limits([.31,.67])[0],0)
        self.assertLess(s.score_limits([.00002,.00015])[1],.001)
        self.assertEqual(s.score_limits([np.nan]),(0,1))
        with self.assertRaises(ValueError):s.score_limits([1.1])
        with self.assertRaisesRegex(ValueError,'clipped'):s.assert_contained([.2,.8],(.3,.7))

    def test_country_identity_attack_rolling_lines_drive_axis_and_raw_is_disclosed(self):
        folder=a.m.OUTPUT/'data'
        overall=pd.read_csv(folder/'monthly_classifier_overall.csv.xz',float_precision='round_trip')
        genres=pd.read_csv(folder/'monthly_classifier_by_genre.csv.xz',float_precision='round_trip')
        coverage=pd.read_csv(folder/'coverage_summary.csv')
        g=genres[genres.classifier.eq('detox_identity_attack') & genres.primary_genre.eq('Country')]
        before=g.copy(deep=True)
        captured={}
        def inspect(fig,path,family,description,panels,**kwargs):
            if Path(path).stem=='country':
                ax,count_ax=fig.axes
                expected=g[['rolling_12m_mean','rank_weighted_rolling_12m_mean']].to_numpy().ravel()
                self.assertEqual(ax.get_ylim(),s.score_limits(expected))
                self.assertLess(ax.get_ylim()[1],.03)
                self.assertGreater(s.metrics(expected,ax.get_ylim())['utilization_ratio'],.75)
                for label,column in [('Equal weight; 12-month mean','rolling_12m_mean'),('Rank-weighted sensitivity','rank_weighted_rolling_12m_mean')]:
                    line=next(line for line in ax.lines if line.get_label()==label)
                    np.testing.assert_array_equal(line.get_ydata(),g[column].to_numpy())
                self.assertGreater(kwargs['context_clipped'],0)
                self.assertIn('outside view',kwargs['note'])
                self.assertTrue(kwargs['reference_path'].endswith('country_full_scale.png'))
                self.assertEqual(count_ax.get_ylim()[0],0)
                captured['country']=True
            if Path(path).stem=='country_full_scale':
                self.assertEqual(fig.axes[0].get_ylim(),(0,1));captured['reference']=True
            plt.close(fig)
        with tempfile.TemporaryDirectory() as tmp,patch.object(mf,'FEATURES',['detox_identity_attack']),patch.object(s,'emit',inspect):
            mf.figures(Path(tmp),overall,genres,coverage)
        self.assertEqual(captured,{'country':True,'reference':True})
        pd.testing.assert_frame_equal(g,before)

    def test_published_audit_covers_catalog_and_no_unresolved_default_flags(self):
        a.validate()
        audit=pd.read_csv(a.ANALYSIS/'figure_audit.csv').fillna('')
        original=pd.read_csv(a.BASELINE)
        self.assertEqual(len(original),615)
        self.assertEqual(original.figure_family.nunique(),13)
        self.assertTrue(set(original.figure_path)<=set(audit.figure_path))
        self.assertTrue(audit.remaining_issue.eq('').all())
        self.assertTrue(audit.labels_inside_canvas.all())
        self.assertTrue((audit.primary_min.astype(float) >= audit.axis_min.astype(float)-1e-10).all())
        self.assertTrue((audit.primary_max.astype(float) <= audit.axis_max.astype(float)+1e-10).all())
        clipped=audit[audit.context_points_clipped.gt(0)]
        self.assertTrue(clipped.full_scale_reference_available.all())
        self.assertTrue(clipped.context_note.ne('').all())


if __name__=='__main__':unittest.main()
