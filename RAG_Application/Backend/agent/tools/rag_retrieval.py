from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline


def make_rag_retrieval_tool(pipeline: "RAGPipeline"):
    @tool
    def rag_retrieval(
        query: str,
        namespace: str = "all",
        top_k: int = 5,
        use_hybrid: bool = True,
    ) -> dict:
        """
        Search the indexed documents for chunks relevant to a query.
        Use this before answering any question about company policies, shipping,
        returns, billing, or account management.

        Args:
            query:       The search query (rewrite vague questions to be specific).
            namespace:   Target namespace or 'all' for cross-namespace search.
            top_k:       Number of chunks to return (default 5).
            use_hybrid:  If True (default), uses hybrid dense+BM25 search for
                         better exact-match retrieval. Set False for speed.
        """
        if use_hybrid and hasattr(pipeline, "hybrid_retrieve"):
            matches = pipeline.hybrid_retrieve(
                query=query,
                namespace=namespace,
                top_k=top_k,
                score_threshold=pipeline.hit_threshold,
            )
        else:
            matches = pipeline.retrieve(
                query=query,
                namespace=namespace,
                top_k_override=top_k,
                score_threshold=pipeline.hit_threshold,
            )

        chunks = [
            {
                "text":        m["metadata"].get("text", ""),
                "source":      m["metadata"].get("source", ""),
                "score":       round(m.get("score", 0), 4),
                "dense_score": round(m.get("dense_score", m.get("score", 0)), 4),
                "bm25_score":  round(m.get("bm25_score", 0), 4),
                "chunk_index": m["metadata"].get("chunk_index", 0),
                "namespace":   m["metadata"].get("namespace", namespace),
            }
            for m in matches
        ]
        return {"chunks": chunks, "count": len(chunks), "hybrid": use_hybrid}

    return rag_retrieval
