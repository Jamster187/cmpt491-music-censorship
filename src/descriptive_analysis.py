"""Reproducible Milestone 2 descriptives; reads only the final public monthly CSV."""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import platform
import tempfile
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'data/public/master_monthly.csv'
OUTPUT = ROOT / 'analysis/milestone2'
VERSION = 'milestone2-descriptive-v1'
LL = ['ll_sexual_content', 'll_violence', 'll_explicit_language', 'll_substance_use']
DETOX = ['detox_' + s for s in ('toxicity', 'severe_toxicity', 'obscene', 'threat',
                              'insult', 'identity_attack', 'sexual_explicit')]
EMOTION = ['emotion_' + s for s in ('admiration amusement anger annoyance approval caring '
    'confusion curiosity desire disappointment disapproval disgust embarrassment excitement '
    'fear gratitude grief joy love nervousness optimism pride realization relief remorse '
    'sadness surprise neutral').split()]
SENTIMENT = ['sentiment_negative', 'sentiment_neutral', 'sentiment_positive']
FEATURES = LL + DETOX + EMOTION + SENTIMENT
CHART = ['monthly_rank', 'reported_last_week_rank', 'reported_peak_position',
         'reported_weeks_on_chart', 'best_chart_rank', 'weekly_observation_count',
         'chart_weeks', 'total_chart_points', 'snapshot_months_selected']
DURATION = 'mb_duration_median_seconds'
NUMERIC = CHART + [DURATION] + FEATURES
CATEGORICAL = ['primary_genre', 'genre_confidence', 'lyrics_available',
               'lyrics_status', 'musicbrainz_match_status']
TEMPORAL = ['month', 'snapshot_chart_date'] + CHART[:4] + ['source_chart_index', 'source_row_index']
SONG_NUMERIC = CHART[4:] + [DURATION] + FEATURES
SELECTED = LL + ['sentiment_positive', 'sentiment_negative', 'emotion_joy',
                 'emotion_sadness', 'emotion_anger']
POPULARITY = ['monthly_rank', 'best_chart_rank', 'chart_weeks', 'snapshot_months_selected']
AGREEMENT = [('ll_explicit_language', 'detox_obscene'),
             ('ll_sexual_content', 'detox_sexual_explicit'), ('ll_violence', 'detox_threat')]
EMOTION_PAIRS = [('sentiment_positive', 'emotion_joy'),
                 ('sentiment_negative', 'emotion_sadness'), ('sentiment_negative', 'emotion_anger')]
HISTOGRAMS = ['monthly_rank', DURATION] + LL + ['detox_toxicity'] + SELECTED[4:]
HEATMAP = ['monthly_rank', 'chart_weeks', 'll_explicit_language', 'll_violence',
           'detox_obscene', 'sentiment_positive', 'sentiment_negative', 'emotion_joy',
           'emotion_sadness', 'emotion_anger']
# Descriptive caution threshold, not an inferential sample-size rule.
SMALL_SONGS = 30


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def song_level(frame):
    """Deduplicate only after proving every non-chart field is invariant by identity."""
    stable = [c for c in frame if c not in TEMPORAL + ['song_id']]
    if frame.song_id.isna().any():
        raise ValueError('Missing song_id')
    conflicts = frame.groupby('song_id', sort=True)[stable].nunique(dropna=False).gt(1)
    if conflicts.any().any():
        raise ValueError('Inconsistent song-level fields: ' + ', '.join(conflicts.columns[conflicts.any()]))
    return frame[['song_id'] + stable].drop_duplicates('song_id').sort_values('song_id').reset_index(drop=True)


