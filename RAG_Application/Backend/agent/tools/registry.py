from __future__ import annotations

from typing import TYPE_CHECKING, List

from langchain_core.tools import BaseTool

from agent.tools.rag_retrieval import make_rag_retrieval_tool
from agent.tools.namespace_router import make_namespace_router_tool
from agent.tools.doc_summarizer import make_doc_summarizer_tool
from agent.tools.multi_namespace import make_multi_namespace_tool
from agent.tools.doc_metadata import make_doc_metadata_tool
from agent.tools.eval_trigger import make_eval_trigger_tool

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline


def build_agent_tools(pipeline: "RAGPipeline") -> List[BaseTool]:
    """
    Tools available to the ReAct agent.
    Restricted to document-grounded tools only — the agent must answer
    exclusively from indexed company documents and refuse unrelated questions.
    """
    return [
        make_rag_retrieval_tool(pipeline),       # search documents in a namespace
        make_namespace_router_tool(pipeline),    # pick the right document category
        make_doc_summarizer_tool(pipeline),      # summarise all chunks in a namespace
        make_multi_namespace_tool(pipeline),     # search across multiple namespaces
        make_doc_metadata_tool(pipeline),        # list available documents / topics
        make_eval_trigger_tool(pipeline),        # run retrieval evaluation on demand
    ]
