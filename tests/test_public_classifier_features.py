"""Only accepted model-specific missingness may enter the public feature matrix."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import public_classifier_features as f

class PublicClassifierTests(unittest.TestCase):
    def fixture(self,sid='test'):
        row={'song_id':sid};jobs={}
        for model in f.MODELS:
            spec=f.SPEC['models'][model];artifact=spec['artifact']
            row.update({model+'_status':'success',model+'_model_revision':artifact['revision'],model+'_checkpoint_sha256':artifact['sha256'][artifact['weight_file']]})
            row.update({col:1/3 if model=='cardiff' else .25 for col in spec['columns']})
            jobs[model]={'status':'success','error_type':None,'token_count':10,'chunk_count':1}
        return row,jobs
    def test_namespaced_projection_has_exactly_42_values(self):
        row,jobs=self.fixture();values=f.project_song(row,jobs)
        self.assertEqual(len(values),42);self.assertEqual(values,tuple(row[col] for col in f.COLUMNS))
        self.assertEqual(set(f.MODELS),{'lyriclens','detoxify','goemotions','cardiff'})
    def test_two_exceptions_keep_other_38_features(self):
        self.assertEqual(len(f.EXCEPTIONS),2)
        for sid,model in f.EXCEPTIONS:
            row,jobs=self.fixture(sid);self.assertEqual(model,'lyriclens')
            jobs[model].update(status='error',error_type='ValueError',token_count=None,chunk_count=None)
            row[model+'_status']='error'
            for col in f.SPEC['models'][model]['columns']:row[col]=None
            values=f.project_song(row,jobs)
            self.assertEqual(values[:4],(None,)*4);self.assertTrue(all(v is not None for v in values[4:]))
            row['ll_violence']=0
            with self.assertRaisesRegex(ValueError,'NULL'):f.project_song(row,jobs)
    def test_unknown_failure_and_unfinished_work_rejected(self):
        for state in ('error','pending','running'):
            row,jobs=self.fixture();row['lyriclens_status']=state;jobs['lyriclens']['status']=state
            with self.assertRaisesRegex(ValueError,'Undocumented'):f.project_song(row,jobs)
    def test_wrong_exception_type_or_new_success_is_not_silently_accepted(self):
        sid,model=next(iter(f.EXCEPTIONS));row,jobs=self.fixture(sid)
        with self.assertRaisesRegex(ValueError,'exception evidence'):f.project_song(row,jobs)
        row[model+'_status']='error';jobs[model].update(status='error',error_type='RuntimeError',token_count=None,chunk_count=None)
        with self.assertRaisesRegex(ValueError,'exception evidence'):f.project_song(row,jobs)
    def test_nonfinite_missing_out_of_range_and_text_scores_rejected(self):
        for value in (None,float('nan'),float('inf'),-.01,1.01,'PRIVATE_TEXT_CANARY'):
            row,jobs=self.fixture();row['detox_toxicity']=value
            with self.assertRaisesRegex(ValueError,'Invalid classifier'):f.project_song(row,jobs)
    def test_model_provenance_and_job_set_checked(self):
        row,jobs=self.fixture();row['cardiff_model_revision']='wrong'
        with self.assertRaisesRegex(ValueError,'version'):f.project_song(row,jobs)
        row,jobs=self.fixture();jobs.pop('cardiff')
        with self.assertRaisesRegex(ValueError,'model jobs'):f.project_song(row,jobs)
    def test_private_extra_fields_are_not_projected(self):
        row,jobs=self.fixture();row['lyrics_text']='PRIVATE_TEXT_CANARY';row['private_path']='/Users/private'
        self.assertTrue(all(isinstance(v,float) for v in f.project_song(row,jobs)))
    def test_sentiment_and_status_mismatch_checked(self):
        row,jobs=self.fixture();row['sentiment_positive']=.9
        with self.assertRaisesRegex(ValueError,'sum'):f.project_song(row,jobs)
        row,jobs=self.fixture();row['detoxify_status']='pending'
        with self.assertRaisesRegex(ValueError,'status mismatch'):f.project_song(row,jobs)

if __name__=='__main__':unittest.main()
