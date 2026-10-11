"""
Ticket and Order Lookup Tools for ReAct Agent
==============================================
Provides real-time SQL database lookup for tickets, orders, and item conditions.
"""
from __future__ import annotations

import logging
import re
from langchain_core.tools import tool
from database.session import get_db_session
from database.crud import get_ticket, get_order, get_tickets, get_orders

logger = logging.getLogger(__name__)

# Normalize ticket IDs (e.g. TCK-1001, T01, etc.)
_TICKET_ID_RE = re.compile(r"^[A-Za-z0-9\-_]+$")


def make_ticket_lookup_tool():
    @tool
    def ticket_lookup(ticket_id: str) -> dict:
        """
        Look up real-time support ticket details from the SQL database.
        Use this tool whenever:
        - The user mentions a ticket ID (e.g., TCK-1001, T01, TCK-XXX)
        - You need to know the subject, description, current status, priority, or linked order of a ticket.
        Returns: ticket status, priority, description, category, customer tier, and linked order ID.
        """
        tid = ticket_id.strip().upper()
        if not _TICKET_ID_RE.match(tid):
            return {
                "found": False,
                "error": "INVALID_TICKET_ID_FORMAT",
                "message": f"'{tid}' is not a valid ticket ID format. Please check the ticket number.",
            }

        db = get_db_session()
        try:
            ticket = get_ticket(db, tid)
            if not ticket:
                return {
                    "found": False,
                    "error": "TICKET_NOT_FOUND",
                    "ticket_id": tid,
                    "message": f"Ticket #{tid} was not found in the database. Please verify the ticket ID.",
                }

            order_info = None
            if ticket.order:
                order_info = {
                    "order_id": ticket.order.id,
                    "status": ticket.order.status,
                    "carrier": ticket.order.carrier,
                    "tracking_number": ticket.order.tracking_number,
                    "order_total": ticket.order.order_total,
                    "items": [
                        {
                            "product": it.product_name,
                            "quantity": it.quantity,
                            "condition": it.item_condition,
                        }
                        for it in ticket.order.items
                    ],
                }

            return {
                "found": True,
                "ticket_id": ticket.id,
                "customer_id": ticket.customer_id,
                "customer_name": ticket.customer.name if ticket.customer else "Unknown",
                "customer_tier": ticket.customer.tier if ticket.customer else "basic",
                "subject": ticket.subject,
                "description": ticket.description,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "resolution_notes": ticket.resolution_notes,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "linked_order": order_info,
            }
        except Exception as exc:
            logger.error("Error in ticket_lookup for %s: %s", tid, exc)
            return {"found": False, "error": "DB_ERROR", "message": str(exc)}
        finally:
            db.close()

    return ticket_lookup


def make_order_lookup_tool():
    @tool
    def order_lookup(order_id: str) -> dict:
        """
        Look up real-time customer order details and shipment status from the SQL database.
        Use this tool whenever:
        - The user mentions an order ID (e.g., ORD-1001, order #1002)
        - You need to know order status (processing, shipped, delivered), carrier, tracking number, or purchased items.
        - You need to check item condition (unopened, opened, damaged, missing) for refund or exchange eligibility.
        """
        # Normalize order_id e.g. '#ORD-1001' or 'ORD-1001'
        clean_oid = order_id.strip().upper().replace("#", "")

        db = get_db_session()
        try:
            order = get_order(db, clean_oid)
            if not order:
                return {
                    "found": False,
                    "error": "ORDER_NOT_FOUND",
                    "order_id": clean_oid,
                    "message": f"Order #{clean_oid} was not found in the database. Please verify the order number.",
                }

            return {
                "found": True,
                "order_id": order.id,
                "customer_id": order.customer_id,
                "customer_name": order.customer.name if order.customer else "Unknown",
                "status": order.status,
                "carrier": order.carrier,
                "tracking_number": order.tracking_number,
                "order_total": order.order_total,
                "shipping_address": order.shipping_address,
                "order_date": order.order_date.isoformat() if order.order_date else None,
                "delivered_date": order.delivered_date.isoformat() if order.delivered_date else None,
                "items": [
                    {
                        "product_name": it.product_name,
                        "sku": it.sku,
                        "quantity": it.quantity,
                        "unit_price": it.unit_price,
                        "item_condition": it.item_condition,
                    }
                    for it in order.items
                ],
            }
        except Exception as exc:
            logger.error("Error in order_lookup for %s: %s", clean_oid, exc)
            return {"found": False, "error": "DB_ERROR", "message": str(exc)}
        finally:
            db.close()

    return order_lookup


