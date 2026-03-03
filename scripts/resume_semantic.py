from typing import Any


SECTION_LAYOUT_RULES = {
    "work": {
        "min_count": 3,
        "max_count": 5,
        "default_count": 4,
        "line_units": 62.0,
        "prefix_units": 4.0,
        "section_units": 340.0,
    },
    "research": {
        "min_count": 3,
        "max_count": 5,
        "default_count": 4,
        "line_units": 62.0,
        "prefix_units": 4.0,
        "section_units": 350.0,
    },
    "internship": {
        "min_count": 1,
        "max_count": 1,
        "default_count": 1,
        "line_units": 92.0,
        "prefix_units": 0.0,
        "section_units": 92.0,
    },
}

SECTION_LABELS = {
    "zh": {
        "SECTION_EDU": "教育经历",
        "SECTION_CERT": "职业认证",
        "SECTION_RESEARCH": "科研经历",
        "SECTION_WORK": "工作经历",
        "SECTION_INTERN": "实习经历",
        "SECTION_SKILLS": "职业技能",
    },
    "en": {
        "SECTION_EDU": "Education",
        "SECTION_CERT": "Certifications",
        "SECTION_RESEARCH": "Research",
        "SECTION_WORK": "Work Experience",
        "SECTION_INTERN": "Internships",
        "SECTION_SKILLS": "Skills",
    },
}


def normalize_bullet_text(text: str) -> str:
    return " ".join(str(text).split())


def measure_text_units(text: str) -> float:
    units = 0.0
    for char in text:
        if char.isspace():
            units += 0.35
        elif ord(char) < 128:
            units += 0.55
        else:
            units += 1.0
    return units


def truncate_to_unit_limit(text: str, limit: float) -> str:
    normalized = normalize_bullet_text(text)
    if not normalized or measure_text_units(normalized) <= limit:
        return normalized

    best_clause = ""
    best_units = 0.0
    for idx, char in enumerate(normalized):
        if char not in "，,；;：:、":
            continue
        candidate = normalized[:idx].rstrip(" ,;:，；：、")
        candidate_units = measure_text_units(candidate)
        if candidate and candidate_units <= limit and candidate_units > best_units:
            best_clause = candidate
            best_units = candidate_units

    if best_clause:
        return best_clause

    pieces: list[str] = []
    units = 0.0
    for char in normalized:
        char_units = measure_text_units(char)
        if units + char_units > limit:
            break
        pieces.append(char)
        units += char_units

    trimmed = "".join(pieces).rstrip(" ,;:，；：、")
    return trimmed or normalized[:1]


def resolve_requested_count(requested_count: int | None, section_kind: str) -> int:
    rule = SECTION_LAYOUT_RULES[section_kind]
    raw_value = requested_count if requested_count is not None else int(rule["default_count"])
    return max(int(rule["min_count"]), min(int(rule["max_count"]), int(raw_value)))


def fit_bullets_to_layout(
    bullets: list[str],
    section_kind: str,
    requested_count: int | None = None,
) -> list[str]:
    rule = SECTION_LAYOUT_RULES[section_kind]
    normalized = [normalize_bullet_text(bullet) for bullet in bullets if normalize_bullet_text(bullet)]
    if not normalized:
        return []

    kept = list(normalized)
    max_count = min(len(kept), int(rule["max_count"]))
    min_count = min(len(kept), int(rule["min_count"]))
    target_count = min(max_count, resolve_requested_count(requested_count, section_kind))
    count = max(min_count, target_count)

    while count > min_count:
        total_units = sum(measure_text_units(bullet) for bullet in kept[:count])
        if total_units <= float(rule["section_units"]):
            break
        count -= 1

    return kept[:count]


def is_semantic_resume(data: dict[str, Any]) -> bool:
    if not isinstance(data, dict):
        return False
    if not isinstance(data.get("profile"), dict):
        return False
    return any(key in data for key in ("education", "certifications", "work", "research", "internships", "skills"))


