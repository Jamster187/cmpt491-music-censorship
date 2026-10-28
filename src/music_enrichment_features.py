"""Additional local form and graph features; no remote lyric processing."""
from __future__ import annotations
from collections import Counter, defaultdict
import calendar
import json
import math
import re
import time

import numpy as np
import pandas as pd
from scipy.special import gammaln

from enrichment_common import ROOT, LOCAL, MUSIC, sha, write_csv, write_json
from feature_expansion_features import tokens

DEFINITIONS={}


def define(name,description,group,candidate='',availability='F',unit='ratio'):
    DEFINITIONS[name]={'feature':name,'definition':description,'group':group,'candidate_id':candidate,
        'historical_availability':availability,'units':unit,'source':'approved private lyric text' if group.startswith('lyric') else 'exact original title' if group=='title' else 'approved MusicBrainz credit consensus + strictly earlier chart entries',
        'measurement_version':'music-enrichment-v2.1','missingness':'Null when unsupported; phonology is an English-dictionary proxy with explicit coverage; no missing-value imputation'}


for name,description,unit in [
    ('lyric_mtld','Mean forward/reverse MTLD; segment TTR threshold .72; fractional final factor; null below 50 tokens','tokens'),
    ('lyric_hdd42','Expected type/token diversity in random 42-token draw without replacement; null below 42 tokens','ratio'),
    ('lyric_token_entropy','Natural-log Shannon entropy of token frequencies; differs from length and type count','nats'),
    ('lyric_third_person_share',"English he/she/him/her/his/hers/they/them/their/theirs/reflexives and contractions / all tokens",'ratio'),
    ('lyric_third_person_feminine_share',"English she/her/hers/herself/she's/she'd/she'll / all tokens; textual pronouns, not identity inference",'ratio'),
    ('lyric_third_person_masculine_share',"English he/him/his/himself/he's/he'd/he'll / all tokens; textual pronouns, not identity inference",'ratio'),
    ('lyric_past_deixis_share','English yesterday/ago/before/once/previously/formerly / all tokens; lexical markers, not grammatical tense','ratio'),
    ('lyric_future_deixis_share',"English tomorrow/soon/later/eventually/someday/gonna / all tokens; lexical markers, not tense",'ratio'),
    ('lyric_longest_identical_line_run','Longest run of consecutive identical normalized nonempty lyric lines','lines'),
    ('lyric_terminal_repetition_share','Adjacent nonempty lines ending with identical normalized token / all adjacent line pairs','ratio'),
    ('lyric_mean_token_characters','Mean Unicode character length of lexical tokens, including contraction apostrophes','characters')]:
    define(name,description,'lyric_form',unit=unit)
for name,description,candidate,unit in [
    ('lyric_marked_section_count','Count recognized provider section markers; null if no markers; marker availability is not song structure','C036','markers'),
    ('lyric_marked_chorus_token_share','Tokens in explicitly marked chorus sections / tokens in all marked sections; null without both chorus and other labelled sections','C037','ratio'),
    ('lyric_cmu_token_coverage','Tokens in CMUdict primary pronunciation / all lyric tokens','','ratio'),
    ('lyric_cmu_endword_coverage','Nonempty lines whose last token has a CMUdict pronunciation / all nonempty lines','','ratio'),
    ('lyric_known_syllable_count','Sum of CMUdict vowel phonemes in covered tokens; lower bound, never imputed uncovered syllables','C084','syllables'),
    ('lyric_syllable_count_complete','Total syllables only if every token has dictionary pronunciation; otherwise null','','syllables'),
    ('lyric_syllables_per_covered_word','Known syllables / covered tokens; reported only at token coverage >=.8','C085','syllables/token'),
    ('lyric_polysyllabic_covered_word_share','Covered tokens with >=3 dictionary syllables / covered tokens at coverage >=.8','','ratio'),
    ('lyric_adjacent_end_rhyme_share','Different adjacent line-end words with identical last-stressed-vowel phoneme tail / pairs with both known pronunciations; null if fewer than 3 known pairs','C086','ratio'),
    ('lyric_multisyllabic_adjacent_rhyme_share','Known adjacent pairs with different words and identical two-or-more-syllable stressed tails / known adjacent pairs; >=3 pairs','C087','ratio'),
    ('lyric_rhyme_pair_coverage','Adjacent pairs with both CMUdict line-end pronunciations / all adjacent pairs','','ratio')]:
    define(name,description,'lyric_phonology' if 'cmu' in name or 'syll' in name or 'rhyme' in name else 'lyric_structure',candidate,unit=unit)
