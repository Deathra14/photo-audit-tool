from __future__ import annotations

import argparse
from pathlib import Path

from .core import audit, discover_photos, read_ids, write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="photo-audit", description="Audit foto terhadap daftar Excel/CSV")
    commands = parser.add_subparsers(dest="command", required=True)
    audit_parser = commands.add_parser("audit", help="Jalankan audit")
    audit_parser.add_argument("input", type=Path, help="File CSV/XLSX")
    audit_parser.add_argument("photos", type=Path, help="Folder foto")
    audit_parser.add_argument("--id-column", default="ID", help="Nama kolom ID (default: ID)")
    audit_parser.add_argument("--sheet", help="Nama sheet Excel")
    audit_parser.add_argument("--output", type=Path, default=Path("reports"), help="Folder laporan")
    audit_parser.add_argument("--match-prefix", action="store_true", help="Cocokkan bagian sebelum underscore")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input.is_file():
        raise SystemExit(f"File input tidak ditemukan: {args.input}")
    if not args.photos.is_dir():
        raise SystemExit(f"Folder foto tidak ditemukan: {args.photos}")
    ids = read_ids(args.input, args.id_column, args.sheet)
    photos = discover_photos(args.photos, args.match_prefix)
    rows, extras = audit(ids, photos)
    summary = write_reports(rows, extras, args.output)
    print(f"Selesai. Laporan: {args.output.resolve()}")
    print(" | ".join(f"{key}={value}" for key, value in summary.items()))
    return 0

