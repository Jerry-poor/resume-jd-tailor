import argparse
import concurrent.futures
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from console import safe_print
from resume_semantic import (
    SECTION_LAYOUT_RULES,
    add_experience_plan_to_semantic,
    base_resume_to_semantic,
    fit_bullets_to_layout,
    flatten_semantic_resume,
    normalize_bullet_text,
)

PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML object: {path}")
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid JSON object: {path}")
    return data


def score_experience(exp: dict[str, Any], target_tags: set[str]) -> int:
    tags = set(exp.get("tags") or [])
    priority = PRIORITY_WEIGHT.get(str(exp.get("priority", "")).lower(), 0)
    tag_hits = len(tags.intersection(target_tags))
    return priority * 5 + tag_hits * 3


def is_internship_experience(exp: dict[str, Any]) -> bool:
    title = str(exp.get("title", "")).lower()
    exp_id = str(exp.get("id", "")).lower()
    company = str(exp.get("company", "")).lower()
    return "intern" in title or "实习" in title or "intern" in exp_id or "intern" in company


def select_ranked(
    exps: list[dict[str, Any]],
    matcher: Any,
    target_tags: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    candidates = [e for e in exps if matcher(e)]
    ranked = sorted(candidates, key=lambda e: score_experience(e, target_tags), reverse=True)
    return ranked[:limit]


def rank_bullets(lang_block: dict[str, Any], keywords: list[str], max_count: int) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    sections = [
        (lang_block.get("core") or [], 3),
        (lang_block.get("optional") or [], 2),
        (lang_block.get("expandable") or [], 1),
    ]

    idx = 0
    for bullets, base in sections:
        for b in bullets:
            text = str(b)
            hit = sum(1 for k in keywords if k and k.lower() in text.lower())
            ranked.append((hit * 5 + base, -idx, text))
            idx += 1

    ranked.sort(reverse=True)
    picked = [t[2] for t in ranked[:max_count]]
    return picked


def find_env_file(start_path: Path) -> Path | None:
    current = start_path.resolve()
    if len(current.parents) >= 2:
        preferred = current.parents[1] / ".env"
        if preferred.exists():
            return preferred
    for base in (current, *current.parents):
        env_path = base / ".env"
        if env_path.exists():
            return env_path
    return None


def load_env() -> Path | None:
    env_path = find_env_file(Path(__file__).resolve().parent)
    if env_path is None:
        return None

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        with env_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                entry = line.strip()
                if entry and not entry.startswith("#") and "=" in entry:
                    key, val = entry.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())
    return env_path


def get_llm_max_workers(task_count: int) -> int:
    configured = os.environ.get("RESUME_LLM_MAX_WORKERS", "6")
    try:
        limit = int(configured)
    except ValueError:
        limit = 6
    return max(1, min(limit, task_count))


def build_job_info(jd_doc: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": jd_doc.get("name", ""),
        "title": jd_doc.get("target_title", out.get("TITLE", "")),
        "summary": jd_doc.get("summary", ""),
        "keywords": jd_doc.get("must_keywords") or [],
        "target_tags": jd_doc.get("target_tags") or [],
    }


def build_experience_plan(
    exp: dict[str, Any] | None,
    lang: str,
    prefix: str,
    section_kind: str,
    bullet_slots: int,
    keywords: list[str],
    dates_map: dict[str, str],
    requested_count: int | None = None,
) -> dict[str, Any] | None:
    if not exp:
        return None

    exp_id = str(exp.get("id", ""))
    organization = exp.get("organization") or exp.get("company", "")
    lang_block = exp.get(lang) or {}
    max_pick = int(SECTION_LAYOUT_RULES[section_kind]["max_count"])
    ranked_bullets = rank_bullets(lang_block, keywords, max_pick)
    fitted_bullets = fit_bullets_to_layout(ranked_bullets, section_kind, requested_count=requested_count)

    return {
        "prefix": prefix,
        "section_kind": section_kind,
        "organization": organization,
        "title": exp.get("title", ""),
        "dates": dates_map.get(exp_id, ""),
        "bullet_slots": bullet_slots,
        "bullets": fitted_bullets,
        "refined_bullets": [],
        "repo": exp.get("repo", ""),
        "repo_url": exp.get("repo_url", ""),
        "exp_context": {
            "type": exp.get("type", ""),
            "title": exp.get("title", ""),
            "organization": organization,
        },
    }


