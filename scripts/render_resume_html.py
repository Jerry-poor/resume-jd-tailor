import argparse
import base64
import html
import json
import re
from pathlib import Path
from typing import Any

from console import safe_print
from resume_semantic import flatten_semantic_resume, is_semantic_resume

TOKEN_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("resume json must be an object")
    return data


def resolve_photo(data_path: Path, photo_value: str | None) -> Path | None:
    if not photo_value:
        return None
    raw = Path(str(photo_value))
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append((data_path.parent / raw).resolve())
        candidates.append(raw.resolve())
        candidates.append((data_path.parent.parent / raw.name).resolve())
        candidates.append((Path(__file__).resolve().parent.parent / "assets" / raw.name).resolve())
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def file_to_data_uri(path: Path | None) -> str:
    if path is None:
        return ""
    suffix = path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(v) for v in value if str(v).strip())
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def esc(value: Any) -> str:
    return html.escape(stringify(value), quote=True)


def lookup_token(data: dict[str, Any], token: str) -> Any:
    if token in data:
        return data[token]
    if " " in token:
        alt = token.replace(" ", "_")
        if alt in data:
            return data[alt]
    if "_" in token:
        alt = token.replace("_", " ")
        if alt in data:
            return data[alt]
    return ""


def render_template(template: str, data: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        token = match.group(1).strip()
        return esc(lookup_token(data, token))

    return TOKEN_RE.sub(repl, template)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a resume HTML from JSON using {{TOKEN}} placeholders")
    default_template = Path(__file__).resolve().parents[1] / "assets" / "templates" / "template_html.html"
    ap.add_argument("--template", default=str(default_template), help="Path to HTML template")
    ap.add_argument("--data", required=True, help="Path to resume JSON")
    ap.add_argument("--out", required=True, help="Output HTML path")
    args = ap.parse_args()

    template_path = Path(args.template)
    data_path = Path(args.data)
    out_path = Path(args.out)

    template = template_path.read_text(encoding="utf-8")
    data = load_json(data_path)
    if is_semantic_resume(data):
        data = flatten_semantic_resume(data)

    photo_value = str(data.get("PHOTO", "")).strip() or None
    photo_path = resolve_photo(data_path, photo_value)
    if photo_value and photo_path is None:
        safe_print(f"warn: PHOTO file not found, leaving blank: {photo_value}")
    data["PHOTO"] = file_to_data_uri(photo_path)

    rendered = render_template(template, data)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    safe_print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
