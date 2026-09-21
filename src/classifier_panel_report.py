"""Generate panel design/evaluation report without lyrics or period analysis."""
import json
import statistics
from classifier_panel import OUT,ROOT,REPORTS,MODELS,THEMES
from lyriclens_evaluation import read_csv

def main():
    runs={m:json.loads((OUT/(m+'_run.json')).read_text()) for m in MODELS}
    counts=json.loads((OUT/'diagnostic_counts.json').read_text())
    comparisons=[r for r in read_csv(OUT/'agreement.csv') if r['aggregation']=='token_weighted_mean' and r['sample']=='core_180']
    dist=[r for r in read_csv(OUT/'distributions.csv') if r['aggregation']=='token_weighted_mean' and r['sample']=='all_200']
    sensitivity=read_csv(OUT/'aggregation_sensitivity.csv')
    themes=json.loads(THEMES.read_text())['themes']
    total=sum(r['inference_seconds'] for r in runs.values());init=sum(r['load_seconds'] for r in runs.values())
    data_files=[p for p in OUT.iterdir() if p.name.endswith(('_songs.csv','_chunks.jsonl'))]
    size=sum(p.stat().st_size for p in data_files)
    lines=['# Five-classifier judge panel: design and 200-song test','',
    '**The five-model pilot is operational, but not yet approved for full-corpus classification.** All five judges evaluated the exact frozen 200 songs with deterministic whole-input chunking. Keep the individual outputs and aggregation alternatives. The immediate methodological blocker is BART\'s neutral-dominant high theme scores; validate neutral handling and label-specific aggregation with a blinded content/context review. BART memory must also be bounded before a long run. No consensus or hardness score was created.','',
    '## Classifiers and conceptual scope','',
    '[Complete specification, exact checkpoints, training data, licenses, limitations, concept mapping and rebuild commands](../docs/classifier_panel_specification.md). [Pinned file hashes](classifier_panel/artifacts.json).','',
    '| Judge | Input | Numerical outputs retained | Principal limitation |','|---|---|---|---|',
    '| LyricLens | English-normalized lyric; Longformer, 1,024 tokens/chunk | Four logits/sigmoids: sexual, violence, language, substance | Lossy normalization; saturation/metaphor errors; training-label provenance limits |',
    '| Detoxify unbiased | Original lyric; RoBERTa, 512 tokens/chunk | Seven main logits/sigmoids plus nine auxiliary outputs | Comment toxicity differs from lyrical content; threat is not narrated violence |',
    '| SamLowe GoEmotions | Original lyric; RoBERTa, 512 tokens/chunk | 28 emotion/neutral logits and independent sigmoids | Reddit emotions; rare labels and narrator/context ambiguity |',
    '| Cardiff multilingual sentiment | Mention/URL-normalized lyric; XLM-R, 512 tokens/chunk | Negative, neutral, positive logits and joint softmax | Tweet polarity, not harmfulness; uneven language transfer |',
    '| BART-large-MNLI | Lyric premise plus each theme hypothesis; BART, 1,024 total pair tokens | Three NLI logits/softmax per theme and independent two-class theme confidence | Prompt-dependent entailment, not supervised lyric-theme truth; English |',
    '',
    'The panel has **59 model-label outputs**, not 59 independent dimensions or five interchangeable raters. Concept families group sexual content, violence, explicit language, substance use, hostility/negative affect, emotion, sentiment and themes without equating their labels. All original outputs survive; no cross-model averaging is performed.',
    '', '## Frozen BART themes','',
    'Frozen in commit `88eb28b` before new panel inference. Template: `This song contains {}.`. `multi_label=True` semantics score every theme independently. [Versioned labels and rationale](../docs/classifier_panel_themes.json).','',
    '| Stable theme ID | Hypothesis label |','|---|---|']
    for t in themes:lines.append(f"| {t['id']} | {t['label']} |")
    lines+=['',
    'The themes come from the research scope, not historical results. Profanity was added for a third language-content judge; drug and alcohol themes remain separate. Changing wording or deleting a theme later requires a new version and validation, not selection for interesting time patterns.',
    '', '## Chunking and aggregation','',
    'Tokenize the complete model-specific input once; reserve special tokens and, for BART, the longest hypothesis. Partition into the minimum number of balanced contiguous chunks that fit. There is no overlap or dropped tail. Exact per-chunk token spans and input hashes make coverage auditable. Chunk boundaries can split syntax, and LyricLens normalization still discards some raw information; whole-token coverage is not proof of semantic completeness.',
    '',
    'For every label retain **mean, token-weighted mean, maximum and q90** separately. Weighted mean is a candidate for overall affect/polarity; MAX is a candidate for any-occurrence content but is vulnerable to one false positive and song length. q90 is not robust with only one or two chunks. No universal aggregation is finalized. MAX/q90 sentiment vectors are not probability distributions.',
    '', '## 200-song panel','',
    '| Model | Successful / failed | Content chunks | Songs with >1 chunk | Maximum chunks/song | Content tokens/chunk budget | Model inputs including themes |',
    '|---|---:|---:|---:|---:|---:|---:|']
    for m in MODELS:
        r=runs[m];c=counts['counts'][m]
        lines.append(f"| {m} | {r['successful']} / {r['failed']} | {c['chunks']} | {c['multichunk']} | {c['max_chunks']} | {r['fingerprint']['content_budget']} | {r['model_input_pairs']} |")
    lines+=['',
    'All 1,000 song/model dispositions are successful. Numerical chunk evidence, four summaries per label, processing metadata and run fingerprints are in [the experimental output directory](classifier_panel/). Token IDs, lyric text, checkpoints and caches are excluded. The 81,800-row public master and all 19,372 accepted lyric files remain unchanged.',
    '',
    '### Distributions and low-information outputs','',
    '[Full distributions](classifier_panel/distributions.csv) contain min, max, mean, median, sample SD, Q05/Q25/Q75/Q95 and floor/ceiling counts for all 59 labels × four aggregations, separately for the core 180 and all 200. [Highest/lowest identities](classifier_panel/extremes.csv) contain top/bottom three for every token-weighted label. Below are all-200 token-weighted summaries for the overlapping outputs, all sentiment outputs and selected emotions.','',
    '| Model / label | Mean | Median | Q95 | Min | Max | <.01 / 200 | >.99 / 200 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    chosen={'lyriclens':None,'detoxify':None,'sentiment':None,'emotion':{'anger','disgust','love','sadness','grief','pride','relief','neutral'},'bart':{'sexual','violence','profanity','drugs','alcohol','romance','distress'}}
    for r in dist:
        if chosen[r['model']] is None or r['label'] in chosen[r['model']]:
            lines.append('| '+r['model']+'.'+r['label']+' | '+' | '.join(f"{float(r[k]):.5g}" for k in ('mean','median','q95','min','max'))+f" | {r['below_01']} | {r['above_99']} |")
    floor=[r['model']+'.'+r['label'] for r in dist if int(r['below_01'])>=180]
    lines+=['',
    'At least 180/200 weighted scores are below .01 for: '+(', '.join(floor) if floor else 'none')+'. Keep these raw outputs, but do not treat numerical rank differences within a compressed floor as strong evidence. Sparsity alone is not proof that a label is useless or truly absent.',
    '',
    f"**BART neutral ambiguity:** {counts['bart_neutral_majority_pairs']:,} chunk/theme pairs have three-way neutral probability above .5; {counts['bart_neutral_majority_and_theme_over_half']:,} of these still have two-class theme confidence above .5. This follows the zero-shot ratio's omission of neutral, not lost data. Such responses cannot be treated as confident theme presence without further validation.",
    '',
    '[Aggregation sensitivity](classifier_panel/aggregation_sensitivity.csv) reports mean-versus-MAX rank correlations and changes. Largest average MAX increases (not cross-model scores):','',
    '| Model / label | Mean increase | Largest increase | Songs increasing >.1 | Mean–MAX Spearman |','|---|---:|---:|---:|---:|']
    for r in sorted(sensitivity,key=lambda r:float(r['mean_increase']),reverse=True)[:8]:
        lines.append(f"| {r['model']}.{r['label']} | {float(r['mean_increase']):.3f} | {float(r['largest_increase']):.3f} | {r['songs_increase_over_01']} | {float(r['mean_vs_max_spearman']):.3f} |")
    lines+=['', '## Agreement','',
    'Core 180 results below use token-weighted means and the same song IDs. [All 160 comparisons](classifier_panel/agreement.csv) also include the full 200 and all four aggregations. Percentiles are tied midranks on the stated reference sample. “High overlap” is the number shared by both top-quintile sets; Jaccard divides their intersection by their union. No significance tests or period summaries are calculated.','',
    '| Model-label pair | Pearson | Spearman | Mean absolute percentile gap | High overlap | High Jaccard | Opposite quintiles |','|---|---:|---:|---:|---:|---:|---:|']
    for r in comparisons:
        lines.append(f"| {r['model_a']}.{r['label_a']} / {r['model_b']}.{r['label_b']} | {float(r['pearson']):.3f} | {float(r['spearman']):.3f} | {float(r['mean_absolute_percentile_gap']):.3f} | {r['high_intersection']} | {float(r['high_jaccard']):.3f} | {r['opposite_quintiles']} |")
    lines+=['',
    '[Selected agreements/disagreements](classifier_panel/agreement_cases.csv) preserve raw scores, percentiles and song identities for 160 pair-specific selections. These are diagnostic selections, not independent ground truth. Rank normalization removes scale units but cannot repair domain mismatch, label inequivalence or a nearly constant output. The core/full-sample distinction also shows that percentile positions depend on the reference set.',
    '', '### Interpretation of cases','']
    notes_path=ROOT/'docs/classifier_panel_findings.md'
    if notes_path.exists():lines+=notes_path.read_text().splitlines()+['']
    else:lines+=['Case interpretation pending complete inference review.','']
    lines+=['## Retained outputs and future panel design','',
    'Retain all 59 raw model-label outputs, all chunk evidence and all four within-label summaries. Emotion and sentiment add distinct affective information; they are not substitutes for sexual/violent/substance content. Highly correlated language judgments may be redundant evidence rather than independent confirmation. Low-range rare emotions and threat/severe-toxicity outputs need reliability checks before influencing an outcome; no label is deleted based on this pilot.',
    '',
    'A future agreement representation could include separate per-judge empirical-CDF percentiles, a mean normalized rank and a dispersion statistic (SD/range/MAD), with judge count and missingness. These are **proposals only**: no consensus columns are created. Fit and freeze a suitable reference distribution rather than ranking within each era. Do not give missing judges zero votes or count related models as independent votes. Blinded labels are needed to assess reliability and any weights.',
    '',
    'Traditional inter-rater metrics are not automatically suitable: ICC assumes comparable interval measurements; kappa needs justified categories and depends on prevalence; concordance requires judges to rank a common construct. Pairwise rank correlation/quintile overlap are useful diagnostics but not confidence in truth.',
    '',
    'Eventual storage: a versioned song-score table keyed by song_id and run/version; a run registry with exact artifacts/settings; linked chunk outputs. After aggregation choices are approved, expose one selected version per song for a stable LEFT JOIN to the public master. Keep model-specific token/chunk counts, because a single cross-model token count is undefined. No production join or schema migration occurred.',
    '', '## Performance','',
    '| Model | Device / batch | Inference seconds | Seconds/song | Projected 19,372-song hours | Peak process RSS GiB | Peak MPS driver GiB |','|---|---|---:|---:|---:|---:|---:|']
    for m in MODELS:
        r=runs[m];f=r['fingerprint']
        lines.append(f"| {m} | {f['device']} / {f['batch_size']} | {r['inference_seconds']:.2f} | {r['seconds_per_song']:.3f} | {r['seconds_per_song']*19372/3600:.2f} | {r['peak_rss_bytes']/2**30:.2f} | {r['gpu_driver_bytes']/2**30:.2f} |")
    lines+=['',
    f"**Total measured model/preprocessing work: {total/60:.2f} minutes**, plus {init:.2f} seconds summed initialization. Sequential extrapolation: **{total/200*19372/3600:.2f} hours** for the full corpus with this CPU/MPS allocation, same length distribution and 17 themes. Setup, report generation, journal writes and interruptions are excluded; longer corpus inputs and thermal load can increase runtime. CPU-only full-panel time was not measured.",
    '',
    'The BART device benchmark used four theme pairs from the first sample song: warm CPU batches took about 1.05 s versus 0.239 s on MPS, with maximum logit difference about 1.1e-5. This small benchmark supports device selection, not a universal speed ratio. [Benchmark](classifier_panel/bart_device_benchmark.json). RSS and MPS driver allocations overlap on unified memory; do not add them as independent RAM requirements. Models ran sequentially on the 16-GiB machine.',
    '',
    f"Published raw chunk outputs and song-summary CSVs total **{size:,} bytes ({size/2**20:.2f} MiB)** for 200 songs. A proportional full-corpus estimate is **{size*19372/200/2**20:.1f} MiB**, plus journals/diagnostics. The five checkpoints total approximately 4.0 GiB locally; they are not committed. The measured speed makes the battery plausible locally, with BART dominating cost, but long-run memory stability is not established.",
    '', '## Recommendation and validation','',
    '**Do not run the full corpus yet.** First validate a neutral-aware BART interpretation against a blinded content/context rubric using the frozen themes; the current two-class ratios falsely look confident for neutral-dominant mild-song examples. Separately, bound BART MPS memory (for example, a small fixed set of padding shapes or bounded worker lifetimes, with score-equivalence checks): driver allocation reached 11.02 GiB and full-corpus stability is untested. Then approve label-specific aggregation using disagreement and long/non-English cases. Distinguish content presence, severity, narrator/endorsement and affect. Repeated evidence from similar models must not be mistaken for validated severity.',
    '',
    '**Validation completed:** 203 tests passed; 4,715 exact chunk/pair input hashes were independently reconstructed. All 198 single-chunk LyricLens and 135 single-chunk Detoxify cases reproduced the prior pilot within 1e-6. The research/public-data/corpus validators and two deterministic diagnostic rebuilds passed.',
    '',
    'Validation includes exact sample identity, input hashes after independent retokenization, full token coverage, all raw-logit activations, every song summary, previous-pilot single-chunk replays, artifact/version pins, deterministic diagnostics, output safety, the complete test suite and existing corpus/research/public-dataset validators. See [reproduction commands](../docs/classifier_panel_specification.md). No full-corpus classifier run, master modification, consensus/hardness score or longitudinal/COVID analysis was performed.','']
    (REPORTS/'classifier_panel_design.md').write_text('\n'.join(lines))
    print('Generated classifier panel design report.')

if __name__=='__main__':main()
