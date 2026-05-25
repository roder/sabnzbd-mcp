"""SABnzbd MCP server — zero external dependencies."""

import base64
import json
import os
import ssl
import sys
import threading
import time
import urllib.parse
import urllib.request

_send_lock = threading.Lock()

def _log(msg):
    """Write a diagnostic line to stderr (never interferes with stdout JSON-RPC)."""
    print(f"[sabnzbd-mcp] {msg}", file=sys.stderr, flush=True)

def load_env():
    """Load variables from .env or ~/.homelab.env into os.environ if they don't already exist."""
    env_paths = [os.path.join(os.getcwd(), ".env"), os.path.expanduser("~/.homelab.env")]
    for path in env_paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() not in os.environ:
                            os.environ[k.strip()] = v.strip().strip("'\"")

load_env()

SABNZBD_URL = os.environ.get("SABNZBD_URL", "http://localhost:8080").rstrip("/")
SABNZBD_API_KEY = os.environ.get("SABNZBD_API_KEY", "")
SABNZBD_SSL_VERIFY = os.environ.get("SABNZBD_SSL_VERIFY", "true").lower() not in ("false", "0", "no")
SABNZBD_POLL_INTERVAL = int(os.environ.get("SABNZBD_POLL_INTERVAL", "15"))

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
        "description": "Current download queue",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start": {"type": "integer", "description": "Offset/start index (default: 0)"},
                "limit": {"type": "integer", "description": "Max number of items to return (default: 25)"},
                "search": {"type": "string", "description": "Filter/search queue items by filename or name"},
                "category": {"type": "string", "description": "Filter queue items by category"},
            }
        },
    },
    {
        "name": "sab_history",
        "description": "Download history (completed/failed)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start": {"type": "integer", "description": "Offset/start index (default: 0)"},
                "limit": {"type": "integer", "description": "Max number of items to return (default: 25)"},
                "search": {"type": "string", "description": "Filter/search history items by filename or name"},
                "category": {"type": "string", "description": "Filter history items by category"},
            }
        },
    },
    {
        "name": "sab_status",
        "description": "Server status: speed, disk, directories",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sab_categories",
        "description": "Download categories",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sab_get_config",
        "description": "Server configuration",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # ── Control ──
    {
        "name": "sab_pause",
        "description": "Pause downloads",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {"type": "string", "description": "Download ID to pause. If omitted, pauses all downloads."}
            }
        },
    },
    {
        "name": "sab_resume",
        "description": "Resume downloads",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {"type": "string", "description": "Download ID to resume. If omitted, resumes all downloads."}
            }
        },
    },
    {
        "name": "sab_set_speedlimit",
        "description": "Set speed limit: percentage or absolute",
        "inputSchema": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "string",
                    "description": "Speed: '80' (percent), '5M' (5 MB/s), '100' (unlimited)",
                },
                "mode": {
                    "type": "string",
                    "enum": ["percent", "absolute"],
                    "description": "percent or absolute",
                },
            },
            "required": ["value"],
        },
    },
    # ── Add downloads ──
    {
        "name": "sab_add_url",
        "description": "Add NZB from URL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "NZB URL"},
                "category": {"type": "string", "description": "Category name"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "sab_add_nzb_file",
        "description": "Upload NZB file content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Base64 NZB content"},
                "filename": {"type": "string", "description": "Filename"},
                "category": {"type": "string", "description": "Category name"},
            },
            "required": ["content"],
        },
    },
    # ── Queue management ──
    {
        "name": "sab_queue_delete",
        "description": "Remove from queue",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {"type": "string", "description": "Download ID (from sab_queue)"},
                "del_files": {"type": "boolean", "description": "Also delete the files associated with the job (default: false)"}
            },
            "required": ["nzo_id"],
        },
    },
    {
        "name": "sab_change_priority",
        "description": "Change download priority",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {"type": "string", "description": "Download ID (from sab_queue)"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "force"],
                    "description": "low, normal, high, or force",
                },
            },
            "required": ["nzo_id", "priority"],
        },
    },
    {
        "name": "sab_set_category",
        "description": "Change download category",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {"type": "string", "description": "Download ID (from sab_queue)"},
                "category": {"type": "string", "description": "Category name"},
            },
            "required": ["nzo_id", "category"],
        },
    },
    {
        "name": "sab_change_position",
        "description": "Move a queued download to a different position in the queue",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {"type": "string", "description": "Download ID (from sab_queue)"},
                "position": {"type": "integer", "description": "Target position in the queue, 0-indexed (0 for top/next)"}
            },
            "required": ["nzo_id", "position"],
        },
    },
    # ── History management ──
    {
        "name": "sab_retry",
        "description": "Retry failed downloads",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {
                    "type": "string",
                    "description": "Download ID, omit to retry all",
                },
            },
        },
    },
    {
        "name": "sab_history_delete",
        "description": "Remove from history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nzo_id": {"type": "string", "description": "Download ID (from sab_history), or 'all' to delete everything, or 'failed' to delete failed items"},
                "del_files": {"type": "boolean", "description": "Also delete the downloaded files on disk (default: false)"}
            },
            "required": ["nzo_id"],
        },
    },
]

