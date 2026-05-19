"""SABnzbd MCP server — zero external dependencies."""

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


TOOLS = [
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
        "description": "Show SABnzbd server status",
        "inputSchema": {"type": "object", "properties": {}},
    },
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
        "name": "sab_add_url",
        "description": "Add an NZB by URL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL of the NZB file"},
                "category": {"type": "string", "description": "SABnzbd category (optional)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "sab_categories",
        "description": "List configured download categories",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _fmt_queue(data):
    q = data.get("queue", {})
    slots = q.get("slots", [])[:10]
    lines = [
        f"Queue: {q.get('noofslots_total', 0)} items | "
        f"{q.get('kbpersec', '0')} KB/s | "
        f"{q.get('mbleft', '0')} MB left | "
        f"Status: {q.get('status', '?')}"
    ]
    for s in slots:
        pct = s.get("percentage", "0")
        mb = s.get("mb", "0")
        lines.append(f"  [{pct}%] {s.get('filename', '?')} ({mb} MB)")
    return "\n".join(lines)


def _fmt_history(data):
    h = data.get("history", {})
    slots = h.get("slots", [])[:10]
    if not slots:
        return "History is empty."
    lines = [f"History: {h.get('total_size', '0')} total"]
    for s in slots:
        icon = "✅" if s.get("status") == "Completed" else "⏳"
        lines.append(f"  {icon} {s.get('name', '?')}")
    return "\n".join(lines)


def _fmt_status(data):
    s = data.get("status", {})
    return (
        f"Speed: {s.get('speed', '0')} ({s.get('speedlimit', '100')}% limit)\n"
        f"Disk: {s.get('diskspacetotal1', '?')} total, {s.get('diskspace1', '?')} free\n"
        f"Download folder: {s.get('downloaddir', '?')}\n"
        f"Complete folder: {s.get('completedir', '?')}"
    )


TOOL_HANDLERS = {
    "sab_queue": lambda a: _fmt_queue(_sab("queue")),
    "sab_history": lambda a: _fmt_history(_sab("history")),
    "sab_status": lambda a: _fmt_status(_sab("status")),
    "sab_pause": lambda a: "Paused" if "error" not in (d := _sab("pause")) else d["error"],
    "sab_resume": lambda a: "Resumed" if "error" not in (d := _sab("resume")) else d["error"],
    "sab_add_url": lambda a: "Added NZB" if "error" not in (d := _sab("addurl", name=a["url"], cat=a.get("category", ""))) else d["error"],
    "sab_categories": lambda a: "\n".join(
        ["Categories:"] + [f"  {c.get('name', '?')}" for c in _sab("get_cats").get("categories", [])]
    ) if _sab("get_cats").get("categories") else "No categories.",
}


def _recv():
    """Read a JSON-RPC message from stdin."""
    raw = sys.stdin.readline()
    return json.loads(raw) if raw else None


def _send(msg):
    """Write a JSON-RPC message to stdout."""
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
                    "serverInfo": {"name": "sabnzbd-mcp", "version": "0.1.0"},
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
