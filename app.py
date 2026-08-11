"""
RAG Application Entry Point
============================
Command-line interface for the Retrieval-Augmented Generation (RAG) application.

Usage:
    # Index documents first:
    python app.py --index

    # Ask a question (non-streaming):
    python app.py --query "What is Retrieval-Augmented Generation?"

    # Ask a question with streaming output:
    python app.py --query "Explain machine learning" --stream

    # Ask a question and show source documents:
    python app.py --query "What is deep learning?" --sources

    # Interactive chat mode:
    python app.py --chat

    # View index statistics:
    python app.py --stats
"""

import os
import sys
import argparse
import logging
import glob
from dotenv import load_dotenv

from rag.rag_pipeline import RAGPipeline

load_dotenv()

logging.basicConfig(
    level=logging.WARNING,  # Suppress verbose logs in CLI mode
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                       RAG Application                        ║
╚══════════════════════════════════════════════════════════════╝
"""


def print_banner():
    print(BANNER)


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def run_indexing(pipeline: RAGPipeline, docs_dir: str = "documents") -> None:
    """
    Discover and index all .txt and .md files in the documents directory.

    Args:
        pipeline (RAGPipeline): Initialized RAG pipeline.
        docs_dir (str): Path to the documents directory.
    """
    # Scan for all supported file types
    extensions = ["*.txt", "*.md", "*.pdf", "*.docx", "*.csv", "*.json", "*.html", "*.htm"]
    all_files = []
    for pattern in extensions:
        all_files.extend(glob.glob(os.path.join(docs_dir, pattern)))

    if not all_files:
        print(f"[!] No .txt or .md files found in '{docs_dir}/'")
        print(f"    Add documents to the '{docs_dir}/' folder and re-run.")
        sys.exit(1)

    print(f"\n[+] Found {len(all_files)} document(s) to index:")
    for f in all_files:
        print(f"    - {f}")

    print("\n[~] Indexing documents... (this may take a moment)")
    count = pipeline.index_documents(file_paths=all_files)
    print(f"\n[✓] Indexing complete! {count} vectors stored in Pinecone.\n")


# ---------------------------------------------------------------------------
# Single Query
# ---------------------------------------------------------------------------

def run_query(
    pipeline: RAGPipeline,
    question: str,
    stream: bool = False,
    show_sources: bool = False,
) -> None:
    """
    Execute a single RAG query and print the result.

    Args:
        pipeline (RAGPipeline): Initialized RAG pipeline.
        question (str): User question string.
        stream (bool): If True, stream the response token-by-token.
        show_sources (bool): If True, print retrieved source documents.
    """
    print(f"\n[?] Question: {question}\n")
    print("[~] Retrieving context and generating answer...\n")
    print("─" * 60)

    result = pipeline.query(
        question=question,
        stream=stream,
        return_sources=show_sources,
    )

    print("[Answer]")

    if stream:
        # Stream mode: print tokens as they arrive
        for token in result["answer"]:
            print(token, end="", flush=True)
        print()  # newline after streamed output
    else:
        print(result["answer"])

    print("─" * 60)

    # Print similarity scores
    if result.get("scores"):
        print(f"\n[i] Retrieval scores: {result['scores']}")

    # Print hit rate
    if result.get("hit_rate"):
        print_hit_rate(result["hit_rate"], result.get("scores", []))

    # Print sources if requested
    if show_sources and result.get("sources"):
        print("\n[Sources]")
        for i, src in enumerate(result["sources"], 1):
            print(f"\n  [{i}] File: {src['source']} | Chunk: {src['chunk_index']} | Score: {src['score']}")
            print(f"      Preview: {src['text'][:150]}...")

    print()


# ---------------------------------------------------------------------------
# Hit Rate Display
# ---------------------------------------------------------------------------

def print_hit_rate(hit_rate: dict, scores: list) -> None:
    """
    Pretty-print hit rate statistics for a retrieval query.

    A 'hit' is any retrieved chunk whose similarity score meets or
    exceeds the configured threshold (default: 0.5).

    Args:
        hit_rate (dict): Dict with keys 'hits', 'total', 'threshold', 'rate'.
        scores (list): Raw similarity scores for each retrieved chunk.
    """
    hits      = hit_rate.get("hits", 0)
    total     = hit_rate.get("total", 0)
    threshold = hit_rate.get("threshold", 0.5)
    rate      = hit_rate.get("rate", 0.0)

    # Build a mini bar: filled blocks = hits, empty = misses
    bar_width = total if total > 0 else 1
    filled    = "#" * hits
    empty     = "." * (total - hits)
    bar       = filled + empty

    pct = rate * 100

    print("\n+" + "-" * 59 + "+")
    print(f"|  [Hit Rate]  Threshold: score >= {threshold:<6}                        |")
    print(f"|  Result : {hits}/{total} chunks hit  [{bar:<{bar_width}}]  {pct:5.1f}%                |")

    # Per-chunk score line
    score_labels = []
    for i, s in enumerate(scores, 1):
        marker = "[Y]" if s >= threshold else "[N]"
        score_labels.append(f"  chunk-{i}: {s:.4f} {marker}")

    print("|  Scores :" + "                                                  |")
    for label in score_labels:
        print(f"|    {label:<55} |")

    print("+" + "-" * 59 + "+")


# ---------------------------------------------------------------------------
# Interactive Chat Mode
# ---------------------------------------------------------------------------

def run_chat(pipeline: RAGPipeline) -> None:
    """
    Start an interactive REPL loop for continuous Q&A with the RAG pipeline.

    Type 'exit' or 'quit' to stop. Type 'sources' before a question
    to include source attribution.

    Args:
        pipeline (RAGPipeline): Initialized RAG pipeline.
    """
    print("\n[Interactive Chat Mode]")
    print("Type your question and press Enter. Type 'exit' to quit.")
    print("Prefix your question with 'sources:' to see source documents.\n")
    print("─" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n[Goodbye!]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "bye"):
            print("[Goodbye!]")
            break

        show_sources = False
        question = user_input

        # Check for 'sources:' prefix
        if user_input.lower().startswith("sources:"):
            show_sources = True
            question = user_input[len("sources:"):].strip()

        if not question:
            print("[!] Please enter a valid question.")
            continue

        result = pipeline.query(
            question=question,
            stream=True,
            return_sources=show_sources,
        )

        print("\nAssistant: ", end="", flush=True)
        for token in result["answer"]:
            print(token, end="", flush=True)
        print()  # Newline after streamed output

        # Show hit rate after every answer
        if result.get("hit_rate"):
            print_hit_rate(result["hit_rate"], result.get("scores", []))

        if show_sources and result.get("sources"):
            print("\n[Sources]")
            for i, src in enumerate(result["sources"], 1):
                print(
                    f"  [{i}] {src['source']} | chunk {src['chunk_index']} "
                    f"| score {src['score']}"
                )


# ---------------------------------------------------------------------------
# Index Stats
# ---------------------------------------------------------------------------

def run_stats(pipeline: RAGPipeline) -> None:
    """
    Print Pinecone index statistics.

    Args:
        pipeline (RAGPipeline): Initialized RAG pipeline.
    """
    print("\n[Pinecone Index Statistics]")
    stats = pipeline.get_index_stats()
    print(f"  Total vectors : {stats.get('total_vector_count', 'N/A')}")
    print(f"  Dimension     : {stats.get('dimension', 'N/A')}")
    print(f"  Namespaces    : {stats.get('namespaces', {})}")
    print()


# ---------------------------------------------------------------------------
# Argument Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RAG Application — Pinecone + Groq + Sentence Transformers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Index documents from the 'documents/' folder into Pinecone.",
    )
    parser.add_argument(
        "--query",
        type=str,
        metavar="QUESTION",
        help="Ask a single question using the RAG pipeline.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream the LLM response token-by-token (use with --query or --chat).",
    )
    parser.add_argument(
        "--sources",
        action="store_true",
        help="Show source document excerpts alongside the answer.",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Start interactive chat mode for continuous Q&A.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Display Pinecone index statistics.",
    )
    parser.add_argument(
        "--docs-dir",
        type=str,
        default="documents",
        metavar="DIR",
        help="Directory containing documents to index (default: documents/).",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print_banner()
    parser = build_parser()
    args = parser.parse_args()

    # Show help if no arguments provided
    if not any([args.index, args.query, args.chat, args.stats]):
        parser.print_help()
        sys.exit(0)

    # Initialize pipeline
    print("[~] Initializing RAG pipeline...")
    try:
        pipeline = RAGPipeline()
        print("[✓] Pipeline initialized successfully.\n")
    except ValueError as e:
        print(f"[✗] Configuration error: {e}")
        sys.exit(1)

    # Route to appropriate action
    if args.index:
        run_indexing(pipeline, docs_dir=args.docs_dir)

    if args.query:
        run_query(
            pipeline,
            question=args.query,
            stream=args.stream,
            show_sources=args.sources,
        )

    if args.chat:
        run_chat(pipeline)

    if args.stats:
        run_stats(pipeline)


if __name__ == "__main__":
    main()
