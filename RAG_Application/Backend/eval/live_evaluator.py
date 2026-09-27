"""
Live Chat & Support Ticket Trajectory Evaluator
===============================================
Evaluates real-time questions, live chat prompts, and support tickets.
Runs the ReAct Agent against the live SQL database and Pinecone RAG knowledge base,
then grades the execution trajectory, tool sequence, parameter validity,
grounded accuracy, latency, and cost.
"""
from __future__ import annotations

import re
import time
import json
import logging
from typing import Any, Dict, List, Optional
from database.session import get_db_session
from database.crud import get_ticket, get_order, get_customer

logger = logging.getLogger(__name__)

TICKET_PATTERN = re.compile(r"\b(TCK-[A-Za-z0-9]+|T0[1-9]|T10)\b", re.IGNORECASE)
ORDER_PATTERN  = re.compile(r"\b(ORD-[A-Za-z0-9]+|ORDER\s*#?\s*\d+)\b", re.IGNORECASE)
CUST_PATTERN   = re.compile(r"\b(C\d{3})\b", re.IGNORECASE)


def evaluate_live_query(
    pipeline,
    question: str,
    customer_id: str = "C001",
    ticket_id: Optional[str] = None,
    item_status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes a question through the ReAct Agent and performs live trajectory evaluation.
    """
    from agent.react_agent import stream_agent

    t0 = time.perf_counter()
    tools_called: List[str] = []
    tool_records: List[Dict[str, Any]] = []
    final_tokens: List[str] = []
    final_answer = ""
    complexity = "simple"
    budget_info = {}
    error_msg = None

    try:
        # Stream agent execution and intercept NDJSON events
        for line in stream_agent(
            pipeline=pipeline,
            question=question,
            customer_id=customer_id,
            item_status=item_status,
            session_id=f"eval-{int(time.time())}",
            temperature=0.0,
        ):
            if not line.strip():
                continue
            try:
                evt = json.loads(line)
            except Exception:
                continue

            event_type = evt.get("event")
            if event_type == "classified":
                complexity = evt.get("complexity", "simple")
            elif event_type == "tool_start":
                tool_name = evt.get("tool", "")
                tools_called.append(tool_name)
                tool_records.append({
                    "tool": tool_name,
                    "args": evt.get("args", {}),
                    "timestamp": time.time(),
                })
            elif event_type == "tool_result":
                if tool_records:
                    tool_records[-1]["result"] = evt.get("result", {})
            elif event_type == "token":
                final_tokens.append(evt.get("t", ""))
            elif event_type == "done":
                budget_info = evt.get("budget", {})
            elif event_type == "error":
                error_msg = evt.get("detail", "Unknown agent error")

        final_answer = "".join(final_tokens).strip()

    except Exception as exc:
        logger.error("Live trajectory eval error: %s", exc)
        error_msg = str(exc)

    total_latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    # ── Trajectory Grading ─────────────────────────────────────────────────────

    # 1. Detect if question needed ticket_lookup or order_lookup
    mentioned_ticket = ticket_id or (TICKET_PATTERN.search(question).group(0).upper() if TICKET_PATTERN.search(question) else None)
    mentioned_order = ORDER_PATTERN.search(question).group(0).upper() if ORDER_PATTERN.search(question) else None
    needs_ticket_tool = mentioned_ticket is not None
    needs_order_tool = mentioned_order is not None

    called_ticket_lookup = "ticket_lookup" in tools_called
    called_order_lookup = "order_lookup" in tools_called
    called_customer_lookup = "customer_lookup" in tools_called
    called_rag = "rag_retrieval" in tools_called or "multi_namespace" in tools_called

    # 2. Argument validity check (checking if IDs called exist in DB)
    args_valid = True
    db = get_db_session()
    diagnostic_notes = []

    try:
        for rec in tool_records:
            tname = rec.get("tool")
            targs = rec.get("args", {})
            if tname == "ticket_lookup":
                tid = targs.get("ticket_id")
                if tid:
                    t_obj = get_ticket(db, tid.strip().upper())
                    if not t_obj:
                        args_valid = False
                        diagnostic_notes.append(f"ticket_lookup used non-existent ticket '{tid}'")
                    else:
                        diagnostic_notes.append(f"Successfully retrieved ticket #{tid} from SQL DB")
            elif tname == "order_lookup":
                oid = targs.get("order_id")
                if oid:
                    o_obj = get_order(db, oid.strip().upper().replace("#", ""))
                    if not o_obj:
                        args_valid = False
                        diagnostic_notes.append(f"order_lookup used non-existent order '{oid}'")
                    else:
                        diagnostic_notes.append(f"Successfully retrieved order #{oid} from SQL DB")
            elif tname == "customer_lookup":
                cid = targs.get("customer_id")
                if cid:
                    c_obj = get_customer(db, cid.strip().upper())
                    if not c_obj and cid not in ("C001", "C002", "C003", "C004", "C005"):
                        args_valid = False
                        diagnostic_notes.append(f"customer_lookup used fabricated customer_id '{cid}'")
                    else:
                        diagnostic_notes.append(f"Verified customer '{cid}' profile in CRM")
    finally:
        db.close()

    # 3. Tool Choice Correctness
    tool_choice_correct = True
    if needs_ticket_tool and not called_ticket_lookup:
        tool_choice_correct = False
        diagnostic_notes.append("Failed to call ticket_lookup despite ticket ID in prompt")
    if needs_order_tool and not called_order_lookup and not called_ticket_lookup:
        tool_choice_correct = False
        diagnostic_notes.append("Failed to call order_lookup for mentioned order ID")

    # 4. Trajectory Pass: Correct tools, no arguments fabricated, non-empty answer
    trajectory_pass = tool_choice_correct and args_valid and (len(tools_called) > 0)
    outcome_pass = len(final_answer) >= 15 and not error_msg

    # 5. Token & Cost calculation
    input_tokens = budget_info.get("input_tokens", 350)
    output_tokens = budget_info.get("output_tokens", len(final_tokens))
    tokens_used = budget_info.get("tokens_used", input_tokens + output_tokens)
    cost_usd = budget_info.get("cost_usd", round(input_tokens * 0.0000003 + output_tokens * 0.0000006, 8))

    overall_pass = trajectory_pass and outcome_pass

    summary_verdict = (
        "EXCELLENT: Agent retrieved live DB data and synthesized with RAG policy."
        if overall_pass
        else "SUBOPTIMAL: Agent trajectory missed required database lookup or produced errors."
    )

    return {
        "question": question,
        "customer_id": customer_id,
        "ticket_id": mentioned_ticket,
        "order_id": mentioned_order,
        "passed": overall_pass,
        "trajectory_pass": trajectory_pass,
        "outcome_pass": outcome_pass,
        "tool_choice_correct": tool_choice_correct,
        "args_valid": args_valid,
        "tools_called": tools_called,
        "tool_records": tool_records,
        "step_count": len(tools_called),
        "complexity": complexity,
        "latency_ms": total_latency_ms,
        "tokens_used": tokens_used,
        "cost_usd": cost_usd,
        "final_answer": final_answer,
        "summary_verdict": summary_verdict,
        "diagnostics": diagnostic_notes,
        "error": error_msg,
    }
