"""Read-only final genre reconciliation; writes only aggregate audit artifacts."""
from collections import Counter
from contextlib import closing
import csv
import fcntl
import json
from pathlib import Path
import re
import sqlite3
import subprocess

import genre_production as g
from genre_evidence import ro, sha, PERIODS
from genre_production_audit import review_sample

OUT = g.ROOT / 'reports/genre_final_audit'
FIELDS = ('song_id', 'primary_genre', 'secondary_genres', 'confidence', 'reason')


def accepted_rows(obj, ids):
    """Mirror strict individual acceptance without modifying a database."""
    if not isinstance(obj, dict) or set(obj) != {'predictions'} or not isinstance(obj['predictions'], list):
        return []
    counts = Counter(r.get('song_id') for r in obj['predictions']
                     if isinstance(r, dict) and isinstance(r.get('song_id'), str))
    accepted = []
    for row in obj['predictions']:
        if not isinstance(row, dict) or not isinstance(row.get('song_id'), str):
            continue
        if row['song_id'] not in ids or counts[row['song_id']] != 1:
            continue
        try:
            g.check_predictions({'predictions': [row]}, [row['song_id']])
        except (ValueError, TypeError, KeyError):
            continue
        accepted.append(row)
    return accepted


def validate_review(rows, reviews):
    selected = {r['song_id']: r for r in review_sample(rows)}
    if len(reviews) != 160 or len({r['song_id'] for r in reviews}) != 160 or set(selected) != {r['song_id'] for r in reviews}:
        raise ValueError('Review is not the exact deterministic 160-song sample')
    for r in reviews:
        if any(r[k] != selected[r['song_id']][k] for k in ('title', 'artist', 'period', 'primary_genre', 'confidence')):
            raise ValueError('Review identity or production label changed')
        if r['judgment'] not in ('plausible', 'questionable', 'clearly wrong') or not r['review_note'].strip():
            raise ValueError('Missing review judgment/note')
    return dict(Counter(r['judgment'] for r in reviews))


