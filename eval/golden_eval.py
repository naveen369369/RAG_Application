"""
Golden Evaluation — Hit Rate @ 3
=================================
Evaluates the RAG retriever against 12 hardcoded golden Q&A pairs.

Workflow:
  1. /golden/discover  — embeds each golden *answer*, queries Pinecone, stores
                         the best-matching chunk_id per question.
  2. /golden/evaluate  — embeds each golden *question*, queries Pinecone top-3,
                         checks whether the stored correct chunk_id appears.
                         Reports X/12 hit rate.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

MAP_PATH = Path(__file__).parent / "golden_chunk_map.json"

# ---------------------------------------------------------------------------
# 12 Golden Q&A pairs — question, answer, and expected Pinecone namespace
# ---------------------------------------------------------------------------

GOLDEN_QA: List[Dict[str, str]] = [
    {
        "id": "Q1",
        "question": "What should I do if my account gets locked after multiple failed login attempts?",
        "answer": (
            "If your account is locked due to 5 failed login attempts, you have two options: "
            "wait 30 minutes for the lockout to lift automatically, or use the Forgot Password "
            "link on the login page to reset your credentials immediately. After clicking "
            "Forgot Password, enter your registered email address, check your inbox for the "
            "reset link (also check Spam/Promotions), and use the link within 60 minutes to "
            "set a new password. Your new password must be 8-20 characters and include at "
            "least one uppercase letter, one number, and one special character."
        ),
        "namespace": "Account Management & Login Issues",
    },
    {
        "id": "Q2",
        "question": "What is the difference between account deactivation and permanent account deletion?",
        "answer": (
            "Deactivation hides your account while retaining all your data for 90 days, and "
            "you can reactivate simply by logging back in during that period. Permanent deletion "
            "removes all your data after a 30-day grace period and cannot be undone once that "
            "window passes. If you are unsure, choose deactivation first — it gives you time to "
            "reconsider without losing your account history, orders, or settings."
        ),
        "namespace": "Account Management & Login Issues",
    },
    {
        "id": "Q3",
        "question": "Why do I see two charges on my bank statement for the same order?",
        "answer": (
            "Two charges on the same date are typically the result of a temporary bank "
            "authorization hold appearing alongside the actual charge once the order is "
            "confirmed. The authorization hold clears automatically within 3-5 business days "
            "and is not a real deduction. If both charges remain after 5 business days, contact "
            "your bank first to confirm; if both are actual debits, contact our billing support "
            "team via Live Chat with your order number and transaction IDs."
        ),
        "namespace": "Billing & Payment Support",
    },
    {
        "id": "Q4",
        "question": "How long does a refund take to appear after it is approved?",
        "answer": (
            "Refund timelines depend on the original payment method. Credit and debit card "
            "refunds take 5-10 business days. PayPal refunds process in 1-3 business days. "
            "Bank transfer (ACH) refunds take 5-7 business days. Store credit is applied "
            "within 24 hours. You will receive an email confirmation the moment the refund "
            "is processed on our end."
        ),
        "namespace": "Billing & Payment Support",
    },
    {
        "id": "Q5",
        "question": "Can I return an electronic item that I have already opened?",
        "answer": (
            "Yes, opened electronics can be returned within 30 days, but only if the item is "
            "defective or not functioning as described. Non-defective opened electronics are "
            "reviewed on a case-by-case basis. To start the process, go to Orders > Order "
            "History, select the item, click Start Return, and choose the return reason — a "
            "support agent will review and confirm eligibility within 1 business day."
        ),
        "namespace": "Product Returns & Refund Policy",
    },
    {
        "id": "Q6",
        "question": "What happens if I receive a damaged item? Do I need to ship it back?",
        "answer": (
            "No return shipping is required for items verified as damaged on arrival. Document "
            "the damage by taking 3-5 clear photos of both the packaging and the product, then "
            "contact our support team within 48 hours of delivery via Live Chat or email. Our "
            "team will confirm the damage and offer you a replacement shipped within 2 business "
            "days or a full refund. You keep the damaged item — no return label is needed."
        ),
        "namespace": "Product Returns & Refund Policy",
    },
    {
        "id": "Q7",
        "question": "What does error code ERR-1001 mean and how do I fix it?",
        "answer": (
            "ERR-1001 means your authentication token has expired. The fix is straightforward: "
            "log out of your account completely, then log back in with your credentials. If you "
            "are using SSO, re-authorize the connected app. If you encounter ERR-1001 repeatedly "
            "even after fresh logins, clear your browser cookies and cache, then try again."
        ),
        "namespace": "Technical Troubleshooting Guide",
    },
    {
        "id": "Q8",
        "question": "My app keeps crashing on mobile. What steps should I follow to fix it?",
        "answer": (
            "Follow these steps in order: force-close the app and relaunch it, check for a "
            "pending app update, clear the app cache by going to Settings > Apps > Clear Cache, "
            "and if the crash continues, uninstall and reinstall the app. If the crash only "
            "happens on a specific screen, note the exact steps and report via the in-app "
            "feedback option."
        ),
        "namespace": "Technical Troubleshooting Guide",
    },
    {
        "id": "Q9",
        "question": "My tracking status shows Delivered but I never received my package. What should I do?",
        "answer": (
            "First, wait 24 hours — carriers sometimes mark packages as delivered up to one day "
            "before they actually arrive. Check with neighbors, your building's mailroom, or any "
            "secure package lockers, and look for a delivery notice. If the package still has not "
            "arrived after 24 hours, contact our support team with your order number and tracking "
            "number. We will open a carrier investigation within 1 business day and issue a "
            "replacement or full refund within 5 business days if lost."
        ),
        "namespace": "Shipping & Delivery Information",
    },
    {
        "id": "Q10",
        "question": "Can I change the delivery address on my order after it has been placed?",
        "answer": (
            "Address changes are possible only while your order is still in the processing stage, "
            "before a tracking number has been generated. Contact our Live Chat support team "
            "immediately with your order number and the correct delivery address. Once a tracking "
            "number is assigned and the package has been handed to the carrier, the address cannot "
            "be changed on our end — contact the carrier directly to request a package hold."
        ),
        "namespace": "Shipping & Delivery Information",
    },
    {
        "id": "Q11",
        "question": "How do I escalate my complaint to a senior agent or manager?",
        "answer": (
            "There are three ways to request an escalation. During a Live Chat or phone call, "
            "say I would like to escalate this to a senior agent. Via email, reply to your "
            "existing support ticket and include ESCALATION REQUEST in the subject line. Through "
            "the Help Center portal, navigate to My Cases > Open Case > Request Escalation. "
            "Once escalated, a Senior Agent will contact you within 4-8 business hours."
        ),
        "namespace": "Customer Escalation & Complaint Resolution",
    },
    {
        "id": "Q12",
        "question": "What are my options if the company's internal resolution does not satisfy my complaint?",
        "answer": (
            "If our internal resolution process does not meet your expectations after 30 days, "
            "you have several external options. In the US, you can file a complaint with the "
            "Better Business Bureau or initiate a chargeback through your credit card issuer. "
            "EU residents can escalate privacy-related concerns to their national Data Protection "
            "Authority under GDPR. Filing externally does not close your case with us."
        ),
        "namespace": "Customer Escalation & Complaint Resolution",
    },
]


def load_chunk_map() -> Dict[str, Any]:
    if not MAP_PATH.exists():
        return {}
    with open(MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_chunk_map(chunk_map: Dict[str, Any]) -> None:
    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(chunk_map, f, indent=2)


def discover_chunk_ids(pipeline) -> Dict[str, Any]:
    """
    Embed each golden *answer*, query Pinecone in the correct namespace,
    and store the top-1 matching chunk_id as the ground-truth for evaluation.
    """
    chunk_map = load_chunk_map()

    discovered = []
    for qa in GOLDEN_QA:
        qid = qa["id"]
        namespace = qa["namespace"]
        answer_text = qa["answer"]

        try:
            answer_emb = pipeline.embedding_model.embed_texts([answer_text])[0]
            matches = pipeline.vector_db.query(
                query_vector=answer_emb,
                top_k=1,
                namespace=namespace,
            )
            best_id = matches[0]["id"] if matches else None
        except Exception as exc:
            logger.warning(f"Discover failed for {qid}: {exc}")
            best_id = None

        chunk_map[qid] = {
            "question": qa["question"],
            "namespace": namespace,
            "correct_chunk_id": best_id,
        }
        discovered.append({
            "id": qid,
            "namespace": namespace,
            "correct_chunk_id": best_id,
        })
        logger.info(f"Discover {qid}: best chunk = {best_id} in {namespace}")

    save_chunk_map(chunk_map)
    return {"discovered": discovered, "map_path": str(MAP_PATH)}


def evaluate_hit_rate(pipeline, top_k: int = 3, use_reranker: bool = False) -> Dict[str, Any]:
    """
    For each of the 12 golden questions, embed the *question*, query Pinecone,
    optionally rerank, and check whether the stored correct_chunk_id appears in
    the top-{top_k} results.

    When use_reranker=True:
      - Retrieves 2×top_k candidates from Pinecone
      - Reranks with the cross-encoder
      - Checks whether correct_chunk_id is in the reranked top-{top_k}

    Returns cumulative hit rate and per-question breakdown.
    """
    chunk_map = load_chunk_map()
    candidate_k = top_k * 2 if use_reranker else top_k

    results = []
    hits = 0
    total = 0

    for qa in GOLDEN_QA:
        qid = qa["id"]
        mapping = chunk_map.get(qid, {})
        correct_chunk_id = mapping.get("correct_chunk_id")
        namespace = mapping.get("namespace", qa["namespace"])

        if not correct_chunk_id:
            results.append({
                "id": qid,
                "question": qa["question"],
                "namespace": namespace,
                "correct_chunk_id": None,
                "retrieved_ids": [],
                "is_hit": None,
                "note": "Run Discover first to map chunk IDs",
            })
            continue

        try:
            question_emb = pipeline.embedding_model.embed_texts([qa["question"]])[0]
            matches = pipeline.vector_db.query(
                query_vector=question_emb,
                top_k=candidate_k,
                namespace=namespace,
            )
            if use_reranker and matches:
                matches = pipeline.rerank(query=qa["question"], matches=matches, top_k=top_k)
            retrieved_ids = [m["id"] for m in matches]
        except Exception as exc:
            logger.warning(f"Evaluate failed for {qid}: {exc}")
            retrieved_ids = []

        is_hit = correct_chunk_id in retrieved_ids
        total += 1
        if is_hit:
            hits += 1

        results.append({
            "id": qid,
            "question": qa["question"],
            "namespace": namespace,
            "correct_chunk_id": correct_chunk_id,
            "retrieved_ids": retrieved_ids,
            "is_hit": is_hit,
        })

    rate = round(hits / total, 4) if total > 0 else 0.0
    return {
        "hits": hits,
        "total": total,
        "rate": rate,
        "rate_pct": round(rate * 100, 1),
        "top_k": top_k,
        "use_reranker": use_reranker,
        "results": results,
    }
