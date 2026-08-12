"""
Pinecone Vector Database Module
================================
Handles all interactions with the Pinecone vector database, including
index creation, upserting vectors, and performing similarity searches.
"""

import os
import logging

from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PineconeDB:
    """
    Client wrapper for Pinecone vector database operations.

    Handles index lifecycle management, vector upsert operations,
    and semantic similarity queries.

    Attributes:
        api_key (str): Pinecone API key.
        index_name (str): Name of the Pinecone index.
        dimension (int): Vector dimension for the index.
        pc (Pinecone): Pinecone client instance.
        index: Active Pinecone index handle.
    """

    def __init__(self, dimension: int, index_name: str = None):
        """
        Initialize the Pinecone client and connect to (or create) the index.

        Args:
            dimension (int): Dimensionality of vectors to store.
            index_name (str, optional): Name of the Pinecone index.
                Defaults to PINECONE_INDEX_NAME from .env or 'rag-index'.

        Raises:
            ValueError: If PINECONE_API_KEY is not set.
        """
        self.api_key = os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "PINECONE_API_KEY not found. Please set it in your .env file."
            )

        self.index_name = index_name or os.getenv("PINECONE_INDEX_NAME", "rag-index")
        self.dimension = dimension
    
        # Initialize Pinecone client (v3+ API)
        self.pc = Pinecone(api_key=self.api_key)
        self.index = self._get_or_create_index()
        logger.info(f"Connected to Pinecone index: '{self.index_name}'")

    def _get_or_create_index(self):
        """
        Retrieve existing Pinecone index or create a new one.

        Returns:
            Pinecone Index: Connected index handle.
        """
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            logger.info(
                f"Index '{self.index_name}' not found. Creating new index..."
            )
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info(f"Index '{self.index_name}' created successfully.")
        else:
            logger.info(f"Index '{self.index_name}' already exists.")

        return self.pc.Index(self.index_name)

    def upsert_vectors(
        self,
        vectors: List[List[float]],
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
        namespace: str = "default",
        batch_size: int = 100,
    ) -> int:
        """
        Upsert vectors with associated text and metadata into Pinecone.

        Args:
            vectors (List[List[float]]): List of embedding vectors to store.
            texts (List[str]): Source text for each vector.
            metadata (List[Dict], optional): Additional metadata per vector.
            namespace (str): Pinecone namespace to upsert into.
            batch_size (int): Number of vectors per upsert batch.

        Returns:
            int: Total number of vectors upserted.
        """
        records = []
        for i, (vector, text) in enumerate(zip(vectors, texts)):
            record = {
                "id": f"chunk-{i}",
                "values": vector,
                "metadata": {"text": text, **(metadata[i] if metadata else {})},
            }
            records.append(record)

        # Upsert in batches to avoid request size limits
        total_upserted = 0
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            self.index.upsert(vectors=batch, namespace=namespace)
            total_upserted += len(batch)
            logger.info(
                f"Upserted batch {start // batch_size + 1}: "
                f"{total_upserted}/{len(records)} vectors"
            )

        logger.info(f"Total vectors upserted: {total_upserted}")
        return total_upserted

    def query(
        self,
        query_vector: List[float],
        top_k: int = 5,
        namespace: str = "default",
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query the Pinecone index for semantically similar vectors.

        Args:
            query_vector (List[float]): Query embedding vector.
            top_k (int): Number of top results to return.
            namespace (str): Pinecone namespace to search in.
            filter (Dict, optional): Metadata filter for the query.

        Returns:
            List[Dict]: List of matches, each with 'id', 'score', and 'metadata'.
        """
        query_params = {
            "vector": query_vector,
            "top_k": top_k,
            "include_metadata": True,
            "namespace": namespace,
        }
        if filter:
            query_params["filter"] = filter

        response = self.index.query(**query_params)
        matches = response.get("matches", [])
        logger.info(f"Query returned {len(matches)} results.")
        return matches

    def delete_index(self):
        """Delete the current Pinecone index entirely."""
        self.pc.delete_index(self.index_name)
        logger.info(f"Index '{self.index_name}' deleted.")
