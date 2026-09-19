"""Synthetic fixtures for production acceptance, review quarantine and crash recovery."""
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import lyrics_lrclib as legacy
import lyrics_production as production
import lyrics_production_match as m

TEXT='\n'.join(' '.join('fictional%d'%i for i in range(n,n+10)) for n in range(0,100,10))+'\n'


def song(**kw):
    return dict(song_id='fixture',title='Synthetic Song',artist='Example Featuring Guest',first_chart_date='2020-01-01',metadata={'durations':[],'albums':[]},**kw)


def candidate(**kw):
    c=dict(id=1,trackName='Synthetic Song',artistName='Example & Guest',albumName='Studio Album',duration=240,plainLyrics=TEXT,syncedLyrics=None,instrumental=False)
    c.update(kw);return c


class ProductionMatchingTests(unittest.TestCase):
    def test_accept_without_metadata_and_full_guest_required(self):
        self.assertEqual(m.decide(song(),[candidate()])['status'],'accepted')
        self.assertEqual(m.decide(song(),[candidate(artistName='Example')])['status'],'quarantined')
        self.assertEqual(m.decide(song(),[candidate(artistName='Unrelated Person')])['status'],'wrong_identity')
        self.assertNotEqual(m.decide(song(),[candidate(trackName='Other Song')])['status'],'accepted')

    def test_feature_relocation_and_provider_nul_separators(self):
        for c in [candidate(artistName='Example\x00Guest'),candidate(artistName='Example',trackName='Synthetic Song (feat. Guest)')]:
            self.assertEqual(m.decide(song(),[c])['status'],'accepted')
        self.assertEqual(m.artist_credit('Beyoncé & Guest'),m.artist_credit('Beyonce feat. Guest'))
        self.assertNotEqual(m.artist_credit('First Last'),m.artist_credit('Last First'))

    def test_small_transcription_variation_not_generic_ambiguity(self):
        c=candidate(id=2,plainLyrics=TEXT.replace('fictional42','alternate42'))
        d=m.decide(song(),[candidate(),c]);self.assertEqual(d['status'],'accepted')
        self.assertIn('minor_transcription_variation',d['text_warnings'])
        self.assertTrue(m.compatible('do not go',"don't go")[0] is False)  # not a license to rewrite words

    def test_new_verse_and_different_text_require_review(self):
        c=candidate(id=2,plainLyrics=TEXT+'\n'+' '.join('additional%d'%i for i in range(30)))
        self.assertEqual(m.decide(song(),[candidate(),c])['status'],'quarantined')
        self.assertFalse(m.compatible(TEXT,TEXT.replace('fictional','different'))[0])
        long=TEXT*30
        self.assertFalse(m.compatible(long,long+' '+' '.join('new%d'%i for i in range(35)))[0])

    def test_remixes_plural_and_live_do_not_supply_studio_text(self):
        for album in ('Remixes','Live Album','Acoustic Sessions','Karaoke'):
            d=m.decide(song(),[candidate(albumName=album)])
            self.assertEqual(d['status'],'quarantined')
        d=m.decide(song(),[candidate(albumName='Remixes'),candidate(id=2)])
        self.assertEqual(d['selected'],2);self.assertIn('remix',d['version_warnings'])

    def test_clean_is_a_title_not_a_censorship_label(self):
        s=song();s['title']='Clean'
        d=m.decide(s,[candidate(trackName='Clean')]);self.assertEqual(d['status'],'accepted')
        self.assertNotIn('clean',d['version_warnings'])

    def test_material_masking_never_uncensored_and_clean_label_warns(self):
        masked=TEXT.replace('fictional1','f**k').replace('fictional2','s**t')
        self.assertEqual(m.decide(song(),[candidate(plainLyrics=masked)])['status'],'quarantined')
        d=m.decide(song(),[candidate(plainLyrics=masked),candidate(id=2,albumName='Clean Album')])
        self.assertEqual(d['selected'],2);self.assertIn('clean',d['version_warnings'])
        self.assertIn('material_censorship',d['text_warnings'])
        self.assertIn('f**k',m.quality(candidate(plainLyrics=masked),song())[0])

    def test_text_missing_bad_and_uncertain_separate_from_identity(self):
        for c,status,grade in [(candidate(plainLyrics=''), 'bad_missing_text','text_missing'),
                               (candidate(instrumental=True),'bad_missing_text','text_missing'),
                               (candidate(plainLyrics='<html>'+TEXT),'bad_missing_text','text_bad'),
                               (candidate(plainLyrics=TEXT[:150]),'quarantined','text_usable_with_minor_noise')]:
            d=m.decide(song(),[c]);self.assertEqual(d['status'],status);self.assertEqual(d['text_quality'],grade)
            self.assertEqual(d['identity_confidence'],'identity_high_confidence')

    def test_bad_alternative_does_not_veto_good_candidate(self):
        d=m.decide(song(),[candidate(plainLyrics='download fake lyrics'),candidate(id=2)])
        self.assertEqual(d['status'],'accepted');self.assertEqual(d['selected'],2)

    def test_corruption_thresholds_and_mixed_script(self):
        self.assertEqual(m.quality(candidate(plainLyrics=TEXT+'\n�'*6),song())[1],'text_bad')
        self.assertEqual(m.decide(song(),[candidate(plainLyrics=TEXT.replace('fictional1','fictiоnal1'))])['status'],'quarantined')

    def test_duration_support_selection_and_conflict_quarantine(self):
        s=song();s['metadata']={'durations':[240],'albums':['Preferred']}
        d=m.decide(s,[candidate(id=1,duration=310),candidate(id=2,duration=240,albumName='Preferred')])
        self.assertEqual(d['selected'],2)
        d=m.decide(s,[candidate(duration=310)])
        self.assertEqual(d['status'],'quarantined');self.assertEqual(d['identity_confidence'],'identity_high_confidence')


