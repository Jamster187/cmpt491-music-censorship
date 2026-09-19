"""Summaries of the Phase 2A experiment; does not call external services."""

import csv
import hashlib
import json
import platform
import unicodedata
from collections import Counter
from pathlib import Path

from metadata_match import MATCHER_VERSION, artist_credit
from musicbrainz import write_json
from phase2a import PERIODS

STATUSES = ("high_confidence", "ambiguous", "not_found", "error")


def has_names(values):
    return any(isinstance(value, dict) and value.get("name") for value in values)


def coverage_flags(result):
    if result["status"] != "high_confidence":
        return {}
    metadata = result.get("metadata") or {}
    recording = metadata.get("recording", {})
    artists, groups = metadata.get("artists", []), metadata.get("release_groups", [])
    releases = recording.get("releases", [])
    return {
        "recording_genres": has_names(recording.get("genres", [])),
        "recording_positive_vote_genres": any(row.get("name") and row.get("count", 0) > 0 for row in recording.get("genres", [])),
        "recording_tags": has_names(recording.get("tags", [])),
        "recording_genres_or_tags": has_names(recording.get("genres", []) + recording.get("tags", [])),
        "release_group_genres": any(has_names(row.get("genres", [])) for row in groups),
        "release_group_tags": any(has_names(row.get("tags", [])) for row in groups),
        "artist_genres": any(has_names(row.get("genres", [])) for row in artists),
        "artist_tags": any(has_names(row.get("tags", [])) for row in artists),
        "first_release_date": bool(recording.get("first-release-date")),
        "album_or_release": any(row.get("id") and row.get("title") for row in releases),
        "album_context": any(row.get("primary-type") == "Album" for row in groups) or any(row.get("release-group", {}).get("primary-type") == "Album" for row in releases),
        "duration": isinstance(recording.get("length"), int) and recording["length"] > 0,
        "recording_id": bool(recording.get("id")),
        "artist_ids": any(isinstance(row, dict) and row.get("artist", {}).get("id") for row in recording.get("artist-credit", [])),
        "release_group_ids": bool(groups) or any(row.get("release-group", {}).get("id") for row in releases),
        "isrcs": bool(recording.get("isrcs")),
        "work_ids": any(row.get("work", {}).get("id") for row in recording.get("relations", [])),
        "artist_type": any(row.get("type") for row in artists),
        "artist_country": any(row.get("country") for row in artists),
        "release_country": any(row.get("country") for row in releases),
        "release_text_language": any(row.get("text-representation", {}).get("language") for row in releases),
        "recording_rating": recording.get("rating", {}).get("value") is not None,
    }


def percent(numerator, denominator):
    return round(100 * numerator / denominator, 2) if denominator else None


def summarize(sample, results):
    expected = {song["song_id"] for song in sample["songs"]}
    identifiers = [row["song"]["song_id"] for row in results]
    if len(set(identifiers)) != len(identifiers) or set(identifiers) - expected:
        raise ValueError("Unexpected or repeated result identities")
    if any(row["status"] not in STATUSES or row["matcher_version"] != MATCHER_VERSION for row in results):
        raise ValueError("Unknown status or stale matcher version in results")
    high = [row for row in results if row["status"] == "high_confidence"]
    flags = [coverage_flags(row) for row in high]
    status_counts = {status: sum(row["status"] == status for row in results) for status in STATUSES}
    fields = list(coverage_flags({"status": "high_confidence", "metadata": {}}))
    coverage = {field: {"count": sum(row[field] for row in flags),
                        "percent_of_high_confidence": percent(sum(row[field] for row in flags), len(high)),
                        "percent_of_sample": percent(sum(row[field] for row in flags), len(expected))} for field in fields}
    by_period = []
    for label, _, _, _ in PERIODS:
        rows = [row for row in results if row["song"]["period"] == label]
        total = sum(song["period"] == label for song in sample["songs"])
        counts = {status: sum(row["status"] == status for row in rows) for status in STATUSES}
        by_period.append(dict(period=label, sample_size=total, processed=len(rows), **counts,
                              match_percent=percent(counts["high_confidence"], total),
                              recording_genre_count=sum(coverage_flags(row).get("recording_genres", False) for row in rows)))
    return {"sample_size": len(expected), "processed": len(results), "pending": len(expected) - len(results),
            "status_counts": status_counts, "high_confidence_percent": percent(len(high), len(expected)),
            "coverage": coverage, "by_period": by_period,
            "decision_reasons": dict(sorted(Counter(row["reason"] for row in results).items())),
            "songs_with_optional_enrichment_errors": sum(bool((row.get("metadata") or {}).get("enrichment_errors")) for row in results),
            "difficulty_counts": dict(Counter(flag for song in sample["songs"] for flag in song["difficulty_flags"])),
            "selection_counts": dict(Counter(song["selection_reason"] for song in sample["songs"]))}


