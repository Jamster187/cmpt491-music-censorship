"""Deterministic Phase 2A-R summary and review evidence."""

from collections import Counter
import hashlib
import json


def coverage(result):
    records = [m for m in result["metadata_evidence"] if m["level"] == "recording"]
    releases = [r for m in records for r in m["raw"].get("releases", [])]
    flags = {
        "release_date": any(d["category"] != "invalid" for c in result["candidates"] if c["recording_id"] in result["supporting_recording_ids"] for d in c["dates"]),
        "duration": any(m["raw"].get("length") for m in records),
        "release": bool(releases),
        "release_group": bool(result["linked_release_group_ids"]),
        "album_release": any(r.get("release-group", {}).get("primary-type") == "Album" for r in releases),
        "recording_ids": bool(result["supporting_recording_ids"]),
        "artist_ids": bool(result["supporting_artist_ids"]),
        "isrc": any(m["raw"].get("isrcs") for m in records),
        "work_relations": any(r.get("target-type") == "work" for m in records for r in m["raw"].get("relations", [])),
    }
    for level, name in (("recording", "recording"), ("release-group", "release_group"), ("artist", "artist")):
        objects = [m for m in result["metadata_evidence"] if m["level"] == level]
        # Embedded release-group objects may contain metadata even without lookup.
        raw = [m["raw"] for m in objects]
        if level == "release-group":
            raw += [r["release-group"] for r in releases if r.get("release-group")]
        if level == "artist":
            raw += [p["artist"] for m in records for p in m["raw"].get("artist-credit", []) if isinstance(p, dict) and p.get("artist")]
        flags[name + "_genres"] = any(o.get("genres") for o in raw)
        flags[name + "_tags"] = any(o.get("tags") for o in raw)
        flags[name + "_lookup_available"] = any(m["response_kind"] == "lookup" for m in objects)
    return flags


def aggregate(rows):
    accepted = [r for r in rows if r["asset_match_status"] == "high_confidence"]
    keys = coverage(rows[0]) if rows else {}
    measured = [coverage(r) for r in accepted]
    return {k: {"count": sum(r[k] for r in measured),
                "percent_of_accepted": round(100 * sum(r[k] for r in measured) / len(accepted), 2) if accepted else 0,
                "percent_of_sample": round(100 * sum(r[k] for r in measured) / len(rows), 2) if rows else 0}
            for k in keys}


def review_sample(rows):
    new = [r for r in rows if r["newly_accepted"]]
    # Review every newly accepted asset: stronger than a 40-case subsample and
    # removes any temptation to select attractive examples after seeing results.
    return sorted(new, key=lambda r: hashlib.sha256(("phase2ar-review-v1" + r["song"]["song_id"]).encode()).hexdigest())


