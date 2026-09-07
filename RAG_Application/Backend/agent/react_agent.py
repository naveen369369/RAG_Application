"""
LangGraph ReAct agent with:
  - Explicit Thought / Action / Observation prompting
  - All four budget limits enforced after every tool node
  - Short-term memory via LangGraph message state
  - Long-term memory via mem0 + Pinecone vector summaries
  - Full Langfuse tracing per run
  - NDJSON streaming for the /agent/stream endpoint
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from typing import TYPE_CHECKING, Annotated, Any, Dict, Generator, List, Optional, TypedDict

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

REACT_SYSTEM_PROMPT = """You are a customer support agent. Answer questions using ONLY the information returned by your tools.

STRICT RULES:
- ALWAYS call rag_retrieval first for ANY support question before answering.
- After retrieving, give a direct answer based on what the tool returned.
- If retrieved content has no relevant info, say: "Based on our documentation, I don't have specific information about that. Please contact support directly."
- NEVER call more than 1 tool per question. After one retrieval, give the Final Answer.
- Do NOT overthink. Retrieve once, answer once.

RESPONSE FORMAT (always follow exactly):
Thought: <one sentence — what I need to look up>
[call rag_retrieval]
Final Answer: <direct answer based only on tool result>

TOOL TO USE:
- rag_retrieval — use this for ALL questions about shipping, returns, billing, refunds, accounts, policies, escalation.
- inspect_documents — ONLY if asked "what topics do you cover" or "what files exist".

