"""Public projections must preserve joins while excluding private acquisition evidence."""
import csv
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import public_dataset as public
from research import SCHEMA


class PublicDatasetTests(unittest.TestCase):
    def setUp(self):
        self.c = sqlite3.connect(':memory:')
        self.c.executescript(SCHEMA)
        self.ids = []
        for index, status in enumerate(('high_confidence', 'ambiguous')):
            title = 'A, "Title"' if index == 0 else 'Été'
            sid = public.identity_id(title, 'Artist & Guest')
            self.ids.append(sid)
            self.c.execute('INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                           (sid, title, 'Artist & Guest', title, 'artist',
                            '2000-01-01', '2000-01-01', index+1, 1, 1, 100-index))
            self.c.execute('INSERT INTO study_population VALUES (?,?,?,?)',
                           (sid, '2000-01', '2000-01', 1))
            self.c.execute('INSERT INTO monthly_top100 VALUES (?,?,?,?,?,?,?,?)',
                           ('2000-01', index+1, sid, 100-index, 1, index+1, index+1, 1))
            self.c.execute('INSERT INTO metadata_matches VALUES (?,?,?,?,?,?,?,?,?)',
                           (sid, 'MusicBrainz', status, 'private evidence', 'fixture-v1',
                            '/Users/private/cache.json', 'hash', 'date', '{"secret":"canary"}'))
            self.c.execute('''INSERT INTO lyrics_manifest
              (song_id,lyrics_status,lyrics_source,match_status,lyrics_path,lyrics_sha256,
               retrieved_at,provenance_json) VALUES (?,?,?,?,?,?,?,?)''',
                           (sid, 'success' if index == 0 else 'quarantined', 'LRCLIB',
                            'high_confidence', '/Users/private/'+sid+'.txt', 'hash', 'date',
                            '{"plainLyrics":"PRIVATE_TEXT_CANARY"}'))
        self.add_entity('recording', 'r1', [{'length': 100000}, {'length': 100000}])
        self.add_entity('recording', 'r2', [{'length': 200001}, {'length': None}])
        self.add_entity('release', 'later', [{'date': '2001-03-02', 'title': 'Later'}])
        self.add_entity('release', 'earlier', [{'date': '1999', 'title': 'Earlier'},
                                              {'date': '1999-02', 'title': 'Other territory'}])

    def generate(self,directory):
        return public.generate(self.c,directory,self.features)

    @property
    def features(self):
        return {self.ids[0]:tuple(.25 for _ in public.CLASSIFIER_COLUMNS)}

    def tearDown(self):
        self.c.close()

    def add_entity(self, kind, identifier, variants):
        for variant in variants:
            variant['plainLyrics'] = 'PRIVATE_TEXT_CANARY'
            variant['path'] = '/Users/private/evidence'
        self.c.execute('INSERT INTO external_entities VALUES (?,?,?,?,?)',
                       ('MusicBrainz', kind, identifier, json.dumps(variants), '{"secret":"canary"}'))
        self.c.execute('INSERT INTO song_external_links VALUES (?,?,?,?,?)',
                       (self.ids[0], 'MusicBrainz', kind, identifier, 'supports_asset'))

    def test_projection_excludes_private_evidence_and_preserves_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.assertEqual(self.generate(d), {'songs': 2, 'monthly': 2, 'master': 2, 'baskets': 1})
            raw = (d/'songs.csv').read_text() + (d/'master_dataset.csv').read_text()
            self.assertNotIn('PRIVATE_TEXT_CANARY', raw)
            self.assertNotIn('/Users/', raw)
            self.assertNotIn('canary', raw)
            with (d/'songs.csv').open(newline='') as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                self.assertEqual(row['song_id'], public.identity_id(row['title'], row['artist']))
            self.assertEqual({r['lyrics_available'] for r in rows}, {'0', '1'})

    def test_master_preserves_repeated_song_and_all_source_values(self):
        self.c.execute('INSERT INTO monthly_top100 VALUES (?,?,?,?,?,?,?,?)',
                       ('2000-02', 1, self.ids[0], 100, 1, 1, 1, 1))
        self.c.execute("UPDATE study_population SET last_selected_month='2000-02',months_selected=2 WHERE song_id=?",
                       (self.ids[0],))
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.generate(d)
            def read(name):
                with (d/name).open(newline='') as f:
                    return list(csv.DictReader(f))
            songs = {r['song_id']: r for r in read('songs.csv')}
            monthly, master = read('monthly_top100.csv'), read('master_dataset.csv')
            self.assertEqual(len(master), 3)
            self.assertEqual(sum(r['song_id'] == self.ids[0] for r in master), 2)
            for m, joined in zip(monthly, master):
                self.assertEqual({k: joined[k] for k in m}, m)
                self.assertEqual({k: joined[k] for k in songs[m['song_id']]}, songs[m['song_id']])
            self.assertEqual(master[1]['mb_release_title'], '')
            self.assertEqual(tuple(master[0]), public.MASTER_COLUMNS)

    def test_master_rejects_duplicate_or_missing_song_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.generate(d)
            original = (d/'songs.csv').read_text()
            with (d/'songs.csv').open(newline='') as f:
                rows = list(csv.reader(f))
            public.write_csv(d/'songs.csv', rows[0], rows[1:] + [rows[1]])
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                list(public.master_rows(d,self.features))
            (d/'songs.csv').write_text(original)
            public.write_csv(d/'songs.csv', rows[0], [])
            with self.assertRaisesRegex(ValueError, 'no song match'):
                list(public.master_rows(d,{}))

    def test_master_rejects_unapproved_columns_and_detects_changed_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.generate(d)
            path = d/'master_dataset.csv'
            with path.open(newline='') as f:
                rows = list(csv.reader(f))
            rows[1][0] = '1990-01'
            public.write_csv(path, rows[0], rows[1:])
            with self.assertRaises(ValueError):
                public.reconcile_csv(path, public.MASTER_COLUMNS, public.master_rows(d,self.features))
            with (d/'songs.csv').open(newline='') as f:
                songs = list(csv.reader(f))
            public.write_csv(d/'songs.csv', songs[0]+['private_evidence'],
                             [r+['synthetic'] for r in songs[1:]])
            with self.assertRaisesRegex(ValueError, 'Unexpected song columns'):
                list(public.master_rows(d,self.features))

    def test_classifier_join_preserves_missingness_and_rejects_wrong_population(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);self.generate(d)
            rows=list(public.master_rows(d,self.features))
            self.assertEqual(rows[0][-42:],self.features[self.ids[0]])
            self.assertEqual(rows[1][-42:],(None,)*42)
            partial={self.ids[0]:(None,)*4+self.features[self.ids[0]][4:]}
            self.assertEqual(list(public.master_rows(d,partial))[0][-42:],partial[self.ids[0]])
            for bad in ({},{self.ids[1]:self.features[self.ids[0]]}):
                with self.assertRaisesRegex(ValueError,'coverage'):list(public.master_rows(d,bad))
            with self.assertRaisesRegex(ValueError,'feature count'):list(public.master_rows(d,{self.ids[0]:(.5,)}))
            with self.assertRaisesRegex(ValueError,'Invalid classifier'):list(public.master_rows(d,{self.ids[0]:(float('inf'),)*42}))

    def test_release_date_title_and_precision_are_coherent(self):
        values = public.metadata_summaries(self.c)[self.ids[0]]
        self.assertEqual(values[:5], (2, 2, '1999', 'year', 'Earlier'))
        self.assertEqual(values[5:], ('150.0005', '100', '200.001', 2))

    def test_uncertain_metadata_is_not_exported(self):
        self.assertEqual(public.metadata_summaries(self.c)[self.ids[1]], ('',)*9)

    def test_missing_durations_and_undated_release(self):
        self.c.execute("UPDATE external_entities SET metadata_json='[{\"length\":null}]' WHERE entity_type='recording'")
        self.c.execute("UPDATE external_entities SET metadata_json='[{\"title\":\"Undated\"}]' WHERE entity_type='release'")
        self.assertEqual(public.metadata_summaries(self.c)[self.ids[0]][2:],
                         ('', '', 'Undated', '', '', '', 0))

    def test_deterministic_regeneration(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'
            a.mkdir(); b.mkdir()
            self.generate(a)
            self.c.execute('PRAGMA reverse_unordered_selects=ON')
            self.generate(b)
            for name in ('songs.csv', 'monthly_top100.csv', 'master_dataset.csv'):
                self.assertEqual((a/name).read_bytes(), (b/name).read_bytes())

    def test_reject_missing_manifest(self):
        self.c.execute('DELETE FROM lyrics_manifest WHERE song_id=?', (self.ids[1],))
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            self.generate(Path(tmp))

    def test_reject_orphan_and_inconsistent_measurement(self):
        rows = public.song_rows(self.c)
        for sid, points in (('missing', 100), (self.ids[0], 99)):
            with self.assertRaises(ValueError):
                public.validate_relations(rows, [('2000-01', 1, sid, points, 1, 1, 1, 1)])

    def test_csv_corruption_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'test.csv'
            public.write_csv(p, ('id',), [('a',)])
            with self.assertRaises(ValueError):
                public.reconcile_csv(p, ('id',), [('b',)])
            p.write_text('id\na\nextra\n')
            with self.assertRaises(ValueError):
                public.reconcile_csv(p, ('id',), [('a',)])

    def test_private_fields_rejected_without_rejecting_release_labels(self):
        for value in ('/Users/person/file', 'C:\\private\\file', 'api_key=abc',
                      'password=abc', 'file:///etc/private', float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                public.public_cell(value)
        for value in ('Secret: Songs', 'R&B:/ Soul', 'A/B', 'Café'):
            self.assertEqual(public.public_cell(value), value)

    def test_partial_dates_preserved_and_invalid_dates_rejected(self):
        for value in ('2000', '2000-02', '2000-02-29'):
            self.assertEqual(public.partial_date(value), value)
        for value in ('2001-02-29', '2000-13', '2000-1', 'unknown'):
            with self.assertRaises(ValueError):
                public.partial_date(value)


if __name__ == '__main__':
    unittest.main()
