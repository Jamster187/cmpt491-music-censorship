"""A rerun may refresh timings, never silently accept changed results or code."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import course_common as c
import course_verify as verify


class CourseVerificationTests(unittest.TestCase):
    def test_explicit_record_allows_only_operational_artifact_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);name="analysis/course_methods/classification/execution.json";path=root/name
            path.parent.mkdir(parents=True);path.write_text('{"wall_seconds": 2}')
            manifest={"sha256":{name:"previous timing hash"},"sources_sha256":{}}
            with patch.object(c,"ROOT",root):
                with self.assertRaisesRegex(ValueError,"Publication changed"):verify.check_manifest(manifest)
                self.assertEqual(verify.check_manifest(manifest,True),[name])
                result="analysis/course_methods/classification/evaluation.csv";(root/result).write_text("changed metrics")
                manifest["sha256"][result]="previous result hash"
                with self.assertRaisesRegex(ValueError,"evaluation.csv"):verify.check_manifest(manifest,True)

    def test_source_changes_are_never_operational_exemptions(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);name="src/course_classification.py";(root/"src").mkdir();(root/name).write_text("changed implementation")
            manifest={"sha256":{},"sources_sha256":{name:"previous code hash"}}
            with patch.object(c,"ROOT",root):
                with self.assertRaisesRegex(ValueError,"course_classification.py"):verify.check_manifest(manifest,True)


if __name__=="__main__":unittest.main()
