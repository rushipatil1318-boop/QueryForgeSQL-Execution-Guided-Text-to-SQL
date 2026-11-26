from pathlib import Path
import tempfile
import unittest

from queryforgesql.config import Settings
from queryforgesql.data import load_examples
from queryforgesql.pipeline import run_question
from queryforgesql.providers import FixtureProvider, HTTPProvider, ModelError
from queryforgesql.config import ModelSettings
from scripts.prepare_demo import prepare_demo


class FakeRunner:
    def execute(self, path, sql):
        if "missing" in sql:
            return {"status": "error", "error": "no such column: missing"}
        return {"status": "ok", "columns": ["answer"], "rows": [[1]]}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.schema = {"tables": {"orders": {"columns": [{"name": "id", "type": "INTEGER", "primary_key": True}], "foreign_keys": []}}}
        self.question = {"id": "one", "db_id": "shop", "question": "Count orders"}

    def run_case(self, responses, feedback=True):
        provider = FixtureProvider({"one": responses})
        return run_question(self.question, Path("unused"), self.schema, provider,
                            FakeRunner(), Settings(), feedback)

    def test_baseline_makes_one_call(self):
        result = self.run_case(["SELECT missing FROM orders", "SELECT 1"], feedback=False)
        self.assertEqual(result["model_calls"], 1)
        self.assertNotEqual(result["final_result"]["status"], "ok")

    def test_execution_error_can_be_repaired(self):
        result = self.run_case(["SELECT missing FROM orders", "SELECT 1"])
        self.assertEqual(result["model_calls"], 2)
        self.assertEqual(result["final_result"]["status"], "ok")
        self.assertIn("no such column", result["attempts"][1]["messages"][-1]["content"])

    def test_validation_failure_is_repaired_before_execution(self):
        result = self.run_case(["DELETE FROM orders", "SELECT 1"])
        self.assertEqual(result["attempts"][0]["status"], "validation_error")
        self.assertEqual(result["final_result"]["status"], "ok")

    def test_never_exceeds_two_repairs(self):
        result = self.run_case(["SELECT missing FROM orders"])
        self.assertEqual(result["model_calls"], 3)
        self.assertEqual([a["kind"] for a in result["attempts"]], ["initial", "repair", "repair"])

    def test_executable_wrong_query_does_not_trigger_oracle_repair(self):
        result = self.run_case(["SELECT 999", "SELECT 1"])
        self.assertEqual(result["model_calls"], 1)
        self.assertEqual(result["final_sql"], "SELECT 999")

    def test_gold_cannot_enter_public_pipeline(self):
        self.question["gold_sql"] = "SELECT 12345"
        with self.assertRaises(ValueError):
            self.run_case(["SELECT 1"])

    def test_missing_usage_is_not_reported_as_zero_cost(self):
        result = self.run_case(["SELECT 1"])
        self.assertIsNone(result["estimated_api_usd"])
        self.assertIsNone(result["prompt_tokens"])

    def test_network_provider_rejects_plaintext_remote_credentials(self):
        with self.assertRaises(ValueError):
            HTTPProvider(ModelSettings(provider="chat_completions", endpoint="http://example.com/v1/chat/completions"))

    def test_model_failure_stops_loop(self):
        class BrokenProvider:
            def complete(self, messages, **kwargs):
                raise ModelError("Model unavailable")
        result = run_question(self.question, Path("unused"), self.schema, BrokenProvider(), FakeRunner(), Settings(), True)
        self.assertEqual(result["model_calls"], 1)
        self.assertEqual(result["final_result"]["status"], "model_error")

    def test_public_examples_exclude_reference_sql(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            prepare_demo(Path(temp))
            examples = load_examples(Path(temp) / "examples.jsonl")
            self.assertTrue(all("gold_sql" not in example.public() for example in examples))


if __name__ == "__main__":
    unittest.main()
