"""
MCP Configuration — All MCP Servers
=====================================
This file registers all MCP servers available to the agent HOST.
Adding or removing a server here requires NO changes to the agent module (react_agent.py).

Server 1: CRM Agent Server  — 9 built-in local tools (runs inside the FastAPI process)
Server 2: TicketHistoryServer — 2 remote tools via HTTP/SSE on port 8100

Transport options per server:
  "http"  — remote HTTP/SSE  (preferred for Server 2, supports auth)
  "stdio" — local subprocess pipe (no network, simpler for dev)
  "local" — runs inside the same process (Server 1 — no TCP port needed)

Auth: Set MCP_API_KEY env var. Never hard-code secrets here.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# MCP server registry
# ---------------------------------------------------------------------------
# Each entry describes one MCP server the agent HOST can connect to.
# The agent HOST reads this config to discover tools dynamically:
# ZERO code changes required in the agent module (react_agent.py).

MCP_SERVERS: List[Dict[str, Any]] = [
    # ── Server 1: CRM Agent Server ───────────────────────────────────────────
    # Runs INSIDE the FastAPI process (local/in-process). No separate port.
    # All 9 tools are registered directly by agent/tools/registry.py.
    {
        "server_id":   "crm-agent-server-v1",
        "name":        "CRM Agent Server",
        "description": "Built-in agent tools for CRM lookups, RAG document search, and evaluation",
        "transport":   "local",
        "url":         None,  # No TCP port — runs in-process with the FastAPI backend
        "auth": {
            "type":  "none",
            "token": None,
        },
        "tools": [
            "ticket_lookup",
            "order_lookup",
            "customer_lookup",
            "rag_retrieval",
            "route_namespace",
            "summarize_document",
            "multi_namespace_search",
            "inspect_documents",
            "run_evaluation",
        ],
        "tool_categories": {
            "CRM": ["ticket_lookup", "order_lookup", "customer_lookup"],
            "RAG / Documents": ["rag_retrieval", "route_namespace", "summarize_document", "multi_namespace_search", "inspect_documents"],
            "Admin": ["run_evaluation"],
        },
        "enabled": True,
        "version": "1.0",
    },

    # ── Server 2: Ticket History Server ──────────────────────────────────────
    # Runs as a SEPARATE process on port 8100.
    # Start with: python mcp/ticket_history_server.py
    # Added purely via config; zero lines changed in react_agent.py.
    {
        "server_id":   "ticket-history-v2",
        "name":        "TicketHistoryServer",
        "description": "Provides get_ticket and get_escalation_history tools for customer ticket audit trails",
        "transport":   os.environ.get("MCP_TRANSPORT", "http"),
        "url":         os.environ.get("MCP_SERVER2_URL", "http://127.0.0.1:8100/mcp"),
        "auth": {
            "type":  "bearer",
            "token": os.environ.get("MCP_API_KEY", ""),  # Read from environment, NEVER hard-coded
        },
        "tools": [
            "get_ticket",
            "get_escalation_history",
        ],
        "tool_categories": {
            "Ticket Audit": ["get_ticket", "get_escalation_history"],
        },
        "enabled": True,
        "version": "2.0",
    },
]


def get_enabled_servers() -> List[Dict[str, Any]]:
    """Return only enabled server entries."""
    return [s for s in MCP_SERVERS if s.get("enabled", True)]


def get_server_by_id(server_id: str) -> Dict[str, Any] | None:
    """Return a specific server config by its server_id."""
    return next((s for s in MCP_SERVERS if s["server_id"] == server_id), None)
