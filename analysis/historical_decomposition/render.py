"""Small, measured figure set and report for the completed historical analysis."""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import historical_decomposition as hd

PUBLIC=hd.PUBLIC
LEGACY=hd.comparison_id('1990s','2015–2024')
RECENT=hd.comparison_id('2010s','2020–2025')
CONTENT=['detox_toxicity','ll_sexual_content','ll_explicit_language','ll_substance_use','ll_violence']
NAMES={'detox_toxicity':'Toxicity','ll_sexual_content':'Sexual content','ll_explicit_language':'Explicit language',
       'll_substance_use':'Substance use','ll_violence':'Violence','sentiment_positive':'Positive sentiment',
       'sentiment_negative':'Negative sentiment','emotion_joy':'Joy','emotion_love':'Love',
       'emotion_sadness':'Sadness','emotion_anger':'Anger'}
COLORS={'Pop':'#0072B2','Rock':'#D55E00','Hip-Hop / Rap':'#009E73','R&B / Soul':'#CC79A7',
        'Country':'#8B6508','Electronic / Dance':'#56B4E9','Other 10 genres':'#999999'}


def number(value,digits=4):
    return '—' if pd.isna(value) else f'{value:.{digits}f}'


def table(columns,rows):
    rows=[[str(v).replace('|','/').replace('\n',' ') for v in row] for row in rows]
    return '\n'.join(['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']+
        ['| '+' | '.join(row)+' |' for row in rows])


def load():
    return {name:pd.read_csv(PUBLIC/(name+('.csv.gz' if name=='annual_trajectories' else '.csv')))
        for name in ['historical_comparisons','decomposition_results','sensitivity_results','breakpoint_results',
                     'genre_period_statistics','annual_trajectories','annual_genre_shares','primary_tests','preliminary_claims_audit']}


