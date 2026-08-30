"""
LLM-as-a-Judge Evaluator (Groq-powered)
=========================================
Uses your existing Groq client to score RAG pipeline outputs across
three RAG-specific metrics:

  - faithfulness        : Is the answer grounded in the retrieved context?
  - answer_relevancy    : Does the answer directly address the question?
  - context_utilization : Does the answer make good use of the context?

Scores (0.0–1.0) are pushed to Langfuse via trace.score() so they appear
as chart columns on every trace in the Langfuse dashboard — exactly like
the managed evaluator, but powered by Groq (free-tier friendly).

Usage (standalone batch run):
    python -m eval.llm_judge

Usage (in /chat endpoint):
    from eval.llm_judge import LLMJudge
    judge = LLMJudge(groq_client=pipeline.llm.client)
    judge.score_trace(trace, question, context_chunks, answer)
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Judge model — use a larger/smarter model than the generation model
# openai/gpt-oss-120b is available on Groq and excellent for evaluation
# ---------------------------------------------------------------------------
DEFAULT_JUDGE_MODEL = "openai/gpt-oss-120b"


# ---------------------------------------------------------------------------
# Evaluation prompt templates
# ---------------------------------------------------------------------------

FAITHFULNESS_PROMPT = """\
You are a strict RAG evaluation expert assessing FAITHFULNESS.

FAITHFULNESS: The answer must contain ONLY information that is explicitly supported \
by the retrieved CONTEXT. Any claim not found in the context is unfaithful.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
{answer}

Evaluate faithfulness. Respond with valid JSON only — no explanation outside the JSON:
{{
  "score": <float 0.0 to 1.0>,
  "reason": "<one concise sentence>"
}}
Score guide: 1.0 = every claim is grounded in context. 0.0 = answer is completely hallucinated.\
"""

ANSWER_RELEVANCY_PROMPT = """\
You are a strict RAG evaluation expert assessing ANSWER RELEVANCY.

ANSWER RELEVANCY: Does the answer directly and completely address what the user asked?
A highly relevant answer stays on-topic and fully resolves the question.

QUESTION:
{question}

ANSWER:
{answer}

Evaluate answer relevancy. Respond with valid JSON only — no explanation outside the JSON:
{{
  "score": <float 0.0 to 1.0>,
  "reason": "<one concise sentence>"
}}
Score guide: 1.0 = perfectly relevant and complete. 0.0 = completely off-topic.\
"""

CONTEXT_UTILIZATION_PROMPT = """\
You are a strict RAG evaluation expert assessing CONTEXT UTILIZATION.

CONTEXT UTILIZATION: Does the answer make good use of the retrieved context to answer \
the question? A high-quality answer draws key facts from the context rather than ignoring it.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
{answer}

