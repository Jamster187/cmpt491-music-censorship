"""Auditable title/performer matching, without choosing one recording edition."""

import re
from difflib import SequenceMatcher

from metadata_match import comparison_key

MATCHER_VERSION = "phase2b-wikidata-asset-v1"
MUSIC_TYPES = {"Q7366", "Q134556", "Q7302866", "Q105543609", "Q3302947"}
JOIN = re.compile(r"^(?:\s+(?:feat\.|with|&|x|vs\.?|\+)\s+|\s*,\s*|\s*/\s*)")


def claims(entity, prop, include_deprecated=False):
    return [row for row in entity.get("claims", {}).get(prop, [])
            if include_deprecated or row.get("rank") != "deprecated"]


def values(entity, prop):
    return [row["mainsnak"]["datavalue"]["value"] for row in claims(entity, prop)
            if row.get("mainsnak", {}).get("snaktype") == "value" and "datavalue" in row["mainsnak"]]


def item_ids(entity, prop):
    return sorted({v["id"] for v in values(entity, prop) if isinstance(v, dict) and v.get("id", "").startswith("Q")})


def names(entity, titles=False):
    result = [{"value": value["value"], "language": value["language"], "origin": "label"}
              for value in entity.get("labels", {}).values()]
    result += [{"value": value["value"], "language": value["language"], "origin": "alias"}
               for language in entity.get("aliases", {}).values() for value in language]
    if titles:
        result += [{"value": value["text"], "language": value.get("language"), "origin": "P1476"}
                   for value in values(entity, "P1476") if isinstance(value, dict) and value.get("text")]
    return result


def label(entity):
    return next((entity.get("labels", {}).get(lang, {}).get("value") for lang in ("en", "mul")
                 if entity.get("labels", {}).get(lang, {}).get("value")), entity.get("id", ""))


def credit_evidence(credit, performers):
    """Match complete names/aliases, allowing separators between distinct entities.

    Whole ensemble names are tried intact. No featured artist can disappear and
    no extra performer on a multi-cover composition can be silently ignored.
    """
    credit = comparison_key(credit, artist=True)
    aliases = {qid: [(comparison_key(n["value"], artist=True), n) for n in names(entity)]
               for qid, entity in performers.items()}
    overlap = sorted(qid for qid, entries in aliases.items()
                     if any(key and re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", credit) for key, _ in entries))

    def consume(remaining, unused):
        if not unused:
            return [] if not remaining else None
        for qid in sorted(unused):
            for key, raw_name in aliases[qid]:
                if not key or not remaining.startswith(key):
                    continue
                rest = remaining[len(key):]
                if len(unused) == 1 and not rest:
                    return [dict(raw_name, artist_id=qid)]
                separator = JOIN.match(rest)
                if separator:
                    tail = consume(rest[separator.end():], unused - {qid})
                    if tail is not None:
                        return [dict(raw_name, artist_id=qid)] + tail
        return None

    mapping = consume(credit, set(performers)) if 0 < len(performers) <= 10 else None
    return {"full_credit_exact": mapping is not None, "matched_names": mapping or [], "overlapping_artist_ids": overlap}


def type_path(qid, entities, depth=4, seen=None):
    if qid in MUSIC_TYPES:
        return [qid]
    seen = set(seen or ())
    if depth == 0 or qid in seen:
        return []
    for parent in item_ids(entities.get(qid, {}), "P279"):
        path = type_path(parent, entities, depth - 1, seen | {qid})
        if path:
            return [qid] + path
    return []


def evaluate(song, entity, context, pair_search_ids):
    title_key = comparison_key(song["title"])
    possible_names = names(entity, titles=True)
    matching_names = [n for n in possible_names if comparison_key(n["value"]) == title_key]
    title_ratio = max((SequenceMatcher(None, title_key, comparison_key(n["value"]), autojunk=False).ratio()
                       for n in possible_names), default=0)
    performer_ids = item_ids(entity, "P175")
    performers = {qid: context.get(qid, {"id": qid}) for qid in performer_ids}
    credit = credit_evidence(song["artist"], performers)
    unknown_performer = any(row.get("mainsnak", {}).get("snaktype") != "value" for row in claims(entity, "P175"))
    paths = [p for p in (type_path(qid, context) for qid in item_ids(entity, "P31")) if p]
    description = entity.get("descriptions", {}).get("en", {}).get("value", "")
    version_text = label(entity) + " " + description
    version_markers = re.findall(r"\b(?:remix(?:ed)?|remaster(?:ed)?|live recording|karaoke|instrumental version)\b", version_text, re.I)
    unexpected = [v for v in version_markers if v.casefold() not in song["title"].casefold()]
    plausible = bool(matching_names) and bool(credit["overlapping_artist_ids"] or entity["id"] in pair_search_ids)
    eligible = bool(matching_names and paths and credit["full_credit_exact"] and not unknown_performer and not unexpected)
    dates = [v for v in values(entity, "P577") if isinstance(v, dict)]
    years = [int(v["time"][1:5]) for v in dates if re.match(r"^\+\d{4}-", v.get("time", "")) and v.get("precision", 0) >= 9]
    score = round(50 * title_ratio + (45 if credit["full_credit_exact"] else 20 if credit["overlapping_artist_ids"] else 0) + (5 if paths else 0), 3)
    return {"entity_id": entity["id"], "revision_id": entity.get("lastrevid"),
            "candidate_title": label(entity), "candidate_artist": " + ".join(label(performers[qid]) for qid in performer_ids),
            "artist_ids": performer_ids, "entity_types": item_ids(entity, "P31"),
            "eligible": eligible, "plausible": plausible, "match_score": score,
            "evidence": {"matched_titles": matching_names, "title_similarity": round(title_ratio, 4),
                         "credit": credit, "unknown_performer_statement": unknown_performer,
                         "music_type_paths": paths, "unexpected_version_markers": unexpected,
                         "joint_search_hit": entity["id"] in pair_search_ids,
                         "publication_years": years,
                         "all_publication_years_after_chart": bool(years) and min(years) > int(song["first_chart_date"][:4]) + 1}}


def decide(song, entities, context, pair_search_ids=(), truncated=False):
    candidates = sorted((evaluate(song, entity, context, pair_search_ids) for entity in entities.values() if "missing" not in entity),
                        key=lambda c: (-c["match_score"], c["entity_id"]))
    eligible = [c for c in candidates if c["eligible"]]
    plausible = [c for c in candidates if c["plausible"]]
    status, reason, selected = "not_found", "no_plausible_title_performer_candidate", []
    if eligible:
        performer_sets = {tuple(c["artist_ids"]) for c in eligible}
        if len(performer_sets) > 1:
            status, reason = "ambiguous", "different_artist_entities_share_the_credit"
        else:
            status, reason = "high_confidence", "exact_title_and_complete_performer_set"
            selected = [c["entity_id"] for c in eligible]
    elif plausible:
        status, reason = "ambiguous", "incomplete_credit_type_or_version_evidence"
    if truncated and status != "high_confidence":
        status, reason = "ambiguous", "bounded_search_incomplete"
    return {"status": status, "reason": reason, "found": bool(plausible or eligible),
            "selected_entity_ids": selected, "match_score": max((c["match_score"] for c in eligible or plausible), default=None),
            "candidates": candidates, "search_truncated": truncated}
