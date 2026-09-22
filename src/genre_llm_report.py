"""Render the LLM pilot report from recorded predictions and separate review."""
import json
from genre_llm import ROOT, OUT

def report():
    s=json.loads((OUT/'summary.json').read_text());p=s['performance'];q=s['review'];c=s['confidence']
    v=json.loads((OUT/'validation.json').read_text())
    pct=lambda n,d:f'{100*n/d:.1f}%'
    text=f'''# LLM primary-genre pilot

## Decision

**A — Ready for a full pass producing model-derived primary labels**, retaining
confidence and treating secondary labels as provisional. This experiment concerns only the unchanged 300-song
genre pilot. No public dataset, classifier result, lyric, genre population or
historical analysis was changed. A forced primary is not evidence of accuracy.

## Model and reproducibility

Baseline A used **GPT-5.5** (`gpt-5.5`) through authenticated Codex CLI 0.155.1,
medium reasoning, on 2026-09-21 UTC. Each ten-song request started an isolated,
ephemeral session with no research conversation, no project instructions, and
shell/web/memory/multi-agent features disabled. No inference tool calls occurred. An input audit found performance/admin tags
on 18 songs; 13 affected metadata batches were rerun after removing those tags.
Two rebatching batches and one exact-repeat batch were also refreshed. Original
nonconforming attempts remain archived locally and are excluded from final results.
The exact [prompt](../docs/genre/llm/prompt.txt),
[schema](../docs/genre/llm/output.schema.json), [inputs](genre_llm/inputs.json),
[manifest](genre_llm/manifest.json) and [request hashes/usage](genre_llm/runs.json)
are saved. Raw requests/responses and transport events remain local.

There is no exposed temperature/seed setting, and the CLI returns no resolved
checkpoint identifier. The requested alias and CLI version are exact; claiming a
pinned underlying snapshot or perfect determinism would be incorrect. The
[model page](https://developers.openai.com/api/docs/models/gpt-5.5) lists an API
snapshot `gpt-5.5-2026-04-23` and December 2025 knowledge cutoff; that snapshot was
not explicitly requested in this CLI pilot. A future API migration requires an
explicitly versioned replay, not an assumption of equivalent behavior.
[Structured CLI operation](https://developers.openai.com/codex/noninteractive)
provides the interface used here, including standard harness instructions.

## Inputs

A: exact title, artist, first Billboard chart date and positive cached raw tags,
kept separate by provider and recording/artist level. Exact duplicate tag copies
are collapsed; maximum support and distinct entity count are supplied, not summed
votes. Unmapped genre tags remain available. Chart/rank/top-number and research-outcome
tag patterns are excluded under input-screen version 2. The sample's cached evidence contains no
release-level tags, so no album context was invented. The full original evidence
and provenance remain untouched. Chart date is explicitly not release date.

B: the same prompt but only identity and first chart date for 77 preselected songs
(11 per period). Neither arm receives content scores, popularity, earlier primary
genres, research outcomes or review lookups. Learned musical knowledge is allowed,
but reasons must distinguish it from supplied evidence. Inputs are not audio;
recording-specific style and obscure identities remain important limitations.

## Same 300-song comparison

| Method | Primary returned | High | Medium | Low | Ambiguous / insufficient |
|---|---:|---:|---:|---:|---|
| Refined tags | 90 | not comparable | not comparable | not comparable | 28 / 182 |
| LLM A | {s['assigned']} | {c.get('high',0)} | {c.get('medium',0)} | {c.get('low',0)} | forced primary; uncertainty retained in confidence/secondary/reason |

The LLM returns {s['genres'].get('Other',0)} Other labels. Other can mean either
outside-taxonomy style or insufficient identification under this prompt; those
meanings must not be treated as one homogeneous musical genre.

| Period | Songs | High | Medium | Low |
|---|---:|---:|---:|---:|
'''
    for period,r in s['periods'].items():
        t=r['confidence'];text+=f"| {period} | {r['n']} | {t.get('high',0)} | {t.get('medium',0)} | {t.get('low',0)} |\n"
    text+=f'''
These are sample diagnostics, not historical genre estimates. The pilot includes
63 challenge anchors and 237 stratified selections; confidence is self-reported,
not calibrated and not a measure of accuracy or population coverage.

## Qualitative review

Reviewed {q['n']} A predictions: **{q['counts'].get('plausible',0)} plausible,
{q['counts'].get('questionable',0)} questionable,
{q['counts'].get('clearly wrong',0)} clearly wrong**.
[Case-level review](genre_llm/review.csv) records each judgment and basis.
This is assistant qualitative inspection, including factual checks where needed,
**not an independently labeled human accuracy study**. Team review has not been
claimed; a [blank review template](genre_llm/review_template.csv) is provided.
The review deliberately includes all B cases, original challenge anchors, strong-tag disagreements, earlier
failure examples and all low-confidence A cases, then fills by hash to 140.
Three additional diagnostic cases surfaced during inspection. This is not a random accuracy sample.
Questionable includes unresolved evidence, not necessarily incorrect style.
External facts are review-only and never feed back into either baseline.

| A confidence | Plausible | Questionable | Clearly wrong |
|---|---:|---:|---:|
'''
    for c,r in q['by_confidence'].items():text+=f"| {c} | {r.get('plausible',0)} | {r.get('questionable',0)} | {r.get('clearly wrong',0)} |\n"
    text+='\n| Review period | Plausible | Questionable | Clearly wrong |\n|---|---:|---:|---:|\n'
    for period,r in q['by_period'].items():text+=f"| {period} | {r.get('plausible',0)} | {r.get('questionable',0)} | {r.get('clearly wrong',0)} |\n"
    text+=f'''
## Agreement and ablation

A agrees exactly with **{s['strong_primary_agree']}/{s['strong_primary_n']}
({pct(s['strong_primary_agree'],s['strong_primary_n'])})** refined strong primaries.
Where any strong direct mapped category exists, its primary falls in that set for
**{s['strong_set_agree']}/{s['strong_set_n']}
({pct(s['strong_set_agree'],s['strong_set_n'])})**. Those thresholds define a noisy
comparator, not ground truth. Disagreement may correct an overly generic tag.

A and B primary labels agree on **{s['identity_agree']}/{s['identity_n']}
({pct(s['identity_agree'],s['identity_n'])})** songs. Reviewed B predictions:
{q['identity_counts']}. Paired cases with tags: {s['identity_by_evidence']['tags']};
without tags: {s['identity_by_evidence']['no_tags']}. Differences on no-tag cases
cannot be attributed to tag information. Batch context and stochastic generation
also differ between arms; this is a useful check, not a controlled causal estimate
of tag benefit. Neither method's forced coverage establishes superiority.

## Stability

Byte-identical requests for 30 songs (three original batches) produced
**{s['exact_repeat_agree']}/{s['exact_repeat_n']}
({pct(s['exact_repeat_agree'],s['exact_repeat_n'])})** exact primary agreement.
A separate stratified 42-song rebatching repeat produced
**{s['repeat_agree']}/{s['repeat_n']}
({pct(s['repeat_agree'],s['repeat_n'])})**. Rebatching also tests context sensitivity;
only the first comparison isolates repeat calls with identical complete requests.
These are one-repeat checks, not guarantees across future model updates.

## Runtime, cost and scale

A took {p['metadata']['seconds']:.1f} summed request-seconds for 300 songs;
B {p['identity']['seconds']:.1f}s; rebatching {p['repeat']['seconds']:.1f}s;
exact repeats {p['exact_repeat']['seconds']:.1f}s. The entire pilot's wall span
was {p['elapsed_wall_seconds']/60:.1f} minutes, with up to three independent arms
running concurrently. No arm used multiple simultaneous batches. Superseded
input-screening attempts added {p['superseded_requests']['seconds']:.1f} request-seconds
across {p['superseded_requests']['batches']} batches; they are excluded from final
label statistics and the per-song throughput estimate.

The measured A rate projects to **{p['full_serial_hours']:.1f} serial hours** for
28,041 songs, excluding quota pauses/retries. Ten-song batches mean approximately
2,805 requests. Output JSON projects to about
{p['prediction_bytes_per_song']*28041/1e6:.1f} MB, excluding inputs/raw transport
logs. Larger batches could reduce overhead but require a new stability check.

A token usage: `{p['metadata']['tokens']}`. This run used ChatGPT/Codex access,
not an API key; no per-token invoice or monetary charge was available. At the
[documented GPT-5.5 API rates](https://developers.openai.com/api/docs/models/gpt-5.5)
of $5 input/$0.50 cached input/$30 output per million tokens, mechanically scaling
this CLI workload gives approximately **${p['full_api_observed_cache_usd_upper']:.0f}
with observed caching to ${p['full_api_uncached_usd_upper']:.0f} without input caching**.
This is an illustrative API-equivalent budget, not the cost of this subscription
run. It conservatively adds separately reported reasoning tokens to output even
if already included. A bare API request has different overhead and must be measured.

No pilot request hit a rate limit. Subscription quotas and an API account's limits
are different; available full-run capacity is not established by this pilot.
Use bounded concurrency and resumable per-batch persistence, respect retry-after,
and never replace accepted outputs silently. The API model page lists Batch
support, but migrating to that transport needs a replay and account-specific
pricing/limit check. No full-run process was started.

## Production representation

Keep `primary_genre`, `secondary_genres`, qualitative `genre_confidence`,
`genre_method`, `genre_model`, `genre_evidence_summary`, prompt/input hashes and
processing/review status, joined by song_id. Preserve raw provider evidence
separately. Uncertain classifications should remain explicitly filterable; Other
must retain its reason. These are model-derived classifications, not ground truth.
The taxonomy remains unchanged at 16 possible values. No content-score consensus,
public joins or historical estimates are produced.

## Validation and rebuild

See [commands and input rules](../docs/genre/llm/README.md).
`genre_llm_validate.py` verifies all IDs, enums, exact inputs/request hashes,
unaltered response hashes, no tool calls and exact-repeat request equivalence.
The prior genre integrity validation protects 21,706 files including 21,693 lyric
files, research/classifier databases, immutable source and all public exports.
All remain unchanged. **{v['tests_passed']} tests passed.** Artifact hashes accompany the
experiment; local raw logs are ignored by Git.
'''
    text+='\n## Primary label counts (pilot only)\n\n| Genre | Songs |\n|---|---:|\n'
    from genre_rules import TAXONOMY
    for genre in TAXONOMY:text+=f"| {genre} | {s['genres'].get(genre,0)} |\n"
    notes=ROOT/'docs/genre/llm/findings.md'
    if notes.exists():text+='\n'+notes.read_text()
    (ROOT/'reports/llm_genre_evaluation.md').write_text(text)

if __name__=='__main__':report()
