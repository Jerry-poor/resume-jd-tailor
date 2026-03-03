import argparse
import shutil
from pathlib import Path

from console import safe_print


def copy_tree(src: Path, dst: Path, force: bool) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    if not src.is_dir():
        raise NotADirectoryError(src)

    if dst.exists():
        if not dst.is_dir():
            raise NotADirectoryError(dst)
        if not force:
            safe_print(f"skip (exists): {dst}")
            return

    if hasattr(shutil, "copytree"):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        # Fallback for very old Python; keep it simple.
        if dst.exists() and force:
            for p in dst.rglob("*"):
                if p.is_file():
                    p.unlink()
        shutil.copytree(src, dst)
    safe_print(f"copied: {src} -> {dst}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold a runnable resume workspace from this skill")
    ap.add_argument("--dest", required=True, help="Destination directory (workspace root)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing directories/files")
    args = ap.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    dest_root = Path(args.dest).expanduser().resolve()
    dest_root.mkdir(parents=True, exist_ok=True)

    # Copy scripts so the workspace is runnable without referencing the skill path.
    copy_tree(skill_root / "scripts", dest_root / "scripts", force=args.force)

    # Copy data + templates from assets into conventional workspace layout.
    copy_tree(skill_root / "assets" / "data", dest_root / "data", force=args.force)
    copy_tree(skill_root / "assets" / "templates", dest_root / "templates", force=args.force)

    outputs_dir = dest_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    safe_print(f"ok: ensured {outputs_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
