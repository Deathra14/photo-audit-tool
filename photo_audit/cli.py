from __future__ import annotations

import argparse
from pathlib import Path

from .core import all_photo_paths, audit, discover_photos, find_content_duplicates, read_ids, write_reports


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
    audit_parser.add_argument("--prefix-separator", default="_", help="Pemisah prefix (default: _)")
    audit_parser.add_argument("--content-hash", action="store_true", help="Cari file identik dengan SHA-256")
    commands.add_parser("gui", help="Buka antarmuka desktop")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "gui":
        from .gui import launch
        launch()
        return 0
    if not args.input.is_file():
        raise SystemExit(f"File input tidak ditemukan: {args.input}")
    if not args.photos.is_dir():
        raise SystemExit(f"Folder foto tidak ditemukan: {args.photos}")
    ids = read_ids(args.input, args.id_column, args.sheet)
    photos = discover_photos(args.photos, args.match_prefix, args.prefix_separator)
    rows, extras = audit(ids, photos)
    duplicates = find_content_duplicates(all_photo_paths(photos)) if args.content_hash else []
    summary = write_reports(rows, extras, args.output, duplicates)
    print(f"Selesai. Laporan: {args.output.resolve()}")
    print(" | ".join(f"{key}={value}" for key, value in summary.items()))
    return 0

