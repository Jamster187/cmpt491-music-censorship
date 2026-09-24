"""Figure rendering only. Inputs are existing numerical results; no aggregation."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import figure_style as style
from moving_average_analysis import (FEATURES, MIN_OVERALL_N, MIN_GENRE_N, MAJOR, COLORS, label, slug)

def figures(stage, overall, genres, coverage):
    style.setup()
    records = []
    def axes(title):
        fig, (ax, count_ax) = plt.subplots(2, 1, figsize=(13, 7), sharex=True,
            gridspec_kw={'height_ratios': [4, 1]})
        ax.set(title=title, ylabel='Classifier score (0–1)', ylim=(0, 1))
        count_ax.set(ylabel='Scored songs', xlabel='Chart month (not release month)')
        for panel in [ax, count_ax]:
            panel.axvline(pd.Timestamp('2020-01-01'), color='gray', linestyle=':', linewidth=1)
            panel.grid(alpha=.15)
        ax.text(pd.Timestamp('2020-01-01'), .99, '2020', transform=ax.get_xaxis_transform(), color='gray', ha='right', va='top', fontsize=10)
        fig.subplots_adjust(left=.09, right=.74, bottom=.20, top=.86, hspace=.15)
        return fig, ax, count_ax
    def save(fig, path, c, kind, genre='All genres'):
        target = stage/'figures'/c/path
        ax, count_ax = fig.axes
        primary = np.concatenate([style.finite(line.get_ydata()) for line in ax.lines
            if '12-month' in line.get_label() or line.get_label() == 'Rank-weighted sensitivity'
            or (kind == 'major_genres' and not line.get_label().startswith('_'))])
        context = np.concatenate([style.finite(line.get_ydata()) for line in ax.lines
            if 'onthly mean' in line.get_label()]) if kind in ['overall', 'individual_genre'] else np.array([])
        limits = style.score_limits(primary)
        style.assert_contained(primary, limits)
        ax.set_ylim(limits)
        style.numeric_axis(ax)
        for panel in fig.axes:
            panel.set_xlim(pd.Timestamp(overall.month.min()), pd.Timestamp(overall.month.max()))
        count_ax.set_ylim(bottom=0)
        count_ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=3, integer=True))
        ax.get_legend().remove()
        ax.legend(loc='upper left', bbox_to_anchor=(1.015, 1), frameon=False, fontsize=10)
        clipped = int(((context < limits[0]) | (context > limits[1])).sum())
        note = 'Y-axis follows displayed 12-month means; classifier scores range 0–1.'
        if len(context):
            note += f' Raw monthly context: {clipped} values outside view.'
        text = fig.text(.09, .085, note, fontsize=10, color='#555555')
        fig.text(.09, .045, 'Gaps retain the existing coverage rules. 2020 is a neutral reference, not a fitted breakpoint.', fontsize=10, color='#555555')
        ref = target.with_name(target.stem+'_full_scale.png') if clipped else None
        family = 'moving_average_'+kind
        style.emit(fig, target, family, 'equal-weight 12-month mean'+
            ('; rank-weighted 12-month sensitivity' if kind in ['individual_genre', 'rank_sensitivity'] else ''),
            [(ax, primary)], note=note, reference_path=str(ref) if ref else '', context_clipped=clipped,
            action='Scale only finite displayed rolling series; exterior legend; readable count panel; 300 dpi')
        if ref:
            ax.set_ylim(0, 1)
            text.set_text('Full theoretical 0–1 reference; all qualifying raw monthly values and rolling means are visible.')
            style.emit(fig, ref, family, 'equal-weight/rank-weighted rolling means; full-domain reference',
                [(ax, primary)], action='Full-domain companion preserves every qualifying raw monthly value')
        records.append(dict(classifier=c, figure_type=kind, primary_genre=genre,
                            path=str(target.relative_to(stage))))
    indexed_genres = {(g,c): d for (g,c),d in genres.groupby(['primary_genre','classifier'], sort=True)}
    for number, c in enumerate(FEATURES, 1):
        data = overall[overall.classifier.eq(c)].sort_values('month')
        dates = pd.to_datetime(data.month)
        fig, ax, count_ax = axes(label(c) + '\nOverall equal-weight Top-100 representation; trailing 12 months')
        ax.plot(dates, data['mean'].where(data.n.ge(MIN_OVERALL_N)), color='#0072B2', alpha=.22, linewidth=.7, label='Raw monthly mean')
        ax.plot(dates, data.rolling_12m_mean, color='#0072B2', linewidth=1.7, label='12-month mean')
        count_ax.plot(dates, data.n, color='#0072B2', linewidth=.7)
        count_ax.axhline(MIN_OVERALL_N, color='gray', linestyle='--', linewidth=.7)
        ax.legend(loc='upper left', fontsize=10)
        save(fig, 'overall.png', c, 'overall')
        fig, ax, count_ax = axes(label(c) + '\nMajor genres: 12 consecutive months with ≥5 scored songs/month')
        for genre in MAJOR:
            g = indexed_genres[(genre,c)].sort_values('month')
            dates = pd.to_datetime(g.month)
            ax.plot(dates, g.rolling_12m_mean, color=COLORS[genre], label=f'{genre} ({g.rolling_12m_mean.notna().sum()} endpoints)', linewidth=1.3)
            count_ax.plot(dates, g.n, color=COLORS[genre], alpha=.7, linewidth=.7)
        count_ax.axhline(MIN_GENRE_N, color='gray', linestyle='--', linewidth=.7)
        ax.legend(loc='upper left', fontsize=10, ncol=2)
        save(fig, 'major_genres.png', c, 'major_genres', 'Major genres')
        fig, ax, count_ax = axes(label(c) + '\nOverall sensitivity: equal-weight vs rank-weighted Top-100 representation')
        dates = pd.to_datetime(data.month)
        ax.plot(dates, data.rolling_12m_mean, color='#0072B2', label='Equal weight; 12-month mean')
        ax.plot(dates, data.rank_weighted_rolling_12m_mean, color='#D55E00', linestyle='--', label='Weight = 101 − rank; 12-month mean')
        count_ax.plot(dates, data.n, color='#0072B2', linewidth=.7)
        ax.legend(loc='upper left', fontsize=10)
        save(fig, 'rank_sensitivity.png', c, 'rank_sensitivity')
        eligible = coverage[(coverage.classifier == c) & coverage.individual_plot_generated]
        for genre in eligible.primary_genre:
            g = indexed_genres[(genre,c)].sort_values('month')
            dates = pd.to_datetime(g.month)
            fig, ax, count_ax = axes(label(c) + '\n' + genre + ': gaps mark insufficient coverage')
            ax.plot(dates, g['mean'].where(g.n.ge(MIN_GENRE_N)), color='#0072B2', alpha=.25, linewidth=.7, label='Monthly mean; n ≥ 5')
            ax.plot(dates, g.rolling_12m_mean, color='#0072B2', label='Equal weight; 12-month mean', linewidth=1.7)
            ax.plot(dates, g.rank_weighted_rolling_12m_mean, color='#D55E00', linestyle='--', linewidth=1, label='Rank-weighted sensitivity')
            count_ax.plot(dates, g.n, color='#0072B2', linewidth=.7)
            count_ax.axhline(MIN_GENRE_N, color='gray', linestyle='--', linewidth=.7)
            low = g.n.lt(MIN_GENRE_N)
            count_ax.scatter(dates[low], g.loc[low, 'n'], color='#D55E00', s=3)
            ax.legend(loc='upper left', fontsize=10)
            save(fig, slug(genre)+'.png', c, 'individual_genre', genre)
        if number % 7 == 0:
            print(f'Figures complete for {number}/42 classifiers', flush=True)
    return pd.DataFrame(records)

