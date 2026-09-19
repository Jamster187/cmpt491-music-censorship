"""Conservative asset-level LRCLIB matching. Pure functions; no HTTP or review overrides."""
import difflib
import re
import unicodedata
from lyrics_lrclib import normalize, credit, digest
from lyrics_lrclib_r import raw_text, clean, diagnostics

VERSION = 'lrclib-production-v1'
RISK = {'live','remix','acoustic','karaoke','instrumental','medley','demo'}
LABELS = RISK | {'clean','explicit','dirty','edited','radio edit'}


def version_labels(value):
    value=re.sub(r'\bremixes\b','remix',normalize(value))
    return set(re.findall(r'\b(?:'+ '|'.join(sorted(LABELS)) +r')\b',value))


def artist_credit(value):
    # NUL separators occur in provider credits. Never drop an artist or sort name tokens.
    value=value.replace('\x00',' & ').replace('\\x00',' & ').replace('\\u0000',' & ')
    value=re.sub(r'\s+/\s+', ' & ',value)
    return credit(value)


def title_artist(c):
    title=c['trackName'];artist=c['artistName'];warnings=[]
    # A trailing feature credit can be relocated without losing names.
    feature=re.search(r'\s*[\[(](?:feat\.?|ft\.?|featuring)\s+([^\])]+)[\])]\s*$',title,re.I)
    if feature:
        artist+=' & '+feature[1];title=title[:feature.start()].strip();warnings.append('feature_credit_in_title')
    suffix=re.search(r'\s*[\[(](clean|explicit|dirty)(?:\s+version)?[\])]\s*$',title,re.I)
    if suffix:
        warnings.append('version_'+suffix[1].lower());title=title[:suffix.start()].strip()
    return title,artist,warnings


def quality(c,s):
    text,changes=clean(raw_text(c),s['title'],s['artist']);d=diagnostics(c,s)
    warnings=[];fatal=[];uncertain=[]
    if c.get('instrumental') or not text.strip():return text,'text_missing',['instrumental_or_missing'],changes,d
    if changes:warnings.append('formatting_cleanup')
    if not c.get('plainLyrics'):warnings.append('synced_text_fallback')
    if re.search(r'<(?:html|script|div|br)\b|[\x00-\x08\x0b\x0c\x0e-\x1f]',text,re.I):fatal.append('malformed_markup_or_controls')
    if d['encoding_markers']:
        warnings.append('encoding_noise')
        if d['encoding_markers']>=5 or d['encoding_markers']/max(d['words'],1)>.02:fatal.append('severe_encoding_damage')
    mixed=sum(bool(re.search('[A-Za-z]',w) and re.search('[\u0400-\u04ff]',w)) for w in text.split())
    if mixed:uncertain.append('mixed_script_words')
    if d['masked_fragments']:
        warnings.append('censorship_markers')
        if d['masked_fragments']>=3 or d['masked_fragments']/max(d['words'],1)>.005:uncertain.append('material_censorship')
    if d['words']<60:uncertain.append('short_text_requires_review')
    if d['lines']<4 and d['words']>=60:uncertain.append('unstructured_text')
    if re.search(r'https?://|www\.|\b(?:embed|contributors?|lyrics provided by|submit corrections)\b',text,re.I):uncertain.append('possible_non_lyric_material')
    if re.search(r'\b(?:repeat|fade)\b|\.{3}|…|\[.*?\]|\(.*?\)',text,re.I):warnings.append('annotation_or_repetition_uncertainty')
    # Keep short bracket labels that the narrow cleaner does not recognize, but quarantine metadata-like credits.
    if re.search(r'^\s*(?:written by|words\s*(?:&|and)\s*music|copyright|transcribed by)\b',text,re.I|re.M):uncertain.append('embedded_credits')
    if fatal:return text,'text_bad',sorted(set(warnings+fatal)),changes,d
    if uncertain:return text,'text_usable_with_minor_noise',sorted(set(warnings+uncertain)),changes,d
    return text,'text_usable_with_minor_noise' if warnings else 'text_good',warnings,changes,d


REVIEW_TEXT={'mixed_script_words','material_censorship','short_text_requires_review','unstructured_text','possible_non_lyric_material','embedded_credits'}


def compatible(a,b):
    x=normalize(a).split();y=normalize(b).split()
    if x==y:return True,1.0
    # High sequence agreement plus bounded edits. Bag-of-words overlap never establishes compatibility.
    sm=difflib.SequenceMatcher(None,x,y,autojunk=False)
    ratio=sm.ratio()
    edits=[max(j-i,l-k) for op,i,j,k,l in sm.get_opcodes() if op!='equal']
    chars=difflib.SequenceMatcher(None,''.join(x),''.join(y),autojunk=False)
    character_edits=[max(j-i,l-k) for op,i,j,k,l in chars.get_opcodes() if op!='equal']
    return (ratio>=.92 and max(edits,default=0)<=12) or (chars.ratio()>=.97 and max(character_edits,default=0)<=30),round(ratio,5)


