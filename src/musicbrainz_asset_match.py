"""Offline asset evidence rules; no fuzzy scores or network access."""

import calendar
import datetime as dt
import re
import unicodedata

from metadata_match import artist_credit

VERSION = "phase2ar-asset-v1"

# Unknown performance descriptors cannot silently contribute asset metadata.
BENIGN_DESCRIPTOR = re.compile(
    r"(?:clean(?: version)?|explicit|(?:original )?(?:mono|stereo)(?: mix)?|"
    r"(?:original|album|single|main) version|radio edit|edited single version|"
    r"(?:\d{4} )?remaster(?:ed)?|dolby atmos(?: mix)?|5\.1 mix|"
    r"dts 6\.1 surround|360 reality audio mix)(?:, (?:clean|explicit))?$")


def text_key(value, artist=False):
    value = unicodedata.normalize("NFC", value).casefold()
    value = value.translate(str.maketrans({"’": "'", "‘": "'", "‐": "-", "‑": "-", "–": "-", "—": "-"}))
    if artist:
        # Accent folding is confined to Latin letters; preserve other scripts.
        value = "".join("".join(c for c in unicodedata.normalize("NFD", ch)
                                 if not unicodedata.combining(c))
                        if "LATIN" in unicodedata.name(ch, "") else ch for ch in value)
        value = re.sub(r"\b(?:featuring|feat\.?|ft\.?)\s+", "and ", value)
        value = value.replace("&", " and ")
        value = re.sub(r"(^|\band\s+)the\s+", r"\1", value)
    # Apostrophes and full stops may disappear; separators keep word boundaries.
    value = value.translate(str.maketrans({"'": "", ".": "", ",": " ", ":": " ",
                                         ";": " ", "-": " ", '"': " ", "“": " ", "”": " "}))
    return " ".join(value.split())


