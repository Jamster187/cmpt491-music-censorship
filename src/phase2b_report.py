"""Generate Phase 2B coverage and the comparison with the frozen Phase 2A run."""

import csv
import hashlib
import json
import platform
import unicodedata
from collections import Counter

from billboard import ROOT
from enrichment_report import coverage_flags as musicbrainz_coverage, percent
from musicbrainz import write_json
from phase2a import PERIODS, file_hash
from phase2b import CACHE, OUTPUT, SAMPLE_SHA256, load_sample, verify_foundation
from wikidata_match import MATCHER_VERSION, claims, item_ids, label, values

STATUSES = ("high_confidence", "ambiguous", "not_found", "error")


def coverage_flags(result):
    metadata = result.get("metadata") or {}
    entities = metadata.get("entities", []) if result["status"] == "high_confidence" else []
    genres = [row for entity in entities for row in claims(entity, "P136")
              if row.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")]
    genre_entity_ids = {entity["id"] for entity in entities if item_ids(entity, "P136")}
    genre_type_roots = {path[-1] for candidate in result.get("candidates", [])
                        if candidate["entity_id"] in genre_entity_ids
                        for path in candidate["evidence"]["music_type_paths"]}

    def has(prop):
        return any(values(entity, prop) for entity in entities)

    durations = [value for entity in entities for value in values(entity, "P2047")]
    valid_duration = False
    for value in durations:
        try:
            valid_duration |= float(value.get("amount", "0")) > 0 and value.get("unit") not in (None, "1")
        except (ValueError, AttributeError):
            pass
    return {
        "song_item_genres": bool(genres),
        "recording_or_track_item_genres": bool(genre_type_roots & {"Q7302866", "Q3302947"}),
        "single_release_item_genres": "Q134556" in genre_type_roots,
        "composition_item_genres": "Q105543609" in genre_type_roots,
        "generic_song_item_genres": "Q7366" in genre_type_roots,
        "song_item_genres_unqualified": any(not row.get("qualifiers") for row in genres),
        "song_item_genres_with_references": any(row.get("references") for row in genres),
        "publication_date": any(isinstance(v, dict) and v.get("time") and v.get("precision", 0) >= 9
                                for entity in entities for v in values(entity, "P577")),
        "album_context": bool(entities and metadata.get("album_ids")),
        "duration_quantity": valid_duration,
        "wikidata_song_item_id": bool(entities), "performer_ids": any(item_ids(e, "P175") for e in entities),
        "musicbrainz_recording_id": has("P4404"), "musicbrainz_work_id": has("P435"),
        "musicbrainz_release_group_id": has("P436"), "isrc": has("P1243"),
        "composer_ids": has("P86"), "producer_ids": has("P162"), "record_label_ids": has("P264"),
        "work_language": has("P407"),
        "artist_context_genres": bool(entities) and any(item_ids(a, "P136") for a in metadata.get("artists", [])),
        "album_context_genres": bool(entities) and any(item_ids(a, "P136") for a in metadata.get("parents", [])
                                                      if a["id"] in metadata.get("album_ids", [])),
    }


def summarize(sample, results, phase2a_results):
    expected = {s["song_id"]: s for s in sample["songs"]}
    ids = [r["song"]["song_id"] for r in results]
    if len(set(ids)) != len(ids) or set(ids) - set(expected):
        raise ValueError("Repeated or unknown Phase 2B result identity")
    for row in results:
        if row["song"] != expected[row["song"]["song_id"]] or row["matcher_version"] != MATCHER_VERSION or row["sample_sha256"] != SAMPLE_SHA256:
            raise ValueError("Stale or mismatched Phase 2B result")
        if row["status"] not in STATUSES:
            raise ValueError("Unknown match status")
    a_index = {r["song"]["song_id"]: r for r in phase2a_results}
    if len(a_index) != len(phase2a_results) or set(a_index) != set(expected):
        raise ValueError("Phase 2A comparison must contain exactly the same sample")
    if any(a_index[qid]["song"] != song for qid, song in expected.items()):
        raise ValueError("Phase 2A identity or period was modified")
    fields = list(coverage_flags({"status": "high_confidence"}))

    def measures(rows, n):
        high = sum(r["status"] == "high_confidence" for r in rows)
        flags = [coverage_flags(r) for r in rows]
        counts = {status: sum(r["status"] == status for r in rows) for status in STATUSES}
        candidate_found = sum(r.get("found", False) for r in rows)
        song_candidate_found = sum(any(c["plausible"] and c["evidence"]["music_type_paths"] for c in r.get("candidates", [])) for r in rows)
        return {"sample_size": n, "processed": len(rows), "pending": n - len(rows), "status_counts": counts,
                "candidate_found": candidate_found, "candidate_found_percent": percent(candidate_found, n),
                "song_candidate_found": song_candidate_found, "song_candidate_found_percent": percent(song_candidate_found, n),
                "high_confidence_percent": percent(high, n),
                "coverage": {field: {"count": sum(f[field] for f in flags),
                                     "percent_of_sample": percent(sum(f[field] for f in flags), n),
                                     "percent_of_high_confidence": percent(sum(f[field] for f in flags), high)} for field in fields}}

    summary = measures(results, len(expected))
    summary["by_period"] = [dict(period=period, **measures([r for r in results if r["song"]["period"] == period],
                            sum(s["period"] == period for s in sample["songs"]))) for period, _, _, _ in PERIODS]
    summary["decision_reasons"] = dict(sorted(Counter(r["reason"] for r in results).items()))
    a_high = {qid for qid, r in a_index.items() if r["status"] == "high_confidence"}
    b_high = {r["song"]["song_id"] for r in results if r["status"] == "high_confidence"}
    a_genre = {qid for qid, r in a_index.items() if musicbrainz_coverage(r).get("recording_genres")}
    a_tag = {qid for qid, r in a_index.items() if musicbrainz_coverage(r).get("recording_genres_or_tags")}
    b_genre = {r["song"]["song_id"] for r in results if coverage_flags(r)["song_item_genres"]}
    summary["comparison"] = {"phase2a_high": len(a_high), "phase2a_recording_genres": len(a_genre),
        "phase2a_recording_genres_or_tags": len(a_tag), "both_high": len(a_high & b_high),
        "phase2b_only_high": len(b_high - a_high), "phase2a_only_high": len(a_high - b_high),
        "either_high": len(a_high | b_high), "either_has_genre_evidence_different_scopes": len(a_genre | b_genre),
        "either_has_genre_or_tag_evidence_different_scopes": len(a_tag | b_genre)}
    selected = [c for r in results for c in r.get("candidates", []) if c["entity_id"] in r.get("selected_entity_ids", [])]
    summary["selected_items_with_late_publication_years"] = sum(c["evidence"]["all_publication_years_after_chart"] for c in selected)
    summary["accepted_assets_with_multiple_items"] = sum(len(r.get("selected_entity_ids", [])) > 1 for r in results)
    summary["searches_with_more_results"] = sum(r.get("search_truncated", False) for r in results)
    summary["songs_with_optional_enrichment_errors"] = sum(bool((r.get("metadata") or {}).get("enrichment_errors")) for r in results)
    return summary


def audit_cache():
    statuses, actions, timestamps, keys = Counter(), Counter(), [], set()
    for path in sorted((CACHE / "requests").glob("*.json")):
        envelope = json.loads(path.read_text(encoding="utf-8"))
        keys.add(envelope["cache_key"])
        actions[envelope["params"]["action"]] += 1
        for attempt in envelope["attempts"]:
            if hashlib.sha256(attempt["body"].encode()).hexdigest() != attempt["body_sha256"]:
                raise ValueError("Cached response checksum mismatch: " + path.name)
            statuses[str(attempt["status"])] += 1
            timestamps.append(attempt["requested_at"])
    return {"unique_requests": len(keys), "attempt_status_counts": dict(statuses), "requests_by_action": dict(actions),
            "first_request_at": min(timestamps) if timestamps else None,
            "last_request_at": max(timestamps) if timestamps else None}, keys


def markdown(summary, results, a_results):
    n, high = summary["sample_size"], summary["status_counts"]["high_confidence"]
    c = summary["comparison"]
    lines = ["# Phase 2B: alternative metadata pilot", "",
        "Generated from cached Wikidata responses. Last.fm and Discogs were researched but not queried for song enrichment. "
        "See [source research](phase2b_source_research.md) and [reproduction and matching rules](../experiments/phase2b/README.md).", "",
        "## Scope and definitions", "",
        f"Exactly {n} Billboard identities, copied byte-for-byte from the Phase 2A sample; {summary['processed']} processed, {summary['pending']} pending. "
        "The same first-chart period buckets and deliberate difficult cases are retained. These balanced pilot rates are not population estimates.", "",
        "Candidate-found means an exact title with performer-name support or a hit in the joint title/artist search. "
        "It can still be an album, incomplete credit, or mixed work item. Song-candidate-found additionally requires a supported music-item type. "
        "High-confidence requires a complete performer-set match and the documented type/version checks. These are operational rules, not a measured precision estimate.", "",
        "## Overall results", "", "| Measure | Count | % of sample |", "| --- | ---: | ---: |",
        f"| Candidate found | {summary['candidate_found']} | {summary['candidate_found_percent']:.2f}% |",
        f"| Song candidate found | {summary['song_candidate_found']} | {summary['song_candidate_found_percent']:.2f}% |"]
    for status in STATUSES:
        count = summary["status_counts"][status]
        lines.append(f"| {status} | {count} | {percent(count, n):.2f}% |")
    lines += ["", "Not-found means no plausible pair in the bounded searches, not proven absence from Wikidata. "
              "An inconclusive capped search stays ambiguous. API errors are separate from negative matches.", "",
              "## Comparison on the same sample", "", "| Measure | Phase 2A: MusicBrainz | Phase 2B: Wikidata |", "| --- | ---: | ---: |",
              f"| High-confidence assets | {c['phase2a_high']}/{n} ({percent(c['phase2a_high'], n):.2f}%) | {high}/{n} ({percent(high, n):.2f}%) |",
              f"| Accepted assets with genre evidence | {c['phase2a_recording_genres']}/{n} recording genres | {summary['coverage']['song_item_genres']['count']}/{n} song/work/single/track-item genres |",
              f"| Accepted assets with genre or tag evidence | {c['phase2a_recording_genres_or_tags']}/{n} recording genres/tags | {summary['coverage']['song_item_genres']['count']}/{n} item genres; no free-form tag endpoint |", "",
              "Both provider and matcher changed: Phase 2A required a unique recording and supporting date, whereas Phase 2B links title/performer assets, "
              "permits multiple same-performer items and does not require dates. The yield difference cannot be attributed to the provider alone. "
              "Wikidata genres on work/single items and MusicBrainz recording genres also have different scopes.", "",
              f"Accepted by both: {c['both_high']}; only MusicBrainz: {c['phase2a_only_high']}; only Wikidata: {c['phase2b_only_high']}; "
              f"accepted by either: {c['either_high']}/{n}. Genre evidence at either source's stated level reaches "
              f"{c['either_has_genre_evidence_different_scopes']}/{n}; including MusicBrainz raw tags reaches "
              f"{c['either_has_genre_or_tag_evidence_different_scopes']}/{n}. These unions are audit comparisons, not merged genre assignments.", "",
              "## Historical coverage", "",
              "Percentages below use each period's full sample. Metadata counts require an accepted link.", "",
              "| First-chart period | N | Found candidates | Accepted (% of N) | Ambiguous | Not found | Error | Item genres | Dates | Albums | Duration | MB accepted |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in summary["by_period"]:
        counts, fields = row["status_counts"], row["coverage"]
        a_high = sum(r["status"] == "high_confidence" and r["song"]["period"] == row["period"] for r in a_results)
        lines.append(f"| {row['period']} | {row['sample_size']} | {row['candidate_found']} | {counts['high_confidence']} ({row['high_confidence_percent']:.2f}%) | "
                     f"{counts['ambiguous']} | {counts['not_found']} | {counts['error']} | {fields['song_item_genres']['count']} | {fields['publication_date']['count']} | "
                     f"{fields['album_context']['count']} | {fields['duration_quantity']['count']} | {a_high} |")
    lines += ["", "## Metadata coverage", "", f"Denominators: {high} accepted assets and {n} sampled assets. "
              "An asset contributes once per field even when it links to several items. Only non-deprecated value statements count toward coverage; all returned raw statements remain cached.", "",
              "| Field / scope | Count | % accepted | % sample |", "| --- | ---: | ---: | ---: |"]
    for field, row in summary["coverage"].items():
        accepted_percent = "—" if row["percent_of_high_confidence"] is None else f"{row['percent_of_high_confidence']:.2f}%"
        lines.append(f"| {field} | {row['count']} | {accepted_percent} | {row['percent_of_sample']:.2f}% |")
    lines += ["", "Wikidata supplies structured genre IDs/labels, not Last.fm-style free-form tags. "
              "Genre scope rows overlap when an asset has several item types or links; they are not additive. "
              "The generic song type does not resolve composition versus recording scope. "
              "Publication dates preserve precision, qualifiers and calendar; they are not automatically original release dates. "
              "Durations retain quantities and units. Album coverage requires an explicit parent relation and album type. "
              "Artist/album genres are separate context and never counted as song-item genres. A statement reference may merely be an import from a wiki; it is not independent validation.", "",
              "## Examples", ""]
    for status in STATUSES:
        pool = [r for r in results if r["status"] == status]
        # Show different periods when possible, without hand-promoting a match.
        examples = []
        for period, _, _, _ in PERIODS:
            example = next((r for r in pool if r["song"]["period"] == period), None)
            if example:
                examples.append(example)
        lines += [f"### {status}", "", "| Billboard identity | Evidence |", "| --- | --- |"]
        for r in examples[:5]:
            selected = [c for c in r.get("candidates", []) if c["entity_id"] in r.get("selected_entity_ids", [])]
            best = selected or [c for c in r.get("candidates", []) if c["plausible"]][:1]
            evidence = r["reason"]
            if best:
                evidence += "; " + "; ".join(f"[{v['entity_id']}](https://www.wikidata.org/wiki/{v['entity_id']}) / {v['candidate_artist']}" for v in best)
            genre_labels = [(v.get("genre_label") or v.get("genre_id")) for v in (r.get("metadata") or {}).get("raw_genres", [])
                            if v.get("genre_label") or v.get("genre_id")]
            if genre_labels:
                evidence += "; raw genres: " + ", ".join(genre_labels)
            text = f"{r['song']['title']} / {r['song']['artist']}".replace("|", "\\|")
            lines.append(f"| {text} | {evidence.replace('|', '/')} |")
        if not examples:
            lines.append("| None in this run | — |")
        lines.append("")
    lines += ["See [inspected examples and review notes](phase2b_review_notes.md) for additional cover, alias, featured-credit and entity-scope cases.", "",
        "## Limitations and next step", "",
        "Wikidata can provide auditable genre and identity statements for some title/performer assets, but is not a complete music catalog. "
        "Albums sharing a song title, compositions with several cover performers, missing featured credits, missing item types, sparse older/new entries, "
        "and bounded English-language retrieval can all reduce yield. An absent genre is not evidence of a genre-free song.", "",
        "Last.fm remains the most promising direct title/artist tag interface from documentation; its coverage is untested here. "
        "Academic access, a project key, snapshot retention and sharing conditions should be resolved before that comparison. "
        "Discogs may add release context, but release styles should not be silently transferred to tracks and its API retention terms need clarification.", "",
        "Do not scale to all 32,723 assets yet. Review accepted and ambiguous links against independent evidence, evaluate a fresh holdout, "
        "and test Last.fm on this same sample if access is obtained. MusicBrainz remains useful for identifiers, dates, release context and duration, "
        "especially with a separately evaluated asset-level association rule. Keep provider disagreements and semantic levels explicit. "
        "No taxonomy or final study population is chosen here.", "",
        "## Audit", "",
        f"Decision reasons: `{json.dumps(summary['decision_reasons'], sort_keys=True)}`.", "",
        f"Capped searches: {summary['searches_with_more_results']}; accepted assets with multiple items: {summary['accepted_assets_with_multiple_items']}; "
        f"selected items whose reported publication years are all later than chart year + 1: {summary['selected_items_with_late_publication_years']}; "
        f"assets with optional metadata lookup errors: {summary['songs_with_optional_enrichment_errors']}.", "",
        f"Cached unique requests: {summary['cache']['unique_requests']}; attempts by HTTP status: `{json.dumps(summary['cache']['attempt_status_counts'])}`. "
        f"Retrieval window (UTC): {summary['cache']['first_request_at']} through {summary['cache']['last_request_at']}.", "",
        f"Sample SHA-256: `{SAMPLE_SHA256}`. Matcher: `{MATCHER_VERSION}`. Full source/code hashes and runtime versions are in the local summary JSON. "
        "Original responses, revision IDs, claims, references and candidate decisions are retained under the documented ignored cache/experiment paths. "
        "Phase 1 and the Phase 2A sample are checked against their frozen hashes. No lyrics, content classifier, taxonomy collapse or statistical analysis is included.", ""]
    return "\n".join(lines)


def generate_report():
    sample = load_sample()
    verify_foundation(sample)
    if file_hash(OUTPUT / "sample.json") != SAMPLE_SHA256:
        raise ValueError("Phase 2B sample copy differs from Phase 2A")
    results = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((OUTPUT / "results").glob("*.json"))]
    a_results = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "data/experiments/phase2a/results").glob("*.json"))]
    summary = summarize(sample, results, a_results)
    summary["cache"], keys = audit_cache()
    for row in results:
        if set(row["cache_keys"]) - keys:
            raise ValueError("Result references a missing cache entry")
    summary["provenance"] = {"sample_sha256": SAMPLE_SHA256, "canonical_database_sha256": sample["canonical_database_sha256"],
        "billboard_source_sha256": sample["billboard_source_sha256"], "matcher_version": MATCHER_VERSION,
        "python_version": platform.python_version(), "unicode_version": unicodedata.unidata_version,
        "code_sha256": {name: file_hash(ROOT / "src" / name) for name in
                        ("phase2b.py", "phase2b_report.py", "wikidata.py", "wikidata_match.py", "metadata_match.py", "musicbrainz.py", "phase2a.py", "enrichment_report.py")}}
    write_json(OUTPUT / "summary.json", summary)
    a_index = {r["song"]["song_id"]: r for r in a_results}
    rows = []
    for result in results:
        song = result["song"]
        metadata = result.get("metadata") or {}
        entities = metadata.get("entities", [])
        rows.append(dict(song_id=song["song_id"], title=song["title"], artist=song["artist"], period=song["period"],
            provider="Wikidata", status=result["status"], found=result["found"], reason=result["reason"], match_score=result["match_score"],
            external_titles=json.dumps([label(e) for e in entities], ensure_ascii=False),
            artist_ids=json.dumps(sorted({qid for e in entities for qid in item_ids(e, "P175")})),
            musicbrainz_recording_ids=json.dumps([v for e in entities for v in values(e, "P4404")]),
            entity_ids=json.dumps(result.get("selected_entity_ids", [])), raw_genres=json.dumps(metadata.get("raw_genres", []), ensure_ascii=False),
            publication_dates=json.dumps([v for e in entities for v in claims(e, "P577", True)], ensure_ascii=False),
            duration_quantities=json.dumps([v for e in entities for v in claims(e, "P2047", True)], ensure_ascii=False),
            album_ids=json.dumps(metadata.get("album_ids", [])),
            phase2a_status=a_index[song["song_id"]]["status"], cache_keys=json.dumps(result["cache_keys"])))
    if rows:
        path = OUTPUT / "matches.csv"
        temporary = path.with_suffix(".csv.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(path)
    report = ROOT / "archive/intermediate_reports/phase2b_metadata_feasibility.md"
    temporary = report.with_suffix(".md.tmp")
    temporary.write_text(markdown(summary, results, a_results), encoding="utf-8")
    temporary.replace(report)
    print(json.dumps({key: summary[key] for key in ("sample_size", "processed", "pending", "status_counts", "high_confidence_percent", "comparison")}, indent=2))
    print("Report:", report)
