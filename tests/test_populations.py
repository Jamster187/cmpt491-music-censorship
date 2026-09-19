"""Population regressions using small local SQLite fixtures."""
import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from populations import attach_weekly, create_monthly, validate, export_query


class PopulationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name) / "source.db"
        with sqlite3.connect(str(self.source)) as c:
            c.execute("CREATE TABLE songs(song_id TEXT PRIMARY KEY)")
            c.execute("CREATE TABLE chart_observations(song_id TEXT,chart_date TEXT,rank INTEGER)")
        self.conn = sqlite3.connect(":memory:", uri=True)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def build(self, rows):
        with sqlite3.connect(str(self.source)) as c:
            c.executemany("INSERT INTO songs VALUES (?)", [(s,) for s in sorted({r[0] for r in rows})])
            c.executemany("INSERT INTO chart_observations VALUES (?,?,?)", rows)
        self.before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        attach_weekly(self.conn,self.source)
        create_monthly(self.conn)
        validate(self.conn)
        return self.conn.execute("SELECT * FROM monthly_top100 ORDER BY month,monthly_rank").fetchall()

    def test_month_assignment_persistence_and_points(self):
        rows = self.build([('a','2020-01-25',1),('a','2020-02-01',100),
                           ('b','2020-01-04',40),('b','2020-01-11',40)])
        self.assertEqual(rows[0][:4], ('2020-01',1,'b',122))
        self.assertEqual(rows[2][:4], ('2020-02',1,'a',1))
        self.assertEqual(rows[0][4:],(2,40,40.0,2))

    def test_all_tie_breakers_and_exact_averages(self):
        rows = []
        for sid,ranks in [('a',[1]),('b',[50,52]),('c',[51,51]),('d',[51,51]),('e',[51,76,76])]:
            rows += [(sid,'2020-01-{:02}'.format(i+1),rank) for i,rank in enumerate(ranks)]
        actual = self.build(list(reversed(rows)))
        self.assertEqual([r[2] for r in actual],['a','b','c','d','e'])
        self.assertTrue(all(r[3]==100 for r in actual))

    def test_cutoff_is_exactly_100_even_when_tied(self):
        actual = self.build([('s{:03}'.format(i),'2020-01-04',100) for i in reversed(range(101))])
        self.assertEqual(len(actual),100)
        self.assertEqual(actual[-1][2],'s099')

    def test_small_month_keeps_all_eligible_songs(self):
        self.assertEqual(len(self.build([('a','2020-01-04',1)])),1)

    def test_duplicate_observations_are_not_duplicate_weeks(self):
        actual = self.build([('a','2020-01-04',1),('a','2020-01-04',20),('a','2020-01-11',3)])
        self.assertEqual(actual[0][3:],(279,2,1,8.0,3))

    def test_readonly_source_and_weekly_export_unchanged(self):
        self.build([('a','2020-01-04',1),('a','2020-01-11',100)])
        with self.assertRaises(sqlite3.OperationalError):
            self.conn.execute("DELETE FROM source.chart_observations")
        target = Path(self.tmp.name) / "weekly.csv"
        self.assertEqual(export_query(self.conn,target,"SELECT * FROM weekly_top100 ORDER BY chart_date"),2)
        self.assertEqual(self.before,hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_missing_or_invalid_rank_fails(self):
        for rank in (None,0,101):
            with self.subTest(rank=rank):
                with sqlite3.connect(str(self.source)) as c:
                    c.execute("DELETE FROM chart_observations")
                    c.execute("INSERT INTO chart_observations VALUES ('a','2020-01-04',?)",(rank,))
                conn = sqlite3.connect(":memory:",uri=True)
                try:
                    attach_weekly(conn,self.source)
                    with self.assertRaises(ValueError):
                        create_monthly(conn)
                finally:
                    conn.close()

    def test_reconciliation_detects_corrupted_points(self):
        self.build([('a','2020-01-04',1)])
        self.conn.execute("UPDATE monthly_top100 SET monthly_points=99")
        with self.assertRaisesRegex(ValueError,"reconciliation"):
            validate(self.conn)

    def test_orphan_ids_fail_validation(self):
        self.build([('a','2020-01-04',1)])
        # Read-only attachment is detached only to inject an invalid source fixture.
        self.conn.commit()
        self.conn.execute("DROP VIEW weekly_top100")
        self.conn.execute("DETACH DATABASE source")
        with sqlite3.connect(str(self.source)) as c:
            c.execute("DELETE FROM songs")
        attach_weekly(self.conn,self.source)
        with self.assertRaisesRegex(ValueError,"referential integrity"):
            validate(self.conn)


if __name__ == '__main__':
    unittest.main()
