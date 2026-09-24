"""Readable views of existing Milestone 2 results; no numerical exports are written."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.cbook import boxplot_stats
import numpy as np
import figure_style as style
import descriptive_analysis as d


def figures(out, frame, songs, genres, yearly_table, availability_table):
    dest = out/'figures'
    dest.mkdir(exist_ok=True)
    style.setup()

    def save(fig, name, family, description, panels, **kwargs):
        fig.tight_layout(rect=(0, .065, 1, .97))
        style.emit(fig, dest/(name+'.png'), family, description, panels, **kwargs)

    for c in d.HISTOGRAMS:
        x = frame[c].dropna()
        bins = np.arange(.5, 101.5, 1) if c == 'monthly_rank' else np.linspace(0, 1, 41) if c in d.FEATURES else 40
        density, edges = np.histogram(x, bins=bins, density=True)
        densities = [density]
        if c in songs:
            densities.append(np.histogram(songs[c].dropna(), bins=edges, density=True)[0])
        positive = np.concatenate(densities)
        positive = positive[positive > 0]
        skewed = positive.max()/positive.min() > 100
        fig, axes = plt.subplots(1, 2 if skewed else 1, figsize=(12, 4.8) if skewed else (8, 4.8), squeeze=False)
        for index, ax in enumerate(axes[0]):
            ax.hist(x, bins=edges, density=True, alpha=.5, color='#0072B2', label=f'Song-months (n={len(x):,})')
            if c in songs:
                ax.hist(songs[c].dropna(), bins=edges, density=True, histtype='step', linewidth=1.5,
                        color='#D55E00', label=f'Songs (n={songs[c].notna().sum():,})')
            ax.set(xlabel=d.label(c), ylabel='Density', title=d.label(c)+(' — tail detail' if index else ' — distribution'))
            if index:
                ax.set_yscale('log')
                ax.set_ylabel('Density (log scale; empty bins omitted)')
            else:
                style.numeric_axis(ax)
            ax.grid(axis='y', alpha=.15)
            if c == 'monthly_rank': ax.set_xlabel('Monthly rank (1 = best; 100 = worst)')
        handles, labels = axes[0,0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.5,.075), ncol=2, frameon=False, fontsize=10)
        fig.text(.04, .025, 'All observations and original bin edges retained.'+(' Linear and log-density views show the same bins.' if skewed else ''), fontsize=10)
        fig.tight_layout(rect=(0,.17,1,.97))
        style.emit(fig, dest/('hist_'+c+'.png'), 'histogram', 'density of all original bins; both available weightings',
             [(axes[0,0], np.r_[0, np.concatenate(densities)])],
             issue='Tail densities >100 times smaller than peak' if skewed else '',
             action='Add log-density companion panel; retain full support and original bins' if skewed else 'Retain full support; improve text and 300 dpi')

    # Reference retains every flier on a common domain. Default makes each central box legible.
    arrays = [songs[c].dropna().to_numpy() for c in d.SELECTED]
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.boxplot(arrays, vert=False, tick_labels=[d.label(c) for c in d.SELECTED], flierprops={'markersize':1, 'alpha':.2})
    ax.set(xlabel='Model score (0–1)', xlim=(0, 1), title='Representative scores — full distributions; each song once')
    ax.grid(axis='x', alpha=.15)
    save(fig, 'song_score_boxplots_full_scale', 'score_boxplot', 'all song scores including all outliers',
         [(ax, np.concatenate(arrays))], axis_dimension='x', action='Full-domain reference retains all outliers')
    fig, axes = plt.subplots(3, 3, figsize=(13, 8.5))
    panels=[]; clipped=0
    for ax, c, values in zip(axes.flat, d.SELECTED, arrays):
        stats=boxplot_stats(values)[0]
        central=[stats['whislo'], stats['whishi']]
        limits=style.score_limits(central)
        outside=int(((values < limits[0]) | (values > limits[1])).sum()); clipped+=outside
        ax.boxplot([values], vert=False, flierprops={'markersize':1, 'alpha':.2})
        ax.set(xlim=limits, yticks=[], title=d.label(c), xlabel=f'Score; {outside:,} values outside view')
        ax.grid(axis='x', alpha=.15); style.numeric_axis(ax, 'x')
        style.assert_contained(central, limits); panels.append((ax, central))
    fig.suptitle('Representative scores — central 1.5-IQR whisker views; each song once', fontsize=14)
    fig.text(.04, .025, 'Independent X-axes; theoretical scores 0–1. All outliers remain in song_score_boxplots_full_scale.png.', fontsize=10)
    save(fig, 'song_score_boxplots', 'score_boxplot', '1.5-IQR whiskers and boxes, independently scaled by score', panels,
         axis_dimension='x', reference_path=str(dest/'song_score_boxplots_full_scale.png'), context_clipped=clipped,
         note='Outliers beyond the view counted on each panel; full-domain companion retains all',
         issue='Near-zero emotion boxes compressed by shared domain and legitimate outliers',
         action='Separate central whisker views with independent labeled X-axes and complete full-scale companion')

    for c in ['ll_explicit_language', 'll_violence', 'sentiment_positive', 'sentiment_negative']:
        order=songs.groupby('primary_genre')[c].median().sort_values().index
        groups=[songs.loc[songs.primary_genre.eq(g), c].dropna() for g in order]
        labels=[f'{g} (n={len(x):,})'+(' *' if len(x)<d.SMALL_SONGS else '') for g,x in zip(order, groups)]
        fig,ax=plt.subplots(figsize=(12, 8))
        boxes=ax.boxplot(groups, vert=False, tick_labels=labels, flierprops={'markersize':1,'alpha':.15}, patch_artist=True)
        for patch, genre in zip(boxes['boxes'], order):
            patch.set(facecolor=style.COLORS.get(genre, '#BBBBBB'), alpha=.5)
        ax.set(xlabel=d.label(c)+' (0–1)', xlim=(0,1), title='By genre — each song once; * fewer than 30 available songs')
        ax.grid(axis='x', alpha=.15)
        compressed=sum(len(x)>=d.SMALL_SONGS and x.median()<.03 and (x.quantile(.75)-x.quantile(.25))<.03 for x in groups)>=3
        if compressed:
            save(fig, 'genre_'+c+'_full_scale', 'genre_boxplot', 'complete song score distributions; linear-domain reference',
                 [(ax, np.concatenate(groups))], axis_dimension='x', action='Linear full-scale reference retains all outliers')
            ax.set_xscale('symlog',linthresh=.001,linscale=1,base=10)
            ax.set_xticks([0,.001,.01,.1,1],['0','0.001','0.01','0.1','1'])
            ax.set_xlabel(d.label(c)+' (0–1; linear to 0.001, logarithmic above)')
            fig.text(.04,.025,'All observations retained. Nonlinear X-axis expands near-zero boxes; linear companion: '+ 'genre_'+c+'_full_scale.png',fontsize=9)
        save(fig, 'genre_'+c, 'genre_boxplot', 'complete song score distributions by genre; outliers retained',
             [(ax, np.concatenate(groups))], axis_dimension='x',
             reference_path=str(dest/('genre_'+c+'_full_scale.png')) if compressed else '',
             issue='At least three well-covered genre boxes have near-zero median and IQR below 0.03' if compressed else '',
             action='Disclosed symlog X-axis (linear through 0.001); retain all outliers and linear companion' if compressed else
                    'Retain full distributions; readable genre labels and stable major-genre colors')

    fig,ax=plt.subplots(figsize=(12,10))
    corr=frame[d.HEATMAP].corr(method='spearman')
    im=ax.imshow(corr, vmin=-1, vmax=1, cmap='RdBu_r')
    ax.set_xticks(range(len(d.HEATMAP)), [d.label(c) for c in d.HEATMAP], rotation=50, ha='right')
    ax.set_yticks(range(len(d.HEATMAP)), [d.label(c) for c in d.HEATMAP])
    for i in range(len(d.HEATMAP)):
        for j in range(len(d.HEATMAP)):
            value=corr.iloc[i,j]
            ax.text(j,i,f'{value:.2f}',ha='center',va='center',fontsize=10,color='white' if abs(value)>.65 else 'black')
    ax.set_title('Spearman correlation — song-month weighted, pairwise complete\nLower monthly rank = better chart position')
    cb=fig.colorbar(im,ax=ax,label='Spearman correlation')
    save(fig,'selected_spearman_heatmap','correlation','pairwise Spearman coefficients (colour axis)',
         [(cb.ax,corr.to_numpy().ravel())],action='Retain signed -1 to 1 colour domain; improve annotation contrast and labels')

    pairs=[('ll_explicit_language','monthly_rank'),('sentiment_positive','monthly_rank'),
           ('ll_explicit_language','chart_weeks'),('sentiment_negative','chart_weeks')]+d.AGREEMENT[:2]
    for a,b in pairs:
        data=frame if b=='monthly_rank' else songs
        pair=data[[a,b]].dropna()
        fig,ax=plt.subplots(figsize=(9,5.8))
        h=ax.hexbin(pair[a],pair[b],gridsize=35,mincnt=1,bins='log',cmap='viridis')
        ax.set(xlabel=d.label(a),ylabel=d.label(b),title=f'{d.label(a)} vs {d.label(b)}\n'+
               ('Song-months' if b=='monthly_rank' else 'Each song once')+f'; paired n={len(pair):,}')
        if b=='monthly_rank':
            ax.invert_yaxis();ax.set_ylabel('Monthly rank (1 = best; top of axis)')
        fig.colorbar(h,ax=ax,label='Count per hexagon (log scale)')
        save(fig,'relationship_'+a+'_vs_'+b,'scatter_hexbin','all pairwise-complete observations; log-count colour',
             [(ax,pair[b])],action='Retain all points and log-count density; larger labels and 300 dpi')

    fig,ax=plt.subplots(figsize=(11,5.8));values=[]
    for measure in ['lyrics_available','all_42_classifier_scores',d.DURATION]:
        g=availability_table[(availability_table.group_dimension=='decade') & (availability_table.measure==measure)]
        y=100-g.available_pct;values.extend(y)
        ax.plot(g['group'],y,marker='o',label=d.label(measure))
    ax.set(ylabel='Unavailable observations (%)',xlabel='Chart decade',ylim=(0,100),
           title='Missing coverage by decade — song-month weighted')
    ax.legend(loc='upper left',bbox_to_anchor=(1.01,1),frameon=False,fontsize=9);ax.grid(alpha=.15)
    save(fig,'missingness_by_decade','missingness','unavailable observation percentages',[(ax,values)],
         action='Keep interpretable 0–100 percentage scale; move legend outside data')

    for name,columns in [('content',d.LL),('sentiment_emotion',d.SELECTED[4:])]:
        fig,axes=plt.subplots(len(columns),1,figsize=(12,2.8*len(columns)),sharex=True)
        panels=[]
        for ax,c in zip(axes,columns):
            values=[]
            for weighting,linestyle in [('observation','-'),('song_within_year','--')]:
                g=yearly_table[(yearly_table.variable==c) & (yearly_table.weighting==weighting)]
                ax.plot(g.year,g['mean'],linestyle,label='Mean — '+weighting.replace('_',' '));values.extend(g['mean'])
                if weighting=='observation':
                    ax.plot(g.year,g['median'],':',color='gray',label='Median — observation');values.extend(g['median'])
                    partial=g[g.partial_year]
                    ax.scatter(partial.year,partial['mean'],marker='x',color='black',label='Partial year')
            limits=style.score_limits(values);style.assert_contained(values,limits)
            ax.set(ylim=limits,ylabel='Score',title=d.label(c));style.numeric_axis(ax)
            ax.axvline(2020,color='#888888',linestyle=':',linewidth=.9);ax.grid(alpha=.15)
            panels.append((ax,values))
        handles,labels=axes[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.975),ncol=2,frameon=False)
        fig.suptitle('Annual descriptive scores — changing song mix and coverage',y=.997)
        axes[-1].set_xlabel('Chart calendar year (not release year)')
        fig.text(.04,.025,'Each axis follows its displayed means AND median; scores range 0–1. 2020 is a neutral reference.',fontsize=10)
        fig.tight_layout(rect=(0,.05,1,.92))
        style.emit(fig,dest/('annual_'+name+'.png'),'annual_summary','annual means (both weightings) and observation median',panels,
                   action='Scale all displayed annual series; exterior legend; larger panels; neutral 2020 reference')
