from dataclasses import replace
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from queryforgesql.config import Settings
from queryforgesql.evaluation import compare_results
from scripts.evaluate import evaluate
from scripts.prepare_demo import prepare_demo


def result(rows, columns=None):
    return {"status": "ok", "columns": columns or ["x"], "rows": rows}


class ComparisonTests(unittest.TestCase):
    def test_unordered_comparison_preserves_duplicate_counts(self):
        score = compare_results(result([[1]]), result([[1], [1]]), "SELECT id FROM t")
        self.assertFalse(score["strict_match"])
        self.assertTrue(score["bird_set_match"])

    def test_order_by_requires_order_for_strict_metric(self):
        score = compare_results(result([[2], [1]]), result([[1], [2]]), "SELECT id FROM t ORDER BY id")
        self.assertFalse(score["strict_match"])
        self.assertTrue(score["bird_set_match"])

    def test_no_order_by_compares_bags(self):
        score = compare_results(result([[2], [1]]), result([[1], [2]]), "SELECT id FROM t")
        self.assertTrue(score["strict_match"])

    def test_empty_results_with_different_width_are_not_a_match(self):
        score = compare_results(result([], ["a", "b"]), result([], ["a"]), "SELECT a FROM t")
        self.assertFalse(score["strict_match"])

    def test_reference_timeout_is_disclosed_not_scored_as_match(self):
        score = compare_results(result([]), {"status": "timeout"}, "SELECT a FROM t")
        self.assertFalse(score["scoreable"])
        self.assertFalse(score["strict_match"])


class ExperimentTests(unittest.TestCase):
    def test_demo_is_paired_logged_and_resumable(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp, redirect_stdout(io.StringIO()):
            root = Path(temp)
            dataset, output = root / "data", root / "run"
            prepare_demo(dataset)
            summary = evaluate(dataset, Settings(), output, [42])
            self.assertEqual(summary["run_type"], "scripted_plumbing_demo")
            scores = summary["by_seed"]["42"]
            self.assertEqual(scores["baseline"]["strict_execution_accuracy"], 2/6)
            self.assertEqual(scores["feedback"]["strict_execution_accuracy"], 4/6)
            self.assertEqual(scores["feedback"]["model_calls_total"], 10)
            self.assertIsNone(scores["feedback"]["estimated_api_usd_total"])
            logs = [json.loads(line) for line in (output / "predictions.jsonl").read_text().splitlines()]
            self.assertEqual(len(logs), 12)
            for identifier in {r["id"] for r in logs}:
                pair = [r for r in logs if r["id"] == identifier]
                self.assertEqual(pair[0]["pipeline"]["attempts"][0]["messages"], pair[1]["pipeline"]["attempts"][0]["messages"])
            wrong = next(r for r in logs if r["id"] == "demo_semantic" and r["arm"] == "feedback")
            self.assertEqual(wrong["pipeline"]["final_result"]["status"], "ok")
            self.assertFalse(wrong["score"]["strict_match"])
            original = (output / "predictions.jsonl").read_bytes()
            with patch("scripts.evaluate.make_provider") as factory:
                evaluate(dataset, Settings(), output, [42])
                self.assertFalse(factory.return_value.complete.called)
            self.assertEqual((output / "predictions.jsonl").read_bytes(), original)
            with self.assertRaises(ValueError):
                evaluate(dataset, replace(Settings(), max_repairs=1), output, [42])


if __name__ == "__main__":
    unittest.main()
