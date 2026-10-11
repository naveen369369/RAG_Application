"""
Database Schema and Query Tools for ReAct Agent
================================================
Provides dynamic database schema introspection and safe read-only SQL query execution.
Never hardcodes table or column names; inspects live database metadata dynamically via SQLAlchemy.
Never exposes database connection credentials.
"""
from __future__ import annotations

import decimal
import datetime
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from sqlalchemy import inspect, text
from database.session import engine

logger = logging.getLogger(__name__)

# Disallowed SQL statements to ensure read-only execution
_WRITE_KEYWORDS_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)

# Sanitize/redact sensitive patterns from error messages
_CREDENTIAL_PATTERNS = re.compile(
    r"(password|pwd|secret|token|api_key|trusted_connection|driver)=[^;&\s]+",
    re.IGNORECASE,
)


def _sanitize_error_message(msg: str) -> str:
    """Remove any connection strings, passwords, or credentials from error output."""
    if not msg:
        return "Unknown database error."
    sanitized = _CREDENTIAL_PATTERNS.sub(r"\1=***", str(msg))
    # Hide host/port details if present
    sanitized = re.sub(r"//[^/@]+@", "//***:***@", sanitized)
    return sanitized


def _json_serializable(val: Any) -> Any:
    """Convert DB types (datetime, Decimal, bytes, etc.) to JSON-friendly primitives."""
    if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
        return val.isoformat()
    if isinstance(val, decimal.Decimal):
        return float(val)
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return val


def make_database_schema_tool():
    """
    Factory creating the dynamic database_schema tool.
    Inspects live tables, columns, data types, PKs, FKs, constraints, and sample values.
    """
    @tool
    def database_schema(table_name: Optional[str] = None) -> dict:
        """
        Dynamically inspect and retrieve the database schema, including all tables, columns,
        data types, primary keys, foreign keys, table relationships, constraints, and sample records.

        Use this tool whenever:
        - The user asks a relational or database question (e.g., 'Which customer has the most tickets?',
          'What is the total order value per customer tier?', 'Which orders have damaged items?').
        - You need to understand the database structure, table relationships, foreign keys, or column names
          BEFORE constructing and executing a SQL query.

        Do NOT call this tool for general store policy or FAQ questions (use rag_retrieval for those).

        Args:
            table_name: Optional table name to inspect. If omitted or 'all', inspects all tables.

        Returns:
            Dict with:
              - tables: list of all table names
              - schema: mapping of table name to columns (with data types, nullability, PK, FK),
                        primary keys, foreign keys, relationships, constraints, and sample rows.
              - relationships_summary: plain-English summary of foreign key relationships.
        """
        try:
            inspector = inspect(engine)
            all_tables = inspector.get_table_names()

            if not all_tables:
                return {
                    "found": False,
                    "tables": [],
                    "message": "No database tables found in current database.",
                }

            # Filter table if a specific table was requested
            target_tables = all_tables
            if table_name and table_name.strip().lower() not in ("all", "", "none"):
                requested = table_name.strip().lower()
                matched = [t for t in all_tables if t.lower() == requested]
                if matched:
                    target_tables = matched
                else:
                    return {
                        "found": False,
                        "error": "TABLE_NOT_FOUND",
                        "available_tables": all_tables,
                        "message": f"Table '{table_name}' was not found. Available tables: {', '.join(all_tables)}",
                    }

            schema_info: Dict[str, Any] = {}
            relationships_summary: List[str] = []

            dialect_name = engine.dialect.name.lower()

            for tbl in target_tables:
                # 1. Columns & data types
                columns_meta = []
                for col in inspector.get_columns(tbl):
                    columns_meta.append({
                        "name": col.get("name"),
                        "type": str(col.get("type")),
                        "nullable": col.get("nullable", True),
                        "default": str(col.get("default")) if col.get("default") is not None else None,
                    })

                # 2. Primary Keys
                pk_info = inspector.get_pk_constraint(tbl) or {}
                pk_columns = pk_info.get("constrained_columns", [])

                # 3. Foreign Keys
                fk_info = inspector.get_foreign_keys(tbl) or []
                fks_clean = []
                for fk in fk_info:
                    fk_entry = {
                        "constrained_columns": fk.get("constrained_columns", []),
                        "referred_table": fk.get("referred_table"),
                        "referred_columns": fk.get("referred_columns", []),
                    }
                    fks_clean.append(fk_entry)

                    # Build human-readable relationship description
                    from_cols = ", ".join(fk.get("constrained_columns", []))
                    to_tbl = fk.get("referred_table")
                    to_cols = ", ".join(fk.get("referred_columns", []))
                    relationships_summary.append(f"{tbl}.{from_cols} -> {to_tbl}.{to_cols}")

                # 4. Constraints / Indexes
                indexes_info = inspector.get_indexes(tbl) or []
                indexes_clean = [
                    {"name": idx.get("name"), "columns": idx.get("column_names", []), "unique": idx.get("unique", False)}
                    for idx in indexes_info
                ]

                # 5. Dynamic Sample values (up to 2 sample rows per table, credentials never included)
                sample_rows = []
                try:
                    with engine.connect() as conn:
                        if dialect_name == "mssql":
                            query = text(f"SELECT TOP 2 * FROM [{tbl}]")
                        else:
                            query = text(f'SELECT * FROM "{tbl}" LIMIT 2')
                        res = conn.execute(query)
                        for r in res.fetchall():
                            row_dict = {k: _json_serializable(v) for k, v in dict(r._mapping).items()}
                            sample_rows.append(row_dict)
                except Exception as sample_err:
                    logger.debug("Sample fetch skipped for table %s: %s", tbl, sample_err)

                schema_info[tbl] = {
                    "columns": columns_meta,
                    "primary_keys": pk_columns,
                    "foreign_keys": fks_clean,
                    "indexes": indexes_clean,
                    "sample_rows": sample_rows,
                }

            return {
                "found": True,
                "database_dialect": dialect_name,
                "tables": all_tables,
                "inspected_tables": target_tables,
                "schema": schema_info,
                "relationships_summary": relationships_summary,
            }

        except Exception as exc:
            sanitized = _sanitize_error_message(str(exc))
            logger.error("Error inspecting database schema: %s", sanitized)
            return {
                "found": False,
                "error": "SCHEMA_INSPECTION_ERROR",
                "message": sanitized,
            }

    return database_schema


