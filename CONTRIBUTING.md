# Contributing

## One PR, One Tool

Add a new tool in a single PR. Include:
- The tool handler in `server.py`
- An entry in `TOOLS` and `TOOL_HANDLERS`
- A test case in `tests/`

## Running locally

```bash
pip install -e .
SABNZBD_URL="http://localhost:8080" SABNZBD_API_KEY="your-key" python -m sabnzbd_mcp
```

## Before submitting

```bash
pip install ruff
ruff check src/
python -m pytest tests/
```
