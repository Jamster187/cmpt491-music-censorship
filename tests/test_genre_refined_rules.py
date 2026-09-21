import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from genre_refined_rules import assign,support,tag_family

def row(label,votes=1,level='recording',provider='MusicBrainz',eid='r'):
    return dict(label=label,votes=votes,level=level,provider=provider,entity_id=eid,raw='{}')

class RefinedGenreTests(unittest.TestCase):
    def test_compatible_subgenres_collective_support(self):
        d=assign([row('contemporary r&b',2),row('neo soul',2)])
        self.assertEqual(d['primary_genre'],'R&B / Soul');self.assertEqual(d['genre_support_count'],2)
    def test_three_compatible_families_with_some_vote_support(self):
        d=assign([row('gospel',2),row('christian',1),row('contemporary gospel',1)])
        self.assertEqual(d['primary_genre'],'Gospel / Christian')
    def test_spelling_and_synonyms_not_independent(self):
        d=assign([row('hip hop',2),row('hip-hop',2),row('rap',2)])
        self.assertEqual(d['disposition'],'insufficient')
        self.assertEqual(d['support']['direct_song']['Hip-Hop / Rap']['supporting_tag_count'],1)
    def test_repeated_editions_and_cache_rows_do_not_add_votes(self):
        a=[row('country',2)];b=a*20+[row('country',2,eid='another')]
        self.assertEqual(assign(a)['disposition'],assign(b)['disposition'])
        self.assertEqual(support(b)['Country']['max_tag_votes'],2)
    def test_strong_category_ignores_isolated_noise(self):
        self.assertEqual(assign([row('soul',9),row('ambient',1),row('rock',1)])['primary_genre'],'R&B / Soul')
    def test_generic_pop_is_not_veto(self):
        d=assign([row('pop',20),row('country',4),row('pop rock',1)])
        self.assertEqual(d['primary_genre'],'Country');self.assertIn('Pop',d['mapped_genres'])
    def test_specific_pop_remains_contender(self):
        self.assertEqual(assign([row('dance-pop',4),row('house',4)])['disposition'],'ambiguous')
    def test_similarly_strong_cross_genre_abstains(self):
        self.assertIsNone(assign([row('hip hop',4),row('soul',5)])['primary_genre'])
    def test_dominance_preserves_secondary(self):
        d=assign([row('country',8),row('country pop',4)])
        self.assertEqual(d['primary_genre'],'Country');self.assertIn('Pop',d['secondary_genres'])
    def test_weak_cluster_not_automatically_reliable(self):
        self.assertEqual(assign([row('house'),row('deep house'),row('garage house')])['disposition'],'insufficient')
    def test_artist_or_album_does_not_make_primary(self):
        for level in ('artist','release','release-group','album'):
            self.assertIsNone(assign([row('country',20,level)])['primary_genre'])
    def test_context_cannot_break_direct_tie(self):
        self.assertEqual(assign([row('hip hop',4),row('soul',4),row('hip hop',20,'artist')])['disposition'],'ambiguous')
    def test_rock_parent_but_not_hard_rock(self):
        self.assertEqual(assign([row('rock',10),row('heavy metal',3)])['primary_genre'],'Metal')
        self.assertEqual(assign([row('hard rock',3),row('heavy metal',3)])['disposition'],'ambiguous')
    def test_other_requires_evidence(self):
        self.assertEqual(assign([row('comedy')])['disposition'],'insufficient')
        self.assertEqual(assign([row('comedy',3)])['disposition'],'Other')
    def test_provider_agreement_is_counted_not_probability(self):
        d=assign([row('country'),row('country',level='song_item',provider='Wikidata')])
        self.assertEqual(d['primary_genre'],'Country')
        self.assertEqual(d['support']['direct_song']['Country']['supporting_provider_count'],2)
    def test_order_invariant(self):
        a=[row('country',8),row('country pop',4),row('rock',1)]
        self.assertEqual(assign(a),assign(list(reversed(a))))
    def test_additional_spellings_collapse(self):
        self.assertEqual(tag_family('southern rap'),tag_family('southern hip hop'))
        self.assertEqual(tag_family('synthpop'),tag_family('synth-pop'))
        self.assertEqual(tag_family('EDM'),tag_family('electronic dance music'))
        self.assertEqual(tag_family('house'),tag_family('house music'))
        self.assertEqual(tag_family('trap'),tag_family('trap music'))

if __name__=='__main__':unittest.main()
