"""
multi_agent_orchestrator.py
===========================
Official CrewAI Multi-Agent System for Customer Support & Database Retrieval.
Built using the exact `crewai` library (Agent, Task, Crew, Process, LLM).

Architecture:
  1. Triage Specialist Agent (triage_specialist):
     - Analyzes customer query, extracts intent, IDs (ticket, order, customer), and category.
  2. CRM & Database Investigator Agent (crm_db_investigator):
     - Executes live SQL database tools (tickets, orders, schema introspection, read-only SELECT queries).
  3. Policy & Resolution Authority Agent (policy_resolver):
     - Consults knowledge base policies via hybrid dense + BM25 RAG retrieval, synthesizing
       ground-truth database findings into an authoritative final answer.

All agent and tool actions stream NDJSON events in real-time to the frontend chat UI:
  {"event":"start","session_id":...,"agent":"orchestrator","framework":"crewai"}
  {"event":"handoff","from_agent":"orchestrator","to_agent":"triage_specialist","tokens_sent":N}
  {"event":"triage_complete","agent":"triage_specialist","ticket_type":...,"summary":...}
  {"event":"handoff","from_agent":"triage_specialist","to_agent":"crm_db_investigator","tokens_sent":N}
  {"event":"tool_start","agent":"crm_db_investigator","tool":"ticket_lookup","args":{...}}
  {"event":"tool_result","agent":"crm_db_investigator","tool":"ticket_lookup","result":{...}}
  {"event":"handoff","from_agent":"crm_db_investigator","to_agent":"policy_resolver","tokens_sent":N}
  {"event":"token","agent":"policy_resolver","t":"..."}
  {"event":"done","agent":"policy_resolver","latency_ms":N,...}
  {"event":"orchestrator_done","agent":"orchestrator","latency_ms":N,...}
"""

from __future__ import annotations

import json
import logging
import os
import queue
import re
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Generator, List, Optional

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

from agent.tools.customer_lookup import make_customer_lookup_tool
from agent.tools.database_tools import make_database_schema_tool, make_db_query_tool
from agent.tools.intent_guard import classify_intent
from agent.tools.rag_retrieval import make_rag_retrieval_tool
from agent.tools.ticket_tools import (
    make_list_tickets_and_orders_tool,
    make_order_lookup_tool,
    make_ticket_lookup_tool,
)

if TYPE_CHECKING:
    from agent.memory.long_term import LongTermMemory
    from agent.memory.short_term import SessionStore
    from rag.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Triage prompt & templates
# ---------------------------------------------------------------------------
TRIAGE_PROMPT = """You are a customer support TRIAGE specialist.
Your ONLY job is to classify the incoming ticket and extract key metadata.
Do NOT answer the customer's question.

Respond with valid JSON only (no markdown):
{
  "ticket_type": "refund|shipping|account|policy|order_status|crm_list|database_query|general",
  "complexity": "simple|complex",
  "needs_order_lookup": true|false,
  "needs_customer_lookup": true|false,
  "needs_policy_lookup": true|false,
  "needs_db_list": true|false,
  "needs_schema_lookup": true|false,
  "summary": "<one-sentence description of what the customer needs>"
}

Rules:
- refund: customer wants money back or return
- shipping: delivery timeframes, tracking, address change
- account: login, suspension, invoices, billing
- order_status: tracking number, delivery status
- crm_list: user asks to list all tickets, all orders, or view CRM database records
- database_query: user asks relational questions, database schema, counts/joins across tables
- policy: general questions about policies/procedures
- general: anything else
"""

POLICY_CONTEXT_TEMPLATE = """[ORCHESTRATOR ROUTING]
Ticket type : {ticket_type}
Complexity  : {complexity}
Summary     : {summary}
Needs order : {needs_order_lookup}
Needs CRM   : {needs_customer_lookup}
Needs policy: {needs_policy_lookup}
Needs DB list: {needs_db_list}
Needs Schema: {needs_schema_lookup}

Original question:
{question}
"""


