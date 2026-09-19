"""Read the immutable snapshot and define conservative, versioned identities."""

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://github.com/mhollingshead/billboard-hot-100"
CHART_FIELDS = ("date", "data")
SONG_FIELDS = ("song", "artist", "this_week", "last_week", "peak_position", "weeks_on_chart")
NUMERIC_FIELDS = SONG_FIELDS[2:]
IDENTITY_VERSION = "billboard-song-v1"
NORMALIZATION_VERSION = "nfc-casefold-unicode-whitespace-nfc-v1"
SONG_COLUMNS = ("song_id", "title", "artist", "normalized_title", "normalized_artist")
OBSERVATION_COLUMNS = (
    "song_id", "chart_date", "rank", "last_week", "peak_position", "weeks_on_chart",
    "source_chart_index", "source_row_index",
)


class DataError(ValueError):
    """An unsupported source or failed integrity check; never skip the record."""


def normalize_text(value):
    value = unicodedata.normalize("NFC", value)
    return unicodedata.normalize("NFC", " ".join(value.casefold().split()))


def song_id(title, artist):
    # JSON array encoding prevents ambiguous boundaries between title and artist.
    identity = json.dumps([title, artist], ensure_ascii=False, separators=(",", ":"))
    payload = (IDENTITY_VERSION + "\0" + identity).encode("utf-8")
    return "song_" + hashlib.sha256(payload).hexdigest()


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise DataError("Duplicate JSON object key: {!r}".format(key))
        obj[key] = value
    return obj


def _reject_constant(value):
    raise DataError("Non-standard JSON constant: " + value)


@dataclass
class Source:
    path: Path
    sha256: str
    byte_count: int
    charts: list
    songs: list
    identities: dict

    def observations(self):
        for chart_index, chart in enumerate(self.charts):
            for row_index, row in enumerate(chart["data"]):
                yield (
                    self.identities[(row["song"], row["artist"])], chart["date"],
                    row.get("this_week"), row.get("last_week"), row.get("peak_position"),
                    row.get("weeks_on_chart"), chart_index, row_index,
                )

    @property
    def observation_count(self):
        return sum(len(chart["data"]) for chart in self.charts)


def read_source(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    try:
        charts = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DataError("Invalid source JSON: {}".format(exc)) from exc
    if not isinstance(charts, list) or not charts:
        raise DataError("Expected a nonempty top-level array of weekly charts")

    identities = {}
    ids = {}
    for chart_index, chart in enumerate(charts):
        location = "chart[{}]".format(chart_index)
        if not isinstance(chart, dict) or set(chart) != set(CHART_FIELDS):
            raise DataError(location + ": expected exactly the keys date and data")
        chart_date = chart["date"]
        try:
            valid_date = isinstance(chart_date, str) and date.fromisoformat(chart_date).isoformat() == chart_date
        except ValueError:
            valid_date = False
        if not valid_date:
            raise DataError(location + ": date must be an ISO YYYY-MM-DD string")
        if not isinstance(chart["data"], list):
            raise DataError(location + ": data must be an array")
        for row_index, row in enumerate(chart["data"]):
            location = "chart[{}].data[{}]".format(chart_index, row_index)
            if not isinstance(row, dict):
                raise DataError(location + ": song entry must be an object")
            extras = set(row) - set(SONG_FIELDS)
            if extras:
                raise DataError(location + ": unmapped fields: " + ", ".join(sorted(extras)))
            for field in ("song", "artist"):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    raise DataError(location + ": " + field + " must be a nonblank string")
                try:
                    row[field].encode("utf-8")
                except UnicodeError as exc:
                    raise DataError(location + ": invalid Unicode in " + field) from exc
            for field in NUMERIC_FIELDS:
                value = row.get(field)
                if value is not None and type(value) is not int:
                    raise DataError(location + ": " + field + " must be an integer, null, or absent")
                if value is not None and not -(2**63) <= value < 2**63:
                    raise DataError(location + ": " + field + " exceeds SQLite integer capacity")
            identity = (row["song"], row["artist"])
            if identity not in identities:
                identifier = song_id(*identity)
                if identifier in ids and ids[identifier] != identity:
                    raise DataError("SHA-256 song ID collision; aborting rather than merging")
                identities[identity] = identifier
                ids[identifier] = identity

    songs = sorted(
        (identifier, title, artist, normalize_text(title), normalize_text(artist))
        for (title, artist), identifier in identities.items()
    )
    return Source(path, hashlib.sha256(raw).hexdigest(), len(raw), charts, songs, identities)


def source_label(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return path.name


def pipeline_sha256():
    digest = hashlib.sha256()
    for name in ("billboard.py", "phase1.py", "quality.py"):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update((Path(__file__).parent / name).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
