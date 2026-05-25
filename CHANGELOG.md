# Changelog

## 0.3.0 (2026-05-25)

- Added Resources capability: exposes `sabnzbd://queue`, `sabnzbd://history`, `sabnzbd://status`, `sabnzbd://categories`, and `sabnzbd://config` as live JSON resources.
- Added Prompt templates capability: `sabnzbd_summary` and `sabnzbd_download_nzb`.
- Enhanced MCP standard conformance: full JSON-RPC 2.0 error handling (Parse error, Invalid Request, Method not found, etc.) and aligned download notification scheme to MCP logs.
- Added `sab_change_position` tool to reorder the download queue.
- Added optional pagination and search parameters (`start`, `limit`, `search`, `category`) to `sab_queue` and `sab_history`.
- Added optional disk cleanup flag (`del_files`) to `sab_queue_delete` and `sab_history_delete` to remove files from disk.
- Enabled pausing and resuming individual queue items in `sab_pause` and `sab_resume` by NZO ID.
- Set up automated CI linting and testing via GitHub Actions.

## 0.2.0 (2026-05-19)

- Added 8 new tools (15 total):
  - `sab_get_config` — read server configuration
  - `sab_set_speedlimit` — percentage or absolute speed limit
  - `sab_add_nzb_file` — upload NZB from base64 content
  - `sab_queue_delete` — remove downloads from queue
  - `sab_change_priority` — low/normal/high/force priority
  - `sab_set_category` — change category of queued item
  - `sab_retry` — retry failed downloads (single or all)
  - `sab_history_delete` — remove items from history
- Queue and history output now includes NZO IDs for management tools
- Added Dockerfile, .env.example
- CI tests across Python 3.10–3.13, validates MCP protocol startup
- Added CONTRIBUTING, SECURITY, AGENTS.md, issue templates

## 0.1.0 (2026-05-19)

- Initial release
- 7 tools: sab_queue, sab_history, sab_status, sab_pause, sab_resume, sab_add_url, sab_categories
- Zero external dependencies (stdlib only)
- stdio transport with JSON-RPC 2.0
