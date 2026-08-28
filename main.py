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
import re
import time
import json
import shutil
import tempfile
import logging
from collections import deque
from contextlib import asynccontextmanager
from typing import Generator, List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rag.rag_pipeline import RAGPipeline
from eval.golden_eval import discover_chunk_ids, evaluate_hit_rate
from observability.langfuse_client import create_trace, flush_langfuse

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

app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the RAG pipeline once at startup and hold it for the app's lifetime."""
    logger.warning("Initializing RAG Pipeline...")
    try:
        app_state.pipeline = RAGPipeline()
        logger.warning("RAG Pipeline initialized successfully.")
    except Exception as exc:
        logger.error(f"Failed to initialize RAG Pipeline: {exc}")
        raise
    yield
    logger.warning("Shutting down RAG Pipeline.")


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
    trace.score(name="latency_ms", value=latency_ms)
    trace.score(name="sources_retrieved", value=float(len(retrieval_scores)))
    trace.score(name="sources_hit", value=1.0 if retrieval_scores else 0.0)
    if retrieval_scores:
        trace.score(name="avg_retrieval_score", value=round(sum(retrieval_scores) / len(retrieval_scores), 4))
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

        # ── Greeting bypass ───────────────────────────────────────────────────
        greeting_reply = pipeline._is_greeting(request.question)
        if greeting_reply:
            words = greeting_reply.split(" ")
            for i, word in enumerate(words):
                yield json.dumps({"t": word + (" " if i < len(words) - 1 else "")}) + "\n"
                time.sleep(0.02)
            latency_ms = round((time.perf_counter() - _t0) * 1000, 1)
            trace.update(output={"answer": greeting_reply, "type": "greeting"})
            trace.score(name="latency_ms", value=latency_ms)
            trace.score(name="sources_hit", value=0.0, comment="Greeting bypass — no retrieval")
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

        generation_span.end(output={"answer": full_answer[:500]})

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

        flush_langfuse()

        yield json.dumps({
            "done": True,
            "latency_ms": latency_ms,
            "reranked": request.use_reranker,
            "hyde": request.use_hyde,
            "sources": sources,
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
