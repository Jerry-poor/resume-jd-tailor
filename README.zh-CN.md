# resume-jd-tailor

这是一个用于按职位描述定制简历的公开仓库技能。

本项目实现了一条简历生成流水线:

`经历库 + 基础资料 + JD 配置 -> (可选 LLM 改写) -> 语义 JSON -> token JSON -> HTML -> PDF`

设计目标是适合放在公开 GitHub 仓库中: 不跟踪任何个人真实简历内容。

## 1. 你需要准备什么

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

如果你要用 "JD 图片 -> Gemini（Vertex AI）改写 / PDF 视觉审计":

```powershell
uv sync --extra gemini
```

如果你不用 `uv`:

```powershell
python -m pip install google-genai
```

## 2. 隐私与文件组织（public 仓库强制要求）

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

## 3. 如何填写你的本地数据

1. 复制示例文件为本地文件:

```powershell
Copy-Item .\assets\data\profile\base_resume.example.json .\assets\data\profile\base_resume.local.json
Copy-Item .\assets\data\experiences\experiences_zh.example.yaml .\assets\data\experiences\experiences_zh.local.yaml
Copy-Item .\assets\data\jd\jd.example.yaml .\assets\data\jd\jd.local.yaml
```

2. 编辑 `base_resume.local.json`（个人信息与基础技能）:

- `NAME/PHONE/EMAIL/GITHUB/TITLE`
- `PHOTO`: 建议留空。若要放照片，请使用本地路径，且不要提交到 git。
- `experience_dates`: 填写每条经历 id 的日期范围（用于最终渲染）

可选链接字段（为空则不显示）:

- `CERT_1_URL`, `CERT_1_URL_LABEL`
- `RESEARCH_1_REPO`, `RESEARCH_1_REPO_URL`
- `RESEARCH_1_ARTICLE_URL`, `RESEARCH_1_ARTICLE_LABEL`

3. 编辑 `experiences_zh.local.yaml`（你的经历库）:

- 每条经历包含 `id/type/company/title/priority/tags` 与 `zh` 或 `en` 的 bullet 列表
- 生成时会根据 `jd.local.yaml` 的 `target_tags/must_keywords` 选择最匹配的经历

4. 编辑 `jd.local.yaml`（目标岗位配置）:

- `target_title`: 目标岗位名
- `target_tags`: 用于匹配经历（建议用小写、短标签）
- `must_keywords`: 用于 bullet 关键词贴合与排序
- `work_bullet_count`, `research_bullet_count`: 控制信息密度

## 4. 可选 LLM 改写与路由规则

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

## 5. 一键运行（推荐）

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

## 6. 会实现什么功能

- 从经历库中自动选择:
  - 1 段工作经历（非实习）
  - 最多 2 段实习经历
  - 1 段科研经历
- 将 bullet 与 JD 关键词对齐（可选 LLM 改写，且要求不虚构事实）
- 渲染到 HTML 并导出 1 页 PDF
- 输出目录只保留 latest，并将历史 `resume*` 归档到 `archive/`

## 7. 会生成哪些文件

默认输出到 `outputs/final/`（`--prefix resume` 时）:

- `resume.pdf`（最终简历）
- `resume.html`（最终 HTML）
- `resume.zh.jd.json`（扁平 token JSON，模板渲染输入）
- `resume.semantic.json`（语义 JSON，便于调试/审阅）
- `archive/<timestamp>/...`（历史归档）
