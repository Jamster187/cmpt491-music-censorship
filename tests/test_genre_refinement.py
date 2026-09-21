import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from genre_refinement import review_set,audit_ambiguity
from genre_refined_rules import assign
from test_genre_refined_rules import row

class GenreRefinementTests(unittest.TestCase):
    def test_review_size_and_order_invariance(self):
        rows=[dict(song_id=f'{p}-{i}',period=str(p),sample_role='stratified_hash',primary_genre='Country',old_disposition='ambiguous') for p in range(7) for i in range(15)]
        a=review_set(rows);self.assertEqual(len(a),60)
        self.assertEqual(a,review_set(list(reversed(rows))))
    def test_dominant_crossgenre_is_not_called_fake_ambiguity(self):
        evidence=[row('country',8),row('country pop',4)]
        old=dict(song_id='a',title='a',artist='b',primary_candidates='["Country","Pop"]')
        audit=audit_ambiguity(old,evidence,assign(evidence))
        self.assertEqual(audit['primary_reason'],'cross_genre_strong_evidence')
        self.assertEqual(audit['new_primary'],'Country')

if __name__=='__main__':unittest.main()
