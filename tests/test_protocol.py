"""Tests for the MCP protocol handler and JSON-RPC engine."""

import json

import pytest

from minimcp.protocol import MCPHandler
from minimcp.registry import Registry


@pytest.fixture
def handler():
    registry = Registry()

    @registry.tool
    def add(a: int, b: int) -> int:
        return a + b

    return MCPHandler(registry)


def post(handler, message, session_id="s1"):
    return handler.handle_message(message, session_id)


def test_initialize(handler):
    response, status = post(
        handler,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        },
    )
    assert status == 200
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["protocolVersion"] == "2025-03-26"
    assert response["result"]["serverInfo"]["name"] == "MiniMCP"


def test_initialized_notification(handler):
    # initialize first
    post(
        handler,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        },
    )
    # initialized is a notification: no id, no response body
    response, status = post(handler, {"jsonrpc": "2.0", "method": "initialized"})
    assert response is None
    assert status == 202


def test_ping(handler):
    post(
        handler,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        },
    )
    post(handler, {"jsonrpc": "2.0", "method": "initialized"})
    response, status = post(handler, {"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert status == 200
    assert response["result"] == {}


def test_tools_list(handler):
    post(
        handler,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        },
    )
    post(handler, {"jsonrpc": "2.0", "method": "initialized"})
    response, status = post(handler, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert status == 200
    tools = response["result"]["tools"]
    assert any(t["name"] == "add" for t in tools)
    assert "inputSchema" in tools[0]


def test_tools_call(handler):
    post(
        handler,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        },
    )
    post(handler, {"jsonrpc": "2.0", "method": "initialized"})
    response, status = post(
        handler,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 5, "b": 7}},
        },
    )
    assert status == 200
    assert response["result"]["isError"] is False
    assert response["result"]["content"][0]["text"] == "12"


def test_invalid_json_is_parse_error(handler):
    # handle_message receives already-parsed dicts; parse errors are produced by
    # the transport layer when body cannot be decoded. Test a non-dict message.
    response, status = post(handler, [1, 2, 3])
    assert status == 400
    assert response["error"]["code"] == -32700 or response["error"]["code"] == -32600


def test_invalid_jsonrpc_version(handler):
    response, status = post(
        handler,
        {"jsonrpc": "1.0", "id": 1, "method": "ping"},
    )
    assert status == 400
    assert response["error"]["code"] == -32600


def test_unknown_method(handler):
    post(
        handler,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        },
    )
    post(handler, {"jsonrpc": "2.0", "method": "initialized"})
    response, status = post(handler, {"jsonrpc": "2.0", "id": 9, "method": "nonexistent"})
    assert status == 400
    assert response["error"]["code"] == -32601


def test_invalid_parameters(handler):
    post(
        handler,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        },
    )
    post(handler, {"jsonrpc": "2.0", "method": "initialized"})
    response, status = post(
        handler,
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": "x", "b": 2}},
        },
    )
    assert status == 400
    assert response["error"]["code"] == -32602


def test_invalid_lifecycle_request_before_initialize(handler):
    response, status = post(handler, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert status == 400
    assert response["error"]["code"] in (-32001, -32600)


def test_notification_no_response(handler):
    post(
        handler,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        },
    )
    response, status = post(handler, {"jsonrpc": "2.0", "method": "initialized"})
    assert response is None
    assert status == 202
