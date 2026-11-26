import unittest
from queryforgesql.config import Limits, Settings
from queryforgesql.validation import ValidationError, extract_sql, validate_sql


class ValidationTests(unittest.TestCase):
    def test_select_cte_and_union_are_accepted(self):
        for sql in ("SELECT count(*) FROM orders", "WITH x AS (SELECT 1 AS n) SELECT n FROM x",
                    "SELECT 1 UNION ALL SELECT 2", "SELECT '; DELETE' AS harmless_text"):
            with self.subTest(sql=sql):
                self.assertEqual(validate_sql(sql), sql)

    def test_mutations_and_commands_are_rejected(self):
        for sql in ("DELETE FROM customers", "UPDATE customers SET name='x'", "DROP TABLE customers",
                    "INSERT INTO customers VALUES(3,'x')", "PRAGMA query_only=OFF",
                    "ATTACH DATABASE 'x.db' AS other", "VACUUM", "BEGIN", "SELECT 1 INTO file"):
            with self.subTest(sql=sql), self.assertRaises(ValidationError):
                validate_sql(sql)

    def test_multiple_statements_are_rejected(self):
        with self.assertRaises(ValidationError):
            validate_sql("SELECT 1; DELETE FROM customers")

    def test_write_inside_cte_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_sql("WITH x AS (DELETE FROM customers RETURNING *) SELECT * FROM x")

    def test_extension_file_io_and_metadata_are_rejected(self):
        for sql in ("SELECT load_extension('x')", "SELECT readfile('/etc/passwd')",
                    "SELECT * FROM sqlite_master", "SELECT * FROM pragma_table_info('x')",
                    "SELECT * FROM other.customers", "SELECT * FROM read_csv('x')"):
            with self.subTest(sql=sql), self.assertRaises(ValidationError):
                validate_sql(sql)

    def test_empty_nul_and_oversize_are_rejected(self):
        for sql in ("", "SELECT '\x00'", "SELECT '" + "x" * 17000 + "'"):
            with self.assertRaises(ValidationError):
                validate_sql(sql)

    def test_sql_fence_is_extracted_but_prose_is_not_guessed(self):
        self.assertEqual(extract_sql("```sql\nSELECT 1\n```"), "SELECT 1")
        self.assertEqual(extract_sql("Here is SELECT 1"), "Here is SELECT 1")

    def test_repair_budget_and_limits_are_checked(self):
        with self.assertRaises(ValueError):
            Settings(max_repairs=3)
        with self.assertRaises(ValueError):
            Limits(max_rows=0)

    def test_current_clock_queries_require_fixed_dates(self):
        for sql in ("SELECT CURRENT_DATE", "SELECT date('now')", "SELECT datetime()", "SELECT strftime('%Y','now')"):
            with self.subTest(sql=sql), self.assertRaises(ValidationError):
                validate_sql(sql)
        self.assertEqual(validate_sql("SELECT date('2026-10-30','-1 month')"), "SELECT date('2026-10-30','-1 month')")


if __name__ == "__main__":
    unittest.main()
