"""Print useful diagnostic facts without importing a model or exposing secrets."""

import importlib.metadata
import json
import platform
import shutil
import sqlite3
import sys


def main():
    try:
        parser = importlib.metadata.version("sqlglot")
    except importlib.metadata.PackageNotFoundError:
        parser = None
    with sqlite3.connect(":memory:") as con:
        heap_supported = con.execute("PRAGMA hard_heap_limit").fetchone() is not None
    print(json.dumps({"python": sys.version.split()[0], "os": platform.system(),
                      "sqlite": sqlite3.sqlite_version, "sqlglot": parser,
                      "sqlite_hard_heap_limit_supported": heap_supported,
                      "linux_process_limits_available": sys.platform.startswith("linux"),
                      "ollama_executable_found": shutil.which("ollama") is not None,
                      "gpu_required_for_demo": False}, indent=2))


if __name__ == "__main__":
    main()
