"""Check database and exact-normalized-question overlap before research runs."""

import argparse
from pathlib import Path
from queryforgesql.data import assert_disjoint, load_examples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    args = parser.parse_args()
    assert_disjoint(load_examples(args.train), load_examples(args.development), load_examples(args.test))
    print("PASS: database sets and exact normalized questions are disjoint.")
    print("This does not establish semantic deduplication or absence of foundation-model pretraining contamination.")


if __name__ == "__main__":
    main()