def build_llm_prompt(
    bullets: list[str],
    job_info: dict[str, Any],
    exp_context: dict[str, str],
    lang: str,
    jd_text: str | None,
) -> str:
    keywords_str = ", ".join(job_info.get("keywords", []))
    tags_str = ", ".join(job_info.get("target_tags", []))
    jd_summary = str(job_info.get("summary", "")).strip()
    exp_label = " / ".join(part for part in [exp_context.get("organization", ""), exp_context.get("title", "")] if part)
    source_payload = json.dumps({"bullets": bullets}, ensure_ascii=False)
    jd_full = (jd_text or "").strip()

    if lang == "en":
        lines: list[str] = [
            "You are a senior resume editor. Tailor the resume bullets to the target JD without inventing facts.",
            f"Target role: {job_info.get('title', '')}",
            f"JD summary: {jd_summary}",
            f"Priority keywords: {keywords_str}",
            f"Target tags: {tags_str}",
        ]
        if jd_full:
            lines.append(f"Full JD text: {jd_full}")
        lines += [
            f"Experience: {exp_label}",
            f"Source JSON: {source_payload}",
            "",
            "Rewrite the bullets so they stay truthful, highlight the most relevant skills, and align with the JD.",
            "Return JSON only in this shape:",
            '{"bullets":["bullet 1","bullet 2"]}',
            "Requirements:",
            "1. Keep the same number of bullets as the source JSON.",
            "2. Keep every bullet concise and resume-ready.",
            "3. Do not add facts not present in the source.",
            "4. Output JSON only, with no markdown fences.",
        ]
        return "\n".join(lines)

    lines = [
        "你是资深简历优化专家，需要根据目标 JD 微调已有经历，但不得虚构事实。",
        f"目标岗位：{job_info.get('title', '')}",
        f"JD 概述：{jd_summary}",
        f"岗位关键词：{keywords_str}",
        f"目标标签：{tags_str}",
    ]
    if jd_full:
        lines.append(f"JD 原文：{jd_full}")
    lines += [
        f"当前经历：{exp_label}",
        f"原始 JSON：{source_payload}",
        "",
        "请基于原始内容重写这些经历，并自然融入最相关的 JD 关键词。",
        "要求：",
        "1. 保持真实，只能重组和突出已有事实，不得添加未出现的项目、指标或职责。",
        "2. 保留与目标岗位最相关的技术动作或业务结果。",
        "3. 每条尽量精炼，适合简历表述。",
        "4. 严格输出 JSON，格式必须是 {\"bullets\": [\"...\", \"...\"]}。",
        "5. 返回的 bullets 数量必须与原始 JSON 一致。",
        "6. 不要输出 Markdown 代码块，不要输出任何解释。",
    ]
    return "\n".join(lines)