def _emit(obj: dict) -> str:
    return json.dumps(obj)


def _count_tokens(text: str) -> int:
    """Rough token estimate: words * 1.3."""
    return max(1, int(len(text.split()) * 1.3))


def get_crewai_llm(model_name: Optional[str] = None, temperature: float = 0.2) -> LLM:
    """
    Instantiate CrewAI LLM pointing to the Groq OpenAI-compatible completion API.
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    raw_model = model_name or os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-120b")
    # CrewAI openai provider strips leading 'openai/' so prefixing preserves exact model id
    crew_model = f"openai/{raw_model}" if raw_model.startswith("openai/") else f"openai/{raw_model}"
    return LLM(
        model=crew_model,
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        temperature=temperature,
    )


def build_crewai_tools(pipeline: "RAGPipeline", event_queue: Optional[queue.Queue] = None):
    """
    Wrap existing pipeline and database tools into official CrewAI tools with real-time event logging.
    """
    lc_ticket = make_ticket_lookup_tool()
    lc_order = make_order_lookup_tool()
    lc_list = make_list_tickets_and_orders_tool()
    lc_schema = make_database_schema_tool()
    lc_query = make_db_query_tool()
    lc_customer = make_customer_lookup_tool()
    lc_rag = make_rag_retrieval_tool(pipeline)

    def _push(evt: dict):
        if event_queue:
            event_queue.put(evt)

    @tool("ticket_lookup")
    def ticket_lookup(ticket_id: str = "", customer_id: str = "") -> str:
        """Look up support ticket details (status, subject, priority, description, linked order) from the SQL database. Provide ticket_id (e.g. TCK-1001) or customer_id."""
        _push({"event": "tool_start", "agent": "crm_db_investigator", "tool": "ticket_lookup", "args": {"ticket_id": ticket_id, "customer_id": customer_id}})
        try:
            res = str(lc_ticket.invoke({"ticket_id": ticket_id, "customer_id": customer_id}))
        except Exception as e:
            res = f"Error in ticket_lookup: {e}"
        _push({"event": "tool_result", "agent": "crm_db_investigator", "tool": "ticket_lookup", "result": res})
        return res

    @tool("order_lookup")
    def order_lookup(order_id: str = "", customer_id: str = "") -> str:
        """Look up customer order details (order status, carrier, tracking, items) from the SQL database. Provide order_id (e.g. ORD-1001) or customer_id."""
        _push({"event": "tool_start", "agent": "crm_db_investigator", "tool": "order_lookup", "args": {"order_id": order_id, "customer_id": customer_id}})
        try:
            res = str(lc_order.invoke({"order_id": order_id, "customer_id": customer_id}))
        except Exception as e:
            res = f"Error in order_lookup: {e}"
        _push({"event": "tool_result", "agent": "crm_db_investigator", "tool": "order_lookup", "result": res})
        return res

    @tool("list_tickets_and_orders")
    def list_tickets_and_orders(record_type: str = "both") -> str:
        """List all tickets, orders, or both from the live database. record_type can be 'tickets', 'orders', or 'both'."""
        _push({"event": "tool_start", "agent": "crm_db_investigator", "tool": "list_tickets_and_orders", "args": {"record_type": record_type}})
        try:
            res = str(lc_list.invoke({"record_type": record_type}))
        except Exception as e:
            res = f"Error in list_tickets_and_orders: {e}"
        _push({"event": "tool_result", "agent": "crm_db_investigator", "tool": "list_tickets_and_orders", "result": res})
        return res

    @tool("database_schema")
    def database_schema(table_name: str = "") -> str:
        """Inspect dynamic database schema, table structures, columns, and foreign keys."""
        _push({"event": "tool_start", "agent": "crm_db_investigator", "tool": "database_schema", "args": {"table_name": table_name}})
        try:
            res = str(lc_schema.invoke({"table_name": table_name}))
        except Exception as e:
            res = f"Error in database_schema: {e}"
        _push({"event": "tool_result", "agent": "crm_db_investigator", "tool": "database_schema", "result": res})
        return res

    @tool("db_query")
    def db_query(query: str) -> str:
        """Run a safe read-only SQL SELECT query against the customer support and order database tables."""
        _push({"event": "tool_start", "agent": "crm_db_investigator", "tool": "db_query", "args": {"query": query}})
        try:
            res = str(lc_query.invoke({"query": query}))
        except Exception as e:
            res = f"Error in db_query: {e}"
        _push({"event": "tool_result", "agent": "crm_db_investigator", "tool": "db_query", "result": res})
        return res

    @tool("customer_lookup")
    def customer_lookup(customer_id: str) -> str:
        """Look up customer profile, membership tier (basic/premium), contact info, and status for customer_id (e.g. C001)."""
        _push({"event": "tool_start", "agent": "crm_db_investigator", "tool": "customer_lookup", "args": {"customer_id": customer_id}})
        try:
            res = str(lc_customer.invoke({"customer_id": customer_id}))
        except Exception as e:
            res = f"Error in customer_lookup: {e}"
        _push({"event": "tool_result", "agent": "crm_db_investigator", "tool": "customer_lookup", "result": res})
        return res

    @tool("get_ticket")
    def get_ticket(ticket_id: str) -> str:
        """Retrieve real-time status, priority, category, subject, customer_id, and resolution notes for a support ticket (e.g. TCK-1001, TCK-1004)."""
        _push({"event": "tool_start", "agent": "crm_db_investigator", "tool": "get_ticket", "args": {"ticket_id": ticket_id}})
        db = None
        try:
            from database.session import get_db_session
            from database.crud import get_ticket as crud_get_ticket
            db = get_db_session()
            tid = ticket_id.strip().upper()
            t = crud_get_ticket(db, tid)
            if not t:
                res = json.dumps({"found": False, "error": "TICKET_NOT_FOUND", "ticket_id": tid})
            else:
                res = json.dumps({
                    "found": True,
                    "id": t.id,
                    "subject": t.subject,
                    "status": t.status,
                    "priority": t.priority,
                    "customer_id": t.customer_id,
                    "category": t.category,
                    "resolution_notes": t.resolution_notes,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                })
        except Exception as e:
            res = f"Error in get_ticket: {e}"
        finally:
            if db:
                db.close()
        _push({"event": "tool_result", "agent": "crm_db_investigator", "tool": "get_ticket", "result": res})
        return res

    @tool("get_escalation_history")
    def get_escalation_history(ticket_id: str) -> str:
        """Retrieve the full chronological escalation audit trail, agent actions, supervisor overrides, timestamps, and notes for a ticket (e.g. TCK-1004, TCK-1001)."""
        _push({"event": "tool_start", "agent": "crm_db_investigator", "tool": "get_escalation_history", "args": {"ticket_id": ticket_id}})
        db = None
        try:
            from database.session import get_db_session
            from database.crud import get_escalation_history as crud_get_escalation
            db = get_db_session()
            tid = ticket_id.strip().upper()
            events = crud_get_escalation(db, tid)
            if not events:
                res = json.dumps({"found": False, "ticket_id": tid, "event_count": 0, "message": f"No escalation events found for {tid}"})
            else:
                hist = [
                    {
                        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                        "actor": e.actor,
                        "action": e.action,
                        "note": e.note,
                    }
                    for e in events
                ]
                res = json.dumps({"found": True, "ticket_id": tid, "event_count": len(hist), "history": hist})
        except Exception as e:
            res = f"Error in get_escalation_history: {e}"
        finally:
            if db:
                db.close()
        _push({"event": "tool_result", "agent": "crm_db_investigator", "tool": "get_escalation_history", "result": res})
        return res

    @tool("intent_guard")
    def intent_guard(query: str) -> str:
        """Validate whether the customer query is a valid product support inquiry, greeting, off-topic question, or prompt injection."""
        _push({"event": "tool_start", "agent": "triage_worker", "tool": "intent_guard", "args": {"query": query}})
        is_off, intent, reply = classify_intent(query, use_llm_fallback=False)
        res = json.dumps({"is_off_topic": is_off, "intent": intent, "canned_reply": reply})
        _push({"event": "tool_result", "agent": "triage_worker", "tool": "intent_guard", "result": res})
        return res

    @tool("rag_retrieval")
    def rag_retrieval(query: str, namespace: str = "all") -> str:
        """Search knowledge base and company policy documents (shipping timeframes, return policies, warranty rules, billing) using hybrid dense + BM25 retrieval."""
        _push({"event": "tool_start", "agent": "policy_resolver", "tool": "rag_retrieval", "args": {"query": query, "namespace": namespace}})
        try:
            res = str(lc_rag.invoke({"query": query, "namespace": namespace}))
        except Exception as e:
            res = f"Error in rag_retrieval: {e}"
        _push({"event": "tool_result", "agent": "policy_resolver", "tool": "rag_retrieval", "result": res})
        return res

    return {
        "triage_tools": [intent_guard],
        "db_tools": [
            ticket_lookup,
            order_lookup,
            list_tickets_and_orders,
            database_schema,
            db_query,
            customer_lookup,
            get_ticket,
            get_escalation_history,
        ],
        "rag_tools": [rag_retrieval],
    }


def stream_multi_agent(
    pipeline: "RAGPipeline",
    question: str,
    customer_id: str = "C001",
    item_status: Optional[str] = None,
    session_id: str = "",
    temperature: float = 0.2,
    budget_config: Optional[Dict[str, Any]] = None,
    session_store: Optional["SessionStore"] = None,
    long_term: Optional["LongTermMemory"] = None,
    langfuse_trace_id: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Stream NDJSON events from the official CrewAI Multi-Agent system.
    Runs 3 specialized CrewAI Agents:
      1. triage_specialist
      2. crm_db_investigator
      3. policy_resolver
    """
    t0 = time.monotonic()
    event_queue: queue.Queue = queue.Queue()

    # Initial start event
    yield _emit({
        "event": "start",
        "session_id": session_id,
        "agent": "orchestrator",
        "mode": "multi-agent",
        "framework": "crewai",
    })

    # Fast Intent Guard Check (Instant response for pure greetings or off-topic questions)
    is_off, intent, canned_reply = classify_intent(question, use_llm_fallback=False)
    if is_off:
        yield _emit({"event": "intent_classified", "agent": "orchestrator", "intent": intent})
        for tok in canned_reply.split(" "):
            yield _emit({"event": "token", "agent": "orchestrator", "t": tok + " "})
        elapsed = round((time.monotonic() - t0) * 1000, 1)
        yield _emit({
            "event": "done",
            "agent": "orchestrator",
            "answer": canned_reply,
            "latency_ms": elapsed,
            "triage": {"ticket_type": intent, "summary": canned_reply},
        })
        yield _emit({
            "event": "orchestrator_done",
            "agent": "orchestrator",
            "framework": "crewai",
            "latency_ms": elapsed,
            "handoff_count": 0,
            "triage_tokens": 0,
            "policy_tokens": 0,
            "ticket_type": intent,
        })
        return

    # Prepare CrewAI LLM & Tools
    llm = get_crewai_llm(model_name=getattr(getattr(pipeline, "llm", None), "model_name", None), temperature=temperature)
    tools = build_crewai_tools(pipeline, event_queue)

    # ── Agents ─────────────────────────────────────────────────────────────
    triage_agent = Agent(
        role="Customer Support Triage Specialist",
        goal="Analyze the customer request, classify ticket category, extract IDs, and establish required investigations.",
        backstory=(
            "You are an expert customer service triage dispatcher. You identify the ticket category, "
            "extract customer ID, order ID, and ticket ID, and determine if database queries or policy lookups are needed."
        ),
        tools=tools["triage_tools"],
        llm=llm,
        verbose=False,
    )

    investigator_agent = Agent(
        role="CRM & Database Operations Specialist",
        goal="Query live database tables, check tickets, inspect orders, and verify customer CRM records using database tools.",
        backstory=(
            "You are a skilled database administrator and support operations investigator. "
            "You use SQL query and ticket/order lookup tools to retrieve real ground-truth facts."
        ),
        tools=tools["db_tools"],
        llm=llm,
        verbose=False,
    )

    resolver_agent = Agent(
        role="Customer Policy & Resolution Authority",
        goal="Search company policy documents via RAG retrieval and formulate an authoritative, empathetic final answer for the customer.",
        backstory=(
            "You are a senior customer resolution specialist. You consult official policy documentation "
            "and combine policy rules with verified database facts to resolve the inquiry."
        ),
        tools=tools["rag_tools"],
        llm=llm,
        verbose=False,
    )

    # State container for task transitions
    handoff_metrics = {
        "triage_tokens": _count_tokens(question + customer_id + TRIAGE_PROMPT),
        "db_tokens": 0,
        "policy_tokens": 0,
        "ticket_type": "general",
        "summary": "",
    }

    # Initial handoff: Orchestrator -> Triage Specialist
    yield _emit({
        "event": "handoff",
        "from_agent": "orchestrator",
        "to_agent": "triage_worker",
        "tokens_sent": handoff_metrics["triage_tokens"],
        "purpose": "classify ticket category and extract entities",
    })
    yield _emit({"event": "thought", "agent": "triage_worker", "text": "Classifying customer request and extracting entities..."})

    def _on_triage_done(task_output):
        text = str(task_output.raw if hasattr(task_output, "raw") else task_output)
        handoff_metrics["summary"] = text[:150]
        # Infer ticket type
        lower = text.lower()
        if "refund" in lower or "return" in lower:
            handoff_metrics["ticket_type"] = "refund"
        elif "shipping" in lower or "delivery" in lower or "carrier" in lower:
            handoff_metrics["ticket_type"] = "shipping"
        elif "order" in lower:
            handoff_metrics["ticket_type"] = "order_status"
        elif "schema" in lower or "table" in lower or "sql" in lower or "database" in lower:
            handoff_metrics["ticket_type"] = "database_query"
        elif "account" in lower:
            handoff_metrics["ticket_type"] = "account"
        else:
            handoff_metrics["ticket_type"] = "policy"

        handoff_metrics["db_tokens"] = _count_tokens(text)
        event_queue.put({
            "event": "triage_complete",
            "agent": "triage_worker",
            "ticket_type": handoff_metrics["ticket_type"],
            "summary": handoff_metrics["summary"],
            "complexity": "simple",
            "needs_order_lookup": "order" in lower,
            "needs_customer_lookup": True,
            "needs_policy_lookup": "policy" in lower or "refund" in lower or "shipping" in lower,
            "needs_db_list": "list" in lower,
            "needs_schema_lookup": "schema" in lower or "table" in lower,
        })
        event_queue.put({
            "event": "handoff",
            "from_agent": "triage_worker",
            "to_agent": "crm_db_investigator",
            "tokens_sent": handoff_metrics["db_tokens"],
            "purpose": f"investigate database records for {handoff_metrics['ticket_type']}",
        })
        event_queue.put({
            "event": "thought",
            "agent": "crm_db_investigator",
            "text": f"Investigating database records and customer profile for {customer_id}...",
        })

    def _on_investigation_done(task_output):
        text = str(task_output.raw if hasattr(task_output, "raw") else task_output)
        handoff_metrics["policy_tokens"] = _count_tokens(text)
        event_queue.put({
            "event": "handoff",
            "from_agent": "crm_db_investigator",
            "to_agent": "policy_worker",
            "tokens_sent": handoff_metrics["policy_tokens"],
            "purpose": "apply company policies and compose final resolution",
        })
        event_queue.put({
            "event": "thought",
            "agent": "policy_worker",
            "text": "Retrieving policy guidelines and synthesizing final customer response...",
        })

    # ── Tasks ──────────────────────────────────────────────────────────────
    triage_task = Task(
        description=(
            f"Customer ID: {customer_id}\n"
            f"Query: {question}\n"
            "Analyze the inquiry. Determine ticket category (refund, shipping, order_status, database_query, policy, general), "
            "extract IDs (ticket ID, order ID, customer ID), and state what data must be retrieved."
        ),
        expected_output="Triage classification summary with category, extracted IDs, and needed checks.",
        agent=triage_agent,
        callback=_on_triage_done,
    )

    investigation_task = Task(
        description=(
            f"For customer {customer_id} and inquiry '{question}', check the database tools for relevant facts:\n"
            "- If a ticket ID or order ID is mentioned, look it up using ticket_lookup or get_ticket.\n"
            "- If the user asks about escalation history, audit events, supervisor actions, or what happened on a ticket, use get_escalation_history.\n"
            "- If customer records or accounts are referenced, look up customer.\n"
            "- If relational or database schema questions are asked, inspect schema or query tables.\n"
            "State all verified database facts found."
        ),
        expected_output="Verified factual findings from the SQL database and CRM records.",
        agent=investigator_agent,
        context=[triage_task],
        callback=_on_investigation_done,
    )

    resolution_task = Task(
        description=(
            f"Using the verified investigation facts and customer query '{question}', "
            "search official policy documents with rag_retrieval if necessary. "
            "Write the complete, empathetic, professional final answer resolving the customer's request."
        ),
        expected_output="The final, complete customer response answering the inquiry with verified evidence.",
        agent=resolver_agent,
        context=[triage_task, investigation_task],
    )

    crew = Crew(
        agents=[triage_agent, investigator_agent, resolver_agent],
        tasks=[triage_task, investigation_task, resolution_task],
        process=Process.sequential,
        verbose=False,
    )

    # Run Crew in background worker thread and pump events to caller
    execution_result: Dict[str, Any] = {"result": None, "error": None, "done": False}

    def _worker():
        try:
            res = crew.kickoff()
            execution_result["result"] = str(res)
        except Exception as exc:
            logger.exception("CrewAI execution error: %s", exc)
            execution_result["error"] = str(exc)
        finally:
            execution_result["done"] = True
            event_queue.put(None)  # Sentinel to stop queue polling

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    # Stream real-time events as they arrive
    while True:
        try:
            evt = event_queue.get(timeout=0.1)
            if evt is None:
                break
            yield _emit(evt)
        except queue.Empty:
            if execution_result["done"]:
                break

    # Drain any remaining events in the queue
    while not event_queue.empty():
        evt = event_queue.get_nowait()
        if evt is not None:
            yield _emit(evt)

    # Determine final response
    elapsed = round((time.monotonic() - t0) * 1000, 1)
    if execution_result["error"]:
        final_answer = (
            f"I encountered a temporary issue while coordinating with our support specialists: "
            f"{execution_result['error']}. Please try again or contact support."
        )
    else:
        final_answer = execution_result["result"] or "Inquiry resolved."

    # Stream answer tokens for frontend typewriter effect
    tokens = final_answer.split(" ")
    for tok in tokens:
        yield _emit({
            "event": "token",
            "agent": "policy_worker",
            "t": tok + " ",
        })

    # Final completion events
    yield _emit({
        "event": "done",
        "agent": "policy_worker",
        "answer": final_answer,
        "latency_ms": elapsed,
        "triage": {
            "ticket_type": handoff_metrics["ticket_type"],
            "summary": handoff_metrics["summary"],
        },
    })

    yield _emit({
        "event": "orchestrator_done",
        "agent": "orchestrator",
        "framework": "crewai",
        "latency_ms": elapsed,
        "handoff_count": 3,
        "triage_tokens": handoff_metrics["triage_tokens"],
        "policy_tokens": handoff_metrics["policy_tokens"],
        "ticket_type": handoff_metrics["ticket_type"],
    })


# Alias for backwards compatibility
stream_crew_agent = stream_multi_agent