for name,description,unit in [
    ('title_parenthetical_token_share','Tokens inside balanced nonnested (...) or [...] / title tokens; version/text form, not recording verification','ratio'),
    ('title_version_marker','Original title has remix/live/acoustic/remaster/version/edit words; explicit textual marker only','binary'),
    ('title_year_reference','Four-digit number 1900-2099 in original title; earliest lexical occurrence; not release year','year')]:define(name,description,'title',availability='C',unit=unit)
for name,description,candidate,unit in [
    ('artist_prior_collaborator_count','Mean number of distinct previously linked co-performer MBIDs per focal credited entity; graph before debut date','C077','entities'),
    ('artist_prior_collaboration_degree_max','Maximum prior distinct-neighbor count among focal entities','','entities'),
    ('artist_prior_collaborator_success_mean','Mean prior attained Top10 song count among distinct prior collaborators of focal team; null with no prior collaborators','C079','songs'),
    ('artist_team_prior_edge_density','Fraction of possible pairs within current team observed in earlier chart-song credits; null for solo','','ratio'),
    ('artist_prior_local_clustering','Mean local clustering coefficient among focal credited artists with >=2 prior neighbors; prior consensus graph only','','ratio'),
    ('collaboration_prior_genre_distance','Mean pairwise total-variation distance between collaborators earlier labelled chart-song genre distributions; null unless >=2 entities have history','C083','distance')]:define(name,description,'collaboration_graph',candidate,unit=unit)


SECTION=re.compile(r'^\s*\[(intro|outro|verse(?:\s+\d+)?|chorus|pre[- ]chorus|bridge|instrumental|interlude)(?:\s*:[^\]]*)?\]\s*$',re.I)


def token_lines(text):
    return [words for line in text.splitlines() if not SECTION.fullmatch(line) and (words:=tokens(line))]


def load_dictionary(path):
    dictionary={}
    for line in path.read_text().splitlines():
        parts=line.split('#',1)[0].split()
        if len(parts)<2:continue
        word=re.sub(r'\(\d+\)$','',parts[0]).casefold()
        if word not in dictionary:dictionary[word]=tuple(parts[1:])
    return dictionary


def mtld(words):
    def direction(seq):
        types=set();length=0;factors=0.
        for word in seq:
            length+=1;types.add(word)
            if len(types)/length<=.72:
                factors+=1.;types=set();length=0
        if length: factors+=(1-len(types)/length)/(1-.72)
        return len(seq)/factors if factors else np.nan
    if len(words)<50:return np.nan
    return float(np.mean([direction(words),direction(list(reversed(words)))]))


def hdd(words,draw=42):
    n=len(words)
    if n<draw:return np.nan
    denom=gammaln(n+1)-gammaln(draw+1)-gammaln(n-draw+1)
    expected=0.
    for count in Counter(words).values():
        absent=0. if n-count<draw else math.exp(gammaln(n-count+1)-gammaln(draw+1)-gammaln(n-count-draw+1)-denom)
        expected+=1-absent
    return expected/draw


def rhyme_key(pronunciation):
    stressed=[i for i,p in enumerate(pronunciation) if p[-1:] in {'1','2'}]
    vowels=[i for i,p in enumerate(pronunciation) if p[-1:].isdigit()]
    if not vowels:return None
    index=(stressed or vowels)[-1]
    return tuple(re.sub(r'\d','',p) for p in pronunciation[index:])


