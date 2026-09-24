"""Local planning/manifest tests; fixture text is synthetic, never song lyrics."""
import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lyrics_plan import select,prepare
from research import SCHEMA,validate_lyrics_files
from research_report import group_summary,collect


def population():
    return [{'song_id':'song_{}_{}'.format(y,i),'title':'Fixture {} {}'.format(y,i),'artist':'Synthetic Artist','first_chart_date':'{}-05-01'.format(y)}
            for y in range(1958,2027) for i in range(4)]


class LyricsPlanningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'archive/intermediate_reports').mkdir(parents=True)
        (self.root/'archive/intermediate_reports/lyrics_source_assessment.md').write_text('Test: acquisition permission not established.')
        self.conn=sqlite3.connect(':memory:');self.conn.execute('PRAGMA foreign_keys=ON');self.conn.executescript(SCHEMA)
        for s in population():
            self.conn.execute('INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?)',(s['song_id'],s['title'],s['artist'],s['title'],s['artist'],s['first_chart_date'],s['first_chart_date'],1,1,1,100))
            self.conn.execute('INSERT INTO study_population VALUES (?,?,?,?)',(s['song_id'],s['first_chart_date'][:7],s['first_chart_date'][:7],1))
            self.conn.execute('INSERT INTO lyrics_manifest(song_id) VALUES (?)',(s['song_id'],))
        self.conn.commit()

    def tearDown(self):
        self.conn.close();self.tmp.cleanup()

    def test_deterministic_pilot_covers_all_years(self):
        a=select(population());b=select(list(reversed(population())))
        self.assertEqual(a,b);self.assertEqual(len(a),200)
        self.assertEqual({s['first_chart_date'][:4] for s in a},{str(y) for y in range(1958,2027)})

    def test_planning_no_network_and_idempotent(self):
        with patch('lyrics_plan.ROOT',self.root),patch('socket.socket.connect',side_effect=AssertionError('No network')):
            a=prepare(self.conn);before=self.conn.execute('SELECT * FROM lyrics_manifest ORDER BY song_id').fetchall()
            b=prepare(self.conn)
        self.assertEqual(a,b)
        self.assertEqual(before,self.conn.execute('SELECT * FROM lyrics_manifest ORDER BY song_id').fetchall())
        self.assertEqual(self.conn.execute('SELECT count(*) FROM lyrics_pilot').fetchone()[0],200)
        self.assertEqual(validate_lyrics_files(self.conn,self.root),0)

    def test_existing_pilot_cannot_be_silently_replaced(self):
        with patch('lyrics_plan.ROOT',self.root):
            prepare(self.conn)
            self.conn.execute("UPDATE lyrics_pilot SET selection_version='changed'")
            with self.assertRaises(ValueError):
                prepare(self.conn)

    def test_successful_file_is_preserved_and_checked(self):
        sid=population()[0]['song_id'];path=self.root/'data/lyrics'/(sid+'.txt')
        path.parent.mkdir(parents=True);path.write_text('Synthetic fixture text for an integrity test.\n')
        checksum=hashlib.sha256(path.read_bytes()).hexdigest()
        self.conn.execute("UPDATE lyrics_manifest SET lyrics_status='success',lyrics_source='synthetic-test',match_status='high_confidence',lyrics_path=?,lyrics_sha256=?,retrieved_at='2026-09-19T00:00:00Z' WHERE song_id=?",(str(path.relative_to(self.root)),checksum,sid));self.conn.commit()
        before=path.stat().st_mtime_ns
        with patch('lyrics_plan.ROOT',self.root):
            prepare(self.conn)
        self.assertEqual(validate_lyrics_files(self.conn,self.root),1)
        self.assertEqual(path.stat().st_mtime_ns,before)
        path.write_text('Changed fixture')
        with self.assertRaises(ValueError):
            validate_lyrics_files(self.conn,self.root)

    def test_orphan_file_is_detected(self):
        path=self.root/'data/lyrics/orphan.txt';path.parent.mkdir(parents=True);path.write_text('Synthetic fixture')
        with self.assertRaisesRegex(ValueError,'Unmanifested'):
            validate_lyrics_files(self.conn,self.root)

    def test_blocked_is_not_counted_as_attempted_or_not_found(self):
        summary=group_summary([{'metadata_status':None,'lyrics_status':'blocked_source_access'}])
        self.assertEqual(summary['lyrics_attempted'],0)
        self.assertEqual(summary['metadata_attempted'],0)
        self.assertNotIn('not_found',summary['lyrics'])

    def test_partial_coverage_denominators_are_distinct(self):
        rows=[{'metadata_status':status,'lyrics_status':'blocked_source_access'} for status in ('high_confidence','ambiguous',None)]
        s=group_summary(rows)
        self.assertEqual(s['metadata_high_confidence_percent_of_population'],33.33)
        self.assertEqual(s['metadata_high_confidence_percent_of_attempted'],50.0)
        self.assertEqual(s['lyrics_attempted'],0)

    def test_report_field_coverage_keeps_artist_genres_separate(self):
        sid=population()[0]['song_id']
        self.conn.execute('INSERT INTO metadata_matches VALUES (?,?,?,?,?,?,?,?,?)',
                          (sid,'MusicBrainz','high_confidence','fixture','fixture','fixture.json','fixture','2026-09-19','{}'))
        self.conn.execute('INSERT INTO external_entities VALUES (?,?,?,?,?)',
                          ('MusicBrainz','artist','a','[{"genres":[{"name":"genre fixture"}]}]','[]'))
        self.conn.execute('INSERT INTO song_external_links VALUES (?,?,?,?,?)',(sid,'MusicBrainz','artist','a','credited_artist'))
        s=collect(self.conn)
        self.assertEqual(s['metadata_field_coverage']['artist.genres'],1)
        self.assertEqual(s['metadata_field_coverage']['recording.genres'],0)
        self.assertEqual(sum(p['population'] for p in s['by_period']),len(population()))


if __name__=='__main__':
    unittest.main()
