"""Synthetic fixtures only; never embed real lyrics in tests."""
import json
import io
import urllib.error
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import lyrics_lrclib as l

TEXT='Synthetic fixture words describing a fictional scene for software testing only.\n'

def song(title='Example',artist='Artist'):
    return dict(song_id='synthetic',title=title,artist=artist,metadata={'durations':[],'albums':[]})

def candidate(**kw):
    r=dict(id=1,trackName='Example',artistName='Artist',albumName='Album',duration=200,plainLyrics=TEXT,instrumental=False)
    r.update(kw);return r


class LyricsTests(unittest.TestCase):
    def test_title_artist_and_guest_preservation(self):
        self.assertEqual(l.decide(song(),[candidate()])['status'],'success')
        self.assertEqual(l.decide(song(),[candidate(artistName='Other')])['status'],'ambiguous')
        self.assertEqual(l.decide(song(artist='Artist Featuring Guest'),[candidate()])['status'],'ambiguous')
        self.assertEqual(l.credit('Artist feat. Guest'),l.credit('Guest & Artist'))
        self.assertNotEqual(l.credit('First Last'),l.credit('Last First'))
        self.assertEqual(l.normalize('Dón’t Stop!'),l.normalize("Dont Stop"))

    def test_variants_and_conflicting_text_are_not_silently_selected(self):
        for kw in [dict(trackName='Example (Live)'),dict(albumName='Live'),dict(instrumental=True),dict(plainLyrics='')]:
            self.assertEqual(l.decide(song(),[candidate(**kw)])['status'],'ambiguous')
        a=candidate();b=candidate(id=2,plainLyrics=TEXT+'Additional fictional verse words.')
        self.assertEqual(l.decide(song(),[a,b])['status'],'ambiguous')
        self.assertEqual(l.decide(song(),[a,candidate(id=2)])['selected'],1)

    def test_duration_and_album_aid_selection_without_prerequisite(self):
        s=song();s['metadata']={'durations':[200],'albums':['Preferred']}
        a=candidate(id=1,duration=201,albumName='Other');b=candidate(id=2,duration=200,albumName='Preferred')
        self.assertEqual(l.decide(s,[a,b])['selected'],2)
        self.assertEqual(l.decide(s,[candidate(duration=300)])['status'],'ambiguous')
        self.assertEqual(l.decide(song(),[candidate(duration=300)])['status'],'success')

    def test_empty_search_distinguished_from_errors_and_mismatch(self):
        self.assertEqual(l.decide(song(),[])['status'],'not_found')
        with self.assertRaises(ValueError): l.parse({'status':503,'body':'[]'})
        with self.assertRaises(ValueError): l.parse({'status':200,'body':'{}'})
        with self.assertRaises(ValueError): l.parse({'status':200,'body':'[{"id":1}]'})

    def test_cache_integrity_and_no_redownload(self):
        with tempfile.TemporaryDirectory() as d:
            client=l.Client(Path(d));params={'track_name':'Example'}
            url='https://lrclib.net/api/search?track_name=Example'
            body=json.dumps([candidate()])
            path=client.cache/(l.digest(url.encode())+'.json')
            l.save_json(path,dict(url=url,status=200,body=body,sha256=l.digest(body.encode())))
            with patch('urllib.request.urlopen',side_effect=AssertionError('No HTTP')):
                self.assertEqual(l.parse(client.search(params))[0]['id'],1)
            r=json.loads(path.read_text());r['body']='[]';l.save_json(path,r)
            with self.assertRaises(ValueError):client.search(params)

    def test_retry_after_is_persisted_and_honored(self):
        with tempfile.TemporaryDirectory() as d:
            clock=[100.0]; calls=[]
            class Response:
                status=200; headers={}
                def __enter__(self): return self
                def __exit__(self,*args): pass
                def read(self): return b'[]'
            def request(*args,**kwargs):
                calls.append(clock[0])
                if len(calls)==1:
                    raise urllib.error.HTTPError('url',429,'limited',{'Retry-After':'3'},io.BytesIO(b'limited'))
                return Response()
            def sleep(n): clock[0]+=n
            with patch('lyrics_lrclib.time.time',side_effect=lambda:clock[0]), patch('lyrics_lrclib.time.sleep',side_effect=sleep), patch('urllib.request.urlopen',side_effect=request):
                client=l.Client(Path(d))
                self.assertEqual(client.search({'track_name':'Example'})['status'],200)
                self.assertGreaterEqual(calls[1]-calls[0],3)
                client.search({'track_name':'Example'})
                self.assertEqual(len(calls),2)
                self.assertGreater(json.loads(client.clock.read_text())['until'],clock[0])

    def test_files_persist_and_recover_identical_orphan(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'data/processed').mkdir(parents=True)
            c=l.database(root)
            c.execute("INSERT INTO settings VALUES ('pilot',?)",(json.dumps([song()]),));c.commit()
            r=dict(song(),status='success')
            l.persist(c,r,TEXT,root)
            self.assertEqual(l.validate(c,root),1)
            path=root/r['lyrics_path'];before=path.stat().st_mtime_ns
            l.persist(c,r,TEXT,root)
            self.assertEqual(before,path.stat().st_mtime_ns)
            path.write_text('damaged')
            with self.assertRaises(ValueError):l.validate(c,root)
            with self.assertRaises(ValueError):l.persist(c,r,TEXT,root)
            c.close()

    def test_synced_text_and_malformed(self):
        self.assertEqual(l.lyrics_text(candidate(plainLyrics=None,syncedLyrics='[00:01.00]'+TEXT)),TEXT)
        self.assertIsNone(l.lyrics_text(candidate(plainLyrics='<html>'+TEXT)))



