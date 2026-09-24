"""Add genre overlays from frozen moving-average exports; never recompute scores."""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import tempfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import moving_average_analysis as ma

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT/'analysis/moving_averages'
OUTPUT = REPORT/'figures/all_genres'
MAJOR_ENDPOINTS = 120
VERSION = 'all-genres-overlays-v1'
MARKER = '<!-- BEGIN GENERATED ALL-GENRES OVERLAYS -->'
# Fixed catalog, including genres with no qualifying endpoints. No per-chart palettes.
STYLES = {
    'Pop': ('#0072B2', '-'),
    'Rock': ('#D55E00', '-'),
    'Hip-Hop / Rap': ('#009E73', '-'),
    'R&B / Soul': ('#CC79A7', '-'),
    'Country': ('#8B6508', '-'),
    'Latin': ('#E69F00', '--'),
    'Electronic / Dance': ('#6A3D9A', '--'),
    'Alternative / Indie': ('#222222', '-.'),
    'Metal': ('#A50F15', ':'),
    'Folk / Singer-Songwriter': ('#66A61E', '--'),
    'Jazz / Blues': ('#1B9E77', ':'),
    'Reggae / Dancehall': ('#A6761D', '-.'),
    'Gospel / Christian': ('#E7298A', ':'),
    'K-Pop': ('#56B4E9', '--'),
    'Afrobeats / African Pop': ('#7570B3', ':'),
    'Other': ('#777777', '--'),
}
INSPECT = ma.descriptive.LL + ['detox_toxicity', 'sentiment_positive', 'sentiment_negative',
                              'emotion_joy', 'emotion_love', 'emotion_anger', 'emotion_sadness']
SHORTLIST = ['ll_explicit_language', 'll_violence', 'll_sexual_content', 'll_substance_use',
             'detox_toxicity', 'sentiment_positive', 'sentiment_negative', 'emotion_love', 'emotion_sadness']


def load_frozen():
    """Check prior provenance and read exactly its serialized values, with no smoothing."""
    baseline = json.loads((REPORT/'manifest.json').read_text())
    protected = {ma.INPUT: baseline['source_sha256'], REPORT/'manifest.json': ma.descriptive.sha(REPORT/'manifest.json')}
    for rel, digest in baseline['pipeline_sha256'].items():
        protected[ROOT/rel] = digest
    for rel, digest in baseline['artifacts'].items():
        path = REPORT/rel
        if rel == 'moving_average_findings.md':
            continue  # Original text is checked separately; only an appendix may change.
        if path.exists():
            protected[path] = digest
        elif not rel.endswith('.csv') or not Path(str(path)+'.xz').exists():
            raise ValueError('Missing prior artifact: '+rel)
    for path, digest in protected.items():
        if ma.descriptive.sha(path) != digest:
            raise ValueError('Prior artifact changed: '+str(path))
    text = (REPORT/'moving_average_findings.md').read_text()
    prefix = text.split(MARKER)[0]
    import hashlib
    if hashlib.sha256(prefix.encode()).hexdigest() != baseline['artifacts']['moving_average_findings.md']:
        raise ValueError('Original findings text changed')
    source = REPORT/'data/monthly_classifier_by_genre.csv.xz'
    frame = pd.read_csv(source, float_precision='round_trip')
    coverage = pd.read_csv(REPORT/'data/coverage_summary.csv')
    validate(frame, coverage)
    return frame, coverage, prefix, protected


def validate(frame, coverage):
    calendar = pd.period_range('1958-08', '2026-09', freq='M').astype(str)
    if len(frame) != 818*16*42 or frame.duplicated(['month','primary_genre','classifier']).any():
        raise ValueError('Invalid time-series grid')
    if set(frame.primary_genre) != set(STYLES) or set(frame.classifier) != set(ma.FEATURES):
        raise ValueError('Unexpected genre/classifier catalog')
    if not frame.rolling_12m_mean.dropna().between(0, 1).all():
        raise ValueError('Invalid score scale')
    if not frame.rolling_12m_mean.notna().equals(frame.rolling_qualifying_months.eq(12)):
        raise ValueError('Existing rolling validity mask differs')
    cov = coverage[~coverage.primary_genre.eq('All genres')]
    if len(cov) != 16*42 or cov.duplicated(['primary_genre','classifier']).any():
        raise ValueError('Invalid coverage grid')
    cov = cov.set_index(['primary_genre','classifier'])
    for key, g in frame.groupby(['primary_genre','classifier'], sort=True):
        g = g.sort_values('month')
        if g.month.tolist() != list(calendar):
            raise ValueError('Incomplete calendar grid')
        if g.rolling_12m_mean.notna().sum() != cov.loc[key, 'valid_rolling_endpoints']:
            raise ValueError('Coverage count differs from existing values')


