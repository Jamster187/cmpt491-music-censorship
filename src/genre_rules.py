"""Exact raw-label mapping and conservative pilot-only primary-genre decisions."""
import json
from pathlib import Path
import re
import unicodedata
ROOT=Path(__file__).resolve().parents[1]
RULES=json.loads((ROOT/'docs/genre/taxonomy_mapping.json').read_text())
TAXONOMY=tuple(RULES['taxonomy'])


def normalize(value):
    return ' '.join(unicodedata.normalize('NFKC',value).casefold().translate(str.maketrans({'‐':'-','‑':'-','–':'-','—':'-'})).split())


def mapping(label):return RULES['aliases'].get(normalize(label),[])


def eligible(row):
    if row['votes']<=0:return False
    if row['provider']=='Wikidata':
        statement=json.loads(row['raw'])
        if statement.get('rank')=='deprecated' or statement.get('qualifiers'):return False
    return bool(mapping(row['label']))


def assign(rows):
    """No voting by record duplication; weaker levels cannot settle strong ties."""
    usable=[r for r in rows if eligible(r)]
    supported=sorted({g for r in usable for g in mapping(r['label'])},key=TAXONOMY.index)
    # Release/album evidence stays context: compilation and recording specificity
    # are not established by the existing asset-level enrichment.
    tiers=[('direct_song', [r for r in usable if r['level'] in ('recording','song_item')]),
           ('single_release',[r for r in usable if r.get('single_release_context')]),
           ('artist_context',[r for r in usable if r['level']=='artist'])]
    selected=[];tier='none'
    for tier,selected in tiers:
        if selected:break
    if not selected:
        return dict(primary_genre=None,mapped_genres=supported,primary_candidates=[],genre_confidence='insufficient_evidence',genre_source=[],genre_ambiguous=False,disposition='insufficient_evidence')
    choices={g for r in selected for g in mapping(r['label'])}
    # Broad rock can be redundant alongside an explicitly identified subgenre.
    # Other rock labels (pop rock, country rock, etc.) remain competing evidence.
    rock_rows=[r for r in selected if 'Rock' in mapping(r['label'])]
    if choices&{'Metal','Alternative / Indie'} and rock_rows and all(normalize(r['label']) in ('rock','rock music') for r in rock_rows):choices.discard('Rock')
    choices=sorted(choices,key=TAXONOMY.index)
    sources=sorted({r['provider']+'/'+r['level'] for r in selected})
    primary=choices[0] if len(choices)==1 else None
    if len(choices)>1:disposition='ambiguous';confidence=tier+'_multiple'
    elif tier=='artist_context':disposition='context_only';confidence='artist_context_only'
    elif primary=='Other':disposition='Other';confidence=tier+'_other'
    elif tier=='direct_song':disposition='confident_primary';confidence='direct_single_category'
    elif tier=='single_release':disposition='release_supported';confidence='single_release_context'
    else:disposition='context_only';confidence='artist_context_only'
    # Artist-only evidence is a provisional suggestion, not a confident song label.
    if tier=='artist_context':primary=None
    return dict(primary_genre=primary,mapped_genres=supported,primary_candidates=choices,genre_confidence=confidence,genre_source=sources,genre_ambiguous=len(choices)>1,disposition=disposition)
