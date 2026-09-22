"""Bounded, resumable genre experiment: only the frozen 300-song pilot."""
import argparse
import fcntl
import hashlib
import json
import re
import subprocess
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from genre_rules import TAXONOMY
from genre_pilot import load_sample

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/genre_llm'
LOCAL = ROOT / 'data/experiments/genre_llm'
DOC = ROOT / 'docs/genre/llm'
MODEL = 'gpt-5.5'
BATCH = 10
EXCLUDED_TAG = re.compile(r'billboard|chart|rank|top\s*\d|number\s*(one|1)|covid|pandemic', re.I)
CONFIG = ['model_reasoning_effort="medium"', 'web_search="disabled"',
          'features.shell_tool=false', 'features.unified_exec=false',
          'features.multi_agent=false', 'project_doc_max_bytes=0',
          'features.memories=false']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix=path.name, suffix='.tmp', delete=False) as handle:
        handle.write(text)
        tmp = Path(handle.name)
    tmp.replace(path)


def schema():
    fields = {'song_id': {'type': 'string'},
              'primary_genre': {'type': 'string', 'enum': list(TAXONOMY)},
              'secondary_genres': {'type': 'array', 'items': {'type': 'string', 'enum': list(TAXONOMY)}},
              'confidence': {'type': 'string', 'enum': ['high', 'medium', 'low']},
              'reason': {'type': 'string'}}
    row = {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}
    return {'type': 'object', 'properties': {'predictions': {'type': 'array', 'items': row}},
            'required': ['predictions'], 'additionalProperties': False}


def check_predictions(obj, ids):
    if set(obj) != {'predictions'}:
        raise ValueError('Unexpected response fields')
    rows = obj['predictions']
    if len(rows) != len(ids) or {r['song_id'] for r in rows} != set(ids):
        raise ValueError('Missing, duplicate or foreign song_id')
    for r in rows:
        if set(r) != set(schema()['properties']['predictions']['items']['properties']):
            raise ValueError('Unexpected prediction fields')
        if r['primary_genre'] not in TAXONOMY or r['confidence'] not in ('high', 'medium', 'low'):
            raise ValueError('Invalid genre/confidence')
        sec = r['secondary_genres']
        if not isinstance(sec, list) or len(set(sec)) != len(sec) or any(x not in TAXONOMY or x == r['primary_genre'] for x in sec):
            raise ValueError('Invalid secondary genres')
        if not isinstance(r['reason'], str) or not r['reason'].strip() or len(r['reason'].split()) > 60:
            raise ValueError('Missing/overlong reason')
    return rows


def subset(sample, count, seed):
    """Period round robin, hashed within each period; independent of predictions."""
    if count < 0 or count > len({r['song_id'] for r in sample}):
        raise ValueError('Subset size exceeds available unique songs')
    groups = defaultdict(list)
    for r in sample:
        groups[r['period']].append(r['song_id'])
    for g in groups.values():
        g.sort(key=lambda x: digest((seed + x).encode()))
    result = []
    while len(result) < count:
        for p in sorted(groups):
            if groups[p] and len(result) < count:
                result.append(groups[p].pop(0))
    return result


def evidence_input(row, evidence):
    groups = {}
    for e in evidence:
        # No mapping or previous decision enters the prompt; retain even unmapped labels.
        if e['votes'] <= 0 or EXCLUDED_TAG.search(e['label']):
            continue
        if e['provider'] == 'Wikidata':
            raw = json.loads(e['raw'])
            if raw.get('rank') == 'deprecated' or raw.get('qualifiers'):
                continue
        key = (e['provider'], e['level'], e['label'])
        g = groups.setdefault(key, {'max_support': 0, 'entities': set()})
        g['max_support'] = max(g['max_support'], e['votes'])
        g['entities'].add(e['entity_id'])
    tags = [{'provider': p, 'level': l, 'raw_tag': t, 'max_support': g['max_support'],
             'entity_count': len(g['entities'])} for (p,l,t),g in sorted(groups.items())]
    return {**{k: row[k] for k in ('song_id', 'title', 'artist', 'first_chart_date')}, 'genre_evidence': tags}


