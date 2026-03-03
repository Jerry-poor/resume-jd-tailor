import argparse
from pathlib import Path

from console import safe_print


def main() -> int:
    ap = argparse.ArgumentParser(description="Delete non-PDF files in an output directory")
    ap.add_argument("--dir", default="outputs", help="Output directory to clean (default: outputs)")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be deleted without deleting")
    args = ap.parse_args()

    out_dir = Path(args.dir)
    if not out_dir.exists():
        raise SystemExit(f"Directory not found: {out_dir}")
    if not out_dir.is_dir():
        raise SystemExit(f"Not a directory: {out_dir}")

    removed = 0

    # 1) Remove all non-PDF files (recursive).
    for path in sorted(out_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir():
            continue
        if path.suffix.lower() == ".pdf":
            continue
        if args.dry_run:
            safe_print(f"would delete: {path}")
            removed += 1
            continue
        try:
            path.unlink()
            safe_print(f"deleted: {path}")
            removed += 1
        except OSError as e:
            safe_print(f"skip (cannot delete): {path} ({e})")

    # 2) Remove empty directories (recursive).
    for path in sorted(out_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if not path.is_dir():
            continue
        try:
            if any(path.iterdir()):
                continue
            if args.dry_run:
                safe_print(f"would remove dir: {path}")
            else:
                path.rmdir()
                safe_print(f"removed dir: {path}")
        except OSError:
            pass

    safe_print(f"done (removed={removed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
