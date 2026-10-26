"""Regression safeguards for the exhaustive expanded-data campaign."""
import itertools
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from scipy import linalg
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import regression_expanded_spec as spec
import regression_expanded_core as core
from regression_expanded_store import Store


class ExpandedRegressionTests(unittest.TestCase):
    def frame(self):
        rng=np.random.default_rng(19);n=50
        return pd.DataFrame(dict(song_id=[str(i) for i in range(n)],debut_rank=rng.integers(1,100,n).astype(float),debut_reported_peak_position=np.full(n,4.),primary_genre=['rock','pop',None,'jazz','pop']*10,secondary_genres=['["rock"]','[]',None,'["jazz", "pop"]','["pop"]']*10))

    def fold(self):
        f=self.frame();f['debut_reported_peak_position']=f.debut_rank
        names=['debut_rank','debut_reported_peak_position','primary_genre','secondary_genres']
        e=core.BlockEncoder().fit(f.iloc[:35],names);x=e.transform(f.iloc[:35]);v=e.transform(f.iloc[35:])
        y=f.debut_rank.to_numpy()*.7+np.sin(np.arange(50))
        return core.original_core.Fold(x,v,y[:35],y[35:],np.ones(35),np.ones(15),e.groups,e,f.iloc[:35],f.iloc[35:],{'start':'2018-01-01'})

    def test_complete_universe_and_categories_count_once(self):
        self.assertEqual([len(spec.predictors(t)) for t in spec.CONFIG['tracks']],[37,108])
        self.assertEqual([len(spec.candidates(t)) for t in spec.CONFIG['tracks']],[8473,210042])
        self.assertEqual(len([r for r in spec.REGISTRY.values() if r['origin']=='new']),57)
        self.assertIn('debut_season_phase',spec.REGISTRY)
        self.assertNotIn('debut_season_cos',spec.REGISTRY)
        self.assertTrue(all(spec.REGISTRY[n]['availability']=='C' for n in spec.predictors('strict')))
        self.assertTrue(all('primary_genre' not in c for _,c in spec.candidates('strict')))

    def test_training_only_medians_categories_constants_and_replay(self):
        f=self.frame();f.loc[0,'debut_rank']=np.nan
        e=core.BlockEncoder().fit(f.iloc[:30],['debut_rank','debut_reported_peak_position','primary_genre'])
        before=spec.digest(e.state);held=f.iloc[30:].copy();held['primary_genre']='future';held['debut_rank']=np.nan
        transformed=e.transform(held)
        self.assertEqual(spec.digest(e.state),before)
        self.assertEqual(e.groups['debut_reported_peak_position'],[])
        self.assertEqual(e.unsupported(held)['primary_genre'],20)
        self.assertTrue(np.isfinite(transformed).all())
        np.testing.assert_array_equal(transformed,core.BlockEncoder(e.state).transform(held))

    def test_invalid_multilabel_and_infinity_fail(self):
        f=self.frame();f.loc[0,'secondary_genres']='{"invalid": 1}'
        with self.assertRaises(ValueError):core.BlockEncoder().fit(f,['secondary_genres'])
        f.loc[0,'debut_rank']=np.inf
        with self.assertRaises(ValueError):core.BlockEncoder().fit(f,['debut_rank'])

    def test_cached_ols_matches_direct_svd_and_training_metrics(self):
        f=self.fold()
        for k in [1,2,3]:
            for combo in itertools.combinations(f.groups,k):
                core.independent_reference(f,combo)
                b,_,_=f.fit_batch([combo]);pred=f.X@b[:,0]+f.mean
                expected=core.metrics(f.y,pred,f.w,f.mean,f.median)['r2']
                self.assertAlmostEqual(core.training_r2(f,b)[0],expected,places=10)
                model=core.export_model(f,combo,{},'test')
                np.testing.assert_allclose(core.predict_model(model,f.validation),f.V@b[:,0]+f.mean,rtol=1e-12,atol=1e-12)

    def test_lifetime_cutoff_cannot_see_future_return_or_rank(self):
        q=pd.DataFrame(dict(song_id=['a','a','a','b'],chart_date=['2000-01-01','2000-01-08','2011-01-01','2009-01-01'],weekly_rank=[80,70,1,20]))
        before=spec.lifetime_at(q[q.chart_date.lt('2010-01-01')],'2010-01-01')
        pd.testing.assert_frame_equal(before,spec.lifetime_at(q,'2010-01-01'))
        a=before.set_index('song_id').loc['a'];self.assertEqual(a.best_rank,70);self.assertEqual(a.chart_weeks,2);self.assertEqual(a.chart_points,52);self.assertTrue(a.mature and a.inactive)
        b=before.set_index('song_id').loc['b'];self.assertFalse(b.mature);self.assertFalse(b.inactive)
        # Future returns expose why inactivity is a proxy, not proof of completion.
        self.assertFalse(spec.lifetime_at(q,'2012-01-01').set_index('song_id').loc['a'].inactive)

    def test_only_published_debut_reports_enter_features(self):
        q=pd.DataFrame(dict(song_id=['a','a','a'],chart_date=['2000-01-01','2000-01-01','2000-01-08'],reported_last_week_rank=[np.nan,95,1],reported_peak_position=[90,80,1],reported_weeks_on_chart=[1,2,99]))
        r=spec.debut_reports(q).iloc[0]
        self.assertEqual(r.debut_reported_last_week_rank,95);self.assertEqual(r.debut_reported_peak_position,80);self.assertEqual(r.debut_reported_weeks_on_chart,2)

    def test_process_exit_rolls_back_uncommitted_checkpoint(self):
        import subprocess
        names=['debut_rank'];candidates=[(0,('debut_rank',))]
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'crash.sqlite'
            store=Store(path,{'crash':1},candidates,names);store.close()
            program="import sqlite3,sys,os; c=sqlite3.connect(sys.argv[1]); c.execute('BEGIN'); c.execute('INSERT INTO scores VALUES (0,0,0,1,1,0,1,0,NULL)'); os._exit(7)"
            process=subprocess.run([sys.executable,'-c',program,str(path)],check=False)
            self.assertEqual(process.returncode,7)
            store=Store(path,{'crash':1},candidates,names)
            self.assertEqual(store.completed(0),set())
            with self.assertRaisesRegex(ValueError,'Incomplete'):store.rankings()
            store.close()

    def test_transactional_resume_ranking_and_identity_guard(self):
        fold=self.fold();names=list(fold.groups);candidates=list(enumerate(itertools.chain.from_iterable(itertools.combinations(names,k) for k in [1,2,3])))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'resume.sqlite';q=Path(d)/'full.sqlite'
            s=Store(p,{'identity':1},candidates,names)
            result,timing=fold.evaluate([c for _,c in candidates[:2]])
            s.save(0,candidates[:2],result,fold.metadata,timing);s.close()
            s=Store(p,{'identity':1},candidates,names);t=Store(q,{'identity':1},candidates,names)
            for number in range(4):
                for store in [s,t]:
                    pending=[r for r in candidates if r[0] not in store.completed(number)]
                    r,timing=fold.evaluate([c for _,c in pending]);store.save(number,pending,r,fold.metadata,timing)
            a=[tuple(r) for r in s.db.execute('SELECT * FROM scores ORDER BY id,fold')]
            b=[tuple(r) for r in t.db.execute('SELECT * FROM scores ORDER BY id,fold')]
            self.assertEqual(a,b);pd.testing.assert_frame_equal(s.rankings(),t.rankings())
            ranked=s.rankings().copy()
            with s.db:s.db.execute('UPDATE scores SET skill=-999,r2=-999 WHERE fold=3')
            pd.testing.assert_frame_equal(ranked,s.rankings());self.assertTrue(s.complete(range(4)))
            s.close();t.close()
            with self.assertRaisesRegex(ValueError,'identity'):Store(p,{'identity':2},candidates,names)
            with self.assertRaisesRegex(ValueError,'catalog'):Store(p,{'identity':1},candidates[:-1],names)


if __name__=='__main__':unittest.main()
