# sabnzbd-mcp — Agent Instructions

Zero-dependency Python MCP server that wraps the SABnzbd Usenet download API into 16 agent-accessible tools.

## Quick Start

```bash
pip install sabnzbd-mcp
export SABNZBD_URL="http://localhost:8080"
export SABNZBD_API_KEY="your-key"
sabnzbd-mcp
```

Or via uv:
```bash
uv sync
uv run sabnzbd-mcp
```

## Repository Structure

- `src/sabnzbd_mcp/server.py` — Single-file MCP server (stdlib only, zero deps)
- `tests/` — pytest test suite
- `Dockerfile` + `docker-compose.yml` — Containerized deployment
- `pyproject.toml` — Project config (uv-managed)

## Env Vars

- `SABNZBD_URL` — Base URL of the SABnzbd instance (e.g. http://localhost:8080)
- `SABNZBD_API_KEY` — API key from SABnzbd settings
- `SABNZBD_SSL_VERIFY` — Set to `false` for self-signed certs (default: `true`)
- `SABNZBD_POLL_INTERVAL` — Seconds between background polling (default: `15`)

## Tools

| Tool | When to use |
|---|---|
| `sab_queue` | User asks about current downloads, speed, progress |
| `sab_history` | User asks what finished or failed |
| `sab_status` | User asks about server health, disk space, config |
| `sab_categories` | User asks what categories exist for sorting |
| `sab_get_config` | User asks about server configuration |
| `sab_pause` / `sab_resume` | User wants to stop/start downloads |
| `sab_set_speedlimit` | User wants to throttle or unlimit downloads |
| `sab_add_url` | User provides an NZB URL to download |
| `sab_add_nzb_file` | User provides NZB content as text (encode to base64 first) |
| `sab_queue_delete` | User wants to remove a specific download |
| `sab_change_priority` | User wants a download to go faster/slower |
| `sab_set_category` | User wants to change the category of a queued item |
| `sab_change_position` | User wants to reorder/change position of a queued item |
| `sab_retry` | User wants to retry a failed download |
| `sab_history_delete` | User wants to clean up history |

## Architecture

```
Agent ←→ sabnzbd-mcp (stdio, JSON-RPC 2.0) ←→ SABnzbd HTTP API
```

The server is a single file (`src/sabnzbd_mcp/server.py`) with no dependencies beyond the Python standard library.

## Verification

```bash
ruff check src/
python -m pytest tests/
```

## CI

- `ci.yml` — Run lint + tests on push/PR
- `publish.yml` — Build and publish to PyPI