def figures(tables):
    folder=PUBLIC/'figures';folder.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'svg.hashsalt':'historical-decomposition-v2','axes.spines.top':False,'axes.spines.right':False})
    index=[]
    def save(fig,name,description,source):
        bottom=.12 if fig.legends else .035
        fig.get_layout_engine().set(rect=(0,bottom,1,1-bottom))
        fig.text(.5,.008,'Exploratory · existing Billboard monthly population · no causal attribution',fontsize=9,ha='center')
        svg=folder/(name+'.svg');fig.savefig(svg,metadata={'Date':None})
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
        preview=Path(tempfile.gettempdir())/('cmpt491-historical-'+name+'.png')
        fig.savefig(preview,dpi=220);plt.close(fig)
        index.append(dict(name=name,description=description,source=source,svg='figures/'+name+'.svg'))
    annual=tables['annual_trajectories'];overall=annual[(annual.weighting=='song_month')&(annual.genre=='All genres')]
    fig,axes=plt.subplots(4,3,figsize=(13,12),layout='constrained')
    for ax,c in zip(axes.flat,hd.PRIMARY):
        f=overall[overall.classifier==c].sort_values('year');ax.plot(f.year,f['mean'],color='#2166ac',lw=1.6)
        ax.axvline(2020,color='#777777',ls='--',lw=.8);ax.set(title=NAMES[c],xlabel='Chart year',ylabel='Mean score')
        ax.set_ylim(0,max(.02,float(f['mean'].max())*1.1));ax.grid(alpha=.18)
    axes.flat[-1].axis('off');axes.flat[-1].text(0,.8,'All eleven prespecified dimensions\nAnnual song-month-weighted means\nSeparate classifier scales (0–1)\n2026 excluded\n2020 is a time reference',va='top',linespacing=1.8)
    save(fig,'01_historical_trajectories','Annual complete-case trajectories for all eleven named dimensions','annual_trajectories.csv.gz')

    major=list(COLORS)[:-1];fig,axes=plt.subplots(2,2,figsize=(13,8.5),layout='constrained')
    for ax,c in zip(axes.flat,['ll_explicit_language','detox_toxicity','ll_substance_use','emotion_love']):
        for genre in major:
            f=annual[(annual.weighting=='song_month')&(annual.genre==genre)&(annual.classifier==c)].sort_values('year')
            ax.plot(f.year,f['mean'].where(f.n_songs>=30),label=genre,color=COLORS[genre],lw=1.5)
        ax.axvline(2020,color='#777777',ls='--',lw=.8);ax.set(title=NAMES[c],xlabel='Chart year',ylabel='Mean score',ylim=(0,1 if c=='ll_explicit_language' else None));ax.grid(alpha=.18)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.035),ncol=3,fontsize=9)
    fig.suptitle('Six largest genres · gaps where fewer than 30 distinct scored songs/year\nAll sixteen genres remain in the result tables',fontsize=12)
    save(fig,'02_genre_trajectories','Four dimensions and six genres selected by overall population counts; sparse years remain gaps','annual_trajectories.csv.gz')

    totals=tables['historical_comparisons'];legacy=totals[(totals.comparison==LEGACY)&(totals.weighting=='song_month')].set_index('classifier')
    fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained')
    for ax,scores in zip(axes,[CONTENT,[c for c in hd.PRIMARY if c not in CONTENT]]):
        f=legacy.loc[scores];y=np.arange(len(f));positive=np.zeros(len(f));negative=np.zeros(len(f))
        for term,color in [('within','#2166ac'),('composition','#d95f02')]:
            value=f[term].to_numpy();left=np.where(value>=0,positive,negative)
            ax.barh(y,value,left=left,label=term.replace('within','Within genre').replace('composition','Composition'),color=color)
            positive+=np.where(value>0,value,0);negative+=np.where(value<0,value,0)
        ax.errorbar(f.delta,y,xerr=[f.delta-f.delta_low,f.delta_high-f.delta],fmt='D',ms=4,color='black',capsize=3,label='Total change, 95% interval')
        ax.set(yticks=y,yticklabels=[NAMES[c] for c in scores],xlabel='Change in classifier score',title='1990s → 2015–2024');ax.invert_yaxis();ax.axvline(0,color='#555555',lw=.8)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.035),ncol=3,fontsize=9)
    save(fig,'03_decomposition_legacy','Exact symmetric components; total-change intervals use crossed artist/calendar resampling','historical_comparisons.csv')

    detail=tables['decomposition_results'];g=detail[(detail.comparison==LEGACY)&(detail.weighting=='song_month')]
    genres=sorted(g.genre.unique());fig,axes=plt.subplots(1,2,figsize=(14,9),layout='constrained')
    limit=max(abs(g[g.classifier.isin(CONTENT)].within).max(),abs(g[g.classifier.isin(CONTENT)].composition).max())
    for ax,term in zip(axes,['within','composition']):
        values=g.pivot(index='genre',columns='classifier',values=term).loc[genres,CONTENT].to_numpy()
        im=ax.imshow(values,aspect='auto',cmap='RdBu_r',vmin=-limit,vmax=limit)
        ax.set(yticks=np.arange(len(genres)),yticklabels=genres,xticks=np.arange(len(CONTENT)),xticklabels=[NAMES[c] for c in CONTENT],title=term.capitalize()+' contribution')
        ax.tick_params(axis='x',labelrotation=35)
        for i in range(len(genres)):
            for j in range(len(CONTENT)):ax.text(j,i,f'{values[i,j]:+.3f}',ha='center',va='center',fontsize=8,color='white' if abs(values[i,j])>.65*limit else 'black')
    fig.colorbar(im,ax=axes,shrink=.65,label='Contribution in score units');fig.suptitle('All sixteen genres · 1990s → 2015–2024')
    save(fig,'04_genre_contributions','Every original genre; common color scale; signed contributions can offset','decomposition_results.csv')

    shares=tables['annual_genre_shares'];shares=shares[shares.weighting=='song_month'].pivot(index='year',columns='genre',values='full_share').fillna(0)
    remainder=shares.drop(columns=major).sum(axis=1);fig,axes=plt.subplots(2,1,figsize=(13,11),layout='constrained',gridspec_kw={'height_ratios':[1,1.5]})
    axes[0].stackplot(shares.index,*[shares[c] for c in major],remainder,labels=major+['Other 10 genres'],colors=[COLORS[g] for g in major+['Other 10 genres']])
    axes[0].set(ylabel='Share of all song-months',xlabel='Chart year',ylim=(0,1),title='Full population, including songs without scores')
    axes[0].legend(ncol=4,fontsize=8,loc='upper left');axes[0].axvline(2020,color='black',ls='--',lw=.8)
    cells=tables['genre_period_statistics'];cov=cells[(cells.weighting=='song_month')&(cells.classifier=='detox_toxicity')]
    periods=list(hd.PERIODS);values=cov.pivot(index='genre',columns='period',values='score_coverage').loc[genres,periods].to_numpy()*100
    im=axes[1].imshow(values,aspect='auto',cmap='YlGnBu',vmin=0,vmax=100)
    axes[1].set(yticks=np.arange(len(genres)),yticklabels=genres,xticks=np.arange(len(periods)),xticklabels=periods,title='Toxicity-score coverage by original genre and period · blank = genre absent')
    for i in range(len(genres)):
        for j in range(len(periods)):
            if np.isfinite(values[i,j]):axes[1].text(j,i,f'{values[i,j]:.0f}',ha='center',va='center',fontsize=8,color='white' if values[i,j]>70 else 'black')
    fig.colorbar(im,ax=axes[1],shrink=.8,label='Scored song-month weight (%)')
    save(fig,'05_genre_shares_and_coverage','Changing representation and uneven score coverage; six individual series plus explicitly grouped remainder','annual_genre_shares.csv; genre_period_statistics.csv')

    sens=tables['sensitivity_results'];fig,axes=plt.subplots(1,2,figsize=(14,6),layout='constrained')
    for k,(weight,color) in enumerate(zip(hd.WEIGHTINGS,['#2166ac','#d95f02','#7570b3'])):
        f=totals[(totals.comparison==LEGACY)&(totals.weighting==weight)].set_index('classifier').loc[CONTENT]
        axes[0].scatter(f.within_percent,np.arange(5)+(k-1)*.15,label=weight.replace('_',' '),color=color,s=40)
    axes[0].set(yticks=np.arange(5),yticklabels=[NAMES[c] for c in CONTENT],xlabel='Within-genre share of observed change (%)',title='Weighting changes the estimand');axes[0].invert_yaxis();axes[0].legend(fontsize=9)
    bounds=sens[(sens.comparison==LEGACY)&(sens.scenario=='unrestricted_0_1_bounds')].set_index('classifier').loc[CONTENT]
    for i,c in enumerate(CONTENT):
        axes[1].plot([bounds.loc[c,'delta_low'],bounds.loc[c,'delta_high']],[i,i],color='#999999',lw=4)
        values=sens[(sens.comparison==LEGACY)&(sens.classifier==c)&(sens.analysis=='missingness')].delta.dropna()
        axes[1].plot([values.min(),values.max()],[i,i],color='#d95f02',lw=8)
        axes[1].scatter(legacy.loc[c,'delta'],i,color='#2166ac',s=40,zorder=3)
    axes[1].axvline(0,color='black',lw=.8);axes[1].set(yticks=np.arange(5),yticklabels=[NAMES[c] for c in CONTENT],xlabel='Change in population mean score',title='Missing-score assumptions · 1990s → 2015–2024');axes[1].invert_yaxis()
    from matplotlib.lines import Line2D
    axes[1].legend(handles=[Line2D([0],[0],color='#999999',lw=4,label='Unrestricted [0,1] outer bounds'),Line2D([0],[0],color='#d95f02',lw=6,label='MAR / ±0.10 scenario range'),Line2D([0],[0],marker='o',color='#2166ac',ls='',label='Observed-score change')],fontsize=8)
    save(fig,'06_weighting_missingness_sensitivity','Percent shares are not invariant to weighting; bound intervals are assumptions, not confidence intervals','historical_comparisons.csv; sensitivity_results.csv')

    breaks=tables['breakpoint_results'];current=breaks[breaks.break_year==2020]
    fig,axes=plt.subplots(1,2,figsize=(14,7.5),layout='constrained')
    for ax,term in zip(axes,['level','slope']):
        for k,(model,color) in enumerate([('unadjusted','#d95f02'),('genre_adjusted','#2166ac')]):
            f=current[current.model==model].set_index('classifier').loc[hd.PRIMARY]
            ax.errorbar(f[term],np.arange(11)+(k-.5)*.2,xerr=[f[term]-f[term+'_low'],f[term+'_high']-f[term]],fmt='o',ms=4,capsize=2,color=color,label=model.replace('_',' '))
        ax.axvline(0,color='#555555',lw=.8);ax.set(yticks=np.arange(11),yticklabels=[NAMES[c] for c in hd.PRIMARY],xlabel='Score units' if term=='level' else 'Score units per year',title='January 2020 '+term+' change');ax.invert_yaxis();ax.legend(fontsize=9)
    fig.suptitle('Same 2014–2025 window · 95% crossed artist/calendar intervals\nGlobal BY status is reported separately; an interval alone is not a discovery claim',fontsize=12)
    save(fig,'07_breakpoint_2020','Prespecified level and slope changes, with and without additive genre adjustment','breakpoint_results.csv')

    fig,axes=plt.subplots(1,2,figsize=(14,7),layout='constrained');f=breaks[breaks.model=='genre_adjusted']
    for ax,term in zip(axes,['level','slope']):
        values=f.pivot(index='classifier',columns='break_year',values=term).loc[hd.PRIMARY,hd.BREAKS]
        ranks=values.abs().rank(axis=1,ascending=False,method='min').to_numpy()
        im=ax.imshow(ranks,aspect='auto',cmap='YlOrRd_r',vmin=1,vmax=11)
        ax.set(yticks=np.arange(11),yticklabels=[NAMES[c] for c in hd.PRIMARY],xticks=np.arange(11),xticklabels=hd.BREAKS,title='Absolute '+term+' change rank');ax.tick_params(axis='x',labelrotation=50)
        for i in range(11):
            for j in range(11):ax.text(j,i,str(int(ranks[i,j])),ha='center',va='center',fontsize=8,color='white' if ranks[i,j]<=3 else 'black')
        ax.axvline(9.5,color='black',lw=1.5)
    fig.suptitle('Genre-adjusted comparisons · 1 = largest absolute change within that score\nTen historical alternatives overlap; these are descriptive ranks, not placebo p-values',fontsize=12)
    save(fig,'08_historical_placebo_comparison','Identical six-year-before/six-year-after windows at eleven fixed dates','breakpoint_results.csv')
    hd.write_json(PUBLIC/'figure_index.json',index)
    return index


