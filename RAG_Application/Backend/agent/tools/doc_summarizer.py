from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline


def make_doc_summarizer_tool(pipeline: "RAGPipeline"):
    @tool
    def summarize_document(namespace: str, max_chunks: int = 20) -> dict:
        """
        Retrieve and summarize all documents in a given namespace.
        max_chunks caps the number of chunks included (cost guard, max 20).
        Use when the user asks for a summary or overview of a topic area.
        Does NOT answer specific questions — use rag_retrieval for that.
        """
        max_chunks = min(max_chunks, 20)
        try:
            # Query with a broad semantic term to pull representative chunks
            matches = pipeline.retrieve(
                query="overview summary main topics key information",
                namespace=namespace,
                top_k_override=max_chunks,
                score_threshold=0.0,
            )
            if not matches:
                return {"summary": "No documents found in this namespace.", "chunks_used": 0}

            texts = [m["metadata"].get("text", "") for m in matches if m["metadata"].get("text")]
            summary = pipeline.llm.generate(
                query="Provide a comprehensive 3-5 sentence summary of all the information in the following document chunks.",
                context_chunks=texts,
                temperature=0.1,
                max_tokens=512,
            )
            return {"summary": summary, "chunks_used": len(texts)}
        except Exception as exc:
            return {"error": str(exc), "summary": "", "chunks_used": 0}

    return summarize_document
