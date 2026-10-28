"""Failure-oriented regression tests for new enrichment and temporal data layers."""
import json
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from music_enrichment_features import hdd, lyric_features, graph_features, title_features
from music_enrichment_views import chart_features
from music_enrichment_audio import accept, lookup
from external_historical_sources import numeric, period_dates, federal_election_day
from external_historical_features import compounded, drawdown, monthly_matrix
from external_historical_joins import asof_series, period_panel, release_context_keys
from external_historical_political import contains_us


class LocalEnrichmentTests(unittest.TestCase):
    def test_hdd_expected_unique_and_repeated_words(self):
        self.assertAlmostEqual(hdd([str(i) for i in range(50)]),1.)
        self.assertAlmostEqual(hdd(['same']*50),1/42)
        self.assertTrue(np.isnan(hdd(['short']*10)))

    def test_unknown_pronunciations_do_not_become_syllables_or_rhymes(self):
        dictionary={'cat':('K','AE1','T'),'hat':('HH','AE1','T')}
        result=lyric_features('cat\nhat\nunknown\ncat\nhat',dictionary)
        self.assertAlmostEqual(result['lyric_cmu_token_coverage'],.8)
        self.assertEqual(result['lyric_known_syllable_count'],4)
        self.assertTrue(np.isnan(result['lyric_syllable_count_complete']))
        self.assertTrue(np.isnan(result['lyric_adjacent_end_rhyme_share']))
        self.assertAlmostEqual(result['lyric_rhyme_pair_coverage'],.5)

    def test_provider_section_marker_absence_is_unknown(self):
        result=lyric_features('one line\none line',{})
        self.assertTrue(np.isnan(result['lyric_marked_section_count']))
        self.assertTrue(np.isnan(result['lyric_marked_chorus_token_share']))
        self.assertEqual(result['lyric_longest_identical_line_run'],2)
        result=lyric_features('[Verse 1]\none two\n[Chorus]\nthree four',{})
        self.assertEqual(result['lyric_marked_section_count'],2)
        self.assertEqual(result['lyric_marked_chorus_token_share'],.5)

    def test_graph_excludes_simultaneous_entrants_and_future_hits(self):
        weekly=pd.DataFrame([['a','2000-01-01',80],['b','2000-01-01',1],['c','2000-01-08',70]],columns=['song_id','chart_date','weekly_rank'])
        credits={'a':['x','y'],'b':['x','z'],'c':['x','w']}
        original=graph_features(weekly,credits,{}).set_index('song_id')
        self.assertEqual(original.loc['b','artist_prior_collaborator_count'],0)
        self.assertEqual(original.loc['c','artist_prior_collaboration_degree_max'],2)
        later=pd.concat([weekly,pd.DataFrame([['a','2000-01-15',1]],columns=weekly.columns)],ignore_index=True)
        pd.testing.assert_frame_equal(original,graph_features(later,credits,{}).set_index('song_id'))

    def test_title_year_and_version_are_textual_only(self):
        result=title_features('1999 (Live Version)')
        self.assertEqual(result['title_year_reference'],1999)
        self.assertEqual(result['title_version_marker'],1)
        self.assertTrue(np.isnan(title_features('No Year')['title_year_reference']))

    def test_chart_features_preserve_duplicate_source_rows_and_gate_window(self):
        data=pd.DataFrame([
            ['a','2000-01-01',100,0,0],['a','2000-01-01',90,0,1],
            ['b','2000-01-08',50,1,0],['a','2000-01-15',80,2,0],
            ['a','2000-01-29',10,3,0]],columns=['song_id','chart_date','weekly_rank','source_chart_index','source_row_index'])
        result,_=chart_features(data)
        self.assertEqual(len(result),len(data))
        a=result.loc[result.song_id.eq('a')]
        self.assertTrue(a.iloc[:3].chart_first4w_points_after_window.isna().all())
        self.assertEqual(a.iloc[-1].chart_first4w_points_after_window,33)
        self.assertEqual(a.iloc[2].chart_prior_absent_chart_count,1)
        self.assertEqual(a.iloc[2].chart_rank_improvement_per_elapsed_week,5)
        prefix,_=chart_features(data.iloc[:4])
        pd.testing.assert_frame_equal(result.iloc[:4].reset_index(drop=True),prefix)


class AudioGateTests(unittest.TestCase):
    def body(self):return {'metadata':{'tags':{'musicbrainz_recordingid':['r'],'musicbrainz_artistid':['a']},'audio_properties':{'length':200}}}

    def test_exact_identity_and_duration_are_all_required(self):
        body=self.body()
        self.assertTrue(accept(body,'r',['a'],201).startswith('exact_'))
        self.assertEqual(accept(body,'other',['a'],200),'recording_tag_mismatch')
        self.assertEqual(accept(body,'r',['a','guest'],200),'artist_tag_mismatch_or_missing')
        self.assertEqual(accept(body,'r',['a'],230),'duration_disagrees_review_required')
        self.assertEqual(accept(body,'r',['a'],np.nan),'duration_evidence_missing')

    def test_missing_feature_stays_missing_nonfinite_rejected(self):
        self.assertIsNone(lookup({},'rhythm.bpm'))
        with self.assertRaises(ValueError):lookup({'rhythm':{'bpm':float('inf')}},'rhythm.bpm')


