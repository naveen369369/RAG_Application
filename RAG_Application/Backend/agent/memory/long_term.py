from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, List, Dict

from langchain_core.messages import SystemMessage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline

SUMMARY_THRESHOLD = 20   # number of messages before compressing


class LongTermMemory:
    """
    Two-layer long-term memory:
      Layer A — mem0: persistent user-level facts (extracted + deduplicated automatically)
      Layer B — Vector summarisation: compress old turns into Pinecone (_session_summaries ns)
    """

    def __init__(self, pipeline: "RAGPipeline") -> None:
        self.pipeline = pipeline
        self._mem = self._build_mem0()

    def _build_mem0(self):
        try:
            from mem0 import Memory
            config = {
                "llm": {
                    "provider": "groq",
                    "config": {
                        "model": os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile").removeprefix("groq/"),
                        "api_key": os.getenv("GROQ_API_KEY", ""),
                    },
                },
                "vector_store": {
                    "provider": "pinecone",
                    "config": {
                        "api_key": os.getenv("PINECONE_API_KEY", ""),
                        "collection_name": os.getenv("PINECONE_INDEX_NAME", "rag-index"),
                        "embedding_model_dims": 384,
                    },
                },
                "embedder": {
                    "provider": "huggingface",
                    "config": {"model": "all-MiniLM-L6-v2"},
                },
            }
            mem = Memory.from_config(config)
            logger.info("LongTermMemory: mem0 initialised with Pinecone backend")
            return mem
        except Exception as exc:
            logger.warning("LongTermMemory: mem0 unavailable (%s), running without it", exc)
            return None

    # ── mem0 Layer A ─────────────────────────────────────────────────────────

    def store_mem0(self, session_id: str, messages: List[Dict]) -> None:
        """Extract and store facts from conversation messages using mem0."""
        if not self._mem or not session_id:
            return
        try:
            self._mem.add(messages, user_id=session_id)
        except Exception as exc:
            logger.debug("mem0 store error: %s", exc)

    def recall_mem0(self, session_id: str, query: str) -> List[Dict]:
        """Retrieve relevant facts from mem0 for this user."""
        if not self._mem or not session_id:
            return []
        try:
            results = self._mem.search(query, user_id=session_id, limit=5)
            return results if isinstance(results, list) else []
        except Exception as exc:
            logger.debug("mem0 recall error: %s", exc)
            return []

    def build_mem0_system_message(self, session_id: str, query: str) -> SystemMessage | None:
        """Build a SystemMessage from recalled mem0 facts, or None if empty."""
        facts = self.recall_mem0(session_id, query)
        if not facts:
            return None
        lines = []
        for f in facts:
            text = f.get("memory") or f.get("text") or str(f)
            if text:
                lines.append(f"- {text}")
        if not lines:
            return None
        return SystemMessage(
            content="[Remembered facts about this user]\n" + "\n".join(lines)
        )

    # ── Vector Summarisation Layer B ─────────────────────────────────────────

    def maybe_summarise(self, messages: list, session_id: str) -> list:
        """
        If messages exceeds SUMMARY_THRESHOLD, compress the oldest turns into
        a vector summary stored in Pinecone (_session_summaries namespace).
        Returns the trimmed messages list.
        """
        if len(messages) < SUMMARY_THRESHOLD or not session_id:
            return messages

        to_compress = messages[:15]
        texts = [
            m.content for m in to_compress
            if hasattr(m, "content") and m.content
        ]
        if not texts:
            return messages

        try:
            summary_text = self.pipeline.llm.generate(
                query=(
                    "Summarise this conversation in 3 sentences, "
                    "preserving key facts, decisions, and customer details."
                ),
                context_chunks=texts,
                temperature=0.1,
                max_tokens=256,
            )
            vec = self.pipeline.embedding_model.embed_text(summary_text)
            self.pipeline.vector_db.upsert_vectors(
                vectors=[vec],
                texts=[summary_text],
                metadata=[{"session_id": session_id, "compressed_from": len(to_compress)}],
                namespace="_session_summaries",
            )
            trimmed = [SystemMessage(content=f"[Earlier context summary]: {summary_text}")]
            trimmed.extend(messages[15:])
            logger.info("LongTermMemory: summarised %d messages for session %s", len(to_compress), session_id)
            return trimmed
        except Exception as exc:
            logger.warning("LongTermMemory: summarisation failed: %s", exc)
            return messages

    def recall_session_summary(self, session_id: str, query: str) -> str | None:
        """Pull the most relevant prior session summary from Pinecone."""
        if not session_id:
            return None
        try:
            matches = self.pipeline.retrieve(
                query=query,
                namespace="_session_summaries",
                top_k_override=1,
                score_threshold=0.3,
            )
            for m in matches:
                meta = m.get("metadata", {})
                if meta.get("session_id") == session_id:
                    return meta.get("text", "")
        except Exception:
            pass
        return None