def lyric_features(text,dictionary):
    lines=token_lines(text);words=[w for line in lines for w in line];n=len(words)
    if not n:return {}
    counts=Counter(words);ends=[line[-1] for line in lines]
    known=[dictionary[w] for w in words if w in dictionary]
    syllables=[sum(p[-1:].isdigit() for p in pronunciation) for pronunciation in known]
    coverage=len(known)/n
    pairs=[(a,b) for a,b in zip(ends,ends[1:]) if a in dictionary and b in dictionary]
    rhymes=[(a,b) for a,b in pairs if a!=b and rhyme_key(dictionary[a]) is not None and rhyme_key(dictionary[a])==rhyme_key(dictionary[b])]
    multis=[(a,b) for a,b in rhymes if sum(any(ch.isdigit() for ch in p) for p in dictionary[a][-len(rhyme_key(dictionary[a])):])>=2]
    normalized=[tuple(x) for x in lines];longest=run=1
    for a,b in zip(normalized,normalized[1:]):run=run+1 if a==b else 1;longest=max(longest,run)
    masculine=set("he him his himself he's he'd he'll".split());feminine=set("she her hers herself she's she'd she'll".split())
    plural=set("they them their theirs themselves they're they've they'll they'd".split())
    r=dict(lyric_mtld=mtld(words),lyric_hdd42=hdd(words),lyric_token_entropy=-sum(c/n*math.log(c/n) for c in counts.values()),
        lyric_third_person_share=sum(w in masculine|feminine|plural for w in words)/n,
        lyric_third_person_masculine_share=sum(w in masculine for w in words)/n,lyric_third_person_feminine_share=sum(w in feminine for w in words)/n,
        lyric_past_deixis_share=sum(w in {'yesterday','ago','before','once','previously','formerly'} for w in words)/n,
        lyric_future_deixis_share=sum(w in {'tomorrow','soon','later','eventually','someday','gonna'} for w in words)/n,
        lyric_longest_identical_line_run=longest,lyric_terminal_repetition_share=sum(a==b for a,b in zip(ends,ends[1:]))/(len(ends)-1) if len(ends)>1 else np.nan,
        lyric_mean_token_characters=sum(map(len,words))/n,lyric_cmu_token_coverage=coverage,
        lyric_cmu_endword_coverage=sum(w in dictionary for w in ends)/len(ends),lyric_known_syllable_count=sum(syllables) if known else np.nan,
        lyric_syllable_count_complete=sum(syllables) if len(known)==n else np.nan,
        lyric_syllables_per_covered_word=float(np.mean(syllables)) if coverage>=.8 else np.nan,
        lyric_polysyllabic_covered_word_share=sum(s>=3 for s in syllables)/len(syllables) if coverage>=.8 else np.nan,
        lyric_adjacent_end_rhyme_share=len(rhymes)/len(pairs) if len(pairs)>=3 else np.nan,
        lyric_multisyllabic_adjacent_rhyme_share=len(multis)/len(pairs) if len(pairs)>=3 else np.nan,
        lyric_rhyme_pair_coverage=len(pairs)/(len(ends)-1) if len(ends)>1 else np.nan)
    sections=[];section=None;marked=chorus=0
    for line in text.splitlines():
        match=SECTION.fullmatch(line)
        if match:section=match[1].casefold();sections.append(section)
        elif section:
            count=len(tokens(line));marked+=count
            if section=='chorus':chorus+=count
    r['lyric_marked_section_count']=len(sections) if sections else np.nan
    r['lyric_marked_chorus_token_share']=chorus/marked if marked and 'chorus' in sections and any(s!='chorus' for s in sections) else np.nan
    return r


def title_features(title):
    words=tokens(title);parenthetical=[w for x in re.findall(r'\([^()]*\)|\[[^\[\]]*\]',title) for w in tokens(x)]
    year=re.search(r'\b(?:19|20)\d{2}\b',title)
    return {'title_parenthetical_token_share':len(parenthetical)/len(words) if words else np.nan,
            'title_version_marker':int(bool(set(words)&{'remix','live','acoustic','remaster','remastered','version','edit'})),
            'title_year_reference':int(year[0]) if year else np.nan}


