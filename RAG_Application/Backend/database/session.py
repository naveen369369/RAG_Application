"""
Database Session & Connection Management
=========================================
Supports Microsoft SQL Server with automatic fallback to SQLite for local development.

Configurable via .env:
  # Option A: Windows Integrated Authentication (named instance safe)
  SQL_SERVER_HOST=.\\SQLEXPRESS
  SQL_SERVER_DATABASE=Rag_Test
  SQL_SERVER_TRUSTED_CONNECTION=yes

  # Option B: SQL auth
  SQL_SERVER_HOST=localhost
  SQL_SERVER_DATABASE=SupportCRM
  SQL_SERVER_USER=sa
  SQL_SERVER_PASSWORD=your_password
"""
import os
import logging
import urllib.parse
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
    # 1. Direct explicit DATABASE_URL (user-supplied, used as-is)
    db_url = os.getenv("DATABASE_URL", "").strip()
    if db_url:
        return db_url

    # 2. SQL Server via component env vars
    sql_host = os.getenv("SQL_SERVER_HOST", "").strip()
    sql_db = os.getenv("SQL_SERVER_DATABASE", "").strip()
    if sql_host and sql_db:
        driver = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 17 for SQL Server")
        trusted = os.getenv("SQL_SERVER_TRUSTED_CONNECTION", "no").lower() in ("yes", "true", "1")
        if trusted:
            # Use odbc_connect= so backslashes in named instances (.\SQLEXPRESS) are handled safely
            odbc = (
                f"DRIVER={{{driver}}};"
                f"SERVER={sql_host};"
                f"DATABASE={sql_db};"
                f"Trusted_Connection=yes;"
            )
            return f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc)}"
        user = os.getenv("SQL_SERVER_USER", "sa")
        password = os.getenv("SQL_SERVER_PASSWORD", "")
        odbc = (
            f"DRIVER={{{driver}}};"
            f"SERVER={sql_host};"
            f"DATABASE={sql_db};"
            f"UID={user};"
            f"PWD={password};"
        )
        return f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc)}"

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
