import argparse
import shutil
from datetime import datetime
from pathlib import Path

from console import safe_print


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def move_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    ensure_dir(dst.parent)
    shutil.move(str(src), str(dst))


def copy_file(src: Path, dst: Path) -> None:
    ensure_dir(dst.parent)
    shutil.copy2(str(src), str(dst))


def main() -> int:
    ap = argparse.ArgumentParser(description="Archive old outputs and publish the latest resume to stable filenames")
    ap.add_argument("--html", required=True, help="Source HTML file to publish")
    ap.add_argument("--pdf", required=True, help="Source PDF file to publish")
    ap.add_argument("--data", required=True, help="Source flattened resume JSON to publish")
    ap.add_argument("--semantic", default=None, help="Optional semantic resume JSON to publish")
    ap.add_argument("--out-dir", default="outputs/final", help="Output directory (default: outputs/final)")
    ap.add_argument("--prefix", default="resume", help="Published filename prefix (default: resume)")
    ap.add_argument(
        "--archive",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Archive existing published files before overwriting (default: true)",
    )
    ap.add_argument(
        "--keep-only-latest",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Keep only published stable files in out-dir; archive all other resume*.{html,pdf,json} (default: true)",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir).resolve()
    ensure_dir(out_dir)

    src_html = Path(args.html).resolve()
    src_pdf = Path(args.pdf).resolve()
    src_data = Path(args.data).resolve()
    src_semantic = Path(args.semantic).resolve() if args.semantic else None

    for src in (src_html, src_pdf, src_data):
        if not src.is_file():
            raise FileNotFoundError(f"File not found: {src}")
    if src_semantic and not src_semantic.is_file():
        raise FileNotFoundError(f"File not found: {src_semantic}")

    dst_html = out_dir / f"{args.prefix}.html"
    dst_pdf = out_dir / f"{args.prefix}.pdf"
    dst_data = out_dir / f"{args.prefix}.zh.jd.json"
    dst_semantic = out_dir / f"{args.prefix}.semantic.json"

    arch_dir: Path | None = None
    if args.archive or args.keep_only_latest:
        arch_dir = out_dir / "archive" / timestamp()

    if args.archive:
        assert arch_dir is not None
        move_if_exists(dst_html, arch_dir / dst_html.name)
        move_if_exists(dst_pdf, arch_dir / dst_pdf.name)
        move_if_exists(dst_data, arch_dir / dst_data.name)
        move_if_exists(dst_semantic, arch_dir / dst_semantic.name)

    copy_file(src_html, dst_html)
    copy_file(src_pdf, dst_pdf)
    copy_file(src_data, dst_data)
    if src_semantic:
        copy_file(src_semantic, dst_semantic)
    elif dst_semantic.exists():
        dst_semantic.unlink()

    if args.keep_only_latest:
        assert arch_dir is not None
        protected = {dst_html.resolve(), dst_pdf.resolve(), dst_data.resolve(), dst_semantic.resolve()}
        for path in sorted(out_dir.glob("resume*")):
            if path.is_dir():
                continue
            if "archive" in path.parts:
                continue
            if path.suffix.lower() not in {".html", ".pdf", ".json"}:
                continue
            if not path.name.startswith("resume"):
                continue
            if path.resolve() in protected:
                continue
            move_if_exists(path, arch_dir / path.name)

    safe_print(str(dst_html))
    safe_print(str(dst_pdf))
    safe_print(str(dst_data))
    if src_semantic:
        safe_print(str(dst_semantic))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
