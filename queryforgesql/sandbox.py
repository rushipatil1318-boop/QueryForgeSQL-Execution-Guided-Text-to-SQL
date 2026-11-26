"""Parent-side process runner. SQL is stdin JSON, never a shell command."""

from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from .config import Limits


def database_path(root: Path, db_id: str) -> Path:
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]+", db_id):
        raise ValueError("Invalid database id")
    root = root.resolve()
    path = (root / db_id / f"{db_id}.sqlite").resolve()
    if not path.is_relative_to(root):
        raise ValueError("Database path escapes approved root")
    if not path.is_file():
        raise FileNotFoundError(f"Missing snapshot: {path}")
    return path


class DatabaseRunner:
    def __init__(self, limits: Limits | None = None):
        self.limits = limits or Limits()

    def request(self, db_path: Path, action: str, sql: str = "") -> dict:
        if action not in {"query", "schema"}:
            raise ValueError("Unknown database action")
        request = {"action": action, "db_path": str(db_path.resolve()), "sql": sql,
                   "limits": asdict(self.limits)}
        # No API keys or model credentials are passed to the SQL child.
        env = {k: v for k, v in os.environ.items()
               if k in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG"}}
        env["PYTHONIOENCODING"] = "utf-8"
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "queryforgesql.worker"],
                input=json.dumps(request).encode("utf-8"), capture_output=True,
                timeout=self.limits.wall_seconds + 2, env=env,
                cwd=Path(__file__).resolve().parents[1], check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "SQL worker exceeded its wall-clock budget",
                    "worker_wall_seconds": time.perf_counter() - started}
        if completed.returncode != 0:
            return {"status": "worker_failed", "error": "SQL worker stopped (possible OS resource limit)",
                    "returncode": completed.returncode,
                    "worker_wall_seconds": time.perf_counter() - started}
        try:
            if len(completed.stdout) > self.limits.max_result_bytes + 100000:
                raise ValueError("Worker output exceeds protocol budget")
            result = json.loads(completed.stdout)
        except (ValueError, UnicodeError):
            result = {"status": "worker_failed", "error": "Invalid worker response"}
        result["worker_wall_seconds"] = time.perf_counter() - started
        return result

    def schema(self, db_path: Path) -> dict:
        result = self.request(db_path, "schema")
        if result["status"] != "ok":
            raise RuntimeError(result.get("error", "Schema inspection failed"))
        return result["schema"]

    def execute(self, db_path: Path, sql: str) -> dict:
        return self.request(db_path, "query", sql)
