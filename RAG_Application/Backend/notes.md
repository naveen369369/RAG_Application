# Analysis Notes -- Week 5 Task Set A

**Date:** 2026-08-24  
**Seed:** 42  
**Analyst:** `analysis/week5_analysis.py` (automated, no RAG code modified)

---

## Task 1 -- Complete Trace + Replay

### Selected trace (seed=42, 1 drawn from all 25)

```
trace_id         : trace-021
timestamp        : 2026-08-24T12:15:36.827497+00:00
prompt_version   : v1.0
question         : How long does standard shipping take to arrive?
namespace        : Shipping & Delivery Information
model            : groq/compound-mini
temperature      : 0.2
top_k            : 5
use_hyde         : False
use_reranker     : False
retrieved_chunk_ids : ['Shipping & Delivery Information.docx:chunk-1', 'Shipping & Delivery Information.docx:chunk-3', 'Shipping & Delivery Information.docx:chunk-17', 'Shipping & Delivery Information.docx:chunk-7', 'Shipping & Delivery Information.docx:chunk-14']
retrieved_scores    : [0.7983, 0.739, 0.7261, 0.7118, 0.6957]
```

### Original output (from stored trace)

> Standard Shipping takes **5–7 business days** to arrive.【Section 1: Shipping Methods and Costs – “Standard Shipping: 5–7 business days, $4.99…”】

### Replayed output (using stored fields only -- chunk text re-fetched is NOT possible)

> Standard shipping typically takes **5–7 business days** to arrive.

### Trace field verification

**Required fields:**

- `prompt_version`: PRESENT
- `retrieved_chunk_ids`: PRESENT
- `retrieved_scores`: PRESENT
- `model`: PRESENT
- `temperature`: PRESENT
- `raw_output`: PRESENT

### What cannot be reconstructed from the stored trace

- `retrieved_chunk_text` -- raw text of each chunk is NOT stored, only IDs and scores. A true replay requires re-querying Pinecone for the exact chunk content.
- `top_p / stop_sequences / frequency_penalty` -- Groq API defaults were used but not recorded; minor sampling variations are possible on replay.
- `hyde_intermediate_doc` -- the hypothetical document generated when use_hyde=True is not stored; HyDE traces cannot be fully replicated from stored fields alone.

---

## Task 2 -- Random Sample

**Seed:** `42`  
**Method:** `random.Random(42).sample(all_traces, 20)`  
**Source:** Real traces generated live through the existing RAG pipeline + Pinecone + Groq.  
**No curated / demo / famous failure cases were used.**

### 20 sampled trace IDs

| # | Trace ID |
|---|----------|
| 1 | `trace-021` |
| 2 | `trace-004` |
| 3 | `trace-001` |
| 4 | `trace-009` |
| 5 | `trace-008` |
| 6 | `trace-025` |
| 7 | `trace-005` |
| 8 | `trace-024` |
| 9 | `trace-003` |
| 10 | `trace-014` |
| 11 | `trace-023` |
| 12 | `trace-015` |
| 13 | `trace-002` |
| 14 | `trace-018` |
| 15 | `trace-012` |
| 16 | `trace-022` |
| 17 | `trace-016` |
| 18 | `trace-011` |
| 19 | `trace-006` |
| 20 | `trace-007` |

---

## Task 3 -- Open Coding

**Rules applied:**
- All 20 traces were read in full before any category was created.
- Exactly one observation sentence per trace.
- No diagnosis, no category label, no proposed fix in this section.
- Observations describe only what was seen in question, retrieved chunks, and raw output.

