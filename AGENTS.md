# Agent Instructions for sabnzbd-mcp

This is a zero-dependency Python MCP server that wraps the SABnzbd API.

## Env vars
- `SABNZBD_URL` — base URL of the SABnzbd instance (e.g. http://localhost:8080)
- `SABNZBD_API_KEY` — API key from SABnzbd settings

## Tools

| Tool | When to use |
|---|---|
| `sab_queue` | User asks about current downloads, speed, progress |
| `sab_history` | User asks what finished or failed |
| `sab_status` | User asks about server health, disk space, config |
| `sab_pause` / `sab_resume` | User wants to stop/start downloads |
| `sab_add_url` | User provides an NZB URL or magnet to download |
| `sab_categories` | User asks what categories exist for sorting |

## Architecture

```
Agent ←→ sabnzbd-mcp (stdio, JSON-RPC 2.0) ←→ SABnzbd HTTP API
```

The server is a single file (`src/sabnzbd_mcp/server.py`) with no dependencies.
