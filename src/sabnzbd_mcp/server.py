"""SABnzbd MCP server — zero external dependencies."""

import base64
import json
import os
import sys
import urllib.parse
import urllib.request

SABNZBD_URL = os.environ.get("SABNZBD_URL", "http://localhost:8080")
SABNZBD_API_KEY = os.environ.get("SABNZBD_API_KEY", "")


def _sab(mode, **extra):
    """Call the SABnzbd API and return parsed JSON."""
    params = {"mode": mode, "apikey": SABNZBD_API_KEY, "output": "json"} | extra
    url = f"{SABNZBD_URL}/api?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _sab_post(url, data=None, headers=None):
    """POST to SABnzbd API (for file uploads)."""
    try:
        req = urllib.request.Request(url, data=data, headers=headers or {})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


TOOLS = [
    # ── Read ──
    {
        "name": "sab_queue",
        "description": "Show the SABnzbd download queue",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sab_history",
        "description": "Show SABnzbd download history",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sab_status",
        "description": "Show SABnzbd server status — speed, disk, directories",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sab_categories",
        "description": "List configured download categories",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sab_get_config",
        "description": "Get SABnzbd server configuration",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # ── Control ──
    {
        "name": "sab_pause",
        "description": "Pause all active downloads",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sab_resume",
        "description": "Resume paused downloads",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sab_set_speedlimit",
        "description": "Set the global download speed limit. Use a percentage like '80' (80% of full speed) or absolute like '5M' (5 MB/s). Set to '100' for unlimited.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "string",
                    "description": "Speed limit: percentage ('80'), absolute ('5M' for 5 MB/s), or '100' for unlimited",
                },
                "mode": {
                    "type": "string",
                    "enum": ["percent", "absolute"],
                    "description": "'percent' (default) treats value as percentage. 'absolute' treats value as KB/s or with suffix like '5M'.",
                },
            },
            "required": ["value"],
        },
    },
    # ── Add downloads ──
    {
        "name": "sab_add_url",
        "description": "Add an NZB by URL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL of the NZB file"},
                "category": {
                    "type": "string",
                    "description": "SABnzbd category (optional, use sab_categories to list)",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "sab_add_nzb_file",
        "description": "Upload an NZB file as base64-encoded content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Base64-encoded content of the NZB file",
                },
                "filename": {
                    "type": "string",
                    "description": "Filename for the NZB (e.g. 'download.nzb')",
                },
                "category": {
                    "type": "string",
                    "description": "SABnzbd category (optional)",
                },
            },
            "required": ["content"],
        },
    },
    # ── Queue management ──
    {
        "name": "sab_queue_delete",
        "description": "Remove a download from the queue by NZO ID (get IDs from sab_queue)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {
                    "type": "string",
                    "description": "NZO ID of the download to remove (use sab_queue to find this)",
                },
            },
            "required": ["nzo_id"],
        },
    },
    {
        "name": "sab_change_priority",
        "description": "Change the priority of a queued download",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {
                    "type": "string",
                    "description": "NZO ID of the download (use sab_queue to find this)",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "force"],
                    "description": "New priority level",
                },
            },
            "required": ["nzo_id", "priority"],
        },
    },
    {
        "name": "sab_set_category",
        "description": "Change the category of a queued download",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {
                    "type": "string",
                    "description": "NZO ID of the download (use sab_queue to find this)",
                },
                "category": {
                    "type": "string",
                    "description": "Category name (use sab_categories to list)",
                },
            },
            "required": ["nzo_id", "category"],
        },
    },
    # ── History management ──
    {
        "name": "sab_retry",
        "description": "Retry failed downloads from history. Leave nzo_id empty to retry all failed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {
                    "type": "string",
                    "description": "NZO ID to retry (optional — omit to retry all failed downloads)",
                },
            },
        },
    },
    {
        "name": "sab_history_delete",
        "description": "Remove an item from the download history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {
                    "type": "string",
                    "description": "NZO ID of the history item to delete (use sab_history to find this)",
                },
            },
            "required": ["nzo_id"],
        },
    },
]


def _fmt_queue(data):
    q = data.get("queue", {})
    slots = q.get("slots", [])[:25]
    lines = [
        f"Queue: {q.get('noofslots_total', 0)} items | "
        f"{q.get('kbpersec', '0')} KB/s | "
        f"{q.get('mbleft', '0')} MB left | "
        f"Status: {q.get('status', '?')}"
    ]
    for s in slots:
        pct = s.get("percentage", "0")
        mb = s.get("mb", "0")
        nzo_id = s.get("nzo_id", "?")
        lines.append(f"  [{pct}%] [{nzo_id}] {s.get('filename', '?')} ({mb} MB)")
    return "\n".join(lines)


def _fmt_history(data):
    h = data.get("history", {})
    slots = h.get("slots", [])[:25]
    if not slots:
        return "History is empty."
    lines = [f"History: {h.get('total_size', '0')} total"]
    for s in slots:
        icon = "✅" if s.get("status") == "Completed" else "⏳"
        nzo_id = s.get("nzo_id", "?")
        name = s.get("name", "?")
        lines.append(f"  {icon} [{nzo_id}] {name}")
    return "\n".join(lines)


