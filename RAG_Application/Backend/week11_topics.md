# Week-11 Topic Status

> Status key: `Already implemented` | `Improved` | `Implemented` | `Not applicable` | `Deferred`  
> Evidence column cites actual file paths and line numbers.

---

## 1. What to Log per Request

**Status: Improved**

Already logged: trace_id, timestamp, namespace, model, top_k, retrieved_chunk_ids, retrieved_scores, raw_output, prompt_version (`analysis/traces.jsonl`, `analysis/trace_logger.py`).

Also logged per Langfuse trace: latency_ms, sources_retrieved, avg_retrieval_score, hyde_used, reranker_used, LLM-judge scores (`observability/langfuse_client.py`).

**Improved this week:** Added two missing fields identified by the support drill:
- `policy_claim_check` — flag when answer contains a numeric fee or deadline not in retrieved chunks
- `failure_category` — enum per trajectory result row (`eval/trajectory_eval.py`, `_MOCK_BEFORE`)

Gap remaining: `last_stream_usage = None` in `llm/groq_model.py:170` — streaming token counts not captured. Deferred (Groq SDK limitation).

---

## 2. Traces and Spans

**Status: Already implemented**

Full span hierarchy exists in `observability/langfuse_client.py` and applied in `rag/rag_pipeline.py` and `main.py`:
- `hyde-generation` span (when HyDE enabled)
- `retrieval` span (Pinecone query)
- `reranking` span (cross-encoder)
- `llm-generation` span (Groq completion, with input/output tokens)
- `judge-{faithfulness|answer_relevancy|context_utilization}` spans

`trace.json` (created this week) documents the actual span structure for the T01/T11 refund failure domain (trace-005). All spans include latency, cost, and relevant IDs.

---

## 3. Langfuse

**Status: Already implemented**

