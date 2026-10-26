"""Public release integrity, matched populations, metrics and portable replay."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from feature_expansion_common import PUBLIC,DATA,read_json,sha
from feature_expansion_predict import predict_export
from feature_expansion_models import metrics


@unittest.skipUnless((PUBLIC/'publication_manifest.json').exists(),'Feature expansion publication not present')
class FeaturePublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.features=pd.read_csv(DATA/'song_features.csv.xz').set_index('song_id')
        cls.outcomes=pd.read_csv(DATA/'song_outcomes.csv.xz').set_index('song_id')
        cls.pred=pd.read_csv(PUBLIC/'selected_predictions.csv.gz')
        cls.selected=pd.read_csv(PUBLIC/'selected_models.csv')
        cls.comparison=pd.read_csv(PUBLIC/'model_comparison.csv')

    def test_publication_hashes_and_feature_code_provenance(self):
        manifest=read_json(PUBLIC/'publication_manifest.json')
        for name,expected in manifest['artifacts'].items():self.assertEqual(sha(PUBLIC/name),expected,name)
        for name,expected in manifest['code'].items():self.assertEqual(sha(ROOT/'src'/name),expected,name)
        for name,expected in manifest['inputs'].items():self.assertEqual(sha(DATA/name),expected,name)
        build=read_json(DATA/'manifest.json')
        for name,expected in build['pipeline_sha256'].items():self.assertEqual(sha(ROOT/name),expected,name)
        self.assertEqual(len(self.features),32723);self.assertEqual(set(self.features.index),set(self.outcomes.index))

    def test_configuration_populations_and_outcomes_match(self):
        for keys,g in self.pred.groupby(['track','target','partition']):
            sets=[set(q.song_id) for _,q in g.groupby('configuration')]
            self.assertEqual(len(sets),3);self.assertTrue(all(s==sets[0] for s in sets))
            self.assertFalse(g.duplicated(['configuration','song_id']).any())
            self.assertTrue(self.outcomes.loc[g.song_id,'eligible_26'].all())
            np.testing.assert_array_equal(g.actual.to_numpy(),self.outcomes.loc[g.song_id,keys[1]+'_26'].to_numpy())
            if keys[1]=='top10':self.assertTrue(self.features.loc[g.song_id,'debut_rank'].gt(10).all())

    def test_saved_metrics_and_portable_predictions(self):
        for choice in self.selected.itertuples():
            bundle=read_json(PUBLIC/'models'/f'{choice.track}_{choice.target}_{choice.configuration}.json.gz')
            for partition in ['validation','test']:
                g=self.pred[self.pred.track.eq(choice.track)&self.pred.target.eq(choice.target)&self.pred.configuration.eq(choice.configuration)&self.pred.partition.eq(partition)]
                sample=g.iloc[np.linspace(0,len(g)-1,min(24,len(g)),dtype=int)]
                predicted=predict_export(bundle,self.features.loc[sample.song_id])
                np.testing.assert_allclose(predicted,sample.prediction,rtol=1e-9,atol=1e-9)
                cls=choice.target in ['top10','long_chart'];m=metrics(g.actual,g.prediction,cls,choice.threshold)
                row=self.comparison[self.comparison.track.eq(choice.track)&self.comparison.target.eq(choice.target)&self.comparison.configuration.eq(choice.configuration)&self.comparison.method.eq(choice.method)&self.comparison.partition.eq(partition)].iloc[0]
                for name in ['balanced_accuracy','brier','roc_auc','pr_auc'] if cls else ['r2','mae','rmse']:
                    self.assertAlmostEqual(m[name],row[name],places=9,msg=str((choice.track,choice.target,choice.configuration,partition,name)))


if __name__=='__main__':unittest.main()
