# resume-jd-tailor

This is a public skill repo for tailoring resumes to a target job description.

This repo implements a resume pipeline:

`experience library + base profile + JD config -> (optional LLM rewrite) -> semantic JSON -> token JSON -> HTML -> PDF`

It is designed to be safe for a public GitHub repo: no personal resume content is tracked.

## 1. Prerequisites

Runtime:

- Python 3.10+ recommended
- Microsoft Edge or Google Chrome on Windows (used for HTML -> PDF export)

Install deps (recommended with `uv`):

```powershell
uv sync
```

Install minimal deps (without `uv`):

```powershell
python -m pip install pyyaml python-dotenv
```

If you want "JD image -> Gemini (Vertex AI) rewrite / PDF visual audit":

```powershell
uv sync --extra gemini
```

Without `uv`:

```powershell
python -m pip install google-genai
```

## 2. Privacy model (public repo)

This repo tracks example data only:

- `assets/data/**.example.*`

Put your real data in local files (untracked by git):

- `assets/data/profile/base_resume.local.json`
- `assets/data/experiences/experiences_zh.local.yaml` or `experiences_en.local.yaml`
- `assets/data/jd/jd.local.yaml`

Never commit:

- `.env`
- `outputs/`
- `*.pdf/*.docx`
- any headshot/photo files

`.gitignore` already enforces these rules.

## 3. Filling your local data

1. Copy examples into local files:

```powershell
Copy-Item .\assets\data\profile\base_resume.example.json .\assets\data\profile\base_resume.local.json
Copy-Item .\assets\data\experiences\experiences_zh.example.yaml .\assets\data\experiences\experiences_zh.local.yaml
Copy-Item .\assets\data\jd\jd.example.yaml .\assets\data\jd\jd.local.yaml
```

2. Edit `base_resume.local.json`:

- `NAME/PHONE/EMAIL/GITHUB/TITLE`
- `PHOTO`: recommended to keep empty for public-friendly workflows
- `experience_dates`: date ranges for each experience id

Optional link fields (hidden when empty):

- `CERT_1_URL`, `CERT_1_URL_LABEL`
- `RESEARCH_1_REPO`, `RESEARCH_1_REPO_URL`
- `RESEARCH_1_ARTICLE_URL`, `RESEARCH_1_ARTICLE_LABEL`

3. Edit `experiences_*.local.yaml` (your experience library):

- each item has `id/type/company/title/priority/tags` and `zh` or `en` bullet groups
- generation picks best matches using `target_tags/must_keywords` from `jd.local.yaml`

4. Edit `jd.local.yaml` (target job config):

- `target_title`
- `target_tags`
- `must_keywords`
- `work_bullet_count`, `research_bullet_count`

## 4. Optional LLM rewriting and routing

LLM rewriting is enabled by default. Disable it with `--no-llm`.

Routing (decided by `--jd-raw`):

- image (`.png/.jpg/.jpeg/.webp`): Gemini on Vertex AI
- text (`.txt/.md`): DeepSeek chat completions
- no `--jd-raw`: deterministic keyword-driven selection only

DeepSeek config (text JD):

- create a repo-root `.env` (do not commit)
- only `DEEPSEEK_API_KEY` is required to enable rewriting

Example `.env`:

```ini
DEEPSEEK_API_KEY=your_key
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
RESUME_LLM_MAX_WORKERS=6
```

Gemini config (image JD via Vertex AI):

- requires Google Cloud ADC on your machine
- requires Vertex AI access in the target project
- pass runtime flags:
  - `--vertex-project-id`
  - `--vertex-location` (default `global`)
  - `--gemini-model` (default `gemini-3-flash-preview`)

## 5. One-command run (recommended)

Deterministic mode (no LLM):

```powershell
python .\scripts\run_latest.py `
  --lang zh `
  --experiences .\assets\data\experiences\experiences_zh.local.yaml `
  --base .\assets\data\profile\base_resume.local.json `
  --jd .\assets\data\jd\jd.local.yaml `
  --out-dir .\outputs\final `
  --prefix resume `
  --no-llm
```

DeepSeek rewrite (text JD):

```powershell
python .\scripts\run_latest.py `
  --lang zh `
  --experiences .\assets\data\experiences\experiences_zh.local.yaml `
  --base .\assets\data\profile\base_resume.local.json `
  --jd .\assets\data\jd\jd.local.yaml `
  --jd-raw .\your_jd.txt `
  --out-dir .\outputs\final `
  --prefix resume
```

Gemini rewrite (image JD via Vertex AI):

```powershell
python .\scripts\run_latest.py `
  --lang zh `
  --experiences .\assets\data\experiences\experiences_zh.local.yaml `
  --base .\assets\data\profile\base_resume.local.json `
  --jd .\assets\data\jd\jd.local.yaml `
  --jd-raw .\your_jd.png `
  --vertex-project-id YOUR_GCP_PROJECT_ID `
  --vertex-location global `
  --gemini-model gemini-3-flash-preview `
  --out-dir .\outputs\final `
  --prefix resume
```

## 6. What it does

- auto-selects:
  - 1 work experience (non-intern)
  - up to 2 internship experiences
  - 1 research experience
- optionally rewrites bullets toward the target JD (without inventing facts)
- renders HTML and exports a 1-page PDF
- keeps only the latest outputs and archives older `resume*` artifacts under `archive/`

## 7. Generated files

Default outputs under `outputs/final/` (when `--prefix resume`):

- `resume.pdf`
- `resume.html`
- `resume.zh.jd.json`
- `resume.semantic.json`
- `archive/<timestamp>/...`