def plot(frame, classifier, major=False):
    """Retain full calendar arrays, including NaNs; validate each rendered Line2D."""
    threshold = MAJOR_ENDPOINTS if major else 1
    fig, ax = plt.subplots(figsize=(17, 8.5), dpi=100)
    fig.subplots_adjust(left=.065, right=.72, bottom=.15, top=.88)
    records = []
    dates = pd.to_datetime(sorted(frame.month.unique()))
    for genre, (color, style) in STYLES.items():
        g = frame[(frame.classifier == classifier) & (frame.primary_genre == genre)].sort_values('month')
        values = g.rolling_12m_mean.to_numpy(copy=True)
        count = int(g.rolling_12m_mean.notna().sum())
        if count < threshold:
            continue
        line, = ax.plot(pd.to_datetime(g.month), values, color=color, linestyle=style,
            linewidth=1.05, marker='.', markersize=1.8, label=f'{genre} ({count} months)')
        # Plot exact serialized endpoints; NaNs break lines, including isolated points.
        np.testing.assert_array_equal(line.get_ydata(), values)
        np.testing.assert_array_equal(line.get_xdata(), pd.to_datetime(g.month).to_numpy())
        if line.get_color() != color or line.get_linestyle() != style:
            raise ValueError('Plot style differs from catalog')
        records.append(dict(classifier=classifier, variant='major_coverage' if major else 'all_genres',
                            primary_genre=genre, valid_endpoints=count, color=color, line_style=style))
    ax.axvline(pd.Timestamp('2020-01-01'), color='#888888', linewidth=.9, linestyle=':')
    ax.text(pd.Timestamp('2020-01-01'), .99, '2020', transform=ax.get_xaxis_transform(),
            ha='right', va='top', color='#666666', fontsize=10)
    ax.set(xlim=(dates.min(), dates.max()), ylim=(0,1), xlabel='Chart month (1958–2026)',
           ylabel='12-month moving-average score', title=ma.label(classifier))
    ax.title.set_fontsize(17)
    ax.xaxis.label.set_fontsize(12)
    ax.yaxis.label.set_fontsize(12)
    ax.tick_params(labelsize=11)
    ax.grid(alpha=.15)
    ax.legend(loc='upper left', bbox_to_anchor=(1.015,1), frameon=False, fontsize=10,
              title='Genre (valid rolling endpoints)', title_fontsize=10, handlelength=3)
    rule = (f'Major coverage: ≥{MAJOR_ENDPOINTS} valid endpoints per genre' if major
            else 'All genres with ≥1 valid endpoint; short runs shown with point markers')
    fig.text(.065, .93, rule, fontsize=12)
    fig.text(.065, .065, 'Existing equal-weight series • 12 consecutive months with ≥5 scored songs/month • Gaps remain gaps', fontsize=11)
    fig.text(.065, .035, 'No raw monthly lines. The 2020 marker is a neutral reference, not a fitted breakpoint.', fontsize=10, color='#555555')
    return fig, records


def appendix(frame):
    lines = [MARKER, '', '## All-genres overlays (additional figures)', '',
        'Rebuild only these overlays with `python3 src/moving_average_all_genres.py`. The original tables, calculations and 420 figures remain unchanged.', '',
        '- Added 84 single-panel, 5100 × 2550 pixel PNGs (300 dpi): all qualifying genres and a cleaner major-coverage version for each of 42 scores. No raw monthly series or rank sensitivity is added to these overlays.',
        '- Major coverage means **at least 120 valid rolling endpoints per classifier**, about ten years of endpoints, not necessarily consecutive. This is only a figure-selection rule; monthly N ≥5 and 12 consecutive qualifying months are unchanged.',
        '- Every non-missing exported rolling value is plotted in the all-genres version, including Latin’s four endpoints. Full calendar arrays retain missing periods; markers make isolated endpoints visible. Eight genres have any endpoints, while five pass the major-coverage threshold for each classifier.',
        '- Genre colors and line styles are fixed across all images; the mapping and plotted counts are in figures/all_genres/manifest.json. Legends list plotted genres and their endpoint counts. Genres with no endpoints remain in the original coverage table.',
        '- Every chart uses a 0–1 y-axis for comparison. Low-amplitude emotion series may look nearly flat; cross-model scales do not imply equivalent substantive effects.', '',
        '### Inspection of the requested dimensions', '',
        'For a like-for-like descriptive comparison, the table uses the first and last dates where all five coverage-qualified genres have valid values. Sparse later coverage prevents a full five-genre comparison near 2020 or at the dataset endpoint. A change in endpoint spread alone does not establish sustained convergence.', '',
        '| Classifier | Common dates | First → last five-genre spread | Highest / lowest at last common date |',
        '|---|---|---:|---|']
    for c in INSPECT:
        sub = frame[frame.classifier.eq(c)]
        eligible = [g for g in STYLES if sub.loc[sub.primary_genre.eq(g), 'rolling_12m_mean'].notna().sum() >= MAJOR_ENDPOINTS]
        panel = sub[sub.primary_genre.isin(eligible)].pivot(index='month', columns='primary_genre', values='rolling_12m_mean').dropna()
        if panel.empty:
            lines.append(f'| {c} | No complete overlap | — | — |')
            continue
        first, last = panel.iloc[0], panel.iloc[-1]
        lines.append(f'| {c} | {panel.index[0]} → {panel.index[-1]} | {first.max()-first.min():.4f} → {last.max()-last.min():.4f} | {last.idxmax()} ({last.max():.4f}) / {last.idxmin()} ({last.min():.4f}) |')
    lines += ['',
        '- LyricLens explicit language, violence, sexual content and substance use show clear genre separation where coverage overlaps. Their five-genre endpoint spreads narrow across the common interval, while substantial differences remain. The overlays show non-monotonic paths and coverage gaps, so this is not a claim of uniform long-run convergence.',
        '- Hip-Hop/Rap remains visually separated on explicit language and toxicity across much of its eligible history. Country approaches Hip-Hop/Rap in several later substance-use windows, while Pop remains lower; these local approaches are not uniform convergence.',
        '- Sentiment curves occupy a tighter band on the shared 0–1 axes. Across the common comparison dates, the positive-sentiment spread narrows slightly (0.0461 to 0.0421), while negative sentiment widens (0.0422 to 0.0551). Cross-model scale differences are not equivalent substantive effects.',
        '- Love shows a narrower five-genre spread at the later common endpoint (0.1923 to 0.1000), with several trajectories drawing closer during parts of that interval. Hip-Hop/Rap generally occupies the lower portion of the love and sadness overlays during eligible periods. Joy stays close to zero on this scale; later Hip-Hop/Rap anger separates upward from Pop and Country. Near-zero values and short runs are not evidence of no change.',
        '- Alternative/Indie and Electronic/Dance add shorter historical trajectories beyond the five major-coverage genres. Latin has only four qualifying endpoints and should be treated as a brief observed segment, not a full trajectory. No curves are drawn for the eight genres with no eligible windows.', '',
        '### Recommended all-genres figures (9)', '']
    for c in SHORTLIST:
        lines.append(f'- [{c}](figures/all_genres/{c}.png) · [cleaner coverage version](figures/all_genres/{c}_major_coverage.png)')
    lines += ['', 'These choices span content, toxicity, sentiment and contrasting emotions with overlapping genre coverage; they are not selected solely for dramatic extrema. Inspect joy and anger too, but their smaller absolute levels are less visible on the fixed scale. No significance tests or causal interpretation are supplied.', '']
    return '\n'.join(lines)


