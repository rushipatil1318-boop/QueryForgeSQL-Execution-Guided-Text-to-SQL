"""Paired baseline / execution-feedback evaluation with resumable JSONL logs."""

import argparse
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import statistics
import sys

import sqlglot

from queryforgesql.config import load_settings
from queryforgesql.data import load_examples, sha256_file, verify_manifest, write_json
from queryforgesql.evaluation import compare_results, summarize
from queryforgesql.pipeline import run_question
from queryforgesql.providers import make_provider
from queryforgesql.sandbox import DatabaseRunner, database_path


def code_fingerprint() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for directory in ("queryforgesql", "scripts"):
        for path in sorted((root / directory).rglob("*.py")):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    # A partial line is never silently dropped; keep it for inspection and start a new run.
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(dataset_dir: Path, settings, output_dir: Path, seeds: list[int]) -> dict:
    manifest = verify_manifest(dataset_dir)
    examples = load_examples(dataset_dir / "examples.jsonl")
    fixture_path = dataset_dir / "fixture_responses.json"
    if settings.model.provider == "fixture" and manifest["source"]["kind"] != "original_teaching_fixture":
        raise ValueError("Scripted fixtures cannot be evaluated as BIRD/model research")
    fixtures = json.loads(fixture_path.read_text()) if settings.model.provider == "fixture" else None
    experiment = {"format": 1, "settings": asdict(settings), "seeds": seeds,
                  "dataset_manifest_sha256": sha256_file(dataset_dir / "manifest.json"),
                  "code_sha256": code_fingerprint(),
                  "fixture_sha256": sha256_file(fixture_path) if fixtures else None,
                  "environment": {"python": sys.version, "platform": platform.platform(),
                                  "sqlite": sqlite3.sqlite_version, "sqlglot": sqlglot.__version__},
                  "run_type": "scripted_plumbing_demo" if fixtures else "llm_evaluation"}
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_path = output_dir / "experiment.json"
    records_path = output_dir / "predictions.jsonl"
    if meta_path.exists():
        if json.loads(meta_path.read_text(encoding="utf-8")) != experiment:
            raise ValueError("Cannot resume: configuration, dataset, code or environment changed. Use a fresh --output")
    elif records_path.exists():
        raise ValueError("Cannot resume predictions without experiment.json")
    else:
        write_json(meta_path, experiment)
    records = read_records(records_path)
    completed = {(r["seed"], r["arm"], r["id"]) for r in records}
    if len(completed) != len(records):
        raise ValueError("Duplicate prediction keys in saved run")
    expected_keys = {(seed, arm, e.id) for seed in seeds for arm in ("baseline", "feedback") for e in examples}
    if not completed.issubset(expected_keys):
        raise ValueError("Saved predictions contain cases outside this experiment")
    runner = DatabaseRunner(settings.limits)
    schemas = {db_id: runner.schema(database_path(dataset_dir / "databases", db_id))
               for db_id in sorted({e.db_id for e in examples})}
    with records_path.open("a", encoding="utf-8") as handle:
        for seed in seeds:
            seeded = replace(settings, seed=seed)
            for arm in ("baseline", "feedback"):
                provider = make_provider(seeded.model, fixtures)
                for example in examples:
                    key = (seed, arm, example.id)
                    if key in completed:
                        continue
                    db_path = database_path(dataset_dir / "databases", example.db_id)
                    pipeline = run_question(example.public(), db_path, schemas[example.db_id],
                                            provider, runner, seeded, feedback=arm == "feedback")
                    # Gold is executed only AFTER the pipeline stops. It is never a repair signal.
                    reference = runner.execute(db_path, example.gold_sql)
                    score = compare_results(pipeline["final_result"], reference, example.gold_sql)
                    record = {"seed": seed, "arm": arm, "id": example.id, "db_id": example.db_id,
                              "difficulty": example.difficulty, "pipeline": pipeline,
                              "reference_sql": example.gold_sql, "reference_result": reference, "score": score}
                    handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                    records.append(record)
                    completed.add(key)
                    print(f"seed={seed} {arm:8s} {example.id:20s} status={pipeline['final_result']['status']:16s} "
                          f"strict_match={score['strict_match']} calls={pipeline['model_calls']}")
    if completed != expected_keys:
        raise ValueError("Saved predictions do not match the requested cases")
    by_seed = {}
    for seed in seeds:
        by_seed[str(seed)] = {arm: summarize([r for r in records if r["seed"] == seed and r["arm"] == arm])
                              for arm in ("baseline", "feedback")}
    variation = {}
    for arm in ("baseline", "feedback"):
        scores = [by_seed[str(seed)][arm]["strict_execution_accuracy"] for seed in seeds]
        variation[arm] = {"mean_strict_accuracy": statistics.mean(scores),
                          "sample_std_across_seeds": statistics.stdev(scores) if len(scores) >= 2 else None}
    summary = {"run_type": experiment["run_type"], "seeds": seeds, "by_seed": by_seed,
               "seed_variation": variation,
               "paired_accuracy_delta_by_seed": {str(seed): by_seed[str(seed)]["feedback"]["strict_execution_accuracy"] - by_seed[str(seed)]["baseline"]["strict_execution_accuracy"] for seed in seeds},
               "note": "Fixture scores demonstrate control flow only; they are not model or BIRD performance. Single-instance execution match is not semantic proof."}
    write_json(output_dir / "summary.json", summary)
    print(f"Saved complete logs and summary: {output_dir}")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/demo"))
    parser.add_argument("--config", type=Path, default=Path("configs/demo.json"))
    parser.add_argument("--output", type=Path, default=Path("runs/demo"))
    parser.add_argument("--seeds", default="42", help="Comma-separated, e.g. 42,43,44")
    args = parser.parse_args()
    seeds = [int(value) for value in args.seeds.split(",")]
    if len(seeds) != len(set(seeds)) or not seeds:
        parser.error("Seeds must be a nonempty unique list")
    evaluate(args.dataset, load_settings(args.config), args.output, seeds)


if __name__ == "__main__":
    main()