def prepare():
    sample_file = ROOT / 'reports/genre/sample.csv'
    rows = load_sample(sample_file)
    if len(rows) != 300 or len({r['song_id'] for r in rows}) != 300:
        raise ValueError('Only the frozen 300-song pilot is supported')
    raw_path = ROOT / 'data/experiments/genre_pilot/pilot_evidence.json'
    raw = {r['song_id']: r['evidence'] for r in json.loads(raw_path.read_text())}
    inputs = [evidence_input(r, raw[r['song_id']]) for r in rows]
    manifest = {'input_screen_version': 2, 'model': MODEL, 'reasoning_effort': 'medium', 'temperature': None,
                'temperature_note': 'Not exposed by this Codex interface; no deterministic guarantee',
                'cli_version': subprocess.check_output(['codex', '--version'], text=True).strip(),
                'batch_size': BATCH, 'config': CONFIG,
                'sample_sha256': digest(sample_file.read_bytes()), 'raw_evidence_sha256': digest(raw_path.read_bytes()),
                'prompt_sha256': digest((DOC / 'prompt.txt').read_bytes()),
                'inputs_sha256': digest(json.dumps(inputs, sort_keys=True, ensure_ascii=False).encode()),
                'identity_only_ids': subset(rows, 77, 'identity-v1'),
                'repeat_ids': subset(rows, 42, 'repeat-v1')}
    target = OUT / 'manifest.json'
    if target.exists() and json.loads(target.read_text()) != manifest:
        raise ValueError('Frozen experiment changed; create a new explicit version')
    dump(target, manifest)
    dump(OUT / 'inputs.json', inputs)
    dump(DOC / 'output.schema.json', schema())
    return inputs, manifest


def run(mode, limit=None):
    inputs, manifest = prepare()
    if mode == 'identity':
        wanted = set(manifest['identity_only_ids'])
        inputs = [{k:v for k,v in r.items() if k != 'genre_evidence'} for r in inputs if r['song_id'] in wanted]
    if mode == 'repeat':
        wanted = set(manifest['repeat_ids'])
        inputs = [r for r in inputs if r['song_id'] in wanted]
    batches = [inputs[i:i+BATCH] for i in range(0,len(inputs),BATCH)]
    if mode == 'exact_repeat':
        batches = [batches[i] for i in (0, 12, 25)]
    for i, batch in enumerate(batches):
        if limit is not None and i >= limit:
            break
        folder = LOCAL / mode / f'{i:03d}'
        folder.mkdir(parents=True, exist_ok=True)
        prompt = (DOC / 'prompt.txt').read_text() + json.dumps(batch, ensure_ascii=False, sort_keys=True) + '\n'
        ids = [r['song_id'] for r in batch]
        done = folder / 'complete.json'
        if done.exists():
            meta = json.loads(done.read_text())
            if meta['prompt_sha256'] != digest(prompt.encode()):
                raise ValueError('Cached prompt mismatch')
            if digest((folder / 'response.json').read_bytes()) != meta['response_sha256']:
                raise ValueError('Cached response changed')
            check_predictions(json.loads((folder / 'response.json').read_text()), ids)
            print(mode, i, 'cached', flush=True)
            continue
        if (folder / 'events.jsonl').exists():
            raise ValueError(f'Prior incomplete attempt at {folder}; inspect before retry')
        (folder / 'request.txt').write_text(prompt)
        with tempfile.TemporaryDirectory(prefix='genre-judge-') as isolated:
            cmd = ['codex', 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral',
                   '--skip-git-repo-check', '-C', isolated, '-s', 'read-only', '-m', MODEL,
                   '--output-schema', str(DOC / 'output.schema.json'), '--json',
                   '-o', str(folder / 'response.json')]
            for c in CONFIG:
                cmd += ['-c', c]
            cmd += ['-']
            start = time.monotonic()
            date = datetime.now(timezone.utc).isoformat()
            with (folder/'events.jsonl').open('w') as stdout, (folder/'stderr.log').open('w') as stderr:
                result = subprocess.run(cmd, input=prompt, text=True, stdout=stdout, stderr=stderr, timeout=600)
            elapsed = time.monotonic()-start
        if result.returncode:
            raise RuntimeError(f'Inference failed: {mode}/{i}; inspect private stderr')
        events = [json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines()]
        items = [e['item'] for e in events if 'item' in e]
        if any(x['type'] not in ('agent_message', 'reasoning') for x in items):
            raise ValueError('Unexpected tool use; do not accept these predictions')
        completed = [e for e in events if e['type'] == 'turn.completed']
        if len(completed) != 1:
            raise ValueError('Expected a single completed inference turn')
        check_predictions(json.loads((folder/'response.json').read_text()), ids)
        dump(done, {'date': date, 'elapsed_seconds': elapsed, 'model_requested': MODEL,
                    'prompt_sha256': digest(prompt.encode()), 'usage': completed[0].get('usage'),
                    'response_sha256': digest((folder/'response.json').read_bytes()), 'song_ids': ids})
        print(mode, i, len(ids), round(elapsed, 1), 'seconds', flush=True)
    all_rows = []
    for i, batch in enumerate(batches):
        folder = LOCAL / mode / f'{i:03d}'
        if (folder/'complete.json').exists():
            all_rows += check_predictions(json.loads((folder/'response.json').read_text()), [r['song_id'] for r in batch])
    dump(OUT / f'{mode}.json', all_rows)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['prepare', 'metadata', 'identity', 'repeat', 'exact_repeat'])
    p.add_argument('--limit-batches', type=int)
    a = p.parse_args()
    if a.command == 'prepare':
        prepare()
    else:
        LOCAL.mkdir(parents=True, exist_ok=True)
        with (LOCAL / (a.command + '.lock')).open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run(a.command, a.limit_batches)
