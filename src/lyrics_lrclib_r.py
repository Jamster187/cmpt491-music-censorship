"""Offline Phase LRCLIB-R review. No provider client or network entry point."""
import argparse
from collections import Counter
import difflib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

from lyrics_lrclib import ROOT, PERIODS, normalize, credit, digest, guards, save_json, atomic

VERSION = 'lrclib-r-v1'
LEDGER = ROOT/'reports/lyrics_lrclib_r_review.json'
OUTPUT = ROOT/'data/processed/lyrics_lrclib_r.json'
TEXTS = ROOT/'data/cache/lrclib-r/texts'


def load(root=ROOT):
    c=sqlite3.connect((root/'data/processed/lyrics.db').as_uri()+'?mode=ro',uri=True)
    try:
        rows=[json.loads(p) for p, in c.execute('SELECT payload FROM results ORDER BY song_id')]
    finally: c.close()
    if Counter(r['status'] for r in rows)!=Counter(success=112,ambiguous=83,not_found=5):
        raise ValueError('Expected frozen post-review 200-song baseline')
    for r in rows:
        candidates={}
        for ref in r['retrievals']:
            path=root/'data/cache/lrclib'/(digest(ref['url'].encode())+'.json')
            rec=json.loads(path.read_text())
            if rec['url']!=ref['url'] or digest(rec['body'].encode())!=rec['sha256'] or rec['sha256']!=ref['sha256'] or rec['status']!=200:
                raise ValueError('Cache/provenance mismatch')
            for candidate in json.loads(rec['body']):
                if candidate['id'] in candidates and candidates[candidate['id']]!=candidate:
                    raise ValueError('Different revisions of the same ID require explicit handling')
                candidates[candidate['id']]=candidate
        r['raw_candidates']=sorted(candidates.values(),key=lambda x:x['id'])
    return rows


def raw_text(c):
    # Prefer genuine plain text. Do not silently replace a defective plain field with synced text.
    if isinstance(c.get('plainLyrics'),str) and c['plainLyrics'].strip(): return c['plainLyrics']
    if isinstance(c.get('syncedLyrics'),str) and c['syncedLyrics'].strip():
        return re.sub(r'\[\d+:\d+(?:[.:]\d+)?\]', '',c['syncedLyrics'])
    return ''


def clean(text, title, artist):
    """Only reversible formatting and structurally explicit non-lyric headers."""
    changes=[]
    normalized=unicodedata.normalize('NFC',text.replace('\r\n','\n').replace('\r','\n'))
    if normalized!=text: changes.append('unicode_nfc_newlines')
    lines=normalized.splitlines()
    # Remove a title/artist/writer block only when all three lines identify it as a header.
    if len(lines)>=3 and normalize(lines[0])==normalize(title) and normalize(lines[1])==normalize(artist) and re.fullmatch(r'\s*\(words\s*&\s*music\s+by\s+[^\n]+\)\s*',lines[2],re.I):
        lines=lines[3:];changes.append('explicit_title_artist_writer_header')
    kept=[]
    for line in lines:
        if re.fullmatch(r'\s*\[(?:intro|outro|verse(?:\s+\d+)?|chorus|pre-chorus|bridge|instrumental|interlude)\]\s*',line,re.I):
            changes.append('standalone_section_label');continue
        kept.append(line.rstrip())
    result='\n'.join(kept).strip()
    result=(result+'\n') if result else ''
    if result!=normalized and not changes: changes.append('outer_whitespace')
    return result, sorted(set(changes))


def diagnostics(c, song):
    text,changes=clean(raw_text(c),song['title'],song['artist'])
    return {'words':len(text.split()),'lines':len(text.splitlines()),
            'masked_fragments':len(re.findall(r'\b\w*(?:\*{2,}|_{2,})\w*|\b(?:f|sh|ni|n|p|b)-(?=\s|[.,!?])',text,re.I)),
            'encoding_markers':len(re.findall('Ã|â€|�|âs',text)),
            'changes':changes,'sha256':digest(text.encode())}


