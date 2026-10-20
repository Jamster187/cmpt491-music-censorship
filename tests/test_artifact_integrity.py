"""Fresh clones validate public archives without silently exempting corruption."""
import hashlib
import lzma
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
import artifact_integrity as a
import repository_layout as r


class ArtifactIntegrityTests(unittest.TestCase):
    def test_archive_is_hashed_as_decompressed_bytes_without_materializing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in a.COMPRESSED_PUBLIC:
                path = root/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                data = b"public,values\n1,2\n"
                path.with_suffix(".csv.xz").write_bytes(lzma.compress(data))
                self.assertEqual(a.sha(path, root), hashlib.sha256(data).hexdigest())
                self.assertFalse(path.exists())
                path.with_suffix(".csv.xz").write_bytes(lzma.compress(b"changed"))
                self.assertNotEqual(a.sha(path, root), hashlib.sha256(data).hexdigest())
                path.with_suffix(".csv.xz").write_bytes(b"not xz")
                with self.assertRaises(lzma.LZMAError):
                    a.sha(path, root)

    def test_present_plain_corruption_is_not_masked_by_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root/"data/public/master_weekly.csv"
            path.parent.mkdir(parents=True)
            path.with_suffix(".csv.xz").write_bytes(lzma.compress(b"good"))
            path.write_bytes(b"bad")
            self.assertEqual(a.sha(path, root), hashlib.sha256(b"bad").hexdigest())

    def test_arbitrary_missing_files_do_not_get_archive_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"unknown.csv.xz").write_bytes(lzma.compress(b"data"))
            with self.assertRaises(FileNotFoundError):
                a.sha(root/"unknown.csv", root)

    def test_only_documented_optional_links_are_exempt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root/"docs/lyrics_exclusion_audit.md"
            path.parent.mkdir()
            path.write_text("[local](../data/processed/lyrics_exclusion_categories.csv)\n"
                            "[broken](../data/processed/unknown.csv)\n[typo](missing.md)\n")
            with patch.object(r, "ROOT", root), patch.object(r, "markdown_files", return_value=[path]):
                broken, n = r.broken_links()
            self.assertEqual(n, 3)
            self.assertEqual([target for _, target in broken], ["../data/processed/unknown.csv", "missing.md"])


if __name__ == "__main__":
    unittest.main()
