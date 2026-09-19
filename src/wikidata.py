"""Bounded, cached Wikidata Action API reads for the Phase 2B pilot."""

import email.utils
import fcntl
import gzip
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from musicbrainz import APIError, utc_now, write_json

BASE_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = "CMPT491MusicMetadata/0.2 (https://github.com/Jamster187/cmpt491-music-censorship)"


class WikidataClient:
    def __init__(self, cache_dir, offline=False, retry_errors=False, opener=None, clock=None, sleep=None):
        self.cache_dir = Path(cache_dir)
        self.offline, self.retry_errors = offline, retry_errors
        self.opener = opener or urllib.request.urlopen
        self.clock, self.sleep = clock or time.time, sleep or time.sleep
        self.network_requests, self.cache_hits = 0, 0
        self.next_allowed, self.lock = 0.0, None
        self.entity_index = {}

    def __enter__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.lock = (self.cache_dir / "client.lock").open("a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            state = self.cache_dir / "rate_state.json"
            if state.exists():
                self.next_allowed = json.loads(state.read_text())["next_allowed"]
            # Entity batches may overlap. Reuse the earliest cached revision per ID.
            envelopes = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((self.cache_dir / "requests").glob("*.json"))]
            for envelope in sorted(envelopes, key=lambda e: (e["attempts"][0]["requested_at"], e["cache_key"])):
                payload = self._cached_payload(envelope)
                if payload is not None:
                    self._index_entities(payload, envelope["cache_key"])
        except Exception:
            self.lock.close()
            raise
        return self

    def __exit__(self, *args):
        if self.lock:
            self.lock.close()

    @staticmethod
    def _cached_payload(envelope):
        for attempt in envelope["attempts"]:
            if hashlib.sha256(attempt["body"].encode("utf-8")).hexdigest() != attempt["body_sha256"]:
                raise APIError("Wikidata cache checksum mismatch", envelope["cache_key"])
        latest = envelope["attempts"][-1] if envelope["attempts"] else None
        if latest and latest["status"] == 200 and not latest["error"]:
            return json.loads(latest["body"])
        return None

    def _index_entities(self, payload, key):
        for qid, entity in payload.get("entities", {}).items():
            self.entity_index.setdefault(qid, (entity, key))

    def _set_next(self, value):
        self.next_allowed = value
        write_json(self.cache_dir / "rate_state.json", {"next_allowed": value})

    def get(self, **params):
        params = dict(params, format="json", maxlag=5)
        url = BASE_URL + "?" + urllib.parse.urlencode(sorted(params.items()))
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        path = self.cache_dir / "requests" / (key + ".json")
        envelope = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "provider": "Wikidata", "url": url, "params": params, "cache_key": key,
            "request_headers": {"User-Agent": USER_AGENT, "Accept": "application/json", "Accept-Encoding": "gzip"},
            "attempts": [],
        }
        if envelope["url"] != url:
            raise APIError("Cache URL mismatch", key)
        payload = self._cached_payload(envelope)
        if payload is not None:
            self.cache_hits += 1
            self._index_entities(payload, key)
            return payload, key
        if self.offline or (envelope["attempts"] and not self.retry_errors):
            self.cache_hits += 1
            raise APIError("Offline cache miss or cached failed request", key)
        for attempt_number in range(3):
            while self.clock() < self.next_allowed:
                self.sleep(min(30, self.next_allowed - self.clock()))
            self._set_next(self.clock() + 1.1)
            requested_at = utc_now()
            status, headers, raw, error, api_code = None, {}, b"", None, None
            self.network_requests += 1
            try:
                with self.opener(urllib.request.Request(url, headers=envelope["request_headers"]), timeout=30) as response:
                    status, headers, raw = response.status, dict(response.headers.items()), response.read()
            except urllib.error.HTTPError as exc:
                status, headers, raw, error = exc.code, dict(exc.headers.items()), exc.read(), str(exc)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                error = str(exc)
            if next((v for k, v in headers.items() if k.lower() == "content-encoding"), "") == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except (OSError, EOFError) as exc:
                    error = "Invalid gzip response: " + str(exc)
            body = raw.decode("utf-8", errors="replace")
            if status == 200 and not error:
                try:
                    payload = json.loads(body)
                    if not isinstance(payload, dict):
                        raise ValueError("Expected a JSON object")
                    if payload.get("error"):
                        api_code = payload["error"].get("code")
                        error = "Wikidata API error: " + str(payload["error"])
                except (ValueError, TypeError) as exc:
                    error = "Invalid JSON: " + str(exc)
            envelope["attempts"].append({"requested_at": requested_at, "received_at": utc_now(),
                "status": status, "headers": headers, "body": body,
                "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(), "error": error})
            write_json(path, envelope)
            if status == 200 and not error:
                self._index_entities(payload, key)
                return payload, key
            delay = 5 * 2 ** attempt_number
            retry_after = next((v for k, v in headers.items() if k.lower() == "retry-after"), None)
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    try:
                        delay = max(delay, email.utils.parsedate_to_datetime(retry_after).timestamp() - self.clock())
                    except (TypeError, ValueError):
                        pass
            self._set_next(max(self.next_allowed, self.clock() + delay))
            if status not in (None, 429, 500, 502, 503, 504) and api_code not in ("maxlag", "ratelimited", "readonly"):
                break
        raise APIError("Wikidata request failed: " + str(error or status), key)

    def entities(self, ids):
        ids = sorted(set(ids))
        if any(not qid.startswith("Q") or not qid[1:].isdigit() for qid in ids):
            raise ValueError("Expected Wikidata Q identifiers")
        missing = [qid for qid in ids if qid not in self.entity_index]
        for begin in range(0, len(missing), 50):
            self.get(action="wbgetentities", ids="|".join(missing[begin:begin + 50]),
                     props="info|labels|aliases|descriptions|claims", languages="en|mul")
        if any(qid not in self.entity_index for qid in ids):
            raise APIError("Entity response omitted a requested identifier")
        return {qid: self.entity_index[qid][0] for qid in ids}, sorted({self.entity_index[qid][1] for qid in ids})
