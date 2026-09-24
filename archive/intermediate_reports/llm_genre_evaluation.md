# LLM primary-genre pilot

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
The exact [prompt](../../docs/genre/llm/prompt.txt),
[schema](../../docs/genre/llm/output.schema.json), [inputs](../../reports/genre_llm/inputs.json),
[manifest](../../reports/genre_llm/manifest.json) and [request hashes/usage](../../reports/genre_llm/runs.json)
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
| LLM A | 300 | 217 | 65 | 18 | forced primary; uncertainty retained in confidence/secondary/reason |

The LLM returns 7 Other labels. Other can mean either
outside-taxonomy style or insufficient identification under this prompt; those
meanings must not be treated as one homogeneous musical genre.

| Period | Songs | High | Medium | Low |
|---|---:|---:|---:|---:|
| 1958–1969 | 43 | 26 | 11 | 6 |
| 1970s | 43 | 32 | 7 | 4 |
| 1980s | 43 | 30 | 10 | 3 |
| 1990s | 43 | 32 | 11 | 0 |
| 2000s | 43 | 35 | 8 | 0 |
| 2010–2019 | 43 | 35 | 8 | 0 |
| 2020–2026 | 42 | 27 | 10 | 5 |

These are sample diagnostics, not historical genre estimates. The pilot includes
63 challenge anchors and 237 stratified selections; confidence is self-reported,
not calibrated and not a measure of accuracy or population coverage.

## Qualitative review

Reviewed 143 A predictions: **117 plausible,
23 questionable,
3 clearly wrong**.
[Case-level review](../../reports/genre_llm/review.csv) records each judgment and basis.
This is assistant qualitative inspection, including factual checks where needed,
**not an independently labeled human accuracy study**. Team review has not been
claimed; a [blank review template](../../reports/genre_llm/review_template.csv) is provided.
The review deliberately includes all B cases, original challenge anchors, strong-tag disagreements, earlier
failure examples and all low-confidence A cases, then fills by hash to 140.
Three additional diagnostic cases surfaced during inspection. This is not a random accuracy sample.
Questionable includes unresolved evidence, not necessarily incorrect style.
External facts are review-only and never feed back into either baseline.

| A confidence | Plausible | Questionable | Clearly wrong |
|---|---:|---:|---:|
| high | 98 | 2 | 0 |
| low | 0 | 16 | 2 |
| medium | 19 | 5 | 1 |

| Review period | Plausible | Questionable | Clearly wrong |
|---|---:|---:|---:|
| 1958–1969 | 17 | 6 | 0 |
| 1970s | 16 | 4 | 1 |
| 1980s | 17 | 2 | 2 |
| 1990s | 19 | 0 | 0 |
| 2000s | 16 | 2 | 0 |
| 2010–2019 | 17 | 2 | 0 |
| 2020–2026 | 15 | 7 | 0 |

## Agreement and ablation

A agrees exactly with **83/90
(92.2%)** refined strong primaries.
Where any strong direct mapped category exists, its primary falls in that set for
**114/118
(96.6%)**. Those thresholds define a noisy
comparator, not ground truth. Disagreement may correct an overly generic tag.

A and B primary labels agree on **69/77
(89.6%)** songs. Reviewed B predictions:
{'plausible': 71, 'questionable': 6}. Paired cases with tags: {'agree': 37, 'n': 41};
without tags: {'agree': 32, 'n': 36}. Differences on no-tag cases
cannot be attributed to tag information. Batch context and stochastic generation
also differ between arms; this is a useful check, not a controlled causal estimate
of tag benefit. Neither method's forced coverage establishes superiority.

## Stability

Byte-identical requests for 30 songs (three original batches) produced
**30/30
(100.0%)** exact primary agreement.
A separate stratified 42-song rebatching repeat produced
**41/42
(97.6%)**. Rebatching also tests context sensitivity;
only the first comparison isolates repeat calls with identical complete requests.
These are one-repeat checks, not guarantees across future model updates.

## Runtime, cost and scale

