# sabnzbd-mcp — Copilot Instructions

Zero-dependency Python MCP server for SABnzbd Usenet downloads. Published on PyPI.

## Quick Commands

```bash
pip install -e ".[dev]"   # Development install
ruff check src/            # Lint
python -m pytest tests/    # Run tests
uv run sabnzbd-mcp         # Run MCP server
```

## Key Paths

- `src/sabnzbd_mcp/server.py` — Single-file MCP server (stdlib only)
- `tests/` — pytest test suite
- `Dockerfile` + `docker-compose.yml` — Containerized deployment

## Conventions

- **Runtime:** Python 3.10+
- **Package manager:** uv
- **Linter:** Ruff
- **Tests:** pytest
- **CI:** GitHub Actions (ci.yml, publish.yml)
- **Commit style:** Conventional Commits

## Pre-Commit Rule

```bash
ruff check src/ && python -m pytest tests/   # Run before pushing.
```
