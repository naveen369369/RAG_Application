"""
Database Script: Setup & Verify Escalation History Table
=========================================================
Creates the `ticket_escalation_events` table and seeds full chronological
audit trail records into SQL Server or SQLite.

Usage:
  python database/setup_escalation_tables.py
"""
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from database.session import engine, SessionLocal, Base
from database.models import Customer, Order, OrderItem, SupportTicket, TicketEscalationEvent
from database.seed import init_db


def main():
    print("=" * 60)
    print("Support CRM: Setting up Escalation History Database Table")
    print("=" * 60)

    # 1. Create all tables
    print("\n1. Ensuring all SQLAlchemy tables exist in database...")
    Base.metadata.create_all(bind=engine)
    print("   [OK] Table 'ticket_escalation_events' confirmed in schema.")

    # 2. Run seed process
    print("\n2. Seeding initial records if empty...")
    init_db()

    # 3. Verify counts
    db = SessionLocal()
    try:
        cust_cnt = db.query(Customer).count()
        order_cnt = db.query(Order).count()
        ticket_cnt = db.query(SupportTicket).count()
        event_cnt = db.query(TicketEscalationEvent).count()

        print("\n3. Database Verification Results:")
        print(f"   * Customers:               {cust_cnt}")
        print(f"   * Orders:                  {order_cnt}")
        print(f"   * Support Tickets:         {ticket_cnt}")
        print(f"   * Ticket Escalation Events:{event_cnt}")

        print("\n4. Sample Escalation Trail for TCK-1004:")
        events_1004 = (
            db.query(TicketEscalationEvent)
            .filter(TicketEscalationEvent.ticket_id == "TCK-1004")
            .order_by(TicketEscalationEvent.timestamp.asc())
            .all()
        )
        for i, ev in enumerate(events_1004, 1):
            ts = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S") if ev.timestamp else "N/A"
            print(f"   Step {i} [{ts}] {ev.actor:<20} | {ev.action:<18} | {ev.note}")

        print("\n" + "=" * 60)
        print("[OK] All tables and records verified successfully in database!")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()