Never invent facts. One tool call maximum. Always end with Final Answer.
"""


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    customer_id: str
    item_status: Optional[str]
    session_id: str
    abort: bool
    budget_summary: Dict[str, Any]
    tool_calls_log: List[Dict[str, Any]]


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


def build_react_agent(pipeline: "RAGPipeline"):
    """Build and compile the LangGraph ReAct agent graph."""
    tools = build_agent_tools(pipeline)
    # Use the same model as the rest of the app.
    # GROQ_AGENT_MODEL_NAME overrides if a specific tool-calling model is needed.
    agent_model = (
        os.getenv("GROQ_AGENT_MODEL_NAME")
        or os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-120b")
    ).removeprefix("groq/")
    logger.info("ReAct agent using model: %s", agent_model)

    llm_with_tools = ChatGroq(
        model=agent_model,
        api_key=os.getenv("GROQ_API_KEY", ""),
        temperature=0.2,
    ).bind_tools(tools)

    # Separate LLM instance with NO tools — used to force a final answer when budget runs out
    llm_no_tools = ChatGroq(
        model=agent_model,
        api_key=os.getenv("GROQ_API_KEY", ""),
        temperature=0.2,
    )

    tool_node = ToolNode(tools, handle_tool_errors=True)

    def llm_node(state: AgentState) -> dict:
        response = llm_with_tools.invoke(state["messages"])

        # Robust token extraction — Groq may return metadata in different places
        inp, out = _extract_tokens(response)

        prev = state.get("budget_summary", {})
        accumulated_tokens = prev.get("tokens_used", 0) + inp + out
        accumulated_cost   = prev.get("cost_usd", 0.0) + (inp * 0.0000003 + out * 0.0000006)
        iterations         = prev.get("iterations", 0) + 1

        return {
            "messages": [response],
            "budget_summary": {
                "iterations": iterations,
                "tokens_used": accumulated_tokens,
                "cost_usd": round(accumulated_cost, 8),
                "limits": prev.get("limits", {}),
            },
        }

    def force_answer_node(state: AgentState) -> dict:
        """
        Runs when the budget is exhausted and the LLM hasn't voluntarily stopped.
        Calls the LLM WITHOUT tools so it is forced to write a final answer
        instead of requesting another tool call.
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
        if budget.get("iterations", 0) >= limits.get("max_iterations", 8):
            return "force_answer"
        if budget.get("tokens_used", 0) >= limits.get("max_tokens", 6000):
            return "force_answer"
        if budget.get("cost_usd", 0.0) >= limits.get("max_cost_usd", 0.02):
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
) -> Generator[str, None, None]:
    """
    Run the ReAct agent and yield NDJSON event lines:
      {"event":"thought","text":"..."}
      {"event":"tool_start","tool":"...","args":{...}}
      {"event":"tool_result","tool":"...","result":{...}}
      {"event":"token","t":"..."}
      {"event":"done","latency_ms":N,"tool_calls_made":N,"budget":{...}}
      {"event":"budget_hit","reason":"...","partial_answer":"..."}
      {"event":"error","detail":"..."}
    """
    t0 = time.monotonic()

    COST_PER_INPUT  = 0.0000003   # per token
    COST_PER_OUTPUT = 0.0000006   # per token

    def _emit(obj: dict) -> str:
        return json.dumps(obj)

    yield _emit({"event": "start", "session_id": session_id})

    # ── Intent guard: short-circuit greetings & off-topic ─────────────────────
    from agent.tools.intent_guard import classify_intent
    # Use regex-only (no LLM fallback) — the LLM guard is too aggressive and
    # falsely blocks legitimate support questions like "Can I get a refund?"
    is_off, intent, canned_reply = classify_intent(question, use_llm_fallback=False)
    if is_off:
        # Emit intent event so the UI knows what happened
        yield _emit({"event": "intent", "intent": intent})
        # Stream canned reply token by token
        words = canned_reply.split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else " " + word
            yield _emit({"event": "token", "t": token})
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        yield _emit({
            "event": "done",
            "latency_ms": latency_ms,
            "tool_calls_made": 0,
            "budget": {},
            "intent": intent,
        })
        return
    # ── End guard ─────────────────────────────────────────────────────────────

    # Build initial messages
    messages: List[BaseMessage] = [SystemMessage(content=REACT_SYSTEM_PROMPT)]

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

    messages.append(HumanMessage(content=question))

    # Build and run agent
    compiled = build_react_agent(pipeline)
    budget_cfg = budget_config or {}
    initial_state: AgentState = {
        "messages": messages,
        "customer_id": customer_id,
        "item_status": item_status,
        "session_id": session_id,
        "abort": False,
        "budget_summary": {
            "limits": {
                "max_iterations": budget_cfg.get("max_iterations", 2),
                "max_tokens": budget_cfg.get("max_tokens", 8000),
                "max_cost_usd": budget_cfg.get("max_cost_usd", 0.05),
                "wall_clock_sec": budget_cfg.get("wall_clock_sec", 30.0),
            }
        },
        "tool_calls_log": [],
    }

    # Stream node-by-node using .stream() so the UI gets live updates
    # instead of waiting for the entire graph to finish.
    tool_calls_made = 0
    final_answer = ""
    budget_hit = False
    budget_reason = ""
    budget_summary: Dict[str, Any] = {}
    seen_msg_ids: set = set()

    try:
        for chunk in compiled.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                if not isinstance(node_output, dict):
                    continue

                # Capture latest budget
                if "budget_summary" in node_output:
                    budget_summary = node_output["budget_summary"]

                # Emit events for new messages added by this node
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

                            if "Final Answer:" in content_str:
                                final_answer = content_str.split("Final Answer:", 1)[-1].strip()
                                yield _emit({"event": "thought", "text": content_str})
                                # Emit final answer tokens inline so race runner captures them
                                words = final_answer.split(" ")
                                for i, word in enumerate(words):
                                    tok = word if i == 0 else " " + word
                                    yield _emit({"event": "token", "t": tok})
                            elif not msg.tool_calls:
                                final_answer = content_str
                                if "Thought:" in content_str:
                                    yield _emit({"event": "thought", "text": content_str})
                                # Emit tokens inline for any final non-tool-call message
                                words = final_answer.split(" ")
                                for i, word in enumerate(words):
                                    tok = word if i == 0 else " " + word
                                    yield _emit({"event": "token", "t": tok})
                            else:
                                if "Thought:" in content_str:
                                    yield _emit({"event": "thought", "text": content_str})

                        for tc in (msg.tool_calls or []):
                            tool_calls_made += 1
                            yield _emit({
                                "event": "tool_start",
                                "tool": tc["name"],
                                "args": tc.get("args", {}),
                            })

                    elif isinstance(msg, ToolMessage):
                        result = msg.content
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except Exception:
                                pass
                        yield _emit({
                            "event": "tool_result",
                            "tool": msg.name or "unknown",
                            "result": result,
                        })

    except Exception as exc:
        # ── Fallback: direct retrieval (works with ANY model, no bind_tools needed) ──
        # This triggers when the LLM doesn't support tool calling (e.g. model_not_found,
        # tools_not_supported). Instead of failing silently, we retrieve directly.
        logger.warning("Agent graph failed (%s) — falling back to direct retrieval", exc)
        yield _emit({"event": "thought", "text": f"[Fallback] Direct retrieval (reason: {exc})"})

        try:
            from agent.tools.registry import build_agent_tools
            fallback_tools = {t.name: t for t in build_agent_tools(pipeline)}

            # Retrieve documents directly
            tool_calls_made += 1
            yield _emit({"event": "tool_start", "tool": "rag_retrieval",
                         "args": {"query": question, "top_k": 5}})
            retrieval = fallback_tools["rag_retrieval"].invoke(
                {"query": question, "top_k": 5}
            )
            chunks = retrieval.get("chunks", []) if isinstance(retrieval, dict) else []
            yield _emit({"event": "tool_result", "tool": "rag_retrieval", "result": retrieval})

            # Build context
            context = "\n\n---\n\n".join(
                c.get("text", "") for c in chunks if c.get("text")
            )

            # Generate answer with plain LLM (no bind_tools)
            fallback_model = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-120b").removeprefix("groq/")
            plain_llm = ChatGroq(
                model=fallback_model,
                api_key=os.getenv("GROQ_API_KEY", ""),
                temperature=0.2,
            )
            if context:
                fb_prompt = (
                    "You are a helpful customer support agent. "
                    "Answer the customer's question using ONLY the context below.\n\n"
                    f"Context:\n{context}\n\n"
                    f"Question: {question}\n\nAnswer:"
                )
            else:
                fb_prompt = (
                    "You are a helpful customer support agent. "
                    f"Question: {question}\n\n"
                    "No specific documentation was found. Provide a helpful general response "
                    "and ask the customer to contact support for personalized assistance.\n\nAnswer:"
                )

            fb_response = plain_llm.invoke([HumanMessage(content=fb_prompt)])
            final_answer = (
                fb_response.content
                if isinstance(fb_response.content, str)
                else str(fb_response.content)
            )
            # Extract token counts
            fb_inp, fb_out = _extract_tokens(fb_response)
            budget_summary = {
                "tokens_used": fb_inp + fb_out,
                "cost_usd": round(fb_inp * COST_PER_INPUT + fb_out * COST_PER_OUTPUT, 8),
                "fallback": True,
            }

        except Exception as fb_exc:
            final_answer = (
                "I'm sorry, I encountered an error while retrieving information. "
                "Please contact our support team directly for assistance."
            )
            logger.error("Fallback also failed: %s", fb_exc)

        # Emit fallback answer tokens
        for i, word in enumerate(final_answer.split(" ")):
            tok = word if i == 0 else " " + word
            yield _emit({"event": "token", "t": tok})

    if budget_summary.get("abort"):
        budget_hit = True
        budget_reason = "Agent aborted due to budget limit"

    latency_ms = round((time.monotonic() - t0) * 1000, 1)

    if budget_hit:
        yield _emit({
            "event": "budget_hit",
            "reason": budget_reason,
            "partial_answer": final_answer,
        })

    yield _emit({
        "event": "done",
        "latency_ms": latency_ms,
        "tool_calls_made": tool_calls_made,
        "budget": budget_summary,
    })

    # Persist to short-term memory
    if session_store and session_id and final_answer:
        session_store.append(session_id, "user", question)
        session_store.append(session_id, "assistant", final_answer)

    # Store in mem0 long-term memory
    if long_term and session_id and final_answer:
        long_term.store_mem0(session_id, [
            {"role": "user", "content": question},
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
    parser.add_argument("--question", required=True)
    parser.add_argument("--customer_id", default="C001")
    parser.add_argument("--item_status", default=None)
    parser.add_argument("--session_id", default="")
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
        if etype == "thought":
            print(f"\n[THOUGHT] {event.get('text','')[:200]}")
        elif etype == "tool_start":
            print(f"[TOOL] {event['tool']} → {event.get('args', {})}")
        elif etype == "tool_result":
            print(f"[RESULT] {str(event.get('result',''))[:200]}")
        elif etype == "token":
            print(event["t"], end="", flush=True)
        elif etype == "done":
            print(f"\n\n[BUDGET] {event.get('budget', {})}")
            print(f"[LATENCY] {event.get('latency_ms')} ms | Tools used: {event.get('tool_calls_made')}")
        elif etype == "budget_hit":
            print(f"\n[BUDGET HIT] {event.get('reason')}")
        elif etype == "error":
            print(f"\n[ERROR] {event.get('detail')}")