def audit(rows, start=1, end=83):
    ambiguous=sorted([r for r in rows if r['status']=='ambiguous'],key=lambda r:r['first_chart_date']+r['song_id'])
    # Index is diagnostic only; all decisions bind immutable song IDs and candidate hashes.
    for i,r in enumerate(ambiguous,1):
        if not start<=i<=end:continue
        exact=[c for c in r['raw_candidates'] if normalize(c['trackName'])==normalize(r['title']) and credit(c['artistName'])==credit(r['artist'])]
        if not exact:
            print('NO EXACT IDENTITY',r['title']);continue
        groups={}
        for c in exact or r['raw_candidates']:
            text,_=clean(raw_text(c),r['title'],r['artist'])
            groups.setdefault(normalize(text),[]).append(c)
        print('\n',i,r['song_id'],r['title'],'|',r['artist'],'|',r['first_chart_date'],r['reason'])
        print('duration metadata',r['metadata']['durations'])
        reference=None
        for key,cs in groups.items():
            c=cs[0];words=key.split()
            print('GROUP',c['id'],'count',len(cs),'title',c['trackName'],'artist',c['artistName'],'album',c.get('albumName'),'duration',c.get('duration'),'instrumental',c.get('instrumental'),diagnostics(c,r))
            print('OPEN',' '.join(raw_text(c).split()[:18]),'END',' '.join(raw_text(c).split()[-18:]))
            if reference is not None:
                sm=difflib.SequenceMatcher(None,reference,words,autojunk=False)
                diffs=[(tag,reference[a:b],words[x:y]) for tag,a,b,x,y in sm.get_opcodes() if tag!='equal']
                print('SIMILARITY',round(sm.ratio(),4),'DIFFS',str(diffs)[:1100])
            else: reference=words


IDENTITIES = {'identity_high_confidence','identity_ambiguous','identity_wrong'}
QUALITIES = {'text_good','text_usable_with_minor_noise','text_bad','text_missing'}


def disposition(identity, quality):
    if identity not in IDENTITIES or quality not in QUALITIES:
        raise ValueError('Unsupported independent review status')
    if identity=='identity_wrong': return 'wrong_identity'
    if identity=='identity_ambiguous': return 'identity_ambiguous'
    if quality=='text_missing': return 'missing_text'
    if quality=='text_bad': return 'bad_text'
    return 'recoverable'


def reconcile(rows, ledger):
    expected={r['song_id'] for r in rows if r['status']=='ambiguous'}
    reviews=ledger['reviews']
    if ledger['version']!=VERSION or len(reviews)!=len(expected) or {x['song_id'] for x in reviews}!=expected:
        raise ValueError('Review ledger must cover every original ambiguous asset exactly once')
    indexed={r['song_id']:r for r in rows}
    result=[]
    for review in sorted(reviews,key=lambda x:x['song_id']):
        r=indexed[review['song_id']]
        if (review['billboard_title'],review['billboard_artist'])!=(r['title'],r['artist']):
            raise ValueError('Billboard identity changed')
        cs=[c for c in r['raw_candidates'] if c['id']==review['candidate_id']]
        if len(cs)!=1: raise ValueError('Reviewed candidate absent from frozen cache')
        c=cs[0]
        if digest(json.dumps(c,ensure_ascii=False,sort_keys=True).encode())!=review['candidate_sha256']:
            raise ValueError('Reviewed candidate revision changed')
        outcome=disposition(review['identity_confidence'],review['text_quality'])
        if review['outcome']!=outcome: raise ValueError('Outcome conflicts with independent statuses')
        text,changes=clean(raw_text(c),r['title'],r['artist'])
        if outcome=='recoverable' and (not text.strip() or c.get('instrumental')):
            raise ValueError('Empty/instrumental candidate cannot be a recoverable text')
        if review['text_quality']=='text_missing' and text.strip():
            raise ValueError('Text marked missing despite nonempty selected source text')
        result.append(dict(review,first_chart_date=r['first_chart_date'],original_reason=r['reason'],
                           source='LRCLIB',matched_title=c['trackName'],matched_artist=c['artistName'],
                           album=c.get('albumName'),duration=c.get('duration'),
                           source_text_sha256=digest(raw_text(c).encode()),cleaned_sha256=digest(text.encode()),
                           cleaning_steps=changes,diagnostics=diagnostics(c,r),
                           candidate_availability=bool(r['raw_candidates']),
                           candidates=[dict(id=x['id'],title=x['trackName'],artist=x['artistName'],
                                            album=x.get('albumName'),duration=x.get('duration'),
                                            instrumental=x.get('instrumental'),diagnostics=diagnostics(x,r)) for x in r['raw_candidates']],
                           source_retrievals=r['retrievals'],metadata_evidence=r['metadata'],
                           cleaned_text=text))
    return result


