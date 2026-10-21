"""Read-only classroom view of measured discovery results; never fits/searches."""
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


@st.cache_data(max_entries=2)
def results(collection='Preserved pilot',artifact_token=None):
    path=spec.PUBLIC/('full_phase1/demo_results.json.gz' if collection=='Full Phase 1' else 'pilot_results/results.json.gz')
    rows=json.loads(gzip.decompress(path.read_bytes()))
    for row in rows:
        if 'priority_cross_domain' not in row:
            domains=[spec.domain(n) for n in [row['target'],*row['predictors']]] if row['family']!='structure' else []
            broad=['lyrics' if d.startswith('lyrical_') else d for d in domains]
            row['priority_cross_domain']=row['category'].startswith('C') and len(set(broad))>1
    return rows


@st.cache_data
def selected_plot_data():
    path=spec.PUBLIC/'full_phase1/selected_plot_data.json.gz'
    return json.loads(gzip.decompress(path.read_bytes())) if path.exists() else {}


@st.cache_data(max_entries=8)
def target_details(family,target,artifact_token=None):
    mapping=json.loads((spec.PUBLIC/'full_phase1/demo_detail_files.json').read_text())
    path=spec.PUBLIC/'full_phase1'/mapping[family][target]
    return {r['candidate_id']:r for r in json.loads(gzip.decompress(path.read_bytes()))}


@st.cache_data
def artist_checks():
    path=spec.PUBLIC/'full_phase1/artist_sensitivity.csv'
    return pd.read_csv(path,dtype={'candidate_id':str}).set_index('candidate_id') if path.exists() else pd.DataFrame()


def ranking_key(row):
    if row['family']=='pairwise':
        return (row.get('status')!='ok',row.get('effect_name',''),row.get('q_by_global',1)>.05,-(row.get('stability_fraction') or 0),-abs(row.get('effect') or 0),row['candidate_id'])
    return (not row.get('positive_stable_performance_tier',False),
        -(row.get('worst_period_relative_improvement') if row.get('worst_period_relative_improvement') is not None else -float('inf')),
        -(row.get('ci_low') if row.get('ci_low') is not None else -float('inf')),row['candidate_id'])


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


def axis_label(name):
    unit='months since 1970-01' if name in {'first_snapshot_month','last_snapshot_month'} else 'days since 1970-01-01' if name in spec.old.original.DATES else 'calendar year' if name=='mb_release_year' else 'classifier score' if name in spec.old.original.SCORES else 'seconds' if name in spec.old.original.DURATIONS else None
    return name.replace('_',' ')+(f' ({unit})' if unit else '')


def plot_curve(row,frame,years=(1958,2025)):
    diagnostics=[d for d in row['diagnostics'] if d['period'][0]<=years[1] and d['period'][1]-1>=years[0]]
    if not diagnostics:st.info('No saved outer-evaluation curve overlaps the selected years.');return
    labels=[f"{r['period'][0]}–{r['period'][1]-1}" for r in diagnostics]
    period=st.selectbox('Curve evaluation period',labels,index=len(labels)-1,key='curve_period')
    detail=diagnostics[labels.index(period)];a,b=detail['period'];x=row['predictors'][0];y=row['target']
    observed=frame.loc[frame.first_iso.ge(f'{a}-01-01') & frame.last_iso.lt(f'{b}-01-01')].dropna(subset=[x,y])
    observed=observed.sort_values('_hash').head(1200)
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    if len(observed):ax.scatter(observed[x],observed[y],s=8,alpha=.15,color='#555555',label='Actual held-out observations')
    ax.plot(detail['x'],detail['linear'],label='OLS',color='#888888',linewidth=2)
    ax.plot(detail['x'],detail['nonlinear'],label=detail['selected_method'],color='#2166ac',linewidth=2)
    ax.set(xlabel=axis_label(x),ylabel=axis_label(y));ax.legend();st.pyplot(fig);plt.close(fig)
    st.caption(f"Training-fitted curves; method chosen by inner historical validation. Up to 1,200 actual observations are shown. Published metrics use every eligible held-out song. {detail['extrapolation_rows']} evaluation inputs were outside the training range.")
    if detail.get('plot_grid_note'):st.caption(detail['plot_grid_note'])
    st.session_state['supporting_observations']=len(observed)


def predictive_details(row,genre,years=(1958,2025)):
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
            if detail['period'][0]>years[1] or detail['period'][1]-1<years[0]:continue
            conditional=detail.get('conditional_correlations',{})
            for g in conditional.get('subgroups',[]):
                if genre!='All genres' and row['family']=='genre_interaction' and g['group']!=genre:continue
                records.append(dict(period=f"{detail['period'][0]}–{detail['period'][1]-1}",pooled_rho=conditional.get('marginal_spearman'),
                    partial_rho=conditional.get('partial_spearman'),**g))
        st.dataframe(pd.DataFrame(records),hide_index=True,width='stretch')
        st.caption('Subgroup correlations and sign reversals are descriptive. Saved whole evaluation windows overlap the selected years; no subset is refitted. Inadequate groups have no reported correlation; they are not hidden.')
        if row['family']=='genre_interaction':
            support=[r for r in row.get('subgroup_results',[]) if r['period'][0]<=years[1] and r['period'][1]-1>=years[0] and (genre=='All genres' or r['genre']==genre)]
            with st.expander('Genre coverage and held-out loss reductions'):
                st.dataframe(pd.DataFrame(support),hide_index=True,width='stretch')
                st.caption('Positive MSE improvement means lower squared error than the additive model. Prediction counts include training-imputed predictors; correlation uses complete pairs and may be unavailable.')


