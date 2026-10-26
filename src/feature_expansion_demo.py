"""Read-only professor demonstration using published models and saved predictions."""
from pathlib import Path
import gzip
import json
import sys
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0,str(Path(__file__).resolve().parent))
from feature_expansion_predict import predict_export

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'analysis/feature_expansion_v1'
DATA=ROOT/'data/public/feature_expansion_v1'
LABELS=dict(top10='Reach Top 10',long_chart='At least 13 chart weeks',best_rank='Best chart rank',chart_weeks='Chart weeks',chart_points='Chart points')


@st.cache_data(show_spinner=False)
def load_data():
    f=pd.read_csv(DATA/'song_features.csv.xz');o=pd.read_csv(DATA/'song_outcomes.csv.xz')
    predictions=pd.read_csv(PUBLIC/'selected_predictions.csv.gz')
    comparison=pd.read_csv(PUBLIC/'model_comparison.csv');selected=pd.read_csv(PUBLIC/'selected_models.csv')
    comparison=comparison.merge(selected[['track','target','configuration','method']],on=['track','target','configuration','method'],validate='many_to_one')
    return f.merge(o,on='song_id',validate='one_to_one'),predictions,comparison,pd.read_csv(PUBLIC/'permutation_importance.csv')


@st.cache_data(show_spinner=False)
def load_model(track,target,configuration):
    return json.loads(gzip.decompress((PUBLIC/'models'/f'{track}_{target}_{configuration}.json.gz').read_bytes()))


