"""
RAG Application — FastAPI Backend
==================================
Exposes the existing RAG pipeline as REST endpoints.

Endpoints:
    GET  /health          — Health check
    POST /chat            — Ask a question (non-streaming)
    POST /chat/stream     — Ask a question with real token streaming (NDJSON)
    POST /index           — Upload & index one or more documents
    POST /golden/discover — Map golden answer chunks in Pinecone
    GET  /golden/evaluate — Run Hit Rate @ K evaluation

Observability:
    Every /chat and /chat/stream request creates a Langfuse trace with nested
    spans for HyDE generation, retrieval, reranking, and LLM generation.
    Python logs are forwarded to Langfuse as trace events when enabled.
"""

import os

# Must be set before numpy/torch/scipy are imported to prevent OpenBLAS memory conflicts on Windows
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import re
import time
import json
import shutil
import tempfile
import logging
from collections import deque
from contextlib import asynccontextmanager
from typing import Generator, List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rag.rag_pipeline import RAGPipeline
from eval.golden_eval import discover_chunk_ids, evaluate_hit_rate
from eval.llm_judge import LLMJudge
from observability.langfuse_client import create_trace, flush_langfuse, is_enabled
from agent.schemas import AgentRequest, WorkflowRequest
from agent.memory.short_term import SessionStore
from agent.memory.long_term import LongTermMemory
from database import init_db, get_db
import database.crud as db_crud
import database.schemas as db_schemas

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Latency store — keeps the last 1000 query latencies (milliseconds)
# ---------------------------------------------------------------------------

_latency_store: deque = deque(maxlen=1000)


# ---------------------------------------------------------------------------
# Application state — shared RAGPipeline instance
# ---------------------------------------------------------------------------

class AppState:
    pipeline: Optional[RAGPipeline] = None
    session_store: Optional[SessionStore] = None
    long_term_memory: Optional[LongTermMemory] = None

