"""One CPU-friendly command: prepare fixtures, then test both pipeline arms."""

import argparse
from pathlib import Path
from queryforgesql.config import load_settings
from scripts.prepare_demo import prepare_demo
from scripts.evaluate import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("runs/demo"))
    args = parser.parse_args()
    prepare_demo(Path("data/demo"))
    evaluate(Path("data/demo"), load_settings("configs/demo.json"), args.output, [42])
    print("Demo finished. Responses were SCRIPTED; no LLM was called and no BIRD accuracy was measured.")


if __name__ == "__main__":
    main()
