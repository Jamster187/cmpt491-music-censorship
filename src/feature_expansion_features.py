"""Deterministic local features; chart state is updated only after each date batch."""
from __future__ import annotations
from collections import Counter, defaultdict, deque
from contextlib import closing
import json
import math
import re
import sqlite3
import unicodedata
import zlib

import numpy as np
import pandas as pd

from feature_expansion_common import ROOT, PUBLIC, DATA, LOCAL, SCORES, VERSION, freeze, sha, write_csv, write_json

WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
DEFINITIONS = {}


def define(name, definition, group, availability='C', candidate='', dtype='float64'):
    DEFINITIONS[name] = dict(feature=name, definition=definition, group=group,
        historical_availability=availability, candidate_id=candidate, dtype=dtype,
        source_columns=('private approved lyrics + title' if group=='lyric_structure' else
            'approved stored MusicBrainz recording artist-credit + chart_date/song_id/rank' if group=='entity_credit' else
            'frozen primary_genre/42 scores + strict chart prefixes' if group=='relative_content' else
            'master_weekly: chart_date,weekly_rank,song_id,title,artist,source_chart_index,source_row_index'),
        calculation='src/feature_expansion_features.py; full date batch before state update',
        missingness='Undefined history/consensus/text remains null; counts are zero when observed prefix has no events',
        leakage_risk=('Retrospective measurement/version and monthly-selection bias; prefix alone does not establish historical availability' if availability=='F' else
            'Strict date < debut for history; current published chart allowed only for chart context'),
        matching_limitations=('Modern consensus MBIDs, not original release verification; no inferred aliases' if group=='entity_credit' else
            'Exact full credit only; collaborations are distinct credits; no fuzzy merge. Lyrics preserve provider/version/format limitations.'))


HISTORY = {
'credit_prior_song_count': ('Other identities entered under exact full credit before debut','C001'),
'credit_prior_top10_song_count': ('Prior distinct identities already at rank <=10 before debut','C002'),
'credit_prior_top40_song_count': ('Prior distinct identities already at rank <=40 before debut',''),
'credit_prior_chart_points': ('Source-row sum of 101-rank strictly before debut','C003'),
'credit_prior_chart_weeks': ('Sum of distinct song/date appearances before debut',''),
'credit_prior_best_rank': ('Minimum observed rank of credit before debut; null if new credit',''),
'credit_chart_career_days': ('Days since first observed credit appearance; zero without earlier history','C004'),
'credit_days_since_last_entry': ('Days since most recent earlier distinct entry date; same-date tie handled jointly','C005'),
'credit_recent_chart_presence': ('Number of distinct chart dates with this credit in preceding 365 days','C006'),
'credit_recent_points_slope': ('OLS slope per observed chart of credit points over prior 13 charts, including absent zeroes','C007'),
'credit_prior_song_observed_longevity_median': ('Median prior-song distinct chart dates attained before cutoff; ongoing songs truncated','C008'),
'credit_previous_entry_best_rank_so_far': ('Best rank so far among identities tied at most recent earlier entry date','C009'),
'credit_simultaneous_other_songs': ('Distinct identities of credit on preceding chart','C010'),
'credit_prior_reentry_song_share': ('Share of prior identities returning after absence on consecutive <=8-day source charts','C011'),
'credit_prior_chart_rank_volatility': ('Population SD of rank differences on consecutive <=8-day observed charts, prior credit songs','C012'),
}
for n,(d,c) in HISTORY.items():define(n,d,'artist_history',candidate=c)
CONTEXT = {
'previous_chart_new_entry_count': ('Distinct first-observed entrants on preceding chart','C013'),
'previous_chart_credit_concentration': ('HHI of exact-credit shares among distinct songs on preceding chart','C014'),
'previous_chart_incumbent_age_median': ('Median distinct chart-date count attained by songs on preceding chart','C015'),
'previous_chart_turnover_share': ('Share of preceding-chart songs absent from chart immediately before it; null over gap >8 days','C016'),
'debut_chart_established_credit_share': ('Share of other distinct credits on debut chart with earlier observed entry','C017'),
'prior_year_unique_chart_song_count': ('Distinct identities appearing in preceding 365 days','C018'),
'previous_chart_leader_tenure': ('Consecutive <=8-day source charts with same rank-one identity through preceding chart','C019'),
'same_credit_debut_cluster_size': ('Other first-observed identities with exact credit on current chart','C020'),
'debut_competing_new_entry_count': ('Other first-observed identities on published debut chart',''),
}
for n,(d,c) in CONTEXT.items():define(n,d,'chart_competition',candidate=c)
for n,d,c in [
('debut_season_sin','sin(2*pi*(day_of_year-1)/days_in_year)','C021'),
('debut_season_cos','cos(2*pi*(day_of_year-1)/days_in_year); same construct as sine','C021'),
('christmas_proximity_days','Signed nearest December 25 date minus debut date','C022'),
('chart_weekday','Python calendar weekday (Monday=0); observed calendar, not official methodology','C023'),
('song_title_token_count','Unicode lexical token count in original title','C024'),
('song_title_has_number','Contains Unicode digit or English zero through twelve','C025'),
('song_title_question_form','Contains ? or starts who/what/when/where/why/how/is/are/can/do/does/did','C026'),
('song_title_prior_usage_count','Earlier distinct identities with exact original title','C027'),
('artist_credit_feature_marker','Original full credit contains case-insensitive featuring/feat./ft. as word marker','C028')]:define(n,d,'calendar_title',candidate=c)

