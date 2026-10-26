"""Bounded chronological model comparison, saved predictions, and interpretation."""
from __future__ import annotations
import argparse
import itertools
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import (balanced_accuracy_score,precision_score,recall_score,f1_score,roc_auc_score,
    average_precision_score,confusion_matrix,brier_score_loss,log_loss,r2_score,mean_absolute_error,mean_squared_error)
from threadpoolctl import threadpool_limits

from feature_expansion_common import (ROOT,PUBLIC,DATA,LOCAL,CONFIG,SEED,SCORES,TARGETS,sha,digest,clean,
    write_csv,write_json,read_json,split_frame,freeze,environment)
from feature_expansion_features import DEFINITIONS
from feature_expansion_predict import Preprocessor,export_estimator,predict_export


def columns(track,configuration):
    base=['debut_rank'] if track=='strict' else ['debut_rank','primary_genre','duration_seconds']+SCORES
    new=[n for n,d in DEFINITIONS.items() if track=='retrospective' or d['historical_availability']=='C']
    return base if configuration=='baseline' else new if configuration=='new_only' else base+new


def load_population(track):
    f=pd.read_csv(DATA/'song_features.csv.xz');o=pd.read_csv(DATA/'song_outcomes.csv.xz');f=f.merge(o,on='song_id',validate='one_to_one')
    if track=='retrospective':f=f[f[SCORES].notna().all(axis=1)&f.lyric_word_count.notna()].copy()
    return f.sort_values('song_id').reset_index(drop=True)


def task_splits(frame,target,horizon=26,**kwargs):
    if target=='top10':frame=frame[frame.debut_rank.gt(10)]
    return split_frame(frame,horizon,**kwargs)


def model(method,parameter,classification):
    if method=='regularized':
        return LogisticRegression(C=parameter,max_iter=2000,solver='lbfgs',random_state=SEED) if classification else Ridge(alpha=parameter)
    if method=='tree':
        cls=DecisionTreeClassifier if classification else DecisionTreeRegressor
        return cls(max_depth=parameter,min_samples_leaf=CONFIG['tree_min_leaf'],random_state=SEED)
    cls=HistGradientBoostingClassifier if classification else HistGradientBoostingRegressor
    return cls(max_leaf_nodes=parameter,max_iter=CONFIG['hgb_max_iter'],learning_rate=CONFIG['hgb_learning_rate'],
        min_samples_leaf=CONFIG['hgb_min_leaf'],l2_regularization=CONFIG['hgb_l2'],early_stopping=False,random_state=SEED)


def native_predict(estimator,x,classification):return estimator.predict_proba(x)[:,1] if classification else estimator.predict(x)


def choose_threshold(y,p):
    return max(CONFIG['thresholds'],key=lambda t:(balanced_accuracy_score(y,p>=t),-abs(t-.5),-t))


def metrics(y,p,classification,threshold=.5):
    y=np.asarray(y);p=np.asarray(p)
    if classification:
        pred=p>=threshold;tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel();bins=np.minimum((np.clip(p,0,1)*10).astype(int),9)
        ece=sum(np.mean(bins==b)*abs(y[bins==b].mean()-p[bins==b].mean()) for b in range(10) if (bins==b).any())
        return dict(balanced_accuracy=balanced_accuracy_score(y,pred),precision=precision_score(y,pred,zero_division=0),recall=recall_score(y,pred,zero_division=0),
            f1=f1_score(y,pred,zero_division=0),roc_auc=roc_auc_score(y,p) if len(np.unique(y))==2 else np.nan,
            pr_auc=average_precision_score(y,p) if y.sum() else np.nan,brier=brier_score_loss(y,p),log_loss=log_loss(y,p,labels=[0,1]),
            ece_10_bins=ece,tn=int(tn),fp=int(fp),fn=int(fn),tp=int(tp),positive_rate=float(y.mean()))
    error=p-y
    return dict(r2=r2_score(y,p),mae=mean_absolute_error(y,p),rmse=math_sqrt(mean_squared_error(y,p)),mean_error=error.mean(),
        median_absolute_error=np.median(abs(error)),p90_absolute_error=np.quantile(abs(error),.9),p95_absolute_error=np.quantile(abs(error),.95),
        error_q05=np.quantile(error,.05),error_q50=np.median(error),error_q95=np.quantile(error,.95))


