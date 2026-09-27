"""
Database CRUD operations for Customers, Orders, and Support Tickets.
"""
from typing import List, Optional, Any
from datetime import datetime
import uuid
from sqlalchemy.orm import Session, joinedload
from database.models import Customer, Order, OrderItem, SupportTicket, TicketEscalationEvent
from database.schemas import CustomerCreate, OrderCreate, TicketCreate, TicketUpdate


# ── Customer Operations ───────────────────────────────────────────────────────

def get_customer(db: Session, customer_id: str) -> Optional[Customer]:
    return db.query(Customer).filter(Customer.id == customer_id).first()


def get_customers(db: Session, skip: int = 0, limit: int = 100) -> List[Customer]:
    return db.query(Customer).order_by(Customer.id.asc()).offset(skip).limit(limit).all()


def create_customer(db: Session, customer: CustomerCreate) -> Customer:
    db_customer = Customer(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        tier=customer.tier,
        account_status=customer.account_status,
        preferred_contact=customer.preferred_contact,
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


# ── Order Operations ──────────────────────────────────────────────────────────

def get_order(db: Session, order_id: str) -> Optional[Order]:
    return (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )


def get_orders(db: Session, customer_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Order]:
    query = db.query(Order).options(joinedload(Order.items))
    if customer_id:
        query = query.filter(Order.customer_id == customer_id)
    return query.order_by(Order.order_date.desc()).offset(skip).limit(limit).all()


def create_order(db: Session, order: OrderCreate) -> Order:
    # ── Auto-generate Order ID in ORD-NNNN format if not provided ──────────────
    if not order.id or not order.id.strip():
        # Find the highest existing ORD-NNNN number and increment
        existing = db.query(Order.id).filter(Order.id.like("ORD-%")).all()
        max_num = 1000
        for (oid,) in existing:
            try:
                num = int(oid.replace("ORD-", ""))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
        generated_id = f"ORD-{max_num + 1}"
    else:
        generated_id = order.id.strip().upper()

    db_order = Order(
        id=generated_id,
        customer_id=order.customer_id,
        status=order.status,
        carrier=order.carrier,
        tracking_number=order.tracking_number,
        order_total=order.order_total,
        shipping_address=order.shipping_address,
    )
    db.add(db_order)
    db.flush()

    for item in order.items:
        db_item = OrderItem(
            order_id=generated_id,
            product_name=item.product_name,
            sku=item.sku,
            quantity=item.quantity,
            unit_price=item.unit_price,
            item_condition=item.item_condition,
        )
        db.add(db_item)

    db.commit()
    db.refresh(db_order)
    return db_order


# ── Ticket Operations ─────────────────────────────────────────────────────────

def get_ticket(db: Session, ticket_id: str) -> Optional[SupportTicket]:
    return (
        db.query(SupportTicket)
        .options(joinedload(SupportTicket.customer), joinedload(SupportTicket.order))
        .filter(SupportTicket.id == ticket_id)
        .first()
    )


def get_tickets(
    db: Session,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[SupportTicket]:
    query = (
        db.query(SupportTicket)
        .options(joinedload(SupportTicket.customer), joinedload(SupportTicket.order))
    )
    if customer_id:
        query = query.filter(SupportTicket.customer_id == customer_id)
    if status:
        query = query.filter(SupportTicket.status == status)
    return query.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit).all()


def create_ticket(db: Session, ticket: TicketCreate) -> SupportTicket:
    tid = ticket.id.strip() if ticket.id and ticket.id.strip() else f"TCK-{uuid.uuid4().hex[:6].upper()}"
    db_ticket = SupportTicket(
        id=tid,
        customer_id=ticket.customer_id,
        order_id=ticket.order_id,
        subject=ticket.subject,
        description=ticket.description,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


def update_ticket(db: Session, ticket_id: str, updates: TicketUpdate) -> Optional[SupportTicket]:
    db_ticket = get_ticket(db, ticket_id)
    if not db_ticket:
        return None
    if updates.status is not None:
        db_ticket.status = updates.status
    if updates.priority is not None:
        db_ticket.priority = updates.priority
    if updates.resolution_notes is not None:
        db_ticket.resolution_notes = updates.resolution_notes
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


# ── Escalation History Operations ─────────────────────────────────────────────

def get_escalation_history(db: Session, ticket_id: str) -> List[TicketEscalationEvent]:
    """Retrieve full chronological escalation history for a ticket."""
    return (
        db.query(TicketEscalationEvent)
        .filter(TicketEscalationEvent.ticket_id == ticket_id)
        .order_by(TicketEscalationEvent.timestamp.asc())
        .all()
    )


def create_escalation_event(
    db: Session,
    ticket_id: str,
    actor: str,
    action: str,
    note: str,
    timestamp: Optional[Any] = None,
) -> TicketEscalationEvent:
    """Create a new chronological audit event for a ticket."""
    event = TicketEscalationEvent(
        ticket_id=ticket_id,
        actor=actor,
        action=action,
        note=note,
        timestamp=timestamp or datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

