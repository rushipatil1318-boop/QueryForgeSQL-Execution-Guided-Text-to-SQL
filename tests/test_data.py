import io
from contextlib import redirect_stdout
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from queryforgesql.data import Example, assert_disjoint, normalized_question, verify_manifest
from queryforgesql.download import download_verified
from queryforgesql.retrieval import retrieve_schema
from scripts.import_bird import select_examples
from scripts.prepare_demo import prepare_demo


class DataTests(unittest.TestCase):
    def test_normalization_handles_unicode_case_and_whitespace(self):
        self.assertEqual(normalized_question("  ＣＯＵＮＴ\n Orders "), "count orders")

    def test_database_leakage_is_detected(self):
        one = Example("1", "same", "Count A", "SELECT 1")
        two = Example("2", "same", "Count B", "SELECT 2")
        with self.assertRaises(ValueError):
            assert_disjoint([one], [two], [])

    def test_duplicate_question_across_databases_is_detected(self):
        one = Example("1", "one", " Count A ", "SELECT 1")
        two = Example("2", "two", "count a", "SELECT 2")
        with self.assertRaises(ValueError):
            assert_disjoint([one], [], [two])

    def test_disjoint_split_is_accepted(self):
        assert_disjoint([Example("1", "one", "A", "SELECT 1")], [], [Example("2", "two", "B", "SELECT 2")])

    def test_changed_database_is_rejected_by_manifest(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            root = Path(temp)
            prepare_demo(root)
            path = root / "databases/shop/shop.sqlite"
            with path.open("ab") as handle:
                handle.write(b"changed")
            with self.assertRaises(ValueError):
                verify_manifest(root)

    def test_selection_is_stable_independent_of_source_order(self):
        examples = [Example(str(i), "one", f"q{i}", "SELECT 1", difficulty=["simple", "moderate"][i % 2]) for i in range(20)]
        first = select_examples(examples, ["one"], 7, 42)
        second = select_examples(list(reversed(examples)), ["one"], 7, 42)
        self.assertEqual([x.id for x in first], [x.id for x in second])
        self.assertEqual(len(first), 7)

    def test_download_retries_connection_reset_then_uses_cache(self):
        payload = b"verified data"
        response = io.BytesIO(payload)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp, redirect_stdout(io.StringIO()):
            destination = Path(temp) / "data.json"
            with patch("urllib.request.urlopen", side_effect=[urllib.error.URLError(ConnectionResetError()), response]) as request, patch("time.sleep"):
                download_verified("https://example.com/data", destination, hashlib.sha256(payload).hexdigest())
                self.assertEqual(request.call_count, 2)
                download_verified("https://example.com/data", destination, hashlib.sha256(payload).hexdigest())
                self.assertEqual(request.call_count, 2)

    def test_download_rejects_wrong_hash_without_writing(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            destination = Path(temp) / "data.json"
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b"bad")):
                with self.assertRaises(ValueError):
                    download_verified("https://example.com/data", destination, "0" * 64)
            self.assertFalse(destination.exists())

    def test_retrieval_is_deterministic_and_keeps_join_keys(self):
        schema = {"tables": {
            "orders": {"columns": [{"name":"id", "type":"INTEGER", "primary_key":True}, {"name":"ordered_at", "type":"TEXT", "primary_key":False}], "foreign_keys":[]},
            "items": {"columns": [{"name":"order_id", "type":"INTEGER", "primary_key":False}, {"name":"quantity", "type":"INTEGER", "primary_key":False}], "foreign_keys":[{"column":"order_id","target_table":"orders","target_column":"id"}]},
        }}
        result = retrieve_schema("quantity of items", schema, top_k=2, columns_per_table=1)
        self.assertIn("order_id", result["columns"]["items"])
        self.assertIn("id", result["columns"]["orders"])
        self.assertEqual(result, retrieve_schema("quantity of items", schema, top_k=2, columns_per_table=1))

    def test_local_import_copies_offline_snapshot_and_preserves_provenance(self):
        # Exercise the BIRD-format import path with ORIGINAL teaching records,
        # not fabricated BIRD results or benchmark database contents.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            root = Path(temp)
            prepare_demo(root / "source")
            completed = subprocess.run([
                sys.executable, "-m", "scripts.import_bird",
                "--questions", str(root / "source/examples.jsonl"),
                "--db-root", str(root / "source/databases"),
                "--db-ids", "shop", "--max-cases", "3",
                "--output", str(root / "imported")],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            manifest = verify_manifest(root / "imported")
            self.assertEqual(len(manifest["selected_ids"]), 3)
            self.assertEqual(set(manifest["database_sha256"]), {"shop"})


if __name__ == "__main__":
    unittest.main()
