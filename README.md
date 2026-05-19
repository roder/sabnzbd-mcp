# SABnzbd MCP Server

[![CI](https://github.com/zz-plant/sabnzbd-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/zz-plant/sabnzbd-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![PyPI](https://img.shields.io/badge/PyPI-0.1.0-blue)](https://pypi.org/project/sabnzbd-mcp/)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-purple)](https://modelcontextprotocol.io/)

A [Model Context Protocol](https://modelcontextprotocol.io/) server for [SABnzbd](https://sabnzbd.org/) — zero external dependencies. Give any AI agent control over Usenet downloads.

```bash
pip install sabnzbd-mcp
export SABNZBD_URL="http://localhost:8080"
export SABNZBD_API_KEY="your-key"
sabnzbd-mcp
```

## Features

- **No dependencies** — pure Python standard library. One file, zero installs beyond the package itself.
- **7 tools** — queue, history, status, pause, resume, add NZB, list categories.
- **Any client** — Claude Desktop, Claude Code, Codex, OpenCode, Cursor, Windsurf, or any MCP host.
- **Minimal** — ~200 lines. Easy to audit, extend, or fork.

## Tools

| Tool | Description | Annotations |
|---|---|---|
| `sab_queue` | View the download queue — items, speed, progress | read-only |
| `sab_history` | Browse completed and failed downloads | read-only |
| `sab_status` | Server health — speed limits, disk space, directories | read-only |
| `sab_pause` | Pause all active downloads | mutating |
| `sab_resume` | Resume paused downloads | mutating |
| `sab_add_url` | Add an NZB by URL (optional category) | destructive |
| `sab_categories` | List configured categories | read-only |

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `SABNZBD_URL` | Yes | `http://localhost:8080` | Base URL of your SABnzbd instance |
| `SABNZBD_API_KEY` | Yes | — | API Key from Settings → General |

## Client Setup

<details>
<summary><b>Claude Desktop</b></summary>

```json
{
  "mcpServers": {
    "sabnzbd": {
      "command": "sabnzbd-mcp",
      "env": {
        "SABNZBD_URL": "http://localhost:8080",
        "SABNZBD_API_KEY": "your-api-key"
      }
    }
  }
}
```
</details>

<details>
<summary><b>Claude Code / Codex</b></summary>

```bash
claude mcp add sabnzbd -- sabnzbd-mcp \
  -e SABNZBD_URL="http://localhost:8080" \
  -e SABNZBD_API_KEY="your-api-key"
```
</details>

<details>
<summary><b>OpenCode</b></summary>

```json
"sabnzbd": {
  "type": "local",
  "command": ["sabnzbd-mcp"],
  "env": {
    "SABNZBD_URL": "http://localhost:8080",
    "SABNZBD_API_KEY": "your-api-key"
  },
  "enabled": true
}
```
</details>

<details>
<summary><b>Cursor</b></summary>

Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "sabnzbd": {
      "command": "sabnzbd-mcp",
      "env": {
        "SABNZBD_URL": "http://localhost:8080",
        "SABNZBD_API_KEY": "your-api-key"
      }
    }
  }
}
```
</details>

## Example Prompts

Once connected, your agent can respond to:

> *"What's downloading right now?"* → `sab_queue`

> *"Pause all downloads until tomorrow"* → `sab_pause`

> *"Add this NZB to the games category"* → `sab_add_url`

> *"Show me what finished yesterday"* → `sab_history`

> *"How much disk space is left on the server?"* → `sab_status`

## Automation Pipeline

Combine with other MCP servers for end-to-end media automation:

```
Prowlarr (mcparr) → search indexers
  → qBittorrent / SABnzbd → download
    → Retroarr / Sonarr → sort & import
      → RomM → scan library
```

See [`docs/recipes/`](docs/recipes/) for full pipeline examples.

## Architecture

```
┌──────────────┐    stdin/stdout     ┌──────────────┐    HTTP     ┌───────────┐
│  AI Agent    │ ◄─────────────────► │  sabnzbd-mcp │ ◄─────────► │ SABnzbd   │
│  (Claude,    │    JSON-RPC 2.0     │  (Python)    │             │ (your     │
│   Codex...)  │                     │  stdlib only │             │  server)  │
└──────────────┘                     └──────────────┘             └───────────┘
```

The server is a single self-contained Python file ([`src/sabnzbd_mcp/server.py`](src/sabnzbd_mcp/server.py)) with no dependencies beyond the standard library. It communicates over stdio using line-delimited JSON-RPC 2.0 — no Content-Length framing required.

## Development

```bash
git clone https://github.com/zz-plant/sabnzbd-mcp.git
cd sabnzbd-mcp
pip install -e ".[dev]"
ruff check src/
python -m pytest tests/
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). One PR per tool. Tests required.

## License

MIT