LYRICS = {
'lyric_word_count': ('Unicode lexical tokens; NFC/casefold; apostrophe contractions kept','C029'),
'lyric_vocabulary_size': ('Distinct normalized lexical token types','C030'),
'lyric_mattr': ('Mean type/token ratio over all sliding 50-token windows; null below 50 tokens','C031'),
'lyric_hapax_share': ('Types occurring once divided by all distinct types','C032'),
'lyric_compression_ratio': ('zlib level 9 byte length / original UTF-8 bytes of normalized token lines','C033'),
'lyric_repeated_line_share': ('(Nonempty token lines - distinct token lines) / nonempty token lines','C034'),
'lyric_repeated_bigram_share': ('(Adjacent bigram occurrences - distinct bigrams) / bigram occurrences','C035'),
'lyric_line_length_dispersion': ('Population SD of lexical tokens per nonempty token line','C038'),
'lyric_mean_line_length': ('Mean lexical tokens per nonempty token line',''),
'lyric_question_line_share': ('Share of retained nonempty lines ending in ?','C039'),
'lyric_first_person_singular_share': ("English tokens i/me/my/mine/myself/i'm/i've/i'll/i'd divided by all tokens",'C040'),
'lyric_second_person_share': ("English you/your/yours/yourself/yourselves/you're/you've/you'll/you'd divided by all tokens",'C041'),
'lyric_first_person_plural_share': ("English we/us/our/ours/ourselves/we're/we've/we'll/we'd divided by all tokens",'C042'),
'lyric_negation_token_share': ("English no/not/never/none/nobody/nothing/neither/nor/without or suffix n't divided by all tokens",'C043'),
'lyric_temporal_deixis_share': ('English yesterday/today/tomorrow/tonight/now/then/always/forever/ago divided by all tokens','C044'),
'lyric_title_phrase_repetition': ('Contiguous exact normalized full title token matches per 100 approved lyric tokens; title-equal opening lyric retained','C045'),
}
for n,(d,c) in LYRICS.items():define(n,d,'lyric_structure','F',c)
for n,d,c in [
('prior_year_primary_genre_share','Share of labelled distinct earlier entries in preceding 365 days with focal genre','C047'),
('lyric_content_distance_prior_hits','RMSE across 42 raw [0,1] scores against centroid of distinct prior attained Top10 songs; equal dimensions, no estimated scaling','C048'),
('lyric_content_distance_recent_chart','RMSE against complete-profile distinct songs on preceding chart','C049'),
('credit_prior_genre_diversity','Natural-log entropy of labelled prior exact-credit entries','C050'),
('debut_chart_same_genre_share','Share of other labelled distinct songs on published debut chart with focal primary genre','')]:define(n,d,'relative_content','F',c)
for n,d,c in [
('credited_artist_entity_count','Number of distinct MBIDs in unanimous ordered recording-credit consensus','C052'),
('first_credited_entity_prior_song_count','Distinct earlier identities containing first listed MBID; first-listed is not assumed lead vocalist',''),
('credited_entities_prior_top10_mean','Mean count of previously attained distinct Top10 songs per unique credited MBID',''),
('credit_team_prior_song_count','Prior distinct identities with identical unordered set of >=2 consensus MBIDs; null for solo','')]:define(n,d,'entity_credit','F',c)


