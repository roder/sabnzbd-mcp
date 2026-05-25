"""Unit tests for tool definitions."""
import json
from sabnzbd_mcp import server


def test_tool_count():
    assert len(server.TOOLS) == 16


def test_tool_names():
    names = {t["name"] for t in server.TOOLS}
    expected = {
        "sab_queue", "sab_history", "sab_status", "sab_categories", "sab_get_config",
        "sab_pause", "sab_resume", "sab_set_speedlimit",
        "sab_add_url", "sab_add_nzb_file",
        "sab_queue_delete", "sab_change_priority", "sab_set_category",
        "sab_change_position", "sab_retry", "sab_history_delete",
    }
    assert names == expected, f"Missing: {expected - names}, Extra: {names - expected}"


def test_all_tools_have_required_fields():
    for t in server.TOOLS:
        assert "name" in t
        assert "description" in t
        assert "inputSchema" in t
        assert "type" in t["inputSchema"]
        assert "properties" in t["inputSchema"]


def test_all_handlers_registered():
    for t in server.TOOLS:
        assert t["name"] in server.TOOL_HANDLERS, f"Missing handler for {t['name']}"


def test_no_unused_handlers():
    tool_names = {t["name"] for t in server.TOOLS}
    handler_names = set(server.TOOL_HANDLERS.keys())
    extra = handler_names - tool_names
    assert not extra, f"Unused handlers: {extra}"