Evaluate context utilization. Respond with valid JSON only — no explanation outside the JSON:
{{
  "score": <float 0.0 to 1.0>,
  "reason": "<one concise sentence>"
}}
Score guide: 1.0 = answer uses the context thoroughly. 0.0 = answer ignores the context entirely.\
"""


# ---------------------------------------------------------------------------
# LLMJudge class
# ---------------------------------------------------------------------------

class LLMJudge:
    """
    Groq-powered LLM-as-a-Judge evaluator.

    Reuses the same Groq client that the RAG pipeline uses, so no
    extra API key or package is required.

    Args:
        groq_client: An initialized groq.Groq client instance.
        judge_model:  Groq model ID to use for judging.
                      Defaults to llama-3.3-70b-versatile (free-tier).
    """

    def __init__(self, groq_client, judge_model: str = DEFAULT_JUDGE_MODEL):
        self.client = groq_client
        self.judge_model = judge_model
        logger.info(f"LLMJudge initialized with model: {judge_model}")

    # ── Internal: call the judge LLM and parse JSON ──────────────────────────

    def _call_judge(self, prompt: str) -> Optional[dict]:
        """
        Send prompt to Groq and parse the JSON response.
        Returns None if the call fails or the response is not valid JSON.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.judge_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict evaluation assistant. "
                            "Always respond with valid JSON only. "
                            "Never include markdown fences or extra text."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,   # Deterministic — evaluations must be reproducible
                max_tokens=256,
            )
            raw = response.choices[0].message.content.strip()

            # Try direct load, then regex extraction
            try:
                if raw.startswith("```"):
                    raw_clean = raw.split("```")[1]
                    if raw_clean.startswith("json"):
                        raw_clean = raw_clean[4:]
                    return json.loads(raw_clean.strip())
                return json.loads(raw)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{[^{}]*"score"[^{}]*\}', raw, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                # Fallback to broader JSON regex
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                logger.warning(f"LLMJudge: could not parse JSON from: {raw[:100]}...")
                return None

        except Exception as exc:
            logger.warning(f"LLMJudge: Groq call failed — {exc}")
            return None

    # ── Individual metric scorers ────────────────────────────────────────────

    def score_faithfulness(self, question: str, context: str, answer: str) -> dict:
        """Score how grounded the answer is in the retrieved context (0–1)."""
        prompt = FAITHFULNESS_PROMPT.format(
            question=question, context=context, answer=answer
        )
        result = self._call_judge(prompt)
        return result or {"score": None, "reason": "Evaluation failed (Groq error)"}

    def score_answer_relevancy(self, question: str, answer: str) -> dict:
        """Score how well the answer addresses the user's question (0–1)."""
        prompt = ANSWER_RELEVANCY_PROMPT.format(question=question, answer=answer)
        result = self._call_judge(prompt)
        return result or {"score": None, "reason": "Evaluation failed (Groq error)"}

    def score_context_utilization(
        self, question: str, context: str, answer: str
    ) -> dict:
        """Score how well the answer utilises the retrieved context (0–1)."""
        prompt = CONTEXT_UTILIZATION_PROMPT.format(
            question=question, context=context, answer=answer
        )
        result = self._call_judge(prompt)
        return result or {"score": None, "reason": "Evaluation failed (Groq error)"}

    # ── Combined evaluation ──────────────────────────────────────────────────

    def evaluate_all(
        self, question: str, context_chunks: list[str], answer: str
    ) -> dict:
        """
        Run all three evaluations and return a combined scores dict.

        Args:
            question:       The user's original question.
            context_chunks: List of retrieved text chunks used to generate the answer.
            answer:         The LLM-generated answer.

        Returns:
            {
              "faithfulness":        {"score": float, "reason": str},
              "answer_relevancy":    {"score": float, "reason": str},
              "context_utilization": {"score": float, "reason": str},
            }
        """
        context = "\n\n---\n\n".join(context_chunks)
        return {
            "faithfulness":        self.score_faithfulness(question, context, answer),
            "answer_relevancy":    self.score_answer_relevancy(question, answer),
            "context_utilization": self.score_context_utilization(question, context, answer),
        }

    # ── Langfuse integration — push scores directly onto a trace ────────────

    def score_trace(
        self,
        trace,
        question: str,
        context_chunks: list[str],
        answer: str,
    ) -> None:
        """
        Run all three evaluations and push scores onto a Langfuse trace
        using trace.score(). Scores appear in the Langfuse dashboard
        as chart columns alongside your existing manual scores.

        Args:
            trace:          The active Langfuse trace object.
            question:       The user's original question.
            context_chunks: Retrieved text chunks passed to the LLM.
            answer:         The final LLM-generated answer.
        """
        try:
            scores = self.evaluate_all(question, context_chunks, answer)
            for metric_name, result in scores.items():
                if result.get("score") is not None:
                    trace.score(
                        name=f"llm_judge_{metric_name}",   # e.g. "llm_judge_faithfulness"
                        value=float(result["score"]),
                        comment=result.get("reason", ""),
                    )
                    logger.info(
                        f"LLMJudge scored '{metric_name}': "
                        f"{result['score']:.2f} — {result.get('reason', '')}"
                    )
        except Exception as exc:
            logger.warning(f"LLMJudge.score_trace failed: {exc}")


# ---------------------------------------------------------------------------
# Standalone batch runner — runs judge on all 25 golden Q&A pairs
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """
    Standalone batch evaluation:
      python -m eval.llm_judge

    For each of the 25 golden Q&A pairs, asks the RAG pipeline for an answer,
    then judges it with Groq and prints the scores.
    Requires the full RAG pipeline to be importable (all env vars set).
    """
    import os
    import sys
    import time
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        from rag.rag_pipeline import RAGPipeline
        from eval.create_langfuse_dataset import GOLDEN_QA_25
        from observability.langfuse_client import create_trace, flush_langfuse
    except ImportError as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)

    logger.info("Initializing RAG pipeline for batch judging...")
    pipeline = RAGPipeline()
    judge = LLMJudge(groq_client=pipeline.llm.client)

    results = []
    for qa in GOLDEN_QA_25:
        logger.info(f"\n{'─'*60}")
        logger.info(f"Processing {qa['id']}: {qa['question'][:70]}...")

        # 1. Get answer from RAG pipeline
        try:
            result = pipeline.query(
                question=qa["question"],
                namespace=qa["namespace"],
                stream=False,
                return_sources=True,
            )
            answer = result["answer"]
            context_chunks = [s["text"] for s in result.get("sources", [])]
        except Exception as exc:
            logger.warning(f"Pipeline query failed for {qa['id']}: {exc}")
            continue

        # 2. Create a Langfuse trace for this dataset run
        trace = create_trace(
            name="batch-llm-judge",
            input={"question": qa["question"], "namespace": qa["namespace"]},
            metadata={"golden_id": qa["id"], "difficulty": qa["difficulty"]},
            tags=["batch-eval", "llm-judge"],
        )
        trace.update(output={"answer": answer[:500]})

        # 3. Score with LLM judge and push to Langfuse
        judge.score_trace(
            trace=trace,
            question=qa["question"],
            context_chunks=context_chunks,
            answer=answer,
        )

        flush_langfuse()
        time.sleep(0.5)  # Be gentle with rate limits

    logger.info(f"\n{'='*60}")
    logger.info(f"Batch judging complete. Check Langfuse dashboard for scores.")
    logger.info(f"{'='*60}")
