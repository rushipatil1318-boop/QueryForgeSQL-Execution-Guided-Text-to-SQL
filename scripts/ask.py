"""Ask an actual model a question against an approved local database snapshot."""

import argparse
from pathlib import Path
import uuid

from queryforgesql.config import load_settings
from queryforgesql.data import verify_manifest, write_json
from queryforgesql.pipeline import run_question
from queryforgesql.providers import make_provider
from queryforgesql.sandbox import DatabaseRunner, database_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/ollama.json"))
    parser.add_argument("--dataset", type=Path, default=Path("data/demo"))
    parser.add_argument("--db-id", default="shop")
    parser.add_argument("--question", required=True)
    parser.add_argument("--evidence", default="")
    parser.add_argument("--reference-date", default=None, help="YYYY-MM-DD for relative date questions")
    parser.add_argument("--no-feedback", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    settings = load_settings(args.config)
    if settings.model.provider == "fixture":
        parser.error("ask requires a real model provider; use scripts.run_demo for scripted fixtures")
    verify_manifest(args.dataset)
    path = database_path(args.dataset / "databases", args.db_id)
    runner = DatabaseRunner(settings.limits)
    identifier = uuid.uuid4().hex[:12]
    question = {"id": identifier, "db_id": args.db_id, "question": args.question,
                "evidence": args.evidence, "reference_date": args.reference_date}
    output = args.output or Path("runs/interactive") / f"{identifier}.json"
    if output.exists():
        parser.error("Output exists; select a new path")
    result = run_question(question, path, runner.schema(path), make_provider(settings.model),
                          runner, settings, not args.no_feedback)
    write_json(output, result)
    print("SQL:", result["final_sql"])
    print("Execution status:", result["final_result"]["status"])
    print("Columns:", result["final_result"].get("columns", []))
    for row in result["final_result"].get("rows", [])[:20]:
        print(row)
    if "error" in result["final_result"]:
        print("Error:", result["final_result"]["error"])
    print("Saved:", output)
    print("No reference answer was supplied; correctness has not been verified.")


if __name__ == "__main__":
    main()