def pair_details(row,frame):
    cols=st.columns(4)
    for col,key,label in zip(cols,['pearson','spearman','mutual_information_nats','distance_correlation'],['Pearson','Spearman','Binned MI (nats)','Distance correlation']):
        value=row.get(key);col.metric(label,'Not applicable' if value is None else f'{value:.4f}')
    st.caption('These methods have different scales. The p-value permutes within debut year; it does not test the pooled association without calendar adjustment.')
    if row.get('distance_correlation_n'):
        st.caption(f"Distance correlation uses {row['distance_correlation_n']:,} fixed-hash songs; the association N above counts all complete pairs. Binned mutual information uses all complete pairs.")
    if row.get('knn_mutual_information_n'):
        st.caption(f"The downloadable record also includes five-neighbour mutual information from {row['knn_mutual_information_n']:,} fixed-hash songs.")
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
        ax.scatter(sample[x],sample[y],s=8,alpha=.25);ax.set(xlabel=axis_label(x),ylabel=axis_label(y));st.pyplot(fig);plt.close(fig)
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
    collections=['Full Phase 1','Preserved pilot'] if (spec.PUBLIC/'full_phase1/demo_results.json.gz').exists() else ['Preserved pilot']
    collection=st.sidebar.selectbox('Result collection',collections,key='collection')
    st.warning(('EXPLORATORY FULL PHASE 1' if collection=='Full Phase 1' else 'EXPLORATORY PILOT')+' — this population has already been inspected. No independently confirmed or causal discovery is claimed.')
    result_path=spec.PUBLIC/('full_phase1/demo_results.json.gz' if collection=='Full Phase 1' else 'pilot_results/results.json.gz')
    artifact_token=result_path.stat().st_mtime_ns
    all_rows=results(collection,artifact_token)
    if collection=='Full Phase 1':st.caption('All 9,159 approved candidates are retained. Global BY uses the complete campaign, including failed and reconstruction controls.')
    family=st.sidebar.selectbox('Relationship family',sorted({r['family'] for r in all_rows}),index=1,key='family')
    include=st.sidebar.checkbox('Include reconstruction controls',value=False,key='include_reconstruction')
    cross_only=st.sidebar.checkbox('Cross-domain relationships only',value=False,key='cross_only')
    different_sources=st.sidebar.checkbox('Broader information domains only',value=False,key='different_sources',help='Groups both lyrical affect and content as lyrics, then compares with genre, calendar, chart outcomes and catalog metadata. Domains can still share source data.')
    rows=[r for r in all_rows if r['family']==family and (include or r['category'][0]!='A')]
    if cross_only:rows=[r for r in rows if r['category'].startswith('C')]
    if different_sources:rows=[r for r in rows if r.get('priority_cross_domain',False)]
    if not rows:st.info('No saved relationships match these filters.');return
    rows=sorted(rows,key=ranking_key) if collection=='Full Phase 1' else rows
    targets=sorted({v for r in rows for v in [r['target'],*r['predictors']]}) if family=='pairwise' else sorted({r['target'] for r in rows})
    target=st.sidebar.selectbox('Variable of interest' if family=='pairwise' else 'Target or score panel',targets,key='target')
    rows=[r for r in rows if target in [r['target'],*r['predictors']]] if family=='pairwise' else [r for r in rows if r['target']==target]
    def predictor_label(r):
        if family=='pairwise':return r['target'] if target!=r['target'] else r['predictors'][0]
        return ' + '.join(r['predictors'][:3])+(' …' if len(r['predictors'])>3 else '')
    labels={r['candidate_id']:predictor_label(r)+
        (' | condition: '+r['conditioner'] if r['conditioner'] else '')+
        (' | '+r['method']+' k='+str(r['k']) if 'method' in r else '')+
        (' | q='+str(r['quantile']) if 'quantile' in r else '') for r in rows}
    # Store the displayed strings in the widget. Dynamic format_func mappings
    # can leave a stale ID behind when target/family options change on rerun.
    options={label+' ['+candidate[:8]+']':candidate for candidate,label in labels.items()}
    if st.session_state.get('relationship') not in options:
        st.session_state['relationship']=next(iter(options))
    choice=st.sidebar.selectbox('Relationship',list(options),key='relationship')
    chosen=options[choice]
    row=next(r for r in rows if r['candidate_id']==chosen)
    if collection=='Full Phase 1':row=target_details(family,row['target'],artifact_token)[chosen]
    genre=st.sidebar.selectbox('Supporting-data genre',['All genres']+spec.GENRES,key='genre')
    years=st.sidebar.slider('Supporting-data debut years',1958,2025,(1958,2025),key='years')
    st.sidebar.markdown('[Existing OLS demo](http://127.0.0.1:8501)')
    st.caption(row['category']+' · '+row['family'])
    if family!='structure' and all(spec.domain(v).startswith('lyrical_') for v in [row['target'],*row['predictors']]):
        st.caption('Both sides are classifier measurements of lyrics. Their relationship can reflect shared measurement and conceptual overlap, including some category C pairs.')
    if collection=='Full Phase 1':
        st.dataframe(pd.DataFrame([dict(rank=i+1,predictor_or_other_variable=predictor_label(r),category=r['category'][0],
            effect=r.get('effect'),outer_r2=r.get('r2'),comparison_r2=r.get('comparison_metrics',{}).get('r2'),
            mse_gain_percent=100*r['relative_mse_improvement'] if r.get('relative_mse_improvement') is not None else None,
            positive_period_fraction=r.get('stability_fraction'),global_by_q=r.get('q_by_global'),n=r['n'],status=r['status']) for i,r in enumerate(rows)]),hide_index=True,width='stretch')
        st.caption('Predictive order: supported positive performance tier, then worst-period improvement and interval lower bound. Pairwise order stays within effect type, then BY status, annual sign stability and magnitude. No combined novelty score.')
    if row['category'][0]=='A':st.warning('Reconstruction control: retained in the inventory, excluded from the nontrivial leaderboards.')
    metrics=st.columns(4)
    metrics[0].metric('Measured effect','Unavailable' if row.get('effect') is None else f"{row['effect']:.4f}")
    metrics[1].metric('Outer R²','Not applicable' if row.get('r2') is None else f"{row['r2']:.4f}")
    metrics[2].metric('Evaluation/association N',f"{row['n']:,}")
    metrics[3].metric('Global BY q','Descriptive only' if row.get('q_by_global') is None else f"{row['q_by_global']:.5f}")
    st.write(row.get('effect_name','Coverage failure'));st.caption(row['multiple_testing_status'])
    if family=='pairwise':st.caption(row['predictors'][0]+' ↔ '+row['target']+'; pairwise association is symmetric.')
    if row.get('ci_low') is not None:st.write(f"95% fixed-model block interval: [{row['ci_low']:.4f}, {row['ci_high']:.4f}]")
    elif row.get('effect_interval'):st.write('95% fixed-analysis block interval:',row['effect_interval'].get('interval'))
    st.info('Genre and year filters change supporting observations and descriptive views. Published evaluation metrics remain the saved complete-cohort results; filters do not select or refit a model.')
    st.session_state['displayed_candidate_id']=row['candidate_id'];st.session_state['displayed_effect']=row.get('effect');st.session_state['displayed_r2']=row.get('r2')
    st.session_state['displayed_collection']=collection
    if row.get('status')!='ok':st.warning('This candidate was retained with status: '+row['status']);return
    if family=='temporal':temporal_details(row,genre,years)
    elif family=='structure':structure_details(row,genre)
    else:
        raw=observations();f=raw.loc[raw.last_iso.lt('2026-01-01') & raw.debut_year.between(*years)]
        if genre!='All genres':f=f.loc[f.primary_genre.eq(genre)]
        if family=='pairwise':pair_details(row,f)
        else:
            predictive_details(row,genre,years)
            if family=='nonlinear':plot_curve(row,f,years)
    if collection=='Full Phase 1':
        check=artist_checks()
        if row['candidate_id'] in check.index:
            st.write('Artist-credit sensitivity (descriptive):',check.loc[row['candidate_id']].to_dict())
            st.caption('Fixed models/ranks; exact credit clusters; collaborations may split performers. This is separate from temporal uncertainty and adds no significance claim.')
        detail=selected_plot_data().get(row['candidate_id'])
        if detail:
            with st.expander('Selected finding: fitted genre slopes and actual versus predicted'):
                slopes=pd.DataFrame(detail.get('artist_slopes',[]))
                if len(slopes):
                    if genre!='All genres':slopes=slopes.loc[slopes.genre.eq(genre)]
                    st.dataframe(slopes,hide_index=True,width='stretch')
                points=pd.DataFrame(detail['actual_predicted'])
                st.scatter_chart(points,x='actual',y='predicted')
                st.caption('Fixed hash sample of up to 1,200 outer-evaluation songs. The sample and published metrics retain the complete cohort.')
    with st.expander('Predictors, sample sizes and reliability details'):
        st.write('Predictors:',row['predictors']);st.write('Conditioner:',row.get('conditioner'))
        for key in ['leakage_warning','inference_warning','uncertainty_warning']:
            if row.get(key):st.write(row[key])
        st.json({k:row[k] for k in ['p_value','q_by_family','four_year_sensitivity','effect_interval','minimum_group_n','group_coverage_warning'] if k in row})
    st.download_button('Download this measured relationship',json.dumps(row,indent=2),file_name=row['candidate_id']+'.json',mime='application/json')


if __name__=='__main__':main()
