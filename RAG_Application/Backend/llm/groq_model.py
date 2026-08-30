"""
Groq LLM Module
================
Handles interactions with the Groq LLM API for fast inference.
Provides a clean interface for generating answers given a context
and a user query, with configurable model and generation parameters.
"""

import os
import logging

from typing import List, Dict, Optional
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from groq import Groq

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Default system prompt for the RAG assistant
RAG_SYSTEM_PROMPT = """You are a helpful and knowledgeable AI assistant.
You answer user questions based strictly on the provided context.
If the answer cannot be found in the context, clearly state that you don't have 
enough information to answer. Do not make up information or use knowledge outside 
the provided context.

CRITICAL INSTRUCTIONS:
- You MUST include ALL specific numeric values, time windows, deadlines, fees, exceptions, and eligibility conditions from the provided context.
- NEVER add information, assumptions, navigation paths, or policies not present in the context.
- Be concise, accurate, and precise.
- Quote or reference relevant parts of the context when appropriate.
- If the context does not contain enough information to fully answer the question, state that clearly and honestly without guessing.
"""


class GroqModel:
    """
    Client wrapper for Groq LLM API.

    Provides methods for generating answers using the Groq inference
    API with streaming and non-streaming support.

    Attributes:
        api_key (str): Groq API key.
        model_name (str): Groq model identifier.
        client (Groq): Groq API client instance.
    """

    def __init__(self, model_name: str = None, api_key: str = None):
        """
        Initialize the Groq client.

        Args:
            model_name (str, optional): Groq model name.
                Defaults to GROQ_MODEL_NAME from .env or 'llama3-8b-8192'.
            api_key (str, optional): Groq API key.
                Defaults to GROQ_API_KEY from .env.

        Raises:
            ValueError: If GROQ_API_KEY is not found.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Please set it in your .env file."
            )

        self.model_name = model_name or os.getenv(
            "GROQ_MODEL_NAME", "llama3-8b-8192"
        )
        self.client = Groq(api_key=self.api_key)
        logger.info(f"Groq LLM initialized with model: {self.model_name}")

    def build_prompt(self, query: str, context_chunks: List[str]) -> List[Dict]:
        """
        Construct the message list for the Groq API chat completion.

        Args:
            query (str): The user's question.
            context_chunks (List[str]): Retrieved document chunks as context.

        Returns:
            List[Dict]: Formatted messages for the chat API.
        """
        context = "\n\n---\n\n".join(context_chunks)
        user_message = (
            f"Use the following context to answer the question.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {query}\n\n"
            f"ANSWER:"
        )
        return [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

    def generate(
        self,
        query: str,
        context_chunks: List[str],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate an answer using the Groq LLM given a query and context.

        Args:
            query (str): The user's question.
            context_chunks (List[str]): List of relevant text chunks as context.
            temperature (float): Sampling temperature (0.0 = deterministic).
            max_tokens (int): Maximum tokens in the generated response.
            system_prompt (str, optional): Override the default system prompt.

        Returns:
            str: The LLM-generated answer.
        """
        messages = self.build_prompt(query, context_chunks)

        # Override system prompt if provided
        if system_prompt:
            messages[0]["content"] = system_prompt

        logger.info(
            f"Sending request to Groq [{self.model_name}] | "
            f"Context chunks: {len(context_chunks)} | "
            f"Temperature: {temperature}"
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        answer = response.choices[0].message.content.strip()
        logger.info("Response received from Groq.")
        return answer

    def generate_stream(
        self,
        query: str,
        context_chunks: List[str],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ):
        """
        Stream the LLM response token-by-token for real-time output.

        Args:
            query (str): The user's question.
            context_chunks (List[str]): List of relevant text chunks as context.
            temperature (float): Sampling temperature.
            max_tokens (int): Maximum tokens in the generated response.

        Yields:
            str: Individual text chunks as they arrive from the API.
        """
        messages = self.build_prompt(query, context_chunks)
        logger.info(f"Streaming request to Groq [{self.model_name}]...")

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    def list_available_models(self) -> List[str]:
        """
        Retrieve the list of available models from Groq.

        Returns:
            List[str]: Model IDs available via the Groq API.
        """
        models = self.client.models.list()
        model_ids = [m.id for m in models.data]
        logger.info(f"Available Groq models: {model_ids}")
        return model_ids
