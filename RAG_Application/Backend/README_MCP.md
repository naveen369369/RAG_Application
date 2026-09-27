# MCP (Model Context Protocol) Implementation Guide

## 1. Architecture: Host, MCP Client, and MCP Server
* **Host / Agent (`react_agent.py`)**: Runs the LLM (e.g. Groq LLaMA-3.3-70B). The Host maintains conversation memory, orchestrates reasoning trajectories (ReAct loop), and decides which tools to invoke.
* **MCP Client (`mcp_client.py` / FastMCP Client)**: The client-side adapter inside the Host application that connects to MCP servers, executes protocol handshakes (`initialize`), dynamically discovers tools (`tools/list`), and dispatches RPC invocations (`tools/call`).
* **MCP Server (`ticket_history_server.py`)**: A standalone process exposing capabilities over a standard transport. **Critical architectural rule**: The LLM runs exclusively in the Host/Agent; the MCP Server *never* imports or calls an LLM.

## 2. Tools, Resources, and Prompts
* **Tools**: Model-invoked operations (e.g., `get_ticket`, `get_escalation_history`). The LLM generates the parameters; the server executes and returns the result.
* **Resources**: Application-attached context blobs (e.g., `ticket://schema`, `ticket://active-count`) fetched by the host environment to ground discussions, not directly executed as actions by the model.
* **Prompts**: Reusable prompt templates (e.g., `escalation_summary_prompt`) parameterized by the host to enforce consistent prompting standards.

## 3. Transports: stdio vs. HTTP
* **stdio**: Communication happens across child-process standard input/output streams. Ideal for local tools, zero-network desktop assistants, and CLI agents.
* **HTTP / SSE (Server-Sent Events)**: Communication runs across HTTP POST requests and persistent SSE streams. Preferred for production and remote servers, enabling distributed microservices, load balancing, and network authentication.

## 4. JSON-RPC 2.0 Protocol Handshake
* `initialize`: Negotiates protocol versions and exchanges server/client capabilities and instructions.
* `tools/list`: Allows the Host to dynamically discover all server-side tools and their JSON schemas at runtime.
* `tools/call`: Dispatches a tool execution with structured arguments and returns multi-modal content parts.

Every message contains `jsonrpc: "2.0"` and a correlating `id`. Successes return `result`; failures return `error`.

## 5. Dynamic Discovery Without Modifying Agent Code
Server 2 (`TicketHistoryServer`) is introduced purely through `Backend/mcp/mcp_config.py`. The agent module `react_agent.py` remains 100% untouched (`0 changed lines` in `agent_diff.txt`), discovering tools dynamically at startup.

## 6. FastMCP Framework
Built using FastMCP, providing high-performance ASGI-compatible endpoints, automatic Pydantic-to-JSON-Schema conversion, and native SSE streaming.

## 7. Recoverable Error Semantics
Instead of returning opaque runtime exceptions (`500 Internal Server Error` or generic `Error 3`), errors are surfaced with structured domain diagnostics (`TICKET_NOT_FOUND`) and actionable docstrings. The LLM can interpret the explanation and guide the user to provide a valid ticket ID.

## 8. Remote Access & Bearer Authentication
All remote HTTP requests are guarded by `BearerAuthMiddleware`. Tokens are supplied via the `MCP_API_KEY` environment variable and never hard-coded in source files. Unauthorized requests are rejected immediately with HTTP 401 Unauthorized.

---

## Running and Verifying

### Step 1: Start MCP Server 2
```powershell
$env:MCP_API_KEY="mcp-secret-dev-token-2026"
$env:MCP_PORT="8100"
$env:MCP_TRANSPORT="http"
python mcp/ticket_history_server.py
```

### Step 2: Run End-to-End Validation
```powershell
$env:MCP_API_KEY="mcp-secret-dev-token-2026"
$env:MCP_SERVER2_URL="http://127.0.0.1:8100/mcp"
python mcp/validate_mcp.py
```
