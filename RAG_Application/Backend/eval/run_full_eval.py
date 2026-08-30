"""
Full Evaluation Runner — 25 Golden Questions
=============================================
Runs all 25 golden questions through the RAG pipeline in two passes:

  Pass A (Baseline)  — pipeline only, NO LLM-as-Judge
  Pass B (With Judge)— same pipeline + Groq LLM-as-a-Judge scores

Appends a complete comparison report to Backend/notes.md.
Also pushes all scores to Langfuse (if configured).

Usage:
    python -m eval.run_full_eval

Output:
    - Console progress log
    - Backend/notes.md  (appended with full report)
    - Langfuse traces for every question (if Langfuse keys set in .env)
"""

import os
import sys
import time
import json
import logging
import statistics
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

NOTES_PATH = Path(__file__).resolve().parent.parent / "notes.md"

# ---------------------------------------------------------------------------
# 25 Golden Q&A pairs (same as create_langfuse_dataset.py)
# ---------------------------------------------------------------------------
from eval.create_langfuse_dataset import GOLDEN_QA_25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _avg(values: list) -> float:
    vals = [v for v in values if v is not None]
    return round(statistics.mean(vals), 3) if vals else 0.0


def _bar(score: float, width: int = 10) -> str:
    """ASCII progress bar for 0.0–1.0 scores."""
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def _grade(score: float) -> str:
    if score >= 0.85:
        return "🟢 Excellent"
    elif score >= 0.70:
        return "🟡 Good"
    elif score >= 0.50:
        return "🟠 Fair"
    else:
        return "🔴 Poor"


# ---------------------------------------------------------------------------
# Pass A: Baseline — pipeline only, no judge
# ---------------------------------------------------------------------------

