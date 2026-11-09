from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def normalize_id(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text.casefold()


def read_ids(path: Path, column: str, sheet: str | None = None) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or column not in reader.fieldnames:
                raise ValueError(f"Kolom '{column}' tidak ditemukan. Kolom: {reader.fieldnames or []}")
            return ["" if row[column] is None else str(row[column]) for row in reader]
    if suffix in {".xlsx", ".xlsm"}:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("Excel memerlukan openpyxl: pip install -r requirements.txt") from exc
        workbook = load_workbook(path, read_only=True, data_only=True)
        worksheet = workbook[sheet] if sheet else workbook.active
        rows = worksheet.iter_rows(values_only=True)
        headers = [str(item).strip() if item is not None else "" for item in next(rows, ())]
        if column not in headers:
            raise ValueError(f"Kolom '{column}' tidak ditemukan. Kolom: {headers}")
        index = headers.index(column)
        return ["" if row[index] is None else str(row[index]) for row in rows if index < len(row)]
    raise ValueError("Format daftar harus .csv, .xlsx, atau .xlsm")


def discover_photos(folder: Path, match_prefix: bool = False) -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = defaultdict(list)
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGES:
            stem = path.stem.split("_", 1)[0] if match_prefix else path.stem
            found[normalize_id(stem)].append(path)
    return dict(found)


@dataclass(frozen=True)
class AuditRow:
    source_id: str
    status: str
    photo_count: int
    photo_paths: str


def audit(ids: Iterable[str], photos: dict[str, list[Path]]) -> tuple[list[AuditRow], list[Path]]:
    rows: list[AuditRow] = []
    expected: set[str] = set()
    for raw_id in ids:
        key = normalize_id(raw_id)
        if not key:
            rows.append(AuditRow(raw_id, "EMPTY_ID", 0, ""))
            continue
        expected.add(key)
        matches = photos.get(key, [])
        status = "MISSING" if not matches else "DUPLICATE" if len(matches) > 1 else "OK"
        rows.append(AuditRow(raw_id, status, len(matches), ";".join(str(path) for path in matches)))
    extras = [path for key, paths in photos.items() if key not in expected for path in paths]
    return rows, sorted(extras)


def write_reports(rows: list[AuditRow], extras: list[Path], output: Path) -> dict[str, int]:
    output.mkdir(parents=True, exist_ok=True)
    with (output / "audit.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source_id", "status", "photo_count", "photo_paths"])
        writer.writerows((row.source_id, row.status, row.photo_count, row.photo_paths) for row in rows)
    with (output / "unlisted_photos.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["photo_path"])
        writer.writerows((str(path),) for path in extras)
    summary = {status: sum(row.status == status for row in rows) for status in ("OK", "MISSING", "DUPLICATE", "EMPTY_ID")}
    summary["UNLISTED_PHOTOS"] = len(extras)
    summary["TOTAL_ROWS"] = len(rows)
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary

