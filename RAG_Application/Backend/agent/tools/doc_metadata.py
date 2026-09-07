from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline


def make_doc_metadata_tool(pipeline: "RAGPipeline"):
    @tool
    def inspect_documents(namespace: str = "all") -> dict:
        """
        List indexed documents, vector counts, and source file names.
        namespace: specific namespace to inspect, or 'all' for a full overview.
        Use when the user asks what documents are available or what topics are indexed.
        Does NOT retrieve document content — use rag_retrieval for that.
        """
        try:
            stats = pipeline.vector_db.index.describe_index_stats()
            ns_stats = stats.get("namespaces", {})

            if namespace == "all":
                result = {
                    "total_vectors": stats.get("total_vector_count", 0),
                    "dimension": stats.get("dimension", 0),
                    "namespaces": {
                        ns: {"vector_count": info.get("vector_count", 0)}
                        for ns, info in ns_stats.items()
                        if not ns.startswith("_")
                    },
                }
                return result

            ns_info = ns_stats.get(namespace, {})
            vector_count = ns_info.get("vector_count", 0)

            # Sample a few chunks to extract unique source file names
            sources: list[str] = []
            if vector_count > 0:
                sample = pipeline.retrieve(
                    query="document file source",
                    namespace=namespace,
                    top_k_override=10,
                    score_threshold=0.0,
                )
                seen: set[str] = set()
                for m in sample:
                    src = m["metadata"].get("source", "")
                    if src and src not in seen:
                        seen.add(src)
                        sources.append(src)

            return {
                "namespace": namespace,
                "vector_count": vector_count,
                "sources": sources,
                "dimension": stats.get("dimension", 0),
            }
        except Exception as exc:
            return {"error": str(exc)}

    return inspect_documents
