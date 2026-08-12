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
import shutil
import tempfile
import logging

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag.rag_pipeline import RAGPipeline

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

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


class SourceItem(BaseModel):
    text: str
    source: str
    chunk_index: int
    score: float


class HitRate(BaseModel):
    hits: int
    total: int
    threshold: float
    rate: float


class ChatResponse(BaseModel):
    question: str
    answer: str
    scores: List[float]
    hit_rate: HitRate
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

@app.get("/health", tags=["System"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "pipeline_ready": app_state.pipeline is not None}


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
        result = pipeline.query(
            question=request.question,
            namespace=request.namespace,
            temperature=request.temperature,
            stream=False,           # REST doesn't support generator streaming
            return_sources=request.return_sources,
        )
    except Exception as exc:
        logger.error(f"/chat error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    hit_rate_raw = result.get("hit_rate", {})
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
        hit_rate=HitRate(
            hits=hit_rate_raw.get("hits", 0),
            total=hit_rate_raw.get("total", 0),
            threshold=hit_rate_raw.get("threshold", 0.5),
            rate=hit_rate_raw.get("rate", 0.0),
        ),
        sources=sources,
    )


@app.post("/index", response_model=IndexResponse, tags=["Index"])
async def index_documents(
    files: List[UploadFile] = File(...),
    namespace: str = "default",
):
    """
    Upload one or more documents and index them into Pinecone.

    Supported formats: .txt, .md, .pdf, .docx, .csv, .json, .html, .htm

    Files are temporarily saved on the server, processed by the RAG pipeline,
    then cleaned up automatically.
    """
    pipeline = get_pipeline()

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

        # Run the existing indexing logic — completely unchanged
        count = pipeline.index_documents(
            file_paths=saved_paths,
            namespace=namespace,
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