def _fmt_status(data):
    s = data.get("status", {})
    return (
        f"Speed: {s.get('speed', '0')} ({s.get('speedlimit', '100')}% limit)\n"
        f"Disk: {s.get('diskspacetotal1', '?')} total, {s.get('diskspace1', '?')} free\n"
        f"Download folder: {s.get('downloaddir', '?')}\n"
        f"Complete folder: {s.get('completedir', '?')}"
    )


def _fmt_config(data):
    cfg = data.get("config", {})
    keys = ["host", "port", "download_dir", "complete_dir", "username",
            "api_key", "ssl", "web_dir", "enable_https", "https_port",
            "max_art_tries", "queue_complete", "history_retention"]
    lines = []
    for k in keys:
        val = cfg.get(k, "?")
        if k == "api_key" and val:
            val = f"{val[:4]}...{val[-4:]}"
        lines.append(f"{k}: {val}")
    return "\n".join(lines)


def _speedlimit_value(value, mode):
    """Format speed limit for SABnzbd API."""
    if mode == "absolute" or any(c in value for c in "KM"):
        return value
    return value


TOOL_HANDLERS = {
    "sab_queue": lambda a: _fmt_queue(_sab("queue")),
    "sab_history": lambda a: _fmt_history(_sab("history")),
    "sab_status": lambda a: _fmt_status(_sab("status")),
    "sab_categories": lambda a: (
        "Categories:\n" + "\n".join(
            f"  {c.get('name','?')}" for c in _sab("get_cats").get("categories", [])
        )
    ) if _sab("get_cats").get("categories") else "No categories.",
    "sab_get_config": lambda a: _fmt_config(_sab("get_config")),
    "sab_pause": lambda a: "Paused" if "error" not in (d := _sab("pause")) else d["error"],
    "sab_resume": lambda a: "Resumed" if "error" not in (d := _sab("resume")) else d["error"],
    "sab_set_speedlimit": lambda a: (
        d := _sab("config", name="speedlimit", value=_speedlimit_value(a["value"], a.get("mode", "percent")))
    ) and ("Speed limit set" if "error" not in d else d["error"]),
    "sab_add_url": lambda a: (
        d := _sab("addurl", name=a["url"], cat=a.get("category", ""))
    ) and ("Added NZB" if "error" not in d else d["error"]),
    "sab_add_nzb_file": lambda a: _handle_add_nzb(a),
    "sab_queue_delete": lambda a: (
        d := _sab("queue", name="delete", value=a["nzo_id"])
    ) and ("Removed from queue" if "error" not in d else d["error"]),
    "sab_change_priority": lambda a: (
        d := _sab("priority", name=a["priority"], value=a["nzo_id"])
    ) and (f"Priority changed to {a['priority']}" if "error" not in d else d["error"]),
    "sab_set_category": lambda a: (
        d := _sab("change_cat", value=a["nzo_id"], cat=a["category"])
    ) and (f"Category changed to {a['category']}" if "error" not in d else d["error"]),
    "sab_retry": lambda a: (
        d := _sab("retry", value=a.get("nzo_id", "all"))
    ) and ("Retrying" if "error" not in d else d["error"]),
    "sab_history_delete": lambda a: (
        d := _sab("history", name="delete", value=a["nzo_id"])
    ) and ("Deleted from history" if "error" not in d else d["error"]),
}


def _handle_add_nzb(args):
    """Upload NZB from base64 content via multipart POST."""
    content_b64 = args.get("content", "")
    filename = args.get("filename", "upload.nzb")
    category = args.get("category", "")
    try:
        raw = base64.b64decode(content_b64)
    except Exception as e:
        return f"Invalid base64 content: {e}"
    boundary = b"----sabnzbd-mcp-boundary"
    body = []
    if category:
        body.append(b"--" + boundary)
        body.append(b'Content-Disposition: form-data; name="cat"')
        body.append(b"")
        body.append(category.encode())
    body.append(b"--" + boundary)
    body.append(
        f'Content-Disposition: form-data; name="name"; filename="{filename}"'.encode()
    )
    body.append(b"Content-Type: application/x-nzb")
    body.append(b"")
    body.append(raw)
    body.append(b"--" + boundary + b"--")
    payload = b"\r\n".join(body)
    url = f"{SABNZBD_URL}/api?mode=addfile&output=json&apikey={SABNZBD_API_KEY}"
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"}
    result = _sab_post(url, data=payload, headers=headers)
    if "error" in result:
        return f"Upload failed: {result['error']}"
    return "NZB file uploaded successfully"


def _recv():
    raw = sys.stdin.readline()
    return json.loads(raw) if raw else None


def _send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main():
    while True:
        msg = _recv()
        if msg is None:
            break
        msg_id = msg.get("id", 0)
        method = msg.get("method", "")
        params = msg.get("params", {})

        if method == "initialize":
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "sabnzbd-mcp", "version": "0.1.1"},
                },
            })
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            handler = TOOL_HANDLERS.get(name)
            if handler:
                text = handler(args)
                _send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": [{"type": "text", "text": text}]},
                })
            else:
                _send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                })
        elif method == "notifications/initialized":
            pass
        else:
            _send({"jsonrpc": "2.0", "id": msg_id, "result": {}})


if __name__ == "__main__":
    main()
