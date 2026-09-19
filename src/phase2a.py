#!/usr/bin/env python3
"""Isolated, restartable 200-song MusicBrainz feasibility experiment."""

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from contextlib import closing
from pathlib import Path

from billboard import ROOT
from metadata_match import MATCHER_VERSION, artist_credit, decide, evaluate_candidate, search_queries
from musicbrainz import APIError, MusicBrainzClient, utc_now, write_json

SEED = "cmpt491-phase2a-v1"
PERIODS = (("1958–1969", 1958, 1969, 29), ("1970s", 1970, 1979, 29),
           ("1980s", 1980, 1989, 29), ("1990s", 1990, 1999, 29),
           ("2000s", 2000, 2009, 28), ("2010s", 2010, 2019, 28), ("2020–2026", 2020, 2026, 28))
EXPERIMENT = ROOT / "data/experiments/phase2a"
CACHE = ROOT / "data/cache/musicbrainz"


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def population(db_path):
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute("""
            SELECT s.*, min(c.chart_date) AS first_chart_date, max(c.chart_date) AS last_chart_date,
                   count(*) AS chart_observation_count, min(c.rank) AS best_chart_rank
            FROM songs s JOIN chart_observations c USING (song_id) GROUP BY s.song_id ORDER BY s.song_id
        """)]
        source_hash = db.execute("SELECT value FROM build_metadata WHERE key='source_sha256'").fetchone()[0]
    title_counts = Counter(row["normalized_title"] for row in rows)
    for row in rows:
        flags = []
        if re.search(r"\b(?:featuring|feat\.?|ft\.?)\s", row["artist"], re.I):
            flags.append("featured_artists")
        if sum(unicodedata.category(c).startswith("P") for c in row["title"] + row["artist"]) >= 3:
            flags.append("punctuation_heavy")
        if title_counts[row["normalized_title"]] >= 3:
            flags.append("common_title")
        if len(row["artist"]) >= 45 or re.search(r"\b(?:with|orchestra|presents)\b| & | / | x |,", row["artist"], re.I):
            flags.append("unusual_credit")
        if int(row["first_chart_date"][:4]) <= 1969:
            flags.append("early_chart_era")
        row["difficulty_flags"] = flags
    return rows, source_hash


def select_sample(rows):
    selected = []
    for period, begin, end, quota in PERIODS:
        pool = sorted((dict(row) for row in rows if begin <= int(row["first_chart_date"][:4]) <= end),
                      key=lambda row: hashlib.sha256((SEED + row["song_id"]).encode()).hexdigest())
        chosen = {}

        def take(candidates, count, reason):
            for row in candidates:
                if count == 0:
                    break
                if row["song_id"] not in chosen:
                    chosen[row["song_id"]] = dict(row, period=period, selection_reason=reason)
                    count -= 1

        for year in range(begin, end + 1):
            take((row for row in pool if int(row["first_chart_date"][:4]) == year), 1, "year_coverage")
        for flag in ("featured_artists", "punctuation_heavy", "common_title", "unusual_credit"):
            take((row for row in pool if flag in row["difficulty_flags"]), 2, "challenge:" + flag)
        take(pool, quota - len(chosen), "hash_fill")
        if len(chosen) != quota:
            raise ValueError("Insufficient identities for sample period " + period)
        selected.extend(sorted(chosen.values(), key=lambda row: row["song_id"]))
    return selected


def prepare_sample(db_path, output_dir):
    rows, source_hash = population(db_path)
    result = {"sample_version": SEED, "canonical_database_sha256": file_hash(db_path),
              "billboard_source_sha256": source_hash, "population_size": len(rows),
              "population_by_period": {label: sum(start <= int(row["first_chart_date"][:4]) <= end for row in rows) for label, start, end, _ in PERIODS},
              "songs": select_sample(rows)}
    path = output_dir / "sample.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != result:
        raise ValueError("Existing sample differs from source/rules; use another experiment directory, do not overwrite a study")
    if not path.exists():
        write_json(path, result)
    return result


