# The 10× Plan — What Breaks First at 10× Volume?

> Clearly distinguished: **M** = measured/observed from code or logs, **E** = estimate/projection.  
> No invented load-test numbers. Load-test plan included where data is missing.

---

## Current Baseline

| Metric | Value | Source |
|---|---|---|
| Traced queries | 25 (single batch run) | `analysis/traces.jsonl` **M** |
| Trace batch duration | ~88 seconds for 25 queries | timestamps trace-001 to trace-025 **M** |
| Sequential throughput | ~0.28 qps (25/88s) | Calculated **M** |
| Assumed daily traffic | ~100–500 queries/day | No live traffic data; estimate based on small team/dev use **E** |
| Concurrency | 1 (sequential trace run) | `trace_logger.py` **M** |
| Mean query latency | ~2.8 s | 88s / 25 **M** |
| Mean agent latency (mock) | ~520 ms | trajectory_eval mock data, 10 cases **M** |
| Cost per simple RAG query | ~$0.000046 | `cost_by_stage.md` **E** |
| Cost per agent query | ~$0.000199 | `cost_by_stage.md` **E** |

**Traffic baseline assumption:** 250 queries/day (midpoint of estimated range).

---

## 10× Projected Load

| Metric | Baseline | 10× Projection | Source |
|---|---|---|---|
| Queries/day | 250 | 2,500 | **E** |
| Queries/hour (peak 2× avg) | ~21 | ~208 | **E** |
| Queries/second (peak) | ~0.006 | ~0.058 | **E** |
| Concurrency (assumed 10× parallel) | 1 | ~10 | **E** |
| Daily generation cost (RAG path) | $0.012 | $0.115 | **E** |
| Daily generation cost (agent path) | $0.050 | $0.498 | **E** |

---

## Provider Rate Limits and Headroom

### Groq API (compound-mini / llama-3.3-70b-versatile)

| Limit | Typical Groq limit | At 10× (0.058 qps) | Headroom |
|---|---|---|---|
| Requests per minute (RPM) | 30 RPM (free) / 6,000 RPM (paid) | ~3.5 RPM | Free: 88% headroom; paid: 99.9% **E** |
| Tokens per minute (TPM) | 6,000 TPM (free) / 1M TPM (paid) | ~2,300 TPM (agent path × 10) | Free: **TIGHT at 10×**; paid: ample **E** |
| Daily token budget | Check plan | ~585,000 input + 94,000 output tokens/day | Below most paid plan limits **E** |

> **At 10× on the Groq free tier**, tokens-per-minute is the binding constraint.  
> At 10× peak (10 concurrent × ~230 tokens/call): ~2,300 TPM vs 6,000 TPM limit → 38% of limit.  
> However, if agent path with 3 LLM turns: ~6,900 TPM — **exceeds the 6,000 TPM free tier limit**.

### Pinecone Serverless
- No hard RPS limit on serverless; scales automatically.
- Cost scales linearly with read units. At 10×: ~$0.013/day — negligible.

### Local SentenceTransformer Embedding
- CPU-bound. Single-threaded sequential encoding.
- At 0.058 qps with ~312 ms encoding latency: 0.058 × 0.312 = 1.8% CPU utilization — no bottleneck **E**.

---

## First Bottleneck at 10×

**The first bottleneck is: Groq free-tier TPM limit on the agent path.**

| Evidence | Number |
|---|---|
| Free tier TPM limit | 6,000 TPM |
| 10× agent load TPM estimate (3 turns × 325 tokens × 10 concurrent) | ~9,750 TPM |
| Excess above limit | **+3,750 TPM (62.5% over)** |
| Result | HTTP 429 rate limit errors; exponential backoff; latency spike from ~0.5s to 30s+ |

On the **paid tier**, the first bottleneck shifts to:

**Local embedding latency + single-process FastAPI concurrency.**  
- With 10 concurrent requests and 312 ms embedding per request: effective throughput cap ~3 qps on a single process.  
- At 10× (0.058 qps peak) this is not yet a problem — but at 100×, embedding becomes the bottleneck.

---

## Cost at 10×

| Path | Daily cost (10×) | Monthly cost (10×) |
|---|---|---|
| Simple RAG only | $0.115/day | ~$3.45/month |
| Mixed RAG + Agent (50/50) | $0.307/day | ~$9.21/month |
| Agent only | $0.498/day | ~$14.94/month |

Cost does not break the bank at 10×. The constraint is rate limits, not spend.

---

## Recommended Mitigation

| Issue | Mitigation | Expected trade-off |
|---|---|---|
| Groq free-tier TPM exhausted | Upgrade to Groq paid tier ($0.30/$0.60 per 1M tokens) | +$15/month at 10× agent volume; removes the bottleneck |
| Single-process embedding bottleneck | Run embedding in a thread pool (`asyncio.to_thread`) or deploy a separate embedding service | +complexity; removes ~3 qps ceiling |
| No prompt caching | Enable Groq prompt prefix caching for the static system prompt (~120 tokens) | Could save ~22% input token cost per query; not yet measurable |
| No retry budget | Add exponential backoff with jitter + circuit breaker for Groq 429s | Prevents retry storms under rate-limit pressure |

---

## Load-Test Plan (data gap)

No real traffic or load-test data exists. To validate 10× assumptions:

```bash
# Install locust
pip install locust

# locustfile.py — send 10 concurrent /chat requests
# from locust import HttpUser, task
# class RagUser(HttpUser):
#     @task
#     def chat(self):
#         self.client.post("/chat", json={"query": "What is the return window for electronics?", "namespace": "Product Returns & Refund Policy"})

# Run: locust -f locustfile.py --headless -u 10 -r 2 --run-time 5m --host http://localhost:8000
# Capture: latency P50/P95/P99, error rate, Groq 429 events, embedding CPU %
```

Validate these projections against actual measured results before any production scaling decision.