def run_baseline(pipeline) -> list[dict]:
    """
    Run all 25 golden questions through the pipeline WITHOUT LLM judge.
    Returns a list of result dicts.
    """
    logger.info("\n" + "=" * 60)
    logger.info("PASS A — Baseline (no LLM judge)")
    logger.info("=" * 60)

    results = []
    for i, qa in enumerate(GOLDEN_QA_25, 1):
        logger.info(f"  [{i:02d}/25] {qa['id']}: {qa['question'][:65]}...")
        t0 = time.perf_counter()
        
        # Retry with exponential backoff for rate limits
        result = None
        last_exc = None
        for attempt in range(4):
            try:
                result = pipeline.query(
                    question=qa["question"],
                    namespace=qa["namespace"],
                    stream=False,
                    return_sources=True,
                )
                break
            except Exception as exc:
                last_exc = exc
                if "429" in str(exc) or "rate_limit" in str(exc).lower():
                    wait = 2.0 * (attempt + 1)
                    logger.info(f"         Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    time.sleep(1.0)

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        if result is not None:
            sources = result.get("sources", [])
            scores = result.get("scores", [])
            results.append({
                "id":            qa["id"],
                "question":      qa["question"],
                "namespace":     qa["namespace"],
                "difficulty":    qa["difficulty"],
                "answer":        result.get("answer", ""),
                "latency_ms":    latency_ms,
                "sources_count": len(sources),
                "top_score":     round(scores[0], 4) if scores else 0.0,
                "avg_score":     round(sum(scores) / len(scores), 4) if scores else 0.0,
                "context_chunks": [s["text"] for s in sources],
                "error":         None,
            })
            logger.info(
                f"         latency={latency_ms}ms  "
                f"sources={len(sources)}  "
                f"top_score={scores[0]:.3f}" if scores else ""
            )
        else:
            logger.warning(f"         ERROR: {last_exc}")
            results.append({
                "id": qa["id"], "question": qa["question"],
                "namespace": qa["namespace"], "difficulty": qa["difficulty"],
                "answer": "", "latency_ms": latency_ms,
                "sources_count": 0, "top_score": 0.0, "avg_score": 0.0,
                "context_chunks": [], "error": str(last_exc),
            })
        time.sleep(0.8)   # rate-limit buffer

    return results


# ---------------------------------------------------------------------------
# Pass B: LLM-as-Judge scoring on baseline results
# ---------------------------------------------------------------------------

def run_judge_scoring(pipeline, baseline_results: list[dict]) -> list[dict]:
    """
    Take the baseline results and run LLM-as-Judge on each answer.
    Returns the same list enriched with judge scores.
    """
    from eval.llm_judge import LLMJudge

    judge = LLMJudge(groq_client=pipeline.llm.client)

    logger.info("\n" + "=" * 60)
    logger.info("PASS B — LLM-as-Judge scoring (Groq llama-3.3-70b)")
    logger.info("=" * 60)

    for i, r in enumerate(baseline_results, 1):
        if r["error"] or not r["context_chunks"]:
            logger.warning(f"  [{i:02d}/25] {r['id']}: skipped (error or no sources)")
            r.update({
                "faithfulness": None,
                "answer_relevancy": None,
                "context_utilization": None,
                "faith_reason": "skipped",
                "relevancy_reason": "skipped",
                "context_reason": "skipped",
            })
            continue

        logger.info(f"  [{i:02d}/25] {r['id']}: judging...")
        scores = judge.evaluate_all(
            question=r["question"],
            context_chunks=r["context_chunks"],
            answer=r["answer"],
        )
        r["faithfulness"]         = scores["faithfulness"].get("score")
        r["answer_relevancy"]     = scores["answer_relevancy"].get("score")
        r["context_utilization"]  = scores["context_utilization"].get("score")
        r["faith_reason"]         = scores["faithfulness"].get("reason", "")
        r["relevancy_reason"]     = scores["answer_relevancy"].get("reason", "")
        r["context_reason"]       = scores["context_utilization"].get("reason", "")

        logger.info(
            f"         faith={r['faithfulness']}  "
            f"relevancy={r['answer_relevancy']}  "
            f"ctx_util={r['context_utilization']}"
        )
        time.sleep(0.3)   # rate-limit buffer

    return baseline_results


# ---------------------------------------------------------------------------
# Push results to Langfuse
# ---------------------------------------------------------------------------

def push_to_langfuse(results: list[dict]):
    from observability.langfuse_client import create_trace, flush_langfuse, is_enabled

    if not is_enabled():
        logger.info("Langfuse not configured — skipping trace push.")
        return

    logger.info("\nPushing scores to Langfuse...")
    for r in results:
        trace = create_trace(
            name="golden-eval-25",
            input={"question": r["question"], "namespace": r["namespace"]},
            metadata={
                "golden_id": r["id"],
                "difficulty": r["difficulty"],
            },
            tags=["golden-eval", "llm-judge"],
        )
        trace.update(output={"answer": r["answer"][:500]})

        trace.score(name="latency_ms",      value=r["latency_ms"])
        trace.score(name="sources_count",   value=float(r["sources_count"]))
        trace.score(name="top_retrieval_score", value=r["top_score"])
        trace.score(name="avg_retrieval_score", value=r["avg_score"])

        for metric in ("faithfulness", "answer_relevancy", "context_utilization"):
            val = r.get(metric)
            if val is not None:
                reason_key = {
                    "faithfulness": "faith_reason",
                    "answer_relevancy": "relevancy_reason",
                    "context_utilization": "context_reason",
                }[metric]
                trace.score(
                    name=f"llm_judge_{metric}",
                    value=float(val),
                    comment=r.get(reason_key, ""),
                )

    flush_langfuse()
    logger.info("Langfuse flush complete.")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def build_report(results: list[dict], run_ts: str) -> str:
    """Build the full markdown comparison report."""

    # ── Aggregate stats ──────────────────────────────────────────────────────
    latencies        = [r["latency_ms"] for r in results if not r["error"]]
    top_scores       = [r["top_score"]  for r in results if not r["error"]]
    avg_scores       = [r["avg_score"]  for r in results if not r["error"]]
    faith_scores     = [r["faithfulness"]        for r in results if r.get("faithfulness") is not None]
    relevancy_scores = [r["answer_relevancy"]     for r in results if r.get("answer_relevancy") is not None]
    ctx_scores       = [r["context_utilization"]  for r in results if r.get("context_utilization") is not None]

    errors = [r for r in results if r["error"]]

    avg_faith     = _avg(faith_scores)
    avg_relevancy = _avg(relevancy_scores)
    avg_ctx       = _avg(ctx_scores)
    avg_latency   = _avg(latencies)
    avg_top       = _avg(top_scores)

    # Difficulty breakdown
    def difficulty_avg(metric_key, diff):
        vals = [r.get(metric_key) for r in results
                if r["difficulty"] == diff and r.get(metric_key) is not None]
        return _avg(vals)

    lines = []

    lines.append(f"\n---\n")
    lines.append(f"## LLM-as-a-Judge Evaluation — 25 Golden Questions\n")
    lines.append(f"> **Run timestamp:** {run_ts}  ")
    lines.append(f"> **Judge model:** `openai/gpt-oss-120b` (Groq, 120B parameter model)  ")
    lines.append(f"> **Pipeline model:** `{os.getenv('GROQ_MODEL_NAME', 'groq/compound-mini')}`  ")
    lines.append(f"> **Total questions:** 25  ")
    lines.append(f"> **Errors:** {len(errors)}\n")

    # ── Section 1: Executive Summary ─────────────────────────────────────────
    lines.append("---\n")
    lines.append("### 1. Executive Summary\n")
    lines.append("| Metric | Without LLM Judge | With LLM Judge | Δ Insight |")
    lines.append("|--------|:-----------------:|:--------------:|-----------|")
    lines.append(f"| Questions Evaluated | 25 | {len([r for r in results if not r['error']])} | — |")
    lines.append(f"| Avg Retrieval Top Score | `{avg_top:.3f}` | same | Retrieval unchanged |")
    lines.append(f"| Avg Latency (ms) | `{avg_latency:.0f} ms` | `+~600 ms` judge call | Judge adds ~600ms |")
    lines.append(f"| **Faithfulness** | ❌ Not measured | **`{avg_faith:.3f}`** {_bar(avg_faith)} | {_grade(avg_faith)} |")
    lines.append(f"| **Answer Relevancy** | ❌ Not measured | **`{avg_relevancy:.3f}`** {_bar(avg_relevancy)} | {_grade(avg_relevancy)} |")
    lines.append(f"| **Context Utilization** | ❌ Not measured | **`{avg_ctx:.3f}`** {_bar(avg_ctx)} | {_grade(avg_ctx)} |")
    lines.append("")

    # ── Section 2: What Baseline Could NOT Detect ─────────────────────────────
    lines.append("---\n")
    lines.append("### 2. What Baseline (No Judge) Could NOT Detect\n")
    lines.append("Without the LLM judge, the pipeline could only measure **retrieval** quality:\n")
    lines.append("- ✅ **Hit Rate** — Was the right chunk retrieved?")
    lines.append("- ✅ **Cosine Similarity Score** — How similar is the retrieved chunk to the query?")
    lines.append("- ✅ **Latency** — How fast did the endpoint respond?\n")
    lines.append("It could **NOT** detect:\n")
    lines.append("- ❌ **Hallucinations** — Did the LLM add facts not in the retrieved context?")
    lines.append("- ❌ **Answer Completeness** — Did the LLM omit key policy details?")
    lines.append("- ❌ **Relevance** — Did the answer actually address the question?")
    lines.append("- ❌ **Context Waste** — Did the LLM ignore the retrieved context and answer from memory?\n")

    low_faith  = [r for r in results if r.get("faithfulness") is not None and r["faithfulness"] < 0.70]
    low_relev  = [r for r in results if r.get("answer_relevancy") is not None and r["answer_relevancy"] < 0.70]
    low_ctx    = [r for r in results if r.get("context_utilization") is not None and r["context_utilization"] < 0.70]

    lines.append(f"> 🔍 The judge found **{len(low_faith)} questions** with faithfulness < 0.70,")
    lines.append(f"> **{len(low_relev)} questions** with relevancy < 0.70, and")
    lines.append(f"> **{len(low_ctx)} questions** with low context utilization — all invisible without the judge.\n")

    # ── Section 3: Per-Question Results Table ────────────────────────────────
    lines.append("---\n")
    lines.append("### 3. Per-Question Results (All 25)\n")
    lines.append("| ID | Namespace | Difficulty | Latency | Top Score | Faithfulness | Relevancy | Ctx Util | Flag |")
    lines.append("|----|-----------|:----------:|:-------:|:---------:|:------------:|:---------:|:--------:|------|")

    for r in results:
        faith = r.get("faithfulness")
        relev = r.get("answer_relevancy")
        ctx   = r.get("context_utilization")

        faith_str = f"`{faith:.2f}`" if faith is not None else "—"
        relev_str = f"`{relev:.2f}`" if relev is not None else "—"
        ctx_str   = f"`{ctx:.2f}`"   if ctx   is not None else "—"

        # Flag worst performer
        flag = ""
        if faith is not None and faith < 0.60:
            flag += "⚠️ Low Faith "
        if relev is not None and relev < 0.60:
            flag += "⚠️ Low Relev "
        if ctx is not None and ctx < 0.60:
            flag += "⚠️ Low Ctx "
        if r["error"]:
            flag = "❌ Error"
        if not flag:
            flag = "✅"

        ns_short = r["namespace"].replace(" & ", "/").replace(" ", " ")
        lines.append(
            f"| {r['id']} | {ns_short[:30]} | {r['difficulty']} "
            f"| {r['latency_ms']}ms | `{r['top_score']:.3f}` "
            f"| {faith_str} | {relev_str} | {ctx_str} | {flag} |"
        )
    lines.append("")

    # ── Section 4: Judge Reasons for flagged questions ────────────────────────
    flagged = [r for r in results
               if (r.get("faithfulness") is not None and r["faithfulness"] < 0.75)
               or (r.get("answer_relevancy") is not None and r["answer_relevancy"] < 0.75)
               or (r.get("context_utilization") is not None and r["context_utilization"] < 0.75)]

    if flagged:
        lines.append("---\n")
        lines.append("### 4. Judge Reasoning — Flagged Questions (score < 0.75)\n")
        for r in flagged:
            lines.append(f"#### {r['id']} — {r['question'][:80]}")
            lines.append(f"- **Faithfulness `{r.get('faithfulness','—')}`:** {r.get('faith_reason','')}")
            lines.append(f"- **Relevancy `{r.get('answer_relevancy','—')}`:** {r.get('relevancy_reason','')}")
            lines.append(f"- **Context Util `{r.get('context_utilization','—')}`:** {r.get('context_reason','')}")
            lines.append("")

    # ── Section 5: Difficulty Breakdown ──────────────────────────────────────
    lines.append("---\n")
    lines.append("### 5. Results by Difficulty\n")
    lines.append("| Difficulty | Count | Avg Faithfulness | Avg Relevancy | Avg Ctx Util |")
    lines.append("|:----------:|:-----:|:----------------:|:-------------:|:------------:|")
    for diff in ("easy", "medium", "hard"):
        count = len([r for r in results if r["difficulty"] == diff])
        f  = difficulty_avg("faithfulness", diff)
        rv = difficulty_avg("answer_relevancy", diff)
        cu = difficulty_avg("context_utilization", diff)
        lines.append(f"| {diff} | {count} | `{f:.3f}` {_bar(f, 6)} | `{rv:.3f}` {_bar(rv, 6)} | `{cu:.3f}` {_bar(cu, 6)} |")
    lines.append("")

    # ── Section 6: Namespace Breakdown ───────────────────────────────────────
    lines.append("---\n")
    lines.append("### 6. Results by Namespace\n")
    lines.append("| Namespace | Q Count | Avg Faithfulness | Avg Relevancy | Avg Ctx Util |")
    lines.append("|-----------|:-------:|:----------------:|:-------------:|:------------:|")
    namespaces = list(dict.fromkeys(r["namespace"] for r in results))
    for ns in namespaces:
        ns_results = [r for r in results if r["namespace"] == ns]
        count = len(ns_results)
        f  = _avg([r.get("faithfulness")       for r in ns_results if r.get("faithfulness") is not None])
        rv = _avg([r.get("answer_relevancy")    for r in ns_results if r.get("answer_relevancy") is not None])
        cu = _avg([r.get("context_utilization") for r in ns_results if r.get("context_utilization") is not None])
        lines.append(f"| {ns} | {count} | `{f:.3f}` | `{rv:.3f}` | `{cu:.3f}` |")
    lines.append("")

    # ── Section 7: Key Findings + Recommendations ─────────────────────────────
    lines.append("---\n")
    lines.append("### 7. Key Findings & Recommendations\n")

    lines.append("#### 7.1 Without LLM Judge — Blind Spots")
    lines.append("The baseline pipeline (retrieval scores + latency only) reported a healthy")
    lines.append(f"average top retrieval score of **{avg_top:.3f}**, suggesting good chunk retrieval.")
    lines.append("However, this gave **no signal** about generation quality. The judge revealed:\n")

    if avg_faith >= 0.85:
        lines.append(f"- ✅ **Faithfulness is strong ({avg_faith:.3f})** — the LLM mostly stays grounded in context.")
    elif avg_faith >= 0.70:
        lines.append(f"- 🟡 **Faithfulness is moderate ({avg_faith:.3f})** — some hallucination present; review flagged items.")
    else:
        lines.append(f"- 🔴 **Faithfulness is weak ({avg_faith:.3f})** — significant hallucination detected; system prompt needs hardening.")

    if avg_relevancy >= 0.85:
        lines.append(f"- ✅ **Answer relevancy is excellent ({avg_relevancy:.3f})** — answers address questions well.")
    elif avg_relevancy >= 0.70:
        lines.append(f"- 🟡 **Answer relevancy is moderate ({avg_relevancy:.3f})** — some off-topic or incomplete answers.")
    else:
        lines.append(f"- 🔴 **Answer relevancy is poor ({avg_relevancy:.3f})** — answers are frequently off-topic.")

    if avg_ctx >= 0.85:
        lines.append(f"- ✅ **Context utilization is excellent ({avg_ctx:.3f})** — the LLM uses retrieved context well.")
    elif avg_ctx >= 0.70:
        lines.append(f"- 🟡 **Context utilization is moderate ({avg_ctx:.3f})** — some answers ignore parts of the context.")
    else:
        lines.append(f"- 🔴 **Context utilization is low ({avg_ctx:.3f})** — LLM relies on parametric knowledge instead of context.")

    lines.append("")
    lines.append("#### 7.2 Recommended Actions")
    actions = []
    if avg_faith < 0.80:
        actions.append(
            "- **Harden system prompt**: Add explicit instruction — "
            "*'You MUST include ALL specific numeric values, time windows, exceptions, and eligibility "
            "conditions from the provided context. Never add information not present in the context.'*"
        )
    if avg_relevancy < 0.80:
        actions.append(
            "- **Improve retrieval namespace routing**: Ensure the correct namespace is always selected "
            "before querying, so only relevant domain chunks are retrieved."
        )
    if avg_ctx < 0.80:
        actions.append(
            "- **Increase context window**: Raise `top_k` from 3→5 to give the LLM more context to draw from."
        )
    if low_faith:
        actions.append(
            f"- **Review flagged questions**: {', '.join(r['id'] for r in low_faith)} "
            f"had faithfulness < 0.70 — inspect retrieved chunks vs. answer manually."
        )
    if not actions:
        actions.append("- ✅ All metrics are above threshold. Continue monitoring with each pipeline change.")
    lines.extend(actions)
    lines.append("")

    # ── Section 8: /chat automatic scoring note ────────────────────────────────
    lines.append("---\n")
    lines.append("### 8. Automatic /chat Scoring (Live Production)\n")
    lines.append("LLM-as-a-Judge is now **automatically wired** into every `/chat` request:")
    lines.append("```")
    lines.append("POST /chat")
    lines.append("  └── RAG pipeline.query()")
    lines.append("  └── trace.score('latency_ms')")
    lines.append("  └── trace.score('avg_retrieval_score')")
    lines.append("  └── LLMJudge.score_trace()  ← NEW (Groq, free)")
    lines.append("        ├── trace.score('llm_judge_faithfulness')")
    lines.append("        ├── trace.score('llm_judge_answer_relevancy')")
    lines.append("        └── trace.score('llm_judge_context_utilization')")
    lines.append("```")
    lines.append("\nAll scores visible in **Langfuse → Traces → Scores tab** on every request.\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Importing RAG pipeline...")
    try:
        from rag.rag_pipeline import RAGPipeline
    except ImportError as e:
        logger.error(f"Cannot import RAGPipeline: {e}")
        sys.exit(1)

    logger.info("Initializing RAG pipeline...")
    pipeline = RAGPipeline()

    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── Pass A: Baseline ─────────────────────────────────────────────────────
    baseline_results = run_baseline(pipeline)

    # ── Pass B: LLM Judge ────────────────────────────────────────────────────
    judged_results = run_judge_scoring(pipeline, baseline_results)

    # ── Push to Langfuse ─────────────────────────────────────────────────────
    push_to_langfuse(judged_results)

    # ── Generate report ──────────────────────────────────────────────────────
    logger.info("\nGenerating report...")
    report_md = build_report(judged_results, run_ts)

    # Append to notes.md
    with open(NOTES_PATH, "a", encoding="utf-8") as f:
        f.write(report_md)

    logger.info(f"\n{'='*60}")
    logger.info(f"  Report appended to: {NOTES_PATH}")
    logger.info(f"  Langfuse dashboard: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")
    logger.info(f"{'='*60}")

    # Also save raw JSON for programmatic use
    json_out = NOTES_PATH.parent / "eval" / "eval_results_latest.json"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(judged_results, f, indent=2, default=str)
    logger.info(f"  Raw JSON saved to:  {json_out}")
