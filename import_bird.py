"""Import a deterministic small subset from local official BIRD databases."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from queryforgesql.data import load_examples, save_dataset, sha256_file
from queryforgesql.sandbox import database_path, DatabaseRunner


def select_examples(examples, db_ids: list[str], max_cases: int, seed: int):
    """Difficulty round-robin, with a stable hash order independent of input order."""
    from collections import defaultdict, deque
    groups = defaultdict(list)
    for example in examples:
        if example.db_id in db_ids:
            groups[(example.db_id, example.difficulty)].append(example)
    pools = []
    for key in sorted(groups):
        ordered = sorted(groups[key], key=lambda e: hashlib.sha256(f"{seed}:{e.id}".encode()).hexdigest())
        pools.append(deque(ordered))
    selected = []
    while any(pools) and len(selected) < max_cases:
        for pool in pools:
            if pool and len(selected) < max_cases:
                selected.append(pool.popleft())
    if not selected:
        raise ValueError("No examples match requested database IDs")
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=Path("data/raw/bird/mini_dev_sqlite.jsonl"))
    parser.add_argument("--db-root", type=Path, required=True, help="Parent containing db_id/db_id.sqlite")
    parser.add_argument("--db-ids", nargs="+", default=["california_schools"])
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/bird_small"))
    args = parser.parse_args()
    if args.max_cases < 1:
        parser.error("--max-cases must be positive")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Use a new output directory; an existing dataset is never overwritten")
    examples = load_examples(args.questions)
    selected = select_examples(examples, args.db_ids, args.max_cases, args.seed)
    source_path = args.questions.parent / "source.json"
    source = json.loads(source_path.read_text()) if source_path.exists() else {"kind": "local_bird_import", "version": "user_supplied"}
    if source.get("sha256") and source["sha256"] != sha256_file(args.questions):
        raise ValueError("Question source fingerprint does not match source.json")
    source["imported_questions_sha256"] = sha256_file(args.questions)
    source["selection"] = "database/difficulty round-robin, seeded hash within groups; no gold-based filtering"
    hashes = {}
    for db_id in sorted({e.db_id for e in selected}):
        original = database_path(args.db_root, db_id)
        if any(Path(str(original) + ending).exists() for ending in ("-wal", "-journal")):
            raise ValueError("Close the source database and provide a clean offline snapshot")
        target = args.output / "databases" / db_id / f"{db_id}.sqlite"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        DatabaseRunner().schema(target)
        hashes[db_id] = sha256_file(target)
    save_dataset(args.output, selected, source, args.seed, hashes)
    print(f"Imported {len(selected)} cases from {len(hashes)} databases into {args.output}.")
    print("This is a development subset. Unseen-database claims require the documented disjoint protocol.")


if __name__ == "__main__":
    main()