def validate(frame, expected=True):
    required = set(NUMERIC + CATEGORICAL + TEMPORAL + ['song_id', 'artist', 'title'])
    if not required <= set(frame):
        raise ValueError('Missing required columns: ' + ', '.join(sorted(required - set(frame))))
    if expected and (frame.shape != (81797, 78) or frame.song_id.nunique() != 28041
                     or frame.month.nunique() != 818 or frame.primary_genre.nunique() != 16):
        raise ValueError('Unexpected final dataset dimensions/population')
    for c in NUMERIC:
        if not pd.api.types.is_numeric_dtype(frame[c]):
            raise ValueError('Non-numeric measurement: ' + c)
        x = frame[c].dropna()
        if not np.isfinite(x).all():
            raise ValueError('Non-finite measurement: ' + c)
        if c in FEATURES and not x.between(0, 1).all():
            raise ValueError('Invalid score range: ' + c)
    for c in ['monthly_rank', 'reported_last_week_rank', 'reported_peak_position', 'best_chart_rank']:
        x = frame[c].dropna()
        if not x.between(1, 100).all() or not (x % 1 == 0).all():
            raise ValueError('Invalid rank range: ' + c)
    if frame.monthly_rank.isna().any() or frame.month.isna().any():
        raise ValueError('Missing chart month/rank')
    pd.to_datetime(frame.month, format='%Y-%m', errors='raise')
    if not frame.lyrics_available.isin([0, 1]).all():
        raise ValueError('Invalid lyrics availability')
    return song_level(frame)


def summary(frame, columns, weighting):
    rows = []
    for c in columns:
        x = frame[c].dropna()
        q1, q3 = x.quantile([.25, .75], interpolation='linear')
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = int(((x < lo) | (x > hi)).sum())
        rows.append(dict(variable=c, weighting=weighting, non_missing_n=len(x),
            missing_n=len(frame)-len(x), missing_pct=100 * (len(frame)-len(x))/len(frame),
            mean=x.mean(), median=x.median(), std=x.std(ddof=1), variance=x.var(ddof=1),
            minimum=x.min(), q25=q1, q75=q3, maximum=x.max(), iqr=iqr,
            lower_outlier_fence=lo, upper_outlier_fence=hi, potential_outlier_n=outliers,
            potential_outlier_pct=100*outliers/len(x) if len(x) else np.nan))
    return pd.DataFrame(rows)


def correlations(frame, columns, weighting):
    """Pairwise complete observations; Spearman ranks computed within each pair."""
    result = {}
    for method in ['pearson', 'spearman']:
        matrix = frame[columns].corr(method=method, min_periods=3)
        valid = frame[columns].notna().astype('int64')
        counts = valid.T @ valid
        result[method] = pd.DataFrame([
            dict(weighting=weighting, variable_x=a, variable_y=b,
                 pairwise_n=int(counts.loc[a, b]), correlation=matrix.loc[a, b])
            for a, b in itertools.combinations(columns, 2)])
    return result


def categorical(frame, songs):
    rows = []
    for weighting, data in [('observation', frame), ('song', songs)]:
        for c in CATEGORICAL:
            counts = data[c].fillna('(missing)').astype(str).value_counts().sort_index()
            for value, n in counts.items():
                rows.append(dict(variable=c, category=value, weighting=weighting,
                                 count=n, denominator=len(data), percentage=100*n/len(data)))
    return pd.DataFrame(rows)


def group_counts(frame, column):
    g = frame.groupby(column, dropna=False).agg(observation_count=('song_id', 'size'),
                                               unique_songs=('song_id', 'nunique')).reset_index()
    g['observation_pct'] = 100*g.observation_count/len(frame)
    g['unique_song_pct'] = 100*g.unique_songs/frame.song_id.nunique()
    g['small_group_lt_30_songs'] = g.unique_songs < SMALL_SONGS
    return g.sort_values(['observation_count', column], ascending=[False, True]).reset_index(drop=True)


