"""
Database package for Support CRM (SQL Server + SQLite).
"""
from database.session import engine, get_db, get_db_session, Base
from database.models import Customer, Order, OrderItem, SupportTicket
from database.seed import init_db

__all__ = ["engine", "get_db", "get_db_session", "Base", "Customer", "Order", "OrderItem", "SupportTicket", "init_db"]