def summary(rows, reviewed):
    original=[r for r in rows if r['status']=='success']
    counts=Counter(r['outcome'] for r in reviewed)
    high={r['song_id'] for r in original}|{r['song_id'] for r in reviewed if r['identity_confidence']=='identity_high_confidence'}
    usable={r['song_id'] for r in original}|{r['song_id'] for r in reviewed if r['outcome']=='recoverable'}
    available={r['song_id'] for r in rows if r['raw_candidates']}
    data={'population':len(rows),'original_accepted':len(original),'ambiguous_reviewed':len(reviewed),
          'recovery':dict(counts),'candidate_availability':len(available),'identity_coverage':len(high),
          'text_usable_coverage':len(usable),'not_found':sum(r['status']=='not_found' for r in rows),
          'identity_grades_reviewed':dict(Counter(r['identity_confidence'] for r in reviewed)),
          'text_grades_reviewed':dict(Counter(r['text_quality'] for r in reviewed)),
          'cleaning_steps_recovered':dict(Counter(x for r in reviewed if r['outcome']=='recoverable' for x in r['cleaning_steps'])),
          'periods':[]}
    for lo,hi,label in PERIODS:
        group={r['song_id'] for r in rows if lo<=int(r['first_chart_date'][:4])<=hi}
        data['periods'].append({'period':label,'assets':len(group),'candidates':len(group&available),
                               'identity_high_confidence':len(group&high),'usable':len(group&usable),
                               'usable_percent':round(100*len(group&usable)/len(group),2)})
    return data


