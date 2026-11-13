"""Tests for authentication and security behavior."""

import os

from minimcp.transport import create_app


def _client_with_token(token):
    os.environ["MINIMCP_AUTH_TOKEN"] = token
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_missing_token_rejected():
    client = _client_with_token("secret-token")
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
    )
    assert r.status_code == 401


def test_invalid_token_rejected():
    client = _client_with_token("secret-token")
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code == 401


def test_valid_token_accepted():
    client = _client_with_token("secret-token")
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Authorization": "Bearer secret-token"},
    )
    # ping without initialize returns not-initialized (400), not 401 -> auth passed
    assert r.status_code != 401


def test_no_token_configured_allows_requests():
    os.environ.pop("MINIMCP_AUTH_TOKEN", None)
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
    )
    assert r.status_code != 401


def test_secret_not_in_error_response():
    os.environ["MINIMCP_AUTH_TOKEN"] = "super-secret"
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
    )
    body = r.get_data(as_text=True)
    assert "super-secret" not in body
    os.environ.pop("MINIMCP_AUTH_TOKEN", None)
