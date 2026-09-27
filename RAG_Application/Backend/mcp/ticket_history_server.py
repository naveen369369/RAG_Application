"""
MCP Server 2 — Ticket History Server
=====================================
Architecture
------------
  Host/Agent  : The ReAct agent (react_agent.py) that runs the LLM (Groq).
  MCP Client  : The adapter layer that discovers and calls this server.
  MCP Server  : THIS FILE. No LLM call is ever made here.

Responsibilities
----------------
  Tools     — model-invoked actions: get_ticket, get_escalation_history
  Resources — application-attached context blobs exposed to the host (not called by model)
  Prompts   — reusable prompt templates the host can inject

Transport : HTTP/SSE (default port 8100) or stdio
Auth      : Bearer token read from MCP_API_KEY environment variable. Never hard-coded.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Optional

from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
import uvicorn
import sys
from pathlib import Path

# Ensure Backend root is in sys.path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from database.session import get_db_session
from database.models import SupportTicket, TicketEscalationEvent
from database.seed import init_db

# ── Auth & Config ─────────────────────────────────────────────────────────────
# Token is read ONLY from the environment – it is never hard-coded here.
_API_KEY: str = os.environ.get("MCP_API_KEY", "")

logger = logging.getLogger(__name__)

# Ensure tables and seed data exist in real database on startup
try:
    init_db()
except Exception as _e:
    logger.warning("Database init_db notice: %s", _e)

# ── FastMCP app ────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "TicketHistoryServer",
    instructions=(
        "This MCP server exposes ticket details and escalation history tools. "
        "Use get_ticket to check ticket status and priority. "
        "Use get_escalation_history to retrieve the full audit trail of actions taken "
        "on a ticket, including agent names, timestamps, and notes. "
        "Ticket IDs must follow the format TCK-NNNN (e.g. TCK-1004, TCK-1001). "
        "The LLM that calls these tools runs in the Host/Agent; this server never calls any LLM."
    ),
)


# ── Tools ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_ticket(ticket_id: str) -> dict:
    """
    Retrieve the current status, priority, subject, and resolution notes for a support ticket.

    Use this tool when:
    - The user asks about a ticket's current state (e.g. 'What is the status of TCK-1004?').
    - You need the ticket subject, category, or resolution notes before fetching history.

    Args:
        ticket_id: Ticket identifier in the format TCK-NNNN (e.g. TCK-1004).
                   Do NOT pass raw numbers like '4471'; always include the 'TCK-' prefix.

    Returns:
        A dict with keys: found, id, subject, status, priority, customer_id,
        created_at, category, resolution_notes.

    Errors (recoverable):
        If the ticket is not found, the response contains:
          {"found": False, "error": "TICKET_NOT_FOUND",
           "message": "Ticket TCK-9999 was not found. IDs should look like TCK-nnnn."}
        The model should inform the customer the ticket was not found and ask
        them to verify the ticket number.
    """
    tid = ticket_id.strip().upper()
    db = get_db_session()
    try:
        ticket = db.query(SupportTicket).filter(SupportTicket.id == tid).first()
        if not ticket:
            return {
                "found": False,
                "error": "TICKET_NOT_FOUND",
                "ticket_id": tid,
                "message": (
                    f"Ticket {tid} was not found. "
                    "IDs should look like TCK-nnnn (e.g. TCK-1004). "
                    "Please ask the customer to verify their ticket number."
                ),
            }
        return {
            "found": True,
            "id": ticket.id,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "customer_id": ticket.customer_id,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "category": ticket.category,
            "resolution_notes": ticket.resolution_notes,
        }
    finally:
        db.close()


@mcp.tool()
def get_escalation_history(ticket_id: str) -> dict:
    """
    Retrieve the full chronological escalation and action history for a ticket.

    Use this tool when:
    - The user asks what happened with a ticket, who handled it, or how it was resolved.
    - You need the audit trail of agents, supervisors, or automated actions taken.

    Args:
        ticket_id: Ticket identifier in the format TCK-NNNN (e.g. TCK-1004).
                   Do NOT pass raw numbers like '4471'; always include the 'TCK-' prefix.

    Returns:
        A dict with keys: found, ticket_id, event_count, history (list of events).
        Each event has: timestamp, actor, action, note.

    Errors (recoverable):
        If no history exists:
          {"found": False, "error": "NO_HISTORY",
           "message": "No escalation history found for TCK-9999. IDs should look like TCK-nnnn."}
        If the ticket exists but has no history yet, event_count will be 0.
    """
    tid = ticket_id.strip().upper()
    db = get_db_session()
    try:
        events = (
            db.query(TicketEscalationEvent)
            .filter(TicketEscalationEvent.ticket_id == tid)
            .order_by(TicketEscalationEvent.timestamp.asc())
            .all()
        )
        if not events:
            ticket = db.query(SupportTicket).filter(SupportTicket.id == tid).first()
            if not ticket:
                return {
                    "found": False,
                    "error": "TICKET_NOT_FOUND",
                    "ticket_id": tid,
                    "message": (
                        f"Ticket {tid} was not found in the database. "
                        "IDs should look like TCK-nnnn (e.g. TCK-1004)."
                    ),
                }
            return {
                "found": False,
                "error": "NO_HISTORY",
                "ticket_id": tid,
                "message": (
                    f"No escalation history found for {tid}. "
                    "IDs should look like TCK-nnnn (e.g. TCK-1004). "
                    "Please ask the customer to verify their ticket number."
                ),
            }

        history = [
            {
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                "actor": ev.actor,
                "action": ev.action,
                "note": ev.note,
            }
            for ev in events
        ]
        return {
            "found": True,
            "ticket_id": tid,
            "event_count": len(history),
            "history": history,
        }
    finally:
        db.close()


# ── Resources ──────────────────────────────────────────────────────────────────

@mcp.resource("ticket://schema")
def ticket_schema() -> str:
    """
    Provides the JSON schema for a support ticket used by this server.
    This is a Resource: it is attached to the host application context,
    not invoked by the LLM model directly.
    """
    return """{
  "type": "object",
  "properties": {
    "id":              {"type": "string",  "example": "TCK-1004"},
    "subject":         {"type": "string"},
    "status":          {"type": "string",  "enum": ["open","escalated","resolved","closed"]},
    "priority":        {"type": "string",  "enum": ["low","standard","high","critical"]},
    "customer_id":     {"type": "string"},
    "created_at":      {"type": "string",  "format": "date-time"},
    "category":        {"type": "string"},
    "resolution_notes":{"type": ["string","null"]}
  }
}"""


@mcp.resource("ticket://active-count")
def active_ticket_count() -> str:
    """Live count of open/escalated tickets from real database (Resource, not a Tool)."""
    db = get_db_session()
    try:
        count = db.query(SupportTicket).filter(
            SupportTicket.status.in_(["open", "escalated"])
        ).count()
        return str(count)
    finally:
        db.close()


# ── Prompts ────────────────────────────────────────────────────────────────────

@mcp.prompt()
def escalation_summary_prompt(ticket_id: str) -> str:
    """
    Reusable prompt template a host can inject when summarising an escalation.
    Prompts are template strings, not LLM calls — the LLM runs in the Host.
    """
    return (
        f"You are a customer support supervisor reviewing ticket {ticket_id}. "
        "Using the escalation history retrieved by the tool, write a concise paragraph "
        "explaining: (1) when the ticket was opened, (2) why it was escalated, "
        "(3) what resolution was applied, and (4) the current status. "
        "Use factual language; do not invent details."
    )


# ── Auth Middleware ────────────────────────────────────────────────────────────

class BearerAuthMiddleware(BaseHTTPMiddleware):
    """
    Enforces Bearer authentication on all HTTP endpoints when MCP_API_KEY is set.
    Rejects unauthorized requests with 401 Unauthorized.
    """
    async def dispatch(self, request: Request, call_next):
        api_key = os.environ.get("MCP_API_KEY", "")
        if api_key:
            auth_header = request.headers.get("authorization", "")
            if not auth_header or auth_header != f"Bearer {api_key}":
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32000,
                            "message": "Unauthorized: Invalid or missing Bearer token",
                        },
                        "id": None,
                    },
                    status_code=401,
                )
        return await call_next(request)


# ── Entrypoint ─────────────────────────────────────────────────────────────────

def start_server():
    port = int(os.environ.get("MCP_PORT", "8100"))
    transport = os.environ.get("MCP_TRANSPORT", "http").lower()
    api_key = os.environ.get("MCP_API_KEY", "")

    print(f"[TicketHistoryServer] Starting on transport={transport} port={port}", flush=True)
    print(f"[TicketHistoryServer] Auth: {'enabled (token checked)' if api_key else 'DISABLED (dev mode)'}", flush=True)
    print("[TicketHistoryServer] NOTE: No LLM calls happen inside this server.", flush=True)

    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        app = mcp.http_app()
        if api_key:
            app.add_middleware(BearerAuthMiddleware)
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    start_server()
