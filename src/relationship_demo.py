"""Read-only classroom view of measured discovery pilot results; never fits/searches."""
from pathlib import Path
import gzip
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import streamlit as st

sys.path.insert(0,str(Path(__file__).resolve().parent))
import relationship_discovery_spec as spec


@st.cache_data
def results():
    return json.loads(gzip.decompress((spec.PUBLIC/'pilot_results/results.json.gz').read_bytes()))


@st.cache_data
def observations():
    raw=pd.read_csv(spec.ROOT/'data/public/songs.csv',dtype={'song_id':str},keep_default_na=False,na_values=[''])
    frame=spec.old.original.convert(raw)
    frame['first_iso']=raw.first_chart_date;frame['last_iso']=raw.last_chart_date
    frame['debut_year']=pd.to_datetime(raw.first_chart_date).dt.year
    secondary=raw.secondary_genres.map(lambda v:json.loads(v) if pd.notna(v) else None)
    for genre in spec.GENRES:frame['secondary_genre::'+genre]=secondary.map(lambda v:float(genre in v) if v is not None else np.nan)
    frame['_hash']=pd.util.hash_pandas_object(frame.song_id,index=False).to_numpy()
    return frame


def plot_curve(row,frame):
    diagnostics=row['diagnostics'];labels=[f"{r['period'][0]}–{r['period'][1]-1}" for r in diagnostics]
    period=st.selectbox('Curve evaluation period',labels,index=len(labels)-1,key='curve_period')
    detail=diagnostics[labels.index(period)];a,b=detail['period'];x=row['predictors'][0];y=row['target']
    observed=frame.loc[frame.first_iso.ge(f'{a}-01-01') & frame.last_iso.lt(f'{b}-01-01')].dropna(subset=[x,y])
    observed=observed.sort_values('_hash').head(1200)
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    if len(observed):ax.scatter(observed[x],observed[y],s=8,alpha=.15,color='#555555',label='Actual held-out observations')
    ax.plot(detail['x'],detail['linear'],label='OLS',color='#888888',linewidth=2)
    ax.plot(detail['x'],detail['nonlinear'],label=detail['selected_method'],color='#2166ac',linewidth=2)
    ax.set(xlabel=x,ylabel=y);ax.legend();st.pyplot(fig);plt.close(fig)
    st.caption(f"Training-fitted curves; method chosen by inner historical validation. Up to 1,200 actual observations are shown. Published metrics use every eligible held-out song. {detail['extrapolation_rows']} evaluation inputs were outside the training range.")
    st.session_state['supporting_observations']=len(observed)


def predictive_details(row,genre):
    valid=[f for f in row['folds'] if f['status']=='ok']
    frame=pd.DataFrame([dict(period=f"{f['period'][0]}–{f['period'][1]-1}",n=f['n_test'],predictor_complete=f['n_test_predictor_complete'],
        model_r2=f['metrics']['r2'],comparison_r2=f['comparison_metrics']['r2'],model_rmse=f['metrics']['rmse'],
        comparison_rmse=f['comparison_metrics']['rmse'],relative_mse_improvement=f['relative_mse_improvement'],
        selected_method=f['selected_method']) for f in valid])
    st.dataframe(frame,hide_index=True,width='stretch')
    if len(frame):st.bar_chart(frame.set_index('period')[['model_r2','comparison_r2']])
    st.caption('Negative R² remains visible. A model can improve on its comparison while still predict poorly.')
    if row['family']!='nonlinear':
        records=[]
        for detail in row['diagnostics']:
            conditional=detail.get('conditional_correlations',{})
            for g in conditional.get('subgroups',[]):
                if genre!='All genres' and row['family']=='genre_interaction' and g['group']!=genre:continue
                records.append(dict(period=f"{detail['period'][0]}–{detail['period'][1]-1}",pooled_rho=conditional.get('marginal_spearman'),
                    partial_rho=conditional.get('partial_spearman'),**g))
        st.dataframe(pd.DataFrame(records),hide_index=True,width='stretch')
        st.caption('Subgroup correlations and sign reversals are descriptive. Inadequate groups have no reported correlation; they are not hidden.')