def recording_metadata(song, selected, client, cache_refs):
    recording, key = client.get("recording/" + selected["recording_id"], inc="artist-credits+releases+release-groups+isrcs+genres+tags+ratings+work-rels")
    cache_refs.append({"kind": "recording", "entity_id": selected["recording_id"], "key": key})
    confirmation = dict(recording, score=selected["evidence"]["provider_search_score"])
    confirmed = evaluate_candidate(song, confirmation)
    metadata = {"recording": recording, "artists": [], "release_groups": [], "enrichment_errors": [],
                "lookup_confirms_match": confirmed["eligible"]}
    artists = {part["artist"]["id"] for part in recording.get("artist-credit", []) if isinstance(part, dict) and part.get("artist", {}).get("id")}
    for identifier in sorted(artists):
        try:
            artist, key = client.get("artist/" + identifier, inc="genres+tags+aliases")
            cache_refs.append({"kind": "artist", "entity_id": identifier, "key": key})
            metadata["artists"].append(artist)
        except APIError as exc:
            metadata["enrichment_errors"].append({"kind": "artist", "entity_id": identifier, "error": str(exc), "cache_key": exc.cache_key})
    # Bounded contextual lookup: up to three earliest dated, non-compilation groups.
    groups = {}
    for release in recording.get("releases", []) + selected["releases"]:
        group = release.get("release-group", {})
        date = release.get("date", "")
        if group.get("id") and date and date[:4].isdigit() and int(date[:4]) <= int(song["first_chart_date"][:4]) + 1:
            if release.get("status") not in (None, "Official") or "Compilation" in group.get("secondary-types", []):
                continue
            groups[group["id"]] = min(date, groups.get(group["id"], date))
    requested_groups = sorted(groups, key=lambda identifier: (groups[identifier], identifier))[:3]
    metadata["release_group_lookup_limit"] = 3
    metadata["eligible_release_groups_in_returned_releases"] = len(groups)
    for identifier in requested_groups:
        try:
            group, key = client.get("release-group/" + identifier, inc="genres+tags+artist-credits")
            cache_refs.append({"kind": "release-group", "entity_id": identifier, "key": key})
            metadata["release_groups"].append(group)
        except APIError as exc:
            metadata["enrichment_errors"].append({"kind": "release-group", "entity_id": identifier, "error": str(exc), "cache_key": exc.cache_key})
    return metadata


def enrich_song(song, client):
    result = {"song": song, "provider": "MusicBrainz", "matcher_version": MATCHER_VERSION,
              "processed_at": utc_now(), "cache_refs": [], "searches": [], "metadata": None}
    candidates = {}
    truncated = False
    try:
        for query in search_queries(song):
            response, key = client.get("recording", query=query, limit=100, offset=0)
            if not isinstance(response.get("recordings"), list) or type(response.get("count")) is not int:
                raise APIError("Unexpected MusicBrainz search schema", key)
            result["cache_refs"].append({"kind": "search", "key": key})
            result["searches"].append({"query": query, "count": response["count"], "returned": len(response["recordings"]), "cache_key": key})
            truncated = truncated or response["count"] > len(response["recordings"])
            for candidate in response["recordings"]:
                identifier = candidate.get("id")
                if not identifier:
                    raise APIError("Search candidate missing recording ID", key)
                # Preserve each raw search in cache; score uses the highest provider score for a repeated MBID.
                if identifier not in candidates or int(candidate.get("score", 0)) > int(candidates[identifier].get("score", 0)):
                    candidates[identifier] = candidate
            initial = decide(song, list(candidates.values()), truncated)
            if any(row["evidence"]["title_exact"] and row["evidence"]["artist_credit_exact"] for row in initial["candidates"]):
                break
        result.update(decide(song, list(candidates.values()), truncated))
        if result["status"] == "high_confidence":
            selected = next(row for row in result["candidates"] if row["recording_id"] == result["selected_recording_id"])
            result["metadata"] = recording_metadata(song, selected, client, result["cache_refs"])
            if not result["metadata"]["lookup_confirms_match"]:
                result.update(status="ambiguous", reason="recording_lookup_changed_matching_evidence", selected_recording_id=None)
    except APIError as exc:
        result.update(status="error", reason="api_or_cache_error", error=str(exc), error_cache_key=exc.cache_key,
                      selected_recording_id=None, match_score=None)
        result.setdefault("candidates", decide(song, list(candidates.values()), truncated)["candidates"])
    return result


