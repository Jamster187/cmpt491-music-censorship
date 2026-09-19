"""Synthetic text only: independent identity/quality and reversible cleaning safeguards."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import lyrics_lrclib_r as r


def fixture():
    candidate={'id':7,'trackName':'Synthetic Song','artistName':'Synthetic Artist',
               'plainLyrics':'Fictional words remain exactly as supplied for this software test.','instrumental':False}
    row={'song_id':'fixture','status':'ambiguous','title':'Synthetic Song','artist':'Synthetic Artist',
         'first_chart_date':'2000-01-01','reason':'Fixture conflict','raw_candidates':[candidate],
         'retrievals':[],'metadata':{'durations':[],'albums':[]}}
    item={'song_id':'fixture','billboard_title':row['title'],'billboard_artist':row['artist'],
          'candidate_id':7,'candidate_sha256':r.digest(json.dumps(candidate,ensure_ascii=False,sort_keys=True).encode()),
          'identity_confidence':'identity_high_confidence','text_quality':'text_good','outcome':'recoverable'}
    return row,{'version':r.VERSION,'reviews':[item]}


class LRCLIBReviewTests(unittest.TestCase):
    def test_identity_and_quality_are_independent(self):
        self.assertEqual(r.disposition('identity_wrong','text_good'),'wrong_identity')
        self.assertEqual(r.disposition('identity_ambiguous','text_good'),'identity_ambiguous')
        self.assertEqual(r.disposition('identity_high_confidence','text_missing'),'missing_text')
        self.assertEqual(r.disposition('identity_high_confidence','text_bad'),'bad_text')
        self.assertEqual(r.disposition('identity_high_confidence','text_usable_with_minor_noise'),'recoverable')
        with self.assertRaises(ValueError):r.disposition('probably','text_good')

    def test_header_requires_all_three_structural_lines(self):
        text='Synthetic Song\nSynthetic Artist\n(words & music by Fictional Writer)\nActual fixture words\n'
        self.assertEqual(r.clean(text,'Synthetic Song','Synthetic Artist'),('Actual fixture words\n',['explicit_title_artist_writer_header']))
        # A repeated title or name in the song body must never be removed as metadata.
        content='Synthetic Song\nSynthetic Artist\nActual fixture words\n'
        self.assertEqual(r.clean(content,'Synthetic Song','Synthetic Artist')[0],content)
        self.assertEqual(r.clean(text,'Different Title','Synthetic Artist')[0],text)

    def test_only_narrow_standalone_section_labels_removed(self):
        text='[Chorus]\nActual fixture words\n[Verse 2]\nMore fictional words\n[Artist speaking]\n(Repeat 2x)\n'
        expected='Actual fixture words\nMore fictional words\n[Artist speaking]\n(Repeat 2x)\n'
        self.assertEqual(r.clean(text,'Title','Artist')[0],expected)
        self.assertEqual(r.clean('I sing [Chorus] aloud\n','Title','Artist')[0],'I sing [Chorus] aloud\n')

    def test_no_lexical_repair_uncensoring_or_repeat_expansion(self):
        text='Cafe\u0301\r\nF**k and g- remain supplied\r\nBroken âs stays unchanged\r\n(Repeat chorus 4x)\r\n'
        cleaned,_=r.clean(text,'Title','Artist')
        self.assertEqual(cleaned,'Café\nF**k and g- remain supplied\nBroken âs stays unchanged\n(Repeat chorus 4x)\n')
        self.assertEqual(r.clean(cleaned,'Title','Artist')[0],cleaned)

    def test_case_reconciliation_binds_identity_and_raw_candidate(self):
        row,ledger=fixture()
        out=r.reconcile([row],ledger)
        self.assertEqual(out[0]['outcome'],'recoverable')
        self.assertEqual(out[0]['source_text_sha256'],r.digest(row['raw_candidates'][0]['plainLyrics'].encode()))
        changed=copy.deepcopy(row);changed['raw_candidates'][0]['plainLyrics']='Changed source'
        with self.assertRaisesRegex(ValueError,'revision'):r.reconcile([changed],ledger)
        changed=copy.deepcopy(ledger);changed['reviews'][0]['billboard_artist']='Different Artist'
        with self.assertRaisesRegex(ValueError,'identity'):r.reconcile([row],changed)

    def test_missing_extra_and_duplicate_reviews_fail(self):
        row,ledger=fixture()
        for reviews in [[],ledger['reviews']*2,[dict(ledger['reviews'][0],song_id='other')]]:
            with self.assertRaises(ValueError):r.reconcile([row],dict(ledger,reviews=reviews))

    def test_bad_status_cannot_be_promoted_by_outcome_string(self):
        row,ledger=fixture();ledger['reviews'][0]['identity_confidence']='identity_wrong'
        with self.assertRaisesRegex(ValueError,'Outcome'):r.reconcile([row],ledger)

    def test_missing_and_instrumental_cannot_be_recovered(self):
        for content,instrumental in [('',False),('Synthetic words',True)]:
            row,ledger=fixture();c=row['raw_candidates'][0];c['plainLyrics']=content;c['instrumental']=instrumental
            ledger['reviews'][0]['candidate_sha256']=r.digest(json.dumps(c,ensure_ascii=False,sort_keys=True).encode())
            with self.assertRaisesRegex(ValueError,'Empty/instrumental'):r.reconcile([row],ledger)


if __name__=='__main__':unittest.main()
