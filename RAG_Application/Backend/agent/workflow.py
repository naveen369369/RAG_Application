"""
Fixed LangGraph workflow (no agentic loop).
Three nodes always run in the same order regardless of input:
  route → retrieve → generate

Yields NDJSON step events for /workflow/stream.
One-command CLI: python -m agent.workflow --question "..." --customer_id C001
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, TypedDict

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

from agent.tools.registry import build_agent_tools

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    question: str
    customer_id: str
    item_status: Optional[str]
    namespace: str
    chunks: List[Dict]
    answer: str
    intent: str            # "greeting" | "off_topic" | "support"
    steps_completed: List[str]
    total_input_tokens: int
    total_output_tokens: int


def build_workflow(pipeline: "RAGPipeline"):
    """Compile the fixed workflow with intent guard → route → retrieve → generate."""
    from agent.tools.intent_guard import classify_intent

    tools_by_name = {t.name: t for t in build_agent_tools(pipeline)}
    model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile").removeprefix("groq/")

    # ── Guard node: classify intent before doing any retrieval ────────────────
    def guard_node(state: WorkflowState) -> dict:
        """Tier-1 regex check (instant). LLM fallback only for borderline cases."""
        is_off, intent, reply = classify_intent(state["question"], use_llm_fallback=False)
        if is_off:
            return {
                "intent": intent,
                "answer": reply,
                "steps_completed": state["steps_completed"] + ["guard_classify"],
            }
        return {
            "intent": "support",
            "steps_completed": state["steps_completed"] + ["guard_classify"],
        }

    def _should_proceed(state: WorkflowState) -> str:
        """Route to 'blocked' if off-topic/greeting, else continue to 'route'."""
        return "blocked" if state["intent"] in ("greeting", "off_topic") else "route"

    def guard_respond_node(state: WorkflowState) -> dict:
        """Final node for short-circuited replies — no LLM, no retrieval."""
        # answer is already set by guard_node; just mark step done
        return {"steps_completed": state["steps_completed"] + ["guard_respond"]}

    def route_node(state: WorkflowState) -> dict:
        result = tools_by_name["route_namespace"].invoke({"question": state["question"]})
        ns = result.get("namespace", "all") if isinstance(result, dict) else "all"
        return {"namespace": ns, "steps_completed": state["steps_completed"] + ["route_namespace"]}

    def retrieve_node(state: WorkflowState) -> dict:
        result = tools_by_name["rag_retrieval"].invoke({
            "query": state["question"],
            "namespace": state["namespace"],
            "top_k": 5,
        })
        chunks = result.get("chunks", []) if isinstance(result, dict) else []
        return {"chunks": chunks, "steps_completed": state["steps_completed"] + ["rag_retrieval"]}

    def generate_node(state: WorkflowState) -> dict:
        context_parts = []
        for chunk in state.get("chunks", []):
            text = chunk.get("text", "")
            if text:
                context_parts.append(text)

        context = "\n\n---\n\n".join(context_parts) if context_parts else ""
        llm = ChatGroq(
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY", ""),
            temperature=0.2,
        )

        if context:
            prompt = (
                f"You are a helpful support agent. Answer the customer's question based strictly on the context below.\n\n"
                f"Context:\n{context}\n\n"
                f"Question: {state['question']}\n\n"
                f"Answer:"
            )
        else:
            prompt = (
                f"You are a helpful support agent. No specific document context was retrieved for this question.\n"
                f"Please provide a helpful, general response letting the customer know we understand their query "
                f"and asking them to contact support directly for personalized assistance.\n\n"
                f"Question: {state['question']}\n\n"
                f"Answer:"
            )

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            answer = response.content if isinstance(response.content, str) else str(response.content)
            # Robust token extraction — try usage_metadata, fallback to Groq response_metadata
            um = getattr(response, "usage_metadata", None)
            if um:
                inp_toks = getattr(um, "input_tokens", None) or (um.get("input_tokens", 0) if hasattr(um, "get") else 0)
                out_toks = getattr(um, "output_tokens", None) or (um.get("output_tokens", 0) if hasattr(um, "get") else 0)
            else:
                inp_toks, out_toks = 0, 0
            if not (inp_toks or out_toks):
                rm = getattr(response, "response_metadata", {}) or {}
                tu = rm.get("token_usage", {}) or {}
                inp_toks = tu.get("prompt_tokens", 0)
                out_toks = tu.get("completion_tokens", 0)
        except Exception as exc:
            answer = f"I'm sorry, I encountered an error generating a response. Please contact support. (Error: {exc})"
            inp_toks, out_toks = 0, 0

        return {
            "answer": answer,
            "steps_completed": state["steps_completed"] + ["generate"],
            "total_input_tokens": state.get("total_input_tokens", 0) + int(inp_toks),
            "total_output_tokens": state.get("total_output_tokens", 0) + int(out_toks),
        }

    g = StateGraph(WorkflowState)
    g.add_node("guard",          guard_node)
    g.add_node("guard_respond",  guard_respond_node)
    g.add_node("route",          route_node)
    g.add_node("retrieve",       retrieve_node)
    g.add_node("generate",       generate_node)
    g.set_entry_point("guard")
    g.add_conditional_edges("guard", _should_proceed, {"blocked": "guard_respond", "route": "route"})
    g.add_edge("guard_respond", END)
    g.add_edge("route",     "retrieve")
    g.add_edge("retrieve",  "generate")
    g.add_edge("generate",  END)
    return g.compile()


def stream_workflow(
    pipeline: "RAGPipeline",
    question: str,
    customer_id: str = "C001",
    item_status: Optional[str] = None,
    namespace: str = "all",
) -> Generator[str, None, None]:
    """
    Run the fixed workflow and yield NDJSON step events:
      {"event":"step_start","step":"route_namespace"}
      {"event":"step_done","step":"route_namespace","result":{...}}
      {"event":"token","t":"..."}
      {"event":"done","latency_ms":N,"total_tokens":N,"cost_usd":N}
    """
    t0 = time.monotonic()

    def _emit(obj: dict) -> str:
        return json.dumps(obj)

    # Pricing for llama-3.3-70b-versatile
    COST_PER_INPUT = 0.0000003
    COST_PER_OUTPUT = 0.0000006

    compiled = build_workflow(pipeline)

    initial: WorkflowState = {
        "question": question,
        "customer_id": customer_id,
        "item_status": item_status,
        "namespace": namespace,
        "chunks": [],
        "answer": "",
        "intent": "support",
        "steps_completed": [],
        "total_input_tokens": 0,
        "total_output_tokens": 0,
    }

    # Don't emit upfront step_start — steps are conditional on intent.
    # Instead emit step_done per completed step after invocation.

    try:
        final_state = compiled.invoke(initial)
    except Exception as exc:
        yield _emit({"event": "error", "detail": str(exc)})
        return

    # Emit step_done for each completed step
    for step_name in final_state.get("steps_completed", []):
        result_val: Any = {}
        if step_name == "guard_classify":
            result_val = {"intent": final_state.get("intent", "support")}
        elif step_name == "guard_respond":
            answer = final_state.get("answer", "")
            result_val = {"answer_preview": answer[:80]}
        elif step_name == "route_namespace":
            result_val = {"namespace": final_state.get("namespace", "all")}
        elif step_name == "rag_retrieval":
            result_val = {"count": len(final_state.get("chunks", []))}
        elif step_name == "generate":
            answer = final_state.get("answer", "")
            result_val = {"answer_preview": answer[:100]}

        yield _emit({"event": "step_done", "step": step_name, "result": result_val})

    # Stream final answer token by token
    answer = final_state.get("answer", "No answer generated.")
    words = answer.split(" ")
    for i, word in enumerate(words):
        token = word if i == 0 else " " + word
        yield _emit({"event": "token", "t": token})

    input_toks = final_state.get("total_input_tokens", 0)
    output_toks = final_state.get("total_output_tokens", 0)
    total_tokens = input_toks + output_toks
    cost_usd = round(input_toks * COST_PER_INPUT + output_toks * COST_PER_OUTPUT, 8)
    latency_ms = round((time.monotonic() - t0) * 1000, 1)

    yield _emit({
        "event": "done",
        "latency_ms": latency_ms,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "steps_completed": final_state.get("steps_completed", []),
    })


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv()

    from rag.rag_pipeline import RAGPipeline

    parser = argparse.ArgumentParser(description="Run the fixed workflow from CLI")
    parser.add_argument("--question", required=True)
    parser.add_argument("--customer_id", default="C001")
    parser.add_argument("--item_status", default=None)
    args = parser.parse_args()

    pipeline = RAGPipeline()
    print(f"\n{'='*60}")
    print(f"WORKFLOW | Question: {args.question}")
    print(f"{'='*60}")

    for line in stream_workflow(
        pipeline=pipeline,
        question=args.question,
        customer_id=args.customer_id,
        item_status=args.item_status,
    ):
        event = json.loads(line)
        etype = event.get("event", "")
        if etype == "step_start":
            print(f"[→] Starting: {event['step']}")
        elif etype == "step_done":
            print(f"[✓] Done: {event['step']} → {str(event.get('result',''))[:100]}")
        elif etype == "token":
            print(event["t"], end="", flush=True)
        elif etype == "done":
            print(f"\n\n[METRICS] {event.get('latency_ms')}ms | {event.get('total_tokens')} tokens | ${event.get('cost_usd'):.6f}")
        elif etype == "error":
            print(f"\n[ERROR] {event.get('detail')}")
