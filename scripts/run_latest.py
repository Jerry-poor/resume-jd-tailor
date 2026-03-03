import argparse
import sys
from datetime import datetime
from pathlib import Path

from console import safe_print


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_python(script: Path, *args: str) -> None:
    import subprocess

    cmd = [sys.executable, str(script), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or f"Command failed: {' '.join(cmd)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the full pipeline and publish only the latest outputs")
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--experiences", required=True, help="Path to experiences_*.yaml")
    ap.add_argument("--base", required=True, help="Path to base profile JSON")
    ap.add_argument("--jd", required=True, help="Path to JD profile yaml")
    ap.add_argument("--jd-raw", default=None, help="Optional raw JD file path (.txt/.md or image)")
    ap.add_argument("--out-dir", default="outputs/final", help="Output directory (default: outputs/final)")
    ap.add_argument("--prefix", default="resume", help="Published filename prefix (default: resume)")
    ap.add_argument("--no-llm", action="store_true", help="Disable LLM rewrite pass (default: enabled)")
    ap.add_argument("--vertex-project-id", default="gen-lang-client-0259616768")
    ap.add_argument("--vertex-location", default="global")
    ap.add_argument("--gemini-model", default="gemini-3-flash-preview")
    args = ap.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = ts()

    semantic = out_dir / f"{args.prefix}.{run_id}.semantic.json"
    data = out_dir / f"{args.prefix}.{run_id}.zh.jd.json"
    html = out_dir / f"{args.prefix}.{run_id}.html"
    pdf = out_dir / f"{args.prefix}.{run_id}.pdf"

    script_dir = Path(__file__).resolve().parent
    build_data = script_dir / "build_resume_data.py"
    build_pdf = script_dir / "build_resume_html_pdf.py"
    publish = script_dir / "publish_latest.py"

    build_args = [
        "--lang",
        args.lang,
        "--experiences",
        str(Path(args.experiences).resolve()),
        "--base",
        str(Path(args.base).resolve()),
        "--jd",
        str(Path(args.jd).resolve()),
        "--semantic-out",
        str(semantic),
        "--out",
        str(data),
        "--vertex-project-id",
        str(args.vertex_project_id),
        "--vertex-location",
        str(args.vertex_location),
        "--gemini-model",
        str(args.gemini_model),
    ]
    if args.jd_raw:
        build_args += ["--jd-raw", str(Path(args.jd_raw).resolve())]
    if args.no_llm:
        build_args += ["--no-llm"]

    run_python(build_data, *build_args)
    run_python(build_pdf, "--data", str(data), "--html-out", str(html), "--pdf-out", str(pdf))
    run_python(
        publish,
        "--html",
        str(html),
        "--pdf",
        str(pdf),
        "--data",
        str(data),
        "--semantic",
        str(semantic),
        "--out-dir",
        str(out_dir),
        "--prefix",
        str(args.prefix),
    )

    safe_print(str(out_dir / f"{args.prefix}.pdf"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

