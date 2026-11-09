import csv
import tempfile
import unittest
from pathlib import Path

from photo_audit.core import (
    audit, discover_photos, find_content_duplicates, normalize_id, read_ids, write_reports,
)


class CoreTests(unittest.TestCase):
    def test_normalize_excel_number(self):
        self.assertEqual(normalize_id("12345.0"), "12345")

    def test_audit_statuses_and_extra(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("A.jpg", "B.jpg", "B.png", "EXTRA.webp"):
                (root / name).touch()
            rows, extras = audit(["A", "B", "C", ""], discover_photos(root))
            self.assertEqual([row.status for row in rows], ["OK", "DUPLICATE", "MISSING", "EMPTY_ID"])
            self.assertEqual([path.name for path in extras], ["EXTRA.webp"])

    def test_prefix_matching(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ABC_01.jpg").touch()
            rows, _ = audit(["ABC"], discover_photos(root, match_prefix=True))
            self.assertEqual(rows[0].status, "OK")

    def test_csv_and_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["ID"])
                writer.writerow(["X1"])
            self.assertEqual(read_ids(source, "ID"), ["X1"])
            report = root / "report"
            summary = write_reports(*audit(["X1"], {}), report)
            self.assertEqual(summary["MISSING"], 1)
            self.assertTrue((report / "summary.json").is_file())
            self.assertTrue((report / "report.html").is_file())

    def test_content_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second, different = root / "one.jpg", root / "two.jpg", root / "three.jpg"
            first.write_bytes(b"same photo bytes")
            second.write_bytes(b"same photo bytes")
            different.write_bytes(b"different")
            groups = find_content_duplicates([first, second, different])
            self.assertEqual([[path.name for path in group] for group in groups], [["one.jpg", "two.jpg"]])

    def test_custom_prefix_separator(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ASSET-02.png").touch()
            photos = discover_photos(root, match_prefix=True, prefix_separator="-")
            self.assertIn("asset", photos)


if __name__ == "__main__":
    unittest.main()
