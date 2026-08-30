"""
Langfuse Dataset Creator — 25 Golden Q&A Pairs
===============================================
Creates a Langfuse Dataset named "rag-golden-eval-25" and uploads
all 25 golden question-answer pairs as Dataset Items.

Each item contains:
  - input:           {"question": str, "namespace": str}
  - expected_output: {"answer": str}
  - metadata:        {"id": str, "category": str, "difficulty": str}

Usage:
    python -m eval.create_langfuse_dataset

Requirements:
    - LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set in .env
    - pip install langfuse==2.60.10
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 25 Golden Q&A pairs across 6 namespaces (4-5 per namespace)
# ---------------------------------------------------------------------------

GOLDEN_QA_25 = [

    # ── Account Management & Login Issues (Q1–Q5) ───────────────────────────
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
        "difficulty": "medium",
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
        "difficulty": "medium",
    },
    {
        "id": "Q3",
        "question": "How do I change the email address associated with my account?",
        "answer": (
            "To change your registered email address, go to Account Settings > Personal Information "
            "and click Edit next to your email. Enter the new email address and save the change. "
            "A verification link will be sent to the new email — click it within 24 hours to confirm "
            "the update. Until you verify, your old email address remains active. If you no longer "
            "have access to your original email, contact our support team via Live Chat with proof "
            "of identity to update it manually."
        ),
        "namespace": "Account Management & Login Issues",
        "difficulty": "easy",
    },
    {
        "id": "Q4",
        "question": "Can I use the same email address to create multiple accounts?",
        "answer": (
            "No, each email address can only be linked to one account in our system. If you try "
            "to register with an email that already exists, you will see an error prompting you to "
            "log in or use the Forgot Password option instead. If you need a separate account for "
            "business purposes, you must use a different email address. Contact our support team "
            "if you need to merge two existing accounts."
        ),
        "namespace": "Account Management & Login Issues",
        "difficulty": "easy",
    },
    {
        "id": "Q5",
        "question": "How do I enable two-factor authentication on my account?",
        "answer": (
            "To enable two-factor authentication (2FA), go to Account Settings > Security and "
            "toggle on Two-Factor Authentication. You can choose between SMS OTP or an authenticator "
            "app (e.g., Google Authenticator or Authy). For the app method, scan the QR code shown "
            "on screen and enter the 6-digit code to confirm setup. Once enabled, you will be asked "
            "for a verification code at every login. Save your backup codes in a safe place — they "
            "are the only way to recover access if you lose your device."
        ),
        "namespace": "Account Management & Login Issues",
        "difficulty": "medium",
    },

    # ── Billing & Payment Support (Q6–Q10) ──────────────────────────────────
    {
        "id": "Q6",
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
        "difficulty": "medium",
    },
    {
        "id": "Q7",
        "question": "How long does a refund take to appear after it is approved?",
        "answer": (
            "Refund timelines depend on the original payment method. Credit and debit card "
            "refunds take 5-10 business days. PayPal refunds process in 1-3 business days. "
            "Bank transfer (ACH) refunds take 5-7 business days. Store credit is applied "
            "within 24 hours. You will receive an email confirmation the moment the refund "
            "is processed on our end."
        ),
        "namespace": "Billing & Payment Support",
        "difficulty": "easy",
    },
    {
        "id": "Q8",
        "question": "My payment failed at checkout but the amount was deducted from my account. What should I do?",
        "answer": (
            "A deduction despite a failed payment is usually a temporary authorization hold, "
            "not an actual charge — the funds are reserved by your bank but not transferred to us. "
            "This hold typically releases automatically within 3-5 business days. If the amount "
            "has not returned after 5 business days, share your bank statement and the failed "
            "order ID with our billing team via Live Chat. Do not attempt to place the same "
            "order again before the hold clears, as you may be charged twice."
        ),
        "namespace": "Billing & Payment Support",
        "difficulty": "hard",
    },
    {
        "id": "Q9",
        "question": "How do I update my saved payment method or add a new credit card?",
        "answer": (
            "Go to Account Settings > Payment Methods. To add a new card, click Add Payment Method "
            "and enter your card details — we accept Visa, Mastercard, American Express, and Discover. "
            "To update an existing card (e.g., new expiry date), select the card and click Edit. "
            "To remove a card, click Delete next to the payment method. For security, card numbers "
            "are never stored in full — only the last four digits are shown. Changes take effect "
            "immediately for future orders."
        ),
        "namespace": "Billing & Payment Support",
        "difficulty": "easy",
    },
    {
        "id": "Q10",
        "question": "Can I split a payment between two different payment methods?",
        "answer": (
            "Currently, our checkout supports only one primary payment method per order. However, "
            "you can use store credit in combination with a card — if your store credit balance "
            "covers part of the total, the remaining amount will be charged to your selected card. "
            "Splitting between two different credit or debit cards is not supported at this time. "
            "If you have a gift card, it can be applied at checkout in addition to your primary "
            "payment method by entering the gift card code in the designated field."
        ),
        "namespace": "Billing & Payment Support",
        "difficulty": "medium",
    },

    # ── Product Returns & Refund Policy (Q11–Q15) ───────────────────────────
    {
        "id": "Q11",
        "question": "Can I return an electronic item that I have already opened?",
        "answer": (
            "Yes, opened electronics can be returned within 30 days, but only if the item is "
            "defective or not functioning as described. Non-defective opened electronics are "
            "reviewed on a case-by-case basis. To start the process, go to Orders > Order "
            "History, select the item, click Start Return, and choose the return reason — a "
            "support agent will review and confirm eligibility within 1 business day."
        ),
        "namespace": "Product Returns & Refund Policy",
        "difficulty": "medium",
    },
    {
        "id": "Q12",
        "question": "What happens if I receive a damaged item? Do I need to ship it back?",
        "answer": (
            "No return shipping is required for items verified as damaged on arrival. Document "
            "the damage by taking 3-5 clear photos of both the packaging and the product, then "
            "contact our support team within 48 hours of delivery via Live Chat or email. Our "
            "team will confirm the damage and offer you a replacement shipped within 2 business "
            "days or a full refund. You keep the damaged item — no return label is needed."
        ),
        "namespace": "Product Returns & Refund Policy",
        "difficulty": "medium",
    },
    {
        "id": "Q13",
        "question": "What is the standard return window and are there any product categories excluded from returns?",
        "answer": (
            "The standard return window is 30 days from the delivery date for most products. "
            "However, certain categories are non-returnable: perishable goods, personalised or "
            "custom-made items, digital downloads once accessed, and hygiene products once opened "
            "(e.g., earbuds, underwear). Hazardous materials and items marked Final Sale at "
            "purchase are also excluded. If you are unsure whether your item qualifies, check "
            "the product page or contact support before initiating a return."
        ),
        "namespace": "Product Returns & Refund Policy",
        "difficulty": "hard",
    },
    {
        "id": "Q14",
        "question": "How do I generate a return shipping label?",
        "answer": (
            "To get a return shipping label, go to Orders > Order History, select the order, "
            "and click Start Return. Choose the item(s) you want to return and select your reason. "
            "On the next screen, click Generate Return Label — a pre-paid label will be emailed "
            "to you and also available to download from the portal. Print the label, attach it "
            "to your package, and drop it off at any authorised carrier location. Refunds are "
            "processed within 3-5 business days after the item is received at our warehouse."
        ),
        "namespace": "Product Returns & Refund Policy",
        "difficulty": "easy",
    },
    {
        "id": "Q15",
        "question": "Can I exchange an item instead of getting a refund?",
        "answer": (
            "Yes, exchanges are available for eligible items within the 30-day return window. "
            "To request an exchange, go to Orders > Order History, click Start Return, and select "
            "Exchange instead of Refund as your resolution. Choose the replacement item (same "
            "product, different size or colour where available). The replacement will be shipped "
            "once we receive and inspect the returned item. If the exchange item costs more, "
            "you will be charged the difference; if less, the difference is refunded as store credit."
        ),
        "namespace": "Product Returns & Refund Policy",
        "difficulty": "medium",
    },

    # ── Technical Troubleshooting Guide (Q16–Q19) ───────────────────────────
    {
        "id": "Q16",
        "question": "What does error code ERR-1001 mean and how do I fix it?",
        "answer": (
            "ERR-1001 means your authentication token has expired. The fix is straightforward: "
            "log out of your account completely, then log back in with your credentials. If you "
            "are using SSO, re-authorize the connected app. If you encounter ERR-1001 repeatedly "
            "even after fresh logins, clear your browser cookies and cache, then try again."
        ),
        "namespace": "Technical Troubleshooting Guide",
        "difficulty": "easy",
    },
    {
        "id": "Q17",
        "question": "My app keeps crashing on mobile. What steps should I follow to fix it?",
        "answer": (
            "Follow these steps in order: force-close the app and relaunch it, check for a "
            "pending app update, clear the app cache by going to Settings > Apps > Clear Cache, "
            "and if the crash continues, uninstall and reinstall the app. If the crash only "
            "happens on a specific screen, note the exact steps and report via the in-app "
            "feedback option."
        ),
        "namespace": "Technical Troubleshooting Guide",
        "difficulty": "medium",
    },
    {
        "id": "Q18",
        "question": "The website is not loading properly — images are broken and buttons are not working. What should I do?",
        "answer": (
            "Broken images and unresponsive buttons are typically caused by browser cache issues "
            "or a JavaScript error. Try these steps: hard-reload the page (Ctrl+Shift+R on Windows, "
            "Cmd+Shift+R on Mac), clear your browser cache and cookies, then reload. If the issue "
            "persists, try a different browser or disable browser extensions one by one. Check our "
            "status page at status.oursite.com to see if there is an ongoing outage. If only your "
            "account is affected, log out and back in to refresh your session."
        ),
        "namespace": "Technical Troubleshooting Guide",
        "difficulty": "medium",
    },
    {
        "id": "Q19",
        "question": "What does error code ERR-5003 mean and how can it be resolved?",
        "answer": (
            "ERR-5003 indicates a server-side timeout — our system did not receive a response "
            "from an internal service within the expected time. This is usually a temporary issue. "
            "Wait 2-3 minutes and try your request again. If the error persists beyond 15 minutes, "
            "check our status page for any active incidents. If you were in the middle of a "
            "checkout or form submission, do not resubmit immediately — check your order history "
            "first to confirm whether the action was processed before the timeout occurred."
        ),
        "namespace": "Technical Troubleshooting Guide",
        "difficulty": "hard",
    },

    # ── Shipping & Delivery Information (Q20–Q22) ───────────────────────────
    {
        "id": "Q20",
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
        "difficulty": "hard",
    },
    {
        "id": "Q21",
        "question": "Can I change the delivery address on my order after it has been placed?",
        "answer": (
            "Address changes are possible only while your order is still in the processing stage, "
            "before a tracking number has been generated. Contact our Live Chat support team "
            "immediately with your order number and the correct delivery address. Once a tracking "
            "number is assigned and the package has been handed to the carrier, the address cannot "
            "be changed on our end — contact the carrier directly to request a package hold."
        ),
        "namespace": "Shipping & Delivery Information",
        "difficulty": "medium",
    },
    {
        "id": "Q22",
        "question": "What are the available shipping options and how long does each take?",
        "answer": (
            "We offer three shipping tiers: Standard Shipping (5-7 business days, free on orders "
            "over $50), Express Shipping (2-3 business days, $9.99), and Overnight Shipping "
            "(next business day if ordered before 2 PM local time, $24.99). Delivery estimates "
            "begin from the dispatch date, not the order date — processing typically takes 1 "
            "business day. Remote areas and PO Boxes may have extended delivery times. "
            "International shipping availability and rates vary by destination country."
        ),
        "namespace": "Shipping & Delivery Information",
        "difficulty": "easy",
    },

    # ── Customer Escalation & Complaint Resolution (Q23–Q25) ────────────────
    {
        "id": "Q23",
        "question": "How do I escalate my complaint to a senior agent or manager?",
        "answer": (
            "There are three ways to request an escalation. During a Live Chat or phone call, "
            "say I would like to escalate this to a senior agent. Via email, reply to your "
            "existing support ticket and include ESCALATION REQUEST in the subject line. Through "
            "the Help Center portal, navigate to My Cases > Open Case > Request Escalation. "
            "Once escalated, a Senior Agent will contact you within 4-8 business hours."
        ),
        "namespace": "Customer Escalation & Complaint Resolution",
        "difficulty": "medium",
    },
    {
        "id": "Q24",
        "question": "What are my options if the company's internal resolution does not satisfy my complaint?",
        "answer": (
            "If our internal resolution process does not meet your expectations after 30 days, "
            "you have several external options. In the US, you can file a complaint with the "
            "Better Business Bureau or initiate a chargeback through your credit card issuer. "
            "EU residents can escalate privacy-related concerns to their national Data Protection "
            "Authority under GDPR. Filing externally does not close your case with us."
        ),
        "namespace": "Customer Escalation & Complaint Resolution",
        "difficulty": "hard",
    },
    {
        "id": "Q25",
        "question": "How long does the complaint resolution process typically take from start to finish?",
        "answer": (
            "The resolution timeline depends on the complexity of your complaint. Standard "
            "complaints (e.g., refund delays, incorrect charges) are resolved within 3-5 business "
            "days. Complex cases involving investigations (e.g., lost packages, fraud) may take "
            "up to 10 business days. Escalated cases handled by a Senior Agent are acknowledged "
            "within 4-8 hours and resolved within 5 business days. You will receive email updates "
            "at each stage, and you can track your case status at any time through the Help Center "
            "portal under My Cases."
        ),
        "namespace": "Customer Escalation & Complaint Resolution",
        "difficulty": "medium",
    },
]


# ---------------------------------------------------------------------------
# Dataset upload to Langfuse
# ---------------------------------------------------------------------------

DATASET_NAME = "rag-golden-eval-25"
DATASET_DESCRIPTION = (
    "25 golden Q&A pairs across 6 support namespaces used for "
    "reproducible RAG pipeline evaluation. Each item includes "
    "the expected answer and metadata (namespace, difficulty)."
)


def create_dataset():
    pub = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sec = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not pub or not sec or pub.startswith("your_") or sec.startswith("your_"):
        logger.error(
            "Langfuse keys not configured. "
            "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in your .env file."
        )
        sys.exit(1)

    try:
        from langfuse import Langfuse
    except ImportError:
        logger.error("langfuse not installed. Run: pip install langfuse==2.60.10")
        sys.exit(1)

    lf = Langfuse(public_key=pub, secret_key=sec, host=host)
    logger.info(f"Connected to Langfuse at {host}")

    # ── Create or get dataset ────────────────────────────────────────────────
    logger.info(f"Creating dataset: '{DATASET_NAME}'")
    dataset = lf.create_dataset(
        name=DATASET_NAME,
        description=DATASET_DESCRIPTION,
        metadata={
            "version": "1.0",
            "total_items": len(GOLDEN_QA_25),
            "namespaces": [
                "Account Management & Login Issues",
                "Billing & Payment Support",
                "Product Returns & Refund Policy",
                "Technical Troubleshooting Guide",
                "Shipping & Delivery Information",
                "Customer Escalation & Complaint Resolution",
            ],
        },
    )
    logger.info(f"Dataset created: {dataset.name}")

    # ── Upload each Q&A pair as a Dataset Item ───────────────────────────────
    success_count = 0
    for qa in GOLDEN_QA_25:
        try:
            lf.create_dataset_item(
                dataset_name=DATASET_NAME,
                input={
                    "question": qa["question"],
                    "namespace": qa["namespace"],
                },
                expected_output={
                    "answer": qa["answer"],
                },
                metadata={
                    "id": qa["id"],
                    "category": qa["namespace"],
                    "difficulty": qa["difficulty"],
                },
            )
            success_count += 1
            logger.info(f"  Uploaded {qa['id']}: {qa['question'][:60]}...")
        except Exception as exc:
            logger.error(f"  Failed to upload {qa['id']}: {exc}")

    lf.flush()
    logger.info(
        f"\n{'='*60}\n"
        f"  Dataset '{DATASET_NAME}' ready in Langfuse.\n"
        f"  Items uploaded: {success_count}/{len(GOLDEN_QA_25)}\n"
        f"  View at: {host}\n"
        f"{'='*60}"
    )
    return success_count


if __name__ == "__main__":
    create_dataset()