def tokens(text):return WORD.findall(unicodedata.normalize('NFC',text).casefold().replace('’',"'"))


def lyric_features(text,title):
    # Approved stored texts already received conservative provider cleanup. A title
    # alone is not evidence of a header: it can be the opening lyric itself.
    section=r'\s*\[(?:intro|outro|verse(?:\s+\d+)?|chorus|pre-chorus|bridge|instrumental|interlude)\]\s*'
    lines=[x.strip() for x in text.splitlines() if x.strip() and not re.fullmatch(section,x,re.I)]
    pairs=[(x,tokens(x)) for x in lines];pairs=[p for p in pairs if p[1]]
    words=[w for _,ws in pairs for w in ws]
    if not words:return {k:np.nan for k in LYRICS}
    counts=Counter(words);n=len(words);normalized=[' '.join(ws) for _,ws in pairs]
    raw='\n'.join(normalized).encode('utf-8');bigrams=list(zip(words,words[1:]))
    mattr=np.nan
    if n>=50:
        window=Counter(words[:50]);s=len(window)
        for i in range(50,n):
            old=words[i-50];window[old]-=1
            if not window[old]:del window[old]
            window[words[i]]+=1;s+=len(window)
        mattr=s/(50*(n-49))
    result=dict(lyric_word_count=n,lyric_vocabulary_size=len(counts),lyric_mattr=mattr,
        lyric_hapax_share=sum(x==1 for x in counts.values())/len(counts),
        lyric_compression_ratio=len(zlib.compress(raw,9))/len(raw),
        lyric_repeated_line_share=1-len(set(normalized))/len(normalized),
        lyric_repeated_bigram_share=1-len(set(bigrams))/len(bigrams) if bigrams else np.nan,
        lyric_line_length_dispersion=float(np.std([len(ws) for _,ws in pairs])),
        lyric_mean_line_length=n/len(pairs),lyric_question_line_share=sum(x.endswith('?') for x,_ in pairs)/len(pairs))
    lexicons=dict(lyric_first_person_singular_share="i me my mine myself i'm i've i'll i'd",
        lyric_second_person_share="you your yours yourself yourselves you're you've you'll you'd",
        lyric_first_person_plural_share="we us our ours ourselves we're we've we'll we'd",
        lyric_negation_token_share='no not never none nobody nothing neither nor without',
        lyric_temporal_deixis_share='yesterday today tomorrow tonight now then always forever ago')
    for name,lex in lexicons.items():
        terms=set(lex.split());result[name]=sum(v for w,v in counts.items() if w in terms or (name=='lyric_negation_token_share' and w.endswith("n't")))/n
    title_words=tokens(title);k=len(title_words)
    result['lyric_title_phrase_repetition']=100*sum(words[i:i+k]==title_words for i in range(n-k+1))/n if k else np.nan
    return result


def ro(path):return sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)