def date_bounds(value):
    """Partial dates are intervals, not invented exact release dates."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}(?:-\d{2})?(?:-\d{2})?", value):
        return None
    try:
        parts = [int(p) for p in value.split("-")]
        y = parts[0]
        m = parts[1] if len(parts) > 1 else 1
        d = parts[2] if len(parts) > 2 else 1
        start = dt.date(y, m, d)
        end = dt.date(y, parts[1] if len(parts) > 1 else 12,
                      parts[2] if len(parts) > 2 else calendar.monthrange(y, parts[1] if len(parts) > 1 else 12)[1])
        return start, end
    except ValueError:
        return None


def credit_compatible(billboard, raw):
    key = text_key(billboard, True)
    if key and key == text_key(artist_credit(raw), True):
        return True
    # "with" is a separator only at known structured artist boundaries. It is
    # never replaced inside a band's name, and no contributor may be omitted.
    parts = [p for p in raw.get("artist-credit", []) if isinstance(p, dict)]
    if len(parts) < 2:
        return False
    names = [text_key(p.get("name", p.get("artist", {}).get("name", "")), True) for p in parts]
    if not all(names):
        return False
    pattern = r"(?: and | with )".join(r"(?:the )?" + re.escape(name) for name in names)
    return re.fullmatch(pattern, key) is not None


def evaluate(song, raw, artist_entities=None):
    title = raw.get("title", "")
    credit = artist_credit(raw)
    ids = sorted({p["artist"]["id"] for p in raw.get("artist-credit", [])
                  if isinstance(p, dict) and p.get("artist", {}).get("id")})
    chart = dt.date.fromisoformat(song["first_chart_date"])
    date_evidence = []
    dates = [("recording.first-release-date", raw.get("id"), raw.get("first-release-date"))]
    for release in raw.get("releases", []):
        dates.append(("release.date", release.get("id"), release.get("date")))
        group = release.get("release-group", {})
        dates.append(("release-group.first-release-date", group.get("id"), group.get("first-release-date")))
    for field, entity, value in dates:
        if not value:
            continue
        bounds = date_bounds(value)
        category = "invalid"
        if bounds:
            category = ("before_or_on_chart" if bounds[1] <= chart else
                        "overlaps_chart" if bounds[0] <= chart else
                        "later_in_chart_year" if bounds[0].year == chart.year else
                        "within_following_year" if bounds[0].year <= chart.year + 1 else "later")
        date_evidence.append({"field": field, "entity_id": entity, "value": value, "category": category})
    descriptor = unicodedata.normalize("NFC", raw.get("disambiguation", "")).casefold().replace("‐", "-")
    # These change performances/content. Ordinary remasters, mono/stereo and edits
    # do not by themselves change the asset, but remain explicit version evidence.
    pattern = r"\b(live|remix(?:ed)?|instrumental|karaoke|demo|acoustic|re-?record(?:ing|ed)|dj[ -]?mix|video)\b"
    unexpected = sorted(set(re.findall(pattern, text_key(title) + " " + descriptor)) -
                        set(re.findall(pattern, text_key(song["title"]))))
    dated_version = bool(re.search(r"\b\d{4}\s+(?:version|recording)\b", descriptor))
    unknown_descriptor = bool(descriptor and not BENIGN_DESCRIPTOR.fullmatch(descriptor))
    impossible = []
    for aid in ids:
        entity = (artist_entities or {}).get(aid, {})
        begin = date_bounds(entity.get("life-span", {}).get("begin"))
        if begin and begin[0] > dt.date(chart.year + 1, 12, 31):
            impossible.append({"artist_id": aid, "begin": entity["life-span"]["begin"], "type": entity.get("type")})
    title_ok = bool(text_key(title)) and text_key(title) == text_key(song["title"])
    artist_ok = credit_compatible(song["artist"], raw)
    complete_ids = all(p.get("artist", {}).get("id") for p in raw.get("artist-credit", []) if isinstance(p, dict))
    compatible = title_ok and artist_ok and bool(ids) and complete_ids and not unexpected and not dated_version and not unknown_descriptor and not raw.get("video") and not impossible
    anchor = any(d["category"] in ("before_or_on_chart", "overlaps_chart", "later_in_chart_year", "within_following_year") for d in date_evidence)
    return {"recording_id": raw.get("id"), "title": title, "artist_credit": credit,
            "artist_ids": ids, "disambiguation": raw.get("disambiguation", ""),
            "title_compatible": title_ok, "artist_compatible": artist_ok,
            "compatible": compatible, "temporal_anchor": anchor,
            "dates": date_evidence, "excluded_version_markers": unexpected,
            "dated_version": dated_version, "video": bool(raw.get("video")),
            "unknown_version_descriptor": unknown_descriptor,
            "impossible_artist_chronology": impossible,
            "provider_search_score": raw.get("score"), "duration_ms": raw.get("length"),
            "duration_outlier_review": isinstance(raw.get("length"), (int, float)) and
            (raw["length"] < 45000 or raw["length"] > 900000),
            "normalized_title": text_key(title), "normalized_credit": text_key(credit, True)}


def decide(song, candidates, artist_entities=None, truncated=False):
    evidence = sorted((evaluate(song, c, artist_entities) for c in candidates), key=lambda c: c["recording_id"])
    compatible = [c for c in evidence if c["compatible"]]
    groups = {tuple(c["artist_ids"]) for c in compatible}
    status, reason = "ambiguous", "no_compatible_full_title_and_credit"
    if not candidates:
        status, reason = "not_found", "no_cached_search_candidates"
    elif len(groups) > 1:
        reason = "competing_artist_identities"
    elif compatible and not any(c["temporal_anchor"] for c in compatible):
        reason = "compatible_identity_but_no_temporal_anchor"
    elif compatible:
        status, reason = "high_confidence", "compatible_asset_with_release_anchor"
    support = compatible if status == "high_confidence" else []
    flags = []
    if truncated:
        flags.append("bounded_search_truncated")
    if support:
        categories = {d["category"] for c in support for d in c["dates"]}
        if not categories.intersection({"before_or_on_chart", "overlaps_chart", "later_in_chart_year"}):
            flags.append("anchor_only_in_following_year")
        if not categories.intersection({"before_or_on_chart"}):
            flags.append("no_date_definitely_before_chart")
        if any(not c["temporal_anchor"] for c in support):
            flags.append("later_or_undated_recordings_supported_by_asset_anchor")
        if any(c["disambiguation"] for c in support):
            flags.append("version_descriptors_retained")
        if any(re.search(r"\b(?:clean|explicit)\b", c["disambiguation"], re.I) for c in support):
            flags.append("content_version_requires_future_resolution")
        if any(c["duration_outlier_review"] for c in support):
            flags.append("duration_outlier_review")
        if any(text_key(c["title"]) != c["title"].casefold() or
               text_key(c["artist_credit"], True) != c["artist_credit"].casefold() for c in support):
            flags.append("formatting_normalization_used")
    return {"asset_match_status": status, "reason": reason,
            "canonical_recording_status": "unresolved_multiple" if len(support) > 1 else
            "single_observed_candidate" if support else "unresolved",
            "supporting_recording_ids": [c["recording_id"] for c in support],
            "supporting_artist_ids": sorted({a for c in support for a in c["artist_ids"]}),
            "review_flags": flags, "candidates": evidence}
