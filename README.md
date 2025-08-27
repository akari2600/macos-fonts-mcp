# macos-fonts-mcp (v0.2)

**Simplified tool surface for LLM UX**

Tools:
- `list_families()`
- `faces_for_family({ "family": "..." })`
- `font_overview({ "postScriptName": "..." })`
- `publish_font({ "postScriptName": "...", "convert": { ... }, "publish": { ... } })`  ← one-step pipeline

`publish_font` does: resolve face → optional subsetting/instancing → WOFF2 → S3 upload → returns URL, CSS, sample HTML.

## Quickstart

```bash
uv venv
source .venv/bin/activate
uv pip install -e .[dev]  # or: pip install -e .[dev]
python server.py
```
