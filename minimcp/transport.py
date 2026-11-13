"""Flask transport layer exposing Streamable HTTP endpoints.

Endpoints:
    POST /mcp   - JSON-RPC 2.0 / MCP messages (and notifications).
    GET  /mcp   - Endpoint information (Streamable HTTP discovery).
    GET  /health - Service health and readiness.

Authentication (Bearer token), CORS, request-size limits, and session handling
via the Mcp-Session-Id header are implemented here, keeping protocol logic in
protocol.py and out of the transport layer.
"""

import json
import secrets

from flask import Flask, jsonify, render_template, request

from . import errors
from .config import Config
from .errors import INVALID_REQUEST, PARSE_ERROR
from .protocol import MCPHandler
from .registry import Registry
from .security import require_auth
from .tools import registry as builtin_registry


def _make_json_response(payload, status_code, headers=None):
    response = jsonify(payload)
    response.status_code = status_code
    if headers:
        for key, value in headers.items():
            response.headers[key] = value
    return response


def _parse_body(body):
    """Parse raw request body as JSON. Returns (parsed_or_none, error_response)."""
    try:
        return json.loads(body), None
    except (json.JSONDecodeError, ValueError):
        return None, _make_json_response(
            _error_payload(PARSE_ERROR, "Parse error", None, None), 400
        )


def _error_payload(code, message, data=None, request_id=None):
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "error": error, "id": request_id}


def create_app(registry: Registry = None):
    """Build and configure the Flask application."""
    if registry is None:
        registry = builtin_registry

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config["JSON_SORT_KEYS"] = False

    handler = MCPHandler(registry)

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    @app.after_request
    def _add_cors(response):
        origin = request.headers.get("Origin")
        allowed = Config.CORS_ORIGINS
        if "*" in allowed:
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin and origin in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, Mcp-Session-Id, Accept"
        )
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    # ------------------------------------------------------------------ #
    # Request size limit for /mcp
    # ------------------------------------------------------------------ #
    @app.before_request
    def _limit_request_size():
        if request.path == "/mcp" and request.method == "POST":
            length = request.content_length
            if length and length > Config.MAX_REQUEST_SIZE:
                return _make_json_response(
                    {"error": "Request too large"}, 413
                )

    # ------------------------------------------------------------------ #
    # Health endpoint (public)
    # ------------------------------------------------------------------ #
    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route("/health", methods=["GET"])
    def health():
        return _make_json_response(
            {
                "status": "ready",
                "version": Config.SERVER_VERSION,
                "protocolVersion": Config.PROTOCOL_VERSION,
                "toolCount": len(registry.list_tools()),
                "transport": "streamable-http",
            },
            200,
        )

    # ------------------------------------------------------------------ #
    # MCP endpoint
    # ------------------------------------------------------------------ #
    def _handle_mcp(message):
        session_id = request.headers.get("Mcp-Session-Id") or secrets.token_hex(8)
        headers = {"Mcp-Session-Id": session_id}

        if isinstance(message, list):
            # Batch handling: process each message, collect non-null responses.
            responses = []
            for item in message:
                response, _status = handler.handle_message(item, session_id)
                if response is not None:
                    responses.append(response)
            if not responses:
                return _make_json_response("", 202, headers)
            return _make_json_response(responses, 200, headers)

        response, status_code = handler.handle_message(message, session_id)
        if response is None:
            # Notification: no JSON-RPC response body.
            return _make_json_response("", 202, headers)
        return _make_json_response(response, status_code, headers)

    @app.route("/mcp", methods=["OPTIONS"])
    def mcp_options():
        return _make_json_response("", 204)

    @app.route("/mcp", methods=["GET"])
    def mcp_get():
        # Streamable HTTP endpoint discovery. GET is not used to send messages.
        return _make_json_response(
            {
                "endpoint": "/mcp",
                "protocolVersion": Config.PROTOCOL_VERSION,
                "transport": "streamable-http",
                "methods": ["POST"],
            },
            200,
        )

    @app.route("/mcp", methods=["POST"])
    def mcp_post():
        # Authentication (Bearer token).
        auth_result = require_auth(request)
        if auth_result is not None:
            response, status_code = auth_result
            return _make_json_response(response, status_code)

        # Content-Type must be application/json.
        if not request.is_json:
            return _make_json_response(
                _error_payload(
                    INVALID_REQUEST, "Content-Type must be application/json", None, None
                ),
                400,
            )

        body = request.get_data()
        message, error_response = _parse_body(body)
        if error_response is not None:
            # Still echo a session id header.
            return _make_json_response(
                _error_payload(PARSE_ERROR, "Parse error", None, None),
                400,
                {"Mcp-Session-Id": request.headers.get("Mcp-Session-Id", secrets.token_hex(8))},
            )

        return _handle_mcp(message)

    return app
