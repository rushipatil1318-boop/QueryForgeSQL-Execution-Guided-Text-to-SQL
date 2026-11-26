from pathlib import Path
import sqlite3
import tempfile
import unittest

from queryforgesql.config import Limits
from queryforgesql.data import sha256_file
from queryforgesql.sandbox import DatabaseRunner, database_path
from queryforgesql.worker import open_readonly, make_authorizer, inspect_schema
from scripts.prepare_demo import prepare_demo


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.directory = Path(cls.temp.name)
        prepare_demo(cls.directory)
        cls.db = database_path(cls.directory / "databases", "shop")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_schema_contains_columns_and_relationships(self):
        schema = DatabaseRunner().schema(self.db)
        self.assertEqual(len(schema["tables"]), 4)
        self.assertEqual(len(schema["tables"]["order_items"]["foreign_keys"]), 2)

    def test_readonly_aggregate_has_expected_answer(self):
        result = DatabaseRunner().execute(self.db, "SELECT COUNT(*) FROM orders")
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["rows"], [[5]])

    def test_worker_independently_blocks_mutation(self):
        before = sha256_file(self.db)
        result = DatabaseRunner().execute(self.db, "DELETE FROM products")
        self.assertNotEqual(result["status"], "ok")
        self.assertEqual(sha256_file(self.db), before)

    def test_runtime_authorizer_blocks_nonapproved_function(self):
        # sqlite_version is a known SQLGlot function, so this reaches runtime policy.
        result = DatabaseRunner().execute(self.db, "SELECT sqlite_version()")
        self.assertNotEqual(result["status"], "ok")

    def test_no_partial_result_is_scored_at_row_limit(self):
        result = DatabaseRunner(Limits(max_rows=2)).execute(self.db, "SELECT name FROM products")
        self.assertEqual(result["status"], "row_limit", result)
        self.assertNotIn("rows", result)

    def test_small_byte_budget_is_enforced(self):
        result = DatabaseRunner(Limits(max_result_bytes=20)).execute(self.db, "SELECT name FROM products")
        self.assertNotEqual(result["status"], "ok")
        self.assertNotIn("rows", result)

    def test_recursive_query_stops_at_deadline(self):
        sql = "WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x) SELECT SUM(n) FROM x"
        result = DatabaseRunner(Limits(wall_seconds=0.05)).execute(self.db, sql)
        self.assertNotEqual(result["status"], "ok", result)
        self.assertLess(result["worker_wall_seconds"], 3)

    def test_path_traversal_and_missing_database_are_rejected(self):
        with self.assertRaises(ValueError):
            database_path(self.directory, "../secret")
        with self.assertRaises(FileNotFoundError):
            database_path(self.directory, "absent")

    def test_missing_database_does_not_create_a_file(self):
        missing = self.directory / "missing.sqlite"
        result = DatabaseRunner().execute(missing, "SELECT 1")
        self.assertNotEqual(result["status"], "ok")
        self.assertFalse(missing.exists())

    def test_readonly_connection_blocks_write_without_parser(self):
        con = open_readonly(self.db, Limits())
        try:
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("DELETE FROM products")
        finally:
            con.close()

    def test_runtime_authorizer_blocks_write_on_otherwise_writable_connection(self):
        with sqlite3.connect(":memory:") as con:
            con.execute("CREATE TABLE example(id INTEGER)")
            con.set_authorizer(make_authorizer(inspect_schema(con)))
            self.assertEqual(con.execute("SELECT COUNT(*) FROM example").fetchone()[0], 0)
            with self.assertRaises(sqlite3.DatabaseError):
                con.execute("DELETE FROM example")


if __name__ == "__main__":
    unittest.main()
