from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline


def make_rag_retrieval_tool(pipeline: "RAGPipeline"):
    @tool
    def rag_retrieval(query: str, namespace: str = "all", top_k: int = 5) -> dict:
        """
        Search the indexed documents for chunks relevant to a query.
        Use this before answering any question about company policies, shipping,
        returns, billing, or account management.
        namespace: target namespace or 'all' for cross-namespace search.
        """

        matches = pipeline.retrieve(
            query=query,
            namespace=namespace,
            top_k_override=top_k,
            score_threshold=pipeline.hit_threshold,
        )
        chunks = [
            {
                "text": m["metadata"].get("text", ""),
                "source": m["metadata"].get("source", ""),
                "score": round(m["score"], 4),
                "chunk_index": m["metadata"].get("chunk_index", 0),
                "namespace": m["metadata"].get("namespace", namespace),
            }
            for m in matches
        ]
        return {"chunks": chunks, "count": len(chunks)}

    return rag_retrieval
