"""Descriptive pilot diagnostics only; no historical hypothesis tests or inference."""
import csv
import json
import math
from pathlib import Path
import statistics
from lyriclens_evaluation import ROOT,WORK,REPORTS,PERIODS,SCORE_NAMES,read_csv,write_csv,sha

SCORES=SCORE_NAMES+('CSI','app_CSI')

def quantile(values,p):
    values=sorted(values)
    if not values or not 0<=p<=1:raise ValueError('Invalid quantile')
    x=(len(values)-1)*p;i=int(x);j=min(i+1,len(values)-1)
    return values[i]+(values[j]-values[i])*(x-i)


def summary(values):
    return dict(n=len(values),min=min(values),max=max(values),mean=statistics.mean(values),
        median=statistics.median(values),sd=statistics.stdev(values),
        q05=quantile(values,.05),q25=quantile(values,.25),q75=quantile(values,.75),q95=quantile(values,.95),
        zero=sum(x==0 for x in values),one=sum(x==1 for x in values),
        below_01=sum(x<.01 for x in values),above_99=sum(x>.99 for x in values))


def ranks(values):
    result=[0.0]*len(values);order=sorted(range(len(values)),key=lambda i:values[i]);i=0
    while i<len(order):
        j=i+1
        while j<len(order) and values[order[j]]==values[order[i]]:j+=1
        for k in range(i,j):result[order[k]]=(i+j-1)/2+1
        i=j
    return result


def spearman(xs,ys):
    xs=ranks(xs);ys=ranks(ys);a=statistics.mean(xs);b=statistics.mean(ys)
    den=math.sqrt(sum((x-a)**2 for x in xs)*sum((y-b)**2 for y in ys))
    return sum((x-a)*(y-b) for x,y in zip(xs,ys))/den if den else None


