"""Tests for the Flask transport layer."""

import json

import pytest

from minimcp.transport import create_app
from minimcp.tools import registry as builtin_registry


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_http_post_handling(client):
    # initialize then call within one session
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
    )
    assert r.status_code == 200
    sid = r.headers.get("Mcp-Session-Id")
    assert sid is not None

    client.post("/mcp", json={"jsonrpc": "2.0", "method": "initialized"}, headers={"Mcp-Session-Id": sid})

    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        headers={"Mcp-Session-Id": sid},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "tools" in data["result"]


def test_content_type_validation(client):
    r = client.post("/mcp", data=b"hello", content_type="text/plain")
    assert r.status_code == 400
    data = r.get_json()
    assert data["error"]["code"] == -32600


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ready"
    assert data["protocolVersion"] == "2025-03-26"
    assert data["toolCount"] >= 1
    assert "transport" in data


def test_cors_headers(client):
    r = client.options("/mcp", headers={"Origin": "http://example.com"})
    assert r.status_code == 204
    assert r.headers.get("Access-Control-Allow-Methods") is not None

    r = client.get("/health", headers={"Origin": "http://example.com"})
    assert "Access-Control-Allow-Origin" in r.headers


def test_index_route(client):
    r = client.get("/")
    assert r.status_code == 200


def test_mcp_get(client):
    r = client.get("/mcp")
    assert r.status_code == 200


def test_batch_handling(client):
    # Initialize one session, then send a batch of pings.
    sid = None
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
    )
    assert r.status_code == 200
    sid = r.headers.get("Mcp-Session-Id")
    client.post("/mcp", json={"jsonrpc": "2.0", "method": "initialized"}, headers={"Mcp-Session-Id": sid})

    r = client.post(
        "/mcp",
        json=[
            {"jsonrpc": "2.0", "id": 2, "method": "ping"},
            {"jsonrpc": "2.0", "id": 3, "method": "ping"},
        ],
        headers={"Mcp-Session-Id": sid},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 2
    assert all(item["result"] == {} for item in data)