app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the RAG pipeline, agent memory, and database once at startup."""
    logger.warning("Initializing RAG Pipeline and Database...")
    try:
        app_state.pipeline = RAGPipeline()
        app_state.session_store = SessionStore()
        app_state.long_term_memory = LongTermMemory(app_state.pipeline)
        init_db()
        logger.warning("RAG Pipeline, agent memory, and database initialized successfully.")
    except Exception as exc:
        logger.error(f"Failed to initialize: {exc}")
        raise
    yield
    logger.warning("Shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RAG Application API",
    description="Retrieval-Augmented Generation API powered by Pinecone + Groq",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str
    return_sources: bool = False
    namespace: str = "all"
    temperature: float = 0.2
    use_reranker: bool = False
    use_hyde: bool = False


class SourceItem(BaseModel):
    text: str
    source: str
    chunk_index: int
    score: float


class ChatResponse(BaseModel):
    question: str
    answer: str
    scores: List[float]
    reranked: bool = False
    hyde: bool = False
    latency_ms: float = 0.0
    sources: Optional[List[SourceItem]] = None


class IndexResponse(BaseModel):
    message: str
    files_indexed: List[str]
    vectors_stored: int


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_pipeline() -> RAGPipeline:
    if app_state.pipeline is None:
        raise HTTPException(status_code=503, detail="RAG Pipeline is not initialized.")
    return app_state.pipeline


SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".docx", ".csv", ".json", ".html", ".htm"
}


def _percentile(sorted_data: list, p: float) -> float:
    """Linear-interpolation percentile over a pre-sorted list."""
    idx = (len(sorted_data) - 1) * p / 100
    lo = int(idx)
    hi = min(lo + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo)


def _retrieval_mode(use_hyde: bool, use_reranker: bool) -> str:
    if use_hyde and use_reranker:
        return "HyDE + Reranker"
    if use_hyde:
        return "HyDE"
    if use_reranker:
        return "Reranker"
    return "Semantic"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/namespaces", tags=["System"])
def get_namespaces():
    pipeline = get_pipeline()
    try:
        namespaces = pipeline.get_namespaces()
        return {"namespaces": namespaces}
    except Exception as exc:
        logger.error(f"/namespaces error: {exc}")
        return {"namespaces": ["default"]}


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "pipeline_ready": app_state.pipeline is not None}


@app.get("/metrics", tags=["System"])
def get_latency_metrics():
    """Return P50, P95, P99 latency percentiles from stored query samples."""
    samples = list(_latency_store)
    count = len(samples)
    if count == 0:
        return {"sample_count": 0, "p50_ms": None, "p95_ms": None, "p99_ms": None,
                "avg_ms": None, "min_ms": None, "max_ms": None}
    s = sorted(samples)
    return {
        "sample_count": count,
        "p50_ms": round(_percentile(s, 50), 1),
        "p95_ms": round(_percentile(s, 95), 1),
        "p99_ms": round(_percentile(s, 99), 1),
        "avg_ms": round(sum(samples) / count, 1),
        "min_ms": round(min(samples), 1),
        "max_ms": round(max(samples), 1),
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest):
    """Ask a question using the RAG pipeline (non-streaming)."""
    pipeline = get_pipeline()
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    # --- Langfuse: start trace ---
    trace = create_trace(
        name="rag-chat",
        input={"question": request.question},
        metadata={
            "namespace": request.namespace,
            "use_hyde": request.use_hyde,
            "use_reranker": request.use_reranker,
            "temperature": request.temperature,
            "mode": _retrieval_mode(request.use_hyde, request.use_reranker),
        },
        tags=["chat", "non-streaming"],
    )

    try:
        _t0 = time.perf_counter()

        result = pipeline.query(
            question=request.question,
            namespace=request.namespace,
            temperature=request.temperature,
            stream=False,
            return_sources=request.return_sources,
            use_reranker=request.use_reranker,
            use_hyde=request.use_hyde,
        )
        latency_ms = round((time.perf_counter() - _t0) * 1000, 1)
        _latency_store.append(latency_ms)

    except Exception as exc:
        logger.error(f"/chat error: {exc}")
        trace.update(output={"error": str(exc)})
        flush_langfuse()
        raise HTTPException(status_code=500, detail=str(exc))

    sources = None
    if request.return_sources and result.get("sources"):
        sources = [
            SourceItem(
                text=s.get("text", ""),
                source=s.get("source", "unknown"),
                chunk_index=s.get("chunk_index", -1),
                score=s.get("score", 0.0),
            )
            for s in result["sources"]
        ]

    retrieval_scores = result.get("scores", [])
    trace.update(output={"answer": result["answer"][:500], "latency_ms": latency_ms})

    # Generation observation — enables token count + cost in Langfuse
    gen_usage = getattr(pipeline.llm, "last_usage", None)
    gen_obs = trace.generation(
        name="llm-generation",
        model=pipeline.llm.model_name,
        input={"question": request.question, "context_chunks": len(retrieval_scores)},
        usage=gen_usage,
    )
    gen_obs.end(output={"answer": result["answer"][:500]})

    trace.score(name="latency_ms", value=latency_ms)
    trace.score(name="sources_retrieved", value=float(len(retrieval_scores)))
    trace.score(name="sources_hit", value=1.0 if retrieval_scores else 0.0)
    if retrieval_scores:
        trace.score(name="avg_retrieval_score", value=round(sum(retrieval_scores) / len(retrieval_scores), 4))

    # --- LLM-as-a-Judge: Groq-powered free evaluation (faithfulness, relevancy, context utilization)
    if is_enabled() and result.get("sources"):
        try:
            context_chunks = [s["text"] for s in result["sources"]]
            judge = LLMJudge(groq_client=pipeline.llm.client)
            judge.score_trace(
                trace=trace,
                question=request.question,
                context_chunks=context_chunks,
                answer=result["answer"],
            )
        except Exception as _judge_exc:
            logger.warning(f"LLM judge scoring skipped: {_judge_exc}")

    flush_langfuse()

    return ChatResponse(
        question=result["question"],
        answer=result["answer"],
        scores=retrieval_scores,
        reranked=result.get("reranked", False),
        hyde=result.get("hyde", False),
        latency_ms=latency_ms,
        sources=sources,
    )


@app.post("/chat/stream", tags=["Chat"])
def chat_stream(request: ChatRequest):
    """
    Ask a question and receive the answer as a real token stream (NDJSON).

    Each line is a JSON object:
      {"t": "<token>"}          — one LLM token as it arrives
      {"done": true, "latency_ms": ..., "reranked": ..., "hyde": ..., "sources": [...]}
                                — final metadata line after streaming completes
    """
    pipeline = get_pipeline()
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    # Create trace BEFORE the generator (it's captured by closure)
    trace = create_trace(
        name="rag-chat-stream",
        input={"question": request.question},
        metadata={
            "namespace": request.namespace,
            "use_hyde": request.use_hyde,
            "use_reranker": request.use_reranker,
            "temperature": request.temperature,
            "mode": _retrieval_mode(request.use_hyde, request.use_reranker),
        },
        tags=["chat", "streaming"],
    )

    def _generate() -> Generator[str, None, None]:
        _t0 = time.perf_counter()
        try:
            # ── Intent guard (Greetings, Math, Off-Topic, Injections) ─────────────
            from agent.tools.intent_guard import classify_intent
            is_off, intent, guard_reply = classify_intent(request.question, use_llm_fallback=False)
            if not is_off:
                legacy_greeting = pipeline._is_greeting(request.question)
                if legacy_greeting:
                    is_off = True
                    intent = "greeting"
                    guard_reply = legacy_greeting

            if is_off:
                words = guard_reply.split(" ")
                for i, word in enumerate(words):
                    yield json.dumps({"t": word + (" " if i < len(words) - 1 else "")}) + "\n"
                    time.sleep(0.01)
                latency_ms = round((time.perf_counter() - _t0) * 1000, 1)
                trace.update(output={"answer": guard_reply, "type": intent})
                trace.score(name="latency_ms", value=latency_ms)
                trace.score(name="sources_hit", value=0.0, comment=f"{intent} bypass — no retrieval")
                flush_langfuse()
                yield json.dumps({
                    "done": True,
                    "latency_ms": latency_ms,
                    "reranked": False,
                    "hyde": False,
                    "sources": [],
                }) + "\n"
                return

            # ── HyDE generation ───────────────────────────────────────────────────
            hyde_doc = None
            if request.use_hyde:
                hyde_span = trace.generation(
                    name="hyde-generation",
                    model=pipeline.llm.model_name,
                    input={"query": request.question},
                    metadata={"purpose": "Generate hypothetical document for embedding"},
                )
                hyde_doc = pipeline._generate_hyde_document(request.question)
                hyde_span.end(output={"hyde_doc": hyde_doc[:300]})

            retrieval_query = hyde_doc if hyde_doc else request.question
            effective_reranker = request.use_reranker and not request.use_hyde

            # ── Retrieval ─────────────────────────────────────────────────────────
            candidate_top_k = pipeline.top_k * 2 if effective_reranker else None
            retrieval_span = trace.span(
                name="retrieval",
                input={
                    "query": retrieval_query[:300],
                    "namespace": request.namespace,
                    "top_k": candidate_top_k or pipeline.top_k,
                    "score_threshold": pipeline.hit_threshold,
                },
            )
            matches = pipeline.retrieve(
                query=retrieval_query,
                namespace=request.namespace,
                top_k_override=candidate_top_k,
                score_threshold=pipeline.hit_threshold,
            )
            retrieval_span.end(output={
                "num_matches": len(matches),
                "scores": [round(m.get("score", 0), 4) for m in matches[:10]],
                "sources": [m["metadata"].get("source", "?") for m in matches[:5]],
            })

            if not matches:
                no_ctx_msg = "I couldn't find relevant context in the indexed documents to answer your question."
                yield json.dumps({"t": no_ctx_msg}) + "\n"
                latency_ms = round((time.perf_counter() - _t0) * 1000, 1)
                trace.update(output={"answer": no_ctx_msg, "type": "no_context"})
                trace.score(name="latency_ms", value=latency_ms)
                trace.score(name="sources_hit", value=0.0, comment="No chunks passed threshold")
                flush_langfuse()
                yield json.dumps({"done": True, "latency_ms": latency_ms, "reranked": False, "hyde": request.use_hyde, "sources": []}) + "\n"
                return

            # ── Reranking ─────────────────────────────────────────────────────────
            if effective_reranker:
                rerank_span = trace.span(
                    name="reranking",
                    input={
                        "num_candidates": len(matches),
                        "top_k": pipeline.top_k,
                        "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                    },
                )
                matches = pipeline.rerank(query=request.question, matches=matches, top_k=pipeline.top_k)
                rerank_span.end(output={
                    "num_kept": len(matches),
                    "scores": [round(m.get("score", 0), 4) for m in matches],
                })

            # ── LLM streaming generation ──────────────────────────────────────────
            context_chunks = [
                m["metadata"]["text"] for m in matches if m.get("metadata", {}).get("text")
            ]
            generation_span = trace.generation(
                name="llm-generation",
                model=pipeline.llm.model_name,
                input={
                    "question": request.question,
                    "context_chunks_count": len(context_chunks),
                    "temperature": request.temperature,
                },
            )

            token_stream = pipeline.generate_answer(
                query=request.question,
                context_matches=matches,
                temperature=request.temperature,
                stream=True,
            )

            full_answer = ""
            for token in token_stream:
                full_answer += token
                yield json.dumps({"t": token}) + "\n"

            stream_usage = getattr(pipeline.llm, "last_stream_usage", None)
            generation_span.end(output={"answer": full_answer[:500]}, usage=stream_usage)

            latency_ms = round((time.perf_counter() - _t0) * 1000, 1)
            _latency_store.append(latency_ms)

            # ── Sources ───────────────────────────────────────────────────────────
            sources = []
            if request.return_sources:
                sources = [
                    {
                        "text": m["metadata"].get("text", "")[:200] + "...",
                        "source": m["metadata"].get("source", "unknown"),
                        "chunk_index": m["metadata"].get("chunk_index", -1),
                        "score": round(m.get("score", 0), 4),
                    }
                    for m in matches
                ]

            # ── Langfuse: finalize trace with scores ──────────────────────────────
            retrieval_scores = [round(m.get("score", 0), 4) for m in matches]
            trace.update(output={
                "answer": full_answer[:500],
                "latency_ms": latency_ms,
                "sources_count": len(matches),
                "mode": _retrieval_mode(request.use_hyde, request.use_reranker),
            })
            trace.score(name="latency_ms", value=latency_ms, comment="End-to-end streaming latency in milliseconds")
            trace.score(name="sources_retrieved", value=float(len(matches)), comment="Number of chunks retrieved after threshold")
            trace.score(name="sources_hit", value=1.0, comment="Context was found and answer was generated")
            if retrieval_scores:
                trace.score(name="avg_retrieval_score", value=round(sum(retrieval_scores) / len(retrieval_scores), 4), comment="Average cosine similarity of retrieved chunks")
            if request.use_hyde:
                trace.score(name="hyde_used", value=1.0)
            if effective_reranker:
                trace.score(name="reranker_used", value=1.0)

            # ── LLM-as-a-Judge: Groq-powered evaluation for live stream chat ──────
            if is_enabled() and context_chunks and full_answer:
                try:
                    judge = LLMJudge(groq_client=pipeline.llm.client)
                    judge.score_trace(
                        trace=trace,
                        question=request.question,
                        context_chunks=context_chunks,
                        answer=full_answer,
                    )
                except Exception as _judge_exc:
                    logger.warning(f"LLM judge streaming scoring skipped: {_judge_exc}")

            flush_langfuse()

            yield json.dumps({
                "done": True,
                "latency_ms": latency_ms,
                "reranked": request.use_reranker,
                "hyde": request.use_hyde,
                "sources": sources,
            }) + "\n"
        except Exception as exc:
            logger.error(f"Error in chat_stream: {exc}", exc_info=True)
            yield json.dumps({
                "t": f"I apologize, but I encountered an issue processing your query: {str(exc)}. Please try again."
            }) + "\n"
            yield json.dumps({
                "done": True,
                "latency_ms": 0,
                "reranked": False,
                "hyde": False,
                "sources": [],
            }) + "\n"

    return StreamingResponse(_generate(), media_type="application/x-ndjson")


@app.post("/index", response_model=IndexResponse, tags=["Index"])
async def index_documents(
    files: List[UploadFile] = File(...),
    namespace: str = "default",
    chunking_strategy: str = "fixed_overlap",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
):
    """Upload one or more documents and index them into Pinecone."""
    pipeline = get_pipeline()

    if not namespace or namespace.strip().lower() == "auto":
        first_fn = files[0].filename if files else "doc"
        clean_name = os.path.splitext(first_fn)[0]
        namespace = re.sub(r"[^a-zA-Z0-9_-]", "_", clean_name).lower().strip("_") or "default"
        logger.info(f"Auto-generated namespace from filename: '{namespace}'")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"Unsupported file type '{ext}' for '{f.filename}'. "
                    f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
                ),
            )

    # Langfuse trace for indexing
    trace = create_trace(
        name="document-indexing",
        input={
            "files": [f.filename for f in files],
            "namespace": namespace,
            "strategy": chunking_strategy,
        },
        tags=["indexing"],
    )

    tmp_dir = tempfile.mkdtemp(prefix="rag_upload_")
    saved_paths: List[str] = []
    indexed_names: List[str] = []

    try:
        for upload in files:
            dest = os.path.join(tmp_dir, upload.filename)
            with open(dest, "wb") as out:
                shutil.copyfileobj(upload.file, out)
            saved_paths.append(dest)
            indexed_names.append(upload.filename)

        count = pipeline.index_documents(
            file_paths=saved_paths,
            namespace=namespace,
            strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    except HTTPException:
        trace.update(output={"error": "HTTPException"})
        flush_langfuse()
        raise
    except Exception as exc:
        logger.error(f"/index error: {exc}")
        trace.update(output={"error": str(exc)})
        flush_langfuse()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    trace.update(output={"vectors_stored": count, "files_indexed": indexed_names})
    trace.score(name="vectors_stored", value=float(count))
    flush_langfuse()

    return IndexResponse(
        message=f"Successfully indexed {len(indexed_names)} file(s).",
        files_indexed=indexed_names,
        vectors_stored=count,
    )


# ---------------------------------------------------------------------------
# Golden Evaluation Endpoints
# ---------------------------------------------------------------------------

@app.post("/golden/discover", tags=["Evaluation"])
def golden_discover():
    """
    Discover correct chunk IDs for all 12 golden questions.
    Embeds each golden answer and finds the best-matching chunk in Pinecone.
    """
    pipeline = get_pipeline()
    try:
        result = discover_chunk_ids(pipeline)
        return result
    except Exception as exc:
        logger.error(f"/golden/discover error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/golden/evaluate", tags=["Evaluation"])
def golden_evaluate(top_k: int = 3, use_reranker: bool = False, use_hyde: bool = False):
    """
    Run Hit Rate @ {top_k} evaluation over all 12 golden questions.
    Sends results to Langfuse as a scored trace.
    """
    pipeline = get_pipeline()

    trace = create_trace(
        name="golden-evaluation",
        input={"top_k": top_k, "use_reranker": use_reranker, "use_hyde": use_hyde},
        tags=["evaluation", "golden"],
        metadata={"mode": _retrieval_mode(use_hyde, use_reranker)},
    )

    try:
        result = evaluate_hit_rate(pipeline, top_k=top_k, use_reranker=use_reranker, use_hyde=use_hyde)
    except Exception as exc:
        logger.error(f"/golden/evaluate error: {exc}")
        trace.update(output={"error": str(exc)})
        flush_langfuse()
        raise HTTPException(status_code=500, detail=str(exc))

    # Score the evaluation run in Langfuse
    trace.update(output={
        "hit_rate_pct": result.get("rate_pct"),
        "hits": result.get("hits"),
        "total": result.get("total"),
        "mode": _retrieval_mode(use_hyde, use_reranker),
    })
    trace.score(name="hit_rate_pct", value=float(result.get("rate_pct", 0)), comment=f"Golden Hit Rate @ {top_k}")
    trace.score(name="hits", value=float(result.get("hits", 0)), comment="Number of questions with correct chunk in top-k")
    flush_langfuse()

    return result


# ---------------------------------------------------------------------------
# Agent Endpoints
# ---------------------------------------------------------------------------

@app.post("/agent/stream", tags=["Agent"])
def agent_stream(request: AgentRequest):
    """
    Run the ReAct agent and stream NDJSON events.

    Event types:
      {"event":"start","session_id":"..."}
      {"event":"classified","complexity":"simple|complex","namespace":"...","rewritten_query":"..."}
      {"event":"thought","text":"..."}
      {"event":"tool_start","tool":"...","args":{...}}
      {"event":"tool_result","tool":"...","result":{...}}
      {"event":"token","t":"..."}
      {"event":"done","latency_ms":N,"tool_calls_made":N,"budget":{...},"complexity":"..."}
      {"event":"budget_hit","reason":"...","partial_answer":"..."}
      {"event":"error","detail":"..."}
    """
    pipeline = get_pipeline()
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    from agent.react_agent import stream_agent
    import uuid
    trace_id = str(uuid.uuid4())

    def _generate():
        for line in stream_agent(
            pipeline=pipeline,
            question=request.question,
            customer_id=request.customer_id,
            item_status=request.item_status,
            session_id=request.session_id,
            temperature=request.temperature,
            budget_config=request.budget_config,
            session_store=app_state.session_store,
            long_term=app_state.long_term_memory,
            langfuse_trace_id=trace_id,
        ):
            yield line + "\n"

    return StreamingResponse(_generate(), media_type="application/x-ndjson")


@app.post("/workflow/stream", tags=["Workflow"])
def workflow_stream(request: WorkflowRequest):
    """
    Run the fixed 5-step workflow and stream NDJSON step events.

    Event types:
      {"event":"step_start","step":"route_namespace"}
      {"event":"step_done","step":"route_namespace","result":{...}}
      {"event":"token","t":"..."}
      {"event":"done","latency_ms":N,"total_tokens":N,"cost_usd":N}
    """
    pipeline = get_pipeline()
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    from agent.workflow import stream_workflow

    def _generate():
        for line in stream_workflow(
            pipeline=pipeline,
            question=request.question,
            customer_id=request.customer_id,
            item_status=request.item_status,
            namespace=request.namespace,
        ):
            yield line + "\n"

    return StreamingResponse(_generate(), media_type="application/x-ndjson")


@app.post("/race", tags=["Race"])
def run_race_endpoint():
    """
    Run the 10-ticket Agent vs Workflow race.
    Streams NDJSON progress events as each ticket completes.
    Final event: {"event":"race_complete","summary":{...},"verdict":"..."}
    """
    pipeline = get_pipeline()

    from agent.race import run_race
    import queue
    import threading

    event_queue: queue.Queue = queue.Queue()

    def _callback(evt):
        event_queue.put(evt)

    def _run():
        try:
            run_race(pipeline, stream_callback=_callback)
        finally:
            event_queue.put(None)  # sentinel

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    def _generate():
        while True:
            evt = event_queue.get()
            if evt is None:
                break
            yield json.dumps(evt) + "\n"

    return StreamingResponse(_generate(), media_type="application/x-ndjson")


# ---------------------------------------------------------------------------
# Trajectory Evaluation endpoint
# ---------------------------------------------------------------------------

@app.get("/agent/trajectory-eval", tags=["Agent Eval"])
def run_trajectory_eval():
    """
    Run the 10-ticket trajectory evaluation (deterministic mock data, no LLM calls).

    Returns full evaluation report:
      - Per-case trajectory & outcome pass/fail
      - Failure mode counts (before / after mitigation)
      - Mean, P50, P99 cost per task
      - Outcome-vs-trajectory gap
      - Right-answer / wrong-path trace
      - Regression table
    """
    from eval.trajectory_eval import run_eval
    return run_eval()


class LiveEvalRequest(BaseModel):
    question: str
    customer_id: str = "C001"
    ticket_id: Optional[str] = None
    item_status: Optional[str] = None


@app.post("/agent/evaluate-live", tags=["Agent Eval"])
def evaluate_live_endpoint(req: LiveEvalRequest):
    """
    Run real-time trajectory evaluation for any live chat question or support ticket.
    Executes the ReAct Agent against the database & RAG pipeline and grades:
      - DB tool selection (ticket_lookup, order_lookup, customer_lookup)
      - Argument validity against database
      - Step efficiency & latency
      - Answer groundedness
    """
    pipeline = get_pipeline()
    from eval.live_evaluator import evaluate_live_query
    return evaluate_live_query(
        pipeline=pipeline,
        question=req.question,
        customer_id=req.customer_id,
        ticket_id=req.ticket_id,
        item_status=req.item_status,
    )


@app.post("/agent/evaluate-live-all", tags=["Agent Eval"])
def evaluate_live_all_endpoint():
    """
    Run ALL 10 ticket cases through the REAL ReAct Agent and SQL database.

    Unlike /agent/trajectory-eval (deterministic mock data), this endpoint:
      - Executes each of the 10 DB-grounded questions against the live Groq LLM
      - Validates tool arguments against the real SQL Server / SQLite DB
      - Reports actual tool usage, argument correctness, and pass/fail for each case

    Returns aggregate pass rates + per-case trajectory results.
    """
    pipeline = get_pipeline()
    from eval.trajectory_eval import run_live_eval_all
    return run_live_eval_all(pipeline=pipeline)


# ---------------------------------------------------------------------------
# Security Tests endpoint
# ---------------------------------------------------------------------------

@app.get("/agent/security-eval", tags=["Agent Eval"])
def run_security_eval():
    """
    Run the agent security test suite (deterministic, no LLM calls).

    Returns:
      - 5 security test results (before / after defenses)
      - Indirect injection deep-dive (S02)
      - Tool sandboxing results
      - Output guardrail validation
      - OWASP LLM Top 10 mapping table
    """
    from eval.security_tests import run_security_tests
    return run_security_tests()


# ---------------------------------------------------------------------------
# Support CRM Endpoints (SQL Server / DB Backend)
# ---------------------------------------------------------------------------

@app.get("/api/customers", response_model=List[db_schemas.CustomerResponse], tags=["CRM Customers"])
def list_customers(db=Depends(get_db)):
    """List all customers with active order and ticket counts."""
    customers = db_crud.get_customers(db)
    return [c.to_dict() for c in customers]


@app.post("/api/customers", response_model=db_schemas.CustomerResponse, tags=["CRM Customers"])
def create_customer(customer: db_schemas.CustomerCreate, db=Depends(get_db)):
    """Register a new customer profile."""
    existing = db_crud.get_customer(db, customer.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Customer '{customer.id}' already exists.")
    c = db_crud.create_customer(db, customer)
    return c.to_dict()


@app.get("/api/orders", response_model=List[db_schemas.OrderResponse], tags=["CRM Orders"])
def list_orders(customer_id: Optional[str] = None, db=Depends(get_db)):
    """List customer orders, optionally filtered by customer_id."""
    if customer_id in (None, "", "undefined", "null", "all"):
        customer_id = None
    orders = db_crud.get_orders(db, customer_id=customer_id)
    return [o.to_dict() for o in orders]


@app.post("/api/orders", response_model=db_schemas.OrderResponse, tags=["CRM Orders"])
def create_order(order: db_schemas.OrderCreate, db=Depends(get_db)):
    """Create a new customer order with item conditions."""
    existing = db_crud.get_order(db, order.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Order '{order.id}' already exists.")
    o = db_crud.create_order(db, order)
    return o.to_dict()


@app.get("/api/orders/{order_id}", response_model=db_schemas.OrderResponse, tags=["CRM Orders"])
def get_order_detail(order_id: str, db=Depends(get_db)):
    """Fetch order details, carrier tracking, and line items."""
    o = db_crud.get_order(db, order_id.strip().upper())
    if not o:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")
    return o.to_dict()


@app.get("/api/tickets", response_model=List[db_schemas.TicketResponse], tags=["CRM Tickets"])
def list_tickets(customer_id: Optional[str] = None, status: Optional[str] = None, db=Depends(get_db)):
    """List support tickets, optionally filtered by customer or status."""
    if customer_id in (None, "", "undefined", "null", "all"):
        customer_id = None
    if status in (None, "", "undefined", "null", "all"):
        status = None
    tickets = db_crud.get_tickets(db, customer_id=customer_id, status=status)
    return [t.to_dict() for t in tickets]


@app.post("/api/tickets", response_model=db_schemas.TicketResponse, tags=["CRM Tickets"])
def create_ticket(ticket: db_schemas.TicketCreate, db=Depends(get_db)):
    """Submit a new customer support ticket."""
    t = db_crud.create_ticket(db, ticket)
    return t.to_dict()


@app.get("/api/tickets/{ticket_id}", response_model=db_schemas.TicketResponse, tags=["CRM Tickets"])
def get_ticket_detail(ticket_id: str, db=Depends(get_db)):
    """Get support ticket details by ID."""
    t = db_crud.get_ticket(db, ticket_id.strip().upper())
    if not t:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return t.to_dict()


@app.patch("/api/tickets/{ticket_id}", response_model=db_schemas.TicketResponse, tags=["CRM Tickets"])
def update_ticket_status(ticket_id: str, updates: db_schemas.TicketUpdate, db=Depends(get_db)):
    """Update support ticket status, priority, or resolution notes."""
    t = db_crud.update_ticket(db, ticket_id.strip().upper(), updates)
    if not t:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return t.to_dict()


# ---------------------------------------------------------------------------
# MCP Endpoints — Server 2 (Ticket History) & Protocol Inspection
# ---------------------------------------------------------------------------

@app.get("/api/mcp/servers", tags=["MCP Server"])
async def get_mcp_servers():
    """
    Returns all registered MCP servers with their transport details, live connection
    status, tool counts, and tool categories for UI differentiation.

    Server 1: CRM Agent Server  — 9 local tools (runs in-process, always online)
    Server 2: TicketHistoryServer — 2 remote tools (separate process on port 8100)
    """
    import importlib.util
    cfg_path = os.path.join(os.path.dirname(__file__), "mcp", "mcp_config.py")
    spec = importlib.util.spec_from_file_location("mcp_config", cfg_path)
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)

    servers = cfg.get_enabled_servers()
    server_url = os.environ.get("MCP_SERVER2_URL", "http://127.0.0.1:8100/mcp")
    api_key = os.environ.get("MCP_API_KEY", "mcp-secret-dev-token-2026")

    # ── Server 2: probe live connection via FastMCP Client ─────────────────
    server2_online = False
    server2_discovered_tools = []
    server2_error = None

    try:
        from fastmcp import Client
        async with Client(server_url, auth=api_key) as client:
            tools = await client.list_tools()
            server2_discovered_tools = [
                {"name": t.name, "description": t.description} for t in tools
            ]
            server2_online = True
    except Exception as e:
        server2_error = str(e)

    # ── Build enriched server list for the UI ──────────────────────────────
    enriched = []
    for s in servers:
        entry = dict(s)
        # Remove token from response for security
        if "auth" in entry and "token" in entry["auth"]:
            entry["auth"] = {**entry["auth"], "token": "***hidden***"}

        if s["server_id"] == "crm-agent-server-v1":
            entry["status"] = "online"   # always online (in-process)
            entry["status_detail"] = "Running inside FastAPI process (no separate port)"
            entry["tool_count"] = len(s["tools"])
            entry["discovered_tools"] = [{"name": t} for t in s["tools"]]
            entry["error"] = None
        elif s["server_id"] == "ticket-history-v2":
            entry["status"] = "online" if server2_online else "offline"
            entry["status_detail"] = (
                f"Running on {server_url}" if server2_online
                else f"Offline — {server2_error}"
            )
            entry["tool_count"] = len(server2_discovered_tools) if server2_discovered_tools else len(s["tools"])
            entry["discovered_tools"] = server2_discovered_tools or [{"name": t} for t in s["tools"]]
            entry["error"] = server2_error

        enriched.append(entry)

    total_tools = sum(e["tool_count"] for e in enriched)

    return {
        "total_servers": len(enriched),
        "total_tools": total_tools,
        "servers": enriched,
        # Summary for backward compat
        "tool_count_server1": 9,
        "tool_count_server2": len(server2_discovered_tools),
        "tool_count_total": total_tools,
    }


@app.get("/api/mcp/history/{ticket_id}", tags=["MCP Server"])
async def get_mcp_ticket_history(ticket_id: str):
    """
    Queries MCP Server 2 for ticket details and the complete chronological
    escalation audit trail. Handles recoverable errors gracefully.
    """
    from fastmcp import Client
    server_url = os.environ.get("MCP_SERVER2_URL", "http://127.0.0.1:8100/mcp")
    api_key = os.environ.get("MCP_API_KEY", "mcp-secret-dev-token-2026")

    tid = ticket_id.strip().upper()

    try:
        async with Client(server_url, auth=api_key) as client:
            # Query get_ticket
            t_res = await client.call_tool("get_ticket", {"ticket_id": tid})
            ticket_data = json.loads(t_res.content[0].text) if t_res.content else {}

            # Query get_escalation_history
            h_res = await client.call_tool("get_escalation_history", {"ticket_id": tid})
            history_data = json.loads(h_res.content[0].text) if h_res.content else {}

            return {
                "ticket_id": tid,
                "ticket": ticket_data,
                "history": history_data,
                "is_recoverable_error": not ticket_data.get("found", True),
                "server_url": server_url,
                "transport": "HTTP/SSE",
            }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with MCP Server 2: {exc}")


@app.get("/api/mcp/wire", tags=["MCP Server"])
def get_mcp_wire_logs():
    """
    Returns the real JSON-RPC 2.0 wire exchange (initialize -> tools/list -> tools/call)
    and tool discovery counts for the UI inspector.
    """
    backend_dir = os.path.dirname(__file__)
    wire_file = os.path.join(backend_dir, "wire.json")
    counts_file = os.path.join(backend_dir, "tool_counts.txt")

    wire_data = {}
    if os.path.exists(wire_file):
        try:
            with open(wire_file, "r", encoding="utf-8") as f:
                wire_data = json.load(f)
        except Exception as e:
            wire_data = {"error": str(e)}

    counts_text = ""
    if os.path.exists(counts_file):
        try:
            with open(counts_file, "r", encoding="utf-8") as f:
                counts_text = f.read()
        except Exception as e:
            counts_text = str(e)

    return {
        "wire": wire_data,
        "tool_counts": counts_text,
    }


@app.get("/api/mcp/artifacts", tags=["MCP Server"])
def get_mcp_artifacts():
    """
    Returns the content of all Week-9 MCP deliverable files for UI display:
    - agent_diff.txt  : proves 0 lines changed in react_agent.py
    - config_diff.txt : shows what was added to mcp_config.py
    - error_before_after.md : BEFORE vs AFTER recoverable error transcript
    - risk_note.md    : 5-line supply-chain risk assessment
    - tool_counts.txt : tool count before/after with names
    """
    backend_dir = os.path.dirname(__file__)
    artifact_files = {
        "agent_diff": "agent_diff.txt",
        "config_diff": "config_diff.txt",
        "error_before_after": "error_before_after.md",
        "risk_note": "risk_note.md",
        "tool_counts": "tool_counts.txt",
    }
    result = {}
    for key, filename in artifact_files.items():
        path = os.path.join(backend_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                result[key] = f.read()
        except Exception as e:
            result[key] = f"[Error reading {filename}: {e}]"
    return result
