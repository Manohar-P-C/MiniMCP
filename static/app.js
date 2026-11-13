/* MiniMCP Developer Playground - frontend logic.
   All data comes from the real backend endpoints (/health, POST /mcp).
   Nothing is hardcoded or faked. */

(function () {
  const BASE = "";
  const MCP_PATH = "/mcp";
  const HEALTH_PATH = "/health";

  const tokenInput = document.getElementById("tokenInput");
  const refreshBtn = document.getElementById("refreshBtn");
  const statusChip = document.getElementById("statusChip");
  const statusText = document.getElementById("statusText");
  const protocolVersionEl = document.getElementById("protocolVersion");
  const serverNameEl = document.getElementById("serverName");

  const statTools = document.getElementById("statTools");
  const statStatus = document.getElementById("statStatus");
  const statTransport = document.getElementById("statTransport");
  const statVersion = document.getElementById("statVersion");

  const toolFilter = document.getElementById("toolFilter");
  const toolGrid = document.getElementById("toolGrid");
  const toolCountBadge = document.getElementById("toolCountBadge");
  const toolResult = document.getElementById("toolResult");

  const rpcRequest = document.getElementById("rpcRequest");
  const rpcResponse = document.getElementById("rpcResponse");
  const sendRpcBtn = document.getElementById("sendRpcBtn");
  const clearRpcBtn = document.getElementById("clearRpcBtn");

  const infoName = document.getElementById("infoName");
  const infoVersion = document.getElementById("infoVersion");
  const infoProtocol = document.getElementById("infoProtocol");
  const infoCapabilities = document.getElementById("infoCapabilities");

  // Restore persisted token.
  try {
    const saved = localStorage.getItem("minimcp_token");
    if (saved) tokenInput.value = saved;
  } catch (e) { /* ignore */ }
  tokenInput.addEventListener("input", () => {
    try { localStorage.setItem("minimcp_token", tokenInput.value); } catch (e) { /* ignore */ }
  });

  let sessionId = null;

  function authHeaders() {
    const headers = { "Content-Type": "application/json", Accept: "application/json" };
    const token = tokenInput.value.trim();
    if (token) headers["Authorization"] = "Bearer " + token;
    if (sessionId) headers["Mcp-Session-Id"] = sessionId;
    return headers;
  }

  async function request(payload) {
    const resp = await fetch(MCP_PATH, {
      method: "POST",
      headers: authHeaders(),
      body: typeof payload === "string" ? payload : JSON.stringify(payload),
    });
    const text = await resp.text();
    let data = null;
    if (text) {
      try { data = JSON.parse(text); } catch (e) { data = { _raw: text }; }
    }
    // Capture session id returned by the server.
    const sid = resp.headers.get("Mcp-Session-Id");
    if (sid) sessionId = sid;
    return { status: resp.status, data, ok: resp.ok };
  }

  function setStatus(online, message) {
    if (online) {
      statusChip.classList.remove("offline");
      statusChip.classList.add("online");
      statusText.textContent = message || "online";
      statusChip.querySelector(".dot").classList.add("online");
    } else {
      statusChip.classList.remove("online");
      statusChip.classList.add("offline");
      statusText.textContent = message || "offline";
      statusChip.querySelector(".dot").classList.remove("online");
    }
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderJson(value) {
    if (value == null) return "null";
    if (typeof value === "string") return value;
    return JSON.stringify(value, null, 2);
  }

  // ---------- Health / overview ----------
  async function loadHealth() {
    try {
      const resp = await fetch(HEALTH_PATH, { headers: { Accept: "application/json" } });
      const data = await resp.json();
      statTools.textContent = data.toolCount == null ? "-" : data.toolCount;
      statStatus.textContent = data.status || "-";
      statStatus.style.color = data.status === "ready" ? "var(--success)" : "var(--danger)";
      statTransport.textContent = data.transport || "-";
      statVersion.textContent = data.version || "-";
      setStatus(data.status === "ready", data.status || "-");
    } catch (e) {
      statTools.textContent = "-";
      statStatus.textContent = "unreachable";
      statStatus.style.color = "var(--danger)";
      statTransport.textContent = "-";
      statVersion.textContent = "-";
      setStatus(false, "unreachable");
    }
  }

  // ---------- Tool explorer ----------
  async function loadTools() {
    const res = await request({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/list",
    });
    toolGrid.innerHTML = "";
    if (res.status !== 200 || !res.data || !res.data.result) {
      toolGrid.innerHTML = '<div class="empty">Unable to load tools (' + (res.data && res.data.error ? res.data.error.message : res.status) + ").</div>";
      toolCountBadge.textContent = "-";
      return;
    }
    const tools = res.data.result.tools || [];
    toolCountBadge.textContent = tools.length + " tools";
    let html = "";
    for (const tool of tools) {
      html += renderToolCard(tool);
    }
    toolGrid.innerHTML = html;
    attachToolExecHandlers();
  }

  function renderToolCard(tool) {
    const schema = tool.inputSchema || {};
    const props = schema.properties || {};
    const required = schema.required || [];
    let argsHtml = "";
    for (const [name, spec] of Object.entries(props)) {
      const req = required.includes(name);
      const type = spec.type || "any";
      const def = "default" in spec ? " (default: " + escapeHtml(String(spec.default)) + ")" : "";
      const inputId = "arg_" + tool.name + "_" + name;
      const isTextarea = type === "string" && (spec.default || "").length > 40;
      const tag = isTextarea ? "textarea" : "input";
      const valueAttr = spec.default != null ? ` value="${escapeHtml(String(spec.default))}"` : "";
      argsHtml += `
        <div class="arg-row">
          <label class="${req ? 'arg-required' : ''}">${escapeHtml(name)}</label>
          <div class="arg-type">${type}${def}${req ? " required" : ""}</div>
          <${tag} id="${inputId}" data-tool="${escapeHtml(tool.name)}" data-param="${escapeHtml(name)}" data-type="${escapeHtml(type)}" placeholder="${req ? "required" : "optional"}"${valueAttr}></${tag}>
        </div>`;
    }
    return `
      <div class="tool-card">
        <div class="tool-header">
          <div class="tool-name">${escapeHtml(tool.name)}</div>
          <span class="chip" style="border:none;background:transparent;padding:0;font-size:0.7rem;color:var(--text-muted);">tool</span>
        </div>
        <p class="tool-desc">${escapeHtml(tool.description || "")}</p>
        <div class="tool-args">${argsHtml}</div>
        <div class="tool-actions">
          <button class="exec-btn" data-tool="${escapeHtml(tool.name)}">Execute</button>
        </div>
      </div>`;
  }

  function attachToolExecHandlers() {
    document.querySelectorAll(".exec-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const toolName = btn.getAttribute("data-tool");
        const card = btn.closest(".tool-card");
        const args = {};
        let valid = true;
        card.querySelectorAll("input, textarea").forEach((el) => {
          const name = el.getAttribute("data-param");
          const type = el.getAttribute("data-type");
          const raw = el.value.trim();
          if (raw === "") return;
          try {
            if (type === "number") args[name] = Number(raw);
            else if (type === "integer") args[name] = parseInt(raw, 10);
            else if (type === "boolean") args[name] = raw.toLowerCase() === "true";
            else args[name] = raw;
          } catch (e) {
            valid = false;
          }
        });
        if (!valid) {
          showToolResult("error", "Invalid argument values.");
          return;
        }
        btn.textContent = "Running&hellip;";
        btn.disabled = true;
        try {
          const res = await request({
            jsonrpc: "2.0",
            id: Date.now(),
            method: "tools/call",
            params: { name: toolName, arguments: args },
          });
          const data = res.data || {};
          if (res.status === 200 && data.result) {
            showToolResult("ok", data.result);
          } else {
            showToolResult("error", data.error || { message: "Request failed (" + res.status + ")" });
          }
        } catch (e) {
          showToolResult("error", { message: e.message || String(e) });
        } finally {
          btn.textContent = "Execute";
          btn.disabled = false;
        }
      });
    });
  }

  function showToolResult(kind, payload) {
    toolResult.classList.remove("hidden");
    toolResult.className = "result-panel " + (kind === "error" ? "is-error" : "result-ok");
    let body;
    if (kind === "ok") {
      const content = payload && payload.content;
      if (Array.isArray(content) && content[0] && content[0].text !== undefined) {
        body = content[0].text;
      } else {
        body = renderJson(payload);
      }
      toolResult.innerHTML = `<div class="result-title"><span style="color:var(--success)">&#10003;</span> OK</div><pre>${escapeHtml(body)}</pre>`;
    } else {
      const msg = payload && payload.message ? payload.message : renderJson(payload);
      const code = payload && payload.code != null ? " (code " + payload.code + ")" : "";
      toolResult.innerHTML = `<div class="result-title"><span style="color:var(--danger)">&#10007;</span> Error${escapeHtml(code)}</div><pre>${escapeHtml(msg)}</pre>`;
    }
    toolResult.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  toolFilter.addEventListener("input", () => {
    const term = toolFilter.value.toLowerCase();
    document.querySelectorAll(".tool-card").forEach((card) => {
      const name = card.querySelector(".tool-name").textContent.toLowerCase();
      const desc = card.querySelector(".tool-desc").textContent.toLowerCase();
      card.style.display = name.includes(term) || desc.includes(term) ? "" : "none";
    });
  });

  // ---------- JSON-RPC console ----------
  const EXAMPLES = {
    list: {
      jsonrpc: "2.0",
      id: 1,
      method: "tools/list",
    },
    call: {
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: { name: "add", arguments: { a: 40, b: 2 } },
    },
    init: {
      jsonrpc: "2.0",
      id: 3,
      method: "initialize",
      params: { protocolVersion: "2025-03-26" },
    },
    ping: {
      jsonrpc: "2.0",
      id: 4,
      method: "ping",
    },
    bad: "not valid json",
  };

  document.querySelectorAll(".example-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const ex = EXAMPLES[btn.getAttribute("data-example")];
      rpcRequest.value = typeof ex === "string" ? ex : JSON.stringify(ex, null, 2);
    });
  });

  clearRpcBtn.addEventListener("click", () => {
    rpcResponse.textContent = "Response will appear here&hellip;";
  });

  sendRpcBtn.addEventListener("click", async () => {
    sendRpcBtn.textContent = "Sending&hellip;";
    sendRpcBtn.disabled = true;
    rpcResponse.textContent = "Sending&hellip;";
    try {
      const raw = rpcRequest.value.trim();
      let payload;
      try {
        payload = raw ? JSON.parse(raw) : null;
      } catch (e) {
        rpcResponse.textContent = "Invalid JSON in request editor: " + e.message;
        return;
      }
      if (!payload) {
        rpcResponse.textContent = "Empty request.";
        return;
      }
      const res = await request(payload);
      rpcResponse.textContent = renderJson(res.data || { _status: res.status, _note: "empty response" });
    } catch (e) {
      rpcResponse.textContent = "Request failed: " + (e.message || String(e));
    } finally {
      sendRpcBtn.textContent = "Send request";
      sendRpcBtn.disabled = false;
    }
  });

  // ---------- Server information ----------
  async function loadServerInfo() {
    const res = await request({
      jsonrpc: "2.0",
      id: Date.now(),
      method: "initialize",
      params: { protocolVersion: "2025-03-26" },
    });
    if (res.status === 200 && res.data && res.data.result) {
      const r = res.data.result;
      const si = r.serverInfo || {};
      infoName.textContent = si.name || "-";
      infoVersion.textContent = si.version || "-";
      infoProtocol.textContent = r.protocolVersion || "-";
      infoCapabilities.textContent = renderJson(r.capabilities || {});
      protocolVersionEl.textContent = r.protocolVersion || "-";
      serverNameEl.textContent = si.name || "-";
    } else {
      infoName.textContent = "-";
      infoVersion.textContent = "-";
      infoProtocol.textContent = "-";
      infoCapabilities.textContent = "-";
    }
  }

  // ---------- Bootstrap ----------
  refreshBtn.addEventListener("click", async () => {
    await loadHealth();
    await loadTools();
    await loadServerInfo();
  });

  loadHealth();
  loadTools();
  loadServerInfo();
})();
