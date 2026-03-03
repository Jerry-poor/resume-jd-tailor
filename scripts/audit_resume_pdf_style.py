import argparse
import json
from pathlib import Path
from typing import Any

from console import safe_print

CHECKLIST: list[dict[str, str]] = [
    {
        "id": "page_usage",
        "name": "Page Usage and Whitespace Balance",
        "focus": "Check whether the single page is used efficiently, with balanced top/bottom margins, no awkward empty blocks, and no section that looks visually starved or overcrowded.",
    },
    {
        "id": "section_spacing",
        "name": "Section Separation and Vertical Rhythm",
        "focus": "Check whether spacing between section titles, content blocks, and bullet groups is consistent, with no sudden gaps or compressed areas that break reading flow.",
    },
    {
        "id": "alignment",
        "name": "Block Alignment and Edge Consistency",
        "focus": "Check whether major modules share stable left and right visual edges, and whether titles, labels, bullets, and metadata align cleanly without drifting.",
    },
    {
        "id": "overlap",
        "name": "Occlusion, Overlap, and Cropping",
        "focus": "Check whether any text, photo, divider, or container overlaps another element, gets clipped, or touches the page edge in a visually unsafe way.",
    },
    {
        "id": "bullet_layout",
        "name": "Bullet Layout and Text Wrapping",
        "focus": "Check bullet indentation, hanging alignment, line wrapping, and line-length consistency so bullets read as one system rather than uneven fragments.",
    },
    {
        "id": "typography",
        "name": "Typography Consistency",
        "focus": "Check whether font sizing, line height, weight, and emphasis hierarchy remain consistent across sections, especially for Chinese text mixed with English terms.",
    },
    {
        "id": "photo_module",
        "name": "Photo Placement and Visual Safety",
        "focus": "Check whether the headshot is proportionate, not stretched, not too dominant, and does not visually collide with nearby text or containers.",
    },
    {
        "id": "print_readiness",
        "name": "Print Readiness and Delivery Safety",
        "focus": "Check for anything that would make the PDF look broken when shared, such as faint clipping, hidden overflow, floating modules, or suspicious blank space.",
    },
]


def load_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                if key.strip():
                    # Keep existing process env values if already present.
                    import os

                    os.environ.setdefault(key.strip(), value.strip())


def build_prompt(pdf_name: str, checklist: list[dict[str, str]]) -> str:
    checklist_lines = "\n".join(
        f"- {item['id']} | {item['name']}: {item['focus']}" for item in checklist
    )
    return (
        "You are a strict visual QA reviewer for resume PDFs.\n"
        f"Review the attached PDF file named {pdf_name}.\n"
        "Focus only on visual layout and presentation quality, not on whether the career claims are accurate.\n"
        "Use the following checklist exactly as the review framework:\n"
        f"{checklist_lines}\n\n"
        "Instructions:\n"
        "1. Inspect the PDF visually and judge each checklist item.\n"
        "2. Be concrete. Cite the visible symptom and where it appears.\n"
        "3. If something cannot be determined confidently from the PDF, mark it as 'unknown' and explain why.\n"
        "4. Prefer strict design QA standards suitable for a job application resume.\n"
        "5. Pay special attention to blank space balance, visual obstruction, clipping, module drift, and alignment consistency.\n\n"
        "Return JSON only with this shape:\n"
        "{\n"
        '  "overall_status": "pass|needs_revision|fail",\n'
        '  "summary": "short overall assessment",\n'
        '  "checks": [\n'
        "    {\n"
        '      "id": "page_usage",\n'
        '      "name": "Page Usage and Whitespace Balance",\n'
        '      "status": "pass|minor_issue|major_issue|unknown",\n'
        '      "severity": "none|low|medium|high",\n'
        '      "evidence": "specific observation from the PDF",\n'
        '      "recommendation": "specific fix suggestion"\n'
        "    }\n"
        "  ],\n"
        '  "blocking_issues": ["issue 1", "issue 2"],\n'
        '  "ship_decision": "ship|ship_after_minor_fixes|revise_before_sending"\n'
        "}\n"
    )


def run_audit(
    pdf_path: Path,
    vertex_project_id: str,
    vertex_location: str,
    model: str,
) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True,
        project=vertex_project_id,
        location=vertex_location,
        http_options=types.HttpOptions(api_version="v1"),
    )

    prompt = build_prompt(pdf_path.name, CHECKLIST)
    pdf_part = types.Part.from_bytes(
        data=pdf_path.read_bytes(),
        mime_type="application/pdf",
    )
    response = client.models.generate_content(
        model=model,
        contents=[pdf_part, prompt],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    raw_text = (response.text or "").strip()
    if not raw_text:
        raise RuntimeError("Gemini returned an empty response.")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini response was not valid JSON: {raw_text}") from exc

    payload["_meta"] = {
        "vertexProjectId": vertex_project_id,
        "vertexLocation": vertex_location,
        "model": model,
        "pdf": str(pdf_path),
        "checklist": CHECKLIST,
    }
    return payload


def main() -> int:
    load_env()

    ap = argparse.ArgumentParser(description="Audit a resume PDF's visual quality with Gemini on Vertex AI")
    ap.add_argument("--pdf", required=True, help="Path to the PDF to audit")
    ap.add_argument("--vertex-project-id", required=True, help="Vertex AI project id")
    ap.add_argument("--vertex-location", required=True, help="Vertex AI location, e.g. global")
    ap.add_argument("--model", required=True, help="Model id, e.g. gemini-3-flash-preview")
    ap.add_argument("--out", required=False, help="Optional JSON output path")
    args = ap.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    result = run_audit(
        pdf_path=pdf_path,
        vertex_project_id=args.vertex_project_id,
        vertex_location=args.vertex_location,
        model=args.model,
    )

    if args.out:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        safe_print(str(out_path))
    else:
        safe_print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
