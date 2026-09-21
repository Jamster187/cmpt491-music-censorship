"""Bounded Detoxify benchmark: only the frozen LyricLens 200, never the corpus."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import resource
import time
from lyriclens_evaluation import ROOT, REPORTS, read_csv, write_csv, sha, validate_sample

WORK = ROOT / 'data/experiments/detoxify'
SAMPLE = REPORTS / 'lyriclens_sample.csv'
SAMPLE_SHA = '47103f916c19dbe89e9d8541ee56c101158a1a24ec120c2123b529087e962f03'
LL_SHA = 'abef9ffbdf61f3fbe2767c2b1cb067be903657f008c927d53d3a1f5bab9d6f28'
VERSION = 'detoxify-pilot-v1'
LABELS = ('toxicity', 'severe_toxicity', 'obscene', 'identity_attack', 'insult', 'threat', 'sexual_explicit')

def frozen_sample():
    if sha(SAMPLE) != SAMPLE_SHA or sha(REPORTS/'lyriclens_predictions.csv') != LL_SHA:
        raise ValueError('Frozen LyricLens inputs changed')
    rows = read_csv(SAMPLE)
    validate_sample(rows)
    for r in rows:
        if sha(ROOT/'data/lyrics'/f"{r['song_id']}.txt") != r['lyrics_sha256']:
            raise ValueError('Lyric changed')
    return rows

def join_predictions(sample, predictions):
    indexed = {r['song_id']: r for r in predictions}
    if len(indexed) != len(predictions) or set(indexed) != {r['song_id'] for r in sample}:
        raise ValueError('Prediction identities missing/duplicated/extra')
    return [(r, indexed[r['song_id']]) for r in sample]

def validate_scores(logits, scores):
    if len(logits) != 16 or len(scores) != 16:
        raise ValueError('Expected all 16 checkpoint outputs')
    if any(not math.isfinite(x) for x in logits + scores):
        raise ValueError('Nonfinite prediction')
    for x, p in zip(logits, scores):
        expected = 1 / (1 + math.exp(-x)) if x >= 0 else math.exp(x) / (1 + math.exp(x))
        if not 0 <= p <= 1 or abs(expected - p) > 1e-7:
            raise ValueError('Invalid sigmoid output')

def run():
    rows = frozen_sample()
    output = REPORTS/'detoxify_predictions.csv'
    if output.exists():
        raise ValueError('Pilot already exists; validate it instead of overwriting')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import torch
    import transformers
    from transformers import RobertaConfig, RobertaTokenizer, RobertaForSequenceClassification
    torch.set_num_threads(4)
    torch.manual_seed(0)
    pins = json.loads((WORK/'artifacts.json').read_text())
    ckpt = WORK/'toxic_debiased-c7548aa0.ckpt'
    model_hash = sha(ckpt)
    if not model_hash.startswith('c7548aa0'):
        raise ValueError('Official checkpoint checksum prefix mismatch')
    for name, h in pins['tokenizer'].items():
        if sha(WORK/'tokenizer'/name) != h:
            raise ValueError('Tokenizer changed')
    start = time.perf_counter()
    loaded = torch.load(ckpt, map_location='cpu', weights_only=True)
    config = loaded['config']
    if config['dataset']['args']['classes'] != list(LABELS):
        raise ValueError('Unexpected class order')
    model = RobertaForSequenceClassification(RobertaConfig.from_pretrained(WORK/'tokenizer', num_labels=16, local_files_only=True))
    state = loaded['state_dict']
    # Older Transformers serialized this now nonpersistent, deterministic buffer.
    position_ids = state.pop('roberta.embeddings.position_ids', None)
    if position_ids is None or not torch.equal(position_ids, model.roberta.embeddings.position_ids):
        raise ValueError('Unexpected legacy position buffer')
    model.load_state_dict(state, strict=True)
    del loaded
    tokenizer = RobertaTokenizer.from_pretrained(WORK/'tokenizer', local_files_only=True)
    if tokenizer.model_max_length != 512:
        raise ValueError('Unexpected tokenizer limit')
    model.eval()
    load_seconds = time.perf_counter() - start
    # Call upstream predict unchanged, bypassing only its network/pickle loader.
    import sys
    sys.path.insert(0, str(WORK/'source'))
    from detoxify import Detoxify
    upstream = Detoxify.__new__(Detoxify)
    upstream.model, upstream.tokenizer, upstream.class_names, upstream.device = model, tokenizer, list(LABELS), 'cpu'
    captured = []
    hook = model.register_forward_hook(lambda module, args, output: captured.append(output.logits.detach().cpu()))
    results, raw, timings = [], [], []
    for index, row in enumerate(rows):
        text = (ROOT/'data/lyrics'/f"{row['song_id']}.txt").read_text()
        full_tokens = len(tokenizer.encode(text, truncation=False, verbose=False))
        captured.clear()
        started = time.perf_counter()
        scores = upstream.predict(text)
        elapsed = time.perf_counter() - started
        logits = captured[0][0].tolist()
        probabilities = torch.sigmoid(captured[0])[0].tolist()
        validate_scores(logits, probabilities)
        if any(scores[k] != probabilities[i] for i, k in enumerate(LABELS)):
            raise ValueError('Upstream score mismatch')
        raw.append(dict(song_id=row['song_id'], logits=logits, sigmoid_outputs=probabilities, upstream_scores=scores))
        results.append(dict(row, **scores, detoxify_token_count=full_tokens, detoxify_input_tokens=min(full_tokens,512), detoxify_truncated=full_tokens>512,
                            inference_seconds=elapsed, inference_version=VERSION, model_commit=pins['detoxify_commit'], model_sha256=model_hash))
        timings.append(elapsed)
        if (index+1)%25 == 0:
            print(f'{index+1}/200 predictions', flush=True)
    hook.remove()
    rawpath = REPORTS/'detoxify_raw_outputs.jsonl'
    rawpath.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in raw))
    write_csv(output, results)
    pins.update(checkpoint_url='https://github.com/unitaryai/detoxify/releases/download/v0.3-alpha/toxic_debiased-c7548aa0.ckpt', checkpoint_sha256=model_hash,
                checkpoint_bytes=ckpt.stat().st_size, checkpoint_config=config,
                source={str(p.relative_to(WORK/'source')):sha(p) for p in sorted((WORK/'source').rglob('*')) if p.is_file() and '__pycache__' not in str(p)})
    (REPORTS/'detoxify_artifacts.json').write_text(json.dumps(pins,indent=2,sort_keys=True)+'\n')
    run_info = dict(version=VERSION, sample_sha256=sha(SAMPLE), lyriclens_predictions_sha256=LL_SHA, predictions_sha256=sha(output), raw_sha256=sha(rawpath),
                    wrapper_sha256=sha(Path(__file__)), python=platform.python_version(), machine=platform.machine(), torch=torch.__version__, transformers=transformers.__version__,
                    device='cpu', threads=4, dtype='float32', successful=200, failed=0, load_seconds=load_seconds,
                    inference_seconds=sum(timings), seconds_per_song=sum(timings)/200, projected_19372_hours=sum(timings)/200*19372/3600,
                    peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, parameters=sum(p.numel() for p in model.parameters()))
    (REPORTS/'detoxify_run.json').write_text(json.dumps(run_info,indent=2,sort_keys=True)+'\n')
    print(json.dumps(run_info,indent=2))

def validate():
    sample = frozen_sample()
    predictions = read_csv(REPORTS/'detoxify_predictions.csv')
    raw = [json.loads(s) for s in (REPORTS/'detoxify_raw_outputs.jsonl').read_text().splitlines()]
    provenance = json.loads((REPORTS/'detoxify_run.json').read_text())
    for path, key in [('detoxify_predictions.csv','predictions_sha256'), ('detoxify_raw_outputs.jsonl','raw_sha256')]:
        if sha(REPORTS/path) != provenance[key]: raise ValueError('Output changed')
    if sha(Path(__file__)) != provenance['wrapper_sha256']: raise ValueError('Wrapper changed')
    raw_index = {r['song_id']:r for r in raw}
    join_predictions(sample, raw)
    from public_dataset import public_cell
    for a,b in join_predictions(sample,predictions):
        if any(b[k] != v for k,v in a.items()): raise ValueError('Sample metadata changed')
        r = raw_index[a['song_id']]
        validate_scores(r['logits'], r['sigmoid_outputs'])
        for i,k in enumerate(LABELS):
            if float(b[k]) != r['sigmoid_outputs'][i] or float(b[k]) != r['upstream_scores'][k]: raise ValueError('Score mismatch')
        for v in b.values(): public_cell(v)
    print('Validated exact frozen 200 identities, unchanged sampled lyrics, all 16 raw outputs, seven scores and provenance.')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['run','validate'])
    args=parser.parse_args()
    run() if args.command=='run' else validate()