def math_sqrt(v):return float(np.sqrt(v))


def selection_key(y,p,classification,threshold):
    return (balanced_accuracy_score(y,p>=threshold),-brier_score_loss(y,p)) if classification else (-mean_absolute_error(y,p),)


def population_row(frame,cols):
    return dict(n=len(frame),first_debut=frame.first_chart_date.min(),last_debut=frame.first_chart_date.max(),
        missing_predictor_cells=int(frame[cols].isna().sum().sum()),predictor_cells=len(frame)*len(cols),
        song_ids_sha256=digest(sorted(frame.song_id)))


def fit_case(splits,cols,target,method,parameter,horizon=26):
    classification=target in ['top10','long_chart'];prep=Preprocessor(cols).fit(splits['train']);
    xs={s:prep.transform(f) for s,f in splits.items()};ys={s:f[f'{target}_{horizon}'].to_numpy() for s,f in splits.items()}
    estimator=model(method,parameter,classification);estimator.fit(xs['train'],ys['train']);vp=native_predict(estimator,xs['validation'],classification)
    threshold=choose_threshold(ys['validation'],vp) if classification else None
    return dict(estimator=estimator,preprocessing=prep,threshold=threshold,method=method,parameter=parameter,
        validation_key=selection_key(ys['validation'],vp,classification,threshold))


def predictions(case,frame,classification):return native_predict(case['estimator'],case['preprocessing'].transform(frame),classification)


