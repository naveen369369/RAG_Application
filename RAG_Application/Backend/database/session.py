"""
Database Session & Connection Management
=========================================
Supports Microsoft SQL Server with automatic fallback to SQLite for local development.

Configurable via .env:
  # Option 1: Full Connection String
  DATABASE_URL=mssql+pyodbc://username:password@server_name/database_name?driver=ODBC+Driver+17+for+SQL+Server
  
  # Option 2: SQL Server Components
  SQL_SERVER_HOST=localhost
  SQL_SERVER_DATABASE=SupportCRM
  SQL_SERVER_USER=sa
  SQL_SERVER_PASSWORD=your_password
  SQL_SERVER_DRIVER=ODBC Driver 17 for SQL Server
  SQL_SERVER_TRUSTED_CONNECTION=yes   # for Windows Authentication
"""
import os
import logging
from pathlib import Path
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from Backend/.env
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

logger = logging.getLogger(__name__)

Base = declarative_base()

def _get_database_url() -> str:
    # 1. Direct explicit DATABASE_URL
    db_url = os.getenv("DATABASE_URL", "").strip()
    if db_url:
        return db_url

    # 2. Check for SQL Server environment variables
    sql_host = os.getenv("SQL_SERVER_HOST", "").strip()
    sql_db = os.getenv("SQL_SERVER_DATABASE", "").strip()
    if sql_host and sql_db:
        driver = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 17 for SQL Server").replace(" ", "+")
        trusted = os.getenv("SQL_SERVER_TRUSTED_CONNECTION", "no").lower() in ("yes", "true", "1")
        if trusted:
            return f"mssql+pyodbc://@{sql_host}/{sql_db}?driver={driver}&trusted_connection=yes"
        user = os.getenv("SQL_SERVER_USER", "sa")
        password = os.getenv("SQL_SERVER_PASSWORD", "")
        return f"mssql+pyodbc://{user}:{password}@{sql_host}/{sql_db}?driver={driver}"

    # 3. Default fallback to local SQLite
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    sqlite_path = data_dir / "support_crm.db"
    return f"sqlite:///{sqlite_path.as_posix()}"


_DB_URL = _get_database_url()
_is_sqlite = _DB_URL.startswith("sqlite")

try:
    if _is_sqlite:
        engine = create_engine(_DB_URL, connect_args={"check_same_thread": False})
        logger.info("Using SQLite database: %s", _DB_URL)
    else:
        engine = create_engine(_DB_URL, pool_pre_ping=True, fast_executemany=True)
        logger.info("Using SQL Server database at: %s", _DB_URL.split("@")[-1] if "@" in _DB_URL else _DB_URL)
except Exception as exc:
    logger.warning("Failed to initialize engine for %s: %s. Falling back to SQLite.", _DB_URL, exc)
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    sqlite_path = data_dir / "support_crm.db"
    _DB_URL = f"sqlite:///{sqlite_path.as_posix()}"
    engine = create_engine(_DB_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Direct context manager or session getter for agent tools."""
    return SessionLocal()
