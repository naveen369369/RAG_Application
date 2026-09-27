"""
SQLAlchemy Data Models for Support CRM
======================================
Defines Customers, Orders, Order Items, and Support Tickets.
Fully compatible with Microsoft SQL Server (T-SQL) and SQLite.
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from database.session import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(32), primary_key=True, index=True)  # e.g. "C001"
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    tier = Column(String(20), default="basic", nullable=False)  # basic | premium | vip
    account_status = Column(String(30), default="active", nullable=False)  # active | suspended
    preferred_contact = Column(String(30), default="email")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    tickets = relationship("SupportTicket", back_populates="customer", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "tier": self.tier,
            "account_status": self.account_status,
            "preferred_contact": self.preferred_contact,
            "active_orders": sum(1 for o in self.orders if o.status in ("processing", "shipped")),
            "total_orders": len(self.orders),
            "open_tickets": sum(1 for t in self.tickets if t.status not in ("resolved", "closed")),
        }


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(32), primary_key=True, index=True)  # e.g. "ORD-1001"
    customer_id = Column(String(32), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), default="processing", nullable=False)  # processing | shipped | delivered | cancelled | returned
    carrier = Column(String(50), nullable=True)  # FedEx | UPS | DHL | USPS
    tracking_number = Column(String(100), nullable=True, index=True)
    order_total = Column(Float, default=0.0)
    shipping_address = Column(String(255), nullable=True)
    order_date = Column(DateTime, default=datetime.utcnow)
    delivered_date = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    tickets = relationship("SupportTicket", back_populates="order")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.id,
            "customer_id": self.customer_id,
            "status": self.status,
            "carrier": self.carrier,
            "tracking_number": self.tracking_number,
            "order_total": self.order_total,
            "shipping_address": self.shipping_address,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "delivered_date": self.delivered_date.isoformat() if self.delivered_date else None,
            "items": [item.to_dict() for item in self.items],
        }


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(32), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_name = Column(String(150), nullable=False)
    sku = Column(String(50), nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    item_condition = Column(String(30), default="unopened")  # unopened | opened | damaged | missing

    # Relationships
    order = relationship("Order", back_populates="items")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_name": self.product_name,
            "sku": self.sku,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "item_condition": self.item_condition,
        }


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(String(32), primary_key=True, index=True)  # e.g. "TCK-1001" or "T01"
    customer_id = Column(String(32), ForeignKey("customers.id", ondelete="NO ACTION"), nullable=False, index=True)
    order_id = Column(String(32), ForeignKey("orders.id", ondelete="NO ACTION"), nullable=True, index=True)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), default="general")  # shipping | return_refund | billing | technical | account
    priority = Column(String(20), default="standard")  # low | standard | high | urgent
    status = Column(String(30), default="open")  # open | in_progress | escalated | waiting_customer | resolved | closed
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="tickets")
    order = relationship("Order", back_populates="tickets")
    escalation_events = relationship(
        "TicketEscalationEvent",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketEscalationEvent.timestamp",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "customer_tier": self.customer.tier if self.customer else "basic",
            "order_id": self.order_id,
            "subject": self.subject,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "escalation_events": [e.to_dict() for e in self.escalation_events] if self.escalation_events else [],
        }


class TicketEscalationEvent(Base):
    __tablename__ = "ticket_escalation_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(32), ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    actor = Column(String(100), nullable=False)   # e.g. L1-Agent-Sarah, L2-Supervisor-Marcus, billing-bot, system
    action = Column(String(50), nullable=False)   # e.g. opened, escalated, approved_override, resolved
    note = Column(Text, nullable=False)

    # Relationships
    ticket = relationship("SupportTicket", back_populates="escalation_events")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "actor": self.actor,
            "action": self.action,
            "note": self.note,
        }

