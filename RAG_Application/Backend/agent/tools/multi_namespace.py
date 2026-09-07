from __future__ import annotations

from typing import TYPE_CHECKING, List

from langchain_core.tools import tool

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline


def make_multi_namespace_tool(pipeline: "RAGPipeline"):
    @tool
    def multi_namespace_search(
        query: str,
        namespaces: List[str] = [],
        top_k_per_namespace: int = 3,
    ) -> dict:
        """
        Search across multiple namespaces simultaneously and synthesize results.
        namespaces: list of namespace names; empty list = search all namespaces.
        Returns per-namespace chunk results and a synthesized answer.
        Use when a question spans multiple document topics.
        """
        top_k_per_namespace = min(top_k_per_namespace, 5)
        target_ns = namespaces if namespaces else pipeline.get_namespaces()
        if not target_ns:
            return {"per_namespace": {}, "synthesis": "No namespaces available."}

        per_namespace: dict[str, list] = {}
        for ns in target_ns:
            try:
                matches = pipeline.retrieve(
                    query=query,
                    namespace=ns,
                    top_k_override=top_k_per_namespace,
                    score_threshold=0.0,
                )
                per_namespace[ns] = [
                    {"text": m["metadata"].get("text", ""), "score": round(m["score"], 4)}
                    for m in matches
                ]
            except Exception:
                per_namespace[ns] = []

        all_chunks = [
            chunk["text"]
            for chunks in per_namespace.values()
            for chunk in chunks
            if chunk["text"]
        ]
        if not all_chunks:
            return {"per_namespace": per_namespace, "synthesis": "No relevant content found."}

        synthesis = pipeline.llm.generate(
            query=query,
            context_chunks=all_chunks,
            temperature=0.2,
            max_tokens=512,
        )
        return {"per_namespace": per_namespace, "synthesis": synthesis}

    return multi_namespace_search
