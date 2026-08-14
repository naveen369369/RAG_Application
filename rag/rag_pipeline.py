"""
RAG Pipeline Module
====================
Orchestrates the full Retrieval-Augmented Generation (RAG) workflow:
  1. Document ingestion and text chunking
  2. Embedding generation via Sentence Transformers
  3. Vector storage and retrieval via Pinecone
  4. Answer generation via Groq LLM

Supported document formats:
  .txt, .md  — Plain text and Markdown
  .pdf       — PDF documents (via pypdf)
  .docx      — Microsoft Word documents (via python-docx)
  .csv       — Comma-separated values
  .json      — JSON files
  .html/.htm — Web pages (via beautifulsoup4)

This module ties all components together into a single, easy-to-use pipeline.
"""

import os
import csv
import json
import logging


from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from embeddings.embedding_model import EmbeddingModel
from vector_db.pinecone_db import PineconeDB
from llm.groq_model import GroqModel
from rag.chunking import get_chunker

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    End-to-end Retrieval-Augmented Generation Pipeline.

    Combines document ingestion, embedding, vector storage,
    retrieval, and LLM-based answer generation.

    Attributes:
        chunk_size (int): Maximum character length of each text chunk.
        chunk_overlap (int): Number of overlapping characters between chunks.
        top_k (int): Number of top documents to retrieve per query.
        embedding_model (EmbeddingModel): Sentence Transformer embedding model.
        vector_db (PineconeDB): Pinecone vector database client.
        llm (GroqModel): Groq language model client.
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        top_k: int = None,
        hit_threshold: float = None,
    ):
        """
        Initialize all RAG pipeline components.

        Args:
            chunk_size (int, optional): Max characters per chunk.
                Defaults to CHUNK_SIZE from .env or 500.
            chunk_overlap (int, optional): Overlap between chunks in characters.
                Defaults to CHUNK_OVERLAP from .env or 50.
            top_k (int, optional): Number of retrieved results per query.
                Defaults to TOP_K_RESULTS from .env or 5.
            hit_threshold (float, optional): Minimum similarity score to count
                a retrieved chunk as a "hit". Defaults to HIT_THRESHOLD from
                .env or 0.5.
        """
        self.chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", 500))
        self.chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", 50))
        self.top_k = top_k or int(os.getenv("TOP_K_RESULTS", 5))
        self.hit_threshold = hit_threshold or float(os.getenv("HIT_THRESHOLD", 0.5))

        logger.info("Initializing RAG Pipeline components...")

        # Initialize embedding model
        self.embedding_model = EmbeddingModel()

        # Initialize vector database with correct dimension
        self.vector_db = PineconeDB(
            dimension=self.embedding_model.get_dimension()
        )

        # Initialize Groq LLM
        self.llm = GroqModel()

        # Cross-encoder loaded lazily on first rerank() call
        self._cross_encoder = None

        logger.info(
            f"RAG Pipeline ready | chunk_size={self.chunk_size} | "
            f"chunk_overlap={self.chunk_overlap} | top_k={self.top_k}"
        )

    # -------------------------------------------------------------------------
    # Document Processing
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Format-specific loaders
    # -------------------------------------------------------------------------

    def _load_txt(self, path: Path) -> str:
        """Load plain text or Markdown file."""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_pdf(self, path: Path) -> str:
        """Load PDF file using pypdf."""
        try:
            import pypdf
        except ImportError:
            raise ImportError(
                "pypdf is required to load PDF files. "
                "Install it with: pip install pypdf"
            )
        text_parts = []
        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    def _load_docx(self, path: Path) -> str:
        """Load Microsoft Word (.docx) file using python-docx."""
        try:
            import docx
        except ImportError:
            raise ImportError(
                "python-docx is required to load Word files. "
                "Install it with: pip install python-docx"
            )
        doc = docx.Document(str(path))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paragraphs)

    def _load_csv(self, path: Path) -> str:
        """Load CSV file and convert rows to readable text."""
        rows = []
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_text = " | ".join(f"{k}: {v}" for k, v in row.items())
                rows.append(row_text)
        return "\n".join(rows)

    def _load_json(self, path: Path) -> str:
        """Load JSON file and convert to readable text."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _load_html(self, path: Path) -> str:
        """Load HTML file and extract visible text using BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "beautifulsoup4 is required to load HTML files. "
                "Install it with: pip install beautifulsoup4"
            )
        with open(path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        # Remove script and style tags
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    # -------------------------------------------------------------------------
    # Document router
    # -------------------------------------------------------------------------

    SUPPORTED_FORMATS = {
        ".txt": "_load_txt",
        ".md": "_load_txt",
        ".pdf": "_load_pdf",
        ".docx": "_load_docx",
        ".csv": "_load_csv",
        ".json": "_load_json",
        ".html": "_load_html",
        ".htm": "_load_html",
    }

    def load_document(self, file_path: str) -> str:
        """
        Load a document from disk. Automatically selects the correct
        loader based on the file extension.

        Supported formats:
            .txt, .md  — Plain text / Markdown
            .pdf       — PDF (requires pypdf)
            .docx      — Word document (requires python-docx)
            .csv       — CSV spreadsheet
            .json      — JSON data file
            .html/.htm — Web page (requires beautifulsoup4)

        Args:
            file_path (str): Absolute or relative path to the document.

        Returns:
            str: Full extracted text content.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is not supported.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        ext = path.suffix.lower()
        loader_method = self.SUPPORTED_FORMATS.get(ext)

        if loader_method is None:
            supported = ", ".join(self.SUPPORTED_FORMATS.keys())
            raise ValueError(
                f"Unsupported file format: '{ext}'. "
                f"Supported formats: {supported}"
            )

        content = getattr(self, loader_method)(path)
        logger.info(f"Loaded '{path.name}' ({ext}) — {len(content)} characters")
        return content

    def chunk_text(
        self,
        text: str,
        strategy: str = "fixed_overlap",
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[str]:
        """
        Split text into chunks using the specified chunking strategy.

        Args:
            text (str): Document text to split.
            strategy (str): 'fixed_overlap' or 'hybrid'.
            chunk_size (int, optional): Custom chunk size. Defaults to self.chunk_size.
            chunk_overlap (int, optional): Custom overlap. Defaults to self.chunk_overlap.

        Returns:
            List[str]: List of text chunks.
        """
        size = chunk_size if chunk_size is not None else self.chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else self.chunk_overlap

        chunker = get_chunker(strategy)
        chunks = chunker.chunk_text(text, chunk_size=size, chunk_overlap=overlap)

        logger.info(
            f"Chunked text using strategy='{strategy}' | chunk_size={size} | "
            f"chunk_overlap={overlap} -> {len(chunks)} chunks created."
        )
        return chunks

    def load_and_chunk_documents(
        self,
        file_paths: List[str],
        strategy: str = "fixed_overlap",
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> tuple[List[str], List[Dict[str, Any]]]:
        """
        Load multiple documents and return their chunks with source metadata.

        Args:
            file_paths (List[str]): List of document file paths.
            strategy (str): Chunking strategy ('fixed_overlap' or 'hybrid').
            chunk_size (int, optional): Chunk size.
            chunk_overlap (int, optional): Chunk overlap.

        Returns:
            Tuple of:
                - List[str]: All text chunks across all documents.
                - List[Dict]: Corresponding metadata for each chunk.
        """
        all_chunks = []
        all_metadata = []

        # Standardize strategy string for metadata tag
        metadata_strategy_tag = (
            "hybrid"
            if (strategy or "").lower().strip() in ("hybrid", "section_recursive")
            else "fixed_overlap"
        )

        for file_path in file_paths:
            text = self.load_document(file_path)
            chunks = self.chunk_text(
                text=text,
                strategy=strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            source_name = Path(file_path).name

            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadata.append({
                    "source": source_name,
                    "chunk_index": i,
                    "chunking_strategy": metadata_strategy_tag,
                })

        logger.info(
            f"Total chunks from {len(file_paths)} document(s) with strategy='{metadata_strategy_tag}': {len(all_chunks)}"
        )
        return all_chunks, all_metadata

    # -------------------------------------------------------------------------
    # Indexing
    # -------------------------------------------------------------------------

    def index_documents(
        self,
        file_paths: List[str],
        namespace: str = "default",
        strategy: str = "fixed_overlap",
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> int:
        """
        Full ingestion pipeline: load → chunk → embed → upsert to Pinecone.

        Args:
            file_paths (List[str]): Paths to documents to index.
            namespace (str): Pinecone namespace to store vectors in.
            strategy (str): Chunking strategy ('fixed_overlap' or 'hybrid').
            chunk_size (int, optional): Custom chunk size.
            chunk_overlap (int, optional): Custom chunk overlap.

        Returns:
            int: Number of vectors stored in Pinecone.
        """
        logger.info(
            f"Starting document indexing for {len(file_paths)} file(s) [strategy={strategy}]..."
        )

        # Step 1: Load and chunk
        chunks, metadata = self.load_and_chunk_documents(
            file_paths=file_paths,
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        if not chunks:
            logger.warning("No chunks created from input documents.")
            return 0

        # Step 2: Generate embeddings
        vectors = self.embedding_model.embed_texts(chunks)

        # Step 3: Upsert to Pinecone
        count = self.vector_db.upsert_vectors(
            vectors=vectors,
            texts=chunks,
            metadata=metadata,
            namespace=namespace,
        )

        logger.info(f"Indexing complete. {count} vectors stored.")
        return count

    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Cross-Encoder Reranking
    # -------------------------------------------------------------------------

    def _get_cross_encoder(self):
        """Lazy-load the cross-encoder model on first use."""
        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder
            logger.info("Loading cross-encoder model (first use)…")
            self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            logger.info("Cross-encoder model ready.")
        return self._cross_encoder

    def rerank(
        self,
        query: str,
        matches: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Rerank retrieved chunks with a cross-encoder and return the top_k best.
        The cross-encoder scores each (query, chunk_text) pair jointly, producing
        more accurate relevance judgements than embedding cosine similarity alone.
        """
        if not matches:
            return matches
        texts = [m["metadata"].get("text", "") for m in matches]
        pairs = [[query, t] for t in texts]
        scores = self._get_cross_encoder().predict(pairs)
        ranked = sorted(zip(scores, matches), key=lambda x: x[0], reverse=True)
        reranked = [m for _, m in ranked[:top_k]]
        logger.info(f"Reranked {len(matches)} candidates → top {len(reranked)} kept")
        return reranked

    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        namespace: str = "default",
        filter: Optional[Dict[str, Any]] = None,
        top_k_override: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant document chunks for a given query.

        Args:
            query (str): User's search query.
            namespace (str): Pinecone namespace to search.
            filter (Dict, optional): Metadata filter for retrieval.
            top_k_override (int, optional): Fetch this many candidates instead
                of self.top_k. Used to widen the candidate pool before reranking.

        Returns:
            List[Dict]: Matching document chunks with scores and metadata.
        """
        logger.info(f"Retrieving context for query: '{query}'")

        query_vector = self.embedding_model.embed_text(query)

        matches = self.vector_db.query(
            query_vector=query_vector,
            top_k=top_k_override if top_k_override is not None else self.top_k,
            namespace=namespace,
            filter=filter,
        )

        return matches

    # -------------------------------------------------------------------------
    # Generation
    # -------------------------------------------------------------------------

    def generate_answer(
        self,
        query: str,
        context_matches: List[Dict[str, Any]],
        temperature: float = 0.2,
        stream: bool = False,
    ):
        """
        Generate an answer using the Groq LLM given retrieved context.

        Args:
            query (str): User's question.
            context_matches (List[Dict]): Pinecone match objects with metadata.
            temperature (float): LLM sampling temperature.
            stream (bool): If True, yields streamed response chunks.

        Returns:
            str | Generator: Full answer string, or a generator if stream=True.
        """
        # Extract text from retrieved matches
        context_chunks = [
            match["metadata"]["text"]
            for match in context_matches
            if match.get("metadata", {}).get("text")
        ]

        if not context_chunks:
            return "I could not find relevant information to answer your question."

        if stream:
            return self.llm.generate_stream(
                query=query,
                context_chunks=context_chunks,
                temperature=temperature,
            )

        return self.llm.generate(
            query=query,
            context_chunks=context_chunks,
            temperature=temperature,
        )

    # -------------------------------------------------------------------------
    # Main Query Interface
    def get_namespaces(self) -> List[str]:
        """Retrieve list of all active namespaces in Pinecone."""
        return self.vector_db.list_namespaces()

    # -------------------------------------------------------------------------


    def query(
        self,
        question: str,
        namespace: str = "default",
        temperature: float = 0.2,
        stream: bool = False,
        return_sources: bool = False,
        use_reranker: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute the full RAG pipeline for a given question.

        Steps:
            1. Embed the question
            2. Retrieve relevant chunks from Pinecone
               (fetches 2× top_k candidates when use_reranker=True)
            3. Optionally rerank with cross-encoder
            4. Generate an answer with Groq LLM

        Args:
            question (str): The user's natural language question.
            namespace (str): Pinecone namespace to search.
            temperature (float): LLM generation temperature.
            stream (bool): If True, streams the response.
            return_sources (bool): If True, include source metadata in output.
            use_reranker (bool): If True, apply cross-encoder reranking before
                passing chunks to the LLM.

        Returns:
            Dict with keys:
                - 'question': The original question
                - 'answer': The LLM-generated answer (or generator if stream=True)
                - 'sources': List of source metadata (if return_sources=True)
                - 'scores': List of retrieval similarity scores
                - 'reranked': Whether cross-encoder reranking was applied
        """
        logger.info(f"\n{'='*60}\nQuestion: {question}\n{'='*60}")

        # Widen candidate pool when reranking so the reranker has more to work with
        candidate_top_k = self.top_k * 2 if use_reranker else None
        matches = self.retrieve(query=question, namespace=namespace, top_k_override=candidate_top_k)

        if not matches:
            logger.warning("No relevant documents found.")
            return {
                "question": question,
                "answer": "I couldn't find relevant context to answer your question.",
                "sources": [],
                "scores": [],
                "reranked": False,
            }

        # Cross-encoder reranking: re-score all candidates jointly with the query,
        # then trim back down to self.top_k for LLM context.
        if use_reranker:
            matches = self.rerank(query=question, matches=matches, top_k=self.top_k)

        # Generate answer
        answer = self.generate_answer(
            query=question,
            context_matches=matches,
            temperature=temperature,
            stream=stream,
        )

        scores = [round(m.get("score", 0), 4) for m in matches]

        result = {
            "question": question,
            "answer": answer,
            "scores": scores,
            "reranked": use_reranker,
        }

        if return_sources:
            result["sources"] = [
                {
                    "text": m["metadata"].get("text", "")[:200] + "...",
                    "source": m["metadata"].get("source", "unknown"),
                    "chunk_index": m["metadata"].get("chunk_index", -1),
                    "score": round(m.get("score", 0), 4),
                }
                for m in matches
            ]

        return result
