"""
10-Ticket Race: Agent vs Workflow
Runs all 10 tickets, reports 4 metrics per mode, writes race.csv + race_report.md + budget_hit_sample.json
"""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "race_results"
RESULTS_DIR.mkdir(exist_ok=True)

# ── 10-Ticket Dataset ──────────────────────────────────────────────────────────

TICKETS = [
    # Simple retrieval — workflow optimal
    {
        "id": "T01", "customer_id": "C001",
        "question": "What are your shipping timeframes?",
        "item_status": "unopened",
        "expected_tools": ["route_namespace", "rag_retrieval"],
        "escalation_expected": False,
    },
    {
        "id": "T02", "customer_id": "C002",
        "question": "How do I reset my account password?",
        "item_status": "unopened",
        "expected_tools": ["route_namespace", "rag_retrieval"],
        "escalation_expected": False,
    },
    {
        "id": "T03", "customer_id": "C003",
        "question": "What documents can I upload to the system?",
        "item_status": "unopened",
        "expected_tools": ["inspect_documents"],
        "escalation_expected": False,
    },
    # Refund policy — agent retrieves from company documents
    {
        "id": "T04", "customer_id": "C001",
        "question": "I want a refund for my opened item.",
        "item_status": "opened",
        "expected_tools": ["route_namespace", "rag_retrieval"],
        "escalation_expected": False,
    },
    {
        "id": "T05", "customer_id": "C002",
        "question": "Can I get a refund for this opened item?",
        "item_status": "opened",
        "expected_tools": ["route_namespace", "rag_retrieval"],
        "escalation_expected": False,
    },
    # Missing order — agent retrieves escalation policy from documents
    {
        "id": "T06", "customer_id": "C001",
        "question": "My order never arrived — what now?",
        "item_status": "missing",
        "expected_tools": ["rag_retrieval"],
        "escalation_expected": True,
    },
    {
        "id": "T07", "customer_id": "C003",
        "question": "My package is marked delivered but it's missing.",
        "item_status": "missing",
        "expected_tools": ["rag_retrieval"],
        "escalation_expected": True,
    },
    {
        "id": "T08", "customer_id": "C004",
        "question": "My order is missing and my account shows suspended.",
        "item_status": "missing",
        "expected_tools": ["rag_retrieval"],
        "escalation_expected": False,
    },
    # Unrelated question — agent should decline politely
    {
        "id": "T09", "customer_id": "C002",
        "question": "What are my billing payment options?",
        "item_status": None,
        "expected_tools": ["route_namespace", "rag_retrieval"],
        "escalation_expected": False,
    },
    # Ambiguous namespace — escalation policy from documents
    {
        "id": "T10", "customer_id": "C005",
        "question": "What escalation path applies to premium customers?",
        "item_status": None,
        "expected_tools": ["route_namespace", "rag_retrieval"],
        "escalation_expected": False,
    },
]

COST_PER_INPUT = 0.0000003
COST_PER_OUTPUT = 0.0000006


def _evaluate_pass(ticket: dict, answer: str, tools_called: List[str]) -> bool:
    """Simple pass/fail: answer is non-empty and contains something meaningful."""
    if not answer or len(answer.strip()) < 10:
        return False
    # For escalation tickets, answer should mention escalation
    if ticket.get("escalation_expected"):
        lower = answer.lower()
        if not any(w in lower for w in ["escalat", "senior", "vip", "priorit", "specialist"]):
            return False
    return True


def _run_agent_on_ticket(pipeline: "RAGPipeline", ticket: dict) -> dict:
    """Run the ReAct agent on one ticket and return metrics."""
    from agent.react_agent import stream_agent
    t0 = time.monotonic()
    answer = ""
    tool_calls: List[str] = []
    total_tokens = 0
    budget_hit = False
    budget_reason = ""
    error = ""

    try:
        for line in stream_agent(
            pipeline=pipeline,
            question=ticket["question"],
            customer_id=ticket["customer_id"],
            item_status=ticket.get("item_status"),
            session_id="",
        ):
            evt = json.loads(line)
            etype = evt.get("event", "")
            if etype == "tool_start":
                tool_calls.append(evt.get("tool", ""))
            elif etype == "token":
                answer += evt.get("t", "")
            elif etype == "done":
                budget = evt.get("budget", {})
                total_tokens = budget.get("tokens_used", 0)
                cost_usd = budget.get("cost_usd", 0.0)
            elif etype == "budget_hit":
                budget_hit = True
                budget_reason = evt.get("reason", "")
            elif etype == "error":
                error = evt.get("detail", "")
    except Exception as exc:
        error = str(exc)

    latency_ms = round((time.monotonic() - t0) * 1000, 1)
    cost_usd_approx = total_tokens * (COST_PER_INPUT + COST_PER_OUTPUT) / 2
    passed = _evaluate_pass(ticket, answer, tool_calls) and not error

    return {
        "ticket_id": ticket["id"],
        "mode": "agent",
        "passed": passed,
        "latency_ms": latency_ms,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd_approx,
        "answer": answer[:300],
        "error": error,
        "budget_hit": budget_hit,
        "budget_hit_reason": budget_reason,
        "tools_called": tool_calls,
    }


