"""
LangGraph ReAct agent with:
  - Tiered system prompt (simple 1-tool vs complex multi-tool)
  - Pre-step question classifier: auto-detects complexity + best namespace
  - Tiered tool budget: max 1 tool for simple, up to 3 for complex questions
  - Wall-clock enforcement via started_at in budget_summary
  - customer_lookup tool for personalised escalation (fixes T06, T07)
  - Hybrid dense+BM25 search via rag_retrieval (improved accuracy)
  - LLM-as-Judge scoring after every agent run (faithfulness, relevancy)
  - Full Langfuse AGENT/TOOL typed tracing per run
  - Short-term memory via LangGraph message state
  - Long-term memory via mem0 + Pinecone vector summaries
  - NDJSON streaming for the /agent/stream endpoint
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from typing import TYPE_CHECKING, Annotated, Any, Dict, Generator, List, Optional, TypedDict

from observability.langfuse_client import create_trace, flush_langfuse, is_enabled

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage,
)
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agent.budgets import BudgetTracker
from agent.memory.long_term import LongTermMemory
from agent.memory.short_term import SessionStore
from agent.tools.registry import build_agent_tools

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts — tiered by question complexity
# ---------------------------------------------------------------------------

REACT_SYSTEM_PROMPT_SIMPLE = """You are a customer support agent. Answer questions using ONLY the information returned by your tools.

QUESTION TYPE: Simple (one-step retrieval is sufficient)

RULES:
- Call rag_retrieval ONCE to get relevant document chunks.
- Give a direct Final Answer based only on what the tool returned.
- If retrieved content has no relevant info, say: "Based on our documentation, I don't have specific information about that. Please contact support directly."
- Do NOT call more than 1 tool. Retrieve once, answer once.

RESPONSE FORMAT:
Thought: <one sentence — what I need to look up>
[call rag_retrieval with a precise, specific query]
Final Answer: <direct answer based only on tool result>

TOOLS:
- rag_retrieval — for ALL questions about policies, shipping, returns, billing, refunds, accounts.
- doc_metadata / doc_summarizer — ONLY if asked "what topics do you cover?" or "what files exist?".

Never invent facts. Always end with Final Answer.
"""

REACT_SYSTEM_PROMPT_COMPLEX = """You are a customer support agent. Answer questions using ONLY the information returned by your tools.

QUESTION TYPE: Complex (may require customer context + policy lookup)

RULES:
- Step 1: If the question involves escalation, priority, or account-specific handling → call customer_lookup FIRST to get the customer's tier.
- Step 2: Call rag_retrieval to find the relevant policy or procedure.
- Step 3: Combine customer tier + policy to give a personalised Final Answer.
- Maximum 3 tool calls. Think carefully before each call.
- If info is insufficient after 2 tools, give the best answer you can and recommend contacting support.

RESPONSE FORMAT:
Thought: <what do I need to know — customer context or policy?>
[call customer_lookup if customer tier is relevant]
Thought: <what policy should I look up?>
[call rag_retrieval with a precise query]
Final Answer: <personalised answer combining customer tier + policy info>

TOOLS:
- customer_lookup — get customer tier (basic/premium/vip), account status, escalation policy.
- rag_retrieval   — search company documents for policies, procedures, and guidelines.
- multi_namespace — search across ALL document categories at once (use for broad questions).