def load_lyrics(study):
    records={};wanted=set(study.song_id)
    with closing(ro(ROOT/'data/processed/research.db')) as c:
        for sid,path,h,status in c.execute("SELECT song_id,lyrics_path,lyrics_sha256,match_status FROM lyrics_manifest WHERE lyrics_status='success'"):
            if sid in wanted:
                if status!='high_confidence':raise ValueError('Nonapproved lyric match')
                records[sid]=(path,h)
    with closing(ro(ROOT/'data/processed/month_end_catchup/lyrics.db')) as c:
        for sid,raw in c.execute('SELECT song_id,payload FROM production_results'):
            r=json.loads(raw)
            if sid in wanted and r['status']=='accepted':
                if sid in records:raise ValueError('Duplicate approved lyric identity')
                records[sid]=(r['lyrics_path'],r['lyrics_sha256'])
    result={};provenance=[];titles=study.set_index('song_id').title.to_dict()
    for sid,(path,h) in sorted(records.items()):
        p=ROOT/path
        if p.is_symlink() or p.resolve()!=(ROOT/'data/lyrics'/f'{sid}.txt').resolve() or sha(p)!=h:raise ValueError('Lyric integrity mismatch: '+sid)
        result[sid]=lyric_features(p.read_text(),titles[sid]);provenance.append(dict(song_id=sid,path=path,sha256=h))
    write_json(LOCAL/'lyric_input_provenance.json',provenance)
    return result


def consensus_credit(variants):
    credits=[]
    for v in variants:
        raw=v.get('artist-credit')
        if not raw or any(not x.get('artist_id') for x in raw):return None
        # Deduplicate an entity repeated in the credit without inventing an identity.
        credits.append(tuple(dict.fromkeys(x['artist_id'] for x in raw)))
    return credits[0] if credits and len(set(credits))==1 else None


def load_credit_map(study):
    wanted=set(study.loc[study.musicbrainz_match_status.eq('high_confidence'),'song_id']);variants=defaultdict(list)
    for path in [ROOT/'data/processed/research.db',ROOT/'data/processed/month_end_catchup/metadata.db']:
        with closing(ro(path)) as c:
            for sid,raw in c.execute("""SELECT l.song_id,e.metadata_json FROM song_external_links l JOIN external_entities e USING(provider,entity_type,entity_id)
                JOIN metadata_matches m ON m.song_id=l.song_id WHERE l.entity_type='recording' AND m.match_status='high_confidence'"""):
                if sid in wanted:variants[sid].extend(json.loads(raw))
    mapping={sid:consensus_credit(v) for sid,v in variants.items()};mapping={sid:v for sid,v in mapping.items() if v}
    write_json(LOCAL/'credit_consensus.json',mapping)
    return mapping,dict(high_confidence=len(wanted),with_recording_variants=len(variants),unanimous=len(mapping),ambiguous_or_incomplete=len(wanted)-len(mapping))


