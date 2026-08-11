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

logging.disable(logging.CRITICAL)
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from embeddings.embedding_model import EmbeddingModel
from vector_db.pinecone_db import PineconeDB
from llm.groq_model import GroqModel

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

    def chunk_text(self, text: str) -> List[str]:
        """
        Split a long text into overlapping chunks for embedding.

        Uses a character-based sliding window approach to ensure
        that no context is lost at chunk boundaries.

        Args:
            text (str): The full document text to split.

        Returns:
            List[str]: List of text chunks.
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            # Slide window forward, minus overlap
            start += self.chunk_size - self.chunk_overlap

        logger.info(f"Text split into {len(chunks)} chunks.")
        return chunks

    def load_and_chunk_documents(
        self, file_paths: List[str]
    ) -> tuple[List[str], List[Dict[str, Any]]]:
        """
        Load multiple documents and return their chunks with source metadata.

        Args:
            file_paths (List[str]): List of document file paths.

        Returns:
            Tuple of:
                - List[str]: All text chunks across all documents.
                - List[Dict]: Corresponding metadata for each chunk
                  (source filename, chunk index).
        """
        all_chunks = []
        all_metadata = []

        for file_path in file_paths:
            text = self.load_document(file_path)
            chunks = self.chunk_text(text)
            source_name = Path(file_path).name

            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadata.append({"source": source_name, "chunk_index": i})

        logger.info(
            f"Total chunks from {len(file_paths)} document(s): {len(all_chunks)}"
        )
        return all_chunks, all_metadata

    # -------------------------------------------------------------------------
    # Indexing
    # -------------------------------------------------------------------------

    def index_documents(
        self,
        file_paths: List[str],
        namespace: str = "default",
    ) -> int:
        """
        Full ingestion pipeline: load → chunk → embed → upsert to Pinecone.

        Args:
            file_paths (List[str]): Paths to documents to index.
            namespace (str): Pinecone namespace to store vectors in.

        Returns:
            int: Number of vectors stored in Pinecone.
        """
        logger.info(f"Starting document indexing for {len(file_paths)} file(s)...")

        # Step 1: Load and chunk
        chunks, metadata = self.load_and_chunk_documents(file_paths)

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

    def retrieve(
        self,
        query: str,
        namespace: str = "default",
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant document chunks for a given query.

        Args:
            query (str): User's search query.
            namespace (str): Pinecone namespace to search.
            filter (Dict, optional): Metadata filter for retrieval.

        Returns:
            List[Dict]: Top-k matching document chunks with scores and metadata.
        """
        logger.info(f"Retrieving context for query: '{query}'")

        # Embed the query
        query_vector = self.embedding_model.embed_text(query)

        # Search Pinecone
        matches = self.vector_db.query(
            query_vector=query_vector,
            top_k=self.top_k,
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
    # -------------------------------------------------------------------------

    def query(
        self,
        question: str,
        namespace: str = "default",
        temperature: float = 0.2,
        stream: bool = False,
        return_sources: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute the full RAG pipeline for a given question.

        Steps:
            1. Embed the question
            2. Retrieve relevant chunks from Pinecone
            3. Generate an answer with Groq LLM

        Args:
            question (str): The user's natural language question.
            namespace (str): Pinecone namespace to search.
            temperature (float): LLM generation temperature.
            stream (bool): If True, streams the response.
            return_sources (bool): If True, include source metadata in output.

        Returns:
            Dict with keys:
                - 'question': The original question
                - 'answer': The LLM-generated answer (or generator if stream=True)
                - 'sources': List of source metadata (if return_sources=True)
                - 'scores': List of retrieval similarity scores
        """
        logger.info(f"\n{'='*60}\nQuestion: {question}\n{'='*60}")

        # Retrieve context
        matches = self.retrieve(query=question, namespace=namespace)

        if not matches:
            logger.warning("No relevant documents found.")
            return {
                "question": question,
                "answer": "I couldn't find relevant context to answer your question.",
                "sources": [],
                "scores": [],
                "hit_rate": {
                    "hits": 0,
                    "total": 0,
                    "threshold": self.hit_threshold,
                    "rate": 0.0,
                },
            }

        # Generate answer
        answer = self.generate_answer(
            query=question,
            context_matches=matches,
            temperature=temperature,
            stream=stream,
        )

        # Compute hit rate — a chunk is a "hit" if its score >= hit_threshold
        scores = [round(m.get("score", 0), 4) for m in matches]
        hits = sum(1 for s in scores if s >= self.hit_threshold)
        hit_rate_info = {
            "hits": hits,
            "total": len(scores),
            "threshold": self.hit_threshold,
            "rate": round(hits / len(scores), 4) if scores else 0.0,
        }

        # Build result
        result = {
            "question": question,
            "answer": answer,
            "scores": scores,
            "hit_rate": hit_rate_info,
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

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Return statistics about the Pinecone index.

        Returns:
            Dict: Vector count, namespace info, and dimension details.
        """
        return self.vector_db.get_index_stats()
