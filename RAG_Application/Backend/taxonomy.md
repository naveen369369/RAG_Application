# Error Taxonomy -- Week 5 Task Set A

**Analysis date:** 2026-08-24  
**Sample:** 20 traces randomly selected, seed = 42  
**Ranked by:** Frequency (%) x Severity (1-5)

> Severity scale: 1 = cosmetic | 2 = minor | 3 = moderate | 4 = significant | 5 = critical

| Rank | Failure Mode | Count | Frequency | Severity | Freq x Sev | Trace IDs |
|------|-------------|------:|----------:|---------:|-----------:|-----------|
| 1 | Selective answer truncation -- model omits key policy detail present in the retrieved chunk | 4 | 20% | 4 | 80 | `trace-001`, `trace-005`, `trace-018`, `trace-012` |
| 2 | Out-of-context addition -- model appends plausible-sounding text not found in any retrieved chunk | 3 | 15% | 4 | 60 | `trace-011`, `trace-012`, `trace-018` |
| 3 | Wrong-chunk retrieval -- answer grounded in retrieved chunk but chunk does not fit the user's actual sub-scenario | 2 | 10% | 3 | 30 | `trace-015`, `trace-016` |
| 4 | Unverified capability claim -- model asserts a portal feature exists that the retrieved chunk does not confirm | 1 | 5% | 3 | 15 | `trace-024` |
| 5 | Correct answer -- question fully and accurately answered from retrieved context | 10 | 50% | 0 | 0 | `trace-021`, `trace-004`, `trace-009`, `trace-008`, `trace-025`, `trace-003`, `trace-014`, `trace-023`, `trace-002`, `trace-006` |

---

## Ranking Notes

- **Rank 1 (Selective answer truncation):** In all 4 cases the correct chunk was retrieved
  (high cosine scores 0.71-0.81), but the model produced a partial answer, omitting specific
  policy clauses -- e.g., the 60-minute reset-link expiry, password complexity rules, the
  non-defective electronics case-by-case review path, and the EU GDPR escalation authority.
  This is the top RAG-logic failure: retrieval is working, generation is lossy.

- **Rank 2 (Out-of-context addition):** The model appended plausible-sounding information
  not present in any retrieved chunk: a 'Tier-4 Executive Escalation team' label, a generic
  'consumer protection agency in your country' statement, and category-specific return
  sub-windows. This is a hallucination risk -- customers may act on fabricated policy details.

- **Rank 3 (Wrong-chunk retrieval):** The retriever found the correct domain (billing) but
  a chunk covering a different sub-scenario (prepaid card rules) for a regular-card question.
  The answer was therefore grounded but misaligned with the user's actual situation.

- **Rank 4 (Unverified capability claim):** The model asserted a dedicated complaint
  status-tracking page exists on the Help Center portal; no retrieved chunk confirms this.

- **Rank 5 (Correct):** 10 of 20 sampled traces (50%) had fully correct, well-grounded
  answers with no observed failure or omission.
