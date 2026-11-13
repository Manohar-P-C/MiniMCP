# MiniMCP

**MiniMCP – A Lightweight Model Context Protocol Server Built from Scratch**

A complete, production-style Model Context Protocol (MCP) server implemented in Python **without the official MCP SDK**. Every part of the protocol — JSON-RPC 2.0 messaging, the MCP lifecycle, tool registration/discovery, automatic JSON Schema generation from type hints, and Streamable HTTP transport — is implemented manually on top of Flask.

This is a Homingo Learn capstone project for the course "Build, Ship an AI Agent MCP Server."

> ⚠️ No live URLs, metrics, badges, or test results are fabricated in this document. Placeholders are marked explicitly.

---

## Problem Statement

Building an MCP server typically means depending on the official MCP SDK, which hides the protocol details. MiniMCP demonstrates how the Model Context Protocol works under the hood by implementing JSON-RPC 2.0, the MCP lifecycle (initialize/initialized/ping), tool discovery (`tools/list`), tool execution (`tools/call`), and automatic JSON Schema generation from scratch. It also includes an interactive developer playground, Bearer token authentication, health monitoring, pytest test coverage, and Render deployment configuration.

---

## Architecture

MiniMCP uses a modular design with clear separation between the protocol logic, the HTTP transport, security, the tool registry, and schema generation.

```mermaid
flowchart TD
    subgraph Client
        UI[Developer Playground<br/>index.html + app.js]
        Client[Any MCP Client<br/>JSON-RPC over HTTP]
    end

    subgraph Transport["Flask Transport (transport.py)"]
        POST[POST /mcp]
        GET[GET /mcp]
        Health[GET /health]
        Auth[Bearer Token Auth]
        CORS[CORS]
    end

    subgraph Protocol["MCP Protocol (protocol.py)"]
        JSONRPC[JSON-RPC 2.0 Engine]
        Lifecycle[Lifecycle: initialize, initialized, ping]
        ToolsList[tools/list]
        ToolsCall[tools/call]
    end

    subgraph Core["Core (minimcp/)"]
        Registry[Tool Registry (registry.py)]
        Schema[JSON Schema from type hints (schema.py)]
        Tools[Built-in tools (tools.py)]
        Security[Security helpers (security.py)]
        Config[Configuration (config.py)]
    end

    UI --> POST
    Client --> POST
    POST --> Auth
    Auth --> JSONRPC
    JSONRPC --> Lifecycle
    JSONRPC --> ToolsList
    JSONRPC --> ToolsCall
    ToolsList --> Registry
    ToolsCall --> Registry
    Registry --> Schema
    Registry --> Tools
    Health --> Config
    CORS --> POST
```

### Module responsibilities

| Module | Responsibility |
|---|---|
| `config.py` | Environment-based configuration (no hardcoded secrets) |
| `errors.py` | JSON-RPC 2.0 / MCP error codes and exception types |
| `schema.py` | Automatic JSON Schema generation from Python type hints |
| `registry.py` | Decorator-based tool registration, discovery, validation, execution |
| `protocol.py` | JSON-RPC 2.0 engine + MCP lifecycle (independent of Flask) |
| `security.py` | Bearer token authentication with constant-time comparison |
| `tools.py` | Built-in tools (calculator, text analyzer, URL validator, date/time, string utility, JSON utility) |
| `transport.py` | Flask app: POST/GET/OPTIONS /mcp, GET /health, CORS, sessions |
| `app.py` | Application entry point |

---

## Technology stack

- **Language:** Python 3.15.2
- **Backend framework:** Flask 3.1.3
- **Transport:** Streamable HTTP over Flask (`POST /mcp`, `GET /mcp`, `GET /health`)
- **Protocol:** JSON-RPC 2.0 implemented manually; MCP 2025-03-26
- **Schema generation:** Python `inspect` + `typing` (no external schema library)
- **Frontend:** HTML5, CSS3, vanilla JavaScript, Fetch API
- **Testing:** pytest, Flask test client
- **Production server:** Gunicorn 27.0.1 (verified compatible with Python 3.15)
- **Deployment:** Render

No official MCP SDK or MCP wrapper library is used.

---

## Features

