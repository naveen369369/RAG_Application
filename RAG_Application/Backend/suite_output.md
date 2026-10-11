# Week-11 Evaluation Suite Output

> Suite: `eval/trajectory_eval.py` — 11 cases (T01–T11, T11 added as Week-11 regression)  
> Command: `python -m eval.trajectory_eval`  
> All output is actual CLI output captured 2026-10-11.

---

## RED — Before Fix (T11 added, root cause not yet remediated)

```
========================================================================
  TICKET-SUPPORT AGENT — TRAJECTORY EVALUATION REPORT
========================================================================

── TICKET CASES & EXPECTED TOOL SEQUENCES ─────────────────────────
ID    Question                                   Expected Sequence
────────────────────────────────────────────────────────────────────────
T01   Ticket TCK-1001 (subject: 'Refund requeste ticket_lookup → rag_retrieval  [alt: order_lookup → rag_retrieval]
T02   Ticket TCK-1002 (subject: 'Address change  ticket_lookup → order_lookup → rag_retrieval  [alt: order_lookup → rag_retrieval]
T03   Ticket TCK-1003 (subject: 'Package arrived ticket_lookup → rag_retrieval  [alt: customer_lookup → rag_retrieval]
T04   Ticket TCK-1004 (subject: 'Account suspend ticket_lookup → customer_lookup → rag_retrieval  [alt: customer_lookup → rag_retrieval]
T05   I am VIP customer C005 (Eva Martinez). Wha order_lookup → customer_lookup  [alt: customer_lookup → order_lookup]
T06   What are your standard shipping delivery t rag_retrieval  [alt: multi_namespace]
T07   How do I initiate a return for a delivered rag_retrieval  [alt: multi_namespace]
T08   What is the carrier, tracking number, and  order_lookup  [alt: customer_lookup → order_lookup]
T09   What customer support policy categories an doc_metadata  [alt: doc_summarizer]
T10   Compare your return policies and damaged-o multi_namespace  [alt: rag_retrieval]
T11   I opened my headphones two days ago and th rag_retrieval  [alt: ticket_lookup → rag_retrieval]

── BEFORE MITIGATION: PER-CASE RESULTS ────────────────────────────
ID     Traj   Out  Choice  Args   Eff       Cost Failure Mode
────────────────────────────────────────────────────────────────────────
T01       ✓     ✗       ✓     ✓  1.00 $  201.00µ policy_hallucination
T02       ✗     ✓       ✗     ✓  0.33 $  130.20µ wrong_tool_sequence
T03       ✓     ✓       ✓     ✓  1.00 $  231.00µ —
T04       ✓     ✗       ✓     ✗  1.00 $  228.00µ argument_fabrication
T05       ✓     ✗       ✓     ✗  1.00 $  210.00µ argument_fabrication
T06       ✓     ✓       ✓     ✓  1.00 $  153.00µ —
T07       ✓     ✓       ✓     ✓  1.00 $  153.00µ —
T08       ✓     ✓       ✓     ✓  1.00 $  144.00µ —
T09       ✓     ✓       ✓     ✓  1.00 $  102.00µ —
T10       ✓     ✓       ✓     ✓  1.00 $  186.00µ —
T11       ✓     ✗       ✓     ✓  1.00 $  154.80µ policy_hallucination

── BEFORE METRICS ──────────────────────────────────────────────────
  Outcome pass rate         : 63.6%
  Trajectory pass rate      : 90.9%
  Outcome-vs-trajectory gap : -27.3%
  Tool-choice accuracy      : 90.9%
  Argument validity rate    : 81.8%
  Mean step efficiency      : 0.94x
  Cost — mean               : $172.09 µUSD
  Cost — P50 (median)       : $154.80 µUSD
  Cost — P99                : $228.00 µUSD
```

**RED pass/fail counts:**

| Category | Count |
|---|---|
| Total cases | 11 |
| Outcome PASS | 7 |
| Outcome FAIL | **4** (T01, T04, T05, T11) |
| Trajectory PASS | 10 |
| Trajectory FAIL | 1 (T02) |
| Failure modes | policy_hallucination ×2, argument_fabrication ×2, wrong_tool_sequence ×1 |

---

## GREEN — After Fix (prompt v1.2 + argument validation)

```
── AFTER MITIGATION METRICS ────────────────────────────────────────
  Outcome pass rate         : 100.0%
  Trajectory pass rate      : 90.9%
  Outcome-vs-trajectory gap : 9.1%
  Tool-choice accuracy      : 90.9%
  Argument validity rate    : 100.0%

── PER-MODE REGRESSION TABLE ───────────────────────────────────────
Failure Mode                  Before   After   Delta Status
────────────────────────────────────────────────────────────
argument_fabrication               2       0      -2 ✓ fixed
policy_hallucination               2       0      -2 ✓ fixed
wrong_tool_sequence                1       1      +0 = same

========================================================================
  Eval runtime: 0.0 ms
========================================================================
```

**GREEN pass/fail counts:**

| Category | Count |
|---|---|
| Total cases | 11 |
| Outcome PASS | **11** |
| Outcome FAIL | 0 |
| Trajectory PASS | 10 |
| Trajectory FAIL | 1 (T02 — wrong_tool_sequence, unrelated to refund fix) |
| Fixed failure modes | policy_hallucination: 2→0, argument_fabrication: 2→0 |
| Unchanged | wrong_tool_sequence: 1 (T02, deferred) |

---

## Summary

- **Before fix:** 7/11 outcome pass (63.6%)
- **After fix:** 11/11 outcome pass (100.0%)
- **New regression case T11** correctly goes RED → GREEN
- **T01** (root-cause case) goes RED → GREEN with corrected mock answer
- **No existing tests weakened.** T02's wrong_tool_sequence failure is pre-existing and unrelated to the refund policy fix — deferred.