def cache_audit(cache_dir):
    statuses, times, requests, endpoints = Counter(), [], 0, Counter()
    for path in sorted((cache_dir / "requests").glob("*.json")):
        envelope = json.loads(path.read_text(encoding="utf-8"))
        requests += 1
        endpoints[envelope["url"].split("/ws/2/")[1].split("?")[0].split("/")[0]] += 1
        for attempt in envelope["attempts"]:
            statuses[str(attempt["status"])] += 1
            times.append(attempt["requested_at"])
            if hashlib.sha256(attempt["body"].encode("utf-8")).hexdigest() != attempt["body_sha256"]:
                raise ValueError("Cached body checksum mismatch: " + path.name)
    return {"unique_cached_requests": requests, "attempt_status_counts": dict(statuses), "requests_by_entity_type": dict(endpoints),
            "first_request_at": min(times) if times else None, "last_request_at": max(times) if times else None}


def flatten(result):
    song = result["song"]
    metadata = (result.get("metadata") or {}) if result["status"] == "high_confidence" else {}
    recording = metadata.get("recording", {})
    return dict(song_id=song["song_id"], title=song["title"], artist=song["artist"], period=song["period"],
                first_chart_date=song["first_chart_date"], status=result["status"], reason=result["reason"],
                provider=result["provider"], match_score=result.get("match_score"), recording_id=result.get("selected_recording_id"),
                external_title=recording.get("title"), external_artist=artist_credit(recording),
                first_release_date=recording.get("first-release-date"), duration_ms=recording.get("length"),
                artist_ids=json.dumps([p["artist"]["id"] for p in recording.get("artist-credit", []) if isinstance(p, dict) and p.get("artist", {}).get("id")]),
                releases=json.dumps(recording.get("releases", []), ensure_ascii=False),
                isrcs=json.dumps(recording.get("isrcs", [])),
                recording_genres=json.dumps(recording.get("genres", []), ensure_ascii=False),
                recording_tags=json.dumps(recording.get("tags", []), ensure_ascii=False),
                release_group_genres_tags=json.dumps([{k: g.get(k) for k in ("id", "title", "genres", "tags")} for g in metadata.get("release_groups", [])], ensure_ascii=False),
                artist_genres_tags=json.dumps([{k: a.get(k) for k in ("id", "name", "genres", "tags")} for a in metadata.get("artists", [])], ensure_ascii=False),
                candidate_count=len(result["candidates"]))


def cell(value):
    return str(value).replace("|", "&#124;").replace("\n", " ")


