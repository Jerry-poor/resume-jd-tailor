# Resume Generation Constitution

Version: `v2.0.0`  
Scope: `resume-jd-tailor` resume generation outputs (`json/html/pdf`)

## 1) Truthfulness
- All content must be traceable to user-provided facts or maintained experience library.
- No fabricated company, timeline, role, metric, or impact statement.

## 2) Pipeline Discipline
- Mandatory sequence: `build_json -> render_html -> export_pdf`.
- Parallel execution of dependent steps is forbidden.

## 3) Section Priority & Ordering
- Full-time work experience is the primary emphasis.
- Within the same section, items are ordered by start date descending by default.

## 4) Template Truth
- `assets/templates/template_html.html` is the single source of truth template.
- All content insertion must be represented as `{{TOKEN}}` placeholders in the HTML and filled from JSON.
- Placeholder aliasing is allowed only for space/underscore swap (e.g. `{{SECTION EDU}}` maps to `SECTION_EDU`).

## 5) Photo Rule
- Input JSON key: `PHOTO`.
- The renderer must embed the photo as a `data:` URI (self-contained HTML/PDF).
- Missing photo must not crash the build; it should render as blank.

## 6) Quality Gates Before Delivery
- No unresolved placeholders (`{{...}}`) in final HTML.
- Final PDF must exist and correspond to the latest HTML.
- PDF must not exceed 1 page (unless explicitly overridden by user).

## 7) Governance
- Any rule change requires updating this file and corresponding machine-readable constitution.
