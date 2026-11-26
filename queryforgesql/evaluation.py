"""Reference execution is kept outside generation and its repair loop."""

from collections import Counter, defaultdict
import math
import statistics
import sqlglot


def freeze(value):
    if isinstance(value, list):
        return tuple(freeze(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, freeze(item)) for key, item in value.items()))
    return value


def compare_results(prediction: dict, reference: dict, gold_sql: str) -> dict:
    if reference["status"] != "ok":
        return {"scoreable": False, "strict_match": False, "bird_set_match": False,
                "reason": "reference_execution_failed", "reference_status": reference["status"]}
    if prediction["status"] != "ok":
        return {"scoreable": True, "strict_match": False, "bird_set_match": False,
                "reason": "prediction_not_executable"}
    predicted = [freeze(row) for row in prediction["rows"]]
    expected = [freeze(row) for row in reference["rows"]]
    try:
        tree = sqlglot.parse_one(gold_sql, read="sqlite")
        ordered = bool(tree.args.get("order"))
    except sqlglot.errors.SqlglotError:
        return {"scoreable": False, "strict_match": False, "bird_set_match": False,
                "reason": "reference_order_contract_unparseable"}
    # Column aliases are ignored, but number and position of columns are preserved.
    width_ok = len(prediction["columns"]) == len(reference["columns"])
    strict = predicted == expected if ordered else Counter(predicted) == Counter(expected)
    return {"scoreable": True, "strict_match": width_ok and strict,
            "bird_set_match": set(predicted) == set(expected),
            "ordered": ordered, "reason": "compared_complete_results"}


def _percentile(values: list[float], percentile: float):
    return sorted(values)[max(0, math.ceil(len(values) * percentile) - 1)] if values else None


def summarize(records: list[dict]) -> dict:
    if not records:
        return {"n": 0, "strict_execution_accuracy": None, "bird_set_execution_accuracy": None}
    n = len(records)
    attempts = [attempt for record in records for attempt in record["pipeline"]["attempts"]]
    generated = [attempt for attempt in attempts if "sql" in attempt]
    initial_failures = [record for record in records if record["pipeline"]["attempts"]
                        and record["pipeline"]["attempts"][0]["status"] not in {"ok", "model_error"}]
    repaired = [record for record in initial_failures if record["pipeline"]["final_result"]["status"] == "ok"]
    latencies = [record["pipeline"]["pipeline_seconds"] for record in records]
    costs = [record["pipeline"]["estimated_api_usd"] for record in records]
    groups = defaultdict(list)
    databases = defaultdict(list)
    for record in records:
        groups[record["difficulty"]].append(record)
        databases[record["db_id"]].append(record)

    def score_group(group):
        return {"n": len(group), "strict_execution_accuracy": sum(r["score"]["strict_match"] for r in group) / len(group)}

    strict_correct = sum(record["score"]["strict_match"] for record in records)
    scoreable = sum(record["score"]["scoreable"] for record in records)
    invalid_statuses = {"validation_error", "sql_error", "authorization_error"}
    return {
        "n": n, "strict_execution_accuracy": strict_correct / n,
        "bird_set_execution_accuracy": sum(record["score"]["bird_set_match"] for record in records) / n,
        "reference_failures": n - scoreable,
        "scoreable_examples": scoreable,
        "strict_accuracy_on_scoreable_only": strict_correct / scoreable if scoreable else None,
        "executable_query_rate": sum(r["pipeline"]["final_result"]["status"] == "ok" for r in records) / n,
        "initial_invalid_query_rate": sum(bool(r["pipeline"]["attempts"]) and r["pipeline"]["attempts"][0]["status"] in invalid_statuses for r in records) / n,
        "attempt_invalid_query_rate": sum(a["status"] in invalid_statuses for a in generated) / len(generated) if generated else None,
        "attempt_validation_rejection_rate": sum(a["status"] == "validation_error" for a in generated) / len(generated) if generated else None,
        "model_error_cases": sum(r["pipeline"]["final_result"]["status"] == "model_error" for r in records),
        "final_status_counts": dict(Counter(r["pipeline"]["final_result"]["status"] for r in records)),
        "initial_execution_or_validation_failures": len(initial_failures),
        "repair_executability_success_rate": len(repaired) / len(initial_failures) if initial_failures else None,
        "repair_correctness_success_rate": sum(r["score"]["strict_match"] for r in repaired) / len(initial_failures) if initial_failures else None,
        "model_calls_total": sum(r["pipeline"]["model_calls"] for r in records),
        "model_calls_mean": statistics.mean(r["pipeline"]["model_calls"] for r in records),
        "latency_mean_seconds": statistics.mean(latencies),
        "latency_p50_seconds": _percentile(latencies, 0.5),
        "latency_p95_seconds": _percentile(latencies, 0.95),
        "estimated_api_usd_total": sum(costs) if all(c is not None for c in costs) else None,
        "by_difficulty": {key: score_group(group) for key, group in sorted(groups.items())},
        "by_database": {key: score_group(group) for key, group in sorted(databases.items())},
        "denominator_note": "Primary accuracy uses all examples; failed references count as failures and are separately disclosed.",
        "cost_note": "null means unavailable, not free. Token rates exclude local compute and retries/billing outside this client.",
    }