def campaign_key():
    manifest=read_json(DATA/'manifest.json')
    for name,expected in manifest['pipeline_sha256'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Feature pipeline changed; rebuild the versioned feature dataset before fitting')
    for name,record in manifest['files'].items():
        if sha(DATA/name)!=record['sha256']:raise ValueError('Feature dataset differs from its validated manifest')
    return digest(dict(protocol=freeze(),inputs={p.name:sha(p) for p in [DATA/'song_features.csv.xz',DATA/'song_outcomes.csv.xz']},
        code={p.name:sha(p) for p in [Path(__file__),ROOT/'src/feature_expansion_predict.py',ROOT/'src/feature_expansion_features.py',ROOT/'src/feature_expansion_common.py']}))


def train():
    started=time.time();key=campaign_key();cache=LOCAL/key;cache.mkdir(parents=True,exist_ok=True)
    comparison=[];tuning=[];selected=[];saved_predictions=[];calibration=[];all_importances=[];replay=[];populations=[]
    for track in ['strict','retrospective']:
        frame=load_population(track)
        for target,configuration in itertools.product(TARGETS,CONFIG['configurations']):
            classification=target in ['top10','long_chart'];splits=task_splits(frame,target);cols=columns(track,configuration);best_methods=[]
            for partition,f in splits.items():populations.append(dict(track=track,target=target,configuration=configuration,partition=partition,**population_row(f,cols)))
            for method in CONFIG['methods']:
                params=(CONFIG['logistic_C'] if classification else CONFIG['ridge_alpha']) if method=='regularized' else CONFIG['tree_depth'] if method=='tree' else CONFIG['hgb_leaf_nodes']
                cases=[]
                for param in params:
                    path=cache/f'{track}_{target}_{configuration}_{method}_{param}.joblib'
                    if path.exists():case=joblib.load(path)
                    else:
                        case=fit_case(splits,cols,target,method,param);joblib.dump(case,path)
                    cases.append(case);tuning.append(dict(track=track,target=target,configuration=configuration,method=method,parameter=param,threshold=case['threshold'],validation_key=case['validation_key']))
                case=max(cases,key=lambda c:c['validation_key']);best_methods.append(case)
                est=case['estimator'];names=case['preprocessing'].names
                if hasattr(est,'coef_'):values=est.coef_.reshape(-1);kind='standardized_coefficient'
                elif hasattr(est,'feature_importances_'):values=est.feature_importances_;kind='impurity_importance'
                else:values=[];kind='not_available'
                all_importances.extend(dict(track=track,target=target,configuration=configuration,method=method,kind=kind,feature=n,value=v) for n,v in zip(names,values))
                for partition,f in splits.items():
                    p=predictions(case,f,classification);m=metrics(f[target+'_26'],p,classification,case['threshold'])
                    comparison.append(dict(track=track,target=target,configuration=configuration,method=method,parameter=case['parameter'],partition=partition,threshold=case['threshold'],**population_row(f,cols),**m))
            winner=max(best_methods,key=lambda c:c['validation_key']);tag=f'{track}_{target}_{configuration}';joblib.dump(winner,cache/(tag+'_selected.joblib'))
            selected.append(dict(track=track,target=target,configuration=configuration,method=winner['method'],parameter=winner['parameter'],threshold=winner['threshold'],features=len(cols)))
            bundle=dict(version=CONFIG['version'],track=track,target=target,configuration=configuration,horizon_weeks=26,method=winner['method'],parameter=winner['parameter'],threshold=winner['threshold'],
                preprocessing=winner['preprocessing'].export(),estimator=export_estimator(winner['estimator'],classification),campaign_key=key)
            write_json(PUBLIC/'models'/(tag+'.json.gz'),bundle);portable=read_json(PUBLIC/'models'/(tag+'.json.gz'))
            for partition,f in splits.items():
                p=predictions(winner,f,classification);portable_p=predict_export(portable,f)
                delta=float(np.max(abs(portable_p-p)))
                if not np.allclose(portable_p,p,rtol=1e-10,atol=1e-9):raise ValueError('Model replay mismatch '+tag)
                replay.append(dict(model=tag,partition=partition,n=len(f),max_absolute_difference=delta))
                if partition!='train':
                    for sid,actual,value in zip(f.song_id,f[target+'_26'],p):saved_predictions.append(dict(track=track,target=target,configuration=configuration,partition=partition,song_id=sid,actual=actual,prediction=value,predicted_class=int(value>=winner['threshold']) if classification else None))
                if classification:
                    bins=np.minimum((p*10).astype(int),9);y=f[target+'_26'].to_numpy()
                    for b in range(10):
                        take=bins==b
                        if take.any():calibration.append(dict(track=track,target=target,configuration=configuration,partition=partition,bin=b,n=int(take.sum()),mean_probability=p[take].mean(),observed_rate=y[take].mean()))
            print(f'Selected {tag}: {winner["method"]} {winner["parameter"]}; elapsed {time.time()-started:.1f}s',flush=True)
            # Persist completed summaries so interrupted fits are restartable without losing progress.
            write_csv(PUBLIC/'model_comparison.csv',comparison);write_csv(PUBLIC/'selected_models.csv',selected)
    for filename,rows in [('hyperparameter_validation.csv',tuning),('selected_predictions.csv.gz',saved_predictions),('calibration.csv',calibration),('coefficient_tree_importance.csv',all_importances),('model_replay_audit.csv',replay),('model_populations.csv',populations)]:write_csv(PUBLIC/filename,rows)
    write_json(LOCAL/'active_campaign.json',dict(key=key,cache=str(cache),training_seconds=time.time()-started,environment=environment()))


def active():
    a=read_json(LOCAL/'active_campaign.json')
    if a['key']!=campaign_key():raise ValueError('Code/input changed since fitting; rerun train to establish matching checkpoints')
    return a,Path(a['cache'])


def baseline_and_uncertainty():
    a,cache=active();base_rows=[];intervals=[];periods=[];rng=np.random.default_rng(SEED)
    for track in ['strict','retrospective']:
        frame=load_population(track)
        for target in TARGETS:
            cls=target in ['top10','long_chart'];splits=task_splits(frame,target);ytrain=splits['train'][target+'_26'].to_numpy();test=splits['test'];y=test[target+'_26'].to_numpy()
            methods={c:joblib.load(cache/f'{track}_{target}_{c}_selected.joblib') for c in CONFIG['configurations']};ps={c:predictions(case,test,cls) for c,case in methods.items()}
            for partition,f in splits.items():
                yf=f[target+'_26'].to_numpy()
                if cls:
                    for name,p in [('majority',np.full(len(f),float(ytrain.mean()>=.5))),('training_prevalence',np.full(len(f),ytrain.mean()))]:
                        base_rows.append(dict(track=track,target=target,partition=partition,baseline=name,n=len(f),**metrics(yf,p,True,.5)))
                    if target=='top10':
                        p=(f.credit_prior_top10_song_count.to_numpy()+5*ytrain.mean())/(f.credit_prior_song_count.to_numpy()+5)
                        vf=splits['validation'];vp=(vf.credit_prior_top10_song_count.to_numpy()+5*ytrain.mean())/(vf.credit_prior_song_count.to_numpy()+5)
                        threshold=choose_threshold(vf[target+'_26'],vp)
                        base_rows.append(dict(track=track,target=target,partition=partition,baseline='smoothed_prior_credit_hit_fraction',n=len(f),threshold=threshold,**metrics(yf,p,True,threshold)))
                else:
                    for name,value in [('training_mean',ytrain.mean()),('training_median',np.median(ytrain))]:base_rows.append(dict(track=track,target=target,partition=partition,baseline=name,n=len(f),**metrics(yf,np.full(len(f),value),False)))
            def score(indices,c):
                return balanced_accuracy_score(y[indices],ps[c][indices]>=methods[c]['threshold']) if cls else mean_absolute_error(y[indices],ps[c][indices])
            all_i=np.arange(len(test));base_score=score(all_i,'baseline');comb_score=score(all_i,'combined')
            for grouping,labels in [('artist_credit',test.artist.to_numpy()),('debut_year',pd.to_datetime(test.first_chart_date).dt.year.to_numpy())]:
                unique=np.unique(labels);groups=[np.flatnonzero(labels==label) for label in unique];values=[];absolute=[]
                for _ in range(CONFIG['bootstrap_repeats']):
                    idx=np.concatenate([groups[i] for i in rng.integers(0,len(groups),len(groups))])
                    if cls and len(np.unique(y[idx]))<2:continue
                    b=score(idx,'baseline');c=score(idx,'combined');values.append(c-b if cls else b-c);absolute.append(c)
                for kind,point,dist in [('combined_minus_baseline_improvement',comb_score-base_score if cls else base_score-comb_score,values),('combined_absolute',comb_score,absolute)]:
                    intervals.append(dict(track=track,target=target,metric='balanced_accuracy' if cls else 'mae',quantity=kind,cluster=grouping,clusters=len(unique),repeats=len(dist),estimate=point,lower=np.quantile(dist,.025),upper=np.quantile(dist,.975)))
            for start,end in [(2018,2021),(2021,2024),(2024,2027)]:
                mask=pd.to_datetime(test.first_chart_date).dt.year.between(start,end-1).to_numpy()
                if not mask.any():continue
                for c in CONFIG['configurations']:periods.append(dict(track=track,target=target,configuration=c,period=f'{start}-{end-1}',n=int(mask.sum()),**metrics(y[mask],ps[c][mask],cls,methods[c]['threshold'])))
    write_csv(PUBLIC/'simple_baselines.csv',base_rows);write_csv(PUBLIC/'uncertainty.csv',intervals);write_csv(PUBLIC/'test_period_metrics.csv',periods)


def interpret():
    a,cache=active();permutations=[];ablations=[];rng=np.random.default_rng(SEED)
    for track in ['strict','retrospective']:
        frame=load_population(track);cols=columns(track,'combined')
        for target in TARGETS:
            cls=target in ['top10','long_chart'];splits=task_splits(frame,target);case=joblib.load(cache/f'{track}_{target}_combined_selected.joblib');vf=splits['validation']
            if len(vf)>CONFIG['permutation_sample_max']:vf=vf.iloc[np.sort(rng.choice(len(vf),CONFIG['permutation_sample_max'],replace=False))]
            y=vf[target+'_26'].to_numpy();base=predictions(case,vf,cls)
            score=lambda p:balanced_accuracy_score(y,p>=case['threshold']) if cls else -mean_absolute_error(y,p)
            reference=score(base)
            for col in cols:
                drops=[]
                for _ in range(CONFIG['permutation_repeats']):
                    altered=vf.copy();altered[col]=rng.permutation(altered[col].to_numpy());drops.append(reference-score(predictions(case,altered,cls)))
                permutations.append(dict(track=track,target=target,feature=col,group=DEFINITIONS.get(col,{}).get('group','existing_scores' if col in SCORES else col),n=len(vf),metric='balanced_accuracy_drop' if cls else 'mae_increase',mean_drop=np.mean(drops),std_drop=np.std(drops),repeats=len(drops)))
            groups=default_groups(cols)
            for group,removed in groups.items():
                kept=[c for c in cols if c not in removed]
                if not kept:continue
                path=cache/f'ablation_{track}_{target}_{group}.joblib'
                if path.exists():reduced=joblib.load(path)
                else:
                    reduced=fit_case(splits,kept,target,case['method'],case['parameter']);joblib.dump(reduced,path)
                for partition in ['validation','test']:
                    f=splits[partition];p=predictions(reduced,f,cls);full=predictions(case,f,cls);m=metrics(f[target+'_26'],p,cls,reduced['threshold']);fm=metrics(f[target+'_26'],full,cls,case['threshold'])
                    ablations.append(dict(track=track,target=target,removed_group=group,removed_features=len(removed),partition=partition,n=len(f),method=case['method'],parameter=case['parameter'],
                        degradation=fm['balanced_accuracy']-m['balanced_accuracy'] if cls else m['mae']-fm['mae'],threshold=reduced['threshold'],**m))
            print(f'Interpreted {track} {target}',flush=True)
            write_csv(PUBLIC/'permutation_importance.csv',permutations);write_csv(PUBLIC/'feature_ablation.csv',ablations)


def default_groups(cols):
    groups={}
    for c in cols:
        g=DEFINITIONS[c]['group'] if c in DEFINITIONS else 'existing_scores' if c in SCORES else c
        groups.setdefault(g,[]).append(c)
    return groups


def backtests():
    a,cache=active();rows=[]
    for track in ['strict','retrospective']:
        frame=load_population(track)
        for target,configuration in itertools.product(TARGETS,CONFIG['configurations']):
            cls=target in ['top10','long_chart'];cols=columns(track,configuration)
            for spec in [dict(name='horizon_12',horizon=12,train_end='2010-01-01',validation_end='2018-01-01',test_end=None)]+[
                dict(name=f'historical_{b["test_start"]}_{b["test_end"]}',horizon=26,train_end=f'{b["test_start"]-5}-01-01',validation_end=f'{b["test_start"]}-01-01',test_end=f'{b["test_end"]}-01-01') for b in CONFIG['historical_backtests']]:
                h=spec['horizon'];splits=task_splits(frame,target,h,**{k:spec[k] for k in ['train_end','validation_end','test_end']});path=cache/f'{spec["name"]}_{track}_{target}_{configuration}.joblib'
                if path.exists():case=joblib.load(path)
                else:case=fit_case(splits,cols,target,'hist_gradient_boosting',15,h);joblib.dump(case,path)
                for partition,f in splits.items():rows.append(dict(experiment=spec['name'],track=track,target=target,configuration=configuration,horizon=h,partition=partition,threshold=case['threshold'],**population_row(f,cols),**metrics(f[f'{target}_{h}'],predictions(case,f,cls),cls,case['threshold'])))
            print(f'Backtests {track} {target} {configuration}',flush=True)
            write_csv(PUBLIC/'historical_sensitivity.csv',rows)


def determinism():
    a,cache=active();rows=[]
    for method in CONFIG['methods']:
        frame=load_population('strict');splits=task_splits(frame,'top10');cols=columns('strict','combined');parameter=.1 if method=='regularized' else 3 if method=='tree' else 15
        first=joblib.load(cache/f'strict_top10_combined_{method}_{parameter}.joblib');second=fit_case(splits,cols,'top10',method,parameter)
        p=predictions(first,splits['test'],True);q=predictions(second,splits['test'],True)
        if not np.array_equal(p,q):raise ValueError('Repeat fit changed predictions')
        rows.append(dict(method=method,parameter=parameter,n=len(p),bitwise_equal=True,max_absolute_difference=float(np.max(abs(p-q)))))
    write_csv(PUBLIC/'determinism_audit.csv',rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['train','interpret','baselines','backtests','determinism','all']);args=parser.parse_args()
    with threadpool_limits(limits=2):
        for name,fn in [('train',train),('baselines',baseline_and_uncertainty),('interpret',interpret),('backtests',backtests),('determinism',determinism)]:
            if args.action in [name,'all']:fn()
