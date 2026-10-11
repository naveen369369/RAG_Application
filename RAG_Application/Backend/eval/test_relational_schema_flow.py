"""
test_relational_schema_flow.py
==============================
Test suite validating the Database Schema Tool and the complete relational agent flow:
  User Question -> Schema Tool -> Understand tables/relationships -> Generate SQL -> DB Query Tool -> Get results -> Answer user

Also proves that for non-database questions, the Schema Tool is NOT called.
"""
from __future__ import annotations

import json
import logging
import sys
import unittest
from pathlib import Path

# Add Backend root to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agent.tools.database_tools import make_database_schema_tool, make_db_query_tool
from agent.react_agent import stream_agent
from rag.rag_pipeline import RAGPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure Windows cp1252 doesn't fail on unicode output in console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class TestDatabaseSchemaFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema_tool = make_database_schema_tool()
        cls.query_tool = make_db_query_tool()
        cls.pipeline = RAGPipeline()

    def test_01_dynamic_schema_inspection(self):
        """1. Schema tool retrieves tables, columns, types, PKs, FKs, relationships, and samples dynamically."""
        result = self.schema_tool.invoke({})
        self.assertTrue(result.get("found"), "Schema tool should report found=True")
        tables = result.get("tables", [])
        self.assertIsInstance(tables, list)
        self.assertGreater(len(tables), 0, "Database must have tables")

        # Verify no hardcoded assumptions: check structure of each table
        schema = result.get("schema", {})
        for table_name in tables:
            self.assertIn(table_name, schema)
            tbl_info = schema[table_name]
            self.assertIn("columns", tbl_info)
            self.assertIn("primary_keys", tbl_info)
            self.assertIn("foreign_keys", tbl_info)
            self.assertIn("sample_rows", tbl_info)

            # Check column types exist
            for col in tbl_info["columns"]:
                self.assertIn("name", col)
                self.assertIn("type", col)
                self.assertIn("nullable", col)

        # Check relationships summary is generated from foreign keys
        relationships = result.get("relationships_summary", [])
        self.assertIsInstance(relationships, list)
        logger.info("Discovered relationships: %s", relationships)

        # Verify credentials are never exposed
        schema_dump = json.dumps(result)
        self.assertNotIn("password", schema_dump.lower())
        self.assertNotIn("trusted_connection", schema_dump.lower())
        print(f" PASS: Dynamically inspected {len(tables)} tables and {len(relationships)} relationships.")

    def test_02_safe_db_query_execution_and_mutation_blocking(self):
        """2. DB query tool executes read-only SELECTs and strictly blocks mutations."""
        # A valid relational query
        valid_sql = """
        SELECT c.name, COUNT(t.id) AS ticket_count
        FROM customers c
        LEFT JOIN support_tickets t ON c.id = t.customer_id
        GROUP BY c.name
        ORDER BY ticket_count DESC
        """
        res = self.query_tool.invoke({"query": valid_sql})
        self.assertTrue(res.get("success"), f"Query failed: {res}")
        self.assertGreater(res.get("row_count", 0), 0, "Query should return rows")
        self.assertIn("columns", res)
        self.assertIn("rows", res)
        logger.info("Sample query result: %s", res["rows"][0])

        # Test safety: blocked mutations
        blocked_drop = self.query_tool.invoke({"query": "DROP TABLE customers"})
        self.assertFalse(blocked_drop.get("success"))
        self.assertEqual(blocked_drop.get("error"), "READ_ONLY_VIOLATION")

        blocked_insert = self.query_tool.invoke({"query": "INSERT INTO customers (id, name) VALUES ('C999', 'Hacker')"})
        self.assertFalse(blocked_insert.get("success"))
        self.assertEqual(blocked_insert.get("error"), "READ_ONLY_VIOLATION")

        # Test error sanitization
        syntax_err = self.query_tool.invoke({"query": "SELECT * FROM non_existent_table_xyz_123"})
        self.assertFalse(syntax_err.get("success"))
        self.assertEqual(syntax_err.get("error"), "SQL_EXECUTION_ERROR")
        self.assertNotIn("password", str(syntax_err).lower())
        print(" PASS: DB query executes read-only queries and safely blocks mutations and sanitizes errors.")

    def test_03_end_to_end_relational_question_flow(self):
        """3. Relational question: Schema Tool -> SQL generation -> DB query -> Final answer."""
        question = "Which customer has the most support tickets in the database, and how many tickets do they have?"
        print(f"\n--- Testing Relational Question Flow: '{question}' ---")

        tools_called = []
        final_answer = ""

        for line in stream_agent(self.pipeline, question):
            try:
                data = json.loads(line)
            except Exception:
                continue

            event = data.get("event")
            if event == "tool_start":
                tool_name = data.get("tool")
                tools_called.append(tool_name)
                print(f" -> Tool Called: {tool_name} with args: {data.get('args')}")
            elif event == "tool_result":
                tool_name = data.get("tool")
                print(f" <- Tool Result received for: {tool_name}")
            elif event == "token":
                final_answer += data.get("t", "")

        print(f"\nAll Tools Called in Trajectory: {tools_called}")
        try:
            print(f"Final Answer: {final_answer}\n")
        except UnicodeEncodeError:
            print(f"Final Answer: {final_answer.encode('ascii', errors='replace').decode('ascii')}\n")

        # 1. Proves Schema Tool was invoked first
        self.assertIn(
            "database_schema",
            tools_called,
            "Agent MUST call 'database_schema' for relational questions to inspect table structure.",
        )

        # 2. Proves DB Query Tool was invoked next with generated SQL
        self.assertIn(
            "db_query",
            tools_called,
            "Agent MUST call 'db_query' to execute SQL based on the retrieved schema.",
        )

        # Verify ordering: database_schema was called before db_query
        schema_idx = tools_called.index("database_schema")
        query_idx = tools_called.index("db_query")
        self.assertLess(
            schema_idx,
            query_idx,
            "Agent must call database_schema BEFORE calling db_query.",
        )

        # 3. Proves final answer contains ground-truth relational data: Bob Smith has 2 tickets
        self.assertIn(
            "bob smith",
            final_answer.lower(),
            "Final answer must identify Bob Smith as having the most tickets.",
        )
        self.assertIn(
            "2",
            final_answer,
            "Final answer must state Bob Smith has 2 tickets.",
        )
        print(" PASS: Full Relational Flow confirmed: User Question -> database_schema -> SQL -> db_query -> grounded answer.")

    def test_04_non_database_question_does_not_call_schema_tool(self):
        """4. Non-database questions (policy/return questions) must NOT call database_schema."""
        question = "What is the return window for items and what condition must they be in?"
        print(f"\n--- Testing Non-Database Question Flow: '{question}' ---")

        tools_called = []
        for line in stream_agent(self.pipeline, question):
            try:
                data = json.loads(line)
            except Exception:
                continue
            if data.get("event") == "tool_start":
                tools_called.append(data.get("tool"))

        print(f"Tools called for policy question: {tools_called}")
        self.assertNotIn(
            "database_schema",
            tools_called,
            "Non-database questions must NOT call database_schema tool.",
        )
        self.assertNotIn(
            "db_query",
            tools_called,
            "Non-database questions must NOT call db_query tool.",
        )
        self.assertIn(
            "rag_retrieval",
            tools_called,
            "Policy questions must use rag_retrieval.",
        )
        print(" PASS: Schema tool correctly skipped for non-database question.")


if __name__ == "__main__":
    unittest.main()