def base_resume_to_semantic(base: dict[str, Any], lang: str, job_info: dict[str, Any]) -> dict[str, Any]:
    return {
        "profile": {
            "name": str(base.get("NAME", "")),
            "gender": str(base.get("GENDER", "")),
            "age": str(base.get("AGE", "")),
            "phone": str(base.get("PHONE", "")),
            "email": str(base.get("EMAIL", "")),
            "github": str(base.get("GITHUB", "")),
            "title": str(job_info.get("title", base.get("TITLE", ""))),
            "photo": str(base.get("PHOTO", "")),
            "research_repo": str(base.get("RESEARCH_1_REPO", "")),
            "research_repo_url": str(base.get("RESEARCH_1_REPO_URL", "")),
            "cert_1_url": str(base.get("CERT_1_URL", "")),
            "cert_1_url_label": str(base.get("CERT_1_URL_LABEL", "")),
            "research_article_url": str(base.get("RESEARCH_1_ARTICLE_URL", "")),
            "research_article_label": str(base.get("RESEARCH_1_ARTICLE_LABEL", "")),
        },
        "education": [
            {
                "school": str(base.get("EDU_1_SCHOOL", "")),
                "dates": str(base.get("EDU_1_DATES", "")),
                "degree": str(base.get("EDU_1_DEGREE", "")),
            }
        ],
        "certifications": [
            {
                "organization": str(base.get("CERT_1_ORG", "")),
                "dates": str(base.get("CERT_1_DATES", "")),
                "title": str(base.get("CERT_1_TITLE", "")),
                "url": str(base.get("CERT_1_URL", "")),
                "url_label": str(base.get("CERT_1_URL_LABEL", "")),
            }
        ],
        "work": [],
        "research": [],
        "internships": [],
        "skills": [
            str(base.get("SKILLS_LLM", "")),
            str(base.get("SKILLS_RAG", "")),
            str(base.get("SKILLS_FULLSTACK", "")),
        ],
        "labels": dict(SECTION_LABELS[lang]),
        "jd_target_summary": str(job_info.get("summary", "")),
    }


def add_experience_plan_to_semantic(semantic: dict[str, Any], plan: dict[str, Any]) -> None:
    bullets = list(plan.get("refined_bullets") or plan.get("bullets") or [])
    section_kind = str(plan.get("section_kind", ""))

    if section_kind == "work":
        semantic.setdefault("work", []).append(
            {
                "company": str(plan.get("organization", "")),
                "title": str(plan.get("title", "")),
                "dates": str(plan.get("dates", "")),
                "bullets": bullets,
            }
        )
        return

    if section_kind == "research":
        profile = semantic.get("profile") or {}
        semantic.setdefault("research", []).append(
            {
                "organization": str(plan.get("organization", "")),
                "title": str(plan.get("title", "")),
                "dates": str(plan.get("dates", "")),
                "bullets": bullets,
                "repo": str(plan.get("repo") or profile.get("research_repo", "")),
                "repo_url": str(plan.get("repo_url") or profile.get("research_repo_url", "")),
                "article_url": str(profile.get("research_article_url", "")),
                "article_label": str(profile.get("research_article_label", "")),
            }
        )
        return

    if section_kind == "internship":
        semantic.setdefault("internships", []).append(
            {
                "company": str(plan.get("organization", "")),
                "title": str(plan.get("title", "")),
                "dates": str(plan.get("dates", "")),
                "bullets": bullets[:1],
            }
        )


def _seed_layout_defaults(out: dict[str, Any]) -> None:
    section_slots = {
        "WORK_1": 5,
        "RESEARCH_1": 5,
        "INTERN_1": 1,
        "INTERN_2": 1,
    }

    out["WORK_1_STYLE"] = "display:none;"
    out["RESEARCH_1_STYLE"] = "display:none;"
    out["INTERN_1_STYLE"] = "display:none;"
    out["INTERN_2_STYLE"] = "display:none;"
    out["INTERN_SECTION_STYLE"] = "display:none;"

    for prefix, slots in section_slots.items():
        for i in range(1, slots + 1):
            out[f"{prefix}_BULLET_{i}"] = ""
            out[f"{prefix}_BULLET_{i}_STYLE"] = "display:none;"


def _normalize_entry_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    entries = [entry for entry in raw if isinstance(entry, dict)]
    return entries


def _apply_experience_entry(
    out: dict[str, Any],
    entry: dict[str, Any] | None,
    prefix: str,
    section_kind: str,
    bullet_slots: int,
    org_key: str,
    org_field: str,
) -> None:
    entry = entry or {}
    raw_bullets = entry.get("bullets")
    if not isinstance(raw_bullets, list):
        summary = str(entry.get("summary", "")).strip()
        raw_bullets = [summary] if summary else []

    bullets = fit_bullets_to_layout(raw_bullets, section_kind, requested_count=len(raw_bullets))
    organization = str(entry.get(org_field, ""))
    title = str(entry.get("title", ""))
    dates = str(entry.get("dates", ""))
    has_content = bool(organization) and bool(title) and bool(bullets)

    out[org_key] = organization
    out[f"{prefix}_TITLE"] = title
    out[f"{prefix}_DATES"] = dates
    out[f"{prefix}_BULLETS"] = bullets
    out[f"{prefix}_STYLE"] = "" if has_content else "display:none;"

    for i in range(1, bullet_slots + 1):
        bullet_text = bullets[i - 1] if i <= len(bullets) else ""
        out[f"{prefix}_BULLET_{i}"] = bullet_text
        out[f"{prefix}_BULLET_{i}_STYLE"] = "" if bullet_text else "display:none;"


