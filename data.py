"""Dataset records, integrity checks, and database-disjoint split checks."""

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from .sandbox import database_path


@dataclass(frozen=True)
class Example:
    id: str
    db_id: str
    question: str
    gold_sql: str
    evidence: str = ""
    difficulty: str = "unknown"
    reference_date: str | None = None

    def public(self) -> dict:
        return {name: value for name, value in asdict(self).items() if name != "gold_sql"}


def normalized_question(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_examples(path: Path) -> list[Example]:
    text = path.read_text(encoding="utf-8-sig")
    records = json.loads(text) if text.lstrip().startswith("[") else [json.loads(line) for line in text.splitlines() if line.strip()]
    examples, seen = [], set()
    for index, record in enumerate(records):
        identifier = str(record.get("id", record.get("question_id", index)))
        sql = record.get("gold_sql", record.get("SQL"))
        db_id, question = record["db_id"], record["question"]
        if identifier in seen:
            raise ValueError(f"Duplicate question id: {identifier}")
        if not isinstance(db_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", db_id):
            raise ValueError("Invalid db_id")
        if not isinstance(question, str) or not question.strip() or not isinstance(sql, str) or not sql.strip():
            raise ValueError("Each example needs nonempty question and reference SQL")
        evidence = record.get("evidence") or ""
        if not isinstance(evidence, str):
            raise ValueError("evidence must be text")
        examples.append(Example(identifier, db_id, question, sql, evidence,
                                record.get("difficulty", "unknown"), record.get("reference_date")))
        seen.add(identifier)
    if not examples:
        raise ValueError("Dataset is empty")
    return examples


def assert_disjoint(train: list[Example], development: list[Example], test: list[Example]):
    """Exact normalized question + database checks; not semantic deduplication."""
    groups = [train, development, test]
    for left in range(3):
        for right in range(left + 1, 3):
            db_overlap = {x.db_id for x in groups[left]} & {x.db_id for x in groups[right]}
            question_overlap = {normalized_question(x.question) for x in groups[left]} & {
                normalized_question(x.question) for x in groups[right]}
            if db_overlap or question_overlap:
                raise ValueError(f"Split leakage: databases={sorted(db_overlap)}, duplicate_questions={len(question_overlap)}")


def verify_manifest(dataset_dir: Path) -> dict:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    if sha256_file(dataset_dir / "examples.jsonl") != manifest["examples_sha256"]:
        raise ValueError("Dataset examples changed after manifest creation")
    for db_id, expected in manifest["database_sha256"].items():
        if sha256_file(database_path(dataset_dir / "databases", db_id)) != expected:
            raise ValueError(f"Database snapshot hash mismatch: {db_id}")
    return manifest


def save_dataset(directory: Path, examples: list[Example], source: dict, seed: int,
                 database_hashes: dict):
    path = directory / "examples.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text("".join(json.dumps(asdict(example), ensure_ascii=False) + "\n" for example in examples), encoding="utf-8")
    temporary.replace(path)
    write_json(directory / "manifest.json", {
        "format": 1, "source": source, "selection_seed": seed,
        "selected_ids": [example.id for example in examples],
        "examples_sha256": sha256_file(path), "database_sha256": database_hashes,
    })
