# resume-jd-tailor (public skill)

This repo contains the resume tailoring pipeline (select experiences -> optional LLM rewrite -> render HTML -> export PDF).

## Privacy model

- This public repo ships only **example** data under `assets/data/**.example.*`.
- Put your real resume profile, experiences, and JD configs in `*.local.*` files and keep them untracked (see `.gitignore`).
- Never commit `.env` or generated `outputs/`.

## Quick run

```powershell
python .\scripts\run_latest.py `
  --lang zh `
  --experiences .\assets\data\experiences\experiences_zh.example.yaml `
  --base .\assets\data\profile\base_resume.example.json `
  --jd .\assets\data\jd\jd.example.yaml `
  --out-dir .\outputs\final `
  --prefix resume `
  --no-llm
```

English example data is available at `assets/data/experiences/experiences_en.example.yaml`.

If you want LLM rewriting:

- Text JD: pass `--jd-raw <path-to-text>` and configure `DEEPSEEK_API_KEY` in `.env`
- Image JD: pass `--jd-raw <path-to-image>` and configure Vertex AI credentials (ADC) plus `--vertex-project-id/--gemini-model` if needed