def make_db_query_tool():
    """
    Factory creating the safe, read-only db_query tool.
    Executes SELECT statements generated by the agent after reading schema.
    """
    @tool
    def db_query(query: str, limit: int = 50) -> dict:
        """
        Execute a safe, read-only SQL query against the database to answer relational questions.
        Use this tool AFTER calling database_schema to understand the tables and columns.
        Only read-only SELECT queries are allowed.

        Args:
            query: The SQL SELECT statement to execute (e.g. 'SELECT c.name, COUNT(t.id) FROM customers c JOIN support_tickets t ON c.id = t.customer_id GROUP BY c.name').
            limit: Maximum rows to return (default 50, max 100).

        Returns:
            Dict containing 'columns', 'rows' (list of dicts), 'row_count', or error details.
        """
        clean_sql = query.strip()

        # Remove surrounding markdown fences if model passed ```sql ... ```
        if clean_sql.startswith("```"):
            lines = clean_sql.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_sql = "\n".join(lines).strip()

        clean_sql = clean_sql.rstrip(";")

        # Read-only validation
        if not clean_sql.upper().startswith(("SELECT", "WITH")):
            return {
                "success": False,
                "error": "READ_ONLY_VIOLATION",
                "message": "Only read-only SELECT statements are permitted. Write and DDL operations are blocked.",
            }

        # Check for disallowed mutation keywords
        if _WRITE_KEYWORDS_RE.search(clean_sql):
            return {
                "success": False,
                "error": "MUTATION_BLOCKED",
                "message": "Query contains disallowed mutation keywords (INSERT/UPDATE/DELETE/DROP/ALTER/EXEC). Only SELECT statements are permitted.",
            }

        safe_limit = max(1, min(int(limit), 100))

        try:
            with engine.connect() as conn:
                stmt = text(clean_sql)
                result = conn.execute(stmt)

                columns = list(result.keys()) if result.returns_rows else []
                fetched = result.fetchmany(safe_limit) if result.returns_rows else []

                rows = []
                for r in fetched:
                    row_dict = {col: _json_serializable(val) for col, val in dict(r._mapping).items()}
                    rows.append(row_dict)

                return {
                    "success": True,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "truncated": len(rows) >= safe_limit,
                }

        except Exception as exc:
            sanitized = _sanitize_error_message(str(exc))
            logger.error("SQL execution error: %s", sanitized)
            return {
                "success": False,
                "error": "SQL_EXECUTION_ERROR",
                "message": sanitized,
            }

    return db_query