def chart_features(weekly,study=None,credit_map=None):
    """Uses only the six supplied chart fields, never source-reported lifetime totals."""
    weekly=weekly.sort_values(['chart_date','source_chart_index','source_row_index']).copy()
    weekly['chart_date']=pd.to_datetime(weekly.chart_date)
    if weekly[['source_chart_index','source_row_index']].duplicated().any():raise ValueError('Duplicate source location')
    identity=weekly[['song_id','title','artist']].drop_duplicates()
    if identity.song_id.duplicated().any():raise ValueError('Identity changed')
    meta={} if study is None else study.set_index('song_id').to_dict('index');credit_map=credit_map or {}
    state={};credits=defaultdict(list);credit_points=Counter();credit_weeks=Counter();credit_dates=defaultdict(deque)
    credit_changes=defaultdict(list);title_counts=Counter();past_charts=deque(maxlen=13);year_charts=deque();year_songs=Counter()
    recent_entries=deque();genre_counts=Counter();credit_genres=defaultdict(Counter)
    entities=defaultdict(set);entity_hits=defaultdict(set);teams=Counter();hit_seen=set();hit_sum=np.zeros(len(SCORES));hit_n=0
    previous=set();previous_credits=Counter();previous_new=0;previous_turnover=np.nan;leader=None;leader_tenure=0;previous_date=None
    result=[];chart_index=-1;gap_generation=0
    for date,chart in weekly.groupby('chart_date',sort=True):
        chart_index+=1;minimum=date-pd.Timedelta(days=365)
        if previous_date is not None and (date-previous_date).days>8:gap_generation+=1
        while year_charts and year_charts[0][0]<minimum:
            _,ids=year_charts.popleft();year_songs.subtract(ids)
            for sid in ids:
                if year_songs[sid]==0:del year_songs[sid]
        while recent_entries and recent_entries[0][0]<minimum:
            _,g=recent_entries.popleft();genre_counts[g]-=1
        current=chart.groupby('song_id',sort=True).agg(title=('title','first'),artist=('artist','first'),rank=('weekly_rank','min'),points=('weekly_rank',lambda s:float((101-s).sum())))
        new=[s for s in current.index if s not in state];new_credit=Counter(current.loc[new,'artist']);all_credits=set(current.artist)
        prev_profiles=[np.array([meta[s].get(k,np.nan) for k in SCORES],float) for s in sorted(previous) if s in meta]
        prev_profiles=[p for p in prev_profiles if np.isfinite(p).all()];prev_centroid=np.mean(prev_profiles,axis=0) if prev_profiles else None
        current_genres=Counter(meta[s]['primary_genre'] for s in current.index if s in meta)
        for sid in new:
            row=current.loc[sid];credit=row.artist;prior=credits[credit];records=[state[s] for s in prior]
            recent=credit_dates[credit]
            while recent and recent[0]<minimum:recent.popleft()
            values=[x.get(credit,0) for x in past_charts];slope=float(np.polyfit(np.arange(len(values)),values,1)[0]) if len(values)>1 else np.nan
            latest=max((s['debut'] for s in records),default=None)
            f=dict(song_id=sid,title=row.title,artist=credit,first_chart_date=date.date().isoformat(),debut_rank=int(row['rank']),
                credit_prior_song_count=len(prior),credit_prior_top10_song_count=sum(s['peak']<=10 for s in records),
                credit_prior_top40_song_count=sum(s['peak']<=40 for s in records),credit_prior_chart_points=credit_points[credit],
                credit_prior_chart_weeks=credit_weeks[credit],credit_prior_best_rank=min((s['peak'] for s in records),default=np.nan),
                credit_chart_career_days=(date-min(s['debut'] for s in records)).days if records else 0,
                credit_days_since_last_entry=(date-latest).days if latest is not None else np.nan,
                credit_recent_chart_presence=len(recent),credit_recent_points_slope=slope,
                credit_prior_song_observed_longevity_median=float(np.median([s['weeks'] for s in records])) if records else np.nan,
                credit_previous_entry_best_rank_so_far=min((s['peak'] for s in records if s['debut']==latest),default=np.nan),
                credit_simultaneous_other_songs=previous_credits[credit],credit_prior_reentry_song_share=sum(s['reentry'] for s in records)/len(records) if records else np.nan,
                credit_prior_chart_rank_volatility=float(np.std(credit_changes[credit])) if credit_changes[credit] else np.nan,
                previous_chart_new_entry_count=previous_new if previous_date is not None else np.nan,
                previous_chart_credit_concentration=sum((v/len(previous))**2 for v in previous_credits.values()) if previous else np.nan,
                previous_chart_incumbent_age_median=float(np.median([state[s]['weeks'] for s in previous])) if previous else np.nan,
                previous_chart_turnover_share=previous_turnover,
                debut_chart_established_credit_share=sum(bool(credits[c]) for c in all_credits-{credit})/len(all_credits-{credit}) if len(all_credits-{credit}) else np.nan,
                prior_year_unique_chart_song_count=len(year_songs),previous_chart_leader_tenure=leader_tenure if previous else np.nan,
                same_credit_debut_cluster_size=new_credit[credit]-1,debut_competing_new_entry_count=len(new)-1,
                debut_season_sin=math.sin(2*math.pi*(date.dayofyear-1)/(366 if date.is_leap_year else 365)),
                debut_season_cos=math.cos(2*math.pi*(date.dayofyear-1)/(366 if date.is_leap_year else 365)),
                christmas_proximity_days=min(((pd.Timestamp(y,12,25)-date).days for y in [date.year-1,date.year,date.year+1]),key=abs),
                chart_weekday=date.weekday(),song_title_token_count=len(tokens(row.title)),
                song_title_has_number=int(any(x.isdigit() for x in row.title) or bool(set(tokens(row.title))&set('zero one two three four five six seven eight nine ten eleven twelve'.split()))),
                song_title_question_form=int('?' in row.title or bool(tokens(row.title) and tokens(row.title)[0] in 'who what when where why how is are can do does did'.split())),
                song_title_prior_usage_count=title_counts[row.title],artist_credit_feature_marker=int(bool(re.search(r'\b(featuring|feat\.?|ft\.?)\b',credit,re.I))))
            m=meta.get(sid,{});g=m.get('primary_genre');p=np.array([m.get(k,np.nan) for k in SCORES],float)
            f.update(prior_year_primary_genre_share=genre_counts[g]/sum(genre_counts.values()) if g is not None and sum(genre_counts.values()) else np.nan,
                lyric_content_distance_prior_hits=float(np.sqrt(np.mean((p-hit_sum/hit_n)**2))) if hit_n and np.isfinite(p).all() else np.nan,
                lyric_content_distance_recent_chart=float(np.sqrt(np.mean((p-prev_centroid)**2))) if prev_centroid is not None and np.isfinite(p).all() else np.nan,
                credit_prior_genre_diversity=-sum((v/sum(credit_genres[credit].values()))*math.log(v/sum(credit_genres[credit].values())) for v in credit_genres[credit].values()) if credit_genres[credit] else np.nan,
                debut_chart_same_genre_share=(current_genres[g]-1)/(sum(current_genres.values())-1) if g is not None and sum(current_genres.values())>1 else np.nan)
            ids=credit_map.get(sid)
            f.update(credited_artist_entity_count=len(ids) if ids else np.nan,
                first_credited_entity_prior_song_count=len(entities[ids[0]]) if ids else np.nan,
                credited_entities_prior_top10_mean=float(np.mean([len(entity_hits[e]) for e in ids])) if ids else np.nan,
                credit_team_prior_song_count=teams[tuple(sorted(ids))] if ids and len(ids)>1 else np.nan)
            result.append(f)
        # Every new feature for this date has been captured. Now publish the batch to history.
        for sid in new:
            row=current.loc[sid];credits[row.artist].append(sid);title_counts[row.title]+=1
            state[sid]=dict(debut=date,weeks=0,peak=101,last_index=-1,last_rank=None,reentry=False,last_date=None,gap_generation=gap_generation)
            if sid in meta:
                g=meta[sid]['primary_genre'];recent_entries.append((date,g));genre_counts[g]+=1;credit_genres[row.artist][g]+=1
            ids=credit_map.get(sid,())
            for entity in ids:entities[entity].add(sid)
            if len(ids)>1:teams[tuple(sorted(ids))]+=1
        for sid,row in current.iterrows():
            s=state[sid];gap=(date-s['last_date']).days if s['last_date'] is not None else None
            if s['last_index']==chart_index-1 and gap is not None and gap<=8:credit_changes[row.artist].append(row['rank']-s['last_rank'])
            # A return requires at least one known absent chart and no >8-day source gap since last presence.
            if s['last_index']>=0 and s['last_index']<chart_index-1 and s['gap_generation']==gap_generation:s['reentry']=True
            s.update(weeks=s['weeks']+1,peak=min(s['peak'],row['rank']),last_index=chart_index,last_rank=row['rank'],last_date=date,gap_generation=gap_generation)
            credit_weeks[row.artist]+=1;credit_points[row.artist]+=row.points
            if row['rank']<=10:
                for entity in credit_map.get(sid,()):entity_hits[entity].add(sid)
                if sid not in hit_seen:
                    hit_seen.add(sid)
                    p=np.array([meta.get(sid,{}).get(k,np.nan) for k in SCORES],float)
                    if np.isfinite(p).all():hit_sum+=p;hit_n+=1
        for credit in set(current.artist):credit_dates[credit].append(date)
        past_charts.append(current.groupby('artist').points.sum().to_dict())
        current_ids=set(current.index);year_charts.append((date,current_ids));year_songs.update(current_ids)
        current_leaders=tuple(sorted(current.index[current['rank'].eq(1)]))
        leader_tenure=leader_tenure+1 if current_leaders==leader and previous_date is not None and (date-previous_date).days<=8 else 1
        leader=current_leaders;previous_turnover=len(current_ids-previous)/len(current_ids) if previous and (date-previous_date).days<=8 else np.nan
        previous=current_ids;previous_credits=Counter(current.artist);previous_new=len(new);previous_date=date
    return pd.DataFrame(result).sort_values('song_id').reset_index(drop=True)