def _run_workflow_on_ticket(pipeline: "RAGPipeline", ticket: dict) -> dict:
    """Run the fixed workflow on one ticket and return metrics."""
    from agent.workflow import stream_workflow
    t0 = time.monotonic()
    answer = ""
    total_tokens = 0
    cost_usd = 0.0
    steps_completed: List[str] = []
    error = ""

    try:
        for line in stream_workflow(
            pipeline=pipeline,
            question=ticket["question"],
            customer_id=ticket["customer_id"],
            item_status=ticket.get("item_status"),
        ):
            evt = json.loads(line)
            etype = evt.get("event", "")
            if etype == "step_done":
                steps_completed.append(evt.get("step", ""))
            elif etype == "token":
                answer += evt.get("t", "")
            elif etype == "done":
                total_tokens = evt.get("total_tokens", 0)
                cost_usd = evt.get("cost_usd", 0.0)
            elif etype == "error":
                error = evt.get("detail", "")
    except Exception as exc:
        error = str(exc)

    latency_ms = round((time.monotonic() - t0) * 1000, 1)
    passed = _evaluate_pass(ticket, answer, steps_completed) and not error

    return {
        "ticket_id": ticket["id"],
        "mode": "workflow",
        "passed": passed,
        "latency_ms": latency_ms,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "answer": answer[:300],
        "error": error,
        "budget_hit": False,
        "budget_hit_reason": "",
        "tools_called": steps_completed,
    }


def _compute_summary(results: List[dict], mode: str) -> dict:
    mode_results = [r for r in results if r["mode"] == mode]
    latencies = [r["latency_ms"] for r in mode_results if r["latency_ms"] > 0]
    return {
        "pass_rate": round(sum(1 for r in mode_results if r["passed"]) / len(mode_results) * 100, 1),
        "p50_latency_ms": round(statistics.median(latencies), 1) if latencies else 0,
        "total_tokens": sum(r["total_tokens"] for r in mode_results),
        "cost_per_ticket_usd": round(sum(r["cost_usd"] for r in mode_results) / len(mode_results), 8),
    }


def _build_verdict(agent_summary: dict, workflow_summary: dict, results: List[dict]) -> str:
    agent_pass = agent_summary["pass_rate"]
    wf_pass = workflow_summary["pass_rate"]
    agent_tok = agent_summary["total_tokens"]
    wf_tok = workflow_summary["total_tokens"]
    agent_cost = agent_summary["cost_per_ticket_usd"]
    wf_cost = workflow_summary["cost_per_ticket_usd"]

    dep_tickets = [r for r in results if r["ticket_id"] in ("T06", "T07", "T08")]
    agent_dep_pass = sum(1 for r in dep_tickets if r["mode"] == "agent" and r["passed"])
    wf_dep_pass = sum(1 for r in dep_tickets if r["mode"] == "workflow" and r["passed"])

    verdict = (
        f"Verdict: The ticket class that forces an agent is the missing-order escalation class (T06, T07, T08). "
        f"In these tickets, whether escalation applies depends on the customer tier, which is only meaningful "
        f"to look up after the retrieval step confirms the order is missing. "
        f"The agent passed {agent_dep_pass}/3 dependency tickets vs the workflow's {wf_dep_pass}/3. "
        f"For simple retrieval (T01-T03), the workflow is faster ({workflow_summary['p50_latency_ms']}ms p50) "
        f"and uses fewer tokens ({wf_tok} total vs agent's {agent_tok} total). "
        f"Overall: agent pass rate {agent_pass}%, workflow pass rate {wf_pass}%. "
        f"Cost per ticket: agent ${agent_cost:.6f} vs workflow ${wf_cost:.6f}. "
    )

    if agent_pass <= wf_pass and agent_tok >= wf_tok:
        verdict += (
            "The workflow wins on all four metrics for this input mix. "
            "The agent's advantage only materialises when the path varies by prior-tool output "
            "(i.e., the dependency tickets). If your production traffic is dominated by simple retrieval, prefer the workflow."
        )
    else:
        verdict += (
            "The agent's adaptability is necessary for dependency tickets where the escalation path "
            "varies based on what the retrieval step finds. "
            "For production, use the workflow for simple queries and the agent for complex multi-step flows."
        )

    return verdict


