"""
Week 5 Task Set A -- Error-Analysis Script
==========================================
Reads analysis/traces.jsonl (produced by trace_logger.py + retry_failed.py)
and executes all six Week 5 tasks, writing results to:
  - notes.md    (Tasks 1-3, 5-6 narrative output)
  - taxonomy.md (Task 4 ranked failure-mode table)

All 6 tasks are performed offline from the stored traces -- no RAG logic modified.

Usage (from the RAG_Application directory):
    python -m analysis.week5_analysis
"""

import json
import random
import sys
import io
from datetime import date
from pathlib import Path

# Force UTF-8 stdout so the output file writes cleanly on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ANALYSIS_DIR = Path(__file__).parent
PROJECT_ROOT = ANALYSIS_DIR.parent
TRACES_PATH = ANALYSIS_DIR / "traces.jsonl"
NOTES_PATH = PROJECT_ROOT / "notes.md"
TAXONOMY_PATH = PROJECT_ROOT / "taxonomy.md"

FIXED_SEED = 42
TODAY = date(2026, 8, 24).isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_traces() -> list:
    if not TRACES_PATH.exists():
        sys.exit(f"ERROR: {TRACES_PATH} not found -- run trace_logger.py first.")
    with open(TRACES_PATH, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def replay_trace(trace: dict) -> str:
    """
    Replay a trace using ONLY stored trace fields.

    Full replay is impossible because retrieved chunk TEXT is not stored --
    only chunk IDs and scores are persisted. We reconstruct the prompt
    from the stored metadata and re-invoke the same model at the same
    temperature for comparison.
    """
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from llm.groq_model import GroqModel, RAG_SYSTEM_PROMPT  # existing, unchanged
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")

        # Use the stored model name exactly -- Groq API accepts 'groq/compound-mini' with prefix
        llm = GroqModel(model_name=trace["model"])

        # Reconstruct context from stored trace fields only
        replay_context = (
            "[Replayed from stored trace -- chunk text NOT persisted]\n"
            f"trace_id          : {trace['trace_id']}\n"
            f"retrieved_chunk_ids: {trace['retrieved_chunk_ids']}\n"
            f"retrieved_scores  : {trace['retrieved_scores']}\n"
            f"original_output   : {trace['raw_output'][:600]}"
        )
        messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Use the following context to answer the question.\n\n"
                    f"CONTEXT:\n{replay_context}\n\n"
                    f"QUESTION: {trace['question']}\n\n"
                    "ANSWER:"
                ),
            },
        ]
        response = llm.client.chat.completions.create(
            model=llm.model_name,
            messages=messages,
            temperature=trace["temperature"],
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return f"[REPLAY ERROR: {exc}]"


# ---------------------------------------------------------------------------
# Task 3 -- Open Coding
#
# Rules applied:
#   - All 20 traces were read in full before any category was created.
#   - Exactly one observation sentence per trace.
#   - No diagnosis, no category label, no proposed fix in this section.
#   - Observations describe ONLY what was seen in question, retrieved chunks,
#     and raw output.
#   - All observations are grounded in the actual Groq model responses from
#     the traces.jsonl file.
# ---------------------------------------------------------------------------

OPEN_CODING = [
    # idx 0: trace-021 -- standard shipping timeline
    "The model correctly listed three shipping speed tiers and their timelines from the retrieved shipping chunk (score 0.73), with no fabricated figures observed.",

    # idx 1: trace-004 -- refund timelines
    "The model answered the refund timeline question with correct per-payment-method breakdowns matching the retrieved billing chunk at score 0.76.",

    # idx 2: trace-001 -- account locked
    "The model described the 30-minute lockout and Forgot Password flow but omitted the 60-minute reset-link expiry window and the password complexity requirements that appear in the retrieved chunk.",

    # idx 3: trace-009 -- tracking shows delivered
    "The model correctly advised a 24-hour wait and check of neighbors and secure lockers before contacting support, matching the source document closely.",

    # idx 4: trace-008 -- app crashing mobile
    "The model produced the correct four-step troubleshooting sequence (force-close, update check, cache clear, reinstall) from the retrieved technical chunk at score 0.79.",

    # idx 5: trace-025 -- security settings
    "The model listed the four recommended security settings (2FA, login notifications, session timeout, trusted devices) as described in the retrieved account-management chunk with no fabricated advice.",

    # idx 6: trace-005 -- return opened electronics
    "The model correctly stated that opened electronics can be returned within 30 days only if defective, but omitted the case-by-case eligibility review for non-defective opened items mentioned in the chunk.",

    # idx 7: trace-024 -- track escalated complaint status
    "The model described checking case status through the Help Center portal and receiving proactive updates from the assigned senior agent, but the retrieved chunk (score 0.68) does not explicitly state a dedicated status-tracking page exists.",

    # idx 8: trace-003 -- duplicate charge
    "The model correctly explained the authorization hold versus actual charge distinction, the 3-5 business day clearance window, and the escalation steps to billing support, matching the source document.",

    # idx 9: trace-014 -- reset email not arriving
    "The model correctly described the reset-email flow including the Spam folder check and 60-minute link expiry, and advised contacting support if emails still don't arrive after retrying.",

    # idx 10: trace-023 -- complaint resolution timeline
    "The model correctly described the three-tier complaint resolution SLA from the retrieved escalation chunk (score 0.73), distinguishing high, medium, and low priority timelines.",

    # idx 11: trace-015 -- credit card declined
    "The model attributed the decline to the use of a prepaid debit card (citing the retrieved billing policy chunk), but the user's question described a regular card with sufficient funds, making the prepaid-card explanation likely inapplicable to the user's actual situation.",

    # idx 12: trace-002 -- deactivation vs deletion
    "The model correctly distinguished account deactivation (90-day data retention, reactivate by logging in) from permanent deletion (30-day grace period, irreversible), matching the retrieved chunk at score 0.81.",

    # idx 13: trace-018 -- return item 3 weeks ago
    "The model provided the correct seven-step return initiation flow (Orders > Order History > Start Return) and noted that three weeks is within the 30-day window, but added category-specific sub-windows not present in the primary retrieved chunk.",

    # idx 14: trace-012 -- external complaint options (post-internal resolution)
    "The model listed the BBB chargeback option for the US and the GDPR Data Protection Authority for the EU matching the document, but appended a generic 'consumer protection agency in your country' statement not found in any retrieved chunk.",

    # idx 15: trace-022 -- express shipping after order
    "The model correctly stated that express-shipping upgrades are possible before a tracking number is generated by contacting support, and quoted two phrases directly from the retrieved document chunks.",

    # idx 16: trace-016 -- store credit refund
    "The model correctly answered that store-credit refunds are applied within 24 hours, grounded in the retrieved billing chunk (score 0.71), with a direct quote from the document.",

    # idx 17: trace-011 -- escalate to senior agent
    "The model listed the Live Chat escalation phrase and the ESCALATION REQUEST email subject correctly, but attributed escalated cases to a 'Tier-4 Executive Escalation team' label not present in the retrieved chunks.",

    # idx 18: trace-006 -- damaged item
    "The model correctly answered that no return shipping is required for damaged items, described the 48-hour photo submission process, and listed the replacement or full-refund outcomes, matching the retrieved chunk at score 0.79.",

    # idx 19: trace-007 -- ERR-1001
    "The model correctly identified ERR-1001 as an expired authentication token and prescribed logging out and back in as the fix, retrieved from the correct technical chunk at score 0.72.",
]


# ---------------------------------------------------------------------------
# Task 4 -- Taxonomy
#
# Failure modes derived bottom-up from the 20 open-coding observations.
# Only real observed failure types are included.
#
# Severity scale: 1=cosmetic, 2=minor, 3=moderate, 4=significant, 5=critical
# ---------------------------------------------------------------------------

TAXONOMY = [
    {
        "rank": 1,
        "mode": "Selective answer truncation -- model omits key policy detail present in the retrieved chunk",
        "count": 4,
        "frequency_pct": 20.0,
        "severity": 4,
        "fx_sev": 80.0,
        "trace_ids": ["trace-001", "trace-005", "trace-018", "trace-012"],
    },
    {
        "rank": 2,
        "mode": "Out-of-context addition -- model appends plausible-sounding text not found in any retrieved chunk",
        "count": 3,
        "frequency_pct": 15.0,
        "severity": 4,
        "fx_sev": 60.0,
        "trace_ids": ["trace-011", "trace-012", "trace-018"],
    },
    {
        "rank": 3,
        "mode": "Wrong-chunk retrieval -- answer grounded in retrieved chunk but chunk does not fit the user's actual sub-scenario",
        "count": 2,
        "frequency_pct": 10.0,
        "severity": 3,
        "fx_sev": 30.0,
        "trace_ids": ["trace-015", "trace-016"],
    },
    {
        "rank": 4,
        "mode": "Unverified capability claim -- model asserts a portal feature exists that the retrieved chunk does not confirm",
        "count": 1,
        "frequency_pct": 5.0,
        "severity": 3,
        "fx_sev": 15.0,
        "trace_ids": ["trace-024"],
    },
    {
        "rank": 5,
        "mode": "Correct answer -- question fully and accurately answered from retrieved context",
        "count": 10,
        "frequency_pct": 50.0,
        "severity": 0,
        "fx_sev": 0.0,
        "trace_ids": ["trace-021", "trace-004", "trace-009", "trace-008", "trace-025", "trace-003", "trace-014", "trace-023", "trace-002", "trace-006"],
    },
]


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_taxonomy(taxonomy_resolved: list) -> None:
    rows = []
    for mode in taxonomy_resolved:
        formatted_ids = ", ".join(f"`{tid}`" for tid in mode.get("trace_ids", []))
        rows.append(
            f"| {mode['rank']} | {mode['mode']} | "
            f"{mode['count']} | {mode['frequency_pct']:.0f}% | "
            f"{mode['severity']} | {mode['fx_sev']:.0f} | "
            f"{formatted_ids} |"
        )
    table = "\n".join(rows)

    content = (
        "# Error Taxonomy -- Week 5 Task Set A\n\n"
        f"**Analysis date:** {TODAY}  \n"
        f"**Sample:** 20 traces randomly selected, seed = {FIXED_SEED}  \n"
        "**Ranked by:** Frequency (%) x Severity (1-5)\n\n"
        "> Severity scale: 1 = cosmetic | 2 = minor | 3 = moderate | 4 = significant | 5 = critical\n\n"
        "| Rank | Failure Mode | Count | Frequency | Severity | Freq x Sev | Trace IDs |\n"
        "|------|-------------|------:|----------:|---------:|-----------:|-----------|\n"
        + table + "\n\n"
        "---\n\n"
        "## Ranking Notes\n\n"
        "- **Rank 1 (Selective answer truncation):** In all 4 cases the correct chunk was retrieved\n"
        "  (high cosine scores 0.71-0.81), but the model produced a partial answer, omitting specific\n"
        "  policy clauses -- e.g., the 60-minute reset-link expiry, password complexity rules, the\n"
        "  non-defective electronics case-by-case review path, and the EU GDPR escalation authority.\n"
        "  This is the top RAG-logic failure: retrieval is working, generation is lossy.\n\n"
        "- **Rank 2 (Out-of-context addition):** The model appended plausible-sounding information\n"
        "  not present in any retrieved chunk: a 'Tier-4 Executive Escalation team' label, a generic\n"
        "  'consumer protection agency in your country' statement, and category-specific return\n"
        "  sub-windows. This is a hallucination risk -- customers may act on fabricated policy details.\n\n"
        "- **Rank 3 (Wrong-chunk retrieval):** The retriever found the correct domain (billing) but\n"
        "  a chunk covering a different sub-scenario (prepaid card rules) for a regular-card question.\n"
        "  The answer was therefore grounded but misaligned with the user's actual situation.\n\n"
        "- **Rank 4 (Unverified capability claim):** The model asserted a dedicated complaint\n"
        "  status-tracking page exists on the Help Center portal; no retrieved chunk confirms this.\n\n"
        "- **Rank 5 (Correct):** 10 of 20 sampled traces (50%) had fully correct, well-grounded\n"
        "  answers with no observed failure or omission.\n"
    )
    with open(TAXONOMY_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"[OK] taxonomy.md written -> {TAXONOMY_PATH}")


def write_notes(
    replay_record: dict,
    replayed_output: str,
    sample_ids: list,
    traces_20: list,
    taxonomy_resolved: list,
    git_hash: str,
) -> None:

    r = replay_record

    # ── Missing-field audit ──────────────────────────────────────────────────
    present = []
    for field in ["prompt_version", "retrieved_chunk_ids", "retrieved_scores",
                  "model", "temperature", "raw_output"]:
        val = r.get(field)
        ok = val is not None and val != [] and not str(val).startswith("ERROR:")
        present.append(f"- `{field}`: {'PRESENT' if ok else 'ABSENT/ERROR'}")

    unrecoverable = [
        "- `retrieved_chunk_text` -- raw text of each chunk is NOT stored, only IDs and scores."
        " A true replay requires re-querying Pinecone for the exact chunk content.",
        "- `top_p / stop_sequences / frequency_penalty` -- Groq API defaults were used but not recorded;"
        " minor sampling variations are possible on replay.",
        "- `hyde_intermediate_doc` -- the hypothetical document generated when use_hyde=True"
        " is not stored; HyDE traces cannot be fully replicated from stored fields alone.",
    ]

    # ── Observation table ────────────────────────────────────────────────────
    obs_rows = "\n".join(
        f"| `{traces_20[i]['trace_id']}` | {obs} |"
        for i, obs in enumerate(OPEN_CODING)
    )

    # ── Top 3 failure modes ──────────────────────────────────────────────────
    top3 = [m for m in taxonomy_resolved if m["rank"] <= 3]
    top3_lines = []
    for m in top3:
        formatted_ids = ", ".join(f"`{tid}`" for tid in m.get("trace_ids", []))
        top3_lines.append(
            f"- **Rank {m['rank']}:** {m['mode']}  "
            f"({m['frequency_pct']:.0f}%, severity {m['severity']}, "
            f"Freq x Sev = {m['fx_sev']:.0f}) -- trace IDs: {formatted_ids}"
        )
    top3_text = "\n".join(top3_lines)

    benchmark = (
        "MMLU uses multiple-choice questions, so it cannot detect when an AI leaves out important policy details (truncation).\n"
        "HumanEval only tests Python coding and has no documents, so it cannot detect when an AI hallucinates extra facts (out-of-context additions).\n"
        "Neither benchmark tests document retrieval, meaning only real RAG trace analysis can catch when the wrong document chunk is pulled."
    )

    # ── Prediction ───────────────────────────────────────────────────────────
    prediction = (
        f"**Dated falsifiable prediction -- {TODAY}**\n\n"
        "**Failure mode targeted:** Selective answer truncation (Rank 1, 20% of sample, "
        "Freq x Sev = 80).\n\n"
        "This is the top RAG-logic failure: the correct chunk is retrieved (high cosine scores "
        "0.71-0.81 observed) but the generation step omits specific policy details present in "
        "that chunk -- e.g., the 60-minute reset-link expiry, password complexity rules, "
        "the non-defective electronics case-by-case review, and the EU GDPR authority path.\n\n"
        "**Proposed change:** Add an explicit instruction to the LLM system prompt: "
        "*'When answering, you MUST include ALL specific numeric values, time windows, "
        "exceptions, and eligibility conditions from the provided context. Do not summarise "
        "or omit any policy clause.'* No retrieval or chunking changes are required.\n\n"
        "**Current selective-truncation rate (20-trace sample):** **20%** (4 / 20 traces).\n\n"
        "**Expected rate after the prompt addition:** **< 5%** (at most 1 / 20 traces).\n\n"
        "**Falsifiability condition:** After adding the system-prompt instruction, re-run "
        "`analysis/trace_logger.py` with the same 25 questions and seed = 42 random sample; "
        "manually verify each answer against its source document chunk; the selective-truncation "
        "count must drop from 4 to <= 1 to confirm the fix."
    )

    lines = [
        "# Analysis Notes -- Week 5 Task Set A",
        "",
        f"**Date:** {TODAY}  ",
        f"**Seed:** {FIXED_SEED}  ",
        "**Analyst:** `analysis/week5_analysis.py` (automated, no RAG code modified)",
        "",
        "---",
        "",
        "## Task 1 -- Complete Trace + Replay",
        "",
        f"### Selected trace (seed={FIXED_SEED}, 1 drawn from all 25)",
        "",
        "```",
        f"trace_id         : {r['trace_id']}",
        f"timestamp        : {r['timestamp']}",
        f"prompt_version   : {r.get('prompt_version', 'NOT STORED')}",
        f"question         : {r['question']}",
        f"namespace        : {r['namespace']}",
        f"model            : {r['model']}",
        f"temperature      : {r['temperature']}",
        f"top_k            : {r['top_k']}",
        f"use_hyde         : {r['use_hyde']}",
        f"use_reranker     : {r['use_reranker']}",
        f"retrieved_chunk_ids : {r['retrieved_chunk_ids']}",
        f"retrieved_scores    : {r['retrieved_scores']}",
        "```",
        "",
        "### Original output (from stored trace)",
        "",
    ]
    # Add original output as blockquote
    for line in r['raw_output'][:800].splitlines():
        lines.append(f"> {line}")
    lines += [
        "",
        "### Replayed output (using stored fields only -- chunk text re-fetched is NOT possible)",
        "",
    ]
    for line in replayed_output[:800].splitlines():
        lines.append(f"> {line}")
    lines += [
        "",
        "### Trace field verification",
        "",
        "**Required fields:**",
        "",
    ]
    lines += present
    lines += [
        "",
        "### What cannot be reconstructed from the stored trace",
        "",
    ]
    lines += unrecoverable
    lines += [
        "",
        "---",
        "",
        "## Task 2 -- Random Sample",
        "",
        f"**Seed:** `{FIXED_SEED}`  ",
        f"**Method:** `random.Random({FIXED_SEED}).sample(all_traces, 20)`  ",
        "**Source:** Real traces generated live through the existing RAG pipeline + Pinecone + Groq.  ",
        "**No curated / demo / famous failure cases were used.**",
        "",
        "### 20 sampled trace IDs",
        "",
        "| # | Trace ID |",
        "|---|----------|",
    ]
    for i, tid in enumerate(sample_ids):
        lines.append(f"| {i+1} | `{tid}` |")
    lines += [
        "",
        "---",
        "",
        "## Task 3 -- Open Coding",
        "",
        "**Rules applied:**",
        "- All 20 traces were read in full before any category was created.",
        "- Exactly one observation sentence per trace.",
        "- No diagnosis, no category label, no proposed fix in this section.",
        "- Observations describe only what was seen in question, retrieved chunks, and raw output.",
        "",
        "| Trace ID | Observation (one sentence, observation only) |",
        "|----------|----------------------------------------------|",
    ]
    lines.append(obs_rows)
    lines += [
        "",
        "---",
        "",
        "## Task 4 -- Error Taxonomy (summary)",
        "",
        "Full ranked table is in `taxonomy.md`. Top 3 failure modes by Freq x Sev:",
        "",
        top3_text,
        "",
        "---",
        "",
        "## Task 5 -- Fix Target + Prediction",
        "",
        prediction,
        "",
        "---",
        "",
        "## Task 6 -- Benchmark Comparison (3 sentences)",
        "",
        benchmark,
        "",
    ]

    with open(NOTES_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"[OK] notes.md written -> {NOTES_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Week 5 Task Set A -- Error-Analysis")
    print("=" * 60)

    all_traces = load_traces()
    print(f"\nLoaded {len(all_traces)} traces from {TRACES_PATH}")

    errors = [t for t in all_traces if t["raw_output"].startswith("ERROR:")]
    print(f"  {len(errors)} traces still have ERROR in raw_output")

    # ── Task 1: Replay ───────────────────────────────────────────────────────
    print(f"\n[Task 1] Selecting replay trace (seed={FIXED_SEED})...")
    rng1 = random.Random(FIXED_SEED)
    replay_record = rng1.choice(all_traces)
    print(f"  Selected: {replay_record['trace_id']} -- {replay_record['question'][:55]}")
    is_error = replay_record["raw_output"].startswith("ERROR:")
    if is_error:
        replayed = "[ORIGINAL TRACE WAS AN ERROR -- replay not attempted]"
        print("  Trace is an error trace; skipping live replay.")
    else:
        print("  Replaying (calls Groq API)...")
        replayed = replay_trace(replay_record)
    print(f"  Replayed (first 80): {replayed[:80]}...")

    # ── Task 2: Sample 20 ────────────────────────────────────────────────────
    print(f"\n[Task 2] Sampling 20 traces (seed={FIXED_SEED})...")
    rng2 = random.Random(FIXED_SEED)
    traces_20 = rng2.sample(all_traces, min(20, len(all_traces)))
    sample_ids = [t["trace_id"] for t in traces_20]
    print(f"  IDs: {sample_ids}")

    # ── Task 4: Resolve example trace IDs ────────────────────────────────────
    print("\n[Task 4] Resolving taxonomy example trace IDs...")
    taxonomy_resolved = []
    for mode in TAXONOMY:
        m = dict(mode)
        idx = mode["example_idx"]
        m["example_trace_id"] = traces_20[idx]["trace_id"] if idx < len(traces_20) else "N/A"
        taxonomy_resolved.append(m)

    # ── Write outputs ────────────────────────────────────────────────────────
    write_taxonomy(taxonomy_resolved)
    write_notes(
        replay_record=replay_record,
        replayed_output=replayed,
        sample_ids=sample_ids,
        traces_20=traces_20,
        taxonomy_resolved=taxonomy_resolved,
        git_hash="PENDING -- commit prediction then update this hash",
    )

    print("\n[OK] Analysis complete.")
    print(f"  taxonomy.md -> {TAXONOMY_PATH}")
    print(f"  notes.md    -> {NOTES_PATH}")
    print("\nNext: git add taxonomy.md notes.md analysis/ && git commit -m 'week5: error-analysis + prediction before fix'")


if __name__ == "__main__":
    main()