def run(db_path, output_dir, cache_dir, offline=False, retry_errors=False, limit=None, replay=False):
    sample = prepare_sample(db_path, output_dir)
    songs = sample["songs"][:limit] if limit else sample["songs"]
    new_results, consecutive_errors = 0, 0
    with MusicBrainzClient(cache_dir, offline=offline, retry_errors=retry_errors) as client:
        for index, song in enumerate(songs, 1):
            path = output_dir / "results" / (song["song_id"] + ".json")
            if path.exists() and not replay:
                existing = json.loads(path.read_text(encoding="utf-8"))
                if existing["song"] != song or existing["matcher_version"] != MATCHER_VERSION:
                    raise ValueError("Existing result uses different sample/matcher; replay explicitly from cache")
                if not retry_errors or (existing["status"] != "error" and not (existing.get("metadata") or {}).get("enrichment_errors")):
                    continue
            result = enrich_song(song, client)
            write_json(path, result)
            new_results += 1
            print("{}/{} {} | {} / {} | requests={} cache_hits={}".format(index, len(songs), result["status"], song["title"], song["artist"], client.network_requests, client.cache_hits), flush=True)
            consecutive_errors = consecutive_errors + 1 if result["status"] == "error" else 0
            if consecutive_errors >= 3 and not offline:
                raise APIError("Three consecutive song errors; stopped to avoid repeatedly calling a failing service. Cached progress is restartable.")
        print("Completed {} new/replayed results; network requests: {}; cache hits: {}".format(new_results, client.network_requests, client.cache_hits), flush=True)
    if file_hash(db_path) != sample["canonical_database_sha256"]:
        raise ValueError("Canonical database changed during the experiment")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("sample", "run", "report"))
    parser.add_argument("--database", type=Path, default=ROOT / "data/processed/music.db")
    parser.add_argument("--output-dir", type=Path, default=EXPERIMENT)
    parser.add_argument("--cache-dir", type=Path, default=CACHE)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--replay", action="store_true", help="Recompute decisions from cached responses")
    parser.add_argument("--limit", type=int, help="Process only the first N of the fixed 200-song sample")
    args = parser.parse_args(argv)
    try:
        for path in (args.output_dir.resolve(), args.cache_dir.resolve()):
            for protected in ((ROOT / "data/raw").resolve(), (ROOT / "data/processed").resolve()):
                if path == protected or protected in path.parents:
                    raise ValueError("Experiment/cache may not write into raw or canonical processed data")
        if args.limit is not None and not 1 <= args.limit <= 200:
            raise ValueError("--limit must be between 1 and 200")
        if args.command == "sample":
            sample = prepare_sample(args.database, args.output_dir)
            print("Sampled {} identities: {}".format(len(sample["songs"]), dict(Counter(row["period"] for row in sample["songs"]))))
        elif args.command == "run":
            run(args.database, args.output_dir, args.cache_dir, args.offline, args.retry_errors, args.limit, args.replay)
        else:
            from enrichment_report import generate_report
            generate_report(args.output_dir, args.cache_dir, ROOT / "reports/phase2a_metadata_feasibility.md")
    except (APIError, OSError, ValueError, sqlite3.Error) as exc:
        print("Phase 2A failed: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