def render(data):
    co=Counter(data['recovery'])
    lines=['# Phase LRCLIB-R: offline ambiguity review','',
           'All 83 ambiguous pilot assets were reviewed using only existing cached LRCLIB responses. **Zero new network requests.** The original 112 accepted files, five not-found decisions, original pilot database, and MusicBrainz state were preserved.', '',
           '## Recovery','',
           '| Result | Assets |','|---|---:|',f"| Original accepted | {data['original_accepted']} |",f"| Ambiguous reviewed | {data['ambiguous_reviewed']} |",f"| Newly recoverable | {co['recoverable']} |",f"| Still identity ambiguous | {co['identity_ambiguous']} |",f"| Rejected for bad text, identity established | {co['bad_text']} |",f"| Missing/instrumental text, identity established | {co['missing_text']} |",f"| Rejected for wrong identity | {co['wrong_identity']} |",f"| Original not found | {data['not_found']} |",'',
           'The recovery outcomes partition the 83 reviewed assets; the other 117 retain their original decisions. Missing text is reported separately from defective text. A wrong-identity candidate can have well-formed text: its text grade does not make it usable for the target asset.', '',
           '| Independent coverage metric | Assets / 200 | Coverage |','|---|---:|---:|']
    for name,key in [('Any LRCLIB candidate','candidate_availability'),('High-confidence Billboard identity','identity_coverage'),('Text usable for the intended content study','text_usable_coverage')]:
        lines.append(f"| {name} | {data[key]} / 200 | {data[key]/2:.1f}% |")
    lines += ['', 'Identity coverage includes confirmed instrumental/missing-text and bad-text assets. It carries forward the original 112 identity acceptances; those assets were not regraded in this focused review. Candidate availability includes unrelated search hits and must not be interpreted as correct-song coverage.', '',
              '## Revised period coverage','',
              '| First-chart period | Pilot assets | Any candidate | Correct identity | Usable text | Usable coverage |',
              '|---|---:|---:|---:|---:|---:|']
    for p in data['periods']:
        lines.append(f"| {p['period']} | {p['assets']} | {p['candidates']} | {p['identity_high_confidence']} | {p['usable']} | {p['usable_percent']}% |")
    lines += ['', '2015–2019 overlaps 2010–2019 and contains only eight assets. Periods use first Billboard appearance, not release dates. Pilot results do not establish full-population coverage.', '',
              '## Identity and text findings','',
              '- Multiple records and minor text differences are not identity failures. Many rejections reflected contractions, vocalizations, word boundaries, spelling, or refrain repetitions. Conflicting texts remain retained; neither majority count nor a similarity score proves correctness.',
              '- Explicit reviewed crosswalks recover full credits separated differently, a featured artist moved into the title, an attached AKA name, and guest evidence present in another cached version. Missing collaborator evidence remains unresolved for Fame And Fortune, I Chose To Sing The Blues, Hot Dawgit, MJB Da MVP, and the composite-credit I\'m A Flirt.',
              '- Knife Talk has an existing substantially unmasked source with complete artist names separated by escaped null markers. Gangstas has an existing Dirty title variant, despite a contradictory Clean album label. These existing texts are selected without inventing or uncensoring words; version/censorship warnings remain. No claim is made that either is the exact radio edit heard during its chart run.',
              '- Flooded The Face contains a spam candidate and a masked candidate alongside usable text. Rejecting those candidate texts does not require rejecting the matching asset.',
              '- Steady Mobbin\' has a 310-second cached record matching available duration evidence and sharing the exact text of the 165-second record. The original duration-only rejection is resolved without external queries.',
              '- Wonderland remains text_bad: all matching cached texts terminate after 49 words with an unfinished continuation. All About My Girl, Popcorn and Theme From Magnum P.i. retain high-confidence identities with text_missing/instrumental status; no empty file is treated as a successful lyric.',
              '- Our Lips Are Sealed retains its unique verses and bridge; an abbreviated final reprise is minor repetition uncertainty under this content-oriented review. Gone Till November has one localized encoding defect in 548 words, retained unchanged. When You\'re Mad retains its localized alternate wording with a version warning.', '',
              'These are assistant reviews of cached metadata, excerpts and token differences, not audio-verified or independently transcribed ground truth. text_good means no material defect identified; text_usable_with_minor_noise means the substantive text is present with documented uncertainty. Exact lyric-frequency or performed-repetition studies may need stricter exclusions. No classifier or hardness scores were implemented.', '',
              '## Conservative cleaning','',
              'The cleaner normalizes line endings and Unicode NFC, trims outer/trailing whitespace, removes narrowly recognized standalone bracketed section labels, and removes a leading title/artist/writer block only when all three lines structurally establish it as a header. It does not strip arbitrary parenthetical content, artist names inside lyrics, spoken outros, repetitions, or censored fragments. It does not repair mojibake, infer missing words, expand refrain instructions, or uncensor text.', '',
              'An American Trilogy is recovered by removing its explicit metadata header. The raw source, raw-text hash, cleaning operations and cleaned-text hash are retained. The cleaner is applied only to selected newly recoverable texts, with every choice bound to a specific cached candidate revision.', '',
              '## Reproduce and audit','',
              '```bash','python3 src/lyrics_lrclib_r.py build','python3 -m unittest discover -s tests -v','```','',
              '- [Versioned review ledger](../../reports/lyrics_lrclib_r_review.json): one explicit identity grade, text grade, selected candidate, source hash, reason and warning list for every ambiguous asset.',
              '- [Generated case table](../../reports/lyrics_lrclib_r_cases.csv): 83 rows with original Billboard identity, matched LRCLIB identity, independent grades and review reasons; no lyrics.',
              '- Local result/combined-corpus manifest: `data/processed/lyrics_lrclib_r.json`.',
              '- Newly recoverable cleaned texts: `data/cache/lrclib-r/texts/<song_id>.txt`; original accepted files remain `data/lyrics/<song_id>.txt`. No canonical files were replaced and no unified-database import was run.',
              '- Existing candidate responses remain under `data/cache/lrclib/`. Outputs reference their URLs, retrieval timestamps, response hashes and frozen metadata evidence. Rebuild validates all 83 ledger entries and their cached candidate hashes, and leaves both acquisition databases untouched.',
              '- The ledger is an explicit pilot crosswalk, not a trained/general matcher. Full acquisition would need to carry forward the same independent grades and route uncertain identities, substantial text defects and version conflicts to review; these 83 decisions cannot simply be applied to new songs.', '',
              '## Recommendation','',
              f"**GO for a staged, reviewed full-population collection using LRCLIB**, subject to the user's next authorization. Revised usable coverage is {data['text_usable_coverage']}/200 ({data['text_usable_coverage']/2:.1f}%). Identity mistakes were not traded for recall: unresolved credits and unrelated performers remain excluded. Preserve raw/cleaned variants and censorship warnings, and retain text-quality review instead of treating HTTP success as corpus acceptance. This is not approval of unattended acceptance or a claim that the original matcher generalizes.", '',
              'No full acquisition, provider change, classifier, or statistical analysis was started.']
    return '\n'.join(lines)+'\n'


