"""Tests for MCP-specific protocol features: JSON-RPC errors, resources, and prompts."""

import json
import os
import subprocess
import sys
import pytest

def run_server_with_input(input_data):
    """Helper to run the server process with given stdin and capture stdout."""
    # Ensure background polling doesn't cause tests to hang by setting interval low
    env = os.environ.copy()
    env["SABNZBD_POLL_INTERVAL"] = "1"
    
    proc = subprocess.run(
        [sys.executable, "-m", "sabnzbd_mcp"],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=5,
        env=env
    )
    # Parse lines from stdout
    results = []
    for line in proc.stdout.strip().split("\n"):
        if line.strip():
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                results.append({"raw": line})
    return results


def test_json_rpc_parse_error():
    # Sending malformed JSON
    results = run_server_with_input("{\n")
    assert len(results) == 1
    assert results[0]["jsonrpc"] == "2.0"
    assert "error" in results[0]
    assert results[0]["error"]["code"] == -32700
    assert "Parse error" in results[0]["error"]["message"]
    assert results[0]["id"] is None


def test_json_rpc_invalid_request():
    # Sending object missing jsonrpc version or method
    results = run_server_with_input('{"id": 1, "params": {}}\n')
    assert len(results) == 1
    assert results[0]["jsonrpc"] == "2.0"
    assert "error" in results[0]
    assert results[0]["error"]["code"] == -32600
    assert "Invalid Request" in results[0]["error"]["message"]
    assert results[0]["id"] == 1


def test_json_rpc_method_not_found():
    # Sending unknown method
    results = run_server_with_input('{"jsonrpc": "2.0", "id": 99, "method": "sab_magic_download"}\n')
    assert len(results) == 1
    assert results[0]["jsonrpc"] == "2.0"
    assert "error" in results[0]
    assert results[0]["error"]["code"] == -32601
    assert "Method not found" in results[0]["error"]["message"]
    assert results[0]["id"] == 99


def test_mcp_resources_list():
    results = run_server_with_input('{"jsonrpc": "2.0", "id": 2, "method": "resources/list"}\n')
    assert len(results) == 1
    assert "result" in results[0]
    assert "resources" in results[0]["result"]
    resources = results[0]["result"]["resources"]
    assert len(resources) == 5
    uris = {r["uri"] for r in resources}
    assert uris == {
        "sabnzbd://queue",
        "sabnzbd://history",
        "sabnzbd://status",
        "sabnzbd://categories",
        "sabnzbd://config"
    }


def test_mcp_resources_read_invalid_uri():
    results = run_server_with_input('{"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": "sabnzbd://invalid"}}\n')
    assert len(results) == 1
    assert "error" in results[0]
    assert results[0]["error"]["code"] == -32602
    assert "Unknown resource URI" in results[0]["error"]["message"]


def test_mcp_resources_read_valid_uri_returns_json():
    # Even if connection fails, resources/read should return a result with the error string in 'text'
    results = run_server_with_input('{"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {"uri": "sabnzbd://queue"}}\n')
    assert len(results) == 1
    assert "result" in results[0]
    assert "contents" in results[0]["result"]
    contents = results[0]["result"]["contents"]
    assert len(contents) == 1
    assert contents[0]["uri"] == "sabnzbd://queue"
    assert contents[0]["mimeType"] == "application/json"
    # Ensure text is JSON format (which represents the error or valid response)
    text_data = json.loads(contents[0]["text"])
    assert isinstance(text_data, dict)


def test_mcp_prompts_list():
    results = run_server_with_input('{"jsonrpc": "2.0", "id": 5, "method": "prompts/list"}\n')
    assert len(results) == 1
    assert "result" in results[0]
    assert "prompts" in results[0]["result"]
    prompts = results[0]["result"]["prompts"]
    assert len(prompts) == 2
    names = {p["name"] for p in prompts}
    assert names == {"sabnzbd_summary", "sabnzbd_download_nzb"}


def test_mcp_prompts_get():
    # Summary prompt (no args)
    results = run_server_with_input('{"jsonrpc": "2.0", "id": 6, "method": "prompts/get", "params": {"name": "sabnzbd_summary"}}\n')
    assert len(results) == 1
    assert "result" in results[0]
    assert "messages" in results[0]["result"]
    messages = results[0]["result"]["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert "sab_status" in messages[0]["content"]["text"]

    # Download NZB prompt (with args)
    results = run_server_with_input('{"jsonrpc": "2.0", "id": 7, "method": "prompts/get", "params": {"name": "sabnzbd_download_nzb", "arguments": {"url": "http://example.com/test.nzb", "category": "movies"}}}\n')
    assert len(results) == 1
    assert "result" in results[0]
    messages = results[0]["result"]["messages"]
    assert len(messages) == 1
    assert "http://example.com/test.nzb" in messages[0]["content"]["text"]
    assert "movies" in messages[0]["content"]["text"]