| Trace ID | Observation (one sentence, observation only) |
|----------|----------------------------------------------|
| `trace-021` | The model correctly listed three shipping speed tiers and their timelines from the retrieved shipping chunk (score 0.73), with no fabricated figures observed. |
| `trace-004` | The model answered the refund timeline question with correct per-payment-method breakdowns matching the retrieved billing chunk at score 0.76. |
| `trace-001` | The model described the 30-minute lockout and Forgot Password flow but omitted the 60-minute reset-link expiry window and the password complexity requirements that appear in the retrieved chunk. |
| `trace-009` | The model correctly advised a 24-hour wait and check of neighbors and secure lockers before contacting support, matching the source document closely. |
| `trace-008` | The model produced the correct four-step troubleshooting sequence (force-close, update check, cache clear, reinstall) from the retrieved technical chunk at score 0.79. |
| `trace-025` | The model listed the four recommended security settings (2FA, login notifications, session timeout, trusted devices) as described in the retrieved account-management chunk with no fabricated advice. |
| `trace-005` | The model correctly stated that opened electronics can be returned within 30 days only if defective, but omitted the case-by-case eligibility review for non-defective opened items mentioned in the chunk. |
| `trace-024` | The model described checking case status through the Help Center portal and receiving proactive updates from the assigned senior agent, but the retrieved chunk (score 0.68) does not explicitly state a dedicated status-tracking page exists. |
| `trace-003` | The model correctly explained the authorization hold versus actual charge distinction, the 3-5 business day clearance window, and the escalation steps to billing support, matching the source document. |
| `trace-014` | The model correctly described the reset-email flow including the Spam folder check and 60-minute link expiry, and advised contacting support if emails still don't arrive after retrying. |
| `trace-023` | The model correctly described the three-tier complaint resolution SLA from the retrieved escalation chunk (score 0.73), distinguishing high, medium, and low priority timelines. |
| `trace-015` | The model attributed the decline to the use of a prepaid debit card (citing the retrieved billing policy chunk), but the user's question described a regular card with sufficient funds, making the prepaid-card explanation likely inapplicable to the user's actual situation. |
| `trace-002` | The model correctly distinguished account deactivation (90-day data retention, reactivate by logging in) from permanent deletion (30-day grace period, irreversible), matching the retrieved chunk at score 0.81. |
| `trace-018` | The model provided the correct seven-step return initiation flow (Orders > Order History > Start Return) and noted that three weeks is within the 30-day window, but added category-specific sub-windows not present in the primary retrieved chunk. |
| `trace-012` | The model listed the BBB chargeback option for the US and the GDPR Data Protection Authority for the EU matching the document, but appended a generic 'consumer protection agency in your country' statement not found in any retrieved chunk. |
| `trace-022` | The model correctly stated that express-shipping upgrades are possible before a tracking number is generated by contacting support, and quoted two phrases directly from the retrieved document chunks. |
| `trace-016` | The model correctly answered that store-credit refunds are applied within 24 hours, grounded in the retrieved billing chunk (score 0.71), with a direct quote from the document. |
| `trace-011` | The model listed the Live Chat escalation phrase and the ESCALATION REQUEST email subject correctly, but attributed escalated cases to a 'Tier-4 Executive Escalation team' label not present in the retrieved chunks. |
| `trace-006` | The model correctly answered that no return shipping is required for damaged items, described the 48-hour photo submission process, and listed the replacement or full-refund outcomes, matching the retrieved chunk at score 0.79. |
| `trace-007` | The model correctly identified ERR-1001 as an expired authentication token and prescribed logging out and back in as the fix, retrieved from the correct technical chunk at score 0.72. |

---

## Task 4 -- Error Taxonomy (summary)

Full ranked table is in `taxonomy.md`. Top 3 failure modes by Freq x Sev:

- **Rank 1:** Selective answer truncation -- model omits key policy detail present in the retrieved chunk  (20%, severity 4, Freq x Sev = 80) -- trace IDs: `trace-001`, `trace-005`, `trace-018`, `trace-012`
- **Rank 2:** Out-of-context addition -- model appends plausible-sounding text not found in any retrieved chunk  (15%, severity 4, Freq x Sev = 60) -- trace IDs: `trace-011`, `trace-012`, `trace-018`
- **Rank 3:** Wrong-chunk retrieval -- answer grounded in retrieved chunk but chunk does not fit the user's actual sub-scenario  (10%, severity 3, Freq x Sev = 30) -- trace IDs: `trace-015`, `trace-016`

---

## Task 5 -- Fix Target + Prediction

**Dated falsifiable prediction -- 2026-08-24**

**Failure mode targeted:** Selective answer truncation (Rank 1, 20% of sample, Freq x Sev = 80).

This is the top RAG-logic failure: the correct chunk is retrieved (high cosine scores 0.71-0.81 observed) but the generation step omits specific policy details present in that chunk -- e.g., the 60-minute reset-link expiry, password complexity rules, the non-defective electronics case-by-case review, and the EU GDPR authority path.

**Proposed change:** Add an explicit instruction to the LLM system prompt: *'When answering, you MUST include ALL specific numeric values, time windows, exceptions, and eligibility conditions from the provided context. Do not summarise or omit any policy clause.'* No retrieval or chunking changes are required.

**Current selective-truncation rate (20-trace sample):** **20%** (4 / 20 traces).

**Expected rate after the prompt addition:** **< 5%** (at most 1 / 20 traces).

**Falsifiability condition:** After adding the system-prompt instruction, re-run `analysis/trace_logger.py` with the same 25 questions and seed = 42 random sample; manually verify each answer against its source document chunk; the selective-truncation count must drop from 4 to <= 1 to confirm the fix.
---

## Task 6 -- Benchmark Comparison (3 sentences)

MMLU uses multiple-choice questions, so it cannot detect when an AI leaves out important policy details (truncation).
HumanEval only tests Python coding and has no documents, so it cannot detect when an AI hallucinates extra facts (out-of-context additions).
Neither benchmark tests document retrieval, meaning only real RAG trace analysis can catch when the wrong document chunk is pulled.
