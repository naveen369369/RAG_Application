# Week-11 Support Drill Report

## Drill 1 — Baseline (Before Observability Improvement)

| Field | Value |
|---|---|
| **Time-to-find** | **04:23** |
| Search slice | `traces.jsonl` filtered by `namespace = "Product Returns & Refund Policy"` and manual keyword scan of `raw_output` for "return" + "headphones" |
| Driller | Sanjith Kumaran (developer, self-timed) |
| Planted failure | T01 mock trajectory answer: "opened items in good condition qualify for return with 15% restocking fee" — fabricated policy not present in Hr-3.md |
| Search path | 1. Checked `analysis/traces.jsonl` for refund-related traces → found trace-005 with correct answer → confirmed the discrepancy with T01 mock → traced back to `eval/trajectory_eval.py:_MOCK_BEFORE["T01"]` |

### Why it took 04:23

The failure required **three manual steps**:
1. Open `traces.jsonl` and scan for refund namespace entries (no structured `failure_category` field)
2. Read `trajectory_eval.py` mock data to find the contradicting T01 answer
3. Cross-reference `Hr-3.md` policy text to confirm the claim was fabricated

**Missing field identified:** No `policy_claim_check` boolean per trace/eval result to flag when an answer contains a numeric percentage or fee not present in the retrieved chunks.

---

## Missing Log Field / Index

| Field | Description | Where to add |
|---|---|---|
| `policy_claim_check` | Boolean — True if the generated answer contains a numeric fee, percentage, or deadline not verbatim in retrieved chunks | Per-generation span in `observability/langfuse_client.py`; also as a Langfuse score |
| `forbidden_terms_detected` | List of strings — policy terms in the answer that have no match in retrieved chunk text | Same location |
| `failure_category` | Enum: `policy_hallucination`, `argument_fabrication`, `wrong_tool_sequence`, `retrieval_miss`, `none` | Eval result rows in `trajectory_eval.py` and any future live eval log |

---

## Drill 2 — After Observability Improvement

| Field | Value |
|---|---|
| **Time-to-find** | **01:07** |
| Search slice | Filter Langfuse traces by `policy_claim_check = true` (or in `traces.jsonl` by `failure_category = "policy_hallucination"`) |
| Improvement driver | `policy_claim_check` field added to eval result rows and logged as a Langfuse score; `failure_category` field now present in every trajectory result row |
| Method | Query `traces.jsonl` or Langfuse dataset for `failure_category = "policy_hallucination"` → 2 results (T01, T11) surfaced immediately |

### Time improvement: 04:23 → 01:07 (−03:16, −74%)

**Root cause of improvement:** Adding `failure_category` and `policy_claim_check` to structured logs makes the failure searchable in O(1) rather than requiring manual text scanning of raw output.

---

## Canary and Rollback Plan

**Prompt version change:** v1.0 → v1.2 (added POLICY HALLUCINATION GUARD instruction)

### Two-line canary plan
1. Route 5% of live refund-policy queries to prompt v1.2 for 24 hours; compare `policy_claim_check` flag rate and LLM judge faithfulness score between v1.0 and v1.2 cohorts.
2. If faithfulness drops below 0.85 or `policy_claim_check` rate increases vs. v1.0, revert `PROMPT_VERSION` in `llm/groq_model.py` to `v1.0` — one-line change, zero downtime, no data migration needed.

### Rollback
```python
# llm/groq_model.py — revert this line to roll back
PROMPT_VERSION = "v1.0"   # was "v1.2"
# Also revert RAG_SYSTEM_PROMPT to remove the POLICY HALLUCINATION GUARD paragraph.
```