# ── Resources ──
RESOURCES = [
    {
        "uri": "sabnzbd://queue",
        "name": "SABnzbd Queue",
        "mimeType": "application/json",
        "description": "Current download queue, speed, progress, and queued items"
    },
    {
        "uri": "sabnzbd://history",
        "name": "SABnzbd History",
        "mimeType": "application/json",
        "description": "Download history including completed and failed downloads"
    },
    {
        "uri": "sabnzbd://status",
        "name": "SABnzbd Status",
        "mimeType": "application/json",
        "description": "Server health, speed limits, disk space, and directories"
    },
    {
        "uri": "sabnzbd://categories",
        "name": "SABnzbd Categories",
        "mimeType": "application/json",
        "description": "Configured download categories"
    },
    {
        "uri": "sabnzbd://config",
        "name": "SABnzbd Config",
        "mimeType": "application/json",
        "description": "SABnzbd server configuration details"
    }
]

# ── Prompts ──
PROMPTS = [
    {
        "name": "sabnzbd_summary",
        "description": "Generate a summary of the SABnzbd server status, download queue, and recent history.",
        "arguments": []
    },
    {
        "name": "sabnzbd_download_nzb",
        "description": "Guides the agent to download a Usenet NZB from a URL.",
        "arguments": [
            {
                "name": "url",
                "description": "The URL of the NZB file to add",
                "required": True
            },
            {
                "name": "category",
                "description": "Optional category to assign to the download",
                "required": False
            }
        ]
    }
]


def _fmt_queue(data):
    if "error" in data:
        return data["error"]
    q = data.get("queue", {})
    slots = q.get("slots", [])
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
    slots = h.get("slots", [])
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
    extra = {}
    if "start" in args:
        extra["start"] = args["start"]
    if "limit" in args:
        extra["limit"] = args["limit"]
    if "search" in args:
        extra["search"] = args["search"]
    if "category" in args:
        extra["category"] = args["category"]
    d = _sab("queue", **extra)
    return _fmt_queue(d), d

def handle_history(args):
    extra = {}
    if "start" in args:
        extra["start"] = args["start"]
    if "limit" in args:
        extra["limit"] = args["limit"]
    if "search" in args:
        extra["search"] = args["search"]
    if "category" in args:
        extra["category"] = args["category"]
    d = _sab("history", **extra)
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
    nzo_id = args.get("nzo_id")
    if nzo_id:
        d = _sab("queue", name="pause", value=nzo_id)
        return d["error"] if "error" in d else f"Paused download {nzo_id}", d
    else:
        d = _sab("pause")
        return d["error"] if "error" in d else "Paused all downloads", d

def handle_resume(args):
    nzo_id = args.get("nzo_id")
    if nzo_id:
        d = _sab("queue", name="resume", value=nzo_id)
        return d["error"] if "error" in d else f"Resumed download {nzo_id}", d
    else:
        d = _sab("resume")
        return d["error"] if "error" in d else "Resumed all downloads", d

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
    extra = {}
    if args.get("del_files"):
        extra["del_files"] = "1"
    d = _sab("queue", name="delete", value=args["nzo_id"], **extra)
    return d["error"] if "error" in d else "Removed from queue", d

def handle_change_priority(args):
    d = _sab("priority", name=args["priority"], value=args["nzo_id"])
    return d["error"] if "error" in d else f"Priority changed to {args['priority']}", d

def handle_set_category(args):
    d = _sab("change_cat", value=args["nzo_id"], cat=args["category"])
    return d["error"] if "error" in d else f"Category changed to {args['category']}", d

def handle_change_position(args):
    d = _sab("queue", name="change_pos", value=args["nzo_id"], value2=str(args["position"]))
    return d["error"] if "error" in d else f"Moved to position {args['position']}", d

def handle_retry(args):
    d = _sab("retry", value=args.get("nzo_id", "all"))
    return d["error"] if "error" in d else "Retrying", d

def handle_history_delete(args):
    extra = {}
    if args.get("del_files"):
        extra["del_files"] = "1"
    d = _sab("history", name="delete", value=args["nzo_id"], **extra)
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
    "sab_change_position": handle_change_position,
    "sab_retry": handle_retry,
    "sab_history_delete": handle_history_delete,
}

# ── Resources Logic ──

def _read_resource_queue():
    return json.dumps(_sab("queue"))

def _read_resource_history():
    return json.dumps(_sab("history"))

def _read_resource_status():
    return json.dumps(_sab("status"))

def _read_resource_categories():
    return json.dumps(_sab("get_cats"))

def _read_resource_config():
    res = _sab("get_config")
    if "config" in res and "api_key" in res["config"]:
        key = res["config"]["api_key"]
        if key:
            res["config"]["api_key"] = f"{key[:4]}...{key[-4:]}"
    return json.dumps(res)