def select_review(rows):
    """Sentinels, category extremes, CSI low/middle/high, and every period, plus two language/version checks."""
    result={}
    def add(row,reason):
        sid=row['song_id']
        if sid not in result:result[sid]=dict(row,review_selection=reason)
        else:result[sid]['review_selection']+='; '+reason
    for r in rows:
        if r['sample_component']!='stratified_core':add(r,r['sample_component'])
    for score in SCORE_NAMES:
        ordered=sorted(rows,key=lambda r:(float(r[score]),r['song_id']))
        add(ordered[0],score+' minimum');add(ordered[-1],score+' maximum')
    ordered=sorted(rows,key=lambda r:(float(r['CSI']),r['song_id']))
    for i in (0,1,99,100,198,199):add(ordered[i],'CSI low/middle/high')
    for p in PERIODS:
        group=[r for r in ordered if r['period']==p];add(group[len(group)//2],'period midpoint')
    for r in sorted(rows,key=lambda r:(abs(float(r['CSI'])-25),r['song_id'])):
        if len(result)>=45:break
        add(r,'intermediate CSI')
    if len(result)!=45:raise ValueError('Unexpected base review size')
    for row in rows:
        if (row['title'],row['artist']) in {('Rosones','Tito Double P'),('Macarena','Los Del Rio')}:
            add(row,'Spanish text / language-version diagnostic')
    if len(result)!=47:raise ValueError('Missing language diagnostic cases')
    return list(result.values())


def write_report(rows,data):
    from collections import Counter
    run=json.loads((WORK/'run_provenance.json').read_text())
    benchmark=json.loads((WORK/'benchmark.json').read_text())
    annotations=json.loads((ROOT/'docs/lyriclens_review_notes.json').read_text())
    review=select_review(rows)
    if set(annotations['annotations'])!={r['song_id'] for r in review}:raise ValueError('Review annotations do not match selection')
    for r in review:r.update(annotations['annotations'][r['song_id']])
    write_csv(REPORTS/'lyriclens_review.csv',review)
    counts=Counter(r['verdict'] for r in review)
    lines=['# LyricLens evaluation: 200-song pilot','',
      '**Recommendation C: consider raw category probabilities only as one candidate feature set alongside a separately validated model. Do not adopt CSI/MCR as the project outcome or proceed to full-corpus scoring on this evidence.**','',
      'The model is fast and often detects obvious content, but confidence in category presence is not continuous severity. Figurative language and ordinary romance produce clear errors; mild references can saturate scores. A blinded human rubric and an independent severity/context measure are needed before a production decision. This pilot does not establish historical or COVID effects.','',
      '[Inspection, licensing, output definitions, limitations, and reproduction commands](../docs/lyriclens_methodology.md). Full-paper access was blocked; the accessible abstract, complete repository, and checkpoint metadata were inspected.','',
      '## Scope and provenance','',
      f"- 200/200 successful predictions; zero missing/failed predictions and {run['preprocessing_fallbacks']} preprocessing fallbacks.",
      '- 180 stratified diagnostic songs plus 20 preselected sentinels; 200 unique identities, no new corpus acquisition.',
      '- 47 qualitative read-throughs by the assistant, not an independent human-labelled test set.',
      '- Git revision `'+run['model_commit']+'`; weights SHA-256 `'+rows[0]['model_sha256']+'`.',
      '- [Sample](lyriclens_sample.csv), [experimental predictions](lyriclens_predictions.csv), [review decisions](lyriclens_review.csv), [artifact provenance](lyriclens_artifacts.json), [run provenance](lyriclens_run.json), [CPU/MPS replay](lyriclens_benchmark.json). Lyrics and model files are excluded.',
      '- Raw logits, probabilities, and complete app outputs remain in ignored local JSONL; their SHA-256 is `'+run['raw_outputs_sha256']+'`.','',
      '## Score distributions','',
      'Category scores are raw sigmoid values in [0,1]. CSI is the README formula (100 times their mean); app_CSI is the actual app formula after clipping/rescaling. SD uses n−1; quantiles use linear interpolation. Neither CSI is a trained severity output.','',
      '| Score (all 200) | Min | P05 | P25 | Median | Mean | SD | P75 | P95 | Max |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for score in SCORES:
        v=data['all_200'][score];lines.append('| '+score+' | '+' | '.join(f"{v[k]:.6f}" for k in ('min','q05','q25','median','mean','sd','q75','q95','max'))+' |')
    lines+=['','| Raw category | Below 0.01 | Above 0.99 |','|---|---:|---:|']
    for score in SCORE_NAMES:
        v=data['all_200'][score];lines.append(f"| {score} | {v['below_01']}/200 | {v['above_99']}/200 |")
    lines+=['','No raw probability equals exactly zero or one, but the tails are heavily saturated. '
        f"The app transform makes CSI exactly zero for {data['all_200']['app_CSI']['zero']}/200 songs, discarding real differences below its threshold. "
        'MCR counts: '+', '.join(f'{k} {v}' for k,v in data['mcr'].items())+'.',
        '', 'The 180-song core has mean raw CSI '+f"{data['core_180']['CSI']['mean']:.3f}"+
        ' (all 200: '+f"{data['all_200']['CSI']['mean']:.3f}"+'). Sentinel selection therefore affects the combined distribution; neither is a weighted corpus estimate.','',
        '## Highest and lowest identities','',
        'Extremes include sentinels and are diagnostic examples, not population rankings.','',
        '| Score | End | Song — artist | Value |','|---|---|---|---:|']
    for score in SCORE_NAMES+('CSI',):
        for end in ('lowest','highest'):
            for r in data['extremes'][score][end]:
                identity=(r['title']+' — '+r['artist']).replace('|','/')
                lines.append(f"| {score} | {end} | {identity} | {float(r[score]):.6f} |")
    lines+=['','## Qualitative review','',
        f"Of 47 selected cases, {counts['correct']} were broadly plausible category-presence detections, {counts['questionable']} were questionable, and {counts['clearly_wrong']} had clear face-validity failures. "
        'This outcome-selected review is not an accuracy estimate. Correct presence can still imply a misleading severity or adult rating. Scores were not adjusted.','',
        'Examples of the distinction: a beer mention in *If I Were A Boy*, a cigarette in *Lipstick Traces*, and mild profanity in *Keep Me In Mind* trigger near-one probabilities. These observations support detection, not a claim of extreme severity. Antiwar discussion in *Highwire* and *What Is Truth* is detected without representing stance. *Imagine* raises both violence and language scores near one despite negation/peace and a literal religious reference.','',
        '*My Girl*, *Georgy Girl*, and *Fading Away* have unsupported sexual-content responses for the intended explicitness measurement. *River Deep – Mountain High* has a clear figurative-height/substance error. *Smack That* also raises a separate clean/transcription-quality concern; the local text was preserved unchanged.','',
        '| Song — artist | Assessment | Evidence summary (no lyric excerpts) |','|---|---|---|']
    for r in review:
        identity=(r['title']+' — '+r['artist']).replace('|','/')
        note=(r['note']+' '+r['text_quality_note']).strip().replace('|','/')
        lines.append(f"| {identity} | {r['verdict']} | {note} |")
    lines+=['','## Temporal and length diagnostics — not a historical analysis','',
        'Means below use only the stratified core; periods are first chart appearance. These differences cannot distinguish actual content mix, sample selection, length, language style, or model error. No COVID breakpoint, hypothesis test, or causal conclusion was applied.','',
        '| Period | n | Sexual | Violence | Language | Substance | Raw CSI | App CSI |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for p,v in data['period_core'].items():
        lines.append(f"| {p} | {v['n']} | "+' | '.join(f'{v[k]:.3f}' for k in SCORES)+' |')
    lines+=['','Core Spearman correlations with raw lyric word count: '+', '.join(f'{k} {v:.3f}' for k,v in data['length_core'].items())+'.',
        '',f"{data['truncated']}/200 inputs exceeded the app's 1,024-token limit: "+
        ', '.join(r['title']+' ('+r['token_count']+' tokens)' for r in rows if r['truncated']=='1')+
        '. Prefix-only processing can miss later content; none of the supplied texts were shortened on disk.',
        '', 'Modern slang is sometimes recognized (explicit drug/sex references in the sentinels), but the patois case *Not Nice* remains ambiguous. This is not a slang-robustness benchmark. Two additional language checks expanded the review to 47: Spanish *Rosones* has clear sexual/profane wording but language probability only 0.050, while *Macarena* raises Spanish/remix-version and repetition/truncation questions. Historical false positives in romance/metaphor, modern contextual errors, and loss of censored/non-English tokens justify a dedicated invariance check. No paired clean/explicit versions were rescored; low language scores apply to the supplied text only.','',
        '## Measured performance','']
    mean=data['timing']['mean'];gpu=statistics.mean(benchmark['devices']['mps']['forward_seconds']) if 'forward_seconds' in benchmark['devices'].get('mps',{}) else None
    lines += [f"CPU: native arm64 Python 3.11.8, PyTorch 2.7.1, four threads, float32, one 1,024-token padded input per forward pass. The 200 input runs took {run['inference_seconds']:.3f} seconds: mean {mean:.3f} s/song, median {data['timing']['median']:.3f}, P95 {data['timing']['q95']:.3f}. These timings include preprocessing and diagnostic token counting; model/tokenizer loading took {run['load_seconds']:.3f} seconds separately.",
        '', f"Linear estimate for 19,372 songs: **{mean*19372/3600:.2f} CPU hours**, plus loading/I/O and possible thermal/load variation. This is an estimate; the full corpus was not run.",
        '', f"CPU peak process RSS was {run['peak_rss_bytes']:,} bytes ({run['peak_rss_bytes']/1024**3:.2f} GiB) on this 16 GiB Mac. This is process RSS, not a general minimum-RAM guarantee. Inference weights occupy 594,684,336 bytes; seven downloaded inference/evaluation artifacts total "+f"{sum(p.stat().st_size for p in (WORK/'model').iterdir()):,} bytes. The isolated environment and NLTK resources need additional storage.",
        '', f"Five length-spread pilot inputs were replayed: CPU predictions matched the first run exactly (max probability difference {benchmark['cpu_repeat_max_delta']})."]
    if gpu is not None:
        lines += ['',f"Apple MPS forward-only mean was {gpu:.3f} s/song after a {benchmark['devices']['mps']['warmup_seconds']:.3f}-second warm-up. A forward-only extrapolation is {gpu*19372/3600:.2f} hours; preprocessing, transfers and deployment overhead are additional. CPU/MPS maximum probability difference was {benchmark['max_probability_delta']:.8f}. The upstream app selects CUDA or CPU, not MPS: this was a separate diagnostic device adapter, not the canonical pilot or a production GPU implementation. No CUDA GPU is available."]
    rawsize=(WORK/'raw_predictions.jsonl').stat().st_size;csvsize=(REPORTS/'lyriclens_predictions.csv').stat().st_size
    lines += ['',f"Experimental CSV: {csvsize:,} bytes; raw JSONL: {rawsize:,} bytes for 200 songs. Linear output-storage estimate for 19,372 songs is {(csvsize+rawsize)*19372/200/1024**2:.1f} MiB for both, excluding models and lyrics. Full-corpus inference is technically practical on this machine; measurement validity is the limiting issue.",
        '', '## Integrity and validation', '',
        'The dedicated validator reconciles all raw outputs and CSV scores, checks finite probabilities and label mapping, recomputes both CSI formulas, verifies sample/lyric/model hashes, confirms corpus and public-export fingerprints, and checks that reviews cover exactly their deterministic selection. The full unittest suite passed 184 tests; the standard research-database and dedicated pilot validations passed. See the reproduction commands for reruns. No accepted lyrics, research tables, or public dataset columns were changed.',
        '', 'Before any full-corpus decision: obtain the full paper and label/split documentation; define and independently annotate the intended content-intensity rubric across periods; compare raw category features with an independent context/severity model; and evaluate calibration, negation, metaphor, clean versions, and preprocessing/truncation effects. No such second model was implemented or run here.','']
    (REPORTS/'lyriclens_evaluation.md').write_text('\n'.join(lines),encoding='utf-8')


def main():
    rows=read_csv(REPORTS/'lyriclens_predictions.csv')
    if len(rows)!=200:raise ValueError('Expected exactly 200 predictions')
    core=[r for r in rows if r['sample_component']=='stratified_core']
    data={'all_200':{},'core_180':{},'period_core':{},'length_core':{},'extremes':{}}
    for name,group in [('all_200',rows),('core_180',core)]:
        data[name]={score:summary([float(r[score]) for r in group]) for score in SCORES}
    for p in PERIODS:
        group=[r for r in core if r['period']==p]
        data['period_core'][p]={'n':len(group),**{s:statistics.mean(float(r[s]) for r in group) for s in SCORES}}
    for score in SCORES:
        data['length_core'][score]=spearman([int(r['word_count']) for r in core],[float(r[score]) for r in core])
        ordered=sorted(rows,key=lambda r:(float(r[score]),r['song_id']))
        data['extremes'][score]={end:[{k:r[k] for k in ('song_id','title','artist','sample_component',score)} for r in group]
             for end,group in [('lowest',ordered[:3]),('highest',list(reversed(ordered[-3:])))]}
    data['truncated']=sum(int(r['truncated']) for r in rows)
    data['mcr']={v:sum(r['MCR']==v for r in rows) for v in sorted({r['MCR'] for r in rows})}
    data['timing']=summary([float(r['inference_seconds']) for r in rows])
    data['predictions_sha256']=sha(REPORTS/'lyriclens_predictions.csv')
    (WORK/'diagnostics.json').write_text(json.dumps(data,indent=2)+'\n')
    write_csv(WORK/'review_selection.csv',select_review(rows))
    write_report(rows,data)
    print('Generated LyricLens diagnostics, 47-case review, and evaluation report.')


if __name__=='__main__':main()