def main():
    frame, coverage, prefix, protected = load_frozen()
    before_frame = pd.util.hash_pandas_object(frame, index=True).to_numpy()
    code_paths = [Path(__file__), ROOT/'src/moving_average_analysis.py', ROOT/'src/descriptive_analysis.py']
    code_hashes = {str(p.relative_to(ROOT)):ma.descriptive.sha(p) for p in code_paths}
    with tempfile.TemporaryDirectory(prefix='.all-genres-', dir=REPORT) as tmp:
        stage = Path(tmp)
        rows = []
        for i, c in enumerate(ma.FEATURES, 1):
            for major in [False, True]:
                fig, records = plot(frame, c, major)
                filename = c+('_major_coverage' if major else '')+'.png'
                fig.savefig(stage/filename, dpi=300, metadata={'Software':VERSION})
                plt.close(fig)
                rows.extend(dict(r, filename=filename) for r in records)
            if i % 7 == 0:
                print(f'Completed {i}/42 classifier overlays', flush=True)
        findings = prefix+appendix(frame)
        np.testing.assert_array_equal(before_frame, pd.util.hash_pandas_object(frame, index=True).to_numpy())
        for path, digest in protected.items():
            if ma.descriptive.sha(path) != digest:
                raise ValueError('Protected input or prior output changed: '+str(path))
        for rel, digest in code_hashes.items():
            if ma.descriptive.sha(ROOT/rel) != digest:
                raise ValueError('Code changed during generation')
        if len(list(stage.glob('*.png'))) != 84:
            raise ValueError('Expected exactly 84 figures')
        import hashlib
        manifest = dict(version=VERSION, major_coverage_minimum_endpoints=MAJOR_ENDPOINTS,
            source_series_sha256=protected[REPORT/'data/monthly_classifier_by_genre.csv.xz'],
            source_values_unchanged=True, previous_data_and_figures_unchanged=True,
            original_findings_prefix_sha256=hashlib.sha256(prefix.encode()).hexdigest(),
            extended_findings_sha256=hashlib.sha256(findings.encode()).hexdigest(),
            code_sha256=code_hashes, styles={g:dict(color=c,line_style=s) for g,(c,s) in STYLES.items()},
            runtime=dict(python=platform.python_version(), pandas=pd.__version__,numpy=np.__version__,matplotlib=matplotlib.__version__),
            plot_validation='Line2D values/dates exactly equal full exported arrays including NaNs; fixed styles checked',
            plotted_series=rows, figures={p.name:ma.descriptive.sha(p) for p in sorted(stage.glob('*.png'))})
        (stage/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        (stage/'findings.tmp').write_text(findings)
        OUTPUT.mkdir(parents=True,exist_ok=True)
        for p in sorted(stage.iterdir()):
            target = REPORT/'moving_average_findings.md' if p.name == 'findings.tmp' else OUTPUT/p.name
            os.replace(p,target)
    print('Added 84 figures; original data and figures verified unchanged.',flush=True)


if __name__ == '__main__':
    main()