def strip_code_fences(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_llm_bullets_payload(content: str, fallback: list[str]) -> list[str]:
    candidate = strip_code_fences(content)
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = candidate[start : end + 1]

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return fallback

    bullets = payload.get("bullets") if isinstance(payload, dict) else None
    if not isinstance(bullets, list):
        return fallback

    cleaned = [normalize_bullet_text(item) for item in bullets if normalize_bullet_text(item)]
    if not cleaned:
        return fallback
    return cleaned


def refine_bullets_with_llm(
    bullets: list[str],
    job_info: dict[str, Any],
    exp_context: dict[str, str],
    lang: str,
    jd_text: str | None,
) -> list[str]:
    url = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    if url.endswith("/"):
        url = url[:-1]
    url_endpoint = f"{url}/chat/completions"
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    if not api_key:
        return bullets

    prompt = build_llm_prompt(bullets, job_info, exp_context, lang, jd_text=jd_text)

    data = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 500,
        }
    ).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    req = urllib.request.Request(url_endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = response.read()
            res_json = json.loads(res_body)
            content = res_json["choices"][0]["message"]["content"].strip()
            return parse_llm_bullets_payload(content, bullets)
    except Exception as e:
        safe_print(f"[Warning] LLM rewrite failed: {e}")
        return bullets


def refine_bullets_with_gemini(
    bullets: list[str],
    job_info: dict[str, Any],
    exp_context: dict[str, str],
    lang: str,
    jd_image: Path,
    vertex_project_id: str,
    vertex_location: str,
    model: str,
) -> list[str]:
    try:
        from google import genai
        from google.genai import types
    except Exception as e:
        safe_print(f"[Warning] Gemini SDK not available: {e}")
        return bullets

    if not jd_image.is_file():
        safe_print(f"[Warning] JD image not found: {jd_image}")
        return bullets

    exp_label = " / ".join(
        part for part in [exp_context.get("organization", ""), exp_context.get("title", "")] if part
    )
    keywords_str = ", ".join(job_info.get("keywords", []))
    tags_str = ", ".join(job_info.get("target_tags", []))
    jd_summary = str(job_info.get("summary", "")).strip()
    source_payload = json.dumps({"bullets": bullets}, ensure_ascii=False)

    if lang == "en":
        prompt = (
            "You are a senior resume editor.\n"
            "The attached image is the Job Description (JD).\n"
            "Rewrite the resume bullets to align with the JD without inventing facts.\n"
            f"Target role: {job_info.get('title', '')}\n"
            f"JD summary: {jd_summary}\n"
            f"Priority keywords: {keywords_str}\n"
            f"Target tags: {tags_str}\n"
            f"Experience: {exp_label}\n"
            f"Source JSON: {source_payload}\n\n"
            "Return JSON only: {\"bullets\": [\"...\", \"...\"]}\n"
            "Keep bullet count identical to the source JSON.\n"
            "Output JSON only (no markdown)."
        )
    else:
        prompt = (
            "你是资深简历优化专家。\n"
            "附件图片为目标 JD。\n"
            "请在不虚构事实前提下，将简历 bullets 改写为更贴合 JD 的表述。\n"
            f"目标岗位：{job_info.get('title', '')}\n"
            f"JD 概述：{jd_summary}\n"
            f"岗位关键词：{keywords_str}\n"
            f"目标标签：{tags_str}\n"
            f"当前经历：{exp_label}\n"
            f"原始 JSON：{source_payload}\n\n"
            "返回格式必须为 JSON：{\"bullets\": [\"...\", \"...\"]}\n"
            "bullets 数量必须与原始 JSON 一致。\n"
            "只输出 JSON，不要解释，不要 Markdown。"
        )

    try:
        client = genai.Client(
            vertexai=True,
            project=vertex_project_id,
            location=vertex_location,
            http_options=types.HttpOptions(api_version="v1"),
        )
        suffix = jd_image.suffix.lower()
        mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(suffix, "application/octet-stream")
        jd_part = types.Part.from_bytes(data=jd_image.read_bytes(), mime_type=mime)
        response = client.models.generate_content(
            model=model,
            contents=[jd_part, prompt],
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        raw_text = (response.text or "").strip()
        if not raw_text:
            return bullets
        return parse_llm_bullets_payload(raw_text, bullets)
    except Exception as e:
        safe_print(f"[Warning] Gemini rewrite failed: {e}")
        return bullets


def refine_experience_plans_concurrently(
    plans: list[dict[str, Any]],
    job_info: dict[str, Any],
    lang: str,
    enable_llm: bool,
    jd_text: str | None,
    jd_image: Path | None,
    vertex_project_id: str,
    vertex_location: str,
    gemini_model: str,
) -> None:
    tasks: list[dict[str, Any]] = []
    for plan in plans:
        bullets = plan.get("bullets") or []
        plan["refined_bullets"] = list(bullets)
        if bullets:
            tasks.append(plan)

    if not enable_llm:
        return
    if not tasks:
        return

    use_gemini = bool(jd_image)
    use_deepseek = not use_gemini
    if use_deepseek and not os.environ.get("DEEPSEEK_API_KEY", ""):
        return

    max_workers = get_llm_max_workers(len(tasks))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                refine_bullets_with_gemini if use_gemini else refine_bullets_with_llm,
                list(plan.get("bullets") or []),
                job_info,
                plan["exp_context"],
                lang,
                *(
                    (
                        jd_image or Path(),
                        vertex_project_id,
                        vertex_location,
                        gemini_model,
                    )
                    if use_gemini
                    else (jd_text,)
                ),
            ): plan
            for plan in tasks
        }
        for future in concurrent.futures.as_completed(future_map):
            plan = future_map[future]
            plan["refined_bullets"] = future.result()

    for plan in plans:
        desired_count = len(plan.get("bullets") or [])
        plan["refined_bullets"] = fit_bullets_to_layout(
            plan.get("refined_bullets") or [],
            str(plan["section_kind"]),
            requested_count=desired_count,
        )


