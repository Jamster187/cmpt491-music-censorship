"""V4 enumeration, temporal alignment, OLS and checkpoint regressions."""
import itertools,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import cross_domain_v4_common as c
import cross_domain_v4_data as data
import cross_domain_v4_audit as audit
import cross_domain_v4_pilot as pilot
from regression_core import Fold

class EnumerationTests(unittest.TestCase):
 def test_closed_form_matches_complete_enumeration(self):
  rng=np.random.default_rng(44)
  for n in range(1,11):
   names=list(map(str,range(n)))
   for _ in range(8):
    edges=[x for x in itertools.combinations(names,2) if rng.random()<.25]
    triples=[x for x in itertools.combinations(names,3) if rng.random()<.1]
    combos=list(audit.enumerate_combinations(names,edges,triples));counts=audit.count_combinations(names,edges,triples)
    self.assertEqual(len(combos),len(set(combos)))
    self.assertEqual(counts,{k:sum(len(x)==k for x in combos) for k in [1,2,3]})
 def test_identity_excluded_in_every_direction(self):
  names=['sentiment_positive','sentiment_negative','sentiment_neutral','other']
  reg={n:dict(origin='music',kind='numeric',source_columns=[n],domain='affect',source=['lyrics'],base=n,lag=0,frequency='song',dependencies=[]) for n in names}
  for target in names[:3]:
   eligible,edges,triples=audit.constraints(target,names,reg,'raw');pairs=set(names[:3])-{target}
   self.assertNotIn(target,eligible)
   self.assertTrue(all(not pairs<=set(x) for x in audit.enumerate_combinations(eligible,edges,triples)))
 def test_shared_provenance_is_not_exclusion(self):
  reg={n:dict(origin='music',kind='numeric',source_columns=[n],domain=domain,source=['lyrics'],base=n,lag=0,frequency='song',dependencies=[]) for n,domain in [('a','affect'),('b','structure')]}
  names,_,_=audit.constraints('a',list(reg),reg,'raw');self.assertEqual(names,['b'])
  s=audit.category_subsets('a',names,reg);self.assertEqual(s['cross_domain'],{'b'});self.assertEqual(s['provenance_separated'],set())
 def test_large_counts_do_not_overflow(self):
  counts=audit.count_combinations([str(x) for x in range(5000)])
  self.assertGreater(counts[3],2**31);self.assertEqual(counts[3],5000*4999*4998//6)

class TemporalTests(unittest.TestCase):
 def test_native_quarter_context_preserves_reference(self):
  months=pd.period_range('2000-01','2000-06',freq='M');s=pd.Series([10.,20.],index=pd.period_range('2000Q1','2000Q2',freq='Q'))
  out,end=data.native_to_month(s,'Q',months)
  np.testing.assert_equal(out.to_numpy(),[10,10,10,20,20,20]);self.assertEqual(end.iloc[0],'2000-03-31');self.assertEqual(end.nunique(),2)
 def test_missing_native_period_not_skipped(self):
  s=pd.Series([100.,np.nan,121.],index=pd.period_range('2000-01',periods=3,freq='M'))
  out=data.change_native(s,'log_growth_positive_endpoints');self.assertTrue(out.isna().all())
 def test_native_growth_and_signed_change(self):
  s=pd.Series([100.,110.,121.]);np.testing.assert_allclose(data.change_native(s,'log_growth_positive_endpoints').iloc[1:],100*np.log(1.1))
  x=pd.Series([2.,1.,3.]);np.testing.assert_equal(data.change_native(x,'first_difference_native_period').iloc[1:].to_numpy(),[-1,2])
 def test_return_and_event_not_differenced(self):
  for name in ['FF_MKT_EXCESS','US_EQUITY_TOTAL_RETURN','US_CPI_YOY','US_FEDERAL_ELECTION_MONTH','US_NFCI']:
   self.assertEqual(data.transformation(name,{}),'identity_rate_change_or_event')
 def test_positive_lag_requires_complete_prior_period(self):
  saved_external=pilot.external;saved_ends=pilot.period_end
  try:
   idx=pd.period_range('2000-01',periods=5,freq='M')
   pilot.external=lambda track:pd.DataFrame({'q':[10,10,10,20,20]},index=idx)
   pilot.period_end=lambda:pd.DataFrame({'q':['2000-03-31']*3+['2000-06-30']*2},index=idx)
   f=pd.DataFrame({'month':['2000-02','2000-04','2000-05']});r={'x':dict(origin='external',base='q',lag=1,kind='numeric')}
   x=pilot.materialize(f,['x'],r,'raw').x
   self.assertTrue(pd.isna(x.iloc[0]));self.assertEqual(x.iloc[1],10);self.assertTrue(pd.isna(x.iloc[2]))
  finally:pilot.external=saved_external;pilot.period_end=saved_ends
 def test_lag_cannot_use_future_month(self):
  saved_external=pilot.external;saved_ends=pilot.period_end
  try:
   idx=pd.period_range('2000-01',periods=12,freq='M');pilot.external=lambda track:pd.DataFrame({'x':np.arange(12.)},index=idx);pilot.period_end=lambda:pd.DataFrame({'x':idx.end_time.strftime('%Y-%m-%d')},index=idx)
   f=pd.DataFrame({'month':['2000-07']});reg={'lag3':dict(origin='external',base='x',lag=3,kind='numeric')}
   self.assertEqual(pilot.materialize(f,['lag3'],reg,'raw').lag3.iloc[0],3.)
  finally:pilot.external=saved_external;pilot.period_end=saved_ends
 def test_whole_song_and_embargo(self):
  f=pd.DataFrame({'month':['1990-01','1990-02','2000-01','2000-02'],'last_chart_date':['1990-02-01','2000-01-01','2000-03-01','2002-01-01'],'label_available_date':['1990-07-01','2000-01-01','2000-08-01','2002-01-01']})
  tr,va=audit.masks(f,np.ones(4),['2000-01','2001-01'],0)
  np.testing.assert_equal(tr,[True,False,False,False]);np.testing.assert_equal(va,[False,False,True,False])

class OLSAndCheckpointTests(unittest.TestCase):
 def reg(self):
  return {n:dict(kind=kind,source_columns=[n],origin='music') for n,kind in [('x','numeric'),('z','numeric'),('cat','categorical')]}
 def frames(self):
  rng=np.random.default_rng(491);f=pd.DataFrame({'x':rng.normal(size=160),'z':rng.normal(size=160),'cat':np.resize(['a','b','c'],160),'song_id':[str(i) for i in range(160)]});f.loc[2,'x']=np.nan
  return f.iloc[:100].copy(),f.iloc[100:].copy()
 def test_encoder_uses_only_training_values(self):
  train,valid=self.frames();e=pilot.Encoder(self.reg()).fit(train,['x','cat']);first=e.transform(train).copy();state=c.digest(e.state)
  valid['x']=1e30;valid['cat']='future';e.transform(valid)
  self.assertEqual(state,c.digest(e.state));np.testing.assert_equal(first,e.transform(train))
 def test_categorical_counts_once(self):
  train,_=self.frames();e=pilot.Encoder(self.reg()).fit(train,['cat']);x=e.transform(train)
  self.assertEqual(len(e.groups),1);self.assertEqual(len(e.groups['cat']),2);self.assertEqual(x.shape[1],3)
 def test_sparse_metrics_and_cached_svd_match_full_rows(self):
  train,valid=self.frames();e=pilot.Encoder(self.reg()).fit(train,['x','z','cat']);x=e.transform(train);v=e.transform(valid)
  y=np.nan_to_num(train.x.to_numpy())+2*train.z.to_numpy();z=np.nan_to_num(valid.x.to_numpy())+2*valid.z.to_numpy()
  fold=Fold(x,v,y,z,np.ones(100),np.ones(60),e.groups,e,train,valid,{})
  combos=[('x',),('cat','z'),('cat','x','z')];fast,_=pilot.evaluate(fold,combos);slow,_=fold.evaluate(combos)
  for name in ['mse','mae','r2','skill']:np.testing.assert_allclose(fast[name],slow[name],rtol=1e-12,atol=1e-12)
  for combo in combos:self.assertLess(fold.reference_check(combo)['max_prediction_scaled_error'],1e-10)
 def test_checkpoint_resume_and_corruption(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'test.sqlite';s=pilot.Store(path,'a');s.put('one',{'r2':-.8});s.close()
   s=pilot.Store(path,'a');self.assertEqual(s.get('one'),{'r2':-.8});s.put('one',{'r2':-.8});s.put('two',{'r2':.3});s.close()
   with self.assertRaises(ValueError):pilot.Store(path,'wrong')
   s=pilot.Store(path,'a');s.db.execute("UPDATE results SET body='{}' WHERE key='one'");s.db.commit();s.close()
   with self.assertRaises(ValueError):pilot.Store(path,'a')
 def test_target_support_uses_calendar_not_row_position(self):
  bounds=audit.boundaries(['1958-08','2026-09']);self.assertEqual(bounds[-1],'2026-10');self.assertEqual(len(bounds),5)
 def test_no_private_artifact_under_public_path(self):
  self.assertNotEqual(c.PUBLIC,c.LOCAL);self.assertIn('experiments',c.LOCAL.parts)

if __name__=='__main__':unittest.main()