def decide(s,candidates):
    evidence=[];eligible=[];plausible=False
    target_title=normalize(s['title']);target_credit=artist_credit(s['artist'])
    target_labels=version_labels(' '.join(re.findall(r'[\[(]([^\])]+)[\])]',s['title'])))
    metadata=s.get('metadata',{});durations=metadata.get('durations',[])
    albums={normalize(a) for a in metadata.get('albums',[])}
    for c in candidates:
        title,artist,format_warnings=title_artist(c)
        # Exact original title always takes priority over suffix parsing (e.g. a song named Clean).
        same_title=normalize(c['trackName'])==target_title or normalize(title)==target_title
        same_artist=artist_credit(artist)==target_credit
        title_labels=set() if normalize(c['trackName'])==target_title else version_labels(c['trackName'])
        labels=(title_labels|version_labels(c.get('albumName') or ''))-target_labels
        text,grade,warnings,changes,d=quality(c,s)
        duration=c.get('duration')
        delta=min((abs(duration-v) for v in durations),default=None) if isinstance(duration,(int,float)) else None
        e={'id':c['id'],'title':c['trackName'],'artist':c['artistName'],'album':c.get('albumName'),'duration':duration,
           'title_compatible':same_title,'artist_compatible':same_artist,'text_quality':grade,
           'text_warnings':warnings,'version_warnings':sorted(labels|set(format_warnings)),
           'cleaning_steps':changes,'diagnostics':d,'duration_delta':delta,'album_support':normalize(c.get('albumName') or '') in albums,
           'candidate_sha256':digest(__import__('json').dumps(c,ensure_ascii=False,sort_keys=True).encode())}
        evidence.append(e)
        target_names=set(target_credit);source_names=set(artist_credit(artist))
        name_tokens=set(normalize(s['artist']).split());source_tokens=set(normalize(artist).split())
        if same_title and ((target_names & source_names) or len(name_tokens & source_tokens)/max(1,len(name_tokens | source_tokens))>=.5):plausible=True
        if same_artist and (target_title in normalize(title) or normalize(title) in target_title):plausible=True
        if same_title and same_artist:eligible.append((c,e,text))
    base={'candidate_count':len(candidates),'candidate_found':bool(candidates),'candidates':evidence,
          'selected':None,'identity_confidence':'identity_ambiguous','text_quality':'text_unassessed',
          'version_warnings':[],'text_warnings':[],'cleaning_steps':[],
          'search_may_be_truncated':len(candidates)>=20,'agreement':[]}
    def finish(status,reason,**kw):return dict(base,status=status,reason=reason,**kw)
    if not candidates:return finish('not_found','No LRCLIB candidates')
    if not eligible:
        base['identity_confidence']='identity_ambiguous' if plausible else 'identity_wrong'
        return finish('quarantined' if plausible else 'wrong_identity','No full compatible title and artist credit')
    base['identity_confidence']='identity_high_confidence'
    base['version_warnings']=sorted({w for _,e,_ in eligible for w in e['version_warnings']})
    base['text_warnings']=sorted({w for _,e,_ in eligible for w in e['text_warnings']})
    safe=[v for v in eligible if v[1]['text_quality'] not in ('text_bad','text_missing') and not (set(v[1]['text_warnings']) & REVIEW_TEXT) and not (set(v[1]['version_warnings']) & RISK)]
    if not safe:
        grades={e['text_quality'] for _,e,_ in eligible}
        if grades <= {'text_bad','text_missing'}:
            base['text_quality']='text_bad' if 'text_bad' in grades else 'text_missing'
            return finish('bad_missing_text','Identity established; no usable text')
        base['text_quality']='text_usable_with_minor_noise'
        return finish('quarantined','Identity established; text or version requires review')
    # Compare distinct texts, not every duplicate pair. Reject substantial disagreement.
    groups={}
    for v in safe:groups.setdefault(normalize(v[2]),v)
    vals=list(groups.values())
    for i,a in enumerate(vals):
        for b in vals[i+1:]:
            ok,ratio=compatible(a[2],b[2]);base['agreement'].append({'a':a[0]['id'],'b':b[0]['id'],'ratio':ratio,'compatible':ok})
            if not ok:
                base['text_quality']='text_usable_with_minor_noise'
                return finish('quarantined','Materially different plausible lyric texts')
    # A duration conflict is supporting uncertainty, not recording-level identity failure.
    supported=[v for v in safe if v[1]['duration_delta'] is None or v[1]['duration_delta']<=15]
    if not supported:
        base['text_quality']='text_usable_with_minor_noise'
        return finish('quarantined','All safe candidates conflict with available durations')
    c,e,text=sorted(supported,key=lambda v:(bool(v[1]['text_warnings']),not(v[1]['duration_delta'] is not None and v[1]['duration_delta']<=2),not v[1]['album_support'],-v[1]['diagnostics']['words'],v[0]['id']))[0]
    base.update(selected=c['id'],text_quality=e['text_quality'],cleaning_steps=e['cleaning_steps'],selected_text_warnings=e['text_warnings'])
    if len(groups)>1:base['text_warnings']=sorted(set(base['text_warnings'])|{'minor_transcription_variation'});base['text_quality']='text_usable_with_minor_noise'
    return finish('accepted','Full title/credit agreement; no material text conflict or detected quality defect')
