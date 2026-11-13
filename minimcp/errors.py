"""JSON-RPC 2.0 and MCP error codes and exception types.

Standard JSON-RPC 2.0 error codes are used so clients can interpret failures
portably. Internal exception details are never placed in public error responses.
"""

# JSON-RPC 2.0 standard error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# MCP-specific errors (reserved range -32000 to -32099 per JSON-RPC convention)
MCP_INVALID_INITIALIZE = -32000
MCP_NOT_INITIALIZED = -32001
MCP_UNKNOWN_TOOL = -32002
MCP_TOOL_EXECUTION_ERROR = -32003


class JSONRPCError(Exception):
    """Raised internally to produce a JSON-RPC error response."""

    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data
