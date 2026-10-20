"""Hash canonical bytes, including the explicitly distributed lossless archives."""
import hashlib
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPRESSED_PUBLIC = frozenset({
    "data/public/master_weekly.csv",
    "analysis/moving_averages/data/monthly_classifier_overall.csv",
    "analysis/moving_averages/data/monthly_classifier_by_genre.csv",
})


def sha(path, root=ROOT):
    path = Path(path)
    relative = path.relative_to(root).as_posix()
    opener = path.open
    if not path.exists() and relative in COMPRESSED_PUBLIC:
        archive = path.with_suffix(path.suffix + ".xz")
        opener = lambda mode: lzma.open(archive, mode)
    digest = hashlib.sha256()
    with opener("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()
