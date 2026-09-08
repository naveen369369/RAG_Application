from __future__ import annotations

from typing import TYPE_CHECKING, List

from langchain_core.tools import BaseTool

from agent.tools.rag_retrieval import make_rag_retrieval_tool
from agent.tools.namespace_router import make_namespace_router_tool
from agent.tools.doc_summarizer import make_doc_summarizer_tool
from agent.tools.multi_namespace import make_multi_namespace_tool
from agent.tools.doc_metadata import make_doc_metadata_tool
from agent.tools.eval_trigger import make_eval_trigger_tool
from agent.tools.customer_lookup import make_customer_lookup_tool

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline


def build_agent_tools(pipeline: "RAGPipeline") -> List[BaseTool]:
    """
    Tools available to the ReAct agent.

    Priority order (LLM uses tool descriptions to decide):
      1. customer_lookup  — get customer tier/status for escalation/personalisation
      2. rag_retrieval    — primary document search (hybrid dense + BM25)
      3. route_namespace  — pick the best document namespace
      4. multi_namespace  — cross-namespace search for broad questions
      5. doc_summarizer   — summarise all content in a namespace
      6. doc_metadata     — list available documents/topics
      7. eval_trigger     — run retrieval quality evaluation (admin/testing)
    """
    return [
        make_customer_lookup_tool(),             # customer CRM context + escalation tier
        make_rag_retrieval_tool(pipeline),       # search documents (hybrid search)
        make_namespace_router_tool(pipeline),    # pick the right document category
        make_doc_summarizer_tool(pipeline),      # summarise all chunks in a namespace
        make_multi_namespace_tool(pipeline),     # search across multiple namespaces
        make_doc_metadata_tool(pipeline),        # list available documents / topics
        make_eval_trigger_tool(pipeline),        # run retrieval evaluation on demand
    ]