def flatten_semantic_resume(semantic: dict[str, Any], lang: str | None = None) -> dict[str, Any]:
    if not is_semantic_resume(semantic):
        raise ValueError("Input data is not a semantic resume document")

    out: dict[str, Any] = {}
    _seed_layout_defaults(out)

    labels = semantic.get("labels") if isinstance(semantic.get("labels"), dict) else {}
    resolved_lang = lang or ("en" if labels == SECTION_LABELS.get("en") else "zh")
    active_labels = dict(SECTION_LABELS.get(resolved_lang, SECTION_LABELS["zh"]))
    active_labels.update({k: str(v) for k, v in labels.items() if isinstance(k, str)})
    out.update(active_labels)

    profile = semantic.get("profile") or {}
    out["NAME"] = str(profile.get("name", ""))
    out["GENDER"] = str(profile.get("gender", ""))
    out["AGE"] = str(profile.get("age", ""))
    out["PHONE"] = str(profile.get("phone", ""))
    out["EMAIL"] = str(profile.get("email", ""))
    out["GITHUB"] = str(profile.get("github", ""))
    out["TITLE"] = str(profile.get("title", ""))
    out["PHOTO"] = str(profile.get("photo", ""))

    education = _normalize_entry_list(semantic.get("education"))
    edu = education[0] if education else {}
    out["EDU_1_SCHOOL"] = str(edu.get("school", ""))
    out["EDU_1_DATES"] = str(edu.get("dates", ""))
    out["EDU_1_DEGREE"] = str(edu.get("degree", ""))

    certifications = _normalize_entry_list(semantic.get("certifications"))
    cert = certifications[0] if certifications else {}
    out["CERT_1_ORG"] = str(cert.get("organization", ""))
    out["CERT_1_DATES"] = str(cert.get("dates", ""))
    out["CERT_1_TITLE"] = str(cert.get("title", ""))
    out["CERT_1_URL"] = str(cert.get("url", "")).strip()
    out["CERT_1_URL_LABEL"] = str(cert.get("url_label", "")).strip() or "链接"
    out["CERT_1_URL_STYLE"] = "" if out["CERT_1_URL"] else "display:none;"

    research_entries = _normalize_entry_list(semantic.get("research"))
    research = research_entries[0] if research_entries else {}
    out["RESEARCH_1_REPO"] = str(research.get("repo", ""))
    out["RESEARCH_1_REPO_URL"] = str(research.get("repo_url", ""))
    out["RESEARCH_1_REPO_STYLE"] = "" if out["RESEARCH_1_REPO"] and out["RESEARCH_1_REPO_URL"] else "display:none;"
    out["RESEARCH_1_ARTICLE_URL"] = str(research.get("article_url", "")).strip()
    out["RESEARCH_1_ARTICLE_LABEL"] = str(research.get("article_label", "")).strip() or "链接"
    out["RESEARCH_1_ARTICLE_STYLE"] = "" if out["RESEARCH_1_ARTICLE_URL"] else "display:none;"
    _apply_experience_entry(
        out,
        research,
        prefix="RESEARCH_1",
        section_kind="research",
        bullet_slots=5,
        org_key="RESEARCH_1_ORG",
        org_field="organization",
    )

    work_entries = _normalize_entry_list(semantic.get("work"))
    work = work_entries[0] if work_entries else {}
    _apply_experience_entry(
        out,
        work,
        prefix="WORK_1",
        section_kind="work",
        bullet_slots=5,
        org_key="WORK_1_COMPANY",
        org_field="company",
    )

    internship_entries = _normalize_entry_list(semantic.get("internships"))
    first_intern = internship_entries[0] if len(internship_entries) >= 1 else {}
    second_intern = internship_entries[1] if len(internship_entries) >= 2 else {}
    _apply_experience_entry(
        out,
        first_intern,
        prefix="INTERN_1",
        section_kind="internship",
        bullet_slots=1,
        org_key="INTERN_1_COMPANY",
        org_field="company",
    )
    _apply_experience_entry(
        out,
        second_intern,
        prefix="INTERN_2",
        section_kind="internship",
        bullet_slots=1,
        org_key="INTERN_2_COMPANY",
        org_field="company",
    )
    out["INTERN_SECTION_STYLE"] = (
        ""
        if out.get("INTERN_1_STYLE") != "display:none;" or out.get("INTERN_2_STYLE") != "display:none;"
        else "display:none;"
    )

    skills_raw = semantic.get("skills")
    skills = [str(item).strip() for item in skills_raw if str(item).strip()] if isinstance(skills_raw, list) else []
    while len(skills) < 3:
        skills.append("")
    out["SKILLS_LLM"] = skills[0]
    out["SKILLS_RAG"] = skills[1]
    out["SKILLS_FULLSTACK"] = skills[2]

    out["JD_TARGET_SUMMARY"] = str(semantic.get("jd_target_summary", ""))
    return out