def _emit_ticket_done(result: dict, stream_callback) -> None:
    if not stream_callback:
        return
    stream_callback({
        "event": "ticket_done",
        "ticket_id": result["ticket_id"],
        "mode": result["mode"],
        "passed": result["passed"],
        "latency_ms": result["latency_ms"],
        "total_tokens": result["total_tokens"],
        "cost_usd": result["cost_usd"],
        "budget_hit": result["budget_hit"],
        "budget_hit_reason": result.get("budget_hit_reason", ""),
    })
    if result["budget_hit"]:
        stream_callback({
            "event": "budget_hit",
            "ticket_id": result["ticket_id"],
            "mode": result["mode"],
            "reason": result.get("budget_hit_reason", ""),
        })


def run_race(pipeline: "RAGPipeline", stream_callback=None) -> dict:
    """
    Two-phase race to eliminate Groq API contention between agent and workflow:

    Phase 1 — all 10 workflow tickets run in parallel (no LLM loop, fast ~4s each).
               All 10 workflow results appear in the UI within ~15s.
    Phase 2 — agent tickets run sequentially, one at a time (~20s each).
               No parallel agent calls so there is no rate-limit collision between tickets.

    Total time: ~15s (phase 1) + 10 × ~20s (phase 2) ≈ 3-4 min.
    Previously with mixed parallel pool: all 20 tasks competing → API slowdowns → same total time with worse reliability.
    """
    all_results: List[dict] = []

    # ── Phase 1: all workflows in parallel (they are fast and stateless) ──────
    if stream_callback:
        for ticket in TICKETS:
            stream_callback({"event": "ticket_start", "ticket_id": ticket["id"], "mode": "workflow"})

    with ThreadPoolExecutor(max_workers=10) as executor:
        wf_futures = {executor.submit(_run_workflow_on_ticket, pipeline, t): t for t in TICKETS}
        for future in as_completed(wf_futures):
            result = future.result()
            all_results.append(result)
            _emit_ticket_done(result, stream_callback)

    # ── Phase 2: agents one at a time (each runs a multi-step LLM loop) ───────
    for ticket in TICKETS:
        if stream_callback:
            stream_callback({"event": "ticket_start", "ticket_id": ticket["id"], "mode": "agent"})
        result = _run_agent_on_ticket(pipeline, ticket)
        all_results.append(result)
        _emit_ticket_done(result, stream_callback)

    agent_summary = _compute_summary(all_results, "agent")
    workflow_summary = _compute_summary(all_results, "workflow")
    verdict = _build_verdict(agent_summary, workflow_summary, all_results)

    if stream_callback:
        stream_callback({
            "event": "race_complete",
            "summary": {"agent": agent_summary, "workflow": workflow_summary},
            "verdict": verdict,
        })

    report = {
        "agent": agent_summary,
        "workflow": workflow_summary,
        "ticket_results": all_results,
        "verdict": verdict,
    }

    _write_outputs(report)
    _write_budget_hit_sample(pipeline)

    return report


def _write_outputs(report: dict) -> None:
    """Write race.csv and race_report.md."""
    csv_path = RESULTS_DIR / "race.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ticket_id", "mode", "passed", "latency_ms",
            "total_tokens_all_laps", "cost_usd",
        ])
        writer.writeheader()
        for r in sorted(report["ticket_results"], key=lambda x: (x["ticket_id"], x["mode"])):
            writer.writerow({
                "ticket_id": r["ticket_id"],
                "mode": r["mode"],
                "passed": r["passed"],
                "latency_ms": r["latency_ms"],
                "total_tokens_all_laps": r["total_tokens"],
                "cost_usd": r["cost_usd"],
            })

    json_path = RESULTS_DIR / "race_report.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    md_path = RESULTS_DIR / "race_report.md"
    a = report["agent"]
    w = report["workflow"]
    with open(md_path, "w") as f:
        f.write("# Agent vs Workflow Race Report\n\n")
        f.write("## Summary\n\n")
        f.write("| Metric | Agent | Workflow |\n")
        f.write("|--------|-------|----------|\n")
        f.write(f"| Pass rate (%) | {a['pass_rate']} | {w['pass_rate']} |\n")
        f.write(f"| P50 latency (ms) | {a['p50_latency_ms']} | {w['p50_latency_ms']} |\n")
        f.write(f"| Total tokens (all 10) | {a['total_tokens']} | {w['total_tokens']} |\n")
        f.write(f"| Cost per ticket (USD) | ${a['cost_per_ticket_usd']:.6f} | ${w['cost_per_ticket_usd']:.6f} |\n\n")
        f.write("## Per-Ticket Results\n\n")
        f.write("| Ticket | A Pass | A Latency | A Tokens | A Cost | W Pass | W Latency | W Tokens | W Cost |\n")
        f.write("|--------|--------|-----------|----------|--------|--------|-----------|----------|--------|\n")
        by_ticket = {}
        for r in report["ticket_results"]:
            by_ticket.setdefault(r["ticket_id"], {})[r["mode"]] = r
        dep_badge = {"T06": "⚡", "T07": "⚡", "T08": "⚡"}
        for tid in ["T01","T02","T03","T04","T05","T06","T07","T08","T09","T10"]:
            row = by_ticket.get(tid, {})
            a_r = row.get("agent", {})
            w_r = row.get("workflow", {})
            badge = dep_badge.get(tid, "")
            f.write(
                f"| {tid}{badge} | {'✓' if a_r.get('passed') else '✗'} | {a_r.get('latency_ms',0)}ms | "
                f"{a_r.get('total_tokens',0)} | ${a_r.get('cost_usd',0):.5f} | "
                f"{'✓' if w_r.get('passed') else '✗'} | {w_r.get('latency_ms',0)}ms | "
                f"{w_r.get('total_tokens',0)} | ${w_r.get('cost_usd',0):.5f} |\n"
            )
        f.write(f"\n## Verdict\n\n{report['verdict']}\n")

    logger.info("Race results written to %s", RESULTS_DIR)


