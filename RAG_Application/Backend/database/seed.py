"""
Database Seeder
===============
Populates initial customer profiles, sample orders, and tickets on fresh start.
Matches existing C001-C005 profiles so existing workflows and race benchmarks work out of the box.
"""
import logging
from datetime import datetime, timedelta
from database.session import engine, SessionLocal, Base
from database.models import Customer, Order, OrderItem, SupportTicket, TicketEscalationEvent

logger = logging.getLogger(__name__)


def init_db():
    """Create all tables and seed default data if empty."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Customer).count() == 0:
            logger.info("Database is empty. Seeding initial customers, orders, and tickets...")
            seed_data(db)
            logger.info("Database seeding completed.")
        elif db.query(TicketEscalationEvent).count() == 0:
            logger.info("Seeding escalation events into ticket_escalation_events table...")
            seed_escalation_events(db)
            logger.info("Escalation events seeding completed.")
    except Exception as exc:
        logger.warning("Error during database initialization/seeding: %s", exc)
    finally:
        db.close()


def seed_data(db):
    # 1. Seed Customers
    customers = [
        Customer(
            id="C001",
            name="Alice Johnson",
            email="alice.johnson@example.com",
            phone="+1-555-0101",
            tier="basic",
            account_status="active",
            preferred_contact="email",
        ),
        Customer(
            id="C002",
            name="Bob Smith",
            email="bob.smith@example.com",
            phone="+1-555-0102",
            tier="premium",
            account_status="active",
            preferred_contact="phone",
        ),
        Customer(
            id="C003",
            name="Carol White",
            email="carol.white@example.com",
            phone="+1-555-0103",
            tier="premium",
            account_status="active",
            preferred_contact="email",
        ),
        Customer(
            id="C004",
            name="David Lee",
            email="david.lee@example.com",
            phone="+1-555-0104",
            tier="basic",
            account_status="suspended",
            preferred_contact="email",
        ),
        Customer(
            id="C005",
            name="Eva Martinez",
            email="eva.martinez@example.com",
            phone="+1-555-0105",
            tier="vip",
            account_status="active",
            preferred_contact="dedicated_rep",
        ),
    ]
    for c in customers:
        db.add(c)
    db.flush()

    # 2. Seed Sample Orders
    now = datetime.utcnow()
    orders = [
        Order(
            id="ORD-1001",
            customer_id="C001",
            status="delivered",
            carrier="FedEx",
            tracking_number="FDX-9982341",
            order_total=129.99,
            shipping_address="742 Evergreen Terrace, Springfield, OR",
            order_date=now - timedelta(days=10),
            delivered_date=now - timedelta(days=7),
        ),
        Order(
            id="ORD-1002",
            customer_id="C002",
            status="shipped",
            carrier="UPS",
            tracking_number="1Z9999999999999999",
            order_total=249.50,
            shipping_address="221B Baker St, London, UK",
            order_date=now - timedelta(days=3),
            delivered_date=None,
        ),
        Order(
            id="ORD-1003",
            customer_id="C003",
            status="delivered",
            carrier="DHL",
            tracking_number="DHL-55441209",
            order_total=89.00,
            shipping_address="100 Tech Blvd, Austin, TX",
            order_date=now - timedelta(days=5),
            delivered_date=now - timedelta(days=1),
        ),
        Order(
            id="ORD-1004",
            customer_id="C005",
            status="processing",
            carrier="FedEx",
            tracking_number="FDX-11223344",
            order_total=1450.00,
            shipping_address="1 Penthouse Way, Manhattan, NY",
            order_date=now - timedelta(hours=12),
            delivered_date=None,
        ),
    ]
    for o in orders:
        db.add(o)
    db.flush()

    # 3. Seed Order Items
    items = [
        OrderItem(order_id="ORD-1001", product_name="Wireless Noise-Cancelling Headphones", sku="TECH-WNC-01", quantity=1, unit_price=129.99, item_condition="opened"),
        OrderItem(order_id="ORD-1002", product_name="Mechanical Ergonomic Keyboard", sku="KEY-RGB-09", quantity=1, unit_price=149.50, item_condition="unopened"),
        OrderItem(order_id="ORD-1002", product_name="USB-C Dual 4K Docking Station", sku="DOCK-4K-02", quantity=1, unit_price=100.00, item_condition="unopened"),
        OrderItem(order_id="ORD-1003", product_name="Smart Water Bottle with Temperature Sensor", sku="BTL-TEMP-04", quantity=1, unit_price=89.00, item_condition="damaged"),
        OrderItem(order_id="ORD-1004", product_name="Ultra-Wide 49-inch Curved Gaming Monitor", sku="MON-49-CURV", quantity=1, unit_price=1450.00, item_condition="unopened"),
    ]
    for it in items:
        db.add(it)
    db.flush()

    # 4. Seed Support Tickets
    tickets = [
        SupportTicket(
            id="TCK-1001",
            customer_id="C001",
            order_id="ORD-1001",
            subject="Refund requested for opened headphones",
            description="I opened and tested the headphones, but they feel uncomfortable on my ears. Can I still return them for a refund?",
            category="return_refund",
            priority="standard",
            status="open",
        ),
        SupportTicket(
            id="TCK-1002",
            customer_id="C002",
            order_id="ORD-1002",
            subject="Address change request for in-transit package",
            description="I need to redirect my keyboard delivery to my office address because I will be traveling this week.",
            category="shipping",
            priority="high",
            status="in_progress",
        ),
        SupportTicket(
            id="TCK-1003",
            customer_id="C003",
            order_id="ORD-1003",
            subject="Package arrived damaged - crushed box",
            description="The smart water bottle package arrived completely crushed and the screen is cracked. Photos are ready.",
            category="return_refund",
            priority="high",
            status="open",
        ),
        SupportTicket(
            id="TCK-1004",
            customer_id="C004",
            order_id=None,
            subject="Account suspended - need access to billing invoices",
            description="My account shows suspended status when logging in. I need access to download past invoices for tax purposes.",
            category="account",
            priority="standard",
            status="escalated",
            resolution_notes="Billing supervisor unlocked invoice download portal and verified 2FA authentication.",
        ),
    ]
    for t in tickets:
        if not db.query(SupportTicket).filter(SupportTicket.id == t.id).first():
            db.add(t)

    db.commit()

    # 5. Seed Escalation Events
    seed_escalation_events(db)


def seed_escalation_events(db):
    """Seed chronological escalation audit trail records for tickets TCK-1001 to TCK-1004."""
    events = [
        # TCK-1004 Escalation Audit Trail (Account Suspended - Tax Invoices)
        TicketEscalationEvent(
            ticket_id="TCK-1004",
            timestamp=datetime(2024, 2, 10, 8, 35, 0),
            actor="L1-Agent-Sarah",
            action="opened",
            note="Ticket received from customer portal regarding account suspension and tax invoice urgency.",
        ),
        TicketEscalationEvent(
            ticket_id="TCK-1004",
            timestamp=datetime(2024, 2, 10, 10, 15, 0),
            actor="L1-Agent-Sarah",
            action="escalated",
            note="Escalated to Tier-2 Billing: L1 lacks authority to override suspended account security block.",
        ),
        TicketEscalationEvent(
            ticket_id="TCK-1004",
            timestamp=datetime(2024, 2, 10, 13, 40, 0),
            actor="L2-Supervisor-Marcus",
            action="approved_override",
            note="Supervisor Marcus verified customer tax registration and approved temporary read-only invoice access.",
        ),
        TicketEscalationEvent(
            ticket_id="TCK-1004",
            timestamp=datetime(2024, 2, 10, 15, 0, 0),
            actor="billing-bot",
            action="resolved",
            note="Sent secure 1-time link for past tax invoices. Customer confirmed successful download.",
        ),

        # TCK-1002 Escalation Audit Trail (Address Change In-Transit)
        TicketEscalationEvent(
            ticket_id="TCK-1002",
            timestamp=datetime(2024, 2, 12, 9, 0, 0),
            actor="L1-Agent-Emma",
            action="opened",
            note="Customer requested reroute of keyboard delivery to office address.",
        ),
        TicketEscalationEvent(
            ticket_id="TCK-1002",
            timestamp=datetime(2024, 2, 12, 11, 30, 0),
            actor="L1-Agent-Emma",
            action="escalated",
            note="Package already in-transit with UPS. Escalated to Logistics Supervisor for carrier intercept.",
        ),
        TicketEscalationEvent(
            ticket_id="TCK-1002",
            timestamp=datetime(2024, 2, 12, 14, 0, 0),
            actor="L2-Supervisor-Raj",
            action="approved_override",
            note="UPS Delivery Intercept fee waived; submitted new address to carrier portal.",
        ),

        # TCK-1003 Escalation Audit Trail (Damaged Item)
        TicketEscalationEvent(
            ticket_id="TCK-1003",
            timestamp=datetime(2024, 2, 8, 14, 10, 0),
            actor="L1-Agent-Priya",
            action="opened",
            note="Customer reported smart water bottle arrived completely crushed.",
        ),
        TicketEscalationEvent(
            ticket_id="TCK-1003",
            timestamp=datetime(2024, 2, 8, 15, 0, 0),
            actor="L1-Agent-Priya",
            action="pending_customer",
            note="Requested customer submit photos of damaged box and cracked bottle display.",
        ),

        # TCK-1001 Escalation Audit Trail (Opened Item Return)
        TicketEscalationEvent(
            ticket_id="TCK-1001",
            timestamp=datetime(2024, 1, 10, 9, 5, 0),
            actor="L1-Agent-Priya",
            action="opened",
            note="Return request received for opened noise-cancelling headphones.",
        ),
        TicketEscalationEvent(
            ticket_id="TCK-1001",
            timestamp=datetime(2024, 1, 10, 10, 30, 0),
            actor="L1-Agent-Priya",
            action="pending_customer",
            note="Awaiting customer clarification: defect vs personal comfort change-of-mind.",
        ),
    ]

    for ev in events:
        db.add(ev)

    db.commit()
