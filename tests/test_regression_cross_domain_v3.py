"""V3 completeness, provenance separation, OLS and durable-checkpoint safeguards."""
from pathlib import Path
import itertools
import math
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import regression_cross_domain_spec as spec
import regression_cross_domain_core as core
from regression_cross_domain_store import Store


class CrossDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):spec.LOCAL.mkdir(parents=True,exist_ok=True)

    def candidate(self,names):
        row=sorted(spec.NAMES.index(n) for n in names)+[255]*(3-len(names))
        ids=np.flatnonzero((spec.catalog()==row).all(axis=1));self.assertEqual(len(ids),1);return int(ids[0])

    def test_complete_registry_and_catalog(self):
        self.assertEqual(len(spec.NAMES),129)
        self.assertEqual(sum(r['origin']=='new' for r in spec.REGISTRY.values()),57)
        self.assertEqual(sum(r['meaningful_numerical'] for r in spec.REGISTRY.values()),125)
        c=spec.catalog();self.assertEqual(len(c),sum(math.comb(129,k) for k in [1,2,3]))
        self.assertEqual(len(np.unique(c,axis=0)),len(c))
        for k in [1,2,3]:self.assertEqual(int(((c!=255).sum(axis=1)==k).sum()),math.comb(129,k))
        self.assertNotIn('genre_confidence',spec.REGISTRY)
        self.assertFalse(spec.REGISTRY['debut_season_phase']['meaningful_numerical'])
        self.assertFalse(spec.REGISTRY['chart_weekday']['meaningful_numerical'])

    def test_dependency_and_provenance_categories(self):
        for target,predictor in [('duration_seconds','mb_duration_max_seconds'),('ll_violence','lyric_content_distance_recent_chart'),('lyric_word_count','lyric_mean_line_length'),('best_rank_26','top10_12'),('debut_time_years','primary_genre'),('last_chart_date','observed_lifetime_chart_points')]:
            self.assertEqual(spec.pair(target,predictor)[0],1,(target,predictor))
        self.assertEqual(spec.pair('ll_sexual_content','detox_sexual_explicit')[0],2)
        self.assertEqual(spec.pair('ll_sexual_content','lyric_word_count')[0],3)
        self.assertEqual(spec.pair('debut_time_years','mb_release_year')[0],3)
        self.assertEqual(spec.pair('duration_seconds','lyric_word_count')[0],3)
        self.assertEqual(spec.pair('credit_prior_song_count','previous_chart_new_entry_count')[0],4)
        self.assertEqual(spec.pair('duration_seconds','primary_genre')[0],4)
        self.assertEqual(spec.pair('ll_sexual_content','credit_prior_song_count')[0],5)
        self.assertEqual(spec.pair('lyric_repeated_line_share','primary_genre')[0],5)
        for a in spec.NAMES:
            for b in spec.NAMES:
                if spec.pair(a,b)[0]==5:
                    self.assertNotEqual(spec.REGISTRY[a]['family'],spec.REGISTRY[b]['family'])
                    self.assertFalse(set(spec.REGISTRY[a]['provenance'])&set(spec.REGISTRY[b]['provenance']))

    def test_compound_sentiment_leak_and_mixed_categories(self):
        categories,bits=spec.relations('sentiment_positive')
        cid=self.candidate(['sentiment_negative','sentiment_neutral'])
        self.assertEqual(categories[cid],1);self.assertTrue(bits[cid]&256)
        cid=self.candidate(['sentiment_negative','sentiment_neutral','duration_seconds'])
        self.assertEqual(categories[cid],1)
        categories,_=spec.relations('ll_sexual_content')
        self.assertEqual(categories[self.candidate(['detox_toxicity','credit_prior_song_count'])],2)
        self.assertEqual(categories[self.candidate(['primary_genre','credit_prior_song_count'])],5)
        self.assertEqual(categories[self.candidate(['ll_sexual_content','duration_seconds'])],1)

    def frame(self):
        rng=np.random.default_rng(491);n=65;t=np.arange(n)
        return pd.DataFrame(dict(song_id=[str(i) for i in t],debut_rank=rng.normal(size=n),credit_prior_song_count=rng.integers(0,40,n),mb_duration_min_seconds=t.astype(float),mb_duration_max_seconds=t.astype(float),primary_genre=['Pop','Rock',None,'Jazz','Pop']*13,secondary_genres=['["Pop"]','["Rock"]','[]',None,'["Jazz"]']*13,debut_season_sin=np.sin(t),debut_season_cos=np.cos(t)))

    def fold(self):
        f=self.frame();names=['debut_rank','credit_prior_song_count','mb_duration_min_seconds','mb_duration_max_seconds','primary_genre','secondary_genres','debut_season_phase']
        e=core.Encoder().fit(f.iloc[:45],names);x=e.transform(f.iloc[:45]);v=e.transform(f.iloc[45:]);y=f.debut_rank.to_numpy()*2+np.sin(np.arange(len(f)))
        return core.v2core.original_core.Fold(x,v,y[:45],y[45:],np.ones(45),np.ones(20),e.groups,e,f.iloc[:45],f.iloc[45:],dict(start='2018-01-01',target='ll_violence',validation_variance=float(np.var(y[45:]))))

    def test_training_only_encoding_and_portable_predictions(self):
        f=self.frame();f.loc[0,'debut_rank']=np.nan
        e=core.Encoder().fit(f.iloc[:45],['debut_rank','primary_genre','secondary_genres','debut_season_phase']);before=spec.digest(e.state)
        held=f.iloc[45:].copy();held['debut_rank']=np.nan;held['primary_genre']='Unseen';held['secondary_genres']='["Unseen"]'
        a=e.transform(held);self.assertEqual(before,spec.digest(e.state));self.assertEqual(len(e.groups['debut_season_phase']),2)
        self.assertEqual(e.unsupported(held)['primary_genre'],20);self.assertTrue(np.isfinite(a).all())
        np.testing.assert_array_equal(a,core.Encoder(e.state).transform(held))

    def test_sparse_metrics_and_cached_fits_match_dense_and_full_svd(self):
        f=self.fold()
        combos=list(itertools.chain.from_iterable(itertools.combinations(f.groups,k) for k in [1,2,3]))
        sparse,_=core.evaluate(f,combos);dense,_=f.evaluate(combos)
        for name in ['r2','mae','mse','skill']:np.testing.assert_allclose(sparse[name],dense[name],rtol=1e-10,atol=1e-10)
        for combo in combos:
            f.reference_check(combo);model=core.export_model(f,combo,'lock');b,_,_=f.fit_batch([combo])
            np.testing.assert_allclose(core.predict_model(model,f.validation),f.V@b[:,0]+f.mean,rtol=1e-10,atol=1e-10)
            self.assertEqual(model['version'],spec.CONFIG['version'])

    def test_cutoff_rebuild_ignores_future_returns_and_masks_unfinished_history(self):
        q=pd.DataFrame(dict(song_id=['a','a','a','b'],chart_date=['2000-01-01','2000-01-08','2011-01-01','2009-01-01'],weekly_rank=[80,70,1,20]))
        f=pd.DataFrame(dict(song_id=['a','b','c'],eligible_26=[True]*3,window_end_26=['2000-07-01','2009-07-01','2010-07-01']))
        spec.asof.cache_clear()
        with patch.object(spec,'source_frame',return_value=f),patch.object(spec.v2,'labels_at',side_effect=lambda date:spec.v2.lifetime_at(q,date)):
            before=spec.asof('2010-01-01').set_index('song_id')
            self.assertEqual(before.loc['a','observed_lifetime_best_rank'],70)
            self.assertEqual(before.loc['a','observed_lifetime_chart_weeks'],2)
            self.assertEqual(before.loc['a','observed_lifetime_chart_points'],52)
            self.assertTrue(np.isnan(before.loc['b','observed_lifetime_best_rank']))
            self.assertNotIn('c',before.index)
        spec.asof.cache_clear()

    def test_checkpoint_resume_evaluation_cannot_rerank_and_corruption_fails(self):
        cats,_=spec.relations('ll_violence');ids=np.flatnonzero(cats>1)[:12];metadata={'validation_variance':2.,'baseline':{'mse':3.}}
        with tempfile.TemporaryDirectory(dir=spec.LOCAL) as d:
            identity={'fixture':1};store=Store('ll_violence',identity,base=d,sample_ids=ids)
            values=np.column_stack([np.linspace(.2,1.,len(ids)),np.linspace(.1,.9,len(ids))]);status=np.full(len(ids),2,np.uint16)
            store.save(0,0,values,status,metadata,{'fits':len(ids)});store.close()
            store=Store('ll_violence',identity,base=d,sample_ids=ids)
            self.assertEqual(store.completed(0),{0});self.assertFalse(store.complete())
            # Uncommitted array writes simulate a process interruption after flush.
            store.metrics[1]=999;store.metrics.flush();store.close()
            store=Store('ll_violence',identity,base=d,sample_ids=ids);self.assertEqual(store.completed(1),set())
            for fold in [1,2]:store.save(fold,0,values,status,metadata,{'fits':len(ids)})
            order=store.order().copy();store.save(3,0,values[::-1],status,metadata,{'fits':len(ids)})
            np.testing.assert_array_equal(order,store.order());self.assertTrue(store.complete(range(4)));store.close()
            with self.assertRaisesRegex(ValueError,'identity'):Store('ll_violence',{'fixture':2},base=d,sample_ids=ids)
            a=np.load(Path(d)/'metrics.npy',mmap_mode='r+');a[0,0,0]+=1;a.flush();del a
            with self.assertRaisesRegex(ValueError,'corrupt'):Store('ll_violence',identity,base=d,sample_ids=ids)

    def test_actual_fit_interruption_and_resume_match_uninterrupted_arrays(self):
        from regression_cross_domain_search import fit_fold
        fold=self.fold();available=list(fold.groups)
        ids=sorted(self.candidate(c) for k in [1,2,3] for c in itertools.combinations(available,k))
        with tempfile.TemporaryDirectory(dir=spec.LOCAL) as d:
            interrupted=Path(d)/'interrupted';complete=Path(d)/'complete';identity={'actual_fit_fixture':1}
            # More than one real chunk exercises skipping a committed block.
            with patch.dict(spec.CONFIG,checkpoint_rows=16,batch_size=7):
                store=Store('ll_violence',identity,base=interrupted,sample_ids=ids)
                fit_fold(store,fold,0,stop_after_chunks=1);self.assertEqual(store.completed(0),{0});store.close()
                store=Store('ll_violence',identity,base=interrupted,sample_ids=ids)
                store.metrics[0,16:]=12345;store.metrics.flush();store.close()
                store=Store('ll_violence',identity,base=interrupted,sample_ids=ids)
                for number in range(4):fit_fold(store,fold,number)
                expected=store.metrics.copy();status=store.status.copy();order=store.order().copy();store.close()
                store=Store('ll_violence',identity,base=complete,sample_ids=ids)
                for number in range(4):fit_fold(store,fold,number)
                np.testing.assert_array_equal(store.metrics,expected);np.testing.assert_array_equal(store.status,status);np.testing.assert_array_equal(store.order(),order);store.close()

    def test_report_intervals_preserve_pairing_and_year_diagnostic(self):
        from regression_cross_domain_report import Intervals,diagnostics
        fold=self.fold();fold.train=fold.train.assign(artist=['prior']*len(fold.train))
        fold.validation=fold.validation.assign(artist=['prior','new']*10,first_chart_date=['2018-01-01']*10+['2019-01-01']*10)
        pred=fold.z*.8;intervals=Intervals(fold,99);a=intervals.calculate(pred,pred)
        for row in a:
            if row['metric'] in ['delta_r2_vs_reference','rmse_reduction_vs_reference']:self.assertEqual(row['lower'],0);self.assertEqual(row['upper'],0)
        self.assertEqual(a,Intervals(fold,99).calculate(pred,pred))
        result=diagnostics(fold,fold.z)
        self.assertAlmostEqual(result['within_debut_year_r2'],1.)
        self.assertEqual(result['seen_exact_credit_n'],10);self.assertEqual(result['unseen_exact_credit_n'],10)


if __name__=='__main__':unittest.main()
