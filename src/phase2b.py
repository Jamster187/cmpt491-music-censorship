#!/usr/bin/env python3
"""Isolated Wikidata pilot on exactly the accepted Phase 2A sample."""

import argparse
import json
import sys
from pathlib import Path

from billboard import ROOT
from metadata_match import comparison_key
from musicbrainz import APIError, utc_now, write_json
from phase2a import file_hash
from wikidata import WikidataClient
from wikidata_match import MATCHER_VERSION, MUSIC_TYPES, claims, decide, item_ids, label

SAMPLE = ROOT / "data/experiments/phase2a/sample.json"
SAMPLE_SHA256 = "fb9c0e171b75666c1ef893df00659bc55a49fe0ddc14babfa537c94ca6d3ff69"
OUTPUT = ROOT / "data/experiments/phase2b"
CACHE = ROOT / "data/cache/wikidata"
DATABASE = ROOT / "data/processed/music.db"
RAW = ROOT / "data/raw/billboard-hot-100.json"


def load_sample(path=SAMPLE):
    if file_hash(path) != SAMPLE_SHA256:
        raise ValueError("Phase 2A sample differs from the accepted 200-song snapshot")
    sample = json.loads(Path(path).read_text(encoding="utf-8"))
    if len(sample["songs"]) != 200 or len({s["song_id"] for s in sample["songs"]}) != 200:
        raise ValueError("Exactly 200 unique Phase 2A identities are required")
    return sample


def verify_foundation(sample):
    for path, expected in ((DATABASE, sample["canonical_database_sha256"]), (RAW, sample["billboard_source_sha256"]), (SAMPLE, SAMPLE_SHA256)):
        if file_hash(path) != expected:
            raise ValueError("Phase 1 or the frozen Phase 2A sample changed: " + str(path))


def guard_outputs():
    protected = [ROOT / p for p in ("data/raw", "data/processed", "data/experiments/phase2a", "data/cache/musicbrainz")]
    for output in (OUTPUT, CACHE):
        for path in [output] + list(output.rglob("*")):
            if path.is_symlink():
                raise ValueError("Experiment outputs may not contain symlinks: " + str(path))
        for target in protected:
            if output.resolve() == target.resolve() or target.resolve() in output.resolve().parents:
                raise ValueError("Experiment output overlaps protected data")


def search_candidates(song, client):
    # Search the pair and the title; the latter helps unusual full-credit strings.
    quote = lambda value: '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    query = quote(song["title"]) + " " + quote(song["artist"])
    pair, pair_key = client.get(action="query", list="search", srsearch=query,
                                srnamespace=0, srlimit=20, srprop="", srinfo="totalhits")
    title, title_key = client.get(action="wbsearchentities", search=song["title"],
                                  language="en", uselang="en", type="item", limit=50)
    if "query" not in pair or "search" not in title:
        raise APIError("Unexpected Wikidata search schema")
    pair_ids = {row["title"] for row in pair["query"]["search"]}
    # Fetch only exact label/alias title hits from the broader title search.
    title_ids = {row["id"] for row in title["search"]
                 if any(comparison_key(value) == comparison_key(song["title"])
                        for value in (row.get("label", ""), row.get("match", {}).get("text", "")))}
    ids = sorted(pair_ids | title_ids)
    entities, keys = client.entities(ids)
    truncated = "search-continue" in title or "continue" in pair
    searches = [{"kind": "title_artist", "query": query, "cache_key": pair_key,
                 "total_hits": pair["query"].get("searchinfo", {}).get("totalhits"), "returned": len(pair_ids)},
                {"kind": "title", "query": song["title"], "cache_key": title_key,
                 "returned": len(title["search"]), "exact_title_hits": len(title_ids)}]
    return entities, pair_ids, truncated, searches, [pair_key, title_key] + keys


def context_for_candidates(entities, client):
    ids = {qid for entity in entities.values() for prop in ("P175", "P31") for qid in item_ids(entity, prop)}
    context, keys = client.entities(ids)
    frontier = {qid for entity in entities.values() if item_ids(entity, "P175") for qid in item_ids(entity, "P31")}
    for _ in range(4):
        parents = {qid for child in frontier - MUSIC_TYPES for qid in item_ids(context.get(child, {}), "P279")}
        extra, extra_keys = client.entities(parents - set(context))
        context.update(extra)
        keys.extend(extra_keys)
        frontier = parents
    return context, keys


