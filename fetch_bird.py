"""Download the pinned OFFICIAL SQLite questions, not multi-gigabyte databases."""

import argparse
from pathlib import Path

from queryforgesql.data import load_examples, write_json
from queryforgesql.download import download_verified

REPO = "birdsql/bird_mini_dev"
REVISION = "5b256b5a9c17478f06ed6912612e9a14d17065c8"
SOURCE_FILE = "data/mini_dev_sqlite.jsonl"
SHA256 = "926af2a0d1b47e5d0d15a7aa8a34d4721007f4550a881555b6a89496b54a2606"
SOURCE = {"kind": "bird_mini_dev", "repo": REPO, "revision": REVISION,
          "file": SOURCE_FILE, "sha256": SHA256, "license": "CC-BY-SA-4.0",
          "split": "mini_dev_sqlite", "release": "2026 annotations"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw/bird"))
    args = parser.parse_args()
    path = args.output / "mini_dev_sqlite.jsonl"
    url = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{SOURCE_FILE}"
    download_verified(url, path, SHA256)
    examples = load_examples(path)
    if len(examples) != 500:
        raise ValueError("Unexpected pinned dataset size")
    write_json(args.output / "source.json", SOURCE)
    print(f"Verified {len(examples)} official SQLite questions across {len({e.db_id for e in examples})} databases.")
    print(f"Questions: {path}")
    print("Next: follow docs/DATA.md to obtain official offline SQLite databases, then import a small subset.")


if __name__ == "__main__":
    main()
