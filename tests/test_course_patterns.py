"""Independent brute-force oracle, exact closure, and leakage-sensitive bins."""
import itertools
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import course_patterns as p
import course_common as c


class PatternTests(unittest.TestCase):
    def oracle(self,tx,minimum,k):
        items=sorted(set().union(*map(set,tx)));out={}
        for size in range(1,k+1):
            for candidate in itertools.combinations(items,size):
                if not p.compatible(candidate):continue
                n=sum(set(candidate)<=set(row) for row in tx)
                if n>=minimum:out[candidate]=n
        return out

    def test_three_independent_algorithms_equal_brute_force(self):
        rng=np.random.default_rng(491)
        for seed in range(8):
            tx=[[f"v{j}={int(rng.integers(0,3))}" for j in range(5) if rng.random()<.8] for _ in range(25)]
            tx += [tx[0],[]]
            for minimum in (1,4,12):
                expected=self.oracle(tx,minimum,4)
                for method in (p.apriori,p.fpgrowth,p.eclat):self.assertEqual(method(tx,minimum,4),expected)

    def test_closed_maximal_check_extensions_beyond_cap(self):
        tx=[[f"v{i}=yes" for i in range(5)]]*4+[["v0=yes"]]
        result=p.closed_maximal(p.eclat(tx,3,4),tx,3)
        self.assertFalse(any(r["maximal"] for r in result))
        self.assertFalse(any(r["closed"] for r in result if r["size"]==4))
        self.assertTrue(next(r for r in result if r["items"]==["v0=yes"])["closed"])

    def test_bin_boundaries_and_missing_values(self):
        frame=pd.DataFrame(dict(x=[0.,1.,2.,3.,np.nan],primary_genre=["Pop"]*5,decade=["2000s"]*5,best_chart_rank=[1]*5,chart_weeks=[10]*5))
        tx=p.transactions(frame,{"x":[1.,2.]},10)
        self.assertIn("x=low",tx[1]);self.assertNotIn("x=high",tx[2]);self.assertIn("x=high",tx[3])
        self.assertFalse(any(i.startswith("x=") for i in tx[4]));self.assertIn("long_chart=no",tx[0])

    def test_transaction_hash_is_invariant_to_schema_key_order(self):
        frame=pd.DataFrame(dict(x=[0.,3.],z=[3.,0.],primary_genre=["Pop"]*2,decade=["2000s"]*2,best_chart_rank=[1]*2,chart_weeks=[10]*2))
        first=p.transactions(frame,{"x":[1.,2.],"z":[1.,2.]},10)
        second=p.transactions(frame,{"z":[1.,2.],"x":[1.,2.]},10)
        self.assertEqual(first,second);self.assertEqual(c.digest(first),c.digest(second))

    def test_cmh_null_and_association(self):
        masks=[(1<<100)-1]
        a=p.bitmask(np.arange(100)<50);b=p.bitmask(np.arange(100)%2==0)
        self.assertAlmostEqual(p.cmh_p(a,b,masks),1.)
        self.assertLess(p.cmh_p(a,a,masks),1e-20)

    def test_negative_numerical_items_exclude_missing_values(self):
        frame=pd.DataFrame({"x":[0.,1.,np.nan,2.]})
        b,universe=p.outcome_bits("x=high",True,{"x=high":8},15,frame)
        self.assertEqual(universe,11);self.assertEqual(b,3)
        self.assertEqual(p.rule_metrics(universe,b,p.count(universe))["baseline"],2/3)

    def test_incidental_chart_condition_does_not_make_lyric_reconstruction_cross_domain(self):
        result=p.category(["emotion_grief=high","top10=no"],"emotion_sadness=high")
        self.assertTrue(result["cross_domain"]);self.assertFalse(result["strict_cross_domain"])
        self.assertTrue(p.category(["emotion_grief=high","emotion_sadness=high"],"top10=yes")["strict_cross_domain"])

    def test_whole_history_purging(self):
        f=pd.DataFrame(dict(song_id=list("abcd"),first_chart_date=["2000-01-01","2009-01-01","2010-01-01","2017-01-01"],last_chart_date=["2001-01-01","2011-01-01","2011-01-01","2018-01-01"]))
        tr,te=c.partitions(f)
        self.assertEqual(tr.song_id.tolist(),["a"]);self.assertEqual(te.song_id.tolist(),["c"])


if __name__=="__main__":unittest.main()
