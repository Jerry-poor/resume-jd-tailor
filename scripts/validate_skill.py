import re
import sys
from pathlib import Path


def parse_frontmatter_lines(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter ('---').")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("SKILL.md frontmatter must end with a second '---' line.")
    block = text[4:end]

    out: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid frontmatter line: {raw}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        out[key] = value
    return out


def validate(skill_dir: Path) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise ValueError("Missing SKILL.md")

    fm = parse_frontmatter_lines(skill_md.read_text(encoding="utf-8"))
    allowed = {"name", "description"}
    extra = set(fm.keys()) - allowed
    missing = allowed - set(fm.keys())
    if missing:
        raise ValueError(f"Missing frontmatter keys: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"Unexpected frontmatter keys: {', '.join(sorted(extra))}")

    name = fm["name"].strip()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError(f"Invalid skill name: {name!r} (must be hyphen-case)")

    if skill_dir.name != name:
        raise ValueError(f"Folder name must match skill name: folder={skill_dir.name!r}, name={name!r}")

    agents_yaml = skill_dir / "agents" / "openai.yaml"
    if not agents_yaml.exists():
        raise ValueError("Missing agents/openai.yaml")

    for d in ("scripts", "references", "assets"):
        if not (skill_dir / d).is_dir():
            raise ValueError(f"Missing directory: {d}/")


def main() -> int:
    skill_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    validate(skill_dir)
    print("ok: skill structure looks valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
