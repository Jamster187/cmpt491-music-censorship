"""Replayable models, float32 boundary rules and independent metric checks."""
from pathlib import Path
import sys
import unittest
import numpy as np
from sklearn import metrics
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import course_classification as model
import course_common as c


class ClassificationTests(unittest.TestCase):
    def test_confusion_metrics_against_sklearn(self):
        y=np.array(["a","a","b","b","b","c"]);pred=np.array(["a","b","a","b","c","a"]);classes=["a","b","c"]
        actual=model.metrics(y,pred,classes)
        self.assertAlmostEqual(actual["accuracy"],metrics.accuracy_score(y,pred))
        self.assertAlmostEqual(actual["balanced_accuracy"],metrics.balanced_accuracy_score(y,pred))
        for average in ("macro","weighted"):
            p,r,f,_=metrics.precision_recall_fscore_support(y,pred,labels=classes,average=average,zero_division=0)
            self.assertAlmostEqual(actual["precision_"+average],p);self.assertAlmostEqual(actual["recall_"+average],r)
            self.assertAlmostEqual(actual["f1_"+average],f)

    def test_tree_rules_and_serialization_include_float_boundaries(self):
        rng=np.random.default_rng(491);x=rng.normal(size=(400,42));y=np.where(x[:,0]+x[:,1]>0,"yes","no")
        tree=DecisionTreeClassifier(max_depth=4,random_state=1,class_weight="balanced").fit(x,y)
        export=model.export_tree(tree,x,y);z=x.copy()
        for node,feature in enumerate(tree.tree_.feature):
            if feature>=0:z[node,feature]=tree.tree_.threshold[node]
        expected=tree.predict(z)
        np.testing.assert_array_equal(model.predict_export(export,z)[0],expected)
        np.testing.assert_array_equal(model.predict_rules(export["rules"],c.SCORES,z),expected)
        np.testing.assert_allclose(model.predict_export(export,z)[1],tree.predict_proba(z))

    def test_bayes_export_and_train_only_scaling(self):
        rng=np.random.default_rng(491);x=rng.normal(size=(300,42));y=np.where(x[:,0]>0,"yes","no")
        scaler=StandardScaler().fit(x);bayes=GaussianNB().fit(scaler.transform(x),y);export=model.export_bayes(bayes,scaler)
        test=x[:10]+10
        pred,probs,_=model.predict_export(export,test)
        np.testing.assert_array_equal(pred,bayes.predict(scaler.transform(test)))
        np.testing.assert_allclose(probs,bayes.predict_proba(scaler.transform(test)),rtol=1e-10,atol=1e-12)
        np.testing.assert_allclose(export["mean"],x.mean(axis=0))


if __name__=="__main__":unittest.main()
