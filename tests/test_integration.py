"""Integration tests — requires SABNZBD_URL and SABNZBD_API_KEY."""
import os
import json
import subprocess
import sys

def test_queue():
    url = os.environ.get("SABNZBD_URL")
    key = os.environ.get("SABNZBD_API_KEY")
    if not url or not key:
        pytest.skip("Set SABNZBD_URL and SABNZBD_API_KEY")

    env = os.environ.copy()
    script = (
        '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
        '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"sab_queue","arguments":{}}}\n'
    )
    proc = subprocess.run(
        [sys.executable, "-m", "sabnzbd_mcp"],
        input=script, capture_output=True, text=True, timeout=10, env=env
    )
    lines = [json.loads(l) for l in proc.stdout.strip().split("\n") if l.strip()]
    assert len(lines) == 2
    result = lines[1]["result"]["content"][0]["text"]
    assert "Queue:" in result
