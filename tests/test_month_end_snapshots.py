"""Snapshot membership, source gaps and exact data reuse regressions."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from billboard import song_id
from month_end_snapshots import select_snapshots, project_songs, master_rows, MASTER_COLUMNS, CLASSIFIER_COLUMNS


def chart(dt,ranks=(1,2),title='Song'):
    return {'date':dt,'data':[{'song':title+str(r),'artist':'Artist','this_week':r,
      'last_week':None,'peak_position':r,'weeks_on_chart':2} for r in ranks]}


class MonthEndTests(unittest.TestCase):
    def test_latest_chart_not_aggregated_membership(self):
        rows,gaps=select_snapshots([chart('2020-01-25',title='Final'),chart('2020-01-04',title='Earlier')])
        self.assertEqual({r[1] for r in rows},{'2020-01-25'})
        self.assertEqual(rows[0][3],song_id('Final1','Artist'))
        self.assertEqual(rows[0][-2:],(0,0))
        self.assertEqual(gaps['2020-01-25'],list(range(3,101)))

    def test_partial_month_and_year_boundaries(self):
        rows,_=select_snapshots([chart('2025-12-27'),chart('2026-01-03'),chart('2026-01-10')])
        self.assertEqual(sorted({r[1] for r in rows}),['2025-12-27','2026-01-10'])

    def test_rank_gap_never_filled(self):
        rows,gaps=select_snapshots([chart('1976-12-25',range(1,100))])
        self.assertEqual(len(rows),99)
        self.assertEqual(gaps,{'1976-12-25':[100]})

    def test_duplicate_or_invalid_rank_rejected(self):
        for ranks in [(1,1),(0,1),(1,101),(True,2)]:
            with self.assertRaises(ValueError):select_snapshots([chart('2020-01-25',ranks)])

    def test_multiple_physical_charts_rejected(self):
        with self.assertRaises(ValueError):select_snapshots([chart('2020-01-25'),chart('2020-01-25')])

    def test_repeated_identity_observations_retained(self):
        c=chart('2020-01-25')
        c['data'][1]['song']=c['data'][0]['song']
        rows,_=select_snapshots([c])
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0][3],rows[1][3])

    def fixture(self):
        rows,_=select_snapshots([chart('2020-01-25',(1,)),chart('2020-02-22',(1,))])
        sid=rows[0][3]
        history={sid:(sid,'Song1','Artist','2019-01-01','2020-02-22',1,10,9,980)}
        return rows,sid,history

    def test_new_song_missingness_and_membership(self):
        rows,sid,history=self.fixture()
        songs=project_songs(history,rows,{}, {}, {})
        self.assertEqual(songs[sid][9:13],('2020-01','2020-02',2,'not_attempted'))
        result=list(master_rows(rows,songs,{}))
        self.assertEqual(len(result),2)
        self.assertTrue(all(v is None for v in result[0][-42:]))
        self.assertEqual(len(result[0]),72)

    def test_exact_reuse_and_partial_classifier_missingness(self):
        rows,sid,history=self.fixture()
        meta=tuple(range(9))
        songs=project_songs(history,rows,{sid:meta},{sid:'high_confidence'},{sid:'success'})
        values=(None,)*4+tuple(i/100 for i in range(38))
        result=list(master_rows(rows,songs,{sid:values}))
        for row in result:
            self.assertEqual(row[-42:],values)
            self.assertEqual(row[7:30],songs[sid][1:])
        self.assertEqual(songs[sid][13:22],meta)

    def test_orphan_and_availability_conflict_rejected(self):
        rows,sid,history=self.fixture()
        with self.assertRaises(ValueError):project_songs({},rows,{}, {}, {})
        songs=project_songs(history,rows,{}, {}, {sid:'success'})
        with self.assertRaises(ValueError):list(master_rows(rows,songs,{}))

    def test_schema_no_month_aggregation_or_combined_features(self):
        self.assertEqual(len(MASTER_COLUMNS),len(set(MASTER_COLUMNS)))
        self.assertEqual(len(CLASSIFIER_COLUMNS),42)
        for col in ('monthly_points','weeks_present','best_weekly_rank','average_weekly_rank','weekly_observations','lyrics_text','CSI','MCR','hardness'):
            self.assertNotIn(col,MASTER_COLUMNS)

if __name__=='__main__':unittest.main()
