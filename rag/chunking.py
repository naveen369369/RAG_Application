"""
Modular Chunking Module
========================
Provides text chunking strategies for the RAG pipeline:
1. FixedOverlapChunker — Character-based sliding window.
2. HybridChunker — Section-based + recursive hierarchical splitting with overlap.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import List

logger = logging.getLogger(__name__)


class BaseChunker(ABC):
    """Abstract base class for all chunking strategies."""

    @abstractmethod
    def chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split input text into a list of chunks based on strategy rules."""
        pass


class FixedOverlapChunker(BaseChunker):
    """
    Fixed-size character sliding-window chunking strategy with overlap.
    Preserves exact original RAG pipeline sliding-window logic.
    """

    def chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        step = max(1, chunk_size - chunk_overlap)

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += step

        return chunks


class HybridChunker(BaseChunker):
    """
    Hybrid chunking strategy:
    1. Section-based splitting: Detect headings/sections in markdown/text.
    2. Recursive splitting: If a section exceeds `chunk_size`, split by hierarchy
       (paragraphs '\\n\\n' -> lines '\\n' -> sentences '. ' -> words ' ').
    3. Maintains overlap between sub-chunks and maximum `chunk_size`.
    """

    # Matches Markdown headings (# Heading), underline headers, or label headers (Section 1:, Chapter A:)
    HEADING_PATTERN = re.compile(
        r"(?m)^(?:"
        r"#{1,6}\s+.*|"                          # Markdown headers: # Header
        r"[^\n]+\n[=\-]{3,}|"                     # Markdown underline headers
        r"(?:SECTION|CHAPTER|PART|\b[A-Z0-9\s_-]{3,}:)\s+.*" # Label headers
        r")$",
        re.IGNORECASE,
    )

    DELIMITERS = ["\n\n", "\n", ". ", " "]

    def _split_into_sections(self, text: str) -> List[str]:
        """Split text into sections using heading patterns."""
        matches = list(self.HEADING_PATTERN.finditer(text))
        if not matches:
            # Fallback: No headings detected — treat entire text as 1 section
            return [text.strip()] if text.strip() else []

        sections = []
        last_idx = 0

        for i, match in enumerate(matches):
            start = match.start()
            if start > last_idx:
                prefix_text = text[last_idx:start].strip()
                if prefix_text:
                    sections.append(prefix_text)

            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sec_text = text[start:end].strip()
            if sec_text:
                sections.append(sec_text)
            last_idx = end

        return sections

    def _recursive_split(
        self, text: str, chunk_size: int, chunk_overlap: int, delim_idx: int = 0
    ) -> List[str]:
        """Recursively split text using hierarchical delimiters while respecting size & overlap."""
        text = text.strip()
        if not text:
            return []

        if len(text) <= chunk_size:
            return [text]

        if delim_idx >= len(self.DELIMITERS):
            # Fallback to fixed sliding window if no higher delimiters split it
            fixed_chunker = FixedOverlapChunker()
            return fixed_chunker.chunk_text(text, chunk_size, chunk_overlap)

        delimiter = self.DELIMITERS[delim_idx]
        raw_parts = text.split(delimiter)

        if len(raw_parts) == 1:
            # Delimiter didn't split the text, try next delimiter level
            return self._recursive_split(text, chunk_size, chunk_overlap, delim_idx + 1)

        # Merge short parts (like headings or short lines) with the following part if possible
        parts = []
        for p in raw_parts:
            p_str = p if delim_idx == 0 else p + (delimiter if delimiter != " " else " ")
            if not p_str.strip():
                continue
            parts.append(p_str)

        chunks = []
        current_pieces = []
        current_len = 0

        for part_str in parts:
            part_len = len(part_str)

            # If a single part is larger than chunk_size, recursively split it
            if part_len > chunk_size:
                if current_pieces:
                    assembled = "".join(current_pieces).strip()
                    if assembled:
                        chunks.append(assembled)
                    current_pieces = []
                    current_len = 0

                sub_chunks = self._recursive_split(part_str.strip(), chunk_size, chunk_overlap, delim_idx + 1)
                chunks.extend(sub_chunks)
                continue

            if current_len + part_len > chunk_size:
                assembled = "".join(current_pieces).strip()
                if assembled:
                    chunks.append(assembled)

                # Generate overlap from tail of current_pieces
                overlap_pieces = []
                overlap_len = 0
                for p in reversed(current_pieces):
                    if overlap_len + len(p) <= chunk_overlap:
                        overlap_pieces.insert(0, p)
                        overlap_len += len(p)
                    else:
                        break

                current_pieces = overlap_pieces + [part_str]
                current_len = sum(len(p) for p in current_pieces)
            else:
                current_pieces.append(part_str)
                current_len += part_len

        if current_pieces:
            final_assembled = "".join(current_pieces).strip()
            if final_assembled:
                chunks.append(final_assembled)

        return chunks

    def _semantic_split(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> List[str]:
        """
        Semantic Sentence Similarity Chunking:
        1. Splits section into individual sentences.
        2. Calculates sentence embeddings & cosine similarity distance between consecutive sentences.
        3. Identifies semantic topic shift breakpoints where similarity drops.
        4. Bundles sentences into semantic topic chunks up to chunk_size with overlap.
        5. Falls back to _recursive_split if any sub-piece cannot be split semantically.
        """
        text = text.strip()
        if not text or len(text) <= chunk_size:
            return [text] if text else []

        # Extract sentences preserving punctuation
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if len(sentences) <= 2:
            return self._recursive_split(text, chunk_size, chunk_overlap)

        try:
            from embeddings.embedding_model import EmbeddingModel
            import numpy as np

            if not hasattr(self, "_embed_model"):
                self._embed_model = EmbeddingModel()

            # Encode all sentences
            embeddings = np.array(self._embed_model.embed_texts(sentences))

            # Compute cosine similarities between consecutive sentences
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1e-10
            norm_embeddings = embeddings / norms

            similarities = np.sum(norm_embeddings[:-1] * norm_embeddings[1:], axis=1)
            distances = 1.0 - similarities

            # Determine breakpoint threshold (mean + 0.5 * std)
            if len(distances) > 0:
                threshold = float(np.mean(distances) + 0.5 * np.std(distances))
            else:
                threshold = 0.5

            # Identify sentence indices where topic shifts occur
            breakpoints = set()
            for i, dist in enumerate(distances):
                if dist >= threshold:
                    breakpoints.add(i + 1)

        except Exception as e:
            logger.warning(f"Semantic embedding split unavailable/failed ({e}). Falling back to recursive split.")
            return self._recursive_split(text, chunk_size, chunk_overlap)

        # Assemble sentences into semantic chunks
        chunks = []
        curr_sentences = []
        curr_len = 0

        for idx, sentence in enumerate(sentences):
            sent_len = len(sentence) + 1

            if (idx in breakpoints or curr_len + sent_len > chunk_size) and curr_sentences:
                assembled = " ".join(curr_sentences).strip()
                if len(assembled) > chunk_size:
                    sub_chunks = self._recursive_split(assembled, chunk_size, chunk_overlap)
                    chunks.extend(sub_chunks)
                elif assembled:
                    chunks.append(assembled)

                overlap_sents = []
                overlap_len = 0
                for s in reversed(curr_sentences):
                    if overlap_len + len(s) + 1 <= chunk_overlap:
                        overlap_sents.insert(0, s)
                        overlap_len += len(s) + 1
                    else:
                        break

                curr_sentences = overlap_sents + [sentence]
                curr_len = sum(len(s) + 1 for s in curr_sentences)
            else:
                curr_sentences.append(sentence)
                curr_len += sent_len

        if curr_sentences:
            final_assembled = " ".join(curr_sentences).strip()
            if len(final_assembled) > chunk_size:
                sub_chunks = self._recursive_split(final_assembled, chunk_size, chunk_overlap)
                chunks.extend(sub_chunks)
            elif final_assembled:
                chunks.append(final_assembled)

        return chunks if chunks else [text]

    def chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        if not text or not text.strip():
            return []

        final_chunks = []
        sections = self._split_into_sections(text)
        for sec in sections:
            if len(sec) <= chunk_size:
                final_chunks.append(sec)
            else:
                sub_chunks = self._semantic_split(sec, chunk_size, chunk_overlap)
                final_chunks.extend(sub_chunks)

        return final_chunks


def get_chunker(strategy: str) -> BaseChunker:
    """
    Factory function to get the appropriate chunking strategy instance.

    Args:
        strategy (str): 'fixed_overlap' (or 'fixed') or 'hybrid'.

    Returns:
        BaseChunker: Instantiated chunker object.
    """
    normalized = (strategy or "").lower().strip()
    if normalized in ("hybrid", "section_recursive"):
        return HybridChunker()
    return FixedOverlapChunker()

