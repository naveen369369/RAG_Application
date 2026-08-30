"""
Retry failed traces (those with ERROR: in raw_output).
Adds a 4-second delay between calls to stay under Groq rate limits.
Overwrites the traces.jsonl in place.
"""
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.rag_pipeline import RAGPipeline

TRACES_PATH = PROJECT_ROOT / "analysis" / "traces.jsonl"
DELAY = 4  # seconds between each retry call


def load_traces():
    with open(TRACES_PATH, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def retry_trace(pipeline, trace):
    q = trace["question"]
    ns = trace["namespace"]
    print(f"  Retrying {trace['trace_id']}: {q[:60]}")
    try:
        result = pipeline.query(
            question=q,
            namespace=ns,
            temperature=0.2,
            stream=False,
            return_sources=True,
            use_reranker=False,
            use_hyde=False,
        )
        raw_output = result.get("answer", "")
        sources = result.get("sources") or []
        retrieved_chunk_ids = [
            s.get("source", "") + ":chunk-" + str(s.get("chunk_index", -1))
            for s in sources
        ]
        retrieved_scores = result.get("scores", [])
        trace["raw_output"] = raw_output
        trace["retrieved_chunk_ids"] = retrieved_chunk_ids
        trace["retrieved_scores"] = retrieved_scores
        print(f"    OK — {len(raw_output)} chars")
    except Exception as exc:
        print(f"    STILL FAILING: {exc}")
    return trace


def main():
    print("=== Retry failed traces ===")
    traces = load_traces()
    errors = [t for t in traces if t["raw_output"].startswith("ERROR:")]
    print(f"Found {len(errors)} failed traces (out of {len(traces)} total)")

    if not errors:
        print("No retries needed.")
        return

    pipeline = RAGPipeline()

    for i, trace in enumerate(errors):
        if i > 0:
            print(f"  Waiting {DELAY}s...")
            time.sleep(DELAY)
        trace_id = trace["trace_id"]
        # Update in-place in traces list
        for j, t in enumerate(traces):
            if t["trace_id"] == trace_id:
                traces[j] = retry_trace(pipeline, trace)
                break

    # Write back
    with open(TRACES_PATH, "w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")

    still_errors = [t for t in traces if t["raw_output"].startswith("ERROR:")]
    print(f"\nDone. {len(traces)} traces total, {len(still_errors)} still errored.")


if __name__ == "__main__":
    main()