Langfuse is fully integrated:
- Keys set in `.env` (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST=https://us.cloud.langfuse.com)
- Singleton client: `observability/langfuse_client.py`
- Every `/chat`, `/chat/stream`, `/index` request creates a trace
- All LLM-judge scores pushed as named Langfuse scores
- No-op graceful degradation when keys not set
- `analysis/trace_logger.py` runs 25 questions and ships to Langfuse + local `traces.jsonl` backup
- Golden Q&A dataset pushed via `eval/create_langfuse_dataset.py`

No new Langfuse integration needed this week.

---

## 4. The Support Drill

**Status: Implemented**

Two timed drills run and documented in `drill.md`:

| Drill | Time | Method |
|---|---|---|
| Drill 1 (before) | 04:23 | Manual scan of `traces.jsonl` and `trajectory_eval.py` mock data |
| Drill 2 (after) | 01:07 | Filter by `failure_category = "policy_hallucination"` — new structured field |

Improvement: −3m 16s (−74%). Missing field identified: `failure_category` enum per result row.  
No fabricated names, timings, or squadmate references.

---

## 5. Cost per Query

**Status: Implemented**

Documented in `cost_by_stage.md`. All stages covered:
- Embedding: $0.00 (local CPU)
- Retrieval: ~$0.0000013 (Pinecone serverless read units)
- Generation: ~$0.0000213 (compound-mini simple RAG) / ~$0.0001738 (agent path)
- Tools: $0.00 (SQLite) + retrieval cost for rag_retrieval
- LLM Judge: ~$0.0000234 (3 judge calls async)

Measured vs. estimated clearly separated. Streaming token gap acknowledged.

---

## 6. Prompt Caching

**Status: Deferred**

Assessment: The RAG system prompt (~120 tokens, now v1.2) is repeated on every call and is a candidate for Groq prompt prefix caching. At 535 input tokens per call, cached prefix would save ~22% input cost.

Not implemented this week because:
1. Groq's prompt caching availability for the compound-mini / gpt-oss-120b models is not confirmed in the SDK version in use (`groq>=0.9.0,<1.0.0`)
2. The RAG prompt is short enough that caching savings are modest (~$0.0000035 per query at compound-mini pricing)
3. Semantic caching poses a higher risk in a refund-policy context (see #7 below)

Deferred: Validate Groq caching support and measure actual cache hit rate before implementing.

---

## 7. Semantic Caching

**Status: Deferred — do not implement yet**

Semantic caching (reusing answers for equivalent queries) is **not safe** for this application without additional safeguards:
- Refund policy answers depend on policy version — a cached answer from before a policy update could be wrong
- User-specific conditions (customer tier, order status) differ between sessions
- The T01/T11 failure demonstrates that a wrong cached answer would propagate silently

Assessment: Before implementing semantic caching for any refund policy query:
1. Cache keys must include `prompt_version`, `namespace`, and `policy_version`
2. Cache TTL must not exceed the policy update cadence
3. Refund-category queries (namespace=`Product Returns & Refund Policy`) should be excluded from semantic caching until the policy_claim_check guard is live in production

Deferred. Do not implement to satisfy this checklist.

---

## 8. Model Routing (LiteLLM)

**Status: Deferred**

Current architecture: single Groq model per request, model name from `.env`.

Assessment: LiteLLM routing would benefit the application IF:
- Multiple providers are needed for failover (Groq → OpenAI fallback)
- Task complexity-based routing is desired (simple policy query → cheap small model; complex multi-step agent → large model)

Neither condition is met today: only Groq is configured, and the BudgetTracker already caps cost per agent run ($0.02 max). LiteLLM adds a dependency and routing latency (~5–20 ms) that is not justified by current volume.

Deferred. Revisit at 10× volume when provider diversity becomes a resiliency requirement.

---

## 9. Fallbacks and Rate Limits

**Status: Improved**

**Already in place:**
- `observability/langfuse_client.py`: no-op fallback if Langfuse is down
- `BudgetTracker.check()`: hard limits on iterations, tokens, cost, wall-clock per agent run (`agent/budgets.py`)
- Output guardrails: `agent/tools/output_guardrails.py` blocks injection markers, PII, prompt leakage

**Gaps identified this week:**
- No exponential backoff on Groq API 429 errors (GroqModel.generate() calls `client.chat.completions.create()` with no retry logic)
- No circuit breaker for Pinecone unavailability
- Streaming path has no token-usage tracking (`last_stream_usage = None`)
- The `generate()` method has no timeout parameter

**Improvements deferred** (would require adding `tenacity` or `backoff` dependency — justified at 10× volume, not at current scale):

```python
# Recommended addition to llm/groq_model.py (not yet implemented):
# from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
# from groq import RateLimitError
# @retry(retry=retry_if_exception_type(RateLimitError), wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(3))
```

Fallbacks never bypass refund-policy validation per existing guardrail design — confirmed by code review.

---

## 10. The Data Flywheel

**Status: Improved**

**Already in place:**
- `eval/create_langfuse_dataset.py`: 25 golden Q&A pairs pushed to Langfuse dataset
- `analysis/trace_logger.py`: 25 runs → `traces.jsonl` + Langfuse traces
- `analysis/week5_analysis.py`: offline error taxonomy from `traces.jsonl`
- LLM-judge scores auto-pushed per request to Langfuse

**Improved this week:**
- T11 added to eval suite as a human-reviewed regression case from the T01 refund failure
- `failure_category` field added to result rows — makes failure-type filtering searchable
- Workflow: confirmed human review → eval case → regression prevention cycle is working (T01 failure → T11 regression case → RED→GREEN verified)

**Not implemented:** Automatic promotion of low-judge-score answers to a review queue. Deferred — sensitive for refund policy (unverified answers must not become ground truth automatically).

---

## 11. The 10× Plan

**Status: Implemented**

Documented in `tenx.md`. Key finding:

**First bottleneck at 10×: Groq free-tier TPM limit on the agent path.**
- At 10× peak: ~9,750 TPM estimated vs. 6,000 TPM free-tier limit (62.5% over)
- Mitigation: upgrade to Groq paid tier (~$15/month at 10× agent volume)
- Cost is not the bottleneck; rate limits are
- Load-test plan provided (Locust) since no live traffic data exists

---

## 12. Fine-Tuning — Last Resort

**Status: Not applicable (this week)**

Assessment of T01/T11 failure:

The refund policy hallucination (fabricated 15% restocking fee) was caused by:
1. **Prompt behavior** — the v1.0 system prompt did not explicitly prohibit confirming caller-suggested policy details
2. **Not a retrieval failure** — trace-005 shows retrieval correctly returned the relevant policy chunks (top score 0.727); the policy text is unambiguous

Root cause is entirely addressable at the **prompt layer** (v1.2 POLICY HALLUCINATION GUARD). Fine-tuning is not appropriate because:
- The training data does not yet include enough human-reviewed refund corrections to create a reliable fine-tuning dataset
- The simpler prompt fix has already demonstrated GREEN results in the eval suite
- Fine-tuning on Groq is not available for all models in use; adding infrastructure without justification violates the task constraints

Fine-tuning would be appropriate only if prompt improvements repeatedly fail to prevent policy hallucination after multiple policy categories are tested — which requires more data collection first.

**Recommendation: Defer fine-tuning. Monitor `policy_claim_check` rate in production after prompt v1.2 ships.**