def reference_paths(tables):
    details=tables['decomposition_results'];records=[]
    for (comparison,weighting,score),f in details.groupby(['comparison','weighting','classifier'],sort=True):
        a=f.mean0.fillna(f.mean1).fillna(0);b=f.mean1.fillna(f.mean0).fillna(0)
        old=float((f.share0*(b-a)).sum());new=float((f.share1*(b-a)).sum())
        delta=float((f.share1*b).sum()-(f.share0*a).sum())
        records.append(dict(comparison=comparison,weighting=weighting,classifier=score,
            within_old_reference=old,within_new_reference=new,symmetric_within=(old+new)/2,
            within_old_reference_percent=100*old/delta if abs(delta)>1e-12 else np.nan,
            within_new_reference_percent=100*new/delta if abs(delta)>1e-12 else np.nan,
            description='Two valid sequential paths; their average is the reported symmetric accounting'))
    hd.write_csv('reference_path_audit.csv',records)
    return pd.DataFrame(records)


def findings(t,index,paths):
    h=t['historical_comparisons'];d=t['decomposition_results'];s=t['sensitivity_results'];b=t['breakpoint_results'];tests=t['primary_tests']
    legacy=h[(h.comparison==LEGACY)&(h.weighting=='song_month')].set_index('classifier')
    recent=h[(h.comparison==RECENT)&(h.weighting=='song_month')].set_index('classifier')
    old=t['preliminary_claims_audit'].set_index('classifier');execution=json.loads((PUBLIC/'execution.json').read_text())
    core_rows=[]
    for c in CONTENT:
        r=legacy.loc[c]
        core_rows.append([NAMES[c],number(old.loc[c,'claimed_within_percent'],0)+'%',number(r.mean0),number(r.mean1),number(r.delta),number(r.within_percent,1)+'%',number(r.composition_percent,1)+'%',f"[{r.delta_low:.4f}, {r.delta_high:.4f}]",number(r.delta_q,5),number(r.within_q,5)])
    contributions=[]
    for c in CONTENT:
        f=d[(d.comparison==LEGACY)&(d.weighting=='song_month')&(d.classifier==c)]
        wi=f.sort_values('within',ascending=False).head(3);up=f.loc[f.composition.idxmax()];down=f.loc[f.composition.idxmin()]
        contributions.append([NAMES[c],'; '.join(r.genre+' '+number(r.within) for r in wi.itertuples()),up.genre+' '+number(up.composition),down.genre+' '+number(down.composition)])
    historical=[]
    for a,bb in hd.COMPARISONS:
        f=h[(h.comparison==hd.comparison_id(a,bb))&(h.weighting=='song_month')].set_index('classifier')
        historical.append([a+' → '+bb]+[number(f.loc[c,'delta']) for c in CONTENT+['emotion_love']])
    weight=[];missing=[]
    for c in CONTENT:
        f=h[(h.comparison==LEGACY)&(h.classifier==c)].set_index('weighting')
        weight.append([NAMES[c]]+[number(f.loc[w,'within_percent'],1)+'%' for w in hd.WEIGHTINGS])
        subset=s[(s.comparison==LEGACY)&(s.classifier==c)]
        scenarios=subset[(subset.analysis=='missingness')&subset.delta.notna()]
        bound=subset[subset.scenario=='unrestricted_0_1_bounds'].iloc[0]
        missing.append([NAMES[c],number(scenarios.delta.min())+' to '+number(scenarios.delta.max()),
            '['+number(bound.delta_low)+', '+number(bound.delta_high)+']'])
    coverage=t['genre_period_statistics'];coverage=coverage[(coverage.classifier=='detox_toxicity')&(coverage.weighting=='song_month')]
    cov=coverage.groupby('period')[['scored_weight','total_weight']].sum();cov['coverage']=100*cov.scored_weight/cov.total_weight
    current=b[b.break_year==2020];break_rows=[]
    for c in hd.PRIMARY:
        r=current[(current.classifier==c)&(current.model=='genre_adjusted')].iloc[0]
        break_rows.append([NAMES[c],number(r.level),f'[{r.level_low:.4f}, {r.level_high:.4f}]',number(r.level_q,5),number(r.slope),f'[{r.slope_low:.4f}, {r.slope_high:.4f}]',number(r.slope_q,5),str(int(r.slope_absolute_rank_of_11))+'/11'])
    count=int((tests.q_by_global<=.05).sum());break_pass=int(((current.level_q<=.05)|(current.slope_q<=.05)).sum())
    summary_by=tests.assign(passes=tests.q_by_global<=.05).groupby('family').passes.agg(['size','sum'])
    recent_rows=[[NAMES[c],number(recent.loc[c,'delta']),number(recent.loc[c,'within']),number(recent.loc[c,'composition']),
        f"[{recent.loc[c,'delta_low']:.4f}, {recent.loc[c,'delta_high']:.4f}]",number(recent.loc[c,'delta_q'],5)] for c in hd.PRIMARY]
    rank_toxic=current[(current.classifier=='detox_toxicity')&(current.model=='unadjusted')].iloc[0]
    rank_adjusted=current[(current.classifier=='detox_toxicity')&(current.model=='genre_adjusted')].iloc[0]
    sparse=d[(d.comparison==LEGACY)&(d.weighting=='song_month')&(d.classifier=='detox_toxicity')&d['sparse']]
    restrictions=[]
    for c in CONTENT:
        f=s[(s.comparison==LEGACY)&(s.classifier==c)&(s.analysis=='genre_restriction')]
        restrictions.append([NAMES[c]]+[number(f[f.scenario==name].within_percent.iloc[0],1)+'%' for name in ['genre_high','genre_not_low','six_largest_genres','common_support_30_songs']])
    text=f'''# Historical change and genre decomposition findings

This completed analysis describes the existing Billboard month-end population.
It does not identify COVID effects, recover missing lyrics, or independently
confirm findings from a new dataset. All 42 classifier scores and all 16 original
genres remain in the descriptive accounting; formal uncertainty covers the 11
prespecified dimensions.

## 1. Audit of the Milestone 2 claims

**The original five percentages remain unverified.** Their provenance is the
group's Milestone 2 report, Question 4, as supplied by the user. Original code,
the exact six-genre set, weighting and reference-period convention were unavailable
and were not found in the repository/history. Consequently this is an independent
recalculation, not a claim to have reproduced an unknown original implementation.
Methods were not adjusted to match those percentages.

The primary comparison uses all 16 genres, distinct scored song-months, unchanged
continuous scores and symmetric Kitagawa accounting:

{table(['Dimension','Preliminary within','1990s mean','2015–2024 mean','Change','Within share','Composition share','95% change interval','Change BY q','Within BY q'],core_rows)}

Toxicity, explicit language and substance use pass the global BY threshold for
both total change and within-genre contribution. Sexual-content and violence
changes have positive marginal intervals but do not pass global BY. Percentage
allocations also have substantial uncertainty:

{table(['Dimension','Within share','Marginal 95% within-share interval'],[[NAMES[c],number(legacy.loc[c,'within_percent'],1)+'%',f"[{legacy.loc[c,'within_percent_low']:.1f}%, {legacy.loc[c,'within_percent_high']:.1f}%]"] for c in CONTENT])}

Values above 100% are possible because the composition component can offset the
within component. These intervals concern the observed-score population and do
not include missing-data or measurement uncertainty.

The new within-genre shares differ from the preliminary claims. The exact reason
for each original discrepancy cannot be established without its code. Weighting,
omitted genres, score thresholding and one-sided reference choices can change the
estimand. The current teammate preprocessing exports threshold LyricLens scores
and change genre inclusion; they were preserved and not used here. This is not
evidence that the unavailable original report used those exports.

The [reference-path audit](reference_path_audit.csv) records both sequential
standardization paths. Their average exactly equals the symmetric result.
The six-largest-genre sensitivity is explicitly selected by population counts;
it is not asserted to be the report's unknown six genres.

## 2. Long-run change and its decomposition

Changes are not uniformly monotonic. The following reports every requested period
comparison on the original score scale; 2020–2025 is six complete years, not a decade.

{table(['Comparison']+[NAMES[c] for c in CONTENT+['emotion_love']],historical)}

For 1990s versus 2015–2024, all five content dimensions increase substantially on
their own classifier scales. Within-genre changes account for most of each observed
increase, with a meaningful additional composition component. Love changes by
{legacy.loc['emotion_love','delta']:.4f}, of which {legacy.loc['emotion_love','within_percent']:.1f}% is within-genre under the same accounting.
These are classifier-output changes, not calibrated prevalence or severity of
human-judged lyrical content. Cross-classifier magnitudes are not interchangeable.

For the more recent comparison, report absolute components before percentages:

{table(['Dimension','2010s → 2020–2025 change','Within','Composition','95% change interval','Global BY q'],recent_rows)}

Some recent point ratios exceed 100% because composition offsets within-genre
change. Many total-change intervals include zero, making percent shares unstable.
Even a recent-period mean above the 2010s mean can coexist with a downward slope
after 2020. Period means and breakpoint coefficients answer different questions.

## 3. Which genres contributed most?

Signed score-unit contributions for 1990s versus 2015–2024:

{table(['Dimension','Three largest within contributions','Largest positive composition','Largest negative composition'],contributions)}

Hip-Hop/Rap's growing share makes a large positive composition contribution to
these five dimensions, offset by declining shares of some other genres. R&B/Soul,
Pop and Country often make substantial within-genre contributions. A genre can
have increasing within-genre scores while its declining share offsets that increase
in the aggregate. These allocations are not causal genre effects or judgments
about artists or listeners.

No original genre is silently discarded. For the legacy comparison the sparse
toxicity cells are:

{table(['Genre','Scored songs in 1990s','Scored songs in 2015–2024','Entry/exit convention'],[[r.genre,r.unique_scored0,r.unique_scored1,r.entry_exit_convention] for r in sparse.itertuples()])}

An absent counterperiod mean cannot identify a unique within/composition split.
The primary convention assigns entry/exit contributions to composition; the complete
comparison table also reports the range of within allocations over unknown means
in [0,1]. Sparse observed means are retained and flagged, not treated as precise.

## 4. Weighting, genre confidence and missing lyrics

The legacy within-genre percentages depend on the population being summarized:

{table(['Dimension','Song-month equal weight','Rank-weighted song-months','Unique songs within period'],weight)}

Rank weighting generally changes these shares less than switching to unique-song
weighting. Monthly weights describe chart presence, while unique-song weights
reduce the influence of long-running hits. Repeated observations are not treated
as independent songs in uncertainty estimation.

Genre restrictions also change the target population:

{table(['Dimension','High confidence','High or medium','Six largest genres','≥30 scored songs in both periods'],restrictions)}

Retained population fractions are reported for each restriction in
[sensitivity_results.csv](sensitivity_results.csv). Confidence is an existing
categorical evidence grade, not a calibrated probability of correct classification.

Toxicity-score coverage among all song-months by period:

{table(['Period','Coverage'],[[p,number(cov.loc[p,'coverage'],1)+'%'] for p in hd.PERIODS])}

The historical population is selected differently across periods and genres.
For the legacy comparison, observed-score coverage is
{100*legacy.loc['detox_toxicity','coverage0']:.1f}% versus {100*legacy.loc['detox_toxicity','coverage1']:.1f}%.
Complete-case analysis is not established to be unbiased. Genus-period MAR and
±0.10 expected-missing-score scenarios preserve the direction of the five legacy
content increases, but the unrestricted bounds are much wider:

{table(['Dimension','MAR / ±0.10 scenario change range','Unrestricted [0,1] change bounds'],missing)}

These scenario ranges and bounds are **not confidence intervals**. The outer
bounds deliberately allow worst-case period means and can be wider than bounds
that additionally impose cross-period shared-song constraints. No missing score
was replaced with zero in observed analyses. Only explicit-language and substance-
use increases have positive lower outer bounds in this particular monthly
comparison; that does not establish their decomposition percentages for missing
songs. All other directions require assumptions about the unobserved population.

## 5. Were changes around 2020 unusual?

The fixed January-2020 models use 2014–2025, six years on either side, monthly
seasonal indicators and separate level/slope changes. The table below adds genre
fixed effects. Slopes are changes in score units per year, not total period changes.

{table(['Dimension','Level change','95% level interval','Level BY q','Slope change/year','95% slope interval','Slope BY q','Absolute slope rank'],break_rows)}

{break_pass} of the 22 January-2020 score/model combinations have either primary
break term passing global BY. The original unadjusted toxicity slope change is
{rank_toxic.slope:.4f}/year (absolute rank {int(rank_toxic.slope_absolute_rank_of_11)}/11),
but becomes {rank_adjusted.slope:.4f}/year after additive genre adjustment
(rank {int(rank_adjusted.slope_absolute_rank_of_11)}/11). Several large-looking
unadjusted changes weaken markedly after genre adjustment. This makes composition
a substantive explanation to investigate, not proof of a causal mechanism.

Ten fixed historical alternatives use identical windows; they overlap and provide
coarse descriptive ranks. A first-place rank among eleven dates is not an
independent significance test. March-2020, rank-weighted, confidence-restricted
and quadratic-background alternatives are all retained in the sensitivity table.
No most-dramatic alternative is promoted to a prespecified result.

All genre-adjusted 2020 intervals also include zero under the 12- and 36-month
crossed-block sensitivities. Artist-only or calendar-only sensitivities exclude
zero for some terms; neither accounts for both dependence sources, and these
diagnostic intervals are not multiplicity-corrected discoveries.

The results do not support a reliable, genre-independent COVID-breakpoint claim.
There are only six post-2020 years and few effective two-year calendar blocks.
Artist-credit dependence, non-linear historical trends, changing coverage, genre
classification and concurrent events limit causal and breakpoint interpretation.

## 6. Statistical status and validation

One global BY family contains all **715** prespecified primary terms. **{count}**
pass q≤0.05; this does not make the analysis independently confirmed.

{table(['Family','Primary terms','Global BY passes'],[[name,int(r['size']),int(r['sum'])] for name,r in summary_by.iterrows()])}

The uniform refinement from 999 to 9,999 resamples is documented in the
[precision audit](precision_audit.json); all original coarse tests are retained.
No candidate-specific precision refinement occurred. Crossed artist/calendar
resampling preserves repeated songs within exact artist credits and models
short-range temporal dependence. Separate 12-/36-month, artist-only and calendar-
only sensitivities and HAC intervals are published. Neither this approximate
resampling scheme nor BY eliminates selection bias or classifier measurement error.
For all five legacy content-score increases, marginal total-change intervals
remain positive in each of the four dependence sensitivities; this does not
upgrade the sexual-content or violence results to corrected significance.

All **882** weighted comparisons reconcile; maximum absolute arithmetic discrepancy
is {json.loads((PUBLIC/'validation.json').read_text())['max_reconciliation_error']:.3g}.
Independent direct weighted means and the two reference-period paths agree.
The analysis contains **79,194 distinct song-months**, **27,039 song identities**,
and **9,558 exact artist credits** across 1960–2025. All protected source and prior
artifact hashes match. No dataset, score, genre or earlier result was rewritten.
The full precision analysis took **{execution['seconds']:.1f} seconds** with peak
process RSS **{execution['peak_rss_bytes']/1024**2:.1f} MiB**; test/render time is separate.

## 7. Figures and term-paper recommendations

{table(['Figure','Use'],[[f"[{r['name']}]({r['svg']})",r['description']] for r in index])}

Lead with the legacy decomposition and all-genre contributions, then show weighting
and missingness sensitivity. Use the 2020 forest plot alongside its historical
placebo comparison so a large raw change is not presented without context.
The trajectory panels establish the broader, non-monotonic history.

The defensible conclusion is that large long-run observed changes reflect both
within-genre movement and changing representation, with the within component
usually larger in the legacy comparison. Exact percentages depend on weighting
and coverage. A distinctive, genre-independent 2020 disruption is not established.
No additional data acquisition or discovery campaign was launched.
'''
    # Keep terminology tied to the actual original taxonomy.
    text=text.replace('Genus-period MAR','Genre-period MAR')
    (PUBLIC/'findings.md').write_text(text)


def manifest():
    paths=[p for p in PUBLIC.rglob('*') if p.is_file() and p.name!='artifact_manifest.json' and '__pycache__' not in p.parts]
    sources=[ROOT/'src/historical_decomposition.py',ROOT/'tests/test_historical_decomposition.py',Path(__file__).resolve()]
    sources.extend(ROOT/p for p in ['README.md','docs/commands.md','docs/repository_structure.md','src/README.md',
                                   'tests/test_relationship_phase1_publication.py'])
    extra=ROOT/'tests/test_historical_decomposition_publication.py'
    if extra.exists():sources.append(extra)
    hd.write_json(PUBLIC/'artifact_manifest.json',dict(sha256={str(p.relative_to(ROOT)):hd.descriptive.sha(p) for p in sorted(paths)},
        sources_sha256={str(p.relative_to(ROOT)):hd.descriptive.sha(p) for p in sources},
        input_sha256=hd.descriptive.sha(hd.moving.INPUT),private_bootstrap_arrays_committed=False))


def render():
    tables=load();paths=reference_paths(tables);index=figures(tables);findings(tables,index,paths);manifest()
    print(json.dumps(dict(status='PASS',figures=len(index),findings='analysis/historical_decomposition/findings.md')))


if __name__=='__main__':render()
