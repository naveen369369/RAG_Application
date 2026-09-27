"""
Pydantic Request & Response Schemas for Support CRM API
"""
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Customer Schemas ──────────────────────────────────────────────────────────

class CustomerBase(BaseModel):
    id: str = Field(..., description="Customer ID, e.g. C001")
    name: str
    email: str
    phone: Optional[str] = None
    tier: str = Field(default="basic", description="basic, premium, vip")
    account_status: str = Field(default="active", description="active, suspended")
    preferred_contact: str = Field(default="email")


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    active_orders: int = 0
    total_orders: int = 0
    open_tickets: int = 0

    class Config:
        from_attributes = True


# ── Order Item Schemas ────────────────────────────────────────────────────────

class OrderItemBase(BaseModel):
    product_name: str
    sku: Optional[str] = None
    quantity: int = 1
    unit_price: float = 0.0
    item_condition: str = Field(default="unopened", description="unopened, opened, damaged, missing")


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: str

    class Config:
        from_attributes = True


# ── Order Schemas ─────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    id: Optional[str] = Field(None, description="Order ID, e.g. ORD-1001. Auto-generated if omitted.")
    customer_id: str
    status: str = Field(default="processing", description="processing, shipped, delivered, cancelled, returned")
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    order_total: float = 0.0
    shipping_address: Optional[str] = None
    items: List[OrderItemCreate] = []


class OrderResponse(BaseModel):
    order_id: str
    customer_id: str
    status: str
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    order_total: float = 0.0
    shipping_address: Optional[str] = None
    order_date: Optional[str] = None
    delivered_date: Optional[str] = None
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


# ── Ticket Schemas ────────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    id: Optional[str] = Field(None, description="Optional custom Ticket ID, e.g. TCK-1001. Auto-generated if omitted.")
    customer_id: str
    order_id: Optional[str] = None
    subject: str
    description: str
    category: str = Field(default="general", description="shipping, return_refund, billing, technical, account")
    priority: str = Field(default="standard", description="low, standard, high, urgent")
    status: str = Field(default="open", description="open, in_progress, escalated, waiting_customer, resolved, closed")


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    resolution_notes: Optional[str] = None


class TicketResponse(BaseModel):
    ticket_id: str
    customer_id: str
    customer_name: Optional[str] = None
    customer_tier: str = "basic"
    order_id: Optional[str] = None
    subject: str
    description: str
    category: str
    priority: str
    status: str
    resolution_notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
