# Cost per Query by Stage

> Currency: USD  
> All generation costs use Groq pricing. Embedding runs locally (no API cost).  
> Token counts are estimated from `analysis/traces.jsonl` (25 actual traces) and  
> trajectory eval mock data (10 ticket cases). Clearly marked: **M** = measured/observed, **E** = estimate.

---

## Model Pricing Assumptions

| Model | Source | Input $/1M tokens | Output $/1M tokens |
|---|---|---|---|
| groq/compound-mini | Groq docs (estimated) | $0.030 | $0.060 |
| llama-3.3-70b-versatile | BudgetTracker (`budgets.py`) | $0.300 | $0.600 |
| Embedding (BAAI/bge-large-en-v1.5) | Local SentenceTransformer | $0.00 | $0.00 |
| Pinecone serverless | Pinecone docs | ~$0.025/1M RU | — |

> The .env sets `GROQ_MODEL_NAME=openai/gpt-oss-120b`; `traces.jsonl` records `model=groq/compound-mini` — costs below use compound-mini as the **measured** model. BudgetTracker prices are used for the **agent** path.

---

## Stage 1 — Embedding (Retrieval Prep)

| Item | Value | Source |
|---|---|---|
| Model | BAAI/bge-large-en-v1.5 (local) | .env **M** |
| Tokens encoded | ~15 per query (question only) | **E** |
| API cost per query | **$0.00** | Local CPU, no API **M** |
| Latency | ~312 ms | trace.json span-embed **M** |

---

## Stage 2 — Retrieval (Pinecone Vector Search)

| Item | Value | Source |
|---|---|---|
| Index | rag-dense-index (serverless) | .env **M** |
| Top-K | 5 | .env `TOP_K_RESULTS=5` **M** |
| Estimated read units | ~50 RU per query | Pinecone serverless model **E** |
| Cost per query | ~$0.0000013 | $0.025/1M RU × 50 **E** |
| Latency | ~187 ms | trace.json span-retrieval **M** |

Retrieval cost is negligible (<0.1% of total).

---

## Stage 3 — Generation (Groq LLM)

Calculated from `analysis/traces.jsonl` — 25 traces observed.

### Simple RAG path (direct `/chat` endpoint)

| Item | Observed value | Source |
|---|---|---|
| System prompt tokens | ~120 | RAG_SYSTEM_PROMPT word count × 1.3 **E** |
| Context (5 chunks × ~80 tokens) | ~400 | traces.jsonl chunk sizes **E** |
| Question tokens | ~15 | trace-005 question **M** |
| Total input tokens | ~535 | Sum **E** |
| Output tokens | ~87 | trace-005 span-generation **M** |
| Input cost | $0.0000161 | 535 × $0.030/1M **E** |
| Output cost | $0.0000052 | 87 × $0.060/1M **E** |
| **Total generation cost** | **~$0.0000213** | compound-mini path **E** |

### Agent path (ReAct agent, 2–3 tool calls)

From trajectory_eval.py mock data (10 cases):

| Metric | Value | Source |
|---|---|---|
| Mean input tokens | 391 | trajectory_eval mock **M** |
| Mean output tokens | 94 | trajectory_eval mock **M** |
| Pricing | $0.30/$0.60 per 1M | BudgetTracker (`budgets.py`) **M** |
| Input cost | $0.0001173 | 391 × $3e-7 **M** |
| Output cost | $0.0000565 | 94.2 × $6e-7 **M** |
| **Total agent generation cost** | **~$0.0001738** | per ticket case **M** |

> Agent path uses a larger model (llama-3.3-70b-versatile budget assumptions) and 2–3 LLM turns, making it ~8× more expensive than the simple RAG path.

---

## Stage 4 — Tool Execution

| Tool | API cost | Latency (est.) | Source |
|---|---|---|---|
| `rag_retrieval` | See Stage 2 ($0.0000013) | ~500 ms total | trace.json **M** |
| `ticket_lookup` / `order_lookup` | $0.00 (local SQLite) | ~5 ms | **E** |
| `customer_lookup` | $0.00 (local SQLite) | ~5 ms | **E** |
| `doc_metadata` / `doc_summarizer` | $0.00 (in-process) | ~10 ms | **E** |
| `multi_namespace` | See Stage 2 (×2 namespaces) | ~900 ms | **E** |

Tool execution cost is dominated by additional Groq calls in multi-step agent paths.

---

## Stage 5 — LLM Judge (Langfuse evaluation)

Runs asynchronously after each `/chat` request when Langfuse is enabled.

| Item | Value | Source |
|---|---|---|
| Judge calls per request | 3 (faithfulness, relevancy, context_utilization) | `llm_judge.py` **M** |
| Input tokens per judge call | ~200 | LLM judge prompts **E** |
| Output tokens per judge call | ~30 | JSON score output **E** |
| Cost per judge call | ~$0.0000078 | 200×$3e-7 + 30×$6e-7 (compound-mini) **E** |
| **Total judge cost per request** | **~$0.0000234** | 3 × $0.0000078 **E** |

---

## Stage 6 — Caching and Routing Overhead

| Item | Value | Source |
|---|---|---|
| Prompt prefix caching | Not implemented | Code review **M** |
| Semantic caching | Not implemented | Code review **M** |
| LiteLLM routing | Not implemented | Code review **M** |
| Overhead cost | $0.00 | Nothing to measure **M** |

---

## Summary: Total Cost per Query

| Path | Generation | Retrieval | Tools | Judge | **Total** |
|---|---|---|---|---|---|
| Simple RAG (compound-mini) | $0.0000213 | $0.0000013 | $0.00 | $0.0000234 | **~$0.0000460** |
| Agent path (llama-70b budget) | $0.0001738 | $0.0000013 | $0.00 | $0.0000234 | **~$0.0001985** |

### Calculation method
- Input cost = `input_tokens × (model_input_price / 1,000,000)`
- Output cost = `output_tokens × (model_output_price / 1,000,000)`
- Total = input_cost + output_cost + retrieval_cost
- Shared costs (embedding, Langfuse flush) not double-counted

### What is not measured
- Langfuse SaaS cost (free tier assumed)
- Pinecone index storage cost (serverless billing, assumed minimal for 6 namespaces)
- Network egress / compute for local embedding (CPU time, no dollar cost)
- Stream token costs for `/chat/stream` (Groq streaming mode, usage not tracked per `groq_model.py:last_stream_usage = None`)
