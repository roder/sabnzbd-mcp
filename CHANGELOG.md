# Changelog

## 0.2.0 (2026-05-19)

- Added 9 new tools (16 total):
  - `sab_get_config` — read server configuration
  - `sab_set_speedlimit` — percentage or absolute speed limit
  - `sab_add_nzb_file` — upload NZB from base64 content
  - `sab_queue_delete` — remove downloads from queue
  - `sab_change_priority` — low/normal/high/force priority
  - `sab_set_category` — change category of queued item
  - `sab_retry` — retry failed downloads (single or all)
  - `sab_history_delete` — remove items from history
- Queue and history output now includes NZO IDs for management tools
- Added CI/CD, CONTRIBUTING, SECURITY, AGENTS.md, issue templates

## 0.1.0 (2026-05-19)

- Initial release
- 7 tools: sab_queue, sab_history, sab_status, sab_pause, sab_resume, sab_add_url, sab_categories
- Zero external dependencies (stdlib only)
- stdio transport with JSON-RPC 2.0
