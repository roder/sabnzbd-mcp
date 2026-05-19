"""Minimal startup tests (use with a real SABnzbd for integration tests)."""
import json

def test_tool_definitions():
    from sabnzbd_mcp import server
    assert len(server.TOOLS) == 7
    names = {t["name"] for t in server.TOOLS}
    assert names == {"sab_queue", "sab_history", "sab_status",
                     "sab_pause", "sab_resume", "sab_add_url", "sab_categories"}
