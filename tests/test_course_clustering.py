"""Medoid objective, sample bounds and fitted-only transformations."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.metrics import adjusted_rand_score
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import course_clustering as cluster
import course_common as c


class ClusteringTests(unittest.TestCase):
    def test_one_medoid_matches_exhaustive_optimum(self):
        x=np.array([[0.,0.],[1.,0.],[1.,1.],[9.,9.]])
        result=cluster.kmedoids(x,1,491)
        expected=int(cdist(x,x).sum(axis=1).argmin())
        self.assertEqual(result["medoid_indices"],[expected])
        self.assertAlmostEqual(result["objective"],cdist(x,x).sum(axis=1)[expected])

    def test_medoid_monotonicity_and_reproducible_separated_clusters(self):
        rng=np.random.default_rng(491);x=np.vstack([rng.normal(-8,.2,(40,3)),rng.normal(8,.2,(40,3))])
        first=cluster.kmedoids(x,2,491);second=cluster.kmedoids(x,2,491)
        self.assertEqual(first,second);self.assertTrue(np.all(np.diff(first["objective_trace"])<=1e-8))
        self.assertAlmostEqual(adjusted_rand_score([0]*40+[1]*40,first["native_labels"]),1.)
        for center in first["centers"]:self.assertTrue(np.any(np.all(x==center,axis=1)))

    def test_training_only_scaler_and_family_weights(self):
        rng=np.random.default_rng(491);f=pd.DataFrame(rng.normal(size=(200,42)),columns=c.SCORES);f["song_id"]=[str(i) for i in range(len(f))]
        definition=cluster.representations(f);z=cluster.transform(f,definition,"standardized42")
        np.testing.assert_allclose(z.mean(axis=0),0,atol=1e-12);np.testing.assert_allclose(z.std(axis=0),1)
        later=f.copy();later[c.SCORES]+=100
        self.assertGreater(cluster.transform(later,definition,"standardized42").mean(),90)
        balanced=cluster.transform(f,definition,"family_balanced")
        for names in c.FAMILIES.values():
            indexes=[c.SCORES.index(n) for n in names]
            self.assertAlmostEqual(balanced[:,indexes].var(axis=0).sum(),1.)
        self.assertGreaterEqual(sum(definition["pca_explained_variance_ratio"]),.9)

    def test_sampling_is_bounded_and_reproducible(self):
        first=cluster.sample_indices(10000,1200,491)
        self.assertEqual(len(first),1200);self.assertEqual(len(set(first)),1200)
        np.testing.assert_array_equal(first,cluster.sample_indices(10000,1200,491))


if __name__=="__main__":unittest.main()
