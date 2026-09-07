from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from langchain_core.tools import tool

if TYPE_CHECKING:
    from rag.rag_pipeline import RAGPipeline


def make_eval_trigger_tool(pipeline: "RAGPipeline"):
    @tool
    def run_evaluation(
        eval_type: str,
        question: Optional[str] = None,
        answer: Optional[str] = None,
        context: Optional[List[str]] = None,
        top_k: int = 3,
    ) -> dict:
        """
        Run an evaluation on demand.
        eval_type='hit_rate': run golden Hit Rate @ K evaluation (no extra args needed).
        eval_type='llm_judge': score a specific answer (provide question, answer, context).
        Returns evaluation scores and metrics.
        """
        eval_type = eval_type.strip().lower()

        if eval_type == "hit_rate":
            try:
                from eval.golden_eval import evaluate_hit_rate
                result = evaluate_hit_rate(pipeline, top_k=top_k)
                return result
            except Exception as exc:
                return {"error": f"Hit rate evaluation failed: {exc}"}

        if eval_type == "llm_judge":
            if not question or not answer:
                return {"error": "llm_judge requires 'question' and 'answer' fields"}
            try:
                from eval.llm_judge import LLMJudge
                judge = LLMJudge(groq_client=pipeline.llm.client)
                scores = {}

                def _score(metric: str, prompt: str) -> float:
                    resp = pipeline.llm.client.chat.completions.create(
                        model=pipeline.llm.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                        max_tokens=128,
                    )
                    import json, re
                    text = resp.choices[0].message.content or ""
                    m = re.search(r'"score"\s*:\s*([0-9.]+)', text)
                    return float(m.group(1)) if m else 0.0

                ctx_str = "\n\n".join(context or [])
                scores["faithfulness"] = _score(
                    "faithfulness",
                    f"Rate faithfulness (0-1) of this answer to the context.\nContext:{ctx_str}\nAnswer:{answer}\nRespond JSON: {{\"score\": 0.0}}",
                )
                scores["answer_relevancy"] = _score(
                    "relevancy",
                    f"Rate relevancy (0-1) of this answer to the question.\nQuestion:{question}\nAnswer:{answer}\nRespond JSON: {{\"score\": 0.0}}",
                )
                return scores
            except Exception as exc:
                return {"error": f"LLM judge failed: {exc}"}

        return {"error": f"Unknown eval_type: {eval_type!r}. Use 'hit_rate' or 'llm_judge'."}

    return run_evaluation
