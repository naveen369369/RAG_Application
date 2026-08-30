"""
Trace Logger
=============
Runs 25 representative questions through the existing RAG pipeline and sends
a complete trace record per question to Langfuse (primary) and writes a local
backup to analysis/traces.jsonl.

Each Langfuse trace contains:
  - Input question + namespace
  - Retrieval span with chunk IDs and scores
  - LLM generation span with the full answer
  - Evaluation scores (retrieval quality, source count)

Each JSONL record contains every field for offline review:
  trace_id, timestamp, prompt_version, model, temperature, top_k,
  question, namespace, retrieved_chunk_ids, retrieved_scores, raw_output

Usage (from the RAG_Application directory):
    python -m analysis.trace_logger
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure project root is on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from rag.rag_pipeline import RAGPipeline
from observability.langfuse_client import create_trace, flush_langfuse, is_enabled

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROMPT_VERSION = "v1.0"
TRACES_PATH = Path(__file__).parent / "traces.jsonl"

# ---------------------------------------------------------------------------
# 25 Questions covering all 6 namespaces
# ---------------------------------------------------------------------------
QUESTIONS = [
    # ── Golden set (12) ─────────────────────────────────────────────────────
    {"source": "golden", "question": "What should I do if my account gets locked after multiple failed login attempts?", "namespace": "Account Management & Login Issues"},
    {"source": "golden", "question": "What is the difference between account deactivation and permanent account deletion?", "namespace": "Account Management & Login Issues"},
    {"source": "golden", "question": "Why do I see two charges on my bank statement for the same order?", "namespace": "Billing & Payment Support"},
    {"source": "golden", "question": "How long does a refund take to appear after it is approved?", "namespace": "Billing & Payment Support"},
    {"source": "golden", "question": "Can I return an electronic item that I have already opened?", "namespace": "Product Returns & Refund Policy"},
    {"source": "golden", "question": "What happens if I receive a damaged item? Do I need to ship it back?", "namespace": "Product Returns & Refund Policy"},
    {"source": "golden", "question": "What does error code ERR-1001 mean and how do I fix it?", "namespace": "Technical Troubleshooting Guide"},
    {"source": "golden", "question": "My app keeps crashing on mobile. What steps should I follow to fix it?", "namespace": "Technical Troubleshooting Guide"},
    {"source": "golden", "question": "My tracking status shows Delivered but I never received my package. What should I do?", "namespace": "Shipping & Delivery Information"},
    {"source": "golden", "question": "Can I change the delivery address on my order after it has been placed?", "namespace": "Shipping & Delivery Information"},
    {"source": "golden", "question": "How do I escalate my complaint to a senior agent or manager?", "namespace": "Customer Escalation & Complaint Resolution"},
    {"source": "golden", "question": "What are my options if the company's internal resolution does not satisfy my complaint?", "namespace": "Customer Escalation & Complaint Resolution"},
    # ── Additional representative queries (13) ───────────────────────────────
    {"source": "additional", "question": "How do I enable two-factor authentication on my account?", "namespace": "Account Management & Login Issues"},
    {"source": "additional", "question": "I forgot my password and the reset email is not arriving. What should I do?", "namespace": "Account Management & Login Issues"},
    {"source": "additional", "question": "My credit card was declined even though it has sufficient funds. Why?", "namespace": "Billing & Payment Support"},
    {"source": "additional", "question": "Can I get a refund if I paid with store credit?", "namespace": "Billing & Payment Support"},
    {"source": "additional", "question": "What is the return window for clothing items?", "namespace": "Product Returns & Refund Policy"},
    {"source": "additional", "question": "How do I initiate a return for an item I bought three weeks ago?", "namespace": "Product Returns & Refund Policy"},
    {"source": "additional", "question": "What does error code ERR-3003 mean?", "namespace": "Technical Troubleshooting Guide"},
    {"source": "additional", "question": "The website is loading very slowly on my browser. How can I fix this?", "namespace": "Technical Troubleshooting Guide"},
    {"source": "additional", "question": "How long does standard shipping take to arrive?", "namespace": "Shipping & Delivery Information"},
    {"source": "additional", "question": "Can I request express shipping after placing my order?", "namespace": "Shipping & Delivery Information"},
    {"source": "additional", "question": "How long does a complaint investigation typically take to resolve?", "namespace": "Customer Escalation & Complaint Resolution"},
    {"source": "additional", "question": "Is there a way to track the status of my escalated complaint?", "namespace": "Customer Escalation & Complaint Resolution"},
    {"source": "additional", "question": "What security settings should I configure to keep my account safe?", "namespace": "Account Management & Login Issues"},
]


def run_trace(pipeline: RAGPipeline, idx: int, q_entry: dict) -> dict:
    """Execute one query, send a full Langfuse trace, and return a JSONL record."""
    trace_id = f"trace-{idx + 1:03d}"
    question = q_entry["question"]
    namespace = q_entry["namespace"]
    ts = datetime.now(timezone.utc).isoformat()

    print(f"  [{trace_id}] {question[:70]}...")

    # ── Langfuse trace ────────────────────────────────────────────────────────
    lf_trace = create_trace(
        name="trace-logger-run",
        input={"question": question},
        metadata={
            "trace_id": trace_id,
            "namespace": namespace,
            "source_type": q_entry["source"],
            "prompt_version": PROMPT_VERSION,
            "temperature": 0.2,
            "top_k": pipeline.top_k,
        },
        tags=["trace-logger", q_entry["source"], namespace],
        session_id=f"trace-logger-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
    )

    retrieved_chunk_ids = []
    retrieved_scores = []
    raw_output = ""

    try:
        # Retrieval span
        retrieval_span = lf_trace.span(
            name="retrieval",
            input={"query": question, "namespace": namespace, "top_k": pipeline.top_k},
        )
        matches = pipeline.retrieve(
            query=question,
            namespace=namespace,
            score_threshold=pipeline.hit_threshold,
        )
        retrieved_scores = [round(m.get("score", 0), 4) for m in matches]
        retrieved_chunk_ids = [
            m["metadata"].get("source", "") + ":chunk-" + str(m["metadata"].get("chunk_index", -1))
            for m in matches
        ]
        retrieval_span.end(output={
            "num_matches": len(matches),
            "scores": retrieved_scores,
            "chunk_ids": retrieved_chunk_ids,
        })

        # LLM generation span
        generation_span = lf_trace.generation(
            name="llm-generation",
            model=pipeline.llm.model_name,
            input={"question": question, "context_chunks": len(matches), "temperature": 0.2},
        )
        if matches:
            raw_output = pipeline.generate_answer(
                query=question,
                context_matches=matches,
                temperature=0.2,
                stream=False,
            )
        else:
            raw_output = "I couldn't find relevant context in the indexed documents to answer your question."
        generation_span.end(output={"answer": raw_output[:500]})

    except Exception as exc:
        raw_output = f"ERROR: {exc}"
        lf_trace.update(output={"error": str(exc)})
        logger.error(f"[{trace_id}] failed: {exc}")

    # Scores
    lf_trace.update(output={"answer": raw_output[:500]})
    lf_trace.score(name="sources_retrieved", value=float(len(retrieved_scores)), comment="Chunks retrieved above threshold")
    lf_trace.score(name="sources_hit", value=1.0 if retrieved_scores else 0.0, comment="1 = context found, 0 = no context")
    if retrieved_scores:
        lf_trace.score(
            name="avg_retrieval_score",
            value=round(sum(retrieved_scores) / len(retrieved_scores), 4),
            comment="Average cosine similarity of retrieved chunks",
        )
    flush_langfuse()

    # JSONL record (offline backup)
    return {
        "trace_id": trace_id,
        "timestamp": ts,
        "prompt_version": PROMPT_VERSION,
        "question": question,
        "namespace": namespace,
        "source_type": q_entry["source"],
        "model": pipeline.llm.model_name,
        "temperature": 0.2,
        "top_k": pipeline.top_k,
        "use_hyde": False,
        "use_reranker": False,
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "retrieved_scores": retrieved_scores,
        "raw_output": raw_output,
    }


def main():
    print("=" * 60)
    print("Trace Logger")
    print(f"Langfuse enabled: {is_enabled()}")
    print(f"Local backup: {TRACES_PATH}")
    print(f"Questions: {len(QUESTIONS)}")
    print("=" * 60)

    if not is_enabled():
        print("\n[WARNING] Langfuse is not configured. Traces will only be written to the local JSONL file.")
        print("  Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env to enable dashboard tracing.\n")

    print("\nInitializing RAG pipeline...")
    pipeline = RAGPipeline()
    print(f"  model       : {pipeline.llm.model_name}")
    print(f"  top_k       : {pipeline.top_k}")
    print(f"  chunk_size  : {pipeline.chunk_size}")
    print(f"  prompt_ver  : {PROMPT_VERSION}")
    print()

    TRACES_PATH.parent.mkdir(parents=True, exist_ok=True)

    traces = []
    for idx, q_entry in enumerate(QUESTIONS):
        trace = run_trace(pipeline, idx, q_entry)
        traces.append(trace)

    # Write JSONL backup
    with open(TRACES_PATH, "w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"\n[OK] {len(traces)} traces processed.")
    if is_enabled():
        print("  All traces sent to Langfuse dashboard.")
    print(f"  Local backup: {TRACES_PATH}")

    if traces:
        print("\n  Sample fields from first trace:")
        for k in traces[0]:
            val = traces[0][k]
            print(f"    {k}: {str(val)[:60]}")


if __name__ == "__main__":
    main()
