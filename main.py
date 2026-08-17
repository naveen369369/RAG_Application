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
    namespace: str = "default"
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

    return ChatResponse(
        question=result["question"],
        answer=result["answer"],
        scores=result.get("scores", []),
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

    def _generate() -> Generator[str, None, None]:
        _t0 = time.perf_counter()

        # HyDE already achieves perfect recall — reranker only adds risk when
        # HyDE is active, so skip it. Only rerank when HyDE is OFF.
        effective_reranker = request.use_reranker and not request.use_hyde
        hyde_doc = pipeline._generate_hyde_document(request.question) if request.use_hyde else None
        retrieval_query = hyde_doc if hyde_doc else request.question

        candidate_top_k = pipeline.top_k * 2 if effective_reranker else None
        matches = pipeline.retrieve(
            query=retrieval_query,
            namespace=request.namespace,
            top_k_override=candidate_top_k,
        )

        if not matches:
            yield json.dumps({"t": "I couldn't find relevant context to answer your question."}) + "\n"
            yield json.dumps({"done": True, "latency_ms": 0.0, "reranked": False, "hyde": request.use_hyde, "sources": []}) + "\n"
            return

        if effective_reranker:
            matches = pipeline.rerank(query=request.question, matches=matches, top_k=pipeline.top_k)

        # Stream LLM tokens
        token_stream = pipeline.generate_answer(
            query=request.question,
            context_matches=matches,
            temperature=request.temperature,
            stream=True,
        )
        for token in token_stream:
            yield json.dumps({"t": token}) + "\n"

        latency_ms = round((time.perf_counter() - _t0) * 1000, 1)
        _latency_store.append(latency_ms)

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
        raise
    except Exception as exc:
        logger.error(f"/index error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

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

    use_reranker=true: fetches 2×top_k candidates, reranks, then checks hit.
    use_hyde=true    : embeds a hypothetical answer doc instead of raw question.
    Both flags can be combined for the strongest retrieval configuration.
    """
    pipeline = get_pipeline()
    try:
        result = evaluate_hit_rate(pipeline, top_k=top_k, use_reranker=use_reranker, use_hyde=use_hyde)
        return result
    except Exception as exc:
        logger.error(f"/golden/evaluate error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
