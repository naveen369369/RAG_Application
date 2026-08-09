"""
Embedding Model Module
======================
Handles text embedding generation using Sentence Transformers.
Converts text chunks into dense vector representations for storage
and semantic similarity search in the vector database.
"""

import os
import logging

logging.disable(logging.CRITICAL)
from typing import List, Union
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Wraps the SentenceTransformer model to generate text embeddings.

    Attributes:
        model_name (str): Name of the Sentence Transformer model.
        model (SentenceTransformer): Loaded embedding model instance.
        dimension (int): Dimensionality of the output embeddings.
    """

    def __init__(self, model_name: str = None):
        """
        Initialize the embedding model.

        Args:
            model_name (str, optional): Model name from HuggingFace hub.
                Defaults to EMBEDDING_MODEL_NAME from .env or 'all-MiniLM-L6-v2'.
        """
        self.model_name = model_name or os.getenv(
            "EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"
        )
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(
            f"Embedding model loaded. Dimension: {self.dimension}"
        )

    def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding vector for a single text string.

        Args:
            text (str): Input text to embed.

        Returns:
            List[float]: Embedding vector as a list of floats.
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embedding vectors for a list of text strings.

        Args:
            texts (List[str]): List of input texts to embed.
            batch_size (int): Number of texts to process per batch.

        Returns:
            List[List[float]]: List of embedding vectors.
        """
        logger.info(f"Generating embeddings for {len(texts)} texts...")
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 10,
        )
        logger.info("Embeddings generated successfully.")
        return embeddings.tolist()

    def get_dimension(self) -> int:
        """
        Return the embedding vector dimension.

        Returns:
            int: Number of dimensions in the embedding space.
        """
        return self.dimension
