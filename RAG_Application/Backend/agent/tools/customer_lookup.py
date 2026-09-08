"""
Customer Lookup Tool
====================
Returns customer profile data (tier, order count, account status) for a given customer_id.

In production, replace CUSTOMER_DB with a real CRM / database API call.
The agent uses this to personalise answers and handle escalation logic
(e.g., premium customers get priority escalation paths).
"""
from __future__ import annotations

from langchain_core.tools import tool

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
        """
        cid = customer_id.strip().upper()
        profile = CUSTOMER_DB.get(cid)

        if not profile:
            return {
                "found": False,
                "customer_id": cid,
                "message": "Customer not found in system. Treat as basic tier.",
                "tier": "basic",
                "escalation": ESCALATION_POLICY["basic"],
            }

        tier = profile.get("tier", "basic")
        return {
            "found": True,
            "customer_id": cid,
            "name": profile["name"],
            "tier": tier,
            "account_status": profile["account_status"],
            "active_orders": profile["active_orders"],
            "total_orders": profile["total_orders"],
            "preferred_contact": profile["preferred_contact"],
            "open_tickets": profile["open_tickets"],
            "escalation_policy": ESCALATION_POLICY.get(tier, ESCALATION_POLICY["basic"]),
        }

    return customer_lookup