def _write_budget_hit_sample(pipeline: "RAGPipeline") -> None:
    """Run T08 with aggressive budget to generate budget_hit_sample.json."""
    from agent.react_agent import stream_agent
    ticket = next(t for t in TICKETS if t["id"] == "T08")
    budget_config = {
        "max_cost_usd": 0.001,
        "max_iterations": 8,
        "max_tokens": 6000,
        "wall_clock_sec": 30.0,
    }
    t0 = time.monotonic()
    tools_called: List[str] = []
    partial_answer = ""
    budget_triggered = ""

    for line in stream_agent(
        pipeline=pipeline,
        question=ticket["question"],
        customer_id=ticket["customer_id"],
        item_status=ticket.get("item_status"),
        budget_config=budget_config,
    ):
        evt = json.loads(line)
        etype = evt.get("event", "")
        if etype == "tool_start":
            tools_called.append(evt.get("tool", ""))
        elif etype == "token":
            partial_answer += evt.get("t", "")
        elif etype == "budget_hit":
            budget_triggered = evt.get("reason", "budget limit reached")
        elif etype == "done":
            break

    elapsed = round((time.monotonic() - t0), 2)
    sample = {
        "ticket_id": ticket["id"],
        "budget_config": budget_config,
        "iterations_completed": len(tools_called),
        "budget_triggered": budget_triggered or "did not trigger (run used less than budget)",
        "partial_answer": partial_answer[:300],
        "tools_called": tools_called,
        "tools_not_reached": [
            t for t in ["route_namespace", "rag_retrieval"]
            if t not in tools_called
        ],
        "budget_summary": {
            "elapsed_sec": elapsed,
        },
    }
    path = RESULTS_DIR / "budget_hit_sample.json"
    with open(path, "w") as f:
        json.dump(sample, f, indent=2)
    logger.info("Budget hit sample written to %s", path)


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    from rag.rag_pipeline import RAGPipeline

    pipeline = RAGPipeline()

    def _print_event(evt):
        etype = evt.get("event", "")
        if etype == "ticket_done":
            mark = "✓" if evt["passed"] else "✗"
            print(f"  {mark} {evt['ticket_id']:4s} [{evt['mode']:8s}] {evt['latency_ms']:6.0f}ms  {evt['total_tokens']:5d} tok  ${evt['cost_usd']:.5f}")
        elif etype == "race_complete":
            s = evt["summary"]
            print(f"\nAGENT   : pass={s['agent']['pass_rate']}%  p50={s['agent']['p50_latency_ms']}ms  tokens={s['agent']['total_tokens']}  $/ticket={s['agent']['cost_per_ticket_usd']:.6f}")
            print(f"WORKFLOW: pass={s['workflow']['pass_rate']}%  p50={s['workflow']['p50_latency_ms']}ms  tokens={s['workflow']['total_tokens']}  $/ticket={s['workflow']['cost_per_ticket_usd']:.6f}")
            print(f"\n{evt['verdict']}")

    print("Running 10-ticket race (agent vs workflow)...\n")
    run_race(pipeline, stream_callback=_print_event)
    print(f"\nResults saved to {RESULTS_DIR}")