RESOURCE_HANDLERS = {
    "sabnzbd://queue": _read_resource_queue,
    "sabnzbd://history": _read_resource_history,
    "sabnzbd://status": _read_resource_status,
    "sabnzbd://categories": _read_resource_categories,
    "sabnzbd://config": _read_resource_config,
}

# ── Prompts Logic ──

def handle_get_prompt(name, args):
    if name == "sabnzbd_summary":
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": "Please retrieve the current SABnzbd server status using `sab_status`, view the download queue using `sab_queue`, check the recent history using `sab_history`, and present a concise summary of the server's health, current download progress, and any completed/failed items."
                }
            }
        ]
    elif name == "sabnzbd_download_nzb":
        url = args.get("url")
        if not url:
            raise ValueError("Argument 'url' is required for prompt 'sabnzbd_download_nzb'")
        cat = args.get("category", "")
        cat_suffix = f" with category '{cat}'" if cat else ""
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"Please add the NZB from URL '{url}'{cat_suffix} using the `sab_add_url` tool, then check the queue with `sab_queue` and inform me once it starts downloading."
                }
            }
        ]
    else:
        raise ValueError(f"Unknown prompt name: {name}")


def _poll_notifications():
    """Poll SABnzbd history for new completed/failed items and emit MCP notifications."""
    seen_nzo_ids = set()
    # Prime the set of known nzo_ids so we don't alert on old history on startup
    initial_data = _sab("history", limit=20)
    if "error" not in initial_data:
        for s in initial_data.get("history", {}).get("slots", []):
            seen_nzo_ids.add(s.get("nzo_id"))

    while True:
        time.sleep(SABNZBD_POLL_INTERVAL)
        data = _sab("history", limit=10)
        if "error" in data:
            _log(f"poll notification error: {data['error']}")
            continue
        for s in data.get("history", {}).get("slots", []):
            nzo_id = s.get("nzo_id")
            if nzo_id and nzo_id not in seen_nzo_ids:
                seen_nzo_ids.add(nzo_id)
                status = s.get("status")
                if status in ("Completed", "Failed"):
                    _send({
                        "jsonrpc": "2.0",
                        "method": "notifications/message",
                        "params": {
                            "level": "info",
                            "logger": "sabnzbd-mcp",
                            "message": f"SABnzbd download {status.lower()}: {s.get('name')} ({nzo_id})",
                            "data": {
                                "nzo_id": nzo_id,
                                "name": s.get("name"),
                                "status": status,
                                "raw_slot": s
                            }
                        }
                    })


def _send(msg):
    with _send_lock:
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


def main():
    threading.Thread(target=_poll_notifications, daemon=True).start()
    while True:
        raw = sys.stdin.readline()
        if not raw:
            break
        
        # 1. Parse JSON input
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            _send({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            })
            continue

        # 2. Check JSON-RPC 2.0 structure
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
            msg_id = msg.get("id") if isinstance(msg, dict) else None
            _send({
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request"},
                "id": msg_id
            })
            continue

        msg_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {})
        is_notification = "id" not in msg

        if method == "initialize":
            if is_notification:
                continue
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {}
                    },
                    "serverInfo": {"name": "sabnzbd-mcp", "version": "0.3.0"},
                },
            })
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            if is_notification:
                continue
            _send({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            if is_notification:
                continue
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
        elif method == "resources/list":
            if is_notification:
                continue
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"resources": RESOURCES}
            })
        elif method == "resources/read":
            if is_notification:
                continue
            uri = params.get("uri", "")
            handler = RESOURCE_HANDLERS.get(uri)
            if handler:
                try:
                    text_content = handler()
                    _send({
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "application/json",
                                    "text": text_content
                                }
                            ]
                        }
                    })
                except Exception as e:
                    _send({
                        "jsonrpc": "2.0", "id": msg_id,
                        "error": {"code": -32603, "message": f"Internal error reading resource: {e}"}
                    })
            else:
                _send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32602, "message": f"Unknown resource URI: {uri}"}
                })
        elif method == "prompts/list":
            if is_notification:
                continue
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"prompts": PROMPTS}
            })
        elif method == "prompts/get":
            if is_notification:
                continue
            name = params.get("name", "")
            args = params.get("arguments", {})
            prompt_def = next((p for p in PROMPTS if p["name"] == name), None)
            if prompt_def:
                try:
                    messages = handle_get_prompt(name, args)
                    _send({
                        "jsonrpc": "2.0", "id": msg_id,
                        "result": {
                            "description": prompt_def.get("description", ""),
                            "messages": messages
                        }
                    })
                except Exception as e:
                    _send({
                        "jsonrpc": "2.0", "id": msg_id,
                        "error": {"code": -32602, "message": str(e)}
                    })
            else:
                _send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32602, "message": f"Unknown prompt: {name}"}
                })
        else:
            if is_notification:
                continue
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })


if __name__ == "__main__":
    main()