def main() -> int:
    load_env()
    ap = argparse.ArgumentParser(description="Build JD-specific resume JSON from experience library")
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--experiences", required=True, help="Path to experiences_*.yaml")
    ap.add_argument("--base", required=True, help="Path to base profile JSON")
    ap.add_argument("--jd", required=True, help="Path to JD profile yaml")
    ap.add_argument("--jd-raw", default=None, help="Optional raw JD file path (.txt/.md or image). If image, uses Gemini; if text, uses DeepSeek.")
    ap.add_argument("--out", required=True, help="Output resume JSON")
    ap.add_argument("--semantic-out", required=False, help="Optional semantic resume JSON output")
    ap.add_argument("--no-llm", action="store_true", help="Disable LLM rewrite pass (default: enabled)")
    ap.add_argument("--vertex-project-id", default="gen-lang-client-0259616768", help="Vertex AI project id for Gemini (JD image mode)")
    ap.add_argument("--vertex-location", default="global", help="Vertex AI location for Gemini (JD image mode)")
    ap.add_argument("--gemini-model", default="gemini-3-flash-preview", help="Gemini model id (JD image mode)")
    args = ap.parse_args()

    experiences_doc = load_yaml(Path(args.experiences))
    jd_doc = load_yaml(Path(args.jd))
    base_resume = load_json(Path(args.base))

    experiences = experiences_doc.get("experiences") or []
    if not isinstance(experiences, list):
        raise ValueError("experiences must be a list")

    target_tags = set(jd_doc.get("target_tags") or [])
    dates_map = (base_resume.get("experience_dates") or {}).get(args.lang, {})
    work_bullet_count = int(jd_doc.get("work_bullet_count", 4) or 4)
    research_bullet_count = int(jd_doc.get("research_bullet_count", 4) or 4)

    work_matches = select_ranked(
        experiences,
        lambda exp: exp.get("type") == "work" and not is_internship_experience(exp),
        target_tags,
        limit=1,
    )
    internship_matches = select_ranked(
        experiences,
        lambda exp: exp.get("type") == "work" and is_internship_experience(exp),
        target_tags,
        limit=2,
    )
    research_matches = select_ranked(
        experiences,
        lambda exp: exp.get("type") == "research",
        target_tags,
        limit=1,
    )

    work = work_matches[0] if work_matches else None
    research = research_matches[0] if research_matches else None
    job_info = build_job_info(jd_doc, base_resume)

    jd_text: str | None = None
    jd_image: Path | None = None
    if args.jd_raw:
        raw_path = Path(args.jd_raw).resolve()
        if raw_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            jd_image = raw_path
        else:
            try:
                jd_text = raw_path.read_text(encoding="utf-8")
            except OSError:
                jd_text = raw_path.read_text(encoding="utf-8", errors="replace")

    plans = [
        build_experience_plan(
            work,
            args.lang,
            "WORK_1",
            "work",
            5,
            job_info["keywords"],
            dates_map,
            requested_count=work_bullet_count,
        ),
        build_experience_plan(
            research,
            args.lang,
            "RESEARCH_1",
            "research",
            5,
            job_info["keywords"],
            dates_map,
            requested_count=research_bullet_count,
        ),
        build_experience_plan(
            internship_matches[0] if len(internship_matches) >= 1 else None,
            args.lang,
            "INTERN_1",
            "internship",
            1,
            job_info["keywords"],
            dates_map,
        ),
        build_experience_plan(
            internship_matches[1] if len(internship_matches) >= 2 else None,
            args.lang,
            "INTERN_2",
            "internship",
            1,
            job_info["keywords"],
            dates_map,
        ),
    ]
    plans = [plan for plan in plans if plan is not None]

    refine_experience_plans_concurrently(
        plans,
        job_info,
        args.lang,
        enable_llm=not bool(args.no_llm),
        jd_text=jd_text,
        jd_image=jd_image,
        vertex_project_id=str(args.vertex_project_id),
        vertex_location=str(args.vertex_location),
        gemini_model=str(args.gemini_model),
    )

    semantic_resume = base_resume_to_semantic(base_resume, args.lang, job_info)
    for plan in plans:
        add_experience_plan_to_semantic(semantic_resume, plan)

    if args.semantic_out:
        semantic_path = Path(args.semantic_out)
        semantic_path.parent.mkdir(parents=True, exist_ok=True)
        semantic_path.write_text(json.dumps(semantic_resume, ensure_ascii=False, indent=2), encoding="utf-8")
        safe_print(str(semantic_path))

    out = flatten_semantic_resume(semantic_resume, lang=args.lang)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    safe_print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
