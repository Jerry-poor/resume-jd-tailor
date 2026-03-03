import argparse
import shutil
import subprocess
from pathlib import Path

from console import safe_print


BROWSER_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]


def find_browser() -> str:
    for candidate in BROWSER_CANDIDATES:
        if candidate.is_file():
            return str(candidate)
    for name in ("msedge", "chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    raise FileNotFoundError("No supported browser found. Install Edge or Chrome.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Export HTML to PDF with Edge/Chrome headless")
    ap.add_argument("--html", required=True, help="Input HTML file")
    ap.add_argument("--pdf", required=True, help="Output PDF file")
    ap.add_argument("--browser", default=None, help="Optional browser executable path")
    args = ap.parse_args()

    html_path = Path(args.html).resolve()
    pdf_path = Path(args.pdf).resolve()
    browser = args.browser or find_browser()

    if not html_path.is_file():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()

    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--disable-software-rasterizer",
        f"--print-to-pdf={pdf_path}",
        "--print-to-pdf-no-header",
        html_path.as_uri(),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Browser export failed")
    if not pdf_path.is_file():
        raise RuntimeError("Browser reported success but PDF was not created")

    safe_print(str(pdf_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