def make_list_tickets_and_orders_tool():
    @tool
    def list_tickets_and_orders(resource_type: str = "all", limit: int = 50) -> dict:
        """
        Retrieve all support tickets, all customer orders, or both from the CRM SQL database.
        Use this tool whenever:
        - The user asks to 'list all tickets', 'show all tickets', or view support tickets without a ticket ID.
        - The user asks to 'list all orders', 'show all orders', or view customer orders without an order ID.
        - The user asks to 'list out the all the ticket and orders' or inspect all database records.
        - You need an overview of what tickets and orders currently exist in the database.

        Args:
            resource_type: 'all' (retrieves both tickets and orders), 'tickets' (only tickets), or 'orders' (only orders). Defaults to 'all'.
            limit: Maximum number of records to retrieve per category (default 50).

        Returns:
            A dict containing:
              - 'found': True if records exist
              - 'tickets': list of tickets with id, customer, subject, status, priority, category, linked order
              - 'orders': list of orders with id, customer, status, carrier, tracking number, items, total
              - 'summary': high-level count of records retrieved
        """
        r_type = (resource_type or "all").strip().lower()
        include_tickets = "ticket" in r_type or r_type in ("all", "both", "")
        include_orders = "order" in r_type or r_type in ("all", "both", "")

        db = get_db_session()
        try:
            result = {"found": True}
            tickets_data = []
            orders_data = []

            if include_tickets:
                raw_tickets = get_tickets(db, limit=limit)
                for t in raw_tickets:
                    tickets_data.append({
                        "ticket_id": t.id,
                        "customer_id": t.customer_id,
                        "customer_name": t.customer.name if t.customer else "Unknown",
                        "customer_tier": t.customer.tier if t.customer else "basic",
                        "subject": t.subject,
                        "status": t.status,
                        "priority": t.priority,
                        "category": t.category,
                        "linked_order_id": t.order_id,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "resolution_notes": t.resolution_notes,
                    })
                result["tickets"] = tickets_data
                result["total_tickets"] = len(tickets_data)

            if include_orders:
                raw_orders = get_orders(db, limit=limit)
                for o in raw_orders:
                    orders_data.append({
                        "order_id": o.id,
                        "customer_id": o.customer_id,
                        "customer_name": o.customer.name if o.customer else "Unknown",
                        "status": o.status,
                        "carrier": o.carrier,
                        "tracking_number": o.tracking_number,
                        "order_total": o.order_total,
                        "order_date": o.order_date.isoformat() if o.order_date else None,
                        "delivered_date": o.delivered_date.isoformat() if o.delivered_date else None,
                        "items": [
                            {
                                "product_name": it.product_name,
                                "quantity": it.quantity,
                                "unit_price": it.unit_price,
                                "item_condition": it.item_condition,
                            }
                            for it in o.items
                        ],
                    })
                result["orders"] = orders_data
                result["total_orders"] = len(orders_data)

            summary_parts = []
            if include_tickets:
                summary_parts.append(f"{len(tickets_data)} tickets")
            if include_orders:
                summary_parts.append(f"{len(orders_data)} orders")
            result["summary"] = f"Retrieved {' and '.join(summary_parts)} from database."

            return result
        except Exception as exc:
            logger.error("Error in list_tickets_and_orders: %s", exc)
            return {"found": False, "error": "DB_ERROR", "message": str(exc)}
        finally:
            db.close()

    return list_tickets_and_orders