def main():
    st.set_page_config(page_title='Billboard debut prediction',layout='wide')
    st.title('Chart performance at Billboard debut')
    st.write('Predictions cover the first 26 weeks after a song first appears on the Hot 100. The models apply to songs that have already charted.')
    st.warning('Exploratory historical evaluation: the 2018-onward population was inspected in earlier experiments. These results are not independent confirmation or causal effects.')
    track_label=st.radio('Information available to the model',['Known at chart publication','Retrospective content comparison'],horizontal=True)
    track='strict' if track_label=='Known at chart publication' else 'retrospective'
    if track=='retrospective':st.info('This comparison adds modern lyric measurements, genre labels and recording-credit metadata. Their availability at the historical debut is unverified.')
    configuration=st.selectbox('Feature configuration',['combined','baseline','new_only'],format_func=lambda s:dict(combined='Existing + new features',baseline='Existing eligible baseline',new_only='New features only')[s])
    f,predictions,comparison,importance=load_data()
    held=predictions[(predictions.track==track)&(predictions.target=='long_chart')&(predictions.configuration==configuration)&(predictions.partition=='test')]
    examples=f[f.song_id.isin(held.song_id)].sort_values(['first_chart_date','song_id'])
    lookup=examples.set_index('song_id');labels={r.song_id:f'{r.title} — {r.artist} ({r.first_chart_date})' for r in examples.itertuples()}
    sid=st.selectbox('Song from the evaluation population',examples.song_id.tolist(),format_func=labels.get)
    row=lookup.loc[[sid]].reset_index();record=row.iloc[0]
    st.subheader(record.title+' — '+record.artist)
    st.caption(f'First chart: {record.first_chart_date} · Debut rank: {int(record.debut_rank)} · Outcome window ends: {record.window_end_26} (exclusive)')
    display_cols=st.columns(5)
    output=[]
    for col,target in zip(display_cols,LABELS):
        if target=='top10' and record.debut_rank<=10:
            col.metric(LABELS[target],'Known at debut');col.caption('Already entered in the Top 10; excluded from this classifier.');continue
        bundle=load_model(track,target,configuration);value=float(predict_export(bundle,row)[0]);actual=record[target+'_26']
        saved=predictions[(predictions.track==track)&(predictions.target==target)&(predictions.configuration==configuration)&predictions.song_id.eq(sid)&predictions.partition.eq('test')]
        if len(saved)!=1 or not np.isclose(value,saved.prediction.iloc[0],rtol=1e-9,atol=1e-9):raise ValueError('Saved prediction replay differs')
        if target in ['top10','long_chart']:
            col.metric(LABELS[target],f'{value:.1%}');col.caption(f'Actual: {"Yes" if actual else "No"} · Decision threshold: {bundle["threshold"]:.2f}')
        else:col.metric(LABELS[target],f'{value:.1f}');col.caption(f'Actual in 26 weeks: {int(actual):,}')
        output.append(dict(outcome=LABELS[target],prediction=value,actual_in_26_weeks=actual))
    st.caption('Probabilities are the fitted model’s raw estimates. Calibration varies by era; the tables below report Brier scores. Numerical predictions can fall outside physical bounds because evaluation uses the unmodified fitted models.')
    naive_all=pd.read_csv(PUBLIC/'simple_baselines.csv')
    top_metric=comparison[(comparison.track==track)&comparison.target.eq('top10')&comparison.configuration.eq(configuration)&comparison.partition.eq('test')].iloc[0]
    prevalence_metric=naive_all[(naive_all.track==track)&naive_all.target.eq('top10')&naive_all.baseline.eq('training_prevalence')&naive_all.partition.eq('test')].iloc[0]
    if top_metric.brier>prevalence_metric.brier:
        st.warning(f'Top-10 probability calibration is weak in this evaluation: Brier {top_metric.brier:.3f}, versus {prevalence_metric.brier:.3f} for the training-prevalence baseline (lower is better). Treat the displayed probabilities as raw model estimates.')
    with st.expander('Known chart history at debut',expanded=True):
        fields=['credit_prior_song_count','credit_prior_top10_song_count','credit_prior_top40_song_count','credit_prior_chart_points','credit_prior_chart_weeks','credit_prior_best_rank','credit_days_since_last_entry','credit_recent_chart_presence','credit_recent_points_slope','same_credit_debut_cluster_size','debut_competing_new_entry_count']
        st.dataframe(pd.DataFrame({'Feature':fields,'Observed value':[record[c] for c in fields]}),hide_index=True,width='stretch')
        st.caption('History uses strictly earlier chart dates and exact full artist credits. Collaborations with different credit strings have separate histories.')
    with st.expander('Observed full history for context'):
        st.write(f'Best rank {int(record.observed_lifetime_best_rank)}; {int(record.observed_lifetime_chart_weeks)} chart weeks; {int(record.observed_lifetime_chart_points):,} points through {record.observed_last_chart_date}.')
        st.caption('Full observed histories are descriptive only. Later returns remain possible; these are not the model’s fixed-horizon targets.')
    st.subheader('Evaluation accuracy and baseline comparison')
    target=st.selectbox('Outcome to inspect',list(LABELS),format_func=LABELS.get)
    rows=comparison[(comparison.track==track)&(comparison.target==target)&comparison.partition.eq('test')].copy()
    metrics=['balanced_accuracy','precision','recall','f1','roc_auc','pr_auc','brier','ece_10_bins'] if target in ['top10','long_chart'] else ['r2','mae','rmse','p90_absolute_error']
    st.dataframe(rows[['configuration','method','n']+metrics],hide_index=True,width='stretch')
    naive=naive_all[(naive_all.track==track)&(naive_all.target==target)&naive_all.partition.eq('test')]
    st.dataframe(naive[['baseline','n']+metrics],hide_index=True,width='stretch')
    st.caption('All three feature configurations use the same eligible songs and splits. Models were selected on 2010–2017 validation data and fitted only to pre-2010 training data; target windows crossing boundaries are excluded.')
    st.subheader('Features the combined model uses')
    imp=importance[(importance.track==track)&(importance.target==target)].sort_values('mean_drop',ascending=False).head(10)
    st.bar_chart(imp.set_index('feature')['mean_drop'],horizontal=True)
    st.caption('Validation permutation importance: loss of balanced accuracy, or increase in MAE, after shuffling one feature. Correlated features share information; importance does not establish causation or explain one song by itself.')
    if target in ['top10','long_chart']:
        selected_row=rows[rows.configuration.eq(configuration)].iloc[0]
        st.dataframe(pd.DataFrame([[int(selected_row.tn),int(selected_row.fp)],[int(selected_row.fn),int(selected_row.tp)]],index=['Actual no','Actual yes'],columns=['Predicted no','Predicted yes']),width='stretch')
        calibration=pd.read_csv(PUBLIC/'calibration.csv');calibration=calibration[(calibration.track==track)&(calibration.target==target)&calibration.configuration.eq(configuration)&calibration.partition.eq('test')]
        st.line_chart(calibration,x='mean_probability',y='observed_rate')
    st.caption('Run locally from the existing Streamlit environment. This page reads published artifacts and replays saved models; it does not train models or retrieve lyrics.')


if __name__=='__main__':main()