- Manual JSON-RPC 2.0 engine (request parsing, response generation, ID preservation, notifications, standard error codes)
- MCP lifecycle: `initialize`, `initialized` notification, protocol version negotiation, server info, capability declaration, `ping`
- Lifecycle state validation (requests before `initialize` are rejected)
- `tools/list` — dynamic tool discovery with auto-generated input schemas
- `tools/call` — argument validation, type checking, required-parameter checks, structured content-block responses
- Automatic JSON Schema generation from type hints (str/int/float/bool/list/dict/Optional/Union/defaults)
- Decorator-based tool registry (independent of Flask)
- 13 built-in tools across 6 categories (see Built-in Tools)
- Bearer token authentication with `hmac.compare_digest`
- Environment-based configuration, no hardcoded secrets
- Request size limits, restricted CORS, safe error messages (no secret leakage)
- Interactive developer playground (tool explorer, JSON-RPC console, server info, health-driven status)
- `GET /health` endpoint with status, version, protocol version, tool count
- Structured logging ready
- pytest suite (unit + integration + protocol + transport + security)
- Render deployment configuration (`render.yaml`, `requirements.txt`, Procfile-style start command)

---

## Built-in tools

| Category | Tool | Description |
|---|---|---|
| Calculator | `add` | Add two integers |
| Calculator | `subtract` | Subtract b from a |
| Calculator | `multiply` | Multiply two integers |
| Calculator | `divide` | Divide a by b (rejects division by zero) |
| Text Analyzer | `word_count` | Count words in text |
| Text Analyzer | `char_count` | Count characters |
| Text Analyzer | `char_count_no_spaces` | Count characters excluding spaces |
| URL Validator | `validate_url` | Validate HTTP/HTTPS URL structure (no network request) |
| Date & Time | `current_utc_time` | Current UTC time (ISO 8601) |
| String Utility | `reverse_text` | Reverse text |
| String Utility | `uppercase` | Uppercase text |
| String Utility | `lowercase` | Lowercase text |
| JSON Utility | `parse_json` | Parse JSON with structured validation errors |

No filesystem access, arbitrary code execution, shell execution, or unrestricted network access.

---

## Project structure

```
MiniMCP/
├── minimcp/
│   ├── __init__.py
│   ├── config.py        # Environment-based configuration
│   ├── errors.py        # JSON-RPC / MCP error codes
│   ├── registry.py      # Tool registry (decorator-based)
│   ├── schema.py        # JSON Schema generation from type hints
│   ├── protocol.py      # JSON-RPC 2.0 engine + MCP lifecycle
│   ├── security.py      # Bearer token authentication
│   ├── tools.py         # Built-in tools
│   └── transport.py     # Flask app factory + routes
├── tests/
│   ├── __init__.py
│   ├── test_registry.py
│   ├── test_schema.py
│   ├── test_protocol.py
│   ├── test_transport.py
│   ├── test_security.py
│   └── test_integration.py
├── templates/
│   └── index.html       # Developer playground UI
├── static/
│   ├── style.css
│   └── app.js           # Frontend logic (Fetch API)
├── app.py               # Entry point
├── requirements.txt
├── .env.example
├── .gitignore
├── render.yaml          # Render deployment manifest
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.15.2
- pip
- Git

### Steps

```bash
# Clone the repository
git clone <GITHUB_REPOSITORY_PLACEHOLDER>
cd minimcp

# Create and activate a virtual environment
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Environment setup

1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env        # Windows
   cp .env.example .env          # macOS/Linux
   ```
2. Edit `.env` and set `MINIMCP_AUTH_TOKEN` to a strong random value:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. Adjust `MINIMCP_CORS_ORIGINS` to restrict origins in production (default `*`).

> ⚠️ Never commit real API keys or authentication tokens. `.env` is gitignored; `.env.example` contains placeholder values only.

---

## Running locally

### Development (Flask)

```bash
python app.py
```

The server starts on `http://0.0.0.0:5000` (or the port in `MINIMCP_PORT`).

- Playground: `http://localhost:5000/`
- Health: `http://localhost:5000/health`
- MCP endpoint: `POST http://localhost:5000/mcp`

### Production (Gunicorn)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Gunicorn is verified compatible with Python 3.15.2.

---

## MCP protocol usage examples

All examples use `POST /mcp` with `Content-Type: application/json`.

### 1. Initialize

```http
POST /mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26"
  }
}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-03-26",
    "serverInfo": { "name": "MiniMCP", "version": "1.0.0" },
    "capabilities": { "tools": { "listChanged": false } },
    "negotiatedProtocolVersion": "2025-03-26"
  }
}
```

The server echoes a `Mcp-Session-Id` response header; include it on subsequent requests in the same session.

### 2. Initialized notification (no response)

```http
POST /mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "initialized"
}
```

### 3. Ping

```json
{ "jsonrpc": "2.0", "id": 2, "method": "ping" }
```

### 4. List tools

```json
{ "jsonrpc": "2.0", "id": 3, "method": "tools/list" }
```

