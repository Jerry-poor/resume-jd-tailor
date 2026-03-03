import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from console import safe_print

def truncate_data(data_path: Path) -> bool:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    for prefix in ["RESEARCH_1", "WORK_1"]:
        bullets = data.get(f"{prefix}_BULLETS", [])
        if len(bullets) > 1:
            bullets.pop()
            data[f"{prefix}_BULLETS"] = bullets
            for i in range(1, 10):
                data[f"{prefix}_BULLET_{i}"] = ""
                # Keep template visibility in sync with content after truncation.
                data[f"{prefix}_BULLET_{i}_STYLE"] = "display:none;"
            for i, b in enumerate(bullets):
                data[f"{prefix}_BULLET_{i+1}"] = b
                data[f"{prefix}_BULLET_{i+1}_STYLE"] = ""
            data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            safe_print(f"[Fallback] Truncated 1 bullet from {prefix} to reduce length.")
            return True
    return False


def run_python(script: Path, *args: str) -> None:
    cmd = [sys.executable, str(script), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or f"Command failed: {' '.join(cmd)}")


def count_pdf_pages(pdf_path: Path) -> int:
    data = pdf_path.read_bytes()
    count = data.count(b"/Type /Page")
    pages_node = data.count(b"/Type /Pages")
    pages = count - pages_node
    if pages <= 0:
        raise RuntimeError("Unable to detect PDF page count")
    return pages


def backup_if_exists(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)
    return backup


def restore_backup(backup: Path | None, target: Path) -> None:
    if backup is None:
        if target.exists():
            target.unlink()
        return
    shutil.copy2(backup, target)


def cleanup_backup(backup: Path | None) -> None:
    if backup and backup.exists():
        backup.unlink()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build resume PDF from HTML and enforce a max page count")
    ap.add_argument("--data", required=True, help="Resume JSON path")
    default_template = Path(__file__).resolve().parents[1] / "assets" / "templates" / "template_html.html"
    ap.add_argument("--template", default=str(default_template), help="HTML template path")
    ap.add_argument("--html-out", required=True, help="Final HTML output path")
    ap.add_argument("--pdf-out", required=True, help="Final PDF output path")
    ap.add_argument("--max-pages", type=int, default=1, help="Maximum allowed PDF pages")
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    render_script = script_dir / "render_resume_html.py"
    pdf_script = script_dir / "html_to_pdf.py"

    html_out = Path(args.html_out).resolve()
    pdf_out = Path(args.pdf_out).resolve()
    html_tmp = html_out.with_suffix(".tmp.html")
    pdf_tmp = pdf_out.with_suffix(".tmp.pdf")

    html_backup = backup_if_exists(html_out)
    pdf_backup = backup_if_exists(pdf_out)

    pages = 0
    max_retries = 5
    for attempt in range(max_retries):
        if html_tmp.exists():
            html_tmp.unlink()
        if pdf_tmp.exists():
            pdf_tmp.unlink()
            
        try:
            run_python(
                render_script,
                "--template",
                args.template,
                "--data",
                args.data,
                "--out",
                str(html_tmp),
            )
            run_python(
                pdf_script,
                "--html",
                str(html_tmp),
                "--pdf",
                str(pdf_tmp),
            )
            pages = count_pdf_pages(pdf_tmp)
            if pages <= args.max_pages:
                shutil.move(str(html_tmp), str(html_out))
                shutil.move(str(pdf_tmp), str(pdf_out))
                cleanup_backup(html_backup)
                cleanup_backup(pdf_backup)
                safe_print(f"PAGES: {pages} (Attempt {attempt+1})")
                safe_print(str(pdf_out))
                return 0
                
            safe_print(f"Attempt {attempt+1}: Pages {pages} > max {args.max_pages}. Trying to fallback and truncate...")
            if not truncate_data(Path(args.data)):
                break
        except Exception as e:
            safe_print(f"Render try {attempt+1} failed: {e}")
            break

    # If we get here, all attempts failed
    restore_backup(html_backup, html_out)
    restore_backup(pdf_backup, pdf_out)
    cleanup_backup(html_backup)
    cleanup_backup(pdf_backup)
    
    if html_tmp.exists():
        html_tmp.unlink()
    if pdf_tmp.exists():
        pdf_tmp.unlink()
        
    raise RuntimeError(f"Resume overflowed to {pages} pages even after fallback truncations; restored previous successful outputs.")


if __name__ == "__main__":
    raise SystemExit(main())