class HistoricalAlignmentTests(unittest.TestCase):
    def test_country_codes_accept_numeric_source_format_without_substring_matches(self):
        for value in [2,2.0,'2','2, 20','20,2.0']:
            self.assertTrue(contains_us(value))
        for value in [20,'200','20, 12',np.nan]:
            self.assertFalse(contains_us(value))

    def source(self):
        return pd.DataFrame([
            {'series_id':'IP','frequency':'M','date':'2020-01-01','period_end':'2020-01-31','publication_date':'2020-02-14','vintage_date':'2020-02-14','value':1.,'units':'percent','source_url':'https://example.invalid','retrieval_date':'2026-10-28','license':'fixture','availability_status':'historical_release_vintage'},
            {'series_id':'IP','frequency':'M','date':'2020-02-01','period_end':'2020-02-29','publication_date':'2020-03-17','vintage_date':'2020-03-17','value':99.,'units':'percent','source_url':'https://example.invalid','retrieval_date':'2026-10-28','license':'fixture','availability_status':'historical_release_vintage'}])

    def test_asof_uses_release_day_never_observation_month_or_retrieval(self):
        result=asof_series(self.source(),['2020-02-13','2020-02-14','2020-02-15','2020-03-01','2020-03-17','2020-03-18'],'IP')
        self.assertTrue(np.isnan(result.iloc[0].value))
        self.assertTrue(np.isnan(result.iloc[1].value))
        self.assertEqual(result.value.iloc[2:].tolist(),[1.,1.,1.,99.])
        self.assertEqual(result.iloc[3]['date'],'2020-01-01')
        self.assertEqual(result.iloc[3].age_days,30)

    def test_asof_rejects_latest_snapshot_even_with_recent_publication_date(self):
        frame=self.source();frame['availability_status']='retrieved_snapshot_original_release_unknown'
        with self.assertRaisesRegex(ValueError,'historical-vintage'):asof_series(frame,['2020-02-20'],'IP')

    def test_missing_calendar_month_does_not_become_adjacent_rolling_return(self):
        frame=pd.DataFrame([['R','M','2020-01-01',10.],['R','M','2020-03-01',10.]],columns=['series_id','frequency','date','value'])
        wide=monthly_matrix(frame)
        self.assertEqual(len(wide),3)
        self.assertTrue(compounded(wide.R,2).isna().all())
        self.assertAlmostEqual(compounded(pd.Series([10.,-10.]),2).iloc[-1],-1.)

    def test_drawdown_includes_initial_wealth_and_rejects_missing_bridge(self):
        self.assertEqual(drawdown(pd.Series([-20.,25.,-10.])).round(10).tolist(),[-20.,0.,-10.])
        with self.assertRaises(ValueError):drawdown(pd.Series([10.,np.nan,10.]))

    def test_quarterly_data_does_not_enter_monthly_panel(self):
        frame=pd.DataFrame([['GDP','Q','2020-01-01',2.],['U','M','2020-01-01',4.]],columns=['series_id','frequency','date','value'])
        self.assertNotIn('external__GDP',period_panel(frame,'M'))
        self.assertEqual(period_panel(frame,'Q').quarter.tolist(),['2020Q1'])

    def test_release_uncertainty_and_future_candidate_are_explicit(self):
        songs=pd.DataFrame([{'song_id':'year','mb_earliest_release_date':'1999','first_chart_date':'2000-02-01'},
            {'song_id':'future','mb_earliest_release_date':'2001-01-01','first_chart_date':'2000-02-01'},
            {'song_id':'valid','mb_earliest_release_date':'1999-12','first_chart_date':'2000-02-01'},
            {'song_id':'invalid','mb_earliest_release_date':'1999-02-30','first_chart_date':'2000-02-01'}])
        result=release_context_keys(songs).set_index('song_id')
        self.assertEqual(result.loc['year','release_month'],'')
        self.assertEqual(result.loc['future','release_month'],'')
        self.assertEqual(result.loc['valid','release_month'],'1999-12')
        self.assertFalse(result.release_original_edition_verified.any())
        self.assertEqual(result.loc['invalid','release_join_status'],'invalid_calendar_date')

    def test_numeric_and_calendar_parsers_fail_clearly(self):
        self.assertIsNone(numeric('-'));self.assertIsNone(numeric('-99.99'))
        self.assertEqual(numeric('1,234.5'),1234.5)
        with self.assertRaises(ValueError):numeric('not recorded')
        with self.assertRaises(ValueError):numeric('inf')
        self.assertEqual(period_dates('2020Q1','Q'),('2020-01-01','2020-03-31'))
        self.assertEqual(federal_election_day(2024).isoformat(),'2024-11-05')


if __name__=='__main__':unittest.main()
