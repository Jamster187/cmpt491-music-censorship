"""Regression coverage for full-universe joins and month-end publication."""
import csv
import lzma
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import final_dataset as f


class FinalDatasetTests(unittest.TestCase):
    def setUp(self):
        self.ids=[f.song_id(t,'Artist & Guest') for t in ('Été, "One"','Two','Outside')]
        self.history={s:(s,t,'Artist & Guest','2000-01-01','2000-01-29',1,2,2,200)
                      for s,t in zip(self.ids,('Été, "One"','Two','Outside'))}
        self.monthly=[('2000-01','2000-01-29',i+1,s,None,1,2,1,i) for i,s in enumerate(self.ids[:2])]
        self.metadata={s:('',)*9 for s in self.ids[:2]}
        self.status={s:'not_found' for s in self.ids[:2]}
        self.lyrics={self.ids[0]:'success',self.ids[1]:'not_found'}
        self.features={self.ids[0]:(.125,)*42}
        self.genres={s:('Pop','medium',['Rock']) for s in self.ids[:2]}

    def project(self):
        return f.make_song_rows(self.history,self.monthly,self.metadata,self.status,self.lyrics,self.features,self.genres)

    def test_outside_universe_keeps_identity_but_never_implies_lyrics_failure(self):
        rows,pop=self.project();outside=dict(zip(f.SONG_COLUMNS,rows[self.ids[2]]))
        self.assertEqual(outside['title'],'Outside')
        self.assertEqual(outside['in_final_study_population'],0)
        self.assertEqual(outside['lyrics_status'],'outside_final_study_population')
        self.assertIsNone(outside['lyrics_available'])
        self.assertIsNone(outside['primary_genre'])
        self.assertTrue(all(outside[k] is None for k in f.COLUMNS))
        self.assertEqual(pop,set(self.ids[:2]))

    def test_monthly_and_weekly_share_exact_enrichment_and_keep_repeated_ids(self):
        rows,pop=self.project()
        weekly=[('2000-01-29',1,None,1,2,1,0,self.ids[0]),('2000-01-29',2,None,1,2,1,1,self.ids[0]),
                ('2000-01-01',3,None,3,1,0,2,self.ids[2])]
        w=list(f.table_rows('weekly',rows,pop,weekly,self.monthly))
        m=list(f.table_rows('monthly',rows,pop,weekly,self.monthly))
        self.assertEqual(len(w),3)
        self.assertEqual(w[0][7:],m[0][8:])
        self.assertEqual(w[0][7:],w[1][7:])
        self.assertNotEqual(w[0][6],w[1][6])
        self.assertEqual(m[0][:3],('2000-01','2000-01-29',1))
        self.assertEqual(m[1][-42:],(None,)*42)

    def test_reject_orphans_and_foreign_genre_population(self):
        del self.history[self.ids[1]]
        with self.assertRaisesRegex(ValueError,'Missing song'):self.project()
        self.setUp();self.genres[self.ids[2]]=('Rock','high',[])
        with self.assertRaisesRegex(ValueError,'population join'):self.project()

    def test_reject_unapproved_missingness_and_lyrics_mismatch(self):
        self.features[self.ids[0]]=(None,)*4+(.1,)*38
        with self.assertRaisesRegex(ValueError,'missingness'):self.project()
        self.features={self.ids[1]:(.1,)*42}
        with self.assertRaisesRegex(ValueError,'Lyrics/classifier'):self.project()
        sid=next(iter(f.EXCEPTIONS))[0]
        f.check_feature_nulls(sid,(None,)*4+(.1,)*38,True)
        with self.assertRaisesRegex(ValueError,'missingness'):f.check_feature_nulls(sid,(.1,)*42,True)

    def test_reject_changed_identity_taxonomy_and_secondary_duplicates(self):
        self.history[self.ids[0]]=(self.ids[0],'changed','Artist & Guest',*self.history[self.ids[0]][3:])
        with self.assertRaisesRegex(ValueError,'Identity'):self.project()
        self.setUp();self.genres[self.ids[0]]=('Invented','high',[])
        with self.assertRaisesRegex(ValueError,'Invalid genre'):self.project()
        self.genres[self.ids[0]]=('Pop','high',['Rock','Rock'])
        with self.assertRaisesRegex(ValueError,'secondary'):self.project()

    def test_source_check_keeps_all_original_rows_and_rejects_rank_edit(self):
        def row(rank):return dict(song='Été, "One"',artist='Artist & Guest',this_week=rank,last_week=None,peak_position=1,weeks_on_chart=2)
        charts=[dict(date='2000-01-01',data=[row(1)]),dict(date='2000-01-29',data=[row(1),row(2)])]
        monthly,_=f.select_snapshots(charts)
        weekly=[('2000-01-01',1,None,1,2,0,0,self.ids[0]),('2000-01-29',1,None,1,2,1,0,self.ids[0]),('2000-01-29',2,None,1,2,1,1,self.ids[0])]
        f.validate_charts(charts,weekly,monthly)
        with self.assertRaisesRegex(ValueError,'Weekly source'):f.validate_charts(charts,weekly[:-1],monthly)
        bad=list(weekly);bad[0]=('2000-01-01',4,*bad[0][2:])
        with self.assertRaises(ValueError):f.validate_charts(charts,bad,monthly)
        with self.assertRaisesRegex(ValueError,'Monthly'):f.validate_charts(charts,weekly,monthly[:-1])

    def test_serialization_preserves_unicode_quotes_float_precision_and_missing(self):
        rows,pop=self.project();serial={s:tuple(f.public_cell(v) for v in r) for s,r in rows.items()}
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'songs.csv'
            def values():return f.serialized_rows('songs',serial,pop,[],self.monthly)
            f.write_table(p,f.SONG_COLUMNS,values());f.reconcile(p,f.SONG_COLUMNS,values())
            with p.open() as handle:actual={r['song_id']:r for r in csv.DictReader(handle)}
            self.assertEqual(actual[self.ids[0]]['title'],'Été, "One"')
            self.assertEqual(actual[self.ids[0]][f.COLUMNS[0]],repr(.125))
            self.assertEqual(actual[self.ids[1]][f.COLUMNS[0]],'')
            self.assertEqual(actual[self.ids[0]]['secondary_genres'],'["Rock"]')
            p.write_text(p.read_text().replace('0.125','0.126',1))
            with self.assertRaisesRegex(ValueError,'reconciliation'):f.reconcile(p,f.SONG_COLUMNS,values())

    def test_lossless_deterministic_compression_and_size_gate(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'source';p.write_bytes('title,score\nÉté,0.12345678912345678\n'.encode()*100)
            a,b=Path(td)/'a.xz',Path(td)/'b.xz'
            f.deterministic_xz(p,a);f.deterministic_xz(p,b)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            self.assertEqual(lzma.decompress(a.read_bytes()),p.read_bytes())
        self.assertEqual(f.distribution_name('master_weekly.csv',100*1024**2),'master_weekly.csv.xz')
        with self.assertRaises(ValueError):f.distribution_name('master_monthly.csv',100*1024**2)

    def test_combined_store_overlap_or_missing_disposition_fails(self):
        with self.assertRaisesRegex(ValueError,'Overlapping'):f.combine({'a':1},{'a':2},{'a'})
        with self.assertRaisesRegex(ValueError,'Missing'):f.combine({'a':1},{},{'b'})
        self.assertEqual(f.combine({'a':1,'old':9},{'b':2},{'a','b'}),{'a':1,'b':2})

    def test_schema_excludes_internal_and_old_month_aggregates(self):
        self.assertEqual(len(f.COLUMNS),42)
        for fields in (f.SONG_COLUMNS,f.WEEKLY_COLUMNS,f.MONTHLY_COLUMNS):
            self.assertEqual(len(set(fields)),len(fields))
            self.assertFalse(set(fields)&{'reason','lyrics_text','lyrics_path','monthly_points','weeks_present','average_weekly_rank','model_reasoning'})
        self.assertEqual(f.WEEKLY_COLUMNS[7:],f.MONTHLY_COLUMNS[8:])

class LegacyPublicationGuardTests(unittest.TestCase):
    def test_old_exporter_cannot_overwrite_final_release(self):
        from unittest.mock import patch
        import public_dataset
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'manifest.json').write_text('{"version":"final-snapshots-v3.0"}')
            with patch.object(public_dataset,'PUBLIC',root):
                with self.assertRaisesRegex(ValueError,'Final snapshot release'):
                    public_dataset.build()