def build(root=ROOT):
    import csv
    import io
    from lyrics_lrclib import validate as validate_original
    guards(root)
    rows=load(root)
    ledger=json.loads((root/'reports/lyrics_lrclib_r_review.json').read_text())
    reviewed=reconcile(rows,ledger)
    c=sqlite3.connect((root/'data/processed/lyrics.db').as_uri()+'?mode=ro',uri=True)
    try: validate_original(c,root)
    finally: c.close()
    text_dir=root/'data/cache/lrclib-r/texts'
    for p in [text_dir,*text_dir.parents]:
        if p==root:break
        if p.is_symlink():raise ValueError('Symlink output directory refused')
    data=summary(rows,reviewed)
    corpus=[]
    for r in rows:
        if r['status']=='success':
            corpus.append({'song_id':r['song_id'],'title':r['title'],'artist':r['artist'],
                           'path':r['lyrics_path'],'sha256':r['lyrics_sha256'],'review_basis':'original_pilot_acceptance'})
    serialized=[]
    for r in reviewed:
        item={k:v for k,v in r.items() if k!='cleaned_text'}
        item['path']=None
        if r['outcome']=='recoverable':
            path=text_dir/(r['song_id']+'.txt');data_bytes=r['cleaned_text'].encode()
            if path.exists() and (path.is_symlink() or path.read_bytes()!=data_bytes):
                raise ValueError('Different prior reviewed text; use an explicit new review version')
            if not path.exists():atomic(path,data_bytes)
            item['path']=str(path.relative_to(root))
            corpus.append({'song_id':r['song_id'],'title':r['billboard_title'],'artist':r['billboard_artist'],
                           'path':item['path'],'sha256':r['cleaned_sha256'],'review_basis':VERSION})
        serialized.append(item)
    if len({r['song_id'] for r in corpus})!=len(corpus):raise ValueError('Duplicate corpus identity')
    for r in corpus:
        if digest((root/r['path']).read_bytes())!=r['sha256']:raise ValueError('Combined-corpus file mismatch')
    payload={'version':VERSION,'pipeline_sha256':digest(Path(__file__).read_bytes()),
             'ledger_sha256':digest((root/'reports/lyrics_lrclib_r_review.json').read_bytes()),
             'baseline_rows_sha256':digest(json.dumps([{k:v for k,v in r.items() if k!='raw_candidates'} for r in rows],ensure_ascii=False,sort_keys=True).encode()),
             'normalization_unicode_version':unicodedata.unidata_version,'summary':data,
             'reviews':serialized,'corpus':sorted(corpus,key=lambda x:x['song_id'])}
    save_json(root/'data/processed/lyrics_lrclib_r.json',payload)
    atomic(root/'archive/intermediate_reports/lyrics_lrclib_r_results.md',render(data).encode())
    buf=io.StringIO(newline='')
    fields=['song_id','billboard_title','billboard_artist','first_chart_date','candidate_id','matched_title','matched_artist','album','duration','identity_confidence','text_quality','outcome','reason','warnings','cleaning_steps','source_text_sha256','cleaned_sha256']
    writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for r in serialized:
        writer.writerow({k:json.dumps(r[k],ensure_ascii=False) if isinstance(r[k],list) else r[k] for k in fields})
    # Render provider NUL separators visibly in the human-readable CSV; the JSON
    # manifest retains the exact source metadata with standard JSON escaping.
    atomic(root/'reports/lyrics_lrclib_r_cases.csv',buf.getvalue().replace('\x00',r'\u0000').encode())
    return data


if __name__=='__main__':
    import fcntl
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['audit','build'])
    parser.add_argument('--start',type=int,default=1);parser.add_argument('--end',type=int,default=83)
    args=parser.parse_args();guards()
    with (ROOT/'data/processed/lyrics_lrclib_r.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.command=='audit':audit(load(),args.start,args.end)
        else:print(json.dumps(build(),ensure_ascii=False,indent=2))
