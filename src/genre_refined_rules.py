"""Broad-category evidence support, with explicit abstention; pilot configuration."""
from collections import defaultdict
import json
import re
from genre_rules import ROOT,TAXONOMY,normalize,mapping,eligible
CONFIG=json.loads((ROOT/'docs/genre/refinement_rules.json').read_text())


def tag_family(label):
    """Collapse spelling synonyms, not musically distinct compatible subgenres."""
    s=normalize(label).replace('&',' and ')
    s=re.sub(r'[-/]+',' ',s);s=' '.join(s.split())
    aliases={'hip hop music':'hip hop','rap':'hip hop','rap hip hop':'hip hop',
      'r and b':'rhythm and blues','r b':'rhythm and blues','rnb':'rhythm and blues',
      'country music':'country','rock music':'rock','pop music':'pop','am pop':'pop',
      'heavy metal music':'heavy metal','soul music':'soul','electronic music':'electronic',
      'indie':'indie rock','synthpop':'synth pop','hip hop rap':'hip hop',
      'southern rap':'southern hip hop','east coast rap':'east coast hip hop',
      'west coast rap':'west coast hip hop','alternative rap':'alternative hip hop',
      'trap music':'trap','rap music':'hip hop','edm':'electronic dance music',
      'dance music':'dance','house music':'house','folk music':'folk',
      'jazz music':'jazz','blues music':'blues','reggae music':'reggae',
      'gospel music':'gospel','christian music':'christian'}
    s=s.replace('r and b','rhythm and blues')
    return aliases.get(s,s)


def support(rows):
    """Duplicates, cache revisions and multiple editions cannot multiply support."""
    out={}
    for genre in TAXONOMY:
        tags={};providers=set();entities=set();raw=set()
        for r in rows:
            if not eligible(r) or genre not in mapping(r['label']):continue
            family=tag_family(r['label']);providers.add(r['provider'])
            entities.add((r['provider'],r['level'],r['entity_id']));raw.add(normalize(r['label']))
            tags[family]=max(tags.get(family,0),r['votes'])
        if not tags:continue
        # Votes are per-label maxima, never a sum pretending editors are distinct.
        backed=sum(v>=CONFIG['compatible_tag_min_votes'] for v in tags.values())
        maximum=max(tags.values())
        strong=(maximum>=CONFIG['strong_max_votes'] or backed>=CONFIG['compatible_tag_count']
          or (len(tags)>=CONFIG['broad_compatible_tag_count'] and maximum>=CONFIG['broad_compatible_min_max_votes'])
          or len(providers)>=CONFIG['direct_provider_agreement'])
        out[genre]=dict(supporting_tag_count=len(tags),backed_tag_count=backed,
          supporting_provider_count=len(providers),supporting_entity_count=len(entities),
          max_tag_votes=maximum,tag_support=dict(sorted(tags.items())),raw_labels=sorted(raw),
          providers=sorted(providers),strong=strong)
    return out


def generic_only(evidence,labels):
    backed=[label for label in evidence['raw_labels'] if evidence['tag_support'][tag_family(label)]>=CONFIG['compatible_tag_min_votes']]
    return set(backed or evidence['raw_labels'])<=set(labels)


def assign(rows):
    direct=[r for r in rows if r['level'] in ('recording','song_item')]
    release=[r for r in rows if r['level'] in ('release','release-group','album')]
    artist=[r for r in rows if r['level']=='artist']
    groups={level:support(rs) for level,rs in [('direct_song',direct),('release_context',release),('artist_context',artist)]}
    direct_support=groups['direct_song']
    strong=[g for g in TAXONOMY if direct_support.get(g,{}).get('strong')]
    contenders=list(strong);suppressed=[]
    # Generic Pop is an umbrella, not a veto over strongly evidenced styles.
    if 'Pop' in contenders and len(contenders)>1 and generic_only(direct_support['Pop'],CONFIG['generic_pop']):
        contenders.remove('Pop');suppressed.append('Pop')
    # Rock is a parent of explicit alternative/metal. Hard rock/composite styles
    # remain genuine candidates; they are not silently relabelled as Metal.
    if 'Rock' in contenders and set(contenders)&{'Metal','Alternative / Indie'} and generic_only(direct_support['Rock'],CONFIG['generic_rock']):
        contenders.remove('Rock');suppressed.append('Rock')
    primary=None;reason='no_strong_direct_support'
    if len(contenders)==1:primary=contenders[0];reason='one_strong_category'
    elif contenders:
        ordered=sorted(contenders,key=lambda g:(-direct_support[g]['max_tag_votes'],-direct_support[g]['backed_tag_count'],TAXONOMY.index(g)))
        top=ordered[0];t=direct_support[top]
        # Dominance requires stronger maximum support AND at least as many
        # independently named, backed tag families. No popularity-based weights.
        if all(t['max_tag_votes']>=CONFIG['dominance_ratio']*direct_support[g]['max_tag_votes'] and t['backed_tag_count']>=direct_support[g]['backed_tag_count'] for g in ordered[1:]):
            primary=top;reason='dominant_direct_support'
        else:reason='competing_strong_categories'
    disposition=('Other' if primary=='Other' else 'primary') if primary else ('ambiguous' if contenders else 'insufficient')
    return dict(primary_genre=primary,mapped_genres=strong,secondary_genres=[g for g in strong if g!=primary],
      genre_candidates=contenders,all_mapped_evidence=list(direct_support),
      genre_evidence_level='direct_song' if direct_support else ('release_context' if groups['release_context'] else 'artist_context' if groups['artist_context'] else 'none'),
      genre_support_count=direct_support[primary]['supporting_tag_count'] if primary else None,
      genre_ambiguous=disposition=='ambiguous',conflicting_category_count=max(0,len(contenders)-1),
      suppressed_parent_categories=suppressed,decision_reason=reason,disposition=disposition,support=groups)