class ProductionPersistenceTests(unittest.TestCase):
    def test_atomic_file_then_manifest_and_orphan_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data/processed').mkdir(parents=True)
            sqlite3.connect(root/'data/processed/lyrics.db').close();c=production.connect(root)
            c.execute('INSERT INTO production_assets VALUES (?,?)',('fixture',json.dumps(song())));c.commit()
            path=root/'data/lyrics/fixture.txt';legacy.atomic(path,TEXT.encode())  # interrupted file-before-DB write
            before=path.stat().st_mtime_ns;r=dict(song(),status='accepted')
            production.persist(c,r,TEXT,root)
            self.assertEqual(before,path.stat().st_mtime_ns);self.assertEqual(production.validate(c,root),1)
            with self.assertRaises(ValueError):production.persist(c,r,TEXT+'changed',root)
            with self.assertRaises(ValueError):production.persist(c,dict(song(),status='accepted'),None,root)
            c.close()

    def test_errors_incrementally_replace_with_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data/processed').mkdir(parents=True)
            sqlite3.connect(root/'data/processed/lyrics.db').close();c=production.connect(root)
            production.persist(c,dict(song(),status='error'),root=root)
            production.persist(c,dict(song(),status='quarantined'),root=root)
            self.assertEqual(c.execute('select count(*) from production_history').fetchone()[0],1)
            c.close()

    def test_cache_reused_and_fallback_only_for_empty_search(self):
        class Client:
            def __init__(self):self.calls=[]
            def search(self,params):
                self.calls.append(params)
                return dict(status=200,body=json.dumps([] if len(self.calls)==1 else [candidate()]))
        client=Client();result,text=production.acquire(song(),client)
        self.assertEqual(len(client.calls),2);self.assertEqual(result['status'],'accepted');self.assertEqual(text,TEXT)

    def test_503_retry_after_and_identifying_user_agent(self):
        with tempfile.TemporaryDirectory() as temp:
            clock=[100.];calls=[]
            class Response:
                status=200;headers={}
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def read(self):return b'[]'
            def request(req,**kwargs):
                self.assertEqual(req.get_header('User-agent'),production.UA);calls.append(clock[0])
                if len(calls)==1:raise urllib.error.HTTPError('url',503,'busy',{'Retry-After':'7'},io.BytesIO(b'busy'))
                return Response()
            def sleep(n):clock[0]+=n
            with patch('lyrics_lrclib.time.time',side_effect=lambda:clock[0]),patch('lyrics_lrclib.time.sleep',side_effect=sleep),patch('urllib.request.urlopen',side_effect=request):
                client=legacy.Client(Path(temp),user_agent=production.UA);client.search({'track_name':'Synthetic'})
                self.assertGreaterEqual(calls[1]-calls[0],7)
                client.search({'track_name':'Synthetic'});self.assertEqual(len(calls),2)


if __name__=='__main__':unittest.main()
