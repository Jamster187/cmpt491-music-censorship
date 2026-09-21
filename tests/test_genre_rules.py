"""Genre evidence must not turn vague tags, collaborations or duplicates into certainty."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from genre_rules import TAXONOMY,mapping,assign


def row(label,level='recording',provider='MusicBrainz',**kwargs):
    return dict(label=label,level=level,provider=provider,votes=1,raw='{}',**kwargs)


class GenreRulesTests(unittest.TestCase):
    def test_frozen_categories(self):
        self.assertEqual(len(TAXONOMY),16);self.assertEqual(TAXONOMY[-1],'Other')
        self.assertNotIn('Unknown',TAXONOMY)

    def test_exact_matching_only(self):
        self.assertEqual(mapping(' HIP HOP '),['Hip-Hop / Rap'])
        for label in ('not rock','rocking horse','hip hop fan','country of birth','party','ballad','unknown','soundtrack','world music'):
            self.assertEqual(mapping(label),[])

    def test_fusion_preserved(self):
        d=assign([row('country pop')])
        self.assertIsNone(d['primary_genre']);self.assertTrue(d['genre_ambiguous'])
        self.assertEqual(set(d['primary_candidates']),{'Country','Pop'})

    def test_missing_is_not_other(self):
        self.assertEqual(assign([row('favorite')])['disposition'],'insufficient_evidence')
        self.assertIsNone(assign([])['primary_genre'])
        self.assertEqual(assign([row('classical')])['primary_genre'],'Other')

    def test_artist_is_not_definitive_song_evidence(self):
        r=assign([row('country','artist')])
        self.assertIsNone(r['primary_genre']);self.assertEqual(r['disposition'],'context_only')
        self.assertEqual(r['primary_candidates'],['Country'])

    def test_weaker_evidence_cannot_resolve_direct_conflict(self):
        r=assign([row('pop'),row('soul'),row('pop','artist')])
        self.assertIsNone(r['primary_genre']);self.assertEqual(r['disposition'],'ambiguous')
        r=assign([row('rock'),row('country','artist')])
        self.assertEqual(r['primary_genre'],'Rock');self.assertIn('Country',r['mapped_genres'])

    def test_generic_rock_parent_but_not_crossgenre_suppressed(self):
        self.assertEqual(assign([row('rock'),row('heavy metal')])['primary_genre'],'Metal')
        self.assertEqual(assign([row('rock'),row('indie rock')])['primary_genre'],'Alternative / Indie')
        self.assertIsNone(assign([row('pop rock'),row('heavy metal')])['primary_genre'])

    def test_no_country_or_language_inference(self):
        self.assertEqual(mapping('nigerian'),[]);self.assertEqual(mapping('korean'),[])
        self.assertEqual(mapping('latin pop'),['Latin']);self.assertEqual(mapping('k-pop'),['K-Pop'])

    def test_qualified_and_deprecated_wikidata_not_unqualified_evidence(self):
        for raw in ({'rank':'deprecated'},{'qualifiers':{'P580':[]}}):
            r=row('rock',provider='Wikidata');r['raw']=json.dumps(raw)
            self.assertEqual(assign([r])['disposition'],'insufficient_evidence')

    def test_no_compilation_inheritance(self):
        self.assertIsNone(assign([row('rock','release-group')])['primary_genre'])
        self.assertEqual(assign([row('rock','release-group',single_release_context=True)])['disposition'],'release_supported')

    def test_duplicates_do_not_outvote_other_genre(self):
        r=assign([row('pop')]*20+[row('soul')])
        self.assertIsNone(r['primary_genre']);self.assertEqual(len(r['primary_candidates']),2)

    def test_nonpositive_votes_ignored(self):
        r=row('rock');r['votes']=0
        self.assertEqual(assign([r])['disposition'],'insufficient_evidence')

if __name__=='__main__':unittest.main()
