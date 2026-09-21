"""Generate a lyric-free report from frozen pilot predictions and review notes."""
import json
from collections import Counter
from detoxify_diagnostics import joined, diagnostics, select_review
from detoxify_evaluation import LABELS, REPORTS, ROOT
from lyriclens_evaluation import read_csv, write_csv, PERIODS


def main():
    rows=joined();d=diagnostics(rows)
    run=json.loads((REPORTS/'detoxify_run.json').read_text())
    review=read_csv(REPORTS/'detoxify_review.csv')
    if {r['song_id'] for r in review}!={r['song_id'] for r in select_review(rows)}:raise ValueError('Review selection differs')
    lc=Counter(r['lyriclens_judgment'] for r in review);dc=Counter(r['detoxify_judgment'] for r in review)
    lines=['# Detoxify evaluation: same 200-song pilot','',
    '**Recommendation C: retain selected outputs from both models as complementary candidate features, not as a validated primary severity measure.** Detoxify obscene is a useful independent language benchmark; sexual_explicit offers a narrower sexual-content comparison. LyricLens addresses broader sexual themes, violence and substance use, but retains documented errors. Detoxify toxicity, threat and severe_toxicity should not replace these lyrical constructs. Neither model establishes a continuous severity scale.','',
    '## Model','',
    'English Detoxify **unbiased**, repository 0.5.3, pinned commit `d5376446b6accee5dd2d346f2d3050f9d8a69af1`; RoBERTa-base sequence classifier, 124,657,936 parameters. Official Apache-2.0 distribution; trained on the first two Jigsaw comment datasets, not lyrics. Upstream reports **93.74** on its composite toxicity/bias AUC benchmark, not accuracy or lyric performance. [Inspection, sources, label definitions, license and reproduction](../docs/detoxify_methodology.md).','',
    'Seven returned sigmoid confidence scores: toxicity, severe_toxicity, obscene, threat, insult, identity_attack, sexual_explicit. They are not calibrated severity probabilities. No substance score, CSI, MCR or combined hardness score is introduced.','',
    '## Scope and evidence','',
    '- **200/200 successful, zero failed/missing predictions** on the exact frozen LyricLens sample (180 stratified core plus 20 preselected sentinels). No new sample was selected.',
    '- [Predictions](detoxify_predictions.csv), [all raw logits/sigmoids](detoxify_raw_outputs.jsonl), [run provenance](detoxify_run.json), [artifact hashes](detoxify_artifacts.json), [full diagnostics](detoxify_diagnostics.json). Raw outputs include nine auxiliary identity heads for reproducibility only.',
    '- [50 deterministic qualitative reviews](detoxify_review.csv): all 20 sentinels, directional differences for five overlapping pairs, each Detoxify minimum/maximum, period midpoints, Spanish cases and deterministic supplementation. Selection is score-informed, so review counts are not accuracy estimates.',
    '- Existing accepted lyrics, all acquisition databases, the LyricLens pilot and public master remain unchanged. Only these 200 unique songs received Detoxify predictions; eight were replayed in separate input-sensitivity diagnostics.','',
    '## Score distributions: all 200','',
    'Sample standard deviation (n−1); quantiles use linear interpolation. Scientific notation preserves small nonzero values.','',
    '| Score | Min | Q05 | Q25 | Median | Mean | SD | Q75 | Q95 | Max | <.01 | >.99 |',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for k in LABELS:
        s=d['all_200']['distributions'][k]
        lines.append('| '+k+' | '+' | '.join(f'{s[x]:.5g}' for x in ('min','q05','q25','median','mean','sd','q75','q95','max'))+f" | {s['below_01']} | {s['above_99']} |")
    lines+=['','No outputs equal exactly zero or one. Threat (182/200 below .01) and severe_toxicity (181/200 below .01) are strongly compressed near zero. Sexual_explicit is below .01 for 149/200. Toxicity has three values above .99. This is not a failed model run: all logits are finite and match upstream sigmoid outputs. These sparse/confident responses still offer poor resolution for broad content severity.','',
    '### Highest and lowest identities','',
    'Full top/bottom three per label are in [the extremes table](detoxify_extremes.csv). These are model extremes, not rankings of actual harmfulness.','',
    '| Score | Minimum identity (score) | Maximum identity (score) |','|---|---|---|']
    extremes=[]
    for k in LABELS:
        ordered=sorted(rows,key=lambda r:(float(r[k]),r['song_id']))
        low,high=ordered[0],ordered[-1]
        def identity(r):return f"{r['title']} — {r['artist']} ({float(r[k]):.5g})".replace('|','/')
        lines.append(f'| {k} | {identity(low)} | {identity(high)} |')
        for side, group in [('lowest',ordered[:3]),('highest',list(reversed(ordered[-3:])) )]:
            for rank,r in enumerate(group,1):extremes.append(dict(score=k,side=side,rank=rank,song_id=r['song_id'],title=r['title'],artist=r['artist'],value=r[k]))
    write_csv(REPORTS/'detoxify_extremes.csv',extremes)
    lines+=['','## Comparison with LyricLens','',
    'Pearson compares numerical covariation; Spearman compares ranks with ties averaged. They are descriptive correlations, without significance tests. Different label definitions, calibration and tokenization mean neither agreement nor disagreement establishes correctness.','',
    '| LyricLens | Detoxify | Pearson, 200 | Spearman, 200 | Pearson, core 180 | Spearman, core 180 |','|---|---|---:|---:|---:|---:|']
    for a,b in zip(d['all_200']['correlations'],d['core_180']['correlations']):
        lines.append(f"| {a['lyriclens']} | {a['detoxify']} | {a['pearson']:.3f} | {a['spearman']:.3f} | {b['pearson']:.3f} | {b['spearman']:.3f} |")
    lines+=['',
    '- **Low agreement:** Rainbow Connection, Let It Be and What A Wonderful World are low in overlapping categories. **High agreement:** WAP, Closer and Anaconda contain direct sexual/profane material detected by both.',
    '- **LyricLens high, Detoxify low:** My Girl sexual .632 versus .001 suggests a LyricLens romance false positive. Imagine violence .995/language .993 versus Detoxify threat .006/obscene .001 reflects negation/context. Highwire violence .999 versus threat .004 instead reflects legitimate construct differences: narrated weapons/war are not directed threats.',
    '- **Detoxify high, LyricLens low:** Foolish Heart toxicity .916/insult .867 despite self-address and very low LyricLens scores is an obvious Detoxify construct error. He\'s A Liar has insult .808 but LyricLens language .002: accusation without profanity can explain that difference, rather than either model being universally wrong.',
    '- **Narrative violence:** Murder On My Mind has LyricLens violence .997 and Detoxify threat .022; even its tail-only threat is .043. Using threat as violence would miss this narrative. Severe_toxicity is also not a violence-intensity label.',
    '- **Sexual theme versus explicit wording:** Let\'s Get It On is .995 LyricLens sexual versus .011 Detoxify sexual_explicit. The narrower Detoxify target and comment domain explain why low scores cannot rule out sexual subject matter. Rosones is a clearer language-domain failure for both.',
    '', '## Qualitative review','',
    '| Focus-specific judgment | LyricLens | Detoxify |','|---|---:|---:|']
    for k in ('plausible','questionable','clearly_wrong'):lines.append(f'| {k} | {lc[k]} | {dc[k]} |')
    lines+=['',
    '**These are not accuracy estimates or a model leaderboard.** Review was unblinded, assistant-authored and deliberately enriched for disagreements. Twenty-six cases reuse earlier full-text review evidence; 24 received targeted context and lexical inspection rather than exhaustive semantic annotation. Each row states the category focus, rationale and evidence scope; judgments across different focuses are not directly comparable. No scores were edited.',
    '',
    'Detoxify\'s clear construct errors include Foolish Heart (self-address), Cry Just a Little (figurative heartbreak; threat .553), How Country Feels (courtship; threat .381), and Rosones (Spanish explicit content missed). LyricLens\'s clear errors in this selected set are My Girl and Rosones; its numerous questionable cases include romance/innuendo, mild language saturation and metaphor. This is compatible with useful features, not validated severity outcomes.',
    '', '## Domain and input sensitivity','',
    '- **Toxicity is not content severity:** profanity in consensual sexual material, storytelling and in-group dialogue can raise toxicity without an interpersonal attack. Identity_attack requires review of target/context; auxiliary identity scores are not hate indicators.',
    '- **Quoted speech/fictional narrators:** neither inference interface distinguishes singer, narrator, quotation or endorsement. This pilot does not independently isolate quotation effects. Narrative violence is visibly different from a directed-threat label.',
    '- **Historical language and slang:** romance/euphemism can be nearly certain sexual presence for LyricLens but near zero for Detoxify. English profanity is often detected, but Spanish Rosones is missed by both. Macarena also has language/version ambiguity. The small sample cannot establish equal sensitivity across eras, dialects or languages.',
    '- **Clean/version effects:** existing Smack That and Vigilante Shit texts are clean-looking/noisy relative to expectations from their titles or reputation. We evaluate the retained local text, not assumed lyrics from another release; no files were repaired or replaced.',
    '',
    f"**Truncation:** {d['truncation']['all_200']}/200 lyrics ({d['truncation']['core_180']}/180 core) exceed Detoxify's 512-token input, compared with 2/200 for LyricLens's differently preprocessed 1,024-token input. Detoxify always sees at most 510 content tokens. The unmatched input coverage is a major confound in comparing models.",
    '',
    '[Eight-song sensitivity results](detoxify_sensitivity.csv) preserve original replay, unique-line and final-510-token scores separately. All eight original replays agree within 1e-6. Because I Got High obscene changes .275 → .800 for the tail; Survivor .131 → .007. Removing repeated lines changes How Country Feels threat .381 → .158, while Foolish Heart insult remains high (.867 → .955). These probes change context as well as repetition/position, so they demonstrate input sensitivity without isolating a single causal mechanism. No alternative aggregation or preprocessing is approved here.',
    '',
    '| Score | Spearman with word count, core 180 |','|---|---:|']
    for k in LABELS:lines.append(f"| {k} | {d['core_180']['word_count_spearman'][k]:.3f} |")
    lines+=['','Positive length associations mix content, period, repetition and truncation; they are not estimates of length bias alone. A later validated chunking/context strategy would be needed before interpreting whole-song measures.',
    '', '## Broad-period diagnostic only','',
    'Means below use **only the 180-song stratified core**, excluding the 20 content-selected sentinels. Period is first Billboard appearance, not release date. Full medians and all-200/core distributions are in the diagnostics JSON. These tiny, unweighted strata are not historical indices and support no COVID/trend claim.','',
    '| Period | n | Truncated | Toxicity | Severe | Obscene | Identity attack | Insult | Threat | Sexual explicit |',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in PERIODS:
        g=d['period_core'][p]
        lines.append(f"| {p} | {g['n']} | {g['truncated']} | "+' | '.join(f"{g['means'][k]:.4f}" for k in LABELS)+' |')
    lines+=['',
    'The 1980s threat mean is strongly affected by the Cry Just a Little false positive; the 2010s similarly include How Country Feels. Truncation is 0/26 in the earliest core stratum but 15/25 in 2010–2019 and 13/25 in 2020–2026. Differences in observed period means can therefore reflect content mix, input length and model artifacts; this evaluation cannot disentangle them.',
    '', '## Performance','',
    f"Native Apple Silicon CPU, four threads, float32, batch size one: **{run['inference_seconds']:.2f} seconds for 200 songs**, mean **{run['seconds_per_song']:.4f} seconds/song** including tokenization/predict, plus {run['load_seconds']:.2f} seconds model initialization. Peak process RSS was **{run['peak_rss_bytes']/2**30:.2f} GiB** (includes loading and Python), on a 16-GiB machine.",
    '',
    f"Simple extrapolation to 19,372 songs: **{run['projected_19372_hours']*60:.1f} minutes CPU** for the same prefix-only method, excluding setup and other pipeline work. Sample length mix, thermal load and any future chunking can change that estimate. GPU/MPS was not benchmarked; no GPU speedup is assumed. Full-corpus computation appears practical on this machine, but scientific validity remains the constraint.",
    '',
    f"The checkpoint occupies 498,707,273 bytes (~476 MiB). Pilot prediction CSV plus all-logit JSONL occupies {(REPORTS/'detoxify_predictions.csv').stat().st_size+(REPORTS/'detoxify_raw_outputs.jsonl').stat().st_size:,} bytes; proportional full-corpus output would be about {((REPORTS/'detoxify_predictions.csv').stat().st_size+(REPORTS/'detoxify_raw_outputs.jsonl').stat().st_size)*19372/200/2**20:.1f} MiB, before indexing or extra diagnostics. No model files or lyrics are distributed.",
    '', '## Decision and next requirement','',
    '**C — selected complementary outputs.** Use Detoxify obscene as an independent language benchmark and sexual_explicit as a narrower comparison; retain LyricLens category scores only as experimental candidates for the broader constructs Detoxify lacks. Neither overall toxicity nor CSI/MCR should become the primary outcome. Before production, define a blinded human rubric for content presence, severity and context; evaluate truncation/language handling and category-specific validity against that rubric. This is a recommendation for the next decision, not implementation of a new classifier.',
    '',
    'Validation completed: **192 tests passed**; research database, public exports, all 19,372 lyric files, original LyricLens artifacts, Detoxify score reconciliation and deterministic diagnostic rebuilds passed. No lyrics, caches, databases, model files or credentials are staged for publication.',
    '',
    'Validation commands: `python3 -m unittest discover -s tests -v`, `python3 src/detoxify_evaluation.py validate`, `python3 src/detoxify_validate.py`, `python3 src/lyriclens_validate.py`, `python3 src/public_dataset.py validate`, and `python3 src/research.py validate`. Together, these validators check deterministic diagnostics/review/report regeneration, artifact and corpus integrity, raw-score reconciliation and public-output safety. Full-corpus classification and historical analysis have not started.','']
    (REPORTS/'detoxify_evaluation.md').write_text('\n'.join(lines))
    print('Generated Detoxify evaluation report and 42-row extremes table.')

if __name__=='__main__':main()