def escape(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def report(rows, provenance, root, out):
    from phase2ar import write_json
    accepted = [r for r in rows if r["asset_match_status"] == "high_confidence"]
    new = [r for r in rows if r["newly_accepted"]]
    old_ids = {r["song"]["song_id"] for r in rows if r["phase2a_status"] == "high_confidence"}
    ids = {r["song"]["song_id"] for r in accepted}
    wd = json.loads((root / "data/experiments/phase2b/summary.json").read_text())
    wd_rows = [json.loads(p.read_text()) for p in sorted((root / "data/experiments/phase2b/results").glob("*.json"))]
    wd_ids = {r["song"]["song_id"] for r in wd_rows if r["status"] == "high_confidence"}
    if len(wd_rows) != 200 or {r["song"]["song_id"] for r in wd_rows} != {r["song"]["song_id"] for r in rows}:
        raise ValueError("Phase 2B comparison must use exactly the same 200 assets")
    provenance["phase2b_summary_sha256"] = hashlib.sha256((root / "data/experiments/phase2b/summary.json").read_bytes()).hexdigest()
    provenance["phase2b_results_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / "data/experiments/phase2b/results").glob("*.json"))}
    summary = {
        "sample_size": len(rows), "status_counts": dict(Counter(r["asset_match_status"] for r in rows)),
        "high_confidence_percent": 100 * len(accepted) / len(rows), "phase2a_high_confidence": len(old_ids),
        "newly_accepted": len(new), "previously_accepted_now_ambiguous": sorted(old_ids - ids),
        "new_from_multiple_recordings": sum(r["phase2a_reason"] in ("multiple_eligible_recordings", "competing_plausible_recordings") for r in new),
        "new_by_original_reason": dict(Counter(r["phase2a_reason"] for r in new)),
        "decision_reasons": dict(Counter(r["reason"] for r in rows)),
        "recording_status": dict(Counter(r["canonical_recording_status"] for r in accepted)),
        "accepted_review_flags": dict(Counter(f for r in accepted for f in r["review_flags"])),
        "coverage": aggregate(rows), "provenance": provenance,
        "temporal": {
            "compatible_but_no_anchor": sum(r["reason"] == "compatible_identity_but_no_temporal_anchor" for r in rows),
            "accepted_with_later_or_undated_support": sum("later_or_undated_recordings_supported_by_asset_anchor" in r["review_flags"] for r in accepted),
            "accepted_only_following_year_anchor": sum("anchor_only_in_following_year" in r["review_flags"] for r in accepted),
            "impossible_artist_chronology_candidates": sum(bool(c["impossible_artist_chronology"]) for r in rows for c in r["candidates"]),
            "invalid_date_evidence": sum(d["category"] == "invalid" for r in rows for c in r["candidates"] for d in c["dates"]),
        },
        "wikidata": {"high_confidence": len(wd_ids), "genres": wd["coverage"]["song_item_genres"]["count"],
                     "both": len(ids & wd_ids), "musicbrainz_only": len(ids - wd_ids), "wikidata_only": len(wd_ids - ids),
                     "union": len(ids | wd_ids)},
    }
    periods = list(dict.fromkeys(r["song"]["period"] for r in rows))
    summary["by_period"] = []
    for period in periods:
        subset = [r for r in rows if r["song"]["period"] == period]
        summary["by_period"].append({"period": period, "sample_size": len(subset),
            "phase2a_high": sum(r["phase2a_status"] == "high_confidence" for r in subset),
            "status_counts": dict(Counter(r["asset_match_status"] for r in subset)),
            "high_confidence_percent": round(100 * sum(r["asset_match_status"] == "high_confidence" for r in subset) / len(subset), 2),
            "wikidata_high": sum(r["song"]["song_id"] in wd_ids for r in subset), "coverage": aggregate(subset)})
    review = review_sample(rows)
    summary["review_song_ids"] = [r["song"]["song_id"] for r in review]
    write_json(out / "summary.json", summary)
    write_json(out / "review_sample.json", review)
    report_lines = ["# Phase 2A-R: offline MusicBrainz asset matching", "",
        "Generated from the frozen Phase 2A cache. No new requests, manual promotions, or changes to the canonical database or previous archive/experiments.", "",
        f"The same {len(rows)} assets yield **{len(accepted)}/{len(rows)} high-confidence links ({summary['high_confidence_percent']:.1f}%)**, compared with Phase 2A's 45/200 (22.5%).",
        f"Newly accepted: {len(new)}; still ambiguous: {summary['status_counts'].get('ambiguous', 0)}; no cached candidates: {summary['status_counts'].get('not_found', 0)}. Previously accepted but now excluded: {len(old_ids - ids)}. Unresolved input/API errors: 0; network requests: 0.",
        "No cached candidates means the original bounded searches returned nothing; it does not establish absence from MusicBrainz.", "",
        f"Of the 104 original multiple-recording ambiguity cases, {summary['new_from_multiple_recordings']} are newly accepted. Original reasons for all new links: `{json.dumps(summary['new_by_original_reason'], sort_keys=True)}`.",
        f"Accepted recording status: `{json.dumps(summary['recording_status'], sort_keys=True)}`. No recording is arbitrarily selected.", "",
        "## Historical coverage", "", "| First chart period | N | Phase 2A high | Phase 2A-R high (%) | Ambiguous | No candidates | Wikidata high | Recording genres / tags |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for p in summary["by_period"]:
        s, c = p["status_counts"], p["coverage"]
        report_lines.append(f"| {p['period']} | {p['sample_size']} | {p['phase2a_high']} | {s.get('high_confidence', 0)} ({p['high_confidence_percent']}%) | {s.get('ambiguous', 0)} | {s.get('not_found', 0)} | {p['wikidata_high']} | {c['recording_genres']['count']} / {c['recording_tags']['count']} |")
    report_lines += ["", "## Available metadata", "", "Coverage counts assets with at least one supporting cached value; multiple conflicting values remain separate. These are not canonical recording attributes or verified original-release dates. Album includes compilations.", "",
        "| Field / semantic level | Assets | % accepted | % sample |", "|---|---:|---:|---:|"]
    for field, value in summary["coverage"].items():
        report_lines.append(f"| {field} | {value['count']} | {value['percent_of_accepted']} | {value['percent_of_sample']} |")
    report_lines += ["", "Genres/tags retain their original objects, counts, entity IDs, cache references, timestamps, and recording/release-group/artist scope. Tags are not necessarily genres. No taxonomy or inheritance is applied.",
        "Detailed lookups were originally requested only after Phase 2A acceptance. New links primarily have search metadata. Lookup availability above is at least one lookup per asset, not complete coverage of all its linked entities. Missing genre values on unfetched entities are **unknown**, not proven absent. Thus this replay measures recoverable cached coverage, not the ceiling after targeted lookups.", "",
        "## Temporal evidence", "", f"`{json.dumps(summary['temporal'], sort_keys=True)}`", "",
        "At least one compatible recording must have a returned release date no later than first-chart year + 1. Partial dates are intervals. The one-year allowance retains Phase 2A's heuristic and is flagged separately when it is the only support; it does not infer an original release date. Later/undated recordings can support the same artist-ID group once that asset has an anchor. Late dates alone are not called impossible, but they cannot establish temporal support in this precision-first replay.",
        "An artist's cached birth/formation after first-chart year + 1 is negative evidence. Unexpected live/remix/re-recorded/demo/karaoke/instrumental/acoustic/video/DJ-mix markers cannot supply support. Unrecognized disambiguation text is also excluded; only an explicit list of edition descriptors is allowed. No new biography lookup is made. Absence of impossible evidence is not proof of chronology.", "",
        "## Matching and review", "",
        "The exact rule and normalization are documented in [the experiment instructions](../experiments/phase2ar/README.md). Full normalized title and artist credit must agree, with one consistent artist-ID set and a release anchor. Search relevance is recorded, not treated as identity probability. Multiple recordings do not veto the asset. Search truncation remains a visible risk flag rather than proof that the observed asset is ambiguous.",
        f"All {len(review)} newly accepted assets are included in a deterministic [review packet](phase2ar_review.md); see [review findings](phase2ar_review_notes.md) for the qualitative audit. Acceptance is algorithmic, never manually promoted. Counts are algorithmic coverage, not measured precision; there is no independent labelled gold standard.",
        f"Accepted review flags: `{json.dumps(summary['accepted_review_flags'], sort_keys=True)}`.", "",
        "## Comparison and recommendation", "",
        f"Unchanged Wikidata Phase 2B accepted {len(wd_ids)}/200 (49.5%) and exposed genre statements for {summary['wikidata']['genres']}/200 (42%). MusicBrainz asset matching and Wikidata overlap on {len(ids & wd_ids)} assets; their provisional union is {len(ids | wd_ids)}/200 ({len(ids | wd_ids)/2:.1f}%). This is a union of algorithmically accepted assets, not a validated merged crosswalk.",
        "Wikidata genres span recordings, singles, compositions, and generic song items. Its 42% cannot be compared as if all were recording genres. MusicBrainz now offers substantially more usable identity/release evidence, while Wikidata can contribute complementary song-level context. Neither source justifies silently borrowing artist or compilation genres.",
        "Do not scale yet. Independently review the new links, resolve flagged chronology/version cases, then test bounded detailed MusicBrainz lookups for the recovered assets and compare raw genre coverage at explicit semantic levels. Keep recordings/editions unresolved for identity enrichment; choose a defensible version policy before lyrics or version-sensitive measurements.", "",
        "## Reproduction and limits", "", "Run `python3 src/phase2ar.py` and `python3 -m unittest discover -s tests -v` from the repository root. Full commands and cache prerequisites are in the experiment instructions. The ignored summary stores input, cache, and code fingerprints. Outputs contain no run timestamp, so the frozen-input replay is byte deterministic.",
        "This deliberately balanced 200-asset stress sample is not a population estimate. Search limits and Phase 2A query design still constrain recall. Genre lookups are acceptance-biased; aggregating editions can mix durations, dates, clean/explicit variants, and compilation context. Precise numerical gains do not establish zero false positives.", ""]
    (root / "archive/intermediate_reports/phase2ar_metadata_feasibility.md").write_text("\n".join(report_lines), encoding="utf-8")
    lines = ["# Phase 2A-R newly accepted asset review", "", f"All {len(review)} newly accepted assets, ordered by SHA-256 of `phase2ar-review-v1` plus song_id. No cherry-picking or manual promotions. Full raw variants, all IDs, and cache provenance are in `data/experiments/phase2ar/results/<song_id>.json`.", ""]
    for i, r in enumerate(review, 1):
        song = r["song"]
        support = [c for c in r["candidates"] if c["recording_id"] in r["supporting_recording_ids"]]
        lines += [f"## {i}. {escape(song['title'])} — {escape(song['artist'])}", "",
            f"Billboard first chart: **{song['first_chart_date']}**; period: {song['period']}; song_id: `{song['song_id']}`.",
            f"Phase 2A: `{r['phase2a_reason']}`. Phase 2A-R: `{r['reason']}`; recording status: `{r['canonical_recording_status']}`.",
            f"Review flags: {', '.join(r['review_flags']) or 'none'}.", "",
            "| Recording ID | Candidate title | Complete artist credit | Disambiguation | Date evidence (value: category) |",
            "|---|---|---|---|---|"]
        for c in support:
            dates = sorted({d["value"] + ": " + d["category"] for d in c["dates"]})
            lines.append("| " + " | ".join(escape(v) for v in (c["recording_id"], c["title"], c["artist_credit"], c["disambiguation"], "; ".join(dates) or "none")) + " |")
        lines += ["", "Release examples (dates are release manifestations, not assigned original dates):", ""]
        release_examples = sorted({(rel.get("date", "unknown"), rel.get("title", ""), rel.get("id", "")) for m in r["metadata_evidence"] if m["level"] == "recording" for rel in m["raw"].get("releases", [])})
        for date, title, rid in release_examples[:6]:
            lines.append(f"- {escape(date)} — {escape(title)} (`{rid}`)")
        if len(release_examples) > 6:
            lines.append(f"- {len(release_examples)-6} further returned release variants retained in the result JSON.")
        lines += [""]
    (root / "archive/intermediate_reports/phase2ar_review.md").write_text("\n".join(lines), encoding="utf-8")
    return summary
