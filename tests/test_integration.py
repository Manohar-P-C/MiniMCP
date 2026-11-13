"""Integration tests: initialize, discover tools, execute tool, verify result."""

import pytest

from minimcp.transport import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_full_flow(client):
    sid = None

    def post(payload):
        nonlocal sid
        headers = {"Content-Type": "application/json"}
        if sid:
            headers["Mcp-Session-Id"] = sid
        r = client.post("/mcp", json=payload, headers=headers)
        if r.headers.get("Mcp-Session-Id"):
            sid = r.headers.get("Mcp-Session-Id")
        return r

    # 1. Initialize server
    r = post(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        }
    )
    assert r.status_code == 200
    assert r.get_json()["result"]["serverInfo"]["name"] == "MiniMCP"

    # 2. Send initialized notification
    r = post({"jsonrpc": "2.0", "method": "initialized"})
    assert r.status_code == 202

    # 3. Discover tools
    r = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert r.status_code == 200
    tools = r.get_json()["result"]["tools"]
    assert len(tools) >= 1

    # 4. Execute a tool
    add_tool = next(t for t in tools if t["name"] == "add")
    assert add_tool is not None
    r = post(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 21, "b": 21}},
        }
    )
    assert r.status_code == 200
    result = r.get_json()["result"]
    assert result["isError"] is False
    assert result["content"][0]["text"] == "42"
