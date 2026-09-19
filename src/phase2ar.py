"""Replay the fixed MusicBrainz pilot as title/artist assets. No HTTP client."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import unicodedata
from urllib.parse import urlparse

from metadata_match import artist_credit
from musicbrainz_asset_match import VERSION, decide, text_key

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "data/experiments/phase2a"
OUT = ROOT / "data/experiments/phase2ar"
CACHE = ROOT / "data/cache/musicbrainz/requests"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))


def read_cache(directory):
    responses, entities, fingerprints = {}, {}, {}
    for path in sorted(Path(directory).glob("*.json")):
        envelope = json.loads(path.read_text())
        key = envelope["cache_key"]
        if path.stem != key or hashlib.sha256(envelope["url"].encode()).hexdigest() != key:
            raise ValueError("Cache URL/key mismatch: " + str(path))
        success = []
        for attempt in envelope["attempts"]:
            if attempt.get("body") is not None:
                if hashlib.sha256(attempt["body"].encode()).hexdigest() != attempt["body_sha256"]:
                    raise ValueError("Cache body checksum mismatch: " + str(path))
            if attempt["status"] == 200:
                success.append(attempt)
        if not success:
            continue
        a = success[-1]
        item = {"provider": "MusicBrainz", "cache_key": key, "url": envelope["url"],
                "retrieved_at": a["received_at"], "body_sha256": a["body_sha256"],
                "payload": json.loads(a["body"])}
        responses[key] = item
        parts = urlparse(envelope["url"]).path.strip("/").split("/")
        if len(parts) == 4:
            kind, entity_id = parts[2:]
            if item["payload"].get("id") != entity_id:
                raise ValueError("Lookup entity ID mismatch")
            if (kind, entity_id) in entities:
                raise ValueError("Multiple lookup variants require explicit resolution")
            entities[kind, entity_id] = item
        fingerprints[str(path.relative_to(ROOT))] = digest(path)
    return responses, entities, fingerprints


def union_objects(objects):
    return [json.loads(s) for s in sorted({json.dumps(o, sort_keys=True, ensure_ascii=False) for o in objects})]


def replay_song(song, old, responses, entities):
    raw_by_id = {}
    for search in old["searches"]:
        response = responses[search["cache_key"]]  # Missing cache is an error, never not_found.
        payload = response["payload"]
        if payload["count"] != search["count"] or len(payload.get("recordings", [])) != search["returned"]:
            raise ValueError("Search/result count mismatch")
        for candidate in payload.get("recordings", []):
            raw_by_id.setdefault(candidate["id"], []).append({"cache_key": response["cache_key"], "raw": candidate})
    candidates, conflicts = [], []
    for rid, variants in sorted(raw_by_id.items()):
        lookup = entities.get(("recording", rid))
        if lookup:
            variants.append({"cache_key": lookup["cache_key"], "raw": lookup["payload"]})
        raw = max((v["raw"] for v in variants), key=lambda c: int(c.get("score", 0))).copy()
        for field in ("releases", "genres", "tags", "isrcs", "relations"):
            raw[field] = union_objects([o for v in variants for o in v["raw"].get(field, [])])
        keys = {(text_key(v["raw"].get("title", "")), text_key(artist_credit(v["raw"]), True),
                 tuple(sorted(p["artist"]["id"] for p in v["raw"].get("artist-credit", [])
                              if isinstance(p, dict) and p.get("artist", {}).get("id")))) for v in variants}
        if len(keys) > 1:
            conflicts.append(rid)
        candidates.append(raw)
    artist_entities = {eid: response["payload"] for (kind, eid), response in entities.items() if kind == "artist"}
    result = decide(song, candidates, artist_entities,
                    truncated=any(s["count"] > s["returned"] for s in old["searches"]))
    if set(conflicts).intersection(result["supporting_recording_ids"]):
        result.update(asset_match_status="ambiguous", reason="cached_identity_conflict", supporting_recording_ids=[],
                      supporting_artist_ids=[], canonical_recording_status="unresolved")
    support = set(result["supporting_recording_ids"])
    metadata = []
    for rid in sorted(support):
        for variant in raw_by_id[rid]:
            response = responses[variant["cache_key"]]
            metadata.append({"level": "recording", "entity_id": rid, "cache_key": response["cache_key"],
                             "retrieved_at": response["retrieved_at"], "raw": variant["raw"],
                             "response_kind": "lookup" if "/recording/" in response["url"] else "search"})
    artists = set(result["supporting_artist_ids"])
    groups = {r["release-group"]["id"] for c in candidates if c["id"] in support
              for r in c.get("releases", []) if r.get("release-group", {}).get("id")}
    for kind, ids in (("artist", artists), ("release-group", groups)):
        for entity_id in sorted(ids):
            response = entities.get((kind, entity_id))
            if response:
                metadata.append({"level": kind, "entity_id": entity_id, "cache_key": response["cache_key"],
                                 "retrieved_at": response["retrieved_at"], "raw": response["payload"], "response_kind": "lookup"})
    result.update(song=song, provider="MusicBrainz", matcher_version=VERSION,
                  phase2a_status=old["status"], phase2a_reason=old["reason"],
                  newly_accepted=old["status"] != "high_confidence" and result["asset_match_status"] == "high_confidence",
                  cached_identity_conflicts=conflicts, raw_candidate_variants=raw_by_id,
                  metadata_evidence=metadata, linked_release_group_ids=sorted(groups),
                  searches=old["searches"],
                  cache_provenance={k: {f: responses[k][f] for f in ("provider", "url", "retrieved_at", "body_sha256")}
                                    for k in sorted({v["cache_key"] for vs in raw_by_id.values() for v in vs} |
                                                    {m["cache_key"] for m in metadata} |
                                                    {s["cache_key"] for s in old["searches"]})})
    return result


def run():
    sample_path = OLD / "sample.json"
    sample = json.loads(sample_path.read_text())
    songs = sample["songs"]
    if len(songs) != 200 or len({s["song_id"] for s in songs}) != 200:
        raise ValueError("Expected the original 200 unique identities")
    db = ROOT / "data/processed/music.db"
    if digest(db) != sample["canonical_database_sha256"]:
        raise ValueError("Canonical database differs from original sample")
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
        for song in songs:
            row = conn.execute("SELECT s.title,s.artist,MIN(c.chart_date) FROM songs s JOIN chart_observations c USING(song_id) WHERE s.song_id=? GROUP BY s.song_id", (song["song_id"],)).fetchone()
            if row != (song["title"], song["artist"], song["first_chart_date"]):
                raise ValueError("Sample identity or first chart date differs from canonical database")
    responses, entities, cache_hashes = read_cache(CACHE)
    results = []
    old_hashes = {}
    for song in songs:
        path = OLD / "results" / (song["song_id"] + ".json")
        old = json.loads(path.read_text())
        if old["song"] != song:
            raise ValueError("Phase 2A result sample mismatch")
        result = replay_song(song, old, responses, entities)
        write_json(OUT / "results" / path.name, result)
        old_hashes[str(path.relative_to(ROOT))] = digest(path)
        results.append(result)
    # Copy exactly, including original formatting; independent experiment location.
    target = OUT / "sample.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_bytes(sample_path.read_bytes())
    os.replace(str(tmp), str(target))
    provenance = {"matcher_version": VERSION, "sample_sha256": digest(sample_path),
                  "normalization_unicode_version": unicodedata.unidata_version,
                  "canonical_database_sha256": digest(db), "billboard_source_sha256": digest(ROOT / "data/raw/billboard-hot-100.json"),
                  "network_requests": 0, "cache_files_sha256": cache_hashes, "phase2a_results_sha256": old_hashes,
                  "code_sha256": {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), ROOT / "src/musicbrainz_asset_match.py", ROOT / "src/phase2ar_report.py", ROOT / "src/metadata_match.py"]}}
    from phase2ar_report import report
    summary = report(results, provenance, ROOT, OUT)
    print(json.dumps({k: summary[k] for k in ("sample_size", "status_counts", "newly_accepted", "new_from_multiple_recordings", "coverage")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    run()