A took 661.0 summed request-seconds for 300 songs;
B 170.7s; rebatching 97.7s;
exact repeats 61.7s. The entire pilot's wall span
was 25.8 minutes, with up to three independent arms
running concurrently. No arm used multiple simultaneous batches. Superseded
input-screening attempts added 327.5 request-seconds
across 16 batches; they are excluded from final
label statistics and the per-song throughput estimate.

The measured A rate projects to **17.2 serial hours** for
28,041 songs, excluding quota pauses/retries. Ten-song batches mean approximately
2,805 requests. Output JSON projects to about
10.5 MB, excluding inputs/raw transport
logs. Larger batches could reduce overhead but require a new stability check.

A token usage: `{'cached_input_tokens': 179712, 'input_tokens': 372930, 'output_tokens': 30539, 'reasoning_output_tokens': 1773}`. This run used ChatGPT/Codex access,
not an API key; no per-token invoice or monetary charge was available. At the
[documented GPT-5.5 API rates](https://developers.openai.com/api/docs/models/gpt-5.5)
of $5 input/$0.50 cached input/$30 output per million tokens, mechanically scaling
this CLI workload gives approximately **$189
with observed caching to $265 without input caching**.
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

See [commands and input rules](../../docs/genre/llm/README.md).
`genre_llm_validate.py` verifies all IDs, enums, exact inputs/request hashes,
unaltered response hashes, no tool calls and exact-repeat request equivalence.
The prior genre integrity validation protects 21,706 files including 21,693 lyric
files, research/classifier databases, immutable source and all public exports.
All remain unchanged. **296 tests passed.** Artifact hashes accompany the
experiment; local raw logs are ignored by Git.

## Primary label counts (pilot only)

| Genre | Songs |
|---|---:|
| Pop | 72 |
| Rock | 42 |
| Hip-Hop / Rap | 42 |
| R&B / Soul | 52 |
| Country | 25 |
| Latin | 8 |
| Electronic / Dance | 15 |
| Alternative / Indie | 10 |
| Metal | 2 |
| Folk / Singer-Songwriter | 5 |
| Jazz / Blues | 7 |
| Reggae / Dancehall | 2 |
| Gospel / Christian | 4 |
| K-Pop | 3 |
| Afrobeats / African Pop | 4 |
| Other | 7 |

## What the disagreements show

All seven disagreements with the refined strong primary rule were inspected:
Elvis's *Can't Help Falling in Love* (Rock → Pop), Mel Carter's *Hold Me, Thrill
Me, Kiss Me* (Soul → Pop), England Dan & John Ford Coley's *What Can I Do With
This Broken Heart* (Rock → Pop), Chaka Khan's *I Feel for You* (Pop → Soul),
Ricky Martin's *Livin' La Vida Loca* (Pop → Latin), Marshmello/CHVRCHES's *Here
With Me* (Pop → Dance), and Olivia Rodrigo's *Good 4 U* (Pop → Rock). The first
three are defensible broad-boundary choices; the others make useful style-specific
corrections. [Chaka Khan's R&B Grammy recognition](https://www.grammy.com/video/27th-annual-grammy-awards-best-rb-vocal-performance-female/)
is external review support, not new classifier input.

The LLM also recovers Silk's *Hooked on You*, YNW Melly's *Murder on My Mind*,
Childish Gambino's *Redbone*, and Wizkid's *Essence* without blindly following
isolated Pop, Rap or Dance tags. These were known failure cases from previous
reviews, not newly selected input examples inserted into the prompt.

Two clear errors were low-confidence Other assignments for *Baby Face*
(Wing and a Prayer) and *Black Kisses Never Make You Blue* (Curtie & the Boom Box).
A [contemporary disco review](https://jameshamiltonsdiscopage.com/1975/12/13/december-13-1975/)
establishes the former recording's dance context; a
[recording-specific discography](https://www.allbutforgottenoldies.net/bands-and-artists/info.php?id=curtie-and-the-boombox)
describes the latter's techno-pop sound. Other here is failed recognition rather
than a genuine musical category. The third clear primary error was Sweet Sensation’s *Sincerely Yours*, assigned
R&B/Soul at medium confidence rather than its defining
[freestyle dance identity](https://freestylemusic.org/sincerely-yours-sweet-sensation/).
All labels remain unchanged.

The paired A review was 68 plausible / 7 questionable / 2 clearly wrong, compared
with B's 71 / 6 / 0. All 77 paired cases were reviewed. Do not conclude that tags
improved quality: four of eight primary disagreements had no tags at all. The
empty evidence key and different batch composition can also condition output.
The 30/30 exact and 41/42 rebatching repeats show substantial stability for those
particular samples, not invariance to every prompt change. Steelheart’s *I’ll Never
Let You Go* changed between Rock and Metal under rebatching.

Soul/country (*I Can't Stop Loving You*) and Latin/jazz (*Viva Tirado*) are
legitimate crossover differences. Both final arms agree on Rap for *911*, while
its Soul secondary preserves a real crossover. *Hangover* exposes K-pop scene
versus EDM/hip-hop style: [contemporary reporting](https://www.koreajoongangdaily.com/korea/psy-and-snoop-dog-are-hungover/10083574)
recognizes its hip-hop character. *Geronimo* supports both pop and indie-pop;
the [band's own description](https://wearesheppard.com/pages/about-us) uses Pop.
These are not automatically misclassifications.

High confidence sometimes overstates a difficult boundary: generic Rock for
Linkin Park's *In the End* and Pop for Drake's *One Dance*. *Hangover* is medium
confidence in the final screened-input run.
*One Dance* has [specific dancehall/Afropop/UK-funky influences](https://pitchfork.com/reviews/tracks/18160-drake-one-dance-ft-wizkid-and-kyla/).
The unfamiliar *Sugar on My Tongue* illustrates an artist-based Rap fallback
that underrepresents [its dance/electro-funk direction](https://www.revolt.tv/article/tyler-the-creator-drops-provocative-sugar-on-my-tongue-video).
Its low confidence is useful, but does not repair the label.

Secondary genres are less defensible than the primary counts suggest. For example,
Dance on Debbie Gibson's ballad *Lost in Your Eyes*, Rock on *My Heart Will Go On*,
and Dance on *Feels So Good* are weakly justified. These fields should remain
provisional model suggestions, not independently validated song-level memberships.
The 143-case counts assess primary assignments; notes explicitly flag some
secondary problems, but no exhaustive secondary-label accuracy claim is made.

Older unfamiliar recordings and very recent titles carry more uncertainty than
familiar catalog tracks. Genre-specific styles versus market/scene categories
(K-pop, Latin, African Pop, Christian) remain an interpretive limitation of the
frozen taxonomy. No taxonomy values were changed. These diagnostics cannot
establish time-invariant error rates or unbiased future genre trajectories.

## Recommendation: A — ready for full LLM primary-genre classification

The main objective is a broad, model-derived **primary** feature. The pilot offers
substantially more usable judgments than 90 tag-only primaries, with strong tag
agreement and low observed clearly-wrong counts, while exposing uncertainty.
This supports a production pass with the current method; it does not validate
all secondary labels or make the results objective truth. Team review of the
provided template would strengthen validation, particularly for obscure songs.

Freeze the existing prompt/schema unchanged, requested `gpt-5.5` model and CLI
0.155.1, medium reasoning, ten-song batches, input-screen version 2 excluding performance/outcome tags,
exact identity/first chart date plus positive raw genre evidence grouped by provider/level/label, maximum support and
entity count. Keep recording/release/artist levels separate when scaling; no
previous assignments, chart-performance values, lyrics or content scores enter
inputs. Preserve raw responses, input/prompt/model/interface versions and all
confidence/reason fields. Do not silently promote low-confidence Other into a
known style. Keep secondary labels explicitly provisional. The model alias is a
recorded reproducibility limitation, not a pinned checkpoint guarantee.

Production engineering should freeze all 28,041 inputs and batch membership before
requests, use an incremental per-song/batch result store, skip completed work,
record failures separately, and respect account quotas. This pilot deliberately
provides no full-population runner. Moving to a pinned API snapshot or another
interface requires a small equivalence replay before adopting that configuration.
No production run has started and no public dataset has changed.
