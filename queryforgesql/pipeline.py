"""Generate -> validate -> execute -> at most two error-driven repairs."""

from dataclasses import asdict
from pathlib import Path
import time

from .config import Settings
from .prompts import initial_messages, repair_message
from .providers import ModelError
from .retrieval import retrieve_schema
from .validation import ValidationError, extract_sql, validate_sql


def run_question(public_question: dict, db_path: Path, schema: dict, provider,
                 runner, settings: Settings, feedback: bool) -> dict:
    """No gold SQL argument exists. Evaluation happens AFTER this returns."""
    forbidden = {"gold_sql", "SQL", "answer", "expected_rows"}.intersection(public_question)
    if forbidden:
        raise ValueError("Do not pass evaluation answers to the generation pipeline")
    started = time.perf_counter()
    question_text = public_question["question"]
    if settings.use_evidence:
        question_text += " " + public_question.get("evidence", "")
    retrieved = retrieve_schema(question_text, schema, settings.schema_top_k, settings.columns_per_table)
    messages = initial_messages(public_question, retrieved, settings.use_evidence)
    attempts = []
    final_result = {"status": "not_run"}
    maximum = 1 + (settings.max_repairs if feedback else 0)
    for index in range(maximum):
        if sum(len(message["content"]) for message in messages) > settings.max_prompt_chars:
            final_result = {"status": "prompt_limit", "error": "Prompt character budget exceeded"}
            break
        attempt = {"attempt": index, "kind": "initial" if index == 0 else "repair",
                   "messages": [dict(message) for message in messages]}
        call_started = time.perf_counter()
        try:
            completion = provider.complete(messages, question_id=public_question["id"],
                                           seed=(settings.seed + index) % 2147483648)
        except ModelError as exc:
            attempt.update({"model_seconds": time.perf_counter() - call_started,
                            "status": "model_error", "error": str(exc)})
            attempts.append(attempt)
            final_result = {"status": "model_error", "error": str(exc)}
            break
        attempt.update(asdict(completion))
        attempt["model_seconds"] = time.perf_counter() - call_started
        sql = extract_sql(completion.text)
        attempt["sql"] = sql
        try:
            validate_sql(sql, settings.limits)
        except ValidationError as exc:
            result = {"status": "validation_error", "error": str(exc)}
        else:
            result = runner.execute(db_path, sql)
        attempt["status"] = result["status"]
        attempt["result"] = result
        attempts.append(attempt)
        final_result = result
        if result["status"] == "ok":
            break  # Never ask the gold evaluator whether to try another candidate.
        if index + 1 < maximum:
            messages.append({"role": "assistant", "content": completion.text[:settings.limits.max_sql_chars]})
            messages.append(repair_message(result.get("error", result["status"])))
    usage_known = all(a.get("prompt_tokens") is not None and a.get("completion_tokens") is not None
                      for a in attempts) and bool(attempts)
    prompt_tokens = sum(a.get("prompt_tokens") or 0 for a in attempts) if usage_known else None
    completion_tokens = sum(a.get("completion_tokens") or 0 for a in attempts) if usage_known else None
    cfg = settings.model
    cost = None
    if usage_known and cfg.input_usd_per_million is not None and cfg.output_usd_per_million is not None:
        cost = (prompt_tokens * cfg.input_usd_per_million + completion_tokens * cfg.output_usd_per_million) / 1000000
    return {"id": public_question["id"], "db_id": public_question["db_id"],
            "question": public_question["question"], "retrieval": retrieved,
            "feedback_enabled": feedback, "attempts": attempts,
            "model_calls": len(attempts), "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens, "estimated_api_usd": cost,
            "final_sql": attempts[-1].get("sql") if attempts else None,
            "final_result": final_result, "pipeline_seconds": time.perf_counter() - started,
            "correctness_note": "Executable SQL can still answer the wrong question."}
