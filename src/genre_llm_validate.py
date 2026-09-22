"""Validate pilot artifacts against exact recorded requests and protected sample."""
import csv
import json
import re
from genre_llm import OUT, LOCAL, DOC, prepare, digest, check_predictions, EXCLUDED_TAG


def validate():
    inputs, manifest=prepare()
    by_id={r['song_id']:r for r in inputs}
    assert not any(EXCLUDED_TAG.search(t['raw_tag']) for r in inputs for t in r['genre_evidence'])
    expected={'metadata':set(by_id),'identity':set(manifest['identity_only_ids']),
              'repeat':set(manifest['repeat_ids']),
              'exact_repeat':{inputs[i]['song_id'] for start in (0,120,250) for i in range(start,start+10)}}
    for mode,wanted in expected.items():
        output=json.loads((OUT/f'{mode}.json').read_text())
        check_predictions({'predictions':output},wanted)
        recorded=[]
        for f in sorted((LOCAL/mode).glob('*/complete.json')):
            meta=json.loads(f.read_text());folder=f.parent
            request=(folder/'request.txt').read_text()
            assert digest(request.encode())==meta['prompt_sha256']
            assert digest((folder/'response.json').read_bytes())==meta['response_sha256']
            supplied=json.loads(request.split('INPUT_JSON:\n',1)[1])
            assert request.startswith((DOC/'prompt.txt').read_text())
            for r in supplied:
                expected_input=by_id[r['song_id']].copy()
                if mode=='identity':del expected_input['genre_evidence']
                assert r==expected_input
            assert meta['song_ids']==[r['song_id'] for r in supplied]
            events=[json.loads(x) for x in (folder/'events.jsonl').read_text().splitlines()]
            assert all(e['item']['type'] in ('agent_message','reasoning') for e in events if 'item' in e)
            assert sum(e['type']=='turn.completed' for e in events)==1
            recorded+=check_predictions(json.loads((folder/'response.json').read_text()),meta['song_ids'])
        assert output==recorded
    for j,original in enumerate((0,12,25)):
        assert (LOCAL/'exact_repeat'/f'{j:03d}'/'request.txt').read_bytes()==(LOCAL/'metadata'/f'{original:03d}'/'request.txt').read_bytes()
    for f in OUT.glob('*.json'):
        text=f.read_text()
        for private in ('/Users/', '/home/', 'Bearer ', 'sk-proj-', 'BEGIN PRIVATE KEY', 'data/lyrics/', 'lyrics_text'):
            assert private not in text, (f.name,private)
    reviews=list(csv.DictReader((OUT/'review.csv').open()))
    predictions={r['song_id']:r for r in json.loads((OUT/'metadata.json').read_text())}
    assert len(reviews)>=100 and len({r['song_id'] for r in reviews})==len(reviews)
    for r in reviews:
        p=predictions[r['song_id']]
        assert r['primary_genre']==p['primary_genre'] and r['confidence']==p['confidence'] and r['reason']==p['reason']
        assert r['title']==by_id[r['song_id']]['title'] and r['artist']==by_id[r['song_id']]['artist']
        assert r['review'] in ('plausible','questionable','clearly wrong') and r['review_note']
    tests=(LOCAL/'tests.log').read_text()
    assert tests.rstrip().endswith('OK')
    test_count=int(re.search(r'Ran (\d+) tests', tests).group(1))
    protected=json.loads((LOCAL/'protected_validation.log').read_text())
    assert protected['protected_unchanged']
    report={'tests_passed':test_count,'protected_files_unchanged':protected['protected_files'], 'sample_unchanged':True,'rows':{k:len(v) for k,v in expected.items()},
            'exact_prompts_verified':True,'outputs_match_recorded_responses':True,
            'tool_calls':0,'public_artifact_sha256':{p.name:digest(p.read_bytes()) for p in sorted(OUT.glob('*')) if p.is_file() and p.name!='validation.json'}}
    from genre_llm import dump
    dump(OUT/'validation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='public_artifact_sha256'},indent=2))

if __name__=='__main__':validate()
