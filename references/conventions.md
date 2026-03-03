# Conventions

## Data inputs

- Experience library: `assets/data/experiences/experiences_*.yaml`
  - Each experience has: `id`, `type` (`work`/`research`), `tags`, `priority`, and language blocks (`zh`/`en`) with bullet lists.
- JD profile: `assets/data/jd/*.yaml`
  - `target_tags`: choose best-matching experiences
  - `must_keywords`: keyword scoring for bullets
  - `target_title`: overrides `TITLE` in the output JSON
  - `summary`: optional extra summary text
- Base profile: `assets/data/profile/base_resume*.json`
  - Holds stable personal info and `experience_dates` mapping (removed from final output JSON by the builder).

## HTML template placeholders

- Use `{{TOKEN}}` placeholders in `assets/templates/template_html.html`.
- Tokens are filled from the generated resume JSON (output of `scripts/build_resume_data.py`).
- Token aliasing: the renderer treats spaces/underscores as aliases:
  - `{{SECTION EDU}}` can read `SECTION_EDU` from JSON (and vice versa).
- Photo handling:
  - Input JSON key is `PHOTO` (path or empty string).
  - The renderer embeds it as a `data:` URI so the exported PDF is self-contained.
