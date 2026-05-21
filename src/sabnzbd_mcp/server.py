"""SABnzbd MCP server — zero external dependencies."""

import base64
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request

SABNZBD_URL = os.environ.get("SABNZBD_URL", "http://localhost:8080").rstrip("/")
SABNZBD_API_KEY = os.environ.get("SABNZBD_API_KEY", "")
SABNZBD_SSL_VERIFY = os.environ.get("SABNZBD_SSL_VERIFY", "true").lower() not in ("false", "0", "no")

def _get_ssl_context():
    if not SABNZBD_SSL_VERIFY:
        return ssl._create_unverified_context()
    return None

def _sab(mode, **extra):
    """Call the SABnzbd API and return parsed JSON."""
    params = {"mode": mode, "apikey": SABNZBD_API_KEY, "output": "json"} | extra
    url = f"{SABNZBD_URL}/api?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15, context=_get_ssl_context()) as r:
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
        with urllib.request.urlopen(req, timeout=30, context=_get_ssl_context()) as r:
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
    if "error" in data:
        return data["error"]
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
    if "error" in data:
        return data["error"]
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
    if "error" in data:
        return data["error"]
    s = data.get("status", {})
    return (
        f"Speed: {s.get('speed', '0')} ({s.get('speedlimit', '100')}% limit)\n"
        f"Disk: {s.get('diskspacetotal1', '?')} total, {s.get('diskspace1', '?')} free\n"
        f"Download folder: {s.get('downloaddir', '?')}\n"
        f"Complete folder: {s.get('completedir', '?')}"
    )


def _fmt_config(data):
    if "error" in data:
        return data["error"]
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
    if not value.endswith("%"):
        return f"{value}%"
    return value


def handle_queue(args):
    d = _sab("queue")
    return _fmt_queue(d), d

def handle_history(args):
    d = _sab("history")
    return _fmt_history(d), d

def handle_status(args):
    d = _sab("status")
    return _fmt_status(d), d

def handle_categories(args):
    d = _sab("get_cats")
    if "error" in d:
        return d["error"], d
    cats = d.get("categories", [])
    if not cats:
        return "No categories.", d
    return "Categories:\n" + "\n".join(f"  {c.get('name','?')}" for c in cats), d

def handle_get_config(args):
    d = _sab("get_config")
    return _fmt_config(d), d

def handle_pause(args):
    d = _sab("pause")
    return d["error"] if "error" in d else "Paused", d

def handle_resume(args):
    d = _sab("resume")
    return d["error"] if "error" in d else "Resumed", d

def handle_set_speedlimit(args):
    d = _sab("config", name="speedlimit", value=_speedlimit_value(args["value"], args.get("mode", "percent")))
    return d["error"] if "error" in d else "Speed limit set", d

def handle_add_url(args):
    d = _sab("addurl", name=args["url"], cat=args.get("category", ""))
    return d["error"] if "error" in d else "Added NZB", d

def handle_add_nzb_file(args):
    content_b64 = args.get("content", "")
    filename = args.get("filename", "upload.nzb")
    category = args.get("category", "")
    try:
        raw = base64.b64decode(content_b64)
    except Exception as e:
        return f"Invalid base64 content: {e}", {"error": f"Invalid base64 content: {e}"}
    boundary = b"----sabnzbd-mcp-boundary"
    body = []
    if category:
        body.append(b"--" + boundary)
        body.append(b'Content-Disposition: form-data; name="cat"')
        body.append(b"")
        body.append(category.encode())
    body.append(b"--" + boundary)
    body.append(f'Content-Disposition: form-data; name="name"; filename="{filename}"'.encode())
    body.append(b"Content-Type: application/x-nzb")
    body.append(b"")
    body.append(raw)
    body.append(b"--" + boundary + b"--")
    payload = b"\r\n".join(body)
    url = f"{SABNZBD_URL}/api?mode=addfile&output=json&apikey={SABNZBD_API_KEY}"
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"}
    result = _sab_post(url, data=payload, headers=headers)
    return (f"Upload failed: {result['error']}" if "error" in result else "NZB file uploaded successfully", result)

def handle_queue_delete(args):
    d = _sab("queue", name="delete", value=args["nzo_id"])
    return d["error"] if "error" in d else "Removed from queue", d

def handle_change_priority(args):
    d = _sab("priority", name=args["priority"], value=args["nzo_id"])
    return d["error"] if "error" in d else f"Priority changed to {args['priority']}", d

def handle_set_category(args):
    d = _sab("change_cat", value=args["nzo_id"], cat=args["category"])
    return d["error"] if "error" in d else f"Category changed to {args['category']}", d

def handle_retry(args):
    d = _sab("retry", value=args.get("nzo_id", "all"))
    return d["error"] if "error" in d else "Retrying", d

def handle_history_delete(args):
    d = _sab("history", name="delete", value=args["nzo_id"])
    return d["error"] if "error" in d else "Deleted from history", d


TOOL_HANDLERS = {
    "sab_queue": handle_queue,
    "sab_history": handle_history,
    "sab_status": handle_status,
    "sab_categories": handle_categories,
    "sab_get_config": handle_get_config,
    "sab_pause": handle_pause,
    "sab_resume": handle_resume,
    "sab_set_speedlimit": handle_set_speedlimit,
    "sab_add_url": handle_add_url,
    "sab_add_nzb_file": handle_add_nzb_file,
    "sab_queue_delete": handle_queue_delete,
    "sab_change_priority": handle_change_priority,
    "sab_set_category": handle_set_category,
    "sab_retry": handle_retry,
    "sab_history_delete": handle_history_delete,
}


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
                    "serverInfo": {"name": "sabnzbd-mcp", "version": "0.2.0"},
                },
            })
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            handler = TOOL_HANDLERS.get(name)
            if handler:
                try:
                    result = handler(args)
                    if isinstance(result, tuple):
                        text, raw_data = result
                        content = [{"type": "text", "text": text}]
                        if raw_data:
                            content.append({"type": "text", "text": json.dumps(raw_data)})
                    else:
                        content = [{"type": "text", "text": str(result)}]
                    _send({
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {"content": content},
                    })
                except Exception as e:
                    _send({
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True},
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
