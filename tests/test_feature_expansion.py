"""Adversarial as-of, identity, censoring, preprocessing and portable-model checks."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from threadpoolctl import threadpool_limits

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from feature_expansion_features import chart_features,outcome_table,lyric_features,consensus_credit,DEFINITIONS
from feature_expansion_common import split_frame,clean
from feature_expansion_predict import Preprocessor,export_estimator,predict_export
from feature_expansion_models import columns,model,choose_threshold,task_splits


def chart(rows):
    dates=sorted(set(r[0] for r in rows));positions={d:0 for d in dates};result=[]
    for date,sid,artist,rank in rows:
        positions[date]+=1;result.append(dict(chart_date=date,song_id=sid,artist=artist,title='Title '+sid,weekly_rank=rank,source_chart_index=dates.index(date),source_row_index=positions[date]))
    return pd.DataFrame(result)


class PointInTimeTests(unittest.TestCase):
    def setUp(self):
        self.rows=[('2001-01-06','old','A',80),('2001-01-13','old','A',30),('2001-01-13','solo','B',50),
            ('2001-01-20','new','A',90),('2001-01-20','same','A',70),('2001-01-20','old','A',5),('2001-01-27','new','A',1)]

    def test_future_suffix_invariance(self):
        prefix=chart(self.rows[:-1]);whole=chart(self.rows);a=chart_features(prefix);b=chart_features(whole)
        assert_frame_equal(a,b)

    def test_current_and_same_day_outcomes_excluded_from_history(self):
        f=chart_features(chart(self.rows)).set_index('song_id');a=f.loc['new'];b=f.loc['same']
        self.assertEqual(a.credit_prior_song_count,1);self.assertEqual(a.credit_prior_top10_song_count,0);self.assertEqual(a.credit_prior_top40_song_count,1)
        self.assertEqual(a.credit_prior_chart_points,21+71);self.assertEqual(a.credit_prior_chart_weeks,2);self.assertEqual(a.credit_prior_best_rank,30)
        self.assertEqual(a.same_credit_debut_cluster_size,1);self.assertEqual(a.debut_competing_new_entry_count,1)
        self.assertEqual(a.credit_days_since_last_entry,14)
        for name,d in DEFINITIONS.items():
            if d['group']=='artist_history':self.assertEqual(a[name],b[name])

    def test_duplicate_rows_preserved_points_not_weeks(self):
        rows=self.rows[:2]+[self.rows[1]]+self.rows[2:]
        f=chart_features(chart(rows)).set_index('song_id');self.assertEqual(f.loc['new','credit_prior_chart_points'],21+71*2);self.assertEqual(f.loc['new','credit_prior_chart_weeks'],2)
        o=outcome_table(chart(rows)).set_index('song_id');self.assertEqual(o.loc['old','chart_weeks_26'],3);self.assertEqual(o.loc['old','chart_points_26'],21+71*2+96)

    def test_exact_credits_and_titles_never_merge(self):
        f=chart_features(chart(self.rows+[('2001-01-27','alias','a',10),('2001-01-27','collab','A & B',20)])).set_index('song_id')
        self.assertEqual(f.loc['alias','credit_prior_song_count'],0);self.assertEqual(f.loc['collab','credit_prior_song_count'],0)

    def test_same_day_entity_batches_deduplicate_collaborators(self):
        mapping={'old':('entityA',),'new':('entityA','entityB'),'same':('entityA','entityB')}
        f=chart_features(chart(self.rows),credit_map=mapping).set_index('song_id')
        for sid in ['new','same']:
            self.assertEqual(f.loc[sid,'first_credited_entity_prior_song_count'],1);self.assertEqual(f.loc[sid,'credited_entities_prior_top10_mean'],0);self.assertEqual(f.loc[sid,'credit_team_prior_song_count'],0)
        variant={'artist-credit':[{'artist_id':'x'},{'artist_id':'x'},{'artist_id':'y'}]}
        self.assertEqual(consensus_credit([variant,variant]),('x','y'))
        self.assertIsNone(consensus_credit([variant,{'artist-credit':[{'artist_id':'z'}]}]))
        self.assertIsNone(consensus_credit([{'artist-credit':[{'name':'anonymous'}]}]))

    def test_release_dates_and_source_lifetime_columns_are_unused(self):
        a=chart(self.rows);b=a.copy();b['reported_peak_position']=1;b['total_chart_points']=999999;b['mb_earliest_release_date']='1900-01-01'
        assert_frame_equal(chart_features(a),chart_features(b))
        for track in ['strict','retrospective']:
            self.assertFalse(any('release_date' in c or c in ['best_chart_rank','chart_weeks','total_chart_points'] for c in columns(track,'combined')))

    def test_reentry_not_inferred_across_source_gap(self):
        rows=[('2001-01-01','a','X',50),('2001-01-08','b','Y',60),('2001-01-29','a','X',40),('2001-02-05','c','X',70)]
        f=chart_features(chart(rows)).set_index('song_id');self.assertEqual(f.loc['c','credit_prior_reentry_song_share'],0)
        rows=[('2001-01-01','a','X',50),('2001-01-08','b','Y',60),('2001-01-15','a','X',40),('2001-01-22','c','X',70)]
        self.assertEqual(chart_features(chart(rows)).set_index('song_id').loc['c','credit_prior_reentry_song_share'],1)

    def test_row_order_invariance(self):
        f=chart(self.rows);assert_frame_equal(chart_features(f),chart_features(f.sample(frac=1,random_state=3)))

    def test_outcomes_exclusive_window_and_right_censor(self):
        f=chart([('2001-01-01','s','X',50),('2001-03-26','s','X',1),('2001-07-02','end','Y',10)])
        o=outcome_table(f).set_index('song_id');self.assertEqual(o.loc['s','best_rank_12'],50);self.assertEqual(o.loc['s','best_rank_26'],1)
        self.assertTrue(o.loc['s','eligible_26']);self.assertFalse(o.loc['end','eligible_12'])

    def test_partition_purge_and_top10_already_known(self):
        f=pd.DataFrame(dict(song_id=list('abcdef'),first_chart_date=['2009-01-01','2009-12-01','2010-01-01','2017-12-01','2018-01-01','2026-08-01'],
            window_end_26=['2009-07-02','2010-06-01','2010-07-02','2018-06-01','2018-07-02','2027-02-01'],eligible_26=[True]*5+[False],debut_rank=[50,50,50,50,5,50]))
        s=split_frame(f);self.assertEqual(s['train'].song_id.tolist(),['a']);self.assertEqual(s['validation'].song_id.tolist(),['c']);self.assertEqual(s['test'].song_id.tolist(),['e'])
        self.assertEqual(len(task_splits(f,'top10')['test']),0)

    def test_strict_predictors_exclude_retrospective_measurements(self):
        strict=columns('strict','combined');self.assertIn('debut_rank',strict)
        self.assertTrue(all(c=='debut_rank' or DEFINITIONS[c]['historical_availability']=='C' for c in strict))
        self.assertIn('lyric_word_count',columns('retrospective','new_only'))


class LyricAndModelTests(unittest.TestCase):
    def test_lyrics_structure_and_short_text(self):
        f=lyric_features('[Chorus]\nI love you\nI love you\nDo you love me?','Title')
        self.assertEqual(f['lyric_word_count'],10);self.assertEqual(f['lyric_vocabulary_size'],5);self.assertAlmostEqual(f['lyric_repeated_line_share'],1/3)
        self.assertTrue(np.isnan(f['lyric_mattr']));self.assertAlmostEqual(f['lyric_question_line_share'],1/3)
        self.assertAlmostEqual(lyric_features(' '.join(['one','two']*30),'Other')['lyric_mattr'],.04)

    def test_title_equal_opening_and_unrecognized_brackets_are_lyrics(self):
        f=lyric_features('Stay\n[Stay with me]\n[Chorus]\nStay','Stay')
        self.assertEqual(f['lyric_word_count'],5);self.assertEqual(f['lyric_title_phrase_repetition'],60)

    def test_preprocessing_is_training_only_and_future_categories_unknown(self):
        tr=pd.DataFrame({'x':[1.,3.,np.nan],'empty':[np.nan]*3,'primary_genre':['pop','rock','pop']});future=pd.DataFrame({'x':[9999.],'empty':[88.],'primary_genre':['future']})
        p=Preprocessor(list(tr.columns)).fit(tr);state=json.dumps(clean(p.export()),sort_keys=True);a=p.transform(future)
        self.assertEqual(json.dumps(clean(p.export()),sort_keys=True),state);self.assertEqual(p.median.tolist(),[2.,0.]);self.assertEqual(a[0,-2:].sum(),0)

    def test_export_replay_all_supported_models(self):
        rng=np.random.default_rng(22);f=pd.DataFrame({'x':rng.normal(size=180),'y':rng.normal(size=180),'primary_genre':['a','b','c']*60});y=(f.x+f.y>0).astype(int)
        with threadpool_limits(limits=2):
            p=Preprocessor(list(f.columns)).fit(f);x=p.transform(f)
            for cls in [True,False]:
                for method,param in [('regularized',1),('tree',3),('hist_gradient_boosting',15)]:
                    e=model(method,param,cls).fit(x,y if cls else f.x*2+f.y);expected=e.predict_proba(x)[:,1] if cls else e.predict(x)
                    b=clean(dict(preprocessing=p.export(),estimator=export_estimator(e,cls)))
                    np.testing.assert_allclose(predict_export(json.loads(json.dumps(b)),f),expected,rtol=1e-10,atol=1e-9)


if __name__=='__main__':unittest.main()