def metadata(selected, context, client):
    # Keep complete statements and raw entity snapshots, including deprecated claims.
    artist_ids = {qid for entity in selected.values() for qid in item_ids(entity, "P175")}
    parent_ids = {qid for entity in selected.values() for qid in item_ids(entity, "P361")}
    ids = {qid for entity in selected.values() for prop in ("P136", "P361", "P407", "P264", "P86", "P162", "P2047")
           for qid in item_ids(entity, prop)}
    extra, keys = client.entities(ids)
    context = dict(context, **extra)
    parent_types = {qid for parent in parent_ids for qid in item_ids(context.get(parent, {}), "P31")}
    extra, more_keys = client.entities(parent_types)
    context.update(extra)
    keys.extend(more_keys)
    genre_rows = []
    for qid, entity in selected.items():
        for statement in claims(entity, "P136", include_deprecated=True):
            value_id = statement.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
            raw_labels = context.get(value_id, {}).get("labels", {})
            genre_label = next((raw_labels[lang]["value"] for lang in ("en", "mul") if lang in raw_labels), None)
            genre_rows.append({"provider": "Wikidata", "entity_id": qid, "entity_revision": entity.get("lastrevid"),
                               "semantic_level": "song_work_single_or_track_item", "entity_types": item_ids(entity, "P31"),
                               "genre_id": value_id, "genre_label": genre_label,
                               "raw_statement": statement})
    albums = []
    for qid in sorted(parent_ids):
        parent = context[qid]
        types = item_ids(parent, "P31")
        # Explicit direct album type or a type with an English label ending in 'album'.
        if "Q482994" in types or any(label(context.get(t, {})).casefold().endswith("album") for t in types):
            albums.append(qid)
    return {"entities": list(selected.values()), "raw_genres": genre_rows, "raw_tags": [],
            "artists": [context[qid] for qid in sorted(artist_ids)],
            "parents": [context[qid] for qid in sorted(parent_ids)], "album_ids": albums,
            "referenced_entities": context, "enrichment_errors": []}, keys


def enrich(song, client):
    result = {"provider": "Wikidata", "matcher_version": MATCHER_VERSION, "sample_sha256": SAMPLE_SHA256,
              "song": song, "processed_at": utc_now(), "searches": [], "cache_keys": [], "metadata": None}
    try:
        entities, pair_ids, truncated, searches, keys = search_candidates(song, client)
        result["searches"], result["cache_keys"] = searches, keys
        context, keys = context_for_candidates(entities, client)
        result["cache_keys"].extend(keys)
        result.update(decide(song, entities, context, pair_ids, truncated))
        if result["status"] == "high_confidence":
            selected = {qid: entities[qid] for qid in result["selected_entity_ids"]}
            try:
                result["metadata"], keys = metadata(selected, context, client)
                result["cache_keys"].extend(keys)
            except APIError as exc:
                # A context lookup failure must not erase already confirmed identities.
                result["metadata"] = {"entities": list(selected.values()), "enrichment_errors": [str(exc)]}
                if exc.cache_key:
                    result["cache_keys"].append(exc.cache_key)
    except APIError as exc:
        result.update(status="error", reason=str(exc), found=False, selected_entity_ids=[], candidates=[], match_score=None)
        if exc.cache_key:
            result["cache_keys"].append(exc.cache_key)
    result["cache_keys"] = sorted(set(result["cache_keys"]))
    return result


def run(offline=False, replay=False, retry_errors=False, limit=200):
    guard_outputs()
    sample = load_sample()
    verify_foundation(sample)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    snapshot = OUTPUT / "sample.json"
    if snapshot.exists() and snapshot.read_bytes() != SAMPLE.read_bytes():
        raise ValueError("Phase 2B sample differs from Phase 2A")
    if not snapshot.exists():
        snapshot.write_bytes(SAMPLE.read_bytes())
    consecutive_errors = 0
    try:
        with WikidataClient(CACHE, offline=offline, retry_errors=retry_errors) as client:
            for index, song in enumerate(sample["songs"][:limit], 1):
                path = OUTPUT / "results" / (song["song_id"] + ".json")
                if path.exists():
                    old = json.loads(path.read_text(encoding="utf-8"))
                    if old["song"] != song or old["matcher_version"] != MATCHER_VERSION or old["sample_sha256"] != SAMPLE_SHA256:
                        raise ValueError("Stale or different result; inspect before replacing")
                    failed = old["status"] == "error" or bool((old.get("metadata") or {}).get("enrichment_errors"))
                    if not replay and not (retry_errors and failed):
                        continue
                result = enrich(song, client)
                write_json(path, result)
                print(f'{index}/200 {result["status"]} | {song["title"]} / {song["artist"]} | HTTP={client.network_requests}', flush=True)
                consecutive_errors = consecutive_errors + 1 if result["status"] == "error" else 0
                if consecutive_errors >= 3 and not offline:
                    raise APIError("Three consecutive failed songs; stopped. Inspect cached errors before retrying.")
            print(f'Network requests: {client.network_requests}; cache hits: {client.cache_hits}', flush=True)
    finally:
        verify_foundation(sample)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "report"))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.limit <= 200:
            raise ValueError("--limit must be 1 through 200; this experiment cannot expand the sample")
        if args.command == "run":
            run(args.offline, args.replay, args.retry_errors, args.limit)
        else:
            from phase2b_report import generate_report
            guard_outputs()
            generate_report()
    except (APIError, OSError, ValueError) as exc:
        print("Phase 2B failed: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