def generate_report(output_dir, cache_dir, report_path):
    sample = json.loads((output_dir / "sample.json").read_text(encoding="utf-8"))
    results = []
    for song in sample["songs"]:
        path = output_dir / "results" / (song["song_id"] + ".json")
        if path.exists():
            row = json.loads(path.read_text(encoding="utf-8"))
            if row["song"] != song:
                raise ValueError("Result differs from sample: " + song["song_id"])
            results.append(row)
    summary = summarize(sample, results)
    summary["cache_audit"] = cache_audit(cache_dir)
    summary["canonical_database_sha256"] = sample["canonical_database_sha256"]
    summary["billboard_source_sha256"] = sample["billboard_source_sha256"]
    summary["runtime"] = {"python": platform.python_version(), "unicode": unicodedata.unidata_version}
    summary["sample_sha256"] = hashlib.sha256((output_dir / "sample.json").read_bytes()).hexdigest()
    summary["code_sha256"] = {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest() for name in ("musicbrainz.py", "metadata_match.py", "phase2a.py", "enrichment_report.py")}
    write_json(output_dir / "summary.json", summary)
    if results:
        flat = [flatten(row) for row in results]
        with (output_dir / "matches.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
            writer.writeheader()
            writer.writerows(flat)
    statuses, coverage, audit = summary["status_counts"], summary["coverage"], summary["cache_audit"]
    lines = ["# Phase 2A: metadata feasibility", "", "Generated from the cached MusicBrainz experiment. No manual match overrides were applied.", "",
             "MusicBrainz is the only provider tested. See [source research](phase2a_source_research.md) for fields, authentication, rate limits, terms, and possible complements; see [experiment instructions](../experiments/phase2a/README.md) for reproduction and exact matching rules.", "",
             "## Sample and scope", "",
             "The fixed sample has {} unique Billboard title/artist pairs from {} identities. Periods use first Billboard appearance, not release year. Every first-appearance year from 1958 through 2026 is represented. The sample deliberately balances periods and oversamples difficult credits; its aggregate rates are descriptive pilot results, not population estimates.".format(summary["sample_size"], sample["population_size"]), "",
             "Difficulty flags overlap: `{}`. Selection reasons: `{}`.".format(json.dumps(summary["difficulty_counts"], ensure_ascii=False, sort_keys=True), json.dumps(summary["selection_counts"], sort_keys=True)), "",
             "## Matching results", "", "| Status | Count | % of sample |", "| --- | ---: | ---: |"]
    for status in STATUSES:
        lines.append("| {} | {} | {:.2f}% |".format(status, statuses[status], percent(statuses[status], summary["sample_size"])))
    lines += ["| pending | {} | {:.2f}% |".format(summary["pending"], percent(summary["pending"], summary["sample_size"])), "",
              "High-confidence means a unique recording link passing the documented rule, not independently measured matching accuracy. A Billboard asset can legitimately have several recordings: this strict pilot leaves those ambiguous rather than selecting one arbitrarily. `not_found` means no candidates from the two bounded searches, not proof that MusicBrainz lacks the song.", "",
              "| First-chart period | Sample | High confidence | Ambiguous | Not found | Error | Match rate | Recording genres / sample |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in summary["by_period"]:
        lines.append("| {period} | {sample_size} | {high_confidence} | {ambiguous} | {not_found} | {error} | {match_percent:.2f}% | {recording_genre_count}/{sample_size} |".format(**row))
    lines += ["", "## Metadata coverage on accepted links", "",
              "The first percentage uses the {} high-confidence matches; the second uses all {} sampled identities. Unmatched/ambiguous songs do not contribute metadata coverage. Raw tags can describe things other than genre, and contextual release-group/artist genres are not song-level genre assignments.".format(statuses["high_confidence"], summary["sample_size"]), "",
              "| Field / entity level | Count | % of matches | % of sample |", "| --- | ---: | ---: | ---: |"]
    for field, values in coverage.items():
        lines.append("| {} | {} | {}% | {:.2f}% |".format(field, values["count"], "{:.2f}".format(values["percent_of_high_confidence"]) if values["percent_of_high_confidence"] is not None else "N/A", values["percent_of_sample"]))
    lines += ["", "Dates are required by the acceptance rule, so their coverage among accepted links is conditional by construction. Dates may have only year/month precision. Durations are milliseconds. Release text language is not lyric language. Album/release coverage includes singles and reissues; no canonical album is inferred. Release-group lookups are bounded to three eligible groups and recording lookups return only the provider's linked-release subset.", "",
              "## Decision reasons and API reliability", "", "| Reason | Count |", "| --- | ---: |"]
    for reason, count in summary["decision_reasons"].items():
        lines.append("| {} | {} |".format(reason, count))
    lines += ["", "Cached requests: {}. HTTP/transport attempts: `{}`. Optional contextual-lookup errors affected {} songs. Retries and failures are retained, including failures recovered before a song completed.".format(audit["unique_cached_requests"], json.dumps(audit["attempt_status_counts"], sort_keys=True), summary["songs_with_optional_enrichment_errors"]),
              "", "Retrieval window (UTC): {} through {}.".format(audit["first_request_at"], audit["last_request_at"]), "",
              "## Examples", ""]
    for status in STATUSES:
        lines += ["", "### " + status, "", "| Billboard identity | Period | Evidence / reason |", "| --- | --- | --- |"]
        examples = [row for row in results if row["status"] == status][:4]
        for row in examples:
            candidates = row["candidates"]
            evidence = row["reason"]
            if status == "high_confidence":
                rec = row["metadata"]["recording"]
                evidence += "; {} / {}; first release {}; [recording]({})".format(rec["title"], artist_credit(rec), rec.get("first-release-date"), "https://musicbrainz.org/recording/" + rec["id"])
            elif candidates:
                evidence += "; {} candidates; {} eligible; top: {} / {} ({})".format(len(candidates), sum(c["eligible"] for c in candidates), candidates[0]["candidate_title"], candidates[0]["candidate_artist"], candidates[0].get("first_release_date"))
            else:
                evidence += "; " + (row.get("error") or "no results from title + full credit or title + lead artist search")
            lines.append("| {} / {} | {} | {} |".format(cell(row["song"]["title"]), cell(row["song"]["artist"]), row["song"]["period"], cell(evidence)))
        if not examples:
            lines.append("| None in this run | — | — |")
    lines += ["", "### Deliberately difficult cases", "", "| Billboard identity | Difficulty | Outcome |", "| --- | --- | --- |"]
    for flag in ("featured_artists", "punctuation_heavy", "common_title", "unusual_credit"):
        example = next((row for row in results if flag in row["song"]["difficulty_flags"]), None)
        if example:
            lines.append("| {} / {} | {} | {}: {} |".format(cell(example["song"]["title"]), cell(example["song"]["artist"]), flag, example["status"], example["reason"]))
    lines += ["", "See [review notes](phase2a_review_notes.md) for additional inspected examples, including covers, featured credits, older recordings charting recently, and restrictive search-score thresholds. These notes do not override any match decision.", "",
              "## Recommendation", "",
              "Do not scale this matcher to all 32,723 identities yet. Direct recording-genre coverage in this pilot is {}/{} ({:.2f}%); accepted recording links with raw genres are {}/{} ({:.2f}%). Artist/release-group tags offer context but cannot be silently substituted for song genres. This measures the yield of this strict matcher, not the maximum metadata coverage MusicBrainz could provide for title/artist assets.".format(coverage["recording_genres"]["count"], summary["sample_size"], coverage["recording_genres"]["percent_of_sample"], coverage["recording_genres"]["count"], statuses["high_confidence"], coverage["recording_genres"]["percent_of_high_confidence"] or 0), "",
              "Before scaling, independently review a labeled set of accepted and rejected candidates to measure precision, decide how a title/artist asset should link to multiple legitimate recordings, improve artist-credit/alias retrieval without dropping contributors, and investigate dated reissues and early/new-release gaps. Evaluate an additional genre source or an explicitly labeled contextual-genre strategy on this same frozen sample, then validate on a fresh holdout sample. Keep every match decision and entity-level tag provenance. No major-genre taxonomy is chosen here.", "",
              "This run retrieves no lyrics and makes no classifier, COVID-breakpoint, or content-trend inference. Phase 1 remains separate and unchanged. The source snapshot and canonical database hashes, code hashes, full candidate evidence, original responses, per-song results, and CSV export are retained locally in the documented locations.", ""]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("sample_size", "processed", "status_counts", "high_confidence_percent", "coverage", "by_period")}, ensure_ascii=False, indent=2))