def pair_details(row,frame):
    cols=st.columns(4)
    for col,key,label in zip(cols,['pearson','spearman','mutual_information_nats','distance_correlation'],['Pearson','Spearman','Binned MI (nats)','Distance correlation']):
        value=row.get(key);col.metric(label,'Not applicable' if value is None else f'{value:.4f}')
    st.caption('These methods have different scales. The p-value permutes within debut year; it does not test the pooled association without calendar adjustment.')
    x=row['predictors'][0];y=row['target'];f=frame.dropna(subset=[x,y])
    st.write(f'{len(f):,} observed pairs match the supporting-data filters.')
    xcat=spec.kind(x)=='categorical';ycat=spec.kind(y)=='categorical'
    if xcat and ycat:st.dataframe(pd.crosstab(f[x],f[y]),width='stretch')
    elif xcat or ycat:
        category=x if xcat else y;value=y if xcat else x
        summary=f.groupby(category)[value].agg(['count','mean','median']);st.dataframe(summary,width='stretch')
        st.bar_chart(summary[['mean']])
    else:
        sample=f.sort_values('_hash').head(1500);fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
        ax.scatter(sample[x],sample[y],s=8,alpha=.25);ax.set(xlabel=x,ylabel=y);st.pyplot(fig);plt.close(fig)
    st.session_state['supporting_observations']=len(f)


def temporal_details(row,genre,years):
    annual=pd.DataFrame([r for r in row['annual'] if r['genre']==genre and years[0]<=r['year']<=years[1]])
    if len(annual):st.line_chart(annual.set_index('year')[['rho']]);st.dataframe(annual,hide_index=True,width='stretch')
    else:st.info('No annual estimates meet the sample/variation requirements for these filters.')
    comparisons=[r for r in row['breakpoints'] if r['genre']==genre]
    st.dataframe(pd.DataFrame(comparisons),hide_index=True,width='stretch')
    st.warning('Five annual points per side: breakpoint intervals are descriptive. No breakpoint is called significant. 2020 is compared with 1980, 1990, 2000 and 2010.')
    rolling=pd.DataFrame([r for r in row['rolling'] if r['genre']==genre and r['adequate']])
    if len(rolling):st.line_chart(rolling.set_index('start')[['rho']]);st.caption('Ten-year windows overlap by five years; they are not independent tests.')


def structure_details(row,genre):
    options=[f"{r['period'][0]}–{r['period'][1]-1}" for r in row['folds']]
    label=st.selectbox('Structure evaluation period',options,index=len(options)-1,key='structure_period')
    fold=row['folds'][options.index(label)]
    st.write(f"Training songs: {fold['n_train']:,}; evaluation songs: {fold['n_test']:,}.")
    st.write('Three block-refit stability measurements:',fold['stability_values'])
    if row['method']=='pca':
        load=np.array(fold['loadings']);pc=int(st.selectbox('Component',list(range(1,row['k']+1)),key='component'))-1
        order=np.argsort(np.abs(load[pc]))[-15:]
        chart=pd.DataFrame({'variable':[row['predictors'][i] for i in order],'loading':load[pc,order]}).set_index('variable')
        st.bar_chart(chart,horizontal=True)
        profiles=[g for g in fold['genre_profiles'] if genre=='All genres' or g['genre']==genre]
        st.dataframe(pd.DataFrame(profiles),hide_index=True,width='stretch')
    else:
        st.write('Silhouette:',fold['silhouette']);st.dataframe(pd.DataFrame(fold['cluster_profiles']),hide_index=True,width='stretch')
        st.caption('Cluster profiles summarize the complete evaluation cohort; genre filters do not refit or redefine clusters.')
    st.warning(row['uncertainty_warning'])


