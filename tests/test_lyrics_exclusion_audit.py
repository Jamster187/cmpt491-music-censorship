"""Synthetic audit regressions; no copyrighted/provider lyric fixtures."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import lyrics_exclusion_audit as audit
from lyrics_production_match import decide
from lyrics_lrclib import digest


def candidate(artist='Alpha feat. Beta'):
    return dict(id=1,trackName='Example',artistName=artist,albumName='Example Album',duration=180,
                instrumental=False,plainLyrics='\n'.join(' '.join('token'+str(i+j) for i in range(20)) for j in range(5)),syncedLyrics=None)


class ExclusionAuditTest(unittest.TestCase):
    def test_syntax_probe_keeps_all_names_and_does_not_mutate(self):
        song=dict(song_id='sample',title='Example',artist='Alpha With Beta',metadata={})
        c=candidate();before=copy.deepcopy((song,c))
        self.assertEqual(decide(song,[c])['status'],'quarantined')
        self.assertEqual(audit.syntax_probe(song,{1:c})['status'],'accepted')
        self.assertEqual((song,c),before)
        self.assertNotEqual(audit.syntax_probe(song,{1:candidate('Alpha')})['status'],'accepted')
        self.assertNotEqual(audit.syntax_probe(song,{1:candidate('Alpha feat. Gamma')})['status'],'accepted')

    def test_unicode_feature_and_junior_comma(self):
        self.assertEqual(audit.syntax_credit('Person, Jr.'),'Person Jr.')
        song=dict(title='Example',artist='Alpha Featuring Beta',metadata={})
        self.assertEqual(audit.syntax_probe(song,{1:candidate('Alpha Feat․ Beta')})['status'],'accepted')
        # No inferred separators or name aliases.
        self.assertNotEqual(audit.syntax_probe(song,{1:candidate('Alpha Beta')})['status'],'accepted')
        self.assertEqual(audit.syntax_credit('The Example Group'),'The Example Group')

    def test_probe_retains_text_and_version_gates(self):
        song=dict(title='Example',artist='Alpha With Beta',metadata={})
        c=candidate();c['plainLyrics']='brief synthetic fragment'
        self.assertEqual(audit.syntax_probe(song,{1:c})['status'],'quarantined')
        c=candidate();c['albumName']='Example Live'
        self.assertEqual(audit.syntax_probe(song,{1:c})['status'],'quarantined')
        c=candidate();song['metadata']={'durations':[300]}
        self.assertEqual(audit.syntax_probe(song,{1:c})['status'],'quarantined')

    def test_repeat_profile_is_a_description_not_acceptance(self):
        a='red blue\ngreen yellow\nred blue\ngreen yellow'
        b='red blue\ngreen yellow'
        p=audit.text_profile([a,b])
        self.assertEqual(p['primary'],'text_repeat_count_only')
        self.assertNotIn('accepted',p)
        self.assertEqual(audit.text_profile(['red\nblue','blue\nred'])['primary'],'text_same_lines_reordered')
        self.assertEqual(audit.text_profile([a,'unrelated silver purple'])['primary'],'text_substantive_conflict')

    def test_identity_and_text_questions_stay_separate(self):
        row=dict(eligible_candidates=0,primary='identity_incomplete_credit',status='quarantined')
        self.assertEqual(audit.text_question(row),'unassessed_for_target_identity')
        row.update(eligible_candidates=2,primary='text_near_agreement')
        self.assertEqual(audit.text_question(row),'quality_screened_but_transcriptions_conflict')

    def test_all_text_groups_matter(self):
        text=' '.join('word'+str(i) for i in range(100))
        self.assertEqual(audit.text_profile([text,text+' extra','entirely different'])['primary'],'text_substantive_conflict')

    def test_sampling_is_order_independent(self):
        rows=[dict(song_id=str(i),status='quarantined',primary='identity_title_variant') for i in range(50)]
        self.assertEqual(audit.sample(rows),audit.sample(list(reversed(rows))))
        self.assertEqual(len(audit.sample(rows)),20)

    def test_projection_does_not_double_count_safe_or_errors(self):
        rows=[dict(song_id=str(i),status='quarantined',primary='example') for i in range(10)]
        rows.append(dict(song_id='error',status='error',primary='error'))
        reviews=[dict(rows[0],outcome='safe_candidate'),dict(rows[1],outcome='possible_deterministic'),
                 dict(rows[2],outcome='manual_review'),dict(rows[-1],outcome='retryable_transport')]
        weights,_=audit.recovery_weights(rows,reviews,{'0'})
        self.assertEqual(weights['0'],0)
        self.assertEqual(weights['error'],0)
        self.assertEqual(sum(weights.values()),4.5)

    def test_cache_is_bound_to_retrieval_and_candidate_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=root/'data/cache/lrclib';directory.mkdir(parents=True)
            c=candidate();body=json.dumps([c]);url='https://example.invalid/cached'
            record=dict(url=url,body=body,sha256=digest(body.encode()),status=200)
            path=directory/(digest(url.encode())+'.json');path.write_text(json.dumps(record))
            result=dict(song_id='test',retrievals=[dict(url=url,sha256=record['sha256'])],
                        candidates=[dict(id=1,candidate_sha256=digest(json.dumps(c,ensure_ascii=False,sort_keys=True).encode()))])
            before=path.read_bytes()
            self.assertEqual(audit.cached_candidates(result,root),{1:c})
            self.assertEqual(path.read_bytes(),before)
            result['candidates'][0]['candidate_sha256']='wrong'
            with self.assertRaisesRegex(ValueError,'Candidate checksum'):audit.cached_candidates(result,root)
            result['retrievals'][0]['sha256']='wrong'
            with self.assertRaisesRegex(ValueError,'Cache provenance'):audit.cached_candidates(result,root)


if __name__=='__main__':unittest.main()
