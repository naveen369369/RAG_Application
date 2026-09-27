"""
MCP Client — connects to registered MCP servers and discovers tools.
====================================================================
This client is the HOST-side adapter that:
  1. Reads mcp_config.py for server URLs / auth.
  2. Calls initialize → tools/list to discover tools dynamically.
  3. Wraps each remote tool as a LangChain BaseTool so the agent graph
     can call it transparently.

The agent module (react_agent.py) is NOT modified.
The LLM runs exclusively in the Agent/Host — never inside the MCP server.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level JSON-RPC helper
# ---------------------------------------------------------------------------

class MCPJsonRpcClient:
    """
    Minimal synchronous JSON-RPC 2.0 client for MCP over HTTP.
    Covers: initialize → tools/list → tools/call
    """

    def __init__(self, base_url: str, api_key: str = "", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key  = api_key
        self.timeout  = timeout
        self._id      = 0

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _call(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id":      self._next_id(),
            "method":  method,
        }
        if params:
            payload["params"] = params
        resp = httpx.post(
            self.base_url,
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def initialize(self) -> Dict[str, Any]:
        return self._call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "rag-agent-host", "version": "1.0.0"},
        })

    def list_tools(self) -> List[Dict[str, Any]]:
        result = self._call("tools/list")
        return result.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._call("tools/call", {
            "name":      tool_name,
            "arguments": arguments,
        })


# ---------------------------------------------------------------------------
# LangChain Tool wrapper
# ---------------------------------------------------------------------------

class RemoteMCPTool(BaseTool):
    """
    Wraps a single MCP server tool as a LangChain BaseTool.
    The agent graph treats it identically to local tools.
    """
    name:        str = Field(...)
    description: str = Field(...)
    server_url:  str = Field(...)
    api_key:     str = Field(default="")

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **kwargs: Any) -> Any:
        if "kwargs" in kwargs and isinstance(kwargs["kwargs"], dict):
            kwargs = kwargs["kwargs"]
        import asyncio
        import concurrent.futures
        from fastmcp import Client

        async def _call():
            async with Client(self.server_url, auth=self.api_key or None) as client:
                resp = await client.call_tool(self.name, kwargs)
                if resp.content and hasattr(resp.content[0], "text"):
                    raw = resp.content[0].text
                    try:
                        return json.loads(raw)
                    except Exception:
                        return raw
                return str(resp)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(_call())).result()

    async def _arun(self, **kwargs: Any) -> Any:
        if "kwargs" in kwargs and isinstance(kwargs["kwargs"], dict):
            kwargs = kwargs["kwargs"]
        from fastmcp import Client
        async with Client(self.server_url, auth=self.api_key or None) as client:
            resp = await client.call_tool(self.name, kwargs)
            if resp.content and hasattr(resp.content[0], "text"):
                raw = resp.content[0].text
                try:
                    return json.loads(raw)
                except Exception:
                    return raw
            return str(resp)


# ---------------------------------------------------------------------------
# Discovery: build LangChain tools from all configured MCP servers
# ---------------------------------------------------------------------------

def build_mcp_tools() -> List[BaseTool]:
    """
    Read mcp_config.py, connect to each enabled MCP server, call tools/list,
    and return a list of RemoteMCPTool instances ready for the agent.

    This is called once at agent startup; no code in react_agent.py changes.
    """
    get_enabled_servers = None
    try:
        from mcp.mcp_config import get_enabled_servers
    except (ImportError, ModuleNotFoundError):
        pass

    if get_enabled_servers is None:
        try:
            import mcp_config
            get_enabled_servers = mcp_config.get_enabled_servers
        except (ImportError, ModuleNotFoundError):
            pass

    if get_enabled_servers is None:
        try:
            import importlib.util
            cfg_path = os.path.join(os.path.dirname(__file__), "mcp_config.py")
            spec = importlib.util.spec_from_file_location("local_mcp_config", cfg_path)
            cfg_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cfg_mod)
            get_enabled_servers = cfg_mod.get_enabled_servers
        except Exception:
            logger.warning("mcp_config not found — no remote MCP tools loaded.")
            return []

    tools: List[BaseTool] = []
    import asyncio
    import concurrent.futures
    from fastmcp import Client

    for server_cfg in get_enabled_servers():
        url     = server_cfg.get("url", "")
        api_key = server_cfg.get("auth", {}).get("token", "") or os.environ.get("MCP_API_KEY", "")
        sid     = server_cfg.get("server_id", "unknown")

        if not url:
            logger.warning("Server %s has no URL — skipping.", sid)
            continue

        try:
            async def _discover():
                async with Client(url, auth=api_key or None) as c:
                    return await c.list_tools()

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                remote_tools = pool.submit(lambda: asyncio.run(_discover())).result()

            logger.info("MCP server '%s' exposes %d tools: %s",
                        sid, len(remote_tools), [t.name for t in remote_tools])
            for tool_def in remote_tools:
                t = RemoteMCPTool(
                    name=tool_def.name,
                    description=tool_def.description or "Remote MCP tool",
                    server_url=url,
                    api_key=api_key,
                )
                tools.append(t)
        except Exception as exc:
            logger.warning("Could not connect to MCP server '%s': %s", sid, exc)

    return tools