def outcome_table(weekly):
    f=weekly.copy();f['chart_date']=pd.to_datetime(f.chart_date);last=f.chart_date.max();rows=[]
    for sid,g in f.groupby('song_id',sort=True):
        start=g.chart_date.min();dates=sorted(g.chart_date.unique());r=dict(song_id=sid,observed_last_chart_date=g.chart_date.max().date().isoformat(),
            observed_lifetime_best_rank=int(g.weekly_rank.min()),observed_lifetime_chart_weeks=g.chart_date.nunique(),
            observed_lifetime_chart_points=int((101-g.weekly_rank).sum()),near_endpoint=int((last-g.chart_date.max()).days<=28),
            observed_return_after_26weeks=int(any(pd.Timestamp(d)>=start+pd.Timedelta(weeks=26) for d in dates)))
        for h in [12,26]:
            end=start+pd.Timedelta(weeks=h);w=g[g.chart_date.lt(end)];weeks=w.chart_date.nunique()
            r.update({f'window_end_{h}':end.date().isoformat(),f'eligible_{h}':bool(last>=end),f'top10_{h}':int(w.weekly_rank.min()<=10),
                f'long_chart_{h}':int(weeks>=math.ceil(h/2)),f'best_rank_{h}':int(w.weekly_rank.min()),f'chart_weeks_{h}':weeks,f'chart_points_{h}':int((101-w.weekly_rank).sum())})
        rows.append(r)
    return pd.DataFrame(rows)