Never invent facts. Always end with Final Answer.
"""


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    customer_id: str
    item_status: Optional[str]
    session_id: str
    abort: bool
    budget_summary: Dict[str, Any]
    tool_calls_log: List[Dict[str, Any]]
    complexity: str   # "simple" | "complex"


def _extract_tokens(response) -> tuple:
    """
    Robust token extractor that handles:
    - LangChain UsageMetadata object  (usage_metadata.input_tokens / output_tokens)
    - Groq raw response_metadata dict (token_usage.prompt_tokens / completion_tokens)
    Returns (input_tokens, output_tokens) as ints.
    """
    # Try standard LangChain usage_metadata first
    um = getattr(response, "usage_metadata", None)
    if um:
        inp = getattr(um, "input_tokens", None) or (um.get("input_tokens", 0) if hasattr(um, "get") else 0)
        out = getattr(um, "output_tokens", None) or (um.get("output_tokens", 0) if hasattr(um, "get") else 0)
        if inp or out:
            return int(inp), int(out)

    # Groq fallback: response_metadata → token_usage
    rm = getattr(response, "response_metadata", {}) or {}
    tu = rm.get("token_usage", {}) or {}
    inp = tu.get("prompt_tokens", 0)
    out = tu.get("completion_tokens", 0)
    return int(inp), int(out)


# ---------------------------------------------------------------------------
# Pre-step: question complexity classifier + namespace router
# ---------------------------------------------------------------------------

def _classify_question(question: str, pipeline: "RAGPipeline") -> Dict[str, Any]:
    """
    Quickly classify a question BEFORE the agent loop starts.

    Returns:
        {
          "complexity": "simple" | "complex",
          "namespace": "<best namespace or 'all'>",
          "needs_customer_context": bool,
          "rewritten_query": "<cleaned-up retrieval query>"
        }

    Uses a fast LLM call with temperature=0 for deterministic output.
    Falls back to {"complexity": "simple", "namespace": "all"} on any error.
    """
    try:
        namespaces = pipeline.get_namespaces() if hasattr(pipeline, "get_namespaces") else []
        ns_list = ", ".join(namespaces) if namespaces else "all"

        classify_prompt = f"""Classify this customer support question.

Question: "{question}"

Available document namespaces: {ns_list}

Respond with valid JSON only:
{{
  "complexity": "simple" or "complex",
  "namespace": "<best namespace from the list above, or 'all'>",
  "needs_customer_context": true or false,
  "rewritten_query": "<rewrite the question as a precise search query>"
}}

