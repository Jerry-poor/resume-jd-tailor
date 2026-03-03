# resume-jd-tailor (public skill)

This repo implements a resume pipeline:

`experience library + base profile + JD config -> (optional LLM rewrite) -> semantic JSON -> token JSON -> HTML -> PDF`

It is designed to be safe for a **public GitHub repo**: no personal resume content is tracked.

## 中文说明

### 1. 你需要准备什么

运行环境:

- Python 3.10+（建议）
- Windows 上安装 Microsoft Edge 或 Google Chrome（用于 HTML 转 PDF）

安装依赖（推荐用 `uv`）:

```powershell
uv sync
```

安装依赖（不使用 `uv`，最小可运行）:

```powershell
python -m pip install pyyaml python-dotenv
```

如果你要用 “JD 图片 -> Gemini（Vertex AI）改写 / PDF 视觉审计”:

```powershell
uv sync --extra gemini
```

如果你不用 `uv`:

```powershell
python -m pip install google-genai
```

### 2. 隐私与文件组织（public 仓库强制要求）

本仓库只跟踪示例数据:

- `assets/data/**.example.*`

你的真实数据必须放在本地文件（不会被 git 跟踪）:

- `assets/data/profile/base_resume.local.json`
- `assets/data/experiences/experiences_zh.local.yaml` 或 `experiences_en.local.yaml`
- `assets/data/jd/jd.local.yaml`

敏感文件永远不要提交:

- `.env`
- `outputs/`
- `*.pdf/*.docx`
- 任何头像/照片文件

这些规则已在 `.gitignore` 中实现。

### 3. 如何填写你的本地数据

1) 复制示例文件为本地文件:

```powershell
Copy-Item .\assets\data\profile\base_resume.example.json .\assets\data\profile\base_resume.local.json
Copy-Item .\assets\data\experiences\experiences_zh.example.yaml .\assets\data\experiences\experiences_zh.local.yaml
Copy-Item .\assets\data\jd\jd.example.yaml .\assets\data\jd\jd.local.yaml
```

2) 编辑 `base_resume.local.json`（个人信息与基础技能）:

- `NAME/PHONE/EMAIL/GITHUB/TITLE`
- `PHOTO`: 建议留空。若要放照片，请使用本地路径，且不要提交到 git。
- `experience_dates`: 填写每条经历 id 的日期范围（用于最终渲染）

可选链接字段（为空则不显示）:

- `CERT_1_URL`, `CERT_1_URL_LABEL`
- `RESEARCH_1_REPO`, `RESEARCH_1_REPO_URL`
- `RESEARCH_1_ARTICLE_URL`, `RESEARCH_1_ARTICLE_LABEL`

3) 编辑 `experiences_zh.local.yaml`（你的经历库）:

- 每条经历包含 `id/type/company/title/priority/tags` 与 `zh` 或 `en` 的 bullet 列表
- 生成时会根据 `jd.local.yaml` 的 `target_tags/must_keywords` 选择最匹配的经历

4) 编辑 `jd.local.yaml`（目标岗位配置）:

- `target_title`: 目标岗位名
- `target_tags`: 用于匹配经历（建议用小写、短标签）
- `must_keywords`: 用于 bullet 关键词贴合与排序
- `work_bullet_count`, `research_bullet_count`: 控制信息密度

### 4. 可选 LLM 改写与路由规则

默认开启 LLM 改写。你可以用 `--no-llm` 关闭。

LLM 路由规则（由 `--jd-raw` 决定）:

- `--jd-raw` 是图片（`.png/.jpg/.jpeg/.webp`）: 使用 Gemini（Vertex AI）改写
- `--jd-raw` 是文本文件（`.txt/.md`）: 使用 DeepSeek 改写
- 不传 `--jd-raw`: 只使用 `jd.local.yaml` 的关键词做确定性选择与排序（不额外读取 JD 原文）

DeepSeek 配置（文本 JD）:

- 在项目根目录创建 `.env`（不要提交）
- 只需要 `DEEPSEEK_API_KEY` 就能启用改写

示例 `.env`:

```ini
DEEPSEEK_API_KEY=your_key
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
RESUME_LLM_MAX_WORKERS=6
```

Gemini 配置（图片 JD，走 Vertex AI）:

- 需要 Google Cloud 的 Application Default Credentials（ADC）
- 需要在目标 Project 开通 Vertex AI 权限
- 运行时通过参数传入:
  - `--vertex-project-id`
  - `--vertex-location`（默认 `global`）
  - `--gemini-model`（默认 `gemini-3-flash-preview`）

### 5. 一键运行（推荐）

不使用 LLM（纯确定性）:

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

使用 DeepSeek（文本 JD）:

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

使用 Gemini（图片 JD，Vertex AI）:

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

### 6. 会实现什么功能

- 从经历库中自动选择:
  - 1 段工作经历（非实习）
  - 最多 2 段实习经历
  - 1 段科研经历
- 将 bullet 与 JD 关键词对齐（可选 LLM 改写，且要求不虚构事实）
- 渲染到 HTML 并导出 1 页 PDF
- 输出目录只保留 latest，并将历史 `resume*` 归档到 `archive/`

### 7. 会生成哪些文件

默认输出到 `outputs/final/`（`--prefix resume` 时）:

- `resume.pdf`（最终简历）
- `resume.html`（最终 HTML）
- `resume.zh.jd.json`（扁平 token JSON，模板渲染输入）
- `resume.semantic.json`（语义 JSON，便于调试/审阅）
- `archive/<timestamp>/...`（历史归档）

## English

### 1. Prerequisites

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

### 2. Privacy model (public repo)

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

### 3. Filling your local data

1) Copy examples into local files:

```powershell
Copy-Item .\assets\data\profile\base_resume.example.json .\assets\data\profile\base_resume.local.json
Copy-Item .\assets\data\experiences\experiences_zh.example.yaml .\assets\data\experiences\experiences_zh.local.yaml
Copy-Item .\assets\data\jd\jd.example.yaml .\assets\data\jd\jd.local.yaml
```

2) Edit `base_resume.local.json`:

- `NAME/PHONE/EMAIL/GITHUB/TITLE`
- `PHOTO`: recommended to keep empty for public-friendly workflows
- `experience_dates`: date ranges for each experience id

Optional link fields (hidden when empty):

- `CERT_1_URL`, `CERT_1_URL_LABEL`
- `RESEARCH_1_REPO`, `RESEARCH_1_REPO_URL`
- `RESEARCH_1_ARTICLE_URL`, `RESEARCH_1_ARTICLE_LABEL`

3) Edit `experiences_*.local.yaml` (your experience library):

- each item has `id/type/company/title/priority/tags` and `zh` or `en` bullet groups
- generation picks best matches using `target_tags/must_keywords` from `jd.local.yaml`

4) Edit `jd.local.yaml` (target job config):

- `target_title`
- `target_tags`
- `must_keywords`
- `work_bullet_count`, `research_bullet_count`

### 4. Optional LLM rewriting and routing

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

### 5. One-command run (recommended)

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

### 6. What it does

- auto-selects:
  - 1 work experience (non-intern)
  - up to 2 internship experiences
  - 1 research experience
- optionally rewrites bullets toward the target JD (without inventing facts)
- renders HTML and exports a 1-page PDF
- keeps only the latest outputs and archives older `resume*` artifacts under `archive/`

### 7. Generated files

Default outputs under `outputs/final/` (when `--prefix resume`):

- `resume.pdf`
- `resume.html`
- `resume.zh.jd.json`
- `resume.semantic.json`
- `archive/<timestamp>/...`