class LyricsReviewImportTests(unittest.TestCase):
    def test_review_quarantine_idempotence_and_checksum_binding(self):
        from lyrics_pilot_report import apply_reviews
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'data/processed').mkdir(parents=True)
            c=l.database(root)
            c.execute("INSERT INTO settings VALUES ('pilot',?)",(json.dumps([song()]),));c.commit()
            r=dict(song(),status='success',matched={'id':1})
            l.persist(c,r,TEXT,root)
            review={'song_id':'synthetic','lrclib_id':1,'lyrics_sha256':r['lyrics_sha256'],'reject':True,'finding':'Synthetic defect'}
            apply_reviews(c,[review],root)
            apply_reviews(c,[review],root)
            self.assertEqual(l.validate(c,root),0)
            self.assertEqual(c.execute('SELECT count(*) FROM review_history').fetchone()[0],1)
            self.assertEqual((root/'data/cache/lrclib/quarantine/synthetic.txt').read_text(),TEXT)
            with self.assertRaises(ValueError):apply_reviews(c,[dict(review,lyrics_sha256='bad')],root)
            c.close()

    def test_import_atomicity_and_idempotence(self):
        import sqlite3
        from research import SCHEMA
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'data/processed').mkdir(parents=True)
            side=l.database(root)
            side.execute("INSERT INTO settings VALUES ('pilot',?)",(json.dumps([song()]),));side.commit()
            r=dict(song(),status='success',matched={'id':1,'trackName':'Example','artistName':'Artist'},retrievals=[{'retrieved_at':'2026-09-19'}],processed_at='2026-09-19',reason='Synthetic agreement')
            l.persist(side,r,TEXT,root);side.close()
            target=sqlite3.connect(root/'data/processed/research.db');target.executescript(SCHEMA)
            target.execute('INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?)',('synthetic','Example','Artist','example','artist','2000-01-01','2000-01-01',1,1,1,100))
            target.execute('INSERT INTO study_population VALUES (?,?,?,?)',('synthetic','2000-01','2000-01',1))
            target.execute('INSERT INTO lyrics_pilot VALUES (?,?,?,?)',('synthetic','2000s',1,'fixture'))
            target.execute('INSERT INTO lyrics_manifest(song_id) VALUES (?)',('synthetic',));target.commit()
            # Defaults capture ROOT; inject only the local sidecar connection for this fixture.
            with patch('lyrics_lrclib.ROOT',root),patch('lyrics_lrclib.guards'),patch('lyrics_lrclib.database',side_effect=lambda:sqlite3.connect(root/'data/processed/lyrics.db')),patch('lyrics_lrclib.validate',side_effect=lambda c:l_validate(c,root)):
                l.import_results();l.import_results()
                self.assertEqual(target.execute('SELECT lyrics_status FROM lyrics_manifest').fetchone()[0],'success')
                target.execute("UPDATE songs SET artist='Other'");target.commit()
                with self.assertRaises(ValueError):l.import_results()
                self.assertEqual(target.execute('SELECT lyrics_status FROM lyrics_manifest').fetchone()[0],'success')
            target.close()

# Preserve a reference for the import fixture's patched validator.
l_validate=l.validate

if __name__=='__main__':unittest.main()
