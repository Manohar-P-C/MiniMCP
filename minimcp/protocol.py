"""MCP protocol implementation on top of a manual JSON-RPC 2.0 engine.

Implements the MCP lifecycle (initialize, initialized, ping), tool discovery
(tools/list) and tool execution (tools/call) per the Model Context Protocol
specification (2025-03-26), without using the official MCP SDK.

Lifecycle states are tracked per session id so concurrent clients are
independent. Requests that violate the lifecycle (e.g. tools/list before
initialize) are rejected.
"""

import json

from . import errors
from .config import Config
from .errors import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    INTERNAL_ERROR,
    METHOD_NOT_FOUND,
    JSONRPCError,
    MCP_NOT_INITIALIZED,
    MCP_UNKNOWN_TOOL,
    PARSE_ERROR,
)
from .registry import Registry


def _result_response(result, request_id):
    return {"jsonrpc": "2.0", "result": result, "id": request_id}


def _error_response(code, message, data=None, request_id=None):
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "error": error, "id": request_id}


class MCPHandler:
    """Handles JSON-RPC 2.0 / MCP messages for a set of sessions."""

    def __init__(self, registry: Registry):
        self.registry = registry
        # session_id -> {"initialized": bool, "protocol_version": str|None}
        self._sessions = {}

    def _session(self, session_id):
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "initialized": False,
                "protocol_version": None,
            }
        return self._sessions[session_id]

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def handle_message(self, message, session_id):
        """Process one JSON-RPC message.

        Returns (response_dict_or_none, http_status_code).
        A response of None means the message is a notification and no
        JSON-RPC response should be sent (HTTP 202).
        """
        # --- structural validation ------------------------------------- #
        if not isinstance(message, dict):
            return _error_response(INVALID_REQUEST, "Invalid Request", None, None), 400

        if message.get("jsonrpc") != "2.0":
            return (
                _error_response(INVALID_REQUEST, "Invalid JSON-RPC version", None, message.get("id")),
                400,
            )

        method = message.get("method")
        request_id = message.get("id")
        is_notification = "id" not in message
        params = message.get("params")
        if not isinstance(params, dict):
            params = {}

        session = self._session(session_id)

        try:
            if method == "initialize":
                result = self._handle_initialize(params)
                session["initialized"] = True
                session["protocol_version"] = params.get("protocolVersion")
                return _result_response(result, request_id), 200

            if method == "initialized":
                # Notification: marks lifecycle complete, no response.
                session["initialized"] = True
                return None, 202

            # All remaining methods require an initialized session.
            if not session["initialized"]:
                if is_notification:
                    return None, 202
                return (
                    _error_response(MCP_NOT_INITIALIZED, "Server not initialized", None, request_id),
                    400,
                )

            if method == "ping":
                return _result_response({}, request_id), 200

            if method == "tools/list":
                tools = [tool.to_dict() for tool in self.registry.list_tools()]
                return _result_response({"tools": tools}, request_id), 200

            if method == "tools/call":
                return self._handle_tool_call(params, request_id)

            # Unknown method.
            if is_notification:
                return None, 202
            return (
                _error_response(METHOD_NOT_FOUND, f"Method not found: {method}", None, request_id),
                400,
            )

        except JSONRPCError as exc:
            if is_notification:
                return None, 202
            return _error_response(exc.code, exc.message, exc.data, request_id), 400
        except KeyError as exc:
            if is_notification:
                return None, 202
            return _error_response(MCP_UNKNOWN_TOOL, str(exc), None, request_id), 400
        except Exception:  # pragma: no cover - defensive
            if is_notification:
                return None, 202
            return _error_response(INTERNAL_ERROR, "Internal error", None, request_id), 500

    # ------------------------------------------------------------------ #
    # Method handlers
    # ------------------------------------------------------------------ #
    def _handle_initialize(self, params):
        client_protocol = params.get("protocolVersion")
        # Capability declaration: this server offers tool discovery/execution.
        return {
            "protocolVersion": Config.PROTOCOL_VERSION,
            "serverInfo": {"name": Config.SERVER_NAME, "version": Config.SERVER_VERSION},
            "capabilities": {
                "tools": {"listChanged": False},
            },
            # Echo back the negotiated protocol version for the client.
            "negotiatedProtocolVersion": client_protocol or Config.PROTOCOL_VERSION,
        }

    def _handle_tool_call(self, params, request_id):
        name = params.get("name")
        arguments = params.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}

        if not isinstance(name, str) or not name:
            return (
                _error_response(INVALID_PARAMS, "Missing tool name", None, request_id),
                400,
            )

        try:
            result = self.registry.execute(name, arguments)
        except KeyError:
            return (
                _error_response(MCP_UNKNOWN_TOOL, f"Unknown tool: {name}", None, request_id),
                400,
            )
        except JSONRPCError as exc:
            return _error_response(exc.code, exc.message, exc.data, request_id), 400
        except Exception:  # pragma: no cover - defensive
            return _error_response(
                INTERNAL_ERROR, f"Tool execution failed: {name}", None, request_id
            ), 500

        # Structured content block response per MCP.
        if isinstance(result, str):
            text = result
        else:
            text = json.dumps(result, ensure_ascii=False)
        content = [{"type": "text", "text": text}]
        return _result_response({"content": content, "isError": False}, request_id), 200