Rules:
- complexity=complex ONLY if the question involves: escalation, customer tier, premium/VIP treatment, account suspension, multi-step dependency.
- needs_customer_context=true ONLY if knowing the customer's tier changes the answer.
- rewritten_query: make the query specific and document-search friendly (e.g., "refund policy damaged items" not "I want my money back").
"""
        response = pipeline.llm.client.chat.completions.create(
            model=pipeline.llm.model_name,
            messages=[
                {"role": "system", "content": "You are a classification assistant. Respond with valid JSON only, no markdown."},
                {"role": "user", "content": classify_prompt},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        # Validate fields
        result.setdefault("complexity", "simple")
        result.setdefault("namespace", "all")
        result.setdefault("needs_customer_context", False)
        result.setdefault("rewritten_query", question)
        logger.info(
            "Question classified: complexity=%s ns=%s needs_customer=%s",
            result["complexity"], result["namespace"], result["needs_customer_context"]
        )
        return result
    except Exception as exc:
        logger.warning("Question classification failed (%s) — defaulting to simple", exc)
        return {
            "complexity": "simple",
            "namespace": "all",
            "needs_customer_context": False,
            "rewritten_query": question,
        }


# ---------------------------------------------------------------------------
# Agent graph builder
# ---------------------------------------------------------------------------

def build_react_agent(pipeline: "RAGPipeline", complexity: str = "simple"):
    """Build and compile the LangGraph ReAct agent graph."""
    tools = build_agent_tools(pipeline)
    agent_model = (
        os.getenv("GROQ_AGENT_MODEL_NAME")
        or os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-120b")
    ).removeprefix("groq/")
    logger.info("ReAct agent using model: %s | complexity: %s", agent_model, complexity)

    llm_with_tools = ChatGroq(
        model=agent_model,
        api_key=os.getenv("GROQ_API_KEY", ""),
        temperature=0.2,
    ).bind_tools(tools)

    # Separate LLM instance with NO tools — used to force a final answer
    llm_no_tools = ChatGroq(
        model=agent_model,
        api_key=os.getenv("GROQ_API_KEY", ""),
        temperature=0.2,
    )

    tool_node = ToolNode(tools, handle_tool_errors=True)

    def llm_node(state: AgentState) -> dict:
        response = llm_with_tools.invoke(state["messages"])
        inp, out = _extract_tokens(response)
        prev = state.get("budget_summary", {})
        accumulated_tokens = prev.get("tokens_used", 0) + inp + out
        accumulated_cost   = prev.get("cost_usd", 0.0) + (inp * 0.0000003 + out * 0.0000006)
        iterations         = prev.get("iterations", 0) + 1
        # Count tool calls in this response
        tool_calls_in_response = len(response.tool_calls) if hasattr(response, "tool_calls") and response.tool_calls else 0
        tool_calls_made = prev.get("tool_calls_made", 0) + tool_calls_in_response

        return {
            "messages": [response],
            "budget_summary": {
                "iterations":     iterations,
                "tokens_used":    accumulated_tokens,
                "tool_calls_made": tool_calls_made,
                "cost_usd":       round(accumulated_cost, 8),
                "started_at":     prev.get("started_at"),
                "limits":         prev.get("limits", {}),
            },
        }

    def force_answer_node(state: AgentState) -> dict:
        """
        Runs when the budget is exhausted. Calls the LLM WITHOUT tools
        so it is forced to write a Final Answer using gathered info.
        """
        nudge = SystemMessage(
            content=(
                "You have reached the maximum number of tool calls allowed. "
                "Using only the information you have already gathered, give the customer "
                "a direct, concise answer right now. "
                "Begin your reply with 'Final Answer:'"
            )
        )
        response = llm_no_tools.invoke(list(state["messages"]) + [nudge])
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        if state.get("abort"):
            return "force_answer"

        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return "end"

        budget = state.get("budget_summary", {})
        limits = budget.get("limits", {})

        # Iteration budget
        if budget.get("iterations", 0) >= limits.get("max_iterations", 8):
            return "force_answer"
        # Token budget
        if budget.get("tokens_used", 0) >= limits.get("max_tokens", 6000):
            return "force_answer"
        # Cost budget
        if budget.get("cost_usd", 0.0) >= limits.get("max_cost_usd", 0.02):
            return "force_answer"
        # ── Tiered tool-call budget ──────────────────────────────────────────
        max_tool_calls = limits.get("max_tool_calls", 1)  # 1=simple, 3=complex
        if budget.get("tool_calls_made", 0) > max_tool_calls:
            return "force_answer"
        # ── Wall-clock budget ────────────────────────────────────────────────
        started_at = budget.get("started_at")
        wall_limit = limits.get("wall_clock_sec", 30.0)
        if started_at is not None:
            elapsed = time.monotonic() - started_at
            if elapsed >= wall_limit:
                logger.warning("Agent wall-clock limit hit: %.1fs >= %.1fs", elapsed, wall_limit)
                return "force_answer"

        return "tools"

    graph = StateGraph(AgentState)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)
    graph.add_node("force_answer", force_answer_node)
    graph.set_entry_point("llm")
    graph.add_conditional_edges(
        "llm",
        should_continue,
        {"tools": "tools", "end": END, "force_answer": "force_answer"},
    )
    graph.add_edge("tools", "llm")
    graph.add_edge("force_answer", END)
    return graph.compile()


# ── Streaming interface used by FastAPI ────────────────────────────────────────

def stream_agent(
    pipeline: "RAGPipeline",
    question: str,
    customer_id: str = "C001",
    item_status: Optional[str] = None,
    session_id: str = "",
    temperature: float = 0.2,
    budget_config: Optional[Dict[str, Any]] = None,
    session_store: Optional[SessionStore] = None,
    long_term: Optional[LongTermMemory] = None,
    langfuse_trace_id: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Run the ReAct agent and yield NDJSON event lines:
      {"event":"start","session_id":"..."}
      {"event":"classified","complexity":"...","namespace":"..."}
      {"event":"thought","text":"..."}
      {"event":"tool_start","tool":"...","args":{...}}
      {"event":"tool_result","tool":"...","result":{...}}
      {"event":"token","t":"..."}
      {"event":"done","latency_ms":N,"tool_calls_made":N,"budget":{...}}
      {"event":"budget_hit","reason":"...","partial_answer":"..."}
      {"event":"error","detail":"..."}
    """
    t0 = time.monotonic()

    COST_PER_INPUT  = 0.0000003
    COST_PER_OUTPUT = 0.0000006

    def _emit(obj: dict) -> str:
        return json.dumps(obj)

    # ── Langfuse: create parent trace ──────────────────────────────────────
    agent_model_name = (
        os.getenv("GROQ_AGENT_MODEL_NAME")
        or os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-120b")
    ).removeprefix("groq/")

    _lf_trace = create_trace(
        id=langfuse_trace_id if langfuse_trace_id else None,
        name="react-agent-run",
        input={"question": question},
        user_id=customer_id,
        session_id=session_id or None,
        tags=["agent", "react"],
        metadata={"customer_id": customer_id, "item_status": item_status, "model": agent_model_name},
    )
    _agent_span  = _lf_trace.span(name="ReActAgent", input={"question": question}, level="DEFAULT")
    _tool_spans: Dict[str, Any] = {}
    _current_llm_gen = None
    # ──────────────────────────────────────────────────────────────────────

    yield _emit({"event": "start", "session_id": session_id})

    # ── Intent guard ───────────────────────────────────────────────────────
    from agent.tools.intent_guard import classify_intent
    is_off, intent, canned_reply = classify_intent(question, use_llm_fallback=False)
    if is_off:
        yield _emit({"event": "intent", "intent": intent})
        for i, word in enumerate(canned_reply.split(" ")):
            yield _emit({"event": "token", "t": word if i == 0 else " " + word})
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        _agent_span.end(output={"answer": canned_reply, "intent": intent, "short_circuit": True})
        _lf_trace.update(output={"answer": canned_reply, "intent": intent}, metadata={"short_circuit": True})
        _lf_trace.score(name="latency_ms", value=latency_ms)
        flush_langfuse()
        yield _emit({"event": "done", "latency_ms": latency_ms, "tool_calls_made": 0, "budget": {}, "intent": intent})
        return

    # ── Pre-step: classify question complexity + best namespace ────────────
    classification = _classify_question(question, pipeline)
    complexity        = classification["complexity"]          # "simple" | "complex"
    best_namespace    = classification["namespace"]           # e.g. "Product Returns & Refund Policy"
    needs_customer    = classification["needs_customer_context"]
    rewritten_query   = classification["rewritten_query"]

    yield _emit({
        "event":      "classified",
        "complexity": complexity,
        "namespace":  best_namespace,
        "needs_customer_context": needs_customer,
        "rewritten_query": rewritten_query,
    })

    # Pick system prompt based on complexity
    system_prompt = REACT_SYSTEM_PROMPT_COMPLEX if complexity == "complex" else REACT_SYSTEM_PROMPT_SIMPLE
    # Inject detected namespace hint into system prompt
    if best_namespace and best_namespace != "all":
        system_prompt += f"\n\n[ROUTING HINT] Best namespace for this question: '{best_namespace}'. Pass this as the namespace arg to rag_retrieval."
    if needs_customer:
        system_prompt += f"\n[ROUTING HINT] Call customer_lookup(customer_id='{customer_id}') FIRST to get customer tier before retrieving policy."

    # ── Build initial messages ─────────────────────────────────────────────
    messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]

    # Inject mem0 long-term facts
    if long_term and session_id:
        fact_msg = long_term.build_mem0_system_message(session_id, question)
        if fact_msg:
            messages.append(fact_msg)

    # Inject prior session summary from Pinecone
    if long_term and session_id:
        prior_summary = long_term.recall_session_summary(session_id, question)
        if prior_summary:
            messages.append(SystemMessage(content=f"[Earlier session context]: {prior_summary}"))

    # Inject short-term history
    if session_store and session_id:
        history = session_store.get(session_id, limit=10)
        for h in history:
            if h["role"] == "user":
                messages.append(HumanMessage(content=h["content"]))
            else:
                messages.append(AIMessage(content=h["content"]))

    # Use rewritten query for better retrieval, keep original for display
    messages.append(HumanMessage(content=rewritten_query if rewritten_query != question else question))

    # ── Build and run agent ────────────────────────────────────────────────
    compiled = build_react_agent(pipeline, complexity=complexity)
    budget_cfg = budget_config or {}

    # Tiered tool budget: simple=1 tool, complex=3 tools
    max_tool_calls = 3 if complexity == "complex" else 1

    initial_state: AgentState = {
        "messages":   messages,
        "customer_id": customer_id,
        "item_status": item_status,
        "session_id":  session_id,
        "abort":       False,
        "complexity":  complexity,
        "budget_summary": {
            "started_at": t0,       # wall-clock anchor
            "tool_calls_made": 0,
            "limits": {
                "max_iterations":  budget_cfg.get("max_iterations", 5),
                "max_tokens":      budget_cfg.get("max_tokens", 8000),
                "max_cost_usd":    budget_cfg.get("max_cost_usd", 0.05),
                "wall_clock_sec":  budget_cfg.get("wall_clock_sec", 30.0),
                "max_tool_calls":  budget_cfg.get("max_tool_calls", max_tool_calls),
            }
        },
        "tool_calls_log": [],
    }

    tool_calls_made = 0
    final_answer    = ""
    budget_hit      = False
    budget_reason   = ""
    budget_summary: Dict[str, Any] = {}
    seen_msg_ids: set = set()
    _current_llm_gen = None
    # Track all retrieved chunks for LLM-as-Judge
    all_context_chunks: List[str] = []

    try:
        for chunk in compiled.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                if not isinstance(node_output, dict):
                    continue

                if "budget_summary" in node_output:
                    budget_summary = node_output["budget_summary"]

                for msg in node_output.get("messages", []):
                    msg_id = getattr(msg, "id", None)
                    if msg_id and msg_id in seen_msg_ids:
                        continue
                    if msg_id:
                        seen_msg_ids.add(msg_id)

                    if isinstance(msg, AIMessage):
                        if msg.content:
                            if isinstance(msg.content, list):
                                content_str = "\n".join(
                                    b["text"] if isinstance(b, dict) and "text" in b else str(b)
                                    for b in msg.content
                                )
                            else:
                                content_str = msg.content

                            # Close any open LLM generation span
                            inp_tok, out_tok = _extract_tokens(msg)
                            if _current_llm_gen is not None:
                                try:
                                    _current_llm_gen.end(
                                        output={"text": content_str[:500]},
                                        usage={"input": inp_tok, "output": out_tok},
                                    )
                                except Exception:
                                    pass
                                _current_llm_gen = None

                            if "Final Answer:" in content_str:
                                final_answer = content_str.split("Final Answer:", 1)[-1].strip()
                                yield _emit({"event": "thought", "text": content_str})
                                for i, word in enumerate(final_answer.split(" ")):
                                    yield _emit({"event": "token", "t": word if i == 0 else " " + word})
                            elif not msg.tool_calls:
                                final_answer = content_str
                                if "Thought:" in content_str:
                                    yield _emit({"event": "thought", "text": content_str})
                                for i, word in enumerate(final_answer.split(" ")):
                                    yield _emit({"event": "token", "t": word if i == 0 else " " + word})
                            else:
                                if "Thought:" in content_str:
                                    yield _emit({"event": "thought", "text": content_str})

                        # Open a generation span for the next LLM iteration
                        _current_llm_gen = _agent_span.generation(
                            name=f"llm-node-iter-{budget_summary.get('iterations', 0) + 1}",
                            model=agent_model_name,
                            input={"question": question},
                        ) if not msg.tool_calls else None

                        for tc in (msg.tool_calls or []):
                            tool_calls_made += 1
                            # Open a TOOL-typed span (counted by Langfuse as Tool Call)
                            _tool_spans[tc["name"]] = _agent_span.span(
                                name=tc["name"],
                                input=tc.get("args", {}),
                                metadata={"tool_call_id": tc.get("id", "")},
                            )
                            yield _emit({"event": "tool_start", "tool": tc["name"], "args": tc.get("args", {})})

                    elif isinstance(msg, ToolMessage):
                        result = msg.content
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except Exception:
                                pass

                        # Collect retrieved chunks for LLM-as-Judge
                        if isinstance(result, dict) and "chunks" in result:
                            for c in result.get("chunks", []):
                                if c.get("text"):
                                    all_context_chunks.append(c["text"])

                        # Close the matching TOOL span
                        tool_name = msg.name or "unknown"
                        _ts = _tool_spans.pop(tool_name, None)
                        if _ts is not None:
                            try:
                                out_preview = (
                                    str(result)[:500]
                                    if not isinstance(result, dict)
                                    else {k: str(v)[:200] for k, v in list(result.items())[:5]}
                                )
                                _ts.end(output=out_preview)
                            except Exception:
                                pass

                        yield _emit({"event": "tool_result", "tool": tool_name, "result": result})

    except Exception as exc:
        # ── Fallback: direct retrieval ──────────────────────────────────────
        logger.warning("Agent graph failed (%s) — falling back to direct retrieval", exc)
        yield _emit({"event": "thought", "text": f"[Fallback] Direct retrieval (reason: {exc})"})

        try:
            from agent.tools.registry import build_agent_tools
            fallback_tools = {t.name: t for t in build_agent_tools(pipeline)}

            tool_calls_made += 1
            yield _emit({"event": "tool_start", "tool": "rag_retrieval", "args": {"query": question, "top_k": 5}})
            retrieval = fallback_tools["rag_retrieval"].invoke({"query": question, "top_k": 5})
            chunks = retrieval.get("chunks", []) if isinstance(retrieval, dict) else []
            all_context_chunks.extend(c.get("text", "") for c in chunks if c.get("text"))
            yield _emit({"event": "tool_result", "tool": "rag_retrieval", "result": retrieval})

            context = "\n\n---\n\n".join(c.get("text", "") for c in chunks if c.get("text"))
            fallback_model = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-120b").removeprefix("groq/")
            plain_llm = ChatGroq(model=fallback_model, api_key=os.getenv("GROQ_API_KEY", ""), temperature=0.2)
            fb_prompt = (
                f"You are a helpful customer support agent. "
                f"Answer the customer's question using ONLY the context below.\n\nContext:\n{context}\n\n"
                f"Question: {question}\n\nAnswer:"
            ) if context else (
                f"You are a helpful customer support agent. Question: {question}\n\n"
                "No specific documentation was found. Provide a helpful general response and ask the customer to contact support.\n\nAnswer:"
            )
            fb_response = plain_llm.invoke([HumanMessage(content=fb_prompt)])
            final_answer = fb_response.content if isinstance(fb_response.content, str) else str(fb_response.content)
            fb_inp, fb_out = _extract_tokens(fb_response)
            budget_summary = {
                "tokens_used": fb_inp + fb_out,
                "cost_usd": round(fb_inp * COST_PER_INPUT + fb_out * COST_PER_OUTPUT, 8),
                "fallback": True,
            }
        except Exception as fb_exc:
            final_answer = "I'm sorry, I encountered an error while retrieving information. Please contact our support team directly for assistance."
            logger.error("Fallback also failed: %s", fb_exc)

        for i, word in enumerate(final_answer.split(" ")):
            yield _emit({"event": "token", "t": word if i == 0 else " " + word})

    if budget_summary.get("abort"):
        budget_hit    = True
        budget_reason = "Agent aborted due to budget limit"

    latency_ms = round((time.monotonic() - t0) * 1000, 1)

    # ── Langfuse: close open spans + score trace ───────────────────────────
    for _ts in _tool_spans.values():
        try:
            _ts.end(output={"note": "closed at agent end"})
        except Exception:
            pass

    _agent_span.end(output={
        "answer": final_answer[:500] if final_answer else "",
        "tool_calls_made": tool_calls_made,
        "budget_hit": budget_hit,
        "complexity": complexity,
    })

    _lf_trace.update(
        output={"answer": final_answer[:500] if final_answer else "", "latency_ms": latency_ms, "tool_calls_made": tool_calls_made},
        metadata={"budget": budget_summary, "budget_hit": budget_hit, "complexity": complexity},
    )
    _lf_trace.score(name="latency_ms",       value=latency_ms,             comment="End-to-end agent latency in ms")
    _lf_trace.score(name="tool_calls_made",  value=float(tool_calls_made), comment="Number of tool invocations")
    if budget_hit:
        _lf_trace.score(name="budget_hit", value=1.0, comment=budget_reason)
    tokens_used = budget_summary.get("tokens_used", 0)
    if tokens_used:
        _lf_trace.score(name="tokens_used", value=float(tokens_used))

    # ── LLM-as-Judge: score faithfulness, relevancy, context_utilization ──
    if is_enabled() and all_context_chunks and final_answer and not budget_hit:
        try:
            from eval.llm_judge import LLMJudge
            judge = LLMJudge(groq_client=pipeline.llm.client)
            judge.score_trace(
                trace=_lf_trace,
                question=question,
                context_chunks=all_context_chunks[:5],   # top 5 chunks max
                answer=final_answer,
            )
            logger.info("LLM-as-Judge scored agent trace for: %s", question[:60])
        except Exception as judge_exc:
            logger.warning("LLM-as-Judge agent scoring failed: %s", judge_exc)

    flush_langfuse()
    # ──────────────────────────────────────────────────────────────────────

    if budget_hit:
        yield _emit({"event": "budget_hit", "reason": budget_reason, "partial_answer": final_answer})

    yield _emit({
        "event":           "done",
        "latency_ms":      latency_ms,
        "tool_calls_made": tool_calls_made,
        "budget":          budget_summary,
        "complexity":      complexity,
    })

    # ── Persist to memory ──────────────────────────────────────────────────
    if session_store and session_id and final_answer:
        session_store.append(session_id, "user", question)
        session_store.append(session_id, "assistant", final_answer)

    if long_term and session_id and final_answer:
        long_term.store_mem0(session_id, [
            {"role": "user",      "content": question},
            {"role": "assistant", "content": final_answer},
        ])


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv()

    from rag.rag_pipeline import RAGPipeline

    parser = argparse.ArgumentParser(description="Run the ReAct agent from CLI")
    parser.add_argument("--question",    required=True)
    parser.add_argument("--customer_id", default="C001")
    parser.add_argument("--item_status", default=None)
    parser.add_argument("--session_id",  default="")
    args = parser.parse_args()

    pipeline = RAGPipeline()
    print(f"\n{'='*60}")
    print(f"Question: {args.question}")
    print(f"{'='*60}")

    for line in stream_agent(
        pipeline=pipeline,
        question=args.question,
        customer_id=args.customer_id,
        item_status=args.item_status,
        session_id=args.session_id,
    ):
        event = json.loads(line)
        etype = event.get("event", "")
        if etype == "classified":
            print(f"\n[CLASSIFY] complexity={event['complexity']} | ns={event['namespace']} | rewritten='{event.get('rewritten_query','')}'")
        elif etype == "thought":
            print(f"\n[THOUGHT] {event.get('text','')[:200]}")
        elif etype == "tool_start":
            print(f"[TOOL] {event['tool']} → {event.get('args', {})}")
        elif etype == "tool_result":
            print(f"[RESULT] {str(event.get('result',''))[:200]}")
        elif etype == "token":
            print(event["t"], end="", flush=True)
        elif etype == "done":
            print(f"\n\n[BUDGET] {event.get('budget', {})} | complexity={event.get('complexity')}")
            print(f"[LATENCY] {event.get('latency_ms')} ms | Tools used: {event.get('tool_calls_made')}")
        elif etype == "budget_hit":
            print(f"\n[BUDGET HIT] {event.get('reason')}")
        elif etype == "error":
            print(f"\n[ERROR] {event.get('detail')}")
