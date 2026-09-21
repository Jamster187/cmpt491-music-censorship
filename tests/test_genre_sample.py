import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from genre_sample import select,complex_credit
from genre_evidence import PERIODS

class GenreSampleTests(unittest.TestCase):
    def test_reordering_does_not_change_sample(self):
        songs=[dict(song_id=f'{p}:{i}',title=f'fixture {i}',artist='A & B' if i%2 else 'A',first_chart_date=str(lo)+'-01-01',best_rank=10 if i%4<2 else 90,weekly_rows=i+1,period=p) for lo,_,p in PERIODS for i in range(100)]
        a,_=select(songs);b,_=select(list(reversed(songs)))
        self.assertEqual(a,b);self.assertEqual(len(a),300)
        self.assertEqual(len({s['song_id'] for s in a}),300)
        self.assertEqual([sum(s['period']==p for s in a) for _,_,p in PERIODS],[43]*6+[42])
    def test_credit_proxy(self):
        self.assertTrue(complex_credit('A Featuring B'))
        self.assertFalse(complex_credit('The Beatles'))

if __name__=='__main__':unittest.main()
