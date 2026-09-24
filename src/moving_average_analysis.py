"""Monthly, separate-score Billboard trajectories; no inference or composite score."""
from __future__ import annotations

import json
import lzma
import shutil
import os
from pathlib import Path
import platform
import re
import tempfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import descriptive_analysis as descriptive

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'data/public/master_monthly.csv'
OUTPUT = ROOT / 'analysis/moving_averages'
FEATURES = descriptive.FEATURES
MAJOR = ['Pop', 'Rock', 'Hip-Hop / Rap', 'R&B / Soul', 'Country']
WINDOW = 12
MIN_GENRE_N = 5
MIN_OVERALL_N = 30
MIN_PLOT_ENDPOINTS = 12
VERSION = 'moving-average-v1'
COLORS = dict(zip(MAJOR, ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#8B6508']))


def prepare(frame, expected=True):
    """Validate invariant scores/genres and collapse duplicate song-months explicitly."""
    if expected:
        descriptive.validate(frame)
    required = ['month', 'song_id', 'primary_genre', 'monthly_rank'] + FEATURES
    if not set(required) <= set(frame):
        raise ValueError('Missing required columns')
    if frame[['month', 'song_id', 'primary_genre', 'monthly_rank']].isna().any().any():
        raise ValueError('Missing month, identity, genre or rank')
    if not frame.monthly_rank.between(1, 100).all() or (frame.monthly_rank % 1 != 0).any():
        raise ValueError('Invalid rank')
    for c in FEATURES:
        values = frame[c].dropna()
        if not pd.api.types.is_numeric_dtype(values) or not values.between(0, 1).all():
            raise ValueError('Invalid classifier scores: ' + c)
    invariants = frame.groupby('song_id')[FEATURES + ['primary_genre']].nunique(dropna=False)
    if invariants.gt(1).any().any():
        raise ValueError('Classifier or genre differs within song_id')
    calendar = pd.period_range(frame.month.min(), frame.month.max(), freq='M').astype(str)
    if expected and (len(calendar) != 818 or set(calendar) != set(frame.month)):
        raise ValueError('Expected exactly 818 complete calendar periods')
    if not set(frame.month) <= set(calendar):
        raise ValueError('Invalid monthly period')
    data = frame[required].copy().sort_values(['month', 'song_id', 'monthly_rank'])
    data['rank_weight'] = 101 - data.monthly_rank
    duplicate_rows = data[data.duplicated(['month', 'song_id'], keep=False)]
    audit = duplicate_rows.groupby(['month', 'song_id'], sort=True).agg(
        primary_genre=('primary_genre', 'first'), source_rows=('song_id', 'size'),
        source_ranks=('monthly_rank', lambda x: '|'.join(str(int(v)) for v in x)),
        analysis_rank_weight=('rank_weight', 'mean')).reset_index()
    audit['analysis_song_month_count'] = 1
    # Stable measurements were checked including missingness, so first is lossless.
    group = data.groupby(['month', 'song_id'], sort=True)
    counts = group.size().rename('source_rows')
    weights = group.rank_weight.mean()
    unique = data.drop_duplicates(['month', 'song_id']).set_index(['month', 'song_id'])
    unique['source_rows'] = counts
    unique['rank_weight'] = weights
    return unique.reset_index().drop(columns='monthly_rank'), calendar, audit


def rolling(series, threshold):
    """Reindexed calendar input; no dropping gaps, interpolation or partial windows."""
    out = series.copy()
    eligible = out.n >= threshold
    out['sample_size_flag'] = np.select([out.n.eq(0), ~eligible], ['no_scores', 'below_minimum'], default='sufficient')
    out['rolling_qualifying_months'] = eligible.astype(int).rolling(WINDOW, min_periods=1).sum().astype(int)
    out['rolling_12m_n'] = out.n.rolling(WINDOW, min_periods=WINDOW).sum()
    out['rolling_12m_min_monthly_n'] = out.n.rolling(WINDOW, min_periods=WINDOW).min()
    out['rolling_12m_mean'] = out['mean'].where(eligible).rolling(WINDOW, min_periods=WINDOW).mean()
    out['rank_weighted_rolling_12m_mean'] = out.rank_weighted_mean.where(eligible).rolling(WINDOW, min_periods=WINDOW).mean()
    return out


def aggregate(data, calendar, by_genre=False):
    groups = sorted(data.primary_genre.unique()) if by_genre else ['All genres']
    result = []
    for genre in groups:
        subset = data.loc[data.primary_genre.eq(genre)] if by_genre else data
        grouped = subset.groupby('month', sort=True)
        sizes = grouped.size().reindex(calendar, fill_value=0)
        source_sizes = grouped.source_rows.sum().reindex(calendar, fill_value=0)
        means = grouped[FEATURES].mean().reindex(calendar)
        medians = grouped[FEATURES].median().reindex(calendar)
        stds = grouped[FEATURES].std(ddof=1).reindex(calendar)
        counts = grouped[FEATURES].count().reindex(calendar, fill_value=0)
        weighted = subset[FEATURES].mul(subset.rank_weight, axis=0)
        weighted['month'] = subset.month
        numerators = weighted.groupby('month')[FEATURES].sum(min_count=1).reindex(calendar)
        denominators = subset[FEATURES].notna().mul(subset.rank_weight, axis=0)
        denominators['month'] = subset.month
        denominators = denominators.groupby('month')[FEATURES].sum().reindex(calendar, fill_value=0)
        for c in FEATURES:
            table = pd.DataFrame(dict(month=calendar, classifier=c, n=counts[c].to_numpy(),
                n_songs_total=sizes.to_numpy(), source_observations=source_sizes.to_numpy(),
                mean=means[c].to_numpy(), median=medians[c].to_numpy(), std=stds[c].to_numpy(),
                rank_weight_sum=denominators[c].to_numpy(),
                rank_weighted_mean=(numerators[c]/denominators[c].replace(0, np.nan)).to_numpy()))
            if by_genre:
                table.insert(1, 'primary_genre', genre)
            result.append(rolling(table, MIN_GENRE_N if by_genre else MIN_OVERALL_N))
    return pd.concat(result, ignore_index=True)


def series_iter(overall, genres):
    for c, g in overall.groupby('classifier', sort=True):
        yield 'All genres', c, g.sort_values('month')
    for (genre, c), g in genres.groupby(['primary_genre', 'classifier'], sort=True):
        yield genre, c, g.sort_values('month')


def summarize(overall, genres):
    checks, coverage, sensitivity = [], [], []
    for genre, c, g in series_iter(overall, genres):
        valid = g[g.rolling_12m_mean.notna()]
        row = dict(primary_genre=genre, classifier=c, valid_rolling_endpoints=len(valid))
        for which, selection in [('earliest', valid.head(1)), ('latest', valid.tail(1)),
                                 ('minimum', valid.sort_values(['rolling_12m_mean', 'month']).head(1)),
                                 ('maximum', valid.sort_values(['rolling_12m_mean', 'month'], ascending=[False, True]).head(1))]:
            for name, column in [('month', 'month'), ('mean', 'rolling_12m_mean'),
                                 ('window_n', 'rolling_12m_n'), ('min_monthly_n', 'rolling_12m_min_monthly_n')]:
                row[which+'_'+name] = selection.iloc[0][column] if len(selection) else ('' if name == 'month' else np.nan)
        row['latest_minus_earliest'] = row['latest_mean'] - row['earliest_mean']
        row['rolling_range'] = row['maximum_mean'] - row['minimum_mean']
        checks.append(row)
        present = g.n_songs_total.gt(0)
        low = g.sample_size_flag.ne('sufficient')
        coverage.append(dict(primary_genre=genre, classifier=c, possible_months=len(g),
            months_genre_absent=int((~present).sum()), months_present_without_scores=int((present & g.n.eq(0)).sum()),
            months_below_minimum=int(low.sum()), months_below_minimum_pct=100*low.mean(),
            months_present_below_minimum=int((present & low).sum()),
            present_months_failure_pct=100*(present & low).sum()/present.sum() if present.any() else np.nan,
            sufficient_months=int((~low).sum()), valid_rolling_endpoints=len(valid),
            individual_plot_generated=genre != 'All genres' and len(valid) >= MIN_PLOT_ENDPOINTS))
        difference = valid.rank_weighted_rolling_12m_mean - valid.rolling_12m_mean
        sensitivity.append(dict(primary_genre=genre, classifier=c, paired_rolling_endpoints=len(valid),
            mean_absolute_difference=difference.abs().mean(), max_absolute_difference=difference.abs().max(),
            mean_signed_difference=difference.mean(),
            equal_weight_endpoint_change=row['latest_minus_earliest'],
            rank_weighted_endpoint_change=(valid.rank_weighted_rolling_12m_mean.iloc[-1] -
                valid.rank_weighted_rolling_12m_mean.iloc[0]) if len(valid) else np.nan))
    return pd.DataFrame(checks), pd.DataFrame(coverage), pd.DataFrame(sensitivity)


def validate_outputs(overall, genres, calendar, genre_names):
    for table, keys, threshold in [(overall, ['month', 'classifier'], MIN_OVERALL_N),
            (genres, ['month', 'primary_genre', 'classifier'], MIN_GENRE_N)]:
        expected = len(calendar)*len(FEATURES)*(len(genre_names) if 'primary_genre' in keys else 1)
        if len(table) != expected or table.duplicated(keys).any():
            raise ValueError('Unexpected or duplicate time-series keys')
        if set(table.month) != set(calendar) or set(table.classifier) != set(FEATURES):
            raise ValueError('Missing calendar periods or classifiers')
        if not table.loc[table.n.eq(0), ['mean', 'median', 'std', 'rank_weighted_mean']].isna().all().all():
            raise ValueError('Missing scores converted to measurements')
        if not table.n.between(0, table.n_songs_total).all():
            raise ValueError('Invalid sample sizes')
        for c in ['mean', 'median', 'rank_weighted_mean', 'rolling_12m_mean', 'rank_weighted_rolling_12m_mean']:
            if not table[c].dropna().between(-1e-12, 1+1e-12).all():
                raise ValueError('Score summary outside original scale')
        if not table.sample_size_flag.eq('sufficient').equals(table.n.ge(threshold)):
            raise ValueError('Sample-size flags inconsistent')
        if not table.rolling_12m_mean.notna().equals(table.rolling_qualifying_months.eq(WINDOW)):
            raise ValueError('Rolling coverage inconsistent')
    summed = genres.groupby(['month', 'classifier']).n.sum().sort_index()
    comparison = overall.set_index(['month', 'classifier']).n.sort_index()
    if not summed.equals(comparison):
        raise ValueError('Genre counts do not sum to overall counts')
    if set(genres.primary_genre) != set(genre_names):
        raise ValueError('Genre lost')


def slug(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def label(c):
    prefix, suffix = c.split('_', 1)
    return {'ll': 'LyricLens', 'detox': 'Detoxify', 'emotion': 'GoEmotions', 'sentiment': 'Sentiment'}[prefix] + ': ' + suffix.replace('_', ' ')


def figures(stage, overall, genres, coverage):
    from moving_average_figures import figures as render
    return render(stage, overall, genres, coverage)


def findings(stage, overall, genres, checks, coverage, sensitivity, audit, inventory):
    overall_checks = checks[checks.primary_genre.eq('All genres')].set_index('classifier')
    change_order = overall_checks.latest_minus_earliest.abs().sort_values(ascending=False)
    range_order = overall_checks.rolling_range.sort_values()
    lines = ['# Moving-average descriptive cheat sheet', '',
        'Generated by `python3 src/moving_average_analysis.py`. Separate model scores; no composite or hypothesis test.', '',
        '## Method and coverage', '',
        '- Input: 81,797 source observations, 818 calendar months (1958-08–2026-09), 28,041 unique song identities. Public input, scores and genres are unchanged.',
        f'- {len(audit)} duplicate song-month groups are audited in data/duplicate_song_months.csv. Each contributes once; its rank weight is the average of its source-row weights. This leaves 81,794 analysis song-months, with source counts retained.',
        '- Equal-weight Top-100 representation: each song counts once within its actual snapshot month and again in later months where it appears. No cross-time song deduplication or rank weighting in the primary series.',
        '- Raw statistics use only non-missing scores; std uses ddof=1. Every month × classifier × genre exists in the export, including n=0 and blank measurements. n is the number of distinct songs with a score.',
        '- Overall monthly minimum: 30 scored songs; genre minimum: 5. Raw low-count statistics remain exported but are flagged and hidden in plots. These are pragmatic display rules, not precision guarantees.',
        '- Trailing 12-month means require all 12 consecutive calendar months to meet the minimum. Each qualifying monthly mean receives equal weight; this is not a pooled 12-month song mean. No interpolation or bridging of gaps. Rolling N counts song-months, not independent songs.',
        '- Individual genre plots require at least 12 emitted rolling endpoints. All genres remain in tables and the coverage report, including those with no eligible plot. Count panels show coverage. Y-limits follow only the displayed rolling series with 8% padding. Faint raw monthly context may exceed the displayed range; counts are disclosed and full-scale companions retain it. Scores retain their original 0–1 scale.',
        '- Rank sensitivity weights each available song by 101 − monthly_rank, renormalizes within month among available scores, then averages 12 monthly weighted means under the identical coverage rule.',
        '- 2020 is a neutral visual reference only. Trailing windows lag short-term changes; changing coverage, genre composition and model behavior can affect trajectories. Dataset endpoints may have incomplete calendar years.', '',
        '## Overall movements', '',
        'Largest absolute earliest-to-latest changes (score units, not cross-model effect sizes):', '',
        '| Classifier | Earliest rolling mean | Latest rolling mean | Change | Rolling range |', '|---|---:|---:|---:|---:|']
    for c in change_order.head(6).index:
        r = overall_checks.loc[c]
        lines.append(f'| {c} | {r.earliest_mean:.4f} ({r.earliest_month}) | {r.latest_mean:.4f} ({r.latest_month}) | {r.latest_minus_earliest:+.4f} | {r.rolling_range:.4f} |')
    lines += ['', 'Smallest full-series absolute ranges: ' + '; '.join(f'{c} {overall_checks.loc[c,"rolling_range"]:.4f}' for c in range_order.head(4).index) +
              '. Small ranges can reflect near-zero model scales rather than substantive stability; endpoint change alone can hide reversals.', '',
              '## Genre differences and convergence/divergence', '']
    for c in descriptive.LL + ['sentiment_positive', 'emotion_sadness']:
        panel = genres[(genres.classifier == c) & genres.primary_genre.isin(MAJOR)].pivot(index='month', columns='primary_genre', values='rolling_12m_mean').dropna()
        if panel.empty:
            lines.append(f'- {c}: no date with all five major genres sufficiently covered; no common-date comparison.')
            continue
        first, last = panel.iloc[0], panel.iloc[-1]
        recent = genres[(genres.classifier == c) & genres.primary_genre.isin(MAJOR) & genres.month.eq(overall.month.max())].dropna(subset=['rolling_12m_mean']).set_index('primary_genre').rolling_12m_mean
        if len(recent):
            lines.append(f'- {c} at {overall.month.max()}: {len(recent)}/5 major genres have valid rolling values; highest {recent.idxmax()} {recent.max():.4f}, lowest {recent.idxmin()} {recent.min():.4f}.')
        lines.append(f'- {c}, latest common eligible month {panel.index[-1]}: highest {last.idxmax()} {last.max():.4f}, lowest {last.idxmin()} {last.min():.4f}. The five-genre spread is {last.max()-last.min():.4f}, versus {first.max()-first.min():.4f} at the first common month ({panel.index[0]}). These endpoint spreads describe this available overlap, not a sustained convergence/divergence test.')
    lines += ['', '## Around the 2020 reference', '']
    for c in descriptive.LL + ['sentiment_positive', 'sentiment_negative']:
        g = overall[overall.classifier.eq(c)].set_index('month')
        start, end = g.loc['2020-01', 'rolling_12m_mean'], g.loc['2020-12', 'rolling_12m_mean']
        verb = 'rises' if end > start else 'falls' if end < start else 'is unchanged'
        lines.append(f'- {c}: the overall trailing mean {verb} from {start:.4f} in January 2020 to {end:.4f} in December 2020. These windows overlap; no claim of unusualness or causation is implied.')
    lines += ['', '## Sample-size warnings', '', '| Genre | Below minimum / 818 months | Failure among months present | Eligible rolling endpoints |', '|---|---:|---:|---:|']
    # LyricLens coverage is shared by its four scores; all 42 are exported separately.
    for r in coverage[(coverage.classifier == 'll_explicit_language') & ~coverage.primary_genre.eq('All genres')].itertuples():
        lines.append(f'| {r.primary_genre} | {r.months_below_minimum} ({r.months_below_minimum_pct:.1f}%) | {r.present_months_failure_pct:.1f}% | {r.valid_rolling_endpoints} |')
    lines += ['', '- Table above uses explicit-language availability. coverage_summary.csv reports every classifier separately and distinguishes absent genres from genres present without scored songs. Afrobeats, K-Pop and Gospel/Christian must be judged by these counts, not interpolated historical curves.',
              '- Missing lyrics/scores are not established to be random; thresholds do not correct selection bias or dependence from songs recurring across months.', '', '## Rank-weighting sensitivity', '']
    overall_s = sensitivity[sensitivity.primary_genre.eq('All genres')].sort_values('max_absolute_difference', ascending=False)
    for r in overall_s.head(5).itertuples():
        lines.append(f'- {r.classifier}: mean absolute difference between rolling versions {r.mean_absolute_difference:.4f}; maximum {r.max_absolute_difference:.4f}; earliest-to-latest change equal-weight {r.equal_weight_endpoint_change:+.4f}, rank-weighted {r.rank_weighted_endpoint_change:+.4f}.')
    # A transparent descriptive marker for review, not a significance/materiality test.
    opposite = overall_s[(overall_s.equal_weight_endpoint_change.abs() >= .02) &
                         (overall_s.rank_weighted_endpoint_change * overall_s.equal_weight_endpoint_change < 0)]
    large = overall_s[overall_s.max_absolute_difference >= .05]
    lines.append(f'- {len(large)}/42 overall dimensions reach an absolute rolling difference of 0.05 somewhere. Among equal-weight endpoint changes of at least 0.02, {len(opposite)} reverse direction under rank weighting. These cutoffs are review aids, not statistical tests; rank weighting can alter local levels even when broad direction agrees.')
    major_s = sensitivity[sensitivity.primary_genre.isin(MAJOR)].dropna(subset=['max_absolute_difference']).sort_values('max_absolute_difference', ascending=False)
    for r in major_s.head(3).itertuples():
        lines.append(f'- Largest major-genre sensitivity: {r.primary_genre}, {r.classifier}: maximum difference {r.max_absolute_difference:.4f} across {r.paired_rolling_endpoints} eligible endpoints. Inspect its individual chart before claiming the visual story is unchanged.')
    lines += ['', '## Figure shortlist for human review', '',
              'These ten figures cover content, contrasting score families, coverage-qualified genres and weighting sensitivity; selection is not a ranking by visual drama.', '']
    shortlist = [('ll_explicit_language', 'overall', 'Long-run content trajectory with monthly variation and coverage'),
        ('ll_sexual_content', 'overall', 'A contrasting content trajectory'),
        ('ll_violence', 'overall', 'Violence separately from explicitness'),
        ('ll_substance_use', 'major_genres', 'Content differences among five genres'),
        ('ll_explicit_language', 'major_genres', 'Genre separation and historical gaps'),
        ('sentiment_positive', 'overall', 'Sentiment on its own model scale'),
        ('emotion_sadness', 'overall', 'Contrasting emotion trajectory'),
        ('detox_toxicity', 'major_genres', 'A second classifier family by genre'),
        ('ll_explicit_language', 'rank_sensitivity', 'Check whether rank weighting changes levels'),
        ('ll_violence', 'rank_sensitivity', 'Compare weighting near the neutral 2020 reference')]
    for c, kind, reason in shortlist:
        lines.append(f'- [{c}: {kind}](figures/{c}/{kind}.png) — {reason}.')
    lines += ['', '## Outputs and limits', '',
        f'- {len(overall):,} overall rows and {len(genres):,} genre rows; {len(inventory):,} figures. All 42 separate dimensions and 16 genres are retained.',
        '- data/trajectory_summary.csv contains first/latest/minimum/maximum values, dates and window counts for all series. data/rank_weighting_sensitivity.csv summarizes matched rolling values. data/figure_inventory.csv identifies all charts.',
        '- This is descriptive exploration. No composite hardness/softness score, significance test, causal conclusion or COVID breakpoint model was created.', '']
    (stage/'moving_average_findings.md').write_text('\n'.join(lines))


def build(stage, frame, render=True, expected=True):
    before = pd.util.hash_pandas_object(frame, index=True).to_numpy()
    data, calendar, audit = prepare(frame, expected=expected)
    overall = aggregate(data, calendar)
    genres = aggregate(data, calendar, by_genre=True)
    validate_outputs(overall, genres, calendar, sorted(data.primary_genre.unique()))
    checks, coverage, sensitivity = summarize(overall, genres)
    folder = stage/'data'
    folder.mkdir(parents=True)
    tables = {'monthly_classifier_overall': overall, 'monthly_classifier_by_genre': genres,
              'trajectory_summary': checks, 'coverage_summary': coverage,
              'rank_weighting_sensitivity': sensitivity, 'duplicate_song_months': audit}
    if render:
        inventory = figures(stage, overall, genres, coverage)
        tables['figure_inventory'] = inventory
        findings(stage, overall, genres, checks, coverage, sensitivity, audit, inventory)
    for name, table in tables.items():
        path = folder/(name+'.csv')
        table.to_csv(path, index=False, float_format='%.10g', lineterminator='\n')
        if name.startswith('monthly_classifier_'):
            with path.open('rb') as source, lzma.open(str(path)+'.xz', 'wb', preset=6) as compressed:
                shutil.copyfileobj(source, compressed)
    if not np.array_equal(before, pd.util.hash_pandas_object(frame, index=True).to_numpy()):
        raise ValueError('Input frame modified')
    return tables


def main():
    source_hash = descriptive.sha(INPUT)
    pipeline_hashes = {str(p.relative_to(ROOT)): descriptive.sha(p) for p in
                       [Path(__file__), ROOT/'src/descriptive_analysis.py']}
    frame = pd.read_csv(INPUT, keep_default_na=False, na_values=[''])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.moving-averages-', dir=OUTPUT.parent) as tmp:
        stage = Path(tmp)
        tables = build(stage, frame)
        if descriptive.sha(INPUT) != source_hash:
            raise ValueError('Source changed; outputs not published')
        if any(descriptive.sha(ROOT/rel) != digest for rel, digest in pipeline_hashes.items()):
            raise ValueError('Pipeline code changed during build; outputs not published')
        manifest = dict(version=VERSION, source_path='data/public/master_monthly.csv', source_sha256=source_hash,
            source_unchanged=True, input_frame_unchanged=True, calendar_periods=818,
            source_observations=len(frame), analysis_song_months=int(tables['monthly_classifier_overall'].loc[tables['monthly_classifier_overall'].classifier.eq(FEATURES[0]), 'n_songs_total'].sum()),
            pipeline_sha256=pipeline_hashes,
            runtime=dict(python=platform.python_version(), pandas=pd.__version__, numpy=np.__version__, matplotlib=matplotlib.__version__),
            rules=dict(window_months=WINDOW, required_consecutive_qualifying_months=WINDOW,
                minimum_genre_monthly_n=MIN_GENRE_N, minimum_overall_monthly_n=MIN_OVERALL_N,
                minimum_individual_plot_endpoints=MIN_PLOT_ENDPOINTS,
                primary='one song per month; equal-weight monthly means; equal-weight months in window',
                duplicates='collapse verified-identical song scores within month; average source rank weights',
                missing='never zero-filled, interpolated or bridged', rank_sensitivity='101 - monthly_rank'),
            table_rows={name:len(table) for name,table in tables.items()},
            artifacts={str(p.relative_to(stage)):descriptive.sha(p) for p in sorted(stage.rglob('*')) if p.is_file()})
        (stage/'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2)+'\n')
        # Only fully built/validated output is published; replace each file atomically.
        old_manifest = OUTPUT/'manifest.json'
        old_files = json.loads(old_manifest.read_text())['artifacts'] if old_manifest.exists() else {}
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                target = OUTPUT/path.relative_to(stage)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(path, target)
        # Remove only prior generated artifacts that this build no longer produces.
        for rel in sorted(set(old_files)-set(manifest['artifacts'])):
            target = (OUTPUT/rel).resolve()
            if OUTPUT.resolve() not in target.parents:
                raise ValueError('Unsafe prior manifest artifact path')
            target.unlink(missing_ok=True)
    print(f'Validated and wrote {len(tables["monthly_classifier_overall"]):,} overall rows, '
          f'{len(tables["monthly_classifier_by_genre"]):,} genre rows and '
          f'{len(tables["figure_inventory"])} figures to {OUTPUT}', flush=True)


if __name__ == '__main__':
    main()
