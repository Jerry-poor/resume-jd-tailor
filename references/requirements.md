# Requirements & troubleshooting

## Python

- Python 3.10+ recommended.
- Dependencies:
  - `PyYAML` (for `scripts/build_resume_data.py`)
  - `python-dotenv` (optional, to load the workspace root `.env` automatically)

If missing, install (example):

```powershell
python -m pip install pyyaml python-dotenv
```

## Optional LLM rewrite

`scripts/build_resume_data.py` checks for a `.env` by walking upward from the script location and loads the first one it finds (normally the project root `.env`).

Supported environment variables:

- `DEEPSEEK_API_KEY`: enables LLM rewriting of selected bullets
- `DEEPSEEK_API_BASE`: override the compatible chat completions endpoint base URL
- `DEEPSEEK_MODEL`: override the model name
- `RESUME_LLM_MAX_WORKERS`: cap concurrent bullet rewrite requests (default `6`)

If `DEEPSEEK_API_KEY` is unset, the script falls back to deterministic keyword ranking only and skips the rewrite pass.

## Optional Gemini PDF visual audit

Use `uv run --with google-genai --with python-dotenv` to execute `scripts/audit_resume_pdf_style.py`.

Requirements:

- A working Google Cloud Application Default Credentials setup on the machine
- Access to Vertex AI in the target project
- Explicit runtime parameters for:
  - `--vertex-project-id`
  - `--vertex-location`
  - `--model`

The audit script sends the generated PDF to Gemini as `application/pdf` and asks for a structured review of whitespace balance, overlap/cropping, alignment, typography consistency, photo safety, and print readiness.

## Browser PDF export

`scripts/html_to_pdf.py` and `scripts/build_resume_html_pdf.py` expect one of these browsers:

- Microsoft Edge
- Google Chrome

The script first checks standard Windows install paths, then falls back to PATH lookup.

## One-page limit

`scripts/build_resume_html_pdf.py` enforces a max page count (default `--max-pages 1`).
If the exported PDF exceeds the limit, the script restores the previous successful `--html-out` and `--pdf-out` files and exits with an error.
