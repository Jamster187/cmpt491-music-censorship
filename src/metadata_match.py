"""Conservative candidate comparison. Scores are evidence, not probabilities."""

import re
import unicodedata
from difflib import SequenceMatcher

MATCHER_VERSION = "phase2a-strict-v1"
VERSION_WORDS = re.compile(r"\b(live|remix|remixed|instrumental|karaoke|demo|acoustic|rerecording|re-recording|remaster(?:ed)?|edit|mono|stereo)\b", re.I)


def comparison_key(value, artist=False):
    value = unicodedata.normalize("NFC", value).casefold()
    value = value.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "‐": "-", "‑": "-", "–": "-", "—": "-"}))
    if artist:
        value = re.sub(r"\b(?:featuring|feat\.?|ft\.?)\s+", "feat. ", value)
        value = re.sub(r"\s+(?:and|&)\s+", " & ", value)
    return " ".join(value.split())


def artist_credit(recording):
    return "".join(part if isinstance(part, str) else part.get("name", part.get("artist", {}).get("name", "")) + part.get("joinphrase", "") for part in recording.get("artist-credit", []))


def query_literal(value):
    return '"' + re.sub(r'([+\-!(){}\[\]^"~*?:\\/]|&&|\|\|)', r'\\\1', value) + '"'


def search_queries(song):
    exact = "recording:{} AND artist:{}".format(query_literal(song["title"]), query_literal(song["artist"]))
    # Retrieval-only fallback. Full credit is still required by the decision rule.
    lead = re.split(r"\s+(?:featuring|feat\.?|ft\.?|with)\s+", song["artist"], flags=re.I)[0]
    fallback = "recording:{} AND artistname:{}".format(query_literal(song["title"]), query_literal(lead))
    return [exact, fallback] if fallback != exact else [exact]


def evaluate_candidate(song, candidate):
    title, artist = candidate.get("title", ""), artist_credit(candidate)
    title_key, artist_key = comparison_key(title), comparison_key(artist, artist=True)
    title_ratio = SequenceMatcher(None, comparison_key(song["title"]), title_key, autojunk=False).ratio()
    artist_ratio = SequenceMatcher(None, comparison_key(song["artist"], artist=True), artist_key, autojunk=False).ratio()
    date = candidate.get("first-release-date") or ""
    year = int(date[:4]) if re.match(r"^\d{4}(?:-|$)", date) else None
    first_chart_year = int(song["first_chart_date"][:4])
    date_support = year is not None and year <= first_chart_year + 1
    unexpected_versions = sorted(set(VERSION_WORDS.findall((title + " " + (candidate.get("disambiguation") or "")).casefold())) - set(VERSION_WORDS.findall(song["title"].casefold())))
    provider_score = int(candidate.get("score", 0))
    evidence = {
        "title_exact": title_ratio == 1, "artist_credit_exact": artist_ratio == 1,
        "title_similarity": round(title_ratio, 4), "artist_similarity": round(artist_ratio, 4),
        "first_release_year": year, "date_support": date_support,
        "date_after_chart_year_plus_one": year is not None and not date_support,
        "unexpected_version_words": unexpected_versions, "video": candidate.get("video") is True,
        "provider_search_score": provider_score,
    }
    eligible = title_ratio == 1 and artist_ratio == 1 and date_support and not unexpected_versions and candidate.get("video") is not True and provider_score >= 95
    rival = title_ratio >= .90 and artist_ratio >= .95 and not unexpected_versions and candidate.get("video") is not True and not evidence["date_after_chart_year_plus_one"] and provider_score >= 90
    return {
        "recording_id": candidate.get("id"), "candidate_title": title, "candidate_artist": artist,
        "artist_ids": [part["artist"]["id"] for part in candidate.get("artist-credit", []) if isinstance(part, dict) and part.get("artist", {}).get("id")],
        "match_score": round(50 * title_ratio + 40 * artist_ratio + (10 if date_support else 0), 3),
        "eligible": eligible, "plausible_rival": rival, "evidence": evidence,
        "first_release_date": date or None, "duration_ms": candidate.get("length"),
        "raw_genres": candidate.get("genres", []), "raw_tags": candidate.get("tags", []),
        "releases": candidate.get("releases", []), "isrcs": candidate.get("isrcs", []),
        "disambiguation": candidate.get("disambiguation", ""),
    }


def decide(song, candidates, truncated=False):
    scored = sorted((evaluate_candidate(song, value) for value in candidates), key=lambda row: (-row["match_score"], row["recording_id"] or ""))
    eligible = [row for row in scored if row["eligible"]]
    selected, status, reason = None, "ambiguous", "no_candidate_passes_strict_rule"
    if not scored:
        status, reason = "not_found", "no_search_candidates"
    elif truncated:
        reason = "search_results_truncated"
    elif len(eligible) > 1:
        reason = "multiple_eligible_recordings"
    elif len(eligible) == 1:
        rivals = [row for row in scored if row["recording_id"] != eligible[0]["recording_id"] and row["plausible_rival"]]
        if rivals:
            reason = "competing_plausible_recordings"
        else:
            selected, status, reason = eligible[0], "high_confidence", "unique_exact_credit_with_date_support"
    return {"status": status, "reason": reason, "selected_recording_id": selected["recording_id"] if selected else None,
            "match_score": selected["match_score"] if selected else (scored[0]["match_score"] if scored else None), "candidates": scored}