def main():
    st.set_page_config(page_title='Music relationship discovery',layout='wide')
    st.title('Music relationship discovery')
    st.warning('EXPLORATORY PILOT — this population has already been inspected. No independently confirmed or causal discovery is claimed.')
    if not (spec.PUBLIC/'pilot_results/results.json.gz').exists():st.error('Published pilot results are missing. See the discovery README.');return
    all_rows=results()
    family=st.sidebar.selectbox('Relationship family',sorted({r['family'] for r in all_rows}),index=1,key='family')
    include=st.sidebar.checkbox('Include reconstruction controls',value=False,key='include_reconstruction')
    rows=[r for r in all_rows if r['family']==family and (include or r['category'][0]!='A')]
    target=st.sidebar.selectbox('Target or score panel',sorted({r['target'] for r in rows}),key='target')
    rows=[r for r in rows if r['target']==target]
    labels={r['candidate_id']:' + '.join(r['predictors'][:3])+(' …' if len(r['predictors'])>3 else '')+
        (' | condition: '+r['conditioner'] if r['conditioner'] else '')+
        (' | '+r['method']+' k='+str(r['k']) if 'method' in r else '')+
        (' | q='+str(r['quantile']) if 'quantile' in r else '') for r in rows}
    chosen=st.sidebar.selectbox('Relationship',list(labels),format_func=lambda v:labels[v],key='relationship')
    row=next(r for r in rows if r['candidate_id']==chosen)
    genre=st.sidebar.selectbox('Supporting-data genre',['All genres']+spec.GENRES,key='genre')
    years=st.sidebar.slider('Supporting-data debut years',1958,2025,(1958,2025),key='years')
    st.sidebar.markdown('[Existing OLS demo](http://127.0.0.1:8501)')
    st.caption(row['category']+' · '+row['family'])
    if row['category'][0]=='A':st.warning('Reconstruction control: retained in the inventory, excluded from the nontrivial leaderboards.')
    metrics=st.columns(4)
    metrics[0].metric('Measured effect','Unavailable' if row.get('effect') is None else f"{row['effect']:.4f}")
    metrics[1].metric('Outer R²','Not applicable' if row.get('r2') is None else f"{row['r2']:.4f}")
    metrics[2].metric('Evaluation/association N',f"{row['n']:,}")
    metrics[3].metric('Global BY q','Descriptive only' if row.get('q_by_global') is None else f"{row['q_by_global']:.5f}")
    st.write(row.get('effect_name','Coverage failure'));st.caption(row['multiple_testing_status'])
    if row.get('ci_low') is not None:st.write(f"95% fixed-model block interval: [{row['ci_low']:.4f}, {row['ci_high']:.4f}]")
    elif row.get('effect_interval'):st.write('95% fixed-analysis block interval:',row['effect_interval'].get('interval'))
    st.info('Genre and year filters change supporting observations and descriptive views. Published evaluation metrics remain the saved complete-cohort results; filters do not select or refit a model.')
    st.session_state['displayed_candidate_id']=row['candidate_id'];st.session_state['displayed_effect']=row.get('effect');st.session_state['displayed_r2']=row.get('r2')
    if family=='temporal':temporal_details(row,genre,years)
    elif family=='structure':structure_details(row,genre)
    else:
        raw=observations();f=raw.loc[raw.last_iso.lt('2026-01-01') & raw.debut_year.between(*years)]
        if genre!='All genres':f=f.loc[f.primary_genre.eq(genre)]
        if family=='pairwise':pair_details(row,f)
        else:
            predictive_details(row,genre)
            if family=='nonlinear':plot_curve(row,f)
    with st.expander('Predictors, sample sizes and reliability details'):
        st.write('Predictors:',row['predictors']);st.write('Conditioner:',row.get('conditioner'))
        for key in ['leakage_warning','inference_warning','uncertainty_warning']:
            if row.get(key):st.write(row[key])
        st.json({k:row[k] for k in ['four_year_sensitivity','effect_interval','minimum_group_n','group_coverage_warning'] if k in row})
    st.download_button('Download this measured relationship',json.dumps(row,indent=2),file_name=row['candidate_id']+'.json',mime='application/json')


if __name__=='__main__':main()