def audit():
    processes = subprocess.check_output(['ps', '-axo', 'pid=,comm=,args='], text=True)
    active = [line for line in processes.splitlines()
              if re.search(r'genre_production\.py\s+run(?:\s|$)', line)
              and ('python' in line.lower() or 'codex exec' in line)]
    if active:
        raise ValueError('Genre worker still active')
    with (g.LOCAL / 'worker.lock').open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    before = sha(g.DB)
    with closing(ro(g.DB)) as c:
        c.row_factory = sqlite3.Row
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('SQLite integrity failure')
        settings = g.verify(c)
        summary = g.stats(c)
        rows = [dict(r) for r in c.execute('SELECT * FROM songs ORDER BY song_id')]
        if summary['status_counts'] != {'completed': 28041} or any(r['error'] for r in rows):
            raise ValueError('Incomplete production or outstanding errors')
        if any(len(r['reason'].split()) > 45 for r in rows):
            raise ValueError('Prompt reason length exceeded')
        if sha(g.EVIDENCE) != settings['evidence_db_sha256']:
            raise ValueError('Frozen evidence database changed')
        pilot_path = g.ROOT / 'reports/genre_llm/metadata.json'
        if sha(pilot_path) != settings['pilot_predictions_sha256']:
            raise ValueError('Pilot labels changed')
        candidates = {}
        for p in json.loads(pilot_path.read_text()):
            candidates.setdefault(p['song_id'], []).append(p)
        attempts = [dict(r) for r in c.execute('SELECT * FROM attempts ORDER BY attempt_id')]
        malformed = 0
        rejected_rows = 0
        for a in attempts:
            folder = g.LOCAL / a['folder']
            manifest = g.saved_request(c, a)
            if manifest['model'] != settings['model'] or manifest['config'] != settings['config'] or manifest['prompt_version'] != g.PILOT_COMMIT:
                raise ValueError('Request model/config drift')
            ids = manifest['song_ids']
            inputs = [json.loads(c.execute('SELECT input_json FROM songs WHERE song_id=?', (sid,)).fetchone()[0]) for sid in ids]
            request = (folder / 'request.txt').read_bytes()
            if request != g.request_text(inputs).encode() or g.digest(request) != manifest['request_sha256']:
                raise ValueError('Request prompt/input drift')
            response = folder / 'response.json'
            if not response.exists():
                if a['status'] != 'error':
                    raise ValueError('Successful attempt missing response')
                continue
            if a['response_sha256'] and sha(response) != a['response_sha256']:
                raise ValueError('Response hash changed')
            try:
                obj = json.loads(response.read_text())
            except json.JSONDecodeError:
                malformed += 1
                continue
            valid = accepted_rows(obj, ids)
            try:
                g.check_predictions(obj, ids)
            except (ValueError, TypeError, KeyError):
                malformed += 1
                rejected_rows += len(obj.get('predictions', [])) - len(valid)
            events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
            if sum(e['type'] == 'turn.completed' for e in events) != 1:
                raise ValueError('Response without unique completed turn')
            for e in events:
                if 'item' in e and e['item']['type'] not in ('agent_message', 'reasoning'):
                    if e['item'] != {'id': e['item'].get('id'), 'type': 'error', 'message': 'Falling back from WebSockets to HTTPS transport. request timed out'}:
                        raise ValueError('Unexpected tool/item in inference')
            for p in valid:
                candidates.setdefault(p['song_id'], []).append(p)
        for row in rows:
            prediction = {k: json.loads(row[k]) if k == 'secondary_genres' else row[k] for k in FIELDS}
            if prediction not in candidates.get(row['song_id'], []):
                raise ValueError('Stored prediction lacks exact accepted response provenance')
        completion = json.loads((g.LOCAL / 'completion.json').read_text())
        if not completion['inference_complete'] or completion['summary']['status_counts'] != summary['status_counts']:
            raise ValueError('Completion marker disagrees')
        exported = [json.loads(line) for line in (g.LOCAL / 'song_genres.jsonl').read_text().splitlines()]
        if [r['song_id'] for r in exported] != [r['song_id'] for r in rows]:
            raise ValueError('Final export coverage differs')
        for ex, row in zip(exported, rows):
            if any(ex[k] != (json.loads(row[k]) if k == 'secondary_genres' else row[k]) for k in ex):
                raise ValueError('Final export differs from database')
        last = max(rows, key=lambda r: r['completed_at'])
        batch_counts = dict(c.execute('SELECT status,count(*) FROM batches GROUP BY status'))
        if batch_counts != {'completed': 2805}:
            raise ValueError('Incomplete batches')
    from month_end_catchup_audit import audit as corpus_audit
    corpus = corpus_audit()
    if (corpus['population'], corpus['final_usable'], corpus['final_all_42']) != (28041, 20981, 20979):
        raise ValueError('Corpus/classifier coverage changed')
    protected = json.loads((g.ROOT / 'data/experiments/genre_pilot/protected.json').read_text())
    if any(sha(g.ROOT / p) != expected for p, expected in protected.items()):
        raise ValueError('Protected file changed')
    if sha(g.DB) != before:
        raise ValueError('Genre database changed during read-only audit')
    with (OUT / 'review.csv').open() as handle:
        reviews = list(csv.DictReader(handle))
    quality = validate_review(rows, reviews)
    tests = (g.LOCAL / 'final_tests.log').read_text()
    if not tests.rstrip().endswith('OK'):
        raise ValueError('Full tests have not passed')
    result = dict(status='COMPLETE', target=28041, completed=28041, remaining=0, errors=0,
                  duplicate_song_ids=0, missing_song_ids=0, active_workers=0,
                  confidence=summary['confidence'], quality=quality, reviewed=len(reviews),
                  attempt_statuses=dict(Counter(a['status'] for a in attempts)), malformed_responses=malformed,
                  unaccepted_response_rows=rejected_rows, outstanding_malformed_responses=0,
                  last_classification={k:last[k] for k in ('song_id','title','artist','completed_at')},
                  completion_time=completion['summary']['as_of'],
                  exit_reason='Inference complete; all batches and final export reconciled. OS exit code was not retained.',
                  frozen_files=settings['frozen_files'], model=settings['model'], config=settings['config'],
                  protected_files=len(protected), protected_unchanged=True, genre_database_sha256=before,
                  corpus_validation={k: corpus[k] for k in ('status', 'population', 'final_usable', 'final_all_42')},
                  review_sha256=sha(OUT / 'review.csv'), tests_passed=int(re.search(r'Ran (\d+) tests', tests).group(1)),
                  genres=summary['genres'], period_genres=summary['period_genres'],
                  sample_confidence=dict(Counter(r['confidence'] for r in reviews)),
                  sample_periods=dict(Counter(r['period'] for r in reviews)),
                  sample_genres=dict(Counter(r['primary_genre'] for r in reviews)))
    g.dump(OUT / 'validation.json', result)
    lines = ['# Final genre audit', '', '**COMPLETE.** No active genre worker; no restart or reclassification performed.', '',
             'Target/completed: 28,041 / 28,041. Remaining: 0. Outstanding errors: 0. Duplicate/missing IDs: 0 / 0.', '',
             f"Last classification: {last['title']} — {last['artist']}, {last['completed_at']}. Completion marker: {result['completion_time']}.",
             'The marker, all 2,805 completed batches, log ending and complete local export agree. The operating-system exit code was not retained.', '',
             f"Attempts: {dict(result['attempt_statuses'])}. {malformed} malformed responses, {rejected_rows} unaccepted response rows; all affected songs later resolved. These historical failures are not outstanding song errors.",
             'The recovered attempt retains its old transport error. Private events confirm a WebSocket-to-HTTPS fallback; the capacity failure contains no completed response. No tool calls or alternate model/API path were accepted.', '',
             '## Confidence', '', '| Confidence | Count |', '|---|---:|']
    lines += [f'| {k} | {summary["confidence"][k]:,} |' for k in ('high','medium','low')]
    lines += ['', '## Genre distribution', '', 'Unique assets; denominator 28,041. Percentages are descriptive, not population-weighted trend estimates.', '', '| Genre | Count | Percent |', '|---|---:|---:|']
    for genre in g.TAXONOMY:
        n=summary['genres'][genre]['count'];lines.append(f'| {genre} | {n:,} | {100*n/28041:.2f}% |')
    periods=[r[2] for r in PERIODS]
    counts={(r['period'],r['primary_genre']):r['n'] for r in summary['period_genres']}
    lines += ['', '## Counts by first-chart period', '', 'Each asset is counted once by its first Billboard chart date, not release date or every later chart appearance. Zero cells are explicit. No historical interpretation.', '', '| Genre | '+' | '.join(periods)+' |', '|---|'+'---:|'*len(periods)]
    for genre in g.TAXONOMY:
        lines.append('| '+genre+' | '+' | '.join(str(counts.get((p,genre),0)) for p in periods)+' |')
    lines += ['| Total | '+' | '.join(str(sum(counts.get((p,g),0) for g in g.TAXONOMY)) for p in periods)+' |', '',
              '## Bounded qualitative review', '',
              f"Reviewed: 160. Plausible: {quality.get('plausible',0)}. Questionable: {quality.get('questionable',0)}. Clearly wrong: {quality.get('clearly wrong',0)}.", '',
              'The unchanged `genre-post-run-review-v1` selector takes two per available genre, 15 per confidence level, five per period, then hash-fills the union to 160. All 16 genres, three confidence levels and seven periods are covered. Exact coverage is in validation.json.', '',
              'Review was performed by the Codex assistant using exact identities, model reasons, retained evidence and targeted external checks. It is not an independent human/musicologist review or a listening study. Plausible means broadly defensible, not verified ground truth; questionable includes inadequate evidence and legitimate boundaries. This stratified diagnostic sample is not an accuracy estimate.', '',
              'The two clearly wrong primary choices are José Feliciano’s anthem as Other, despite its [folk arrangement](https://www.pbs.org/wgbh/americanexperience/features/woodstock-star-spangled-banner/), and Lil Wayne’s Knockout as Rap, despite a contemporary review describing its [power-pop/punk style](https://www.rapreviews.com/2010/02/lil-wayne-rebirth/). These are review judgments; production labels remain unchanged.', '',
              'Systemic concerns: artist identity and broad tags can override song-specific arrangements; scene categories compete with musical styles (including the two Jung Kook singles); novelty/anthem/soundtrack function can displace style; sparse older/recent identities encourage uncertain default labels. Pop/Rock, Latin/Rock, Jazz/Pop and alternative-R&B boundaries remain inconsistent. Secondary labels remain provisional. This sample cannot establish time-invariant or genre-invariant error rates.', '',
              'All 160 judgments and supporting notes are in [review.csv](genre_final_audit/review.csv). No individual production label was rewritten.', '',
              '## Validation', '',
              f"{result['tests_passed']} tests passed. SQLite integrity, exact population/batch/export coverage, all structured outputs, response provenance, frozen request bytes/model/config/taxonomy, 45-word prompt limit and protected hashes pass. {len(protected):,} protected files remain identical, including 21,693 lyric files, Billboard, metadata, both classifier databases and existing public datasets.", '',
              'Phase 1, the combined corpus audit and both production classifier validators passed. Classifier coverage remains 20,981 songs, including 20,979 with all 42 features. The original classifier validator requires `--allow-incomplete` for the two documented LyricLens exceptions; the strict combined corpus audit checks those exceptions explicitly. The catch-up validator requires its documented classifier virtual environment (system Python lacks torch). Initial invocations without those requirements failed; no model or data changes were needed. Logs are private. The 42-feature methodology is unchanged. The frozen model name is an alias rather than an immutable service checkpoint; request manifests record the requested configuration, not an independently attested server checkpoint.', '',
              'Repository artifact inspection found no historical/COVID trend analysis or final weekly/monthly master build. Existing descriptive quality reports and earlier monthly archive/experiments remain preserved. No such analysis or dataset construction was performed in this audit.', '',
              'Reproduce: `python3 src/genre_final_audit.py` after `python3 -m unittest discover -s tests -v > data/experiments/genre_production/final_tests.log 2>&1`. The script opens production SQLite read-only, validates the authored review against the deterministic sample, and regenerates this report and aggregate JSON.', '']
    dest=g.ROOT/'reports/genre_final_audit.md'
    tmp=dest.with_suffix('.md.tmp');tmp.write_text('\n'.join(lines));tmp.replace(dest)
    print(json.dumps({k:result[k] for k in ('status','completed','remaining','errors','confidence','quality','tests_passed','protected_unchanged')},indent=2))


if __name__ == '__main__':
    audit()
