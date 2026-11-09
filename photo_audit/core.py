from __future__ import annotations

import csv
import hashlib
import html
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


def discover_photos(
    folder: Path, match_prefix: bool = False, prefix_separator: str = "_"
) -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = defaultdict(list)
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGES:
            stem = path.stem.split(prefix_separator, 1)[0] if match_prefix else path.stem
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


def file_digest(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def find_content_duplicates(paths: Iterable[Path]) -> list[list[Path]]:
    """Find byte-identical files efficiently by grouping size before hashing."""
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in paths:
        by_size[path.stat().st_size].append(path)
    groups: list[list[Path]] = []
    for candidates in by_size.values():
        if len(candidates) < 2:
            continue
        by_hash: dict[str, list[Path]] = defaultdict(list)
        for path in candidates:
            by_hash[file_digest(path)].append(path)
        groups.extend(sorted(group) for group in by_hash.values() if len(group) > 1)
    return sorted(groups, key=lambda group: str(group[0]))


def all_photo_paths(photos: dict[str, list[Path]]) -> list[Path]:
    return [path for paths in photos.values() for path in paths]


def _write_html_report(
    rows: list[AuditRow], extras: list[Path], duplicate_groups: list[list[Path]], output: Path
) -> None:
    colors = {"OK": "#16803a", "MISSING": "#c62828", "DUPLICATE": "#b26a00", "EMPTY_ID": "#666"}
    table_rows = "".join(
        "<tr><td>{}</td><td><span style='color:{}'>{}</span></td><td>{}</td><td>{}</td></tr>".format(
            html.escape(row.source_id), colors[row.status], row.status, row.photo_count,
            html.escape(row.photo_paths),
        )
        for row in rows
    )
    extra_items = "".join(f"<li>{html.escape(str(path))}</li>" for path in extras) or "<li>None</li>"
    duplicate_items = "".join(
        "<li>" + " &harr; ".join(html.escape(str(path)) for path in group) + "</li>"
        for group in duplicate_groups
    ) or "<li>None</li>"
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Photo Audit Report</title><style>
body{{font:14px system-ui;margin:2rem;color:#172033}} table{{border-collapse:collapse;width:100%}}
th,td{{padding:.6rem;border-bottom:1px solid #dde3ea;text-align:left}} th{{background:#f3f6f9}}
span{{font-weight:700}} code{{background:#f3f6f9;padding:.2rem}}</style></head><body>
<h1>Photo Audit Report</h1><p>Generated locally. No files were uploaded.</p>
<table><thead><tr><th>Source ID</th><th>Status</th><th>Count</th><th>Paths</th></tr></thead>
<tbody>{table_rows}</tbody></table><h2>Unlisted photos</h2><ul>{extra_items}</ul>
<h2>Byte-identical files (SHA-256)</h2><ul>{duplicate_items}</ul></body></html>"""
    (output / "report.html").write_text(document, encoding="utf-8")


def write_reports(
    rows: list[AuditRow], extras: list[Path], output: Path,
    duplicate_groups: list[list[Path]] | None = None,
) -> dict[str, int]:
    duplicate_groups = duplicate_groups or []
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
    summary["CONTENT_DUPLICATE_GROUPS"] = len(duplicate_groups)
    summary["TOTAL_ROWS"] = len(rows)
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (output / "content_duplicates.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["group", "photo_path"])
        for index, group in enumerate(duplicate_groups, start=1):
            writer.writerows((index, str(path)) for path in group)
    _write_html_report(rows, extras, duplicate_groups, output)
    return summary