def build():
    protocol_hash=freeze();cols=['chart_date','weekly_rank','source_chart_index','source_row_index','song_id','title','artist']
    weekly=pd.read_csv(ROOT/'data/public/master_weekly.csv.xz',usecols=cols);study=pd.read_csv(ROOT/'data/public/songs.csv')
    mapping,credit_audit=load_credit_map(study);lyrics=load_lyrics(study)
    print(json.dumps(dict(lyrics=len(lyrics),credit_audit=credit_audit)),flush=True)
    features=chart_features(weekly,study,mapping)
    text=pd.DataFrame.from_dict(lyrics,orient='index').rename_axis('song_id').reset_index();features=features.merge(text,on='song_id',how='left',validate='one_to_one')
    existing=study[['song_id','primary_genre']+SCORES].copy()
    existing['duration_seconds']=study.mb_duration_median_seconds.where(study.mb_distinct_duration_count.eq(1)&study.musicbrainz_match_status.eq('high_confidence'))
    features=features.merge(existing,on='song_id',how='left',validate='one_to_one');outcomes=outcome_table(weekly)
    for name in DEFINITIONS:
        if name not in features:raise ValueError('Feature missing: '+name)
    if len(features)!=32723 or len(outcomes)!=len(features) or features.song_id.duplicated().any():raise ValueError('Population mismatch')
    write_csv(DATA/'song_features.csv.xz',features);write_csv(DATA/'song_outcomes.csv.xz',outcomes)
    write_csv(PUBLIC/'feature_dictionary.csv',list(DEFINITIONS.values()))
    coverage=[]
    for population,frame in [('all_weekly',features),('final_study',features[features.song_id.isin(study.song_id)])]:
        for name in DEFINITIONS:
            s=frame[name];coverage.append(dict(population=population,feature=name,n=len(s),nonmissing=int(s.notna().sum()),missing=int(s.isna().sum()),coverage=float(s.notna().mean()),minimum=s.min(),maximum=s.max(),distinct_values=s.nunique()))
    write_csv(PUBLIC/'coverage_report.csv',coverage)
    inventory=pd.read_csv(ROOT/'analysis/feature_expansion_research/reconstructable_features.csv');dispositions=[]
    for r in inventory.to_dict('records'):
        implemented=[n for n,d in DEFINITIONS.items() if d['candidate_id']==r['candidate_id']]
        reason=('Implemented with exact definitions in dictionary' if implemented else
            'Requires post-debut landmark; incompatible with first-appearance forecast' if r['candidate_id'] in ['C156','C157','C158'] else
            'Provider section markup not consistent enough for comparable chorus/section measures' if r['candidate_id'] in ['C036','C037'] else
            'Alias/name ambiguity requires review; no new entity assumptions' if r['candidate_id']=='C046' else
            'Secondary-genre confidence/denominator semantics require separate validation' if r['candidate_id']=='C051' else
            'Matched release collection includes later manifestations; no proven original-release selection')
        dispositions.append(dict(candidate_id=r['candidate_id'],candidate=r['proposed_column_name'],status='implemented' if implemented else 'deferred',implemented_features=';'.join(implemented),reason=reason))
    write_csv(PUBLIC/'candidate_dispositions.csv',dispositions)
    audit=dict(version=VERSION,protocol_sha256=protocol_hash,song_count=len(features),study_count=len(study),new_columns=len(DEFINITIONS),new_constructs=len(DEFINITIONS)-1,
        local_candidates_implemented=sum(x['status']=='implemented' for x in dispositions),local_candidates_total=len(dispositions),
        availability_counts=Counter(x['historical_availability'] for x in DEFINITIONS.values()),credit_consensus=credit_audit,
        lyrics_used=len(lyrics),source_rows=len(weekly),duplicate_song_dates=int(weekly.duplicated(['song_id','chart_date']).sum()),
        source_date_min=weekly.chart_date.min(),source_date_max=weekly.chart_date.max(),source_gap_days=pd.to_datetime(sorted(weekly.chart_date.unique())).to_series().diff().dt.days.value_counts().to_dict(),
        exact_credit_count=features.artist.nunique(),new_credit_debuts=int(features.credit_prior_song_count.eq(0).sum()),
        incomplete_26=int((~outcomes.eligible_26).sum()),incomplete_12=int((~outcomes.eligible_12).sum()),near_endpoint=int(outcomes.near_endpoint.sum()),
        later_returns=int(outcomes.observed_return_after_26weeks.sum()),zlib_version=zlib.ZLIB_RUNTIME_VERSION,
        pipeline_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/feature_expansion_features.py',ROOT/'src/feature_expansion_common.py']},
        input_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'data/public/songs.csv',ROOT/'data/public/master_weekly.csv.xz']},
        private_provenance_sha256={p.name:sha(p) for p in [LOCAL/'lyric_input_provenance.json',LOCAL/'credit_consensus.json']},
        files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in [DATA/'song_features.csv.xz',DATA/'song_outcomes.csv.xz']})
    write_json(PUBLIC/'feature_build_audit.json',audit);write_json(DATA/'manifest.json',audit)
    print(json.dumps(audit,indent=2),flush=True)


if __name__=='__main__':build()
