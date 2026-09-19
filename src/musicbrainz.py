"""Small, cached, rate-limited MusicBrainz GET client. No credentials required."""

import email.utils
import fcntl
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://musicbrainz.org/ws/2/"
USER_AGENT = "CMPT491MusicMetadata/0.1 (https://github.com/Jamster187/cmpt491-music-censorship)"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class APIError(RuntimeError):
    def __init__(self, message, cache_key=None):
        super().__init__(message)
        self.cache_key = cache_key


class MusicBrainzClient:
    def __init__(self, cache_dir, offline=False, retry_errors=False, opener=None, clock=None, sleep=None):
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.retry_errors = retry_errors
        self.opener = opener or urllib.request.urlopen
        self.clock = clock or time.time
        self.sleep = sleep or time.sleep
        self.network_requests = 0
        self.cache_hits = 0
        self.lock = None
        self.next_allowed = 0.0

    def __enter__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.lock = (self.cache_dir / "client.lock").open("a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise APIError("Another MusicBrainz run holds the cache lock; run only one client")
        state = self.cache_dir / "rate_state.json"
        if state.exists():
            self.next_allowed = json.loads(state.read_text())["next_allowed"]
        return self

    def __exit__(self, *args):
        if self.lock:
            self.lock.close()

    @staticmethod
    def request_url(entity, params):
        if not entity or any(part in entity for part in ("..", "?", "#", ":")):
            raise ValueError("Invalid MusicBrainz entity path")
        query = dict(params, fmt="json")
        return BASE_URL + entity.strip("/") + "?" + urllib.parse.urlencode(sorted(query.items()))

    def _wait(self):
        while self.next_allowed > self.clock():
            self.sleep(min(30, self.next_allowed - self.clock()))

    def _set_next(self, next_allowed):
        self.next_allowed = next_allowed
        write_json(self.cache_dir / "rate_state.json", {"next_allowed": next_allowed})

    def get(self, entity, **params):
        url = self.request_url(entity, params)
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        path = self.cache_dir / "requests" / (key + ".json")
        envelope = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "provider": "MusicBrainz", "url": url, "cache_key": key,
            "request_headers": {"User-Agent": USER_AGENT, "Accept": "application/json"}, "attempts": [],
        }
        if envelope["url"] != url:
            raise APIError("Cache URL mismatch", key)
        if envelope["attempts"]:
            latest = envelope["attempts"][-1]
            if latest["status"] == 200 and not latest.get("error"):
                self.cache_hits += 1
                return json.loads(latest["body"]), key
            if self.offline or not self.retry_errors:
                self.cache_hits += 1
                raise APIError("Cached request failed: " + str(latest.get("error") or latest["status"]), key)
        if self.offline:
            raise APIError("Offline cache miss: " + url, key)
        for attempt in range(3):
            self._wait()
            self._set_next(self.clock() + 1.1)
            requested_at = utc_now()
            status, headers, raw, error = None, {}, b"", None
            self.network_requests += 1
            request = urllib.request.Request(url, headers=envelope["request_headers"])
            try:
                with self.opener(request, timeout=30) as response:
                    status = response.status
                    headers = dict(response.headers.items())
                    raw = response.read()
            except urllib.error.HTTPError as exc:
                status, headers, raw, error = exc.code, dict(exc.headers.items()), exc.read(), str(exc)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                error = str(exc)
            body = raw.decode("utf-8", errors="replace")
            if status == 200:
                try:
                    payload = json.loads(body)
                    if not isinstance(payload, dict):
                        raise ValueError("Expected a JSON object")
                except (ValueError, TypeError) as exc:
                    error = "Invalid API response: " + str(exc)
            saved = {"requested_at": requested_at, "received_at": utc_now(), "status": status,
                     "headers": headers, "body": body, "body_sha256": hashlib.sha256(raw).hexdigest(), "error": error}
            envelope["attempts"].append(saved)
            write_json(path, envelope)  # Every attempt, including 429/503, survives interruption.
            if status == 200 and not error:
                return payload, key
            retry_after = next((v for k, v in headers.items() if k.lower() == "retry-after"), None)
            delay = 2 ** (attempt + 1)
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    try:
                        delay = max(delay, email.utils.parsedate_to_datetime(retry_after).timestamp() - self.clock())
                    except (ValueError, TypeError):
                        pass
            self._set_next(max(self.next_allowed, self.clock() + delay))
            if status not in (None, 429, 500, 502, 503, 504):
                break
        raise APIError("MusicBrainz request failed: " + str(error or status), key)