def graph_features(weekly,credit_map,genres):
    neighbors=defaultdict(set);entity_songs=defaultdict(set);entity_hits=defaultdict(set);entity_genres=defaultdict(Counter)
    seen=set();result=[]
    for date,chart in weekly.groupby('chart_date',sort=True):
        current=chart.groupby('song_id',sort=True).weekly_rank.min()
        new=sorted(set(current.index)-seen)
        for sid in new:
            team=credit_map.get(sid)
            if not team:continue
            team=tuple(dict.fromkeys(team));collaborators=set().union(*(neighbors[a] for a in team))-set(team)
            possible=len(team)*(len(team)-1)/2
            clustering=[]
            for artist in team:
                ns=neighbors[artist]
                if len(ns)>=2:
                    clustering.append(sum(len(neighbors[a]&ns) for a in ns)/(len(ns)*(len(ns)-1)))
            distributions=[{g:n/sum(entity_genres[a].values()) for g,n in entity_genres[a].items()} for a in team if entity_genres[a]]
            distances=[sum(abs(a.get(k,0)-b.get(k,0)) for k in set(a)|set(b))/2 for i,a in enumerate(distributions) for b in distributions[i+1:]]
            result.append(dict(song_id=sid,artist_prior_collaborator_count=float(np.mean([len(neighbors[a]) for a in team])),
                artist_prior_collaboration_degree_max=max(len(neighbors[a]) for a in team),
                artist_prior_collaborator_success_mean=float(np.mean([len(entity_hits[a]) for a in collaborators])) if collaborators else np.nan,
                artist_team_prior_edge_density=sum(b in neighbors[a] for i,a in enumerate(team) for b in team[i+1:])/possible if possible else np.nan,
                artist_prior_local_clustering=float(np.mean(clustering)) if clustering else np.nan,
                collaboration_prior_genre_distance=float(np.mean(distances)) if distances else np.nan))
        # Entire date is scored before any update; simultaneous entrants share prefix.
        for sid in new:
            team=credit_map.get(sid,[])
            for artist in team:
                neighbors[artist].update(set(team)-{artist});entity_songs[artist].add(sid)
                if genres.get(sid):entity_genres[artist][genres[sid]]+=1
        for sid,rank in current.items():
            if rank<=10:
                for artist in credit_map.get(sid,[]):entity_hits[artist].add(sid)
        seen.update(new)
    return pd.DataFrame(result)


def build():
    start=time.monotonic();study=pd.read_csv(ROOT/'data/public/songs.csv',keep_default_na=False)
    dictionary=load_dictionary(LOCAL/'sources/cmudict.dict')
    provenance=json.loads((ROOT/'data/experiments/feature_expansion_v1/lyric_input_provenance.json').read_text())
    rows=[]
    for i,row in enumerate(provenance):
        p=ROOT/row['path']
        if p.is_symlink() or p.resolve()!=(ROOT/'data/lyrics'/f"{row['song_id']}.txt").resolve() or sha(p)!=row['sha256']:raise ValueError('Approved lyric hash mismatch')
        rows.append(dict(song_id=row['song_id'],**lyric_features(p.read_text(),dictionary)))
        if i and i%3000==0:print('lyric forms',i,flush=True)
    lyric=pd.DataFrame(rows)
    title=pd.DataFrame([dict(song_id=s.song_id,**title_features(s.title)) for s in study.itertuples(index=False)])
    credits=json.loads((ROOT/'data/experiments/feature_expansion_v1/credit_consensus.json').read_text())
    weekly=pd.read_csv(ROOT/'data/public/master_weekly.csv.xz',usecols=['song_id','chart_date','weekly_rank'])
    graph=graph_features(weekly,credits,study.set_index('song_id').primary_genre.to_dict())
    frame=title.merge(lyric,on='song_id',how='left',validate='one_to_one').merge(graph,on='song_id',how='left',validate='one_to_one')
    if set(frame)-{'song_id'}!=set(DEFINITIONS):raise ValueError('Feature dictionary differs')
    write_csv(LOCAL/'local_features.csv.xz',frame);write_csv(MUSIC/'new_feature_dictionary.csv',list(DEFINITIONS.values()))
    write_json(MUSIC/'local_build.json',{'songs':len(frame),'approved_lyrics':len(provenance),'new_columns':len(DEFINITIONS),
        'dictionary_sha256':sha(LOCAL/'sources/cmudict.dict'),'code_sha256':sha(__file__),'seconds':time.monotonic()-start})
    print('local features complete',frame.shape,flush=True)


if __name__=='__main__':build()
