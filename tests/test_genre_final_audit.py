import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genre_final_audit import accepted_rows, validate_review
from genre_production_audit import review_sample


class FinalGenreAuditTests(unittest.TestCase):
    def test_foreign_and_duplicate_ids_never_support_provenance(self):
        row=dict(song_id='a', primary_genre='Pop', secondary_genres=[], confidence='high', reason='Clear pop.')
        foreign=dict(row, song_id='foreign')
        self.assertEqual(accepted_rows({'predictions':[row,foreign]}, ['a','b']), [row])
        self.assertEqual(accepted_rows({'predictions':[row,row]}, ['a']), [])

    def test_bad_schema_does_not_support_provenance(self):
        row=dict(song_id='a', primary_genre='Invented', secondary_genres=[], confidence='high', reason='Invalid.')
        self.assertEqual(accepted_rows({'predictions':[row]}, ['a']), [])
        self.assertEqual(accepted_rows({'unexpected':[]}, ['a']), [])

    def fixture(self):
        rows=[dict(song_id=str(i), title=str(i), artist='Artist', primary_genre='Pop', confidence='high', period='1980s') for i in range(200)]
        review=[dict(r, judgment='plausible', review_note='Authored review.') for r in review_sample(rows)]
        return rows,review

    def test_review_rejects_changed_labels_and_missing_judgments(self):
        rows,review=self.fixture()
        self.assertEqual(validate_review(rows,review), {'plausible':160})
        changed=copy.deepcopy(review);changed[0]['primary_genre']='Rock'
        with self.assertRaises(ValueError):validate_review(rows,changed)
        changed=copy.deepcopy(review);changed[0]['review_note']=''
        with self.assertRaises(ValueError):validate_review(rows,changed)

    def test_review_rejects_substitution_and_duplicates(self):
        rows,review=self.fixture()
        changed=copy.deepcopy(review);changed[-1]=changed[0]
        with self.assertRaises(ValueError):validate_review(rows,changed)
        with self.assertRaises(ValueError):validate_review(rows,review[:-1])
