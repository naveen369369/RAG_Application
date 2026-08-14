"""
RAG Application — FastAPI Backend
==================================
Exposes the existing RAG pipeline as REST endpoints.

Endpoints:
    GET  /health          — Health check
    POST /chat            — Ask a question (non-streaming)
    POST /index           — Upload & index one or more documents
"""

import os
import re
import time
import shutil
import tempfile
import logging
from collections import deque

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    # Cleanup (nothing needed for this pipeline)
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

# Allow Streamlit frontend (localhost:8501) to call this API
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
    """Return the shared pipeline instance, raising 503 if not ready."""
    if app_state.pipeline is None:
        raise HTTPException(status_code=503, detail="RAG Pipeline is not initialized.")
    return app_state.pipeline


# Supported file extensions (mirrors rag_pipeline.SUPPORTED_FORMATS)
SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".docx", ".csv", ".json", ".html", ".htm"
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/namespaces", tags=["System"])
def get_namespaces():
    """Retrieve list of active Pinecone namespaces."""
    pipeline = get_pipeline()
    try:
        namespaces = pipeline.get_namespaces()
        return {"namespaces": namespaces}
    except Exception as exc:
        logger.error(f"/namespaces error: {exc}")
        return {"namespaces": ["default"]}


@app.get("/health", tags=["System"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "pipeline_ready": app_state.pipeline is not None}


@app.get("/metrics", tags=["System"])
def get_latency_metrics():
    """Return P50, P95, P99 latency percentiles calculated from stored query samples."""
    samples = list(_latency_store)
    count = len(samples)
    if count == 0:
        return {"sample_count": 0, "p50_ms": None, "p95_ms": None, "p99_ms": None,
                "avg_ms": None, "min_ms": None, "max_ms": None}
    arr = np.array(samples)
    return {
        "sample_count": count,
        "p50_ms": round(float(np.percentile(arr, 50)), 1),
        "p95_ms": round(float(np.percentile(arr, 95)), 1),
        "p99_ms": round(float(np.percentile(arr, 99)), 1),
        "avg_ms": round(float(arr.mean()), 1),
        "min_ms": round(float(arr.min()), 1),
        "max_ms": round(float(arr.max()), 1),
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest):
    """
    Ask a question using the RAG pipeline.

    The pipeline embeds the question, retrieves relevant chunks from Pinecone,
    and generates an answer using the Groq LLM.
    """
    pipeline = get_pipeline()
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        _t0 = time.perf_counter()
        result = pipeline.query(
            question=request.question,
            namespace=request.namespace,
            temperature=request.temperature,
            stream=False,           # REST doesn't support generator streaming
            return_sources=request.return_sources,
            use_reranker=request.use_reranker,
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
        latency_ms=latency_ms,
        sources=sources,
    )


@app.post("/index", response_model=IndexResponse, tags=["Index"])
async def index_documents(
    files: List[UploadFile] = File(...),
    namespace: str = "default",
    chunking_strategy: str = "fixed_overlap",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
):
    """
    Upload one or more documents and index them into Pinecone.

    Supported formats: .txt, .md, .pdf, .docx, .csv, .json, .html, .htm

    Files are temporarily saved on the server, processed by the RAG pipeline,
    then cleaned up automatically.
    """
    pipeline = get_pipeline()

    # Auto-generate namespace from filename if namespace is 'auto' or empty
    if not namespace or namespace.strip().lower() == "auto":
        first_fn = files[0].filename if files else "doc"
        clean_name = os.path.splitext(first_fn)[0]
        namespace = re.sub(r"[^a-zA-Z0-9_-]", "_", clean_name).lower().strip("_") or "default"
        logger.info(f"Auto-generated namespace from filename: '{namespace}'")


    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    # Validate extensions before doing any disk I/O
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

    # Save uploaded files to a temporary directory
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
            logger.warning(f"Saved upload: {dest}")

        # Run indexing logic with selected chunking strategy
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
        # Always clean up temp files
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
    Saves the mapping to eval/golden_chunk_map.json for use by /golden/evaluate.
    """
    pipeline = get_pipeline()
    try:
        result = discover_chunk_ids(pipeline)
        return result
    except Exception as exc:
        logger.error(f"/golden/discover error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/golden/evaluate", tags=["Evaluation"])
def golden_evaluate(top_k: int = 3, use_reranker: bool = False):
    """
    Run Hit Rate @ {top_k} evaluation over all 12 golden questions.
    For each question, embeds the question and checks whether the correct
    chunk_id (discovered via /golden/discover) appears in the top-{top_k} results.
    When use_reranker=True, fetches 2×top_k candidates then reranks before checking.
    Returns overall hit rate and per-question breakdown.
    """
    pipeline = get_pipeline()
    try:
        result = evaluate_hit_rate(pipeline, top_k=top_k, use_reranker=use_reranker)
        return result
    except Exception as exc:
        logger.error(f"/golden/evaluate error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