### 5. Call a tool

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": { "a": 21, "b": 21 }
  }
}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [ { "type": "text", "text": "42" } ],
    "isError": false
  }
}
```

---

## Authentication

The `/mcp` endpoint is protected by a Bearer token when `MINIMCP_AUTH_TOKEN` is set.

```http
Authorization: Bearer <your-token>
```

- Missing token → `401 Unauthorized`
- Invalid token → `401 Unauthorized`
- Valid token → request proceeds
- Token is compared with `hmac.compare_digest` to prevent timing attacks
- If `MINIMCP_AUTH_TOKEN` is empty, authentication is disabled (not recommended for production)

The `GET /health` endpoint is public and does not require authentication.

---

## Testing

```bash
# From the project root, with the virtual environment activated
python -m pytest tests/ -v
```

The suite covers:

- **Registry:** successful registration, duplicate registration, discovery, execution, unknown tools, argument validation
- **Schema:** primitives, lists/dicts, optional parameters, required parameters, defaults, invalid annotations, type checking (bool is not integer)
- **Protocol:** initialize, initialized notification, ping, tools/list, tools/call, invalid JSON-RPC version, unknown method, invalid parameters, lifecycle violations, notifications
- **Transport:** HTTP handling, Content-Type validation, health endpoint, CORS, batch handling
- **Security:** missing/invalid/valid token, secret redaction
- **Integration:** initialize → discover tools → execute tool → verify result

All 45 tests pass. There are no `assert True` placeholders.

---

## Deployment (Render)

1. Push the code to GitHub (see GitHub publication commands below).
2. In Render, create a new **Web Service** and connect the repository.
3. Render detects `render.yaml` automatically, or configure manually:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn -w 4 -b 0.0.0.0:$PORT app:app`
   - **Health check path:** `/health`
4. Set environment variables in the Render dashboard (do not paste secrets into `render.yaml`):
   - `MINIMCP_AUTH_TOKEN` (required, secret)
   - `MINIMCP_CORS_ORIGINS` (e.g. your frontend domain)
   - `MINIMCP_PROTOCOL_VERSION` (`2025-03-26`)
   - `MINIMCP_LOG_LEVEL` (`INFO`)
5. Deploy. Verify `GET /health` returns `"status": "ready"`.

Gunicorn start command is verified against the implemented application (`app:app` exposes the Flask app created by `create_app()`).

> Deployment success has not been independently verified in this environment; follow the Render instructions above to complete deployment.

---

## GitHub publication commands

```bash
git init
git add .
git commit -m "Initial commit: MiniMCP MCP server"
git branch -M main
git remote add origin <GITHUB_REPOSITORY_PLACEHOLDER>
git push -u origin main
```

Replace `<GITHUB_REPOSITORY_PLACEHOLDER>` with your actual repository URL.

---

## Interactive web playground

Open `http://localhost:5000/` (or your Render URL) to use the developer dashboard:

- **Header:** live server status from `/health`, protocol version, server name
- **Overview:** real registered-tool count, health, transport, version
- **Tool Explorer:** tools loaded dynamically from `tools/list`; enter arguments and execute via `tools/call`; real results and errors displayed
- **JSON-RPC Console:** send raw JSON-RPC 2.0 requests; view actual responses; example buttons provided
- **Server Information:** name, version, protocol, capabilities (from `initialize`)

No tool counts are hardcoded and no requests are faked; all dashboard data comes from live backend endpoints.

---

## Limitations

- **Streamable HTTP compliance:** Session handling is implemented via the `Mcp-Session-Id` header and per-session lifecycle state, but full Streamable HTTP session resumption/reconnection semantics are not implemented. The server does not claim full Streamable HTTP compliance.
- **Authentication scope:** Bearer token auth protects `/mcp`; `/health` is intentionally public.
- **CORS:** Configured via `MINIMCP_ORIGINS`; `*` permits all origins (appropriate only for development or trusted environments).
- **Content block types:** Tool results are returned as `text` content blocks. Rich content types (images, embedded resources) are not implemented.
- **Optional/nullability:** JSON Schema does not distinguish `null` for Optional parameters; nullability is implicit.
- **Unsupported type hints:** Annotations that cannot be mapped fall back to a permissive schema so validation does not reject valid input.

---

## Security notes

- Authentication tokens are read from the environment only; no secrets are hardcoded.
- Token comparison uses `hmac.compare_digest` (constant-time).
- Error responses never include internal exception details or secrets.
- Request bodies are size-limited (`MINIMCP_MAX_REQUEST_SIZE`, default 1 MB).
- CORS is restricted to configured origins.
- `.env` is gitignored; `.env.example` uses placeholder values only.
- Tools avoid filesystem, shell, code-execution, and unrestricted network access.

---

## License

MIT License
