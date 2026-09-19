"""Research schema preserves identities and enforces study-only enrichment."""
import sqlite3
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research import SCHEMA


class ResearchSchemaTests(unittest.TestCase):
    def setUp(self):
        self.conn=sqlite3.connect(':memory:')
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.executescript(SCHEMA)
        for sid in ('selected','not_selected'):
            self.conn.execute('INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                              (sid,sid,'Artist',sid,'artist','2000-01-01','2000-01-08',1,2,2,199))
        self.conn.execute("INSERT INTO study_population VALUES ('selected','2000-01','2000-01',1)")

    def tearDown(self):
        self.conn.close()

    def test_weekly_duplicate_song_dates_preserved_by_source_coordinate(self):
        for index in (0,1):
            self.conn.execute('INSERT INTO chart_observations VALUES (?,?,?,?,?,?,?,?)',('selected','2000-01-01',index+1,None,1,1,0,index))
        self.assertEqual(self.conn.execute('SELECT count(*),sum(weekly_points) FROM weekly_top100').fetchone(),(2,199))

    def test_monthly_requires_canonical_identity_and_unique_rank(self):
        values=('2000-01',1,'selected',100,1,1,1,1)
        self.conn.execute('INSERT INTO monthly_top100 VALUES (?,?,?,?,?,?,?,?)',values)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute('INSERT INTO monthly_top100 VALUES (?,?,?,?,?,?,?,?)',values)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute('INSERT INTO monthly_top100 VALUES (?,?,?,?,?,?,?,?)',('2000-01',2,'missing',100,1,1,1,1))

    def test_lyrics_restricted_to_study_and_success_requires_provenance(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO lyrics_manifest(song_id) VALUES ('not_selected')")
        self.conn.execute("INSERT INTO lyrics_manifest(song_id) VALUES ('selected')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE lyrics_manifest SET lyrics_status='success'")
        self.assertEqual(self.conn.execute('SELECT lyrics_status FROM lyrics_manifest').fetchone()[0],'not_attempted')

    def test_multiple_recordings_link_to_one_asset_without_identity_change(self):
        before=self.conn.execute("SELECT * FROM songs WHERE song_id='selected'").fetchone()
        for rid in ('r1','r2'):
            self.conn.execute('INSERT INTO external_entities VALUES (?,?,?,?,?)',('MusicBrainz','recording',rid,'{}','{}'))
            self.conn.execute('INSERT INTO song_external_links VALUES (?,?,?,?,?)',('selected','MusicBrainz','recording',rid,'supports_asset'))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM song_external_links').fetchone()[0],2)
        self.assertEqual(before,self.conn.execute("SELECT * FROM songs WHERE song_id='selected'").fetchone())

    def test_links_cannot_reference_nonstudy_song_or_missing_entity(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO song_external_links VALUES ('selected','MusicBrainz','recording','missing','supports_asset')")


if __name__=='__main__':
    unittest.main()
