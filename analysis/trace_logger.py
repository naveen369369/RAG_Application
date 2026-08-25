"""
Trace Logger — Week 5 Task Set A
=================================
Runs 25 representative questions through the existing RAG pipeline (unchanged)
and writes one complete trace record per question to analysis/traces.jsonl.

Each trace contains every field required for a complete trace review:
  - trace_id, timestamp
  - prompt_version, model, temperature, top_k
  - question, namespace
  - retrieved_chunk_ids, retrieved_scores
  - raw_output

Usage (from the RAG_Application directory):
    python -m analysis.trace_logger

Output:
    analysis/traces.jsonl  — one JSON object per line, 25 lines total
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure project root is on sys.path so existing modules resolve correctly
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.rag_pipeline import RAGPipeline  # existing, unchanged

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt version tag — bump this whenever the system prompt changes
# ---------------------------------------------------------------------------
PROMPT_VERSION = "v1.0"

# ---------------------------------------------------------------------------
# Output file
# ---------------------------------------------------------------------------
TRACES_PATH = Path(__file__).parent / "traces.jsonl"

# ---------------------------------------------------------------------------
# 25 Questions covering all 6 namespaces
#
# Sources:
#   12 questions  — golden_eval.py GOLDEN_QA list (verbatim, same IDs)
#   13 questions  — additional representative queries drawn from Hr-1..Hr-6.md
#
# Namespaces map to Pinecone namespaces used during indexing:
#   "Account Management & Login Issues"
#   "Billing & Payment Support"
#   "Product Returns & Refund Policy"
#   "Technical Troubleshooting Guide"
#   "Shipping & Delivery Information"
#   "Customer Escalation & Complaint Resolution"
# ---------------------------------------------------------------------------

QUESTIONS = [
    # ── Golden set (12) ─────────────────────────────────────────────────────
    {
        "source": "golden",
        "question": "What should I do if my account gets locked after multiple failed login attempts?",
        "namespace": "Account Management & Login Issues",
    },
    {
        "source": "golden",
        "question": "What is the difference between account deactivation and permanent account deletion?",
        "namespace": "Account Management & Login Issues",
    },
    {
        "source": "golden",
        "question": "Why do I see two charges on my bank statement for the same order?",
        "namespace": "Billing & Payment Support",
    },
    {
        "source": "golden",
        "question": "How long does a refund take to appear after it is approved?",
        "namespace": "Billing & Payment Support",
    },
    {
        "source": "golden",
        "question": "Can I return an electronic item that I have already opened?",
        "namespace": "Product Returns & Refund Policy",
    },
    {
        "source": "golden",
        "question": "What happens if I receive a damaged item? Do I need to ship it back?",
        "namespace": "Product Returns & Refund Policy",
    },
    {
        "source": "golden",
        "question": "What does error code ERR-1001 mean and how do I fix it?",
        "namespace": "Technical Troubleshooting Guide",
    },
    {
        "source": "golden",
        "question": "My app keeps crashing on mobile. What steps should I follow to fix it?",
        "namespace": "Technical Troubleshooting Guide",
    },
    {
        "source": "golden",
        "question": "My tracking status shows Delivered but I never received my package. What should I do?",
        "namespace": "Shipping & Delivery Information",
    },
    {
        "source": "golden",
        "question": "Can I change the delivery address on my order after it has been placed?",
        "namespace": "Shipping & Delivery Information",
    },
    {
        "source": "golden",
        "question": "How do I escalate my complaint to a senior agent or manager?",
        "namespace": "Customer Escalation & Complaint Resolution",
    },
    {
        "source": "golden",
        "question": "What are my options if the company's internal resolution does not satisfy my complaint?",
        "namespace": "Customer Escalation & Complaint Resolution",
    },
    # ── Additional representative queries (13) ───────────────────────────────
    {
        "source": "additional",
        "question": "How do I enable two-factor authentication on my account?",
        "namespace": "Account Management & Login Issues",
    },
    {
        "source": "additional",
        "question": "I forgot my password and the reset email is not arriving. What should I do?",
        "namespace": "Account Management & Login Issues",
    },
    {
        "source": "additional",
        "question": "My credit card was declined even though it has sufficient funds. Why?",
        "namespace": "Billing & Payment Support",
    },
    {
        "source": "additional",
        "question": "Can I get a refund if I paid with store credit?",
        "namespace": "Billing & Payment Support",
    },
    {
        "source": "additional",
        "question": "What is the return window for clothing items?",
        "namespace": "Product Returns & Refund Policy",
    },
    {
        "source": "additional",
        "question": "How do I initiate a return for an item I bought three weeks ago?",
        "namespace": "Product Returns & Refund Policy",
    },
    {
        "source": "additional",
        "question": "What does error code ERR-3003 mean?",
        "namespace": "Technical Troubleshooting Guide",
    },
    {
        "source": "additional",
        "question": "The website is loading very slowly on my browser. How can I fix this?",
        "namespace": "Technical Troubleshooting Guide",
    },
    {
        "source": "additional",
        "question": "How long does standard shipping take to arrive?",
        "namespace": "Shipping & Delivery Information",
    },
    {
        "source": "additional",
        "question": "Can I request express shipping after placing my order?",
        "namespace": "Shipping & Delivery Information",
    },
    {
        "source": "additional",
        "question": "How long does a complaint investigation typically take to resolve?",
        "namespace": "Customer Escalation & Complaint Resolution",
    },
    {
        "source": "additional",
        "question": "Is there a way to track the status of my escalated complaint?",
        "namespace": "Customer Escalation & Complaint Resolution",
    },
    {
        "source": "additional",
        "question": "What security settings should I configure to keep my account safe?",
        "namespace": "Account Management & Login Issues",
    },
]


def run_trace(pipeline: RAGPipeline, idx: int, q_entry: dict) -> dict:
    """Execute one query and return a complete trace record."""
    trace_id = f"trace-{idx + 1:03d}"
    question = q_entry["question"]
    namespace = q_entry["namespace"]

    ts = datetime.now(timezone.utc).isoformat()
    print(f"  [{trace_id}] {question[:70]}...")

    try:
        result = pipeline.query(
            question=question,
            namespace=namespace,
            temperature=0.2,
            stream=False,
            return_sources=True,
            use_reranker=False,
            use_hyde=False,
        )
        raw_output = result.get("answer", "")
        sources = result.get("sources") or []
        retrieved_chunk_ids = [s.get("source", "") + ":chunk-" + str(s.get("chunk_index", -1)) for s in sources]
        retrieved_scores = result.get("scores", [])
    except Exception as exc:
        raw_output = f"ERROR: {exc}"
        retrieved_chunk_ids = []
        retrieved_scores = []

    trace = {
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
    return trace


def main():
    print("=" * 60)
    print("Week 5 — Trace Logger")
    print(f"Output: {TRACES_PATH}")
    print(f"Questions: {len(QUESTIONS)}")
    print("=" * 60)

    print("\nInitializing RAG pipeline (unchanged)...")
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

    # Write all traces atomically
    with open(TRACES_PATH, "w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"\n[OK] {len(traces)} traces written to {TRACES_PATH}")
    print("  Fields in each trace:")
    for k in traces[0]:
        val = traces[0][k]
        print(f"    {k}: {str(val)[:60]}")


if __name__ == "__main__":
    main()
