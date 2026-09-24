# LLM genre pilot

This is a bounded experiment on the unchanged `reports/genre/sample.csv` (300
identities). No full-population command is provided. All three earlier genre
archive/experiments and the public datasets remain separate.

## Inputs and inference

`python3 src/genre_llm.py prepare` freezes the exact input array, sample/evidence
hashes, model request, CLI version, settings and preselected subsets. The original
raw evidence/provenance remains in the local genre pilot archive. The public
`reports/genre_llm/inputs.json` is the exact evidence supplied to baseline A:
identity, first chart date, positive raw tags grouped by provider, semantic level
and exact label, with maximum support and distinct entity count. Duplicate cache
copies do not add votes. No mapping to our taxonomy is applied to the input.
Qualified/deprecated Wikidata statements, nonpositive tags and raw tags matching
chart/rank/top-number or research-outcome terms are omitted. The exact exclusion
pattern is versioned in `genre_llm.py`; genre aliases are not mapped before inference. There is no lyric text or prior primary label.
The frozen sample's evidence has recording and artist tags, not release tags;
first chart date supplies date context and is never described as release date.

Baseline B supplies only song_id, exact title/artist and first chart date. Its 77
songs are chosen by hash within period, 11 per period. The rebatching repeat has
42 songs, six per period. The additional exact repeat uses original batches 0,
12 and 25 (30 songs) with byte-identical request text and the same batch context.
All subset rules are independent of predictions. Metadata batches follow the
frozen sample order in groups of ten.

`prompt.txt` and `output.schema.json` define the complete task-specific prompt and
response contract. Inference uses the authenticated Codex CLI, `gpt-5.5`, medium
reasoning, schema-constrained JSON, an empty temporary working directory, ignored
user config/rules, no project instructions, disabled shell/web/memory/multi-agent
features, and a fresh ephemeral session per batch. The CLI still supplies its
standard model/system instructions; this is not a bare API call. No conversation
from this research session is supplied. Event validation rejects tool use.
Temperature/seed are not exposed here; medium reasoning is not temperature zero.
The requested model alias is recorded, but this interface does not return a
resolved immutable checkpoint. Exact future reproduction is not guaranteed.

```sh
python3 src/genre_llm.py prepare
python3 src/genre_llm.py metadata
python3 src/genre_llm.py identity
python3 src/genre_llm.py repeat
python3 src/genre_llm.py exact_repeat
python3 src/genre_llm_analysis.py
python3 -m unittest discover -s tests -v > data/experiments/genre_llm/tests.log 2>&1
python3 src/genre_validate.py > data/experiments/genre_llm/protected_validation.log
python3 src/genre_llm_validate.py
python3 src/genre_llm_report.py
```

Completed requests are reused. Incomplete requests stop for inspection rather
than silently replacing a response. Exact prompts, raw events/responses, dates,
usage and timings stay under ignored `data/experiments/genre_llm/`. Exported
predictions preserve the model's decisions unchanged. The analysis script only
compares outputs and regenerates diagnostics/review selection.

## Review and interpretation

Review selection includes all 77 identity-baseline cases, every low-confidence
metadata prediction, all strong-tag disagreements, the original challenge anchors
and two earlier failure examples (Chaka Khan/Silk), then hash-fills to at
least 140. Three additional diagnostic cases (Sweet Sensation, Blake Lewis and Michael Marcagi)
surfaced during inspection are included separately after that selection. This deliberately difficult review is qualitative, not a random
accuracy estimate. Review notes are explicit observations separate from generated
model outputs. External review evidence must never be added to frozen inputs.
An assistant's factual/qualitative inspection is not an independent human gold
standard; team review remains valuable. The generated blank template supports it.

Genre is model-derived, with semantic overlap among cultural-market categories
and musical styles. Retain primary, secondary, confidence, method, requested model,
prompt/input hashes and reason; preserve raw evidence independently. High confidence
is not a calibrated probability. An Other label from insufficient identity must
not be treated as a coherent musical genre. No primary labels are approved for
production merely because the schema forces 100% assignment.

## Input screening correction

A pre-publication audit found chart-performance/admin labels embedded in raw tags
for 18 songs (including `billboard no 1` and `top 40`). These are inappropriate
judge inputs. Input-screen version 2 removes them. Thirteen metadata batches
(130 predictions), two rebatching batches and one exact-repeat batch were rerun
in fresh sessions; unchanged requests and the identity-only baseline were reused.
The original inputs/results/reviews are preserved under ignored
`data/experiments/genre_llm/pre_input_screen_v1/`, not used as final results.
No prompt or taxonomy was tuned from review findings. Regression coverage checks
that performance/outcome tags cannot enter inputs, while original title/artist
strings remain unchanged. Review judgments are reconciled to the final responses.