def genre_statistics(frame, counts, weighting):
    rows = []
    for genre, data in frame.groupby('primary_genre', sort=True, dropna=False):
        count = counts.set_index('primary_genre').loc[genre]
        row = dict(primary_genre=genre, weighting=weighting,
                   observation_count=int(count.observation_count), unique_songs=int(count.unique_songs),
                   small_group_lt_30_songs=bool(count.small_group_lt_30_songs))
        columns = ([('monthly_rank', ['median'])] if 'monthly_rank' in data else [])
        columns += [(DURATION, ['median'])] + [(c, ['mean', 'median']) for c in SELECTED]
        for c, stats in columns:
            row[c + '_non_missing_n'] = int(data[c].notna().sum())
            row[c + '_small_available_group'] = data.loc[data[c].notna(), 'song_id'].nunique() < SMALL_SONGS
            for stat in stats:
                row[c + '_' + stat] = getattr(data[c], stat)()
        rows.append(row)
    return pd.DataFrame(rows)


def availability(frame):
    data = frame.copy()
    data['decade'] = (pd.to_datetime(data.month).dt.year // 10 * 10).astype(str) + 's'
    data['rank_band'] = pd.cut(data.monthly_rank, [0, 10, 25, 50, 75, 100],
                              labels=['1–10', '11–25', '26–50', '51–75', '76–100'])
    rows = []
    for dimension in ['decade', 'primary_genre', 'rank_band']:
        for label, g in data.groupby(dimension, observed=True, sort=True, dropna=False):
            masks = {'lyrics_available': g.lyrics_available.eq(1),
                     'all_42_classifier_scores': g[FEATURES].notna().all(axis=1),
                     DURATION: g[DURATION].notna()}
            masks.update({c: g[c].notna() for c in FEATURES})
            for measure, mask in masks.items():
                rows.append(dict(group_dimension=dimension, group=str(label), measure=measure,
                    observation_count=len(g), unique_songs=g.song_id.nunique(),
                    available_observations=int(mask.sum()), available_pct=100*mask.mean(),
                    unavailable_observations=int((~mask).sum()),
                    available_unique_songs=g.loc[mask, 'song_id'].nunique()))
    result = pd.DataFrame(rows)
    result['available_unique_song_pct'] = 100*result.available_unique_songs/result.unique_songs
    return result


def yearly(frame):
    data = frame.assign(year=pd.to_datetime(frame.month).dt.year)
    rows = []
    for year, group in data.groupby('year', sort=True):
        for weighting, g in [('observation', group), ('song_within_year', group.drop_duplicates('song_id'))]:
            for c in SELECTED:
                rows.append(dict(year=year, weighting=weighting, variable=c,
                    months_observed=group.month.nunique(), partial_year=group.month.nunique() < 12,
                    observation_count=len(group), unique_songs=group.song_id.nunique(),
                    non_missing_n=int(g[c].notna().sum()), missing_n=int(g[c].isna().sum()),
                    mean=g[c].mean(), median=g[c].median()))
    return pd.DataFrame(rows)


def label(c):
    return c.replace('mb_duration_median_seconds', 'Duration (seconds)').replace('_', ' ').capitalize()


def figures(out, frame, songs, genres, yearly_table, availability_table):
    from descriptive_figures import figures as render
    return render(out, frame, songs, genres, yearly_table, availability_table)


def findings(out, frame, songs, tables):
    obs = tables['summary_statistics'].set_index('variable')
    single = tables['song_level_summary_statistics'].set_index('variable')
    genres = tables['genre_summary']
    lines = ['# Milestone 2 descriptive cheat sheet', '',
        'Generated by `python3 src/descriptive_analysis.py`; exploratory facts, not an assignment submission.', '',
        '## Dataset and interpretation', '',
        f'- {len(frame):,} song-month observations; {len(frame.columns)} columns; {len(songs):,} exact study song identities; {frame.month.nunique()} snapshots.',
        f'- Chart months: {frame.month.min()} through {frame.month.max()}. Chart dates are not release dates.',
        '- Observation weighting counts every source row; song weighting counts each song_id once after checking stable fields. Repeated rows are not independent songs. No p-values or confidence intervals are calculated.',
        '- Scores and genres are model outputs, not ground truth. Correlations describe association, not classifier accuracy or causality. Whole-history chart summaries are not contemporary monthly measures.',
        '- Lower rank means better chart position: negative score–rank correlation means higher scores tend to accompany better ranks. Positive score–chart_weeks correlation means longer chart presence.', '',
        '## Important summary statistics', '',
        '| Variable | Observation mean / median | Song mean / median |', '|---|---:|---:|']
    for c in ['monthly_rank', DURATION, 'chart_weeks'] + SELECTED:
        r = obs.loc[c]
        s = single.loc[c] if c in single.index else None
        lines.append(f'| {c} | {r["mean"]:.4f} / {r["median"]:.4f} | ' +
                     (f'{s["mean"]:.4f} / {s["median"]:.4f}' if s is not None else 'Not a stable song field') + ' |')
    lines += ['', '## Genres', '']
    for name, subset in [('Largest', genres.head(3)), ('Smallest', genres.tail(3).iloc[::-1])]:
        lines.append(f'- {name} by observation count: ' + '; '.join(f'{r.primary_genre}: {r.observation_count:,} observations, {r.unique_songs:,} songs' for r in subset.itertuples()) + '.')
    small = genres.loc[genres.small_group_lt_30_songs, 'primary_genre'].tolist()
    lines.append('- Groups below 30 unique songs: ' + (', '.join(small) if small else 'none') + '. Per-feature available-song flags also mark thin coverage.')
    gs = tables['song_level_genre_statistics']
    for c in ['ll_explicit_language', 'll_violence', 'sentiment_positive', 'sentiment_negative']:
        eligible = gs[~gs[c+'_small_available_group']].sort_values(c+'_mean')
        low, high = eligible.iloc[0], eligible.iloc[-1]
        lines.append(f'- Among genres with ≥30 available songs, song-weighted mean {c}: highest {high.primary_genre} ({high[c+"_mean"]:.4f}); lowest {low.primary_genre} ({low[c+"_mean"]:.4f}). Descriptive extremes, without adjustment for era or other variables.')
    lines += ['', '## Missingness', '']
    for weighting, data in [('observation', frame), ('song', songs)]:
        lines.append(f'- {weighting.capitalize()} weighted: lyrics unavailable {100*data.lyrics_available.eq(0).mean():.2f}%; any classifier score missing {100*data[FEATURES].isna().any(axis=1).mean():.2f}%; duration missing {100*data[DURATION].isna().mean():.2f}%.')
    av = tables['availability_by_group']
    for dimension in ['decade', 'primary_genre', 'rank_band']:
        g = av[(av.group_dimension == dimension) & (av.measure == 'lyrics_available')].sort_values('available_pct')
        lines.append(f'- Lyrics availability by {dimension}: {g.iloc[0]["group"]} {g.iloc[0].available_pct:.2f}% to {g.iloc[-1]["group"]} {g.iloc[-1].available_pct:.2f}% of observations. This coverage imbalance warrants caution.')
    lines += ['- Blank cells alone are missing; zero scores are observed values. lyrics_available=0 and unsuccessful lyrics_status are observed dispositions, not blank cells. No lyric text is read or exported.', '',
              '## Correlations', '', '| Weighting | Pair | Pearson | Spearman | Pairwise N |', '|---|---|---:|---:|---:|']
    def pair_row(data, weighting, a, b):
        return data[(data.weighting == weighting) & (((data.variable_x == a) & (data.variable_y == b)) | ((data.variable_x == b) & (data.variable_y == a)))].iloc[0]
    pears, spears = tables['pearson_correlations'], tables['spearman_correlations']
    for weighting in ['observation', 'song']:
        pop = spears[(spears.weighting == weighting) & spears.variable_x.isin(POPULARITY) & spears.variable_y.isin(FEATURES)]
        best = pop.loc[pop.groupby('variable_x').correlation.apply(lambda x: x.abs().idxmax()).values]
        feature_pairs = spears[(spears.weighting == weighting) & spears.variable_x.isin(FEATURES) & spears.variable_y.isin(FEATURES)]
        strongest = feature_pairs.loc[feature_pairs.correlation.abs().nlargest(3).index]
        pairs = list(dict.fromkeys(AGREEMENT + EMOTION_PAIRS + list(zip(best.variable_x, best.variable_y)) + list(zip(strongest.variable_x, strongest.variable_y))))
        for a, b in pairs:
            p, s = pair_row(pears, weighting, a, b), pair_row(spears, weighting, a, b)
            lines.append(f'| {weighting} | {a} vs {b} | {p.correlation:.4f} | {s.correlation:.4f} | {s.pairwise_n:,} |')
    lines += ['', '- Popularity rows above show the largest absolute Spearman association with a model score for each popularity measure and weighting. Also shown are the three strongest score–score associations by absolute Spearman correlation; outputs of the same model need not be independent. Pairwise deletion means different pairs can describe different subsets. Constant/insufficient pairs produce blank correlations.',
              '- Song correlations exclude time-varying monthly ranks; no arbitrary first-month rank represents a song. Available song-level popularity summaries remain included.', '', '## Distributions and potential outliers', '']
    for c in [DURATION, 'll_explicit_language', 'll_violence', 'detox_toxicity', 'emotion_joy']:
        r = single.loc[c]
        lines.append(f'- {c}, each song once: min {r.minimum:.4f}, Q1 {r.q25:.4f}, median {r["median"]:.4f}, Q3 {r.q75:.4f}, max {r.maximum:.4f}; {int(r.potential_outlier_n):,} potential outliers ({r.potential_outlier_pct:.2f}% of observed songs). Mean {r["mean"]:.4f} versus median {r["median"]:.4f} helps assess asymmetry alongside the histogram.')
    lines += ['- Outliers lie strictly outside Q1 − 1.5 IQR and Q3 + 1.5 IQR. These flags describe tails, not errors; no observations were removed. Bounded scores often have long upper tails, so IQR flags need context.', '', '## Initial time patterns', '']
    yr = tables['yearly_summary']
    for c in ['ll_explicit_language', 'll_violence', 'sentiment_positive', 'emotion_sadness']:
        g = yr[(yr.variable == c) & (yr.weighting == 'observation') & ~yr.partial_year]
        low, high = g.loc[g['mean'].idxmin()], g.loc[g['mean'].idxmax()]
        lines.append(f'- {c}: lowest full-year observation mean {low["mean"]:.4f} ({int(low.year)}); highest {high["mean"]:.4f} ({int(high.year)}). These are descriptive annual extrema, not trend tests.')
    partial = yr.loc[yr.partial_year, ['year','months_observed']].drop_duplicates()
    lines += ['- Partial years: ' + '; '.join(f'{r.year} ({r.months_observed} observed months)' for r in partial.itertuples()) + '. Marked in figures and excluded only from the extrema just reported.',
        '- Annual means/medians use available scores. Song-within-year summaries count each song once in each year; the same song can appear in several years. Coverage, genre mix and repeated-song weighting can change across time. No breakpoint, pre/post comparison or COVID conclusion is produced.', '',
        '## Suggested figures (8)', '']
    for name in ['hist_mb_duration_median_seconds', 'hist_ll_explicit_language', 'song_score_boxplots',
                 'genre_ll_explicit_language', 'selected_spearman_heatmap',
                 'relationship_ll_explicit_language_vs_detox_obscene', 'missingness_by_decade', 'annual_content']:
        lines.append(f'- [{name}](figures/{name}.png)')
    lines += ['', '## Milestone mapping and remaining writing work', '',
        '- Question 2: histograms, score/genre boxplots, missingness, annual descriptive plots and the distribution notes above.',
        '- Question 3: summary_statistics.csv and song_level_summary_statistics.csv (N, missingness, central tendency, variance/spread, quartiles, extrema, IQR/outliers); categorical, artist and genre summaries.',
        '- Question 4: Pearson/Spearman tables, selected heatmap, relationship hexbins, genre comparisons and grouped availability.',
        '- Programs and descriptive outputs are complete. The group still needs to select figures, explain weighting and missingness, and write its own interpretation with model/coverage limitations. No formal COVID analysis has been started.', '']
    (out/'descriptive_findings.md').write_text('\n'.join(lines))


def build(out, frame, songs):
    tables = {'summary_statistics': summary(frame, NUMERIC, 'observation'),
              'song_level_summary_statistics': summary(songs, SONG_NUMERIC, 'song'),
              'categorical_summary': categorical(frame, songs),
              'genre_summary': group_counts(frame, 'primary_genre'),
              'artist_summary': group_counts(frame, 'artist')}
    tables['genre_statistics'] = genre_statistics(frame, tables['genre_summary'], 'observation')
    tables['song_level_genre_statistics'] = genre_statistics(songs, tables['genre_summary'], 'song')
    tables['missingness'] = pd.DataFrame([dict(column=c, non_missing=int(frame[c].notna().sum()),
        missing=int(frame[c].isna().sum()), missing_pct=100*frame[c].isna().mean()) for c in frame])
    tables['availability_by_group'] = availability(frame)
    tables['yearly_summary'] = yearly(frame)
    obs_corr = correlations(frame, NUMERIC, 'observation')
    song_corr = correlations(songs, SONG_NUMERIC, 'song')
    for method in obs_corr:
        tables[method+'_correlations'] = pd.concat([obs_corr[method], song_corr[method]], ignore_index=True)
    table_dir = out/'tables'
    table_dir.mkdir(exist_ok=True)
    for name, data in tables.items():
        data.to_csv(table_dir/(name+'.csv'), index=False, float_format='%.10g', lineterminator='\n')
    figures(out, frame, songs, tables['genre_summary'], tables['yearly_summary'], tables['availability_by_group'])
    findings(out, frame, songs, tables)
    return tables


def main():
    before = sha(INPUT)
    # Empty cells only: preserve literal NA-like artist/title strings.
    frame = pd.read_csv(INPUT, keep_default_na=False, na_values=[''])
    songs = validate(frame)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.milestone2-', dir=OUTPUT.parent) as tmp:
        stage = Path(tmp)
        tables = build(stage, frame, songs)
        if sha(INPUT) != before:
            raise ValueError('Source changed during analysis; outputs not published')
        manifest = dict(version=VERSION, input='data/public/master_monthly.csv', input_sha256=before,
            input_sha256_after=sha(INPUT), source_unchanged=True, pipeline_sha256=sha(__file__),
            rows=len(frame), columns=len(frame.columns), unique_songs=len(songs), snapshots=frame.month.nunique(),
            runtime=dict(python=platform.python_version(), pandas=pd.__version__, numpy=np.__version__,
                         scipy=scipy.__version__, matplotlib=matplotlib.__version__),
            methods=dict(quantiles='linear interpolation', variance_std='sample; ddof=1',
                         outliers='strictly outside Q1-1.5*IQR, Q3+1.5*IQR; retained',
                         correlations='pairwise complete; min N=3; Spearman average ties per pair; no inference',
                         small_group='fewer than 30 total or feature-available unique songs'),
            artifacts={str(p.relative_to(stage)): sha(p) for p in sorted(stage.rglob('*')) if p.is_file()})
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
        # Publish only fully generated, validated artifacts, replacing files atomically.
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                target = OUTPUT/path.relative_to(stage)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(path, target)
    print(f'Validated {len(frame):,} rows, {len(songs):,} songs; wrote {len(tables)} tables and '
          f'{len(list((OUTPUT/"figures").glob("*.png")))} figures to {OUTPUT}')


if __name__ == '__main__':
    main()
