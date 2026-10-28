"""Financial-panel regression tests: time direction, gaps, frequency and permissions."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import financial_acquisition_sources as sources
from financial_acquisition_common import sha,source_path,write_csv
from financial_acquisition import (compound,period_growth,wealth,window_mdd,online_regime,derive,
    monthly_native,point_in_time,strict_native,longest_gap,boolean)
from financial_acquisition_sources import number,release_calendar


def spec(freq='M',public=True,aggregation='native_month'):
    return dict(native_frequency=freq,redistribution_permitted=public,monthly_aggregation=aggregation,
        source_key='fixture',snapshot_vintage_date='2026-10-01',methodological_breaks='fixture')


def native(sid,dates,values,freq='M',public=True,pit=False,pubs=None):
    out=[]
    for i,(date,value) in enumerate(zip(dates,values)):
        p=pd.Period(date,freq='D' if freq in ['W','D'] else freq)
        pub=pubs[i] if pubs else ''
        out.append(dict(series_id=sid,observation_date=str(p.start_time.date()),period_end=str(p.end_time.date()),
            native_frequency=freq,value=value,original_publication_date=pub,historical_vintage_date=pub,
            point_in_time_eligible=pit,source_key='fixture',source_sha256='0'*64,snapshot_vintage_date='2026-10-01',
            retrieved_at='2026-10-28T12:00:00+00:00',redistribution_permitted=public))
    return pd.DataFrame(out)


class FinancialMathTests(unittest.TestCase):
    def test_compound_and_missing_month(self):
        x=pd.Series([10.,-10.,0.,np.nan,20.])
        self.assertAlmostEqual(compound(x,3).iloc[2],-1.)
        self.assertTrue(compound(x,3).iloc[4:].isna().all())

    def test_inflation_uses_observed_endpoints_without_filling(self):
        x=pd.Series([100.,np.nan,121.])
        self.assertAlmostEqual(period_growth(x,2).iloc[2],21.)
        self.assertTrue(pd.isna(period_growth(x,1).iloc[2]))
        self.assertAlmostEqual(period_growth(pd.Series([100.,110.,121.]),2).iloc[2],21.)

    def test_wealth_missing_path_stays_unknown(self):
        x=pd.Series([np.nan,10.,-10.,np.nan,20.])
        w=wealth(x)
        self.assertAlmostEqual(w.iloc[2],.99)
        self.assertTrue(w.iloc[3:].isna().all())

    def test_drawdown_respects_chronology(self):
        self.assertAlmostEqual(window_mdd(np.array([1.,1.2,.9,1.1])), -25.)
        self.assertEqual(window_mdd(np.array([.8,1.,1.2])),0.)

    def test_bear_hysteresis_and_no_backdating(self):
        w=pd.Series([1.,.9,.79,.7,.82,.85,1.])
        self.assertEqual(online_regime(w).tolist(),[0.,0.,1.,1.,1.,0.,0.])
        pd.testing.assert_series_equal(online_regime(w).iloc[:4],online_regime(w.iloc[:4]))

    def test_formula_and_permission_dependency(self):
        idx=pd.period_range('1956-01',periods=30,freq='M')
        raw=pd.DataFrame({'US_TREASURY_10Y':5.,'US_TBILL_3M_DISCOUNT':2.,'US_CORPORATE_BAA':7.,'US_CORPORATE_AAA':6.,
                          'US_CPI_SA':100*1.01**np.arange(30),'US_UNEMPLOYMENT':4.},index=idx)
        specs={s:spec(public='CORPORATE' not in s) for s in raw}
        d,meta=derive(raw,pd.DataFrame(),specs)
        self.assertEqual(d.US_SLOPE_10Y_TBILL_DISCOUNT.iloc[-1],3.)
        self.assertAlmostEqual(d.US_CPI_INFLATION_YOY.iloc[-1],100*(1.01**12-1))
        self.assertAlmostEqual(d.US_MISERY_INDEX.iloc[-1],4+100*(1.01**12-1))
        self.assertFalse(meta.set_index('series_id').loc['US_BAA_AAA_SPREAD','redistribution_permitted'])

    def test_market_trailing_features_are_prefix_invariant(self):
        idx=pd.period_range('1926-07',periods=160,freq='M')
        raw=pd.DataFrame({'FF_MKT_EXCESS':np.sin(np.arange(160))*4,'FF_RF':.2},index=idx)
        specs={s:spec(public=False) for s in raw}
        empty=pd.DataFrame(columns=['series_id','observation_date','value'])
        full,_=derive(raw,empty,specs);prefix,_=derive(raw.iloc[:100],empty,specs)
        pd.testing.assert_frame_equal(full.iloc[:100],prefix)
        self.assertTrue((full.US_MARKET_DRAWDOWN.dropna()<=0).all())
        self.assertEqual(full.US_MARKET_MAX_DRAWDOWN_12M.first_valid_index(),idx[12])

    def test_past_only_standardization_excludes_current(self):
        idx=pd.period_range('1950-01',periods=62,freq='M')
        x=np.arange(62,dtype=float);x[-1]=10000
        raw=pd.DataFrame({'US_EXCESS_BOND_PREMIUM':x},index=idx)
        d,_=derive(raw,pd.DataFrame(),{'US_EXCESS_BOND_PREMIUM':spec()})
        expected=(x[-1]-np.mean(x[:-1]))/np.std(x[:-1],ddof=1)
        self.assertAlmostEqual(d.iloc[-1,0],expected)
        self.assertTrue(d.iloc[:60,0].isna().all())

    def test_longest_gap_includes_leading_and_trailing(self):
        self.assertEqual(longest_gap([True,True,False,True,True,True]),3)
        self.assertTrue(pd.isna(number('-99.99')))
        with self.assertRaises(ValueError):number('broken')
        with self.assertRaises(ValueError):number('inf')


class FinancialAlignmentTests(unittest.TestCase):
    def test_weekly_partial_month_not_promoted_to_complete(self):
        n=native('US_INITIAL_CLAIMS',['1958-01-04','1958-01-11','1958-01-18'],[100,200,300],freq='W')
        frame,meta,_=monthly_native(n,{'US_INITIAL_CLAIMS':spec('W')})
        self.assertTrue(pd.isna(frame.loc['1958-01','US_INITIAL_CLAIMS']))
        self.assertEqual(meta.expected_source_rows.iloc[0],4)
        n=pd.concat([n,native('US_INITIAL_CLAIMS',['1958-01-25'],[400],freq='W')],ignore_index=True)
        frame,_,_=monthly_native(n,{'US_INITIAL_CLAIMS':spec('W')})
        self.assertEqual(frame.loc['1958-01','US_INITIAL_CLAIMS'],250)

    def test_quarterly_not_in_monthly_and_no_future_carry(self):
        n=native('GDP',['1957Q4','1958Q1','1958Q2'],[90,100,120],freq='Q')
        frame,_,q=monthly_native(n,{'GDP':spec('Q')})
        self.assertNotIn('GDP',frame)
        q=q.set_index('month')
        self.assertEqual(q.loc['1958-01','latest_completed_quarter_value'],90)
        self.assertTrue(pd.isna(q.loc['1958-01','quarter_end_value']))
        self.assertEqual(q.loc['1958-03','quarter_end_value'],100)
        self.assertEqual(q.loc['1958-04','reference_quarter'],'1958Q1')
        self.assertTrue(pd.isna(q.loc['1958-09','latest_completed_quarter_value']))

    def test_pit_gate_uses_historical_vintage_and_publication(self):
        n=native('INIT',['1958-01','1958-02'],[.5,.8],pit=True,pubs=['1958-02-15','1958-03-01'])
        rows=point_in_time(n).set_index('month')
        self.assertNotIn('1958-01',rows.index)
        self.assertEqual(rows.loc['1958-02','value'],.5)
        self.assertEqual(rows.loc['1958-03','value'],.8)
        n['point_in_time_eligible']=False
        self.assertTrue(point_in_time(n).empty)

    def test_pit_does_not_use_later_vintage(self):
        n=native('INIT',['1958-01'],[.5],pit=True,pubs=['1958-02-15'])
        n['historical_vintage_date']='1958-04-01'
        p=point_in_time(n)
        self.assertEqual(p.month.min(),'1958-04')

    def test_duplicate_and_bad_periods_fail(self):
        n=native('CPI',['1958-01'],[100])
        with self.assertRaises(ValueError):strict_native(pd.concat([n,n]))
        n.loc[0,'period_end']='1958-01-30'
        with self.assertRaises(ValueError):strict_native(n)

    def test_news_day_coverage_remains_explicit(self):
        n=native('US_ECONOMIC_NEWS_SENTIMENT',['1958-01-01','1958-01-03'],[1,3],freq='D')
        p,a,_=monthly_native(n,{'US_ECONOMIC_NEWS_SENTIMENT':spec('D')})
        self.assertEqual(p.loc['1958-01','US_ECONOMIC_NEWS_SENTIMENT'],2)
        self.assertEqual(a.valid_source_rows.iloc[0],2)
        self.assertEqual(a.expected_source_rows.iloc[0],31)
        self.assertFalse(a.calendar_complete.iloc[0])

    def test_invalid_release_calendar_does_not_guess(self):
        with self.assertRaises(ValueError):release_calendar('January 1958 15-Jan-1958 January 1958 16-Jan-1958')



class FinancialSourceTests(unittest.TestCase):
    def test_export_preserves_float64_round_trip_precision(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'native.csv.xz'
            values=[.12345678901234566,123456.78901234567,-.00012345678901234566]
            write_csv(path,pd.DataFrame({'value':values}))
            restored=pd.read_csv(path,float_precision='round_trip')
            self.assertEqual(restored.value.tolist(),values)

    def test_native_public_does_not_contain_restricted_values(self):
        root=Path(__file__).resolve().parents[1]
        path=root/'data/external_historical/financial/processed/acquisition_v1/native_public.csv.xz'
        if not path.exists():self.skipTest('Published native panel not available')
        data=pd.read_csv(path)
        self.assertTrue(data.redistribution_permitted.map(boolean).all())
        self.assertFalse(data.series_id.str.startswith('FF_').any())
        self.assertFalse(data.series_id.isin(['US_CORPORATE_AAA','US_CORPORATE_BAA','US_CONSUMER_SENTIMENT']).any())
        strict_native(data.fillna({'historical_vintage_date':''}))

    def test_source_hash_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source';path.write_bytes(b'original')
            catalog={'test':{'status':'ok','raw_path':str(path),'sha256':sha(path)}}
            with patch('financial_acquisition_common.snapshots',return_value=catalog):
                self.assertEqual(source_path('test'),path)
                path.write_bytes(b'changed')
                with self.assertRaises(ValueError):source_path('test')

    def test_normalization_failures_do_not_publish_partial_native(self):
        names=['parse_bls','parse_h15','parse_bea','parse_french','parse_g17','parse_michigan','parse_fed_quarterly','parse_research','parse_pink','parse_claims','parse_nfci','parse_nber']
        from contextlib import ExitStack
        with ExitStack() as stack:
            for name in names:
                mocked=stack.enter_context(patch.object(sources,name,side_effect=ValueError('schema changed')));mocked.__name__=name
            write=stack.enter_context(patch.object(sources,'write_csv'))
            stack.enter_context(patch.object(sources,'write_json'))
            with self.assertRaisesRegex(ValueError,'published native datasets preserved'):sources.normalize()
            write.assert_not_called()

    def test_michigan_empty_trailing_csv_field_is_preserved_as_schema(self):
        class Capture:
            def __init__(self):self.rows=[]
            def register(self,*args,**kwargs):pass
            def add(self,*args,**kwargs):self.rows.append(args)
        with tempfile.TemporaryDirectory() as directory:
            paths={}
            for key,period in [('umich_monthly_1','Month'),('umich_Q_1','Quarter')]:
                path=Path(directory)/key;path.write_text('Table 1: The Index of Consumer Sentiment\n'+period+',Year,Index,\n1,1978,83.7,\n');paths[key]=path
            with patch.object(sources,'source_path',side_effect=lambda key:paths[key]):
                c=Capture();sources.parse_michigan(c)
                self.assertEqual(len(c.rows),2)
                self.assertEqual(c.rows[0][1],'1978-01')
                self.assertEqual(c.rows[1][1],'1978Q1')


if __name__=='__main__':unittest.main()
