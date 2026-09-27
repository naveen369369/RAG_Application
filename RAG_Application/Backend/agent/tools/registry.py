from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

from langchain_core.tools import BaseTool

from agent.tools.rag_retrieval import make_rag_retrieval_tool
from agent.tools.namespace_router import make_namespace_router_tool
from agent.tools.doc_summarizer import make_doc_summarizer_tool
from agent.tools.multi_namespace import make_multi_namespace_tool
from agent.tools.doc_metadata import make_doc_metadata_tool
from agent.tools.eval_trigger import make_eval_trigger_tool
from agent.tools.customer_lookup import make_customer_lookup_tool
from agent.tools.ticket_tools import make_ticket_lookup_tool, make_order_lookup_tool

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)


def build_agent_tools(pipeline: "RAGPipeline") -> List[BaseTool]:
    """
    Tools available to the ReAct agent.

    Priority order (LLM uses tool descriptions to decide):
      1. ticket_lookup    — get real support ticket details, subject, status, linked order
      2. order_lookup     — get real order details, shipping carrier, item conditions
      3. customer_lookup  — get customer tier/status for escalation/personalisation
      4. rag_retrieval    — primary document search (hybrid dense + BM25)
      5. route_namespace  — pick the best document namespace
      6. multi_namespace  — cross-namespace search for broad questions
      7. doc_summarizer   — summarise all content in a namespace
      8. doc_metadata     — list available documents/topics
      9. eval_trigger     — run retrieval quality evaluation (admin/testing)
     10. get_ticket             [MCP Server 2] — live ticket status & priority
     11. get_escalation_history [MCP Server 2] — full audit trail for a ticket
    """
    tools: List[BaseTool] = [
        make_ticket_lookup_tool(),               # real ticket lookup from DB
        make_order_lookup_tool(),                # real order lookup from DB
        make_customer_lookup_tool(),             # customer CRM context + escalation tier
        make_rag_retrieval_tool(pipeline),       # search documents (hybrid search)
        make_namespace_router_tool(pipeline),    # pick the right document category
        make_doc_summarizer_tool(pipeline),      # summarise all chunks in a namespace
        make_multi_namespace_tool(pipeline),     # search across multiple namespaces
        make_doc_metadata_tool(pipeline),        # list available documents / topics
        make_eval_trigger_tool(pipeline),        # run retrieval evaluation on demand
    ]

    # ── MCP Server 2: TicketHistoryServer ────────────────────────────────────
    # Dynamically discover and append remote tools via JSON-RPC tools/list.
    # Zero lines changed in react_agent.py — the agent treats MCP tools identically
    # to local tools. Gracefully degrades: if Server 2 is offline the agent still
    # runs with all 9 local tools above.
    try:
        import os
        import importlib.util
        client_path = os.path.join(os.path.dirname(__file__), "..", "..", "mcp", "mcp_client.py")
        if os.path.exists(client_path):
            spec = importlib.util.spec_from_file_location("local_mcp_client", os.path.abspath(client_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mcp_tools = mod.build_mcp_tools()
        else:
            from mcp.mcp_client import build_mcp_tools  # type: ignore
            mcp_tools = build_mcp_tools()

        if mcp_tools:
            logger.info(
                "MCP Server 2: %d remote tools discovered and added to agent: %s",
                len(mcp_tools), [t.name for t in mcp_tools],
            )
            tools.extend(mcp_tools)
    except Exception as exc:  # Server offline or import error — non-fatal
        logger.warning(
            "MCP Server 2 tools not loaded (server may be offline): %s", exc
        )

    return tools
