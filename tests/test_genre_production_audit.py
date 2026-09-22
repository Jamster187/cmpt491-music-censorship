import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from genre_production_audit import review_sample
from genre_rules import TAXONOMY

class ProductionAuditTests(unittest.TestCase):
    def test_review_is_bounded_deterministic_and_covers_strata(self):
        rows=[dict(song_id=str(i),primary_genre=TAXONOMY[i%16],confidence=('high','medium','low')[i%3],period=str(i%7)) for i in range(1000)]
        selected=review_sample(rows)
        self.assertEqual(selected,review_sample(list(reversed(rows))))
        self.assertEqual(len(selected),160)
        self.assertEqual(len({r['song_id'] for r in selected}),160)
        self.assertEqual({r['primary_genre'] for r in selected},set(TAXONOMY))
        self.assertEqual({r['confidence'] for r in selected},{'high','medium','low'})
        self.assertEqual({r['period'] for r in selected},{str(i) for i in range(7)})

    def test_small_population_never_duplicates_rows(self):
        rows=[dict(song_id='a',primary_genre='Pop',confidence='high',period='1958–1969')]
        self.assertEqual(review_sample(rows),rows)
