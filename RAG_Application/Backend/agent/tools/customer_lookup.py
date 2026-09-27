"""
Customer Lookup Tool
====================
Returns customer profile data (tier, order count, account status) for a given customer_id.

In production, replace CUSTOMER_DB with a real CRM / database API call.
The agent uses this to personalise answers and handle escalation logic
(e.g., premium customers get priority escalation paths).

MITIGATION — Argument Validation (2026-09-14)
----------------------------------------------
All customer_id values are validated before the CRM lookup:
  1. Format check: must match ^C\d{3}$ (e.g. C001, C099).
  2. Existence check: must be in CUSTOMER_DB.
Fabricated / invented IDs (e.g. 'CUST-UNKNOWN', 'VIP-ESCALATE') are rejected
with a structured error response that forces the agent to replan using the
correct ID supplied in the user's message or context.
"""
from __future__ import annotations

import logging
import re

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Compiled once — format: C followed by exactly 3 digits (C001 … C999)
_VALID_CID_RE = re.compile(r"^C\d{3}$")

# ---------------------------------------------------------------------------
# Mock CRM data — replace with real DB/API call in production
# ---------------------------------------------------------------------------

CUSTOMER_DB: dict = {
    "C001": {
        "customer_id": "C001",
        "name": "Alice Johnson",
        "tier": "basic",
        "active_orders": 1,
        "total_orders": 3,
        "account_status": "active",
        "preferred_contact": "email",
        "open_tickets": 0,
    },
    "C002": {
        "customer_id": "C002",
        "name": "Bob Smith",
        "tier": "premium",
        "active_orders": 2,
        "total_orders": 15,
        "account_status": "active",
        "preferred_contact": "phone",
        "open_tickets": 1,
    },
    "C003": {
        "customer_id": "C003",
        "name": "Carol White",
        "tier": "premium",
        "active_orders": 0,
        "total_orders": 28,
        "account_status": "active",
        "preferred_contact": "email",
        "open_tickets": 0,
    },
    "C004": {
        "customer_id": "C004",
        "name": "David Lee",
        "tier": "basic",
        "active_orders": 1,
        "total_orders": 1,
        "account_status": "suspended",
        "preferred_contact": "email",
        "open_tickets": 2,
    },
    "C005": {
        "customer_id": "C005",
        "name": "Eva Martinez",
        "tier": "vip",
        "active_orders": 3,
        "total_orders": 52,
        "account_status": "active",
        "preferred_contact": "dedicated_rep",
        "open_tickets": 0,
    },
}

# ---------------------------------------------------------------------------
# Escalation rules based on tier — used by agent to decide escalation path
# ---------------------------------------------------------------------------

ESCALATION_POLICY: dict = {
    "basic":   {"priority": "standard", "sla_hours": 48, "channel": "email"},
    "premium": {"priority": "high",     "sla_hours": 12, "channel": "phone_or_email"},
    "vip":     {"priority": "critical", "sla_hours": 2,  "channel": "dedicated_rep"},
}


def make_customer_lookup_tool():
    @tool
    def customer_lookup(customer_id: str) -> dict:
        """
        Look up a customer's profile, tier, and account status.
        Use this BEFORE rag_retrieval when:
        - The question involves escalation or priority handling
        - The question mentions a specific order problem or account issue
        - You need to know if this is a premium/VIP customer for personalised response
        Returns: customer tier, active orders, account status, escalation policy.

        IMPORTANT — customer_id format:
          - Must be exactly 'C' followed by 3 digits, e.g. C001, C002, C005.
          - Do NOT invent or guess IDs. Extract the real ID from the user's message.
          - If the user did not provide an ID, ask them for it before calling this tool.
        """
        cid = customer_id.strip().upper()

        # ── MITIGATION: Argument Validation ───────────────────────────────
        # 1. Format check
        if not _VALID_CID_RE.match(cid):
            logger.warning(
                "customer_lookup rejected fabricated ID: %r (format ^C\\d{3}$ required)", cid
            )
            return {
                "found": False,
                "error": "INVALID_ID_FORMAT",
                "customer_id": cid,
                "message": (
                    f"'{cid}' is not a valid customer ID format. "
                    "Customer IDs must match the pattern C001–C999. "
                    "Please extract the correct ID from the customer's message and retry."
                ),
                "tier": None,
                "escalation": None,
            }

        # 2. Existence check — First attempt SQL database lookup, fallback to CUSTOMER_DB
        profile = None
        try:
            from database.session import get_db_session
            from database.crud import get_customer
            db = get_db_session()
            db_cust = get_customer(db, cid)
            if db_cust:
                profile = db_cust.to_dict()
            db.close()
        except Exception as db_err:
            logger.debug("Database customer lookup fallback due to: %s", db_err)

        if not profile:
            profile = CUSTOMER_DB.get(cid)

        if not profile:
            logger.info("customer_lookup: ID %s not in CRM — treating as basic tier.", cid)
            return {
                "found": False,
                "error": "NOT_FOUND",
                "customer_id": cid,
                "message": "Customer not found in system. Treat as basic tier.",
                "tier": "basic",
                "escalation": ESCALATION_POLICY["basic"],
            }
        # ─────────────────────────────────────────────────────────────────

        tier = profile.get("tier", "basic")
        return {
            "found": True,
            "customer_id": cid,
            "name": profile.get("name", "Valued Customer"),
            "tier": tier,
            "account_status": profile.get("account_status", "active"),
            "active_orders": profile.get("active_orders", 0),
            "total_orders": profile.get("total_orders", 0),
            "preferred_contact": profile.get("preferred_contact", "email"),
            "open_tickets": profile.get("open_tickets", 0),
            "escalation_policy": ESCALATION_POLICY.get(tier, ESCALATION_POLICY["basic"]),
        }

    return customer_lookup
