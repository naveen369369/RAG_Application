from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline


def make_namespace_router_tool(pipeline: "RAGPipeline"):
    @tool
    def route_namespace(question: str) -> dict:
        """
        Classify which document namespace best matches a question.
        Call this when the user hasn't specified a namespace.
        Returns the namespace name and a confidence level.
        Does NOT retrieve documents — use rag_retrieval after this.
        """
        namespaces = pipeline.get_namespaces()
        if not namespaces:
            return {"namespace": "all", "confidence": "low", "reason": "no namespaces found"}

        ns_list = ", ".join(namespaces)
        prompt = (
            f"Available namespaces: {ns_list}\n\n"
            f'Question: "{question}"\n\n'
            "Return ONLY the single namespace name that best matches this question, "
            "or 'all' if the question is ambiguous or spans multiple topics. "
            "No explanation, just the namespace name."
        )
        try:
            chosen = pipeline.llm.generate(
                query=prompt,
                context_chunks=[],
                temperature=0.0,
                max_tokens=64,
            ).strip().strip('"').strip("'")
            confidence = "high" if chosen in namespaces else "low"
            if chosen not in namespaces and chosen != "all":
                chosen = "all"
                confidence = "low"
        except Exception:
            chosen = "all"
            confidence = "low"

        return {"namespace": chosen, "confidence": confidence}

    return route_namespace
